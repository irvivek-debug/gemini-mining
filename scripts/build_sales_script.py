"""Build the sales demo script from the UAT run.

Every prompt in here was actually executed against the live agent and its
answer recorded on video. Nothing is aspirational: an agent that did not pass
UAT is excluded, because a script that fails in front of a customer is worse
than a shorter script.

The two-turn shape is the demo: turn 1 is an operational scenario and produces
the headline, turn 2 asks what the agent may not do alone and produces the
governance moment. Presenters should run both -- the second is what separates
this from a chatbot.
"""
from __future__ import annotations

import json
import pathlib
import re
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "uat" / "ledger.jsonl"
OUT = ROOT / "docs" / "sales" / "agent-demo-script.md"


def trim(t: str, n: int = 460) -> str:
    t = re.sub(r"\s+", " ", (t or "").strip())
    return t[:n] + ("…" if len(t) > n else "")


def main() -> int:
    rows = [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]
    ok = [r for r in rows if r["passed"]]
    by = defaultdict(list)
    for r in ok:
        by[r["department"]].append(r)

    fr = sorted(r["first_response_s"] for r in ok if r.get("first_response_s"))
    med = fr[len(fr) // 2] if fr else None

    L = ["# Agent demo script\n",
         f"**{len(ok)} agents, every prompt verified live.** Each was run through "
         "Gemini Enterprise in a signed-in browser and its answer recorded. The prompts "
         "below are the ones that produced the answers shown.\n",
         f"\nExpect roughly **{med or 24}s** to first response. Ask the follow-up — "
         "it is where the governance story lands.\n",
         "\n## How to run a demo\n",
         "1. Open the agent's own link (each section has one).\n"
         "2. Paste **Turn 1** verbatim. Wait ~25s.\n"
         "3. While it answers, say the *Set up* line.\n"
         "4. Paste **Turn 2**. This is the moment that matters: the agent states what it "
         "cannot do on its own authority.\n"
         "5. If asked \"is this real?\" — the *Grounded in* tables are live BigQuery.\n"]

    L.append("\n## Pick by audience\n")
    L.append("| If the room cares about | Open with |")
    L.append("| --- | --- |")
    picks = [("Cash and contract leakage", "S10-R-CRITIC", "anti-bribery red flags with ISO 37001 citations"),
             ("Plant throughput", "S05-COORDINATOR", "a live crusher intervention directive"),
             ("Safety and licence to operate", "S08-R-CRITIC", "tailings liquefaction limits"),
             ("Supply chain and port", "S12-COORDINATOR", "demurrage exposure and laycan risk"),
             ("The strategic story", "AGT-19", "cut-off grade under a price shock")]
    have = {r["agent_id"] for r in ok}
    for topic, aid, why in picks:
        if aid in have:
            L.append(f"| {topic} | `{aid}` — {why} |")

    for dept in sorted(by):
        L.append(f"\n## {dept}\n")
        for r in sorted(by[dept], key=lambda x: x["agent_id"]):
            L.append(f"### {r['agent_id']} — {r['name']}\n")
            L.append(f"**For:** {r['persona']}  ·  **Value:** {r['value_class']}"
                     f"{'  ·  human release required' if r['hitl'] else '  ·  advisory'}")
            L.append(f"**Grounded in:** {', '.join(r['tables'])}")
            L.append(f"**Open:** {r['url']}")
            if r.get("video"):
                L.append(f"**Recording:** `{r['video']}`")
            L.append(f"\n*Set up:* “This agent owns {r['name'].lower()} for the "
                     f"{r['persona'].lower()}. Watch what it does with a real situation.”\n")
            L.append(f"**Turn 1 — paste this**\n\n> {r['prompt']}\n")
            L.append(f"**What they will see** _(≈{r.get('first_response_s') or 24}s)_\n\n"
                     f"> {trim(r['reply'])}\n")
            L.append(f"**Turn 2 — paste this**\n\n> {r['followup']}\n")
            L.append(f"**The governance moment**\n\n> {trim(r.get('followup_reply',''))}\n")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L))
    print(f"{len(ok)} agents -> {OUT.relative_to(ROOT)} ({OUT.stat().st_size//1024} KB)")
    print(f"  excluded (failed UAT): {[r['agent_id'] for r in rows if not r['passed']]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
