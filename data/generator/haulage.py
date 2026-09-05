"""Task F (P7) — haul-cycle rollups for the Mine Controller's Optimiser pack.

`method/p7-mine-controller.yaml` is the specification: the Optimiser arbitrates
which route a truck is dispatched onto and how heavily it is loaded, so its
diagnostics need a *time series* of route performance, not the single static
snapshot `haulage_routes` carries today.

The gap this module closes
---------------------------
`haulage_routes` is ten rows, one per route, each a pre-aggregated
`average_cycle_time_mins` / `congestion_factor` with no timestamp at all — a
control-room fact sheet, not an operating record. `operator_vehicle_assignments`
is five rows for a single shift-date (2026-06-18), one day past the work-order
window, so no operator-linked cycle history exists at any usable scale either
(see p7-mine-controller.yaml's `operator_behaviour_variance` driver, which
stays not_instrumented for exactly this reason). Neither table lets the
Optimiser answer "did the congestion on this route actually cost cycle time,
by band, over a campaign" the way `crusher_states` lets the Metallurgist
answer the same shape of question for the crusher gap.

`haul_cycle_log` is a half-day rollup per route — AM (00:00 UTC) and PM
(12:00 UTC) — over the same 2026-01-01..2026-06-16 window the daily-cadence
tables (`crusher_states`, `metallurgical_recovery`) already use: 10 routes x
167 days x 2 halves = 3,340 rows. Half-day grain, not per-trip, both because a
per-trip log at this fleet's real cycle frequency would run to hundreds of
thousands of rows for a demo table, and because it is exactly what the
leading-indicator driver needs: AM congestion on a route is allowed to carry
into that same route's PM outcome, which is undetectable at daily grain and
overkill at per-trip grain.

The ten routes' own `average_cycle_time_mins`, `congestion_factor` and
`distance_meters` are transcribed below from the live `haulage_routes` table
(read 2026-08-18) rather than queried at generation time, the same way
`warranty.py`'s `ENTITLEMENT_PLAN` transcribes its ten live entitlement rows —
the table is ten rows and static, so a live read buys nothing but an
unnecessary BigQuery round-trip during generation.

Model, per (route, day, half)
------------------------------
1. **congestion_index** — a route's `congestion_factor` plus AM/PM-specific
   noise. The PM draw is not independent of the AM draw on the same
   (route, day): PM's mean is nudged upward by `LEAD_COEFFICIENT` times
   whatever AM's congestion ran over the route's baseline. This is the
   leading-indicator signal `queue_buildup_leading_indicator` looks for — a
   queue that built in the morning does not fully clear by afternoon.
2. **mean_cycle_time_mins** — the route's baseline cycle time scaled by
   congestion_index / congestion_factor, plus noise. This is what
   `congestion_cycle_time` bands and compares, the same shape as
   p6-metallurgist.yaml's `liberation` driver bands crusher gap setting.
3. **mean_queue_wait_mins** — zero when congestion_index is at or below the
   route's own baseline, and rises linearly above it. Capped at a fraction of
   the half's own cycle time so queue wait is never reported larger than the
   cycle it is part of.
4. **trip_count** — Poisson, mean set by how many minutes of a half's active
   haulage window (`ACTIVE_MINUTES_PER_HALF`) a route's own cycle time and
   assigned truck-equivalents divide into. Congestion that lengthens cycle
   time mechanically reduces trip_count for the same active window — the
   throughput cost of congestion this pack's guard requires reporting
   alongside the cycle-time finding.
5. **mean_payload_tons** — a per-route utilization fraction against the
   fleet's own average rated capacity (`FLEET_AVG_CAPACITY_TONS`, derived from
   the live `fleet_vehicles` mix of ten 240t and five 290t haul trucks). Three
   routes (`UNDERLOADED_ROUTES`) are deliberately assigned a lower utilization
   band — a planted, genuine finding for `payload_utilization` to surface,
   the same way `warranty.py` plants CONVEYOR-02/TRUCK-08 as deliberate
   exceptions rather than leaving every route at the same target by
   construction.

Two things this table does NOT do, on purpose: it carries no `operator_id` (no
table anywhere links a haul cycle to the operator who drove it at this grain,
which is exactly why `operator_behaviour_variance` in the pack stays
not_instrumented), and it carries no `vehicle_id` (fleet_vehicles is a single
snapshot with no historical assignment record, which is why
`breakdown_reassignment_effectiveness` stays not_instrumented too). Adding
either column here would make the diagnostic look supported when the
attributing join it would need does not exist.
"""

from __future__ import annotations

import os
from hashlib import blake2b

import numpy as np
import pandas as pd

