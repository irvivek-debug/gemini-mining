"""Tests for data/generator/geology.py — Task 7 (A7 geology divergence).

Verifies:
  - the constructed spatial join: assay 3-D positions are recomputed here from
    ``drill_holes`` by an independent desurvey, not taken from the module
  - outside the A7 zone, corr(assay gold, nearest block's estimate) > 0.6
  - inside the A7 zone, assayed gold averages >= 25% below the modelled grade
  - QSP_ORE mean gold >= 2x OVERBURDEN mean, in both tables
  - specific_gravity differs by lithology_type far beyond within-lithology noise
  - gold grades are lognormal by an explicit, scipy-free criterion
  - lithology is spatially coherent (contiguous domains, not scattered)
  - block estimation error grows with distance from the nearest drill hole
  - schemas, row counts, IDs and the spatial skeleton are untouched
  - grades are non-negative and copper is physically plausible
  - calibration reads the frozen backups, not the live tables
  - byte-identical output across two processes with different PYTHONHASHSEED

The lognormality criterion (stated explicitly, implementable without scipy):

    a population of grades is accepted as lognormal when
        (a) the raw grades are materially right-skewed:  skew(g)      >  1.0
        (b) the log-grades are near-symmetric:          |skew(ln g)|  <  0.40
        (c) the log-grades are not heavy-tailed:  |excess kurt(ln g)| <  1.00

    The original tables fail this: their raw gold skew is ~0.0 (near-uniform,
    not right-skewed) and their log-grade skew is ~-1.6 to -2.0 (strongly
    left-skewed logs).  Both (a) and (b) are violated.  Skewness and kurtosis
    are scale-invariant, so the generator's mean calibration cannot fake them.
"""

import hashlib
import math
import os
import subprocess
import sys

# abspath matters: config.py locates data/profile/ relative to its own __file__,
# so an unnormalised ".." on sys.path would send it looking in tests/profile/.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
import pytest

from config import BACKUP_SUFFIX, SEED, STATS
from geology import (
    ASSAY_PARQUET,
    BLOCK_PARQUET,
    LITHOLOGIES,
    SG_BY_LITHOLOGY,
    ZONE_A7_CENTRE,
    ZONE_A7_DEPLETION,
    ZONE_A7_RADII,
    _SOURCE_TABLES,
    fetch_source_tables,
    generate_geology,
    in_zone_a7,
)

# ---------------------------------------------------------------------------
# Thresholds — taken verbatim from the brief
# ---------------------------------------------------------------------------
MIN_CORRELATION = 0.60          # outside the zone, assay vs nearest block
MIN_ZONE_DEPLETION = 0.25       # inside the zone, assays >= 25% below model
MIN_QSP_OVER_OVERBURDEN = 2.0   # QSP_ORE mean gold >= 2x OVERBURDEN mean

# Lognormality criterion (see module docstring)
LOGNORM_MIN_RAW_SKEW = 1.0
LOGNORM_MAX_ABS_LOG_SKEW = 0.40
LOGNORM_MAX_ABS_LOG_EXCESS_KURT = 1.00

# "Roughly where they are" — the brief keeps the means, not the spread.
MEAN_TOLERANCE = 0.20

_ASSAY_STATS = STATS["assay"][0]
_BLOCK_STATS = STATS["blocks"][0]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def generated():
    assays, blocks = generate_geology(seed=SEED)
    return assays, blocks


@pytest.fixture(scope="module")
def sources():
    return fetch_source_tables()


@pytest.fixture(scope="module")
def assay_xyz(generated, sources):
    """Assay 3-D positions, desurveyed here rather than imported.

    This is a deliberately independent reimplementation of the spatial join:
    if geology.py's own desurvey were wrong, importing it would hide the error.
    """
    assays, _ = generated
    _, _, holes = sources
    m = assays.merge(holes, on="drill_hole_id", how="left", validate="many_to_one")
    assert m["collar_easting"].notna().all(), "every assay must match a drill hole"
    mid = (m["depth_start_meters"].to_numpy() + m["depth_end_meters"].to_numpy()) / 2.0
    inclination = np.radians(np.abs(m["dip_degrees"].to_numpy()))
    azimuth = np.radians(m["azimuth_degrees"].to_numpy())
    return np.column_stack([
        m["collar_easting"].to_numpy() + mid * np.cos(inclination) * np.sin(azimuth),
        m["collar_northing"].to_numpy() + mid * np.cos(inclination) * np.cos(azimuth),
        m["collar_elevation"].to_numpy() - mid * np.sin(inclination),
    ])


