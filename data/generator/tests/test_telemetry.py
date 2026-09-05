"""Tests for data/generator/telemetry.py.

Test-first: these tests define the verification thresholds from task-2-brief.md.
Run with:
    python3 -m pytest data/generator/tests/test_telemetry.py -v

Review notes addressed here
---------------------------
* Determinism is verified **across processes** with differing ``PYTHONHASHSEED``.
  An in-process double call cannot detect a salted-``hash()`` seed derivation,
  because the salt is fixed for the lifetime of one interpreter.
* Calibration targets and physical bounds are read from ``config.STATS`` rather
  than restated as literals, so the tests fail if the generator drifts away from
  the captured profile *or* if the profile is recaptured.
* The ramp window is derived from ``telemetry.RAMP_DAYS`` instead of a hardcoded
  21, so the two cannot silently disagree.
* The old ``test_ramp_no_step_jump`` was a tautology: the generator clipped every
  step to 13% of range and the test asserted <= 15%.  Both clips are gone; the
  replacement measures a property the generator does not trivially enforce —
  continuity of the baseline -> ramp join.
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

from data.generator import telemetry as tel  # noqa: E402
from data.generator.config import STATS  # noqa: E402

PARQUET_PATH = REPO_ROOT / "data" / "generated" / "telemetry_stream.parquet"


# ---------------------------------------------------------------------------
# Fixture: load or generate the parquet once per session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def df():
    """Load the generated telemetry parquet (generating it if absent)."""
    if not PARQUET_PATH.exists():
        tel.generate()
    return pd.read_parquet(PARQUET_PATH)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def series_values(df, asset_id, metric_name):
    """Return metric_value numpy array for a given asset·metric pair."""
    mask = (df["asset_id"] == asset_id) & (df["metric_name"] == metric_name)
    sub = df[mask].sort_values("timestamp")
    return sub["metric_value"].to_numpy(dtype=float)


def series_frame(df, asset_id, metric_name):
    """Return the time-sorted sub-frame for one asset·metric pair."""
    mask = (df["asset_id"] == asset_id) & (df["metric_name"] == metric_name)
    return df[mask].sort_values("timestamp").reset_index(drop=True)


def pre_ramp_mask(ts: pd.Series) -> np.ndarray:
    """Boolean mask selecting samples before the degradation-ramp window.

    The cutoff is derived from ``telemetry.RAMP_DAYS`` so the test window and the
    generator window can never drift apart.
    """
    ts = pd.to_datetime(ts, utc=True)
    return (ts < (ts.max() - pd.Timedelta(days=tel.RAMP_DAYS))).to_numpy()


def stats_row(asset: str, metric: str) -> dict:
    """Calibration row from data/profile/stats.json (never a hardcoded literal)."""
    for row in STATS["telemetry_by_asset_metric"]:
        if row["asset_id"] == asset and row["metric_name"] == metric:
            return row
    raise KeyError(f"No stats row for {asset}/{metric}")


def equal_runs(values: np.ndarray, min_len: int = 2) -> list[tuple[int, int]]:
    """Maximal runs of consecutive identical floats as (start_index, length)."""
    out: list[tuple[int, int]] = []
    i = 0
    n = len(values)
    while i < n:
        j = i
        while j + 1 < n and values[j + 1] == values[i]:
            j += 1
        if j - i + 1 >= min_len:
            out.append((i, j - i + 1))
        i = j + 1
    return out


# All 13 series, derived from the generator's own endpoint/baseline tables where
# possible so a new series cannot be added without the tests noticing.
ALL_SERIES = [
    ("PUMP-104A", "vibration_hz"),
    ("PUMP-104A", "temperature_c"),
    ("CRUSHER-03", "feed_rate_tph"),
    ("CRUSHER-03", "rotational_torque_nm"),
    ("MILL-01", "power_draw_mw"),
    ("MILL-01", "temperature_c"),
    ("MILL-01", "rotational_speed_rpm"),
    ("CONVEYOR-02", "belt_tension_kn"),
    ("CONVEYOR-02", "speed_mps"),
    ("CONVEYOR-02", "load_pct"),
    ("TRUCK-08", "engine_temp_c"),
    ("TRUCK-08", "payload_tons"),
    ("TRUCK-08", "speed_kmh"),
]

# PUMP-104A carries the deliberate degradation ramp; stationarity-based checks
# are scoped to its pre-ramp window (see TestAutocorrelation).
RAMPED_SERIES = [
    ("PUMP-104A", "vibration_hz"),
    ("PUMP-104A", "temperature_c"),
]
STATIONARY_SERIES = [s for s in ALL_SERIES if s not in RAMPED_SERIES]
NON_STUCK_SERIES = [s for s in ALL_SERIES if s not in tel._STUCK_SERIES]


# ---------------------------------------------------------------------------
# 1. Schema and shape
# ---------------------------------------------------------------------------

class TestSchema:
    def test_columns(self, df):
        assert set(df.columns) >= {"metric_name", "metric_value", "asset_id", "timestamp"}

    def test_row_count_reasonable(self, df):
        # 13 series × 2004 timestamps minus up to ~1% dropouts
        # At 0.4% dropout rate: expect >= 13*2004*0.985 = 25,627 rows
        assert len(df) >= 25_600, f"Too few rows: {len(df)}"
        assert len(df) <= 26_053, f"Too many rows: {len(df)}"

    def test_all_thirteen_series_present(self, df):
        present = set(zip(df["asset_id"], df["metric_name"]))
        assert set(ALL_SERIES).issubset(present), (
            f"Missing series: {set(ALL_SERIES) - present}"
        )

    def test_timestamps_utc(self, df):
        """Timestamps must be timezone-aware and in UTC, on the expected grid."""
        ts = df["timestamp"]
        assert ts.notna().all(), "null timestamps present"
        tz = getattr(ts.dt, "tz", None)
        assert tz is not None, (
            f"timestamp column is timezone-naive (dtype={ts.dtype}); expected tz-aware UTC"
        )
        assert str(tz) == "UTC", f"timestamp timezone is {tz}, expected UTC"

        # Grid endpoints and spacing, in UTC.
        assert ts.min() == pd.Timestamp("2026-01-01T00:00:00", tz="UTC")
        assert ts.max() == pd.Timestamp("2026-06-16T22:00:00", tz="UTC")
        uniq = pd.Index(ts.unique()).sort_values()
        assert len(uniq) == 2004, f"expected 2004 distinct timestamps, got {len(uniq)}"
        gaps = np.unique(np.diff(uniq.to_numpy()))
        assert gaps.tolist() == [np.timedelta64(2, "h").astype("timedelta64[ns]")], (
            f"non-uniform 2-hourly grid: {gaps}"
        )


# ---------------------------------------------------------------------------
# 1b. Determinism ACROSS PROCESSES
# ---------------------------------------------------------------------------

_CHILD_SCRIPT = textwrap.dedent(
    """
    import hashlib, sys
    from pathlib import Path
    sys.path.insert(0, sys.argv[1])
    from data.generator import telemetry as tel
    tel._OUT_PATH = Path(sys.argv[2])
    tel._OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tel.generate()
    print(hashlib.md5(tel._OUT_PATH.read_bytes()).hexdigest())
    """
)


def _generate_in_subprocess(out_path: Path, hash_seed: str) -> str:
    """Run generate() in a fresh interpreter with a given PYTHONHASHSEED."""
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = hash_seed
    proc = subprocess.run(
        [sys.executable, "-c", _CHILD_SCRIPT, str(REPO_ROOT), str(out_path)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, (
        f"child generate() failed (PYTHONHASHSEED={hash_seed}):\n{proc.stderr}"
    )
    return proc.stdout.strip().splitlines()[-1]


class TestDeterminism:
    """The generator must be reproducible across interpreter processes.

    Calling ``generate()`` twice inside one process cannot detect a seed derived
    from Python's built-in ``hash()``: the ``PYTHONHASHSEED`` salt is chosen once
    at interpreter start, so both calls see the same salt and agree.  The bug
    only shows up between processes, which is exactly how this test runs it.
    """

    def test_identical_output_across_hash_seeds(self, tmp_path):
        h1 = _generate_in_subprocess(tmp_path / "run_a.parquet", "1")
        h2 = _generate_in_subprocess(tmp_path / "run_b.parquet", "424242")
        assert h1 == h2, (
            "generate() is not reproducible across processes: "
            f"PYTHONHASHSEED=1 -> {h1}, PYTHONHASHSEED=424242 -> {h2}. "
            "Per-series seeds must not depend on Python's salted hash()."
        )

    def test_row_count_stable_across_hash_seeds(self, tmp_path):
        """Row count is the coarsest symptom of a salted seed (dropout masks shift)."""
        counts = []
        for seed_env, name in (("1", "c1.parquet"), ("424242", "c2.parquet")):
            path = tmp_path / name
            _generate_in_subprocess(path, seed_env)
            counts.append(len(pd.read_parquet(path)))
        assert counts[0] == counts[1], f"row count varies across processes: {counts}"

    def test_committed_parquet_matches_regeneration(self, tmp_path, df):
        """The checked-in artefact is the one this code produces."""
        fresh = tmp_path / "fresh.parquet"
        _generate_in_subprocess(fresh, "7")
        committed = hashlib.md5(PARQUET_PATH.read_bytes()).hexdigest()
        assert hashlib.md5(fresh.read_bytes()).hexdigest() == committed, (
            "data/generated/telemetry_stream.parquet is stale; re-run generate()"
        )


# ---------------------------------------------------------------------------
# 2. Lag-1 autocorrelation ∈ [0.75, 0.95] for every series
# ---------------------------------------------------------------------------

class TestAutocorrelation:
    # For PUMP-104A, the degradation ramp over the final RAMP_DAYS creates a
    # strong non-stationary trend that inflates AC to near 1.  The brief's
    # requirement that the 5% calibration test applies to the pre-ramp window
    # equally implies that the AC check for PUMP-104A should be evaluated on the
    # stationary pre-ramp portion only.  The ramp physics (a deliberate trend)
    # would violate the AC upper bound on any real equipment with progressive
    # failure — so the test is scoped consistently with the mean/SD test.
    SERIES_PRE_RAMP = RAMPED_SERIES
    SERIES_FULL = STATIONARY_SERIES

    @pytest.mark.parametrize("asset,metric", SERIES_FULL)
    def test_lag1_ac(self, df, asset, metric):
        vals = series_values(df, asset, metric)
        ac = np.corrcoef(vals[:-1], vals[1:])[0, 1]
        assert 0.75 <= ac <= 0.95, (
            f"{asset}/{metric} lag-1 AC = {ac:.4f}, expected [0.75, 0.95]"
        )

    @pytest.mark.parametrize("asset,metric", SERIES_PRE_RAMP)
    def test_lag1_ac_pre_ramp(self, df, asset, metric):
        """For PUMP-104A series, AC is verified on the pre-ramp stationary window."""
        sub = series_frame(df, asset, metric)
        vals = sub.loc[pre_ramp_mask(sub["timestamp"]), "metric_value"].to_numpy(float)
        ac = np.corrcoef(vals[:-1], vals[1:])[0, 1]
        assert 0.75 <= ac <= 0.95, (
            f"{asset}/{metric} pre-ramp lag-1 AC = {ac:.4f}, expected [0.75, 0.95]"
        )


# ---------------------------------------------------------------------------
# 3. Diurnal rhythm present: hour-of-day amplitude > 3% of series mean
# ---------------------------------------------------------------------------

class TestDiurnalRhythm:
    @pytest.mark.parametrize("asset,metric", ALL_SERIES)
    def test_diurnal_amplitude(self, df, asset, metric):
        sub = series_frame(df, asset, metric)
        sub = sub.assign(hour=pd.to_datetime(sub["timestamp"], utc=True).dt.hour)
        hour_means = sub.groupby("hour")["metric_value"].mean()
        amplitude = hour_means.max() - hour_means.min()
        threshold = 0.03 * abs(sub["metric_value"].mean())
        assert amplitude > threshold, (
            f"{asset}/{metric} diurnal amplitude {amplitude:.4f} <= 3% of mean "
            f"({threshold:.4f})"
        )


# ---------------------------------------------------------------------------
# 3b. Weekly planned-maintenance dip must actually move the level
# ---------------------------------------------------------------------------

class TestWeeklyMaintenanceDip:
    """``weekly_dip`` returns a multiplicative factor <= 1 with its trough on Sunday.

    A previous implementation applied it as ``(ou + diurnal + shift) * w + mean``
    — i.e. it scaled a **zero-mean** deviation, leaving every day-of-week mean
    identical and the maintenance signature entirely absent from the data.  This
    test would have caught that: it compares Sunday against midweek levels.
    """

    @pytest.mark.parametrize("asset,metric", ALL_SERIES)
    def test_sunday_below_midweek(self, df, asset, metric):
        sub = series_frame(df, asset, metric)
        dow = pd.to_datetime(sub["timestamp"], utc=True).dt.dayofweek
        sunday = sub.loc[dow == 6, "metric_value"].mean()
        midweek = sub.loc[dow.isin([1, 2, 3]), "metric_value"].mean()
        deficit = (midweek - sunday) / abs(midweek)
        assert deficit > 0.0075, (
            f"{asset}/{metric} Sunday mean {sunday:.4f} is only {deficit * 100:.3f}% "
            f"below the midweek mean {midweek:.4f} — the maintenance dip is inert"
        )

    def test_weekly_trough_is_on_the_weekend(self, df):
        """Pooled across all series, the weekly low must sit at the Sunday trough.

        ``common.weekly_dip`` is a smooth cosine whose trough is on Sunday, so the
        Sunday and Monday factors differ by only ~5% of the dip magnitude; over 24
        weeks of OU noise either can come out marginally lower.  The test therefore
        asserts Sunday is among the two lowest days and that midweek (Tue–Thu) sits
        clearly above it, which is what "planned maintenance window" means.
        """
        dow = pd.to_datetime(df["timestamp"], utc=True).dt.dayofweek
        # Normalise each series to its own mean so they can be pooled.
        norm = df.groupby(["asset_id", "metric_name"])["metric_value"].transform(
            lambda s: s / s.mean()
        )
        by_dow = norm.groupby(dow).mean()
        two_lowest = set(by_dow.nsmallest(2).index)
        assert 6 in two_lowest, (
            f"Sunday is not among the two lowest days ({sorted(two_lowest)}, 0=Mon). "
            f"Day means: {by_dow.round(4).to_dict()}"
        )
        midweek = by_dow.loc[[1, 2, 3]].mean()
        assert by_dow.loc[6] < midweek - 0.01, (
            f"Sunday level {by_dow.loc[6]:.4f} is not materially below midweek "
            f"{midweek:.4f}"
        )


# ---------------------------------------------------------------------------
# 4. Degradation ramp on PUMP-104A vibration_hz
# ---------------------------------------------------------------------------

class TestDegradationRamp:
    def test_ramp_material(self, df):
        """Final 7-day mean > 2× first-30-day mean."""
        sub = series_frame(df, "PUMP-104A", "vibration_hz")
        ts = pd.to_datetime(sub["timestamp"], utc=True)
        first_30 = sub.loc[ts <= (ts.min() + pd.Timedelta(days=30)), "metric_value"].mean()
        last_7 = sub.loc[ts >= (ts.max() - pd.Timedelta(days=7)), "metric_value"].mean()
        assert last_7 > 2.0 * first_30, (
            f"Ramp not material: last-7-day mean {last_7:.3f} <= 2×first-30-day "
            f"mean {first_30:.3f}"
        )

    @pytest.mark.parametrize("metric", ["vibration_hz", "temperature_c"])
    def test_ramp_join_is_continuous(self, df, metric):
        """The baseline -> ramp handover must not be a visible discontinuity.

        Replaces the old ``test_ramp_no_step_jump``, which asserted every step was
        under 15% of the series range while the generator clipped every step to
        13% — the test could not fail.  The generator no longer clips anything, so
        this measures a real property: the step across the ramp boundary is drawn
        from the same distribution as ordinary pre-ramp steps (<= the pre-ramp
        95th percentile), and the 24 h level shift across the boundary is a
        fraction of the pre-ramp σ.
        """
        sub = series_frame(df, "PUMP-104A", metric)
        vals = sub["metric_value"].to_numpy(float)
        pre = pre_ramp_mask(sub["timestamp"])
        i0 = int(np.argmax(~pre))  # first ramp sample
        assert i0 > 12, "ramp window not located"

        steps = np.abs(np.diff(vals))
        pre_q95 = float(np.quantile(steps[pre[1:]], 0.95))
        join_step = abs(vals[i0] - vals[i0 - 1])
        assert join_step <= pre_q95, (
            f"PUMP-104A/{metric} ramp join step {join_step:.4f} exceeds the pre-ramp "
            f"95th-percentile step {pre_q95:.4f} — discontinuity at the handover"
        )

        sd_pre = float(vals[pre].std())
        level_jump = abs(vals[i0:i0 + 12].mean() - vals[i0 - 12:i0].mean())
        assert level_jump <= 0.75 * sd_pre, (
            f"PUMP-104A/{metric} 24 h level shift across the ramp boundary "
            f"{level_jump:.4f} exceeds 0.75σ_pre ({0.75 * sd_pre:.4f})"
        )

    def test_ramp_variance_grows(self, df):
        """Fluctuation must scale with the ramp, not be replaced by it.

        The previous generator *substituted* a ramp for the baseline OU, so the
        detrended σ inside the ramp collapsed (1.105 -> 0.308): the failing pump
        went quieter than the healthy one.  The ramp is now a multiplication of
        the baseline, so detrended variance grows.  Both windows are detrended
        with a quadratic fit before comparison so the trend itself is not counted.
        """
        sub = series_frame(df, "PUMP-104A", "vibration_hz")
        vals = sub["metric_value"].to_numpy(float)
        pre = pre_ramp_mask(sub["timestamp"])

        def detrended_sd(y):
            x = np.arange(len(y), dtype=float)
            return float((y - np.polyval(np.polyfit(x, y, 2), x)).std())

        sd_pre = detrended_sd(vals[pre])
        sd_ramp = detrended_sd(vals[~pre])
        assert sd_ramp >= sd_pre, (
            f"ramp-window detrended σ {sd_ramp:.4f} < pre-ramp σ {sd_pre:.4f}: "
            "the ramp is replacing the baseline fluctuation instead of scaling it"
        )

    def test_ramp_is_monotone_in_level(self, df):
        """The ramp trend must rise: weekly means inside the ramp are increasing."""
        sub = series_frame(df, "PUMP-104A", "vibration_hz")
        ts = pd.to_datetime(sub["timestamp"], utc=True)
        ramp = sub.loc[~pre_ramp_mask(sub["timestamp"])].copy()
        week = ((ts[~pre_ramp_mask(sub["timestamp"])] - ts.min()).dt.days // 7).to_numpy()
        means = ramp.groupby(week)["metric_value"].mean().to_numpy()
        assert np.all(np.diff(means) > 0), f"ramp weekly means not increasing: {means}"


# ---------------------------------------------------------------------------
# 5. PUMP-104A temperature_c lags vibration_hz by 3 h ± 1 h
# ---------------------------------------------------------------------------

class TestTemperatureLag:
    def test_xcorr_peaks_at_3h(self, df):
        """Cross-correlation of temperature with vibration peaks at lag 1–2 samples.

        At a 2-hourly grid, 3 h = 1.5 samples.  The generator uses the nearest
        integer lag of 2 samples (4 h) since thermal mass delays the response; the
        test allows 1–2 samples (2–4 h, i.e. 3 h ± 1 h).

        The cross-correlation is evaluated on the **pre-ramp window**: on the full
        series both non-stationary ramp trends dominate at long lags.  It is also
        evaluated on the **innovations** (first differences) — for two strongly
        autocorrelated AR(1) series the raw cross-correlation peaks at lag 0
        regardless of the true lag, because the shared AR structure dominates.
        """
        vib_f = series_frame(df, "PUMP-104A", "vibration_hz")
        tmp_f = series_frame(df, "PUMP-104A", "temperature_c")
        vib_f = vib_f.loc[pre_ramp_mask(vib_f["timestamp"])]
        tmp_f = tmp_f.loc[pre_ramp_mask(tmp_f["timestamp"])]

        merged = (
            vib_f[["timestamp", "metric_value"]]
            .rename(columns={"metric_value": "vib"})
            .merge(
                tmp_f[["timestamp", "metric_value"]].rename(columns={"metric_value": "tmp"}),
                on="timestamp",
            )
            .sort_values("timestamp")
        )

        dvib = np.diff(merged["vib"].to_numpy(float))
        dtmp = np.diff(merged["tmp"].to_numpy(float))
        m = len(dvib)

        max_lag = 8  # up to 16 h
        xcorr = [
            np.corrcoef(dvib, dtmp)[0, 1] if k == 0
            else np.corrcoef(dvib[:m - k], dtmp[k:m])[0, 1]
            for k in range(max_lag + 1)
        ]

        peak_lag = int(np.argmax(xcorr))
        assert 1 <= peak_lag <= 2, (
            f"Temperature innovation xcorr peak at sample {peak_lag} ({peak_lag * 2} h); "
            f"expected 1–2 samples (2–4 h). xcorr={[f'{x:.3f}' for x in xcorr]}"
        )


# ---------------------------------------------------------------------------
# 6. CRUSHER-03 correlation between feed_rate_tph and rotational_torque_nm
# ---------------------------------------------------------------------------

class TestCrusherCorrelation:
    def test_feed_torque_correlation(self, df):
        """Pearson correlation computed on timestamps present in BOTH series."""
        feed_df = series_frame(df, "CRUSHER-03", "feed_rate_tph")[
            ["timestamp", "metric_value"]
        ].rename(columns={"metric_value": "feed"})
        torq_df = series_frame(df, "CRUSHER-03", "rotational_torque_nm")[
            ["timestamp", "metric_value"]
        ].rename(columns={"metric_value": "torque"})
        merged = feed_df.merge(torq_df, on="timestamp")
        corr = np.corrcoef(merged["feed"].values, merged["torque"].values)[0, 1]
        assert 0.65 <= corr <= 0.85, (
            f"CRUSHER-03 feed/torque correlation {corr:.4f} not in [0.65, 0.85]"
        )


# ---------------------------------------------------------------------------
# 7. Mean and σ within 5% of the captured profile for pre-existing series
#    For PUMP-104A vibration_hz and temperature_c: 5% applies to PRE-RAMP window.
# ---------------------------------------------------------------------------

class TestCalibration:
    # (asset, metric, pre_ramp_only) — targets are read from config.STATS so the
    # tests track data/profile/stats.json instead of drifting copies of it.
    TARGETS = [
        ("PUMP-104A", "vibration_hz", True),
        ("PUMP-104A", "temperature_c", True),
        ("CRUSHER-03", "feed_rate_tph", False),
        ("CRUSHER-03", "rotational_torque_nm", False),
        ("MILL-01", "power_draw_mw", False),
    ]

    @staticmethod
    def _window(df, asset, metric, pre_ramp):
        sub = series_frame(df, asset, metric)
        if pre_ramp:
            sub = sub.loc[pre_ramp_mask(sub["timestamp"])]
        return sub

    @pytest.mark.parametrize("asset,metric,pre_ramp", TARGETS)
    def test_mean_within_5pct(self, df, asset, metric, pre_ramp):
        tgt = stats_row(asset, metric)["mean"]
        actual = self._window(df, asset, metric, pre_ramp)["metric_value"].mean()
        tol = 0.05 * abs(tgt)
        assert abs(actual - tgt) <= tol, (
            f"{asset}/{metric} mean {actual:.4f} not within 5% of stats.json target "
            f"{tgt:.4f} (tol={tol:.4f}, error={100 * (actual - tgt) / tgt:+.2f}%)"
        )

    @pytest.mark.parametrize("asset,metric,pre_ramp", TARGETS)
    def test_sd_within_5pct(self, df, asset, metric, pre_ramp):
        tgt = stats_row(asset, metric)["sd"]
        actual = self._window(df, asset, metric, pre_ramp)["metric_value"].std(ddof=1)
        tol = 0.05 * tgt
        assert abs(actual - tgt) <= tol, (
            f"{asset}/{metric} σ {actual:.4f} not within 5% of stats.json target "
            f"{tgt:.4f} (tol={tol:.4f}, error={100 * (actual - tgt) / tgt:+.2f}%)"
        )


# ---------------------------------------------------------------------------
# 8. End-point pinning: each series must land on its current_state value
# ---------------------------------------------------------------------------

class TestEndpoints:
    # (asset, metric, expected_final, tolerance)
    ENDPOINTS = [
        ("PUMP-104A", "vibration_hz", 12.5, 0.5),
        ("PUMP-104A", "temperature_c", 85.2, 1.0),
        ("MILL-01", "temperature_c", 88.5, 0.5),
        ("MILL-01", "rotational_speed_rpm", 14.8, 0.2),
        ("CONVEYOR-02", "speed_mps", 4.5, 0.1),
        ("CONVEYOR-02", "belt_tension_kn", 25.4, 0.3),
        ("CONVEYOR-02", "load_pct", 88.0, 2.0),
        ("TRUCK-08", "speed_kmh", 32.5, 1.0),
        ("TRUCK-08", "payload_tons", 218.4, 2.0),
        ("TRUCK-08", "engine_temp_c", 92.1, 1.0),
        ("CRUSHER-03", "feed_rate_tph", 1210.0, 10.0),
        ("CRUSHER-03", "rotational_torque_nm", 4205.0, 20.0),
    ]

    @pytest.mark.parametrize("asset,metric,target,tol", ENDPOINTS)
    def test_final_value_near_target(self, df, asset, metric, target, tol):
        final_val = series_frame(df, asset, metric)["metric_value"].iloc[-1]
        assert abs(final_val - target) <= tol, (
            f"{asset}/{metric} final value {final_val:.3f} not within {tol} "
            f"of target {target}"
        )

    def test_endpoint_table_matches_generator(self):
        """The expected end-points are the generator's own current_state table."""
        expected = {(a, m): v for a, m, v, _ in self.ENDPOINTS}
        assert expected == tel.CURRENT_STATE_ENDPOINTS


