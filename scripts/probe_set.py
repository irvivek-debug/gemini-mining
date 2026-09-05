"""Selection over the accumulated probe set.

data/grounding/probes.json holds every agent we can verify, not one group.
Callers that want a single swarm must select it. Group ids are not uniform --
swarms are `S08-1-WATER` (hyphen after the group), deep solvers are `D26`
(no separator at all), so a bare startswith() either misses D entirely or
lets `S01` swallow nothing while `D` swallows `D01..D35` correctly by luck.
This module is the one place that knows the shape.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBES = ROOT / "data" / "grounding" / "probes.json"

# A group is a swarm (S01..S12), the standalone AGT, or the deep-solver pool D.
GROUP_RE = re.compile(r"^(S\d{2}|AGT|D)")


def group_of(agent_id: str) -> str | None:
    m = GROUP_RE.match(agent_id)
    return m.group(1) if m else None


def load(path: Path | None = None) -> list[dict]:
    p = path or PROBES
    return json.loads(p.read_text()) if p.exists() else []


def select_group(group: str, path: Path | None = None) -> list[str]:
    """Agent ids belonging to `group`, in file order."""
    return [d["agent_id"] for d in load(path) if group_of(d["agent_id"]) == group]


def chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


if __name__ == "__main__":
    import sys
    ids = select_group(sys.argv[1])
    size = int(sys.argv[2]) if len(sys.argv) > 2 else len(ids) or 1
    for batch in chunks(ids, size):
        print(",".join(batch))
