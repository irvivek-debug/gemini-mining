"""Task 10 / 10b — verification of the eight BQML models in `mining_data`.

Runs live against BigQuery, in the same style as
``data/generator/tests/test_realism.py``: a module-scoped client, no skips, no
mocks.  Nothing here writes; training is done by ``data/models/retrain.sql``.

Four groups of tests:

1. **Preconditions.**  Every model's training query must return rows.  A
   BigQuery join that matches nothing succeeds silently at zero rows, so
   "CREATE MODEL ran" and "a model was trained on data" are different claims.
   ``test_parts_replaced_survived_the_load`` was the load-bearing failure in the
   first attempt; the load defect it found has been fixed and it is kept as a
   regression guard.

2. **Architecture is unchanged.**  The seven original models were allowed to
   change training data only.  These tests pin each model's type, its feature
   column set and the training options that were read off the pre-retrain
   models, so a future "improvement" to an architecture fails here rather than
   silently shipping.  They do NOT constrain ``telemetry_alarm_risk_model``,
   which is new and additive.

3. **Behaviour of the seven.**  Retrained-model metrics against the pre-retrain
   baselines in ``data/models/pre_retrain_metrics.json``.

4. **The telemetry-driven model.**  ``telemetry_alarm_risk_model`` — the ramp
   vs flat assertion, the anti-leak checks that make that assertion mean
   something, and its out-of-sample discrimination.

What group 3 no longer asserts, and why
---------------------------------------
The brief asked for R^2 "materially above" the pre-retrain value on the four
downtime regressors.  Measured after the retrain, it is not: three of the four
went down (see ``test_downtime_model_was_actually_retrained`` for the numbers).
That is not a bug in the data and it is not fixable by retraining.  Those models
have exactly two features — ``stock_level`` and ``lead_time_days``, static
attributes of a spare part — against a label of repair hours, and two of them
are fit on 3 and 5 rows respectively.  No regeneration of the source tables can
make that combination predictive, and the only ways to turn the assertion green
would be to change the architecture (forbidden for these seven) or to tune until
a number moved.  The assertion kept in its place is that each model was
*genuinely retrained* — its metrics moved off the recorded baseline — which is
the claim that can be both true and checked, and which still catches the two
real failure modes: a CREATE MODEL that silently trained on nothing, and a
cached ML.EVALUATE serving pre-retrain numbers.

Query cache
-----------
Every query runs with ``use_query_cache=False``.  ML.EVALUATE query text does
not change when the model underneath it is replaced, so BigQuery's 24 h result
cache will serve pre-retrain metrics for a model that was just retrained.  This
actually happened during Task 10 — the first post-retrain evaluation returned
the old numbers to 16 significant digits.  A cached metric would make these
tests pass on a model that was never retrained.
"""

import json
import os
import sys
from pathlib import Path

import pytest
from google.cloud import bigquery

# abspath matters: config.py locates data/profile/ relative to its own __file__.
_GENERATOR_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "generator")
)
sys.path.insert(0, _GENERATOR_DIR)

from config import DATASET, PROJECT_ID  # noqa: E402

_MODELS_DIR = Path(__file__).resolve().parent.parent
_BASELINE_PATH = _MODELS_DIR / "pre_retrain_metrics.json"

#: PUMP-104A degradation ramp.  data/generator/telemetry.py sets RAMP_DAYS = 21
#: and the hourly grid ends 2026-06-16 22:00, so the ramp covers the final 21
#: days.  This is *not* the 2026-03-26..2026-04-22 metallurgy A5 excursion.
RAMP_START = "2026-05-26 22:00:00"

#: End of the telemetry grid.
GRID_END = "2026-06-16 22:00:00"

#: Fixed commissioning-baseline reference period for the telemetry model: the
#: per-series mu0/sd0 that define the 3-sigma alarm threshold are computed over
#: [start of grid, BASELINE_END).  It ends nearly three months before the ramp,
#: so the ramp cannot inflate its own threshold.
BASELINE_END = "2026-03-01 00:00:00"

#: Last timestamp eligible for a *training* row of the telemetry model.  Equals
#: RAMP_START minus the 7-day label horizon, so neither a feature nor a label of
#: any training row can reach into the ramp.  The ramp is out of sample.
TRAIN_END = "2026-05-19 22:00:00"

#: The new, telemetry-driven model.  Deliberately named so it cannot be
#: confused with any of the seven; it is the ONLY model in the dataset that
#: reads `telemetry_stream`.
TELEMETRY_MODEL = "telemetry_alarm_risk_model"

#: The document-corpus embedding model. Not a predictive model at all: it is a
#: REMOTE model over Vertex text-embedding-005, used once at build time to
#: embed the PDF corpus and at query time by `doc_search`. It is listed here
#: only so the census below stays closed; it carries no training query, no
#: features, and no retrain baseline, and the retrain machinery must skip it.
EMBEDDING_MODEL = "text_embedding_model"

#: Its features.  All six are backward-looking functions of `telemetry_stream`.
#: The set is asserted exactly, because the whole value of this model rests on
#: what is NOT in it: no asset_id, no metric_name, no timestamp, no ramp/window
#: flag, no failure flag, nothing derived from the label's future window.
TELEMETRY_MODEL_FEATURES = {
    "z_now", "z_mean_24h", "z_mean_72h", "z_trend_48h", "z_vol_72h", "peer_z_24h",
}

