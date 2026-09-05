"""Tests for data/generator/fatigue.py — Task 5.

Run with:
    python3 -m pytest data/generator/tests/test_fatigue.py -v

What these tests are actually checking
--------------------------------------
The bug being fixed is *structural*, not marginal: the original
``biometric_fatigue_logs`` had heart rate drawn independently of sleep deficit
(measured corr **-0.116**, physiologically backwards) and no circadian
accumulation.  The marginals were already fine.  So the load-bearing assertions
here are the ones about **joint** and **temporal** structure:

  * ``TestCorrelations``  — sign and magnitude of the two couplings.
  * ``TestCircadian``     — deficit accumulates across a night block and
                            recovers on days off; roster honours the real
                            ``operator_vehicle_assignments`` rows.
  * ``TestA6Case``        — OP-113's deficit trail peaks on the date of the
                            incident BigQuery already links them to.
  * ``TestDeterminism``   — two *separate processes* with different
                            ``PYTHONHASHSEED`` produce byte-identical parquet.

Honesty notes on tests that are weaker than they look
-----------------------------------------------------
* ``test_alert_rate_above_six_hours`` (the >=90% threshold the brief mandates)
  is satisfied by construction: ``fatigue.ALERT_DEFICIT_HOURS`` is the stated
  alert policy, so every row above it alerts.  It is kept because the brief
  requires it, and it *would* fail if the alert column were ever decoupled from
  the deficit column (e.g. by a row-ordering bug in the mirror table).  The
  falsifiable alert tests are ``test_low_deficit_rows_rarely_alert`` and
  ``test_alert_count_near_observed``.
* ``test_heart_rate_marginal`` is near-structural: the generator maps ranks onto
  a two-piece target distribution fitted to the STATS moments, so the moments
  come out right unless the fit or the rounding is wrong.  It is a regression
  guard, not the main evidence.  The main evidence is
  ``test_deficit_heart_rate_correlation``.

Calibration numbers are read from ``config.STATS`` / ``config.SCHEMAS``, never
restated as literals, so recapturing the profile re-tightens the tests.
"""

import ast
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# os.path.abspath, not a bare "..": an unnormalised relative path makes
# config.py look for tests/profile/ and fail.
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GENERATOR_DIR = os.path.abspath(os.path.join(_TESTS_DIR, os.pardir))
_REPO_ROOT = os.path.abspath(os.path.join(_GENERATOR_DIR, os.pardir, os.pardir))
if _GENERATOR_DIR not in sys.path:
    sys.path.insert(0, _GENERATOR_DIR)

import fatigue  # noqa: E402
from config import SCHEMAS, STATS  # noqa: E402

_FATIGUE_STATS = STATS["fatigue"][0]
_BIO_SCHEMA = SCHEMAS["schemas"]["biometric_fatigue_logs"]
_NODE_SCHEMA = SCHEMAS["schemas"]["fatigue_logs_node"]

_GENERATED_DIR = Path(_REPO_ROOT) / "data" / "generated"
_BIO_PARQUET = _GENERATED_DIR / "biometric_fatigue_logs.parquet"
_NODE_PARQUET = _GENERATED_DIR / "fatigue_logs_node.parquet"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def frames():
    """(biometric, node) frames, generating the parquet files if absent."""
    if not (_BIO_PARQUET.exists() and _NODE_PARQUET.exists()):
        fatigue.write_parquet()
    return pd.read_parquet(_BIO_PARQUET), pd.read_parquet(_NODE_PARQUET)


@pytest.fixture(scope="session")
def bio(frames):
    return frames[0]


@pytest.fixture(scope="session")
def node(frames):
    return frames[1]


@pytest.fixture(scope="session")
def a6_path():
    """The operator -> vehicle -> incident path, resolved in BigQuery.

    Queried through ``MiningOperationsSafetyGraph`` so the test proves the
    swarm's canonical traversal really lands on a row, not just that two
    tables happen to share an id.
    """
    return fatigue.resolve_a6_incident()


def _corr(a, b):
    return float(np.corrcoef(np.asarray(a, dtype=float),
                             np.asarray(b, dtype=float))[0, 1])


# ---------------------------------------------------------------------------
# Shape and schema
# ---------------------------------------------------------------------------

