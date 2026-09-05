"""Generate apps/frontend/data-graph.js from the live BigQuery dataset.

The Screen 5 data-architecture graph shows real tables, real row counts and
real join keys. Nothing here is authored prose: run this script and the graph
redraws against whatever `mining_data` actually holds today.

Two pieces ARE editorial and are declared as such:

  LAYER   -- which architectural tier a table belongs to. BigQuery does not
             record this, so it is classified here by name and documented in
             LAYER_RULES below.
  DOMAIN  -- which part of the value chain a table serves. Same reasoning.

Snapshot copies (`*_original_YYYYMMDD`) and probe tables (`*_probe`) are
excluded from the graph and counted into meta.excluded, so a viewer reads
"39 tables in the architecture, 27 operational copies set aside" rather than
a silently shorter list.

Edges are derived, not asserted: two tables are joined when they share a
key-shaped column (`*_id`, `*_number`, `*_code`, `*_key`). A column appearing
in more than JOIN_UBIQUITY_LIMIT of the tables is too generic to describe a
relationship and is dropped, which is what stops `timestamp`-style columns
from wiring every node to every other node.

Usage:
    python scripts/build_data_graph.py [--out apps/frontend/data-graph.js]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"{name} is unset. Copy .env.example to .env and fill it in "
            "(see docs/RECREATE.md)."
        )
    return value


PROJECT = _required("GOOGLE_CLOUD_PROJECT")
DATASET = os.environ.get("MINING_DATASET", "mining_data")

SNAPSHOT_RE = re.compile(r"_original_\d{8}$")
PROBE_RE = re.compile(r"_probe$")
KEY_COLUMN_RE = re.compile(r"_(id|number|code|key)$")

# A column held by more than this share of tables describes a convention,
# not a relationship. Above the line, an edge would be noise.
JOIN_UBIQUITY_LIMIT = 0.30

LAYER_RULES = [
    # (layer key, label, predicate over the table name)
    # BQML models arrive through __TABLES__ alongside real tables. They carry no
    # columns and no rows, so without their own layer they would render as a
    # cluster of empty operational tables.
    ("model", "BQML models", lambda t: t.endswith("_model") or "_model_" in t),
    ("control", "Agent control plane", lambda t: t.startswith("agent_")),
    ("corpus", "Unstructured corpus", lambda t: t.startswith("doc_chunks") or t == "unstructured_docs_metadata"),
    ("semantic", "Semantic / property graph", lambda t: t.startswith("ontology_") or t.endswith("_node") or t.endswith("_edge")),
    ("serving", "Serving views", lambda t: t.startswith("v_")),
    ("simulation", "Scenario & simulation", lambda t: t.startswith("plan_") or t in {"simulation_runs", "capital_options"}),
]
DEFAULT_LAYER = ("operational", "Operational records")

DOMAIN_RULES = [
    ("geology", "Geology & resource", {"drill_holes", "drill_assay_logs", "geological_block_models"}),
    ("plant", "Processing plant", {"crusher_states", "metallurgical_recovery", "inventory_levels"}),
    ("fleet", "Mobile fleet & haulage", {"fleet_vehicles", "haulage_routes", "haul_cycle_log",
                                         "operator_vehicle_assignments", "telemetry_stream"}),
    ("hse", "Health, safety & people", {"safety_incidents", "incident_involvements", "biometric_fatigue_logs",
                                        "fatigue_logs_node", "operators_node", "radio_communications",
                                        "v_fatigue_scored"}),
    ("maintenance", "Asset & maintenance", {"assets", "asset_dependencies", "maintenance_logs",
                                            "erp_work_orders", "work_order_parts_edge",
                                            "warranty_claims", "warranty_entitlements"}),
    ("commercial", "Commercial & procurement", {"contracts", "contract_transactions", "invoices",
                                                "procurement_bids", "rfp_items", "bid_parts_edge",
                                                "rebate_claims", "contained_metal_price_deck"}),
    ("planning", "Planning & strategy", {"plan_versions", "plan_scenarios", "plan_assumptions",
                                         "capital_options", "simulation_runs"}),
]
DEFAULT_DOMAIN = ("platform", "Platform & ontology")


def bq_json(sql: str) -> list[dict]:
    """Run a query and return its rows, failing loudly rather than silently empty."""
    proc = subprocess.run(
        ["bq", f"--project_id={PROJECT}", "query", "--nouse_legacy_sql",
         "--format=json", "--max_rows=20000", sql],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"BigQuery query failed:\n{proc.stderr.strip()}")
    return json.loads(proc.stdout)


def classify_layer(table: str) -> tuple[str, str]:
    for key, label, pred in LAYER_RULES:
        if pred(table):
            return key, label
    return DEFAULT_LAYER


def classify_domain(table: str) -> tuple[str, str]:
    for key, label, members in DOMAIN_RULES:
        if table in members:
            return key, label
    return DEFAULT_DOMAIN


def agent_consumers() -> dict[str, list[str]]:
    """Map each declared grounding table to the agents that read it.

    Reads the vendored registry catalogue. An import failure raises rather
    than returning an empty map: a silent {} renders as "no agent reads any
    table", which is both wrong and hard to notice on a finished screen.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vendor" / "agent_registry"))
    import catalog_definitions as C  # noqa: PLC0415

    consumers: dict[str, list[str]] = {}
    for a in C.CATALOG:
        for table in a.source_tables or []:
            consumers.setdefault(table, []).append(a.agent_id)
    if not consumers:
        raise SystemExit("catalogue declared no source tables at all -- refusing to "
                         "emit a graph that claims no agent reads any data.")
    return {k: sorted(v) for k, v in consumers.items()}


