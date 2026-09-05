"""Tests for mining_agents.catalog.loader.

These tests require BigQuery and CANNOT be run without valid gcloud credentials.
Each test writes to a uniquely-named scratch table that is dropped on teardown —
they never truncate the shared mining_data.agent_catalog table.

Isolation pattern mirrors tests/test_runlog.py: a pytest fixture collects the
scratch table IDs created during a test and deletes them on teardown.
"""
from __future__ import annotations

import uuid

import pytest
from google.cloud import bigquery

from mining_agents.catalog.definitions import ALL_AGENTS
from mining_agents.catalog.loader import upsert_catalog
from mining_agents.config import settings
from mining_agents.tools.bq_query import run_query


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scratch_table_id(s) -> str:
    """Return a unique scratch table ID for one test run."""
    suffix = uuid.uuid4().hex[:12]
    return f"{s.project_id}.{s.dataset}.agent_catalog_test_{suffix}"


def _drop_table(client: bigquery.Client, table_id: str) -> None:
    """Drop a scratch table, silently ignoring 'not found'."""
    client.delete_table(table_id, not_found_ok=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def scratch_catalog():
    """Create a scratch catalog table from the production schema; drop it on teardown."""
    s = settings()
    client = bigquery.Client(project=s.project_id, location=s.location)
    prod_table_id = f"{s.project_id}.{s.dataset}.agent_catalog"
    table_id = _scratch_table_id(s)

    # Clone schema from production table so upsert_catalog() can use it.
    prod_schema = client.get_table(prod_table_id).schema
    scratch = bigquery.Table(table_id, schema=prod_schema)
    client.create_table(scratch)

    yield table_id

    _drop_table(client, table_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_upsert_writes_every_agent(scratch_catalog):
    written = upsert_catalog(destination_table=scratch_catalog)
    assert written == 100
    rows, _ = run_query(
        f"SELECT COUNT(*) AS n_agents FROM `{scratch_catalog}`",
        {}, [scratch_catalog],
    )
    assert rows[0]["n_agents"] == 100


def test_upsert_is_idempotent(scratch_catalog):
    upsert_catalog(destination_table=scratch_catalog)
    upsert_catalog(destination_table=scratch_catalog)
    rows, _ = run_query(
        f"SELECT COUNT(*) AS n_agents FROM `{scratch_catalog}`",
        {}, [scratch_catalog],
    )
    assert rows[0]["n_agents"] == 100


def test_every_declared_source_table_exists_in_bigquery():
    """A catalog row pointing at a phantom table would fail the PRD metric.

    This test reads from INFORMATION_SCHEMA only — it does not write to any table.
    """
    rows, _ = run_query(
        "SELECT table_name FROM `mining_data.INFORMATION_SCHEMA.TABLES`",
        {}, ["mining_data.INFORMATION_SCHEMA.TABLES"],
    )
    live = {r["table_name"] for r in rows}
    graphs = {"MiningAssetGraph", "MiningSupplyChainGraph",
              "MiningOperationsSafetyGraph", "MiningOntologyGraph"}
    missing = {}
    for agent in ALL_AGENTS:
        bad = [t for t in agent.source_tables
               if t.split(".")[-1] not in live | graphs]
        if bad:
            missing[agent.agent_id] = bad
    assert missing == {}, f"agents reference non-existent objects: {missing}"
