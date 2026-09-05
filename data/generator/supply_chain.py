"""Task 6 (A4) — supply-chain coupling: inventory_levels regeneration.

The demo's central claim is that the predicted PUMP-104A failure and the missing
spare part are *the same event*. Today `inventory_levels` has 15 parts below
their reorder point, but the stock numbers were drawn independently of the work
orders that consume parts and of the asset that is failing, so the claim is
narration rather than data. This module rebuilds the snapshot from a modelled
inventory ledger so that the parts sitting below reorder point are the ones that
genuinely sit on PUMP-104A's critical path, short at the moment the Task 2
degradation ramp peaks.

Model
-----
The output table is a *snapshot* — it has no time column — so the ledger lives
here and only its closing position is written. The ledger runs daily over the
work-order window (the `created_at` range of `erp_work_orders`, currently
2026-01-01 .. 2026-06-17) and the snapshot is its final day.

Demand has three sources:

1. **Issues recorded against completed work orders.** `maintenance_logs.
   parts_replaced` (Task 4 output) is the authoritative record of what was
   consumed and when — the work order's `created_at` dates each issue. Five SKUs
   have such a history.
2. **Kitting against open work orders.** A released work order draws its parts
   from the storeroom when the crew is mobilised; the replacement is only
   *logged* at completion. So the 244 OPEN/IN_PROGRESS work orders consume stock
   that no table records. Each one draws parts from its own asset's empirical
   part mix (from the recorded history for that asset) at that asset's empirical
   parts-per-work-order rate. Nothing is invented about *which* parts an asset
   uses: that comes from the asset's own consumption record.
3. **Background demand** for the 100 catalogue parts that have no consumption
   history at all. Their daily rate is inferred from the catalogue itself via the
   textbook reorder-point identity ROP = demand during lead time, i.e.
   `lambda = reorder_point_limit / lead_time_days`. No new parameter.

The coupling to the ramp enters through source 2. Each asset carries a
*severity* series computed from `telemetry_stream`: the daily value of each of
its metrics divided by that metric's own pre-ramp mean, maximised over metrics
and floored at 1.0. For four of the five assets this sits at 1.02-1.10 all
window; for PUMP-104A it climbs to 2.4 as the bearing degrades. A work order
raised on a degrading asset kits `severity` times the baseline number of parts,
and the *excess* over baseline is routed to the catalogue parts whose
`part_description` names the asset's `asset_type` — for PUMP-104A that resolves
to exactly `SKU-BEARING-PUMP-G1` ("High-load Centrifugal Slurry Pump Bearing
Unit"). The routing rule is a plain token match against data neither this module
nor Task 4 wrote.

Replenishment is a continuous-review order-up-to policy: when the inventory
position (on hand + on order) drops below the reorder point, an order is placed
that brings the position back to `S = reorder_point + Q`, arriving
`lead_time_days` later. `Q = ORDER_COVER * lambda_pre * lead_time_days`, where
`lambda_pre` is the pre-ramp demand rate — the policy is sized on the demand the
planner had seen, which is exactly why a demand shift breaks it. `ORDER_COVER`
is the single calibration parameter, solved by bisection so the mean closing
stock matches `stats.json`.

The A4 injection
----------------
Per §2.1 of the design doc, A4 is an *injection*: "the parts on the critical path
of PUMP-104A's work orders are driven below ROP coincident with the A1 ramp."
What must be emergent, per invariant 2, is that those parts "genuinely traverse
work_order_parts_edge to a PUMP-104A work order — verified by a GRAPH_TABLE
query, not by construction", and that is what `s08_stockout_exposure` checks.

The injection itself is explicit and confined to one unobservable quantity: the
*opening* balance on day 0. The original table is a snapshot of "now", not of
1 January, so no data records what the opening balance was. For the parts on the
degrading asset's critical path the opening balance is chosen as the value
closest to the recorded stock level for which the ledger ends below reorder point
with the replenishment still in transit. Everything else — which parts are on the
critical path, when they are consumed, how fast demand rises, when the crossing
happens — comes from the data. See `_solve_opening_balance`.

Catalogue coverage fix
----------------------
Task 4 found that `SKU-AIR-FILTER-08` and `SKU-VALVE-SEAL-22` are consumed by 26
work orders each but have no `inventory_levels` row, so any agent joining
`parts_replaced -> inventory_levels` drops them silently. Both are added here at
$450.00, the median of the three priced maintenance-consumed SKUs
(180 / 450 / 1250), which is the value Task 4's fallback already uses.

Sources
-------
Per the controller decision, calibration is read from the frozen
`*_original_20260810` backups. `assets` and `work_order_parts_edge` are not in
`REWRITE_TABLES`, have no backup, and are read live. Task 2's and Task 4's
outputs are read from `data/generated/*.parquet`, not from BigQuery, because the
live tables have not been reloaded yet — Task 8 owns loading. Nothing here writes
to BigQuery.
"""

