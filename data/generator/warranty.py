"""Task 2b — warranty data for AGT-13 Warranty & OEM Claims.

`method/agt13-warranty.yaml` is the specification: every driver names a table
and columns a diagnostic needs. This module builds `warranty_entitlements`
and `warranty_claims`, joined correctly to the 152 COMPLETED repairs in
`maintenance_logs` / `erp_work_orders` so `own_cost_repairs` — a repair that
falls inside a coverage window with no matching claim — is answerable.

Entitlement grain is (asset, component, OEM), two per asset across the five
assets `maintenance_logs` actually covers (CONVEYOR-02, CRUSHER-03, MILL-01,
PUMP-104A, TRUCK-08) — `fleet_vehicles`' 15 haul trucks carry no work-order
history of their own, so an entitlement over them could never join to a real
repair; they inform `capital.py`'s options instead (see that module's
docstring).

Coverage design (measured and banded in `tests/test_realism.py` R11 / R11b)
----------------------------------------------------------------------------
The whole point of AGT-13 is that "inside warranty but paid own cost" must be
a genuine finding, not an artefact of a uniformly random coverage_end spread
over two years (which would make every repair's eligibility a coin flip with
no structure to discover) — and not an artefact of a coverage window so broad
that it swallows the entire 2026-01-01..2026-06-17 work-order window, which
would make "inside cover" true of almost every repair instead of a genuine
minority. A producing mine's fleet is mostly past its OEM warranty window at
any given moment: heavy mining equipment typically carries 12-24 months of
manufacturer cover from commissioning (occasionally longer for a standing
extended-service agreement on a critical asset), so a mixed-age fleet has a
minority of assets — and their repairs — inside any live coverage window, not
a majority. So coverage is assigned per *asset*, not independently per
entitlement, in three deliberately clustered groups:

* **CONVEYOR-02** — both entitlements span the whole repair window (well
  before 2026-01-01 to well after 2026-06-17), modelling a standing multi-year
  extended-service agreement on this one critical asset. Every repair on it
  is eligible; the finding here is entitlements that never expire yet are
  still not claimed. It is deliberately the exception, not the rule: it is
  one of five assets, so it cannot on its own push the fleet-wide fraction of
  covered repairs out of the minority band R11b polices.
* **CRUSHER-03, MILL-01, PUMP-104A** — both entitlements on each asset expire
  on the SAME date: a cutoff set at `CLIFF_QUANTILE` (a low quantile, not the
  median) of that asset's own repair dates, recovered from
  `erp_work_orders.created_at` at runtime, never hardcoded. A low quantile
  means the OEM window closed early in this asset's own repair history, so
  only a minority of its repairs land before the cutoff — matching a fleet
  mostly past warranty, not a coin flip. Repairs before the cutoff are
  eligible; repairs after are not. This is the cliff: a repair on CRUSHER-03
  dated one day after its cutoff was never covered, and one day before it was
  — not a smooth probability, a hard edge grounded in when this asset's own
  repairs actually happened.
* **TRUCK-08** — both entitlements expired in 2025, before the repair window
  even starts. No repair on TRUCK-08 was ever covered; the finding is
  recoverable value that a lapsed clause protected but nothing ever tested it
  against, because the window had already closed.

`warranty_claims` is filed against a MINORITY (`CLAIM_FILE_PROB`) of eligible
repairs — the rest are exactly the own-cost-repair findings AGT-13 exists to
surface.
"""

from __future__ import annotations

import os

import pandas as pd
from google.cloud import bigquery

from common import rng_for
from config import PROJECT_ID, DATASET, SEED

WINDOW_START = pd.Timestamp("2026-01-01", tz="UTC")
WINDOW_END = pd.Timestamp("2026-06-17", tz="UTC")

_GENERATED_DIR = os.path.join(os.path.dirname(__file__), "..", "generated")

# --------------------------------------------------------------------------
# Design parameters
# --------------------------------------------------------------------------

#: Fraction of eligible (inside-coverage) repairs that actually get a claim
#: filed. The rest are the own-cost-repair findings by construction.
CLAIM_FILE_PROB = 0.35

#: Rank, within a cliff asset's own sorted repair dates, its entitlements
#: expire at. 0.5 would be the median — a coin-flip split. 0.12 means the
#: cutoff sits at roughly the asset's earliest-repaired-tenth: the OEM window
#: on this component closed early in the asset's own repair history, so only
#: a minority of its repairs land inside cover, consistent with a mixed-age
#: fleet mostly past warranty at any given moment (see the module docstring).
#: Tuned, together with the CONVEYOR-02/TRUCK-08 groups, so the fleet-wide
#: fraction of repairs inside cover lands mid COVERAGE_MINORITY_BAND in
#: tests/test_realism.py's R11b.
CLIFF_QUANTILE = 0.12

