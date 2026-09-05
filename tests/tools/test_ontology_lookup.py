"""Tests for ontology_lookup tool."""
from mining_agents.envelope import Envelope
from mining_agents.tools.ontology_lookup import TABLES, ontology_lookup


def test_a_known_concept_returns_its_related_concepts():
    env = ontology_lookup("CONVEYOR-02")
    Envelope.model_validate(env)
    assert env["success"] is True
    assert len(env["data"]["related"]) == 4
    assert all({"subject", "predicate", "object"} <= set(r)
               for r in env["data"]["related"])


def test_meta_names_both_graph_element_tables():
    env = ontology_lookup("CONVEYOR-02")
    assert env["meta"]["tables_read"] == [
        "mining_data.ontology_concepts",
        "mining_data.ontology_triples",
    ]


def test_declared_tables_come_from_the_traversal_not_a_literal():
    from mining_agents.tools.graph_traverse import TRAVERSALS
    assert TABLES == list(TRAVERSALS["ontology_related"].tables_read)


def test_an_unknown_concept_succeeds_with_empty_results():
    env = ontology_lookup("NO-SUCH-CONCEPT-ZZZ")
    Envelope.model_validate(env)
    assert env["success"] is True
    assert env["data"]["related"] == []
    assert env["data"]["concept"] == "NO-SUCH-CONCEPT-ZZZ"
