"""Export the JSON the two demo applications read.

Both applications must show what is actually deployed, so the catalog export
derives from `mining_agents.catalog.definitions` -- the same module that builds
the agents -- rather than from a hand-maintained copy that would drift the first
time an agent changed.

The graph export has two sources. BigQuery is authoritative when credentials
are available. Without them it falls back to `data/profile/` and the generated
parquet, which hold the same entities. Both paths write the same shape, and the
file records which one produced it, because a graph drawn from a local cache is
a weaker claim than one drawn from the warehouse and the screen says so.

Run: python -m scripts.build_app_data [--out apps/shared/data]
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import pathlib
import re

import yaml

from mining_agents.catalog.definitions import ALL_AGENTS, LEAKS
from mining_agents.method.pack import load_pack
from mining_agents.tools.graph_traverse import TRAVERSALS
from mining_agents.tools.method_lookup import PACK_DIR, PACKS
from scripts.build_workspace_data import build_workspace

REPO = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO / "apps" / "shared" / "data"
PROFILE = REPO / "data" / "profile"
GENERATED = REPO / "data" / "generated"
PERSONA_PROFILES = REPO / "docs" / "persona-profiles.yaml"

# The one dollar figure this repo actually establishes. Everything else is the
# client's to supply; see docs/specs/2026-08-13-applications-design.md.
MILL_DOWNTIME_USD_PER_HOUR = 145_000

# APQC code -> the process name this catalog uses it for. Compound codes on
# agents that span two domains are split on "/" and looked up per part.
APQC_NAMES = {
    "2.0.1": "Develop and manage products and services",
    "4.1.2": "Manage inventory and materials",
    "4.2.2": "Manage production operations",
    "4.3.1": "Manage logistics and transportation",
    "5.2.1": "Procure materials and services",
    "9.1.2": "Manage health, safety and environment",
    "11.0.3": "Manage plant and asset maintenance",
}


# --------------------------------------------------------------------------
# Agent cards (design doc §2, §3) -- decision, leak, archetype, authority,
# financial line and evidence class come from AgentDef.card and are written
# through unchanged. Coverage is the one field on a card this module computes
# rather than copies: it is a live count of a pack's own drivers, read fresh
# every build, so a card can never claim more (or less) coverage than its pack
# currently has. See docs/specs/2026-08-17-value-framing-and-
# agent-cards-design.md section 2, "Coverage is the load-bearing row".
# --------------------------------------------------------------------------

def _coverage(pack_path: pathlib.Path) -> dict:
    """Count a pack's drivers by status, read from the file on every call.

    Never memoised, never typed by hand: the whole point is that this number
    tracks whatever the pack on disk says right now, including while another
    workstream is instrumenting it. `total` is always > 0 -- load_pack itself
    refuses to accept a pack with no drivers -- so a fully-uninstrumented pack
    still exports {"instrumented": 0, "total": N}, not an absent or null
    field, which would read on a card as full coverage.
    """
    pack = load_pack(pack_path)
    instrumented = sum(1 for d in pack.drivers if d.status == "instrumented")
    return {"instrumented": instrumented, "total": len(pack.drivers)}


def _card_record(agent) -> dict:
    """One agent's card, transcribed from AgentDef.card plus its live coverage."""
    card = agent.card
    record = {
        "agent_id": agent.agent_id,
        "display_name": agent.display_name,
        "decision": card.decision,
        "leaks": list(card.leaks),
        "archetype": card.archetype,
        "authority": card.authority,
        "financial_lines": [
            {"line": fl.line, "evidence_class": fl.evidence_class}
            for fl in card.financial_lines
        ],
        "honest_limit": card.honest_limit,
        # Always a list, never an absent key -- even when empty (S03, S05:
        # AgentCard's own docstring, "deliberately allowed to be empty").
        # The screens that read this field (agent-card.js, cockpit.js) branch
        # on its length, and an absent key would force every reader of the
        # export to special-case "field missing" as a second way of saying
        # the same thing as "field present and empty".
        "metric_impacts": [
            {
                "metric": mi.metric,
                "direction": mi.direction,
                "low_pct": mi.low_pct,
                "high_pct": mi.high_pct,
                "source": mi.source,
            }
            for mi in card.metric_impacts
        ],
    }
    if card.pack:
        record["pack"] = card.pack
        record["coverage"] = _coverage(PACK_DIR / card.pack)
    return record


def _cards_by_persona() -> dict:
    """Every catalog agent's card, grouped by the persona it is filed under.

    Only agents with an AgentDef carry a persona; AGT-19 (design §3) has none
    and is handled separately by _group_agent_cards().
    """
    grouped: dict[str, list[dict]] = collections.defaultdict(list)
    for agent in ALL_AGENTS:
        if agent.card is not None:
            grouped[agent.persona].append(_card_record(agent))
    return grouped


# AGT-19 Strategic Planning Advisor has no AgentDef and so never appears in
# ALL_AGENTS or in any persona's roster (design §3: "group-level and has no
# persona in this build"). Its authored fields are hand-transcribed here from
# the same source every other card's fields come from -- the PRD's own agent
# specification and financial-impact framework -- because there is no catalog
# entry to read them off. Its coverage is NOT hand-authored: _group_agent_cards
# computes it from the pack file exactly like every other card's, below.
_AGT19_CARD = {
    "agent_id": "AGT-19",
    "display_name": "Strategic Planning Advisor",
    "decision": "How the group plan should change when a price, cost or "
                "capital assumption moves, and which asset absorbs it.",
    "leaks": ["Latency"],
    "archetype": "Optimiser",
    "authority": "L1 — Recommend (permanent; no promotion path)",
    "financial_lines": [
        {
            "line": "group plan re-tested against a moved assumption → "
                     "capital allocation quality",
            "evidence_class": "C",
        },
    ],
    "honest_limit": "The least measurable agent in the portfolio, and the "
                     "easiest to oversell: it inherits every weakness of the "
                     "assumption set it is given, and a committee price deck "
                     "can be optimised very precisely while still being "
                     "wrong. It contributes nothing to a funding case and "
                     "must not be added to one.",
    "pack": "agt19-strategic-planning.yaml",
    # Deliberately empty, the same way S03's and S05's are (AgentCard's own
    # docstring): the plan's researched benchmark table has no row for
    # capital-allocation quality, and this card's own honest_limit already
    # says its one financial line is Class C and funds nothing -- stretching
    # an adjacent agent's percentage onto it would be exactly the borrowed
    # figure the plan rules out.
    "metric_impacts": [],
}


def _group_agent_cards() -> dict:
    """Cards for agents with no persona in this build -- today, just AGT-19."""
    card = dict(_AGT19_CARD)
    card["coverage"] = _coverage(PACK_DIR / card["pack"])
    return {card["agent_id"]: card}


def _all_cards() -> list[dict]:
    """Every card in the build, persona-holding and group-level alike."""
    cards = [_card_record(a) for a in ALL_AGENTS if a.card is not None]
    cards.extend(_group_agent_cards().values())
    return cards


def _leak_counts(cards: list[dict]) -> dict:
    """How many cards claim each leak, keyed on LEAKS so a count of zero still
    appears rather than being absent (design §1, band 1: every leak counted,
    never omitted)."""
    counts = {leak: 0 for leak in LEAKS}
    for card in cards:
        for leak in card["leaks"]:
            counts[leak] += 1
    return counts


