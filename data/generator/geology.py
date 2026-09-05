"""Geology divergence generator — Task 7 (A7).

Rebuilds ``drill_assay_logs`` and ``geological_block_models`` so that the two
tables describe **one deposit** instead of two unrelated random populations,
and plants a single spatially contiguous zone (A7) where the assays come back
materially below the block model.  That divergence is what swarm S06
(Grade-to-Recovery Reconciliation) exists to discover; today it cannot, because
the two tables were generated independently.

What changes and what does not
------------------------------
Changed:  ``gold_grade_gpt``, ``copper_grade_pct``, ``geology_code`` on the
assays; ``gold_grade_gpt_est``, ``copper_grade_pct_est``, ``lithology_type``,
``specific_gravity`` on the blocks.
Unchanged (copied straight from the frozen backups):  every ID, ``logged_at``,
``depth_start_meters`` / ``depth_end_meters``, ``centroid_x/y/z``.  The spatial
skeleton and the schemas stay exactly as they are.

Source of truth
---------------
Calibration is read from the **frozen Task-1 backups** (``*_original_20260810``),
never the live tables: Task 8 overwrites the live copies with this module's
output, so reading live would make a re-run consume its own output and silently
stop being reproducible.  ``drill_holes`` is not in ``REWRITE_TABLES`` and has
no backup, so it is read live — it is already immutable.

The spatial join has to be constructed
--------------------------------------
``drill_assay_logs`` carries no coordinates, only ``drill_hole_id`` and a depth
interval.  An interval's 3-D position is obtained by desurveying its mid-depth
down the hole::

    inclination = |dip_degrees|                       (holes dip downwards)
    z = collar_elevation  - mid * sin(inclination)
    x = collar_easting    + mid * cos(inclination) * sin(azimuth)
    y = collar_northing   + mid * cos(inclination) * cos(azimuth)

**The brief's claim that every hole is vertical is wrong.**  Only 25 of the 30
holes have ``dip_degrees = -90``; DH-EXP-005 (-69.32), DH-EXP-010 (-73.84),
DH-EXP-023 (-84.64), DH-EXP-029 (-64.29) and DH-EXP-030 (-72.35) are inclined,
and DH-EXP-030 also carries a real azimuth (308.46).  The general desurvey
above is used instead of the brief's vertical shortcut; it reduces to the
shortcut for the 25 vertical holes, so nothing is lost.  Twelve holes carry a
non-zero azimuth but are vertical, where azimuth is meaningless — that is
handled correctly because ``cos(90 deg) = 0`` kills the horizontal term.

The model
---------
1.  **One 3-D grade field, shared by both tables.**  ``gaussian_field`` builds
    an approximately-Gaussian random field from random Fourier features (a
    finite sum of cosines with random frequencies), which gives a smooth,
    anisotropic, seed-reproducible field without needing scipy.  Horizontal
    correlation range 330 m, vertical 95 m — real orebodies are far more
    continuous along strike than across it.

2.  **Lithology domains** are a deterministic function of position alone, so an
    assay and a block at the same place always agree on the rock type:
      * ``OVERBURDEN`` — the top 30 m below the topographic surface, which is
        itself interpolated from the 30 collar elevations.  Barren waste.
      * ``QSP_ORE`` — a tabular lens dipping 28 deg east, half-thickness 55 m,
        its walls warped by a long-wavelength field so the contact is irregular
        rather than planar.  The ore host.
      * ``CHERT`` / ``GRANITE`` / ``BASALT`` — the remaining volume, split by
        thresholding a second smooth field, which yields large contiguous
        domains rather than a scatter.

3.  **Lognormal grades.**  ``ln(Au) = ln(m_lithology) - var/2 + sigma_s * F + nugget``.
    The ``-var/2`` makes ``m_lithology`` the arithmetic mean of the resulting
    lognormal.  ``F`` is the shared structural field; the nugget is the
    short-range sampling/analytical variance that only assays see.  Copper uses
    the same construction with its own lithology means and a field that is 55%
    correlated with gold's — a Cu-Au system, not two independent metals.

4.  **Domain-constrained inverse-distance interpolation** produces the block
    estimates from the assays: for each block, the 12 nearest assays *of the
    same lithology* are weighted by 1/d^2 in an anisotropic frame (vertical
    distance counts 3.2x, matching the field's anisotropy).  Estimating inside
    hard domain boundaries is standard resource practice and is what carries
    the lithology signal into the block model.  Interpolation happens in log
    space, so a block estimate is a weighted geometric mean of its samples —
    this is what makes the block model smoother and slightly lower-grade than
    the assays, exactly as observed in the original tables (block mean 0.392
    vs assay mean 0.466).

5.  **Estimation error grows with distance from drilling**:
    ``sigma_e(d) = 0.08 + 0.45 * (1 - exp(-d / 170))`` in log units, where d is
    the anisotropic distance to the nearest same-lithology sample.  A block
    sitting on a hole is nearly exact; a block 400 m out is a guess.

6.  **The A7 zone.**  An ellipsoid centred at (485500, 7432300, 400) with radii
    (235, 235, 125) m, holding 33 assay intervals and 112 blocks.  The block
    model is interpolated from the **pre-depletion** grades — the story is that
    the model was built from historic drilling, and the new assays came back
    45% low (``ZONE_A7_DEPLETION = 0.55``) because the zone is oxidised and
    leached.  So the model stays optimistic there and only the assays know.
    Copper is deliberately left alone inside A7: the divergence is a gold
    divergence, which keeps S06's signal unambiguous.

7.  **Specific gravity** is a per-lithology physical constant plus 0.035 of
    noise.  Today all five lithologies sit between 2.737 and 2.763, which is
    meaningless.  The new values are the textbook densities of the named rock
    types, which drops the overall mean from 2.749 to ~2.62 because
    unconsolidated overburden really is ~2.05 t/m3.  That is a deliberate
    correction, not drift.

Calibration and determinism
---------------------------
Every calibration number comes from ``data/profile/stats.json`` via
``config.STATS``; none is restated as a literal.  A single multiplicative
constant is fitted at runtime so the generated assay population reproduces the
observed mean gold and copper grades; the same constant is applied to the
blocks, so the block means are *not* forced and remain a genuine test of the
interpolation.

All randomness comes from ``numpy.random.default_rng`` seeded with ``SEED``
plus a fixed integer offset.  Nothing is seeded from ``hash()``, from set
iteration order or from dict ordering, and every array is built in an order
fixed by an SQL ``ORDER BY``, so output is byte-identical across processes with
different ``PYTHONHASHSEED``.
"""

