"""Build the UAT roster from what is ACTUALLY registered in Gemini Enterprise.

WHY THIS IS ITS OWN STEP
The first full UAT ran against a roster written before D31 was deregistered and
before S12 was registered. The result looked complete -- 96 agents, 90 passing
-- while testing one agent that no longer existed and skipping five that did.
A roster derived from anything other than the live registry will drift the
moment the estate changes, and the drift is invisible because the run still
reports a tidy number.

So the roster is derived here, from the registry, immediately before a run.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "vendor" / "agent_registry"))
from register_agents import GE_AGENTS, paged  # noqa: E402
import catalog_definitions as C  # noqa: E402

CID = "YOUR_AGENTSPACE_CID"
OUT = ROOT / "data" / "uat" / "agents.json"
ID = re.compile(r"\(([A-Z0-9][A-Z0-9\-]*)\)\s*$")


def main() -> int:
    cat = {a.agent_id: a for a in C.CATALOG}
    rows = []
    for a in paged(GE_AGENTS, "agents"):
        m = ID.search(a.get("displayName", ""))
        if not m or m.group(1) not in cat:
            continue
        aid = m.group(1)
        c = cat[aid]
        gid = a["name"].split("/")[-1]
        rows.append({
            "agent_id": aid, "name": c.name, "display_name": a["displayName"], "ge_id": gid,
            "department": c.department.value, "persona": c.persona,
            "pattern": c.pattern.value, "value_class": c.value_class.value,
            "hitl": bool(c.hitl_required), "equation": c.governing_equation,
            "tables": list(c.source_tables),
            "url": f"https://vertexaisearch.cloud.google.com/home/cid/{CID}"
                   f"/r/agent/{gid}/session/-?hl=en_US",
        })
    rows.sort(key=lambda r: r["agent_id"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=1))

    unregistered = sorted(set(cat) - {r["agent_id"] for r in rows})
    print(f"roster: {len(rows)} registered agents -> {OUT.relative_to(ROOT)}")
    print(f"  in the catalogue but not registered: {unregistered or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
