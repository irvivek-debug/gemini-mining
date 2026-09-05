"""The shipped P6 pack, checked for structure and against the live data."""
from pathlib import Path

import pytest

from mining_agents.method.pack import load_pack
from mining_agents.tools.bq_query import assert_no_interpolation, run_query

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "method" / "p6-metallurgist.yaml"
BOTH = ["mining_data.metallurgical_recovery", "mining_data.crusher_states"]


def test_the_shipped_pack_loads():
    pack = load_pack(PACK)
    assert pack.metric == "unit cost per tonne of contained metal"
    assert {d.id for d in pack.drivers} == {
        "liberation", "feed_variability", "bypass",
        "reagent_regime", "grind_size_p80",
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
    assert statuses["reagent_regime"] == "not_instrumented"
    assert statuses["grind_size_p80"] == "not_instrumented"
    # bypass has a diagnostic, so it is instrumented. Whether its rows evidence
    # anything is decided when the query runs, not here: this pack was written
    # against one site's 167 days, and on a fork with plenty of bypass events a
    # status of "unevidenced" would be a wrong answer shipped in a YAML file.
    assert statuses["bypass"] == "instrumented"


def test_no_driver_decides_in_advance_what_its_own_diagnostic_will_show():
    """The pack is a method, not a precomputed report with a chat interface.

    Status is instrumentation. The guard is the caveat the method puts on a
    finding — a statement about what a measurement can and cannot establish,
    which is true before any row is read. Neither may carry the finding itself.
    The bypass guard did: "Too few events to support a conclusion is a finding"
    told the agent the count was small before it had counted anything.
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


def test_the_two_banded_drivers_compare_across_a_setting_band():
    """Pinned here because the schema can no longer require it of every driver.

    While `evidenced` implied a comparison, load_pack demanded `compare` on
    every driver carrying SQL. `bypass` counts events and compares nothing, so
    that requirement could not survive the status change — the whitelist still
    refuses an outcome-percentile comparison, but nothing now forces the two
    drivers that DO compare to declare it. This is what makes the shipped pack
    compare against a band the site itself ran rather than its own best days.
    """
    compares = {d.id: d.compare for d in load_pack(PACK).drivers}
    assert compares["liberation"] == "setting_band"
    assert compares["feed_variability"] == "setting_band"


@pytest.mark.integration
def test_the_liberation_diagnostic_reproduces_the_design_finding():
    """The magnitudes, not just the signs.

    Checking only that tight > mid > wide would pass on a query that dropped
    100 days or separated the bands by 0.01 pp — neither of which reproduces
    anything. The generator is seeded and deterministic, so the day counts and
    a floor under the separation are safe to pin, and they are what makes this
    a reproduction rather than a smoke test.
    """
    driver = next(d for d in load_pack(PACK).drivers if d.id == "liberation")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, BOTH
    )
    bands = {r["band"]: r for r in rows}
    assert set(bands) == {"tight", "mid", "wide"}
    # Every day is banded and none is counted twice: the campaign schedule
    # holds one setting per day, so the three counts partition the record.
    assert [bands[b]["days"] for b in ("tight", "mid", "wide")] == [23, 116, 28]
    assert sum(b["days"] for b in bands.values()) == 167
    # Recovery falls monotonically as the gap opens, and by an operationally
    # meaningful margin rather than a rounding artefact.
    assert bands["tight"]["recovery_pct"] > bands["mid"]["recovery_pct"]
    assert bands["mid"]["recovery_pct"] > bands["wide"]["recovery_pct"]
    separation = bands["tight"]["recovery_pct"] - bands["wide"]["recovery_pct"]
    assert separation > 3.0, separation
    # Throughput does not improve when the gap opens — this is what kills the
    # "but you will lose tonnes" objection, so it is a gate.
    assert bands["wide"]["throughput_tph"] <= bands["tight"]["throughput_tph"]


@pytest.mark.integration
def test_the_torque_column_is_named_for_the_daily_mean_it_reports():
    """The pack must not let a daily-mean maximum pass as an instantaneous one.

    crusher_states is a daily roll-up of the 2-hourly telemetry, so a MAX over
    it bounds average duty, not peak duty. An earlier version of this test
    asserted the value sat under the documented 4,500 Nm critical alarm, which
    reads as headroom against that alarm — a claim this table cannot support,
    and one that would silently become false on unrelated data changes. What
    belongs in a pack test is that the column and the guard say what the
    number actually is.
    """
    driver = next(d for d in load_pack(PACK).drivers if d.id == "liberation")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, BOTH
    )
    assert "daily_mean_torque_max_nm" in rows[0]
    assert "torque_max_nm" not in rows[0]
    assert "DAILY MEAN" in driver.guard
    assert "instantaneous" in driver.guard


@pytest.mark.integration
def test_the_setting_effect_survives_the_feed_grade_control():
    driver = next(d for d in load_pack(PACK).drivers if d.id == "feed_variability")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, BOTH
    )
    assert len(rows) == 3
    for row in rows:
        # An empty side makes AVG return NULL, and `None > float` raises
        # TypeError — destroying the assertion message that explains what
        # actually failed. Check the strata are populated first.
        assert row["tight_days"] and row["wide_days"], (
            f"tercile {row['feed_tercile']} has no comparison to make: "
            f"{row['tight_days']} tight days, {row['wide_days']} wide days"
        )
        assert row["recovery_tight"] > row["recovery_wide"], (
            f"tercile {row['feed_tercile']} does not hold; the finding would "
            "be a feed-grade artefact"
        )
        # The residual feed imbalance is what licenses the control. If tight
        # and wide days inside a stratum still differ materially in feed, the
        # stratum has not controlled for feed and the gap is not attributable.
        assert abs(row["feed_tight"] - row["feed_wide"]) < 0.05, (
            f"tercile {row['feed_tercile']} still carries a feed gap of "
            f"{row['feed_tight'] - row['feed_wide']:+.3f}"
        )