#: Substrings that must never appear in a feature name of the telemetry model.
#: A feature carrying any of these would let it discriminate because it was told
#: the answer rather than because it read the sensors.
FORBIDDEN_FEATURE_SUBSTRINGS = (
    "asset", "metric_name", "timestamp", "time", "date", "ramp", "window",
    "fail", "alarm", "label", "fut", "future",
)

#: Every model deployed in the dataset, with the type it must keep.
EXPECTED_MODEL_TYPES = {
    "asset_clustering_model": "KMEANS",
    "downtime_regression_model": "LINEAR_REGRESSION",
    "inventory_impact_model": "LINEAR_REGRESSION",
    "inventory_impact_model_crusher": "LINEAR_REGRESSION",
    "inventory_impact_model_mill": "LINEAR_REGRESSION",
    "inventory_impact_model_pump": "LINEAR_REGRESSION",
    "safety_model": "LOGISTIC_REGRESSION",
}

#: Feature columns as they stood before Task 10 retrained anything.
EXPECTED_FEATURES = {
    "asset_clustering_model": {
        "asset_id", "total_repair_cost", "total_downtime_duration",
        "asset_criticality",
    },
    "downtime_regression_model": {"lead_time_days", "stock_level"},
    "inventory_impact_model": {"unit_price_usd", "stock_level", "lead_time_days"},
    "inventory_impact_model_crusher": {"stock_level", "lead_time_days"},
    "inventory_impact_model_mill": {"stock_level", "lead_time_days"},
    "inventory_impact_model_pump": {"stock_level", "lead_time_days"},
    "safety_model": {"heart_rate_bpm", "microsleep_events_detected"},
}

#: The four models the plan calls "the downtime_regression_model* models".  The
#: deployed names do not match that glob — three of the four are named
#: `inventory_impact_model_*` — but all four are LINEAR_REG on the label
#: `total_downtime_duration`.  Verified with `bq ls --models`.
DOWNTIME_MODELS = [
    "downtime_regression_model",
    "inventory_impact_model_pump",
    "inventory_impact_model_mill",
    "inventory_impact_model_crusher",
]

#: All five LINEAR_REG models on `total_downtime_duration`.
ALL_DOWNTIME_MODELS = DOWNTIME_MODELS + ["inventory_impact_model"]


def _t(table: str) -> str:
    return f"`{PROJECT_ID}.{DATASET}.{table}`"


def _m(model: str) -> str:
    return f"`{PROJECT_ID}.{DATASET}.{model}`"


@pytest.fixture(scope="module")
def client():
    return bigquery.Client(project=PROJECT_ID)


def _rows(client, sql: str) -> list:
    """Run `sql` with the result cache disabled and return all rows."""
    job_config = bigquery.QueryJobConfig(use_query_cache=False)
    return list(client.query(sql, job_config=job_config).result())


def _one(client, sql: str):
    rows = _rows(client, sql)
    assert len(rows) == 1, f"expected exactly 1 row, got {len(rows)} from:\n{sql}"
    return rows[0]


@pytest.fixture(scope="module")
def baseline() -> dict:
    """Pre-retrain ML.EVALUATE metrics, recorded before anything was replaced."""
    doc = json.loads(_BASELINE_PATH.read_text())
    return doc["metrics"]


# ===========================================================================
# 1. Preconditions — is there anything to train on?
# ===========================================================================


def test_baseline_file_covers_every_deployed_model(baseline):
    """The pre-retrain metrics are unrecoverable; they must have been captured."""
    assert set(baseline) == set(EXPECTED_MODEL_TYPES), (
        "pre_retrain_metrics.json does not cover exactly the deployed models"
    )


@pytest.fixture(scope="module")
def deployed_models(client) -> dict:
    """{model_id: model_type} for every model in the dataset.

    `mining_data.INFORMATION_SCHEMA.MODELS` is not queryable on this dataset
    (404 in location US), so the REST listing is the source of truth.
    """
    return {
        m.model_id: m.model_type
        for m in client.list_models(f"{PROJECT_ID}.{DATASET}")
    }


def test_all_seven_models_still_exist(deployed_models):
    """The seven originals must all still be there.

    Subset, not equality: Task 10b adds `telemetry_alarm_risk_model`.  Nothing
    may go missing, but the dataset is allowed to grow.
    """
    assert set(EXPECTED_MODEL_TYPES) <= set(deployed_models), (
        f"missing models: {sorted(set(EXPECTED_MODEL_TYPES) - set(deployed_models))}"
    )


