"""Work-order economics generator — Task 4.

Rebuilds ``erp_work_orders.repair_cost`` so that cost is driven by the work
actually done:

    repair_cost = LABOUR_RATE * crew_size * actual_duration_hours
                + parts_cost(work_order_id)
                + fixed_mobilisation

Source of truth
---------------
All calibration inputs are read from the **frozen backup tables** created by
Task 1 (``*_original_20260810``), never from the live tables.  Task 8 overwrites
the live ``erp_work_orders`` / ``maintenance_logs`` with this module's output;
reading the live tables would make a later re-run consume its own output and
silently stop being reproducible.  ``work_order_parts_edge`` has no backup
because no task rewrites it.

No calibration figure is written as a literal in this file.  Duration bounds and
the total-spend target come from ``data/profile/stats.json`` via ``config.STATS``;
the per-priority duration mean/SD are fitted at runtime from the COMPLETED join.

Design decisions
----------------
* ``LABOUR_RATE = 150`` $/h and ``MOB_BASE = 150`` $ are *design* parameters
  (chosen by tuning, see notes at the bottom), not observed statistics.
  ``fixed_mobilisation = MOB_BASE * crew_size``, so CRITICAL mobilisation = $900,
  HIGH = $600, MEDIUM = $450, LOW = $300.
* ``CREW_SIZE``: CRITICAL 6, HIGH 4, MEDIUM 3, LOW 2 — from the brief.
* **Scatter approach** — the cost formula is fully deterministic per WO given
  its duration, crew and parts list.  There is deliberately **no additive noise
  term**: every cost is recomputable to the cent from stored components.
  Natural scatter comes from three sources:
    1. Duration varies within each priority group (SD ~ 5 h).
    2. Crew size varies *across* priorities, so corr(cost, dur) is dampened
       below 1.0 (a high-priority short job can cost more than a low-priority
       long job).
    3. Parts cost varies (discrete unit prices, 0-2 parts per WO).
  Measured on the 152-row join this gives corr(repair_cost, duration) ~ 0.75;
  the test suite enforces the [0.70, 0.90] band.

* **348 non-completed WOs** get a synthetic duration from a truncated normal
  fitted at runtime to the 152 COMPLETED durations of the same priority, drawn
  by stratified quantile assignment so the generated group moments actually
  reproduce the fitted ones (see :func:`synthetic_durations`).  The same cost
  formula is applied, so the two populations are indistinguishable in shape.

* ``compute_parts_cost(work_order_id)`` is exported so tests can verify
  reproducibility.  Parts are priced from ``work_order_parts_edge`` joined to
  ``inventory_levels``, falling back to the log's ``parts_replaced`` array when
  a work order has no edge row, and falling back to the median price of the
  maintenance-consumed catalogue for SKUs missing a catalogue price.  See
  ``_load_parts_cache`` for why both fallbacks are needed.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import sys
from pathlib import Path
from statistics import NormalDist
from typing import Optional

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import BACKUP_SUFFIX, DATASET, PROJECT_ID, SEED, STATS  # noqa: E402

# ---------------------------------------------------------------------------
# Design parameters (not calibration — see module docstring)
# ---------------------------------------------------------------------------

#: Labour rate in $/h applied to all work orders.
LABOUR_RATE: float = 150.0

#: Mobilisation base.  fixed_mobilisation = MOB_BASE * crew_size.
MOB_BASE: float = 150.0

#: Deterministic crew size by priority.
CREW_SIZE: dict[str, int] = {
    "CRITICAL": 6,
    "HIGH": 4,
    "MEDIUM": 3,
    "LOW": 2,
}

# ---------------------------------------------------------------------------
# Calibration loaded from data/profile/stats.json (never restated as literals)
# ---------------------------------------------------------------------------

_MAINTENANCE_STATS: dict = STATS["maintenance"][0]

#: Duration bounds observed on the original maintenance_logs.
DUR_MIN: float = float(_MAINTENANCE_STATS["dur_min"])
DUR_MAX: float = float(_MAINTENANCE_STATS["dur_max"])

#: Pooled duration moments — the realism target the generated logs must keep.
DUR_MEAN: float = float(_MAINTENANCE_STATS["dur_mean"])
DUR_SD: float = float(_MAINTENANCE_STATS["dur_sd"])

#: Total maintenance spend across all 500 work orders in the original data.
TARGET_TOTAL_SPEND: float = float(STATS["workorders_total"][0]["total_spend"])

# ---------------------------------------------------------------------------
# BigQuery source tables
#
# BigQuery cannot bind a table identifier to a query parameter (@params bind
# *values* only), so identifiers must be interpolated into the SQL text.  To
# make that obviously safe, every table this module reads is declared in the
# allow-list below and is re-validated against a strict identifier pattern
# before interpolation.  No caller-supplied string ever reaches a query.
# ---------------------------------------------------------------------------

_SOURCE_TABLES: dict[str, str] = {
    # Frozen Task-1 backups — Task 8 overwrites the live copies of these.
    "work_orders": "erp_work_orders" + BACKUP_SUFFIX,
    "maintenance_logs": "maintenance_logs" + BACKUP_SUFFIX,
    "inventory": "inventory_levels" + BACKUP_SUFFIX,
    # Not in REWRITE_TABLES, so the live table is already immutable.
    "parts_edge": "work_order_parts_edge",
}

_TABLE_IDENTIFIER_RE = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]{0,1023}\Z")


def _table(key: str) -> str:
    """Return the fully-qualified id of an allow-listed source table."""
    try:
        name = _SOURCE_TABLES[key]
    except KeyError:
        raise KeyError(
            f"{key!r} is not an allow-listed source table "
            f"(allowed: {sorted(_SOURCE_TABLES)})"
        ) from None
    if not _TABLE_IDENTIFIER_RE.match(name):
        raise ValueError(f"unsafe table identifier: {name!r}")
    return f"{PROJECT_ID}.{DATASET}.{name}"


def _client():
    """BigQuery client (deferred import so the module is importable offline)."""
    from google.cloud import bigquery

    return bigquery.Client(project=PROJECT_ID)


# Output paths
_GENERATED_DIR = Path(__file__).parent.parent / "generated"

# ---------------------------------------------------------------------------
# Source-table cache (each table is fetched at most once per process)
# ---------------------------------------------------------------------------

_tables_cache: Optional[tuple[pd.DataFrame, pd.DataFrame]] = None
_parts_cache: Optional[dict[str, float]] = None  # work_order_id -> parts_cost


def _fetch_source_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch the frozen work-order and maintenance-log backups.

    Returns ``(work_orders, maintenance_logs)``.  ``repair_cost`` is not
    fetched because it is recomputed here; ``actual_duration_hours`` is fetched
    because it is the driver of the new cost.
    """
    global _tables_cache
    if _tables_cache is not None:
        return _tables_cache

    client = _client()

    wo_query = f"""
        SELECT
            work_order_id,
            priority,
            status,
            description,
            asset_id,
            created_at
        FROM `{_table('work_orders')}`
        ORDER BY work_order_id
    """

    ml_query = f"""
        SELECT
            log_entry_id,
            work_order_id,
            asset_id,
            technician_notes,
            parts_replaced,
            actual_duration_hours
        FROM `{_table('maintenance_logs')}`
        ORDER BY work_order_id
    """

    wo = client.query(wo_query).to_dataframe()
    ml = client.query(ml_query).to_dataframe()
    _tables_cache = (wo, ml)
    return _tables_cache