from __future__ import annotations

import math
import os
import re
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import BACKUP_SUFFIX, DATASET, PROJECT_ID, SEED, STATS  # noqa: E402

# ---------------------------------------------------------------------------
# Calibration loaded from data/profile/stats.json (never restated as literals)
# ---------------------------------------------------------------------------

_ASSAY_STATS: dict = STATS["assay"][0]
_BLOCK_STATS: dict = STATS["blocks"][0]

#: Observed mean assay grades — the level the regenerated data must reproduce.
TARGET_ASSAY_AU: float = float(_ASSAY_STATS["au_mean"])
TARGET_ASSAY_CU: float = float(_ASSAY_STATS["cu_mean"])

# ---------------------------------------------------------------------------
# Design parameters (chosen by tuning — see the notes at the bottom of the file)
# ---------------------------------------------------------------------------

LITHOLOGIES: tuple[str, ...] = (
    "OVERBURDEN",
    "GRANITE",
    "CHERT",
    "BASALT",
    "QSP_ORE",
)

#: Arithmetic mean gold grade (g/t) of each lithology before global calibration.
AU_MEAN_BY_LITHOLOGY: dict[str, float] = {
    "OVERBURDEN": 0.13,
    "GRANITE": 0.33,
    "CHERT": 0.36,
    "BASALT": 0.45,
    "QSP_ORE": 1.30,
}