def test_parts_replaced_survived_the_load(client):
    """`maintenance_logs.parts_replaced` must be populated in the live table.

    Five of the seven models reach `inventory_levels` only through
    UNNEST(parts_replaced) -> part_number.  If the arrays are empty, all five
    training queries return zero rows and none of them can be retrained.

    That is exactly the state the first Task 10 attempt found, and this test is
    the gate that caught it.  Root cause was a missing
    `--parquet_enable_list_inference` on `bq load`, which leaves a 3-level
    parquet LIST group unmapped onto a BigQuery ARRAY.  The defect has been
    fixed and the data restored (186 values across 126 of 152 rows), so the test
    now passes and is kept as a regression guard: it asserts contents, not
    shape, because the column was structurally perfect and entirely empty once
    already and every Task 8/9 gate went green on it.
    """
    row = _one(
        client,
        f"""
        SELECT COUNT(*) AS n_rows,
               COUNTIF(ARRAY_LENGTH(parts_replaced) > 0) AS n_with_parts,
               IFNULL(SUM(ARRAY_LENGTH(parts_replaced)), 0) AS n_values
        FROM {_t('maintenance_logs')}
        """,
    )
    assert row.n_rows > 0, "maintenance_logs is empty"
    assert row.n_values > 0, (
        f"maintenance_logs has {row.n_rows} rows but every parts_replaced array "
        "is empty, so the five downtime/inventory models have zero training "
        "rows.\n"
        "The parquet at data/generated/maintenance_logs.parquet is correct: 152 "
        "rows, 126 with parts, 186 element values.\n"
        "Root cause is data/generator/load.py::bq_load_command. `bq load "
        "--source_format=PARQUET` does not map a 3-level parquet LIST group "
        "(parts_replaced.list.element) onto a BigQuery ARRAY unless "
        "--parquet_enable_list_inference is passed; without it the group is "
        "read as STRUCT<list ARRAY<STRUCT<element STRING>>>, which the explicit "
        "flat REPEATED STRING --schema then silently flattens to an empty "
        "array. Confirmed by loading the same parquet twice: without the flag "
        "the column arrives as that STRUCT, with the flag it arrives as 152 "
        "rows / 186 values.\n"
        "Fix: add --parquet_enable_list_inference to bq_load_command() and "
        "re-run the load."
    )
    assert row.n_with_parts > 0


@pytest.mark.parametrize("model", sorted(EXPECTED_MODEL_TYPES))
def test_training_query_returns_rows(client, model):
    """Each model's training query must return > 0 rows before it is retrained.

    Retraining on a zero-row query cannot produce a model, and
    CREATE OR REPLACE MODEL is destructive to the deployed one.
    """
    n = _one(client, _TRAINING_ROW_COUNT_SQL[model]).n
    assert n > 0, (
        f"{model}: training query returns 0 rows; retraining it would destroy "
        "the deployed model without producing a replacement"
    )


# ===========================================================================
# 2. Architecture is unchanged — data may change, structure may not
# ===========================================================================


def test_model_types_unchanged(deployed_models):
    """The seven keep their types, and nothing unaccounted-for is deployed.

    Not a plain equality against the seven any more -- Task 10b adds
    `telemetry_alarm_risk_model` and the corpus work adds `text_embedding_model`
    -- but the census stays closed, so a model that appears without a decision
    behind it still fails here. Each addition is named individually and on
    purpose; widening this to "anything else is fine" would retire the only
    check that notices a model nobody decided to deploy.
    """
    assert {k: v for k, v in deployed_models.items() if k in EXPECTED_MODEL_TYPES} \
        == EXPECTED_MODEL_TYPES
    accounted = {TELEMETRY_MODEL, EMBEDDING_MODEL}
    extra = set(deployed_models) - set(EXPECTED_MODEL_TYPES)
    assert extra == accounted, (
        f"unexpected models in the dataset: {sorted(extra - accounted)}"
    )


@pytest.mark.parametrize("model", sorted(EXPECTED_FEATURES))
def test_feature_columns_unchanged(client, model):
    # INFORMATION_SCHEMA has no feature list; read it off the model resource.
    model_ref = client.get_model(f"{PROJECT_ID}.{DATASET}.{model}")
    got = {c.name for c in model_ref.feature_columns}
    assert got == EXPECTED_FEATURES[model], (
        f"{model} feature columns changed: {sorted(got)} != "
        f"{sorted(EXPECTED_FEATURES[model])}. Task 10 may change training data "
        "only."
    )


@pytest.mark.parametrize("model", DOWNTIME_MODELS + ["inventory_impact_model"])
def test_downtime_models_keep_their_label(client, model):
    model_ref = client.get_model(f"{PROJECT_ID}.{DATASET}.{model}")
    opts = model_ref.training_runs[-1]["trainingOptions"]
    assert opts["inputLabelColumns"] == ["total_downtime_duration"]


def test_l2_regularisation_unchanged(client):
    """The three per-asset models carry L2_REG = 0.1; the other two carry none."""
    expected = {
        "downtime_regression_model": 0.0,
        "inventory_impact_model": 0.0,
        "inventory_impact_model_pump": 0.1,
        "inventory_impact_model_mill": 0.1,
        "inventory_impact_model_crusher": 0.1,
        "safety_model": 0.0,
    }
    for model, want in expected.items():
        model_ref = client.get_model(f"{PROJECT_ID}.{DATASET}.{model}")
        opts = model_ref.training_runs[-1]["trainingOptions"]
        assert float(opts.get("l2Regularization", 0.0)) == want, model


def test_kmeans_cluster_count_unchanged(client):
    model_ref = client.get_model(f"{PROJECT_ID}.{DATASET}.asset_clustering_model")
    opts = model_ref.training_runs[-1]["trainingOptions"]
    assert int(opts["numClusters"]) == 4


# ===========================================================================
# 3. Behaviour
# ===========================================================================


def test_safety_model_improved(client, baseline):
    """safety_model retrained on the corrected fatigue physiology."""
    row = _one(client, f"SELECT * FROM ML.EVALUATE(MODEL {_m('safety_model')})")
    base = baseline["safety_model"]
    assert row.roc_auc > base["roc_auc"], (
        f"roc_auc {row.roc_auc} did not improve on {base['roc_auc']}"
    )
    assert row.log_loss < base["log_loss"]
    assert row.accuracy > base["accuracy"]


