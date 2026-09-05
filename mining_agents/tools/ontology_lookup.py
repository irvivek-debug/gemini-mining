"""Ontology concept expansion over MiningOntologyGraph.

Pattern C capability enters this build here — as a tool, not as an agent.

The plan also specified a document-linking feature over
`unstructured_docs_metadata`. It is not implemented, because no honest join
exists: `ontology_concepts.concept_type` is NULL for all 25 rows, and the
document table carries only `doc_id`, `title`, `file_path`, `category`,
`chunk_count`, `last_updated` — no column can contain a concept name such as
`CONVEYOR-02`. A substring scan therefore returns empty for every concept,
which reads to an operator as "no documents exist for this concept" rather
than "this tool cannot answer that". A permanently-empty result is worse than
no result. Document linking needs a real join key generated upstream first.
"""
from __future__ import annotations

from mining_agents.tools.base import tool
from mining_agents.tools.bq_query import run_query
from mining_agents.tools.graph_traverse import TRAVERSALS

_SPEC = TRAVERSALS["ontology_related"]
TABLES = list(_SPEC.tables_read)


@tool(TABLES)
def ontology_lookup(concept: str):
    """Expand a concept into its related concepts via MiningOntologyGraph."""
    related, scanned = run_query(
        _SPEC.sql, {"concept": concept}, list(_SPEC.tables_read)
    )
    return {"concept": concept, "related": related}, scanned
