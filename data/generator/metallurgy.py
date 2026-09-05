"""Metallurgy generator — Task 3: enforce the two-product mass balance.

Rebuilds ``metallurgical_recovery`` and ``crusher_states`` so that recovery is
**computed, not drawn**:

    R = 100 * c * (f - t) / ( f * (c - t) )

with ``f`` = feed grade, ``c`` = concentrate grade, ``t`` = tailings grade.

Why this table needed rebuilding
--------------------------------
In the source data ``recovery_rate_pct`` was an independent draw: its
correlation with ``tailings_grade_pct`` was **+0.067** and with
``feed_grade_pct`` **+0.055**, where the physics demands a strong *negative* and
a moderate *positive* respectively.  Feeding the stored grades through the
two-product formula row by row gives a mean of **93.86** against a stored mean
of **92.21** — a 1.65 pp gap that is itself the proof the column was never
computed.  Here the three grades are generated and ``R`` is derived from them,
so the mass balance holds by construction and the correlations fall out of the
formula instead of being asserted.

Calibration and the shape of the observed marginals
---------------------------------------------------
``stats.json`` records, for each of the four columns, a mean and SD whose ratio
to the observed (min, max) support is the signature of a **uniform** draw::

    column   observed mean / sd     U(min, max) mean / sd
    f        1.1121 / 0.1771        U(0.80, 1.40)   -> 1.100 / 0.1732
    c       27.5795 / 1.4948        U(25.05, 29.98) -> 27.515 / 1.4229
    t        0.0689 / 0.0171        U(0.040, 0.100) -> 0.0700 / 0.0173
    R       92.2094 / 2.3674        U(88.03, 95.95) -> 91.990 / 2.2862

All four were drawn independently and uniformly.  The brief requires ``f`` and
``c`` to be *held near their observed distributions*, so both are given a
uniform marginal on the maximum-entropy interval that matches the observed
moments, ``U(mean - sqrt(3)*sd, mean + sqrt(3)*sd)`` — which for ``f`` is
(0.805, 1.419) against an observed support of (0.80, 1.40), and for ``c`` is
(24.99, 30.17) against (25.05, 29.98).  Matching the moments therefore
reproduces the observed support essentially exactly.  What is *added* is the
temporal structure the original lacked: both series are generated from an OU
process and mapped through the normal CDF, so the marginal is uniform while
consecutive days are correlated — feed grade tracks the ore being delivered
from a bench over days, it does not resample itself every midnight.

``t`` is the column that gets tuned.  It is no longer an independent draw at
all: it is a response surface (see ``_tailings_shape``), and its level is solved
at runtime by bisection so the *computed* recovery mean lands on the observed
``r_mean``.  This is the "tune t upward" step the brief calls for — the
generated tailings mean comes out at ~0.087 against a stored 0.0689, which is
exactly the 1.65 pp of recovery that the stored table could not account for.

**Recovery is never clipped.**  Nothing in this module bounds ``R``.  Its range
is a consequence of the grade distributions: ``f`` and ``c`` have bounded
(uniform) support, the gap-size response is bounded because the setting takes
three discrete values, and the residual is the only unbounded term — which is
why the residual SD is the parameter that was tuned down until the realised
range fitted inside the observed 88.0-96.0 band.

The tailings response surface
-----------------------------
``t`` is a *linear* (not log-linear) response in four physically-motivated
drivers::

    t = level * (1 + B_FEED_GRADE*(f/mean f - 1)
                   + B_GAP*coarseness
                   + B_THROUGHPUT*z(feed_rate)
                   + B_CONC_GRADE*z(c)
                   + residual)

The linear form matters.  Recovery is very nearly ``100*(1 - t/f)/(1 - t/c)``,
so it is close to affine in ``t``; a log-linear response makes ``t`` lognormal,
and the lognormal right tail maps to a long *low*-recovery tail.  An earlier
exponential version of this module hit 85.4 % on its worst day for exactly that
reason.  The linear form keeps ``t`` roughly symmetric, so recovery is roughly
symmetric too and the realised range (88.22-95.24) sits inside the observed
88.03-95.95 band without any clipping.  The drivers:

* ``B_FEED_GRADE * (f / mean f - 1)`` — richer feed loses proportionally *less*
  metal, so the coefficient is well below 1 (0.46).  With ``t/f`` the quantity
  that actually drives recovery, a sub-proportional response is precisely what
  makes ``corr(recovery, feed_grade)`` positive.
* ``B_GAP * coarseness`` — the A5 causal chain, see below.
* ``B_THROUGHPUT * z(feed_rate_tph)`` — higher tonnage means shorter residence
  time in flotation, so more metal reports to tails.  The feed rate used is the
  same series stored in ``crusher_states``.
* ``B_CONC_GRADE * z(c)`` — the grade/recovery trade-off: pushing the cleaner
  circuit for a higher concentrate grade costs recovery.

plus a mean-reverting residual (``RESID_SD``, ``RESID_PHI``) standing for
everything unmodelled (reagent dosing, water chemistry, ore texture).

The A5 excursion
----------------
``gap_size_setting_mm`` is an *operator setting*, so it is piecewise constant
over crushing campaigns rather than jittering daily as it did in the source
data.  The baseline closed-side setting is 120 mm, with three short fine-crush
campaigns at 115 mm.  The A5 event is the single campaign at 125 mm
(2026-03-26 to 2026-04-22, 28 days): the crusher is opened up by 10 mm, the
product coarsens, liberation degrades, tailings grade rises ~26 %, and recovery
falls ~2.5 pp through the formula.  Nothing is written into the recovery column
to make this happen — it propagates through ``t``.

The response is **lagged one day and exponentially smoothed** (``GAP_ALPHA``)
because mill and flotation inventory takes a few days to turn over, so the
tailings grade ramps into and out of the excursion rather than stepping with the
setting.  That is what makes the chain look like a plant rather than a lookup
table, and it is still recoverable by a plain join on the day.

The campaign schedule holds 116 days at 120 mm, 23 at 115 mm and 28 at 125 mm,
which reproduces the observed gap mean of 120.15 exactly (the constraint is
simply ``n125 - n115 = 5``).  The SD comes out at 2.87 against an observed 4.05:
that is deliberate, because the observed 4.05 came from a setting that changed
at random every single day, which no crusher does.

Cross-table consistency with telemetry_stream
---------------------------------------------
``telemetry_stream`` (Task 2) already carries 2-hourly ``feed_rate_tph`` and
``rotational_torque_nm`` series for CRUSHER-03.  ``crusher_states`` is the daily
roll-up of the same instrument, so **both columns are computed as the daily mean
of the telemetry series** rather than generated independently; otherwise the two
tables contradict each other under a one-line join.  This is read from
``data/generated/telemetry_stream.parquet``, not from BigQuery, because Task 8
has not loaded the new telemetry yet.

Sources of truth
----------------
* Calibration: ``data/profile/stats.json`` via ``config.STATS``.  No calibration
  figure appears as a literal in this file.
* Row grid and ``bypass_valve_open``: the **frozen Task-1 backups**
  ``*_original_20260810``, never the live tables — Task 8 overwrites the live
  copies, so reading them would make a re-run consume its own output.
* ``bypass_valve_open`` is carried through unchanged (one True day): it is not
  part of the defect this task fixes, and a rare event is worth preserving.

Determinism
-----------
Per-component seeds are derived with ``hashlib.blake2b``.  Python's built-in
``hash()`` is salted per interpreter by ``PYTHONHASHSEED``, so seeding from it
would make output differ between processes.
"""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from data.generator.common import ou_process
from data.generator.config import BACKUP_SUFFIX, DATASET, PROJECT_ID, SEED, STATS

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GENERATED_DIR = _REPO_ROOT / "data" / "generated"
_TELEMETRY_PATH = _GENERATED_DIR / "telemetry_stream.parquet"