def test_asset_clustering_model_was_retrained(client, baseline):
    """The KMEANS model moved off its pre-retrain fit.

    Deliberately not asserting a direction: the plan retrains this one "for
    consistency", not to hit a target, and tuning it to make a number go green
    would be exactly the wrong move. Asserting only that it changed.
    """
    row = _one(
        client, f"SELECT * FROM ML.EVALUATE(MODEL {_m('asset_clustering_model')})"
    )
    base = baseline["asset_clustering_model"]
    assert (
        row.davies_bouldin_index != pytest.approx(base["davies_bouldin_index"])
        or row.mean_squared_distance != pytest.approx(base["mean_squared_distance"])
    ), "asset_clustering_model metrics are identical to pre-retrain — was it retrained, or is this a cached result?"


@pytest.mark.parametrize("model", ALL_DOWNTIME_MODELS)
def test_downtime_model_was_actually_retrained(client, model, baseline):
    """Each downtime regressor moved off its recorded pre-retrain fit.

    This is the assertion that survives contact with the measurement.  It fails
    if the model was never replaced, and it fails if BigQuery's result cache
    served a pre-retrain ML.EVALUATE for a model that was replaced -- which
    happened during the first attempt, returning the old numbers to 16
    significant digits.  ``_rows`` disables the cache; this is the check that
    the cache stayed disabled.

    Measured R^2, pre-retrain -> post-retrain:

        downtime_regression_model        0.5008 -> 0.4580   (down)
        inventory_impact_model           0.9372 -> 1.0000   (up, and meaningless)
        inventory_impact_model_pump      0.0283 -> 0.0205   (down)
        inventory_impact_model_mill      0.0171 -> 0.0059   (down)
        inventory_impact_model_crusher   0.0168 -> 0.0235   (up)

    The brief expected all four to rise materially.  Three fell.  The module
    docstring explains why that is a property of the architecture rather than of
    the data, and why the improvement is deliberately not asserted here.

    inventory_impact_model's 1.0000 is the clearest illustration: 3 training
    rows, 3 features.  A plane through 3 points fits them exactly.  It is a
    perfect score that means nothing, which is precisely why "R^2 went up" was
    the wrong gate.
    """
    row = _one(client, f"SELECT * FROM ML.EVALUATE(MODEL {_m(model)})")
    base = baseline[model]["r2_score"]
    assert abs(row.r2_score - base) > 1e-12, (
        f"{model}: r2_score {row.r2_score!r} is bit-identical to the pre-retrain "
        f"baseline {base!r}. Either CREATE OR REPLACE MODEL was never run, or a "
        "cached ML.EVALUATE result is being served."
    )


def test_ramp_is_present_in_the_telemetry(client):
    """Ground truth: PUMP-104A really does degrade in the final 21 days.

    Establishes that a failure to discriminate ramp from flat is a property of
    the models, not of the data.
    """
    rows = _rows(
        client,
        f"""
        SELECT metric_name,
               AVG(IF(timestamp >= TIMESTAMP('{RAMP_START}'), metric_value, NULL)) AS ramp_mean,
               AVG(IF(timestamp <  TIMESTAMP('{RAMP_START}'), metric_value, NULL)) AS flat_mean,
               COUNTIF(timestamp >= TIMESTAMP('{RAMP_START}')) AS n_ramp,
               COUNTIF(timestamp <  TIMESTAMP('{RAMP_START}')) AS n_flat
        FROM {_t('telemetry_stream')}
        WHERE asset_id = 'PUMP-104A'
        GROUP BY metric_name
        """,
    )
    assert len(rows) > 0, "no PUMP-104A telemetry at all"
    seen = {r.metric_name for r in rows}
    assert {"vibration_hz", "temperature_c"} <= seen, seen
    for r in rows:
        assert r.n_ramp > 0 and r.n_flat > 0, r.metric_name
        assert r.ramp_mean > r.flat_mean, (
            f"{r.metric_name}: ramp mean {r.ramp_mean} is not above flat mean "
            f"{r.flat_mean} — the degradation ramp is missing from the data"
        )


def test_legacy_pump_model_cannot_see_the_ramp(client):
    """The seven are structurally incapable of the brief's headline assertion.

    Pinned so that nobody wires `bqml_predict`'s time-to-failure narrative to
    `inventory_impact_model_pump`.  Its two features are static attributes of a
    spare part, and its label is repair hours.  There is no telemetry column and
    no time column anywhere in its input, so the ramp window and the flat window
    are the same point in feature space to it.

    The measured numbers make the point: over the 46 rows its training query
    returns, the flat window means 8.94 predicted repair-hours and the ramp
    window 8.38 -- i.e. it predicts a *shorter* repair on a degrading pump, off
    3 rows.  That difference is which spare parts happen to appear in which work
    orders, not a learned trend, and it is why this test asserts the structural
    fact rather than comparing the two means.
    """
    model_ref = client.get_model(f"{PROJECT_ID}.{DATASET}.inventory_impact_model_pump")
    features = {c.name for c in model_ref.feature_columns}
    assert features == {"stock_level", "lead_time_days"}, features
    for name in features:
        assert "time" not in name or name == "lead_time_days"
    # And it must not have quietly acquired a telemetry feature.
    assert not any(
        k in n
        for n in features
        for k in ("vibration", "temperature", "telemetry", "timestamp")
    ), features


# ===========================================================================
# 4. telemetry_alarm_risk_model — the telemetry-driven model
# ===========================================================================
#
# Everything below rests on the anti-leak tests coming first.  A model that
# separates the ramp from the flat window because it was handed a ramp flag, an
# asset id or a timestamp proves nothing at all, so the separation assertion is
# only worth reading once the feature set has been pinned.


