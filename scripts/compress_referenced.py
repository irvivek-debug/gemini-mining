"""Compress exactly the videos the ledger references, nothing else.

compress_dead_air's --batch mode picks the largest .webm in each agent
directory. That is wrong here: 37 stale takes from earlier runs still sit
beside the referenced captures, and the largest file is often one of them.
The ledger names the file that actually ships, so drive from the ledger.

Output mirrors the input path under a new root, keeping the filename, so
the GCS object paths the front end already references stay valid.

Usage: python scripts/compress_referenced.py <out-root>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compress_dead_air import compress  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    out_root = Path(sys.argv[1])
    ids = [a["agent_id"] for a in json.loads(
        (ROOT / "data/uat/agents.json").read_text())]
    last: dict[str, dict] = {}
    for line in (ROOT / "data/uat/ledger.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            last[r["agent_id"]] = r

    tot_in = tot_out = 0.0
    for n, aid in enumerate(ids, 1):
        src = ROOT / last[aid]["video"]
        dst = out_root / aid / src.name
        t, c = compress(src, dst)
        tot_in += t
        tot_out += c
        print(f"[{n}/{len(ids)}] {aid}: {t:.0f}s -> {c:.0f}s", flush=True)
    print(f"TOTAL {tot_in/60:.0f}min -> {tot_out/60:.0f}min "
          f"({100*(1-tot_out/tot_in):.0f}% cut)")
    print("COMPRESS_DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