#: Two components per asset, each with a fictional OEM vendor (industry-
#: plausible, not naming any real manufacturer). "full", "cliff" and
#: "expired" select the coverage group described in the module docstring.
ENTITLEMENT_PLAN: list[dict] = [
    {"asset_id": "CONVEYOR-02", "component": "Belt Drive Motor",
     "oem_vendor": "Northgate Conveyor Systems", "group": "full"},
    {"asset_id": "CONVEYOR-02", "component": "Idler Bearing Assembly",
     "oem_vendor": "Meridian Bearing & Seal Co", "group": "full"},
    {"asset_id": "CRUSHER-03", "component": "Crusher Liner Assembly",
     "oem_vendor": "Apex Crusher Systems", "group": "cliff"},
    {"asset_id": "CRUSHER-03", "component": "Hydraulic Adjustment System",
     "oem_vendor": "Vantage Hydraulics Group", "group": "cliff"},
    {"asset_id": "MILL-01", "component": "Girth Gear Drive",
     "oem_vendor": "Summit Gear & Drive Corp", "group": "cliff"},
    {"asset_id": "MILL-01", "component": "Trunnion Bearing",
     "oem_vendor": "Meridian Bearing & Seal Co", "group": "cliff"},
    {"asset_id": "PUMP-104A", "component": "Slurry Pump Bearing Unit",
     "oem_vendor": "Meridian Bearing & Seal Co", "group": "cliff"},
    {"asset_id": "PUMP-104A", "component": "Seal & Gland Assembly",
     "oem_vendor": "Vantage Hydraulics Group", "group": "cliff"},
    {"asset_id": "TRUCK-08", "component": "Drivetrain & Transmission",
     "oem_vendor": "TerraDrive Powertrain Group", "group": "expired"},
    {"asset_id": "TRUCK-08", "component": "Engine & Powertrain",
     "oem_vendor": "TerraDrive Powertrain Group", "group": "expired"},
]

_FULL_START = pd.Timestamp("2024-01-01", tz="UTC")
_FULL_END = pd.Timestamp("2027-06-01", tz="UTC")
_EXPIRED_START = pd.Timestamp("2023-06-01", tz="UTC")
_EXPIRED_END = pd.Timestamp("2025-11-15", tz="UTC")
_CLIFF_START = pd.Timestamp("2024-06-01", tz="UTC")

_CLAIM_STATUSES = ("SUBMITTED", "APPROVED", "PAID", "DENIED")
_CLAIM_STATUS_WEIGHTS = (0.20, 0.15, 0.55, 0.10)


# --------------------------------------------------------------------------
# Sources
# --------------------------------------------------------------------------


def _client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID)


def load_completed_repairs() -> pd.DataFrame:
    """152 COMPLETED work orders joined to their maintenance log, live.

    `erp_work_orders` and `maintenance_logs` are in REWRITE_TABLES and were
    already regenerated by Task 4/8; the current live copies are exactly the
    data every other agent tool reads, so this reads live too rather than a
    frozen backup that predates that regeneration.
    """
    sql = f"""
        SELECT ml.work_order_id, wo.asset_id, wo.created_at, wo.repair_cost
        FROM `{PROJECT_ID}.{DATASET}.maintenance_logs` ml
        JOIN `{PROJECT_ID}.{DATASET}.erp_work_orders` wo USING (work_order_id)
        WHERE wo.status = 'COMPLETED'
        ORDER BY wo.asset_id, wo.created_at
    """
    df = _client().query(sql).to_dataframe()
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    return df


def cliff_cutoff_date_by_asset(
    repairs: pd.DataFrame, quantile: float = CLIFF_QUANTILE
) -> dict[str, pd.Timestamp]:
    """Each asset's own COMPLETED-repair date at the given quantile rank,
    recovered at runtime — never hardcoded. An *actual observed* repair
    timestamp is returned (the one at that sorted rank), not an interpolated
    value between two repairs, so the cutoff is always a real cliff asset's
    own genuine repair date.
    """
    out: dict[str, pd.Timestamp] = {}
    for asset, group in repairs.groupby("asset_id"):
        dates = group.created_at.sort_values().reset_index(drop=True)
        idx = min(int(round(quantile * (len(dates) - 1))), len(dates) - 1)
        out[asset] = pd.Timestamp(dates.iloc[idx])
    return out