# ---------------------------------------------------------------------------
# Calibration (read from stats.json — never restated as literals)
# ---------------------------------------------------------------------------

_MET: dict = STATS["metallurgy"][0]
_CRU: dict = STATS["crusher_states"][0]

N_DAYS: int = int(_MET["n"])
CONCENTRATOR_ID: str = _MET["conc"]
CRUSHER_ID: str = _CRU["asset"]

# ---------------------------------------------------------------------------
# Crushing-campaign schedule (design parameters, not observed statistics)
#
# (length_days, gap_size_setting_mm).  The single 125 mm campaign is the A5
# excursion.  Day counts are chosen so the mean setting reproduces the observed
# gap mean; see the module docstring.
# ---------------------------------------------------------------------------

CAMPAIGNS: tuple[tuple[int, float], ...] = (
    (20, 120.0),   # commissioning baseline
    (8, 115.0),    # fine-crush trial
    (22, 120.0),
    (8, 115.0),    # second fine-crush trial
    (26, 120.0),
    (28, 125.0),   # <-- A5: crusher opened up 10 mm to chase throughput
    (8, 120.0),    # back to the design setting
    (7, 115.0),    # third fine-crush trial
    (40, 120.0),
)

#: Index of the first and last day of the A5 window within the daily grid.
A5_START_INDEX: int = sum(n for n, _ in CAMPAIGNS[:5])
A5_LENGTH: int = CAMPAIGNS[5][0]
A5_END_INDEX: int = A5_START_INDEX + A5_LENGTH - 1