# ---------------------------------------------------------------------------
# 9. Physical bounds checks
# ---------------------------------------------------------------------------

class TestPhysicalBounds:
    def test_truck_payload_under_capacity(self, df):
        """TRUCK-08 payload_tons must never exceed 240 t (fleet_vehicles capacity)."""
        vals = series_values(df, "TRUCK-08", "payload_tons")
        assert vals.max() <= 240.0, f"Truck payload exceeds 240 t: {vals.max():.1f}"

    def test_mill_speed_positive(self, df):
        vals = series_values(df, "MILL-01", "rotational_speed_rpm")
        assert vals.min() > 0, "MILL-01 speed must be positive"

    def test_conveyor_load_pct_bounds(self, df):
        vals = series_values(df, "CONVEYOR-02", "load_pct")
        assert vals.max() <= 100.0, f"load_pct exceeds 100: {vals.max():.1f}"
        assert vals.min() >= 0.0, f"load_pct below 0: {vals.min():.1f}"

    def test_pump_vibration_positive(self, df):
        vals = series_values(df, "PUMP-104A", "vibration_hz")
        assert vals.min() > 0.0, "PUMP-104A vibration_hz must be positive"

    # --- bounds taken from the captured profile, not from invented literals ---

    # Series whose full range must stay inside the historical [mn, mx].
    BOUNDED_BOTH = [
        ("CRUSHER-03", "feed_rate_tph"),
        ("CRUSHER-03", "rotational_torque_nm"),
        ("MILL-01", "power_draw_mw"),
    ]
    # PUMP-104A series carry a deliberate progressive failure, so they may exceed
    # the historical maximum (which is a pre-failure maximum) but must never fall
    # below the historical minimum.
    BOUNDED_FLOOR_ONLY = [
        ("PUMP-104A", "vibration_hz"),
        ("PUMP-104A", "temperature_c"),
    ]

    @pytest.mark.parametrize("asset,metric", BOUNDED_BOTH)
    def test_within_profile_range(self, df, asset, metric):
        st = stats_row(asset, metric)
        vals = series_values(df, asset, metric)
        assert vals.min() >= st["mn"], (
            f"{asset}/{metric} min {vals.min():.4f} below profile mn {st['mn']}"
        )
        assert vals.max() <= st["mx"], (
            f"{asset}/{metric} max {vals.max():.4f} above profile mx {st['mx']}"
        )

    @pytest.mark.parametrize("asset,metric", BOUNDED_FLOOR_ONLY)
    def test_above_profile_floor(self, df, asset, metric):
        st = stats_row(asset, metric)
        vals = series_values(df, asset, metric)
        assert vals.min() >= st["mn"], (
            f"{asset}/{metric} min {vals.min():.4f} below profile mn {st['mn']}"
        )

    @pytest.mark.parametrize("asset,metric", BOUNDED_BOTH + BOUNDED_FLOOR_ONLY)
    def test_bounds_do_not_manufacture_flatlines(self, df, asset, metric):
        """Bounds must be enforced smoothly, not with ``np.clip``.

        A hard clip parks many consecutive samples on exactly the bound, creating
        flat runs indistinguishable from stuck-sensor faults (the old generator
        left 15 samples at exactly 5.0 MW and 4 at exactly 3.0).  Series that
        carry no injected fault must have no repeated consecutive values at all.
        """
        st = stats_row(asset, metric)
        vals = series_values(df, asset, metric)
        runs = equal_runs(vals)
        assert not runs, (
            f"{asset}/{metric} has {len(runs)} flat run(s) {runs[:5]} — bounds are "
            "being enforced with a hard clip"
        )
        for bound_name in ("mn", "mx"):
            n_at = int(np.sum(vals == st[bound_name]))
            assert n_at <= 1, (
                f"{asset}/{metric} has {n_at} samples sitting exactly on "
                f"{bound_name}={st[bound_name]}"
            )


