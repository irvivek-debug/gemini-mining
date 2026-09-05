"""The shipped P3 pack, checked for structure and against the live data."""
from pathlib import Path

import pytest

from mining_agents.method.pack import load_pack
from mining_agents.tools.bq_query import assert_no_interpolation, run_query

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "method" / "p3-hse.yaml"
INCIDENT_TABLES = [
    "mining_data.safety_incidents",
]
FATIGUE_TABLES = [
    "mining_data.biometric_fatigue_logs",
]
RADIO_TABLES = [
    "mining_data.radio_communications",
]


def test_the_shipped_pack_loads():
    pack = load_pack(PACK)
    assert pack.metric == "severity-weighted incident exposure"
    assert {d.id for d in pack.drivers} == {
        "location_concentration",
        "severity_mix",
        "fatigue_exposure",
        "radio_distress",
        "fatigue_to_incident",
        "shift_pattern",
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
    # fatigue_to_incident: only 5 incidents carry an operator link, so
    #   the attributing join does not exist at usable scale.
    # shift_pattern: incident and fatigue timestamps are all 00:00, so no
    #   within-day temporal resolution exists in this corpus.
    statuses = {d.id: d.status for d in load_pack(PACK).drivers}
    assert statuses["fatigue_to_incident"] == "not_instrumented"
    assert statuses["shift_pattern"] == "not_instrumented"
    # location_concentration has a diagnostic; it is instrumented.
    assert statuses["location_concentration"] == "instrumented"


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


def test_no_guard_describes_the_data():
    """A guard describes what a measurement is, not what this corpus contains.

    The phrase 'in this dataset' is the marker of a data-specific claim. A
    guard that uses it is stating something about the rows — a finding — rather
    than about the measurement. Guards must be true before any row is read, so
    they must not contain observations about any particular dataset.

    A future author who needs to write 'in this dataset' should instead state
    the methodological concern (e.g. 'a small cell count must be reported')
    and require the count to be reported — leaving the measurement to decide
    what the count is.
    """
    for driver in load_pack(PACK).drivers:
        said = (driver.guard or "").lower()
        assert "in this dataset" not in said, (
            f"{driver.id}: the guard contains 'in this dataset', which describes "
            "the data rather than the measurement. Guards must be true before any "
            "row is read; state the methodological concern and require the count "
            "to be reported instead."
        )


def test_every_instrumented_driver_guards_the_cell_count():
    """Safety incident corpora in operations of this scale are bounded.

    Any cross-tabulation produces cells small enough that a single event can
    shift a rate materially. Each guard must require the count to be reported
    beside the finding — without saying what the count will be, which the
    verdict test forbids.
    """
    for driver in load_pack(PACK).drivers:
        if driver.status != "instrumented":
            continue
        said = (driver.guard or "").lower()
        assert "count" in said, f"{driver.id}: {driver.guard}"


@pytest.mark.integration
def test_location_concentration_returns_five_locations_with_correct_totals():
    """17/12/12/10/9 across five locations — counts are deterministic for a
    given corpus and are exactly pinnable.

    The query returns one row per (location, severity_level) pair to avoid
    string-literal predicates; 21 rows cover all location-severity combinations.
    Five locations partition all 60 incidents; any location or severity cell
    missing indicates a filter or grouping error. Every row must carry a
    non-null severity_level — the severity breakdown within each location is the
    driver's whole purpose.
    """
    driver = next(d for d in load_pack(PACK).drivers if d.id == "location_concentration")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, INCIDENT_TABLES
    )
    # Every row must carry a non-null severity_level — a query that collapsed
    # to location-only rows would satisfy the location-total assertions but
    # would defeat the entire purpose of this driver.
    for r in rows:
        assert r["severity_level"] is not None, (
            f"row for location {r.get('location_description', '?')} has NULL "
            "severity_level; the query may have dropped the severity grouping"
        )
    assert len(rows) == 21, (
        f"expected 21 (location, severity_level) rows, got {len(rows)}; "
        "a missing row indicates a filter or grouping error"
    )
    # Aggregate to location level from (location, severity_level, count) rows
    from collections import defaultdict
    loc_totals = defaultdict(int)
    for r in rows:
        loc_totals[r["location_description"]] += r["incident_count"]
    assert len(loc_totals) == 5, (
        f"expected 5 locations, got {len(loc_totals)}; a location may be filtered out"
    )
    counts = sorted(loc_totals.values(), reverse=True)
    assert counts == [17, 12, 12, 10, 9], (
        f"expected [17, 12, 12, 10, 9], got {counts}; query may be filtering or mis-grouping"
    )
    total = sum(loc_totals.values())
    assert total == 60, (
        f"expected 60 total incidents, got {total}"
    )