import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from hashlib import blake2b
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from google.cloud import bigquery

from config import BACKUP_SUFFIX, DATASET, PROJECT_ID, SEED, STATS

# --- Identifiers -------------------------------------------------------------

GRAPH_NAME = "MiningSupplyChainGraph"
DEGRADING_ASSET = "PUMP-104A"
DEGRADING_METRIC = "vibration_hz"

#: Allow-list of every table this module reads. BigQuery query parameters bind
#: *values* only — a table identifier cannot be parameterised — so the few
#: identifiers that are interpolated into SQL are taken from this dict and
#: re-validated by `_table()` before use. No caller-supplied string reaches a
#: query.
_SOURCE_TABLES = {
    # Rewritten by this project, so read the frozen pre-regeneration snapshot.
    "inventory_levels": f"inventory_levels{BACKUP_SUFFIX}",
    # Not in REWRITE_TABLES: no backup exists and none is needed.
    "assets": "assets",
    "work_order_parts_edge": "work_order_parts_edge",
    # Read live *deliberately*, only to detect whether Task 8 has loaded yet.
    "inventory_levels_live": "inventory_levels",
}
_TABLE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_GENERATED_DIR = os.path.join(os.path.dirname(__file__), "..", "generated")
OUTPUT_PARQUET = "data/generated/inventory_levels.parquet"

# --- The two SKUs Task 4 found missing from the catalogue --------------------

MISSING_SKUS = ("SKU-AIR-FILTER-08", "SKU-VALVE-SEAL-22")
MISSING_SKU_PRICE = 450.00
MISSING_SKU_DESCRIPTIONS = {
    "SKU-AIR-FILTER-08": "Engine Air Filter Cartridge Set",
    "SKU-VALVE-SEAL-22": "Hydraulic Valve Gasket and Seal Kit",
}

# --- Design parameters (not calibration; calibration lives in stats.json) ----

#: Statuses whose parts have left the storeroom but are not yet logged.
OPEN_STATUSES = ("OPEN", "IN_PROGRESS")

#: Minimum token length for the asset_type -> part_description match. Four
#: excludes noise like "OF"/"AND" while keeping PUMP, MILL, CRUSHER, TRUCK.
_MATCH_MIN_TOKEN = 4

#: Bisection bracket for ORDER_COVER (order quantity in lead-time-demand units).
_COVER_BRACKET = (2.0, 12.0)
_COVER_ITERATIONS = 25


# ---------------------------------------------------------------------------
# Deterministic seeding
# ---------------------------------------------------------------------------


def _stable_hash(key: str) -> int:
    """Process-stable 32-bit hash.

    Python's built-in hash() is salted per interpreter by PYTHONHASHSEED, so it
    must never appear in a seed derivation (this exact bug shipped in Task 2).
    blake2b is keyed only by its input.
    """
    return int.from_bytes(blake2b(key.encode(), digest_size=4).digest(), "big")


