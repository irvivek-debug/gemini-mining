"""Tests for data/generator/metallurgy.py — Task 3.

Run with:
    python3 -m pytest data/generator/tests/test_metallurgy.py -v

What these tests are actually checking
--------------------------------------
The defect being fixed is that ``metallurgical_recovery.recovery_rate_pct`` was
an *independent* random draw (uniform 88-96, corr with tailings grade +0.07).
It is now a *computed consequence* of the three measured grades via the
two-product formula.

Two traps were deliberately avoided when writing these tests:

* **Circularity in the mass-balance test.**  The test re-derives ``R`` from the
  ``feed_grade_pct`` / ``concentrate_grade_pct`` / ``tailings_grade_pct``
  columns *as read back out of the written parquet* — exactly what a consumer
  joining the table would do — not from any intermediate variable inside the
  generator.  If the generator stored a recovery that disagreed with its own
  stored grades (e.g. by rounding the grades after computing R, or by clipping
  R), this test would fail.

* **Tests that cannot fail.**  Nothing in the generator clips recovery, so the
  band checks are genuine.  ``test_recovery_not_clipped`` guards the converse
  case: a clip would pile rows up on the band edges, so the extremes are
  asserted to be unique and strictly interior.

* **Determinism is checked across processes** with differing ``PYTHONHASHSEED``.
  An in-process double call cannot detect a seed derived from Python's salted
  ``hash()``.

All calibration targets are read from ``config.STATS`` rather than restated as
literals, so the tests fail if the generator drifts from the captured profile.
"""

import hashlib
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data.generator import metallurgy as met  # noqa: E402
from data.generator.config import STATS  # noqa: E402

MET_PATH = REPO_ROOT / "data" / "generated" / "metallurgical_recovery.parquet"
CRU_PATH = REPO_ROOT / "data" / "generated" / "crusher_states.parquet"
TEL_PATH = REPO_ROOT / "data" / "generated" / "telemetry_stream.parquet"

M = STATS["metallurgy"][0]
C = STATS["crusher_states"][0]


# ---------------------------------------------------------------------------
# Fixtures — load the generated parquets once per session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def _generated():
    if not (MET_PATH.exists() and CRU_PATH.exists()):
        met.write_parquet()


@pytest.fixture(scope="session")
def mr(_generated):
    """metallurgical_recovery, time-sorted."""
    return pd.read_parquet(MET_PATH).sort_values("timestamp").reset_index(drop=True)


@pytest.fixture(scope="session")
def cs(_generated):
    """crusher_states, time-sorted."""
    return pd.read_parquet(CRU_PATH).sort_values("timestamp").reset_index(drop=True)


@pytest.fixture(scope="session")
def a5_mask(mr):
    """Boolean mask selecting the A5 excursion window."""
    ts = pd.to_datetime(mr["timestamp"], utc=True)
    return ((ts >= met.A5_START) & (ts <= met.A5_END)).to_numpy()


def two_product_recovery(f, c, t):
    """R = 100 * c * (f - t) / (f * (c - t)) — the two-product formula."""
    return 100.0 * c * (f - t) / (f * (c - t))


# ---------------------------------------------------------------------------
# 1. Schema, shape and grid
# ---------------------------------------------------------------------------

class TestShapeAndSchema:
    def test_row_counts(self, mr, cs):
        assert len(mr) == M["n"], f"metallurgical_recovery: {len(mr)} rows, want {M['n']}"
        assert len(cs) == C["n"], f"crusher_states: {len(cs)} rows, want {C['n']}"

    def test_columns_unchanged(self, mr, cs):
        assert list(mr.columns) == [
            "concentrate_grade_pct", "recovery_rate_pct", "tailings_grade_pct",
            "feed_grade_pct", "concentrator_id", "timestamp",
        ]
        assert list(cs.columns) == [
            "bypass_valve_open", "feed_rate_tph", "gap_size_setting_mm",
            "rotational_torque_nm", "asset_id", "timestamp",
        ]

    def test_entity_ids(self, mr, cs):
        assert set(mr["concentrator_id"]) == {M["conc"]}
        assert set(cs["asset_id"]) == {C["asset"]}

    @pytest.mark.parametrize("name", ["mr", "cs"])
    def test_daily_utc_grid(self, name, mr, cs):
        df = {"mr": mr, "cs": cs}[name]
        ts = pd.to_datetime(df["timestamp"])
        assert ts.notna().all()
        assert str(getattr(ts.dt, "tz", None)) == "UTC", "timestamps must be tz-aware UTC"
        assert ts.min() == pd.Timestamp(M["t0"].replace(" ", "T"))
        assert ts.max() == pd.Timestamp(M["t1"].replace(" ", "T"))
        gaps = np.unique(np.diff(ts.to_numpy()))
        assert gaps.tolist() == [np.timedelta64(1, "D").astype("timedelta64[ns]")]

    def test_no_nulls(self, mr, cs):
        assert not mr.isna().any().any()
        assert not cs.isna().any().any()