@pytest.fixture(scope="module")
def block_xyz(generated):
    _, blocks = generated
    return blocks[["centroid_x", "centroid_y", "centroid_z"]].to_numpy()


@pytest.fixture(scope="module")
def nearest_block(assay_xyz, block_xyz):
    """Index of the nearest block centroid for each assay interval."""
    d = np.sqrt(((assay_xyz[:, None, :] - block_xyz[None, :, :]) ** 2).sum(axis=-1))
    return d.argmin(axis=1)


@pytest.fixture(scope="module")
def zone_mask(assay_xyz):
    return in_zone_a7(assay_xyz)


# ---------------------------------------------------------------------------
# Helpers (no scipy available)
# ---------------------------------------------------------------------------

def skewness(v) -> float:
    v = np.asarray(v, dtype=float)
    return float(((v - v.mean()) ** 3).mean() / v.std() ** 3)


def excess_kurtosis(v) -> float:
    v = np.asarray(v, dtype=float)
    return float(((v - v.mean()) ** 4).mean() / v.std() ** 4 - 3.0)


def anova_f(groups) -> float:
    """One-way ANOVA F statistic, computed by hand."""
    groups = [np.asarray(g, dtype=float) for g in groups if len(g) > 1]
    n = sum(len(g) for g in groups)
    k = len(groups)
    grand = np.concatenate(groups).mean()
    ss_between = sum(len(g) * (g.mean() - grand) ** 2 for g in groups)
    ss_within = sum(((g - g.mean()) ** 2).sum() for g in groups)
    return float((ss_between / (k - 1)) / (ss_within / (n - k)))


def assert_lognormal(values, label):
    raw_skew = skewness(values)
    log_skew = skewness(np.log(values))
    log_kurt = excess_kurtosis(np.log(values))
    assert raw_skew > LOGNORM_MIN_RAW_SKEW, (
        f"{label}: raw grades not right-skewed (skew={raw_skew:.3f})"
    )
    assert abs(log_skew) < LOGNORM_MAX_ABS_LOG_SKEW, (
        f"{label}: log-grades not symmetric (skew={log_skew:.3f})"
    )
    assert abs(log_kurt) < LOGNORM_MAX_ABS_LOG_EXCESS_KURT, (
        f"{label}: log-grades heavy-tailed (excess kurt={log_kurt:.3f})"
    )


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------

class TestSourceProvenance:
    @pytest.mark.parametrize("key", ["assays", "blocks"])
    def test_reads_frozen_backup_not_live_table(self, key):
        """Task 8 overwrites the live tables; reading them would make a re-run
        consume its own output."""
        assert _SOURCE_TABLES[key].endswith(BACKUP_SUFFIX)

    def test_drill_holes_read_live(self):
        """drill_holes is not in REWRITE_TABLES, so it has no backup."""
        assert _SOURCE_TABLES["holes"] == "drill_holes"

    def test_holes_are_not_all_vertical(self, sources):
        """The brief asserted every hole is vertical.  It is not true, so the
        generator must desurvey properly rather than assume dip = -90."""
        _, _, holes = sources
        assert (holes["dip_degrees"] != -90.0).any(), (
            "if every hole really were vertical this test should be deleted"
        )


# ---------------------------------------------------------------------------
# Schema / skeleton preservation
# ---------------------------------------------------------------------------