@pytest.mark.integration
def test_severity_mix_returns_all_five_levels_with_correct_counts():
    """HAZARD 16, MTI 14, FATALITY 14, NEAR_MISS 11, LTI 5 — counts are
    deterministic for a given corpus and are exactly pinnable.

    All five severity levels must appear; a missing level or a wrong count
    indicates a grouping error or a filter that excluded a level. The share
    column must sum to 100 (within rounding tolerance).
    """
    driver = next(d for d in load_pack(PACK).drivers if d.id == "severity_mix")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, INCIDENT_TABLES
    )
    assert len(rows) == 5, (
        f"expected 5 severity levels, got {len(rows)}"
    )
    by_level = {r["severity_level"]: r for r in rows}
    assert set(by_level) == {"HAZARD", "MTI", "FATALITY", "NEAR_MISS", "LTI"}, (
        f"unexpected severity labels: {set(by_level)}"
    )
    assert by_level["HAZARD"]["incident_count"] == 16, by_level["HAZARD"]
    assert by_level["MTI"]["incident_count"] == 14, by_level["MTI"]
    assert by_level["FATALITY"]["incident_count"] == 14, by_level["FATALITY"]
    assert by_level["NEAR_MISS"]["incident_count"] == 11, by_level["NEAR_MISS"]
    assert by_level["LTI"]["incident_count"] == 5, by_level["LTI"]
    total_share = sum(r["share_pct"] for r in rows)
    assert abs(total_share - 100.0) < 1.0, (
        f"shares sum to {total_share:.1f}, expected ~100"
    )


@pytest.mark.integration
def test_fatigue_exposure_returns_banded_counts_and_aggregate_metrics():
    """3,340 total logs, 117 alerts; the threshold-banded result must be consistent.

    The total log count across both bands must equal 3,340 (all logs accounted
    for). Alert counts must be non-negative. Mean and max deficit are real
    numbers; the max must exceed the OPS-FMS-001 clause 4.3 cumulative-deficit
    stand-down threshold (6 hours). Each band must report exactly 20 distinct
    operators; both above and below threshold must independently reach that
    count — max() across bands would pass even if one band dropped operators.
    """
    driver = next(d for d in load_pack(PACK).drivers if d.id == "fatigue_exposure")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, FATIGUE_TABLES
    )
    assert len(rows) == 2, (
        f"expected 2 bands (above_threshold and below_threshold), got {len(rows)}"
    )
    by_band = {r["deficit_band"]: r for r in rows}
    assert set(by_band) == {"above_threshold", "below_threshold"}, (
        f"unexpected bands: {set(by_band)}"
    )
    total_logs = sum(r["log_count"] for r in rows)
    assert total_logs == 3340, (
        f"expected 3,340 total fatigue logs across all bands, got {total_logs}"
    )
    total_alerts = sum(r["alert_count"] for r in rows)
    assert total_alerts == 117, (
        f"expected 117 alerts across all bands, got {total_alerts}"
    )
    # Pin the per-band log and alert splits — a query that mis-assigned rows
    # between bands would still satisfy the total assertions.
    assert by_band["above_threshold"]["log_count"] == 1728, (
        f"above_threshold log_count {by_band['above_threshold']['log_count']} != 1728"
    )
    assert by_band["below_threshold"]["log_count"] == 1612, (
        f"below_threshold log_count {by_band['below_threshold']['log_count']} != 1612"
    )
    assert by_band["above_threshold"]["alert_count"] == 115, (
        f"above_threshold alert_count {by_band['above_threshold']['alert_count']} != 115"
    )
    assert by_band["below_threshold"]["alert_count"] == 2, (
        f"below_threshold alert_count {by_band['below_threshold']['alert_count']} != 2"
    )
    # A floor at the clause 4.3 threshold of 6.0 would not discriminate: a
    # deficit column mis-scaled by a factor that returned 6.5 still clears it.
    # The corpus is deterministic, so the observed maximum is pinned instead,
    # and the relationship to the standard is asserted from the pinned value.
    max_deficit = by_band["above_threshold"]["max_sleep_deficit_hours"]
    assert max_deficit == 7.98, (
        f"above_threshold max sleep deficit {max_deficit} != 7.98; the deficit "
        "column may be mis-scaled or rows may have been dropped from the band"
    )
    # Which is what makes this driver worth running: the record reaches past the
    # OPS-FMS-001 clause 4.3 mandatory stand-down threshold of 6 hours.
    assert max_deficit > 6.0
    # The band predicate must actually partition on @deficit_hours. Without
    # this, a CASE that banded on the wrong column would still produce two
    # bands with the right totals.
    assert by_band["below_threshold"]["max_sleep_deficit_hours"] < driver.params[
        "deficit_hours"
    ], (
        f"below_threshold holds a deficit of "
        f"{by_band['below_threshold']['max_sleep_deficit_hours']}, at or above "
        f"the @deficit_hours boundary of {driver.params['deficit_hours']}"
    )
    # Each band must independently report exactly 20 distinct operators.
    # Using max() across bands would pass even if one band dropped to 15.
    assert by_band["above_threshold"]["distinct_operators"] == 20, (
        f"above_threshold distinct_operators "
        f"{by_band['above_threshold']['distinct_operators']} != 20"
    )
    assert by_band["below_threshold"]["distinct_operators"] == 20, (
        f"below_threshold distinct_operators "
        f"{by_band['below_threshold']['distinct_operators']} != 20"
    )