#: Arithmetic mean copper grade (%) of each lithology before global calibration.
#: BASALT is Cu-rich but Au-poor (mafic host), QSP_ORE carries both.
CU_MEAN_BY_LITHOLOGY: dict[str, float] = {
    "OVERBURDEN": 0.22,
    "GRANITE": 0.52,
    "CHERT": 0.66,
    "BASALT": 1.35,
    "QSP_ORE": 1.90,
}

#: Dry bulk specific gravity (t/m3) by rock type — textbook physical values.
SG_BY_LITHOLOGY: dict[str, float] = {
    "OVERBURDEN": 2.05,   # unconsolidated cover
    "CHERT": 2.56,        # porous silica
    "GRANITE": 2.68,      # felsic intrusive
    "QSP_ORE": 2.85,      # silicified, sulphide-bearing
    "BASALT": 2.98,       # mafic volcanic
}
#: Within-domain SG scatter.  Kept small (0.02) on purpose: the smallest gap
#: between two adjacent rock types here is 0.12 t/m3 (CHERT to GRANITE), so
#: this keeps every pair of lithologies separated by well over 3 SD.
SG_NOISE_SD: float = 0.02

#: Correlation ranges of the structural grade field: (east, north, vertical) m.
FIELD_RANGES: tuple[float, float, float] = (330.0, 330.0, 95.0)
#: Number of random Fourier modes used to synthesise the field.
FIELD_MODES: int = 384

#: Log-scale dispersion: structural (spatially correlated) and nugget (local).
AU_SIGMA_STRUCTURAL: float = 0.58
AU_SIGMA_NUGGET: float = 0.28
CU_SIGMA_STRUCTURAL: float = 0.40
CU_SIGMA_NUGGET: float = 0.22
#: How much of copper's structural field is shared with gold's.
CU_AU_FIELD_CORRELATION: float = 0.55

#: Lithology geometry.
OVERBURDEN_THICKNESS: float = 30.0            # m below the topographic surface
QSP_HALF_THICKNESS: float = 55.0              # m, half-thickness of the ore lens
QSP_DIP_DEGREES: float = 28.0                 # lens dips east
QSP_ANCHOR: tuple[float, float, float] = (485620.0, 7432520.0, 430.0)
QSP_WALL_WARP: float = 38.0                   # m of irregularity on the contacts
DOMAIN_THRESHOLD: float = 0.50                # splits CHERT / GRANITE / BASALT

#: Interpolation.
IDW_ANISOTROPY: tuple[float, float, float] = (1.0, 1.0, 3.2)
IDW_NEIGHBOURS: int = 12
IDW_MIN_DISTANCE: float = 8.0                 # m, avoids a divide-by-zero spike
EST_ERROR_FLOOR: float = 0.08                 # log-units at zero distance
EST_ERROR_RANGE: float = 0.45                 # extra log-units far from drilling
EST_ERROR_DECAY: float = 170.0                # m

#: The A7 divergence zone: a single ellipsoid.
ZONE_A7_CENTRE: np.ndarray = np.array([485500.0, 7432300.0, 400.0])
ZONE_A7_RADII: np.ndarray = np.array([235.0, 235.0, 125.0])
#: Multiplier applied to in-zone assay gold.  0.55 => assays run 45% low.
ZONE_A7_DEPLETION: float = 0.55

#: Reporting precision, matching the original tables.
GRADE_DECIMALS: int = 3
SG_DECIMALS: int = 2
#: Analytical detection limit (g/t and %) — grades are never zero or negative.
DETECTION_LIMIT: float = 0.001

#: RNG stream offsets.  Fixed integers, never derived from hash() or from
#: iteration order, so every stream is stable across interpreters.
_RNG_FIELD_AU: int = 101
_RNG_FIELD_CU: int = 202
_RNG_QSP_WARP: int = 303
_RNG_DOMAIN: int = 404
_RNG_NUGGET: int = 7
_RNG_EST_ERROR: int = 11
_RNG_SG: int = 13

# ---------------------------------------------------------------------------
# BigQuery source tables
#
# BigQuery cannot bind a table identifier to a query parameter (@params bind
# *values* only), so identifiers must be interpolated into the SQL text.  To
# make that obviously safe, every table this module reads is declared in the
# allow-list below and re-validated against a strict identifier pattern before
# interpolation.  No caller-supplied string ever reaches a query.
# ---------------------------------------------------------------------------