# ---------------------------------------------------------------------------
# Tailings response surface (design parameters — see module docstring)
# ---------------------------------------------------------------------------

#: Fractional rise in tailings grade per 100 % rise in feed grade.  Well below
#: 1, so the loss *ratio* t/f falls as the feed gets richer and recovery rises
#: with grade.
B_FEED_GRADE: float = 0.46

#: Fractional rise in tailings grade per 10 mm of extra closed-side setting.
B_GAP: float = 0.55

#: Exponential smoothing weight for the mill/flotation inventory turnover, and
#: the transport lag in days between a crusher setting change and the assay.
GAP_ALPHA: float = 0.55
GAP_LAG_DAYS: int = 1

#: Response to a 1-SD move in daily crusher feed rate (shorter residence time).
B_THROUGHPUT: float = 0.03

#: Response to a 1-SD move in concentrate grade (grade/recovery trade-off).
B_CONC_GRADE: float = 0.05

#: Residual (unmodelled) fractional variation in tailings grade, and its
#: persistence.
RESID_SD: float = 0.11
RESID_PHI: float = 0.35

#: Persistence of the feed-grade and concentrate-grade OU drivers (daily).
GRADE_PHI: float = 0.60

#: Correlation between the concentrate-grade and feed-grade latent drivers.
RHO_FEED_CONC: float = 0.35

# ---------------------------------------------------------------------------
# Reporting precision.  Grades are rounded to their assay reporting precision
# *before* recovery is computed, so that recomputing R from the stored columns
# reproduces the stored value exactly (up to R's own rounding).  Rounding the
# grades afterwards would break the mass balance by up to 0.05 pp.
# ---------------------------------------------------------------------------

DP_FEED_GRADE: int = 2
DP_CONC_GRADE: int = 2
DP_TAILINGS_GRADE: int = 3
DP_RECOVERY: int = 2
DP_CRUSHER: int = 2

# ---------------------------------------------------------------------------
# BigQuery source tables
#
# BigQuery binds parameters to *values* only — a table identifier cannot be a
# query parameter — so identifiers have to be interpolated into the SQL text.
# Every table read here is therefore declared in the allow-list below and
# re-validated against a strict identifier pattern before interpolation.  No
# caller-supplied string ever reaches a query.
# ---------------------------------------------------------------------------

_SOURCE_TABLES: dict[str, str] = {
    "metallurgy": "metallurgical_recovery" + BACKUP_SUFFIX,
    "crusher": "crusher_states" + BACKUP_SUFFIX,
}

_TABLE_IDENTIFIER_RE = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]{0,1023}\Z")


def _table(key: str) -> str:
    """Fully-qualified id of an allow-listed frozen backup table."""
    try:
        name = _SOURCE_TABLES[key]
    except KeyError:
        raise KeyError(
            f"{key!r} is not an allow-listed source table "
            f"(allowed: {sorted(_SOURCE_TABLES)})"
        ) from None
    if not _TABLE_IDENTIFIER_RE.match(name):
        raise ValueError(f"unsafe table identifier: {name!r}")
    return f"{PROJECT_ID}.{DATASET}.{name}"


def _client():
    """BigQuery client (deferred import so the module imports offline)."""
    from google.cloud import bigquery

    return bigquery.Client(project=PROJECT_ID)


# ---------------------------------------------------------------------------
# Seeds
# ---------------------------------------------------------------------------

def _stable_hash(key: str) -> int:
    """Process-stable 32-bit hash.

    ``hash()`` on a str is randomised per interpreter by PYTHONHASHSEED and
    would make this generator non-reproducible across processes.
    """
    return int.from_bytes(hashlib.blake2b(key.encode(), digest_size=4).digest(), "big")


