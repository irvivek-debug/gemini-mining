"""Tests for data/generator/warranty.py (Task 2b — AGT-13 warranty data).

Verifies schema, that entitlement_id / work_order_id foreign keys resolve
(the latter against the live 152-row COMPLETED join, not a fabricated id),
and the coverage design described in the module docstring: one asset fully
covered, three with a clean quantile-dated cliff, one never covered. The
banded cliff statistic and the fleet-wide minority-coverage statistic are
R11 / R11b in ``test_realism.py``.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import pytest

import warranty as W

KNOWN_ASSETS = {"CONVEYOR-02", "CRUSHER-03", "MILL-01", "PUMP-104A", "TRUCK-08"}


@pytest.fixture(scope="module")
def repairs():
    return W.load_completed_repairs()


@pytest.fixture(scope="module")
def cliff_dates(repairs):
    return W.cliff_cutoff_date_by_asset(repairs)


@pytest.fixture(scope="module")
def entitlements(cliff_dates):
    return W.build_entitlements(cliff_dates)


@pytest.fixture(scope="module")
def claims(entitlements, repairs):
    return W.build_claims(entitlements, repairs)


class TestSchema:
    def test_entitlements_columns(self, entitlements):
        assert list(entitlements.columns) == [
            "entitlement_id", "asset_id", "oem_vendor", "component",
            "coverage_start", "coverage_end", "source_clause",
        ]

    def test_claims_columns(self, claims):
        assert list(claims.columns) == [
            "claim_id", "entitlement_id", "work_order_id", "filed_date",
            "status", "amount_claimed",
        ]

    def test_ten_entitlements_two_per_asset(self, entitlements):
        assert len(entitlements) == 10
        assert (entitlements.groupby("asset_id").size() == 2).all()

    def test_entitlement_ids_unique(self, entitlements):
        assert entitlements.entitlement_id.is_unique

    def test_claim_ids_unique(self, claims):
        assert claims.claim_id.is_unique

    def test_coverage_start_before_coverage_end(self, entitlements):
        start = pd.to_datetime(entitlements.coverage_start)
        end = pd.to_datetime(entitlements.coverage_end)
        assert (start < end).all()

    def test_asset_id_is_one_of_the_five_maintenance_logs_assets(self, entitlements):
        assert set(entitlements.asset_id) == KNOWN_ASSETS


class TestForeignKeys:
    def test_claims_entitlement_id_resolves(self, entitlements, claims):
        missing = set(claims.entitlement_id) - set(entitlements.entitlement_id)
        assert not missing, f"warranty_claims.entitlement_id(s) dangling: {missing}"

    def test_claims_work_order_id_resolves_to_a_completed_repair(self, repairs, claims):
        missing = set(claims.work_order_id) - set(repairs.work_order_id)
        assert not missing, f"warranty_claims.work_order_id(s) dangling: {missing}"

    def test_claim_amount_never_exceeds_the_work_orders_repair_cost(self, repairs, claims):
        merged = claims.merge(repairs[["work_order_id", "repair_cost"]], on="work_order_id")
        over = merged[merged.amount_claimed > merged.repair_cost + 0.01]
        assert over.empty, f"claim(s) exceed their work order's repair_cost: {over.claim_id.tolist()}"


class TestCoverageDesign:
    def test_conveyor_02_is_fully_covered_across_the_repair_window(self, entitlements, repairs):
        sub = entitlements[entitlements.asset_id == "CONVEYOR-02"]
        assert (pd.to_datetime(sub.coverage_start, utc=True) <= W.WINDOW_START).all()
        assert (pd.to_datetime(sub.coverage_end, utc=True) >= W.WINDOW_END).all()

    def test_truck_08_entitlements_expired_before_the_repair_window_opened(self, entitlements):
        sub = entitlements[entitlements.asset_id == "TRUCK-08"]
        assert (pd.to_datetime(sub.coverage_end, utc=True) < W.WINDOW_START).all()

    def test_cliff_assets_expire_on_their_own_measured_quantile_repair_date(
        self, entitlements, cliff_dates
    ):
        for asset in ("CRUSHER-03", "MILL-01", "PUMP-104A"):
            sub = entitlements[entitlements.asset_id == asset]
            ends = pd.to_datetime(sub.coverage_end, utc=True)
            assert (ends == cliff_dates[asset]).all(), (
                f"{asset} entitlement coverage_end does not match its own "
                "measured cliff-quantile repair date"
            )

    def test_cliff_assets_have_a_minority_of_repairs_before_their_cutoff(
        self, repairs, cliff_dates
    ):
        for asset in ("CRUSHER-03", "MILL-01", "PUMP-104A"):
            sub = repairs[repairs.asset_id == asset]
            before = (sub.created_at <= cliff_dates[asset]).mean()
            assert before < 0.5, (
                f"{asset}: {before:.2%} of its repairs fall before its own "
                "coverage cutoff — expected a minority (CLIFF_QUANTILE < 0.5), "
                "not a median split"
            )

    def test_repairs_inside_cover_are_a_fleet_wide_minority(self, entitlements, repairs):
        """A mixed-age fleet has a minority of repairs inside any live OEM
        coverage window at a given moment, not the near-total coverage a too-
        broad synthetic window produces. Banded precisely in
        tests/test_realism.py R11b, against the shipped BigQuery tables; this
        is a loose sanity check on the same in-memory generator output.
        """
        eligible = [
            W._active_entitlement(entitlements, r.asset_id, r.created_at) is not None
            for r in repairs.itertuples()
        ]
        fraction = sum(eligible) / len(eligible)
        assert fraction < 0.5, (
            f"{fraction:.2%} of all repairs are inside warranty cover — "
            "expected a genuine minority"
        )

    def test_own_cost_repairs_exist_a_genuine_minority_never_claimed(
        self, entitlements, repairs, claims
    ):
        eligible = [
            r.work_order_id
            for r in repairs.itertuples()
            if W._active_entitlement(entitlements, r.asset_id, r.created_at) is not None
        ]
        claimed = set(claims.work_order_id)
        own_cost = [wo for wo in eligible if wo not in claimed]
        assert len(eligible) > 0
        assert len(own_cost) > 0, "no eligible repair was ever left unclaimed"
        assert len(own_cost) < len(eligible), "every eligible repair was claimed — no gap to find"
