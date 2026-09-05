"""Render the UAT ledger into a reviewable document."""
from __future__ import annotations

import json
import pathlib
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "uat" / "ledger.jsonl"
OUT = ROOT / "docs" / "uat" / "agent-uat.md"

CHECKS = {
    "answered": "A reply rendered in the product, and it is not an error surface.",
    "not_the_prompt": "The reply is the agent's own text, not the question echoed back.",
    "in_character": "It reaches for its own domain — terms from its governing equation, department or declared tables.",
    "no_fabrication": "It does not claim the data was compromised, injected or tampered with.",
    "grounded_or_says_not": "It either names evidence it would use, or states plainly what it cannot evidence.",
}


def main() -> int:
    rows = [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]
    rows.sort(key=lambda r: r["agent_id"])
    passed = [r for r in rows if r["passed"]]
    lat = sorted(r["latency_s"] for r in rows)

    by_dept = defaultdict(list)
    for r in rows:
        by_dept[r["department"]].append(r)

    L = []
    L.append("# Agent UAT — Gemini Enterprise\n")
    L.append(f"**{len(passed)} of {len(rows)} agents passed.** Each was driven through the "
             "Gemini Enterprise UI in a real signed-in browser session — navigated to its own "
             "agent page, asked a question in the composer, and its rendered reply captured. "
             "Every run has a video.\n")
    L.append(f"Latency: median **{lat[len(lat)//2]}s**, range {lat[0]}–{lat[-1]}s.\n")

    L.append("## What a pass means\n")
    L.append("These checks were written to be failable, and were verified against adversarial "
             "input: an empty reply, an error surface, the prompt echoed back, generic "
             "assistant waffle, a fabricated security incident, and a confident number with no "
             "grounding. Each is caught by the check named beside it.\n")
    L.append("| Check | What it asserts |")
    L.append("| --- | --- |")
    for k, v in CHECKS.items():
        L.append(f"| `{k}` | {v} |")
    L.append("")

    L.append("## Coverage by department\n")
    L.append("| Department | Agents | Passed |")
    L.append("| --- | ---: | ---: |")
    for d in sorted(by_dept):
        g = by_dept[d]
        L.append(f"| {d} | {len(g)} | {sum(r['passed'] for r in g)} |")
    L.append("")

    L.append("## Results\n")
    for d in sorted(by_dept):
        L.append(f"### {d}\n")
        for r in sorted(by_dept[d], key=lambda x: x["agent_id"]):
            mark = "PASS" if r["passed"] else "FAIL"
            L.append(f"#### {r['agent_id']} — {r['name']}  ·  {mark}\n")
            L.append(f"- **Persona:** {r['persona']}")
            L.append(f"- **Value class:** {r['value_class']}"
                     f"{' · human release required' if r['hitl'] else ' · advisory'}")
            L.append(f"- **Governing method:** `{r['equation']}`")
            L.append(f"- **Declared tables:** {', '.join(r['tables']) or '—'}")
            if r.get("tables_cited"):
                L.append(f"- **Tables it named in its answer:** {', '.join(r['tables_cited'])}")
            L.append(f"- **Latency:** {r['latency_s']}s")
            L.append(f"- **Video:** `{r['video']}`")
            if not r["passed"]:
                bad = [k for k, v in r["checks"].items() if not v]
                L.append(f"- **Failed checks:** {', '.join(bad)}")
            L.append(f"\n**Asked:**\n\n> {r['prompt']}\n")
            reply = r["reply"].strip().replace("\n", "\n> ")
            L.append(f"**Answered:**\n\n> {reply}\n")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L))
    print(f"{len(rows)} agents, {len(passed)} passed -> {OUT.relative_to(ROOT)}")
    print(f"  {OUT.stat().st_size//1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