class TestShape:

    def test_row_counts_match_profile(self, bio, node):
        assert len(bio) == _BIO_SCHEMA["num_rows"]
        assert len(node) == _NODE_SCHEMA["num_rows"]

    def test_column_order_matches_schema(self, bio, node):
        assert list(bio.columns) == [c["name"] for c in _BIO_SCHEMA["columns"]]
        assert list(node.columns) == [c["name"] for c in _NODE_SCHEMA["columns"]]

    def test_dtypes(self, bio):
        assert pd.api.types.is_integer_dtype(bio["heart_rate_bpm"])
        assert pd.api.types.is_integer_dtype(bio["microsleep_events_detected"])
        assert pd.api.types.is_float_dtype(bio["sleep_deficit_hours"])
        assert pd.api.types.is_bool_dtype(bio["fatigue_alert_triggered"])
        assert pd.api.types.is_datetime64_any_dtype(bio["timestamp"])

    def test_grid_is_complete_and_utc(self, bio):
        n_ops = _FATIGUE_STATS["ops"]
        assert bio["operator_id"].nunique() == n_ops
        assert len(bio) % n_ops == 0
        n_days = len(bio) // n_ops
        assert bio["timestamp"].nunique() == n_days
        ts = bio["timestamp"]
        assert str(ts.dt.tz) == "UTC"
        # daily grain, all rows at midnight
        assert (ts.dt.hour == 0).all()
        assert (ts.dt.minute == 0).all()
        # every operator has exactly one row per day
        assert bio.groupby("operator_id").size().nunique() == 1
        assert not bio.duplicated(subset=["timestamp", "operator_id"]).any()

    def test_window_matches_profile(self, bio):
        assert str(bio["timestamp"].min()) == str(
            pd.Timestamp(_FATIGUE_STATS["t0"]))
        assert str(bio["timestamp"].max()) == str(
            pd.Timestamp(_FATIGUE_STATS["t1"]))

    def test_no_nulls(self, bio, node):
        assert not bio.isna().any().any()
        assert not node.isna().any().any()


# ---------------------------------------------------------------------------
# Marginal calibration
# ---------------------------------------------------------------------------

class TestCalibration:

    def test_sleep_deficit_moments(self, bio):
        sd = bio["sleep_deficit_hours"]
        assert sd.mean() == pytest.approx(_FATIGUE_STATS["sd_mean"], abs=0.05)
        assert sd.std(ddof=1) == pytest.approx(_FATIGUE_STATS["sd_sd"], abs=0.05)

    def test_sleep_deficit_physically_plausible(self, bio):
        sd = bio["sleep_deficit_hours"]
        assert sd.min() >= _FATIGUE_STATS["sd_min"]
        assert sd.max() <= _FATIGUE_STATS["sd_max"]

    def test_heart_rate_marginal(self, bio):
        hr = bio["heart_rate_bpm"]
        assert hr.mean() == pytest.approx(_FATIGUE_STATS["hr_mean"], abs=0.5)
        assert hr.std(ddof=1) == pytest.approx(_FATIGUE_STATS["hr_sd"], abs=0.5)
        assert hr.min() >= _FATIGUE_STATS["hr_min"]
        assert hr.max() <= _FATIGUE_STATS["hr_max"]

    def test_heart_rate_is_stored_as_integer(self, bio, node):
        # the BigQuery column is INTEGER; floats would silently truncate on load
        for frame in (bio, node):
            assert frame["heart_rate_bpm"].dtype.kind == "i"

    def test_microsleep_marginal(self, bio):
        ms = bio["microsleep_events_detected"]
        assert ms.mean() == pytest.approx(_FATIGUE_STATS["ms_mean"], abs=0.02)
        assert ms.min() >= 0
        assert ms.max() <= _FATIGUE_STATS["ms_max"]

    def test_microsleep_is_counts_not_a_constant(self, bio):
        ms = bio["microsleep_events_detected"]
        assert ms.nunique() > 1
        assert (ms > 0).sum() > 0


# ---------------------------------------------------------------------------
# The actual defect being fixed
# ---------------------------------------------------------------------------

