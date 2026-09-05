"""Registry payloads for the 52 externally-callable agents.

Swarm specialists and critics are sub-agents reachable only through their
coordinator. Registering them would falsely advertise 48 independently callable
agents as top-level Gateway endpoints — 12 swarms x (3 specialists + 1 critic).

Ruling R1: GATEWAY_SERVICE_ACCOUNT is the identity the Agent Gateway uses when
it forwards a request to a top-level agent. This account is provisioned outside
the three tier accounts and is NOT created by infra.iam.service_accounts.apply().
It must not appear in {sa_email(a) for a in ALL_AGENTS} — a test enforces this.
"""
from __future__ import annotations

import copy

from mining_agents.catalog.definitions import ALL_AGENTS, SWARMS, AgentDef
from mining_agents.config import settings
from infra.iam.service_accounts import sa_email

VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# R1: External Gateway identity — provisioned outside the tier accounts that
# infra.iam.service_accounts.apply() creates.
#
# THE LOCAL PART OF THIS ADDRESS IS A PLACEHOLDER, NOT A CONFIRMED NAME.
# `gcloud iam service-accounts list` on this project returns no `agent-gateway`
# account, and the Agent Gateway team has not confirmed what theirs is called.
# It is written as a named constant precisely so that the guess lives in one
# place: every caller_allowlist entry for a top-level agent resolves through
# here, so confirming the real name is a one-line change plus a test run.
#
# Until it is confirmed, treat a Gateway call rejected by the allowlist as a
# likely symptom of this constant rather than of the allowlist logic.
#
# The test suite pins the one property that holds regardless of the name: this
# account must never collide with an agent's own tier account, or the Gateway
# would be indistinguishable from the agents it invokes.
# ---------------------------------------------------------------------------
GATEWAY_SERVICE_ACCOUNT: str = (
    f"agent-gateway@{settings().project_id}.iam.gserviceaccount.com"
)

# ---------------------------------------------------------------------------
# R2: GUARDRAILS is a module-level constant for reference and equality checks,
# but registration() copies it — callers cannot mutate the constant through a
# returned payload.
# ---------------------------------------------------------------------------
GUARDRAILS: dict[str, int] = {
    "max_input_bytes": 32768,       # 32 KB
    "max_output_bytes": 262144,     # 256 KB
    "rate_limit_per_min": 60,
}

# ---------------------------------------------------------------------------
# R2: the input-schema template; registration() deep-copies it so no two
# payloads share an object reference.
#
# Private where GUARDRAILS is public, deliberately: GUARDRAILS is part of this
# module's declared interface (callers compare a payload's guardrails against
# it), whereas the schema is only ever read through a registration payload.
# ---------------------------------------------------------------------------
_INPUT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "maxLength": 8192},
        "context": {"type": "object"},
    },
    "required": ["query"],
    "additionalProperties": False,
}

# Pre-built map: sub-agent_id -> coordinator AgentDef.
# Built once at import time; read-only thereafter.
_COORDINATOR_OF: dict[str, AgentDef] = {
    member.agent_id: swarm.coordinator
    for swarm in SWARMS
    for member in [*swarm.specialists, swarm.critic]
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def registrable() -> list[AgentDef]:
    """The 12 swarm coordinators plus the 40 Pattern B deep agents (52 total).

    Specialists and critics are excluded: they are sub-agents callable only
    through their coordinator and must not be advertised as independent
    Gateway endpoints.
    """
    return [
        a for a in ALL_AGENTS
        if a.pattern == "B" or a.swarm_role == "coordinator"
    ]


def caller_allowlist(agent: AgentDef) -> list[str]:
    """Who may invoke this agent.

    Sub-agent (specialist / critic): only its swarm coordinator's SA email.
    Top-level agent (coordinator / Pattern B): only the Agent Gateway SA.

    R1: For top-level agents we return GATEWAY_SERVICE_ACCOUNT rather than
    deriving a gateway email via string surgery on the agent's own address —
    which would reference an account that Task 14 never creates.
    """
    coordinator = _COORDINATOR_OF.get(agent.agent_id)
    if coordinator is not None:
        return [sa_email(coordinator)]
    return [GATEWAY_SERVICE_ACCOUNT]


def registration(agent: AgentDef) -> dict:
    """Full registration payload for a single agent.

    R2: Every mutable field is deep-copied so that mutations by the caller
    cannot corrupt the module-level constants or the catalog's AgentDef objects.
    Specifically: guardrails, input_schema, and source_tables are all independent
    copies on every call.
    """
    return {
        "agent_id": agent.agent_id,
        "version": VERSION,
        "framework": "ADK",
        "display_name": agent.display_name,
        "service_account": sa_email(agent),
        "capability_tags": {
            "pattern": agent.pattern,
            "apqc_code": agent.apqc_code,
            "persona": agent.persona,
            "value_branch": agent.value_branch,
        },
        "input_schema": copy.deepcopy(_INPUT_SCHEMA),   # R2: independent copy
        "guardrails": copy.deepcopy(GUARDRAILS),         # R2: independent copy
        "caller_allowlist": caller_allowlist(agent),
        "hitl_required": agent.hitl_required,
        "source_tables": list(agent.source_tables),      # R2: independent copy
    }


def registrations() -> list[dict]:
    """Registration payloads for all 52 externally-callable agents."""
    return [registration(a) for a in registrable()]