# --------------------------------------------------------------------------
# warranty_entitlements
# --------------------------------------------------------------------------


def build_entitlements(cliff_dates: dict[str, pd.Timestamp],
                        plan: list[dict] = ENTITLEMENT_PLAN) -> pd.DataFrame:
    rows = []
    for i, spec in enumerate(plan):
        group = spec["group"]
        if group == "full":
            start, end = _FULL_START, _FULL_END
        elif group == "expired":
            start, end = _EXPIRED_START, _EXPIRED_END
        elif group == "cliff":
            start, end = _CLIFF_START, cliff_dates[spec["asset_id"]]
        else:
            raise ValueError(f"unknown coverage group {group!r}")

        oem_code = "".join(w[0] for w in spec["oem_vendor"].split())[:4].upper()
        months = max(1, round((end - start).days / 30))
        rows.append(
            {
                "entitlement_id": f"WEN-{i + 1:03d}",
                "asset_id": spec["asset_id"],
                "oem_vendor": spec["oem_vendor"],
                "component": spec["component"],
                "coverage_start": start.date(),
                "coverage_end": end.date(),
                "source_clause": f"{oem_code}-WARR-{months}MO-{spec['component'].split()[0].upper()}",
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# warranty_claims
# --------------------------------------------------------------------------


def _active_entitlement(entitlements: pd.DataFrame, asset_id: str,
                         repair_date: pd.Timestamp) -> pd.Series | None:
    match = entitlements[
        (entitlements.asset_id == asset_id)
        & (pd.to_datetime(entitlements.coverage_start, utc=True) <= repair_date)
        & (pd.to_datetime(entitlements.coverage_end, utc=True) >= repair_date)
    ]
    if match.empty:
        return None
    return match.iloc[0]


def build_claims(entitlements: pd.DataFrame, repairs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for repair in repairs.itertuples():
        entitlement = _active_entitlement(entitlements, repair.asset_id, repair.created_at)
        if entitlement is None:
            continue  # not eligible: no live entitlement covers this repair

        rng = rng_for(SEED, "claim-decision", repair.work_order_id)
        if rng.random() >= CLAIM_FILE_PROB:
            continue  # eligible but never claimed: the own-cost-repair finding

        filed_lag_days = int(rng.integers(5, 26))
        filed_date = repair.created_at + pd.Timedelta(days=filed_lag_days)
        status = rng.choice(_CLAIM_STATUSES, p=_CLAIM_STATUS_WEIGHTS)
        claim_fraction = 1.0 if status in ("PAID", "APPROVED") else round(
            float(rng.uniform(0.6, 1.0)), 4
        )
        rows.append(
            {
                "claim_id": f"WCL-{len(rows) + 1:04d}",
                "entitlement_id": entitlement.entitlement_id,
                "work_order_id": repair.work_order_id,
                "filed_date": filed_date.date(),
                "status": str(status),
                "amount_claimed": round(float(repair.repair_cost) * claim_fraction, 2),
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def write_parquet() -> dict[str, pd.DataFrame]:
    os.makedirs(_GENERATED_DIR, exist_ok=True)
    repairs = load_completed_repairs()
    cliff_dates = cliff_cutoff_date_by_asset(repairs)
    entitlements = build_entitlements(cliff_dates)
    claims = build_claims(entitlements, repairs)

    tables = {"warranty_entitlements": entitlements, "warranty_claims": claims}
    for name, df in tables.items():
        df.to_parquet(os.path.join(_GENERATED_DIR, f"{name}.parquet"), index=False)
    return tables


if __name__ == "__main__":  # pragma: no cover
    tables = write_parquet()
    for name, df in tables.items():
        print(f"{name}: {len(df)} rows")

    repairs = load_completed_repairs()
    cliff_dates = cliff_cutoff_date_by_asset(repairs)
    entitlements = build_entitlements(cliff_dates)
    repairs = repairs.assign(
        eligible=[
            _active_entitlement(entitlements, r.asset_id, r.created_at) is not None
            for r in repairs.itertuples()
        ]
    )
    print("\nEligible-repair fraction by asset:")
    print(repairs.groupby("asset_id").eligible.mean())

    claimed_wo = set(tables["warranty_claims"].work_order_id)
    own_cost = repairs[repairs.eligible & ~repairs.work_order_id.isin(claimed_wo)]
    print(f"\nEligible but never claimed (own-cost repairs): {len(own_cost)} "
          f"of {int(repairs.eligible.sum())} eligible repairs")
