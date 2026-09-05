"""Export the extra JSON the workspace application reads.

Application 1 argues the case; Application 2 is the place a person does the
work, so it has to show *method* — the formula behind a number, the pattern
behind a traversal, the columns behind an approval record. All three already
exist in the deployed code. Retyping any of them for a screen would let the
screen drift from the container, which is the one failure this whole artifact
is built to avoid, so each is lifted off the module that deploys it.

What this file cannot export is what an agent *said*. There are no recorded
responses in this repository — no fixtures, no golden files, no captured
payloads — so the runtime block below states that plainly and the screens
render an explicit not-connected state rather than a plausible transcript.

Imported by scripts/build_app_data.py; not run on its own.
"""
from __future__ import annotations

import json
import pathlib
import re

import yaml

from mining_agents.catalog.definitions import ALL_AGENTS
from mining_agents.tools import request_approval as approval_module
from mining_agents.tools.graph_traverse import TRAVERSALS
from mining_agents.tools.operational_math import _SPECS

REPO = pathlib.Path(__file__).resolve().parents[1]
PROFILE = REPO / "data" / "profile"
GENERATED = REPO / "data" / "generated"
SEMANTICS = REPO / "docs" / "column-semantics.yaml"

# The catalog records that an agent holds operational_math. It does not record
# which of the five formulas that agent calls -- the model chooses at runtime.
# So the only honest attribution is one the agent's own name makes: D27 is the
# "Safety Stock & Reorder Point Calculator" and D28 the "Economic Order
# Quantity Optimiser". Where the name does not say, no claim is made, and the
# screen lists the whole registry as available instead of picking one.
FORMULA_NAMES = {
    "rop": "reorder point",
    "eoq": "economic order quantity",
    "cpk": "process capability",
    "oee": "overall equipment effectiveness",
    "littles_law": "little's law",
}

# The live BigQuery schema, transcribed once at the top of request_approval.py
# where the tool that writes it can be read beside it. SC-4 renders the audit
# record from this, so a column added there reaches the screen without anyone
# editing the screen.
_SCHEMA_LINE = re.compile(r"^ {2}(\w+)\s+(\w+)\s+(REQUIRED|NULLABLE|REPEATED)\s*$")


def _approval_schema() -> dict:
    doc = approval_module.__doc__ or ""
    fields = [
        {"column": m.group(1), "type": m.group(2), "mode": m.group(3)}
        for m in (_SCHEMA_LINE.match(line) for line in doc.splitlines())
        if m
    ]
    if len(fields) != 11:
        raise SystemExit(
            f"parsed {len(fields)} columns out of the agent_approvals schema in "
            "mining_agents/tools/request_approval.py, expected 11. SC-4 renders "
            "this table; a silent parse failure would ship a short one."
        )
    return {
        "table": approval_module.TABLE,
        "fields": fields,
        "pending_decision": "PENDING",
        "pending_principal": approval_module._PENDING_PRINCIPAL,
        # Stated in the module docstring and enforced by the tool: the agent
        # writes PENDING and nothing else. SC-4 is the only writer of APPROVED.
        "rule": (
            "Nothing in the codebase may write APPROVED. The agent writes "
            "decision=PENDING with approver_principal="
            f"{approval_module._PENDING_PRINCIPAL}; only a human acting through "
            "this sheet overwrites both."
        ),
    }


def _holders(predicate) -> list[str]:
    """Entrypoints matching a predicate, in catalog order."""
    return sorted(
        a.agent_id
        for a in ALL_AGENTS
        if a.swarm_role in (None, "coordinator") and predicate(a)
    )


def _formulas() -> dict:
    out = {}
    for key, spec in _SPECS.items():
        needle = FORMULA_NAMES[key]
        out[key] = {
            "name": needle,
            "inputs": list(spec.inputs),
            "expression": spec.expression,
            # Named-in-title agents only; see FORMULA_NAMES.
            "named_by": _holders(
                lambda a, needle=needle: "operational_math" in a.tools
                and needle in a.display_name.lower()
            ),
        }
    return {
        "source": "mining_agents.tools.operational_math",
        "registry": out,
        "agents": _holders(lambda a: "operational_math" in a.tools),
        "note": (
            "The catalog records that an agent holds operational_math, not which "
            "formula it calls -- the model chooses per question. Only agents whose "
            "own display name states the formula are attributed to one."
        ),
    }