class TestSchemaPreserved:
    def test_assay_row_count(self, generated):
        assays, _ = generated
        assert len(assays) == _ASSAY_STATS["n"]

    def test_block_row_count(self, generated):
        _, blocks = generated
        assert len(blocks) == _BLOCK_STATS["n"]

    def test_assay_columns_unchanged(self, generated, sources):
        assays, _ = generated
        src, _, _ = sources
        assert list(assays.columns) == list(src.columns)

    def test_block_columns_unchanged(self, generated, sources):
        _, blocks = generated
        _, src, _ = sources
        assert list(blocks.columns) == list(src.columns)

    def test_spatial_skeleton_and_ids_untouched(self, generated, sources):
        """IDs, timestamps, depths and centroids must be byte-for-byte as today."""
        assays, blocks = generated
        src_a, src_b, _ = sources
        for col in ["drill_hole_id", "logged_at", "depth_start_meters", "depth_end_meters"]:
            pd.testing.assert_series_equal(
                assays[col].reset_index(drop=True), src_a[col].reset_index(drop=True)
            )
        for col in ["block_id", "centroid_x", "centroid_y", "centroid_z"]:
            pd.testing.assert_series_equal(
                blocks[col].reset_index(drop=True), src_b[col].reset_index(drop=True)
            )

    def test_timestamps_are_utc(self, generated):
        assays, _ = generated
        assert str(assays["logged_at"].dt.tz) == "UTC"

    def test_lithology_values_unchanged(self, generated):
        assays, blocks = generated
        assert set(assays["geology_code"]) <= set(LITHOLOGIES)
        assert set(blocks["lithology_type"]) <= set(LITHOLOGIES)

    def test_every_lithology_is_represented(self, generated):
        """A domain model that collapsed to one rock type would still satisfy
        every grade test below, so pin the mix."""
        assays, blocks = generated
        for lith in LITHOLOGIES:
            assert (assays["geology_code"] == lith).sum() >= 10, lith
            assert (blocks["lithology_type"] == lith).sum() >= 50, lith


# ---------------------------------------------------------------------------
# Physical plausibility
# ---------------------------------------------------------------------------

class TestPhysicalPlausibility:
    def test_gold_never_negative(self, generated):
        assays, blocks = generated
        assert (assays["gold_grade_gpt"] > 0).all()
        assert (blocks["gold_grade_gpt_est"] > 0).all()

    def test_copper_never_negative(self, generated):
        assays, blocks = generated
        assert (assays["copper_grade_pct"] > 0).all()
        assert (blocks["copper_grade_pct_est"] > 0).all()

    def test_copper_upper_percentile_plausible(self, generated):
        """The 99th percentile is not clipped by the generator, so this is a
        real constraint on the chosen dispersion, not a restatement of a clip."""
        assays, blocks = generated
        assert np.percentile(assays["copper_grade_pct"], 99) < 4.0
        assert np.percentile(blocks["copper_grade_pct_est"], 99) < 4.0

    def test_gold_mean_roughly_preserved(self, generated):
        """Only the assay mean is calibrated by the generator; the block mean
        is an emergent property of the interpolation and can drift."""
        _, blocks = generated
        target = _BLOCK_STATS["au_mean"]
        got = blocks["gold_grade_gpt_est"].mean()
        assert abs(got - target) / target < MEAN_TOLERANCE, got

    def test_copper_mean_roughly_preserved(self, generated):
        _, blocks = generated
        target = _BLOCK_STATS["cu_mean"]
        got = blocks["copper_grade_pct_est"].mean()
        assert abs(got - target) / target < MEAN_TOLERANCE, got

    def test_gold_dispersion_realistic(self, generated):
        """Real gold populations have CV ~0.8-1.5.  The original tables sat at
        0.55 (near-uniform); a value at either extreme is wrong."""
        assays, _ = generated
        cv = assays["gold_grade_gpt"].std(ddof=1) / assays["gold_grade_gpt"].mean()
        assert 0.7 < cv < 1.6, cv


# ---------------------------------------------------------------------------
# Lognormality
# ---------------------------------------------------------------------------

class TestLognormality:
    def test_assay_gold_is_lognormal(self, generated):
        assays, _ = generated
        assert_lognormal(assays["gold_grade_gpt"], "assay gold")

    def test_block_gold_is_lognormal(self, generated):
        _, blocks = generated
        assert_lognormal(blocks["gold_grade_gpt_est"], "block gold")

    def test_original_tables_fail_the_same_criterion(self, sources):
        """A criterion that everything passes is worthless.  The brief says the
        current data does not pass — confirm that on the frozen backups."""
        src_a, src_b, _ = sources
        with pytest.raises(AssertionError):
            assert_lognormal(src_a["gold_grade_gpt"], "original assay gold")
        with pytest.raises(AssertionError):
            assert_lognormal(src_b["gold_grade_gpt_est"], "original block gold")


