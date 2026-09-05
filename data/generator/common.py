"""Shared stochastic primitives used by all table-regeneration tasks.

Every function takes an explicit seed or rng so callers get full reproducibility
without relying on any global RNG state.
"""

import math
from hashlib import blake2b

import numpy as np


def stable_hash(key: str) -> int:
    """Process-stable 32-bit hash.

    Python's built-in hash() is salted per interpreter by PYTHONHASHSEED, so it
    must never appear in a seed derivation (this exact bug shipped in an early
    generator task and produced a different row count on every process).
    blake2b is keyed only by its input. Shared here rather than copied per
    module because ``contracts.py``, ``warranty.py`` and ``capital.py`` (Task
    2b) all need the identical derivation to compose seeds across tables that
    join to one another (e.g. a contract's transactions must derive from the
    same root as the contract itself).
    """
    return int.from_bytes(blake2b(key.encode(), digest_size=4).digest(), "big")


def rng_for(seed: int, *parts: str) -> np.random.Generator:
    """A deterministic RNG keyed by ``seed`` and an arbitrary tuple of parts."""
    return np.random.default_rng((seed + stable_hash("|".join(parts))) & 0xFFFFFFFF)


def ou_process(
    n: int,
    mu: float,
    sigma: float,
    phi: float,
    seed: int,
) -> np.ndarray:
    """Ornstein-Uhlenbeck (AR-1) process.

    x[t] = mu + phi*(x[t-1] - mu) + eps,  eps ~ N(0, innovation_sd)

    where innovation_sd = sigma * sqrt(1 - phi^2).  This scaling ensures the
    *stationary* standard deviation of the process equals the requested sigma,
    matching the calibration target stored in stats.json (which records the
    observed stationary SD of each series).

    The first element is drawn from the process's stationary distribution
    N(mu, sigma) to avoid a burn-in artifact at the start of every series.

    Returns a 1-D numpy array of length n.
    """
    rng = np.random.default_rng(seed)
    innovation_sd = sigma * math.sqrt(1.0 - phi**2)
    x = np.empty(n)
    x[0] = rng.normal(mu, sigma)
    eps = rng.normal(0.0, innovation_sd, size=n - 1)
    for t in range(1, n):
        x[t] = mu + phi * (x[t - 1] - mu) + eps[t - 1]
    return x


def diurnal(
    ts: np.ndarray,
    amplitude: float,
    peak_hour: int,
) -> np.ndarray:
    """24-h sinusoidal shift-rhythm overlay.

    Returns an array of the same shape as ts whose values are in
    [-amplitude, +amplitude].  Peak occurs at peak_hour (UTC hour-of-day).
    """
    # Convert numpy datetime64 to fractional hours
    ts_s = ts.astype("datetime64[s]").astype(np.int64)
    hour_of_day = (ts_s % 86400) / 3600.0
    phase = 2.0 * math.pi * (hour_of_day - peak_hour) / 24.0
    return amplitude * np.cos(phase)


def shift_step(ts: np.ndarray) -> np.ndarray:
    """12-h day/night step: +1 during 06:00–17:59 UTC, -1 otherwise.

    Handovers at 06:00 (day) and 18:00 (night).
    """
    ts_s = ts.astype("datetime64[s]").astype(np.int64)
    hour = (ts_s % 86400) // 3600
    return np.where((hour >= 6) & (hour < 18), 1.0, -1.0)


def weekly_dip(ts: np.ndarray, magnitude: float) -> np.ndarray:
    """Planned maintenance window: a multiplicative factor in [1-magnitude, 1].

    Values are lowest on Sundays (day-of-week == 6) and highest midweek,
    giving a realistic planned-maintenance signature.
    """
    ts_days = ts.astype("datetime64[D]").astype(np.int64)
    # Day-of-week: numpy epoch (1970-01-01) was a Thursday (dow=3)
    dow = (ts_days + 3) % 7  # 0=Mon, 6=Sun
    # Phase shift so the cosine trough (cos = -1) lands on Sunday (dow=6).
    # Without shift: trough at dow where 2*pi*dow/7 = pi => dow=3.5 (Thu/Fri).
    # With shift of -5*pi/7: trough at dow where 2*pi*dow/7 - 5*pi/7 = pi
    #   => dow = 6 (Sun). Verified: phase(dow=6) = 12*pi/7 - 5*pi/7 = pi.
    phase = 2.0 * math.pi * dow / 7.0 - 5.0 * math.pi / 7.0
    factor = 1.0 - magnitude * 0.5 * (1.0 - np.cos(phase))
    return np.clip(factor, 0.0, 1.0)


def dropout_mask(n: int, rate: float, seed: int) -> np.ndarray:
    """Boolean mask where True means 'keep this row'.

    rate is the fraction of rows to drop (sensor outages).
    """
    rng = np.random.default_rng(seed)
    return rng.random(n) >= rate


def stuck_sensor(
    series: np.ndarray,
    rate: float,
    run_len: int,
    seed: int,
) -> np.ndarray:
    """Inject flatline runs into series to simulate a stuck sensor.

    rate is the expected fraction of the series covered by flatlines.
    run_len is the length of each flatline segment.
    Returns a copy of series with some windows replaced by their first value.
    """
    rng = np.random.default_rng(seed)
    out = series.copy()
    n = len(series)
    if rate <= 0.0 or run_len <= 0:
        return out
    # Probability that any given position starts a stuck run
    p_start = rate / run_len
    starts = np.where(rng.random(n) < p_start)[0]
    for s in starts:
        end = min(s + run_len, n)
        out[s:end] = out[s]
    return out