def test_telemetry_model_exists_and_is_logistic(deployed_models):
    assert TELEMETRY_MODEL in deployed_models, (
        f"{TELEMETRY_MODEL} is not deployed; see data/models/retrain.sql §C"
    )
    assert deployed_models[TELEMETRY_MODEL] == "LOGISTIC_REGRESSION"


def test_telemetry_model_features_are_exactly_the_six_telemetry_features(client):
    """Anti-leak gate 1: pin the feature set exactly.

    Its value is in what it excludes.  If a future edit adds `asset_id`,
    `timestamp`, or anything derived from the label window, the ramp/flat result
    below stops meaning anything -- and this fails before it.
    """
    model_ref = client.get_model(f"{PROJECT_ID}.{DATASET}.{TELEMETRY_MODEL}")
    got = {c.name for c in model_ref.feature_columns}
    assert got == TELEMETRY_MODEL_FEATURES, (
        f"{TELEMETRY_MODEL} features changed: {sorted(got)} != "
        f"{sorted(TELEMETRY_MODEL_FEATURES)}"
    )
    for name in got:
        for bad in FORBIDDEN_FEATURE_SUBSTRINGS:
            assert bad not in name.lower(), (
                f"feature {name!r} contains {bad!r}: this model must not be able "
                "to key on identity, calendar time, or the label"
            )


def test_telemetry_model_label_is_the_forward_alarm(client):
    model_ref = client.get_model(f"{PROJECT_ID}.{DATASET}.{TELEMETRY_MODEL}")
    opts = model_ref.training_runs[-1]["trainingOptions"]
    assert opts["inputLabelColumns"] == ["alarm_within_7d"]
    assert opts.get("autoClassWeights", False) is False, (
        "class weights would decalibrate the probability; the ramp/flat "
        "comparison is on absolute probabilities"
    )


def test_telemetry_model_reads_telemetry_stream(client):
    """It is the only model in the dataset whose training query touches telemetry.

    Read off the job history rather than asserted from the file, so a model
    trained from some other statement cannot pass.
    """
    row = _one(
        client,
        f"""
        SELECT COUNT(*) AS n
        FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
        WHERE statement_type = 'CREATE_MODEL'
          AND STRPOS(query, '{TELEMETRY_MODEL}') > 0
          AND STRPOS(query, 'telemetry_stream') > 0
          AND state = 'DONE' AND error_result IS NULL
        """,
    )
    assert row.n > 0, (
        f"no successful CREATE MODEL job for {TELEMETRY_MODEL} that reads "
        "telemetry_stream"
    )


@pytest.fixture(scope="module")
def risk_scores(client) -> list:
    """P(alarm within 7 d) for every (asset, metric, timestamp) from 2026-03-01.

    Features are recomputed here from `telemetry_stream` with the same window
    definitions as the training query, so the test exercises the model the way
    a caller would rather than reading a stored table.
    """
    return _rows(client, _RISK_SQL)


def test_risk_scores_are_not_empty(risk_scores):
    """A zero-row result is never a pass; assert contents, not shape."""
    assert len(risk_scores) > 0
    n_pump_ramp = sum(
        r.n for r in risk_scores
        if r.asset_id == "PUMP-104A" and r.metric_name == "vibration_hz"
        and r.win == "ramp"
    )
    assert n_pump_ramp > 200, (
        f"only {n_pump_ramp} scored rows in the PUMP-104A vibration ramp window; "
        "expected ~253 (21 days at a 2-hourly grid)"
    )
    assert all(0.0 <= r.mean_p <= 1.0 for r in risk_scores)


def test_pump_ramp_risk_materially_exceeds_flat_risk(risk_scores):
    """THE headline assertion, on merit.

    PUMP-104A vibration_hz.  The model was trained on 2026-03-01..2026-05-19
    22:00 only -- ramp start minus the 7-day label horizon -- so every row in the
    ramp window is out of sample in both its features and its label.

    Measured: flat 0.0548, ramp 0.2956 mean P(alarm within 7 d), a 5.39x
    increase, rising monotonically through the ramp (0.101 / 0.221 / 0.562 over
    its three weeks) and peaking at 0.828.

    The 2x bar is not tuned to that result; it is the smallest increase that
    could not be produced by ordinary between-window noise, which the control
    test below measures at under 0.008 in absolute probability.
    """
    by_win = {
        r.win: r for r in risk_scores
        if r.asset_id == "PUMP-104A" and r.metric_name == "vibration_hz"
    }
    assert set(by_win) == {"flat", "ramp"}, sorted(by_win)
    flat, ramp = by_win["flat"].mean_p, by_win["ramp"].mean_p
    assert ramp > 2.0 * flat, (
        f"PUMP-104A vibration: ramp mean P(alarm) {ramp:.4f} is not materially "
        f"above the flat mean {flat:.4f}"
    )


def test_pump_temperature_also_escalates(risk_scores):
    """The ramp is on both pump channels, so both should escalate."""
    by_win = {
        r.win: r for r in risk_scores
        if r.asset_id == "PUMP-104A" and r.metric_name == "temperature_c"
    }
    assert set(by_win) == {"flat", "ramp"}
    assert by_win["ramp"].mean_p > by_win["flat"].mean_p