def _as_parts_list(value) -> list[str]:
    """Normalise a REPEATED STRING cell to a plain list of strings."""
    if value is None:
        return []
    return [str(p) for p in list(value)]


def _load_parts_cache() -> dict[str, float]:
    """Build ``work_order_id -> parts cost`` from the priced parts consumed.

    Two fallbacks are applied so that ``repair_cost`` cannot disagree with the
    ``parts_replaced`` array that a cost-forecasting agent would join on:

    1. **Missing edge row.**  If a work order has no row in
       ``work_order_parts_edge`` its parts are taken from the log's
       ``parts_replaced`` array instead.  (On the current data the edge table
       reproduces ``parts_replaced`` exactly, so this fallback fires zero times;
       it exists so the two sources cannot drift apart silently.)
    2. **Missing catalogue price.**  Two maintenance SKUs
       (``SKU-AIR-FILTER-08``, ``SKU-VALVE-SEAL-22``) appear on work orders but
       have no row in ``inventory_levels``.  An inner join therefore priced them
       at $0, which left 26 logs listing two replaced parts against $0 of parts
       cost.  Such SKUs are valued at the *median unit price of the
       maintenance-consumed SKUs that are priced* — computed at runtime, never
       hardcoded — so every log with a non-empty ``parts_replaced`` carries a
       non-zero parts cost.
    """
    global _parts_cache
    if _parts_cache is not None:
        return _parts_cache

    client = _client()

    catalogue = {
        row.part_number: float(row.unit_price_usd)
        for row in client.query(
            f"SELECT part_number, unit_price_usd FROM `{_table('inventory')}`"
        ).result()
    }

    edge_rows = [
        (row.work_order_id, row.part_number)
        for row in client.query(
            f"SELECT work_order_id, part_number FROM `{_table('parts_edge')}`"
        ).result()
    ]

    _, ml = _fetch_source_tables()
    logged_parts: dict[str, list[str]] = {
        wo_id: _as_parts_list(parts)
        for wo_id, parts in zip(ml["work_order_id"], ml["parts_replaced"])
    }

    # Reference class for the price fallback: SKUs that maintenance actually
    # consumes and for which the catalogue does have a price.
    consumed = {p for _, p in edge_rows}
    consumed.update(p for parts in logged_parts.values() for p in parts)
    priced_consumed = sorted(catalogue[p] for p in consumed if p in catalogue)
    if not priced_consumed:
        raise RuntimeError("no maintenance-consumed part has a catalogue price")
    fallback_price = float(np.median(priced_consumed))

    def unit_price(part_number: str) -> float:
        return catalogue.get(part_number, fallback_price)

    costs: dict[str, float] = {}
    for wo_id, part_number in edge_rows:
        costs[wo_id] = costs.get(wo_id, 0.0) + unit_price(part_number)

    # Fallback 1: work orders whose parts are only recorded in parts_replaced.
    for wo_id, parts in logged_parts.items():
        if parts and wo_id not in costs:
            costs[wo_id] = sum(unit_price(p) for p in parts)

    _parts_cache = {k: round(v, 2) for k, v in costs.items()}
    return _parts_cache


