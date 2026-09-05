"""The shipped P7 pack, checked for structure and against the live data.

P7 is the Mine Controller — an Optimiser, not a Diagnostician. See
method/p7-mine-controller.yaml's module docstring for how that archetype was
resolved against the same driver-tree schema p1/p2/p3/p5/p6 use.
"""
from pathlib import Path

import pytest

from mining_agents.method.pack import load_pack
from mining_agents.tools.bq_query import assert_no_interpolation, run_query

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "method" / "p7-mine-controller.yaml"
CYCLE_AND_ROUTES = ["mining_data.haul_cycle_log", "mining_data.haulage_routes"]
CYCLE_AND_FLEET = ["mining_data.haul_cycle_log", "mining_data.fleet_vehicles"]


def test_the_shipped_pack_loads():
    pack = load_pack(PACK)
    assert pack.metric == "haul fleet movement rate"
    assert {d.id for d in pack.drivers} == {
        "congestion_cycle_time", "queue_buildup_leading_indicator",
        "payload_utilization", "operator_behaviour_variance",
        "breakdown_reassignment_effectiveness",
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
    assert statuses["operator_behaviour_variance"] == "not_instrumented"
    assert statuses["breakdown_reassignment_effectiveness"] == "not_instrumented"
    assert statuses["congestion_cycle_time"] == "instrumented"
    assert statuses["queue_buildup_leading_indicator"] == "instrumented"
    assert statuses["payload_utilization"] == "instrumented"


def test_no_driver_decides_in_advance_what_its_own_diagnostic_will_show():
    """The pack is a method, not a precomputed report with a chat interface.

    Status is instrumentation. The guard is the caveat the method puts on a
    finding, true before any row is read. Neither may carry the finding
    itself.
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


def test_no_guard_describes_the_data():
    for driver in load_pack(PACK).drivers:
        said = (driver.guard or "").lower()
        assert "in this dataset" not in said, (
            f"{driver.id}: the guard contains 'in this dataset'"
        )


def test_congestion_cycle_time_is_the_one_banded_driver():
    """Pinned here for the same reason test_p6_pack.py pins it: the schema no
    longer requires `compare` on every instrumented driver (bypass-shaped
    drivers count events and compare nothing), so nothing forces the driver
    that DOES compare a controllable choice across bands to declare it.
    """
    compares = {d.id: d.compare for d in load_pack(PACK).drivers}
    assert compares["congestion_cycle_time"] == "setting_band"
    assert compares["queue_buildup_leading_indicator"] is None
    assert compares["payload_utilization"] is None


def test_no_pack_names_a_metal_or_a_dollar_amount():
    text = PACK.read_text().lower()
    for metal in ("copper", "gold", "iron ore", "nickel", "zinc", "lithium"):
        assert metal not in text, f"names a specific commodity {metal!r}"
    assert "$" not in text


def test_no_pack_references_the_data_generator():
    text = PACK.read_text().lower()
    for phrase in ("synthetic data", "data generator", "demo dataset", "demo data"):
        assert phrase not in text, f"references {phrase!r}"


@pytest.mark.integration
def test_congestion_cycle_time_reproduces_the_banded_separation():
    """167 days x 10 routes x 2 halves = 3,340 rows is the whole table; the
    three congestion_ratio bands must partition it exactly, and the
    cycle-time-ratio separation between tight and wide must be an
    operationally meaningful margin rather than a rounding artefact.
    """
    driver = next(
        d for d in load_pack(PACK).drivers if d.id == "congestion_cycle_time"
    )
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, CYCLE_AND_ROUTES
    )
    bands = {r["band"]: r for r in rows}
    assert set(bands) == {"tight", "mid", "wide"}
    assert [bands[b]["halves"] for b in ("tight", "mid", "wide")] == [726, 1695, 919]
    assert sum(b["halves"] for b in bands.values()) == 3340

    assert bands["tight"]["mean_cycle_time_ratio"] < bands["mid"]["mean_cycle_time_ratio"]
    assert bands["mid"]["mean_cycle_time_ratio"] < bands["wide"]["mean_cycle_time_ratio"]
    separation = (
        bands["wide"]["mean_cycle_time_ratio"] - bands["tight"]["mean_cycle_time_ratio"]
    )
    assert separation > 0.20, separation

    # Trip count falls as the congestion band widens — the same half's worth
    # of active haulage minutes buys fewer completed cycles, which is the
    # movement-rate cost this driver's guard requires reporting alongside
    # the cycle-time finding.
    assert bands["wide"]["mean_trip_count"] < bands["tight"]["mean_trip_count"]


@pytest.mark.integration
def test_queue_buildup_leading_indicator_reproduces_the_same_day_persistence():
    """1,670 route-days (10 routes x 167 days) split into am_high / am_normal
    by whether that route-day's AM congestion_ratio cleared the threshold;
    every route-day has both an AM and a PM half, so the two bands must
    partition the full 1,670.
    """
    driver = next(
        d for d in load_pack(PACK).drivers
        if d.id == "queue_buildup_leading_indicator"
    )
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, CYCLE_AND_ROUTES
    )
    bands = {r["am_band"]: r for r in rows}
    assert set(bands) == {"am_high", "am_normal"}
    assert bands["am_high"]["route_days"] == 420
    assert bands["am_normal"]["route_days"] == 1250
    assert sum(b["route_days"] for b in bands.values()) == 1670

    # A route-day whose AM half ran congested shows a materially higher PM
    # cycle-time ratio than one whose AM half did not — the leading
    # indicator this driver exists to surface.
    assert (
        bands["am_high"]["mean_pm_cycle_time_ratio"]
        > bands["am_normal"]["mean_pm_cycle_time_ratio"]
    )
    gap = (
        bands["am_high"]["mean_pm_cycle_time_ratio"]
        - bands["am_normal"]["mean_pm_cycle_time_ratio"]
    )
    assert gap > 0.05, gap


@pytest.mark.integration
def test_payload_utilization_reproduces_the_three_underloaded_routes():
    """Ten routes, one row each; three are deliberately underloaded in the
    generator (see haulage.py's UNDERLOADED_ROUTES) and must show a
    materially lower utilization than the other seven.
    """
    driver = next(
        d for d in load_pack(PACK).drivers if d.id == "payload_utilization"
    )
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, CYCLE_AND_FLEET
    )
    assert len(rows) == 10, f"expected 10 routes, got {len(rows)}"
    by_route = {r["route_id"]: r for r in rows}
    underloaded = {"ROUTE-03", "ROUTE-06", "ROUTE-09"}
    low = sorted(by_route[r]["mean_utilization_pct"] for r in underloaded)
    high = sorted(
        by_route[r]["mean_utilization_pct"]
        for r in by_route if r not in underloaded
    )
    assert max(low) < min(high), (
        f"underloaded routes {low} do not separate from the rest {high}"
    )
    # The gap is large, not a rounding artefact: the lowest underloaded route
    # sits well under 75% while every other route clears 80%.
    assert max(low) < 75.0, low
    assert min(high) > 80.0, high
    for row in rows:
        assert row["halves"] == 334, row  # 167 days x 2 halves, every route
