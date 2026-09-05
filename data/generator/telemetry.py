"""Telemetry stream generator — Task 2.

Produces 13 asset·metric series × 2004 timestamps ≈ 26,000 rows and writes
``data/generated/telemetry_stream.parquet``.

Design decisions
----------------
* **Calibration source**: every mean / σ / min / max used here comes from
  ``data/profile/stats.json`` via ``config.STATS``.  That file is a frozen
  snapshot of the *pre-regeneration* tables (captured 2026-08-10, the same
  vintage as the ``*_original_20260810`` BigQuery backups).  This module never
  reads a live BigQuery table, so re-running it after Task 8 overwrites
  ``telemetry_stream`` cannot become self-referential.  No numeric calibration
  literal appears anywhere in this file.

* **Determinism**: per-series seeds are derived with ``hashlib.blake2b`` rather
  than Python's built-in ``hash()``.  ``hash()`` of a ``str``/``tuple`` is
  salted by ``PYTHONHASHSEED``, so it differs between interpreter processes and
  would make the output non-reproducible across runs.

* **3-h lag resolution**: at a 2-hourly grid, 3 h = 1.5 samples (not an integer).
  We round to **2 samples (4 h)** rather than 1 sample (2 h) because thermal mass
  in a pump bearing/lube system delays response; erring longer is more physical.

* **Degradation ramp**: applied *on top of* the baseline OU as a plain
  multiplication — ``vibration *= env(t)`` — so the ramp scales the whole
  signal, mean and fluctuation alike, and the detrended variance therefore
  *grows* through the ramp exactly as it does on a degrading bearing.

  ``env`` is the exponential wear curve ``1 + K*(1 - exp(-alpha*t))``,
  normalised to be exactly 1.0 at the ramp start (so the baseline→ramp join is
  continuous by construction — no blending fudge, no step clipping) and exactly
  ``target/mean`` at the final sample.

  *Why the saturating exponential rather than ``1 + k*exp(+alpha*t)``*: the end
  point is pinned to ``current_state`` (12.5 Hz) and the pre-ramp mean is pinned
  to the stats.json mean (5.1208 Hz).  Those two pins bound the final-7-day mean
  from above, and for the *convex* form the last-7-day envelope average tops out
  at ~2.10× the baseline for any (k, alpha) — below the 2.0× threshold once the
  OU realisation error in a 7-day window (~0.45 Hz here) is subtracted.  The
  previous implementation only cleared the bar by hardcoding a pre-ramp mean of
  4.9 Hz, 4.3% below the calibration target.  The saturating form reaches ~90%
  of its final value a week before the end, which both clears the bar honestly
  and matches ``assets.current_state``: the pump is *recorded at* 12.5 Hz, i.e.
  it has been running at that degraded level, not peaking there instantaneously.

* **Bounds**: physical bounds are enforced with a smooth saturating map
  (``_soft_bound``) instead of ``np.clip``.  A hard clip parks many consecutive
  samples on exactly the same float, manufacturing flat runs that are
  indistinguishable from genuine stuck-sensor faults.  ``_soft_bound`` is
  strictly monotone, so every sample stays distinct while the bound is never
  crossed.  Bounds for pre-existing series come from ``stats.json`` mn/mx.

* **Faults**: dropouts at ``_DROPOUT_RATE``; exactly ``_STUCK_RUNS_PER_SERIES``
  stuck-sensor runs per affected series, each 3–5 samples (6–10 h) long.

* **Crusher correlation**: CRUSHER-03 rotational_torque_nm is generated from a
  shared OU residual with feed_rate_tph plus an independent noise component,
  giving the required 0.65–0.85 Pearson correlation.

* **Endpoint pinning**: each series is linearly blended toward its current_state
  target over the final 24 h, ensuring a smooth landing without a sudden step.

* **New-series baselines**: all eight new metrics use physically motivated
  parameters documented in the constant block ``NEW_SERIES_BASELINES`` below.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np
import pandas as pd

from data.generator.config import SEED, STATS
from data.generator.common import (
    diurnal,
    dropout_mask,
    ou_process,
    shift_step,
    weekly_dip,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_OUT_PATH = _REPO_ROOT / "data" / "generated" / "telemetry_stream.parquet"

# ---------------------------------------------------------------------------
# Grid — 2-hourly from 2026-01-01T00:00:00Z to 2026-06-16T22:00:00Z
# ---------------------------------------------------------------------------

_T0 = np.datetime64("2026-01-01T00:00:00", "s")
_T1 = np.datetime64("2026-06-16T22:00:00", "s")
_STEP = np.timedelta64(2, "h")
TIMESTAMPS: np.ndarray = np.arange(_T0, _T1 + _STEP, _STEP)
N: int = len(TIMESTAMPS)  # must be 2004

# ---------------------------------------------------------------------------
# Current-state end-points and new-series baselines
# (values that do NOT exist in stats.json must live here, clearly named)
# ---------------------------------------------------------------------------

# fmt: off
CURRENT_STATE_ENDPOINTS: dict[tuple[str, str], float] = {
    ("PUMP-104A",   "vibration_hz"):         12.5,
    ("PUMP-104A",   "temperature_c"):         85.2,
    ("MILL-01",     "temperature_c"):         88.5,
    ("MILL-01",     "rotational_speed_rpm"):  14.8,
    ("CONVEYOR-02", "speed_mps"):              4.5,
    ("CONVEYOR-02", "belt_tension_kn"):       25.4,
    ("CONVEYOR-02", "load_pct"):              88.0,
    ("TRUCK-08",    "speed_kmh"):             32.5,
    ("TRUCK-08",    "payload_tons"):         218.4,
    ("TRUCK-08",    "engine_temp_c"):         92.1,
    ("CRUSHER-03",  "feed_rate_tph"):       1210.0,
    ("CRUSHER-03",  "rotational_torque_nm"): 4205.0,
    # MILL-01 power_draw_mw endpoint is in current_state as 4.25; not required by
    # brief so we omit it from the pinning list (avoids conflicting with calibration).
}

NEW_SERIES_BASELINES: dict[tuple[str, str], dict] = {
    # SAG mill bearing/lube temperature — high but stable; must reach 88.5 °C
    # diurnal_amp set to 3.5 so hour-of-day amplitude > 3% of 85 °C (= 2.55 °C)
    ("MILL-01", "temperature_c"): {
        "mean": 85.0, "sigma": 2.5, "phi": 0.92,
        "diurnal_amp": 3.5, "peak_hour": 14,
        "shift_scale": 0.5, "weekly_mag": 0.045,
        "lo": 76.0, "hi": 96.0,
    },
    # SAG mill rotational speed — very tightly regulated; must reach 14.8 rpm
    # diurnal_amp set to 0.5 so hour-of-day amplitude > 3% of 14.5 rpm (= 0.435 rpm)
    ("MILL-01", "rotational_speed_rpm"): {
        "mean": 14.5, "sigma": 0.35, "phi": 0.90,
        "diurnal_amp": 0.50, "peak_hour": 10,
        "shift_scale": 0.05, "weekly_mag": 0.030,
        "lo": 13.0, "hi": 16.0,
    },
    # Belt tension tracks load_pct; must reach 25.4 kN
    ("CONVEYOR-02", "belt_tension_kn"): {
        "mean": 24.0, "sigma": 1.5, "phi": 0.88,
        "diurnal_amp": 0.4, "peak_hour": 10,
        "shift_scale": 0.2, "weekly_mag": 0.045,
        "lo": 18.0, "hi": 30.0,
    },
    # Belt speed — closely regulated; must reach 4.5 m/s
    # diurnal_amp 0.15 so hour-of-day amplitude > 3% of mean 4.4 m/s (= 0.132 m/s)
    ("CONVEYOR-02", "speed_mps"): {
        "mean": 4.4, "sigma": 0.15, "phi": 0.88,
        "diurnal_amp": 0.15, "peak_hour": 10,
        "shift_scale": 0.04, "weekly_mag": 0.030,
        "lo": 3.8, "hi": 5.0,
    },
    # Load pct — widest-swinging conveyor metric; must reach 88%
    ("CONVEYOR-02", "load_pct"): {
        "mean": 78.0, "sigma": 9.0, "phi": 0.85,
        "diurnal_amp": 3.5, "peak_hour": 10,
        "shift_scale": 2.0, "weekly_mag": 0.060,
        "lo": 40.0, "hi": 100.0,
    },
    # Truck engine temp tracks payload; must reach 92.1 °C
    ("TRUCK-08", "engine_temp_c"): {
        "mean": 88.0, "sigma": 4.0, "phi": 0.88,
        "diurnal_amp": 1.2, "peak_hour": 12,
        "shift_scale": 0.5, "weekly_mag": 0.045,
        "lo": 74.0, "hi": 102.0,
    },
    # Payload — capacity 240 t (fleet_vehicles), bounded; must reach 218.4 t
    ("TRUCK-08", "payload_tons"): {
        "mean": 205.0, "sigma": 22.0, "phi": 0.85,
        "diurnal_amp": 7.0, "peak_hour": 11,
        "shift_scale": 3.0, "weekly_mag": 0.050,
        "lo": 120.0, "hi": 240.0,
    },
    # Speed — loaded haul is slower; must reach 32.5 km/h
    ("TRUCK-08", "speed_kmh"): {
        "mean": 28.0, "sigma": 6.0, "phi": 0.85,
        "diurnal_amp": 2.0, "peak_hour": 10,
        "shift_scale": 1.0, "weekly_mag": 0.050,
        "lo": 8.0, "hi": 55.0,
    },
}
# fmt: on

# --- Degradation ramp (PUMP-104A vibration_hz and temperature_c) ------------
RAMP_DAYS = 21              # final 21 days carry the ramp
_RAMP_ALPHA_PER_DAY = 0.11  # wear-curve rate constant (per day)

# How many samples from the end to pin the endpoint (smooth landing window)
_ENDPOINT_BLEND_SAMPLES = 12  # 12 × 2 h = 24 h

# --- Faults -----------------------------------------------------------------
# Brief: "two stuck-sensor runs of 6-10 h".  On a 2-hourly grid 6 h = 3 samples
# and 10 h = 5 samples, so run length is drawn uniformly from {3, 4, 5} and the
# count is exactly 2 (not Poisson — a Poisson count can yield zero runs).
_STUCK_RUNS_PER_SERIES = 2
_STUCK_RUN_LEN_MIN = 3
_STUCK_RUN_LEN_MAX = 5
_STUCK_SERIES: tuple[tuple[str, str], ...] = (
    ("CONVEYOR-02", "belt_tension_kn"),
    ("TRUCK-08", "engine_temp_c"),
)

# Dropout rate
_DROPOUT_RATE = 0.004

# Softness of the saturating bound, as a fraction of the series σ.
_SOFT_BOUND_FRAC = 0.35


# ---------------------------------------------------------------------------
# Seed management — each series gets a reproducible independent seed
# ---------------------------------------------------------------------------

def _stable_hash(key: str) -> int:
    """Process-stable 32-bit hash.

    ``hash()`` on str/tuple is randomised per interpreter by PYTHONHASHSEED, so
    using it here would make the generator non-reproducible across processes.
    """
    return int.from_bytes(hashlib.blake2b(key.encode(), digest_size=4).digest(), "big")


def _series_seed(base: int, asset: str, metric: str) -> int:
    """Deterministic per-series seed derived from the base seed."""
    return (base + _stable_hash(f"{asset}|{metric}")) & 0xFFFFFFFF


# ---------------------------------------------------------------------------
# Calibration lookup helpers
# ---------------------------------------------------------------------------

def _stats(asset: str, metric: str) -> dict:
    """Return the stats.json row for a pre-existing series."""
    for row in STATS["telemetry_by_asset_metric"]:
        if row["asset_id"] == asset and row["metric_name"] == metric:
            return row
    raise KeyError(f"No stats for {asset}/{metric}")


# ---------------------------------------------------------------------------
# Smooth bounds and moment calibration
# ---------------------------------------------------------------------------

def _soft_bound(
    x: np.ndarray,
    lo: float | None,
    hi: float | None,
    softness: float,
) -> np.ndarray:
    """Strictly monotone map of the real line into the open interval (lo, hi).

    Uses a softplus knee of width ``softness``: the map is the identity to
    within float noise while ``x`` is more than a few ``softness`` inside the
    bound, and saturates smoothly beyond it.  Unlike ``np.clip`` it never maps
    two different inputs to the same float, so it cannot manufacture flat runs
    that would masquerade as stuck-sensor faults.
    """
    out = np.asarray(x, dtype=float)
    s = max(float(softness), 1e-12)
    if lo is not None:
        out = lo + s * np.logaddexp(0.0, (out - lo) / s)
    if hi is not None:
        out = hi - s * np.logaddexp(0.0, (hi - out) / s)
    return out


def _calibrate_bounded(
    x: np.ndarray,
    *,
    mean: float,
    sd: float,
    lo: float | None,
    hi: float | None,
    window: np.ndarray | None = None,
    iters: int = 200,
) -> np.ndarray:
    """Affinely pre-scale ``x`` so that after ``_soft_bound`` the (windowed)
    mean and standard deviation equal the requested targets.

    Saturation biases the moments, so a plain z-score followed by a bound would
    miss the calibration targets.  The fixed-point loop below is deterministic
    (no RNG) and converges in a handful of iterations.
    """
    w = np.ones(len(x), dtype=bool) if window is None else window
    z = (x - x[w].mean()) / (x[w].std() + 1e-12)
    softness = _SOFT_BOUND_FRAC * sd
    gain, offset = sd, mean
    for _ in range(iters):
        y = _soft_bound(z * gain + offset, lo, hi, softness)
        gain *= sd / (y[w].std() + 1e-12)
        offset += mean - y[w].mean()
    return _soft_bound(z * gain + offset, lo, hi, softness)


# ---------------------------------------------------------------------------
# Core series builder
# ---------------------------------------------------------------------------

def _build_raw_series(
    *,
    mean: float,
    sigma: float,
    phi: float,
    diurnal_amp: float,
    peak_hour: int,
    shift_scale: float,
    weekly_mag: float,
    seed: int,
) -> np.ndarray:
    """Generate raw OU + rhythm series (before bounds / pinning / faults).

    The weekly planned-maintenance factor multiplies the *level* (mean
    included), not just the zero-mean deviation — otherwise it would leave the
    day-of-week means untouched and the maintenance dip would be inert.
    """
    ts = TIMESTAMPS.astype("datetime64[s]")

    ou = ou_process(N, mu=0.0, sigma=sigma, phi=phi, seed=seed)
    d = diurnal(ts, amplitude=diurnal_amp, peak_hour=peak_hour)
    s = shift_step(ts) * shift_scale
    w = weekly_dip(ts, magnitude=weekly_mag)

    return (ou + d + s + mean) * w


def _pin_endpoint(series: np.ndarray, target: float, n_blend: int) -> np.ndarray:
    """Smoothly blend the tail of series toward target over the last n_blend samples."""
    out = series.copy()
    n = len(out)
    start = max(0, n - n_blend)
    for i in range(start, n):
        alpha = (i - start) / (n - 1 - start + 1e-9)
        out[i] = (1.0 - alpha) * out[i] + alpha * target
    return out


# ---------------------------------------------------------------------------
# Degradation-ramp helpers
# ---------------------------------------------------------------------------

def ramp_masks() -> tuple[np.ndarray, np.ndarray]:
    """Boolean masks for the pre-ramp and ramp windows of the grid."""
    ramp_start = _T1 - np.timedelta64(RAMP_DAYS * 24 * 3600, "s")
    ramp = TIMESTAMPS >= ramp_start
    return ~ramp, ramp


def _ramp_envelope(final_ratio: float) -> np.ndarray:
    """Exponential wear curve, exactly 1.0 outside the ramp window.

    ``env(t) = 1 + (final_ratio - 1) * (1 - exp(-alpha*t)) / (1 - exp(-alpha*T))``

    ``env(0) == 1.0`` exactly, so the baseline→ramp join is continuous by
    construction — no artificial step, hence no blending window and no step
    clipping.  ``env(T) == final_ratio`` exactly, so the ramp lands on the
    ``current_state`` level.  See the module docstring for why the saturating
    form is used rather than a purely convex ``1 + k*exp(+alpha*t)``.
    """
    _, ramp = ramp_masks()
    idx = np.where(ramp)[0]
    t_days = (TIMESTAMPS[idx] - TIMESTAMPS[idx[0]]) / np.timedelta64(1, "D")
    a = _RAMP_ALPHA_PER_DAY
    norm = 1.0 - math.exp(-a * float(t_days[-1]))
    env = np.ones(N)
    env[idx] = 1.0 + (final_ratio - 1.0) * (1.0 - np.exp(-a * t_days)) / norm
    return env


# ---------------------------------------------------------------------------
# Per-series generators
# ---------------------------------------------------------------------------

def _gen_pump_vibration() -> np.ndarray:
    """PUMP-104A vibration_hz: OU baseline multiplied by the wear ramp.

    The baseline is calibrated on the **pre-ramp window** to the stats.json
    mean/σ and floored at the historical minimum ``mn``.  The ramp is then a
    literal multiplication, ``series = baseline * env``, so it scales the
    fluctuation as well as the level: detrended σ inside the ramp window is
    larger than pre-ramp, which is how bearing wear actually behaves.

    No upper soft bound is applied.  ``mx`` (13.87 Hz) is the maximum of the
    *pre-failure* record; the whole point of this series is a progressive
    failure that takes the pump outside its historical envelope, and it is
    pinned to the ``current_state`` value of 12.5 Hz at the end regardless.
    The lower bound — the side that was actually unphysical before, with the
    old generator reaching 1.195 Hz — is enforced at ``mn``.
    """
    st = _stats("PUMP-104A", "vibration_hz")
    target = CURRENT_STATE_ENDPOINTS[("PUMP-104A", "vibration_hz")]
    mean, sd, mn = st["mean"], st["sd"], st["mn"]

    pre_mask, _ = ramp_masks()

    baseline = _build_raw_series(
        mean=mean, sigma=sd, phi=0.90,
        diurnal_amp=0.35, peak_hour=10, shift_scale=0.10, weekly_mag=0.035,
        seed=_series_seed(SEED, "PUMP-104A", "vibration_hz"),
    )
    baseline = _calibrate_bounded(
        baseline, mean=mean, sd=sd, lo=mn, hi=None, window=pre_mask
    )

    series = baseline * _ramp_envelope(target / mean)
    return _pin_endpoint(series, target=target, n_blend=_ENDPOINT_BLEND_SAMPLES)


def _gen_pump_temperature(vibration_series: np.ndarray) -> np.ndarray:
    """PUMP-104A temperature_c — lags vibration by 2 samples (4 h).

    Decision: 3 h / 2 h per sample = 1.5 samples.  We round up to 2 samples
    (4 h) since thermal mass in a bearing/lube system tends to delay response
    beyond the mechanical excitation period.  The test allows 1–2 samples.

    Temperature is driven by the *detrended* lagged vibration (so the coupling
    coefficient stays a genuine thermal gain rather than absorbing the ramp),
    plus its own wear ramp anchored on the ambient floor ``mn``:
    ``T = mn + (T_base - mn) * env``.  Unlike vibration the deviation is not
    scaled by the envelope — the bearing running hot is a level shift, and
    scaling a 4 °C σ by 3.7× would push the series past the 99.57 °C ceiling.
    """
    st = _stats("PUMP-104A", "temperature_c")
    vib_st = _stats("PUMP-104A", "vibration_hz")
    target = CURRENT_STATE_ENDPOINTS[("PUMP-104A", "temperature_c")]
    mean, sd, mn, mx = st["mean"], st["sd"], st["mn"], st["mx"]

    pre_mask, _ = ramp_masks()
    ts = TIMESTAMPS.astype("datetime64[s]")
    lag = 2  # samples = 4 h

    # Undo the vibration ramp so the thermal coupling sees the OU part only.
    vib_env = _ramp_envelope(
        CURRENT_STATE_ENDPOINTS[("PUMP-104A", "vibration_hz")] / vib_st["mean"]
    )
    vib_detrended = vibration_series / vib_env

    vib_lagged = np.empty(N)
    vib_lagged[:lag] = vib_detrended[0]
    vib_lagged[lag:] = vib_detrended[:-lag]
    vib_z = (vib_lagged - vib_lagged[pre_mask].mean()) / (vib_lagged[pre_mask].std() + 1e-12)

    rho = 0.7  # thermal/mechanical coupling at the 4 h lag
    seed = _series_seed(SEED, "PUMP-104A", "temperature_c")
    noise = ou_process(N, mu=0.0, sigma=1.0, phi=0.90, seed=seed)

    core = rho * vib_z + math.sqrt(1.0 - rho**2) * noise
    raw = (core * sd + diurnal(ts, 1.0, 14) + shift_step(ts) * 0.4 + mean) * weekly_dip(
        ts, magnitude=0.030
    )
    base = _calibrate_bounded(raw, mean=mean, sd=sd, lo=mn, hi=mx, window=pre_mask)

    # Own ramp: the same bearing degrading heats the lube oil.  Anchored on the
    # ambient floor mn so the envelope ratio is solved on (mean - mn).
    env = _ramp_envelope((target - mn) / (mean - mn))
    series = mn + (base - mn) + (mean - mn) * (env - 1.0)
    # Only the ceiling needs re-applying: the floor is preserved by construction
    # (env >= 1 and base >= mn), and re-applying it would double-compress the
    # lower tail and pull the calibrated σ off target.
    series = _soft_bound(series, None, mx, _SOFT_BOUND_FRAC * sd)

    return _pin_endpoint(series, target=target, n_blend=_ENDPOINT_BLEND_SAMPLES)


def _gen_crusher_feed_rate() -> np.ndarray:
    """CRUSHER-03 feed_rate_tph, calibrated to stats.json mean/σ/mn/mx."""
    st = _stats("CRUSHER-03", "feed_rate_tph")
    series = _build_raw_series(
        mean=st["mean"], sigma=st["sd"], phi=0.88,
        diurnal_amp=30.0, peak_hour=10, shift_scale=10.0, weekly_mag=0.05,
        seed=_series_seed(SEED, "CRUSHER-03", "feed_rate_tph"),
    )
    series = _calibrate_bounded(
        series, mean=st["mean"], sd=st["sd"], lo=st["mn"], hi=st["mx"]
    )
    target = CURRENT_STATE_ENDPOINTS[("CRUSHER-03", "feed_rate_tph")]
    return _pin_endpoint(series, target=target, n_blend=_ENDPOINT_BLEND_SAMPLES)


def _gen_crusher_torque(feed_rate: np.ndarray) -> np.ndarray:
    """CRUSHER-03 rotational_torque_nm, correlated 0.65–0.85 with feed_rate_tph.

    A feed-correlated component (weight rho) is blended with an independent OU
    process (weight sqrt(1-rho²)); both are unit-variance so the core has sd 1
    and corr(core, feed) = rho.
    """
    st = _stats("CRUSHER-03", "rotational_torque_nm")
    rho = 0.78
    ou_ind = ou_process(N, mu=0.0, sigma=1.0, phi=0.88,
                        seed=_series_seed(SEED, "CRUSHER-03", "rotational_torque_nm"))
    feed_std = (feed_rate - feed_rate.mean()) / (feed_rate.std() + 1e-12)
    core = rho * feed_std + math.sqrt(1.0 - rho**2) * ou_ind

    ts = TIMESTAMPS.astype("datetime64[s]")
    d = diurnal(ts, amplitude=0.08 * st["sd"], peak_hour=10)
    s = shift_step(ts) * (0.03 * st["sd"])
    w = weekly_dip(ts, magnitude=0.035)
    raw = (core * st["sd"] + d + s + st["mean"]) * w

    series = _calibrate_bounded(
        raw, mean=st["mean"], sd=st["sd"], lo=st["mn"], hi=st["mx"]
    )
    target = CURRENT_STATE_ENDPOINTS[("CRUSHER-03", "rotational_torque_nm")]
    return _pin_endpoint(series, target=target, n_blend=_ENDPOINT_BLEND_SAMPLES)


def _gen_mill_power() -> np.ndarray:
    """MILL-01 power_draw_mw, calibrated to stats.json mean/σ within mn/mx.

    Not endpoint-pinned: current_state carries 4.25 MW but the brief does not
    require pinning this metric, and pinning would fight the calibration test.
    """
    st = _stats("MILL-01", "power_draw_mw")
    series = _build_raw_series(
        mean=st["mean"], sigma=st["sd"], phi=0.88,
        diurnal_amp=0.10, peak_hour=10, shift_scale=0.03, weekly_mag=0.04,
        seed=_series_seed(SEED, "MILL-01", "power_draw_mw"),
    )
    return _calibrate_bounded(
        series, mean=st["mean"], sd=st["sd"], lo=st["mn"], hi=st["mx"]
    )


def _gen_new_series(asset: str, metric: str) -> np.ndarray:
    """Generic generator for the eight new series using NEW_SERIES_BASELINES.

    These metrics have no stats.json row (they did not exist in the source
    table), so their bounds live in NEW_SERIES_BASELINES alongside the other
    physically motivated parameters.
    """
    p = NEW_SERIES_BASELINES[(asset, metric)]
    series = _build_raw_series(
        mean=p["mean"], sigma=p["sigma"], phi=p["phi"],
        diurnal_amp=p["diurnal_amp"], peak_hour=p["peak_hour"],
        shift_scale=p["shift_scale"], weekly_mag=p["weekly_mag"],
        seed=_series_seed(SEED, asset, metric),
    )
    series = _calibrate_bounded(
        series, mean=p["mean"], sd=p["sigma"], lo=p["lo"], hi=p["hi"]
    )
    key = (asset, metric)
    if key in CURRENT_STATE_ENDPOINTS:
        series = _pin_endpoint(
            series, target=CURRENT_STATE_ENDPOINTS[key], n_blend=_ENDPOINT_BLEND_SAMPLES
        )
    return series


# ---------------------------------------------------------------------------
# Faults
# ---------------------------------------------------------------------------

def _stuck_runs(seed: int, *, n_available: int) -> list[tuple[int, int]]:
    """Pick exactly ``_STUCK_RUNS_PER_SERIES`` non-overlapping (start, length)
    stuck-sensor runs of 3–5 samples (6–10 h) inside ``n_available`` samples.

    Runs are kept clear of the endpoint-pinning window so a stuck sensor cannot
    move a series off its ``assets.current_state`` end-point, and are separated
    by at least one sample so two runs never merge into one longer run.
    """
    rng = np.random.default_rng(seed)
    last_usable = n_available - _ENDPOINT_BLEND_SAMPLES - _STUCK_RUN_LEN_MAX - 1
    runs: list[tuple[int, int]] = []
    while len(runs) < _STUCK_RUNS_PER_SERIES:
        length = int(rng.integers(_STUCK_RUN_LEN_MIN, _STUCK_RUN_LEN_MAX + 1))
        start = int(rng.integers(1, last_usable))
        if all(start + length + 1 < s or start > s + ln + 1 for s, ln in runs):
            runs.append((start, length))
    return sorted(runs)


def _apply_stuck_runs(series: np.ndarray, runs: list[tuple[int, int]]) -> np.ndarray:
    """Freeze the series at its first value for each run (stuck transducer)."""
    out = series.copy()
    for start, length in runs:
        out[start:start + length] = out[start]
    return out


# ---------------------------------------------------------------------------
# Main generate function
# ---------------------------------------------------------------------------

def generate() -> None:
    """Generate all 13 telemetry series and write to parquet."""

    _OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    vib = _gen_pump_vibration()
    tmp = _gen_pump_temperature(vib)
    feed = _gen_crusher_feed_rate()
    torque = _gen_crusher_torque(feed)
    power = _gen_mill_power()

    series_list = [
        ("PUMP-104A",   "vibration_hz",         vib),
        ("PUMP-104A",   "temperature_c",        tmp),
        ("CRUSHER-03",  "feed_rate_tph",        feed),
        ("CRUSHER-03",  "rotational_torque_nm", torque),
        ("MILL-01",     "power_draw_mw",        power),
        ("MILL-01",     "temperature_c",        _gen_new_series("MILL-01", "temperature_c")),
        ("MILL-01",     "rotational_speed_rpm", _gen_new_series("MILL-01", "rotational_speed_rpm")),
        ("CONVEYOR-02", "belt_tension_kn",      _gen_new_series("CONVEYOR-02", "belt_tension_kn")),
        ("CONVEYOR-02", "speed_mps",            _gen_new_series("CONVEYOR-02", "speed_mps")),
        ("CONVEYOR-02", "load_pct",             _gen_new_series("CONVEYOR-02", "load_pct")),
        ("TRUCK-08",    "engine_temp_c",        _gen_new_series("TRUCK-08", "engine_temp_c")),
        ("TRUCK-08",    "payload_tons",         _gen_new_series("TRUCK-08", "payload_tons")),
        ("TRUCK-08",    "speed_kmh",            _gen_new_series("TRUCK-08", "speed_kmh")),
    ]

    records = []
    ts_pd = pd.to_datetime(TIMESTAMPS.astype("datetime64[ms]"), utc=True)

    for asset_id, metric_name, values in series_list:
        values = values.copy()
        mask = dropout_mask(
            N, rate=_DROPOUT_RATE,
            seed=_series_seed(SEED, asset_id, metric_name + "_drop"),
        )

        if (asset_id, metric_name) in _STUCK_SERIES:
            runs = _stuck_runs(
                _series_seed(SEED, asset_id, metric_name + "_stuck"), n_available=N
            )
            values = _apply_stuck_runs(values, runs)
            # A stuck transducer keeps *reporting* — it reports a frozen value.
            # Forcing these samples to be kept means the flatline survives the
            # dropout mask intact, which is both physically right and testable.
            for start, length in runs:
                mask[start:start + length] = True

        for t, v in zip(ts_pd[mask], values[mask]):
            records.append({
                "metric_name": metric_name,
                "metric_value": float(v),
                "asset_id": asset_id,
                "timestamp": t,
            })

    df = pd.DataFrame(records, columns=["metric_name", "metric_value", "asset_id", "timestamp"])
    df = df.sort_values(["asset_id", "metric_name", "timestamp"]).reset_index(drop=True)

    df.to_parquet(_OUT_PATH, index=False, engine="pyarrow")
    print(f"Wrote {len(df):,} rows to {_OUT_PATH}")


if __name__ == "__main__":
    generate()