# ---------------------------------------------------------------------------
# 2. Mass balance — the headline requirement
# ---------------------------------------------------------------------------

class TestMassBalance:
    """Recovery must be reproducible from the three *stored* grade columns.

    This is the whole point of the task: recovery stops being an independent
    draw and becomes a consequence of the assays.  The recomputation below uses
    only columns read back from the parquet.
    """

    def test_recovery_reproduces_from_stored_grades(self, mr):
        recomputed = two_product_recovery(
            mr["feed_grade_pct"].to_numpy(float),
            mr["concentrate_grade_pct"].to_numpy(float),
            mr["tailings_grade_pct"].to_numpy(float),
        )
        err = np.abs(recomputed - mr["recovery_rate_pct"].to_numpy(float))
        assert err.max() < 0.01, (
            f"mass balance broken: max |recomputed - stored| = {err.max():.5f} pp "
            f"(worst row {int(err.argmax())})"
        )

    def test_recovery_is_not_an_independent_draw(self, mr):
        """A drawn recovery has ~zero residual explanatory power in the grades.

        The original table scored R^2 ~ 0.01 here.  A computed recovery is a
        deterministic function of the grades, so R^2 must be ~1.
        """
        f = mr["feed_grade_pct"].to_numpy(float)
        c = mr["concentrate_grade_pct"].to_numpy(float)
        t = mr["tailings_grade_pct"].to_numpy(float)
        r = mr["recovery_rate_pct"].to_numpy(float)
        resid = r - two_product_recovery(f, c, t)
        r2 = 1.0 - resid.var() / r.var()
        assert r2 > 0.999, f"recovery explained by grades only to R^2={r2:.4f}"


# ---------------------------------------------------------------------------
# 3. Correlations demanded by the brief
# ---------------------------------------------------------------------------

class TestCorrelations:
    def test_recovery_vs_tailings(self, mr):
        rho = float(np.corrcoef(mr["recovery_rate_pct"], mr["tailings_grade_pct"])[0, 1])
        assert rho < -0.6, f"corr(recovery, tailings_grade) = {rho:.4f}, want < -0.6"

    def test_recovery_vs_feed_grade(self, mr):
        rho = float(np.corrcoef(mr["recovery_rate_pct"], mr["feed_grade_pct"])[0, 1])
        assert rho > 0.3, f"corr(recovery, feed_grade) = {rho:.4f}, want > 0.3"


# ---------------------------------------------------------------------------
# 4. Physical plausibility and calibration
# ---------------------------------------------------------------------------

