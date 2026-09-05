"""The shipped P8 pack, checked for structure and against the live data.

P8 is the Shift Supervisor — a Sentinel, not a Diagnostician. See
method/p8-shift-supervisor.yaml's module docstring for how that archetype was
resolved against the same driver-tree schema p1/p2/p3/p5/p6/p7 use.
"""
from pathlib import Path

import pytest

from mining_agents.method.pack import load_pack
from mining_agents.tools.bq_query import assert_no_interpolation, run_query

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "method" / "p8-shift-supervisor.yaml"
FATIGUE_TABLES = ["mining_data.biometric_fatigue_logs"]
SAFETY_TABLES = ["mining_data.safety_incidents"]
RADIO_TABLES = ["mining_data.radio_communications"]
MAINTENANCE_TABLES = ["mining_data.erp_work_orders"]
PRODUCTION_TABLES = ["mining_data.metallurgical_recovery", "mining_data.crusher_states"]


def test_the_shipped_pack_loads():
    pack = load_pack(PACK)
    assert pack.metric == "shift handover risk surface"
    assert {d.id for d in pack.drivers} == {
        "fatigue_signal_shift_delta", "safety_signal_shift_delta",
        "radio_emergency_shift_delta", "maintenance_demand_shift_delta",
        "production_output_shift_delta", "fleet_availability_shift_delta",
        "dispatch_performance_shift_delta",
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
    statuses = {d.id: d.status for d in load_pack(PACK).drivers}
    assert statuses["fleet_availability_shift_delta"] == "not_instrumented"
    assert statuses["dispatch_performance_shift_delta"] == "not_instrumented"
    for instrumented_id in (
        "fatigue_signal_shift_delta", "safety_signal_shift_delta",
        "radio_emergency_shift_delta", "maintenance_demand_shift_delta",
        "production_output_shift_delta",
    ):
        assert statuses[instrumented_id] == "instrumented"


def test_no_driver_decides_in_advance_what_its_own_diagnostic_will_show():
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


def test_every_instrumented_driver_guards_the_cell_count():
    """A Sentinel comparing two 14-day windows hits the same thin-cell
    problem P3's HSE pack documents: any period, especially safety, can be
    small enough that a count must accompany the finding.
    """
    for driver in load_pack(PACK).drivers:
        if driver.status != "instrumented":
            continue
        said = (driver.guard or "").lower()
        assert "count" in said, f"{driver.id}: {driver.guard}"


def test_no_driver_carries_a_setting_band_comparison():
    """A Sentinel is not banding a controllable setting the way the
    Diagnostician and Optimiser packs do — it is reporting whether a
    period-over-period delta exists. None of these seven drivers declares
    `compare`.
    """
    for driver in load_pack(PACK).drivers:
        assert driver.compare is None, (
            f"{driver.id}: carries compare={driver.compare!r}, which a "
            "Sentinel driver should not declare"
        )


def test_no_pack_names_a_metal_or_a_dollar_amount():
    text = PACK.read_text().lower()
    for metal in ("copper", "gold", "iron ore", "nickel", "zinc", "lithium"):
        assert metal not in text, f"names a specific commodity {metal!r}"
    assert "$" not in text


def test_no_pack_references_the_data_generator():
    text = PACK.read_text().lower()
    for phrase in ("synthetic data", "data generator", "demo dataset", "demo data"):
        assert phrase not in text, f"references {phrase!r}"


def _driver(driver_id):
    return next(d for d in load_pack(PACK).drivers if d.id == driver_id)


@pytest.mark.integration
def test_fatigue_signal_shift_delta_reproduces_the_alert_rate_jump():
    """Both 14-day windows carry the same 280 logs (20 operators x 14 days),
    so any alert_count difference is a rate change, not a coverage change —
    and the alert count nearly quadruples between the two windows.
    """
    driver = _driver("fatigue_signal_shift_delta")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, FATIGUE_TABLES
    )
    by_period = {r["period"]: r for r in rows}
    assert set(by_period) == {"recent", "prior"}
    assert by_period["recent"]["log_count"] == 280
    assert by_period["prior"]["log_count"] == 280
    assert by_period["recent"]["distinct_operators"] == 20
    assert by_period["prior"]["distinct_operators"] == 20
    assert by_period["recent"]["alert_count"] == 23, by_period["recent"]
    assert by_period["prior"]["alert_count"] == 6, by_period["prior"]
    assert by_period["recent"]["alert_count"] > 3 * by_period["prior"]["alert_count"]