@pytest.mark.integration
def test_radio_distress_returns_total_and_emergency_counts():
    """573 total transmissions, 164 emergency-flagged — counts are deterministic
    for a given corpus and are exactly pinnable.

    The query produces exactly three shift buckets (day / afternoon / night).
    A query whose CASE collapsed every row into a single bucket would pass a
    len >= 1 assertion but would defeat the driver's entire purpose. The total
    across all buckets must equal 573 transmissions and 164 emergency-flagged.
    Per-bucket transmission and emergency counts are also pinned so that a query
    that mis-assigned rows between buckets cannot pass.

    The test verifies that mean_sentiment_score is present for every bucket.
    The query returns only a per-bucket mean over all transmissions in that
    bucket; there is no emergency-only sentiment column, so no cross-bucket
    sentiment comparison is asserted here.
    """
    driver = next(d for d in load_pack(PACK).drivers if d.id == "radio_distress")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, RADIO_TABLES
    )
    assert len(rows) == 3, (
        f"expected exactly 3 shift buckets (day, afternoon, night), got {len(rows)}; "
        "the three-bucket split is the core of this driver — a query that collapsed "
        "buckets would produce a count-of-one that cannot evidence shift concentration"
    )
    by_bucket = {r["shift_bucket"]: r for r in rows}
    assert set(by_bucket) == {"day", "afternoon", "night"}, (
        f"unexpected shift buckets: {set(by_bucket)}"
    )
    # Pin per-bucket transmission and emergency counts so a mis-assignment
    # between buckets cannot pass on totals alone.
    assert by_bucket["day"]["transmission_count"] == 191, (
        f"day transmission_count {by_bucket['day']['transmission_count']} != 191"
    )
    assert by_bucket["afternoon"]["transmission_count"] == 191, (
        f"afternoon transmission_count {by_bucket['afternoon']['transmission_count']} != 191"
    )
    assert by_bucket["night"]["transmission_count"] == 191, (
        f"night transmission_count {by_bucket['night']['transmission_count']} != 191"
    )
    assert by_bucket["day"]["emergency_count"] == 44, (
        f"day emergency_count {by_bucket['day']['emergency_count']} != 44"
    )
    assert by_bucket["afternoon"]["emergency_count"] == 57, (
        f"afternoon emergency_count {by_bucket['afternoon']['emergency_count']} != 57"
    )
    assert by_bucket["night"]["emergency_count"] == 63, (
        f"night emergency_count {by_bucket['night']['emergency_count']} != 63"
    )
    total_transmissions = sum(r["transmission_count"] for r in rows)
    assert total_transmissions == 573, (
        f"expected 573 total transmissions, got {total_transmissions}"
    )
    total_emergency = sum(r["emergency_count"] for r in rows)
    assert total_emergency == 164, (
        f"expected 164 emergency-flagged transmissions, got {total_emergency}"
    )
    # Mean sentiment score must be present for every bucket
    for row in rows:
        assert row["mean_sentiment_score"] is not None, (
            f"bucket {row.get('shift_bucket', '?')} has NULL mean_sentiment_score"
        )
