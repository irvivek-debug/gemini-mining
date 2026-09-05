"""End-to-end checks on the data paths the live demo walks through.

A property graph over unmatched tables returns zero rows with no error.
Every assertion below pins a real count for that reason.

Ruling 4: the ontology_lookup demo test is replaced with one that pins
the gap — asserting the set of agents holding ontology_lookup is exactly
empty. The tool is built and tested (tests/tools/test_ontology_lookup.py)
but is currently routed to no agent. This is a known open item awaiting
a customer decision, not an oversight.

Ruling 5: these tests exercise the *agent-level* path rather than
duplicating tests/tools/test_graph_traverse.py. For each scenario we
verify which agents declare the traversal in their catalog, assert the
count is non-empty and matches the expected value, then run the traversal
and pin its row count.
"""
from mining_agents.catalog.definitions import ALL_AGENTS
from mining_agents.tools.graph_traverse import make_graph_traverse
from mining_agents.tools.operational_math import operational_math


def test_sc2_blast_radius_from_a_degrading_conveyor():
    """blast_radius: 3 catalog agents declare this traversal; traversal returns 3 rows."""
    agents_with_blast = [a for a in ALL_AGENTS if "blast_radius" in a.traversals]
    assert len(agents_with_blast) == 3, (
        f"expected 3 agents with blast_radius traversal, got "
        f"{len(agents_with_blast)}: {[a.agent_id for a in agents_with_blast]}"
    )

    gt = make_graph_traverse(["blast_radius"])
    env = gt("blast_radius", {"asset_id": "CONVEYOR-02"})
    assert env["success"] is True
    assert len(env["data"]["rows"]) == 3
    assert env["meta"]["tables_read"]


def test_sc3_stockout_exposure_reaches_named_assets():
    """stockout_exposure: 5 catalog agents declare this traversal; returns 101 rows."""
    agents_with_stockout = [a for a in ALL_AGENTS if "stockout_exposure" in a.traversals]
    assert len(agents_with_stockout) == 5, (
        f"expected 5 agents with stockout_exposure traversal, got "
        f"{len(agents_with_stockout)}: {[a.agent_id for a in agents_with_stockout]}"
    )

    gt = make_graph_traverse(["stockout_exposure"])
    env = gt("stockout_exposure", {
        "below_rop_parts": ["SKU-BELT-SPLICE-G2", "SKU-LUBE-HEAVY-T2"],
        "asset_id": None,
    })
    assert len(env["data"]["rows"]) == 101
    # The demo names affected assets, so every row must carry one. A bare
    # truthiness check on the set would pass on 101 rows of empty asset_ids.
    unnamed = [r for r in env["data"]["rows"] if not r["asset_id"]]
    assert unnamed == []


def test_sc4_fatigue_chain_reaches_incidents():
    """fatigue_to_incident: 4 catalog agents declare this traversal; returns 167 rows."""
    agents_with_fatigue = [a for a in ALL_AGENTS if "fatigue_to_incident" in a.traversals]
    assert len(agents_with_fatigue) == 4, (
        f"expected 4 agents with fatigue_to_incident traversal, got "
        f"{len(agents_with_fatigue)}: {[a.agent_id for a in agents_with_fatigue]}"
    )

    gt = make_graph_traverse(["fatigue_to_incident"])
    env = gt("fatigue_to_incident", {"operator_id": "OP-103"})
    assert len(env["data"]["rows"]) == 167
    assert all(r["incident_id"] for r in env["data"]["rows"])


def test_ontology_lookup_is_not_granted_to_any_agent():
    """Ruling 4: ontology_lookup is built and tested but granted to zero agents.

    This test pins that gap so it is machine-visible and cannot drift silently.
    The tool exists (tests/tools/test_ontology_lookup.py verifies it works) but
    is currently routed to no agent — an open item awaiting a customer decision
    on whether an ontology-aware analyst belongs in the catalog.

    If this test ever fails (non-empty set), it means an agent was granted
    ontology_lookup; the failing test makes that explicit so the team can
    decide whether the grant is intentional.
    """
    agents_with_ontology = {a.agent_id for a in ALL_AGENTS if "ontology_lookup" in a.tools}
    assert agents_with_ontology == set(), (
        f"ontology_lookup should be granted to zero agents; "
        f"found: {agents_with_ontology}"
    )


def test_a_reorder_point_is_computed_in_python_not_by_a_model():
    env = operational_math("rop", {"avg_daily_demand": 12.0,
                                   "lead_time_days": 7.0,
                                   "safety_stock": 30.0})
    assert env["data"]["value"] == 114.0
    assert env["data"]["formula"] == "rop"