def _component_seed(name: str) -> int:
    """Deterministic per-component seed derived from the project seed."""
    return (SEED + _stable_hash(name)) & 0xFFFFFFFF


# ---------------------------------------------------------------------------
# Frozen backup: row grid and the carried-through bypass column
# ---------------------------------------------------------------------------

_backup_cache: Optional[pd.DataFrame] = None


def _fetch_backup_crusher() -> pd.DataFrame:
    """``timestamp`` grid and ``bypass_valve_open`` from the frozen backup."""
    global _backup_cache
    if _backup_cache is not None:
        return _backup_cache

    client = _client()
    df = client.query(
        f"""
        SELECT timestamp, bypass_valve_open
        FROM `{_table('crusher')}`
        ORDER BY timestamp
        """
    ).to_dataframe()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    if len(df) != N_DAYS:
        raise RuntimeError(f"backup crusher_states has {len(df)} rows, expected {N_DAYS}")
    _backup_cache = df.reset_index(drop=True)
    return _backup_cache


# ---------------------------------------------------------------------------
# Telemetry roll-up
# ---------------------------------------------------------------------------

def crusher_daily_from_telemetry() -> pd.DataFrame:
    """Daily means of the CRUSHER-03 telemetry series.

    ``crusher_states`` is the daily roll-up of the same instrument that
    ``telemetry_stream`` samples every two hours, so its ``feed_rate_tph`` and
    ``rotational_torque_nm`` are *derived* from that series rather than drawn
    again.  Reading the parquet rather than BigQuery is deliberate: Task 8 has
    not loaded the regenerated telemetry yet, so the live table is stale.

    Returns a frame indexed by UTC day with one column per metric.
    """
    tel = pd.read_parquet(_TELEMETRY_PATH)
    sub = tel[tel["asset_id"] == CRUSHER_ID].copy()
    sub["day"] = pd.to_datetime(sub["timestamp"], utc=True).dt.floor("D")
    daily = (
        sub.pivot_table(index="day", columns="metric_name", values="metric_value",
                        aggfunc="mean")
        .sort_index()
    )
    missing = {"feed_rate_tph", "rotational_torque_nm"} - set(daily.columns)
    if missing:
        raise RuntimeError(f"telemetry_stream lacks CRUSHER-03 {sorted(missing)}")
    if len(daily) != N_DAYS:
        raise RuntimeError(
            f"CRUSHER-03 telemetry covers {len(daily)} days, expected {N_DAYS}"
        )
    return daily


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------

def _normal_cdf(z: np.ndarray) -> np.ndarray:
    """Standard normal CDF (scipy is not available in this environment)."""
    return 0.5 * (1.0 + np.vectorize(math.erf)(z / math.sqrt(2.0)))


def _uniform_marginal(z: np.ndarray, mean: float, sd: float) -> np.ndarray:
    """Map a standard-normal OU path onto ``U(mean - sqrt(3) sd, mean + sqrt(3) sd)``.

    The probability-integral transform preserves the path's rank ordering — and
    therefore its day-to-day persistence — while replacing the Gaussian
    marginal with the uniform one the source data exhibits.  The interval is the
    maximum-entropy distribution with the requested mean and SD; see the module
    docstring for how closely it reproduces the observed support.
    """
    half_width = math.sqrt(3.0) * sd
    return (mean - half_width) + _normal_cdf(z) * 2.0 * half_width


def gap_schedule() -> np.ndarray:
    """Piecewise-constant closed-side setting, one value per day."""
    gap = np.concatenate([np.full(n, v, dtype=float) for n, v in CAMPAIGNS])
    if len(gap) != N_DAYS:
        raise RuntimeError(f"campaign schedule covers {len(gap)} days, expected {N_DAYS}")
    return gap


def coarseness_index(gap: np.ndarray) -> np.ndarray:
    """Liberation penalty implied by the crusher setting, in 10 mm units.

    The raw setting is lagged by ``GAP_LAG_DAYS`` and exponentially smoothed to
    represent mill and flotation inventory turnover, so the tailings grade ramps
    into and out of a campaign rather than stepping with the setting.  Measured
    against the design point (the modal setting), so a normal campaign
    contributes nothing.
    """
    lagged = np.empty_like(gap)
    lagged[:GAP_LAG_DAYS] = gap[0]
    lagged[GAP_LAG_DAYS:] = gap[:-GAP_LAG_DAYS]

    smoothed = np.empty_like(lagged)
    smoothed[0] = lagged[0]
    for i in range(1, len(lagged)):
        smoothed[i] = GAP_ALPHA * lagged[i] + (1.0 - GAP_ALPHA) * smoothed[i - 1]

    design_point = float(np.median(gap))
    return (smoothed - design_point) / 10.0


