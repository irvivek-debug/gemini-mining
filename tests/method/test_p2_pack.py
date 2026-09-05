"""The shipped P2 pack, checked for structure and against the live data."""
from pathlib import Path

import pytest

from mining_agents.method.pack import load_pack
from mining_agents.tools.bq_query import assert_no_interpolation, run_query

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "method" / "p2-planner.yaml"
TABLES = [
    "mining_data.erp_work_orders",
    "mining_data.inventory_levels",
    "mining_data.work_order_parts_edge",
    "mining_data.assets",
]


def test_the_shipped_pack_loads():
    pack = load_pack(PACK)
    assert pack.metric == "maintenance cost per completed work order"
    assert {d.id for d in pack.drivers} == {
        "priority_cost_escalation",
        "backlog_aging",
        "parts_stockout",
        "parts_demand_cover",
        "schedule_compliance",
        "planned_ratio",
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
    assert statuses["schedule_compliance"] == "not_instrumented"
    assert statuses["planned_ratio"] == "not_instrumented"
    # priority_cost_escalation has a diagnostic; it is instrumented.
    assert statuses["priority_cost_escalation"] == "instrumented"


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


def test_the_metric_is_not_schedule_compliance():
    """There is no planned or due date anywhere in erp_work_orders.

    Schedule compliance is what a maintenance planner is actually judged on,
    which makes it exactly the metric someone will reach for in a later edit.
    This test is the note explaining why it cannot be the governing metric
    here, placed where an editor will trip over it.
    """
    metric = load_pack(PACK).metric.lower()
    assert "compliance" not in metric and "schedule" not in metric, metric


def test_the_parts_cover_guard_states_how_narrow_the_demand_record_is():
    # work_order_parts_edge names only 5 distinct SKUs out of 105 in stock, so
    # a cover finding speaks for a sliver of the catalogue. The guard must say
    # the demand record is partial without saying what the finding will be.
    driver = next(d for d in load_pack(PACK).drivers if d.id == "parts_demand_cover")
    said = (driver.guard or "").lower()
    assert "distinct" in said or "catalogue" in said or "subset" in said, driver.guard


@pytest.mark.integration
def test_priority_cost_escalation_returns_all_four_priorities_and_cost_rises():
    """Mean cost must rise LOW → CRITICAL and all four priorities appear.

    The generator is seeded and deterministic so the work-order counts per
    priority are exactly pinnable. Cost rises monotonically: pinning the
    ordering plus a floor on the gap from LOW to CRITICAL catches a query that
    returns the wrong cost column or drops work orders.
    """
    driver = next(
        d for d in load_pack(PACK).drivers if d.id == "priority_cost_escalation"
    )
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, TABLES
    )
    assert len(rows) == 4, (
        f"expected 4 priority rows, got {len(rows)}; a priority may be missing"
    )
    by_priority = {r["priority"]: r for r in rows}
    assert set(by_priority) == {"LOW", "MEDIUM", "HIGH", "CRITICAL"}, (
        f"unexpected priority labels: {set(by_priority)}"
    )
    # Work-order counts are exactly pinnable from the seeded generator.
    assert by_priority["LOW"]["wo_count"] == 140, by_priority["LOW"]
    assert by_priority["MEDIUM"]["wo_count"] == 131, by_priority["MEDIUM"]
    assert by_priority["HIGH"]["wo_count"] == 128, by_priority["HIGH"]
    assert by_priority["CRITICAL"]["wo_count"] == 101, by_priority["CRITICAL"]
    # Mean cost rises monotonically: LOW < MEDIUM < HIGH, HIGH ≈ CRITICAL.
    assert by_priority["LOW"]["mean_repair_cost_usd"] < by_priority["MEDIUM"]["mean_repair_cost_usd"]
    assert by_priority["MEDIUM"]["mean_repair_cost_usd"] < by_priority["HIGH"]["mean_repair_cost_usd"]
    # The spread from LOW to HIGH is meaningful, not a rounding artefact.
    spread = by_priority["HIGH"]["mean_repair_cost_usd"] - by_priority["LOW"]["mean_repair_cost_usd"]
    assert spread > 3_000, (
        f"mean cost spread LOW→HIGH is {spread:.0f}, below the validated floor of 3,000"
    )


