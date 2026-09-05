import math

import pytest
from mining_agents.envelope import Envelope
from mining_agents.tools.operational_math import FORMULAS, operational_math


def test_all_five_formulas_are_present():
    assert set(FORMULAS) == {"rop", "eoq", "cpk", "oee", "littles_law"}


def test_rop_is_demand_times_lead_time_plus_safety_stock():
    env = operational_math("rop", {"avg_daily_demand": 12.0,
                                   "lead_time_days": 7.0,
                                   "safety_stock": 30.0})
    Envelope.model_validate(env)
    assert env["data"]["value"] == pytest.approx(114.0, rel=1e-9)


def test_eoq_matches_the_closed_form():
    env = operational_math("eoq", {"annual_demand": 4380.0,
                                   "order_cost": 250.0,
                                   "holding_cost": 8.0})
    expected = math.sqrt(2 * 4380.0 * 250.0 / 8.0)
    assert env["data"]["value"] == pytest.approx(expected, rel=1e-9)


def test_cpk_takes_the_minimum_of_the_two_one_sided_indices():
    env = operational_math("cpk", {"usl": 110.0, "lsl": 90.0,
                                   "mean": 104.0, "sigma": 2.0})
    # (110-104)/(3*2) = 1.0 ; (104-90)/(3*2) = 2.333 -> min is 1.0
    assert env["data"]["value"] == pytest.approx(1.0, rel=1e-9)


def test_oee_is_the_product_of_its_three_factors():
    env = operational_math("oee", {"availability": 0.90,
                                   "performance": 0.95,
                                   "quality": 0.99})
    assert env["data"]["value"] == pytest.approx(0.90 * 0.95 * 0.99, rel=1e-9)


def test_littles_law_computes_queue_length_from_arrival_rate_and_wait_time():
    env = operational_math("littles_law", {"arrival_rate": 4.0, "wait_time": 2.5})
    assert env["data"]["value"] == pytest.approx(10.0, rel=1e-9)


def test_division_by_zero_is_an_rfc7807_failure_not_a_crash():
    env = operational_math("cpk", {"usl": 110.0, "lsl": 90.0,
                                   "mean": 100.0, "sigma": 0.0})
    Envelope.model_validate(env)
    assert env["success"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


def test_an_unknown_formula_is_refused():
    env = operational_math("astrology", {})
    assert env["success"] is False
    assert env["error"]["code"] == "UNKNOWN_FORMULA"


def test_a_missing_input_names_the_missing_key():
    env = operational_math("eoq", {"annual_demand": 100.0, "order_cost": 5.0})
    assert env["success"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"
    assert "holding_cost" in env["error"]["details"]["missing"]


def test_the_result_reports_the_formula_it_used():
    env = operational_math("oee", {"availability": 1.0, "performance": 1.0,
                                   "quality": 1.0})
    assert env["data"]["formula"] == "oee"
    assert env["data"]["expression"] == "OEE = availability * performance * quality"
