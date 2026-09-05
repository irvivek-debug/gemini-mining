"""Operator fatigue physiology generator — Task 5.

Rebuilds ``biometric_fatigue_logs`` and its mirror ``fatigue_logs_node`` so that
the Fatigue Intervention swarm can actually find what it is supposed to find.

The defect
----------
The original 3,340 rows were drawn independently per column.  Two consequences:

1. ``heart_rate_bpm`` correlated **-0.116** with ``sleep_deficit_hours``.
   Sleep debt raises resting heart rate; a negative coupling is backwards.
2. There was no time structure at all — no roster, no accumulation across
   consecutive night shifts, no recovery on days off.  Every row was an
   independent draw, so no operator could ever be seen "building toward" an
   incident.

Only the *joint* and *temporal* structure was wrong; the marginals were fine.
This module therefore keeps the observed marginals and rebuilds the structure.

Method
------
1. **Roster.**  A 14-day rotation — 7 day shifts, 2 days off, 5 night shifts —
   staggered across the 20 operators by a per-operator phase.
   ``operator_vehicle_assignments`` cannot drive this: it holds 5 rows, all
   dated 2026-06-18, which is two days *after* the 167-day fatigue window ends.
   Those 5 rows are instead honoured as the rotation's end state — each named
   operator's phase is chosen so the synthesised roster puts them on the shift
   type the assignment records for 2026-06-18.  Nothing contradicts the source.

2. **Sleep-debt recursion.**  Per operator, a damped accumulator over days::

       debt[t] = retention[shift] * debt[t-1] + load[shift] + noise[t]

   ``load`` is strongly positive on nights, mildly positive on days and negative
   on days off; ``retention`` is high on nights (debt carries over) and low on
   days off (debt is paid down).  ``noise`` is an OU process from ``common`` so
   consecutive days are correlated rather than independent.  A per-operator
   random effect makes some people chronically worse sleepers than others, and
   ``common.weekly_dip`` lightens the Sunday roster.

3. **Marginal calibration by rank mapping.**  The recursion produces a latent
   debt with the right *ordering* but an arbitrary scale.  Latent values are
   ranked across all 3,340 rows and pushed through a quantile function fitted to
   the profile.  See :func:`calibrate_two_piece` for why the target is a
   two-piece uniform and how its two parameters are solved from the STATS
   moments rather than copied from the old data.  The map is monotone, so every
   structural property built in step 2 survives it.

4. **Heart rate.**  A Gaussian copula: the HR score is
   ``rho * probit(deficit_rank) + sqrt(1-rho^2) * idiosyncratic``, and the score
   ranks are mapped onto the HR target distribution.  This reverses the sign of
   the coupling while reproducing the observed 50-84 integer band exactly —
   which a simple ``hr = a + b*deficit + noise`` cannot, because 84 sits only
   1.68 SD above the mean and any usable slope would pile rows onto the cap.

5. **Microsleeps.**  ``Poisson(exp(a + b*deficit))`` truncated at the observed
   maximum.  ``b`` is a design parameter (steepness); ``a`` is solved at runtime
   so the truncated expectation equals the profile's mean.

6. **Alerts.**  Policy: a microsleep was detected, or the deficit is at or above
   the statutory :data:`ALERT_DEFICIT_HOURS` threshold.

7. **The A6 case.**  ``OP-113`` is already a NIGHT operator in
   ``operator_vehicle_assignments`` and is already linked, through
   ``incident_involvements`` on ``TRUCK-03``, to ``INC-5059``.  Using them means
   the fatigue trail terminates at an incident that already exists.  A chronic
   sleep-debt episode is layered on their latent debt: a convex ramp over the
   three weeks before the incident date, peaking exactly on it, then decaying
   fast (post-incident stand-down).  The result crosses 6 h on the consecutive
   night shifts leading into the incident.

Source of truth
---------------
All reads come from the **frozen Task-1 backups** (``*_original_20260810``),
never the live tables: Task 8 overwrites the live copies with this module's
output, so reading live would make a re-run consume its own output and stop
being reproducible.  ``operators_node``, ``safety_incidents`` and
``incident_involvements`` are not rewritten by any task, so their live copies
are already immutable and are read directly.

This module never writes to BigQuery.  Task 8 owns loading.

Determinism
-----------
Every RNG stream is seeded from ``config.SEED`` combined with a
``hashlib.blake2b`` digest of the entity name.  The builtin ``hash()`` is never
used: it is salted per interpreter by ``PYTHONHASHSEED`` and silently produced
non-reproducible output in a sibling task.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import ou_process, weekly_dip  # noqa: E402
from config import BACKUP_SUFFIX, DATASET, PROJECT_ID, SCHEMAS, SEED, STATS  # noqa: E402

# ---------------------------------------------------------------------------
# Calibration loaded from data/profile/stats.json — never restated as literals
# ---------------------------------------------------------------------------

_F: dict = STATS["fatigue"][0]

N_OPERATORS: int = int(_F["ops"])
N_ROWS: int = int(_F["n"])

SD_MEAN: float = float(_F["sd_mean"])
SD_SD: float = float(_F["sd_sd"])
SD_MIN: float = float(_F["sd_min"])
SD_MAX: float = float(_F["sd_max"])

HR_MEAN: float = float(_F["hr_mean"])
HR_SD: float = float(_F["hr_sd"])
HR_MIN: float = float(_F["hr_min"])
HR_MAX: float = float(_F["hr_max"])

MS_MEAN: float = float(_F["ms_mean"])
MS_MAX: int = int(_F["ms_max"])

WINDOW_START: pd.Timestamp = pd.Timestamp(_F["t0"])
WINDOW_END: pd.Timestamp = pd.Timestamp(_F["t1"])

# ---------------------------------------------------------------------------
# Design parameters (chosen by tuning, not observed statistics — see the
# tuning notes at the bottom of this file)
# ---------------------------------------------------------------------------

#: Rotation shape: 7 day shifts, 2 days off, 5 night shifts.
ROSTER_DAY_SHIFTS: int = 7
ROSTER_OFF_DAYS: int = 2
ROSTER_NIGHT_SHIFTS: int = 5
ROSTER_CYCLE: int = ROSTER_DAY_SHIFTS + ROSTER_OFF_DAYS + ROSTER_NIGHT_SHIFTS

SHIFT_DAY = "DAY"
SHIFT_OFF = "OFF"
SHIFT_NIGHT = "NIGHT"

#: Debt added per day by shift type, in latent units.
SHIFT_LOAD: dict[str, float] = {SHIFT_DAY: 0.45, SHIFT_OFF: -0.60,
                                SHIFT_NIGHT: 1.25}

#: Fraction of yesterday's debt carried into today.  Low on days off — that is
#: what "recovery" means here.
SHIFT_RETENTION: dict[str, float] = {SHIFT_DAY: 0.55, SHIFT_OFF: 0.40,
                                     SHIFT_NIGHT: 0.85}

#: Stationary SD and lag-1 autocorrelation of the day-to-day disturbance.
NOISE_SD: float = 0.45
NOISE_PHI: float = 0.35

#: SD of the per-operator random effect (chronic sleep quality).
PERSONAL_SD: float = 0.35

#: Depth of the Sunday roster relief applied to positive shift loads.
WEEKLY_RELIEF: float = 0.25

#: Gaussian-copula coupling between deficit rank and heart-rate rank.
#: Tuned so Pearson corr(deficit, heart_rate) lands mid-band (see notes).
HR_DEFICIT_COUPLING: float = 0.48

#: Lag-1 autocorrelation of the idiosyncratic heart-rate component.
HR_NOISE_PHI: float = 0.30

#: Slope of log(microsleep rate) in hours of sleep deficit.
MICROSLEEP_LOG_SLOPE: float = 1.6

#: Statutory deficit at which a fatigue alert is raised regardless of whether a
#: microsleep was actually observed.
ALERT_DEFICIT_HOURS: float = 6.0

#: The planted A6 case.  Validated against the source tables in
#: :func:`resolve_a6_incident` rather than trusted blindly.
A6_OPERATOR: str = "OP-113"

#: Shape of the chronic sleep-debt episode layered on the A6 operator.
A6_RAMP_DAYS: int = 21
A6_RAMP_POWER: float = 3.0        # convex: most of the rise is in the last week
A6_DECAY_HALFLIFE_DAYS: float = 1.2
A6_DECAY_DAYS: int = 12
A6_PEAK: float = 5.5              # latent units added on the incident date

# ---------------------------------------------------------------------------
# BigQuery source tables
#
# BigQuery binds *values* to query parameters, never identifiers, so table and
# property-graph names have to be interpolated into the SQL text.  To make that
# obviously safe, every identifier this module can interpolate is declared in
# the allow-list below and re-validated against a strict pattern immediately
# before use.  No caller-supplied string ever reaches a query.
# ---------------------------------------------------------------------------

_SOURCE_TABLES: dict[str, str] = {
    # Frozen Task-1 backup — Task 8 overwrites the live copy of this one.
    "fatigue_node": "fatigue_logs_node" + BACKUP_SUFFIX,
    # Not in REWRITE_TABLES, so the live tables are already immutable.
    "operators": "operators_node",
}

_SAFETY_GRAPH = "MiningOperationsSafetyGraph"

_IDENTIFIER_RE = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]{0,1023}\Z")


def _table(key: str) -> str:
    """Return the fully-qualified id of an allow-listed source table."""
    try:
        name = _SOURCE_TABLES[key]
    except KeyError:
        raise KeyError(
            f"{key!r} is not an allow-listed source table "
            f"(allowed: {sorted(_SOURCE_TABLES)})"
        ) from None
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(f"refusing to interpolate table identifier {name!r}")
    return f"`{PROJECT_ID}`.`{DATASET}`.`{name}`"


def _client():
    from google.cloud import bigquery  # imported lazily: tests may run offline

    return bigquery.Client(project=PROJECT_ID)


_GENERATED_DIR = Path(__file__).parent.parent / "generated"


# ---------------------------------------------------------------------------
# Deterministic seeding
# ---------------------------------------------------------------------------

def entity_seed(*parts: str) -> int:
    """Derive a stable 32-bit RNG seed from SEED and the given entity names.

    ``hashlib.blake2b`` rather than the builtin ``hash()``: the latter is salted
    per interpreter by ``PYTHONHASHSEED``, which makes output non-reproducible
    across processes.
    """
    digest = hashlib.blake2b("|".join(parts).encode("utf-8"),
                             digest_size=8).digest()
    return (SEED + int.from_bytes(digest, "big")) % (2 ** 32)


# ---------------------------------------------------------------------------
# Marginal calibration
# ---------------------------------------------------------------------------

def calibrate_two_piece(mean: float, sd: float, lo: float,
                        hi: float) -> tuple[float, float]:
    """Fit a two-piece uniform to a mean, an SD and a support.

    The target is ``U(lo, knee)`` with probability ``1 - w`` and
    ``U(knee, hi)`` with probability ``w``.

    Why this family: the profile records ``mean 2.131, SD 1.359, support
    [0, 8]``.  The maximum sits ``(8 - 2.131) / 1.359 = 4.3`` SDs above the
    mean, so no light-tailed unimodal law can produce it — the distribution
    *must* be a narrow bulk plus a thin heavy tail.  Two pieces is the smallest
    family with that shape, and it has exactly two free parameters, so the two
    recorded moments determine it uniquely.  Nothing is copied from the old
    row counts; ``knee`` and ``w`` are solved from STATS.

    Returns ``(knee, w)``.  Bisection on the second moment; the first moment is
    satisfied exactly for every candidate knee by construction.
    """
    target_second_moment = sd * sd + mean * mean

    def weight_for(knee: float) -> float:
        bulk_mean = (lo + knee) / 2.0
        tail_mean = (knee + hi) / 2.0
        return (mean - bulk_mean) / (tail_mean - bulk_mean)

    def residual(knee: float) -> float:
        w = weight_for(knee)
        bulk_m2 = (lo * lo + lo * knee + knee * knee) / 3.0
        tail_m2 = (knee * knee + knee * hi + hi * hi) / 3.0
        return (1.0 - w) * bulk_m2 + w * tail_m2 - target_second_moment

    low, high = lo + 1e-9, hi - 1e-9
    if residual(low) * residual(high) > 0:
        raise ValueError(
            f"no two-piece uniform on [{lo}, {hi}] has mean {mean} and SD {sd}")
    for _ in range(200):
        mid = 0.5 * (low + high)
        if residual(low) * residual(mid) <= 0:
            high = mid
        else:
            low = mid
    knee = 0.5 * (low + high)
    return knee, weight_for(knee)


def two_piece_quantile(u: np.ndarray, knee: float, w: float, lo: float,
                       hi: float) -> np.ndarray:
    """Quantile function of the distribution fitted by :func:`calibrate_two_piece`."""
    out = np.empty_like(u, dtype=float)
    bulk = u < (1.0 - w)
    out[bulk] = lo + (knee - lo) * u[bulk] / (1.0 - w)
    out[~bulk] = knee + (hi - knee) * (u[~bulk] - (1.0 - w)) / w
    return out


def uniform_ranks(values: np.ndarray) -> np.ndarray:
    """Map values to (0, 1) by rank.  Ties broken by position, so deterministic."""
    order = np.argsort(values, kind="stable")
    ranks = np.empty(len(values), dtype=float)
    ranks[order] = np.arange(len(values), dtype=float)
    return (ranks + 0.5) / len(values)


def probit(p: np.ndarray) -> np.ndarray:
    """Inverse standard-normal CDF (Acklam's rational approximation).

    scipy is not installed in this environment, so this is written out.  Peak
    absolute error is ~1.15e-9 over the whole open unit interval, which is far
    below anything that could move a correlation in the fourth decimal.
    """
    a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00)
    p = np.asarray(p, dtype=float)
    out = np.empty_like(p)
    break_point = 0.02425
    low, high = p < break_point, p > 1.0 - break_point
    mid = ~(low | high)

    q = np.sqrt(-2.0 * np.log(p[low]))
    out[low] = ((((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q
                 + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1))

    q = np.sqrt(-2.0 * np.log(1.0 - p[high]))
    out[high] = -((((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q
                   + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1))

    q = p[mid] - 0.5
    r = q * q
    out[mid] = ((((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r
                 + a[5]) * q
                / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1))
    return out


# ---------------------------------------------------------------------------
# BigQuery reads
# ---------------------------------------------------------------------------

_GRID_CACHE: pd.DataFrame | None = None
_OPERATOR_CACHE: list[str] | None = None
_A6_CACHE: dict | None = None


def load_grid() -> pd.DataFrame:
    """The (timestamp, operator_id, log_id) grid, from the frozen backup.

    ``log_id`` is carried over rather than re-minted.  It is the ``FatigueLog``
    node key *and* the ``LOGGED_FOR`` edge key in
    ``MiningOperationsSafetyGraph``; re-minting it would invalidate every id a
    demo transcript, cached agent trace or provenance panel already quotes.
    """
    global _GRID_CACHE
    if _GRID_CACHE is None:
        sql = (
            "SELECT log_id, timestamp, operator_id "
            f"FROM {_table('fatigue_node')} "
            "ORDER BY timestamp, operator_id"
        )
        _GRID_CACHE = _client().query(sql).to_dataframe()
    return _GRID_CACHE.copy()


def load_operator_ids() -> list[str]:
    """Operator ids that exist as ``Operator`` nodes in the safety graph."""
    global _OPERATOR_CACHE
    if _OPERATOR_CACHE is None:
        sql = f"SELECT operator_id FROM {_table('operators')} ORDER BY operator_id"
        _OPERATOR_CACHE = _client().query(sql).to_dataframe()[
            "operator_id"].tolist()
    return list(_OPERATOR_CACHE)


def resolve_a6_incident() -> dict:
    """Resolve the A6 operator to a real incident through the property graph.

    Runs the swarm's canonical S10/S05 traversal
    (``Operator -> Vehicle <- Incident``) so the returned incident is one the
    agents can actually reach, not merely one that shares an id in two tables.
    Where several incidents involve the operator's vehicle, the one the
    operator is personally named on is preferred, then the earliest.

    Note the direction of ``INVOLVED_IN``.  The graph DDL declares
    ``SOURCE KEY (vehicle_id) ... DESTINATION KEY (incident_id)``, so the edge
    runs Vehicle -> Incident.  ``docs/phase-3-design.md`` writes this traversal
    with the arrow reversed (``<-[:incident_involvements]-``); that form returns
    zero rows against the deployed graph.
    """
    global _A6_CACHE
    if _A6_CACHE is not None:
        return dict(_A6_CACHE)

    from google.cloud import bigquery

    if not _IDENTIFIER_RE.match(_SAFETY_GRAPH):
        raise ValueError(f"refusing to interpolate graph name {_SAFETY_GRAPH!r}")

    sql = f"""
        SELECT operator_id, vehicle_id, incident_id, involved_operator_id,
               incident_timestamp
        FROM GRAPH_TABLE(
          {_SAFETY_GRAPH}
          MATCH (o:Operator WHERE o.operator_id = @operator_id)
                -[:OPERATES]-> (v:Vehicle)
                -[e:INVOLVED_IN]-> (i:Incident)
          COLUMNS (o.operator_id AS operator_id,
                   v.vehicle_id AS vehicle_id,
                   i.incident_id AS incident_id,
                   e.operator_id AS involved_operator_id,
                   i.timestamp AS incident_timestamp)
        )
        ORDER BY involved_operator_id = @operator_id DESC, incident_timestamp
        LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("operator_id", "STRING", A6_OPERATOR)
        ],
        default_dataset=f"{PROJECT_ID}.{DATASET}",
    )
    rows = _client().query(sql, job_config=job_config).to_dataframe()
    if rows.empty:
        raise RuntimeError(
            f"{A6_OPERATOR} does not resolve to an incident through "
            f"{_SAFETY_GRAPH}; the A6 case cannot be planted")

    row = rows.iloc[0]
    incident_ts = pd.Timestamp(row["incident_timestamp"])
    if not (WINDOW_START <= incident_ts <= WINDOW_END):
        raise RuntimeError(
            f"incident {row['incident_id']} at {incident_ts} lies outside the "
            f"fatigue window {WINDOW_START}..{WINDOW_END}")

    _A6_CACHE = {
        "operator_id": str(row["operator_id"]),
        "vehicle_id": str(row["vehicle_id"]),
        "incident_id": str(row["incident_id"]),
        "incident_timestamp": incident_ts,
    }
    return dict(_A6_CACHE)


