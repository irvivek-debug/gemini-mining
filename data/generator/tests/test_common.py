"""Tests for data/generator/common.py stochastic primitives."""

import numpy as np
import pytest

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common import (
    ou_process,
    diurnal,
    shift_step,
    weekly_dip,
    dropout_mask,
    stuck_sensor,
)


SEED = 20260810


class TestOuProcess:
    def test_length(self):
        result = ou_process(n=100, mu=50.0, sigma=5.0, phi=0.85, seed=SEED)
        assert len(result) == 100

    def test_returns_ndarray(self):
        result = ou_process(n=100, mu=50.0, sigma=5.0, phi=0.85, seed=SEED)
        assert isinstance(result, np.ndarray)

    def test_lag1_autocorrelation_in_range(self):
        """phi=0.85 must produce measured lag-1 autocorrelation in [0.80, 0.90]."""
        series = ou_process(n=4000, mu=100.0, sigma=10.0, phi=0.85, seed=SEED)
        ac = np.corrcoef(series[:-1], series[1:])[0, 1]
        assert 0.80 <= ac <= 0.90, f"lag-1 autocorrelation {ac:.4f} not in [0.80, 0.90]"

    def test_deterministic(self):
        a = ou_process(n=500, mu=0.0, sigma=1.0, phi=0.5, seed=42)
        b = ou_process(n=500, mu=0.0, sigma=1.0, phi=0.5, seed=42)
        np.testing.assert_array_equal(a, b)

    def test_different_seeds_differ(self):
        a = ou_process(n=500, mu=0.0, sigma=1.0, phi=0.5, seed=1)
        b = ou_process(n=500, mu=0.0, sigma=1.0, phi=0.5, seed=2)
        assert not np.array_equal(a, b)

    def test_initial_element_near_stationary(self):
        """First element should be drawn from N(mu, sigma), not N(mu, sigma/sqrt(1-phi^2)).

        After the variance-scaling fix, innovation_sd = sigma*sqrt(1-phi^2) and
        x[0] ~ N(mu, sigma) — the stationary SD of the corrected process.
        """
        x0_vals = [ou_process(n=1, mu=50.0, sigma=5.0, phi=0.85, seed=s)[0] for s in range(200)]
        assert abs(np.mean(x0_vals) - 50.0) < 2.0
        expected_sd = 5.0  # stationary SD equals sigma after the fix
        assert abs(np.std(x0_vals) - expected_sd) < 2.0

    def test_stationary_sd_matches_sigma(self):
        """Regression: ou_process must produce stationary SD within 2% of sigma.

        Before the fix, phi=0.85 inflated SD by 1/sqrt(1-phi^2) ≈ 1.90×.
        """
        series = ou_process(n=100_000, mu=0.0, sigma=10.0, phi=0.85, seed=SEED)
        measured_sd = np.std(series)
        assert abs(measured_sd - 10.0) / 10.0 < 0.02, (
            f"stationary SD {measured_sd:.4f} deviates >2% from requested sigma=10.0"
        )


class TestDiurnal:
    def _make_ts(self, n=24):
        base = np.datetime64("2026-01-01T00:00:00", "s")
        return base + np.arange(n) * np.timedelta64(3600, "s")

    def test_shape(self):
        ts = self._make_ts(48)
        result = diurnal(ts, amplitude=1.0, peak_hour=12)
        assert result.shape == (48,)

    def test_peak_at_correct_hour(self):
        ts = self._make_ts(24)
        result = diurnal(ts, amplitude=1.0, peak_hour=14)
        hours = np.arange(24)
        assert hours[np.argmax(result)] == 14

    def test_amplitude_range(self):
        ts = self._make_ts(48)
        result = diurnal(ts, amplitude=5.0, peak_hour=12)
        assert np.max(result) <= 5.0 + 1e-9
        assert np.min(result) >= -5.0 - 1e-9


class TestShiftStep:
    def _make_ts(self, n=48):
        base = np.datetime64("2026-01-01T00:00:00", "s")
        return base + np.arange(n) * np.timedelta64(3600, "s")

    def test_shape(self):
        ts = self._make_ts(48)
        result = shift_step(ts)
        assert result.shape == (48,)

    def test_only_two_values(self):
        ts = self._make_ts(48)
        result = shift_step(ts)
        unique_vals = np.unique(result)
        assert len(unique_vals) == 2

    def test_day_night_flip_at_6_and_18(self):
        """Step changes at 06:00 (day) and 18:00 (night)."""
        ts = self._make_ts(24)
        result = shift_step(ts)
        # Hours 6–17 should be day (one value), 18–5 should be night (other value)
        day_val = result[6]
        night_val = result[18]
        assert day_val != night_val
        for h in range(6, 18):
            assert result[h] == day_val, f"hour {h} should be day"
        for h in list(range(0, 6)) + list(range(18, 24)):
            assert result[h] == night_val, f"hour {h} should be night"