_SOURCE_TABLES: dict[str, str] = {
    # Frozen Task-1 backups — Task 8 overwrites the live copies of these.
    "assays": "drill_assay_logs" + BACKUP_SUFFIX,
    "blocks": "geological_block_models" + BACKUP_SUFFIX,
    # Not in REWRITE_TABLES, so the live table is already immutable.
    "holes": "drill_holes",
}

_TABLE_IDENTIFIER_RE = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]{0,1023}\Z")


def _table(key: str) -> str:
    """Return the fully-qualified id of an allow-listed source table."""
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
    """BigQuery client (deferred import so the module is importable offline)."""
    from google.cloud import bigquery

    return bigquery.Client(project=PROJECT_ID)


_GENERATED_DIR = Path(__file__).parent.parent / "generated"
ASSAY_PARQUET = _GENERATED_DIR / "drill_assay_logs.parquet"
BLOCK_PARQUET = _GENERATED_DIR / "geological_block_models.parquet"

_source_cache: Optional[tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]] = None


def fetch_source_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fetch ``(assays, blocks, holes)`` in a fixed, total row order.

    The ORDER BY clauses are what make row order — and therefore every RNG
    draw indexed by row — reproducible.  Each ordering is total: no two rows
    can tie on the full key.
    """
    global _source_cache
    if _source_cache is not None:
        return _source_cache

    client = _client()
    assays = client.query(f"""
        SELECT logged_at, gold_grade_gpt, depth_end_meters, depth_start_meters,
               copper_grade_pct, geology_code, drill_hole_id
        FROM `{_table('assays')}`
        ORDER BY drill_hole_id, depth_start_meters, depth_end_meters, logged_at
    """).to_dataframe().reset_index(drop=True)

    blocks = client.query(f"""
        SELECT gold_grade_gpt_est, copper_grade_pct_est, specific_gravity,
               lithology_type, centroid_z, centroid_y, centroid_x, block_id
        FROM `{_table('blocks')}`
        ORDER BY block_id
    """).to_dataframe().reset_index(drop=True)

    holes = client.query(f"""
        SELECT azimuth_degrees, dip_degrees, total_depth_meters,
               collar_elevation, collar_easting, collar_northing, drill_hole_id
        FROM `{_table('holes')}`
        ORDER BY drill_hole_id
    """).to_dataframe().reset_index(drop=True)

    _source_cache = (assays, blocks, holes)
    return _source_cache


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

def assay_coordinates(assays: pd.DataFrame, holes: pd.DataFrame) -> np.ndarray:
    """Desurvey each assay interval's mid-point to (east, north, elevation).

    Straight-hole desurvey — the survey table records one azimuth/dip per hole,
    so there is no deviation to integrate.  Handles inclined holes; see the
    module docstring on why the brief's vertical-only shortcut is not used.
    """
    m = assays.merge(holes, on="drill_hole_id", how="left", validate="many_to_one")
    if m["collar_easting"].isna().any():
        missing = sorted(set(assays["drill_hole_id"]) - set(holes["drill_hole_id"]))
        raise ValueError(f"assays reference unknown drill holes: {missing}")
    mid = (m["depth_start_meters"].to_numpy() + m["depth_end_meters"].to_numpy()) / 2.0
    inclination = np.radians(np.abs(m["dip_degrees"].to_numpy()))
    azimuth = np.radians(m["azimuth_degrees"].to_numpy())
    horizontal = mid * np.cos(inclination)
    return np.column_stack([
        m["collar_easting"].to_numpy() + horizontal * np.sin(azimuth),
        m["collar_northing"].to_numpy() + horizontal * np.cos(azimuth),
        m["collar_elevation"].to_numpy() - mid * np.sin(inclination),
    ])


def topography(x: np.ndarray, y: np.ndarray, holes: pd.DataFrame) -> np.ndarray:
    """Ground surface elevation, interpolated from the 30 collar elevations.

    Plain 2-D inverse-distance-squared.  Needed because ``OVERBURDEN`` is
    defined by depth below surface, and blocks have no drill hole to measure
    depth from.
    """
    hx = holes["collar_easting"].to_numpy()
    hy = holes["collar_northing"].to_numpy()
    hz = holes["collar_elevation"].to_numpy()
    d = np.sqrt((x[:, None] - hx[None, :]) ** 2 + (y[:, None] - hy[None, :]) ** 2) + 1.0
    w = 1.0 / d ** 2
    return (w * hz[None, :]).sum(axis=1) / w.sum(axis=1)


def gaussian_field(
    points: np.ndarray,
    ranges: tuple[float, float, float],
    seed: int,
    n_modes: int = FIELD_MODES,
) -> np.ndarray:
    """Approximately-Gaussian random field with a squared-exponential covariance.

    Random Fourier features:  f(p) = sqrt(2/M) * sum_k cos(w_k . p + phi_k),
    with w_k ~ N(0, diag(1/range^2)) and phi_k ~ U(0, 2*pi).  As M grows this
    converges to a zero-mean, unit-variance Gaussian process whose covariance is
    the anisotropic squared-exponential kernel with the requested ranges.

    Written out longhand because scipy is not available, and preferred over a
    gridded FFT field because it is defined at arbitrary points — assays and
    block centroids do not live on the same grid, and both must be evaluated
    against the *same* realisation for the two tables to describe one deposit.
    """
    rng = np.random.default_rng(seed)
    w = rng.normal(size=(n_modes, 3)) / np.asarray(ranges, dtype=float)[None, :]
    phase = rng.uniform(0.0, 2.0 * math.pi, size=n_modes)
    return math.sqrt(2.0 / n_modes) * np.cos(points @ w.T + phase[None, :]).sum(axis=1)


def lithology_at(points: np.ndarray, holes: pd.DataFrame, seed: int = SEED) -> np.ndarray:
    """Rock type at each point — a pure function of position.

    Because both tables call this with the same seed, an assay and a block at
    the same place always report the same rock type, which is what makes the
    lithology signal consistent between ``geology_code`` and ``lithology_type``.
    """
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    out = np.full(len(points), "GRANITE", dtype=object)

    # Three background domains from a smooth field: large contiguous bodies.
    domain = gaussian_field(points, (480.0, 480.0, 220.0), seed + _RNG_DOMAIN)
    out[domain < -DOMAIN_THRESHOLD] = "CHERT"
    out[domain > DOMAIN_THRESHOLD] = "BASALT"

    # The ore lens: a dipping tabular body with warped (irregular) walls.
    warp = gaussian_field(points, (420.0, 420.0, 260.0), seed + _RNG_QSP_WARP) * QSP_WALL_WARP
    dip = math.radians(QSP_DIP_DEGREES)
    normal = np.array([math.sin(dip), 0.15, math.cos(dip)])
    normal = normal / np.linalg.norm(normal)
    signed_distance = (points - np.asarray(QSP_ANCHOR)) @ normal + warp
    out[np.abs(signed_distance) < QSP_HALF_THICKNESS] = "QSP_ORE"

    # Overburden blankets everything else — it is the youngest unit.
    out[z > topography(x, y, holes) - OVERBURDEN_THICKNESS] = "OVERBURDEN"
    return out


def in_zone_a7(points: np.ndarray) -> np.ndarray:
    """Boolean mask: is each point inside the A7 divergence ellipsoid?"""
    rel = (np.asarray(points, dtype=float) - ZONE_A7_CENTRE) / ZONE_A7_RADII
    return np.sqrt((rel ** 2).sum(axis=1)) < 1.0


# ---------------------------------------------------------------------------
# Interpolation
# ---------------------------------------------------------------------------

def _domain_idw(
    targets: np.ndarray,
    target_lithology: np.ndarray,
    samples: np.ndarray,
    sample_lithology: np.ndarray,
    sample_log_values: np.ndarray,
    fallback_log_mean: dict[str, float],
) -> tuple[np.ndarray, np.ndarray]:
    """Domain-constrained inverse-distance interpolation in log space.

    Each target is estimated only from samples sharing its lithology — hard
    domain boundaries, as a real resource estimate uses, which is what carries
    the lithology grade signal into the block model.

    Returns ``(log_estimate, distance_to_nearest_sample)``.  The distance is in
    the anisotropic frame and drives the estimation error applied by the caller.
    """
    aniso = np.asarray(IDW_ANISOTROPY, dtype=float)
    estimate = np.empty(len(targets))
    nearest = np.empty(len(targets))
    for i in range(len(targets)):
        lith = target_lithology[i]
        candidates = np.flatnonzero(sample_lithology == lith)
        if candidates.size == 0:
            # No sample of this rock type anywhere: fall back to the domain
            # mean.  Treated as maximally uninformed, so it gets the full
            # estimation error.
            estimate[i] = fallback_log_mean[lith]
            nearest[i] = np.inf
            continue
        d = np.sqrt((((samples[candidates] - targets[i]) / aniso) ** 2).sum(axis=1))
        order = np.argsort(d, kind="stable")[:IDW_NEIGHBOURS]
        d = d[order]
        picked = candidates[order]
        nearest[i] = d[0]
        w = 1.0 / np.maximum(d, IDW_MIN_DISTANCE) ** 2
        estimate[i] = float((w * sample_log_values[picked]).sum() / w.sum())
    return estimate, nearest


def _estimation_error_sd(distance: np.ndarray) -> np.ndarray:
    """Log-scale estimation error as a function of distance to the nearest sample.

    Blocks sitting on a drill hole are nearly exact; blocks far from any hole
    are guesses.  Saturates at ``EST_ERROR_FLOOR + EST_ERROR_RANGE``.
    """
    d = np.where(np.isfinite(distance), distance, np.inf)
    return EST_ERROR_FLOOR + EST_ERROR_RANGE * (1.0 - np.exp(-d / EST_ERROR_DECAY))


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def generate_geology(seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Regenerate both tables from one shared spatial model.

    Returned as ``(drill_assay_logs, geological_block_models)``, each carrying
    its original schema and column order.
    """
    src_assays, src_blocks, holes = fetch_source_tables()

    assay_xyz = assay_coordinates(src_assays, holes)
    block_xyz = src_blocks[["centroid_x", "centroid_y", "centroid_z"]].to_numpy()

    assay_lith = lithology_at(assay_xyz, holes, seed=seed)
    block_lith = lithology_at(block_xyz, holes, seed=seed)

    # --- the shared structural field ---------------------------------------
    field_au = gaussian_field(assay_xyz, FIELD_RANGES, seed + _RNG_FIELD_AU)
    field_cu_indep = gaussian_field(assay_xyz, FIELD_RANGES, seed + _RNG_FIELD_CU)
    rho = CU_AU_FIELD_CORRELATION
    field_cu = rho * field_au + math.sqrt(1.0 - rho ** 2) * field_cu_indep

    # --- assay grades (lognormal) ------------------------------------------
    rng = np.random.default_rng(seed + _RNG_NUGGET)
    nugget_au = rng.normal(0.0, AU_SIGMA_NUGGET, size=len(assay_xyz))
    nugget_cu = rng.normal(0.0, CU_SIGMA_NUGGET, size=len(assay_xyz))

    var_au = AU_SIGMA_STRUCTURAL ** 2 + AU_SIGMA_NUGGET ** 2
    var_cu = CU_SIGMA_STRUCTURAL ** 2 + CU_SIGMA_NUGGET ** 2
    # -var/2 makes the lithology constant the *arithmetic* mean of the lognormal.
    log_mu_au = {k: math.log(v) - var_au / 2.0 for k, v in AU_MEAN_BY_LITHOLOGY.items()}
    log_mu_cu = {k: math.log(v) - var_cu / 2.0 for k, v in CU_MEAN_BY_LITHOLOGY.items()}

    log_au_assay = (
        np.array([log_mu_au[l] for l in assay_lith])
        + AU_SIGMA_STRUCTURAL * field_au
        + nugget_au
    )
    log_cu_assay = (
        np.array([log_mu_cu[l] for l in assay_lith])
        + CU_SIGMA_STRUCTURAL * field_cu
        + nugget_cu
    )

    # --- block estimates ----------------------------------------------------
    # Interpolated from the *pre-depletion* assay population: the block model
    # was built from historic drilling and never saw the A7 depletion, which is
    # precisely why it stays optimistic there.
    est_log_au, nn_au = _domain_idw(
        block_xyz, block_lith, assay_xyz, assay_lith, log_au_assay, log_mu_au
    )
    est_log_cu, _ = _domain_idw(
        block_xyz, block_lith, assay_xyz, assay_lith, log_cu_assay, log_mu_cu
    )

    rng_est = np.random.default_rng(seed + _RNG_EST_ERROR)
    sigma_e = _estimation_error_sd(nn_au)
    log_au_block = est_log_au + rng_est.normal(0.0, 1.0, size=len(block_xyz)) * sigma_e
    # Copper is estimated from the same drilling, so it inherits the same
    # distance-to-data structure, but base metals interpolate more smoothly.
    log_cu_block = est_log_cu + rng_est.normal(0.0, 1.0, size=len(block_xyz)) * sigma_e * 0.8

    # --- the A7 divergence --------------------------------------------------
    zone_assay = in_zone_a7(assay_xyz)
    au_assay = np.exp(log_au_assay) * np.where(zone_assay, ZONE_A7_DEPLETION, 1.0)
    cu_assay = np.exp(log_cu_assay)
    au_block = np.exp(log_au_block)
    cu_block = np.exp(log_cu_block)

    # --- global calibration to the observed assay means ---------------------
    # One scale constant per metal, fitted on the assays and applied unchanged
    # to the blocks, so the block means stay an emergent property.
    k_au = TARGET_ASSAY_AU / au_assay.mean()
    k_cu = TARGET_ASSAY_CU / cu_assay.mean()
    au_assay *= k_au
    au_block *= k_au
    cu_assay *= k_cu
    cu_block *= k_cu

    # --- specific gravity ---------------------------------------------------
    rng_sg = np.random.default_rng(seed + _RNG_SG)
    sg = np.array([SG_BY_LITHOLOGY[l] for l in block_lith]) + rng_sg.normal(
        0.0, SG_NOISE_SD, size=len(block_lith)
    )

    def _grade(v: np.ndarray) -> np.ndarray:
        return np.round(np.maximum(v, DETECTION_LIMIT), GRADE_DECIMALS)

    assays = src_assays.copy()
    assays["gold_grade_gpt"] = _grade(au_assay)
    assays["copper_grade_pct"] = _grade(cu_assay)
    assays["geology_code"] = pd.Series(assay_lith, index=assays.index).astype("string")

    blocks = src_blocks.copy()
    blocks["gold_grade_gpt_est"] = _grade(au_block)
    blocks["copper_grade_pct_est"] = _grade(cu_block)
    blocks["specific_gravity"] = np.round(sg, SG_DECIMALS)
    blocks["lithology_type"] = pd.Series(block_lith, index=blocks.index).astype("string")

    return assays, blocks


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_parquet(seed: int = SEED) -> None:
    """Generate both tables and write them to data/generated/.

    Called by Task 8's loader, or directly::

        python -m geology
    """
    _GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    assays, blocks = generate_geology(seed=seed)
    assays.to_parquet(ASSAY_PARQUET, index=False)
    blocks.to_parquet(BLOCK_PARQUET, index=False)
    print(f"  Written {len(assays)} rows -> {ASSAY_PARQUET}")
    print(f"  Written {len(blocks)} rows -> {BLOCK_PARQUET}")

    # --- verification summary ----------------------------------------------
    _, _, holes = fetch_source_tables()
    a_xyz = assay_coordinates(assays, holes)
    b_xyz = blocks[["centroid_x", "centroid_y", "centroid_z"]].to_numpy()
    d = np.sqrt(((a_xyz[:, None, :] - b_xyz[None, :, :]) ** 2).sum(axis=-1))
    nearest = d.argmin(axis=1)
    zone = in_zone_a7(a_xyz)
    au_a = assays["gold_grade_gpt"].to_numpy()
    au_b = blocks["gold_grade_gpt_est"].to_numpy()

    r = np.corrcoef(au_a[~zone], au_b[nearest[~zone]])[0, 1]
    depletion = 1.0 - au_a[zone].mean() / au_b[nearest[zone]].mean()
    by_a = assays.groupby("geology_code")["gold_grade_gpt"].mean()
    by_b = blocks.groupby("lithology_type")["gold_grade_gpt_est"].mean()

    def skew(v):
        v = np.asarray(v, dtype=float)
        return ((v - v.mean()) ** 3).mean() / v.std() ** 3

    print("\nVerification:")
    print(f"  corr(assay Au, nearest block Au_est) outside A7 = {r:.4f}")
    print(f"  A7: {int(zone.sum())} assays, {int(in_zone_a7(b_xyz).sum())} blocks, "
          f"assays {depletion:.1%} below model")
    print(f"  QSP_ORE / OVERBURDEN mean Au: assays "
          f"{by_a['QSP_ORE'] / by_a['OVERBURDEN']:.1f}x, blocks "
          f"{by_b['QSP_ORE'] / by_b['OVERBURDEN']:.1f}x")
    print(f"  Au mean: assays {au_a.mean():.4f} (target {TARGET_ASSAY_AU}), "
          f"blocks {au_b.mean():.4f} (target {_BLOCK_STATS['au_mean']})")
    print(f"  Cu mean: assays {assays['copper_grade_pct'].mean():.4f} "
          f"(target {TARGET_ASSAY_CU}), blocks "
          f"{blocks['copper_grade_pct_est'].mean():.4f} "
          f"(target {_BLOCK_STATS['cu_mean']})")
    print(f"  Au skew: raw {skew(au_a):+.3f} / log {skew(np.log(au_a)):+.3f} (assays), "
          f"raw {skew(au_b):+.3f} / log {skew(np.log(au_b)):+.3f} (blocks)")
    print(f"  SG by lithology: "
          f"{blocks.groupby('lithology_type')['specific_gravity'].mean().round(2).to_dict()}")


