"""The shipped P1 pack, checked for structure and against the live data."""
from pathlib import Path

import pytest

from mining_agents.method.pack import load_pack
from mining_agents.tools.bq_query import assert_no_interpolation, run_query

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "method" / "p1-reliability.yaml"
TABLES = [
    "mining_data.erp_work_orders",
    "mining_data.assets",
    "mining_data.maintenance_logs",
    "mining_data.telemetry_stream",
]


def test_the_shipped_pack_loads():
    pack = load_pack(PACK)
    assert pack.metric == "unplanned repair cost per asset"
    assert {d.id for d in pack.drivers} == {
        "cost_concentration",
        "criticality_load",
        "excursion_rate",
        "repair_duration",
        "condition_precursors",
        "availability",
        "mtbf",
    }


def test_every_named_sql_file_exists():
    for driver in load_pack(PACK).drivers:
        if driver.sql:
            assert (ROOT / "method" / driver.sql).is_file(), driver.sql


def test_every_diagnostic_uses_parameters_not_literals():
    for driver in load_pack(PACK).drivers:
        if driver.sql:
            assert_no_interpolation((ROOT / "method" / driver.sql).read_text())


def test_the_uninstrumented_drivers_are_declared_not_omitted():
    # Dropping them would let the answer imply the tree was fully explored.
    statuses = {d.id: d.status for d in load_pack(PACK).drivers}
    assert statuses["availability"] == "not_instrumented"
    assert statuses["mtbf"] == "not_instrumented"
    # condition_precursors has a diagnostic; whether its bands separate is
    # decided by the rows, not here.
    assert statuses["condition_precursors"] == "instrumented"


def test_no_driver_decides_in_advance_what_its_own_diagnostic_will_show():
    """The pack is a method, not a precomputed report with a chat interface.

    Status is instrumentation. The guard is the caveat the method puts on a
    finding — a statement about what a measurement can and cannot establish,
    which is true before any row is read. Neither may carry the finding itself.
    """
    verdicts = ("too few", "too many", "unevidenced", "no signal", "insufficient")
    for driver in load_pack(PACK).drivers:
        assert driver.status in ("instrumented", "not_instrumented"), driver.id
        said = (driver.guard or "").lower()
        for verdict in verdicts:
            assert verdict not in said, (
                f"{driver.id}: the guard says {verdict!r}, which decides the "
                "diagnostic's result before it runs"
            )


def test_the_precursor_guard_refuses_a_recommendation_the_bands_do_not_support():
    """This driver measures flat in the shipped data.

    That is a finding, not a reason to hide the driver — but an agent that
    reads a flat result and still recommends condition-based intervention has
    invented a relationship. The guard is the only thing standing between the
    two, so its presence is asserted rather than assumed.
    """
    driver = next(d for d in load_pack(PACK).drivers if d.id == "condition_precursors")
    said = (driver.guard or "").lower()
    assert "separation" in said or "separate" in said, driver.guard
    assert "recommend" in said, driver.guard


@pytest.mark.integration
def test_cost_concentration_returns_all_five_assets_and_cost_varies():
    """The magnitudes, not just the ordering.

    Checking only that one asset costs more than another would pass on a query
    that dropped assets or duplicated rows. The generator is seeded: 500 work
    orders across 5 assets is exactly pinnable, and the cost range across assets
    must exceed a meaningful floor to distinguish real concentration from noise.
    """
    driver = next(d for d in load_pack(PACK).drivers if d.id == "cost_concentration")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, TABLES
    )
    # Every asset is represented.
    assert len(rows) == 5, (
        f"expected 5 assets, got {len(rows)}; a row may have been dropped or duplicated"
    )
    # Total work orders across all assets must sum to 500.
    total_wos = sum(r["wo_count"] for r in rows)
    assert total_wos == 500, (
        f"expected 500 work orders, got {total_wos}; "
        "the query may be filtering or duplicating rows"
    )
    # Cost varies across assets by a meaningful amount — not a rounding artefact.
    costs = [r["total_repair_cost"] for r in rows]
    spread = max(costs) - min(costs)
    assert spread > 50_000, (
        f"cost spread of {spread:,.0f} is below the validated floor of 50,000; "
        "the query may not be reading the correct cost column"
    )
    # Each row carries a cost share summing to 100%.
    total_share = sum(r["cost_share_pct"] for r in rows)
    assert abs(total_share - 100.0) < 0.5, (
        f"cost shares sum to {total_share:.1f}%, not 100%"
    )


