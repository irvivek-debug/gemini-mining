"""Semantic search over the document corpus, returning citable passages.

Retrieval supplies resolution CONTENT — what a manual or a standard permits.
It must never supply method STRUCTURE: top-k search has no completeness
guarantee, and a driver whose chunk fails to retrieve would be silently
skipped, which reads to an operator as "no problem found".
"""
from __future__ import annotations

from mining_agents.tools.base import tool
from mining_agents.tools.bq_query import run_query

# The model is listed because a BigQuery dry run reports it among
# referenced_tables, so assert_reads_only_declared_tables refuses the query
# without it. Verified, not assumed.
TABLES = [
    "mining_data.doc_chunks_embedded",
    "mining_data.text_embedding_model",
]

# top_k is bound as @k deliberately. Written as `top_k => 5` this SQL is
# refused by assert_no_interpolation, because the '>' of '=>' followed by a
# digit matches the literal-predicate regex.
SEARCH_SQL = """
SELECT
  base.file_name  AS file_name,
  base.folder     AS folder,
  base.chunk_text AS chunk_text,
  distance
FROM VECTOR_SEARCH(
  TABLE `mining_data.doc_chunks_embedded`,
  'ml_generate_embedding_result',
  (SELECT ml_generate_embedding_result
     FROM ML.GENERATE_EMBEDDING(
       MODEL `mining_data.text_embedding_model`,
       (SELECT @query AS content),
       STRUCT(TRUE AS flatten_json_output, 'RETRIEVAL_QUERY' AS task_type))),
  top_k => @k)
ORDER BY distance
"""


@tool(TABLES)
def doc_search(query: str, k: int = 5):
    """Search manuals, standards and reports. Returns passages with sources."""
    passages, scanned = run_query(
        SEARCH_SQL, {"query": query, "k": int(k)}, TABLES
    )
    return {"query": query, "passages": passages}, scanned