# ---------------------------------------------------------------------------
# Lithology control
# ---------------------------------------------------------------------------

class TestLithologyControl:
    def test_qsp_ore_gold_at_least_double_overburden_assays(self, generated):
        assays, _ = generated
        by = assays.groupby("geology_code")["gold_grade_gpt"].mean()
        assert by["QSP_ORE"] / by["OVERBURDEN"] >= MIN_QSP_OVER_OVERBURDEN, by.to_dict()

    def test_qsp_ore_gold_at_least_double_overburden_blocks(self, generated):
        _, blocks = generated
        by = blocks.groupby("lithology_type")["gold_grade_gpt_est"].mean()
        assert by["QSP_ORE"] / by["OVERBURDEN"] >= MIN_QSP_OVER_OVERBURDEN, by.to_dict()

    def test_qsp_ore_is_the_richest_lithology(self, generated):
        assays, blocks = generated
        assert assays.groupby("geology_code")["gold_grade_gpt"].mean().idxmax() == "QSP_ORE"
        assert blocks.groupby("lithology_type")["gold_grade_gpt_est"].mean().idxmax() == "QSP_ORE"

    def test_overburden_is_the_barren_lithology(self, generated):
        assays, blocks = generated
        assert assays.groupby("geology_code")["gold_grade_gpt"].mean().idxmin() == "OVERBURDEN"
        assert blocks.groupby("lithology_type")["gold_grade_gpt_est"].mean().idxmin() == "OVERBURDEN"

    def test_lithology_is_spatially_coherent(self, block_xyz, generated):
        """Rock types occur in contiguous domains.  Measured as: the fraction of
        face-adjacent block pairs sharing a lithology must far exceed what
        random scattering of the same mix would give."""
        _, blocks = generated
        lith = blocks["lithology_type"].to_numpy()
        p = blocks["lithology_type"].value_counts(normalize=True).to_numpy()
        random_expectation = float((p ** 2).sum())

        # Face-adjacency on the regular 10x10x10 grid.  The grid step differs
        # per axis (100 m east/north, 25 m vertical), so each axis gets its own.
        pairs = []
        for axis in range(3):
            other = [a for a in range(3) if a != axis]
            delta = np.abs(block_xyz[:, None, axis] - block_xyz[None, :, axis])
            step = np.min(delta[delta > 0])
            aligned = np.ones((len(lith), len(lith)), dtype=bool)
            for a in other:
                aligned &= np.isclose(block_xyz[:, None, a], block_xyz[None, :, a])
            pairs.append(np.triu(np.isclose(delta, step) & aligned, k=1))
        i, j = np.where(pairs[0] | pairs[1] | pairs[2])
        assert len(i) == 2700, f"adjacency detection failed ({len(i)} pairs)"
        same = float((lith[i] == lith[j]).mean())
        assert same > 2.0 * random_expectation, (
            f"lithology looks scattered: {same:.3f} adjacent-same vs "
            f"{random_expectation:.3f} expected at random"
        )

    def test_original_lithology_carries_no_grade_signal(self, sources):
        """Control: the same QSP/OVERBURDEN ratio on the frozen backups is ~1."""
        src_a, src_b, _ = sources
        a = src_a.groupby("geology_code")["gold_grade_gpt"].mean()
        b = src_b.groupby("lithology_type")["gold_grade_gpt_est"].mean()
        assert a["QSP_ORE"] / a["OVERBURDEN"] < MIN_QSP_OVER_OVERBURDEN
        assert b["QSP_ORE"] / b["OVERBURDEN"] < MIN_QSP_OVER_OVERBURDEN


# ---------------------------------------------------------------------------
# Specific gravity
# ---------------------------------------------------------------------------