def compute_parts_cost(work_order_id: str) -> float:
    """Return total parts cost for *work_order_id*.

    Returns 0.0 for work orders with no parts at all.  Deterministic: the parts
    lists and the price catalogue are both read from frozen tables.
    """
    return _load_parts_cache().get(work_order_id, 0.0)


# ---------------------------------------------------------------------------
# Duration distribution — fitted at runtime, never hardcoded
# ---------------------------------------------------------------------------

_dur_targets_cache: Optional[dict[str, tuple[float, float]]] = None
_dur_params_cache: Optional[dict[str, tuple[float, float]]] = None


def fit_duration_params() -> dict[str, tuple[float, float]]:
    """Observed ``priority -> (mean, sd)`` of the COMPLETED durations.

    The 152 logged durations are the only observed durations in the source
    data, so they are the calibration *target* for the 348 synthetic ones.
    """
    global _dur_targets_cache
    if _dur_targets_cache is not None:
        return _dur_targets_cache

    wo, ml = _fetch_source_tables()
    joined = wo[["work_order_id", "priority"]].merge(
        ml[["work_order_id", "actual_duration_hours"]], on="work_order_id"
    )
    grouped = joined.groupby("priority")["actual_duration_hours"]
    _dur_targets_cache = {
        priority: (float(grouped.mean()[priority]), float(grouped.std(ddof=1)[priority]))
        for priority in CREW_SIZE
    }
    return _dur_targets_cache


