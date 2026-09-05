import os

import pytest
from mining_agents.config import settings
from mining_agents.envelope import Envelope
from mining_agents.safety.output_filter import REDACTION
from mining_agents.safety.untrusted import UNTRUSTED_PREFIX
from mining_agents.tools.bq_query import (
    assert_no_interpolation, assert_reads_only_declared_tables, make_bq_query,
    run_query, SqlInterpolationError, UndeclaredTableError,
)


@pytest.mark.parametrize("sql", [
    "SELECT * FROM t WHERE id = 'PUMP-104A'",
    'SELECT * FROM t WHERE id = "PUMP-104A"',
    "SELECT * FROM t WHERE n = 5",
])
def test_literal_values_in_predicates_are_rejected(sql):
    with pytest.raises(SqlInterpolationError):
        assert_no_interpolation(sql)


def test_parameterised_sql_is_accepted():
    assert_no_interpolation("SELECT * FROM t WHERE id = @asset_id LIMIT @n")


def test_run_query_returns_rows_and_a_count():
    rows, scanned = run_query(
        "SELECT asset_id FROM `mining_data.assets` "
        "WHERE asset_id = @asset_id",
        {"asset_id": "PUMP-104A"},
        ["mining_data.assets"],
    )
    assert len(rows) == 1
    assert rows[0]["asset_id"] == "PUMP-104A"
    assert scanned == 1


def test_enveloped_tool_reports_the_declared_tables():
    q = make_bq_query(["mining_data.assets"])
    env = q("SELECT COUNT(*) AS n_assets FROM `mining_data.assets`", {})
    Envelope.model_validate(env)
    assert env["success"] is True
    assert env["meta"]["tables_read"] == ["mining_data.assets"]
    # 88, not 5: `assets` was deepened from 5 rows to 88 to give the fleet and
    # maintenance agents enough depth to reason over. This asserts the envelope
    # carries the warehouse's real count, so pinning it to a literal means
    # repinning whenever the fixture data changes on purpose. What is being
    # tested is that the count is reported faithfully, not that it is any
    # particular number -- so assert against the live table instead.
    live = q("SELECT COUNT(*) AS n FROM `mining_data.assets`", {})["data"]["rows"][0]["n"]
    assert env["data"]["rows"][0]["n_assets"] == live
    assert live > 0, "assets is empty; the fixture is not loaded"


def test_interpolated_sql_fails_inside_the_envelope_not_as_a_crash():
    q = make_bq_query(["mining_data.assets"])
    asset = "PUMP-104A"
    env = q(f"SELECT * FROM `mining_data.assets` WHERE asset_id = '{asset}'", {})
    Envelope.model_validate(env)
    assert env["success"] is False
    assert env["error"]["code"] == "SQL_INTERPOLATION"
    assert env["meta"]["tables_read"] == ["mining_data.assets"]


# ---------------------------------------------------------------------------
# assert_reads_only_declared_tables — the control that constrains reach.
#
# Every case below is checked against a live BigQuery dry run, which is the
# point: these pin what the engine that runs the query says the query means,
# not what a parser or a regex guesses.
# ---------------------------------------------------------------------------

def test_a_query_reading_only_declared_tables_returns_what_it_read():
    read = assert_reads_only_declared_tables(
        "SELECT asset_id FROM `mining_data.assets` WHERE asset_id = @asset_id",
        {"asset_id": "PUMP-104A"},
        ["mining_data.assets", "mining_data.erp_work_orders"],
    )
    # Only the table actually touched, not the whole declared list.
    assert read == ["mining_data.assets"]


def test_reading_an_undeclared_table_is_refused():
    with pytest.raises(UndeclaredTableError) as exc:
        assert_reads_only_declared_tables(
            "SELECT COUNT(*) AS n FROM `mining_data.biometric_fatigue_logs`",
            {},
            ["mining_data.assets"],
        )
    assert exc.value.details["undeclared"] == ["mining_data.biometric_fatigue_logs"]


def test_a_join_is_refused_when_only_one_side_is_declared():
    """The subset check is over every table the statement resolves to, so
    smuggling an undeclared table in as a join partner does not work."""
    with pytest.raises(UndeclaredTableError) as exc:
        assert_reads_only_declared_tables(
            "SELECT a.asset_id FROM `mining_data.assets` a "
            "JOIN `mining_data.erp_work_orders` w USING (asset_id)",
            {},
            ["mining_data.assets"],
        )
    assert exc.value.details["undeclared"] == ["mining_data.erp_work_orders"]