# ---------------------------------------------------------------------------
# Roster
# ---------------------------------------------------------------------------

def _assignments() -> list[dict]:
    """The five real ``operator_vehicle_assignments`` rows, from the profile."""
    return sorted(STATS["operator_assignments"], key=lambda r: r["operator_id"])


def _cycle_day_to_shift(cycle_day: int) -> str:
    if cycle_day < ROSTER_DAY_SHIFTS:
        return SHIFT_DAY
    if cycle_day < ROSTER_DAY_SHIFTS + ROSTER_OFF_DAYS:
        return SHIFT_OFF
    return SHIFT_NIGHT


def _shift_slots(shift_type: str) -> list[int]:
    return [d for d in range(ROSTER_CYCLE)
            if _cycle_day_to_shift(d) == shift_type]


def operator_phases() -> dict[str, int]:
    """Per-operator offset into the 14-day rotation.

    Two requirements pull against each other and both are met:

    * The five operators named in ``operator_vehicle_assignments`` must be on
      the shift type that table records for 2026-06-18.  Because the window
      starts on a day whose index is a multiple of ``ROSTER_CYCLE`` away from
      2026-06-18, the phase *is* the cycle day on that date, so the constraint
      is just "phase must fall in the right slot range".
    * The A6 operator must be mid-night-block on the incident date.  Of the five
      night phases, only the last two put them on nights then, and the last one
      also leaves them on nights at the end of the window (consistent with the
      assignment).  Hence the A6 operator takes the final night slot.

    Remaining operators are spread over the cycle so roughly 11 are on days,
    2 off and 7 on nights on any given date.  The assignment order is by sorted
    operator id and sorted phase — no set or dict iteration order is relied on.
    """
    operators = sorted(load_grid()["operator_id"].unique().tolist())
    assignments = {row["operator_id"]: row["shift_type"]
                   for row in _assignments()}

    # 20 operators over a 14-day cycle: every phase once, plus 6 extras spread
    # evenly so no single date is left unstaffed.
    pool = list(range(ROSTER_CYCLE)) + [0, 2, 4, 6, 9, 11]

    fixed: dict[str, int] = {}
    # A6 operator first: it needs the *last* night slot specifically.
    if A6_OPERATOR in assignments:
        if assignments[A6_OPERATOR] != SHIFT_NIGHT:
            raise RuntimeError(
                f"{A6_OPERATOR} is assigned {assignments[A6_OPERATOR]}, not "
                f"{SHIFT_NIGHT}; the A6 night-block story does not apply")
        fixed[A6_OPERATOR] = _shift_slots(SHIFT_NIGHT)[-1]

    # Remaining named operators: earliest free slot of the recorded shift type.
    for operator_id in sorted(assignments):
        if operator_id in fixed:
            continue
        taken = set(fixed.values())
        for slot in _shift_slots(assignments[operator_id]):
            if slot not in taken:
                fixed[operator_id] = slot
                break
        else:  # pragma: no cover - 5 assignments, 7 day and 5 night slots
            raise RuntimeError(
                f"no free {assignments[operator_id]} phase for {operator_id}")

    for phase in fixed.values():
        pool.remove(phase)
    pool.sort()

    phases = dict(fixed)
    for operator_id, phase in zip(
            [o for o in operators if o not in fixed], pool):
        phases[operator_id] = phase
    return phases