def _std_normal_pdf(x: float) -> float:
    if abs(x) >= 38.0:  # exp(-722) underflows to 0 anyway
        return 0.0
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _std_normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def truncated_normal_moments(mu: float, sigma: float) -> tuple[float, float]:
    """Analytic (mean, sd) of N(mu, sigma) truncated to [DUR_MIN, DUR_MAX]."""
    alpha = (DUR_MIN - mu) / sigma
    beta = (DUR_MAX - mu) / sigma
    z = _std_normal_cdf(beta) - _std_normal_cdf(alpha)
    if z < 1e-9:  # all mass outside the interval — degenerate at the near edge
        return (DUR_MIN if alpha > 0 else DUR_MAX), 0.0
    pa, pb = _std_normal_pdf(alpha), _std_normal_pdf(beta)
    mean = mu + sigma * (pa - pb) / z
    var = sigma * sigma * (1.0 + (alpha * pa - beta * pb) / z - ((pa - pb) / z) ** 2)
    return mean, math.sqrt(max(var, 0.0))


def _fit_truncated_normal(target_mean: float, target_sd: float) -> tuple[float, float]:
    """Solve for (mu, sigma) whose *truncated* moments match the targets.

    The previous implementation plugged the raw sample mean/SD straight into the
    truncated sampler.  That is a mis-specified fit: truncating to
    [DUR_MIN, DUR_MAX] discards both tails, so the realised durations came out
    ~20% narrower and up to 1 h away from the calibration target.  Here the
    parameters are chosen so that the *post-truncation* moments match instead.

    Deterministic coarse-to-fine grid search over a numerically safe box (a
    Newton solve is not used because for high-variance targets the optimum sits
    where sigma >> the interval width and the Jacobian is ill-conditioned).
    Some targets are outside what any truncated normal on a bounded interval can
    reach — the SD of a truncated normal on [1, 19] cannot exceed ~5.2 — so this
    returns the closest achievable fit rather than an exact one.
    """
    lo_mu, hi_mu, lo_sigma, hi_sigma = -80.0, 100.0, 0.25, 30.0
    best: tuple[float, float, float] = (float("inf"), target_mean, target_sd)
    for _ in range(4):
        best = (float("inf"), best[1], best[2])
        for mu in np.linspace(lo_mu, hi_mu, 121):
            for sigma in np.linspace(lo_sigma, hi_sigma, 121):
                mean, sd = truncated_normal_moments(float(mu), float(sigma))
                err = ((mean - target_mean) / target_sd) ** 2 + (
                    (sd - target_sd) / target_sd
                ) ** 2
                if err < best[0]:
                    best = (err, float(mu), float(sigma))
        _, mu_hat, sigma_hat = best
        d_mu = (hi_mu - lo_mu) / 120.0 * 3.0
        d_sigma = (hi_sigma - lo_sigma) / 120.0 * 3.0
        lo_mu, hi_mu = mu_hat - d_mu, mu_hat + d_mu
        lo_sigma, hi_sigma = max(0.05, sigma_hat - d_sigma), sigma_hat + d_sigma
    return best[1], best[2]


def duration_sampling_params() -> dict[str, tuple[float, float]]:
    """``priority -> (mu, sigma)`` of the truncated normal used for sampling.

    These are *not* the observed moments (see :func:`fit_duration_params`);
    they are the pre-truncation parameters whose truncated moments reproduce
    the observed ones as closely as the family allows.
    """
    global _dur_params_cache
    if _dur_params_cache is not None:
        return _dur_params_cache
    _dur_params_cache = {
        priority: _fit_truncated_normal(mean, sd)
        for priority, (mean, sd) in fit_duration_params().items()
    }
    return _dur_params_cache


def truncated_normal_quantile(u: float, mu: float, sigma: float) -> float:
    """Inverse CDF of N(mu, sigma) truncated to [DUR_MIN, DUR_MAX].

    *u* is a uniform in (0, 1).  The result is rounded to 1 decimal place to
    match the observed data format and clipped to the bounds, which only binds
    for u at the very edges (the rounding can push 18.96 to 19.0, never past).
    """
    normal = NormalDist()
    p_lo = normal.cdf((DUR_MIN - mu) / sigma)
    p_hi = normal.cdf((DUR_MAX - mu) / sigma)
    p = p_lo + u * (p_hi - p_lo)
    p = min(max(p, 1e-12), 1.0 - 1e-12)
    return float(np.clip(round(mu + sigma * normal.inv_cdf(p), 1), DUR_MIN, DUR_MAX))


