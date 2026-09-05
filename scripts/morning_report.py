"""Summarise the overnight grounding run from recorded evidence.

Reads data/grounding/results.jsonl (last record wins per agent) and reports
what is grounded, what failed, and -- for each failure -- the evidence needed
to form a hypothesis without re-running anything.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe_set  # noqa: E402

RESULTS = Path(__file__).resolve().parents[1] / "data" / "grounding" / "results.jsonl"

# The signature of a transient stall, measured on the two known cases:
# few tool calls and high latency, versus 5-8 calls in ~25s when healthy.
STALL_CALLS, STALL_SECONDS = 3, 55


def latest() -> dict[str, dict]:
    by: dict[str, dict] = {}
    for line in RESULTS.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            by[r["agent_id"]] = r
    return by


def hypothesis(r: dict) -> str:
    if r.get("transport_error"):
        return f"transport: {r['transport_error'][:90]}"
    if r.get("tool_errors"):
        return f"tool refused: {r['tool_errors'][0][:90]}"
    if r.get("failure_kind") == "transient":
        return "transient — passed on retry; nothing to fix"
    first = r.get("first_attempt") or {}
    calls = r.get("tool_calls", 0)
    if calls == 0:
        return "no tool calls — agent answered from model knowledge; check tools= is attached"
    if calls <= STALL_CALLS and r.get("latency_s", 0) >= STALL_SECONDS:
        return (f"stall signature ({calls} calls / {r.get('latency_s')}s vs 5-8 / ~25s healthy)"
                " — retry also stalled; suspect engine cold-start, not the agent")
    if not r.get("reply_chars"):
        return "empty reply despite tool calls — check the stream parser before the agent"
    checks = r.get("checks", {})
    if checks.get("matches_live_source") and not checks.get("cites_its_source"):
        return "right number, no table named — citation gate, not a grounding failure"
    if not checks.get("matches_live_source"):
        return (f"answered {r.get('matched_number')} vs live {r.get('truth')}"
                " — read the recorded reply; wrong table or wrong filter")
    return "see recorded reply"


def main() -> int:
    if not RESULTS.exists():
        print("no results yet"); return 1
    by = latest()
    groups: dict[str, list[dict]] = {}
    for aid, r in by.items():
        groups.setdefault(probe_set.group_of(aid) or "?", []).append(r)

    total = sum(len(v) for v in groups.values())
    passed = sum(1 for r in by.values() if r.get("passed"))
    print(f"GROUNDING — {passed}/{total} agents grounded against live BigQuery\n")

    for g in sorted(groups):
        rs = groups[g]
        ok = sum(1 for r in rs if r.get("passed"))
        flag = "" if ok == len(rs) else "   <-"
        print(f"  {g:5} {ok}/{len(rs)}{flag}")

    fails = [r for r in by.values() if not r.get("passed")]
    kinds = Counter(r.get("failure_kind", "unclassified") for r in fails)
    print(f"\nFAILURES: {len(fails)}" + (f"  ({dict(kinds)})" if fails else ""))
    for r in sorted(fails, key=lambda r: r["agent_id"]):
        print(f"\n  {r['agent_id']}  tools={r.get('tool_calls')} "
              f"{r.get('latency_s')}s  truth={r.get('truth')} got={r.get('matched_number')}")
        print(f"    failed: {[k for k, v in r.get('checks', {}).items() if not v]}")
        print(f"    hypothesis: {hypothesis(r)}")
        if r.get("reply"):
            print(f"    reply: {r['reply'][:220].strip()}")

    retried = [r for r in by.values() if r.get("failure_kind")]
    if retried:
        t = sum(1 for r in retried if r["failure_kind"] == "transient")
        print(f"\nRETRIES: {len(retried)} agents failed once; {t} passed on retry.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
