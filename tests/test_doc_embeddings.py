"""The embedded table is what doc_search reads, so its shape is a gate."""
import pytest
from google.cloud import bigquery

from mining_agents.config import settings

pytestmark = pytest.mark.integration


def test_every_chunk_has_a_768_dim_embedding():
    s = settings()
    client = bigquery.Client(project=s.project_id, location=s.location)
    row = next(iter(client.query("""
        SELECT COUNT(*) AS n,
               COUNTIF(ARRAY_LENGTH(ml_generate_embedding_result) = 768) AS good
        FROM `mining_data.doc_chunks_embedded`
    """).result()))
    assert row["n"] > 0, "the embedded table is empty"
    assert row["good"] == row["n"], f"{row['n'] - row['good']} chunks embedded badly"


def test_embedded_row_count_matches_source():
    s = settings()
    client = bigquery.Client(project=s.project_id, location=s.location)
    row = next(iter(client.query("""
        SELECT (SELECT COUNT(*) FROM `mining_data.doc_chunks`) AS src,
               (SELECT COUNT(*) FROM `mining_data.doc_chunks_embedded`) AS emb
    """).result()))
    assert row["src"] == row["emb"], "embedding dropped rows"