def _metric_impact_summary(cards: list[dict]) -> list[dict]:
    """Every metric this build's carded agents move, grouped BY METRIC.

    Task C (plan 2026-08-18) asks the cockpit to choose between "metrics,
    with contributing agents" and "agents, with their metrics", and to
    justify the choice. Metric wins, for one concrete reason: several agents
    move the same metric with the identical published range -- S06 and S07
    both cite McKinsey's mineral-recovery range. An agent-first cockpit would
    either print that range twice, under two separate headings, reading as
    two independent claims when it is one; or it would need its own dedup
    pass bolted on afterwards to notice the two agents agree. Grouping by
    metric gets the dedup for free, because the grouping key -- metric,
    direction, bounds, source -- IS the tuple being deduplicated on; every
    agent citing an identical range is folded into that one range's own
    ``agents`` list rather than repeating the range.

    Cards with no metric_impacts (S03, S05, AGT-19) contribute no rows here.
    That is not a gap in this summary -- see AgentCard's own docstring and
    the per-card comments in mining_agents/catalog/definitions.py -- and the
    cockpit says so in its own words rather than leaving their absence
    unexplained.
    """
    by_metric: dict[str, dict] = {}
    for card in cards:
        for mi in card["metric_impacts"]:
            metric = mi["metric"]
            bucket = by_metric.setdefault(
                metric, {"metric": metric, "agents": set(), "ranges": {}}
            )
            bucket["agents"].add(card["agent_id"])
            key = (mi["direction"], mi["low_pct"], mi["high_pct"], mi["source"])
            range_bucket = bucket["ranges"].setdefault(
                key,
                {
                    "direction": mi["direction"],
                    "low_pct": mi["low_pct"],
                    "high_pct": mi["high_pct"],
                    "source": mi["source"],
                    "agents": set(),
                },
            )
            range_bucket["agents"].add(card["agent_id"])

    out = []
    for metric in sorted(by_metric):
        bucket = by_metric[metric]
        ranges = sorted(
            (
                {
                    "direction": r["direction"],
                    "low_pct": r["low_pct"],
                    "high_pct": r["high_pct"],
                    "source": r["source"],
                    "agents": sorted(r["agents"]),
                }
                for r in bucket["ranges"].values()
            ),
            key=lambda r: (r["low_pct"], r["high_pct"], r["source"]),
        )
        out.append({
            "metric": metric,
            "agents": sorted(bucket["agents"]),
            "ranges": ranges,
        })
    return out


def _traversal_holders(traversal: str) -> dict:
    """Which agents run a traversal, read off the catalog rather than typed here.

    The graph screen claims "this is the traversal S01 runs". That claim has to
    come from the same definitions that deploy S01, or it becomes a caption that
    quietly goes stale.
    """
    holders = [a for a in ALL_AGENTS if traversal in (getattr(a, "traversals", None) or ())]
    return {
        "agents": sorted(a.agent_id for a in holders),
        "entrypoints": sorted(
            a.agent_id for a in holders if a.swarm_role in (None, "coordinator")
        ),
    }


# The three property graphs that deployed agents actually traverse. A fourth
# exists in code -- MiningOntologyGraph / ontology_related -- but is granted to
# zero agents (tests/test_demo_scenarios.py pins that at exactly zero), so it is
# not exported: a screen showing a graph no agent reads would be showing scenery.
GRAPH_META = {
    "asset": {
        "bigquery_graph": "MiningAssetGraph",
        "traversal": "blast_radius",
        "question": "If this asset fails, what fails behind it?",
    },
    "supply_chain": {
        "bigquery_graph": "MiningSupplyChainGraph",
        "traversal": "stockout_exposure",
        "question": "If this part runs out, which work orders stall?",
    },
    "safety": {
        "bigquery_graph": "MiningOperationsSafetyGraph",
        "traversal": "fatigue_to_incident",
        "question": "Which fatigue readings precede an operator's incident?",
    },
}

def _traversal_sql(traversal: str) -> dict:
    """The deployed SQL, lifted off the tool rather than retyped for the screen.

    The graph screen prints this text and then walks the same pattern in the
    browser. Retyping it here would let the two drift, and the whole claim of
    that screen is that what it runs is what the agent runs. The COLUMNS
    aliases are parsed out of the same string, so a renamed column renames the
    table header instead of silently leaving it stale.
    """
    spec = TRAVERSALS[traversal]
    columns = re.findall(r"\bAS\s+(\w+)", spec.sql)
    if not columns:
        raise SystemExit(f"no COLUMNS aliases parsed out of {traversal!r} SQL")
    return {
        "sql": spec.sql.strip(),
        "params": list(spec.params),
        "columns": columns,
        "tables_read": list(spec.tables_read),
    }


for _name, _meta in GRAPH_META.items():
    _meta.update(_traversal_holders(_meta["traversal"]))
    _meta.update(_traversal_sql(_meta["traversal"]))


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _entrypoints() -> list:
    """The 52 externally callable agents: deep agents and swarm coordinators.

    A specialist or critic is reachable only through its coordinator, so it is
    not an entrypoint even though it is an agent.
    """
    return [a for a in ALL_AGENTS if a.swarm_role in (None, "coordinator")]


def _agent_record(agent) -> dict:
    return {
        "agent_id": agent.agent_id,
        "display_name": agent.display_name,
        "pattern": agent.pattern,
        "swarm_id": agent.swarm_id,
        "swarm_role": agent.swarm_role,
        "apqc_code": agent.apqc_code,
        "apqc_names": [
            APQC_NAMES.get(part.strip(), part.strip())
            for part in agent.apqc_code.split("/")
        ],
        "persona": agent.persona,
        "value_branch": agent.value_branch,
        "model_tier": agent.model_tier,
        "hitl_required": agent.hitl_required,
        "source_tables": list(agent.source_tables),
        "tools": list(agent.tools),
        "traversals": list(getattr(agent, "traversals", ()) or ()),
        "models": list(getattr(agent, "models", ()) or ()),
        "is_entrypoint": agent.swarm_role in (None, "coordinator"),
    }


def build_catalog() -> dict:
    entries = _entrypoints()

    swarms: dict[str, dict] = {}
    for agent in ALL_AGENTS:
        if agent.swarm_id is None:
            continue
        swarm = swarms.setdefault(
            agent.swarm_id, {"coordinator": None, "specialists": [], "critic": None}
        )
        if agent.swarm_role == "coordinator":
            swarm["coordinator"] = agent.agent_id
        elif agent.swarm_role == "critic":
            swarm["critic"] = agent.agent_id
        else:
            swarm["specialists"].append(agent.agent_id)

    return {
        "generated_at": _now(),
        "source": "mining_agents.catalog.definitions",
        "counts": {
            "agent_nodes": len(ALL_AGENTS),
            "entrypoints": len(entries),
            "swarms": len(swarms),
            "deep_agents": sum(1 for a in entries if a.pattern == "B"),
            "hitl_entrypoints": sum(1 for a in entries if a.hitl_required),
        },
        "by_persona": _counted(entries, lambda a: a.persona),
        "by_value_branch": _counted(entries, lambda a: a.value_branch),
        "by_apqc": _counted(entries, lambda a: a.apqc_code),
        # The literal code strings above include seven compound codes, and the
        # catalog spells two pairs both ways round -- "4.3.1 / 9.1.2" and
        # "9.1.2 / 4.3.1" are one process pair filed as two. Rolling up to the
        # atomic code is what makes the process view answer "how much of the
        # estate touches health and safety", which is the question a client
        # asks. An agent spanning two domains counts in both, so these counts
        # sum above the entrypoint total by design.
        "by_apqc_code": _counted_multi(
            entries, lambda a: [p.strip() for p in a.apqc_code.split("/")]
        ),
        "compound_apqc_codes": sorted(
            {a.apqc_code for a in entries if "/" in a.apqc_code}
        ),
        "tool_usage": dict(
            collections.Counter(t for a in entries for t in a.tools).most_common()
        ),
        "apqc_names": APQC_NAMES,
        "swarms": swarms,
        "agents": [_agent_record(a) for a in ALL_AGENTS],
        # The value screen's leak taxonomy band (design §1) reads leaks and
        # their counts from here rather than carrying its own list, so a
        # leak added or renamed in mining_agents.catalog.definitions moves
        # with the build instead of being retyped on the screen.
        "leaks": list(LEAKS),
        "leak_counts": _leak_counts(_all_cards()),
        # AGT-19 has no AgentDef and so never appears in "agents" above; its
        # card is exported here for the value screen (design §3, §4 step 4).
        "group_agents": _group_agent_cards(),
        # The cockpit's metric-impact band (Task C, plan 2026-08-18), grouped
        # by metric and deduplicated across agents that cite an identical
        # range -- see _metric_impact_summary's own docstring for why metric
        # rather than agent is the grouping key.
        "metric_impact_summary": _metric_impact_summary(_all_cards()),
    }


