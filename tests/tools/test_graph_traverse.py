import pytest
from mining_agents.config import settings
from mining_agents.envelope import Envelope
from mining_agents.tools.graph_traverse import TRAVERSALS, make_graph_traverse


def test_all_four_graphs_are_covered():
    assert set(TRAVERSALS) == {
        "blast_radius", "stockout_exposure", "fatigue_to_incident", "ontology_related",
    }


@pytest.mark.parametrize("name", sorted(TRAVERSALS))
def test_traversals_use_edge_labels_not_table_names(name):
    sql = TRAVERSALS[name].sql
    for table_name in ("asset_dependencies", "work_order_parts_edge",
                       "operator_vehicle_assignments", "incident_involvements"):
        assert f"[:{table_name}" not in sql
    assert "GRAPH_TABLE" in sql


def test_blast_radius_returns_the_verified_row_count():
    gt = make_graph_traverse(["blast_radius"])
    env = gt("blast_radius", {"asset_id": "CONVEYOR-02"})
    Envelope.model_validate(env)
    assert env["success"] is True
    assert len(env["data"]["rows"]) == 3


def test_stockout_exposure_returns_the_verified_row_count():
    gt = make_graph_traverse(["stockout_exposure"])
    env = gt("stockout_exposure", {
        "below_rop_parts": ["SKU-BELT-SPLICE-G2", "SKU-LUBE-HEAVY-T2"],
        "asset_id": None,
    })
    assert env["success"] is True
    assert len(env["data"]["rows"]) == 101


def test_fatigue_to_incident_returns_the_verified_row_count():
    gt = make_graph_traverse(["fatigue_to_incident"])
    env = gt("fatigue_to_incident", {"operator_id": "OP-103"})
    assert env["success"] is True
    assert len(env["data"]["rows"]) == 167


def test_ontology_related_returns_the_verified_row_count():
    gt = make_graph_traverse(["ontology_related"])
    env = gt("ontology_related", {"concept": "CONVEYOR-02"})
    assert env["success"] is True
    assert len(env["data"]["rows"]) == 4


def test_a_sentinel_key_returns_zero_rows_but_still_succeeds():
    """Negative control: proves the row counts above are real matches."""
    gt = make_graph_traverse(["blast_radius"])
    env = gt("blast_radius", {"asset_id": "NO-SUCH-ASSET-ZZZ"})
    assert env["success"] is True
    assert env["data"]["rows"] == []


def test_an_unallowed_traversal_is_refused_inside_the_envelope():
    gt = make_graph_traverse(["blast_radius"])
    env = gt("fatigue_to_incident", {"operator_id": "OP-103"})
    Envelope.model_validate(env)
    assert env["success"] is False
    assert env["error"]["code"] == "TRAVERSAL_NOT_PERMITTED"
    assert env["meta"]["tables_read"]


def test_make_graph_traverse_rejects_empty_allowed_list():
    """I3: an empty allowed list must fail fast rather than advertising all tables."""
    with pytest.raises(ValueError, match="empty"):
        make_graph_traverse([])


@pytest.mark.parametrize("name,expected_tables", [
    (
        "blast_radius",
        {
            f"{settings().dataset}.assets",
            f"{settings().dataset}.asset_dependencies",
        },
    ),
    (
        "stockout_exposure",
        {
            f"{settings().dataset}.inventory_levels",
            f"{settings().dataset}.erp_work_orders",
            f"{settings().dataset}.work_order_parts_edge",
            f"{settings().dataset}.assets",
            # Not walked by the MATCH pattern, but part of the graph's DDL and
            # therefore resolved by BigQuery — see the note in graph_traverse.py.
            f"{settings().dataset}.procurement_bids",
            f"{settings().dataset}.bid_parts_edge",
        },
    ),
    (
        "fatigue_to_incident",
        {
            f"{settings().dataset}.fatigue_logs_node",
            f"{settings().dataset}.operators_node",
            f"{settings().dataset}.operator_vehicle_assignments",
            f"{settings().dataset}.fleet_vehicles",
            f"{settings().dataset}.incident_involvements",
            f"{settings().dataset}.safety_incidents",
        },
    ),
    (
        "ontology_related",
        {
            f"{settings().dataset}.ontology_concepts",
            f"{settings().dataset}.ontology_triples",
        },
    ),
])
def test_traversal_tables_read_matches_graph_backing_tables(name, expected_tables):
    """Pin each traversal's tables_read to its graph's backing tables.

    These sets are hand-written, so this test documents the expectation rather
    than deriving it. It was wrong for stockout_exposure until the dry-run
    check in run_query caught the gap: the set listed the tables the MATCH
    pattern walks, not the tables the graph is built from. What actually
    verifies these now is assert_reads_only_declared_tables, which asks
    BigQuery on every call and refuses the query if a traversal reads beyond
    what it declares.
    """
    assert set(TRAVERSALS[name].tables_read) == expected_tables