class TestPlausibility:
    def test_recovery_within_hard_band(self, mr):
        r = mr["recovery_rate_pct"]
        assert r.min() >= 85.0 and r.max() <= 97.0, f"recovery range {r.min()}-{r.max()}"

    def test_recovery_within_observed_band(self, mr):
        """Calibration target from the brief: stay inside the observed 88.0-96.0."""
        r = mr["recovery_rate_pct"]
        assert r.min() >= 88.0, f"recovery min {r.min()} below observed 88.0"
        assert r.max() <= 96.0, f"recovery max {r.max()} above observed 96.0"

    def test_recovery_not_clipped(self, mr):
        """A clip would pile several rows onto an identical boundary value."""
        r = mr["recovery_rate_pct"]
        counts = r.value_counts()
        assert counts[r.min()] == 1, "several rows share the minimum recovery (clipped?)"
        assert counts[r.max()] == 1, "several rows share the maximum recovery (clipped?)"
        assert r.min() > 88.0 and r.max() < 96.0, "recovery touches the band edge exactly"

    def test_recovery_mean(self, mr):
        got = float(mr["recovery_rate_pct"].mean())
        assert abs(got - M["r_mean"]) <= 0.3, (
            f"recovery mean {got:.4f}, want {M['r_mean']} +/- 0.3"
        )

    def test_grades_physical(self, mr):
        f = mr["feed_grade_pct"].to_numpy(float)
        c = mr["concentrate_grade_pct"].to_numpy(float)
        t = mr["tailings_grade_pct"].to_numpy(float)
        assert (t > 0).all(), "non-positive tailings grade"
        assert (t < f).all(), "tailings grade >= feed grade (recovery would be <= 0)"
        assert (f < c).all(), "feed grade >= concentrate grade (no upgrade)"
        assert (c < 100).all(), "concentrate grade >= 100 %"

    def test_feed_grade_distribution_held(self, mr):
        f = mr["feed_grade_pct"]
        assert abs(f.mean() - M["f_mean"]) <= 0.03, f"feed grade mean {f.mean():.4f}"
        assert abs(f.std(ddof=1) - M["f_sd"]) <= 0.02, f"feed grade sd {f.std(ddof=1):.4f}"
        assert f.min() >= M["f_min"] - 0.02 and f.max() <= M["f_max"] + 0.02

    def test_concentrate_grade_distribution_held(self, mr):
        c = mr["concentrate_grade_pct"]
        assert abs(c.mean() - M["c_mean"]) <= 0.30, f"conc grade mean {c.mean():.4f}"
        assert abs(c.std(ddof=1) - M["c_sd"]) <= 0.20, f"conc grade sd {c.std(ddof=1):.4f}"
        assert c.min() >= M["c_min"] - 0.20 and c.max() <= M["c_max"] + 0.20

    def test_tailings_tuned_upward(self, mr):
        """The calibration fix: t must sit above its stored distribution.

        Feeding the *stored* means into the two-product formula gives R ~ 94.0
        against a stored mean of 92.21.  Closing that 1.8 pp gap requires the
        tailings distribution to move up; if it has not, the mean recovery test
        can only pass by some other (wrong) route.
        """
        t = mr["tailings_grade_pct"]
        assert t.mean() > M["t_mean"], (
            f"tailings mean {t.mean():.4f} not above the stored {M['t_mean']}"
        )
        assert t.mean() < 4.0 * M["t_mean"], "tailings grade implausibly high"


# ---------------------------------------------------------------------------
# 5. The A5 excursion: gap size -> tailings grade -> recovery
# ---------------------------------------------------------------------------

class TestA5Excursion:
    def test_window_is_a_gap_step_up(self, cs):
        ts = pd.to_datetime(cs["timestamp"], utc=True)
        gap = cs["gap_size_setting_mm"].to_numpy(float)
        idx = int(np.flatnonzero((ts >= met.A5_START).to_numpy())[0])
        assert idx > 0, "A5 window starts on the first day; no step to observe"
        step = gap[idx] - gap[idx - 1]
        assert step >= 5.0, f"gap step into the A5 window is only {step} mm"

    def test_gap_at_maximum_through_window(self, cs):
        ts = pd.to_datetime(cs["timestamp"], utc=True)
        inside = ((ts >= met.A5_START) & (ts <= met.A5_END)).to_numpy()
        gap = cs["gap_size_setting_mm"].to_numpy(float)
        assert (gap[inside] == gap.max()).all(), "gap not held at its maximum in the window"
        assert not (gap[~inside] == gap.max()).any(), (
            "the maximum gap setting also occurs outside the A5 window"
        )

    def test_gap_within_observed_settings(self, cs):
        gap = cs["gap_size_setting_mm"]
        assert gap.min() >= C["gap_min"] and gap.max() <= C["gap_max"]
        assert abs(gap.mean() - C["gap_mean"]) <= 0.5, f"gap mean {gap.mean():.3f}"

    def test_gap_lifts_tailings(self, mr, cs, a5_mask):
        t = mr["tailings_grade_pct"].to_numpy(float)
        lift = t[a5_mask].mean() / t[~a5_mask].mean()
        assert lift >= 1.20, f"tailings lift inside A5 is only x{lift:.3f}"
        rho = float(np.corrcoef(cs["gap_size_setting_mm"], t)[0, 1])
        assert rho > 0.3, f"corr(gap_size, tailings_grade) = {rho:.4f}, want > 0.3"

    def test_tailings_depresses_recovery(self, mr, a5_mask):
        r = mr["recovery_rate_pct"].to_numpy(float)
        drop = r[~a5_mask].mean() - r[a5_mask].mean()
        assert drop >= 1.5, f"recovery drop inside A5 is only {drop:.3f} pp"

    def test_worst_recovery_day_is_inside_the_window(self, mr, a5_mask):
        r = mr["recovery_rate_pct"].to_numpy(float)
        assert a5_mask[int(r.argmin())], (
            "the worst recovery day of the series falls outside the A5 window, "
            "so the excursion is not the dominant event"
        )

    def test_chain_is_traceable_by_a_plain_join(self, mr, cs):
        """S07's discovery path: join on timestamp, group by gap setting.

        Tailings must rise monotonically with gap setting and recovery must fall
        monotonically — no knowledge of the generator required.
        """
        j = cs[["timestamp", "gap_size_setting_mm"]].merge(mr, on="timestamp")
        g = j.groupby("gap_size_setting_mm")[["tailings_grade_pct", "recovery_rate_pct"]].mean()
        g = g.sort_index()
        assert len(g) >= 3, "fewer than three distinct gap settings to compare"
        assert g["tailings_grade_pct"].is_monotonic_increasing, g.to_string()
        assert g["recovery_rate_pct"].is_monotonic_decreasing, g.to_string()


