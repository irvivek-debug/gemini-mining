"""Tests for data/generator/supply_chain.py (Task 6 — A4 supply-chain coupling).

Verifies:
  - the regenerated inventory_levels snapshot keeps its schema and gains the two
    catalogue rows (SKU-AIR-FILTER-08, SKU-VALVE-SEAL-22) that Task 4 found
    missing, so every SKU reachable from parts_replaced or work_order_parts_edge
    resolves to a row
  - 12-18 parts sit below reorder point and none of them is negative
  - the S08 GRAPH_TABLE traversal over MiningSupplyChainGraph returns at least
    one path from a below-ROP part through a work order to PUMP-104A, and that
    asset is CRITICAL-rated -- established by traversal, not by construction,
    with a negative control proving the query really filters
  - the stockout is timed against the Task 2 degradation ramp: the ramp onset is
    recovered from the telemetry series by changepoint fit (never hardcoded),
    PUMP-104A part demand accelerates inside that window, the reorder-point
    crossings fall inside it, and the replenishment lands after the snapshot
  - aggregate calibration still matches data/profile/stats.json
  - deterministic across two processes with different PYTHONHASHSEED values
"""

import hashlib
import os
import subprocess
import sys

# abspath matters: config.py locates data/profile/ relative to its own __file__,
# so an unnormalised ".." on sys.path would send it looking in tests/profile/.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
import pytest

from config import BACKUP_SUFFIX, SEED, STATS
from supply_chain import (
    DEGRADING_ASSET,
    GRAPH_NAME,
    OUTPUT_PARQUET,
    MISSING_SKU_PRICE,
    MISSING_SKUS,
    _SOURCE_TABLES,
    build_ledger,
    consumption_events,
    critical_path_parts,
    detect_ramp_start,
    generate_inventory,
    load_telemetry,
    s08_stockout_exposure,
    write_parquet,
)

INV = STATS["inventory"][0]

BELOW_ROP_MIN = 12  # from the brief
BELOW_ROP_MAX = 18

SCHEMA_COLUMNS = [
    "lead_time_days",
    "part_description",
    "reorder_point_limit",
    "stock_level",
    "unit_price_usd",
    "part_number",
]

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


@pytest.fixture(scope="module")
def inv():
    return generate_inventory()


@pytest.fixture(scope="module")
def ledger():
    return build_ledger()


@pytest.fixture(scope="module")
def below_rop(inv):
    return inv[inv.stock_level < inv.reorder_point_limit]


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


class TestSourceProvenance:
    def test_inventory_read_from_frozen_backup(self):
        assert _SOURCE_TABLES["inventory_levels"].endswith(BACKUP_SUFFIX)

    def test_unrewritten_tables_read_live(self):
        # assets and work_order_parts_edge are not in REWRITE_TABLES, so they
        # have no _original_ snapshot and must be read live.
        for name in ("assets", "work_order_parts_edge"):
            assert not _SOURCE_TABLES[name].endswith(BACKUP_SUFFIX)


# ---------------------------------------------------------------------------
# Schema and the catalogue coverage hole
# ---------------------------------------------------------------------------


class TestSchema:
    def test_columns_unchanged(self, inv):
        assert list(inv.columns) == SCHEMA_COLUMNS

    def test_dtypes(self, inv):
        assert inv.lead_time_days.dtype.kind == "i"
        assert inv.reorder_point_limit.dtype.kind == "i"
        assert inv.stock_level.dtype.kind == "i"
        assert inv.unit_price_usd.dtype.kind == "f"

    def test_row_count_is_original_plus_the_two_missing_skus(self, inv):
        assert len(inv) == INV["n"] + len(MISSING_SKUS)

    def test_part_numbers_unique(self, inv):
        assert inv.part_number.is_unique