def _window_dates() -> pd.DatetimeIndex:
    return pd.DatetimeIndex(sorted(load_grid()["timestamp"].unique()))


def _cycle_day(operator_id: str, timestamp: pd.Timestamp,
               phases: dict[str, int] | None = None) -> int:
    phases = operator_phases() if phases is None else phases
    day_index = (pd.Timestamp(timestamp).normalize()
                 - WINDOW_START.normalize()).days
    return (day_index + phases[operator_id]) % ROSTER_CYCLE


def roster_shift(operator_id: str, timestamp) -> str:
    """Shift type for one operator on one date.

    Defined for any date, including the 2026-06-18 assignment date that lies
    outside the fatigue window — that is how the real assignment rows are
    checked against the synthesised rotation.
    """
    return _cycle_day_to_shift(_cycle_day(operator_id, timestamp))


def build_roster() -> pd.DataFrame:
    """Long-form roster over the fatigue window.

    Columns: ``operator_id``, ``timestamp``, ``shift_type``, ``night_index``
    (0-based position within the night block, ``-1`` off nights).
    """
    phases = operator_phases()
    dates = _window_dates()
    day_index = np.arange(len(dates))
    frames = []
    for operator_id in sorted(phases):
        cycle_day = (day_index + phases[operator_id]) % ROSTER_CYCLE
        shift = np.where(
            cycle_day < ROSTER_DAY_SHIFTS, SHIFT_DAY,
            np.where(cycle_day < ROSTER_DAY_SHIFTS + ROSTER_OFF_DAYS,
                     SHIFT_OFF, SHIFT_NIGHT))
        night_index = np.where(
            shift == SHIFT_NIGHT,
            cycle_day - (ROSTER_DAY_SHIFTS + ROSTER_OFF_DAYS), -1)
        frames.append(pd.DataFrame({
            "operator_id": operator_id,
            "timestamp": dates,
            "shift_type": shift,
            "night_index": night_index.astype(int),
        }))
    return (pd.concat(frames, ignore_index=True)
            .sort_values(["timestamp", "operator_id"])
            .reset_index(drop=True))