def test_a_subquery_cannot_hide_an_undeclared_table():
    with pytest.raises(UndeclaredTableError) as exc:
        assert_reads_only_declared_tables(
            "SELECT asset_id FROM `mining_data.assets` WHERE asset_id IN ("
            "  SELECT asset_id FROM `mining_data.erp_work_orders`)",
            {},
            ["mining_data.assets"],
        )
    assert exc.value.details["undeclared"] == ["mining_data.erp_work_orders"]


def test_execute_immediate_is_refused_even_when_it_reads_a_declared_table():
    """The case the statement-type check exists for.

    BigQuery reports EXECUTE IMMEDIATE as SCRIPT with an EMPTY
    referenced_tables list — the dry run never resolves the string it will
    later run. A subset check alone passes this silently, because the empty
    set is a subset of everything. The declared table here is the one the
    statement reads, so a failure can only come from the statement-type gate.
    """
    with pytest.raises(UndeclaredTableError) as exc:
        assert_reads_only_declared_tables(
            "EXECUTE IMMEDIATE 'SELECT COUNT(*) FROM `mining_data.assets`'",
            {},
            ["mining_data.assets"],
        )
    assert exc.value.details["statement_type"] == "SCRIPT"


@pytest.mark.parametrize("sql,expected_type", [
    ("DELETE FROM `mining_data.assets` WHERE asset_id = @asset_id", "DELETE"),
    ("UPDATE `mining_data.assets` SET asset_name = @asset_id WHERE TRUE", "UPDATE"),
])
def test_dml_against_a_declared_table_is_refused(sql, expected_type):
    """A read tool must not write, even to a table the agent declares."""
    with pytest.raises(UndeclaredTableError) as exc:
        assert_reads_only_declared_tables(
            sql, {"asset_id": "PUMP-104A"}, ["mining_data.assets"],
        )
    assert exc.value.details["statement_type"] == expected_type


def test_a_query_that_reads_no_table_is_refused():
    """Not pedantry: a read that resolves to nothing makes meta.tables_read a
    lie, and it is how a caller would try to compute without being audited."""
    with pytest.raises(UndeclaredTableError, match="no table at all"):
        assert_reads_only_declared_tables(
            "SELECT 1 AS n", {}, ["mining_data.assets"],
        )


def test_a_cross_project_read_is_refused_even_for_a_public_dataset():
    """Normalisation strips only THIS project's prefix, so a table in another
    project keeps its prefix and can match no declaration."""
    with pytest.raises(UndeclaredTableError) as exc:
        assert_reads_only_declared_tables(
            "SELECT word FROM `bigquery-public-data.samples.shakespeare` LIMIT 1",
            {},
            ["mining_data.assets", "samples.shakespeare"],
        )
    assert exc.value.details["undeclared"] == [
        "bigquery-public-data.samples.shakespeare"
    ]


def test_a_declaration_written_with_the_project_prefix_still_matches():
    """Both sides are normalised, so the same table declared either way works.
    tests/catalog/test_loader.py declares fully-qualified scratch tables."""
    read = assert_reads_only_declared_tables(
        "SELECT asset_id FROM `mining_data.assets` LIMIT 1",
        {},
        [f"{settings().project_id}.mining_data.assets"],
    )
    assert read == ["mining_data.assets"]


def test_the_check_survives_being_given_the_project_number_as_agent_engine_does():
    """The bug that made every live query fail, pinned against real BigQuery.

    Agent Engine sets GOOGLE_CLOUD_PROJECT to the project NUMBER. BigQuery
    accepts the number when the job is submitted but reports
    `referenced_tables` with the project ID, so normalisation keyed on the
    number strips nothing: the declared side stayed short-form, the referenced
    side stayed fully qualified, and D01's first live query was refused as
    UNDECLARED_TABLE naming the table it had declared.

    Nothing in this suite caught it because tests run against the stand-in
    project from conftest.py, where the configured id and the id BigQuery
    reports are the same string. This test reproduces the container's
    configuration instead, where they differ.
    """
    import mining_agents.tools.bq_query as module

    # The number is INPUT here — it stands in for the container's environment,
    # not for the value under test. The guard below is what keeps it honest: if
    # it ever equalled the project id, this test would exercise nothing.
    project_number = "111222333444"
    assert project_number != settings().project_id, (
        "the stand-in for GOOGLE_CLOUD_PROJECT must be a DIFFERENT spelling of "
        "the project than the id, or this test reproduces nothing"
    )

    saved_client, saved_projects = module._client, module._home_projects
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_number
    module._client = None
    module._home_projects = None
    try:
        assert settings().project_id == project_number, "env override did not take"
        read = assert_reads_only_declared_tables(
            "SELECT asset_id FROM `mining_data.assets` LIMIT 1",
            {},
            ["mining_data.assets"],
        )
        assert read == ["mining_data.assets"]

        # The cross-project refusal must not have been widened to buy this.
        with pytest.raises(UndeclaredTableError) as exc:
            assert_reads_only_declared_tables(
                "SELECT word FROM `bigquery-public-data.samples.shakespeare` LIMIT 1",
                {},
                ["mining_data.assets"],
            )
        assert exc.value.details["undeclared"] == [
            "bigquery-public-data.samples.shakespeare"
        ]
    finally:
        os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
        module._client, module._home_projects = saved_client, saved_projects