class TestCatalogueCoverage:
    def test_missing_skus_added(self, inv):
        for sku in MISSING_SKUS:
            assert sku in set(inv.part_number)

    def test_missing_skus_priced_at_the_discrete_tier_median(self, inv):
        rows = inv[inv.part_number.isin(MISSING_SKUS)]
        assert set(rows.unit_price_usd) == {MISSING_SKU_PRICE}

    def test_missing_sku_price_is_the_median_of_the_discrete_tiers(self, inv):
        # $450 is not a magic number: it is the median of the three priced
        # maintenance-consumed SKUs in the original catalogue.
        priced = inv[
            inv.part_number.isin(
                ["SKU-BEARING-PUMP-G1", "SKU-BELT-SPLICE-G2", "SKU-LUBE-HEAVY-T2"]
            )
        ]
        assert float(np.median(priced.unit_price_usd)) == MISSING_SKU_PRICE

    def test_every_consumed_sku_resolves_to_a_catalogue_row(self, inv):
        """The defect Task 4 found: parts_replaced -> inventory_levels dropped rows."""
        consumed = set(consumption_events().part_number)
        edge = set(_edge_part_numbers())
        assert consumed, "consumption history is empty - fixture is broken"
        assert edge, "work_order_parts_edge is empty - fixture is broken"
        catalogue = set(inv.part_number)
        assert not (consumed | edge) - catalogue

    def test_missing_skus_were_genuinely_absent_before(self):
        """Guards against the test above passing vacuously."""
        original = _original_inventory()
        for sku in MISSING_SKUS:
            assert sku not in set(original.part_number)


def _edge_part_numbers():
    from supply_chain import load_parts_edge

    return load_parts_edge().part_number


def _original_inventory():
    from supply_chain import load_original_inventory

    return load_original_inventory()


# ---------------------------------------------------------------------------
# The headline invariants from the brief
# ---------------------------------------------------------------------------


class TestBelowReorderPoint:
    def test_count_within_band(self, below_rop):
        assert BELOW_ROP_MIN <= len(below_rop) <= BELOW_ROP_MAX

    def test_no_negative_stock(self, inv):
        assert int(inv.stock_level.min()) >= 0

    def test_critical_path_parts_are_below_rop(self, below_rop):
        crit = set(critical_path_parts(DEGRADING_ASSET))
        assert crit, "no critical-path parts found for the degrading asset"
        assert crit & set(below_rop.part_number)

    def test_below_rop_is_not_the_whole_catalogue(self, inv, below_rop):
        # A model that simply zeroed every stock level would satisfy "some parts
        # are below ROP"; this pins the healthy majority.
        assert len(below_rop) < 0.25 * len(inv)


# ---------------------------------------------------------------------------
# Aggregate calibration (targets read from stats.json, never restated)
# ---------------------------------------------------------------------------


class TestCalibration:
    def test_mean_stock_level(self, inv):
        assert inv.stock_level.mean() == pytest.approx(INV["stock_mean"], rel=0.05)

    def test_mean_reorder_point(self, inv):
        assert inv.reorder_point_limit.mean() == pytest.approx(INV["rop_mean"], rel=0.05)

    def test_mean_lead_time(self, inv):
        assert inv.lead_time_days.mean() == pytest.approx(INV["lt_mean"], rel=0.05)

    def test_lead_time_range(self, inv):
        assert int(inv.lead_time_days.min()) >= INV["lt_min"]
        assert int(inv.lead_time_days.max()) <= INV["lt_max"]

    def test_price_range_preserved(self, inv):
        assert float(inv.unit_price_usd.min()) == pytest.approx(INV["price_min"])
        assert float(inv.unit_price_usd.max()) == pytest.approx(INV["price_max"])

    def test_mean_price_moves_only_by_the_two_added_rows(self, inv):
        original = _original_inventory()
        expected = (
            original.unit_price_usd.sum() + len(MISSING_SKUS) * MISSING_SKU_PRICE
        ) / (len(original) + len(MISSING_SKUS))
        assert float(inv.unit_price_usd.mean()) == pytest.approx(expected)
        # and it should still be near the profile figure
        assert float(inv.unit_price_usd.mean()) == pytest.approx(
            INV["price_mean"], rel=0.05
        )

    def test_prices_of_existing_parts_untouched(self, inv):
        original = _original_inventory().set_index("part_number").unit_price_usd
        got = inv.set_index("part_number").unit_price_usd.reindex(original.index)
        assert np.allclose(got.to_numpy(), original.to_numpy())