from config import SEED

WINDOW_START = pd.Timestamp("2026-01-01", tz="UTC")
WINDOW_END = pd.Timestamp("2026-06-16", tz="UTC")  # inclusive; matches
# crusher_states / metallurgical_recovery's own last day, not erp_work_orders'
# 2026-06-17.

_GENERATED_DIR = os.path.join(os.path.dirname(__file__), "..", "generated")

# --------------------------------------------------------------------------
# The ten live haulage_routes rows, transcribed 2026-08-18. See module
# docstring for why this is hardcoded rather than queried at generation time.
# --------------------------------------------------------------------------
ROUTES: list[dict] = [
    {"route_id": "ROUTE-01", "source_location": "Stockpile East",
     "destination_location": "Waste Dump B", "average_cycle_time_mins": 11.57,
     "congestion_factor": 1.27, "distance_meters": 1031.49},
    {"route_id": "ROUTE-02", "source_location": "Pit Floor Bench 4",
     "destination_location": "Primary Crusher C", "average_cycle_time_mins": 15.43,
     "congestion_factor": 1.33, "distance_meters": 3351.94},
    {"route_id": "ROUTE-03", "source_location": "Pit Floor Bench 5",
     "destination_location": "Waste Dump B", "average_cycle_time_mins": 18.56,
     "congestion_factor": 1.04, "distance_meters": 3468.73},
    {"route_id": "ROUTE-04", "source_location": "Pit Floor Bench 5",
     "destination_location": "Primary Crusher C", "average_cycle_time_mins": 9.21,
     "congestion_factor": 1.39, "distance_meters": 533.75},
    {"route_id": "ROUTE-05", "source_location": "Pit Floor Bench 4",
     "destination_location": "Waste Dump B", "average_cycle_time_mins": 13.89,
     "congestion_factor": 1.24, "distance_meters": 2631.23},
    {"route_id": "ROUTE-06", "source_location": "Stockpile North",
     "destination_location": "Tailings Gate 1", "average_cycle_time_mins": 15.89,
     "congestion_factor": 1.24, "distance_meters": 759.67},
    {"route_id": "ROUTE-07", "source_location": "Stockpile East",
     "destination_location": "Primary Crusher C", "average_cycle_time_mins": 11.75,
     "congestion_factor": 1.06, "distance_meters": 2471.96},
    {"route_id": "ROUTE-08", "source_location": "Pit Floor Bench 4",
     "destination_location": "Primary Crusher C", "average_cycle_time_mins": 19.13,
     "congestion_factor": 1.05, "distance_meters": 3183.28},
    {"route_id": "ROUTE-09", "source_location": "Pit Floor Bench 4",
     "destination_location": "Tailings Gate 1", "average_cycle_time_mins": 6.44,
     "congestion_factor": 1.20, "distance_meters": 1446.02},
    {"route_id": "ROUTE-10", "source_location": "Stockpile North",
     "destination_location": "Primary Crusher C", "average_cycle_time_mins": 10.87,
     "congestion_factor": 1.05, "distance_meters": 1949.62},
]

#: (10 x 240t Cat 797F + 5 x 290t Komatsu 930E-5) / 15, from the live
#: fleet_vehicles mix — the fleet-wide reference `payload_utilization` bands
#: mean_payload_tons against.
FLEET_AVG_CAPACITY_TONS = (10 * 240.0 + 5 * 290.0) / 15.0

#: Deliberately underloaded routes — see module docstring point 5. Chosen by
#: hand, not derived, exactly as warranty.py's coverage groups are: a route
#: id list is easier for a reader to audit than a formula that happens to
#: pick three.
UNDERLOADED_ROUTES = {"ROUTE-03", "ROUTE-06", "ROUTE-09"}

#: How much of AM's excess congestion (over the route's own baseline) carries
#: into that day's PM draw. 0 would mean no leading indicator exists to find;
#: 1 would mean the queue never clears at all. See point 1.
LEAD_COEFFICIENT = 0.6

#: Minutes of active haulage a route runs within one 12-hour half, before
#: dividing by that half's own realised cycle time to get an expected trip
#: count. 360 (half of 720) reflects loading/unloading/shift-change time that
#: is not part of the logged cycle itself.
ACTIVE_MINUTES_PER_HALF = 360.0

#: Minutes of queue wait added per whole unit of congestion_index above a
#: route's own baseline (congestion_index / congestion_factor > 1.0).
QUEUE_WAIT_COEFFICIENT = 5.5


def _stable_hash(key: str) -> int:
    """Process-stable 32-bit hash — see common.py's identical function.

    Duplicated locally rather than imported, following supply_chain.py's own
    convention of a local `_stable_hash`/`_rng` pair rather than a shared
    import.
    """
    return int.from_bytes(blake2b(key.encode(), digest_size=4).digest(), "big")


