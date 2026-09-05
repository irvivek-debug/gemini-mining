"""Generate one unfakeable grounding probe per agent, from the catalogue.

Hand-writing 100 probes invites two mistakes I already made once: typing an
expected value that is wrong (17 critical assets; it is 15), and asking
something a model can guess. Both are avoided by deriving the probe from the
agent's own declared table and letting SQL supply the answer at test time.

Each probe asks for a COUNT and a numeric AVG over a table the agent declares.
Neither is guessable -- a model has no prior on how many rows a private table
holds -- and both change if the data changes, so a memorised reply drifts out
of tolerance rather than passing forever.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor" / "agent_registry"))
import catalog_definitions as C  # noqa: E402


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"{name} is unset. Copy .env.example to .env and fill it in "
            "(see docs/RECREATE.md)."
        )
    return value


PROJECT = _required("GOOGLE_CLOUD_PROJECT")
OUT = ROOT / "data" / "grounding" / "probes.json"


def bq(sql: str) -> list[dict]:
    p = subprocess.run(["bq", f"--project_id={PROJECT}", "query", "--nouse_legacy_sql",
                        "--format=json", "--max_rows=2000", sql], capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(p.stderr.strip()[:300])
    return json.loads(p.stdout or "[]")


def numeric_columns() -> dict[str, list[str]]:
    rows = bq(f"SELECT table_name, column_name FROM "
              f"`{PROJECT}.mining_data.INFORMATION_SCHEMA.COLUMNS` "
              f"WHERE data_type IN ('INT64','FLOAT64','NUMERIC') "
              f"ORDER BY table_name, ordinal_position")
    out: dict[str, list[str]] = {}
    for r in rows:
        out.setdefault(r["table_name"], []).append(r["column_name"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="", help="e.g. S01 — restrict to one swarm")
    args = ap.parse_args()

    # Deregistered by decision, not lost: D31 was retired as redundant, so it
    # has no engine and must not reappear in the probe set. Deleting it by hand
    # after each build only lasted until the next one.
    DEREGISTERED = {"D31"}

    nums = numeric_columns()
    # Every readable relation, views included -- a view is as real to an agent
    # as a table, and `safety_telemetry` is one.
    all_tables = {r["table_name"] for r in bq(
        f"SELECT table_name FROM `{PROJECT}.mining_data.INFORMATION_SCHEMA.TABLES`")}
    probes = []
    skipped = []
    for a in C.CATALOG:
        if a.agent_id in DEREGISTERED:
            continue
        if args.group and not a.agent_id.startswith(args.group):
            continue
        table = next((t for t in a.source_tables if t in nums and nums[t]), None)
        if not table:
            # No numeric column means no AVG to ask for -- but a row count is
            # still a fact only the warehouse knows. Skipping these left five
            # registered agents (D22-D25 on `assets`, all-STRING; D38 on the
            # `safety_telemetry` view) with no probe at all, so nothing could
            # ever verify they read data. An agent that cannot be checked is
            # not the same as an agent that passed.
            countable = next((t for t in a.source_tables if t in all_tables), None)
            if not countable:
                skipped.append(a.agent_id)
                continue
            probes.append({
                "agent_id": a.agent_id,
                "question": (
                    f"Query mining_data.{countable} directly and report one exact "
                    f"figure: the total row count. State the fully-qualified table "
                    f"you read. Do not estimate — if you cannot run the query, "
                    f"say so."),
                "truth_sql": (f"SELECT COUNT(*) AS n FROM "
                              f"`{PROJECT}.mining_data.{countable}`"),
                "truth_key": "n",
                "tolerance_pct": 0.5,
                "must_name": [countable],
                "derived": [],
            })
            continue
        col = nums[table][0]
        probes.append({
            "agent_id": a.agent_id,
            "question": (
                f"Query mining_data.{table} directly and report two exact figures: "
                f"the total row count, and the AVG of {col} to four decimal places. "
                f"State the fully-qualified table you read. Do not estimate — if you "
                f"cannot run the query, say so."),
            "truth_sql": (f"SELECT COUNT(*) AS n, ROUND(AVG({col}),4) AS avg_val "
                          f"FROM `{PROJECT}.mining_data.{table}`"),
            "truth_key": "n",
            "tolerance_pct": 0.5,
            "must_name": [table],
            "derived": [["average of " + col, "avg_val", 2.0]],
        })
    # MERGE, never replace. This file was rewritten wholesale for each group,
    # so after --group S08 ran, S01's probes no longer existed. Anything looking
    # for an earlier agent found nothing and skipped it in silence -- a
    # determinism trial exited with zero output and no error because all three
    # of its agents had been erased from the test set.
    #
    # The probe set is the record of what we can verify. It should only ever
    # grow.
    OUT.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if OUT.exists():
        existing = {d["agent_id"]: d for d in json.loads(OUT.read_text())}
    for pr in probes:
        existing[pr["agent_id"]] = pr
    merged = [existing[k] for k in sorted(existing)]
    OUT.write_text(json.dumps(merged, indent=1))
    print(f"{len(probes)} probes generated, {len(merged)} total on file "
          f"-> {OUT.relative_to(ROOT)}")
    if skipped:
        print(f"  no numeric column to probe ({len(skipped)}): {skipped[:6]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