if __name__ == "__main__":
    write_parquet()


# ---------------------------------------------------------------------------
# Tuning notes (for reference, not executed)
# ---------------------------------------------------------------------------
# The free parameters are the per-lithology means, the two log-sigmas, the
# lithology geometry and the A7 ellipsoid.  They were tuned against the five
# verification thresholds; the achieved margins at SEED = 20260810 are:
#
#   corr(assay, nearest block) outside A7    0.78   (threshold > 0.60)
#   A7 depletion vs nearest block            47%    (threshold >= 25%)
#   A7 depletion vs all in-zone blocks       32%    (threshold >= 25%)
#   QSP_ORE / OVERBURDEN gold, assays        23x    (threshold >= 2x)
#   QSP_ORE / OVERBURDEN gold, blocks        21x    (threshold >= 2x)
#
# Sensitivities worth knowing before changing anything:
#  * AU_SIGMA_NUGGET is the main lever on the correlation.  It is the part of
#    an assay that no interpolator can reproduce, so raising it drops the
#    correlation roughly linearly.  At 0.45 the correlation falls below 0.60.
#  * FIELD_RANGES[2] (vertical range) matters more than the horizontal ones:
#    the assays span 62-577 m elevation while the blocks only span 325-550 m,
#    so ~15% of intervals have no block near them and contribute noise to the
#    correlation.  Shortening the vertical range below ~60 m breaks it.
#  * The A7 ellipsoid was placed at the densest cluster of assays that is also
#    well inside the block extent; smaller radii give too few intervals for the
#    depletion to be measurable, larger ones stop it being a "zone".
#  * ZONE_A7_DEPLETION = 0.55 yields 47% measured depletion rather than 45%
#    because the log-space interpolation makes in-zone block estimates a shade
#    lower than the depleted assay mean would suggest on its own.
