"""Build the sales companion document for the agent recordings.

One entry per agent: a context paragraph (~100 words) written so a reader
who has never seen the system understands the input (the operational
scenario), the output (what the agent concluded, with its real numbers),
and the logic (the governing method and the tables it read) — then the
video path and the live agent link.

Everything is drawn from recorded evidence: the scenario prompts, the
ledger's captured replies, and the catalogue. Nothing is invented.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "vendor" / "agent_registry"))
import catalog_definitions as C  # noqa: E402

LEDGER = ROOT / "data" / "uat" / "ledger.jsonl"
AGENTS = ROOT / "data" / "uat" / "agents.json"
SCEN = ROOT / "data" / "uat" / "scenario_prompts.json"
VIDEOS = ROOT / "data" / "uat" / "videos"
OUT = ROOT / "reports" / "sales_recordings_companion.md"
JS_OUT = ROOT / "apps" / "frontend" / "sales-assets.js"


def first_numbers(text: str, n: int = 3) -> list[str]:
    """The most salient figures the agent actually reported.

    Only numbers that read as findings: carrying a unit/% or a real decimal.
    Bare integers are skipped -- the first draft surfaced '475913' (a chunk
    of the project id) and '1.' (a list marker) as "key figures".
    """
    hits = re.findall(
        r"\b\d[\d,]*\.\d+\s*(?:%|mm|kPa|t\b|tph|days?|hours?)?"    # decimals
        r"|\b\d[\d,]*\s*(?:%|mm|kPa|tph|days?|hours?)\b",            # int + unit
        text)
    seen, out = set(), []
    for h in hits:
        h = " ".join(h.split())
        if h in seen or "475913" in h:
            continue
        seen.add(h); out.append(h)
        if len(out) == n:
            break
    return out


def first_sentence(text: str, limit: int = 220) -> str:
    t = re.sub(r"[#*|`]+", " ", text)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:limit].rsplit(" ", 1)[0] + ("…" if len(t) > limit else "")


# Plain-English names for the data each agent reads. Mechanical lookup, not
# generation: unknown tables fall back to humanising the identifier
# (drill_holes -> "drill hole records"), never to invented descriptions.
TABLE_PLAIN = {
    "drill_holes": "drill hole records",
    "assay_logs": "assay results",
    "geological_block_models": "the geological block model",
    "financial_ledger": "the financial ledger",
    "mine_production_schedule": "the mine production schedule",
    "fleet_telemetry": "live fleet telemetry",
    "fleet_vehicles": "the fleet register",
    "haul_cycle_log": "haul cycle logs",
    "haulage_routes": "haulage routes",
    "dispatch_routes": "dispatch routes",
    "crusher_telemetry": "crusher telemetry",
    "plant_telemetry": "plant telemetry",
    "flotation_assays": "flotation assay results",
    "metallurgical_recovery": "metallurgical recovery records",
    "reagent_inventory": "reagent stock levels",
    "water_balance_logs": "water balance logs",
    "tsf_piezometers": "tailings dam sensor readings",
    "geotech_sensors": "geotechnical sensor readings",
    "vibration_monitors": "vibration monitor readings",
    "maintenance_logs": "maintenance history",
    "erp_work_orders": "open work orders",
    "spares_inventory": "spare parts stock",
    "inventory_levels": "inventory levels",
    "purchase_orders": "purchase-order history",
    "procurement_bids": "supplier bids",
    "vendor_contracts": "supplier contracts",
    "contracts": "contracts",
    "contract_transactions": "contract transactions",
    "warranty_claims": "warranty claims",
    "rebate_claims": "rebate claims",
    "invoices": "invoices",
    "rail_schedules": "rail schedules",
    "port_vessels": "vessel movements at the port",
    "stockpiles": "stockpile records",
    "blast_designs": "blast designs",
    "explosives_inventory": "explosives inventory",
    "pit_designs": "pit designs",
    "survey_scans": "survey scans",
    "safety_telemetry": "safety telemetry",
    "assets": "the asset register",
    "lube_samples": "oil sample analyses",
    "qaqc_standards": "QA/QC standards",
    "contained_metal_price_deck": "the contained-metal price deck",
    "plan_assumptions": "planning assumptions",
    "plan_scenarios": "planning scenarios",
}

MEMO_NOISE = re.compile(
    r"^(memorandum|to:|from:|subject:|agent:|governing method:|date:|re:)", re.I)


def plain_tables(tables: list[str]) -> str:
    names = []
    for t in tables[:3]:
        short = t.split(".")[-1]
        names.append(TABLE_PLAIN.get(short, short.replace("_", " ") + " records"))
    if not names:
        return "the operation's own records"
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def method_phrase(equation: str) -> str:
    """The method only if it reads as a name; formulas stay off the sales page."""
    eq = (equation or "").strip()
    # Anything that smells like maths stays off the sales page: symbols,
    # operator words, or a colon introducing a formula.
    mathy = any(ch in eq for ch in "=^{}\\+*/:()[]") or \
            any(w in eq.lower() for w in ("min ", "max ", "sum", "sigma", "delta"))
    if not eq or mathy or len(eq) > 60:
        return "its governing calculation"
    return f"its {eq} method"


def clean_opening(text: str, limit: int = 200) -> str:
    """First substantive line of the real reply, memo boilerplate skipped.

    Selection and trimming only -- every word is the agent's own.
    """
    for raw in re.sub(r"[#*|`]+", " ", text).splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if len(line) < 25 or MEMO_NOISE.match(line):
            continue
        return line[:limit].rsplit(" ", 1)[0] + ("…" if len(line) > limit else "")
    return first_sentence(text, limit)


def paragraph(agent, scen_q: str, reply: str, tables: list[str]) -> str:
    """~100 words a salesperson can read aloud.

    Nothing is generated: the question is verbatim, the quoted line and the
    figures are lifted from the recorded reply, the data names come from a
    fixed lookup, and the connecting sentences are a fixed template.
    """
    nums = first_numbers(reply)
    figures = (f" It reports real figures — {', '.join(nums)} — pulled from "
               f"the data during the recording." if nums else "")
    return (
        f"**Situation.** {scen_q.strip()} "
        f"**Agent Action.** It looks up {plain_tables(tables)} — the "
        f"operation's live data, not a briefing pack — and answers in its own "
        f"words: “{clean_opening(reply)}”{figures} "
        f"**Logic.** Before answering it runs "
        f"{method_phrase(agent.governing_equation if agent else '')}, checks "
        f"any numbers given in the question against what the records actually "
        f"say, points out any difference, and names the records behind every "
        f"figure. If it cannot back something with data, it says so instead "
        f"of guessing."
    )


def main() -> int:
    by_cat = {a.agent_id: a for a in C.CATALOG}
    agents = json.loads(AGENTS.read_text())
    scen = json.loads(SCEN.read_text())
    ledger = {}
    for line in LEDGER.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            ledger[r["agent_id"]] = r

    lines = [
        "# Agent Recordings — Sales Companion",
        "",
        "One entry per agent. Each recording opens on the operational question,",
        "shows the agent reading BigQuery live (the tool trace), then scrolls",
        "the answer at reading pace.",
        "",
        "**Demo-day notes.**",
        "",
        "- *Latency truth.* Agents answer in seconds via the API but typically",
        "  2–4 minutes through the chat UI, and under sustained load the wait",
        "  lands before the agent starts work — a longer timeout does not help.",
        "  Pre-warm the agent you plan to show, or narrate the tool trace: it is",
        "  the proof of grounding, and it is the part worth talking over.",
        "- *Fallback order.* Play the recording first — it is verified and it",
        "  cannot stall. Go live only on request, and only for an agent you",
        "  pre-warmed. If the UI is queuing, drop to the API, which answers in",
        "  seconds and shows the same grounding without the chat surface.",
        "",
    ]
    skipped = []
    for a in sorted(agents, key=lambda x: x["agent_id"]):
        aid = a["agent_id"]
        r = ledger.get(aid)
        if not r or not r.get("passed") or not r.get("reply"):
            skipped.append(aid)
            continue
        pair = scen.get(aid) or ["", ""]
        q = pair[0] if isinstance(pair, list) else pair
        cat = by_cat.get(aid)
        # The ledger names the capture whose reply this entry describes.
        # Globbing the directory instead picks whatever sorts first, and 37
        # stale takes from earlier runs still sit beside the live ones -- that
        # paired 14 entries with a video of a different (sometimes failed) run.
        vid = ROOT / r["video"] if r.get("video") else None
        vids = [vid] if vid and vid.exists() else []
        lines += [
            f"## {a['display_name']}",
            "",
            f"*{a.get('department','')} — {a.get('persona','')}*",
            "",
            paragraph(cat, q, r["reply"], a.get("tables", [])),
            "",
            f"- **Recording:** `{vids[0].relative_to(ROOT)}`" if vids else "- **Recording:** (pending)",
            f"- **Live agent:** {a['url']}",
            "",
        ]
    if skipped:
        lines += ["---", "", f"**Not yet included ({len(skipped)}):** " + ", ".join(skipped),
                  "  (no passing recording on the current ledger — the companion only",
                  "  describes what a recording actually shows)", ""]
    OUT.write_text("\n".join(lines))

    # The same evidence, as data for the front end: the Agent Ecosystem
    # deep-dive shows the recording and the Situation / Agent Action / Logic
    # script in place of the old simulated terminal. Paths are relative to
    # apps/frontend/ so the page works from the filesystem.
    assets = {}
    for a in agents:
        aid = a["agent_id"]
        r = ledger.get(aid)
        if not r or not r.get("passed") or not r.get("reply"):
            continue
        pair = scen.get(aid) or ["", ""]
        q = pair[0] if isinstance(pair, list) else pair
        cat = by_cat.get(aid)
        # The ledger names the capture whose reply this entry describes.
        # Globbing the directory instead picks whatever sorts first, and 37
        # stale takes from earlier runs still sit beside the live ones -- that
        # paired 14 entries with a video of a different (sometimes failed) run.
        vid = ROOT / r["video"] if r.get("video") else None
        vids = [vid] if vid and vid.exists() else []
        nums = first_numbers(r["reply"])
        assets[aid] = {
            "video": f"../../data/uat/videos/{aid}/{vids[0].name}" if vids else "",
            "situation": q.strip(),
            "action": (f"Looks up {plain_tables(a.get('tables', []))} — the "
                       f"operation's live data — and answers in its own words: "
                       f"“{clean_opening(r['reply'])}”"
                       + (f" Real figures from the recording: {', '.join(nums)}."
                          if nums else "")),
            "logic": (f"Before answering it runs "
                      f"{method_phrase(cat.governing_equation if cat else '')}, "
                      f"checks any numbers given in the question against what "
                      f"the records actually say, points out any difference, "
                      f"and names the records behind every figure. If it "
                      f"cannot back something with data, it says so."),
        }
    JS_OUT.write_text("// Generated by scripts/build_sales_doc.py — do not edit.\n"
                      "window.SALES_ASSETS = " + json.dumps(assets, indent=1) + ";\n")
    print(f"{len(assets)} assets -> {JS_OUT.relative_to(ROOT)}")
    print(f"{len(agents) - len(skipped)} entries -> {OUT.relative_to(ROOT)}"
          + (f"  (skipped {len(skipped)})" if skipped else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
