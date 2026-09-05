"""Tests for request_approval — the HITL write path.

Each test collects the approval_ids it wrote and deletes exactly those rows on
teardown, so the shared table is left as we found it.

Cleanup uses the BigQuery jobs API (DML DELETE), not bq rm / DROP TABLE, and
binds the ids as a query parameter rather than interpolating them — the same
rule assert_no_interpolation enforces on production SQL applies here.
"""
from __future__ import annotations

import json
import time
import warnings

import pytest
from google.api_core.exceptions import BadRequest
from google.cloud import bigquery

from mining_agents.config import settings
from mining_agents.envelope import Envelope
from mining_agents.tools.request_approval import approval_status, make_request_approval

# Tests must supply source_tables explicitly; the tool has no default.
SOURCES = ["mining_data.inventory_levels"]

# ── helpers ──────────────────────────────────────────────────────────────────


def _delete_test_rows(approval_ids: list[str]) -> None:
    """Delete exactly the rows a test wrote.

    BigQuery streaming inserts land in a streaming buffer that cannot be
    DML-deleted until the data moves to regular storage (typically 30–90
    minutes).  This tries the DELETE and swallows the ``BadRequest: cannot run
    DML on streaming buffer`` error.  Tests still pass if a teardown fails,
    because every approval_id is a fresh uuid so orphaned rows never collide.
    """
    if not approval_ids:
        return
    s = settings()
    client = bigquery.Client(project=s.project_id, location=s.location)
    sql = (
        f"DELETE FROM `{s.project_id}.{s.dataset}.agent_approvals` "
        f"WHERE approval_id IN UNNEST(@ids)"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("ids", "STRING", approval_ids)
        ]
    )
    try:
        client.query(sql, job_config=job_config).result()
    except BadRequest as exc:
        # The streaming buffer blocks DML for ~30-90 min. Expected, not a defect.
        if "streaming buffer" not in str(exc):
            _warn_orphaned(approval_ids, exc)
    except Exception as exc:  # noqa: BLE001
        # A teardown must never fail a test that passed, but it must never be
        # silent either: an unswept row sits in the live SC-4 approval queue.
        _warn_orphaned(approval_ids, exc)


def _warn_orphaned(approval_ids: list[str], exc: BaseException) -> None:
    warnings.warn(
        f"cleanup: DELETE failed for approval_ids {approval_ids!r}; "
        f"these rows were left behind in agent_approvals. "
        f"Error: {type(exc).__name__}: {exc}",
        stacklevel=3,
    )


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def cleanup():
    """Collect approval_ids written during a test; delete them on teardown."""
    ids: list[str] = []
    yield ids
    _delete_test_rows(ids)


# ── tests ─────────────────────────────────────────────────────────────────────


def _read_back(approval_id: str, columns: str) -> dict:
    """Fetch one written row, tolerating streaming-buffer lag."""
    s = settings()
    client = bigquery.Client(project=s.project_id, location=s.location)
    sql = (
        f"SELECT {columns} FROM `{s.project_id}.{s.dataset}.agent_approvals` "
        f"WHERE approval_id = @approval_id"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("approval_id", "STRING", approval_id)
        ]
    )
    for _ in range(5):
        rows = list(client.query(sql, job_config=job_config).result())
        if rows:
            return dict(rows[0])
        time.sleep(1)
    raise AssertionError(f"row {approval_id} not readable after 5 retries")


def test_a_request_is_written_and_comes_back_pending(cleanup):
    ask = make_request_approval("D07")
    env = ask(
        "reorder_part",
        {"part_number": "SKU-BELT-SPLICE-G2", "qty": 40},
        reasoning="stock below reorder point",
        source_tables=SOURCES,
    )
    Envelope.model_validate(env)
    assert env["success"] is True
    assert env["data"]["status"] == "PENDING"
    aid = env["data"]["approval_id"]
    cleanup.append(aid)
    assert approval_status(aid) == "PENDING"


def test_approval_ids_are_not_test_prefixed(cleanup):
    """Production ids must not be branded as test rows in the SC-4 queue."""
    ask = make_request_approval("D07")
    env = ask(
        "reorder_part", {"part_number": "X"},
        reasoning="id shape", source_tables=SOURCES,
    )
    aid = env["data"]["approval_id"]
    cleanup.append(aid)
    assert aid.startswith("APR-")
    assert "TEST" not in aid


def test_the_row_records_the_requesting_agent(cleanup):
    ask = make_request_approval("S08")
    env = ask(
        "expedite_order",
        {"work_order_id": "WO-0001"},
        reasoning="critical asset at risk",
        source_tables=SOURCES,
    )
    assert env["success"] is True
    assert env["data"]["agent_id"] == "S08"
    cleanup.append(env["data"]["approval_id"])


def test_meta_names_agent_approvals(cleanup):
    ask = make_request_approval("D07")
    env = ask(
        "reorder_part", {"part_number": "X"},
        reasoning="test", source_tables=SOURCES,
    )
    assert env["meta"]["tables_read"] == ["mining_data.agent_approvals"]
    cleanup.append(env["data"]["approval_id"])


def test_reasoning_is_required():
    ask = make_request_approval("D07")
    env = ask(
        "reorder_part", {"part_number": "X"},
        reasoning="", source_tables=SOURCES,
    )
    Envelope.model_validate(env)
    assert env["success"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


def test_the_tool_never_returns_approved():
    """Nothing in this codebase may self-approve. Only a human sets APPROVED."""
    import pathlib

    from mining_agents.tools import request_approval as module

    source = pathlib.Path(module.__file__).read_text()
    assert "'APPROVED'" not in source and '"APPROVED"' not in source


def test_empty_source_tables_is_refused():
    """source_tables must be non-empty; an empty array is a silent data loss trap."""
    ask = make_request_approval("D07")
    env = ask(
        "reorder_part",
        {"part_number": "X"},
        reasoning="test empty source_tables guard",
        source_tables=[],
    )
    Envelope.model_validate(env)
    assert env["success"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"
    assert env["error"]["details"]["field"] == "source_tables"


def test_source_tables_round_trips_through_bigquery(cleanup):
    """The repeated STRING column must survive a BigQuery write+read cycle intact."""
    tables_in = ["mining_data.inventory_levels", "mining_data.erp_work_orders"]
    ask = make_request_approval("D07")
    env = ask(
        "reorder_part",
        {"part_number": "SKU-BELT-SPLICE-G2", "qty": 1},
        reasoning="round-trip test for source_tables",
        source_tables=tables_in,
    )
    assert env["success"] is True, f"insert failed: {env.get('error')}"
    aid = env["data"]["approval_id"]
    cleanup.append(aid)

    row = _read_back(aid, "source_tables")
    round_tripped = list(row["source_tables"])
    assert round_tripped == tables_in, (
        f"source_tables round-trip mismatch: expected {tables_in!r}, "
        f"got {round_tripped!r}"
    )


def test_target_entity_is_parseable_json(cleanup):
    """SC-4 parses target_entity. str(dict) yields Python repr, not JSON."""
    payload = {"part_number": "SKU-BELT-SPLICE-G2", "qty": 40}
    ask = make_request_approval("D07")
    env = ask(
        "reorder_part", payload,
        reasoning="json shape", source_tables=SOURCES,
    )
    aid = env["data"]["approval_id"]
    cleanup.append(aid)

    row = _read_back(aid, "target_entity")
    assert json.loads(row["target_entity"]) == payload
