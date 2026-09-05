"""Tests for mining_agents.registry — 52-agent registration payloads and gateway guardrails.

Ruling references:
  R1 - GATEWAY_SERVICE_ACCOUNT constant must be an external SA not in the 100 per-agent set.
  R2 - No payload may share mutable state with the catalog or module constants.
  R3 - Strengthen three brief tests: vacuous-pass guards.
  R4 - Partition check: 52 registrable + 48 sub-agents = all 100, no overlap.
"""
from mining_agents.build import build_all
from mining_agents.catalog.definitions import ALL_AGENTS, SWARMS
from mining_agents.config import settings
from infra.iam.service_accounts import sa_email
from mining_agents.registry import (
    GATEWAY_SERVICE_ACCOUNT,
    GUARDRAILS,
    VERSION,
    caller_allowlist,
    registrable,
    registration,
    registrations,
)


def test_exactly_fifty_two_agents_are_registered():
    ids = {a.agent_id for a in registrable()}
    assert len(ids) == 52
    assert {f"S{n:02d}" for n in range(1, 13)} <= ids
    assert {f"D{n:02d}" for n in range(1, 41)} <= ids


def test_specialists_and_critics_are_not_registered():
    ids = {a.agent_id for a in registrable()}
    assert "S01-SP1" not in ids
    assert "S01-CRITIC" not in ids


def test_the_guardrails_match_the_design_numbers():
    assert GUARDRAILS == {
        "max_input_bytes": 32768,
        "max_output_bytes": 262144,
        "rate_limit_per_min": 60,
    }


# ---------------------------------------------------------------------------
# Sub-agent caller allowlists under the three-account model.
#
# Under one-account-per-agent this test proved a coordinator could invoke only
# its OWN specialists. That is no longer true by identity: all 12 coordinators
# share mag-agent-coordinator, so IAM cannot tell S01's coordinator from S07's.
#
# Asserting `allowed == [sa_email(swarm.coordinator)]` in a loop would still
# pass — and prove nothing, because every iteration compares the same string to
# itself. The tests below pin what is actually true instead.
# ---------------------------------------------------------------------------
COORDINATOR_SA = f"mag-agent-coordinator@{settings().project_id}.iam.gserviceaccount.com"


def test_every_sub_agent_is_callable_only_by_the_coordinator_account():
    sub_agents = [m for swarm in SWARMS
                  for m in [*swarm.specialists, swarm.critic]]
    assert len(sub_agents) == 48

    wrong = {m.agent_id: caller_allowlist(m) for m in sub_agents
             if caller_allowlist(m) != [COORDINATOR_SA]}
    assert wrong == {}


def test_identity_does_not_separate_one_swarm_from_another():
    """Pin the cost of the three-account model at the registry layer.

    S01's coordinator and S07's coordinator present the same SA, so the
    caller allowlist cannot distinguish them. This is acceptable only because
    sub-agents are not deployed: they are nodes inside their coordinator's
    Workflow graph and have no endpoint for another coordinator to call. The
    allowlist is descriptive metadata here, not an enforced boundary.

    If sub-agents ever become separately deployed, this test fails to say so —
    at that point the allowlist would need real per-swarm identities.
    """
    assert sa_email(SWARMS[0].coordinator) == sa_email(SWARMS[6].coordinator)
    assert SWARMS[0].swarm_id != SWARMS[6].swarm_id

    built = build_all()
    for swarm in SWARMS:
        assert swarm.swarm_id in built
        for member in [*swarm.specialists, swarm.critic]:
            assert member.agent_id not in built, (
                f"{member.agent_id} is now separately deployed; the shared "
                f"coordinator account no longer suffices as its allowlist"
            )


# ---------------------------------------------------------------------------
# R3 — Strengthened: assert exact allowlist contents (not just vacuous all()).
# ---------------------------------------------------------------------------
def test_a_deep_agent_has_no_agent_caller_in_its_allowlist():
    deep = next(a for a in registrable() if a.agent_id == "D01")
    allowed = caller_allowlist(deep)
    # Must be non-empty (the Gateway SA must be present)
    assert allowed == [GATEWAY_SERVICE_ACCOUNT]
    # No coordinator/swarm-agent email in the allowlist
    assert all(not e.startswith("mag-s") for e in allowed)


def test_a_registration_carries_the_framework_and_capability_tags():
    d27 = next(a for a in registrable() if a.agent_id == "D27")
    entry = registration(d27)
    assert entry["framework"] == "ADK"
    assert entry["agent_id"] == "D27"
    # Pinned to exact values rather than truthiness: `assert entry["version"]`
    # would pass on "v0", " ", or any other wrong-but-non-empty string.
    assert entry["version"] == VERSION
    assert entry["display_name"] == d27.display_name
    assert entry["display_name"] == "Safety Stock & Reorder Point Calculator"
    assert set(entry["capability_tags"]) >= {"pattern", "apqc_code", "persona",
                                             "value_branch"}
    # D27 is a non-HITL deep agent, so it runs as the shared base-tier account.
    assert entry["service_account"] == (
        f"mag-agent-base@{settings().project_id}.iam.gserviceaccount.com"
    )
    assert entry["guardrails"] == GUARDRAILS