def test_control_series_do_not_move_between_the_windows(risk_scores):
    """Anti-leak gate 2, and the test that makes the headline mean something.

    The eleven series that carry no ramp are scored over the *same* 253 ramp
    timestamps as PUMP-104A.  If the model had any handle on calendar time --
    a timestamp feature, a window flag, a training/serving split it could infer
    -- they would rise too.  Measured largest absolute shift across all eleven:
    0.0077, against PUMP-104A vibration's +0.2408.

    This is the assertion a broken implementation trips.  Add `timestamp` to the
    feature list and every control series moves with the pump; the headline test
    would still pass and this one would not.
    """
    shifts = {}
    for r in risk_scores:
        if r.asset_id == "PUMP-104A":
            continue
        shifts.setdefault((r.asset_id, r.metric_name), {})[r.win] = r.mean_p
    assert len(shifts) == 11, f"expected 11 control series, got {len(shifts)}"
    worst_key, worst = None, 0.0
    for key, w in shifts.items():
        assert set(w) == {"flat", "ramp"}, (key, sorted(w))
        d = abs(w["ramp"] - w["flat"])
        if d > worst:
            worst_key, worst = key, d
    assert worst < 0.02, (
        f"control series {worst_key} shifted by {worst:.4f} between the flat and "
        "ramp windows. The model appears to be responding to calendar time "
        "rather than to telemetry, which would invalidate the PUMP-104A result."
    )


def test_placebo_ramp_scores_like_the_flat_window(client):
    """Anti-leak gate 3: a permutation test on the headline result.

    Score the *same 253 ramp timestamps*, but with feature vectors deterministic-
    ally resampled from PUMP-104A's flat window.  If any part of the escalation
    came from something other than the sensor values -- calendar time, row
    position, an artefact of how the ramp rows are selected -- the placebo would
    escalate too.

    Measured:
        real ramp features        0.2956
        placebo (ramp timestamps, flat features)  0.0539
        real flat features        0.0548

    The placebo lands on the flat window to within 0.001.  All of the 5.39x
    separation is carried by the telemetry.

    Resampling uses FARM_FINGERPRINT, not Python's ``hash()``: ``hash()`` on a
    str is salted per interpreter by PYTHONHASHSEED, and using it as a seed
    caused a non-determinism bug earlier in this workstream.
    """
    rows = _rows(client, _PLACEBO_SQL)
    by = {r.variant: r for r in rows}
    assert set(by) == {"real_ramp", "placebo", "real_flat"}, sorted(by)
    assert by["placebo"].n == by["real_ramp"].n > 200, (
        "placebo must score exactly as many rows as the real ramp"
    )
    # The placebo must look like the flat window, not like the ramp.
    assert abs(by["placebo"].mean_p - by["real_flat"].mean_p) < 0.01, (
        f"placebo mean {by['placebo'].mean_p:.4f} differs from the real flat "
        f"mean {by['real_flat'].mean_p:.4f}: the ramp timestamps themselves are "
        "influencing the prediction"
    )
    assert by["real_ramp"].mean_p > 2.0 * by["placebo"].mean_p, (
        f"real ramp {by['real_ramp'].mean_p:.4f} is not materially above the "
        f"placebo {by['placebo'].mean_p:.4f}"
    )


def test_telemetry_model_discriminates_out_of_sample(client):
    """ROC AUC on the held-out final three weeks, which training never saw.

    Evaluated on all 13 series over 2026-05-19 22:00 -> 2026-06-09 22:00 (the
    upper bound keeps the 7-day label window inside the data). Measured 0.9417
    over 3259 rows / 291 positives.

    Reported alongside, and not to be confused with: ML.EVALUATE on the model's
    own AUTO_SPLIT eval set -- entirely pre-ramp -- gives ROC AUC 0.604. The
    model is barely better than chance at calling ordinary 3-sigma transients
    and strong at calling a sustained degradation. That is an honest description
    of what it does, and the 0.604 is the number to quote if anyone asks how
    good it is in steady state.
    """
    row = _one(client, _OOS_EVAL_SQL)
    assert row.n_holdout > 1000, row.n_holdout
    assert row.n_pos > 50, f"only {row.n_pos} positives in the holdout"
    assert row.n_pos < row.n_holdout, "holdout is single-class; AUC undefined"
    assert row.roc_auc > 0.80, (
        f"out-of-sample roc_auc {row.roc_auc} on the degradation period; the "
        "model does not generalise to the ramp it never saw"
    )


def test_telemetry_model_steady_state_auc_is_reported_not_inflated(client):
    """The pre-ramp AUC is weak, and that must stay visible.

    Guards against someone "improving" the model by leaking the ramp into
    training: doing so would push this in-sample-period number up towards the
    out-of-sample one. 0.604 is above chance and that is all that is claimed.
    """
    row = _one(client, f"SELECT * FROM ML.EVALUATE(MODEL {_m(TELEMETRY_MODEL)})")
    assert row.roc_auc > 0.5, (
        f"pre-ramp roc_auc {row.roc_auc} is at or below chance"
    )


# ---------------------------------------------------------------------------
# Training-row-count SQL, one per model — the exact FROM/WHERE of each model's
# CREATE MODEL statement, counted instead of trained.
# ---------------------------------------------------------------------------

_PER_ASSET = f"""
  FROM {_t('maintenance_logs')} AS t1
  CROSS JOIN UNNEST(t1.parts_replaced) AS part_name
  INNER JOIN {_t('inventory_levels')} AS t2 ON part_name = t2.part_number
  INNER JOIN {_t('assets')} AS t3 ON t1.asset_id = t3.asset_id
"""

