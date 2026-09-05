"""Task 2b — plan and capital data for AGT-19 Strategic Planning Advisor.

`method/agt19-strategic-planning.yaml` names four tables for the scope this
build covers: `plan_versions`, `plan_assumptions`, `plan_scenarios`,
`capital_options`. The pack's other three drivers (`local_vs_group_divergence`,
`capital_option_dominance`, `plan_output_completeness`) additionally need
`site_plans`, `group_plan`, `option_outcomes` and `plan_output_checklist` — a
simulation/Monte-Carlo capability this build does not have and is out of
scope for Task 2b, which was given exactly these four tables to build. Those
three drivers stay `not_instrumented` for a real reason after this module
lands, not an oversight.

`capital_options.description` is grounded in `fleet_vehicles` (the number of
haul trucks currently in MAINTENANCE status, queried live, never hardcoded)
and in the same five assets `warranty.py` covers — a mining group's actual
candidate capital projects are reliability programs on the equipment already
showing up in the maintenance and warranty data, not invented projects with
no connection to anything else in this dataset.

Realism, by design (measured and banded in `tests/test_realism.py` R12/R13)
-----------------------------------------------------------------------------
* **The contained-metal price assumption is sampled from a real price deck,
  not conjured at each plan version independently.** `contained_metal_price_
  deck` is a standalone shipped table — a monthly reference-price curve,
  2023-01 to 2028-01, an Ornstein-Uhlenbeck path (`common.ou_process`)
  bracketing the 2026 operational window every other table uses. It is the
  data a group finance team's "price deck" (the standard term for a
  treasury/planning function's forward commodity and FX curve) actually
  looks like: dense enough, over a long enough horizon, that a lag-1
  autocorrelation is a real, measurable property of the *shipped* table
  rather than of the six sparse quarterly points `plan_assumptions` alone
  could ever carry — six points give five lag-1 pairs, which is not a
  measurable autocorrelation at all. `plan_assumptions.assumed_value` for
  `contained_metal_price_usd_per_tonne` is sampled from this deck at each
  plan version's `published_date`, so the two are the same data, not two
  numbers that happen to share a name. Never named as a specific metal
  anywhere in this module: it is "contained metal," priced per tonne,
  matching the project's commodity-neutral constraint.
* **Assumptions go stale at differing rates by design, not by chance.** Each
  metric carries its own hazard: `contained_metal_price_usd_per_tonne` and
  `fx_rate_usd_per_local` supersede early in almost every quarter (a plan
  built on a commodity price is out of date within weeks); `discount_rate_pct`
  and `throughput_tpd` rarely move within a single quarterly cycle at all. The
  resulting staleness — `next_review_date - superseded_date` — is therefore
  large for the volatile metrics (they go stale early and the quarterly
  cadence does not catch up) and small or absent for the stable ones. That
  differing-rate distribution is the entire point of `assumption_staleness`.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
from google.cloud import bigquery

from common import ou_process, rng_for, stable_hash
from config import PROJECT_ID, DATASET, SEED

_GENERATED_DIR = os.path.join(os.path.dirname(__file__), "..", "generated")

# --------------------------------------------------------------------------
# plan_versions — six quarterly cycles, 2025-01-15 .. 2026-04-15, so the last
# cycle's review date (2026-07-15) sits after the operational window every
# other table uses (2026-01-01 .. 2026-06-17) ends.
# --------------------------------------------------------------------------

PLAN_VERSION_IDS = [
    "PV-2025-Q1", "PV-2025-Q2", "PV-2025-Q3",
    "PV-2025-Q4", "PV-2026-Q1", "PV-2026-Q2",
]

_PUBLISHED_DATES = pd.to_datetime(
    ["2025-01-15", "2025-04-15", "2025-07-15",
     "2025-10-15", "2026-01-15", "2026-04-15"],
    utc=True,
)
_NEXT_REVIEW_DATES = pd.to_datetime(
    ["2025-04-15", "2025-07-15", "2025-10-15",
     "2026-01-15", "2026-04-15", "2026-07-15"],
    utc=True,
)


def build_plan_versions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "plan_version_id": PLAN_VERSION_IDS,
            "published_date": [d.date() for d in _PUBLISHED_DATES],
            "next_review_date": [d.date() for d in _NEXT_REVIEW_DATES],
        }
    )


# --------------------------------------------------------------------------
# plan_assumptions
# --------------------------------------------------------------------------

#: metric_name -> (ou_mu, ou_sigma, ou_phi, round_decimals, supersede_prob,
#: mean_offset_days, offset_sd_days). Ordered fastest- to slowest-moving.
#: supersede_prob / mean_offset_days is the hazard that gives R13 its
#: differing-rate distribution — see the module docstring.
ASSUMPTION_METRICS: dict[str, tuple] = {
    "contained_metal_price_usd_per_tonne": (9000.0, 450.0, 0.6, 1, 0.95, 18, 6),
    "fx_rate_usd_per_local": (0.70, 0.02, 0.6, 4, 0.85, 30, 10),
    "diesel_price_usd_per_litre": (1.05, 0.05, 0.6, 3, 0.75, 40, 12),
    "opex_escalation_pct_pa": (3.8, 0.3, 0.6, 2, 0.45, 55, 15),
    "strip_ratio": (5.0, 0.15, 0.6, 2, 0.25, 65, 15),
    "throughput_tpd": (40000.0, 800.0, 0.6, 0, 0.20, 70, 12),
    "discount_rate_pct": (8.5, 0.15, 0.6, 2, 0.10, 75, 10),
}

#: The metric whose value is sampled from the dense contained_metal_price_deck
#: table rather than an independent per-plan-version draw — see
#: build_price_deck() below.
PRICE_METRIC = "contained_metal_price_usd_per_tonne"

#: contained_metal_price_deck horizon: a multi-year monthly curve bracketing
#: the 2026-01-01..2026-06-17 operational window every other table uses, the
#: way a real group finance "price deck" spans several years of a life-of-
#: mine plan rather than just the current operating window.
PRICE_DECK_START = pd.Timestamp("2023-01-01", tz="UTC")
PRICE_DECK_END = pd.Timestamp("2028-01-01", tz="UTC")
PRICE_DECK_FREQ = "MS"  # month start: a price deck is refreshed monthly, not daily

#: phi is the AR(1)/OU process's theoretical lag-1 autocorrelation. 0.80
#: lands mid tests/test_realism.py R12's [0.55, 0.95] band on the *shipped*
#: contained_metal_price_deck table itself (measured directly from BigQuery,
#: not an in-memory intermediate) — high enough that a monthly commodity
#: reference price persists the way a real one does, well short of a
#: literal random walk (phi=1, non-stationary).
PRICE_DECK_OU_PHI = 0.80


def build_price_deck() -> pd.DataFrame:
    """Monthly contained-metal reference price curve, an OU (mean-reverting
    random walk) path — not a specific metal, per the project's commodity-
    neutral constraint. This is the table R12 measures lag-1 autocorrelation
    on directly in BigQuery; `plan_assumptions.assumed_value` for
    `PRICE_METRIC` is sampled from it at each plan version's `published_date`,
    so the quarterly snapshot in that table and the deck behind it are the
    same data, not two independent numbers that happen to share a name.
    """
    mu, sigma, _, _, *_ = ASSUMPTION_METRICS[PRICE_METRIC]
    dates = pd.date_range(PRICE_DECK_START, PRICE_DECK_END, freq=PRICE_DECK_FREQ, tz="UTC")
    seed = (SEED + stable_hash("contained-metal-price-deck")) & 0xFFFFFFFF
    values = ou_process(len(dates), mu, sigma, PRICE_DECK_OU_PHI, seed)
    return pd.DataFrame(
        {
            "price_date": [d.date() for d in dates],
            "contained_metal_price_usd_per_tonne": np.round(values, 1),
        }
    )


def _assumed_values(metric: str, plan_versions: pd.DataFrame) -> np.ndarray:
    if metric == PRICE_METRIC:
        deck = build_price_deck()
        deck_dates = pd.to_datetime(deck.price_date, utc=True)
        out = []
        for d in plan_versions.published_date:
            target = pd.Timestamp(d, tz="UTC")
            idx = int((deck_dates - target).abs().idxmin())
            out.append(deck.contained_metal_price_usd_per_tonne.iloc[idx])
        return np.array(out)

    mu, sigma, phi, decimals, *_ = ASSUMPTION_METRICS[metric]
    seed = (SEED + stable_hash(metric)) & 0xFFFFFFFF
    path = ou_process(len(PLAN_VERSION_IDS), mu, sigma, phi, seed)
    return np.round(path, decimals)


def build_plan_assumptions(plan_versions: pd.DataFrame) -> pd.DataFrame:
    published = pd.to_datetime(plan_versions.published_date, utc=True)
    next_review = pd.to_datetime(plan_versions.next_review_date, utc=True)

    rows = []
    for metric, spec in ASSUMPTION_METRICS.items():
        _, _, _, _, supersede_prob, mean_offset, offset_sd = spec
        values = _assumed_values(metric, plan_versions)
        for i, plan_version_id in enumerate(plan_versions.plan_version_id):
            eff = published.iloc[i]
            quarter_days = (next_review.iloc[i] - eff).days

            rng = rng_for(SEED, "assumption", metric, plan_version_id)
            superseded = None
            if rng.random() < supersede_prob:
                offset = int(round(rng.normal(mean_offset, offset_sd)))
                offset = max(1, min(quarter_days - 1, offset))
                superseded = (eff + pd.Timedelta(days=offset)).date()

            rows.append(
                {
                    "assumption_id": f"ASM-{len(rows) + 1:04d}",
                    "plan_version_id": plan_version_id,
                    "metric_name": metric,
                    "assumed_value": float(values[i]),
                    "effective_date": eff.date(),
                    "superseded_date": superseded,
                }
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# plan_scenarios — sensitivity to the contained-metal price, the most
# decision-relevant assumption in the plan.
# --------------------------------------------------------------------------

_SCENARIO_SPECS = (
    ("downside", -0.18, -0.10,
     "trailing 90-day average price falls through the downside case for two "
     "consecutive quarterly reviews"),
    ("upside", 0.08, 0.16,
     "trailing 90-day average price clears the upside case for two "
     "consecutive quarterly reviews"),
)


def build_plan_scenarios(plan_versions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for plan_version_id in plan_versions.plan_version_id:
        for label, lo, hi, trigger_tail in _SCENARIO_SPECS:
            rng = rng_for(SEED, "scenario", plan_version_id, label)
            delta_pct = round(float(rng.uniform(lo, hi)) * 100.0, 1)
            reversal_cost = round(float(rng.uniform(2_000_000.0, 38_000_000.0)), 2)
            rows.append(
                {
                    "scenario_id": f"SCN-{len(rows) + 1:04d}",
                    "plan_version_id": plan_version_id,
                    "assumption_delta": (
                        f"contained_metal_price_usd_per_tonne {delta_pct:+.1f}% "
                        f"vs plan case ({label})"
                    ),
                    "reversal_trigger": (
                        f"Reverse the capital decision this plan case supports if "
                        f"the {trigger_tail}"
                    ),
                    "reversal_cost": reversal_cost,
                }
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# capital_options
# --------------------------------------------------------------------------


def _client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID)


def fleet_maintenance_count() -> int:
    """Haul trucks currently in MAINTENANCE status — queried live, never hardcoded."""
    sql = (
        f"SELECT COUNT(*) AS n FROM `{PROJECT_ID}.{DATASET}.fleet_vehicles` "
        "WHERE operational_status = 'MAINTENANCE'"
    )
    return int(next(iter(_client().query(sql).result())).n)


def _capital_option_catalogue(n_maintenance: int, n_fleet: int) -> dict[str, str]:
    return {
        "CAP-A": (
            f"Autonomous haul fleet reliability program: rebuild or replace the "
            f"{n_maintenance} of {n_fleet} units currently sitting in "
            f"MAINTENANCE status"
        ),
        "CAP-B": (
            "Crusher liner and hydraulic adjustment system life-extension for "
            "CRUSHER-03, timed ahead of its OEM-covered component windows lapsing"
        ),
        "CAP-C": (
            "Slurry pump bearing reliability program for PUMP-104A, addressing "
            "the recorded vibration degradation trend"
        ),
        "CAP-D": (
            "Mill throughput debottlenecking: girth gear drive and trunnion "
            "bearing upgrade for MILL-01"
        ),
        "CAP-E": (
            "Stage 3 processing capacity expansion, sanction contingent on the "
            "contained-metal price case holding"
        ),
    }


#: option key -> first plan_version_id it appears in (index into
#: PLAN_VERSION_IDS). A capital pipeline is a standing set of projects that
#: grows over time, not a fixed list re-evaluated identically every cycle.
_OPTION_ENTRY_INDEX = {"CAP-A": 0, "CAP-B": 0, "CAP-C": 0, "CAP-D": 2, "CAP-E": 4}


def build_capital_options(plan_versions: pd.DataFrame) -> pd.DataFrame:
    n_maintenance = fleet_maintenance_count()
    n_fleet_sql = (
        f"SELECT COUNT(*) AS n FROM `{PROJECT_ID}.{DATASET}.fleet_vehicles`"
    )
    n_fleet = int(next(iter(_client().query(n_fleet_sql).result())).n)
    catalogue = _capital_option_catalogue(n_maintenance, n_fleet)

    rows = []
    for i, plan_version_id in enumerate(plan_versions.plan_version_id):
        for key, description in catalogue.items():
            if i < _OPTION_ENTRY_INDEX[key]:
                continue
            rows.append(
                {
                    "option_id": f"{key}-{plan_version_id}",
                    "plan_version_id": plan_version_id,
                    "description": description,
                }
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def write_parquet() -> dict[str, pd.DataFrame]:
    os.makedirs(_GENERATED_DIR, exist_ok=True)
    plan_versions = build_plan_versions()
    plan_assumptions = build_plan_assumptions(plan_versions)
    plan_scenarios = build_plan_scenarios(plan_versions)
    capital_options = build_capital_options(plan_versions)
    contained_metal_price_deck = build_price_deck()

    tables = {
        "plan_versions": plan_versions,
        "plan_assumptions": plan_assumptions,
        "plan_scenarios": plan_scenarios,
        "capital_options": capital_options,
        "contained_metal_price_deck": contained_metal_price_deck,
    }
    for name, df in tables.items():
        df.to_parquet(os.path.join(_GENERATED_DIR, f"{name}.parquet"), index=False)
    return tables


if __name__ == "__main__":  # pragma: no cover
    tables = write_parquet()
    for name, df in tables.items():
        print(f"{name}: {len(df)} rows")

    pa = tables["plan_assumptions"]
    pv = tables["plan_versions"].set_index("plan_version_id")
    superseded = pa.dropna(subset=["superseded_date"]).copy()
    superseded["next_review_date"] = superseded.plan_version_id.map(pv.next_review_date)
    superseded["staleness_days"] = (
        pd.to_datetime(superseded.next_review_date)
        - pd.to_datetime(superseded.superseded_date)
    ).dt.days
    print("\nMean staleness (days) by metric, where superseded before next review:")
    print(superseded.groupby("metric_name").staleness_days.mean().sort_values(ascending=False))