class TestCorrelations:

    def test_deficit_heart_rate_correlation(self, bio):
        r = _corr(bio["sleep_deficit_hours"], bio["heart_rate_bpm"])
        assert 0.35 <= r <= 0.55, f"corr(sleep_deficit, heart_rate) = {r:.4f}"

    def test_heart_rate_correlation_sign_is_reversed(self, bio):
        # the original table measured -0.116; anything <= 0 is the old bug
        assert _corr(bio["sleep_deficit_hours"], bio["heart_rate_bpm"]) > 0

    def test_deficit_microsleep_correlation(self, bio):
        r = _corr(bio["sleep_deficit_hours"], bio["microsleep_events_detected"])
        assert 0.40 <= r <= 0.60, f"corr(sleep_deficit, microsleep) = {r:.4f}"

    def test_heart_rate_rises_monotonically_with_deficit(self, bio):
        """Mean HR by deficit quartile must be strictly increasing.

        A correlation coefficient can be dragged into range by a handful of
        extreme rows; this checks the relationship holds across the bulk.
        """
        q = pd.qcut(bio["sleep_deficit_hours"], 4, labels=False,
                    duplicates="drop")
        means = bio.groupby(q)["heart_rate_bpm"].mean().to_numpy()
        assert (np.diff(means) > 0).all(), f"HR by deficit quartile: {means}"

    def test_microsleep_rate_rises_with_deficit(self, bio):
        """Poisson rate must increase with deficit, not merely correlate."""
        hi = bio["sleep_deficit_hours"] > _FATIGUE_STATS["sd_mean"]
        assert (bio.loc[hi, "microsleep_events_detected"].mean()
                > 3 * bio.loc[~hi, "microsleep_events_detected"].mean())


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

class TestAlerts:

    def test_alert_rate_above_six_hours(self, bio):
        """>= 90% of rows with deficit > 6 must carry an alert (brief)."""
        severe = bio[bio["sleep_deficit_hours"] > 6.0]
        assert len(severe) > 0
        assert severe["fatigue_alert_triggered"].mean() >= 0.90

    def test_every_microsleep_row_alerts(self, bio):
        fired = bio["microsleep_events_detected"] > 0
        assert bio.loc[fired, "fatigue_alert_triggered"].all()

    def test_low_deficit_rows_rarely_alert(self, bio):
        """Falsifiable: independent microsleeps would alert ~3% of these."""
        calm = bio[bio["sleep_deficit_hours"] < _FATIGUE_STATS["sd_mean"]]
        assert calm["fatigue_alert_triggered"].mean() < 0.01

    def test_alert_count_near_observed(self, bio):
        observed = _FATIGUE_STATS["alerts"]
        n = int(bio["fatigue_alert_triggered"].sum())
        assert 0.6 * observed <= n <= 1.4 * observed, f"{n} alerts"

    def test_alerting_rows_are_the_fatigued_ones(self, bio):
        alerting = bio.loc[bio["fatigue_alert_triggered"], "sleep_deficit_hours"]
        assert alerting.mean() > 2 * bio["sleep_deficit_hours"].mean()


# ---------------------------------------------------------------------------
# Circadian structure and roster
# ---------------------------------------------------------------------------

