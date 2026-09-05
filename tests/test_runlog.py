"""Tests for mining_agents.runlog — every agent invocation writes exactly one row.

Schema (from infra/ddl/agent_tables.sql):
  run_id, agent_id, parent_run_id, pattern, status, blocked_reason,
  started_at, ended_at, tables_read, rows_scanned

Status vocabulary: DONE | BLOCKED | ERROR  (not SUCCESS)
"""
from __future__ import annotations

import time
import uuid

import pytest
from google.api_core.exceptions import BadRequest
from google.cloud import bigquery

from mining_agents.config import settings
from mining_agents.runlog import logged_run, record_run


# ── helpers ──────────────────────────────────────────────────────────────────


def _delete_test_rows(run_ids: list[str]) -> None:
    """Delete exactly the rows a test wrote.

    Streaming inserts cannot be DML-deleted while in the streaming buffer
    (~30–90 minutes). We swallow that one BadRequest so the suite still passes,
    and nothing else — a swallowed auth or syntax error would leave rows behind
    with no signal.

    The project and dataset are interpolated because BigQuery cannot bind an
    identifier to a @parameter; they come from settings(), never from a test
    value. The run_ids — the only values here — are bound.
    """
    if not run_ids:
        return
    s = settings()
    client = bigquery.Client(project=s.project_id, location=s.location)
    sql = (
        f"DELETE FROM `{s.project_id}.{s.dataset}.agent_run_log` "
        f"WHERE run_id IN UNNEST(@ids)"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ArrayQueryParameter("ids", "STRING", run_ids)]
    )
    try:
        client.query(sql, job_config=job_config).result()
    except BadRequest as exc:
        if "streaming buffer" not in str(exc):
            raise


def _read_back(run_id: str) -> dict:
    """Fetch one written row, tolerating streaming-buffer read lag."""
    s = settings()
    client = bigquery.Client(project=s.project_id, location=s.location)
    sql = (
        f"SELECT * FROM `{s.project_id}.{s.dataset}.agent_run_log` "
        f"WHERE run_id = @run_id"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("run_id", "STRING", run_id)]
    )
    for _ in range(10):
        rows = list(client.query(sql, job_config=job_config).result())
        if rows:
            return dict(rows[0])
        time.sleep(2)
    raise AssertionError(f"row {run_id!r} not readable after 10 retries (20 s)")


# ── fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def cleanup():
    """Collect run_ids written during a test; delete them on teardown."""
    ids: list[str] = []
    yield ids
    _delete_test_rows(ids)


# ── tests ─────────────────────────────────────────────────────────────────────


def test_a_successful_run_writes_one_row(cleanup):
    marker = uuid.uuid4().hex[:8]
    with logged_run("D01") as run:
        run.tables_read = ["mining_data.telemetry_stream"]
        run.rows_scanned = 42
    cleanup.append(run.run_id)

    row = _read_back(run.run_id)
    assert row["agent_id"] == "D01"
    assert row["status"] == "DONE"
    assert row["pattern"] == "B"
    assert row["rows_scanned"] == 42
    assert row["blocked_reason"] is None


def test_a_failing_run_is_logged_then_reraised(cleanup):
    with pytest.raises(RuntimeError):
        with logged_run("D01") as run:
            run.tables_read = ["mining_data.telemetry_stream"]
            raise RuntimeError("boom")
    cleanup.append(run.run_id)

    row = _read_back(run.run_id)
    assert row["status"] == "ERROR"
    assert "boom" in row["blocked_reason"]


def test_a_blocked_run_writes_blocked_status_and_does_not_reraise(cleanup):
    """BLOCKED means agent ran correctly but could not reach a conclusion."""
    with logged_run("D35") as run:
        run.tables_read = ["mining_data.biometric_fatigue_logs"]
        run.block("no telemetry for asset — UNVERIFIED")
    cleanup.append(run.run_id)

    row = _read_back(run.run_id)
    assert row["status"] == "BLOCKED"
    assert "UNVERIFIED" in row["blocked_reason"]


def test_blocked_reason_is_scrubbed_before_write(cleanup):
    """blocked_reason passes through scrub(); raw biometrics must not persist."""
    with logged_run("D35") as run:
        run.tables_read = ["mining_data.biometric_fatigue_logs"]
        run.block("OP-014 heart_rate_bpm 118 -> HIGH")
    cleanup.append(run.run_id)

    row = _read_back(run.run_id)
    assert row["status"] == "BLOCKED"
    # Raw heart rate must be redacted
    assert "118" not in row["blocked_reason"]
    # Operator pseudonym is retained
    assert "OP-014" in row["blocked_reason"]


def test_tables_read_is_persisted_as_an_array(cleanup):
    """REPEATED STRING column must survive a BigQuery write+read round-trip intact."""
    with logged_run("D01") as run:
        run.tables_read = ["mining_data.telemetry_stream", "mining_data.assets"]
    cleanup.append(run.run_id)

    row = _read_back(run.run_id)
    assert sorted(row["tables_read"]) == [
        "mining_data.assets",
        "mining_data.telemetry_stream",
    ]


def test_parent_run_id_persists_lineage(cleanup):
    """A2A lineage: swarm specialist writes coordinator's run_id as parent."""
    parent_id = str(uuid.uuid4())
    with logged_run("S01-SP1", parent_run_id=parent_id) as child:
        child.tables_read = ["mining_data.telemetry_stream"]
    cleanup.append(child.run_id)

    row = _read_back(child.run_id)
    assert row["parent_run_id"] == parent_id


def test_record_run_returns_a_unique_id(cleanup):
    a = record_run("D01", "DONE", tables_read=["mining_data.assets"])
    b = record_run("D01", "DONE", tables_read=["mining_data.assets"])
    cleanup.extend([a, b])
    assert a != b


def test_pattern_is_derived_from_catalog_not_caller(cleanup):
    """pattern must come from the catalog, never from the caller."""
    # S01 is pattern A (swarm coordinator); D01 is pattern B (deep)
    with logged_run("S01") as run:
        run.tables_read = ["mining_data.telemetry_stream"]
    cleanup.append(run.run_id)

    row = _read_back(run.run_id)
    assert row["pattern"] == "A"


def test_unknown_agent_id_raises_value_error():
    """An agent_id not in the catalog must raise ValueError, not write a row."""
    with pytest.raises(ValueError, match="BOGUS_AGENT"):
        with logged_run("BOGUS_AGENT"):
            pass