def _counted_multi(entries, keys) -> dict:
    """Like _counted, but an entry may belong to several groups at once."""
    grouped = collections.defaultdict(list)
    for agent in entries:
        for key in keys(agent):
            grouped[key].append(agent.agent_id)
    return {
        k: {"count": len(v), "agents": sorted(v)}
        for k, v in sorted(grouped.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    }


def _counted(entries, key) -> dict:
    """Group entrypoint ids by a key, ordered by descending group size."""
    grouped = collections.defaultdict(list)
    for agent in entries:
        grouped[key(agent)].append(agent.agent_id)
    return {
        k: {"count": len(v), "agents": sorted(v)}
        for k, v in sorted(grouped.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    }


def _persona_method(code: str) -> dict:
    """The governing metric from this persona's method pack, if it has one.

    Read through the same loader the runtime uses — PACKS says which persona
    has which pack, load_pack validates it — so the metric a screen prints is
    the metric the agent is working towards, rather than a second copy of it
    that is free to drift. A persona with no pack gets nothing at all: an empty
    method block would make the screens decide what an absent metric means.

    The pack is a repository file, so a failure to load it is a build failure
    and belongs here, loudly. It is not the runtime's situation, where the tool
    must degrade to a structured error rather than a traceback.
    """
    name = PACKS.get(code)
    if name is None:
        return {}
    return {"metric": load_pack(PACK_DIR / name).metric}


def build_personas(catalog: dict) -> dict:
    """Merge the transcribed persona profiles with live catalog counts.

    The quotes and journeys are human-transcribed from
    docs/personas-and-value-tree.md with line citations. The agent lists come
    from the catalog, so a persona's roster cannot drift from what is deployed.
    """
    profiles = yaml.safe_load(PERSONA_PROFILES.read_text())
    by_persona = catalog["by_persona"]
    cards_by_persona = _cards_by_persona()

    out = {}
    for code, profile in sorted(profiles.items()):
        catalog_agents = by_persona.get(code, {}).get("agents", [])
        if sorted(profile["agents"]) != sorted(catalog_agents):
            raise SystemExit(
                f"{code}: persona-profiles.yaml lists {sorted(profile['agents'])} "
                f"but the catalog says {sorted(catalog_agents)}. The catalog wins; "
                "fix docs/persona-profiles.yaml."
            )
        entry = dict(profile)
        entry["agents"] = catalog_agents
        entry["agent_count"] = len(catalog_agents)
        entry["hitl_agents"] = sorted(
            a["agent_id"]
            for a in catalog["agents"]
            if a["persona"] == code and a["is_entrypoint"] and a["hitl_required"]
        )
        method = _persona_method(code)
        if method:
            entry["method"] = method
        # Business-framing cards (design §2), one per agent of this persona
        # that declares one. Absent entirely for a persona with none, rather
        # than an empty list -- the same "say nothing rather than invent a
        # shape" rule build_personas already follows for `method` above.
        cards = cards_by_persona.get(code)
        if cards:
            entry["cards"] = cards
        out[code] = entry
    return {"generated_at": _now(), "source": str(PERSONA_PROFILES.relative_to(REPO)),
            "personas": out}


# --------------------------------------------------------------------------
# Graph export
# --------------------------------------------------------------------------

def build_graph_from_local() -> dict:
    """Build the property graphs from data/profile and the generated parquet.

    Used when BigQuery credentials are unavailable. Every entity here exists in
    the warehouse too; this path just reads the profiled copy.
    """
    import pandas as pd

    stats = json.loads((PROFILE / "stats.json").read_text())

    nodes: list[dict] = []
    edges: list[dict] = []

    # --- MiningAssetGraph: assets and their DEPENDS_ON chain ---
    for asset in stats["assets"]:
        nodes.append({
            "id": asset["asset_id"],
            "label": asset["asset_id"],
            "type": "Asset",
            "graph": "asset",
            "detail": {
                "name": asset["asset_name"],
                "asset_type": asset["asset_type"],
                "criticality": asset["criticality_rating"],
                "installed": asset["installed"],
                "state_keys": sorted(json.loads(asset["current_state"])),
            },
        })
    for dep in stats["asset_dependencies"]:
        edges.append({
            "source": dep["source_id"],
            "target": dep["target_id"],
            "label": "DEPENDS_ON",
            "graph": "asset",
            "weight": dep["impact_score"],
            "detail": {"dependency_type": dep["dependency_type"],
                       "impact_score": dep["impact_score"]},
        })

    # --- MiningSupplyChainGraph: Asset -> WorkOrder -> SparePart ---
    # The same five assets anchor this graph too. They are emitted a second time
    # under graph="supply_chain" rather than shared with the asset graph: every
    # HAS_WORK_ORDER edge needs its source node present in the view the screen
    # renders, and a screen filtering on graph would otherwise draw 126 edges
    # from nodes it never added.
    for asset in stats["assets"]:
        nodes.append({
            "id": asset["asset_id"],
            "label": asset["asset_id"],
            "type": "Asset",
            "graph": "supply_chain",
            "detail": {"name": asset["asset_name"],
                       "criticality": asset["criticality_rating"]},
        })

    work_orders = pd.read_parquet(GENERATED / "erp_work_orders.parquet")
    logs = pd.read_parquet(GENERATED / "maintenance_logs.parquet")
    inventory = pd.read_parquet(GENERATED / "inventory_levels.parquet")

    wo_parts = [
        (row.work_order_id, part)
        for row in logs.itertuples()
        for part in (row.parts_replaced if row.parts_replaced is not None else [])
    ]
    linked_orders = {wo for wo, _ in wo_parts}
    used_parts = {p for _, p in wo_parts}

    wo_by_id = {r.work_order_id: r for r in work_orders.itertuples()}
    for wo_id in sorted(linked_orders):
        row = wo_by_id.get(wo_id)
        nodes.append({
            "id": wo_id,
            "label": wo_id,
            "type": "WorkOrder",
            "graph": "supply_chain",
            "detail": {
                "asset_id": _field(row, "asset_id"),
                "priority": _field(row, "priority"),
                "status": _field(row, "status"),
                "repair_cost": _field(row, "repair_cost"),
                "description": _field(row, "description"),
            } if row is not None else {},
        })
        if row is not None and getattr(row, "asset_id", None):
            edges.append({"source": row.asset_id, "target": wo_id,
                          "label": "HAS_WORK_ORDER", "graph": "supply_chain"})

    stocked = {r.part_number: r for r in inventory.itertuples()}
    for part in sorted(used_parts):
        row = stocked.get(part)
        nodes.append({
            "id": part,
            "label": part,
            "type": "SparePart",
            "graph": "supply_chain",
            "detail": {
                "description": _field(row, "part_description"),
                "stock_level": _field(row, "stock_level"),
                "reorder_point_limit": _field(row, "reorder_point_limit"),
                "lead_time_days": _field(row, "lead_time_days"),
                "unit_price_usd": _field(row, "unit_price_usd"),
                "below_reorder_point": bool(
                    _field(row, "stock_level") <= _field(row, "reorder_point_limit")
                ),
            } if row is not None else {"stocked": False},
        })
    # Direction matters and is not arbitrary: MiningSupplyChainGraph declares
    # WorkOrder -[REPLACED_PART]-> SparePart, which is why stockout_exposure
    # spells the hop as (p:SparePart) <-[:REPLACED_PART]- (wo:WorkOrder). A
    # screen that draws the arrow the other way is drawing an edge the
    # warehouse does not have.
    for wo_id, part in sorted(set(wo_parts)):
        edges.append({"source": wo_id, "target": part,
                      "label": "REPLACED_PART", "graph": "supply_chain"})

    # --- MiningOperationsSafetyGraph: FatigueLog -> Operator -> Vehicle -> Incident ---
    fatigue = pd.read_parquet(GENERATED / "fatigue_logs_node.parquet")
    alerts = fatigue[fatigue["fatigue_alert_triggered"]]
    for row in alerts.itertuples():
        nodes.append({
            "id": row.log_id,
            "label": row.log_id[:8],
            "type": "FatigueLog",
            "graph": "safety",
            "detail": {
                "timestamp": row.timestamp.isoformat(),
                "operator_id": row.operator_id,
                "heart_rate_bpm": _num(row.heart_rate_bpm),
                "sleep_deficit_hours": _num(row.sleep_deficit_hours),
                "microsleep_events_detected": _num(row.microsleep_events_detected),
            },
        })
        edges.append({"source": row.log_id, "target": row.operator_id,
                      "label": "LOGGED_FOR", "graph": "safety"})

    for operator in sorted(fatigue["operator_id"].unique()):
        readings = fatigue[fatigue["operator_id"] == operator]
        nodes.append({
            "id": operator,
            "label": operator,
            "type": "Operator",
            "graph": "safety",
            "detail": {
                "fatigue_readings": int(len(readings)),
                "alerts_triggered": int(readings["fatigue_alert_triggered"].sum()),
                "max_sleep_deficit_hours": _num(readings["sleep_deficit_hours"].max()),
            },
        })

    vehicles = {v["vehicle_id"]: v for v in stats["fleet_vehicles_sample"]}
    seen_vehicles: set[str] = set()
    for assignment in stats["operator_assignments"]:
        vehicle_id = assignment["vehicle_id"]
        if vehicle_id not in seen_vehicles:
            seen_vehicles.add(vehicle_id)
            vehicle = vehicles.get(vehicle_id, {})
            nodes.append({
                "id": vehicle_id, "label": vehicle_id, "type": "Vehicle",
                "graph": "safety",
                "detail": {"model": vehicle.get("model"),
                           "status": vehicle.get("operational_status"),
                           "payload_capacity_tons": vehicle.get("payload_capacity_tons")},
            })
        edges.append({"source": assignment["operator_id"], "target": vehicle_id,
                      "label": "OPERATES", "graph": "safety",
                      "detail": {"shift_date": assignment["shift_date"],
                                 "shift_type": assignment["shift_type"]}})

    # safety_incidents has neither a parquet nor an entry in the calibration
    # profile, so severity_level -- a column fatigue_to_incident selects -- is
    # not locally derivable. It is declared here as an explicit null rather than
    # left absent, so the screen can print "not in local files" in that cell
    # instead of an empty one that reads as a severity of nothing.
    for involvement in stats["incident_involvements"]:
        incident_id = involvement["incident_id"]
        nodes.append({"id": incident_id, "label": incident_id, "type": "Incident",
                      "graph": "safety", "detail": {"severity_level": None}})
        edges.append({"source": involvement["vehicle_id"], "target": incident_id,
                      "label": "INVOLVED_IN", "graph": "safety"})

    # Every graph below shows less than the whole table it draws from. The
    # sentences are built from the same frames that built the nodes, so a screen
    # quoting them cannot claim a ratio the export does not hold.
    assigned_operators = {a["operator_id"] for a in stats["operator_assignments"]}
    scope = {
        "asset": (
            f"All {len(stats['assets'])} assets and all "
            f"{len(stats['asset_dependencies'])} dependency edges. Nothing filtered."
        ),
        "supply_chain": (
            f"Work orders that consumed a part: {len(linked_orders)} of "
            f"{len(work_orders)}. Parts consumed: {len(used_parts)} of "
            f"{len(inventory)} held in inventory."
        ),
        "safety": (
            f"Fatigue logs that raised an alert: {len(alerts)} of {len(fatigue)}. "
            f"Only {len(assigned_operators)} of {fatigue['operator_id'].nunique()} "
            "operators hold a vehicle assignment, so the traversal returns rows "
            "for those and is empty for the rest."
        ),
    }
    # Provenance, stated at the precision a screen can repeat. These are two
    # different vintages of the same site and saying so matters: stats.json
    # self-describes as the calibration profile captured BEFORE the data was
    # regenerated, and it is the only local source for the edge tables, which
    # have no parquet. So the entities come from the older snapshot and the
    # measurements from the current one. BigQuery settles both; re-run this
    # export against it once credentials are back.
    source = (
        "local files, two vintages: asset, vehicle, assignment and incident "
        f"records from {(PROFILE / 'stats.json').relative_to(REPO)} "
        f"({stats['_note'].rstrip('.')}); work orders, parts and fatigue logs "
        f"from {GENERATED.relative_to(REPO)}/*.parquet, the current generated "
        "data. BigQuery is authoritative for both and was unreachable at build "
        "time."
    )
    return _assemble_graph(nodes, edges, source=source, scope=scope)


def _field(row, name):
    """Read a column off an itertuples row, refusing to invent a missing one.

    getattr(row, name, None) is the obvious spelling and the wrong one: it
    returns None for a column that does not exist, which is indistinguishable
    from a column that exists and is null. That is how every SparePart on the
    supply chain screen came to render an empty price -- inventory_levels calls
    the column stock_level, not quantity_on_hand, and nothing said so.
    """
    if not hasattr(row, name):
        raise SystemExit(
            f"column {name!r} is not in this frame; available: "
            f"{sorted(f for f in row._fields if not f.startswith('_'))}"
        )
    return _num(getattr(row, name))


def _num(value):
    """JSON cannot hold numpy scalars or NaN; normalise both away."""
    if value is None:
        return None
    try:
        as_float = float(value)
    except (TypeError, ValueError):
        return value
    if as_float != as_float:  # NaN
        return None
    return int(as_float) if as_float.is_integer() else round(as_float, 4)


def _assemble_graph(nodes: list[dict], edges: list[dict], source: str,
                    scope: dict[str, str]) -> dict:
    """Deduplicate, then record per-graph counts so a screen can state its scale.

    Identity is (graph, id), not id: an asset is a node of both the asset graph
    and the supply chain graph, and collapsing the two would strip the supply
    chain view of the endpoints its HAS_WORK_ORDER edges point at.
    """
    unique_nodes = {(n["graph"], n["id"]): n for n in nodes}
    unique_edges = {
        (e["graph"], e["source"], e["target"], e["label"]): e for e in edges
    }
    node_list = sorted(unique_nodes.values(), key=lambda n: (n["graph"], n["type"], n["id"]))
    edge_list = sorted(unique_edges.values(), key=lambda e: (e["graph"], e["source"], e["target"]))

    per_graph = {}
    for name in sorted({n["graph"] for n in node_list}):
        graph_nodes = [n for n in node_list if n["graph"] == name]
        graph_edges = [e for e in edge_list if e["graph"] == name]
        present = {n["id"] for n in graph_nodes}
        dangling = sorted(
            {e["source"] for e in graph_edges if e["source"] not in present}
            | {e["target"] for e in graph_edges if e["target"] not in present}
        )
        if dangling:
            raise SystemExit(
                f"graph {name!r} has edges pointing at {len(dangling)} node(s) it "
                f"does not contain: {dangling[:5]}. A renderer would silently drop "
                "those edges, so the screen would understate the graph."
            )
        per_graph[name] = dict(
            GRAPH_META[name],
            scope=scope.get(name),
            nodes=len(graph_nodes),
            edges=len(graph_edges),
            node_types=dict(collections.Counter(n["type"] for n in graph_nodes)),
            edge_labels=dict(collections.Counter(e["label"] for e in graph_edges)),
        )

    return {
        "generated_at": _now(),
        "source": source,
        "graphs": per_graph,
        "nodes": node_list,
        "edges": edge_list,
    }


# The CEO tree from docs/personas-and-value-tree.md section 1, rooted on AISC
# per tonne, expressed as compositions of the catalog's finer value_branch
# values. The catalog decides membership; this only says which branch a
# value_branch rolls into, and build_value_tree refuses to emit a tree whose
# parts do not add back to 52.
CEO_TREE = {
    "B1": {
        "title": "Asset availability and unplanned downtime",
        "apqc": "11.0.3",
        "branches": ["asset_reliability", "maintenance_execution"],
        "mechanism": (
            "Detect the fault before it stops the mill, and rank what to fix by "
            "what fails behind it rather than by who asked loudest."
        ),
        "anchored": True,
    },
    "B2": {
        "title": "Ore realisation — grade and dilution against plan",
        "apqc": "2.0.1",
        "branches": ["geology"],
        "mechanism": (
            "Reconcile what the block model promised against what the mill "
            "received, so dilution is caught in the pit rather than in the "
            "month-end variance."
        ),
        "anchored": False,
    },
    "B3": {
        "title": "Processing recovery and throughput",
        "apqc": "11.0.3",
        "branches": ["processing"],
        "mechanism": (
            "Hold recovery against feed variability by moving the plant set "
            "points on evidence rather than on the last shift's habit."
        ),
        "anchored": False,
    },
    "B4": {
        "title": "Haulage productivity and cycle efficiency",
        "apqc": "11.0.1",
        "branches": ["mine_ops"],
        "mechanism": (
            "Find the queue, the detour and the idling truck while the shift is "
            "still running and the dispatch can still change."
        ),
        "anchored": False,
    },
    "B5": {
        "title": "Materials and procurement cost leakage",
        "apqc": "4.1.2 / 3.0.1",
        "branches": ["supply_chain", "procurement"],
        "mechanism": (
            "Know a part will not be on the shelf before the crew is standing at "
            "the store, and buy it on a contract someone checked."
        ),
        "anchored": False,
    },
    "B6": {
        "title": "Safety, fatigue and licence to operate",
        "apqc": "9.1.2",
        "branches": ["safety"],
        "mechanism": (
            "Connect the fatigue signal to the operator, the vehicle and the "
            "incident, so the intervention lands before the incident does."
        ),
        "anchored": False,
    },
}

# S12 is deliberately not a branch: it is the convergence layer where all six
# resolve into one narrative, and the CEO/GM surface.
CONVERGENCE_BRANCH = "site_wide"


def build_value_tree(catalog: dict) -> dict:
    """The six-branch CEO tree, reconciled against the catalog.

    docs/personas-and-value-tree.md carries an arithmetic slip here: its table
    gives Branch 6 a count of 10 while listing 9 entrypoints, which absorbs S12
    into a branch the same document's prose explicitly places above all six. The
    catalog settles it -- safety holds 9, site_wide holds S12 alone -- and the
    assertion below stops that slip from reaching a screen.
    """
    by_branch = catalog["by_value_branch"]
    tree, claimed = [], []
    for code, spec in CEO_TREE.items():
        agents = sorted(
            a for b in spec["branches"] for a in by_branch.get(b, {}).get("agents", [])
        )
        claimed += agents
        tree.append(dict(spec, code=code, agents=agents, count=len(agents),
                         personas=sorted({
                             a["persona"] for a in catalog["agents"]
                             if a["agent_id"] in set(agents) and a["persona"]
                         })))

    convergence = by_branch.get(CONVERGENCE_BRANCH, {}).get("agents", [])
    total = len(claimed) + len(convergence)
    expected = catalog["counts"]["entrypoints"]
    if sorted(claimed + convergence) != sorted(
        a["agent_id"] for a in catalog["agents"] if a["is_entrypoint"]
    ):
        raise SystemExit(
            f"the CEO tree covers {total} entrypoints, the catalog has {expected}. "
            "Every entrypoint must land in exactly one branch or in the "
            "convergence layer; re-derive CEO_TREE against the catalog."
        )

    return {
        "root": "All-in Sustaining Cost (AISC) per tonne",
        "root_source": "docs/personas-and-value-tree.md section 1",
        "branches": tree,
        "convergence": {
            "agents": convergence,
            "note": (
                "S12 is deliberately not a branch. It sits above the six as the "
                "layer where every branch's day resolves into one narrative, "
                "which is also the CEO and GM surface."
            ),
        },
    }


def build_facts() -> dict:
    """The site as the demo actually holds it, counted rather than remembered.

    Every entry carries the file it was counted from, so screen 1.2 can cite a
    source per figure. Anything the local files cannot settle is left out
    entirely rather than filled in from an earlier note -- the fleet size is the
    live example: data/profile only keeps a three-row vehicle sample, so this
    export cannot honestly state how many vehicles the site runs.
    """
    import pandas as pd

    def parquet(name):
        return pd.read_parquet(GENERATED / f"{name}.parquet")

    telemetry = parquet("telemetry_stream")
    work_orders = parquet("erp_work_orders")
    fatigue = parquet("fatigue_logs_node")
    inventory = parquet("inventory_levels")
    stats = json.loads((PROFILE / "stats.json").read_text())
    generated = f"{GENERATED.relative_to(REPO)}"

    def entry(label, value, unit, source):
        return {"label": label, "value": value, "unit": unit, "source": source}

    return {
        "generated_at": _now(),
        "mill_downtime_usd_per_hour": MILL_DOWNTIME_USD_PER_HOUR,
        "mill_downtime_source": "docs/personas-and-value-tree.md",
        "note": (
            "This is the only monetary figure this repository establishes. Every "
            "other magnitude renders as [CLIENT INPUT REQUIRED]."
        ),
        "site": [
            entry("Assets under management", len(stats["assets"]), "assets",
                  "data/profile/stats.json"),
            entry("Telemetry readings", len(telemetry), "readings",
                  f"{generated}/telemetry_stream.parquet"),
            entry("Distinct telemetry metrics", telemetry["metric_name"].nunique(),
                  "metrics", f"{generated}/telemetry_stream.parquet"),
            entry("Work orders", len(work_orders), "orders",
                  f"{generated}/erp_work_orders.parquet"),
            entry("Parts held in inventory", len(inventory), "SKUs",
                  f"{generated}/inventory_levels.parquet"),
            entry("Parts at or below reorder point",
                  int((inventory["stock_level"] <= inventory["reorder_point_limit"]).sum()),
                  "SKUs", f"{generated}/inventory_levels.parquet"),
            entry("Operators monitored for fatigue", fatigue["operator_id"].nunique(),
                  "operators", f"{generated}/fatigue_logs_node.parquet"),
            entry("Fatigue readings", len(fatigue), "readings",
                  f"{generated}/fatigue_logs_node.parquet"),
            entry("Maintenance log entries", len(parquet("maintenance_logs")), "entries",
                  f"{generated}/maintenance_logs.parquet"),
            entry("Geological block model cells", len(parquet("geological_block_models")),
                  "blocks", f"{generated}/geological_block_models.parquet"),
            entry("Drill assay intervals", len(parquet("drill_assay_logs")), "intervals",
                  f"{generated}/drill_assay_logs.parquet"),
            entry("Metallurgical recovery records", len(parquet("metallurgical_recovery")),
                  "records", f"{generated}/metallurgical_recovery.parquet"),
        ],
        "window": {
            "from": str(telemetry["timestamp"].min()),
            "to": str(telemetry["timestamp"].max()),
            "source": f"{generated}/telemetry_stream.parquet",
        },
        "not_locally_derivable": [
            {
                "figure": "Fleet vehicle count",
                "why": (
                    "data/profile/stats.json keeps a three-row sample of "
                    "fleet_vehicles, not the table. Only the 5 vehicles carrying "
                    "an operator assignment are known locally. BigQuery settles it."
                ),
            },
        ],
    }


# --------------------------------------------------------------------------
# Signal export
# --------------------------------------------------------------------------

# Every series on a screen is drawn at this many points. The generated tables
# hold between 167 and 25,946 rows; a screen cannot draw 25,946 points and does
# not need to, but it must not pretend the 64 it draws are 64 readings. So each
# series carries the reading count it was reduced from and states the reduction
# in its own caption.
SIGNAL_BUCKETS = 64

# One headline metric per asset -- the reading a control-room operator watches
# for that machine. Choosing here rather than on the screen keeps the choice
# next to the assertion below that the metric exists in the table at all.
ASSET_SIGNALS = {
    "MILL-01": ("power_draw_mw", "MW", "Power draw"),
    "CRUSHER-03": ("feed_rate_tph", "t/h", "Feed rate"),
    "CONVEYOR-02": ("belt_tension_kn", "kN", "Belt tension"),
    "TRUCK-08": ("payload_tons", "t", "Payload"),
    "PUMP-104A": ("vibration_hz", "Hz", "Vibration"),
}


def _bucketed(frame, value_col: str, how: str = "mean") -> dict:
    """Reduce a timestamped frame to SIGNAL_BUCKETS points of equal duration.

    Equal duration rather than equal row count: the buckets are read as a time
    axis, and a bucket holding twice the rows of its neighbour because the
    sensor happened to report twice as often would draw a line that is not the
    shape of the signal. A bucket with no rows carries null and the renderer
    breaks the line there rather than joining across a gap that has no data.
    """
    import pandas as pd

    times = pd.to_datetime(frame["timestamp"], utc=True)
    lo, hi = times.min(), times.max()
    edges = pd.date_range(lo, hi, periods=SIGNAL_BUCKETS + 1)
    # right=False keeps the first reading inside bucket 0; the final edge is
    # exclusive under that rule, so the last reading is pulled back by hand
    # rather than dropped.
    index = pd.cut(times, bins=edges, labels=False, right=False, include_lowest=True)
    index = index.fillna(SIGNAL_BUCKETS - 1).astype(int).clip(0, SIGNAL_BUCKETS - 1)

    grouped = frame[value_col].groupby(index)
    reduced = (grouped.sum() if how == "sum" else grouped.mean())
    if how == "sum":
        # A bucket with no alerts genuinely holds zero, which is a fact; a
        # bucket with no readings holds nothing, which is not.
        reduced = reduced.reindex(range(SIGNAL_BUCKETS), fill_value=0)
    else:
        reduced = reduced.reindex(range(SIGNAL_BUCKETS))

    points = [None if v != v else _num(v) for v in reduced.tolist()]
    present = [p for p in points if p is not None]
    return {
        "points": points,
        "min": min(present),
        "max": max(present),
        "readings": int(len(frame)),
        "from": lo.isoformat(),
        "to": hi.isoformat(),
    }


def _histogram(values, bins: int) -> dict:
    """Counts per equal-width bin, with the edges, so a screen can label an axis."""
    import numpy as np

    counts, edges = np.histogram(values.dropna(), bins=bins)
    return {
        "bins": [int(c) for c in counts],
        "edges": [_num(e) for e in edges],
        "n": int(values.notna().sum()),
    }


# The quantities whose best-day-to-median-day gap the value screens argue from,
# and the published benchmark each one is set beside. A row names its benchmark
# here rather than on the screen so that a figure and the third-party claim it
# is compared against cannot drift apart in the markup.
#
# PUMP-104A is deliberately absent. Its p90 day is 45% above its median day,
# which is by far the largest gap in the data and is not an achievement: the
# bearing is degrading across the window. Printing it beside "your best day"
# would present a failing pump as a target.
GAP_METRICS = [
    {"id": "recovery", "label": "Metallurgical recovery",
     "table": "metallurgical_recovery", "column": "recovery_rate_pct",
     "unit": "%", "delta_kind": "points", "benchmark": "throughput_100_assets"},
    # Recovery cites the recovery half of the 100-asset study; feed rate cites
    # the most recent published throughput range rather than the throughput half
    # of the same paper, so the two rows are answered by two publishers.
    {"id": "feed_rate", "label": "Crusher feed rate",
     "asset_id": "CRUSHER-03", "column": "feed_rate_tph",
     "unit": "t/h", "delta_kind": "percent", "benchmark": "mature_ai_uplift"},
    {"id": "payload", "label": "Truck payload",
     "asset_id": "TRUCK-08", "column": "payload_tons",
     "unit": "t", "delta_kind": "percent", "benchmark": "haulage_ahs"},
    {"id": "conveyor_load", "label": "Conveyor load",
     "asset_id": "CONVEYOR-02", "column": "load_pct",
     "unit": "%", "delta_kind": "percent", "benchmark": None},
]

BENCHMARKS = REPO / "docs" / "external-benchmarks.yaml"
BENCHMARK_FIELDS = ("id", "headline", "figure", "title", "publisher", "year", "url")

# Publishers write ranges in words as often as in digits -- "one to three
# percentage points" sits in the same paragraph as "8 to 10 percent". The
# uplift check below has to recognise both, or half the entries would have to
# carry a bound the checker cannot find in the sentence it came from.
NUMBER_WORDS = {
    0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
    6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
    11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
    15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
    19: "nineteen", 20: "twenty", 30: "thirty", 40: "forty", 50: "fifty",
}


def _bound_is_quoted(bound: float, text: str) -> bool:
    """Does this number actually appear in the sentence it was drawn from?

    The uplift blocks in the benchmarks file are a machine-readable restatement
    of numbers that already exist in `figure`. A restatement can drift from its
    original -- somebody widens a range on the screen and nobody re-reads the
    quote. This is the check that makes that impossible: an uplift bound must
    be findable in the published text, in digits or in English.
    """
    forms = {f"{bound:g}"}
    if float(bound).is_integer():
        forms.add(str(int(bound)))
        word = NUMBER_WORDS.get(int(bound))
        if word:
            forms.add(word)
    lowered = text.lower()
    return any(form in lowered for form in forms)


def build_benchmarks() -> dict:
    """Third-party figures, loaded from the one file that is allowed to hold them.

    These are the only numbers on any screen that this repository did not
    measure, so the bar is a citation rather than a query: an entry without a
    title, publisher, year and url cannot be traced back to a document by
    someone who doubts it, and a figure a CEO cannot check is a figure that
    costs more trust than it buys.
    """
    doc = yaml.safe_load(BENCHMARKS.read_text())
    entries = doc.get("benchmarks") or []
    if not entries:
        raise SystemExit(f"{BENCHMARKS.relative_to(REPO)} lists no benchmarks.")

    by_id = {}
    for entry in entries:
        missing = [f for f in BENCHMARK_FIELDS if not entry.get(f)]
        if missing:
            raise SystemExit(
                f"benchmark {entry.get('id', '<no id>')!r} is missing "
                f"{missing}; every external figure must carry its source. "
                f"Fix {BENCHMARKS.relative_to(REPO)}."
            )
        if entry["id"] in by_id:
            raise SystemExit(f"duplicate benchmark id {entry['id']!r}.")
        by_id[entry["id"]] = entry

    wanted = {m["benchmark"] for m in GAP_METRICS if m["benchmark"]}
    unknown = sorted(wanted - set(by_id))
    if unknown:
        raise SystemExit(
            f"GAP_METRICS cites benchmark ids {unknown} that "
            f"{BENCHMARKS.relative_to(REPO)} does not define."
        )

    # Pools in file order, so the screen's "what others published" range is
    # assembled from the source file rather than from a second list kept by
    # hand in JavaScript, where it could disagree with this one silently.
    by_pool: dict[str, list[str]] = {}
    units: dict[tuple[str, str], str] = {}
    for entry in entries:
        pool = entry.get("pool")
        uplifts = entry.get("uplift") or []
        if uplifts and not pool:
            raise SystemExit(
                f"benchmark {entry['id']!r} carries an uplift but no pool; "
                "an uplift with nowhere to be shown is an uplift nobody checks."
            )
        if pool:
            by_pool.setdefault(pool, []).append(entry["id"])
        for up in uplifts:
            for field in ("metric", "low", "high", "unit"):
                if up.get(field) in (None, ""):
                    raise SystemExit(
                        f"benchmark {entry['id']!r} has an uplift missing {field!r}."
                    )
            if up["low"] > up["high"]:
                raise SystemExit(
                    f"benchmark {entry['id']!r} uplift {up['metric']!r} runs "
                    f"{up['low']} to {up['high']}, which is backwards."
                )
            quoted = f"{entry['figure']} {entry.get('aside') or ''}"
            for bound in (up["low"], up["high"]):
                if not _bound_is_quoted(bound, quoted):
                    raise SystemExit(
                        f"benchmark {entry['id']!r} claims an uplift bound of "
                        f"{bound}, which does not appear in the text it quotes. "
                        "Every number on a screen has to be findable in the "
                        "publisher's own sentence."
                    )
            # Two entries in one pool describing the same metric are merged into
            # a single range on the screen, which is only legitimate if they are
            # in the same unit. Points and percent are not interchangeable.
            key = (pool, up["metric"])
            if units.setdefault(key, up["unit"]) != up["unit"]:
                raise SystemExit(
                    f"pool {pool} describes {up['metric']!r} in both "
                    f"{units[key]!r} and {up['unit']!r}; the screen would merge "
                    "them into one range and the range would be meaningless."
                )

    return {
        "generated_at": _now(),
        "source": str(BENCHMARKS.relative_to(REPO)),
        "by_id": by_id,
        "order": [e["id"] for e in entries],
        "by_pool": by_pool,
        # Carried into the bundle so the excluded list travels with the screens
        # it is protecting. Nobody re-adds a figure they can see was rejected.
        "excluded": doc.get("excluded") or [],
        # Retired figures are kept apart from rejected ones: these were properly
        # sourced when they were printed, and the distinction matters to anyone
        # reviewing an older screenshot.
        "superseded": doc.get("superseded") or [],
    }


def build_gap(telemetry, recovery) -> dict:
    """How far this site's best day sits above its ordinary day.

    The whole value argument rests on this: the p90 day is not a capability
    that has to be bought, it is one this plant and these people already
    reached. What is missing is repetition.

    p90 rather than the maximum, because a single best day is an anecdote and
    one unusual shift should not set the target. Median rather than the mean,
    because a handful of bad days would drag a mean down and flatter the gap.

    Daily means, not raw readings: the claim is about a day's operation, and a
    p90 taken over 2-hourly readings would compare the best two hours of the
    half-year against a typical two hours, which is a different and much
    larger number that no one could ever run a site to.
    """
    import pandas as pd

    rows = []
    for metric in GAP_METRICS:
        if "asset_id" in metric:
            frame = telemetry[
                (telemetry["asset_id"] == metric["asset_id"])
                & (telemetry["metric_name"] == metric["column"])
            ]
            if frame.empty:
                raise SystemExit(
                    f"gap metric {metric['id']!r} found no "
                    f"{metric['column']!r} rows for {metric['asset_id']!r}."
                )
            times, values = frame["timestamp"], frame["metric_value"]
            source = f"{GENERATED.relative_to(REPO)}/telemetry_stream.parquet"
            holder = metric["asset_id"]
        else:
            frame = recovery
            times, values = frame["timestamp"], frame[metric["column"]]
            source = (f"{GENERATED.relative_to(REPO)}/"
                      f"{metric['table']}.parquet")
            holder = None

        daily = pd.DataFrame({
            "day": pd.to_datetime(times, utc=True).dt.date,
            "value": values,
        }).groupby("day")["value"].mean()

        median, p90 = float(daily.median()), float(daily.quantile(0.90))
        delta = p90 - median
        # Every day, sorted worst to best. Drawn this way the median and the
        # p90 land at the halfway and nine-tenths marks by construction, so a
        # reader can see where the two figures were taken from instead of
        # being asked to accept them. A time series would not show that -- it
        # would show weather.
        ladder = [_num(v) for v in sorted(float(x) for x in daily)]
        rows.append({
            "id": metric["id"], "label": metric["label"],
            "asset_id": holder, "column": metric["column"],
            "unit": metric["unit"], "delta_kind": metric["delta_kind"],
            "median": _num(median), "p90": _num(p90),
            "delta": _num(delta),
            "delta_pct": _num(delta / median * 100.0),
            "days": int(len(daily)),
            "ladder": ladder,
            "benchmark": metric["benchmark"],
            "source": source,
        })

    return {
        "rows": rows,
        "method": (
            "Each figure is a daily mean. The best day is the 90th percentile "
            "day and the ordinary day is the median day, across "
            f"{rows[0]['days']} days of recorded operation."
        ),
        "caveat": (
            "The gap is the size of the opportunity, not a promise. Some of it "
            "is ore variability, weather and planned work, and no amount of "
            "software recovers that part."
        ),
        "excluded": [{
            "asset_id": "PUMP-104A",
            "reason": (
                "Its best day sits 45% above its ordinary day, the widest gap "
                "in this data, and it is not an achievement — the vibration "
                "trend is a bearing degrading across the window. It belongs to "
                "the downtime argument, not this one."
            ),
        }],
    }


def build_roi(gap: dict, recovery) -> dict:
    """The one conversion this repository can honestly supply to a business case.

    A recovery point is not money until three things are known: how much ore
    goes through the mill, what the ore carries, and what the metal sells for.
    This site's own record settles the middle one -- 167 days of concentrator
    feed assays -- and says nothing about the other two. So the export stops
    exactly there: it publishes tonnes of contained metal per million tonnes
    milled per point of recovery, and leaves throughput and price to the only
    people who hold them. A screen that guessed either would be inventing the
    client's business in front of the client.

    The metal is deliberately not named. The physical half of this calculation
    is metallurgy and does not care which metal the assay is of -- a point of
    recovery on a 1.08% feed is 108 t per Mt whatever is in the concentrate.
    Naming a metal here would invite an argument about the wrong thing, and a
    single spot price would be stale before the deck was read, which is why the
    price side is asked for as a range.

    Contained metal, not payable: smelter payability, treatment and refining
    charges take a cut that this repository has no terms for. Stating the
    figure as contained and saying so is honest; applying a remembered
    payability factor would not be.
    """
    row = next(r for r in gap["rows"] if r["id"] == "recovery")
    grade = float(recovery["feed_grade_pct"].median())
    # One tonne of ore carries grade/100 t of metal. A point of recovery is
    # one percent of that. Per million tonnes milled, the 1e6 and the 100s
    # collapse to grade * 100.
    per_point = grade * 100.0
    return {
        "generated_at": _now(),
        "feed_grade_pct": _num(grade),
        "feed_grade_days": int(len(recovery)),
        "feed_grade_source": (f"{GENERATED.relative_to(REPO)}/"
                              "metallurgical_recovery.parquet"),
        "recovery_gap_pts": row["delta"],
        "t_per_mt_per_point": _num(per_point),
        "client_inputs": [
            "Annual mill throughput",
            "Realised metal price, low",
            "Realised metal price, high",
        ],
        "basis": (
            "Contained metal, before smelter payability and treatment and "
            "refining charges, for which this repository holds no terms."
        ),
    }


def build_signals() -> dict:
    """The real measurements the screens draw.

    Until now the bundle carried schemas and counts and no measurement at all,
    so the only chart in either application plotted how many agents were in a
    branch. That is an org chart wearing a mine's clothes. Everything here is
    reduced from data/generated/*.parquet and every entry names the file and
    the column it came from, because a line on a screen with no source behind
    it is decoration.

    A branch gets a line only where a time axis genuinely exists. B2's block
    model is spatial and B5's inventory is a standing level, so those two carry
    a distribution and a share instead. The asymmetry is the shape of the data
    and is left visible rather than smoothed into six identical sparklines.
    """
    import pandas as pd

    def parquet(name):
        return pd.read_parquet(GENERATED / f"{name}.parquet")

    generated = f"{GENERATED.relative_to(REPO)}"
    telemetry = parquet("telemetry_stream")
    telemetry_src = f"{generated}/telemetry_stream.parquet"

    def series_for(asset_id: str, metric: str):
        rows = telemetry[
            (telemetry["asset_id"] == asset_id) & (telemetry["metric_name"] == metric)
        ]
        if rows.empty:
            raise SystemExit(
                f"telemetry_stream holds no {metric!r} for {asset_id!r}; available: "
                f"{sorted(telemetry[telemetry['asset_id'] == asset_id]['metric_name'].unique())}"
            )
        return _bucketed(rows, "metric_value")

    assets = []
    for asset_id, (metric, unit, label) in ASSET_SIGNALS.items():
        assets.append(dict(
            series_for(asset_id, metric),
            asset_id=asset_id, metric=metric, unit=unit, label=label,
            source=telemetry_src,
        ))

    recovery = parquet("metallurgical_recovery")
    fatigue = parquet("fatigue_logs_node")
    blocks = parquet("geological_block_models")
    inventory = parquet("inventory_levels")

    def reduced_from(readings: int, what: str) -> str:
        return (
            f"{readings:,} {what} reduced to {SIGNAL_BUCKETS} points of equal "
            "duration; each point is the mean of its bucket."
        )

    b1 = dict(series_for("MILL-01", "power_draw_mw"), kind="series",
              label="MILL-01 power draw", unit="MW", source=telemetry_src)
    b1["caption"] = reduced_from(b1["readings"], "readings")

    b3_rows = recovery[["timestamp", "recovery_rate_pct"]]
    b3 = dict(_bucketed(b3_rows, "recovery_rate_pct"), kind="series",
              label="Concentrator recovery rate", unit="%",
              source=f"{generated}/metallurgical_recovery.parquet")
    b3["caption"] = reduced_from(b3["readings"], "daily records")

    b4 = dict(series_for("TRUCK-08", "payload_tons"), kind="series",
              label="TRUCK-08 payload", unit="t", source=telemetry_src)
    b4["caption"] = reduced_from(b4["readings"], "readings")

    b6_rows = fatigue[["timestamp", "fatigue_alert_triggered"]].assign(
        fatigue_alert_triggered=lambda f: f["fatigue_alert_triggered"].astype(int)
    )
    b6 = dict(_bucketed(b6_rows, "fatigue_alert_triggered", how="sum"), kind="series",
              label="Fatigue alerts raised", unit="alerts",
              source=f"{generated}/fatigue_logs_node.parquet")
    b6["caption"] = (
        f"{int(fatigue['fatigue_alert_triggered'].sum())} alerts across "
        f"{b6['readings']:,} readings, summed into {SIGNAL_BUCKETS} buckets of "
        "equal duration."
    )

    # The block model carries two assays. Plotting one of them by name on a
    # screen whose calculator deliberately does not name a metal invites a
    # reader to spend their attention on which commodity this deck is about,
    # which is the wrong question -- the mechanism is reconciliation and it is
    # the same mechanism whatever is in the ore. The percent assay is used
    # because a grade in percent reads as a grade rather than as one metal's
    # convention, and because the mill feed figure elsewhere on the screen is
    # also in percent, so the two are at least in the same units.
    b2 = dict(_histogram(blocks["copper_grade_pct_est"], 24), kind="distribution",
              label="Estimated grade across the block model", unit="%",
              source=f"{generated}/geological_block_models.parquet")
    b2["caption"] = (
        f"{b2['n']:,} block cells by estimated grade, waste included. This is "
        "the model's own spread and not a comparison against mill feed: the "
        "mill only ever sees ore above cut-off, so the two distributions are "
        "not the same population. The block model is spatial, not timed, so "
        "this is a distribution and not a trend."
    )

    below = int((inventory["stock_level"] <= inventory["reorder_point_limit"]).sum())
    b5 = {
        "kind": "share", "label": "SKUs at or below reorder point",
        "part": below, "whole": int(len(inventory)),
        "source": f"{generated}/inventory_levels.parquet",
        "caption": (
            "Inventory is a standing level with no history in these files, so "
            "this is the position today and not a trend."
        ),
    }

    gap = build_gap(telemetry, recovery)

    return {
        "generated_at": _now(),
        "source": f"{generated}/*.parquet",
        "buckets": SIGNAL_BUCKETS,
        "window": {
            "from": str(telemetry["timestamp"].min()),
            "to": str(telemetry["timestamp"].max()),
            "source": telemetry_src,
        },
        "assets": assets,
        "gap": gap,
        "roi": build_roi(gap, recovery),
        "branch_evidence": {"B1": b1, "B2": b2, "B3": b3,
                            "B4": b4, "B5": b5, "B6": b6},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    catalog = build_catalog()
    personas = build_personas(catalog)
    graph = build_graph_from_local()
    facts = build_facts()

    workspace = build_workspace()
    workspace["generated_at"] = _now()

    signals = build_signals()
    # The value screen renders one evidence chart per branch card. A branch with
    # no entry would render an empty card that reads as "no evidence exists",
    # and an entry with no branch would be a chart with nothing to attach to.
    if set(signals["branch_evidence"]) != set(CEO_TREE):
        raise SystemExit(
            f"branch_evidence covers {sorted(signals['branch_evidence'])} but the "
            f"CEO tree has {sorted(CEO_TREE)}. Every branch needs evidence."
        )

    payloads = {"catalog": catalog, "personas": personas,
                "graph": graph, "facts": facts,
                "value_tree": build_value_tree(catalog),
                "workspace": workspace, "signals": signals,
                "benchmarks": build_benchmarks()}
    for name, payload in payloads.items():
        path = args.out / f"{name}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")
        print(f"wrote {path.relative_to(REPO)} ({path.stat().st_size:,} bytes)")

    # The same payloads as one script tag. fetch() is blocked under file://, and
    # someone will open these screens by double-clicking them; a demo that shows
    # an empty page because of an origin rule is a demo that fails in the room.
    bundle = args.out / "bundle.js"
    bundle.write_text(
        "/* Generated by scripts/build_app_data.py. Do not edit. */\n"
        "window.MINING_DATA = " + json.dumps(payloads, sort_keys=False) + ";\n"
    )
    print(f"wrote {bundle.relative_to(REPO)} ({bundle.stat().st_size:,} bytes)")

    # tokens.css has one home, docs/ux/. Copying rather than importing keeps a
    # forked apps/ tree self-contained without giving the design system a
    # second editable copy.
    tokens_src = REPO / "docs" / "ux" / "tokens.css"
    tokens_dst = args.out.parent / "tokens.css"
    tokens_dst.write_text(
        "/* Copied from docs/ux/tokens.css by scripts/build_app_data.py.\n"
        "   Edit the source, not this file. */\n" + tokens_src.read_text()
    )
    print(f"wrote {tokens_dst.relative_to(REPO)} "
          f"({tokens_dst.stat().st_size:,} bytes)")

    print(f"\nagent nodes {catalog['counts']['agent_nodes']}, "
          f"entrypoints {catalog['counts']['entrypoints']}, "
          f"swarms {catalog['counts']['swarms']}, "
          f"HITL {catalog['counts']['hitl_entrypoints']}")
    print(f"personas {len(personas['personas'])}")
    print("leak counts " + ", ".join(
        f"{leak} {n}" for leak, n in catalog["leak_counts"].items()
    ))
    for card in _all_cards():
        cov = card.get("coverage")
        cov_txt = f"{cov['instrumented']} of {cov['total']}" if cov else "no pack"
        print(f"card {card['agent_id']:<8} {card['archetype']:<13} coverage {cov_txt}")
    print(f"formulas {len(workspace['formulas']['registry'])}, "
          f"traversals {len(workspace['traversals'])}, "
          f"models {len(workspace['models'])}, "
          f"approval columns {len(workspace['approval']['fields'])}")
    print(f"signals {len(signals['assets'])} asset series, "
          f"{len(signals['branch_evidence'])} branch evidence entries, "
          f"{signals['buckets']} buckets")
    print(f"benchmarks {len(payloads['benchmarks']['by_id'])} cited, "
          f"{len(payloads['benchmarks']['excluded'])} excluded as unverifiable")
    for row in signals["gap"]["rows"]:
        print(f"gap {row['label']:<24} median {row['median']:>10,.2f} "
              f"p90 {row['p90']:>10,.2f}  +{row['delta_pct']:.1f}%")
    roi = signals["roi"]
    print(f"roi feed grade {roi['feed_grade_pct']}% over "
          f"{roi['feed_grade_days']} days -> {roi['t_per_mt_per_point']:,.0f} t "
          f"contained metal per Mt milled per recovery point")
    for name, info in graph["graphs"].items():
        print(f"graph {name:<14} {info['nodes']:>4} nodes {info['edges']:>4} edges  "
              f"{info['node_types']}")


if __name__ == "__main__":
    main()