def _tailings_shape(
    feed_grade: np.ndarray,
    conc_grade: np.ndarray,
    gap: np.ndarray,
    feed_rate: np.ndarray,
) -> np.ndarray:
    """Fractional tailings-grade deviation about the (later-solved) level.

    Returns ``u`` such that ``t = level * (1 + u)``.  See the module docstring
    for why the response is linear in ``t`` rather than in ``log t``.
    """
    resid = ou_process(
        N_DAYS, mu=0.0, sigma=RESID_SD, phi=RESID_PHI, seed=_component_seed("tailings_resid")
    )
    z_rate = (feed_rate - feed_rate.mean()) / feed_rate.std(ddof=0)
    z_conc = (conc_grade - conc_grade.mean()) / conc_grade.std(ddof=0)
    return (
        B_FEED_GRADE * (feed_grade / feed_grade.mean() - 1.0)
        + B_GAP * coarseness_index(gap)
        + B_THROUGHPUT * z_rate
        + B_CONC_GRADE * z_conc
        + resid
    )


def two_product_recovery(
    feed_grade: np.ndarray, conc_grade: np.ndarray, tailings_grade: np.ndarray
) -> np.ndarray:
    """R = 100 * c * (f - t) / ( f * (c - t) ) — the two-product formula."""
    return (
        100.0
        * conc_grade
        * (feed_grade - tailings_grade)
        / (feed_grade * (conc_grade - tailings_grade))
    )


def _solve_tailings_level(
    shape: np.ndarray,
    feed_grade: np.ndarray,
    conc_grade: np.ndarray,
    target_mean_recovery: float,
) -> float:
    """Bisect the tailings level so mean computed recovery hits the target.

    This is the "tune ``t`` upward" step: the *level* of the tailings
    distribution is whatever makes the mass balance reproduce the observed mean
    recovery.  Recovery itself is never touched.  Recovery is strictly
    decreasing in the level, so bisection is exact and deterministic.  The
    bracket spans a tailings grade of 0.0001 % (recovery ~100 %) to 1.0 %
    (above the feed grade, i.e. nonsensical), so it contains the root by a wide
    margin for any plausible shape.
    """
    lo, hi = 1e-4, 1.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        r = two_product_recovery(feed_grade, conc_grade, mid * (1.0 + shape))
        if r.mean() > target_mean_recovery:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ---------------------------------------------------------------------------
# Table generators
# ---------------------------------------------------------------------------

def generate_crusher_states() -> pd.DataFrame:
    """Daily ``crusher_states`` for CRUSHER-03.

    ``feed_rate_tph`` and ``rotational_torque_nm`` are the daily means of the
    2-hourly telemetry; ``gap_size_setting_mm`` is the campaign schedule;
    ``bypass_valve_open`` is carried through from the frozen backup.
    """
    backup = _fetch_backup_crusher()
    daily = crusher_daily_from_telemetry()

    timestamps = backup["timestamp"].to_numpy()
    if not np.array_equal(timestamps, daily.index.to_numpy()):
        raise RuntimeError(
            "the CRUSHER-03 telemetry day grid does not match the crusher_states grid"
        )

    return pd.DataFrame(
        {
            "bypass_valve_open": backup["bypass_valve_open"].astype(bool).to_numpy(),
            "feed_rate_tph": np.round(daily["feed_rate_tph"].to_numpy(float), DP_CRUSHER),
            "gap_size_setting_mm": gap_schedule(),
            "rotational_torque_nm": np.round(
                daily["rotational_torque_nm"].to_numpy(float), DP_CRUSHER
            ),
            "asset_id": CRUSHER_ID,
            "timestamp": backup["timestamp"],
        }
    )