def test_a_view_resolves_to_its_base_table_not_the_view():
    """Pin the limit of this control, so nobody plans around a false belief.

    BigQuery's dry run expands a plain view to the tables it selects from.
    That is good — access cannot be laundered through a view — but it means
    this control CANNOT be used to grant "the masked view, not the raw table":
    declaring v_fatigue_scored does not authorise the query that reads it, and
    declaring the raw table authorises both. Column-level masking has to be
    enforced elsewhere.
    """
    with pytest.raises(UndeclaredTableError) as exc:
        assert_reads_only_declared_tables(
            "SELECT operator_id FROM `mining_data.v_fatigue_scored` LIMIT 1",
            {},
            ["mining_data.v_fatigue_scored"],
        )
    assert exc.value.details["undeclared"] == ["mining_data.biometric_fatigue_logs"]

    # And the reverse: the raw declaration admits the view.
    read = assert_reads_only_declared_tables(
        "SELECT operator_id FROM `mining_data.v_fatigue_scored` LIMIT 1",
        {},
        ["mining_data.biometric_fatigue_logs"],
    )
    assert read == ["mining_data.biometric_fatigue_logs"]


def test_run_query_enforces_the_constraint_for_every_tool_not_just_bq_query():
    """The check lives in run_query, so every tool with author-written SQL is
    covered by the same gate as the agent-authored one. Counting them here
    would be a number to maintain twice; run_query's own docstring names them,
    and test_every_tool_that_reads_bigquery_goes_through_run_query holds the
    set to whatever the package actually ships."""
    with pytest.raises(UndeclaredTableError):
        run_query(
            "SELECT COUNT(*) AS n FROM `mining_data.biometric_fatigue_logs`",
            {},
            ["mining_data.assets"],
        )


def test_every_tool_that_reads_bigquery_goes_through_run_query():
    """The declared-table check is only estate-wide while run_query is the one
    door out to BigQuery.

    A fork adding the hundred-and-first agent's tool is far likelier to reach
    for `bigquery.Client().query(...)` — every example on the internet does —
    than to find this module, and nothing at runtime would object: the query
    would run, return rows, and read whatever it liked. So the door is held
    shut here, by reading the package rather than by trusting the habit.

    Writes are a separate matter and are allowed their own client. The check
    dry-runs a SELECT to learn which tables it touches; an insert reads
    nothing, and the tables it writes are fixed by this repository's own code
    rather than chosen by an agent.
    """
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parents[2] / "mining_agents"
    reads = re.compile(r"\.query\(|\.query_and_wait\(")
    offenders = sorted(
        str(path.relative_to(root))
        for path in root.rglob("*.py")
        if path.name != "bq_query.py" and reads.search(path.read_text())
    )
    assert offenders == [], (
        f"{offenders} query BigQuery directly, so nothing checks what they read"
    )


def test_an_undeclared_read_fails_inside_the_envelope_not_as_a_crash():
    q = make_bq_query(["mining_data.assets"])
    env = q("SELECT COUNT(*) AS n FROM `mining_data.biometric_fatigue_logs`", {})
    Envelope.model_validate(env)
    assert env["success"] is False
    assert env["error"]["code"] == "UNDECLARED_TABLE"
    assert env["meta"]["tables_read"] == ["mining_data.assets"]


# ---------------------------------------------------------------------------
# Inbound biometric masking, applied in run_query for the same reason the
# declared-table check is: every tool that returns BigQuery rows goes through
# it, so no tool can be left out by omission — and the test above keeps that
# "every" true as tools are added.
# ---------------------------------------------------------------------------