class TestWeeklyDip:
    def _make_ts(self, n_days=14):
        base = np.datetime64("2026-01-05T00:00:00", "s")  # Monday
        hours = n_days * 24
        return base + np.arange(hours) * np.timedelta64(3600, "s")

    def test_shape(self):
        ts = self._make_ts(14)
        result = weekly_dip(ts, magnitude=0.1)
        assert result.shape == ts.shape

    def test_values_between_0_and_1(self):
        ts = self._make_ts(14)
        result = weekly_dip(ts, magnitude=0.2)
        assert np.all(result >= 0.0) and np.all(result <= 1.0)

    def test_nonzero_magnitude_produces_variation(self):
        ts = self._make_ts(14)
        result = weekly_dip(ts, magnitude=0.2)
        assert np.max(result) - np.min(result) > 0.01

    def test_sunday_is_trough(self):
        """Regression: Sunday (dow=6) must have a strictly lower factor than every weekday.

        Base timestamp 2026-01-05T00:00:00 is a Monday (verified: weekday()==0).
        One week: Mon=hour 0, Tue=24, Wed=48, Thu=72, Fri=96, Sat=120, Sun=144.
        """
        ts = self._make_ts(7)  # 7 days = 168 hours starting on Monday
        result = weekly_dip(ts, magnitude=0.2)
        # One sample per day at midnight — take the hour-0 value for each day
        daily = result[::24]  # indices 0..6 => Mon..Sun
        sunday_val = daily[6]
        weekday_vals = daily[:5]  # Mon–Fri
        assert np.all(sunday_val < weekday_vals), (
            f"Sunday value {sunday_val:.4f} not below all weekday values {weekday_vals}"
        )


class TestDropoutMask:
    def test_shape(self):
        mask = dropout_mask(n=1000, rate=0.1, seed=SEED)
        assert len(mask) == 1000

    def test_dtype_bool(self):
        mask = dropout_mask(n=1000, rate=0.1, seed=SEED)
        assert mask.dtype == bool

    def test_true_means_keep(self):
        """True = keep; rate is fraction dropped so ~(1-rate) are True."""
        mask = dropout_mask(n=10000, rate=0.1, seed=SEED)
        keep_fraction = mask.sum() / 10000
        assert abs(keep_fraction - 0.9) < 0.01  # ±1pp tolerance

    def test_rate_within_01pp(self):
        """Drop rate within ±0.1pp of requested rate, verified at n=1_000_000.

        0.1pp = 0.001.  At n=1_000_000 the sampling std dev is
        sqrt(0.15*0.85/1_000_000) ≈ 0.000357, so ±0.1pp is ~2.8 sigma —
        tight enough to catch biased implementations while passing with SEED.
        """
        mask = dropout_mask(n=1_000_000, rate=0.15, seed=SEED)
        actual_drop_rate = (~mask).sum() / 1_000_000
        assert abs(actual_drop_rate - 0.15) < 0.001

    def test_deterministic(self):
        a = dropout_mask(n=500, rate=0.1, seed=7)
        b = dropout_mask(n=500, rate=0.1, seed=7)
        np.testing.assert_array_equal(a, b)

    def test_zero_rate_all_kept(self):
        mask = dropout_mask(n=100, rate=0.0, seed=SEED)
        assert mask.all()


class TestStuckSensor:
    def test_shape_preserved(self):
        rng = np.random.default_rng(SEED)
        series = rng.uniform(0, 100, 1000)
        result = stuck_sensor(series, rate=0.1, run_len=5, seed=SEED)
        assert result.shape == series.shape

    def test_produces_repeated_values(self):
        rng = np.random.default_rng(SEED)
        series = rng.uniform(0, 100, 5000)
        result = stuck_sensor(series, rate=0.1, run_len=5, seed=SEED)
        # Check there are consecutive equal values (flatlines)
        diffs = np.diff(result)
        n_zero = (diffs == 0).sum()
        assert n_zero > 0, "Expected some flatline runs"

    def test_deterministic(self):
        rng = np.random.default_rng(SEED)
        series = rng.uniform(0, 100, 500)
        a = stuck_sensor(series, rate=0.05, run_len=3, seed=42)
        b = stuck_sensor(series, rate=0.05, run_len=3, seed=42)
        np.testing.assert_array_equal(a, b)

    def test_zero_rate_unchanged(self):
        rng = np.random.default_rng(SEED)
        series = rng.uniform(0, 100, 200)
        result = stuck_sensor(series, rate=0.0, run_len=5, seed=SEED)
        np.testing.assert_array_equal(result, series)