@pytest.mark.integration
def test_safety_signal_shift_delta_reproduces_the_thin_period_counts():
    driver = _driver("safety_signal_shift_delta")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, SAFETY_TABLES
    )
    recent_total = sum(r["incident_count"] for r in rows if r["period"] == "recent")
    prior_total = sum(r["incident_count"] for r in rows if r["period"] == "prior")
    assert recent_total == 4, recent_total
    assert prior_total == 3, prior_total
    recent_levels = {r["severity_level"] for r in rows if r["period"] == "recent"}
    assert recent_levels == {"HAZARD"}
    prior_levels = {r["severity_level"] for r in rows if r["period"] == "prior"}
    assert prior_levels == {"FATALITY", "HAZARD", "LTI"}


@pytest.mark.integration
def test_radio_emergency_shift_delta_reproduces_the_flat_transmission_volume():
    """Transmission volume is identical across both windows (48 each) while
    the emergency count and sentiment both shift slightly — a case where the
    Sentinel correctly has little to flag, which is itself a valid finding
    this driver must be able to report.
    """
    driver = _driver("radio_emergency_shift_delta")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, RADIO_TABLES
    )
    by_period = {r["period"]: r for r in rows}
    assert by_period["recent"]["transmission_count"] == 48
    assert by_period["prior"]["transmission_count"] == 48
    assert by_period["recent"]["emergency_count"] == 14
    assert by_period["prior"]["emergency_count"] == 16
    for row in rows:
        assert row["mean_sentiment_score"] is not None


@pytest.mark.integration
def test_maintenance_demand_shift_delta_reproduces_the_created_volume_increase():
    driver = _driver("maintenance_demand_shift_delta")
    params = dict(driver.params, high_priority_values=["HIGH", "CRITICAL"])
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), params, MAINTENANCE_TABLES
    )
    by_period = {r["period"]: r for r in rows}
    assert by_period["recent"]["work_order_count"] == 53
    assert by_period["prior"]["work_order_count"] == 44
    assert by_period["recent"]["high_priority_count"] == 25
    assert by_period["prior"]["high_priority_count"] == 19
    assert round(by_period["recent"]["total_repair_cost_usd"], 2) == 324410.0
    assert round(by_period["prior"]["total_repair_cost_usd"], 2) == 260510.0


@pytest.mark.integration
def test_production_output_shift_delta_reproduces_the_flat_series():
    """Recovery and feed rate are both essentially flat between the two
    windows — 14 daily readings each, an honest "nothing material changed"
    finding rather than a manufactured swing.
    """
    driver = _driver("production_output_shift_delta")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, PRODUCTION_TABLES
    )
    by_key = {(r["metric_name"], r["period"]): r for r in rows}
    assert set(by_key) == {
        ("recovery_rate_pct", "recent"), ("recovery_rate_pct", "prior"),
        ("feed_rate_tph", "recent"), ("feed_rate_tph", "prior"),
    }
    for key, row in by_key.items():
        assert row["reading_count"] == 14, (key, row)
    recovery_gap = abs(
        by_key[("recovery_rate_pct", "recent")]["mean_value"]
        - by_key[("recovery_rate_pct", "prior")]["mean_value"]
    )
    assert recovery_gap < 1.0, recovery_gap