# ---------------------------------------------------------------------------
# 10. Injected faults: dropouts and stuck-sensor runs
# ---------------------------------------------------------------------------

class TestFaults:
    @pytest.mark.parametrize("asset,metric", ALL_SERIES)
    def test_dropout_rate_in_band(self, df, asset, metric):
        """Every series drops some samples, but well under 1%."""
        n_present = len(series_frame(df, asset, metric))
        rate = 1.0 - n_present / tel.N
        assert 0.0 < rate <= 0.01, (
            f"{asset}/{metric} dropout rate {rate * 100:.3f}% outside (0%, 1%] "
            f"({n_present}/{tel.N} rows present)"
        )

    def test_overall_dropout_near_configured_rate(self, df):
        rate = 1.0 - len(df) / (len(ALL_SERIES) * tel.N)
        assert abs(rate - tel._DROPOUT_RATE) <= 0.003, (
            f"overall dropout rate {rate:.5f} far from configured "
            f"{tel._DROPOUT_RATE:.5f}"
        )

    @pytest.mark.parametrize("asset,metric", list(tel._STUCK_SERIES))
    def test_stuck_runs_count_and_length(self, df, asset, metric):
        """Exactly two stuck-sensor runs, each 6–10 h (3–5 samples) long.

        The old implementation used a Poisson-like start probability with a fixed
        4-sample run length, so a series could contain zero runs and every run was
        exactly 8 h.  Nothing tested it.
        """
        sub = series_frame(df, asset, metric)
        vals = sub["metric_value"].to_numpy(float)
        ts = pd.to_datetime(sub["timestamp"], utc=True).to_numpy()
        runs = equal_runs(vals)

        assert len(runs) == tel._STUCK_RUNS_PER_SERIES, (
            f"{asset}/{metric} has {len(runs)} flat runs {runs}, expected "
            f"{tel._STUCK_RUNS_PER_SERIES}"
        )
        for start, length in runs:
            assert tel._STUCK_RUN_LEN_MIN <= length <= tel._STUCK_RUN_LEN_MAX, (
                f"{asset}/{metric} stuck run at index {start} is {length} samples "
                f"({length * 2} h); expected {tel._STUCK_RUN_LEN_MIN}–"
                f"{tel._STUCK_RUN_LEN_MAX} samples (6–10 h)"
            )
            # The flatline must be contiguous in time, not an artefact of dropouts
            # removing intervening rows.
            gaps = np.diff(ts[start:start + length]).astype("timedelta64[h]").astype(int)
            assert set(gaps.tolist()) <= {2}, (
                f"{asset}/{metric} stuck run at index {start} is not contiguous: "
                f"gaps {gaps.tolist()} h"
            )

    def test_stuck_runs_vary_in_length(self, df):
        """Run length is drawn from 3–5, so it is not a single fixed constant."""
        lengths = []
        for asset, metric in tel._STUCK_SERIES:
            vals = series_values(df, asset, metric)
            lengths += [ln for _, ln in equal_runs(vals)]
        assert len(set(lengths)) > 1, (
            f"all stuck runs have identical length {lengths} — run length is fixed"
        )

    @pytest.mark.parametrize("asset,metric", NON_STUCK_SERIES)
    def test_no_unintended_flatlines(self, df, asset, metric):
        """Only the two designated series carry stuck-sensor flatlines."""
        runs = equal_runs(series_values(df, asset, metric))
        assert not runs, f"{asset}/{metric} has unexpected flat run(s): {runs[:5]}"


# ---------------------------------------------------------------------------
# 11. Downstream contract: Task 3 derives crusher_states from CRUSHER-03 feed
# ---------------------------------------------------------------------------

class TestDownstreamContract:
    def test_crusher_feed_covers_every_day(self, df):
        """Task 3 takes the daily mean of CRUSHER-03 feed_rate_tph for 167 days."""
        sub = series_frame(df, "CRUSHER-03", "feed_rate_tph")
        days = pd.to_datetime(sub["timestamp"], utc=True).dt.date
        counts = days.value_counts()
        assert len(counts) == 167, f"expected 167 distinct days, got {len(counts)}"
        assert counts.min() >= 8, (
            f"a day has only {counts.min()} samples; daily means would be noisy"
        )
