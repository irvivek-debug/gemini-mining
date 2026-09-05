"""doc_search returns cited passages, and its SQL survives the literal lint."""
import pytest

from mining_agents.tools.bq_query import assert_no_interpolation
from mining_agents.tools.doc_search import SEARCH_SQL, doc_search


def test_the_sql_carries_no_literal_predicate():
    # top_k => 5 would be refused: the '>' of '=>' plus a digit matches the
    # literal-predicate regex. This gate is why the tool passes top_k => @k.
    assert_no_interpolation(SEARCH_SQL)


def test_the_sql_declares_the_model_as_well_as_the_table():
    # A BQML model is reported by the dry run as a referenced table, so
    # assert_reads_only_declared_tables refuses the query unless it is declared.
    from mining_agents.tools.doc_search import TABLES
    assert TABLES == [
        "mining_data.doc_chunks_embedded",
        "mining_data.text_embedding_model",
    ]


@pytest.mark.integration
def test_the_crusher_manual_ranks_first_for_a_crusher_query():
    """Rank, not mere presence.

    The agent cites the passage it reads first, so "somewhere in the top five"
    is not the property that matters. Asserting only presence would let
    ORDER BY distance be dropped or reversed without any test noticing: the
    corpus is 48 chunks, so almost anything appears in a top-5.
    """
    said = doc_search("crusher gap size aperture torque limit", k=5)
    assert said["success"], said.get("error")
    passages = said["data"]["passages"]
    names = [p["file_name"] for p in passages]
    assert "crusher" in names[0], names
    # Ascending distance is what makes names[0] the nearest rather than an
    # arbitrary row. This is the assertion that pins ORDER BY.
    distances = [p["distance"] for p in passages]
    assert distances == sorted(distances), distances


@pytest.mark.integration
def test_passages_carry_their_source_for_citation():
    said = doc_search("closed side setting", k=3)
    assert said["success"], said.get("error")
    for passage in said["data"]["passages"]:
        assert passage["file_name"], "a passage with no source cannot be cited"
        assert passage["chunk_text"].strip()