# ---------------------------------------------------------------------------
# Latent sleep-debt process
# ---------------------------------------------------------------------------

def a6_episode(day_index: np.ndarray, incident_index: int) -> np.ndarray:
    """Chronic sleep-debt overlay for the A6 operator, in latent units.

    Convex rise over :data:`A6_RAMP_DAYS` so most of the escalation lands in the
    final week (the earlier night block is only mildly lifted, which keeps the
    peak on the incident date rather than one rotation earlier), then a fast
    exponential decay representing the post-incident stand-down.
    """
    offset = day_index - incident_index
    bump = np.zeros(len(day_index), dtype=float)

    rising = (offset >= -A6_RAMP_DAYS) & (offset <= 0)
    bump[rising] = A6_PEAK * (1.0 + offset[rising] / A6_RAMP_DAYS) ** A6_RAMP_POWER

    falling = (offset > 0) & (offset <= A6_DECAY_DAYS)
    bump[falling] = A6_PEAK * 0.5 ** (offset[falling] / A6_DECAY_HALFLIFE_DAYS)
    return bump


def latent_debt(roster: pd.DataFrame, incident_index: int) -> pd.DataFrame:
    """Run the sleep-debt recursion for every operator.

    Returns the roster with a ``latent`` column added.
    """
    dates = _window_dates()
    n_days = len(dates)
    day_index = np.arange(n_days)
    relief = weekly_dip(dates.values.astype("datetime64[ns]"), WEEKLY_RELIEF)

    pieces = []
    for operator_id, group in roster.groupby("operator_id", sort=True):
        group = group.sort_values("timestamp").reset_index(drop=True)
        shifts = group["shift_type"].to_numpy()

        disturbance = ou_process(n_days, 0.0, NOISE_SD, NOISE_PHI,
                                 entity_seed(operator_id, "sleep-noise"))
        personal = np.random.default_rng(
            entity_seed(operator_id, "sleep-personal")).normal(0.0, PERSONAL_SD)

        debt = np.empty(n_days, dtype=float)
        carried = 0.0
        for t in range(n_days):
            shift = shifts[t]
            load = SHIFT_LOAD[shift]
            # The Sunday relief lightens work, it does not shorten recovery, so
            # it scales positive loads only.
            if load > 0:
                load *= relief[t]
            carried = SHIFT_RETENTION[shift] * carried + load + disturbance[t]
            debt[t] = carried

        latent = debt + personal
        if operator_id == A6_OPERATOR:
            latent = latent + a6_episode(day_index, incident_index)

        group["latent"] = latent
        pieces.append(group)

    return (pd.concat(pieces, ignore_index=True)
            .sort_values(["timestamp", "operator_id"])
            .reset_index(drop=True))