# ---------------------------------------------------------------------------
# R3 — Strengthened: assert count == 52 inside the same test.
# ---------------------------------------------------------------------------
def test_every_registration_declares_an_input_schema():
    all_registrations = list(registrations())
    assert len(all_registrations) == 52, (
        f"Expected 52 registrations, got {len(all_registrations)}"
    )
    for entry in all_registrations:
        assert entry["input_schema"]["type"] == "object"
        assert "query" in entry["input_schema"]["properties"]


def test_all_fifty_two_registrations_build():
    assert len(registrations()) == 52


# ---------------------------------------------------------------------------
# R2 — No shared mutable state between payloads and the catalog.
# ---------------------------------------------------------------------------
def test_registration_payloads_do_not_share_mutable_state_with_each_other():
    """Mutating a returned payload must not affect a second call for the same agent."""
    agent = next(a for a in registrable() if a.agent_id == "D27")

    payload1 = registration(agent)
    payload2 = registration(agent)

    # guardrails: must not be the same object
    assert payload1["guardrails"] is not payload2["guardrails"], (
        "registration() returned the same mutable guardrails dict on two calls"
    )
    # Mutate payload1's guardrails; payload2 must be unaffected
    payload1["guardrails"]["max_input_bytes"] = 99999
    assert payload2["guardrails"]["max_input_bytes"] == 32768, (
        "Mutating payload1 guardrails corrupted payload2"
    )

    # input_schema: must not be the same object
    assert payload1["input_schema"] is not payload2["input_schema"], (
        "registration() returned the same mutable input_schema dict on two calls"
    )
    payload1["input_schema"]["type"] = "CORRUPT"
    assert payload2["input_schema"]["type"] == "object", (
        "Mutating payload1 input_schema corrupted payload2"
    )


def test_registration_payloads_do_not_share_source_tables_with_catalog():
    """Mutating a returned payload's source_tables must not corrupt the catalog."""
    agent = next(a for a in registrable() if a.agent_id == "D27")
    original_tables = list(agent.source_tables)

    payload = registration(agent)
    payload["source_tables"].append("INJECTED_TABLE")

    # Catalog must be untouched
    assert agent.source_tables == original_tables, (
        "Mutating payload source_tables corrupted agent.source_tables in the catalog"
    )

    # A fresh payload must also be clean
    payload2 = registration(agent)
    assert "INJECTED_TABLE" not in payload2["source_tables"]


# ---------------------------------------------------------------------------
# R1 — GATEWAY_SERVICE_ACCOUNT must not be among the 100 per-agent SAs.
# ---------------------------------------------------------------------------
def test_gateway_service_account_is_not_a_per_agent_account():
    """The Gateway SA is provisioned externally — it is NOT one of the 100 Task-14 accounts."""
    per_agent_emails = {sa_email(a) for a in ALL_AGENTS}
    assert GATEWAY_SERVICE_ACCOUNT not in per_agent_emails, (
        f"GATEWAY_SERVICE_ACCOUNT ({GATEWAY_SERVICE_ACCOUNT}) "
        "must not be one of the 100 per-agent service accounts created by Task 14"
    )


# ---------------------------------------------------------------------------
# R4 — Partition check: 52 registrable + 48 sub-agents = all 100, no overlap.
# ---------------------------------------------------------------------------
def test_registrable_and_sub_agents_partition_all_one_hundred():
    """The 52 registrable IDs and the 48 sub-agent IDs must together equal the
    full catalog of 100 agents with no overlap.  No agent is dropped.
    """
    all_catalog_ids = {a.agent_id for a in ALL_AGENTS}
    assert len(all_catalog_ids) == 100, (
        f"Expected 100 catalog agents, got {len(all_catalog_ids)}"
    )

    registrable_ids = {a.agent_id for a in registrable()}
    assert len(registrable_ids) == 52

    sub_agent_ids = {
        member.agent_id
        for swarm in SWARMS
        for member in [*swarm.specialists, swarm.critic]
    }
    assert len(sub_agent_ids) == 48, (
        f"Expected 48 sub-agents (12 swarms × 4), got {len(sub_agent_ids)}"
    )

    # No overlap
    overlap = registrable_ids & sub_agent_ids
    assert overlap == set(), f"Unexpected overlap between registrable and sub-agents: {overlap}"

    # Together they cover all 100
    union = registrable_ids | sub_agent_ids
    assert union == all_catalog_ids, (
        f"Union of registrable + sub-agents != all catalog agents. "
        f"Missing: {all_catalog_ids - union}. Extra: {union - all_catalog_ids}"
    )