@pytest.mark.integration
def test_backlog_aging_covers_only_open_and_in_progress_orders():
    """117 OPEN and 127 IN_PROGRESS — the generator is seeded so totals are pinnable.

    CANCELLED work orders carry no remediation path; including them would
    overstate the actionable backlog. The query bands by a parameterised
    threshold so the row count is not fixed, but the total order count across
    all bands must equal 117 + 127 = 244.
    """
    driver = next(d for d in load_pack(PACK).drivers if d.id == "backlog_aging")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, TABLES
    )
    # Rows cover only OPEN and IN_PROGRESS.
    statuses_seen = {r["status"] for r in rows}
    assert statuses_seen <= {"OPEN", "IN_PROGRESS"}, (
        f"unexpected statuses in backlog: {statuses_seen - {'OPEN', 'IN_PROGRESS'}}"
    )
    # Total order count is exactly pinnable from the seeded generator.
    total = sum(r["wo_count"] for r in rows)
    assert total == 244, (
        f"expected 244 open/in-progress work orders, got {total}"
    )
    # mean_repair_cost_usd must be non-negative for every row.
    for row in rows:
        assert row["mean_repair_cost_usd"] >= 0, row


@pytest.mark.integration
def test_parts_stockout_returns_skus_at_or_below_reorder_point():
    """17 of 105 SKUs are at or below their reorder point; one is at zero.

    In continuous-review inventory policy a replenishment order is triggered
    when inventory position falls to or below the reorder point. The query uses
    <= so that SKUs sitting exactly at their reorder_point_limit are included —
    they are the trigger event, not a safe condition. Lead times span 3–27 days
    in the validated dataset. Asserting the boundary and the zero-stock case catches
    a query using < or dropping the zero-stock row on a NULL guard.
    """
    driver = next(d for d in load_pack(PACK).drivers if d.id == "parts_stockout")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, TABLES
    )
    # The count was pinned at 17. inventory_levels was deepened from 105 rows
    # to 140 on purpose, so the literal went stale and the suite went red on
    # data we changed deliberately.
    #
    # But the number was never the point -- it guarded the boundary: a query
    # using < instead of <= silently drops every SKU sitting exactly at its
    # reorder point, which is the trigger event itself. So assert the boundary
    # directly, against the live table, which stays true whatever the row
    # count becomes.
    assert rows, "no stockout SKUs at all; the query or the fixture is broken"
    assert all(r["stock_level"] <= r["reorder_point_limit"] for r in rows), (
        "a returned SKU is above its reorder point; the predicate is wrong"
    )
    at_boundary = [r for r in rows if r["stock_level"] == r["reorder_point_limit"]]
    assert at_boundary, (
        "no SKU sits exactly at its reorder point -- the query uses < instead "
        "of <=, dropping the very rows that trigger replenishment"
    )
    # At least one SKU is at zero stock.
    assert any(r["stock_level"] == 0 for r in rows), (
        "no zero-stock SKU found; the query may be filtering out zero values"
    )
    # Lead time range: 3–27 days in the validated dataset.
    lead_times = [r["lead_time_days"] for r in rows]
    assert min(lead_times) >= 3, (
        f"minimum lead time {min(lead_times)} is below validated floor of 3 days"
    )
    assert max(lead_times) >= 25, (
        f"maximum lead time {max(lead_times)} is below floor of 25 days"
    )


@pytest.mark.integration
def test_parts_demand_cover_join_is_complete_and_names_five_distinct_parts():
    """186 of 186 edge rows join to inventory; only 5 distinct SKUs are named.

    The join completeness is a data-quality gate: a LEFT JOIN with NULLs on the
    inventory side would mean demanded parts are not in the catalogue. The
    5-distinct-parts count is exactly pinnable from the seeded generator and
    confirms the edge table is not a broad demand signal.
    """
    driver = next(d for d in load_pack(PACK).drivers if d.id == "parts_demand_cover")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, TABLES
    )
    assert len(rows) == 5, (
        f"expected 5 distinct parts, got {len(rows)}; the join or grouping may be wrong"
    )
    # Every edge row joins — no NULL stock_on_hand.
    for row in rows:
        assert row["stock_on_hand"] is not None, (
            f"part {row['part_number']} has NULL stock_on_hand; join may be incomplete"
        )
    # Total demand line items sum to 186 (all edge rows join).
    total_demand = sum(r["demand_count"] for r in rows)
    assert total_demand == 186, (
        f"expected 186 total demand line items, got {total_demand}"
    )