# ---------------------------------------------------------------------------
# Observable columns
# ---------------------------------------------------------------------------

def sleep_deficit_from_latent(latent: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Map latent debt onto the calibrated deficit marginal.

    Returns ``(deficit_hours, rank_uniforms)``; the uniforms are reused as the
    copula input for heart rate.
    """
    knee, weight = calibrate_two_piece(SD_MEAN, SD_SD, SD_MIN, SD_MAX)
    u = uniform_ranks(latent)
    deficit = np.round(two_piece_quantile(u, knee, weight, SD_MIN, SD_MAX), 2)
    return deficit, u


def heart_rate_from_deficit(deficit_uniforms: np.ndarray,
                            operator_ids: np.ndarray) -> np.ndarray:
    """Integer heart rate, positively coupled to sleep deficit.

    The target marginal is fitted to the *reflected* variable
    ``(hr_min + hr_max) - hr`` so the same two-piece calibrator can be used: the
    observed heart-rate distribution has its thin tail at the **low** end
    (a handful of rows in 50-59 under a broad 60-84 bulk), which reflection
    turns into the tail-at-top shape :func:`calibrate_two_piece` assumes.
    """
    reflection = HR_MIN + HR_MAX
    knee, weight = calibrate_two_piece(reflection - HR_MEAN, HR_SD,
                                       HR_MIN, HR_MAX)

    # Idiosyncratic component: OU per operator, so an individual's heart rate
    # drifts across consecutive days instead of resampling independently.
    noise = np.empty(len(deficit_uniforms), dtype=float)
    for operator_id in np.unique(operator_ids):
        mask = operator_ids == operator_id
        noise[mask] = ou_process(int(mask.sum()), 0.0, 1.0, HR_NOISE_PHI,
                                 entity_seed(str(operator_id), "heart-rate"))

    rho = HR_DEFICIT_COUPLING
    score = rho * probit(deficit_uniforms) + math.sqrt(1.0 - rho ** 2) * noise

    # Higher score -> higher heart rate -> lower reflected value.
    reflected = two_piece_quantile(uniform_ranks(-score), knee, weight,
                                   HR_MIN, HR_MAX)
    return np.clip(np.rint(reflection - reflected),
                   HR_MIN, HR_MAX).astype(np.int64)


def _truncated_poisson_mean(rate: np.ndarray, cap: int) -> np.ndarray:
    """E[min(X, cap)] for X ~ Poisson(rate), via sum_{k<cap} P(X > k)."""
    total = np.zeros_like(rate)
    pmf = np.exp(-rate)
    cdf = pmf.copy()
    for k in range(cap):
        total += 1.0 - cdf
        pmf = pmf * rate / (k + 1)
        cdf = cdf + pmf
    return total


def microsleeps_from_deficit(deficit: np.ndarray) -> np.ndarray:
    """Poisson counts whose rate rises exponentially with sleep deficit.

    The intercept is solved so the *truncated* expectation matches the profile
    mean — solving on the untruncated rate would overshoot, because the cap at
    ``ms_max`` discards mass from the high-deficit rows where the rate is large.
    The solve uses the analytic expectation, so the intercept does not depend on
    the draw and therefore not on the seed.
    """
    slope = MICROSLEEP_LOG_SLOPE
    low, high = -40.0, 5.0
    for _ in range(200):
        mid = 0.5 * (low + high)
        if _truncated_poisson_mean(np.exp(mid + slope * deficit),
                                   MS_MAX).mean() > MS_MEAN:
            high = mid
        else:
            low = mid
    intercept = 0.5 * (low + high)
    rate = np.exp(intercept + slope * deficit)
    draws = np.random.default_rng(entity_seed("microsleep")).poisson(rate)
    return np.clip(draws, 0, MS_MAX).astype(np.int64)


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def generate() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build ``(biometric_fatigue_logs, fatigue_logs_node)``.

    The two frames are built from a single set of arrays, so they cannot drift
    apart; only the column set and order differ.
    """
    grid = load_grid().sort_values(["timestamp", "operator_id"]).reset_index(
        drop=True)
    if len(grid) != N_ROWS:
        raise RuntimeError(
            f"backup grid has {len(grid)} rows, profile says {N_ROWS}")

    a6 = resolve_a6_incident()
    dates = _window_dates()
    incident_index = int(
        (pd.Timestamp(a6["incident_timestamp"]).normalize()
         - WINDOW_START.normalize()).days)

    roster = build_roster()
    frame = latent_debt(roster, incident_index)

    # Align the roster/latent frame onto the backup grid's row order.
    frame = grid.merge(frame, on=["timestamp", "operator_id"], how="left",
                       validate="one_to_one")
    if frame["latent"].isna().any():
        raise RuntimeError("roster does not cover every row of the backup grid")

    deficit, uniforms = sleep_deficit_from_latent(frame["latent"].to_numpy())
    heart_rate = heart_rate_from_deficit(uniforms,
                                         frame["operator_id"].to_numpy())
    microsleeps = microsleeps_from_deficit(deficit)
    alerts = (microsleeps > 0) | (deficit >= ALERT_DEFICIT_HOURS)

    timestamps = pd.to_datetime(frame["timestamp"], utc=True).astype(
        "datetime64[us, UTC]")

    biometric = pd.DataFrame({
        "sleep_deficit_hours": deficit.astype(np.float64),
        "microsleep_events_detected": microsleeps,
        "fatigue_alert_triggered": alerts.astype(bool),
        "timestamp": timestamps,
        "heart_rate_bpm": heart_rate,
        "operator_id": frame["operator_id"].astype(str),
    })[[c["name"] for c in SCHEMAS["schemas"]["biometric_fatigue_logs"]["columns"]]]

    node = biometric.copy()
    node["log_id"] = frame["log_id"].astype(str)
    node = node[[c["name"]
                 for c in SCHEMAS["schemas"]["fatigue_logs_node"]["columns"]]]

    return biometric.reset_index(drop=True), node.reset_index(drop=True)


def write_parquet() -> None:
    """Generate both tables and write them to ``data/generated/``.

    Task 8's loader reads from there.  This module never writes to BigQuery.
    """
    _GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    biometric, node = generate()

    bio_path = _GENERATED_DIR / "biometric_fatigue_logs.parquet"
    node_path = _GENERATED_DIR / "fatigue_logs_node.parquet"
    biometric.to_parquet(bio_path, index=False)
    node.to_parquet(node_path, index=False)
    print(f"  Written {len(biometric)} rows -> {bio_path}")
    print(f"  Written {len(node)} rows -> {node_path}")

    deficit = biometric["sleep_deficit_hours"]
    heart_rate = biometric["heart_rate_bpm"]
    microsleeps = biometric["microsleep_events_detected"]
    a6 = resolve_a6_incident()
    trail = biometric[biometric["operator_id"] == A6_OPERATOR]
    peak = trail.loc[trail["sleep_deficit_hours"].idxmax()]

    print("\nVerification:")
    print(f"  corr(sleep_deficit_hours, heart_rate_bpm)   = "
          f"{deficit.corr(heart_rate):+.4f}   (was -0.1156)")
    print(f"  corr(sleep_deficit_hours, microsleep_events) = "
          f"{deficit.corr(microsleeps):+.4f}   (was +0.4665)")
    print(f"  sleep_deficit: mean={deficit.mean():.3f} (target {SD_MEAN}) "
          f"sd={deficit.std(ddof=1):.3f} (target {SD_SD}) "
          f"range=[{deficit.min()}, {deficit.max()}]")
    print(f"  heart_rate:    mean={heart_rate.mean():.3f} (target {HR_MEAN}) "
          f"sd={heart_rate.std(ddof=1):.3f} (target {HR_SD}) "
          f"range=[{heart_rate.min()}, {heart_rate.max()}]")
    print(f"  microsleeps:   mean={microsleeps.mean():.4f} (target {MS_MEAN}) "
          f"max={microsleeps.max()} nonzero={(microsleeps > 0).sum()}")
    print(f"  alerts:        {int(biometric['fatigue_alert_triggered'].sum())} "
          f"(observed {_F['alerts']})")
    print(f"  A6 {A6_OPERATOR}: peak {peak['sleep_deficit_hours']} h on "
          f"{peak['timestamp'].date()}; incident {a6['incident_id']} on "
          f"{pd.Timestamp(a6['incident_timestamp']).date()} "
          f"via {a6['vehicle_id']}")


if __name__ == "__main__":
    write_parquet()


# ---------------------------------------------------------------------------
# Tuning notes (for reference, not executed)
# ---------------------------------------------------------------------------
# SHIFT_LOAD / SHIFT_RETENTION set the steady states of the recursion:
#   night  1.25 / (1 - 0.85) = 8.3   reached from ~-0.7 over 5 nights -> ~4.3
#   day    0.45 / (1 - 0.55) = 1.0   decayed to from ~4.3 over 7 days  -> ~1.0
#   off   -0.60 / (1 - 0.40) = -1.0  two days is enough to clear the block
# so night-block debt rises monotonically, the day block pays most of it back
# and the two days off finish the job.  Measured group means after the rank
# map: NIGHT 2.90, DAY 2.05, OFF 0.51 hours; by night index 1.31 -> 4.23.
#
# HR_DEFICIT_COUPLING is the copula rho, not the Pearson correlation of the
# output.  Rounding to integers and the two-piece marginal attenuate it:
#   rho 0.42 -> 0.390   rho 0.45 -> 0.418   rho 0.48 -> 0.453
#   rho 0.50 -> 0.468   rho 0.53 -> 0.497
# 0.48 was chosen to sit in the middle of the brief's [0.35, 0.55] band with
# room on both sides.
#
# MICROSLEEP_LOG_SLOPE trades nonzero-row count against correlation, with the
# intercept re-solved for each slope so the mean always hits 0.076:
#   b 1.0 -> corr 0.451, 164 nonzero    b 1.3 -> corr 0.484, 123 nonzero
#   b 1.6 -> corr 0.494, 100 nonzero    b 1.8 -> corr 0.495, 101 nonzero
# 1.6 reproduces the observed 98 alerting rows most closely while keeping the
# correlation inside [0.40, 0.60].
#
# A6_PEAK was raised until the operator's maximum landed on the incident date
# rather than on the previous night block:
#   4.5 -> peak 2026-04-23 (wrong block)   5.5 -> peak 2026-05-04   6.5 -> 05-04
# 5.5 is the smallest value that puts the peak in the right place, so the
# planted case is as gentle as it can be while still being unambiguous.
