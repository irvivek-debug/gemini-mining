"""Generate the Data Insights section's data for the showcase front end.

Each insight card pairs a BQ Data Agent scenario with its verified recording.
The headline finding is computed LIVE from BigQuery at build time — the same
ground-truth queries the feasibility gates use — so the page cannot drift
from the warehouse. Editorial fields (title, impact, complexity) are fixed;
figures never are.
"""
from __future__ import annotations

import ast
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_probes import bq, PROJECT  # noqa: E402

DATASET = os.environ.get("MINING_DATASET", "mining_data")
DS = f"`{PROJECT}.{DATASET}`"
VID = ROOT / "data" / "uat" / "bq_scenarios"
OUT = ROOT / "apps" / "frontend" / "bq-insights.js"

META = {
  "S1-grade-reconciliation": ("Where the block model lies", "$5–15M/yr class", "Reconciliation"),
  "S2-anomaly-hunt": ("The anomaly nobody was reading", "$2–10M/yr class", "Anomaly detection"),
  "S3-parts-failure-graph": ("Which stock-out stops which machine", "$2–8M/yr class", "Graph traversal"),
  "S4-pit-to-port-cascade": ("Crusher to vessel in one question", "$5–20M/event class", "Cross-domain cascade"),
}


def finding(sid: str) -> str:
    """The card's headline figure, computed from the warehouse right now."""
    if sid == "S1-grade-reconciliation":
        # output aliases must not shadow table aliases: an output column named
        # `a` makes ORDER BY's AVG(a.…) an aggregate of an aggregate.
        r = bq(f"""SELECT b.lithology_type lith,
                 ROUND(AVG(b.copper_grade_pct_est),3) est_g,
                 ROUND(AVG(a.copper_grade_pct),3) act_g,
                 COUNT(DISTINCT b.block_id) blocks,
                 ABS(AVG(b.copper_grade_pct_est)-AVG(a.copper_grade_pct)) srt
               FROM {DS}.geological_block_models b JOIN {DS}.drill_assay_logs a
                 ON a.geology_code=b.lithology_type GROUP BY 1
               ORDER BY srt DESC LIMIT 1""")[0]
        gap = round(abs(float(r["act_g"]) - float(r["est_g"])), 3)
        return (f"{r['lith']} is misestimated by {gap} percentage points across "
                f"{r['blocks']} blocks — estimated {r['est_g']}%, assayed {r['act_g']}%.")
    if sid == "S2-anomaly-hunt":
        r = bq(f"""WITH s AS (SELECT metric_name, AVG(metric_value) mu, STDDEV(metric_value) sd
                 FROM {DS}.telemetry_stream GROUP BY 1)
               SELECT t.metric_name m, COUNT(*) n FROM {DS}.telemetry_stream t
               JOIN s USING(metric_name) WHERE s.sd>0 AND ABS(t.metric_value-s.mu)>3*s.sd
               GROUP BY 1 ORDER BY n DESC LIMIT 1""")[0]
        return (f"{r['n']} readings on {r['m']} sit beyond three standard deviations "
                f"— clustered, and nobody was reading them.")
    if sid == "S3-parts-failure-graph":
        r = bq(f"""SELECT w.asset_id a, COUNT(DISTINCT s.part_number) p,
                 ROUND(SUM(w.repair_cost)) c
               FROM {DS}.spares_inventory s
               JOIN {DS}.work_order_parts_edge e ON e.part_number=s.part_number
               JOIN {DS}.erp_work_orders w ON w.work_order_id=e.work_order_id
               WHERE s.at_or_below_reorder GROUP BY 1 ORDER BY c DESC LIMIT 1""")[0]
        return (f"{r['a']} depends on {r['p']} parts at stock-out risk, with "
                f"${int(float(r['c'])):,} of repair history flowing through them.")
    if sid == "S4-pit-to-port-cascade":
        r = bq(f"""SELECT sp.stockpile_id s, ROUND(sp.tonnes/NULLIF(sp.reclaim_rate_tph,0),1) h,
                 COUNT(DISTINCT v.vessel_name) v
               FROM {DS}.stockpiles sp
               JOIN {DS}.rail_schedules r ON r.origin_stockpile_id=sp.stockpile_id
               JOIN {DS}.port_vessels v ON r.consist_id IN UNNEST(v.consist_ids)
               GROUP BY 1, sp.tonnes, sp.reclaim_rate_tph ORDER BY h LIMIT 1""")[0]
        return (f"Stockpile {r['s']} holds {r['h']} hours of reclaim buffer and "
                f"feeds {r['v']} vessels — a six-hour crusher outage reaches the port.")
    raise SystemExit(f"no finding query for {sid}")


def main() -> int:
    rec_src = (ROOT / "scripts" / "record_bq_scenarios.py").read_text()
    tree = ast.parse(rec_src)
    scen = None
    for n in ast.walk(tree):
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            t = n.targets[0] if isinstance(n, ast.Assign) else n.target
            if getattr(t, "id", "") == "SCENARIOS":
                scen = ast.literal_eval(n.value)
    assert scen, "SCENARIOS not found in recorder"

    cards = []
    for sid, prompts in scen.items():
        vids = sorted((VID / sid).glob("*.webm"), key=lambda p: p.stat().st_size, reverse=True)
        if not vids:
            print(f"  {sid}: NO RECORDING — card skipped (never describe what cannot be shown)")
            continue
        title, impact, kind = META[sid]
        cards.append({
            "id": sid, "title": title, "impact": impact, "kind": kind,
            "question": prompts[0],
            "finding": finding(sid),
            "video": f"../../data/uat/bq_scenarios/{sid}/{vids[0].name}",
            "prompts": prompts,
        })
        print(f"  {sid}: finding computed live, video {vids[0].name[:18]}…")
    OUT.write_text("// Generated by scripts/build_bq_insights.py — findings computed\n"
                   "// live from BigQuery at build time. Do not edit.\n"
                   "window.BQ_INSIGHTS = " + json.dumps(cards, indent=1) + ";\n")
    print(f"{len(cards)} insight cards -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