def generate_metallurgical_recovery(crusher: pd.DataFrame) -> pd.DataFrame:
    """Daily ``metallurgical_recovery`` with recovery computed from the grades."""
    z_feed = ou_process(
        N_DAYS, mu=0.0, sigma=1.0, phi=GRADE_PHI, seed=_component_seed("feed_grade")
    )
    z_indep = ou_process(
        N_DAYS, mu=0.0, sigma=1.0, phi=GRADE_PHI, seed=_component_seed("conc_grade")
    )
    z_conc = RHO_FEED_CONC * z_feed + math.sqrt(1.0 - RHO_FEED_CONC**2) * z_indep

    feed_grade = _uniform_marginal(z_feed, _MET["f_mean"], _MET["f_sd"])
    conc_grade = _uniform_marginal(z_conc, _MET["c_mean"], _MET["c_sd"])

    gap = crusher["gap_size_setting_mm"].to_numpy(float)
    feed_rate = crusher["feed_rate_tph"].to_numpy(float)

    shape = _tailings_shape(feed_grade, conc_grade, gap, feed_rate)
    level = _solve_tailings_level(shape, feed_grade, conc_grade, _MET["r_mean"])
    tailings_grade = level * (1.0 + shape)

    # Round the assays to their reporting precision FIRST, then compute
    # recovery from the rounded values, so that recomputing R from the stored
    # columns reproduces the stored number.
    feed_grade = np.round(feed_grade, DP_FEED_GRADE)
    conc_grade = np.round(conc_grade, DP_CONC_GRADE)
    tailings_grade = np.round(tailings_grade, DP_TAILINGS_GRADE)
    recovery = np.round(
        two_product_recovery(feed_grade, conc_grade, tailings_grade), DP_RECOVERY
    )

    return pd.DataFrame(
        {
            "concentrate_grade_pct": conc_grade,
            "recovery_rate_pct": recovery,
            "tailings_grade_pct": tailings_grade,
            "feed_grade_pct": feed_grade,
            "concentrator_id": CONCENTRATOR_ID,
            "timestamp": crusher["timestamp"],
        }
    )


# ---------------------------------------------------------------------------
# A5 window as timestamps (exported for tests and downstream tasks)
# ---------------------------------------------------------------------------

_GRID_T0 = pd.Timestamp(_MET["t0"].replace(" ", "T"))
A5_START: pd.Timestamp = _GRID_T0 + pd.Timedelta(days=A5_START_INDEX)
A5_END: pd.Timestamp = _GRID_T0 + pd.Timedelta(days=A5_END_INDEX)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def write_parquet(out_dir: Optional[Path] = None) -> None:
    """Generate both tables and write them to ``data/generated/``."""
    out_dir = Path(out_dir) if out_dir is not None else _GENERATED_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    crusher = generate_crusher_states()
    recovery = generate_metallurgical_recovery(crusher)

    crusher.to_parquet(out_dir / "crusher_states.parquet", index=False)
    recovery.to_parquet(out_dir / "metallurgical_recovery.parquet", index=False)

    r = recovery["recovery_rate_pct"]
    t = recovery["tailings_grade_pct"]
    f = recovery["feed_grade_pct"]
    inside = (
        (pd.to_datetime(recovery["timestamp"], utc=True) >= A5_START)
        & (pd.to_datetime(recovery["timestamp"], utc=True) <= A5_END)
    ).to_numpy()

    print(f"Wrote {len(crusher)} rows -> {out_dir / 'crusher_states.parquet'}")
    print(f"Wrote {len(recovery)} rows -> {out_dir / 'metallurgical_recovery.parquet'}")
    print("\nVerification:")
    print(f"  recovery  mean={r.mean():.4f} sd={r.std(ddof=1):.4f} "
          f"range=[{r.min():.2f}, {r.max():.2f}]  (stored mean {_MET['r_mean']})")
    print(f"  tailings  mean={t.mean():.5f} sd={t.std(ddof=1):.5f} "
          f"range=[{t.min():.3f}, {t.max():.3f}]  (stored mean {_MET['t_mean']})")
    print(f"  corr(recovery, tailings) = "
          f"{np.corrcoef(r, t)[0, 1]:.4f}   (want < -0.6)")
    print(f"  corr(recovery, feed)     = "
          f"{np.corrcoef(r, f)[0, 1]:.4f}   (want > 0.3)")
    print(f"  corr(gap, tailings)      = "
          f"{np.corrcoef(crusher['gap_size_setting_mm'], t)[0, 1]:.4f}")
    print(f"  A5 {A5_START.date()}..{A5_END.date()}: tailings "
          f"x{t[inside].mean() / t[~inside].mean():.3f}, "
          f"recovery {r[~inside].mean() - r[inside].mean():.3f} pp lower")


if __name__ == "__main__":
    write_parquet()