def test_run_query_masks_raw_biometric_columns():
    rows, scanned = run_query(
        "SELECT operator_id, heart_rate_bpm, sleep_deficit_hours, "
        "microsleep_events_detected FROM `mining_data.biometric_fatigue_logs` "
        "LIMIT 3",
        {},
        ["mining_data.biometric_fatigue_logs"],
    )
    assert scanned == 3, "masking must not change the row count"
    for row in rows:
        assert row["heart_rate_bpm"] == REDACTION
        assert row["sleep_deficit_hours"] == REDACTION
        assert row["microsleep_events_detected"] == REDACTION
        assert row["operator_id"].startswith("OP-"), "pseudonym must survive"


def test_the_fatigue_band_view_is_readable_and_carries_no_raw_columns():
    """The path agents are told to use. v_fatigue_scored computes the band in
    SQL, so nothing needing masking is returned in the first place."""
    rows, _ = run_query(
        "SELECT operator_id, fatigue_band FROM `mining_data.v_fatigue_scored` "
        "LIMIT 3",
        {},
        ["mining_data.biometric_fatigue_logs"],
    )
    assert len(rows) == 3
    assert {r["fatigue_band"] for r in rows} <= {"LOW", "ELEVATED", "HIGH"}
    assert all(REDACTION not in str(v) for r in rows for v in r.values())


def test_run_query_wraps_free_text_so_the_prompt_instruction_is_true():
    """mining_agents/patterns/deep.py tells every agent that free text arrives wrapped.
    This is the test that makes that claim true rather than aspirational."""
    rows, _ = run_query(
        "SELECT log_entry_id, technician_notes FROM `mining_data.maintenance_logs` "
        "WHERE technician_notes IS NOT NULL LIMIT 3",
        {},
        ["mining_data.maintenance_logs"],
    )
    assert len(rows) == 3
    for row in rows:
        assert row["technician_notes"].startswith(UNTRUSTED_PREFIX)
        assert "mining_data.maintenance_logs.technician_notes" in (
            row["technician_notes"]
        )
        assert UNTRUSTED_PREFIX not in row["log_entry_id"], (
            "only the declared free-text columns may be wrapped"
        )


def test_wrapping_is_keyed_on_what_was_read_not_on_what_was_declared():
    """An agent declaring four tables and reading one must not have the other
    three's columns wrapped by name. Here `description` is a free-text column of
    erp_work_orders, but the query reads only safety_incidents — so the label
    must name safety_incidents alone."""
    rows, _ = run_query(
        "SELECT description FROM `mining_data.safety_incidents` "
        "WHERE description IS NOT NULL LIMIT 1",
        {},
        ["mining_data.safety_incidents", "mining_data.erp_work_orders",
         "mining_data.maintenance_logs", "mining_data.assets"],
    )
    assert "mining_data.safety_incidents.description" in rows[0]["description"]
    assert "mining_data.erp_work_orders" not in rows[0]["description"]


def test_an_alias_survives_row_masking_and_is_left_to_the_output_scrub():
    """Pin the hole against live BigQuery, not just in a unit test.

    `SELECT heart_rate_bpm AS hr` returns a column named `hr` — the dry run
    confirms the output schema is ['hr'] — so nothing in the returned row
    identifies it as biometric. redact_model_response is what catches this,
    on the way out, if the model labels the value in its answer.
    """
    rows, _ = run_query(
        "SELECT heart_rate_bpm AS hr FROM `mining_data.biometric_fatigue_logs` "
        "LIMIT 1",
        {},
        ["mining_data.biometric_fatigue_logs"],
    )
    assert isinstance(rows[0]["hr"], int)
    assert rows[0]["hr"] != REDACTION


def test_a_date_column_comes_back_json_serialisable():
    """Rows must survive json.dumps, because the model API serialises them.

    `assets.installation_date` is DATE, and the BigQuery client returns it as a
    `datetime.date`. Nothing in the tool layer converted it, so the tool
    response reached the SDK's JSON encoder unchanged and raised TypeError
    there — surfacing to the caller as an unexplained HTTP 500 rather than a
    ToolFailure naming the column.

    Asserted by actually calling json.dumps rather than by checking the type,
    so the test states the property that matters instead of the mechanism that
    currently provides it. The value is compared to BigQuery's own ISO
    rendering of the same column, so this cannot pass by finding an empty row
    set or a NULL: both assertions require a real date to be present.
    """
    import json

    rows, count = run_query(
        "SELECT installation_date, "
        "FORMAT_DATE('%Y-%m-%d', installation_date) AS expected "
        "FROM `mining_data.assets` "
        "WHERE installation_date IS NOT NULL LIMIT 1",
        {},
        ["mining_data.assets"],
    )
    assert count == 1, "no asset has an installation_date — the fixture changed"
    json.dumps(rows)          # the assertion: this raised TypeError before
    assert rows[0]["installation_date"] == rows[0]["expected"]