# ---------------------------------------------------------------------------
# 6. Cross-table consistency with telemetry_stream (Task 2)
# ---------------------------------------------------------------------------

class TestTelemetryAgreement:
    """``crusher_states`` is the daily roll-up of the CRUSHER-03 telemetry.

    ``telemetry_stream`` already carries a 2-hourly ``feed_rate_tph`` series for
    CRUSHER-03.  If the daily table disagreed with it, the two tables would
    contradict each other under a trivial join.
    """

    @staticmethod
    def _daily(metric: str) -> pd.Series:
        tel = pd.read_parquet(TEL_PATH)
        sub = tel[(tel["asset_id"] == "CRUSHER-03") & (tel["metric_name"] == metric)].copy()
        sub["day"] = pd.to_datetime(sub["timestamp"], utc=True).dt.floor("D")
        return sub.groupby("day")["metric_value"].mean().sort_index()

    @pytest.mark.parametrize("metric", ["feed_rate_tph", "rotational_torque_nm"])
    def test_daily_mean_matches_telemetry(self, cs, metric):
        daily = self._daily(metric)
        got = cs.set_index(pd.to_datetime(cs["timestamp"], utc=True))[metric]
        assert list(got.index) == list(daily.index), "day grids differ"
        err = np.abs(got.to_numpy(float) - daily.to_numpy(float))
        assert err.max() <= 0.01, (
            f"crusher_states.{metric} disagrees with the CRUSHER-03 telemetry "
            f"daily mean by up to {err.max():.4f}"
        )


# ---------------------------------------------------------------------------
# 7. Determinism across processes
# ---------------------------------------------------------------------------

_CHILD_SCRIPT = textwrap.dedent(
    """
    import hashlib, sys
    from pathlib import Path
    sys.path.insert(0, sys.argv[1])
    from data.generator import metallurgy as met
    out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    met.write_parquet(out_dir=out)
    for name in ("metallurgical_recovery", "crusher_states"):
        print(name, hashlib.md5((out / (name + ".parquet")).read_bytes()).hexdigest())
    """
)


def _generate_in_subprocess(out_dir: Path, hash_seed: str) -> dict:
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = hash_seed
    proc = subprocess.run(
        [sys.executable, "-c", _CHILD_SCRIPT, str(REPO_ROOT), str(out_dir)],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, (
        f"child write_parquet() failed (PYTHONHASHSEED={hash_seed}):\n{proc.stderr}"
    )
    out = {}
    for line in proc.stdout.strip().splitlines():
        parts = line.split()
        if len(parts) == 2 and len(parts[1]) == 32:
            out[parts[0]] = parts[1]
    assert set(out) == {"metallurgical_recovery", "crusher_states"}, proc.stdout
    return out


class TestDeterminism:
    """Two runs must be byte-identical, including across interpreter processes.

    A seed derived from Python's built-in ``hash()`` is salted by
    ``PYTHONHASHSEED`` and therefore differs between processes; calling
    ``write_parquet()`` twice inside one interpreter cannot detect that.
    """

    def test_identical_across_hash_seeds(self, tmp_path):
        a = _generate_in_subprocess(tmp_path / "a", "1")
        b = _generate_in_subprocess(tmp_path / "b", "424242")
        assert a == b, (
            f"not reproducible across processes: PYTHONHASHSEED=1 -> {a}, "
            f"PYTHONHASHSEED=424242 -> {b}"
        )

    def test_committed_parquets_match_regeneration(self, tmp_path, _generated):
        fresh = _generate_in_subprocess(tmp_path / "fresh", "7")
        for name, path in (("metallurgical_recovery", MET_PATH), ("crusher_states", CRU_PATH)):
            committed = hashlib.md5(path.read_bytes()).hexdigest()
            assert fresh[name] == committed, f"data/generated/{name}.parquet is stale"