class TestCircadian:

    def test_roster_cycle_composition(self):
        """Every operator works 7 day / 2 off / 5 night per 14-day cycle."""
        roster = fatigue.build_roster()
        for op, codes in roster.groupby("operator_id"):
            head = codes.sort_values("timestamp").head(fatigue.ROSTER_CYCLE)
            counts = head["shift_type"].value_counts()
            assert counts.get("DAY", 0) == fatigue.ROSTER_DAY_SHIFTS
            assert counts.get("OFF", 0) == fatigue.ROSTER_OFF_DAYS
            assert counts.get("NIGHT", 0) == fatigue.ROSTER_NIGHT_SHIFTS

    def test_roster_honours_real_assignments(self):
        """The 5 rows in operator_vehicle_assignments are the roster's end state."""
        assignments = STATS["operator_assignments"]
        assert assignments, "profile has no operator_assignments"
        for row in assignments:
            got = fatigue.roster_shift(row["operator_id"],
                                       pd.Timestamp(row["shift_date"], tz="UTC"))
            assert got == row["shift_type"], (
                f"{row['operator_id']} on {row['shift_date']}: "
                f"roster says {got}, assignment says {row['shift_type']}")

    def test_deficit_ordering_night_day_off(self, bio):
        """Night > day > days off.  This is the circadian claim itself."""
        merged = bio.merge(fatigue.build_roster(),
                           on=["operator_id", "timestamp"])
        means = merged.groupby("shift_type")["sleep_deficit_hours"].mean()
        assert means["NIGHT"] > means["DAY"] > means["OFF"], means.to_dict()

    def test_deficit_accumulates_across_consecutive_nights(self, bio):
        """Mean deficit must rise monotonically from night 1 to night 5."""
        merged = bio.merge(fatigue.build_roster(),
                           on=["operator_id", "timestamp"])
        nights = merged[merged["shift_type"] == "NIGHT"]
        means = (nights.groupby("night_index")["sleep_deficit_hours"]
                 .mean().sort_index().to_numpy())
        assert len(means) == fatigue.ROSTER_NIGHT_SHIFTS
        assert (np.diff(means) > 0).all(), f"deficit by night index: {means}"
        assert means[-1] > 2 * means[0]

    def test_days_off_recover(self, bio):
        """Deficit on the last day off is below the last night of the block."""
        merged = bio.merge(fatigue.build_roster(),
                           on=["operator_id", "timestamp"])
        last_night = merged[(merged["shift_type"] == "NIGHT")
                            & (merged["night_index"]
                               == fatigue.ROSTER_NIGHT_SHIFTS - 1)]
        off = merged[merged["shift_type"] == "OFF"]
        assert off["sleep_deficit_hours"].mean() < 0.5 * \
            last_night["sleep_deficit_hours"].mean()

    def test_night_operators_are_a_minority_each_day(self, bio):
        """Roster is staggered — not everyone on nights at once."""
        roster = fatigue.build_roster()
        per_day = (roster[roster["shift_type"] == "NIGHT"]
                   .groupby("timestamp").size())
        n_ops = _FATIGUE_STATS["ops"]
        assert per_day.max() < n_ops
        assert per_day.min() > 0


# ---------------------------------------------------------------------------
# The A6 planted case
# ---------------------------------------------------------------------------

class TestA6Case:

    def test_graph_resolves_operator_to_incident(self, a6_path):
        """MiningOperationsSafetyGraph must return a real incident row."""
        assert a6_path["operator_id"] == fatigue.A6_OPERATOR
        assert a6_path["incident_id"].startswith("INC-")
        assert a6_path["vehicle_id"]
        assert a6_path["incident_timestamp"] is not None

    def test_incident_falls_inside_the_fatigue_window(self, bio, a6_path):
        inc = pd.Timestamp(a6_path["incident_timestamp"])
        assert bio["timestamp"].min() <= inc <= bio["timestamp"].max()

    def test_a6_operator_peaks_on_the_incident_date(self, bio, a6_path):
        trail = bio[bio["operator_id"] == fatigue.A6_OPERATOR]
        peak_ts = trail.loc[trail["sleep_deficit_hours"].idxmax(), "timestamp"]
        assert peak_ts == pd.Timestamp(a6_path["incident_timestamp"])

    def test_a6_deficit_crosses_six_on_consecutive_nights(self, bio, a6_path):
        """Two or more consecutive night shifts above 6 h, ending at the incident."""
        inc = pd.Timestamp(a6_path["incident_timestamp"])
        trail = (bio[bio["operator_id"] == fatigue.A6_OPERATOR]
                 .merge(fatigue.build_roster(), on=["operator_id", "timestamp"])
                 .sort_values("timestamp"))
        run = trail[trail["timestamp"] <= inc].tail(
            fatigue.ROSTER_NIGHT_SHIFTS)
        streak = 0
        for _, r in run.iloc[::-1].iterrows():
            if r["sleep_deficit_hours"] > 6.0 and r["shift_type"] == "NIGHT":
                streak += 1
            else:
                break
        assert streak >= 2, run[["timestamp", "shift_type",
                                 "sleep_deficit_hours"]].to_string()

    def test_a6_trail_is_a_build_up_not_a_spike(self, bio, a6_path):
        """Deficit escalates across the three weeks before the incident.

        A single high row on the incident date would satisfy the peak and
        streak tests above; this one only passes if the trail actually climbs,
        which is what makes the case detectable in advance.
        """
        inc = pd.Timestamp(a6_path["incident_timestamp"])
        trail = bio[bio["operator_id"] == fatigue.A6_OPERATOR]
        window = (trail[(trail["timestamp"] > inc - pd.Timedelta(days=21))
                        & (trail["timestamp"] <= inc)]
                  .sort_values("timestamp")["sleep_deficit_hours"].to_numpy())
        assert len(window) == 21
        first, middle, last = window[:7].mean(), window[7:14].mean(), \
            window[14:].mean()
        assert first < middle < last, (first, middle, last)
        assert last > 2 * first
        # and the whole window sits above the fleet's normal day
        assert window.mean() > 1.3 * bio["sleep_deficit_hours"].mean()

    def test_a6_operator_is_a_night_operator_in_the_source_data(self):
        assignments = {a["operator_id"]: a for a in STATS["operator_assignments"]}
        assert assignments[fatigue.A6_OPERATOR]["shift_type"] == "NIGHT"

    def test_a6_alerts_fire_on_the_incident_date(self, bio, a6_path):
        inc = pd.Timestamp(a6_path["incident_timestamp"])
        row = bio[(bio["operator_id"] == fatigue.A6_OPERATOR)
                  & (bio["timestamp"] == inc)]
        assert len(row) == 1
        assert bool(row["fatigue_alert_triggered"].iloc[0])


