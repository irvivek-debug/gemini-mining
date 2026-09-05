"""Tests for data/generator/maintenance.py.

Verifies:
  - corr(repair_cost, actual_duration_hours) in [0.70, 0.90] on the 152-row join
  - repair_cost matches independently computed expected values to the cent, and
    carries no additive noise term
  - mean cost by priority ordered CRITICAL > HIGH > MEDIUM > LOW
  - total spend close to the stats.json figure
  - the 152 logged work orders remain exactly the COMPLETED ones
  - logged durations still hit the stats.json mean/SD calibration
  - the 348 synthetic durations (recovered by inverting the cost formula) are in
    range and reproduce the per-priority moments
  - every log listing replaced parts carries a non-zero parts cost
  - calibration is read from the frozen backup tables, not the live ones
  - deterministic: two runs produce identical output
"""

import os
import sys

# abspath matters: config.py locates data/profile/ relative to its own __file__,
# so an unnormalised ".." on sys.path would send it looking in tests/profile/.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import pytest

from config import BACKUP_SUFFIX, SEED, STATS
from maintenance import (
    CREW_SIZE,
    DUR_MAX,
    DUR_MEAN,
    DUR_MIN,
    DUR_SD,
    LABOUR_RATE,
    MOB_BASE,
    TARGET_TOTAL_SPEND,
    _SOURCE_TABLES,
    compute_parts_cost,
    fit_duration_params,
    duration_sampling_params,
    generate_maintenance_logs,
    generate_work_orders,
    truncated_normal_moments,
    truncated_normal_quantile,
)

# ---------------------------------------------------------------------------
# Tolerances (the targets themselves come from config.STATS — never restated)
# ---------------------------------------------------------------------------
TOTAL_SPEND_TOLERANCE = 0.15  # +/-15%, from the brief
CORR_LOW = 0.70
CORR_HIGH = 0.90
CENT = 0.01

# stats.json stores the duration moments to 3 decimal places.
DURATION_MOMENT_TOLERANCE = 0.01