class TestSpecificGravity:
    def test_sg_differs_by_lithology_beyond_noise(self, generated):
        _, blocks = generated
        groups = [
            blocks.loc[blocks["lithology_type"] == lith, "specific_gravity"].to_numpy()
            for lith in LITHOLOGIES
        ]
        f = anova_f(groups)
        assert f > 100.0, f"SG barely separates by lithology (F={f:.1f})"

    def test_every_pair_of_lithologies_separates(self, generated):
        """Beyond noise means every pair, not just the extremes: each pair of
        lithology means must be at least 3 pooled within-group SDs apart."""
        _, blocks = generated
        g = blocks.groupby("lithology_type")["specific_gravity"]
        means, sds = g.mean(), g.std(ddof=1)
        pooled = float(np.sqrt((sds ** 2).mean()))
        for a in LITHOLOGIES:
            for b in LITHOLOGIES:
                if a < b:
                    assert abs(means[a] - means[b]) > 3.0 * pooled, (a, b, pooled)

    def test_denser_rock_types_carry_higher_sg(self, generated):
        """Observed ordering must follow the physical ordering of the constants."""
        _, blocks = generated
        observed = blocks.groupby("lithology_type")["specific_gravity"].mean()
        expected_order = sorted(LITHOLOGIES, key=lambda l: SG_BY_LITHOLOGY[l])
        assert list(observed.sort_values().index) == expected_order

    def test_sg_physically_plausible(self, generated):
        _, blocks = generated
        assert blocks["specific_gravity"].between(1.7, 3.4).all()

    def test_original_sg_does_not_separate(self, sources):
        """Control: today all five lithologies sit within 0.03 of each other."""
        _, src_b, _ = sources
        groups = [
            src_b.loc[src_b["lithology_type"] == lith, "specific_gravity"].to_numpy()
            for lith in LITHOLOGIES
        ]
        assert anova_f(groups) < 10.0


# ---------------------------------------------------------------------------
# The shared spatial model
# ---------------------------------------------------------------------------

class TestSpatialAgreement:
    def test_assays_and_blocks_share_a_coordinate_frame(self, assay_xyz, block_xyz):
        """Sanity check on the constructed join: most assays must land inside
        or close to the block model extent, otherwise 'nearest block' is
        meaningless and the correlation below would be vacuous."""
        d = np.sqrt(((assay_xyz[:, None, :] - block_xyz[None, :, :]) ** 2).sum(-1))
        assert np.median(d.min(axis=1)) < 80.0

    def test_correlation_outside_zone(self, generated, nearest_block, zone_mask):
        assays, blocks = generated
        outside = ~zone_mask
        r = np.corrcoef(
            assays.loc[outside, "gold_grade_gpt"].to_numpy(),
            blocks["gold_grade_gpt_est"].to_numpy()[nearest_block[outside]],
        )[0, 1]
        assert r > MIN_CORRELATION, f"assay-vs-nearest-block correlation {r:.4f}"

    def test_original_tables_have_no_spatial_agreement(
        self, sources, nearest_block, zone_mask
    ):
        """Control: the same statistic on the frozen backups is ~0, which is the
        whole reason S06 cannot work today."""
        src_a, src_b, _ = sources
        outside = ~zone_mask
        r = np.corrcoef(
            src_a.loc[outside, "gold_grade_gpt"].to_numpy(),
            src_b["gold_grade_gpt_est"].to_numpy()[nearest_block[outside]],
        )[0, 1]
        assert abs(r) < 0.2, r

    def test_block_error_grows_with_distance_from_drilling(
        self, generated, sources, block_xyz
    ):
        """Blocks far from any hole must carry more estimation error.  Measured
        without access to the truth: the discrepancy between a block and the
        nearest assay of the same lithology, versus distance to that assay."""
        assays, blocks = generated
        _, _, holes = sources
        collars = holes[["collar_easting", "collar_northing"]].to_numpy()
        d = np.sqrt(
            ((block_xyz[:, None, :2] - collars[None, :, :]) ** 2).sum(-1)
        ).min(axis=1)
        lith_mean = blocks.groupby("lithology_type")["gold_grade_gpt_est"].transform("mean")
        resid = np.abs(np.log(blocks["gold_grade_gpt_est"] / lith_mean)).to_numpy()
        near, far = d < np.median(d), d >= np.median(d)
        assert resid[far].mean() > resid[near].mean(), (
            resid[near].mean(), resid[far].mean()
        )