def _rng(*parts: str) -> np.random.Generator:
    return np.random.default_rng((SEED + _stable_hash("|".join(parts))) & 0xFFFFFFFF)


def _truck_equivalents(route_id: str) -> float:
    """Deterministic per-route truck-equivalent count, fixed for the campaign."""
    return float(_rng("truck-equiv", route_id).uniform(1.1, 2.0))


def _utilization_target(route_id: str) -> float:
    """Deterministic per-route payload-utilization target. See UNDERLOADED_ROUTES."""
    if route_id in UNDERLOADED_ROUTES:
        return float(_rng("utilization", route_id).uniform(0.62, 0.74))
    return float(_rng("utilization", route_id).uniform(0.83, 0.93))


def build_haul_cycle_log() -> pd.DataFrame:
    days = pd.date_range(WINDOW_START, WINDOW_END, freq="D")
    rows: list[dict] = []
    for route in ROUTES:
        route_id = route["route_id"]
        baseline = route["congestion_factor"]
        truck_equiv = _truck_equivalents(route_id)
        utilization = _utilization_target(route_id)
        for day in days:
            date_str = day.strftime("%Y-%m-%d")

            rng_am = _rng("haul-cycle", route_id, date_str, "AM")
            congestion_am = float(
                np.clip(
                    rng_am.normal(baseline, 0.12 * baseline),
                    baseline * 0.55,
                    baseline * 1.9,
                )
            )

            excess_am = max(0.0, congestion_am - baseline)
            rng_pm = _rng("haul-cycle", route_id, date_str, "PM")
            congestion_pm = float(
                np.clip(
                    rng_pm.normal(
                        baseline + LEAD_COEFFICIENT * excess_am, 0.10 * baseline
                    ),
                    baseline * 0.55,
                    baseline * 2.2,
                )
            )

            for half, ts_hour, congestion_index, rng in (
                ("AM", 0, congestion_am, rng_am),
                ("PM", 12, congestion_pm, rng_pm),
            ):
                timestamp = day + pd.Timedelta(hours=ts_hour)
                cycle_time = route["average_cycle_time_mins"] * (
                    congestion_index / baseline
                ) + float(rng.normal(0.0, 0.4))
                cycle_time = max(
                    cycle_time, route["average_cycle_time_mins"] * 0.5
                )

                queue_wait = max(0.0, congestion_index - baseline) * (
                    QUEUE_WAIT_COEFFICIENT
                ) + float(rng.normal(0.0, 0.3))
                queue_wait = float(np.clip(queue_wait, 0.0, 0.65 * cycle_time))

                lam = max(3.0, ACTIVE_MINUTES_PER_HALF / cycle_time * truck_equiv)
                trip_count = int(rng.poisson(lam))

                payload = utilization * FLEET_AVG_CAPACITY_TONS + float(
                    rng.normal(0.0, 4.0)
                )
                payload = float(np.clip(payload, 0.0, FLEET_AVG_CAPACITY_TONS * 1.05))

                rows.append(
                    {
                        "route_id": route_id,
                        "timestamp": timestamp.to_pydatetime(),
                        "trip_count": trip_count,
                        "mean_cycle_time_mins": round(cycle_time, 2),
                        "mean_queue_wait_mins": round(queue_wait, 2),
                        "mean_payload_tons": round(payload, 2),
                        "congestion_index": round(congestion_index, 4),
                    }
                )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def write_parquet() -> dict[str, pd.DataFrame]:
    os.makedirs(_GENERATED_DIR, exist_ok=True)
    haul_cycle_log = build_haul_cycle_log()
    tables = {"haul_cycle_log": haul_cycle_log}
    for name, df in tables.items():
        df.to_parquet(os.path.join(_GENERATED_DIR, f"{name}.parquet"), index=False)
    return tables


if __name__ == "__main__":  # pragma: no cover
    tables = write_parquet()
    for name, df in tables.items():
        print(f"{name}: {len(df)} rows")

    log = tables["haul_cycle_log"]
    print("\ncongestion_index distribution (all rows):")
    print(log.congestion_index.describe())
    print("\nmean_cycle_time_mins by route:")
    print(log.groupby("route_id").mean_cycle_time_mins.mean().sort_values())
    print("\nmean_payload_tons / FLEET_AVG_CAPACITY_TONS by route (utilization):")
    print(
        (log.groupby("route_id").mean_payload_tons.mean() / FLEET_AVG_CAPACITY_TONS)
        .sort_values()
    )
