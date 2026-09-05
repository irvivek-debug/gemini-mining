"""Re-score a recorded ledger without re-running the browser.

The replies and videos are the evidence and do not change; the assertions are
judgement and did. Re-driving 96 agents to correct a regex would also change
the evidence, which is the wrong way to fix a scoring bug -- so this re-reads
data/uat/ledger.jsonl, applies the current checks, and rewrites the verdicts in
place, leaving every captured reply and .webm untouched.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from uat_run import LEDGER, assess  # noqa: E402


def main() -> int:
    rows = [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]
    before = sum(r.get("passed", False) for r in rows)
    out = []
    for r in rows:
        a = {"tables": r.get("tables", []), "equation": r.get("equation", ""),
             "name": r.get("name", ""), "department": r.get("department", ""),
             "persona": r.get("persona", "")}
        r.update(assess(a, r.get("reply", ""), r.get("prompt", "")))
        out.append(r)
    LEDGER.write_text("\n".join(json.dumps(r) for r in out) + "\n")
    after = sum(r["passed"] for r in out)
    print(f"rescored {len(out)} | passed {before} -> {after}")
    from collections import Counter
    fails = Counter(k for r in out if not r["passed"] for k, v in r["checks"].items() if not v)
    print("failing checks:", dict(fails) or "none")
    for r in out:
        if not r["passed"]:
            bad = [k for k, v in r["checks"].items() if not v]
            print(f"  {r['agent_id']:<18} {','.join(bad)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