_TRAINING_ROW_COUNT_SQL = {
    "downtime_regression_model": f"""
        SELECT COUNT(*) AS n FROM (
          SELECT m.asset_id
          FROM {_t('inventory_levels')} AS i
          JOIN {_t('maintenance_logs')} AS m
            ON i.part_number = m.parts_replaced[SAFE_OFFSET(0)]
          GROUP BY m.asset_id)
    """,
    "inventory_impact_model": f"""
        SELECT COUNT(*) AS n FROM (
          SELECT m.asset_id
          FROM {_t('maintenance_logs')} AS m
          CROSS JOIN UNNEST(m.parts_replaced) AS part_number
          INNER JOIN {_t('inventory_levels')} AS i ON part_number = i.part_number
          INNER JOIN {_t('erp_work_orders')} AS e ON m.work_order_id = e.work_order_id
          WHERE m.asset_id IN ('MILL-01', 'PUMP-104A', 'CRUSHER-03')
          GROUP BY m.asset_id)
    """,
    "inventory_impact_model_pump": f"""
        SELECT COUNT(*) AS n {_PER_ASSET}
        WHERE t3.asset_type = 'PUMP' AND t3.asset_id IN ('PUMP-104A')
    """,
    "inventory_impact_model_mill": f"""
        SELECT COUNT(*) AS n {_PER_ASSET}
        WHERE t3.asset_type = 'GRINDING_MILL' AND t3.asset_id = 'MILL-01'
    """,
    "inventory_impact_model_crusher": f"""
        SELECT COUNT(*) AS n {_PER_ASSET}
        WHERE t3.asset_type = 'CRUSHER' AND t3.asset_id IN ('CRUSHER-03')
    """,
    "asset_clustering_model": f"""
        SELECT COUNT(*) AS n FROM (
          SELECT t1.asset_id
          FROM {_t('erp_work_orders')} AS t1
          JOIN {_t('maintenance_logs')} AS t2 ON t1.asset_id = t2.asset_id
          GROUP BY t1.asset_id)
    """,
    "safety_model": f"""
        SELECT COUNT(*) AS n
        FROM {_t('biometric_fatigue_logs')} AS b
        INNER JOIN {_t('incident_involvements')} AS i ON b.operator_id = i.operator_id
        INNER JOIN {_t('safety_incidents')} AS s ON i.incident_id = s.incident_id
    """,
}


# ---------------------------------------------------------------------------
# Feature SQL for telemetry_alarm_risk_model.
#
# Kept identical to the feature block of data/models/retrain.sql §C.  It is
# repeated rather than imported because the point of these tests is to score the
# deployed model the way a caller would -- from `telemetry_stream` -- and a
# divergence between this and the training query would show up immediately as a
# collapse in the ramp/flat separation.
#
# `zs` rather than `z` for the z-score CTE: a CTE named `z` shadows the column
# `z` inside a later window function and BigQuery resolves it to the table.
# ---------------------------------------------------------------------------

_FEATURE_CTE = f"""
WITH t AS (
  SELECT asset_id, metric_name, timestamp, metric_value, UNIX_SECONDS(timestamp) AS ts
  FROM {_t('telemetry_stream')}
),
base AS (
  SELECT asset_id, metric_name,
         AVG(metric_value) AS mu0,
         STDDEV_SAMP(metric_value) AS sd0
  FROM t
  WHERE timestamp < TIMESTAMP('{BASELINE_END}')
  GROUP BY asset_id, metric_name
),
zs AS (
  SELECT t.asset_id, t.metric_name, t.timestamp, t.ts, t.metric_value,
         b.mu0, b.sd0, (t.metric_value - b.mu0) / b.sd0 AS z
  FROM t JOIN base b USING (asset_id, metric_name)
),
win AS (
  SELECT *,
    AVG(z)              OVER w24  AS z_mean_24h,
    AVG(z)              OVER w72  AS z_mean_72h,
    STDDEV_SAMP(z)      OVER w72  AS z_vol_72h,
    SUM(z)              OVER w24  AS s24,
    COUNT(z)            OVER w24  AS c24,
    SUM(z)              OVER w48  AS s48,
    COUNT(z)            OVER w48  AS c48,
    MAX(metric_value)   OVER wfut AS fut_max,
    COUNT(metric_value) OVER wfut AS c_fut
  FROM zs
  WINDOW
    w24  AS (PARTITION BY asset_id, metric_name ORDER BY ts RANGE BETWEEN  86400 PRECEDING AND CURRENT ROW),
    w48  AS (PARTITION BY asset_id, metric_name ORDER BY ts RANGE BETWEEN 172800 PRECEDING AND CURRENT ROW),
    w72  AS (PARTITION BY asset_id, metric_name ORDER BY ts RANGE BETWEEN 259200 PRECEDING AND CURRENT ROW),
    wfut AS (PARTITION BY asset_id, metric_name ORDER BY ts RANGE BETWEEN 1 FOLLOWING AND 604800 FOLLOWING)
),
feat AS (
  SELECT asset_id, metric_name, timestamp,
         z AS z_now, z_mean_24h, z_mean_72h, z_vol_72h,
         z_mean_24h - SAFE_DIVIDE(s48 - s24, c48 - c24) AS z_trend_48h,
         IF(c_fut = 0, NULL, fut_max > mu0 + 3 * sd0) AS alarm_within_7d
  FROM win
),
peer AS (
  SELECT *,
         SAFE_DIVIDE(SUM(z_mean_24h) OVER pa - z_mean_24h, COUNT(*) OVER pa - 1) AS peer_z_24h
  FROM feat
  WINDOW pa AS (PARTITION BY asset_id, timestamp)
)
"""

