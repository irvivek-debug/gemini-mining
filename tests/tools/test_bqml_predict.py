"""Tests for bqml_predict — ML.PREDICT over the allowlisted BQML models.

The telemetry_alarm_risk_model was trained on six derived z-score features
(z_now, z_mean_24h, z_mean_72h, z_trend_48h, z_vol_72h, peer_z_24h) that are
not present verbatim in mining_data.telemetry_stream.  The input_sql in each
live test therefore computes those columns via CAST and literal constants so
that the subquery satisfies the model's expected schema.  The test does NOT
switch to a different model; it adjusts the input shape.

WHAT THESE LIVE TESTS DO AND DO NOT PROVE.  They prove the wrapper is wired
correctly: the allowlist blocks unlisted identifiers before any SQL is built,
ML.PREDICT compiles against a schema-compatible subquery, and the envelope
carries honest provenance.  They do NOT prove that telemetry_alarm_risk_model
produces meaningful predictions from telemetry_stream.  It cannot: z-scores are
dimensionless normalised statistics, while metric_value is a raw physical
reading in Hz or degrees C, and z_trend_48h is pinned to a constant here.  The
model returns a number, but that number is not interpretable.  No agent may
call this model directly off telemetry_stream until a feature-engineering step
computes real z-scores.  See Task 10 (catalog) and Task 16 (demo scenarios).
"""
from mining_agents.envelope import Envelope
from mining_agents.tools.bqml_predict import list_models, make_bqml_predict

# The six feature columns required by telemetry_alarm_risk_model, projected
# from telemetry_stream via CAST/constant expressions.
_ALARM_RISK_SQL = """
SELECT
    CAST(metric_value AS FLOAT64) AS z_now,
    CAST(metric_value AS FLOAT64) AS z_mean_24h,
    CAST(metric_value AS FLOAT64) AS z_mean_72h,
    0.0                           AS z_trend_48h,
    0.0                           AS z_vol_72h,
    CAST(metric_value AS FLOAT64) AS peer_z_24h
FROM `mining_data.telemetry_stream`
LIMIT @n
"""


#: The eight models an agent may run ML.PREDICT against.
PREDICTIVE_MODELS = [
    "asset_clustering_model",
    "downtime_regression_model",
    "inventory_impact_model",
    "inventory_impact_model_crusher",
    "inventory_impact_model_mill",
    "inventory_impact_model_pump",
    "safety_model",
    "telemetry_alarm_risk_model",
]

#: A REMOTE model over Vertex text-embedding-005, added to embed the PDF
#: corpus for doc_search. It lives in the same dataset as the eight, so
#: list_models() returns it, but ML.PREDICT is not what it is for.
EMBEDDING_MODEL = "text_embedding_model"


def test_the_dataset_exposes_eight_predictive_models_and_one_embedding_model():
    """A census, not an allowlist.

    list_models() reports what is deployed; it does not decide what any agent
    may call. The count is pinned so a model appearing in the dataset without
    a decision behind it is noticed here.
    """
    models = sorted(list_models())
    assert models == sorted([*PREDICTIVE_MODELS, EMBEDDING_MODEL]), (
        f"model census mismatch: {models}"
    )


def test_the_embedding_model_cannot_be_predicted_with():
    """Deployment is not permission.

    The embedding model sits in the same dataset as the eight predictive
    models, so it shows up in any census of the dataset. What stops an agent
    reaching it is that bqml_predict validates against the allowlist it was
    built with, and no agent is built with this one. That is the property
    worth testing, because the census alone would not catch it being handed
    out — and ML.PREDICT over a remote embedding model is not a prediction,
    it is a mistake with a number attached.
    """
    predict = make_bqml_predict(PREDICTIVE_MODELS)
    env = predict(EMBEDDING_MODEL, "SELECT 1 AS x", {})
    assert env["success"] is False
    assert env["error"]["code"] == "MODEL_NOT_PERMITTED"


def test_predict_returns_rows_inside_the_envelope():
    model = "telemetry_alarm_risk_model"
    predict = make_bqml_predict([model])
    env = predict(model, _ALARM_RISK_SQL, {"n": 10})
    Envelope.model_validate(env)
    assert env["success"] is True
    assert len(env["data"]["rows"]) == 10
    assert any("predicted" in key for key in env["data"]["rows"][0])


def test_meta_names_both_the_model_and_the_input_tables():
    model = "telemetry_alarm_risk_model"
    predict = make_bqml_predict([model])
    env = predict(model, _ALARM_RISK_SQL, {"n": 5})
    assert f"mining_data.{model}" in env["meta"]["tables_read"]
    assert "mining_data.telemetry_stream" in env["meta"]["tables_read"]


def test_a_model_outside_the_allowlist_is_refused():
    predict = make_bqml_predict(["telemetry_alarm_risk_model"])
    env = predict("some_other_model", "SELECT 1", {})
    Envelope.model_validate(env)
    assert env["success"] is False
    assert env["error"]["code"] == "MODEL_NOT_PERMITTED"
    assert env["meta"]["tables_read"] == ["mining_data.telemetry_alarm_risk_model"]


def test_hostile_model_name_is_refused():
    """A model name with a backtick or SQL fragment must be rejected before SQL building."""
    predict = make_bqml_predict(["telemetry_alarm_risk_model"])
    hostile = "telemetry_alarm_risk_model`; DROP TABLE assets; --"
    env = predict(hostile, "SELECT 1", {})
    Envelope.model_validate(env)
    assert env["success"] is False
    assert env["error"]["code"] == "MODEL_NOT_PERMITTED"
    assert env["meta"]["tables_read"] == ["mining_data.telemetry_alarm_risk_model"]


def test_interpolated_input_sql_is_refused():
    predict = make_bqml_predict(["telemetry_alarm_risk_model"])
    asset = "PUMP-104A"
    env = predict(
        "telemetry_alarm_risk_model",
        f"SELECT * FROM `mining_data.telemetry_stream` WHERE asset_id = '{asset}'",
        {},
    )
    assert env["success"] is False
    assert env["error"]["code"] == "SQL_INTERPOLATION"