def _rng(*parts: str) -> np.random.Generator:
    return np.random.default_rng((SEED + _stable_hash("|".join(parts))) & 0xFFFFFFFF)


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------


def _table(key: str) -> str:
    name = _SOURCE_TABLES[key]
    if not _TABLE_IDENTIFIER_RE.match(name):
        raise ValueError(f"refusing to interpolate table identifier {name!r}")
    return f"`{PROJECT_ID}.{DATASET}.{name}`"


@lru_cache(maxsize=1)
def _client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID)


def _parquet(name: str) -> pd.DataFrame:
    return pd.read_parquet(os.path.join(_GENERATED_DIR, name))


@lru_cache(maxsize=1)
def load_original_inventory() -> pd.DataFrame:
    """The frozen pre-regeneration catalogue (103 rows)."""
    return _client().query(
        f"SELECT * FROM {_table('inventory_levels')} ORDER BY part_number"
    ).to_dataframe()


@lru_cache(maxsize=1)
def live_inventory() -> pd.DataFrame:
    """The live table, used only to detect whether Task 8 has loaded yet."""
    return _client().query(
        f"SELECT * FROM {_table('inventory_levels_live')} ORDER BY part_number"
    ).to_dataframe()


@lru_cache(maxsize=1)
def load_assets() -> pd.DataFrame:
    return _client().query(
        "SELECT asset_id, asset_type, criticality_rating "
        f"FROM {_table('assets')} ORDER BY asset_id"
    ).to_dataframe()


@lru_cache(maxsize=1)
def load_parts_edge() -> pd.DataFrame:
    return _client().query(
        f"SELECT edge_id, work_order_id, part_number FROM {_table('work_order_parts_edge')} "
        "ORDER BY edge_id"
    ).to_dataframe()


@lru_cache(maxsize=1)
def load_work_orders() -> pd.DataFrame:
    return _parquet("erp_work_orders.parquet").sort_values("work_order_id").reset_index(
        drop=True
    )


@lru_cache(maxsize=1)
def load_maintenance_logs() -> pd.DataFrame:
    return _parquet("maintenance_logs.parquet").sort_values("log_entry_id").reset_index(
        drop=True
    )


@lru_cache(maxsize=1)
def load_telemetry() -> pd.DataFrame:
    return _parquet("telemetry_stream.parquet")


# ---------------------------------------------------------------------------
# Consumption history
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def consumption_events() -> pd.DataFrame:
    """One row per part issued against a completed work order, with its date.

    `parts_replaced` is a REPEATED column; logs with no parts explode to a null
    row, which is dropped.
    """
    logs = load_maintenance_logs()
    wo = load_work_orders()[["work_order_id", "created_at", "asset_id"]]
    events = (
        logs.explode("parts_replaced")
        .rename(columns={"parts_replaced": "part_number"})[
            ["work_order_id", "part_number"]
        ]
        .dropna(subset=["part_number"])
        .merge(wo, on="work_order_id")
        .sort_values(["work_order_id", "part_number"])
        .reset_index(drop=True)
    )
    return events


def critical_path_parts(asset_id: str) -> List[str]:
    """Parts reachable from `asset_id` through work_order_parts_edge.

    This is the same relation the S08 traversal walks, computed here in SQL-free
    form so the traversal has something independent to confirm.
    """
    edge = load_parts_edge()
    wo = load_work_orders()
    on_asset = set(wo.loc[wo.asset_id == asset_id, "work_order_id"])
    return sorted(set(edge.loc[edge.work_order_id.isin(on_asset), "part_number"]))


# ---------------------------------------------------------------------------
# Degradation ramp
# ---------------------------------------------------------------------------