# ---------------------------------------------------------------------------
# Mirror table
# ---------------------------------------------------------------------------

class TestMirror:

    def test_node_mirrors_biometric_row_for_row(self, bio, node):
        shared = [c for c in bio.columns if c in node.columns]
        left = bio.sort_values(["timestamp", "operator_id"])[shared] \
                  .reset_index(drop=True)
        right = node.sort_values(["timestamp", "operator_id"])[shared] \
                    .reset_index(drop=True)
        pd.testing.assert_frame_equal(left, right, check_dtype=True)

    def test_log_ids_unique_and_stable(self, node):
        assert node["log_id"].is_unique
        assert node["log_id"].notna().all()
        # log_id is the FatigueLog node key in MiningOperationsSafetyGraph;
        # it must be carried over from the frozen backup, not re-minted.
        original = fatigue.load_grid()
        assert set(node["log_id"]) == set(original["log_id"])

    def test_operators_exist_as_graph_nodes(self, node):
        """FatigueLog -> Operator edge would dangle otherwise."""
        assert set(node["operator_id"]) <= set(fatigue.load_operator_ids())


# ---------------------------------------------------------------------------
# Determinism — must be cross-process, PYTHONHASHSEED is per-interpreter
# ---------------------------------------------------------------------------

_CHILD = """
import hashlib, os, sys
sys.path.insert(0, os.path.abspath(sys.argv[1]))
import fatigue
bio, node = fatigue.generate()
bio.to_parquet(sys.argv[2], index=False)
node.to_parquet(sys.argv[3], index=False)
"""


def _md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def _run_child(hashseed, tmpdir, tag):
    bio_out = os.path.join(tmpdir, f"bio_{tag}.parquet")
    node_out = os.path.join(tmpdir, f"node_{tag}.parquet")
    env = dict(os.environ, PYTHONHASHSEED=hashseed)
    subprocess.run([sys.executable, "-c", _CHILD, _GENERATOR_DIR,
                    bio_out, node_out],
                   env=env, check=True, capture_output=True)
    return _md5(bio_out), _md5(node_out)


class TestDeterminism:

    def test_identical_output_across_processes(self):
        """Two interpreters with different hash salts must agree byte-for-byte.

        An in-process double call cannot detect a seed derived from the salted
        builtin ``hash()`` — the salt is fixed for one interpreter's lifetime.
        """
        with tempfile.TemporaryDirectory() as tmp:
            a = _run_child("0", tmp, "a")
            b = _run_child("12345", tmp, "b")
        assert a == b, f"PYTHONHASHSEED=0 -> {a}, PYTHONHASHSEED=12345 -> {b}"

    def test_module_does_not_seed_from_builtin_hash(self):
        """Guard against the salted builtin that broke Task 2's determinism.

        Parsed rather than grepped so prose in docstrings cannot trip it and,
        more importantly, so an obfuscated call cannot slip past it.
        """
        tree = ast.parse(Path(_GENERATOR_DIR, "fatigue.py").read_text())
        called = {node.func.id for node in ast.walk(tree)
                  if isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Name)}
        assert "hash" not in called
        referenced = {node.id for node in ast.walk(tree)
                      if isinstance(node, ast.Name)}
        assert "hash" not in referenced