def _wo_sub_seed(master_seed: int, work_order_id: str) -> int:
    """Deterministic per-work-order draw index from master seed + WO ID.

    Uses SHA-256 truncated to 64 bits so a work order's position in its
    priority group is independent of row order in the source table.
    """
    h = hashlib.sha256(f"{master_seed}:{work_order_id}".encode()).digest()
    return int.from_bytes(h[:8], "big")


def synthetic_durations(
    work_order_ids_by_priority: dict[str, list[str]],
    seed: int = SEED,
) -> dict[str, float]:
    """Assign a duration to every non-COMPLETED work order.

    **Stratified** rather than independent sampling: within each priority the
    work orders are ordered by their SHA-256 sub-seed and the *i*-th of *n* is
    given the ``(i + 0.5) / n`` quantile of that priority's fitted truncated
    normal.  Independent draws were tried first and rejected: with n = 73-101
    per group the sampling error on the group mean is ~0.6 h, which is enough to
    flip the CRITICAL-vs-HIGH cost ordering (the two priorities are near-tied by
    design, since 6 crew x 8 h and 4 crew x 12 h are the same labour bill).
    Stratification reproduces the fitted per-priority moments to ~0.01 h while
    staying fully deterministic and order-independent.
    """
    params = duration_sampling_params()
    durations: dict[str, float] = {}
    for priority, wo_ids in work_order_ids_by_priority.items():
        mu, sigma = params[priority]
        ordered = sorted(wo_ids, key=lambda w: (_wo_sub_seed(seed, w), w))
        n = len(ordered)
        for i, wo_id in enumerate(ordered):
            durations[wo_id] = truncated_normal_quantile((i + 0.5) / n, mu, sigma)
    return durations


# ---------------------------------------------------------------------------
# Main generation functions
# ---------------------------------------------------------------------------

def generate_work_orders(seed: int = SEED) -> pd.DataFrame:
    """Generate the 500-row ``erp_work_orders`` table with recomputed ``repair_cost``.

    All non-cost columns carry through unchanged from the frozen backup table.
    ``repair_cost`` is computed from the formula for all 500 rows, with no
    additive noise term.

    Parameters
    ----------
    seed:
        Master RNG seed for the synthetic durations of non-COMPLETED work
        orders.  Two calls with the same seed produce identical output.

    Returns
    -------
    pd.DataFrame with columns:
        created_at, repair_cost, description, work_order_id, priority, status, asset_id
    """
    wo, ml = _fetch_source_tables()

    # Mapping work_order_id -> actual_duration_hours for COMPLETED rows
    completed_dur: dict[str, float] = dict(
        zip(ml["work_order_id"], ml["actual_duration_hours"])
    )

    # Synthetic durations for everything else, stratified within priority.
    pending: dict[str, list[str]] = {priority: [] for priority in CREW_SIZE}
    for wo_id, priority in zip(wo["work_order_id"], wo["priority"]):
        if wo_id not in completed_dur:
            pending[priority].append(wo_id)
    synthetic_dur = synthetic_durations(pending, seed=seed)

    repair_costs = []
    for _, row in wo.iterrows():
        wo_id = row["work_order_id"]
        crew = CREW_SIZE[row["priority"]]
        mob = MOB_BASE * crew
        duration = completed_dur.get(wo_id, synthetic_dur.get(wo_id))
        parts = compute_parts_cost(wo_id)
        cost = LABOUR_RATE * crew * duration + parts + mob
        repair_costs.append(round(cost, 2))

    wo = wo.copy()
    wo["repair_cost"] = repair_costs

    # Reorder columns to match the schema
    return wo[["created_at", "repair_cost", "description", "work_order_id",
               "priority", "status", "asset_id"]]