@pytest.mark.integration
def test_criticality_load_returns_two_tiers_and_critical_dominates():
    """2 rows — one per tier — and the CRITICAL tier carries a validated cost share.

    Checking only that CRITICAL costs more than HIGH would pass on a query that
    dropped one of the three CRITICAL assets or returned a single-row rollup.
    The generator is seeded: 5 assets split 3 CRITICAL / 2 HIGH exactly, and
    the CRITICAL tier carries 64.6% of cost at that split. Pinning the row count
    and a floor under the cost share catches either failure mode; a weaker test
    would not distinguish a dropped asset from a rounding artefact.
    """
    driver = next(d for d in load_pack(PACK).drivers if d.id == "criticality_load")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, TABLES
    )
    assert len(rows) == 2, (
        f"expected 2 criticality tiers, got {len(rows)}; a tier row may have been "
        "dropped or the grouping column differs from the schema"
    )
    tiers = {r["criticality_rating"]: r for r in rows}
    assert set(tiers) == {"CRITICAL", "HIGH"}, (
        f"unexpected tier labels: {set(tiers)}"
    )
    # Asset counts are exactly pinnable: the generator places 3 of 5 in CRITICAL.
    assert tiers["CRITICAL"]["asset_count"] == 3, (
        f"expected 3 CRITICAL assets, got {tiers['CRITICAL']['asset_count']}"
    )
    assert tiers["HIGH"]["asset_count"] == 2, (
        f"expected 2 HIGH assets, got {tiers['HIGH']['asset_count']}"
    )
    # Total work orders across both tiers must sum to 500 (seeded exactly).
    # Note: same work-order population as test_cost_concentration_returns_all_five_assets_and_cost_varies.
    total_wos = tiers["CRITICAL"]["wo_count"] + tiers["HIGH"]["wo_count"]
    assert total_wos == 500, (
        f"expected 500 total WOs, got {total_wos}; a row may be missing or duplicated"
    )
    # CRITICAL cost share floor: validated at 64.6%; floor of 60% tolerates minor
    # re-seeding while catching a dropped asset (which would shift share toward 50%).
    critical_cost = tiers["CRITICAL"]["total_repair_cost"]
    total_cost = critical_cost + tiers["HIGH"]["total_repair_cost"]
    critical_share = critical_cost / total_cost * 100
    assert critical_share >= 60.0, (
        f"CRITICAL cost share {critical_share:.1f}% is below the validated floor of "
        "60%; a CRITICAL asset may have been dropped or miscategorised"
    )


@pytest.mark.integration
def test_repair_duration_returns_all_five_assets_and_log_count_is_exact():
    """152 logs across 5 assets — the generator is seeded so both are pinnable.

    Checking only that mean durations differ across assets would pass on a query
    that silently dropped all logs for one asset (leaving 4 rows) or duplicated
    rows (inflating counts). Pinning the row count and the total log count catches
    either failure. Duration floors anchor that the numeric columns are reading
    actual_duration_hours and not a zero-initialised fallback.
    The column is approx_median_duration_hours (not median_duration_hours) because
    APPROX_QUANTILES is probabilistic; the name is asserted here so that a rename
    back to the unqualified form fails immediately.
    """
    driver = next(d for d in load_pack(PACK).drivers if d.id == "repair_duration")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, TABLES
    )
    assert len(rows) == 5, (
        f"expected 5 assets, got {len(rows)}; an asset may have been dropped "
        "or the join is wrong"
    )
    # Total log count is exactly pinnable: 152 maintenance logs in the seeded dataset.
    total_logs = sum(r["log_count"] for r in rows)
    assert total_logs == 152, (
        f"expected 152 total logs, got {total_logs}; "
        "the query may be filtering or duplicating rows"
    )
    # The column must carry the qualified name that matches the SQL.
    assert "approx_median_duration_hours" in rows[0], (
        "column approx_median_duration_hours not found; the probabilistic-qualifier "
        "rename may have been reverted"
    )
    assert "median_duration_hours" not in rows[0], (
        "the unqualified column name is back; this median is APPROX_QUANTILES, "
        "not an exact median, and the name must say so"
    )
    # Duration floor: the highest mean in the validated data is 11.79h (CRUSHER-03).
    # A floor of 6.0h on the overall max mean catches a query returning near-zero
    # durations from a wrong column without over-fitting to one asset's value.
    means = [r["mean_duration_hours"] for r in rows]
    assert max(means) >= 6.0, (
        f"highest mean duration {max(means):.2f}h is below floor of 6h; "
        "the query may not be reading actual_duration_hours"
    )


@pytest.mark.integration
def test_excursion_rate_covers_all_thirteen_series():
    """13 series, roughly 1,995 rows each — the generator is seeded.

    Checking only that the query runs would pass on a sigma that happens to
    return zero excursions for every series. The row count is the gate: if 13
    series are present and each carries at least 1,990 readings, the join is
    intact.
    """
    driver = next(d for d in load_pack(PACK).drivers if d.id == "excursion_rate")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, TABLES
    )
    assert len(rows) == 13, (
        f"expected 13 series, got {len(rows)}; a metric series may have been "
        "dropped or the group-by is wrong"
    )
    for row in rows:
        assert row["reading_count"] >= 1990, (
            f"{row['asset_id']}/{row['metric_name']}: "
            f"only {row['reading_count']} readings, expected >=1990"
        )