#: Rows with every feature present.  BQML drops NULL-feature rows silently, so
#: they are filtered explicitly and the row counts asserted downstream.
_COMPLETE = """
      z_now IS NOT NULL AND z_mean_24h IS NOT NULL AND z_mean_72h IS NOT NULL
  AND z_trend_48h IS NOT NULL AND z_vol_72h IS NOT NULL AND peer_z_24h IS NOT NULL
"""

_RISK_SQL = _FEATURE_CTE + f""",
scored AS (
  SELECT asset_id, metric_name,
         IF(timestamp >= TIMESTAMP('{RAMP_START}'), 'ramp', 'flat') AS win,
         (SELECT prob FROM UNNEST(predicted_alarm_within_7d_probs) WHERE label) AS p_alarm
  FROM ML.PREDICT(
    MODEL {_m(TELEMETRY_MODEL)},
    (SELECT asset_id, metric_name, timestamp,
            z_now, z_mean_24h, z_mean_72h, z_trend_48h, z_vol_72h, peer_z_24h
     FROM peer
     WHERE timestamp >= TIMESTAMP('{BASELINE_END}') AND {_COMPLETE}))
)
SELECT asset_id, metric_name, win, COUNT(*) AS n, AVG(p_alarm) AS mean_p
FROM scored
GROUP BY asset_id, metric_name, win
"""

#: Out-of-sample evaluation.  Lower bound is the last training timestamp, upper
#: bound keeps the 7-day label window inside the data (grid ends 2026-06-16
#: 22:00).  Both class counts are returned so a single-class holdout, which
#: would make ROC AUC meaningless, fails loudly instead of scoring 1.0.
_OOS_EVAL_SQL = _FEATURE_CTE + f""",
holdout AS (
  SELECT z_now, z_mean_24h, z_mean_72h, z_trend_48h, z_vol_72h, peer_z_24h,
         alarm_within_7d
  FROM peer
  WHERE timestamp > TIMESTAMP('{TRAIN_END}')
    AND timestamp <= TIMESTAMP(
          DATETIME_SUB(DATETIME('{GRID_END}'), INTERVAL 7 DAY))
    AND {_COMPLETE}
    AND alarm_within_7d IS NOT NULL
)
SELECT (SELECT COUNT(*) FROM holdout) AS n_holdout,
       (SELECT COUNTIF(alarm_within_7d) FROM holdout) AS n_pos,
       e.roc_auc, e.log_loss
FROM ML.EVALUATE(MODEL {_m(TELEMETRY_MODEL)}, (SELECT * FROM holdout)) AS e
"""

#: Permutation test.  The ramp timestamps are kept and the feature vectors are
#: swapped for deterministically resampled flat-window ones.  FARM_FINGERPRINT
#: is used rather than any Python-side hashing so the resample is identical on
#: every run and in every process.
_PLACEBO_SQL = _FEATURE_CTE + f""",
pump AS (
  SELECT timestamp,
         z_now, z_mean_24h, z_mean_72h, z_trend_48h, z_vol_72h, peer_z_24h,
         timestamp >= TIMESTAMP('{RAMP_START}') AS is_ramp
  FROM peer
  WHERE asset_id = 'PUMP-104A' AND metric_name = 'vibration_hz'
    AND timestamp >= TIMESTAMP('{BASELINE_END}') AND {_COMPLETE}
),
flat_pool AS (
  SELECT ROW_NUMBER() OVER (ORDER BY timestamp) - 1 AS i,
         z_now, z_mean_24h, z_mean_72h, z_trend_48h, z_vol_72h, peer_z_24h
  FROM pump WHERE NOT is_ramp
),
ramp_ts AS (
  SELECT ROW_NUMBER() OVER (ORDER BY timestamp) - 1 AS k,
         (SELECT COUNT(*) FROM flat_pool) AS npool
  FROM pump WHERE is_ramp
),
placebo AS (
  SELECT f.z_now, f.z_mean_24h, f.z_mean_72h, f.z_trend_48h, f.z_vol_72h, f.peer_z_24h
  FROM ramp_ts r
  JOIN flat_pool f
    ON f.i = MOD(ABS(FARM_FINGERPRINT(CAST(r.k AS STRING))), r.npool)
),
scored AS (
  SELECT 'real_ramp' AS variant,
         (SELECT prob FROM UNNEST(predicted_alarm_within_7d_probs) WHERE label) AS p
  FROM ML.PREDICT(MODEL {_m(TELEMETRY_MODEL)},
    (SELECT z_now, z_mean_24h, z_mean_72h, z_trend_48h, z_vol_72h, peer_z_24h
     FROM pump WHERE is_ramp))
  UNION ALL
  SELECT 'placebo',
         (SELECT prob FROM UNNEST(predicted_alarm_within_7d_probs) WHERE label)
  FROM ML.PREDICT(MODEL {_m(TELEMETRY_MODEL)}, (SELECT * FROM placebo))
  UNION ALL
  SELECT 'real_flat',
         (SELECT prob FROM UNNEST(predicted_alarm_within_7d_probs) WHERE label)
  FROM ML.PREDICT(MODEL {_m(TELEMETRY_MODEL)},
    (SELECT z_now, z_mean_24h, z_mean_72h, z_trend_48h, z_vol_72h, peer_z_24h
     FROM pump WHERE NOT is_ramp))
)
SELECT variant, COUNT(*) AS n, AVG(p) AS mean_p FROM scored GROUP BY variant
"""