def generate_maintenance_logs() -> pd.DataFrame:
    """Generate the 152-row ``maintenance_logs`` table.

    **Deliberate design decision: ``actual_duration_hours`` is an identity
    passthrough of the original values, not a resampled series.**

    The brief's deliverable is worded as "regenerate maintenance_logs", which
    could be read as requiring newly drawn durations.  It is not done here, on
    purpose.  The original durations already hit the realism target exactly —
    mean 9.944 h, SD 5.226 h, range [1, 19] h, which is precisely what
    ``stats.json`` records and what any resampled series would be calibrated
    to reproduce.  Redrawing them would change no distributional property, would
    destroy the only observed duration signal in the dataset, and would break
    the per-priority fit that the 348 synthetic durations depend on.

    The actual defect this workstream exists to fix is that ``repair_cost`` was
    drawn *independently* of duration (and was inverted against priority).  That
    defect is in the cost column, and it is fixed in
    :func:`generate_work_orders`, which now derives every cost from these
    durations.  Carrying the durations through verbatim is what makes that link
    verifiable against the source data.

    This function therefore takes no seed: its output is a pure function of the
    frozen backup table.

    Returns
    -------
    pd.DataFrame with columns:
        parts_replaced, log_entry_id, actual_duration_hours, asset_id,
        technician_notes, work_order_id
    """
    _, ml = _fetch_source_tables()
    ml = ml.copy()

    # Ensure parts_replaced is a list of strings (not a numpy array)
    ml["parts_replaced"] = ml["parts_replaced"].apply(_as_parts_list)

    return ml[["parts_replaced", "log_entry_id", "actual_duration_hours",
               "asset_id", "technician_notes", "work_order_id"]]


# ---------------------------------------------------------------------------
# Write parquet outputs
# ---------------------------------------------------------------------------

def write_parquet(seed: int = SEED) -> None:
    """Generate both tables and write to data/generated/.

    Called by Task 8's loader or directly:
        python -m maintenance
    """
    _GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating work orders …")
    wo = generate_work_orders(seed=seed)
    out_wo = _GENERATED_DIR / "erp_work_orders.parquet"
    wo.to_parquet(out_wo, index=False)
    print(f"  Written {len(wo)} rows → {out_wo}")

    print("Generating maintenance logs …")
    ml = generate_maintenance_logs()
    out_ml = _GENERATED_DIR / "maintenance_logs.parquet"
    ml.to_parquet(out_ml, index=False)
    print(f"  Written {len(ml)} rows → {out_ml}")

    # Quick verification summary
    joined = wo.merge(ml, on="work_order_id")
    corr = joined["repair_cost"].corr(joined["actual_duration_hours"])
    total = wo["repair_cost"].sum()
    means = wo.groupby("priority")["repair_cost"].mean()
    drift = (total - TARGET_TOTAL_SPEND) / TARGET_TOTAL_SPEND
    print("\nVerification:")
    print(f"  corr(repair_cost, actual_duration_hours) = {corr:.4f}")
    print(f"  total spend = ${total:,.2f} "
          f"(target ${TARGET_TOTAL_SPEND:,.2f}, {drift:+.2%})")
    print(f"  cost means: CRITICAL=${means['CRITICAL']:.0f}, HIGH=${means['HIGH']:.0f}, "
          f"MEDIUM=${means['MEDIUM']:.0f}, LOW=${means['LOW']:.0f}")
    print(f"  duration: mean={ml['actual_duration_hours'].mean():.3f} "
          f"(target {DUR_MEAN}), sd={ml['actual_duration_hours'].std(ddof=1):.3f} "
          f"(target {DUR_SD})")


if __name__ == "__main__":
    write_parquet()


# ---------------------------------------------------------------------------
# Tuning notes (for reference, not executed)
# ---------------------------------------------------------------------------
# LABOUR_RATE and MOB_BASE are the only free parameters.  With both at 150 the
# generated total lands within ~1% of the observed total spend:
#   priority  n    crew  mob   mean dur (observed)  mean labour
#   CRITICAL  101  6     $900  ~8.0 h               ~$7.2k
#   HIGH      128  4     $600  ~12.0 h              ~$7.2k
#   MEDIUM    131  3     $450  ~9.5 h               ~$4.3k
#   LOW       140  2     $300  ~10.0 h              ~$3.0k
# Note the CRITICAL/HIGH near-tie: 6 crew x 8 h and 4 crew x 12 h are the same
# labour bill, so the required CRITICAL > HIGH cost ordering rests on the $300
# mobilisation difference plus parts.  That is why the synthetic durations are
# stratified rather than independently drawn — see synthetic_durations().
# Parts add ~$92k across the 126 work orders that consume parts (up from ~$69k
# before the missing-price fallback was added).  The mean duration figures above
# are indicative only — the actual values are fitted at runtime by
# fit_duration_params().