# ---------------------------------------------------------------------------
# The A7 divergence zone
# ---------------------------------------------------------------------------

class TestZoneA7:
    def test_zone_is_a_meaningful_size(self, zone_mask, block_xyz):
        assert zone_mask.sum() >= 20, "too few assays in A7 to be discoverable"
        assert zone_mask.mean() < 0.30, "A7 is a zone, not half the deposit"
        assert in_zone_a7(block_xyz).sum() >= 20

    def test_zone_is_contiguous(self, assay_xyz, zone_mask):
        """Every in-zone assay must be within one ellipsoid radius of the
        centre — i.e. the zone is a single connected body, not a scatter."""
        rel = (assay_xyz[zone_mask] - ZONE_A7_CENTRE) / ZONE_A7_RADII
        assert (np.sqrt((rel ** 2).sum(axis=1)) <= 1.0).all()

    def test_assays_run_below_the_model_inside_the_zone(
        self, generated, nearest_block, zone_mask
    ):
        assays, blocks = generated
        assayed = assays.loc[zone_mask, "gold_grade_gpt"].mean()
        modelled = blocks["gold_grade_gpt_est"].to_numpy()[nearest_block[zone_mask]].mean()
        depletion = 1.0 - assayed / modelled
        assert depletion >= MIN_ZONE_DEPLETION, (
            f"A7 depletion only {depletion:.1%} (assayed {assayed:.3f} vs "
            f"modelled {modelled:.3f})"
        )

    def test_zone_blocks_are_optimistic_too(self, generated, block_xyz, zone_mask):
        """Measured against every block inside the zone, not just the nearest
        ones — S06 will compare zone aggregates."""
        assays, blocks = generated
        assayed = assays.loc[zone_mask, "gold_grade_gpt"].mean()
        modelled = blocks.loc[in_zone_a7(block_xyz), "gold_grade_gpt_est"].mean()
        assert 1.0 - assayed / modelled >= MIN_ZONE_DEPLETION

    def test_no_such_divergence_outside_the_zone(
        self, generated, nearest_block, zone_mask
    ):
        """The divergence must be localised, otherwise S06 finds nothing to
        localise.  Outside A7, assays and model agree within 20%."""
        assays, blocks = generated
        outside = ~zone_mask
        assayed = assays.loc[outside, "gold_grade_gpt"].mean()
        modelled = blocks["gold_grade_gpt_est"].to_numpy()[nearest_block[outside]].mean()
        assert abs(1.0 - assayed / modelled) < 0.20, (assayed, modelled)

    def test_depletion_factor_is_actually_applied(self):
        assert 0.0 < ZONE_A7_DEPLETION < 1.0 - MIN_ZONE_DEPLETION


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

_DETERMINISM_SCRIPT = """
import hashlib, os, sys
sys.path.insert(0, {gen_dir!r})
import geology
a, b = geology.generate_geology()
h = hashlib.md5()
for df in (a, b):
    h.update(df.to_csv(index=False).encode())
print(h.hexdigest())
"""


class TestDeterminism:
    def test_identical_across_processes_with_different_hash_seeds(self):
        """PYTHONHASHSEED salts str.__hash__, so an RNG seeded from hash() gives
        different data per process.  Two in-process calls cannot detect that."""
        gen_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        script = _DETERMINISM_SCRIPT.format(gen_dir=gen_dir)
        digests = []
        for hash_seed in ("0", "12345"):
            env = dict(os.environ, PYTHONHASHSEED=hash_seed)
            out = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True, text=True, check=True, env=env,
            )
            digests.append(out.stdout.strip().splitlines()[-1])
        assert digests[0] == digests[1], digests

    def test_written_parquet_matches_generated_frames(self, generated):
        """The files Task 8 loads must be the frames these tests checked."""
        assays, blocks = generated
        for df, path in ((assays, ASSAY_PARQUET), (blocks, BLOCK_PARQUET)):
            assert path.exists(), f"{path} not written — run python -m geology"
            pd.testing.assert_frame_equal(
                pd.read_parquet(path).reset_index(drop=True),
                df.reset_index(drop=True),
            )