# ---------------------------------------------------------------------------
# Timing against the Task 2 degradation ramp
# ---------------------------------------------------------------------------


class TestRampCoupling:
    def test_ramp_onset_recovered_from_the_series(self):
        """The onset is fitted, not hardcoded; check it lands where Task 2 put it."""
        tel = load_telemetry()
        series = tel[
            (tel.asset_id == DEGRADING_ASSET) & (tel.metric_name == "vibration_hz")
        ]
        end = series.timestamp.max()
        detected = detect_ramp_start(tel)
        # telemetry.RAMP_DAYS == 21; allow a few days of detector slack because
        # the wear envelope starts as a no-op multiplication and is invisible on
        # its first day by construction.
        expected = end - pd.Timedelta(days=21)
        assert abs((detected - expected).total_seconds()) < 5 * 86400
        assert detected < end

    def test_degrading_asset_severity_rises_in_the_ramp(self, ledger):
        sev = ledger.severity[DEGRADING_ASSET]
        rs = ledger.ramp_start_day
        assert sev[:rs].mean() < 1.25
        assert sev[-1] > 2.0

    def test_other_assets_carry_no_material_ramp(self, ledger):
        for asset, sev in ledger.severity.items():
            if asset == DEGRADING_ASSET:
                continue
            assert sev.max() < 1.5, asset

    def test_critical_path_demand_accelerates_inside_the_ramp(self, ledger):
        """Demand for the degrading asset's matched part must rise with the ramp."""
        matched = ledger.matched_parts[DEGRADING_ASSET]
        assert matched, "no catalogue part matches the degrading asset's type"
        for part in matched:
            row = ledger.rows[part]
            assert row["lam_ramp"] > 1.5 * row["lam_pre"], part

    def test_below_rop_critical_path_parts_crossed_inside_the_ramp(self, ledger, below_rop):
        crit = set(critical_path_parts(DEGRADING_ASSET)) & set(below_rop.part_number)
        assert crit
        for part in sorted(crit):
            row = ledger.rows[part]
            assert row["crossing_day"] is not None, part
            assert row["crossing_day"] >= ledger.ramp_start_day, part

    def test_replenishment_lands_after_the_snapshot(self, ledger, below_rop):
        """The stockout is unresolved at the snapshot: stock is on order, not on hand."""
        crit = set(critical_path_parts(DEGRADING_ASSET)) & set(below_rop.part_number)
        for part in sorted(crit):
            row = ledger.rows[part]
            assert row["on_order"] > 0, part

    def test_ledger_conserves_units(self, ledger):
        for part, row in ledger.rows.items():
            assert (
                row["opening"] + row["received"] - row["issued"] == row["stock_level"]
            ), part
            assert row["stock_level"] >= 0, part


# ---------------------------------------------------------------------------
# S08 graph traversal -- the central claim, verified by traversal
# ---------------------------------------------------------------------------


