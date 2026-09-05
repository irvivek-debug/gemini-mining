"""The 100 agent definitions, transcribed from docs/phase-1-prd.md §5.1 and §5.2."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Role = Literal["coordinator", "specialist", "critic"]

#: The PRD's six agent archetypes (Agentic-Mining-PRD.md §9-10 archetype tags).
#: A card's `archetype` must be one of exactly these six — Pydantic enforces
#: membership at construction time via the `Archetype` Literal below, so a
#: typo (or a made-up seventh archetype) raises when the module is imported,
#: not when a screen tries to render it.
ARCHETYPES: tuple[str, ...] = (
    "Sentinel", "Diagnostician", "Optimiser", "Negotiator", "Assurer", "Curator",
)
Archetype = Literal["Sentinel", "Diagnostician", "Optimiser", "Negotiator", "Assurer", "Curator"]

#: The PRD's five leaks in the job map (§5.1): where the five-stage job
#: — Notice, Diagnose, Decide, Act, Prove — breaks today.
LEAKS: tuple[str, ...] = ("Latency", "Blind spot", "Variance", "Coordination", "Assurance")
Leak = Literal["Latency", "Blind spot", "Variance", "Coordination", "Assurance"]

#: The PRD's value-confidence classes (§7.1). Class A is cash-verifiable,
#: Class B is metric-verifiable against a signed baseline, Class C is
#: risk-adjusted and funds nothing (report only, never booked).
EVIDENCE_CLASSES: tuple[str, ...] = ("A", "B", "C")
EvidenceClass = Literal["A", "B", "C"]


class FinancialLine(BaseModel):
    """One line an agent's work can move, at one evidence class.

    Evidence class is modelled per line, not per agent: PRD §7 is explicit
    that a single agent can carry a Class A line (a cash-verifiable recovery)
    alongside a Class B line (a metric moving against a signed baseline) —
    collapsing evidence class onto the agent would force one class to speak
    for both.
    """
    line: str
    evidence_class: EvidenceClass


#: The exact source citations from the plan's researched benchmark table
#: (docs/plans/2026-08-18-sales-ready-workspace.md, "The
#: benchmark set", researched 2026-08-18). A `MetricImpact.source` must be
#: one of these strings, verbatim — not a paraphrase, not a firm name typed
#: from memory. That table is the single citable authority for every
#: percentage on a card; a source that doesn't match it exactly is either a
#: typo or an invented number, and either way it must not reach a client
#: deck. (The value pool / "no material value" / "at scale" rows are
#: portfolio-level, not per-agent, so they are cited on the framing page,
#: not here — their sources are omitted from this set on purpose.)
BENCHMARK_SOURCES: tuple[str, ...] = (
    "BCG, mature AI sites in mining & metals",
    "McKinsey, metals & mining",
    "BCG",
    "McKinsey",
    "McKinsey / Deloitte, predictive maintenance",
    "industry contract-management research",
)


class MetricImpact(BaseModel):
    """A quantified, sourced range for how an agent's work is expected to
    move one operational metric.

    This is an INDUSTRY BENCHMARK RANGE from published research — BCG,
    McKinsey, Deloitte, and named contract-management research — never a
    number measured on this site's data. Nothing here is computed from the
    demo dataset; `source` exists precisely so a reader can tell an industry
    range apart from a site-measured figure. An unattributed percentage is
    the line that ends a CFO conversation, so `source` is validated against
    the plan's researched benchmark table (`BENCHMARK_SOURCES`) rather than
    merely required to be non-empty — a missing OR a fabricated/mistyped
    citation both raise at import, the same way a made-up archetype does.
    """
    metric: str
    direction: Literal["increase", "decrease"]
    low_pct: float
    high_pct: float
    source: str

    @field_validator("metric")
    @classmethod
    def _metric_is_named(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("a metric impact must name a metric")
        return v

    @field_validator("source")
    @classmethod
    def _source_is_a_researched_benchmark(cls, v: str) -> str:
        if v not in BENCHMARK_SOURCES:
            raise ValueError(
                f"{v!r} is not one of the plan's researched benchmark "
                "sources (BENCHMARK_SOURCES) — every impact must cite a "
                "real, checkable source naming the firm or study behind "
                "it, not an invented, paraphrased, or unattributed one"
            )
        return v

    @model_validator(mode="after")
    def _low_at_most_high(self) -> "MetricImpact":
        if self.low_pct > self.high_pct:
            raise ValueError(
                f"low_pct ({self.low_pct}) must be <= high_pct ({self.high_pct})"
            )
        return self


class AgentCard(BaseModel):
    """The business-framing card rendered on a persona page (design §2).

    AUTHORITY IS DECLARED, NOT ENFORCED. This build has no authority engine.
    `authority` is a label the card displays to a reader — it is never read
    by any tool, gate, or approval path in this codebase, and nothing here
    should be taken to mean a future reader can look up "L1" and expect the
    platform to have actually restricted what the agent did. If an authority
    engine is ever built, this field becomes its input; today it is prose.

    Coverage (how many of a pack's drivers are instrumented) deliberately
    does NOT live here — it is computed from the pack file at export time
    (see design §2, "Coverage is the load-bearing row"), never authored by
    hand, so a card cannot silently overclaim what its pack actually covers.

    `metric_impacts` is deliberately allowed to be empty. It carries
    published, sourced benchmark ranges for the operational metrics this
    agent's work plausibly moves — not a measurement, an industry range
    (see `MetricImpact`). An agent whose work has no defensible published
    benchmark (e.g. a Class C, risk-adjusted safety card, or a claim with no
    published baseline) must carry none rather than borrow a number from an
    adjacent agent's benchmark to avoid looking empty; a stretched figure is
    worse than a short list.
    """
    decision: str
    leaks: list[Leak]
    archetype: Archetype
    authority: str
    financial_lines: list[FinancialLine]
    honest_limit: str
    pack: str | None = None
    metric_impacts: list[MetricImpact] = Field(default_factory=list)

    @field_validator("leaks")
    @classmethod
    def _at_least_one_leak(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("a card must name at least one leak")
        return v

    @field_validator("financial_lines")
    @classmethod
    def _at_least_one_financial_line(cls, v: list[FinancialLine]) -> list[FinancialLine]:
        if not v:
            raise ValueError("a card must name at least one financial line")
        return v


class AgentDef(BaseModel):
    agent_id: str
    display_name: str
    pattern: Literal["A", "B"]
    swarm_id: str | None = None
    swarm_role: Role | None = None
    apqc_code: str
    persona: str
    value_branch: str
    model_tier: Literal["reasoning", "balanced"]
    hitl_required: bool = False
    source_tables: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    traversals: list[str] = Field(default_factory=list)
    models: list[str] = Field(default_factory=list)
    card: AgentCard | None = None


@dataclass(frozen=True)
class SwarmDef:
    swarm_id: str
    display_name: str
    coordinator: AgentDef
    specialists: tuple[AgentDef, AgentDef, AgentDef]
    critic: AgentDef

    @property
    def agents(self) -> list[AgentDef]:
        return [self.coordinator, *self.specialists, self.critic]


def _tier(role: Role | None) -> str:
    return "reasoning" if role in ("coordinator", "critic") else "balanced"


def _a(agent_id: str, display_name: str, swarm_id: str, role: Role, *,
       apqc: str, persona: str, branch: str, hitl: bool = False,
       tables: list[str], tools: list[str] = (), traversals: list[str] = (),
       models: list[str] = (), card: AgentCard | None = None) -> AgentDef:
    return AgentDef(
        agent_id=agent_id, display_name=display_name, pattern="A",
        swarm_id=swarm_id, swarm_role=role, apqc_code=apqc, persona=persona,
        value_branch=branch, model_tier=_tier(role), hitl_required=hitl,
        source_tables=tables, tools=list(tools), traversals=list(traversals),
        models=list(models), card=card,
    )


def _b(agent_id: str, display_name: str, *, apqc: str, persona: str, branch: str,
       hitl: bool = False, tables: list[str], tools: list[str] = (),
       traversals: list[str] = (), models: list[str] = ()) -> AgentDef:
    return AgentDef(
        agent_id=agent_id, display_name=display_name, pattern="B",
        swarm_id=None, swarm_role=None, apqc_code=apqc, persona=persona,
        value_branch=branch, model_tier="balanced", hitl_required=hitl,
        source_tables=tables, tools=list(tools), traversals=list(traversals),
        models=list(models),
    )


# ---------------------------------------------------------------------------
# S01 — Cascading Failure Impact & Recovery
# Data: telemetry_stream, asset_dependencies, MiningAssetGraph,
#       downtime_regression_model*, maintenance_logs
# ---------------------------------------------------------------------------
S01 = SwarmDef(
    swarm_id="S01",
    display_name="Cascading Failure Impact & Recovery",
    coordinator=_a(
        "S01", "Cascading Failure Impact & Recovery Coordinator", "S01",
        "coordinator", apqc="11.0.3", persona="P1", branch="asset_reliability",
        hitl=True,
        tables=[
            "mining_data.telemetry_stream",
            "mining_data.asset_dependencies",
            "mining_data.assets",
            "mining_data.maintenance_logs",
        ],
        tools=["bq_query", "graph_traverse", "request_approval"],
        traversals=["blast_radius"],
        card=AgentCard(
            decision="What fails next, when to take it, and exactly what the "
                     "work order should say.",
            leaks=["Blind spot", "Latency"],
            archetype="Diagnostician",
            authority="L1 — Recommend",
            financial_lines=[
                FinancialLine(line="unplanned repair cost → C1 cash cost",
                               evidence_class="B"),
            ],
            honest_limit="Data-driven remaining-useful-life estimation needs "
                          "run-to-failure data, and well-maintained machines "
                          "are protected from failing by definition — this "
                          "starts physics- and rule-based, and earns the "
                          "data over time.",
            pack="p1-reliability.yaml",
            metric_impacts=[
                MetricImpact(
                    metric="Unplanned downtime",
                    direction="decrease",
                    low_pct=30, high_pct=50,
                    source="McKinsey / Deloitte, predictive maintenance",
                ),
            ],
        ),
    ),
    specialists=(
        _a("S01-SP1", "Telemetry Anomaly Detector", "S01", "specialist",
           apqc="11.0.3", persona="P1", branch="asset_reliability",
           tables=["mining_data.telemetry_stream"],
           tools=["bq_query"]),
        _a("S01-SP2", "Dependency Blast-Radius Tracer", "S01", "specialist",
           apqc="11.0.3", persona="P1", branch="asset_reliability",
           tables=["mining_data.asset_dependencies", "mining_data.assets"],
           tools=["graph_traverse"], traversals=["blast_radius"]),
        _a("S01-SP3", "Downtime Duration Forecaster", "S01", "specialist",
           apqc="11.0.3", persona="P1", branch="asset_reliability",
           tables=[
               "mining_data.maintenance_logs",
               "mining_data.erp_work_orders",
               "mining_data.assets",
               "mining_data.telemetry_stream",
           ],
           tools=["bq_query", "bqml_predict", "method_lookup", "run_diagnostic", "doc_search"],
           models=["downtime_regression_model"]),
    ),
    critic=_a(
        "S01-CRITIC", "Recovery Plan Critic", "S01", "critic",
        apqc="11.0.3", persona="P1", branch="asset_reliability",
        tables=["mining_data.maintenance_logs"],
        tools=["bq_query"],
    ),
)

# ---------------------------------------------------------------------------
# S02 — Planned Shutdown Readiness
# Data: erp_work_orders, work_order_parts_edge, inventory_levels,
#       MiningSupplyChainGraph
# ---------------------------------------------------------------------------
S02 = SwarmDef(
    swarm_id="S02",
    display_name="Planned Shutdown Readiness",
    coordinator=_a(
        "S02", "Planned Shutdown Readiness Coordinator", "S02",
        "coordinator", apqc="11.0.3 / 4.1.2", persona="P2",
        branch="maintenance_execution", hitl=True,
        tables=[
            "mining_data.erp_work_orders",
            "mining_data.work_order_parts_edge",
            "mining_data.inventory_levels",
            "mining_data.assets",
        ],
        tools=["bq_query", "graph_traverse", "request_approval"],
        traversals=["stockout_exposure"],
        card=AgentCard(
            decision="Which work orders are ready for the shutdown window, "
                     "and whether the parts and lead time on hand actually "
                     "support committing to it.",
            leaks=["Blind spot", "Latency"],
            archetype="Diagnostician",
            authority="L1 — Recommend",
            financial_lines=[
                FinancialLine(
                    line="maintenance cost per completed work order → "
                         "maintenance cost as % of opex",
                    evidence_class="B",
                ),
            ],
            honest_limit="Work order records carry no planned date or due "
                          "date field, so schedule compliance against a plan "
                          "cannot be evidenced from them — only realised "
                          "cost against priority and backlog age can be.",
            pack="p2-planner.yaml",
            metric_impacts=[
                MetricImpact(
                    metric="Maintenance cost",
                    direction="decrease",
                    low_pct=18, high_pct=25,
                    source="McKinsey",
                ),
            ],
        ),
    ),
    specialists=(
        _a("S02-SP1", "Work Order Bundler", "S02", "specialist",
           apqc="11.0.3 / 4.1.2", persona="P2", branch="maintenance_execution",
           tables=["mining_data.erp_work_orders", "mining_data.work_order_parts_edge"],
           tools=["bq_query"]),
        _a("S02-SP2", "Parts Availability Checker", "S02", "specialist",
           apqc="11.0.3 / 4.1.2", persona="P2", branch="maintenance_execution",
           tables=[
               "mining_data.inventory_levels",
               "mining_data.erp_work_orders",
               "mining_data.work_order_parts_edge",
               "mining_data.assets",
           ],
           tools=["graph_traverse", "bq_query", "method_lookup", "run_diagnostic", "doc_search"],
           traversals=["stockout_exposure"]),
        _a("S02-SP3", "Lead-Time Feasibility Analyst", "S02", "specialist",
           apqc="11.0.3 / 4.1.2", persona="P2", branch="maintenance_execution",
           tables=["mining_data.inventory_levels", "mining_data.erp_work_orders"],
           tools=["bq_query"]),
    ),
    critic=_a(
        "S02-CRITIC", "Readiness Critic", "S02", "critic",
        apqc="11.0.3 / 4.1.2", persona="P2", branch="maintenance_execution",
        tables=["mining_data.erp_work_orders", "mining_data.inventory_levels"],
        tools=["bq_query"],
    ),
)

# ---------------------------------------------------------------------------
# S03 — Fleet Reliability & Availability
# Data: fleet_vehicles, maintenance_logs, erp_work_orders
# ---------------------------------------------------------------------------
S03 = SwarmDef(
    swarm_id="S03",
    display_name="Fleet Reliability & Availability",
    coordinator=_a(
        "S03", "Fleet Reliability & Availability Coordinator", "S03",
        "coordinator", apqc="11.0.3 / 4.3.1", persona="P1",
        branch="asset_reliability", hitl=False,
        tables=[
            "mining_data.fleet_vehicles",
            "mining_data.maintenance_logs",
            "mining_data.erp_work_orders",
        ],
        tools=["bq_query"],
        card=AgentCard(
            decision="Which failures are recoverable, and whether the "
                     "evidence supports the claim.",
            leaks=["Blind spot", "Latency"],
            archetype="Negotiator",
            authority="L1 — Recommend",
            financial_lines=[
                FinancialLine(
                    line="warranty and OEM claims recovery → other income "
                         "/ cost recovery",
                    evidence_class="A",
                ),
            ],
            honest_limit="There is no published data on unclaimed warranty "
                          "value in heavy industry; the baseline must come "
                          "from the site's own claims history, and any "
                          "vendor-quoted figure is unsourceable.",
            pack="agt13-warranty.yaml",
            # No metric_impacts: this card's own honest_limit says there is
            # no published benchmark for unclaimed warranty/OEM claims value
            # in heavy industry. Nothing in the plan's benchmark table prices
            # warranty recovery, and fleet uptime figures (unplanned
            # downtime, maintenance cost) belong to S01/S02's predictive-
            # maintenance work, not to this agent's claims-recovery work —
            # attaching either here would be exactly the borrowed-figure
            # move the plan rules out.
        ),
    ),
    specialists=(
        _a("S03-SP1", "Vehicle Health Screener", "S03", "specialist",
           apqc="11.0.3 / 4.3.1", persona="P1", branch="asset_reliability",
           tables=["mining_data.fleet_vehicles"],
           tools=["bq_query"]),
        _a("S03-SP2", "Duty-Cycle Analyst", "S03", "specialist",
           apqc="11.0.3 / 4.3.1", persona="P1", branch="asset_reliability",
           tables=["mining_data.fleet_vehicles", "mining_data.maintenance_logs"],
           tools=["bq_query"]),
        _a("S03-SP3", "Maintenance History Correlator", "S03", "specialist",
           apqc="11.0.3 / 4.3.1", persona="P1", branch="asset_reliability",
           tables=["mining_data.maintenance_logs", "mining_data.erp_work_orders"],
           tools=["bq_query"]),
    ),
    critic=_a(
        "S03-CRITIC", "Availability Forecast Critic", "S03", "critic",
        apqc="11.0.3 / 4.3.1", persona="P1", branch="asset_reliability",
        tables=["mining_data.fleet_vehicles", "mining_data.maintenance_logs"],
        tools=["bq_query"],
    ),
)

# ---------------------------------------------------------------------------
# S04 — Shift Dispatch Re-plan
# Data: haulage_routes, operator_vehicle_assignments, operators_node,
#       fleet_vehicles
# ---------------------------------------------------------------------------
S04 = SwarmDef(
    swarm_id="S04",
    display_name="Shift Dispatch Re-plan",
    coordinator=_a(
        "S04", "Shift Dispatch Re-plan Coordinator", "S04",
        "coordinator", apqc="4.3.1", persona="P7",
        branch="mine_ops", hitl=True,
        tables=[
            "mining_data.haulage_routes",
            "mining_data.operator_vehicle_assignments",
            "mining_data.operators_node",
            "mining_data.fleet_vehicles",
        ],
        tools=["bq_query", "request_approval"],
        card=AgentCard(
            decision="Which route or load setpoint best serves the shift's "
                     "movement-rate objective when two parts of the "
                     "operation want incompatible things — a route that is "
                     "short but congested against one that is long but "
                     "clear.",
            leaks=["Latency", "Coordination"],
            archetype="Optimiser",
            authority="L1 — Recommend",
            financial_lines=[
                FinancialLine(
                    line="movement rate lost to route and load mismatch → "
                         "C1 cash cost",
                    evidence_class="B",
                ),
            ],
            honest_limit="Congestion is compared against each route's own "
                          "baseline, not a fleet-wide norm, and no table "
                          "links a haul cycle to the operator who drove it "
                          "at usable scale — operator-behaviour and "
                          "breakdown-reassignment findings are reported as "
                          "not instrumented rather than inferred.",
            pack="p7-mine-controller.yaml",
            # No metric_impacts, deliberately. The plan's benchmark table's
            # "Throughput" rows describe mature-AI-site throughput gains
            # generally and are already the S07 (crusher-mill) card's claim;
            # dispatch/haul optimisation moves a different lever toward the
            # same aggregate outcome, and reusing S07's exact cited range
            # here — rather than a range this agent's own mechanism has
            # earned — is the borrowed-figure move the plan rules out. No
            # row in the table prices fleet movement rate or haul dispatch
            # specifically, so an empty list is the honest answer, same as
            # S03 and S05.
        ),
    ),
    specialists=(
        _a("S04-SP1", "Cycle Time Variance Analyst", "S04", "specialist",
           apqc="4.3.1", persona="P7", branch="mine_ops",
           tables=["mining_data.haulage_routes"],
           tools=["bq_query", "operational_math"]),
        _a("S04-SP2", "Route Congestion Modeller", "S04", "specialist",
           apqc="4.3.1", persona="P7", branch="mine_ops",
           tables=["mining_data.haulage_routes"],
           tools=["bq_query"]),
        _a("S04-SP3", "Operator Assignment Fit", "S04", "specialist",
           apqc="4.3.1", persona="P7", branch="mine_ops",
           tables=[
               "mining_data.operator_vehicle_assignments",
               "mining_data.operators_node",
               "mining_data.fleet_vehicles",
           ],
           tools=["bq_query"]),
    ),
    critic=_a(
        "S04-CRITIC", "Dispatch Plan Critic", "S04", "critic",
        apqc="4.3.1", persona="P7", branch="mine_ops",
        tables=[
            "mining_data.haulage_routes",
            "mining_data.operator_vehicle_assignments",
            "mining_data.fleet_vehicles",
        ],
        tools=["bq_query"],
    ),
)

# ---------------------------------------------------------------------------
# S05 — Autonomous Haulage Safety Interlock
# Data: safety_incidents, incident_involvements, biometric_fatigue_logs,
#       radio_communications, MiningOperationsSafetyGraph
# ---------------------------------------------------------------------------
S05 = SwarmDef(
    swarm_id="S05",
    display_name="Autonomous Haulage Safety Interlock",
    coordinator=_a(
        "S05", "Autonomous Haulage Safety Interlock Coordinator", "S05",
        "coordinator", apqc="4.3.1 / 9.1.2", persona="P3",
        branch="safety", hitl=True,
        tables=[
            "mining_data.safety_incidents",
            "mining_data.incident_involvements",
            "mining_data.biometric_fatigue_logs",
            "mining_data.radio_communications",
            "mining_data.fatigue_logs_node",
            "mining_data.operators_node",
            "mining_data.operator_vehicle_assignments",
            "mining_data.fleet_vehicles",
        ],
        tools=["bq_query", "graph_traverse", "request_approval"],
        traversals=["fatigue_to_incident"],
        card=AgentCard(
            decision="Whether the evidence in front of an interlock "
                     "decision — proximity history, fatigue signal, and "
                     "radio traffic — actually supports it.",
            leaks=["Assurance"],
            archetype="Diagnostician",
            authority="L1 — Recommend",
            financial_lines=[
                FinancialLine(
                    line="severity-weighted incident exposure → risk "
                         "position (avoided loss)",
                    evidence_class="C",
                ),
            ],
            honest_limit="Attributing an incident to a fatigue signal "
                          "requires both an operator link and sub-day "
                          "timestamp resolution across the incident and "
                          "biometric records; where either is missing, the "
                          "correlation is reported as not instrumented "
                          "rather than inferred.",
            pack="p3-hse.yaml",
            # No metric_impacts, deliberately. This is the HSE card: its one
            # financial line is Class C, risk-adjusted, and reports avoided
            # exposure — it funds nothing and is never booked. None of the
            # plan's researched benchmarks price safety-incident avoidance
            # or interlock-evidence quality; "Unplanned downtime" and
            # "Maintenance cost" are asset-reliability figures (S01/S02),
            # not safety figures, and stretching either onto a safety agent
            # to avoid an empty list is the exact move the plan forbids. An
            # empty list is the honest answer here.
        ),
    ),
    specialists=(
        _a("S05-SP1", "Proximity & Incident History Screener", "S05", "specialist",
           apqc="4.3.1 / 9.1.2", persona="P3", branch="safety",
           tables=[
               "mining_data.safety_incidents",
               "mining_data.incident_involvements",
           ],
           tools=["bq_query"]),
        _a("S05-SP2", "Operator Fatigue Cross-Check", "S05", "specialist",
           apqc="4.3.1 / 9.1.2", persona="P3", branch="safety",
           tables=[
               "mining_data.biometric_fatigue_logs",
               "mining_data.fatigue_logs_node",
               "mining_data.operators_node",
               "mining_data.operator_vehicle_assignments",
               "mining_data.fleet_vehicles",
               "mining_data.incident_involvements",
               "mining_data.safety_incidents",
               "mining_data.radio_communications",
           ],
           tools=["graph_traverse", "bq_query", "method_lookup", "run_diagnostic", "doc_search"],
           traversals=["fatigue_to_incident"]),
        _a("S05-SP3", "Radio Emergency Listener", "S05", "specialist",
           apqc="4.3.1 / 9.1.2", persona="P3", branch="safety",
           tables=["mining_data.radio_communications"],
           tools=["bq_query"]),
    ),
    critic=_a(
        "S05-CRITIC", "Interlock Critic", "S05", "critic",
        apqc="4.3.1 / 9.1.2", persona="P3", branch="safety",
        tables=[
            "mining_data.safety_incidents",
            "mining_data.biometric_fatigue_logs",
            "mining_data.radio_communications",
        ],
        tools=["bq_query"],
    ),
)

# ---------------------------------------------------------------------------
# S06 — Grade-to-Recovery Reconciliation
# Data: drill_assay_logs, geological_block_models, metallurgical_recovery
# ---------------------------------------------------------------------------
S06 = SwarmDef(
    swarm_id="S06",
    display_name="Grade-to-Recovery Reconciliation",
    coordinator=_a(
        "S06", "Grade-to-Recovery Reconciliation Coordinator", "S06",
        "coordinator", apqc="2.0.1 / 4.2.2", persona="P5",
        branch="geology", hitl=False,
        tables=[
            "mining_data.drill_assay_logs",
            "mining_data.geological_block_models",
            "mining_data.metallurgical_recovery",
        ],
        tools=["bq_query"],
        card=AgentCard(
            decision="Whether the resource model, the grade-control model, "
                     "the pit and the mill agree on contained metal — and "
                     "if not, which one is wrong.",
            leaks=["Latency", "Variance"],
            archetype="Diagnostician",
            authority="L1 — Recommend",
            financial_lines=[
                FinancialLine(
                    line="contained-metal variance between block model and "
                         "realised grade → reserve confidence",
                    evidence_class="B",
                ),
            ],
            honest_limit="The assay-to-block pairing is a spatial "
                          "approximation at a declared search radius; the "
                          "reconciliation is evidence about the paired "
                          "subset only, and the unpaired population may "
                          "differ systematically from it.",
            pack="p5-geologist.yaml",
            metric_impacts=[
                MetricImpact(
                    metric="Mineral recovery",
                    direction="increase",
                    low_pct=1, high_pct=3,
                    source="McKinsey",
                ),
            ],
        ),
    ),
    specialists=(
        _a("S06-SP1", "Assay-to-Block Variance Analyst", "S06", "specialist",
           apqc="2.0.1 / 4.2.2", persona="P5", branch="geology",
           tables=[
               "mining_data.drill_assay_logs",
               "mining_data.geological_block_models",
               "mining_data.drill_holes",
               "mining_data.metallurgical_recovery",
           ],
           tools=["bq_query", "method_lookup", "run_diagnostic", "doc_search"]),
        _a("S06-SP2", "Delivered Feed Grade Tracer", "S06", "specialist",
           apqc="2.0.1 / 4.2.2", persona="P5", branch="geology",
           tables=["mining_data.drill_assay_logs", "mining_data.metallurgical_recovery"],
           tools=["bq_query"]),
        _a("S06-SP3", "Recovery Attribution Analyst", "S06", "specialist",
           apqc="2.0.1 / 4.2.2", persona="P5", branch="geology",
           tables=["mining_data.metallurgical_recovery", "mining_data.geological_block_models"],
           tools=["bq_query"]),
    ),
    critic=_a(
        "S06-CRITIC", "Reconciliation Critic", "S06", "critic",
        apqc="2.0.1 / 4.2.2", persona="P5", branch="geology",
        tables=["mining_data.drill_assay_logs", "mining_data.metallurgical_recovery"],
        tools=["bq_query"],
    ),
)

# ---------------------------------------------------------------------------
# S07 — Crusher–Mill Throughput Balance
# Data: crusher_states, telemetry_stream (MILL-01), metallurgical_recovery
# ---------------------------------------------------------------------------
S07 = SwarmDef(
    swarm_id="S07",
    display_name="Crusher–Mill Throughput Balance",
    coordinator=_a(
        "S07", "Crusher–Mill Throughput Balance Coordinator", "S07",
        "coordinator", apqc="4.2.2 / 11.0.3", persona="P6",
        branch="processing", hitl=True,
        tables=[
            "mining_data.crusher_states",
            "mining_data.telemetry_stream",
            "mining_data.metallurgical_recovery",
        ],
        tools=["bq_query", "operational_math", "request_approval"],
        card=AgentCard(
            decision="Whether the crusher setting or feed variability is "
                     "costing recovered contained metal, and by how much.",
            leaks=["Latency", "Variance"],
            archetype="Diagnostician",
            authority="L1 — Recommend",
            financial_lines=[
                FinancialLine(
                    line="unit cost per tonne of contained metal → C1 cash "
                         "cost",
                    evidence_class="B",
                ),
            ],
            honest_limit="Torque and throughput figures bound the daily "
                          "mean only; a recommended setting change must "
                          "still be checked against the instantaneous alarm "
                          "limit before it is applied.",
            pack="p6-metallurgist.yaml",
            metric_impacts=[
                MetricImpact(
                    metric="Throughput",
                    direction="increase",
                    low_pct=2, high_pct=5,
                    source="BCG, mature AI sites in mining & metals",
                ),
                MetricImpact(
                    metric="Throughput",
                    direction="increase",
                    low_pct=4, high_pct=8,
                    source="McKinsey, metals & mining",
                ),
                MetricImpact(
                    metric="Mineral recovery",
                    direction="increase",
                    low_pct=1, high_pct=3,
                    source="McKinsey",
                ),
            ],
        ),
    ),
    specialists=(
        _a("S07-SP1", "Crusher Setting Analyst", "S07", "specialist",
           apqc="4.2.2 / 11.0.3", persona="P6", branch="processing",
           tables=["mining_data.crusher_states"],
           tools=["bq_query"]),
        _a("S07-SP2", "Mill Load Analyst", "S07", "specialist",
           apqc="4.2.2 / 11.0.3", persona="P6", branch="processing",
           tables=["mining_data.telemetry_stream"],
           tools=["bq_query"]),
        _a("S07-SP3", "Recovery Sensitivity Modeller", "S07", "specialist",
           apqc="4.2.2 / 11.0.3", persona="P6", branch="processing",
           tables=["mining_data.metallurgical_recovery", "mining_data.crusher_states"],
           tools=["bq_query", "method_lookup", "run_diagnostic", "doc_search"]),
    ),
    critic=_a(
        "S07-CRITIC", "Setpoint Safety Critic", "S07", "critic",
        apqc="4.2.2 / 11.0.3", persona="P6", branch="processing",
        tables=["mining_data.crusher_states", "mining_data.metallurgical_recovery"],
        tools=["bq_query", "operational_math", "doc_search"],
    ),
)

# ---------------------------------------------------------------------------
# S08 — Stockout-to-Work-Order Impact
# Data: inventory_levels, MiningSupplyChainGraph, erp_work_orders,
#       inventory_impact_model
# ---------------------------------------------------------------------------
S08 = SwarmDef(
    swarm_id="S08",
    display_name="Stockout-to-Work-Order Impact",
    coordinator=_a(
        "S08", "Stockout-to-Work-Order Impact Coordinator", "S08",
        "coordinator", apqc="4.1.2 / 11.0.3", persona="P4",
        branch="supply_chain", hitl=True,
        tables=[
            "mining_data.inventory_levels",
            "mining_data.erp_work_orders",
            "mining_data.work_order_parts_edge",
            "mining_data.assets",
        ],
        tools=["bq_query", "graph_traverse", "request_approval"],
        traversals=["stockout_exposure"],
    ),
    specialists=(
        _a("S08-SP1", "Below-ROP Screener", "S08", "specialist",
           apqc="4.1.2 / 11.0.3", persona="P4", branch="supply_chain",
           tables=["mining_data.inventory_levels"],
           tools=["bq_query"]),
        _a("S08-SP2", "Work Order Exposure Tracer", "S08", "specialist",
           apqc="4.1.2 / 11.0.3", persona="P4", branch="supply_chain",
           tables=[
               "mining_data.inventory_levels",
               "mining_data.erp_work_orders",
               "mining_data.work_order_parts_edge",
               "mining_data.assets",
           ],
           tools=["graph_traverse"], traversals=["stockout_exposure"]),
        _a("S08-SP3", "Downtime Cost Modeller", "S08", "specialist",
           apqc="4.1.2 / 11.0.3", persona="P4", branch="supply_chain",
           tables=[
               "mining_data.inventory_levels",
               "mining_data.erp_work_orders",
           ],
           tools=["bq_query", "bqml_predict"],
           models=["inventory_impact_model"]),
    ),
    critic=_a(
        "S08-CRITIC", "Stocking Critic", "S08", "critic",
        apqc="4.1.2 / 11.0.3", persona="P4", branch="supply_chain",
        tables=["mining_data.inventory_levels", "mining_data.erp_work_orders"],
        tools=["bq_query"],
    ),
)

# ---------------------------------------------------------------------------
# S09 — RFP & Bid Award Evaluation
# Data: procurement_bids, rfp_items, bid_parts_edge, inventory_levels
# ---------------------------------------------------------------------------
S09 = SwarmDef(
    swarm_id="S09",
    display_name="RFP & Bid Award Evaluation",
    coordinator=_a(
        "S09", "RFP & Bid Award Evaluation Coordinator", "S09",
        "coordinator", apqc="5.2.1", persona="P4",
        branch="procurement", hitl=True,
        tables=[
            "mining_data.procurement_bids",
            "mining_data.rfp_items",
            "mining_data.bid_parts_edge",
            "mining_data.inventory_levels",
        ],
        tools=["bq_query", "request_approval"],
        card=AgentCard(
            decision="Whether this transaction matches the terms of its "
                     "governing contract.",
            leaks=["Coordination"],
            archetype="Negotiator",
            authority="L1 — Recommend",
            financial_lines=[
                FinancialLine(
                    line="post-signature contract leakage recovered → C1 "
                         "cash cost",
                    evidence_class="A",
                ),
            ],
            honest_limit="The widely quoted \"9.2% contract value leakage\" "
                          "figure is a misattribution: the source study "
                          "found that good contract management could "
                          "improve profitability by roughly 9% of annual "
                          "revenue — an opportunity figure, not a leakage "
                          "rate — and it is not used here.",
            pack="agt14-contract-integrity.yaml",
            metric_impacts=[
                # Deliberately NOT the "9.2% leakage" figure disclaimed
                # above — this is the distinct, defensible RECOVERY figure
                # from the plan's benchmark table.
                MetricImpact(
                    metric="Contract value recovered",
                    direction="increase",
                    low_pct=3, high_pct=5,
                    source="industry contract-management research",
                ),
            ],
        ),
    ),
    specialists=(
        _a("S09-SP1", "Bid Compliance Checker", "S09", "specialist",
           apqc="5.2.1", persona="P4", branch="procurement",
           tables=["mining_data.procurement_bids", "mining_data.rfp_items"],
           tools=["bq_query"]),
        _a("S09-SP2", "Technical Scoring Analyst", "S09", "specialist",
           apqc="5.2.1", persona="P4", branch="procurement",
           tables=[
               "mining_data.procurement_bids",
               "mining_data.rfp_items",
               "mining_data.bid_parts_edge",
           ],
           tools=["bq_query"]),
        _a("S09-SP3", "Cost & Spend Anomaly Analyst", "S09", "specialist",
           apqc="5.2.1", persona="P4", branch="procurement",
           tables=[
               "mining_data.procurement_bids",
               "mining_data.inventory_levels",
           ],
           tools=["bq_query"]),
    ),
    critic=_a(
        "S09-CRITIC", "Award Critic", "S09", "critic",
        apqc="5.2.1", persona="P4", branch="procurement",
        tables=[
            "mining_data.procurement_bids",
            "mining_data.rfp_items",
            "mining_data.bid_parts_edge",
        ],
        tools=["bq_query"],
    ),
)

# ---------------------------------------------------------------------------
# S10 — Fatigue Intervention & Stand-down
# Data: biometric_fatigue_logs, operator_vehicle_assignments, safety_model
# ---------------------------------------------------------------------------
S10 = SwarmDef(
    swarm_id="S10",
    display_name="Fatigue Intervention & Stand-down",
    coordinator=_a(
        "S10", "Fatigue Intervention & Stand-down Coordinator", "S10",
        "coordinator", apqc="9.1.2 / 4.3.1", persona="P3",
        branch="safety", hitl=True,
        tables=[
            "mining_data.biometric_fatigue_logs",
            "mining_data.operator_vehicle_assignments",
        ],
        tools=["bq_query", "bqml_predict", "request_approval"],
        models=["safety_model"],
    ),
    specialists=(
        _a("S10-SP1", "Biometric Fatigue Scorer", "S10", "specialist",
           apqc="9.1.2 / 4.3.1", persona="P3", branch="safety",
           tables=["mining_data.biometric_fatigue_logs"],
           tools=["bq_query", "bqml_predict"],
           models=["safety_model"]),
        _a("S10-SP2", "Microsleep Event Escalator", "S10", "specialist",
           apqc="9.1.2 / 4.3.1", persona="P3", branch="safety",
           tables=["mining_data.biometric_fatigue_logs"],
           tools=["bq_query"]),
        _a("S10-SP3", "Shift Coverage Impact Analyst", "S10", "specialist",
           apqc="9.1.2 / 4.3.1", persona="P3", branch="safety",
           tables=[
               "mining_data.operator_vehicle_assignments",
               "mining_data.biometric_fatigue_logs",
           ],
           tools=["bq_query"]),
    ),
    critic=_a(
        "S10-CRITIC", "Intervention Critic", "S10", "critic",
        apqc="9.1.2 / 4.3.1", persona="P3", branch="safety",
        tables=["mining_data.biometric_fatigue_logs", "mining_data.operator_vehicle_assignments"],
        tools=["bq_query"],
    ),
)

# ---------------------------------------------------------------------------
# S11 — Incident Investigation & Corroboration
# Data: safety_incidents, incident_involvements, radio_communications,
#       MiningOperationsSafetyGraph
# ---------------------------------------------------------------------------
S11 = SwarmDef(
    swarm_id="S11",
    display_name="Incident Investigation & Corroboration",
    coordinator=_a(
        "S11", "Incident Investigation & Corroboration Coordinator", "S11",
        "coordinator", apqc="9.1.2", persona="P3",
        branch="safety", hitl=True,
        tables=[
            "mining_data.safety_incidents",
            "mining_data.incident_involvements",
            "mining_data.radio_communications",
            "mining_data.fatigue_logs_node",
            "mining_data.operators_node",
            "mining_data.operator_vehicle_assignments",
            "mining_data.fleet_vehicles",
        ],
        tools=["bq_query", "graph_traverse", "request_approval"],
        traversals=["fatigue_to_incident"],
    ),
    specialists=(
        _a("S11-SP1", "Incident Clustering Analyst", "S11", "specialist",
           apqc="9.1.2", persona="P3", branch="safety",
           tables=["mining_data.safety_incidents"],
           tools=["bq_query"]),
        _a("S11-SP2", "Involvement Tracer", "S11", "specialist",
           apqc="9.1.2", persona="P3", branch="safety",
           tables=[
               "mining_data.incident_involvements",
               "mining_data.fatigue_logs_node",
               "mining_data.operators_node",
               "mining_data.operator_vehicle_assignments",
               "mining_data.fleet_vehicles",
               "mining_data.safety_incidents",
           ],
           tools=["graph_traverse"], traversals=["fatigue_to_incident"]),
        _a("S11-SP3", "Radio Transcript Corroborator", "S11", "specialist",
           apqc="9.1.2", persona="P3", branch="safety",
           tables=["mining_data.radio_communications", "mining_data.safety_incidents"],
           tools=["bq_query"]),
    ),
    critic=_a(
        "S11-CRITIC", "Root-Cause Challenge Critic", "S11", "critic",
        apqc="9.1.2", persona="P3", branch="safety",
        tables=[
            "mining_data.safety_incidents",
            "mining_data.incident_involvements",
            "mining_data.radio_communications",
        ],
        tools=["bq_query"],
    ),
)

# ---------------------------------------------------------------------------
# S12 — Shift Handover & Site Value Briefing
# Data: all six branches, read-only
# ---------------------------------------------------------------------------
S12 = SwarmDef(
    swarm_id="S12",
    display_name="Shift Handover & Site Value Briefing",
    coordinator=_a(
        "S12", "Shift Handover & Site Value Briefing Coordinator", "S12",
        "coordinator", apqc="4.3.1", persona="P8",
        branch="site_wide", hitl=False,
        tables=[
            "mining_data.telemetry_stream",
            "mining_data.asset_dependencies",
            "mining_data.assets",
            "mining_data.maintenance_logs",
            "mining_data.erp_work_orders",
            "mining_data.fleet_vehicles",
            "mining_data.haulage_routes",
            "mining_data.operator_vehicle_assignments",
            "mining_data.metallurgical_recovery",
            "mining_data.crusher_states",
            "mining_data.inventory_levels",
            "mining_data.safety_incidents",
            "mining_data.biometric_fatigue_logs",
        ],
        tools=["bq_query"],
        card=AgentCard(
            decision="What changed since the last shift closed, across "
                     "production, safety, fatigue and maintenance demand, "
                     "and whether the incoming supervisor needs to act on "
                     "it before anything else.",
            leaks=["Blind spot", "Latency"],
            archetype="Sentinel",
            authority="L1 — Recommend",
            financial_lines=[
                FinancialLine(
                    line="shift handover risk surface narrowed → risk "
                         "position (avoided loss)",
                    evidence_class="C",
                ),
            ],
            honest_limit="A period-over-period change is reported only "
                          "where the underlying table carries a genuine "
                          "time series; fleet availability and route-level "
                          "dispatch performance carry no such series today, "
                          "and are reported as not instrumented rather than "
                          "inferred from a single snapshot.",
            pack="p8-shift-supervisor.yaml",
            # No metric_impacts, deliberately, for the same reason as S03 and
            # S05: this is the shift-briefing card, its one financial line is
            # Class C and risk-adjusted, and no row in the plan's benchmark
            # table prices a shift-handover briefing or a noticing agent's
            # coverage. Borrowing an adjacent agent's throughput or downtime
            # figure to avoid an empty list is exactly the move the plan
            # forbids; an empty list is the honest answer.
        ),
    ),
    specialists=(
        _a("S12-SP1", "Availability Summariser", "S12", "specialist",
           apqc="4.3.1", persona="P8", branch="site_wide",
           tables=[
               "mining_data.telemetry_stream",
               "mining_data.fleet_vehicles",
               "mining_data.assets",
               "mining_data.maintenance_logs",
           ],
           tools=["bq_query"]),
        _a("S12-SP2", "Production & Recovery Summariser", "S12", "specialist",
           apqc="4.3.1", persona="P8", branch="site_wide",
           tables=[
               "mining_data.metallurgical_recovery",
               "mining_data.crusher_states",
               "mining_data.haulage_routes",
           ],
           tools=["bq_query"]),
        _a("S12-SP3", "Safety & Compliance Summariser", "S12", "specialist",
           apqc="4.3.1", persona="P8", branch="site_wide",
           tables=[
               "mining_data.safety_incidents",
               "mining_data.biometric_fatigue_logs",
               "mining_data.incident_involvements",
           ],
           tools=["bq_query"]),
    ),
    critic=_a(
        "S12-CRITIC", "Omission Critic", "S12", "critic",
        apqc="4.3.1", persona="P8", branch="site_wide",
        tables=[
            "mining_data.telemetry_stream",
            "mining_data.erp_work_orders",
            "mining_data.inventory_levels",
            "mining_data.safety_incidents",
        ],
        tools=["bq_query"],
    ),
)


SWARMS: list[SwarmDef] = [S01, S02, S03, S04, S05, S06, S07, S08, S09, S10, S11, S12]


# ---------------------------------------------------------------------------
# Pattern B — Deep Departmental Agents (D01–D40)
# ---------------------------------------------------------------------------
DEEP: list[AgentDef] = [
    # --- Asset reliability (P1, D01–D06) ---
    _b("D01", "Vibration Signature Diagnostic",
       apqc="11.0.3", persona="P1", branch="asset_reliability",
       tables=["mining_data.telemetry_stream"],
       tools=["bq_query"]),
    _b("D02", "Thermal Drift Diagnostic",
       apqc="11.0.3", persona="P1", branch="asset_reliability",
       tables=["mining_data.telemetry_stream"],
       tools=["bq_query"]),
    _b("D03", "Torque Signature Diagnostic",
       apqc="11.0.3", persona="P1", branch="asset_reliability",
       tables=["mining_data.telemetry_stream", "mining_data.crusher_states"],
       tools=["bq_query"]),
    _b("D04", "Power Draw Efficiency Analyst",
       apqc="11.0.3", persona="P1", branch="asset_reliability",
       tables=["mining_data.telemetry_stream"],
       tools=["bq_query"]),
    _b("D05", "Asset Dependency Criticality Ranker",
       apqc="11.0.3", persona="P1", branch="asset_reliability",
       tables=["mining_data.asset_dependencies", "mining_data.assets"],
       tools=["graph_traverse"], traversals=["blast_radius"]),
    _b("D06", "Digital Twin Simulation Replay Analyst",
       apqc="11.0.3", persona="P1", branch="asset_reliability",
       tables=["mining_data.simulation_runs"],
       tools=["bq_query"]),

    # --- Maintenance execution (P2, D07–D10) ---
    _b("D07", "Work Order Triage & Prioritisation",
       apqc="11.0.3", persona="P2", branch="maintenance_execution",
       hitl=True,
       tables=["mining_data.erp_work_orders"],
       tools=["bq_query", "request_approval"]),
    _b("D08", "Deferral & Cancellation Risk Analyst",
       apqc="11.0.3", persona="P2", branch="maintenance_execution",
       tables=["mining_data.erp_work_orders", "mining_data.maintenance_logs"],
       tools=["bq_query"]),
    _b("D09", "Repair Cost Variance Analyst",
       apqc="11.0.3", persona="P2", branch="maintenance_execution",
       tables=["mining_data.erp_work_orders", "mining_data.maintenance_logs"],
       tools=["bq_query"]),
    _b("D10", "Maintenance Effectiveness / Repeat-Failure Analyst",
       apqc="11.0.3", persona="P2", branch="maintenance_execution",
       tables=["mining_data.maintenance_logs", "mining_data.work_order_parts_edge"],
       tools=["bq_query"]),

    # --- Mine ops / dispatch (P7, D11–D15) ---
    _b("D11", "Haul Cycle Time Analyst",
       apqc="4.3.1", persona="P7", branch="mine_ops",
       tables=["mining_data.haulage_routes"],
       tools=["bq_query", "operational_math"]),
    _b("D12", "Route Congestion Analyst",
       apqc="4.3.1", persona="P7", branch="mine_ops",
       tables=["mining_data.haulage_routes"],
       tools=["bq_query"]),
    # PRD gives D13 only current_payload_tons / payload_capacity_tons, both on
    # fleet_vehicles. haulage_routes is not one of its sources.
    _b("D13", "Payload Utilisation Analyst",
       apqc="4.3.1", persona="P7", branch="mine_ops",
       tables=["mining_data.fleet_vehicles"],
       tools=["bq_query", "operational_math"]),
    _b("D14", "Fleet Assignment Optimiser",
       apqc="4.3.1", persona="P7", branch="mine_ops",
       hitl=True,
       tables=["mining_data.operator_vehicle_assignments", "mining_data.fleet_vehicles"],
       tools=["bq_query", "request_approval"]),
    _b("D15", "Route Network Cluster Analyst",
       apqc="4.3.1", persona="P7", branch="mine_ops",
       tables=["mining_data.haulage_routes"],
       tools=["bq_query", "bqml_predict"],
       models=["asset_clustering_model"]),

    # --- Geology (P5, D16–D20) ---
    _b("D16", "Assay-to-Block Model Variance Analyst",
       apqc="2.0.1", persona="P5", branch="geology",
       tables=["mining_data.drill_assay_logs", "mining_data.geological_block_models"],
       tools=["bq_query"]),
    _b("D17", "Ore Dilution Estimator",
       apqc="2.0.1", persona="P5", branch="geology",
       tables=["mining_data.drill_assay_logs"],
       tools=["bq_query"]),
    _b("D18", "Lithology Classification Auditor",
       apqc="2.0.1", persona="P5", branch="geology",
       tables=["mining_data.drill_assay_logs", "mining_data.geological_block_models"],
       tools=["bq_query"]),
    _b("D19", "Drill Coverage Gap Analyst",
       apqc="2.0.1", persona="P5", branch="geology",
       tables=["mining_data.drill_holes", "mining_data.geological_block_models"],
       tools=["bq_query"]),
    _b("D20", "Grade Confidence Scorer",
       apqc="2.0.1", persona="P5", branch="geology",
       tables=["mining_data.drill_assay_logs", "mining_data.geological_block_models"],
       tools=["bq_query"]),

    # --- Processing / metallurgy (P6, D21–D26) ---
    _b("D21", "Recovery Rate Variance Analyst",
       apqc="4.2.2", persona="P6", branch="processing",
       tables=["mining_data.metallurgical_recovery"],
       tools=["bq_query", "operational_math"]),
    _b("D22", "Feed Grade Sensitivity Analyst",
       apqc="4.2.2", persona="P6", branch="processing",
       tables=["mining_data.metallurgical_recovery"],
       tools=["bq_query", "operational_math"]),
    _b("D23", "Tailings Loss Analyst",
       apqc="4.2.2", persona="P6", branch="processing",
       tables=["mining_data.metallurgical_recovery"],
       tools=["bq_query", "operational_math"]),
    _b("D24", "Concentrate Quality Analyst",
       apqc="4.2.2", persona="P6", branch="processing",
       tables=["mining_data.metallurgical_recovery"],
       tools=["bq_query", "operational_math"]),
    _b("D25", "Crusher Setpoint Optimiser",
       apqc="4.2.2", persona="P6", branch="processing",
       hitl=True,
       tables=["mining_data.crusher_states"],
       tools=["bq_query", "operational_math", "request_approval"]),
    _b("D26", "Crusher Bypass Event Analyst",
       apqc="4.2.2", persona="P6", branch="processing",
       tables=["mining_data.crusher_states"],
       tools=["bq_query"]),

    # --- Supply chain / inventory (P4, D27–D31) ---
    _b("D27", "Safety Stock & Reorder Point Calculator",
       apqc="4.1.2", persona="P4", branch="supply_chain",
       tables=["mining_data.inventory_levels"],
       tools=["bq_query", "operational_math"]),
    _b("D28", "Economic Order Quantity Optimiser",
       apqc="4.1.2", persona="P4", branch="supply_chain",
       tables=["mining_data.inventory_levels", "mining_data.work_order_parts_edge"],
       tools=["bq_query", "operational_math"]),
    _b("D29", "Lead Time Risk Analyst",
       apqc="4.1.2", persona="P4", branch="supply_chain",
       tables=["mining_data.inventory_levels", "mining_data.erp_work_orders"],
       tools=["bq_query"]),
    _b("D30", "Criticality-Weighted Stocking Policy",
       apqc="4.1.2", persona="P4", branch="supply_chain",
       hitl=True,
       tables=["mining_data.inventory_levels", "mining_data.assets"],
       tools=["bq_query", "request_approval"]),
    _b("D31", "Stockout Exposure Analyst",
       apqc="4.1.2", persona="P4", branch="supply_chain",
       tables=[
           "mining_data.inventory_levels",
           "mining_data.erp_work_orders",
           "mining_data.work_order_parts_edge",
           "mining_data.assets",
       ],
       tools=["graph_traverse"], traversals=["stockout_exposure"]),

    # --- Procurement (P4, D32–D34) ---
    _b("D32", "Bid Compliance Auditor",
       apqc="5.2.1", persona="P4", branch="procurement",
       tables=["mining_data.procurement_bids"],
       tools=["bq_query"]),
    _b("D33", "Vendor Performance & Concentration Analyst",
       apqc="5.2.1", persona="P4", branch="procurement",
       tables=["mining_data.procurement_bids"],
       tools=["bq_query"]),
    _b("D34", "Procurement Spend Anomaly Analyst",
       apqc="5.2.1", persona="P4", branch="procurement",
       tables=["mining_data.procurement_bids", "mining_data.inventory_levels"],
       tools=["bq_query"]),

    # --- Safety (P3, D35–D40) ---
    _b("D35", "Fatigue Risk Scorer",
       apqc="9.1.2", persona="P3", branch="safety",
       tables=["mining_data.biometric_fatigue_logs"],
       tools=["bq_query", "bqml_predict"],
       models=["safety_model"]),
    _b("D36", "Microsleep Trend Analyst",
       apqc="9.1.2", persona="P3", branch="safety",
       tables=["mining_data.biometric_fatigue_logs"],
       tools=["bq_query"]),
    _b("D37", "Radio Sentiment & Emergency Triage",
       apqc="9.1.2", persona="P3", branch="safety",
       hitl=True,
       tables=["mining_data.radio_communications"],
       tools=["bq_query", "request_approval"]),
    _b("D38", "Incident Severity Trend Analyst",
       apqc="9.1.2", persona="P3", branch="safety",
       tables=["mining_data.safety_incidents"],
       tools=["bq_query"]),
    _b("D39", "Procedural Compliance Drift Analyst",
       apqc="9.1.2", persona="P3", branch="safety",
       tables=["mining_data.safety_incidents"],
       tools=["bq_query"]),
    # D40: profiles exposure from incidents and assignments, NOT biometrics.
    # Least-privilege: no biometric_fatigue_logs access for this agent —
    # it correlates operator exposure via incident records and assignments only.
    _b("D40", "Operator Exposure Profile Analyst",
       apqc="9.1.2", persona="P3", branch="safety",
       tables=[
           "mining_data.incident_involvements",
           "mining_data.operator_vehicle_assignments",
       ],
       tools=["bq_query"]),
]


ALL_AGENTS: list[AgentDef] = [a for s in SWARMS for a in s.agents] + DEEP
