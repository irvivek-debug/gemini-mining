"""The shipped P5 pack, checked for structure and against the live data."""
from pathlib import Path

import pytest

from mining_agents.method.pack import load_pack
from mining_agents.tools.bq_query import assert_no_interpolation, run_query

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "method" / "p5-geologist.yaml"
TABLES = [
    "mining_data.drill_assay_logs",
    "mining_data.geological_block_models",
    "mining_data.drill_holes",
    "mining_data.metallurgical_recovery",
]


def test_the_shipped_pack_loads():
    pack = load_pack(PACK)
    assert pack.metric == "contained-metal variance between the block model and realised grade"
    assert {d.id for d in pack.drivers} == {
        "model_bias", "bias_by_lithology", "bias_by_depth",
        "bias_by_elevation", "feed_grade_vs_model",
        "tonnage_reconciliation", "qaqc_bias",
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
    assert statuses["tonnage_reconciliation"] == "not_instrumented"
    assert statuses["qaqc_bias"] == "not_instrumented"


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


def test_the_root_does_not_state_the_direction_of_the_variance():
    """The model under-calls in this data. The pack must not say so.

    Writing the direction into the root turns the pack into a precomputed
    report: the agent would carry the answer into the diagnostic instead of
    reading it out of the rows, and on a fork whose model over-calls the pack
    would ship a wrong answer in a YAML file.
    """
    root = load_pack(PACK).root.lower()
    for leak in ("under", "over", "optimistic", "pessimistic", "understate", "overstate"):
        assert leak not in root, root


@pytest.mark.integration
def test_the_model_bias_diagnostic_pairs_samples_to_blocks():
    driver = next(d for d in load_pack(PACK).drivers if d.id == "model_bias")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, TABLES
    )
    assert rows, "the desurvey join returned nothing"
    row = rows[0]
    # The pairing is the whole diagnostic: assert it found the pairs the design
    # was built on, not merely that a query ran.
    assert row["paired_samples"] >= 100, row
    assert row["modelled_grade"] > 0 and row["assayed_grade"] > 0
    # A variance magnitude floor pins the validated result (abs ~0.016 at the
    # design radius). Checking only sign would pass on near-zero variance from
    # 100 random pairs bearing no relation to the design finding. Direction is
    # NOT asserted: on a fork whose model over-calls the sign reverses, and a
    # direction assertion would ship a wrong answer in the test suite.
    assert abs(row["variance"]) >= 0.01, (
        f"variance magnitude {row['variance']:.4f} is below the validated floor; "
        "the desurvey join may have returned pairs that are not the design pairs"
    )


@pytest.mark.integration
def test_the_feed_grade_vs_model_diagnostic_reproduces_the_design_gap():
    """The day count and gap magnitude, not just the sign.

    Checking only that feed_grade differs from model_grade would pass on a query
    that silently dropped 100 days or produced a gap of 0.001 — neither of which
    reproduces the 43.8% gap the design was validated against. The generator is
    seeded and deterministic, so the day count is exactly pinnable. Direction is
    NOT asserted: a fork whose model over-calls would invert the sign, and a
    direction assertion would be a wrong answer shipped in the test suite.
    """
    driver = next(d for d in load_pack(PACK).drivers if d.id == "feed_grade_vs_model")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, TABLES
    )
    assert rows, "feed_grade_vs_model returned nothing"
    row = rows[0]
    # The generator is seeded: 167 days is the complete metallurgical_recovery
    # record. A different count means a row was dropped or duplicated.
    assert row["day_count"] == 167, (
        f"expected 167 days, got {row['day_count']}; the query may be "
        "filtering or duplicating rows"
    )
    # The validated gap is 0.333 (43.8%). A floor of 0.20 is generous enough
    # to survive minor re-seeding while still catching a query returning
    # near-zero variance — which would pass a sign-only assertion.
    assert abs(row["feed_vs_model_variance"]) >= 0.20, (
        f"gap magnitude {row['feed_vs_model_variance']:.4f} is below the validated "
        "floor of 0.20; the diagnostic may not be reading the correct columns"
    )