def build() -> dict:
    rows = bq_json(
        f"SELECT table_id AS table_name, row_count, size_bytes "
        f"FROM `{PROJECT}.{DATASET}.__TABLES__` ORDER BY table_id"
    )
    cols = bq_json(
        f"SELECT table_name, column_name, data_type "
        f"FROM `{PROJECT}.{DATASET}.INFORMATION_SCHEMA.COLUMNS` "
        f"ORDER BY table_name, ordinal_position"
    )

    row_count = {r["table_name"]: int(r["row_count"]) for r in rows}
    size_bytes = {r["table_name"]: int(r["size_bytes"]) for r in rows}

    columns: dict[str, list[dict]] = {}
    for c in cols:
        columns.setdefault(c["table_name"], []).append(
            {"name": c["column_name"], "type": c["data_type"]}
        )

    every_table = sorted(set(row_count) | set(columns))
    excluded = [t for t in every_table if SNAPSHOT_RE.search(t) or PROBE_RE.search(t)]
    kept = [t for t in every_table if t not in set(excluded)]

    consumers = agent_consumers()

    nodes = []
    for t in kept:
        layer_key, layer_label = classify_layer(t)
        domain_key, domain_label = classify_domain(t)
        cs = columns.get(t, [])
        n = row_count.get(t, 0)
        nodes.append({
            "id": t,
            "layer": layer_key,
            "layerLabel": layer_label,
            "domain": domain_key,
            "domainLabel": domain_label,
            "rows": n,
            "bytes": size_bytes.get(t, 0),
            "columnCount": len(cs),
            "columns": cs,
            # Radius is precomputed so the renderer never has to invent scale.
            "weight": round(math.log10(n + 10), 3),
            "readBy": consumers.get(t, []),
        })

    # Edges from shared key-shaped columns.
    key_owners: dict[str, list[str]] = {}
    for t in kept:
        for c in columns.get(t, []):
            if KEY_COLUMN_RE.search(c["name"]):
                key_owners.setdefault(c["name"], []).append(t)

    limit = max(2, int(len(kept) * JOIN_UBIQUITY_LIMIT))
    pair_keys: dict[tuple[str, str], list[str]] = {}
    dropped_keys = []
    for key, owners in key_owners.items():
        if len(owners) < 2:
            continue
        if len(owners) > limit:
            dropped_keys.append({"column": key, "tables": len(owners)})
            continue
        for i in range(len(owners)):
            for j in range(i + 1, len(owners)):
                pair = tuple(sorted((owners[i], owners[j])))
                pair_keys.setdefault(pair, []).append(key)

    edges = [
        {"source": a, "target": b, "keys": sorted(ks), "weight": len(ks)}
        for (a, b), ks in sorted(pair_keys.items())
    ]

    layers = []
    for key, label, _ in LAYER_RULES:
        layers.append({"key": key, "label": label})
    layers.append({"key": DEFAULT_LAYER[0], "label": DEFAULT_LAYER[1]})
    present = {n["layer"] for n in nodes}
    layers = [l for l in layers if l["key"] in present]

    domains = []
    for key, label, _ in DOMAIN_RULES:
        domains.append({"key": key, "label": label})
    domains.append({"key": DEFAULT_DOMAIN[0], "label": DEFAULT_DOMAIN[1]})
    present_d = {n["domain"] for n in nodes}
    domains = [d for d in domains if d["key"] in present_d]

    return {
        "nodes": nodes,
        "edges": edges,
        "layers": layers,
        "domains": domains,
        "meta": {
            "project": PROJECT,
            "dataset": DATASET,
            "tableCount": len(nodes),
            "edgeCount": len(edges),
            "columnCount": sum(n["columnCount"] for n in nodes),
            "rowCount": sum(n["rows"] for n in nodes),
            "excludedCount": len(excluded),
            "excluded": excluded,
            "genericKeysDropped": sorted(dropped_keys, key=lambda d: -d["tables"]),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="apps/frontend/data-graph.js")
    args = ap.parse_args()

    graph = build()
    out = Path(args.out)
    out.write_text(
        "/* GENERATED by scripts/build_data_graph.py -- do not edit by hand.\n"
        f" * Source: live `{PROJECT}.{DATASET}` -- table storage and INFORMATION_SCHEMA.COLUMNS.\n"
        " * Layer and domain are classifications declared in the generator; every\n"
        " * other field is read straight from BigQuery. */\n"
        "window.dataGraph = " + json.dumps(graph, indent=1) + ";\n",
        encoding="utf-8",
    )
    m = graph["meta"]
    print(f"{m['tableCount']} tables, {m['edgeCount']} join edges, "
          f"{m['columnCount']} columns, {m['rowCount']:,} rows "
          f"({m['excludedCount']} snapshot/probe copies excluded) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