def _traversals() -> dict:
    """The traversal patterns, with the agents the catalog grants them to.

    ontology_related is in TRAVERSALS and granted to no agent
    (tests/test_demo_scenarios.py pins that at exactly zero), so it is omitted
    for the same reason Application 1 omits its graph: a workbench offering a
    query no deployed agent can run is offering scenery.
    """
    out = {}
    for name, spec in TRAVERSALS.items():
        agents = sorted(a.agent_id for a in ALL_AGENTS if name in (a.traversals or ()))
        if not agents:
            continue
        columns = re.findall(r"\bAS\s+(\w+)", spec.sql)
        if not columns:
            raise SystemExit(f"no COLUMNS aliases parsed out of {name!r} SQL")
        out[name] = {
            "sql": spec.sql.strip(),
            "params": list(spec.params),
            "columns": columns,
            "tables_read": list(spec.tables_read),
            "agents": agents,
            "entrypoints": _holders(lambda a, n=name: n in (a.traversals or ())),
        }
    return out


def _models() -> dict:
    out: dict[str, dict] = {}
    for agent in ALL_AGENTS:
        for model in getattr(agent, "models", None) or ():
            out.setdefault(model, {"agents": []})["agents"].append(agent.agent_id)
    for spec in out.values():
        spec["agents"].sort()
        spec["entrypoints"] = sorted(
            a.agent_id
            for a in ALL_AGENTS
            if a.agent_id in spec["agents"] and a.swarm_role in (None, "coordinator")
        )
    return out


def _tables() -> dict:
    """Every table the catalog reads, with its schema, its meaning and its gaps.

    Three sources, deliberately kept distinguishable rather than merged into a
    single "available" boolean:

      * data/profile/schemas.json is BigQuery's own schema for all 28 tables,
        captured when the profile was taken. It is what makes the workbench able
        to name a *column* rather than gesture at "the inventory data".
      * data/generated/*.parquet is the current local copy of ten of them. A
        table with a schema but no parquet is queryable in the warehouse and not
        on this machine, which is a different situation from one that does not
        exist, and the screens say which.
      * docs/column-semantics.yaml carries the business meaning of a column,
        and covers seven tables so far. The rest are pending; the screens print
        that rather than paraphrasing a column name back at the reader.
    """
    profile = json.loads((PROFILE / "schemas.json").read_text())["schemas"]
    semantics = yaml.safe_load(SEMANTICS.read_text()) if SEMANTICS.exists() else {}
    local = {p.stem for p in GENERATED.glob("*.parquet")}

    used = sorted({t for a in ALL_AGENTS for t in a.source_tables})
    out = {}
    for qualified in used:
        short = qualified.split(".", 1)[-1]
        schema = profile.get(short)
        meaning = semantics.get(qualified) or {}
        out[qualified] = {
            "table": short,
            "columns": [
                dict(col, meaning=(meaning.get("columns") or {}).get(col["name"]))
                for col in (schema or {}).get("columns", [])
            ],
            "rows_at_profile": (schema or {}).get("num_rows"),
            "partitioning": (schema or {}).get("partitioning"),
            "clustering": (schema or {}).get("clustering"),
            "schema_known": schema is not None,
            "local_parquet": f"data/generated/{short}.parquet" if short in local else None,
            "description": (meaning.get("description") or "").strip() or None,
            "agents": sorted(a.agent_id for a in ALL_AGENTS if qualified in a.source_tables),
        }
    return {
        "source": {
            "schema": "data/profile/schemas.json (BigQuery INFORMATION_SCHEMA capture)",
            "meaning": str(SEMANTICS.relative_to(REPO)),
            "local": "data/generated/*.parquet",
        },
        "documented": sorted(t for t, v in out.items() if v["description"]),
        "undocumented": sorted(t for t, v in out.items() if not v["description"]),
        "tables": out,
    }


def build_workspace() -> dict:
    return {
        "tables": _tables(),
        "formulas": _formulas(),
        "traversals": _traversals(),
        "models": _models(),
        "approval": _approval_schema(),
        # The honest statement of what this build can and cannot produce. Every
        # screen that would otherwise show an agent's own words renders this
        # instead. It is deliberately a single string in one place: if the
        # workspace is later wired to the deployed endpoints, one edit here
        # removes the disclaimer from every screen at once.
        "runtime": {
            "connected": False,
            "reason": (
                "The 52 agents run as Cloud Run services that require a "
                "Google-signed OIDC identity token. This build had no "
                "credentials, and this repository holds no recorded agent "
                "responses to stand in for them."
            ),
            "consequence": (
                "Structure, method and provenance below are the deployed "
                "article. Anything an agent would have generated in its own "
                "words is marked NOT CONNECTED rather than written for it."
            ),
            "proxy_route": "/api/invoke/{agent_id}",
        },
    }