class TestS08Traversal:
    def test_traversal_returns_a_path_to_the_degrading_asset(self, below_rop):
        parts = sorted(below_rop.part_number)
        paths = s08_stockout_exposure(parts, DEGRADING_ASSET)
        assert len(paths) >= 1, (
            f"GRAPH_TABLE over {GRAPH_NAME} returned zero rows for below-ROP parts "
            f"{parts} -> {DEGRADING_ASSET}. A graph query over unmatched tables "
            "succeeds silently, so a zero-row result is a failure, not a pass."
        )
        assert set(paths.asset_id) == {DEGRADING_ASSET}
        assert set(paths.part_number) <= set(parts)

    def test_traversal_reaches_a_critical_rated_asset(self, below_rop):
        paths = s08_stockout_exposure(sorted(below_rop.part_number), DEGRADING_ASSET)
        assert (paths.criticality_rating == "CRITICAL").any()

    def test_traversal_negative_control(self):
        """Proves the traversal filters on its parameter and is not returning
        rows regardless of input."""
        paths = s08_stockout_exposure(["SKU-DOES-NOT-EXIST-000"], DEGRADING_ASSET)
        assert len(paths) == 0

    def test_traversal_asset_filter_is_real(self, below_rop):
        """The same parts must also reach other assets - so a PUMP-104A-only
        result is a filter working, not an artefact of the parts list."""
        parts = sorted(below_rop.part_number)
        everywhere = s08_stockout_exposure(parts, asset_id=None)
        assert len(everywhere) > len(s08_stockout_exposure(parts, DEGRADING_ASSET))
        assert len(set(everywhere.asset_id)) > 1

    def test_end_to_end_stockout_traversal_after_task_8(self, inv):
        """Full in-graph verification, including the below-ROP predicate.

        The property graph's SparePart node table is the *live* inventory_levels,
        which still holds pre-regeneration stock levels until Task 8 loads this
        parquet. Rather than assert against stale data, this test skips with a
        reason until the live table matches the generated frame, at which point
        it becomes an end-to-end check with no Python-side filtering at all.
        """
        from supply_chain import live_inventory, s08_stockout_exposure_in_graph

        live = live_inventory()
        merged = live.merge(inv, on="part_number", suffixes=("_live", "_gen"))
        loaded = len(merged) == len(inv) and (
            merged.stock_level_live.to_numpy() == merged.stock_level_gen.to_numpy()
        ).all()
        if not loaded:
            pytest.skip(
                "live inventory_levels has not been loaded by Task 8 yet; the "
                "property graph still traverses pre-regeneration stock levels"
            )
        paths = s08_stockout_exposure_in_graph(DEGRADING_ASSET)
        assert len(paths) >= 1


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def _regenerate_in_subprocess(tmp_path, hashseed):
    out = tmp_path / f"inv_{hashseed}.parquet"
    env = dict(os.environ, PYTHONHASHSEED=str(hashseed))
    code = (
        "import sys, os;"
        f"sys.path.insert(0, {os.path.dirname(os.path.dirname(os.path.abspath(__file__)))!r});"
        "import supply_chain;"
        f"supply_chain.write_parquet({str(out)!r})"
    )
    subprocess.run(
        [sys.executable, "-c", code], env=env, check=True, cwd=REPO_ROOT,
        capture_output=True,
    )
    return hashlib.md5(out.read_bytes()).hexdigest()


class TestDeterminism:
    def test_identical_output_across_hash_seeds(self, tmp_path):
        a = _regenerate_in_subprocess(tmp_path, 1)
        b = _regenerate_in_subprocess(tmp_path, 424242)
        assert a == b, (
            f"generate_inventory() is not reproducible across processes: "
            f"PYTHONHASHSEED=1 -> {a}, PYTHONHASHSEED=424242 -> {b}. "
            "Per-entity seeds must not depend on Python's salted hash()."
        )

    def test_committed_parquet_matches_regeneration(self, inv):
        path = os.path.join(REPO_ROOT, OUTPUT_PARQUET)
        assert os.path.exists(path), f"{OUTPUT_PARQUET} has not been written"
        on_disk = pd.read_parquet(path)
        pd.testing.assert_frame_equal(
            on_disk.reset_index(drop=True), inv.reset_index(drop=True)
        )

    def test_seed_comes_from_config(self):
        import supply_chain

        assert supply_chain.SEED == SEED
