"""The single entry point. Builds every agent from the catalog."""
from __future__ import annotations

from mining_agents.catalog.definitions import DEEP, SWARMS
from mining_agents.patterns.deep import build_deep_agent
from mining_agents.patterns.swarm import build_swarm


_SWARM_BY_ID = {s.swarm_id: s for s in SWARMS}
_DEEP_BY_ID = {a.agent_id: a for a in DEEP}


def build_one(entry_id: str) -> object:
    """Build a single externally-callable entrypoint by id.

    A deployed package serves exactly one agent, so it constructs exactly one.
    Calling build_all() there would construct all 52 — 51 of them dead weight
    in every container, and 51 extra ways for an unrelated catalog error to
    fail a deployment that does not depend on it.

    Accepts a swarm id ("S01".."S12") or a deep agent id ("D01".."D40").
    A specialist or critic id is rejected: those are sub-agents reached through
    their coordinator, and giving one its own package would deploy it as an
    independently callable endpoint, which is exactly what the registry
    deliberately refuses to advertise.
    """
    swarm = _SWARM_BY_ID.get(entry_id)
    if swarm is not None:
        return build_swarm(swarm)
    agent = _DEEP_BY_ID.get(entry_id)
    if agent is not None:
        return build_deep_agent(agent)
    raise KeyError(
        f"{entry_id!r} is not an externally-callable entrypoint. Expected a "
        f"swarm id (S01..S12) or a deep agent id (D01..D40). Swarm specialists "
        f"and critics are not entrypoints — they run inside their "
        f"coordinator's graph and share its process."
    )


def build_all() -> dict[str, object]:
    """agent_id -> built agent, for the 52 externally-callable entrypoints.

    Swarms are keyed by swarm.swarm_id ("S01".."S12").
    Deep agents are keyed by agent.agent_id ("D01".."D40").
    Total: 52 keys, matching mining_agents.registry.registrable().
    """
    return {
        entry_id: build_one(entry_id)
        for entry_id in (*_SWARM_BY_ID, *_DEEP_BY_ID)
    }


if __name__ == "__main__":
    agents = build_all()
    print(f"built {len(agents)} entrypoints: {', '.join(sorted(agents))}")