def detect_ramp_start(telemetry: pd.DataFrame) -> pd.Timestamp:
    """Recover the onset of the degradation ramp from the telemetry series.

    Least-squares fit of a "flat then linear" model,
        y(t) = a                for t < k
        y(t) = a + b * (t - k)  for t >= k
    over every candidate breakpoint k in the second half of the series; the k
    with the lowest residual sum of squares wins. The date is never hardcoded:
    a re-run of Task 2 with a different RAMP_DAYS moves this automatically.

    The fitted onset lands a little after the generator's true ramp start
    because Task 2 normalises the wear envelope to 1.0 at t=0, so the ramp's
    first day is a no-op multiplication and carries no signal.
    """
    series = telemetry[
        (telemetry.asset_id == DEGRADING_ASSET)
        & (telemetry.metric_name == DEGRADING_METRIC)
    ].sort_values("timestamp")
    y = series.metric_value.to_numpy()
    ts = series.timestamp.to_numpy()
    n = len(y)
    t = np.arange(n, dtype=float)
    best_sse, best_k = np.inf, n // 2
    for k in range(n // 4, n - 8):
        design = np.column_stack([np.ones(n), np.maximum(t - k, 0.0)])
        coef, *_ = np.linalg.lstsq(design, y, rcond=None)
        sse = float(((y - design @ coef) ** 2).sum())
        if sse < best_sse:
            best_sse, best_k = sse, k
    return pd.Timestamp(ts[best_k])


def _severity_by_asset(
    telemetry: pd.DataFrame, ramp_start: pd.Timestamp, grid: pd.DatetimeIndex
) -> Dict[str, np.ndarray]:
    """Per-asset daily degradation severity, floored at 1.0.

    For each metric of each asset: daily mean divided by that metric's own mean
    over the pre-ramp period. Maximised across the asset's metrics, so an asset
    whose metrics are all stationary sits at ~1.0 and an asset with a runaway
    metric follows it.
    """
    out: Dict[str, np.ndarray] = {}
    for asset in sorted(telemetry.asset_id.unique()):
        sev = np.ones(len(grid))
        asset_rows = telemetry[telemetry.asset_id == asset]
        for _metric, group in asset_rows.groupby("metric_name", sort=True):
            group = group.sort_values("timestamp")
            baseline = group.loc[group.timestamp < ramp_start, "metric_value"].mean()
            if not np.isfinite(baseline) or baseline == 0:
                continue
            daily = (
                group.set_index("timestamp")
                .metric_value.resample("1D")
                .mean()
                .reindex(grid)
                .ffill()
                .bfill()
            )
            sev = np.maximum(sev, daily.to_numpy() / baseline)
        out[asset] = np.maximum(sev, 1.0)
    return out


def _matched_parts(descriptions: Dict[str, str]) -> Dict[str, List[str]]:
    """Catalogue parts whose description names an asset's type.

    e.g. asset_type PUMP -> "High-load Centrifugal Slurry Pump Bearing Unit".
    Assets whose type has no match (MILL-01's GRINDING_MILL, CONVEYOR-02's
    misspelt CONCONVEYOR, TRUCK-08's HAUL_TRUCK) get an empty list and fall back
    to their empirical part mix.
    """
    out: Dict[str, List[str]] = {}
    for row in load_assets().itertuples():
        tokens = [
            tok.lower()
            for tok in re.split(r"[^A-Za-z]+", row.asset_type)
            if len(tok) >= _MATCH_MIN_TOKEN
        ]
        out[row.asset_id] = sorted(
            part
            for part, desc in descriptions.items()
            if any(tok in desc.lower() for tok in tokens)
        )
    return out


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------


def _median_discrete_price(original: pd.DataFrame) -> float:
    """Median unit price of the priced maintenance-consumed SKUs.

    The two SKUs being added are priced at this value, matching the fallback
    Task 4 already applies so that repair_cost and the catalogue agree.
    """
    consumed = set(consumption_events().part_number)
    priced = original[original.part_number.isin(consumed)]
    return round(float(np.median(priced.unit_price_usd)), 2)


def build_catalogue(days: int) -> pd.DataFrame:
    """The 103 original rows plus the two SKUs Task 4 found missing.

    The added rows get a lead time equal to the median of the priced
    maintenance-consumed SKUs, and a reorder point sized by the textbook
    identity ROP = demand during lead time using their observed issue rate.
    """
    original = load_original_inventory()
    consumed = set(consumption_events().part_number)
    priced_consumed = original[original.part_number.isin(consumed)]
    median_lead_time = int(np.median(priced_consumed.lead_time_days))
    price = _median_discrete_price(original)

    events = consumption_events()
    added = []
    for sku in MISSING_SKUS:
        rate = float((events.part_number == sku).sum()) / days
        added.append(
            {
                "lead_time_days": median_lead_time,
                "part_description": MISSING_SKU_DESCRIPTIONS[sku],
                "reorder_point_limit": max(1, int(np.ceil(rate * median_lead_time))),
                "stock_level": 0,  # replaced by the ledger's closing position
                "unit_price_usd": price,
                "part_number": sku,
            }
        )
    return (
        pd.concat([original, pd.DataFrame(added)], ignore_index=True)
        .sort_values("part_number")
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


@dataclass
class Ledger:
    """Closing snapshot plus the per-part audit trail the tests assert on."""

    catalogue: pd.DataFrame
    rows: Dict[str, dict]
    severity: Dict[str, np.ndarray]
    matched_parts: Dict[str, List[str]]
    ramp_start: pd.Timestamp
    ramp_start_day: int
    days: int
    order_cover: float
    grid: pd.DatetimeIndex = field(repr=False, default=None)


def _run_policy(demand: np.ndarray, rop: int, lead_time: int, order_up_to: int,
                opening: int) -> dict:
    """Continuous-review order-up-to ledger over `len(demand)` days.

    Order of operations each day: receive, issue, then review. On hand is never
    negative — demand that cannot be met is recorded as unmet, not backordered
    into the stock column.
    """
    n = len(demand)
    pipeline = np.zeros(n + lead_time + 2, dtype=int)
    on_hand = int(opening)
    on_order = 0
    received = 0
    issued = 0
    unmet = 0
    crossing_day: Optional[int] = None
    below_days = 0

    for t in range(n):
        arrival = int(pipeline[t])
        on_hand += arrival
        on_order -= arrival
        received += arrival

        take = min(on_hand, int(demand[t]))
        unmet += int(demand[t]) - take
        on_hand -= take
        issued += take

        if on_hand < rop:
            below_days += 1
            if crossing_day is None:
                crossing_day = t
        else:
            crossing_day = None

        position = on_hand + on_order
        if position < rop:
            qty = max(1, order_up_to - position)
            pipeline[t + lead_time] += qty
            on_order += qty

    return {
        "stock_level": on_hand,
        "opening": int(opening),
        "received": received,
        "issued": issued,
        "unmet": unmet,
        "on_order": on_order,
        "crossing_day": crossing_day,
        "below_days": below_days,
        "order_up_to": order_up_to,
    }


def _solve_opening_balance(demand, rop, lead_time, order_up_to, recorded, ramp_day):
    """A4 injection, confined to the one unobservable quantity.

    The original table is a snapshot of "now"; nothing records the opening
    balance on day 0. For a critical-path part, choose the opening balance
    closest to the recorded stock level for which the ledger ends below reorder
    point, with the crossing inside the ramp window and the replenishment still
    in transit at the snapshot. Returns None if no such balance exists, in which
    case the caller keeps the recorded value and the part is simply not short.
    """
    candidates = []
    for opening in range(0, order_up_to + 1):
        row = _run_policy(demand, rop, lead_time, order_up_to, opening)
        if (
            row["stock_level"] < rop
            and row["on_order"] > 0
            and row["crossing_day"] is not None
            and row["crossing_day"] >= ramp_day
        ):
            candidates.append((abs(opening - recorded), opening))
    if not candidates:
        return None
    return min(candidates)[1]


def _demand_streams(catalogue, days, ramp_day, severity, matched, grid):
    """Daily demand per part, and the set of parts with a real issue history."""
    events = consumption_events()
    work_orders = load_work_orders()

    def day_index(ts) -> int:
        return int((pd.Timestamp(ts).normalize() - grid[0]).days)

    # Empirical part mix and parts-per-work-order rate, per asset.
    mix = {}
    for asset, group in events.groupby("asset_id", sort=True):
        counts = group.part_number.value_counts().sort_index()
        mix[asset] = (counts.index.to_numpy(), (counts / counts.sum()).to_numpy())
    logged = set(load_maintenance_logs().work_order_id)
    per_wo = {}
    for asset in sorted(mix):
        n_logs = int(
            work_orders[
                (work_orders.asset_id == asset)
                & work_orders.work_order_id.isin(logged)
            ].shape[0]
        )
        per_wo[asset] = float((events.asset_id == asset).sum()) / n_logs

    demand = {part: np.zeros(days, dtype=int) for part in catalogue.part_number}

    # 1. issues recorded against completed work orders
    for row in events.itertuples():
        demand[row.part_number][day_index(row.created_at)] += 1

    # 2. kitting against open work orders, scaled by degradation severity
    open_wos = work_orders[work_orders.status.isin(OPEN_STATUSES)]
    for row in open_wos.itertuples():
        if row.asset_id not in mix:
            continue
        day = day_index(row.created_at)
        sev = float(severity[row.asset_id][day])
        rng = _rng("kit", row.work_order_id)
        pool, probs = mix[row.asset_id]

        def draw(expected: float, choices, weights):
            k = int(np.floor(expected))
            if rng.random() < expected - np.floor(expected):
                k += 1
            return list(rng.choice(choices, size=k, p=weights)) if k else []

        base = per_wo[row.asset_id]
        picks = draw(base, pool, probs)

        excess_pool = matched.get(row.asset_id) or list(pool)
        excess_pool = np.array(excess_pool)
        picks += draw(
            base * (sev - 1.0), excess_pool, np.full(len(excess_pool), 1.0 / len(excess_pool))
        )
        for part in picks:
            demand[part][day] += 1

    with_history = {p for p, d in demand.items() if d.sum() > 0}

    # 3. background demand for parts with no history at all
    for row in catalogue.itertuples():
        if row.part_number in with_history:
            continue
        rate = int(row.reorder_point_limit) / int(row.lead_time_days)
        demand[row.part_number] = _rng("demand", row.part_number).poisson(rate, days)

    return demand, with_history


def _simulate(catalogue, demand, with_history, days, ramp_day, order_cover,
              injected_parts) -> Dict[str, dict]:
    rows: Dict[str, dict] = {}
    for row in catalogue.itertuples():
        part = row.part_number
        lead_time = int(row.lead_time_days)
        stream = demand[part]
        rate_pre = float(stream[:ramp_day].sum()) / ramp_day
        rate_ramp = float(stream[ramp_day:].sum()) / (days - ramp_day)

        # ROP = demand during lead time. For catalogue parts with no history the
        # recorded ROP is the only evidence of their demand and is kept as-is
        # (the identity was used in the other direction to infer their rate);
        # for parts with an observed issue history the identity is applied
        # forwards, which re-bases the five maintenance SKUs whose recorded
        # reorder points sit well under a single lead time of real demand.
        if part in with_history:
            rop = max(1, int(np.ceil(rate_pre * lead_time)))
        else:
            rop = int(row.reorder_point_limit)

        order_qty = max(1, int(round(order_cover * rate_pre * lead_time)))
        order_up_to = rop + order_qty
        recorded = int(row.stock_level) if part not in MISSING_SKUS else order_up_to

        opening = recorded
        if part in injected_parts:
            solved = _solve_opening_balance(
                stream, rop, lead_time, order_up_to, recorded, ramp_day
            )
            if solved is not None:
                opening = solved

        result = _run_policy(stream, rop, lead_time, order_up_to, opening)
        result.update(
            {
                "part_number": part,
                "reorder_point_limit": rop,
                "lead_time_days": lead_time,
                "lam_pre": rate_pre,
                "lam_ramp": rate_ramp,
                "recorded_stock": recorded,
                "injected": part in injected_parts,
            }
        )
        rows[part] = result
    return rows


@lru_cache(maxsize=1)
def build_ledger() -> Ledger:
    """Run the full ledger, solving ORDER_COVER against the stats.json mean."""
    work_orders = load_work_orders()
    start = pd.Timestamp(work_orders.created_at.min()).normalize()
    end = pd.Timestamp(work_orders.created_at.max()).normalize()
    grid = pd.date_range(start, end, freq="D", tz="UTC")
    days = len(grid)

    telemetry = load_telemetry()
    ramp_start = detect_ramp_start(telemetry)
    ramp_day = int((ramp_start.normalize() - start).days)

    catalogue = build_catalogue(days)
    descriptions = dict(zip(catalogue.part_number, catalogue.part_description.fillna("")))
    matched = _matched_parts(descriptions)
    severity = _severity_by_asset(telemetry, ramp_start, grid)

    demand, with_history = _demand_streams(
        catalogue, days, ramp_day, severity, matched, grid
    )
    injected = tuple(critical_path_parts(DEGRADING_ASSET))

    target = STATS["inventory"][0]["stock_mean"]

    def mean_stock(cover: float) -> float:
        rows = _simulate(
            catalogue, demand, with_history, days, ramp_day, cover, injected
        )
        return float(np.mean([r["stock_level"] for r in rows.values()]))

    lo, hi = _COVER_BRACKET
    for _ in range(_COVER_ITERATIONS):
        mid = (lo + hi) / 2.0
        if mean_stock(mid) < target:
            lo = mid
        else:
            hi = mid
    order_cover = (lo + hi) / 2.0

    rows = _simulate(
        catalogue, demand, with_history, days, ramp_day, order_cover, injected
    )
    return Ledger(
        catalogue=catalogue,
        rows=rows,
        severity=severity,
        matched_parts=matched,
        ramp_start=ramp_start,
        ramp_start_day=ramp_day,
        days=days,
        order_cover=order_cover,
        grid=grid,
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def generate_inventory() -> pd.DataFrame:
    """The regenerated inventory_levels snapshot (105 rows, schema unchanged)."""
    ledger = build_ledger()
    out = ledger.catalogue.copy()
    out["stock_level"] = [
        ledger.rows[p]["stock_level"] for p in out.part_number
    ]
    out["reorder_point_limit"] = [
        ledger.rows[p]["reorder_point_limit"] for p in out.part_number
    ]
    out = out[
        [
            "lead_time_days",
            "part_description",
            "reorder_point_limit",
            "stock_level",
            "unit_price_usd",
            "part_number",
        ]
    ]
    out["lead_time_days"] = out.lead_time_days.astype("int64")
    out["reorder_point_limit"] = out.reorder_point_limit.astype("int64")
    out["stock_level"] = out.stock_level.astype("int64")
    out["unit_price_usd"] = out.unit_price_usd.astype("float64")
    return out.sort_values("part_number").reset_index(drop=True)


def write_parquet(path: Optional[str] = None) -> pd.DataFrame:
    inv = generate_inventory()
    if path is None:
        path = os.path.join(_GENERATED_DIR, "inventory_levels.parquet")
    inv.to_parquet(path, index=False)
    return inv


# ---------------------------------------------------------------------------
# S08 traversal
# ---------------------------------------------------------------------------

#: The design doc (§3.2) writes this traversal with edge labels
#: `work_order_parts_edge` / `erp_work_orders` and the direction
#: `(wo)-[:erp_work_orders]->(a)`. Neither is right against the deployed graph:
#: the DDL declares LABEL REPLACED_PART on work_order_parts_edge and LABEL
#: HAS_WORK_ORDER on erp_work_orders, and the latter runs Asset -> WorkOrder
#: (source asset_id, destination work_order_id). Running the doc's version
#: returns "Label work_order_parts_edge not found in property graph". The shape
#: (SparePart <- WorkOrder <- Asset) and the projected columns are unchanged.
_S08_SQL = """
SELECT * FROM GRAPH_TABLE(
  {dataset}.{graph}
  MATCH (p:SparePart WHERE p.part_number IN UNNEST(@below_rop_parts))
        <-[:REPLACED_PART]- (wo:WorkOrder) <-[:HAS_WORK_ORDER]- (a:Asset)
  COLUMNS (p.part_number AS part_number, wo.work_order_id AS work_order_id,
           wo.priority AS priority, wo.repair_cost AS repair_cost,
           a.asset_id AS asset_id, a.criticality_rating AS criticality_rating)
)
WHERE @asset_id IS NULL OR asset_id = @asset_id
ORDER BY part_number, work_order_id
"""

#: Same traversal, but with the below-ROP predicate evaluated *inside* the graph
#: against the SparePart node's own columns. Only meaningful once Task 8 has
#: loaded the regenerated table into live inventory_levels.
_S08_IN_GRAPH_SQL = """
SELECT * FROM GRAPH_TABLE(
  {dataset}.{graph}
  MATCH (p:SparePart WHERE p.stock_level < p.reorder_point_limit)
        <-[:REPLACED_PART]- (wo:WorkOrder) <-[:HAS_WORK_ORDER]- (a:Asset)
  COLUMNS (p.part_number AS part_number, p.stock_level AS stock_level,
           p.reorder_point_limit AS reorder_point_limit,
           wo.work_order_id AS work_order_id, wo.priority AS priority,
           a.asset_id AS asset_id, a.criticality_rating AS criticality_rating)
)
WHERE asset_id = @asset_id
ORDER BY part_number, work_order_id
"""


def _graph_sql(template: str) -> str:
    # BigQuery cannot bind a dataset or graph name as a parameter. Both come
    # from config/constants in this module, never from a caller, and are
    # re-validated here for the same reason `_table()` re-validates.
    for identifier in (DATASET, GRAPH_NAME):
        if not _TABLE_IDENTIFIER_RE.match(identifier):
            raise ValueError(f"refusing to interpolate identifier {identifier!r}")
    return template.format(dataset=DATASET, graph=GRAPH_NAME)


def s08_stockout_exposure(
    below_rop_parts, asset_id: Optional[str] = DEGRADING_ASSET
) -> pd.DataFrame:
    """S08: part -> work order -> asset, over MiningSupplyChainGraph.

    Pass `asset_id=None` to return every asset the parts reach.
    """
    config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter(
                "below_rop_parts", "STRING", list(below_rop_parts)
            ),
            bigquery.ScalarQueryParameter("asset_id", "STRING", asset_id),
        ]
    )
    return _client().query(_graph_sql(_S08_SQL), job_config=config).to_dataframe()


def s08_stockout_exposure_in_graph(asset_id: str = DEGRADING_ASSET) -> pd.DataFrame:
    config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("asset_id", "STRING", asset_id)]
    )
    return (
        _client().query(_graph_sql(_S08_IN_GRAPH_SQL), job_config=config).to_dataframe()
    )


if __name__ == "__main__":  # pragma: no cover
    frame = write_parquet()
    below = frame[frame.stock_level < frame.reorder_point_limit]
    ledger = build_ledger()
    print(f"rows={len(frame)}  below_rop={len(below)}  "
          f"mean_stock={frame.stock_level.mean():.2f}  "
          f"mean_rop={frame.reorder_point_limit.mean():.2f}  "
          f"order_cover={ledger.order_cover:.4f}  ramp_start={ledger.ramp_start}")
    print(below.sort_values("part_number").to_string(index=False))