#: Independently computed expected repair costs.
#:
#: These were derived straight from the brief's formula
#:     150 * crew_size * duration + parts + 150 * crew_size
#: using values read out of the frozen BigQuery backups by hand, *not* by
#: calling anything in maintenance.py.  They pin the cost of one work order for
#: every (priority x parts-count) combination that occurs, including the two
#: SKUs that carry no catalogue price and are valued at the $450 median of the
#: maintenance-consumed catalogue.
EXPECTED_COSTS: list[tuple[str, str, float, float, float]] = [
    # (work_order_id, priority, duration_h, parts_cost, expected_repair_cost)
    ("WO-990004", "LOW", 13.4, 180.00, 4500.00),
    ("WO-990008", "LOW", 3.8, 630.00, 2070.00),
    ("WO-990011", "HIGH", 1.3, 630.00, 2010.00),
    ("WO-990014", "CRITICAL", 12.8, 900.00, 13320.00),
    ("WO-990015", "HIGH", 4.3, 900.00, 4080.00),
    ("WO-990018", "HIGH", 15.7, 1250.00, 11270.00),
    ("WO-990023", "HIGH", 3.8, 0.00, 2880.00),
    ("WO-990032", "MEDIUM", 8.1, 1250.00, 5345.00),
    ("WO-990042", "MEDIUM", 18.3, 0.00, 8685.00),
    ("WO-990075", "MEDIUM", 12.5, 900.00, 6975.00),
    ("WO-990088", "MEDIUM", 4.5, 630.00, 3105.00),
    ("WO-990111", "LOW", 6.3, 900.00, 3090.00),
    ("WO-990144", "CRITICAL", 7.2, 630.00, 8010.00),
    ("WO-990166", "LOW", 18.4, 0.00, 5820.00),
    ("WO-990180", "CRITICAL", 2.4, 1250.00, 4310.00),
    ("WO-990279", "CRITICAL", 11.2, 0.00, 10980.00),
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def generated_data():
    """Generate both tables once and cache for all tests in this module."""
    return generate_work_orders(seed=SEED), generate_maintenance_logs()


@pytest.fixture(scope="module")
def joined(generated_data):
    """152-row join of work orders with maintenance logs."""
    wo, ml = generated_data
    return wo.merge(ml, on="work_order_id", how="inner")


@pytest.fixture(scope="module")
def non_completed(generated_data):
    """The 348 non-COMPLETED work orders with their *implied* duration.

    The duration is recovered by inverting the cost formula, so this exercises
    both the synthetic-duration path and the cost arithmetic for the 70% of
    rows that never appear in the 152-row join.
    """
    wo, ml = generated_data
    logged = set(ml["work_order_id"])
    nc = wo[~wo["work_order_id"].isin(logged)].copy()
    crew = nc["priority"].map(CREW_SIZE)
    parts = nc["work_order_id"].map(compute_parts_cost)
    nc["implied_duration"] = (
        nc["repair_cost"] - parts - MOB_BASE * crew
    ) / (LABOUR_RATE * crew)
    return nc


# ---------------------------------------------------------------------------
# Provenance: calibration must come from the frozen Task-1 backups
# ---------------------------------------------------------------------------

class TestSourceProvenance:
    @pytest.mark.parametrize("key", ["work_orders", "maintenance_logs", "inventory"])
    def test_reads_frozen_backup_not_live_table(self, key):
        """Task 8 overwrites the live tables with this module's own output.

        Reading them back would make the generator consume its own output, so
        every table that Task 8 rewrites must be read from its backup.
        """
        assert _SOURCE_TABLES[key].endswith(BACKUP_SUFFIX), (
            f"{key} reads {_SOURCE_TABLES[key]!r}, which is not a frozen backup"
        )


# ---------------------------------------------------------------------------
# Schema / structure tests
# ---------------------------------------------------------------------------

class TestSchemas:
    def test_work_orders_row_count(self, generated_data):
        wo, _ = generated_data
        assert len(wo) == 500, f"Expected 500 work orders, got {len(wo)}"

    def test_maintenance_logs_row_count(self, generated_data):
        _, ml = generated_data
        assert len(ml) == 152, f"Expected 152 maintenance logs, got {len(ml)}"

    def test_work_orders_columns(self, generated_data):
        wo, _ = generated_data
        expected = {"created_at", "repair_cost", "description", "work_order_id",
                    "priority", "status", "asset_id"}
        assert expected == set(wo.columns), f"Column mismatch: {set(wo.columns)}"

    def test_maintenance_logs_columns(self, generated_data):
        _, ml = generated_data
        expected = {"parts_replaced", "log_entry_id", "actual_duration_hours",
                    "asset_id", "technician_notes", "work_order_id"}
        assert expected == set(ml.columns), f"Column mismatch: {set(ml.columns)}"

    def test_status_mix_unchanged(self, generated_data):
        wo, _ = generated_data
        expected = {row["status"]: row["n"] for row in STATS["workorders_by_status"]}
        assert wo["status"].value_counts().to_dict() == expected


# ---------------------------------------------------------------------------
# Duration calibration (152 logged durations)
# ---------------------------------------------------------------------------

class TestLoggedDurations:
    """Replaces the old range/positivity checks.

    Those asserted ``between(1, 19)`` on a column the generator had just
    clipped to [1, 19], and positivity of a sum of positive terms — neither
    could fail.  The clip is gone; these assert the durations against the
    calibration recorded in stats.json instead.
    """

    def test_duration_mean_matches_stats(self, generated_data):
        _, ml = generated_data
        mean = ml["actual_duration_hours"].mean()
        assert abs(mean - DUR_MEAN) <= DURATION_MOMENT_TOLERANCE, (
            f"Duration mean {mean:.4f} h differs from the stats.json target "
            f"{DUR_MEAN} h by more than {DURATION_MOMENT_TOLERANCE}"
        )

    def test_duration_sd_matches_stats(self, generated_data):
        _, ml = generated_data
        sd = ml["actual_duration_hours"].std(ddof=1)
        assert abs(sd - DUR_SD) <= DURATION_MOMENT_TOLERANCE, (
            f"Duration SD {sd:.4f} h differs from the stats.json target "
            f"{DUR_SD} h by more than {DURATION_MOMENT_TOLERANCE}"
        )

    def test_duration_within_stats_bounds(self, generated_data):
        """No longer tautological — the generator does not clip this column."""
        _, ml = generated_data
        dur = ml["actual_duration_hours"]
        assert dur.between(DUR_MIN, DUR_MAX).all(), (
            f"Duration outside [{DUR_MIN}, {DUR_MAX}]: "
            f"min={dur.min()}, max={dur.max()}"
        )


# ---------------------------------------------------------------------------
# The "152 = COMPLETED" claim
# ---------------------------------------------------------------------------

class TestCompletedAlignment:
    def test_logged_work_orders_are_completed(self, generated_data):
        """All work orders with a maintenance log must have status=COMPLETED."""
        wo, ml = generated_data
        logged_wos = set(ml["work_order_id"])
        statuses = wo[wo["work_order_id"].isin(logged_wos)]["status"]
        assert (statuses == "COMPLETED").all(), \
            f"Non-COMPLETED work orders have logs: {statuses.value_counts().to_dict()}"

    def test_all_completed_have_logs(self, generated_data):
        """Every COMPLETED work order must have exactly one maintenance log."""
        wo, ml = generated_data
        completed_wos = set(wo[wo["status"] == "COMPLETED"]["work_order_id"])
        logged_wos = set(ml["work_order_id"])
        assert completed_wos == logged_wos, \
            f"COMPLETED/logged mismatch: {len(completed_wos)} COMPLETED, {len(logged_wos)} logged"

    def test_join_produces_152_rows(self, joined):
        assert len(joined) == 152, f"Expected 152-row join, got {len(joined)}"


# ---------------------------------------------------------------------------
# Cost / correlation tests
# ---------------------------------------------------------------------------

class TestCostModel:
    def test_correlation_in_band(self, joined):
        """corr(repair_cost, actual_duration_hours) must be in [0.70, 0.90]."""
        corr = joined["repair_cost"].corr(joined["actual_duration_hours"])
        assert CORR_LOW <= corr <= CORR_HIGH, \
            f"Correlation {corr:.4f} not in [{CORR_LOW}, {CORR_HIGH}]"

    def test_priority_ordering(self, generated_data):
        """mean cost: CRITICAL > HIGH > MEDIUM > LOW."""
        wo, _ = generated_data
        means = wo.groupby("priority")["repair_cost"].mean()
        assert means["CRITICAL"] > means["HIGH"], \
            f"CRITICAL mean {means['CRITICAL']:.2f} not > HIGH {means['HIGH']:.2f}"
        assert means["HIGH"] > means["MEDIUM"], \
            f"HIGH mean {means['HIGH']:.2f} not > MEDIUM {means['MEDIUM']:.2f}"
        assert means["MEDIUM"] > means["LOW"], \
            f"MEDIUM mean {means['MEDIUM']:.2f} not > LOW {means['LOW']:.2f}"

    def test_total_spend_close_to_stats(self, generated_data):
        """Total spend within 15% of the stats.json total."""
        wo, _ = generated_data
        total = wo["repair_cost"].sum()
        ratio = abs(total - TARGET_TOTAL_SPEND) / TARGET_TOTAL_SPEND
        assert ratio <= TOTAL_SPEND_TOLERANCE, \
            f"Total spend {total:.2f} deviates {ratio*100:.1f}% from target {TARGET_TOTAL_SPEND:.2f}"

    @pytest.mark.parametrize(
        "work_order_id,priority,duration,parts_cost,expected_cost", EXPECTED_COSTS
    )
    def test_repair_cost_matches_independent_expectation(
        self, generated_data, joined, work_order_id, priority, duration, parts_cost, expected_cost
    ):
        """Cost must equal a value computed outside this module, to the cent.

        The previous version of this test recomputed the cost with the same
        constants and the same ``compute_parts_cost`` the generator uses, so it
        could only show the module agreed with itself.  These figures were
        derived independently from the frozen source tables.
        """
        row = joined[joined["work_order_id"] == work_order_id]
        assert len(row) == 1, f"{work_order_id} missing from the 152-row join"
        row = row.iloc[0]
        assert row["priority"] == priority
        assert abs(row["actual_duration_hours"] - duration) <= CENT
        assert abs(compute_parts_cost(work_order_id) - parts_cost) <= CENT
        assert abs(row["repair_cost"] - expected_cost) <= CENT, (
            f"{work_order_id}: expected {expected_cost:.2f}, "
            f"got {row['repair_cost']:.2f}"
        )

    def test_no_additive_noise_term(self, joined):
        """Cost carries no per-row noise on top of labour + parts + mobilisation.

        Stripping labour and mobilisation must leave only the parts term.  Parts
        cost is discrete (0-2 items drawn from a small catalogue), so a handful
        of distinct residuals is expected; an additive noise term would give a
        different residual on nearly every one of the 152 rows.
        """
        crew = joined["priority"].map(CREW_SIZE)
        residual = (
            joined["repair_cost"]
            - LABOUR_RATE * crew * joined["actual_duration_hours"]
            - MOB_BASE * crew
        ).round(2)
        assert (residual >= -CENT).all(), "Negative parts residual — cost is not additive"
        distinct = sorted(set(residual))
        assert len(distinct) <= 8, (
            f"{len(distinct)} distinct residuals over 152 rows suggests an "
            f"additive noise term: {distinct[:10]}"
        )

    def test_logs_with_parts_have_non_zero_parts_cost(self, generated_data):
        """parts_replaced and repair_cost must not contradict each other.

        A cost-forecasting agent joining parts_replaced -> inventory_levels has
        to reach the same parts bill the cost formula used.  Two SKUs carry no
        catalogue price; before the fallback was added, 26 of the 152 logs listed
        two replaced parts against $0 of parts cost.
        """
        _, ml = generated_data
        offenders = [
            row.work_order_id
            for row in ml.itertuples()
            if len(row.parts_replaced) > 0
            and compute_parts_cost(row.work_order_id) <= 0.0
        ]
        assert not offenders, (
            f"{len(offenders)} logs list replaced parts but carry $0 of parts "
            f"cost, e.g. {offenders[:5]}"
        )


# ---------------------------------------------------------------------------
# Synthetic durations for the 348 non-COMPLETED work orders
# ---------------------------------------------------------------------------

class TestSyntheticDurations:
    """The 348 rows the 152-row join never sees (70% of the table)."""

    def test_covers_all_non_completed_rows(self, non_completed):
        assert len(non_completed) == 348, \
            f"Expected 348 non-COMPLETED work orders, got {len(non_completed)}"

    def test_implied_duration_in_range(self, non_completed):
        """Recovered by inverting the cost formula, so this checks both the
        sampler bounds and the cost arithmetic for these rows."""
        dur = non_completed["implied_duration"]
        assert dur.between(DUR_MIN - CENT, DUR_MAX + CENT).all(), (
            f"Implied duration outside [{DUR_MIN}, {DUR_MAX}]: "
            f"min={dur.min():.3f}, max={dur.max():.3f}"
        )

    @pytest.mark.parametrize("priority", sorted(CREW_SIZE))
    def test_implied_duration_moments_match_fit(self, non_completed, priority):
        """Per-priority mean/SD must reproduce the fitted distribution.

        Tolerances are loose enough to absorb the 0.1 h rounding of the stored
        durations and the fact that a truncated normal on [1, 19] cannot quite
        reach the observed CRITICAL SD of 5.34 h (its ceiling is ~5.2 h), and
        tight enough to fail if the sampler is mis-parameterised: plugging the
        untruncated sample moments straight into the sampler, as the first
        implementation did, put the SD 1.2-1.6 h low.
        """
        mu, sigma = duration_sampling_params()[priority]
        expected_mean, expected_sd = truncated_normal_moments(mu, sigma)
        observed_mean, observed_sd = fit_duration_params()[priority]

        group = non_completed[non_completed["priority"] == priority]["implied_duration"]
        assert abs(group.mean() - expected_mean) <= 0.10, (
            f"{priority}: mean {group.mean():.3f} h vs fitted {expected_mean:.3f} h"
        )
        assert abs(group.std(ddof=1) - expected_sd) <= 0.10, (
            f"{priority}: SD {group.std(ddof=1):.3f} h vs fitted {expected_sd:.3f} h"
        )
        # ... and the fit itself must track the COMPLETED durations it calibrates on.
        assert abs(group.mean() - observed_mean) <= 0.25, (
            f"{priority}: mean {group.mean():.3f} h vs observed {observed_mean:.3f} h"
        )
        assert abs(group.std(ddof=1) - observed_sd) <= 0.45, (
            f"{priority}: SD {group.std(ddof=1):.3f} h vs observed {observed_sd:.3f} h"
        )

    @pytest.mark.parametrize("priority", sorted(CREW_SIZE))
    def test_quantile_clips_at_the_bounds(self, priority):
        """Directly covers the clip guard in truncated_normal_quantile."""
        mu, sigma = duration_sampling_params()[priority]
        assert truncated_normal_quantile(0.0, mu, sigma) == DUR_MIN
        assert truncated_normal_quantile(1.0, mu, sigma) == DUR_MAX


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_two_runs_identical_work_orders(self):
        """Two calls with the same seed must produce identical work orders."""
        wo1 = generate_work_orders(seed=SEED)
        wo2 = generate_work_orders(seed=SEED)
        pd.testing.assert_frame_equal(wo1.reset_index(drop=True), wo2.reset_index(drop=True))

    def test_two_runs_identical_maintenance_logs(self):
        """generate_maintenance_logs takes no seed — it is a pure function of
        the frozen backup table (see its docstring)."""
        ml1 = generate_maintenance_logs()
        ml2 = generate_maintenance_logs()
        pd.testing.assert_frame_equal(ml1.reset_index(drop=True), ml2.reset_index(drop=True))
