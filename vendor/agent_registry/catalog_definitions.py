"""
Declarative Typed Definitions for all 100 Mining Agent Personas.
Provides Pydantic v2 schemas and master CATALOG list for the mining platform.
"""

import os
from enum import Enum
from typing import List, Optional, Dict, Any

# DEPLOYMENT TODO: set GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_PROJECT_NUMBER
# before deploying or registering anything. See "Set these before you deploy"
# in docs/RECREATE.md.
#
# These fall back to visible placeholders instead of raising, because this
# module is also imported by tooling that only inspects the catalogue offline
# and never reaches GCP. That is a deliberate exception to the rule elsewhere
# in this repo that a missing value fails loudly: mining_agents.config, which
# every deploying script goes through, does raise.
#
# The cost of the exception is that an unset variable produces a catalogue
# that looks fine and is wrong. It is designed to be caught by eye -- the
# placeholder is visible in any A2A card it generates, e.g.
# "sa-mining-agent-runner@unset-project.iam.gserviceaccount.com" or a URL
# containing "unset-project-number". If you see either, the environment is
# not set.
_PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "unset-project")
_PROJECT_NUMBER = os.environ.get("GOOGLE_CLOUD_PROJECT_NUMBER", "unset-project-number")
_REGION = os.environ.get("MINING_REGION", "us-central1")

_RUNNER_SA = f"sa-mining-agent-runner@{_PROJECT_ID}.iam.gserviceaccount.com"
_ORCHESTRATOR_SA = f"sa-mining-orchestrator@{_PROJECT_ID}.iam.gserviceaccount.com"
_REGISTRY_BASE_URL = (
    f"https://agent-registry-service-{_PROJECT_NUMBER}.{_REGION}.run.app"
)
_FRONTEND_BASE_URL = (
    f"https://frontend-app-service-{_PROJECT_NUMBER}.{_REGION}.run.app"
)
try:
    from pydantic import BaseModel, Field, ConfigDict, field_validator
except ImportError:
    class BaseModel:
        def __init__(self, **kwargs):
            # Initialize defaults from class hierarchy
            for base_cls in reversed(self.__class__.__mro__):
                for k, v in getattr(base_cls, "__dict__", {}).items():
                    if not k.startswith("_") and not callable(v) and not isinstance(v, property):
                        setattr(self, k, v)
            for k, v in kwargs.items():
                if hasattr(self.__class__, k) and isinstance(getattr(self.__class__, k), property):
                    continue
                setattr(self, k, v)

        def model_dump(self, mode: str = "python", **kwargs):
            res = {}
            for k, v in self.__dict__.items():
                if k.startswith("_"):
                    continue
                if hasattr(v, "model_dump"):
                    res[k] = v.model_dump(mode=mode)
                elif hasattr(v, "value"):
                    res[k] = v.value
                elif isinstance(v, list):
                    res[k] = [
                        item.model_dump(mode=mode) if hasattr(item, "model_dump")
                        else (item.value if hasattr(item, "value") else item)
                        for item in v
                    ]
                elif isinstance(v, dict):
                    res[k] = {
                        dk: (dv.model_dump(mode=mode) if hasattr(dv, "model_dump") else (dv.value if hasattr(dv, "value") else dv))
                        for dk, dv in v.items()
                    }
                else:
                    res[k] = v
            return res

    def Field(default=None, default_factory=None, **kwargs):
        if default_factory is not None:
            return default_factory()
        return default

    def ConfigDict(**kwargs):
        return kwargs

    def field_validator(*args, **kwargs):
        return lambda fn: fn


class DepartmentEnum(str, Enum):
    EXPLORATION_GEOLOGY = "Exploration/Geology"
    MINE_PLANNING_OPS = "Mine Planning/Operations"
    FLEET_HAULAGE = "Fleet/Haulage"
    MINERAL_PROCESSING_PLANT = "Mineral Processing/Plant"
    ASSET_INTEGRITY_MAINTENANCE = "Asset Integrity/Maintenance"
    SAFETY_OHSE_ESG = "Safety/OHSE/ESG"
    SUPPLY_CHAIN_LOGISTICS = "Supply Chain/Logistics"
    COMMERCIAL_FINANCE_STRATEGY = "Commercial/Finance/Strategy"


class EndpointTypeEnum(str, Enum):
    CLOUD_RUN = "cloud_run"
    IN_PROCESS = "in_process"


class PatternEnum(str, Enum):
    L0_STRATEGIC = "L0_STRATEGIC"
    A_COORDINATOR = "A_COORDINATOR"
    A_SPECIALIST = "A_SPECIALIST"
    A_CRITIC = "A_CRITIC"
    B_DEEP = "B_DEEP"


class AuthorityLevelEnum(str, Enum):
    L1_ADVISORY = "L1_ADVISORY"
    L2_BOUNDED_ACTION = "L2_BOUNDED_ACTION"
    L3_AUTOMATED_EXECUTION = "L3_AUTOMATED_EXECUTION"
    L4_POLICY_OVERRIDE = "L4_POLICY_OVERRIDE"


class ValueClassEnum(str, Enum):
    CLASS_A_CASH = "Class A (Cash)"
    CLASS_B_METRIC = "Class B (Metric)"
    CLASS_C_RISK = "Class C (Risk)"


class GuardrailConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    max_input_bytes: int = Field(default=32768, description="Strict 32 KB payload limit")
    max_output_bytes: int = Field(default=262144, description="256 KB max output response")
    rate_limit_per_min: int = Field(default=60, description="Max invocations per minute")
    timeout_seconds: float = Field(default=4.5, description="Asynchronous barrier execution timeout")
    concurrency_limit: int = Field(default=80, description="Max concurrent invocations per instance")
    enforce_compression: bool = Field(default=True, description="Reject or auto-compress payloads > 32 KB")

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


class AgentCard(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    agent_id: str = Field(..., description="Unique immutable agent identifier (e.g. AGT-19, S09-COORDINATOR, D01)")
    name: str = Field(..., description="Human-readable title of the agent")
    description: str = Field(default="", description="Detailed operational and mathematical capability description")
    department: DepartmentEnum = Field(..., description="Mining functional department")
    endpoint_type: EndpointTypeEnum = Field(..., description="Deployment topology (cloud_run vs in_process)")
    pattern: PatternEnum = Field(..., description="Architectural agent pattern")
    persona: str = Field(..., description="Assigned mining operations persona")
    apqc_code: str = Field(..., description="APQC Process Classification Framework code")
    authority_level: AuthorityLevelEnum = Field(..., description="Autonomous decision boundary")
    value_class: ValueClassEnum = Field(..., description="Financial realization confidence tier")
    model_id: str = Field(default="gemini-3.7-flash", description="Underlying LLM model identifier")
    system_instruction: str = Field(default="", description="Standardized system prompt instructions")
    tools: List[str] = Field(default_factory=list, description="Bound tools and physics solvers")
    governing_equation: str = Field(..., description="Analytical equation or deterministic algorithm")
    service_account: str = Field(
        default=_RUNNER_SA,
        description="GCP IAM service account binding"
    )
    caller_allowlist: List[str] = Field(default_factory=list, description="Allowed caller identities")
    parent_coordinator_id: Optional[str] = Field(default=None, description="Parent coordinator for in-process sub-agents")
    hitl_required: bool = Field(default=False, description="Whether human dual-key approval is required")
    source_tables: List[str] = Field(default_factory=list, description="BigQuery grounding tables")
    is_externally_callable: bool = Field(default=True, description="Whether endpoint is directly callable")
    input_schema: Dict[str, Any] = Field(default_factory=lambda: {"type": "object"}, description="Input JSON schema")
    output_schema: Dict[str, Any] = Field(default_factory=lambda: {"type": "object"}, description="Output JSON schema")
    guardrails: GuardrailConfig = Field(default_factory=GuardrailConfig, description="Runtime guardrail configuration")
    fallback_strategy: str = Field(
        default="DETERMINISTIC_PHYSICS_FALLBACK",
        description="Failover policy on failure, timeout, or payload breach"
    )

    @property
    def display_name(self) -> str:
        return self.name

    def to_a2a_card(
        self,
        project_id: str = _PROJECT_ID,
        location: str = "us-central1",
        base_url: str = _REGISTRY_BASE_URL,
    ) -> Dict[str, Any]:
        """Generate official Google A2A Agent Card conforming to apphub.googleapis.com/AgentProperties."""
        apqc_names = {
            "1.2.1": "Develop and Manage Enterprise Strategy & Finance",
            "3.1.1": "Manage Exploration & JORC Resource Estimation",
            "3.1.2": "Execute Drill Core Assays & Lithological Modeling",
            "3.1.3": "Perform Geotechnical & Structural Fault Modeling",
            "3.2.1": "Develop Mine Plans, Cut-Offs & Pushback Schedules",
            "3.2.2": "Monitor Pit Slope Stability & Geotechnical Sensors",
            "3.2.3": "Optimize Stope & Blast Pattern Sequencing",
            "3.2.4": "Manage Hydrogeology, Dewatering & Aquifer Drainage",
            "3.3.1": "Design Drill & Blast Patterns & Flyrock Safety",
            "3.3.2": "Model Blast Detonation Waves & Muckpile Swell",
            "3.3.3": "Analyze In-Situ Blast Fragmentation Distribution",
            "3.4.1": "Dispatch Haul Fleet & Real-Time Production Scheduling",
            "3.4.2": "Monitor Haul Truck Telemetry & Dynamic Payload",
            "3.4.3": "Assess Haul Road Rolling Resistance & Tyre Tonnage",
            "3.4.4": "Optimize Shovel-Truck Match Factor & Queue Delay",
            "3.5.1": "Optimize Primary Gyratory Crushing & Power Draw",
            "3.5.2": "Control SAG & Ball Mill Comminution Grinding Circuits",
            "3.5.3": "Maximize Froth Flotation Recovery & Reagent Dosing",
            "3.6.1": "Monitor Tailings Thickener Underflow & Flocculant",
            "3.6.2": "Control Slurry Pipeline Durand Settling & Pressure",
            "3.6.3": "Ensure Tailings Storage Facility (TSF) GISTM Dam Integrity",
            "4.2.2": "Process Vendor Accounts Payable & Rate Reconciliations",
            "4.3.2": "Reconcile Warehouse RFID Consignment Spares",
            "4.3.3": "Manage Hazardous Reagent Storage & Shelf Life",
            "4.4.2": "Optimize Heavy-Haul Locomotive Braking & Schedules",
            "4.4.4": "Manage Marine Berth Laytime, Demurrage & Shiploader",
            "10.1.1": "Evaluate Worker Circadian Fatigue & SAFTE Alertness",
            "10.1.2": "Monitor Confined Space Atmospheric Multi-Gas Levels",
            "10.2.1": "Audit Statutory Mining Tenements & EPA Environmental Permits",
            "10.3.1": "Track Scope 1 & 2 Greenhouse Gas Carbon Emissions",
        }

        dept_val = self.department.value if hasattr(self.department, "value") else str(self.department)
        pat_val = self.pattern.value if hasattr(self.pattern, "value") else str(self.pattern)
        auth_val = self.authority_level.value if hasattr(self.authority_level, "value") else str(self.authority_level)
        val_val = self.value_class.value if hasattr(self.value_class, "value") else str(self.value_class)

        skills = []
        for idx, tool in enumerate(self.tools or [self.agent_id.lower()]):
            skills.append({
                "id": f"skill_{self.agent_id.lower().replace('-', '_')}_{idx+1}",
                "name": tool.replace("_", " ").title(),
                "description": f"Domain capability executing {tool} grounded by {self.governing_equation}",
                "tags": [f"APQC-{self.apqc_code}", val_val, auth_val, dept_val],
                "governing_equation": self.governing_equation,
                "source_tables": self.source_tables,
                "input_schema": self.input_schema,
                "output_schema": self.output_schema,
            })

        agent_type = (
            "DETERMINISTIC_PHYSICS_SOLVER" if self.agent_id.startswith("D")
            else "MULTI_AGENT_SWARM_COORDINATOR" if "COORDINATOR" in self.agent_id or "ORC" in self.agent_id
            else "AUTONOMOUS_OPERATIONAL_AGENT"
        )

        return {
            "name": f"projects/{project_id}/locations/{location}/agents/{self.agent_id.lower()}",
            "display_name": self.name,
            "description": self.description or f"{self.name} for {dept_val}",
            "version": "2.0.0",
            "url": f"{base_url}/api/v1/a2a/rpc",
            "provider": {
                "name": "Mining Enterprise Operations Platform",
                "organization": "Top-40 Diversified Metals & Mining",
                "contact": _ORCHESTRATOR_SA,
            },
            "documentation_url": f"{_FRONTEND_BASE_URL}/docs",
            "capabilities": {
                "streaming": True,
                "a2a_enabled": True,
                "mcp_enabled": True,
                "governing_equation": self.governing_equation,
                "tools": self.tools,
                "pattern": pat_val,
            },
            "skills": skills,
            "governance": {
                "agent_id": self.agent_id,
                "department": dept_val,
                "apqc_code": self.apqc_code,
                "apqc_name": apqc_names.get(self.apqc_code, "Mining Value Chain Operations"),
                "authority_level": auth_val,
                "value_class": val_val,
                "hitl_required": self.hitl_required,
                "service_account": self.service_account,
                "caller_allowlist": self.caller_allowlist,
                "source_tables": self.source_tables,
                "ot_physical_boundary_compliant": True,
                "iec_62443_sl4_verified": True,
                "erp_staging_mediated": True,
                "guardrails": {
                    "max_input_bytes": getattr(self.guardrails, "max_input_bytes", 32768),
                    "max_output_bytes": getattr(self.guardrails, "max_output_bytes", 262144),
                    "rate_limit_per_min": getattr(self.guardrails, "rate_limit_per_min", 60),
                    "timeout_seconds": getattr(self.guardrails, "timeout_seconds", 4.5),
                },
            },
            "apphub_agent_properties": {
                "agent_type": agent_type,
                "framework": "VERTEX_AI_REASONING_ENGINES",
                "governance_tier": val_val,
                "environment": "PRODUCTION",
                "compliance": ["IEC_62443_SL4", "GISTM", "JORC_2012", "SOX_ITGC"],
                "status": "A2A_ENABLED",
            },
        }

    @field_validator("caller_allowlist", mode="before")
    @classmethod
    def set_default_caller_allowlist(cls, v):
        return v if v else [_ORCHESTRATOR_SA]


# -----------------------------------------------------------------------------
# Complete Catalog of 100 Declarative Agent Definitions
# -----------------------------------------------------------------------------

CATALOG: List[AgentCard] = [
    # 1. Level 0 Strategic Planning Advisor
    AgentCard(
        agent_id="AGT-19",
        name="Strategic Planning Advisor",
        description="Level 0 Executive Advisor governing multi-horizon LOM NPV optimization, dynamic cut-off grade scheduling, commodity price stochastic simulations, and Second-Order Stochastic Dominance (SSD) CapEx ranking.",
        department=DepartmentEnum.COMMERCIAL_FINANCE_STRATEGY,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.L0_STRATEGIC,
        persona="CEO / CFO / Executive Committee",
        apqc_code="1.2.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_A_CASH,
        model_id="gemini-3.7-flash",
        system_instruction="You are the Strategic Planning Advisor (AGT-19). You optimize long-term Life-of-Mine NPV balancing 3-stage Kenneth Lane capacities and evaluate CapEx allocations using Second-Order Stochastic Dominance.",
        tools=["kenneth_lane_optimizer", "ornstein_uhlenbeck_simulator", "ssd_capex_evaluator", "risk_assessor"],
        governing_equation="max NPV = sum [(P-s)Qr - cQc - mQm - F]/(1+d)^t",
        service_account=_ORCHESTRATOR_SA,
        caller_allowlist=[_ORCHESTRATOR_SA, "exec-committee@argolis-mining.com"],
        parent_coordinator_id=None,
        hitl_required=True,
        source_tables=["geological_block_models", "financial_ledger", "mine_production_schedule"],
        is_externally_callable=True
    ),

    # -------------------------------------------------------------------------
    # 12 Collaborative Swarms (60 Agents: S01 to S12)
    # -------------------------------------------------------------------------

    # --- S01: Exploration & Geology Swarm ---
    AgentCard(
        agent_id="S01-COORDINATOR",
        name="Geology Swarm Coordinator",
        description="Arbiter for exploration drillhole assays, 3D lithological domains, and JORC 2012 resource classification.",
        department=DepartmentEnum.EXPLORATION_GEOLOGY,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.A_COORDINATOR,
        persona="Elena (Chief Mine Geologist)",
        apqc_code="3.1.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        system_instruction="Synthesize lithological logs, kriging variograms, and structural fault models into validated geological block models.",
        tools=["variogram_modeler", "rqd_calculator", "kriging_solver"],
        governing_equation="gamma(h) = 1/(2N(h)) * sum [Z(x_i) - Z(x_i+h)]^2",
        hitl_required=True,
        source_tables=["drill_holes", "assay_logs", "geological_block_models"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="S01-1-LITHOLOGY",
        name="Drill Lithology Specialist",
        description="Processes diamond core logging, RQD measurements, and alteration classifications.",
        department=DepartmentEnum.EXPLORATION_GEOLOGY,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Exploration Geologist",
        apqc_code="3.1.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="RQD = (sum(pieces >= 10cm) / total_length) * 100",
        parent_coordinator_id="S01-COORDINATOR",
        source_tables=["drill_holes"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S01-2-GEOSTAT",
        name="Assay Geostatistics Specialist",
        description="Calculates experimental semivariograms, nugget effect, spherical models, and Ordinary Kriging estimations.",
        department=DepartmentEnum.EXPLORATION_GEOLOGY,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Geostatistician",
        apqc_code="3.1.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Z_hat(x0) = sum(lambda_i * Z(x_i))",
        parent_coordinator_id="S01-COORDINATOR",
        source_tables=["assay_logs"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S01-3-STRUCTURAL",
        name="Structural Fault Specialist",
        description="Maps fault kinematics, stereonet orientation dip/strike tensors, and geotechnical domain boundaries.",
        department=DepartmentEnum.EXPLORATION_GEOLOGY,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Structural Geologist",
        apqc_code="3.1.3",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="n = (sin(theta)*cos(phi), sin(theta)*sin(phi), cos(theta))",
        parent_coordinator_id="S01-COORDINATOR",
        source_tables=["geological_block_models"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S01-R-CRITIC",
        name="Resource Critic (JORC / QAQC Red Team)",
        description="Adversarial auditor checking QA/QC blanks, CRM standards, core duplicates, and JORC Competent Person boundaries.",
        department=DepartmentEnum.EXPLORATION_GEOLOGY,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_CRITIC,
        persona="Competent Person (CP / QP)",
        apqc_code="3.1.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="JORC Resource Confidence Index & Blank Contamination Variance",
        parent_coordinator_id="S01-COORDINATOR",
        hitl_required=True,
        source_tables=["assay_logs", "qaqc_standards"],
        is_externally_callable=False
    ),

    # --- S02: Mine Planning & Evacuation Swarm ---
    AgentCard(
        agent_id="S02-COORDINATOR",
        name="Mine Planning Coordinator",
        description="Orchestrates pit pushbacks, Lerchs-Grossmann ultimate pit limit optimization, and dynamic phase scheduling.",
        department=DepartmentEnum.MINE_PLANNING_OPS,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.A_COORDINATOR,
        persona="Planning Superintendent",
        apqc_code="3.2.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Lerchs-Grossmann Graph Max-Flow: max sum(w_i * v_i)",
        hitl_required=True,
        source_tables=["mine_production_schedule", "pit_designs"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="S02-1-GEOTECH",
        name="Pit Wall Geotechnical Specialist",
        description="Calculates Factor of Safety (FoS), pore pressure distribution, and wedge/planar slope stability.",
        department=DepartmentEnum.MINE_PLANNING_OPS,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Geotechnical Engineer",
        apqc_code="3.2.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="FoS = [c' + (sigma_n - u)*tan(phi')] / tau_m",
        parent_coordinator_id="S02-COORDINATOR",
        source_tables=["geotech_sensors"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S02-2-SCHEDULE",
        name="Phase Scheduling Specialist",
        description="Generates medium-term and short-term extraction sequences satisfying mill feed blending constraints.",
        department=DepartmentEnum.MINE_PLANNING_OPS,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Long-Term Planning Engineer",
        apqc_code="3.2.3",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="V_t(S) = max_a [R(S, a) + gamma * V_{t+1}(S')]",
        parent_coordinator_id="S02-COORDINATOR",
        source_tables=["mine_production_schedule"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S02-3-DUMP",
        name="Waste Dump Stability Specialist",
        description="Models waste rock placement angle of repose, lift compaction, and runout slip circle containment.",
        department=DepartmentEnum.MINE_PLANNING_OPS,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Civil Mine Engineer",
        apqc_code="3.2.4",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="Bishop Method: FoS = sum([c'b + (W - ub)tan(phi')]*m_alpha) / sum(W*sin(alpha))",
        parent_coordinator_id="S02-COORDINATOR",
        source_tables=["pit_designs"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S02-R-CRITIC",
        name="Plan Compliance Critic (Red Team)",
        description="Evaluates spatial reconciliation (F1 mined vs planned, F2 milled vs mined) and compliance variance.",
        department=DepartmentEnum.MINE_PLANNING_OPS,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_CRITIC,
        persona="Senior Mine Surveyor",
        apqc_code="3.2.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="F1 = Mined_Volume / Planned_Volume, F2 = Milled_Metal / Mined_Metal",
        parent_coordinator_id="S02-COORDINATOR",
        hitl_required=True,
        source_tables=["survey_scans", "mine_production_schedule"],
        is_externally_callable=False
    ),

    # --- S03: Drill & Blast Optimization Swarm ---
    AgentCard(
        agent_id="S03-COORDINATOR",
        name="Drill & Blast Coordinator",
        description="Optimizes blast burden, spacing, powder factor, and Kuz-Ram fragmentation distribution.",
        department=DepartmentEnum.MINE_PLANNING_OPS,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.A_COORDINATOR,
        persona="Drill & Blast Superintendent",
        apqc_code="3.3.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Kuz-Ram: x50 = A * Q^(1/6) * (115/E)^0.63 * (V0/Q)^0.8",
        hitl_required=True,
        source_tables=["blast_designs", "explosives_inventory"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="S03-1-GEOMETRY",
        name="Blast Geometry Specialist",
        description="Calculates optimum burden, spacing, sub-drilling, and stemming lengths based on rock density.",
        department=DepartmentEnum.MINE_PLANNING_OPS,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="D&B Engineer",
        apqc_code="3.3.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="B = K_b * d_h * sqrt(rho_e / rho_r)",
        parent_coordinator_id="S03-COORDINATOR",
        source_tables=["blast_designs"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S03-2-EXPLOSIVE",
        name="Explosives Energy Specialist",
        description="Calculates bulk emulsion vs ANFO energy partitioning, VOD velocity of detonation, and powder factor.",
        department=DepartmentEnum.MINE_PLANNING_OPS,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Shotfirer Technical Lead",
        apqc_code="3.3.3",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="q = M_exp / V_rock (kg/m3)",
        parent_coordinator_id="S03-COORDINATOR",
        source_tables=["explosives_inventory"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S03-3-VIBRATION",
        name="Blast Vibration Sentinel",
        description="Predicts Peak Particle Velocity (PPV) attenuation curves to protect pit walls and infrastructure.",
        department=DepartmentEnum.MINE_PLANNING_OPS,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Environmental Blast Engineer",
        apqc_code="3.3.4",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="PPV = K * (D / sqrt(W))^(-beta)",
        parent_coordinator_id="S03-COORDINATOR",
        source_tables=["vibration_monitors"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S03-R-CRITIC",
        name="Blast Safety Critic (Red Team)",
        description="Statutory blast exclusion zone verification, misfire detection, and flyrock risk perimeter gate.",
        department=DepartmentEnum.MINE_PLANNING_OPS,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_CRITIC,
        persona="Statutory Shotfirer",
        apqc_code="3.3.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="Statutory Exclusion Zone Radius & Misfire Detection Gate",
        parent_coordinator_id="S03-COORDINATOR",
        hitl_required=True,
        source_tables=["blast_designs", "safety_permits"],
        is_externally_callable=False
    ),

    # --- S04: Load & Haul Fleet Dispatch Swarm ---
    AgentCard(
        agent_id="S04-COORDINATOR",
        name="Load & Haul Coordinator",
        description="Dynamic dispatch arbiter maximizing fleet productivity while eliminating shovel hang time and truck queueing.",
        department=DepartmentEnum.FLEET_HAULAGE,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.A_COORDINATOR,
        persona="Dave (Dispatch Superintendent)",
        apqc_code="3.4.1",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Little's Law Queueing: L = lambda * W",
        tools=["littles_law_haulage_solver"],
        hitl_required=True,
        source_tables=["fleet_telemetry", "dispatch_routes"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="S04-1-SHOVEL",
        name="Shovel Match Specialist",
        description="Calculates pass match factor, bucket fill factor, and spotting delay optimization.",
        department=DepartmentEnum.FLEET_HAULAGE,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Dispatch Controller",
        apqc_code="3.4.2",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Passes = Truck_Capacity / (Shovel_Bucket_Payload * Fill_Factor)",
        parent_coordinator_id="S04-COORDINATOR",
        source_tables=["fleet_telemetry"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S04-2-ROUTE",
        name="Haul Route Optimizer",
        description="Solves real-time shortest path and congestion re-routing for Caterpillar/Komatsu haul trucks.",
        department=DepartmentEnum.FLEET_HAULAGE,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Fleet Planner",
        apqc_code="3.4.3",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="min sum(c_ij * x_ij) s.t. network flow continuity",
        parent_coordinator_id="S04-COORDINATOR",
        source_tables=["dispatch_routes"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S04-3-PAYLOAD",
        name="Truck Payload Sentinel",
        description="Enforces OEM 10/10/20 payload policies to prevent structural suspension and chassis cracking.",
        department=DepartmentEnum.FLEET_HAULAGE,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Fleet Controller",
        apqc_code="3.4.4",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="P(X > 1.20 * Target_Payload) = 0",
        parent_coordinator_id="S04-COORDINATOR",
        source_tables=["fleet_telemetry"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S04-R-CRITIC",
        name="Dispatch Safety Critic (Red Team)",
        description="Monitors haul road grade runaway braking envelope, intersection collision proximity, and speed limits.",
        department=DepartmentEnum.FLEET_HAULAGE,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_CRITIC,
        persona="Mine Safety Lead",
        apqc_code="3.4.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="Haul Road Grade Braking Runaway Distance Envelope",
        parent_coordinator_id="S04-COORDINATOR",
        hitl_required=True,
        source_tables=["fleet_telemetry", "safety_telemetry"],
        is_externally_callable=False
    ),

    # --- S05: Primary Crushing Comminution Swarm ---
    AgentCard(
        agent_id="S05-COORDINATOR",
        name="Primary Crushing Coordinator",
        description="Arbiter for primary gyratory crusher throughput, closed side setting (CSS), and apron feeder speed.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.A_COORDINATOR,
        persona="Fixed Plant Superintendent",
        apqc_code="3.5.1",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Bond Comminution: W = 10 Wi (1/sqrt(P80) - 1/sqrt(F80))",
        tools=["bond_comminution_solver"],
        hitl_required=True,
        source_tables=["crusher_telemetry", "assets"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="S05-1-CSS",
        name="Crusher CSS Specialist",
        description="Optimizes hydraulic mantle positioning and Closed Side Setting to match SAG feed size distribution.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Crusher Technician",
        apqc_code="3.5.2",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Q = 3600 * A_gap * v_discharge",
        parent_coordinator_id="S05-COORDINATOR",
        source_tables=["crusher_telemetry"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S05-2-FEED",
        name="Feeder Speed Specialist",
        description="Regulates apron feeder speed to maintain choke feeding and uniform power draw.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Control Room Operator",
        apqc_code="3.5.3",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="u(t) = Kp*e(t) + Ki*int(e)dt + Kd*de/dt",
        parent_coordinator_id="S05-COORDINATOR",
        source_tables=["crusher_telemetry"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S05-3-WEAR",
        name="Mantle Wear Estimator",
        description="Tracks mantle and concave liner abrasive wear using Archard wear modeling and tonnage throughput.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Fixed Plant Planner",
        apqc_code="3.5.4",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="V = K * (W * L) / H",
        parent_coordinator_id="S05-COORDINATOR",
        source_tables=["assets", "crusher_telemetry"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S05-R-CRITIC",
        name="Tramp Metal Critic (Red Team)",
        description="Eddy-current metal detector watchdog halting crusher feed on GET teeth or drill steel detection.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_CRITIC,
        persona="Electrical Superintendent",
        apqc_code="3.5.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="Tramp Iron Eddy-Current Sensor Interlock Gate",
        parent_coordinator_id="S05-COORDINATOR",
        hitl_required=True,
        source_tables=["crusher_telemetry"],
        is_externally_callable=False
    ),

    # --- S06: SAG & Ball Mill Grinding Swarm ---
    AgentCard(
        agent_id="S06-COORDINATOR",
        name="Grinding & Milling Coordinator",
        description="Coordinates SAG mill load, ball mill power draw, water addition, and hydrocyclone classification.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.A_COORDINATOR,
        persona="Concentrator Superintendent",
        apqc_code="3.6.1",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Morrell Specific Energy: W = 4 * M_i * (x2^f(x2) - x1^f(x1))",
        hitl_required=True,
        source_tables=["plant_telemetry", "assets"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="S06-1-SAG",
        name="SAG Mill Load Specialist",
        description="Analyzes acoustic sensor arrays, bearing pressure, and motor torque to determine internal mill charge toe angle.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Mill Operator",
        apqc_code="3.6.2",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Acoustic Toe Angle & Ball Charge Trajectory",
        parent_coordinator_id="S06-COORDINATOR",
        source_tables=["plant_telemetry"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S06-2-BALL",
        name="Ball Mill Power Specialist",
        description="Optimizes grinding media addition, slurry density, and power draw to achieve target P80 liberation.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Grinding Technician",
        apqc_code="3.6.3",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Austin Population Balance Grinding Kinetics",
        parent_coordinator_id="S06-COORDINATOR",
        source_tables=["plant_telemetry"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S06-3-CYCLONE",
        name="Hydrocyclone Split Specialist",
        description="Calculates Plitt cut size d50c, circulating load ratio, and vortex finder pressure to maintain flotation feed size.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Slurry Specialist",
        apqc_code="3.6.4",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Plitt Cut Size: d50c = (50.5 * Dc^0.46 * Di^0.6 * Do^0.68) / (Du^0.71 * h^0.38 * Q^0.45)",
        parent_coordinator_id="S06-COORDINATOR",
        source_tables=["plant_telemetry"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S06-R-CRITIC",
        name="Slurry Density Critic (Red Team)",
        description="Watches pipeline critical settling velocity, trunnion bearing temperature, and slurry rheology limits.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_CRITIC,
        persona="Process Chemist",
        apqc_code="3.6.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="Pipeline Critical Settling Velocity & Slurry Viscosity Limits",
        parent_coordinator_id="S06-COORDINATOR",
        hitl_required=True,
        source_tables=["plant_telemetry"],
        is_externally_callable=False
    ),

    # --- S07: Flotation Recovery & Grade Swarm ---
    AgentCard(
        agent_id="S07-COORDINATOR",
        name="Flotation Recovery Coordinator",
        description="Arbiter balancing copper recovery percentage against final concentrate grade and smelter penalty elements.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.A_COORDINATOR,
        persona="Marcus (Chief Metallurgist)",
        apqc_code="3.7.1",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Langmuir Kinetics: R(t) = R_inf * [1 - exp(-k*t)]",
        hitl_required=True,
        source_tables=["flotation_assays", "plant_telemetry"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="S07-1-REAGENT",
        name="Collector Dosing Specialist",
        description="Calculates potassium amyl xanthate (PAX) and frother addition rates based on ore mineralogy.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Flotation Technician",
        apqc_code="3.7.2",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="theta = (K * C) / (1 + K * C)",
        parent_coordinator_id="S07-COORDINATOR",
        source_tables=["reagent_inventory"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S07-2-AIR",
        name="Froth Air Specialist",
        description="Regulates superficial gas velocity Jg and froth depth to control bubble residence time and entrainment.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Plant Metallurgist",
        apqc_code="3.7.3",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Gas Holdup: eps_g = J_g / (u_b + J_l)",
        parent_coordinator_id="S07-COORDINATOR",
        source_tables=["plant_telemetry"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S07-3-GRADE",
        name="Concentrate Grade Specialist",
        description="Monitors cleaner bank concentrate assays and separation efficiency SE.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Smelter Marketing Liaison",
        apqc_code="3.7.4",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Separation Efficiency: SE = R_val - R_gangue",
        parent_coordinator_id="S07-COORDINATOR",
        source_tables=["flotation_assays"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S07-R-CRITIC",
        name="Smelter Penalty Critic (Red Team)",
        description="Adversarial auditor tracking deleterious penalty elements (Arsenic > 2000ppm, Bismuth, Antimony).",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_CRITIC,
        persona="Commercial Metallurgist",
        apqc_code="3.7.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_A_CASH,
        model_id="gemini-3.7-flash",
        governing_equation="Arsenic / Bismuth Penalty Threshold Matrix",
        parent_coordinator_id="S07-COORDINATOR",
        hitl_required=True,
        source_tables=["flotation_assays"],
        is_externally_callable=False
    ),

    # --- S08: Tailings (TSF) & Water Balance Swarm ---
    AgentCard(
        agent_id="S08-COORDINATOR",
        name="Tailings (TSF) Coordinator",
        description="Global Industry Standard on Tailings Management (GISTM) conformance coordinator and water loop arbiter.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.A_COORDINATOR,
        persona="TSF Manager (Engineer of Record)",
        apqc_code="3.8.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="GISTM Dam Conformance & Phreatic Surface Line",
        hitl_required=True,
        source_tables=["tsf_piezometers", "water_balance_logs"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="S08-1-WATER",
        name="Decant Water Return Specialist",
        description="Tracks reclaim barge pumping rates, evaporation losses, and decant pond volume.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Water Treatment Operator",
        apqc_code="3.8.2",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="V_ret = V_in - V_evap - V_seep - V_pore",
        parent_coordinator_id="S08-COORDINATOR",
        source_tables=["water_balance_logs"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S08-2-PORE",
        name="Piezometer Pressure Specialist",
        description="Monitors vibrating wire piezometer pore water pressure and Terzaghi consolidation dissipation.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Geotech Instrumentation Tech",
        apqc_code="3.8.3",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="Terzaghi Consolidation: du/dt = c_v * (d2u / dz2)",
        parent_coordinator_id="S08-COORDINATOR",
        source_tables=["tsf_piezometers"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S08-3-THICK",
        name="Slurry Thickener Specialist",
        description="Optimizes flocculant dosing, bed pressure, and underflow density for high-rate thickeners.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Dewatering Technician",
        apqc_code="3.8.4",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Kynch Sedimentation Solids Flux Theory",
        parent_coordinator_id="S08-COORDINATOR",
        source_tables=["plant_telemetry"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S08-R-CRITIC",
        name="TSF Liquefaction Critic (Red Team)",
        description="Adversarial geotech auditor checking static liquefaction state, dam crest freeboard, and spillway capacity.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_CRITIC,
        persona="Statutory Geotechnical Reviewer",
        apqc_code="3.8.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="Critical State Soil Mechanics & Static Liquefaction Index",
        parent_coordinator_id="S08-COORDINATOR",
        hitl_required=True,
        source_tables=["tsf_piezometers", "safety_permits"],
        is_externally_callable=False
    ),

    # --- S09: Asset Reliability Swarm (P0 Crisis Arbiter) ---
    AgentCard(
        agent_id="S09-COORDINATOR",
        name="Asset Reliability Swarm Coordinator",
        description="P0 Crisis Arbiter and Reliability Superintendent orchestrating vibration FFT, tribology, and thermal runaway forensics.",
        department=DepartmentEnum.ASSET_INTEGRITY_MAINTENANCE,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.A_COORDINATOR,
        persona="Priya (Reliability Superintendent)",
        apqc_code="9.3.2",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Weibull Hazard Rate: h(t) = (beta / eta) * (t / eta)^(beta - 1)",
        tools=["vibration_iso10816_solver"],
        hitl_required=True,
        source_tables=["assets", "crusher_telemetry", "erp_work_orders"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="S09-1-VIBRATION",
        name="Vibration FFT Specialist",
        description="Processes 10-1000 Hz accelerometer streams and extracts ISO 10816-3 RMS velocity and bearing defect frequencies.",
        department=DepartmentEnum.ASSET_INTEGRITY_MAINTENANCE,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Vibration Analyst (Category III)",
        apqc_code="9.3.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="ISO 10816-3 RMS Velocity & BPFI Harmonics",
        parent_coordinator_id="S09-COORDINATOR",
        source_tables=["assets", "crusher_telemetry"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S09-2-TRIBOLOGY",
        name="Oil Tribology Specialist",
        description="Monitors Particle Quantifier (PQ) index, Karl Fischer moisture PPM, viscosity, and elemental wear metals.",
        department=DepartmentEnum.ASSET_INTEGRITY_MAINTENANCE,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Lubrication Technician",
        apqc_code="9.3.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="PQ Index & Karl Fischer Moisture PPM",
        parent_coordinator_id="S09-COORDINATOR",
        source_tables=["assets", "lube_samples"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S09-3-THERMAL",
        name="Thermal IR Specialist",
        description="Assesses high-speed shaft bearing temperatures, heat dissipation rates, and thermal runaway Delta-T.",
        department=DepartmentEnum.ASSET_INTEGRITY_MAINTENANCE,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Thermographer",
        apqc_code="9.3.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Delta T Component Temperature Rise Model",
        parent_coordinator_id="S09-COORDINATOR",
        source_tables=["assets", "crusher_telemetry"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S09-R-CRITIC",
        name="Maintenance Safety Critic (Red Team)",
        description="Adversarial safety auditor enforcing Lockout/Tagout (LOTO 09-CR-LOTO-03) isolation integrity and 48hr failure window.",
        department=DepartmentEnum.ASSET_INTEGRITY_MAINTENANCE,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_CRITIC,
        persona="Safety Supervisor",
        apqc_code="9.3.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="LOTO Isolation Integrity & Failure Window Safety Gate",
        parent_coordinator_id="S09-COORDINATOR",
        hitl_required=True,
        source_tables=["assets", "erp_work_orders"],
        is_externally_callable=False
    ),

    # --- S10: Contract Integrity & Procurement Swarm ---
    AgentCard(
        agent_id="S10-COORDINATOR",
        name="Procurement Coordinator",
        description="Arbiter for contract invoice rate-card matching, price escalation indices, and warranty claim recovery.",
        department=DepartmentEnum.SUPPLY_CHAIN_LOGISTICS,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.A_COORDINATOR,
        persona="Sarah (Supply Chain Superintendent)",
        apqc_code="4.2.1",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_A_CASH,
        model_id="gemini-3.7-flash",
        governing_equation="Invoice Contract Matching & Rate Card Variance",
        hitl_required=True,
        source_tables=["vendor_contracts", "invoices"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="S10-1-CONTRACT",
        name="Contract Rate Auditor",
        description="Validates supplier unit prices against signed master service agreements (MSA) using fuzzy string matching.",
        department=DepartmentEnum.SUPPLY_CHAIN_LOGISTICS,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Procurement Analyst",
        apqc_code="4.2.2",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_A_CASH,
        model_id="gemini-3.7-flash",
        governing_equation="Levenshtein Distance & Unit Price Deviation",
        parent_coordinator_id="S10-COORDINATOR",
        source_tables=["vendor_contracts"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S10-2-ESCALATE",
        name="PPI Indexation Auditor",
        description="Calculates contract indexation formulas based on Producer Price Index (PPI) labor and diesel benchmarks.",
        department=DepartmentEnum.SUPPLY_CHAIN_LOGISTICS,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Commercial Specialist",
        apqc_code="4.2.3",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_A_CASH,
        model_id="gemini-3.7-flash",
        governing_equation="P_t = P_0 * [a + b*(L_t/L_0) + c*(M_t/M_0)]",
        parent_coordinator_id="S10-COORDINATOR",
        source_tables=["vendor_contracts"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S10-3-WARRANTY",
        name="Warranty Recovery Specialist",
        description="Cross-references component premature failure history (MTBF) against OEM warranty clauses.",
        department=DepartmentEnum.SUPPLY_CHAIN_LOGISTICS,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Asset Accountant",
        apqc_code="4.2.4",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_A_CASH,
        model_id="gemini-3.7-flash",
        governing_equation="MTBF vs Warranty Period Recovery Claimer",
        parent_coordinator_id="S10-COORDINATOR",
        source_tables=["assets", "vendor_contracts"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S10-R-CRITIC",
        name="Anti-Bribery Audit Critic (Red Team)",
        description="Adversarial auditor scanning single-source contracts, beneficial ownership, and FCPA anti-bribery red flags.",
        department=DepartmentEnum.SUPPLY_CHAIN_LOGISTICS,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_CRITIC,
        persona="Internal Auditor",
        apqc_code="4.2.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="Vendor Beneficial Ownership & Single-Source Flags",
        parent_coordinator_id="S10-COORDINATOR",
        hitl_required=True,
        source_tables=["vendor_contracts", "invoices"],
        is_externally_callable=False
    ),

    # --- S11: Spares Inventory & MRO Swarm ---
    AgentCard(
        agent_id="S11-COORDINATOR",
        name="Spares Inventory Coordinator",
        description="Coordinates Economic Order Quantity (EOQ), safety stock levels, and warehouse carrying cost reduction.",
        department=DepartmentEnum.SUPPLY_CHAIN_LOGISTICS,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.A_COORDINATOR,
        persona="Warehouse Superintendent",
        apqc_code="4.3.1",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_A_CASH,
        model_id="gemini-3.7-flash",
        governing_equation="Wilson EOQ: Q* = sqrt(2*D*S / H)",
        hitl_required=True,
        source_tables=["spares_inventory", "purchase_orders"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="S11-1-STOCK",
        name="Safety Stock Optimizer",
        description="Calculates dynamic safety stock buffers accounting for lead-time demand standard deviations.",
        department=DepartmentEnum.SUPPLY_CHAIN_LOGISTICS,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Inventory Planner",
        apqc_code="4.3.2",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_A_CASH,
        model_id="gemini-3.7-flash",
        governing_equation="SS = Z_alpha * sqrt(L * sigma_D^2 + D^2 * sigma_L^2)",
        parent_coordinator_id="S11-COORDINATOR",
        source_tables=["spares_inventory"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S11-2-LEADTIME",
        name="Vendor Lead Time Specialist",
        description="Fits Gamma distributions to supplier shipment delays and port customs clearance lead times.",
        department=DepartmentEnum.SUPPLY_CHAIN_LOGISTICS,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Supply Expediter",
        apqc_code="4.3.3",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Gamma Distribution Lead Time Modeling",
        parent_coordinator_id="S11-COORDINATOR",
        source_tables=["purchase_orders"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S11-3-HOLDING",
        name="Carrying Cost Analyzer",
        description="Evaluates working capital tie-up, warehouse insurance, and obsolescence depreciation rates.",
        department=DepartmentEnum.SUPPLY_CHAIN_LOGISTICS,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Cost Controller",
        apqc_code="4.3.4",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_A_CASH,
        model_id="gemini-3.7-flash",
        governing_equation="H = C_unit * (i + w + o)",
        parent_coordinator_id="S11-COORDINATOR",
        source_tables=["spares_inventory"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S11-R-CRITIC",
        name="Dead Stock Critic (Red Team)",
        description="Identifies non-moving stock (>365 days) and triggers scrap or vendor buyback recommendations.",
        department=DepartmentEnum.SUPPLY_CHAIN_LOGISTICS,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_CRITIC,
        persona="Finance Auditor",
        apqc_code="4.3.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_A_CASH,
        model_id="gemini-3.7-flash",
        governing_equation="Inactive Inventory Aging (>365 Days) Write-Down",
        parent_coordinator_id="S11-COORDINATOR",
        hitl_required=True,
        source_tables=["spares_inventory"],
        is_externally_callable=False
    ),

    # --- S12: Pit-to-Port Supply Chain & Demurrage Swarm ---
    AgentCard(
        agent_id="S12-COORDINATOR",
        name="Supply Chain & Port Coordinator",
        description="Orchestrates train scheduling, stockpile blending, vessel laytime, and demurrage avoidance.",
        department=DepartmentEnum.SUPPLY_CHAIN_LOGISTICS,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.A_COORDINATOR,
        persona="Logistics Manager",
        apqc_code="4.4.1",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_A_CASH,
        model_id="gemini-3.7-flash",
        governing_equation="Dynamic Network Sim: min sum(Rail + Port + Demurrage)",
        hitl_required=True,
        source_tables=["rail_schedules", "port_vessels", "stockpiles"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="S12-1-RAIL",
        name="Train Cycle Dispatch Specialist",
        description="Optimizes locomotive cycle headway, payload tonnage, and diesel consumption across 400km heavy-haul corridors.",
        department=DepartmentEnum.SUPPLY_CHAIN_LOGISTICS,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Rail Controller",
        apqc_code="4.4.2",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Railway Headway & Velocity Optimization",
        parent_coordinator_id="S12-COORDINATOR",
        source_tables=["rail_schedules"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S12-2-BLEND",
        name="Port Stockpile Blend Specialist",
        description="Solves linear programming multi-stockpile blend optimization to meet customer concentrate specifications.",
        department=DepartmentEnum.SUPPLY_CHAIN_LOGISTICS,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Port Metallurgist",
        apqc_code="4.4.3",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Linear Blend Optimization: min ||A*x - b||",
        parent_coordinator_id="S12-COORDINATOR",
        source_tables=["stockpiles"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S12-3-BERTH",
        name="Marine Laytime & Demurrage Specialist",
        description="Calculates BIMCO Statement of Fact laytime usage, weather interruptions, and demurrage penalties.",
        department=DepartmentEnum.SUPPLY_CHAIN_LOGISTICS,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_SPECIALIST,
        persona="Marine Broker",
        apqc_code="4.4.4",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_A_CASH,
        model_id="gemini-3.7-flash",
        governing_equation="BIMCO Laytime Pro-Rata & Demurrage Liability",
        parent_coordinator_id="S12-COORDINATOR",
        source_tables=["port_vessels"],
        is_externally_callable=False
    ),
    AgentCard(
        agent_id="S12-R-CRITIC",
        name="Moisture & TML Critic (Red Team)",
        description="Enforces International Maritime Solid Bulk Cargoes (IMSBC) Transportable Moisture Limit (TML) interlocks.",
        department=DepartmentEnum.SUPPLY_CHAIN_LOGISTICS,
        endpoint_type=EndpointTypeEnum.IN_PROCESS,
        pattern=PatternEnum.A_CRITIC,
        persona="Cargo Surveyor",
        apqc_code="4.4.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="IMSBC Transportable Moisture Limit (TML) Interlock",
        parent_coordinator_id="S12-COORDINATOR",
        hitl_required=True,
        source_tables=["port_vessels", "stockpiles"],
        is_externally_callable=False
    ),

    # -------------------------------------------------------------------------
    # 39 Deep Specialized Microservices (D01 to D39)
    # -------------------------------------------------------------------------
    AgentCard(
        agent_id="D01",
        name="Core Image Segmenter",
        description="Performs automated semantic segmentation of diamond drill core trays and RQD computation in <12s.",
        department=DepartmentEnum.EXPLORATION_GEOLOGY,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Elena (Mine Geologist)",
        apqc_code="3.1.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="ResNet-UNet Rock Classifier (<12s/tray)",
        source_tables=["drill_holes"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D02",
        name="Hyperspectral Mineral Mapper",
        description="Extracts SWIR/VNIR spectral features to quantify copper alteration and compute CuEq with QA/QC validation.",
        department=DepartmentEnum.EXPLORATION_GEOLOGY,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Geochemist",
        apqc_code="3.1.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="SWIR/VNIR Spectral Feature Extractor",
        source_tables=["drill_holes", "assay_logs"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D03",
        name="JORC Classification Auditor",
        description="Computes spatial drill spacing confidence index and spherical variogram kriging variance for JORC audit.",
        department=DepartmentEnum.EXPLORATION_GEOLOGY,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Competent Person",
        apqc_code="3.1.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="Spatial Drill Spacing Confidence Index",
        hitl_required=True,
        source_tables=["drill_holes", "geological_block_models"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D04",
        name="Blast Wave Front Sim",
        description="Solves Chapman-Jouguet detonation Hugoniot equations for explosive pressure pulse propagation.",
        department=DepartmentEnum.MINE_PLANNING_OPS,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="D&B Specialist",
        apqc_code="3.3.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Chapman-Jouguet Detonation Hugoniot Solver",
        source_tables=["blast_designs"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D05",
        name="Flyrock Trajectory Predictor",
        description="Ballistic physics solver estimating maximum flyrock travel distance and safety exclusion zone.",
        department=DepartmentEnum.MINE_PLANNING_OPS,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Shotfirer",
        apqc_code="3.3.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="Ballistic Range: R = (v0^2 * sin(2*theta)) / g",
        hitl_required=True,
        source_tables=["blast_designs"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D06",
        name="In-Situ Fragment Analyzer",
        description="High-resolution muckpile optical segmentation calculating Rosin-Rammler size distribution curves.",
        department=DepartmentEnum.MINE_PLANNING_OPS,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="D&B Engineer",
        apqc_code="3.3.3",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Split-Desktop High-Res Image Segmentation",
        source_tables=["blast_designs"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D07",
        name="Radar Slope Displacement",
        description="Tracks real-time InSAR slope radar displacement and applies Fukuzono inverse velocity failure forecasting.",
        department=DepartmentEnum.MINE_PLANNING_OPS,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Geotech Engineer",
        apqc_code="3.2.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="InSAR Phase Shift Velocity Gradient Delta_phi",
        hitl_required=True,
        source_tables=["geotech_sensors"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D08",
        name="Borehole Seismicity Sentinel",
        description="Monitors microseismic acoustic emissions and applies Gutenberg-Richter magnitude frequency laws.",
        department=DepartmentEnum.MINE_PLANNING_OPS,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Microseismic Technician",
        apqc_code="3.2.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="Gutenberg-Richter Law: log(N) = a - b*M",
        hitl_required=True,
        source_tables=["geotech_sensors"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D09",
        name="Bench Drainage Permeability",
        description="Solves Darcy's law for pore pressure dissipation and open-pit bench horizontal drain discharge.",
        department=DepartmentEnum.MINE_PLANNING_OPS,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Hydrogeologist",
        apqc_code="3.2.4",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Darcy's Law: Q = -k * A * (dh / dl)",
        source_tables=["pit_designs"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D10",
        name="Haul Road Rolling Resist",
        description="Computes haul road dynamic rolling resistance coefficient from truck wheel torque and road grade.",
        department=DepartmentEnum.FLEET_HAULAGE,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Civil Road Superintendent",
        apqc_code="3.4.3",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Rolling Resistance: RR = W * (C_rr + sin(theta))",
        source_tables=["fleet_telemetry"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D11",
        name="Fleet Fuel Burn Sentinel",
        description="Monitors haul truck ECM engine telemetry to calculate brake-specific fuel consumption (L/tonne-km).",
        department=DepartmentEnum.FLEET_HAULAGE,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Energy Manager",
        apqc_code="3.4.4",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Specific Fuel Consumption: SFC = m_dot_f / P_engine",
        source_tables=["fleet_telemetry"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D12",
        name="Tire TKPH Telemetry Agent",
        description="Calculates Tonne-Kilometre-Per-Hour thermal ratings to prevent tire delamination blowouts.",
        department=DepartmentEnum.FLEET_HAULAGE,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Mobile Fleet Maintenance Lead",
        apqc_code="3.4.4",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="TKPH = Q_avg * V_avg <= Rating",
        source_tables=["fleet_telemetry"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D13",
        name="Shovel GET Tooth Sentinel",
        description="Computer vision and payload inertial watchdog detecting lost ground engaging tool bucket teeth.",
        department=DepartmentEnum.FLEET_HAULAGE,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Shovel Operator",
        apqc_code="3.4.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="YOLOv8 Ground Engaging Tool Watcher",
        hitl_required=True,
        source_tables=["fleet_telemetry"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D14",
        name="Autogenous Grinding Sound",
        description="Processes 1/3-octave band acoustic sensor arrays on SAG mills to identify ball-on-liner impact modes.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Mill Operator",
        apqc_code="3.6.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Acoustic Power Spectrum 1/3 Octave Band FFT",
        source_tables=["plant_telemetry"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D15",
        name="Trommel Screen Blinding",
        description="Quantifies screen mesh aperture blinding and near-size pegging on SAG discharge trommels.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Concentrator Technician",
        apqc_code="3.6.4",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Aperture Occlusion Optical Flow Percentage",
        source_tables=["plant_telemetry"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D16",
        name="Slurry Pump Cavitation",
        description="Computes Net Positive Suction Head Available (NPSHa) vs Required (NPSHr) to detect pump cavitation.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Fixed Plant Fitter",
        apqc_code="3.6.4",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Net Positive Suction Head: NPSHa > NPSHr",
        source_tables=["plant_telemetry"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D17",
        name="Sump Level Anti-Surge",
        description="Dynamic mass balance continuity solver regulating variable speed drive pumps to prevent sump overflow.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Process Control Specialist",
        apqc_code="3.6.4",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Mass Balance Continuity: A * (dh/dt) = Q_in - Q_out",
        source_tables=["plant_telemetry"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D18",
        name="Froth Bubble Sizing/Color",
        description="Extracts Sauter mean bubble diameter d32 and RGB chromaticity from flotation froth camera feeds.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Flotation Technician",
        apqc_code="3.7.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Sauter Mean Bubble Diameter d32 & RGB Grade Proxy",
        source_tables=["flotation_assays", "plant_telemetry"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D19",
        name="Xanthate Degradation",
        description="Arrhenius chemical kinetics model tracking temperature and pH-dependent hydrolysis of xanthate collectors.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Reagent Chemist",
        apqc_code="3.7.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="1st-Order Hydrolysis Kinetics: C(t) = C_0 * exp(-k*t)",
        source_tables=["reagent_inventory"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D20",
        name="Acid Mine Drainage ORP",
        description="Nernst electrochemical equation solver calculating net acid generation potential and lime neutralization.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Environmental Superintendent",
        apqc_code="3.8.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="Nernst Equation: E_h = E0 - (RT/nF) * ln(Q)",
        hitl_required=True,
        source_tables=["water_balance_logs"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D21",
        name="Tailings Beach Slope",
        description="Non-Newtonian yield stress subaerial deposition model predicting tailings beach angle theta.",
        department=DepartmentEnum.MINERAL_PROCESSING_PLANT,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="TSF Engineer",
        apqc_code="3.8.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="Non-Newtonian Yield Stress: tau_y = rho * g * h * sin(theta)",
        hitl_required=True,
        source_tables=["tsf_piezometers"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D22",
        name="Transformer Dissolved Gas",
        description="IEC 60599 dissolved gas analyzer (DGA) evaluating Duval Triangle 1 coordinates for transformer arcing faults.",
        department=DepartmentEnum.ASSET_INTEGRITY_MAINTENANCE,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="HV Electrician",
        apqc_code="9.3.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="Duval Triangle & DGA Ratio (Acetylene / Hydrogen)",
        hitl_required=True,
        source_tables=["assets"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D23",
        name="Motor Partial Discharge",
        description="High-frequency phase-resolved partial discharge pulse counter assessing 6.6kV/11kV stator dielectric health.",
        department=DepartmentEnum.ASSET_INTEGRITY_MAINTENANCE,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Electrical Engineer",
        apqc_code="9.3.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="High-Frequency Transient Phase-Resolved PD",
        hitl_required=True,
        source_tables=["assets"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D24",
        name="Conveyor Belt Rip Ultra",
        description="Acoustic time-of-flight transducer array assessing overland conveyor steel cord rips and puncture tears.",
        department=DepartmentEnum.ASSET_INTEGRITY_MAINTENANCE,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Belt Splicer Lead",
        apqc_code="9.3.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="Time-of-Flight Acoustic Wave Attenuation",
        hitl_required=True,
        source_tables=["assets"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D25",
        name="Chute Wear Ultrasonic",
        description="Archard abrasive wear model tracking Hardox 500 transfer chute wear plates to forecast reline shutdowns.",
        department=DepartmentEnum.ASSET_INTEGRITY_MAINTENANCE,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Boilermaker Lead",
        apqc_code="9.3.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Ultrasonic Thickness Pulse-Echo Gauge: d = (v * t) / 2",
        source_tables=["assets"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D26",
        name="Maintenance Work Backlog",
        description="Calculates ready-to-work maintenance backlog in crew weeks and Critical Path Method (CPM) schedule float.",
        department=DepartmentEnum.ASSET_INTEGRITY_MAINTENANCE,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Tom (Maintenance Planner)",
        apqc_code="9.3.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Critical Path Method (CPM) Schedule Float",
        source_tables=["erp_work_orders"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D27",
        name="Contractor Idle Fee Audit",
        description="Cross-references contractor standby invoices against FMS GPS telematics to eliminate over-billing.",
        department=DepartmentEnum.COMMERCIAL_FINANCE_STRATEGY,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Commercial Manager",
        apqc_code="4.2.3",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_A_CASH,
        model_id="gemini-3.7-flash",
        governing_equation="Standby Hours vs Daily Rate Dispute Validator",
        hitl_required=True,
        source_tables=["vendor_contracts", "fleet_telemetry"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D28",
        name="Fuel Bunkering Density",
        description="ASTM D1250 petroleum temperature compensation standardizing gross diesel delivery volume to 15 deg C.",
        department=DepartmentEnum.COMMERCIAL_FINANCE_STRATEGY,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Fuel Logistics Officer",
        apqc_code="4.2.4",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_A_CASH,
        model_id="gemini-3.7-flash",
        governing_equation="API Gravity: API = (141.5 / SG) - 131.5",
        source_tables=["purchase_orders"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D29",
        name="Grinding Ball Wear Batch",
        description="Calculates daily forged steel grinding ball wear (g/kWh) using Bond wear equations to schedule charging.",
        department=DepartmentEnum.ASSET_INTEGRITY_MAINTENANCE,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Plant Metallurgist",
        apqc_code="3.6.3",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Bond Wear Rate: M_ball = 0.16 * (Wi - 7)^0.5",
        source_tables=["spares_inventory", "plant_telemetry"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D30",
        name="Lube Oil Cleanliness",
        description="Converts optical particle counts (>=4, 6, 14 microns) into standard 3-digit ISO 4406 cleanliness codes.",
        department=DepartmentEnum.ASSET_INTEGRITY_MAINTENANCE,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Tribologist",
        apqc_code="9.3.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="ISO 4406 Solid Contamination Cleanliness Code",
        source_tables=["assets", "lube_samples"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D31",
        name="Duplicate Invoice Match",
        description="Scans accounts payable invoices with Levenshtein fuzzy vendor matching and exact amount hashes.",
        department=DepartmentEnum.COMMERCIAL_FINANCE_STRATEGY,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Accounts Payable Lead",
        apqc_code="4.2.2",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_A_CASH,
        model_id="gemini-3.7-flash",
        governing_equation="Levenshtein Distance & Exact Amount Hash Match",
        hitl_required=True,
        source_tables=["invoices"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D32",
        name="Consignment Stock Logger",
        description="Reconciles physical RFID warehouse gate departure logs against SAP ERP Movement Type 201 records.",
        department=DepartmentEnum.SUPPLY_CHAIN_LOGISTICS,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Warehouse Clerk",
        apqc_code="4.3.2",
        authority_level=AuthorityLevelEnum.L2_BOUNDED_ACTION,
        value_class=ValueClassEnum.CLASS_A_CASH,
        model_id="gemini-3.7-flash",
        governing_equation="RFID Tag vs SAP Movement Type 201 Reconciler",
        source_tables=["spares_inventory"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D33",
        name="Laytime BIMCO Parser",
        description="Parses BIMCO Statement of Fact records, calculating weather working day deductions and demurrage.",
        department=DepartmentEnum.SUPPLY_CHAIN_LOGISTICS,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Logistics Officer",
        apqc_code="4.4.4",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_A_CASH,
        model_id="gemini-3.7-flash",
        governing_equation="BIMCO Laytime Standard Statement of Fact Parser",
        source_tables=["port_vessels"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D34",
        name="Reagent Shelf Life",
        description="Arrhenius kinetic model evaluating thermal degradation and potency loss of bulk flotation collectors.",
        department=DepartmentEnum.SUPPLY_CHAIN_LOGISTICS,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Hazmat Technician",
        apqc_code="4.3.3",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="Arrhenius Reaction: k = A * exp(-E_a / RT)",
        source_tables=["reagent_inventory"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D35",
        name="Locomotive Brake Curve",
        description="Heavy-haul locomotive braking distance solver calculating kinetic energy and regenerative retard limits.",
        department=DepartmentEnum.SUPPLY_CHAIN_LOGISTICS,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Rail Master",
        apqc_code="4.4.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="Braking Distance: d = v^2 / [2g*(mu +- theta)]",
        hitl_required=True,
        source_tables=["rail_schedules"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D36",
        name="Shiploader 3D LiDAR",
        description="Continuous 3D LiDAR point cloud anti-collision sentinel checking clearance between shiploader and ship hatch.",
        department=DepartmentEnum.SUPPLY_CHAIN_LOGISTICS,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Shiploader Operator",
        apqc_code="4.4.4",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="3D LiDAR Collision Margin: Distance > 5.0m",
        hitl_required=True,
        source_tables=["port_vessels"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D37",
        name="SAFTE Driver Fatigue",
        description="Biomathematical circadian fatigue evaluation analyzing driver sleep logs and PVT reaction times.",
        department=DepartmentEnum.SAFETY_OHSE_ESG,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Jack (Mine Safety Lead)",
        apqc_code="10.1.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="SAFTE Score: E(t) = S(t) + C(t) - P(t)",
        tools=["safte_circadian_fatigue_solver"],
        hitl_required=True,
        source_tables=["fatigue_monitoring_logs"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D38",
        name="Confined Space Gas",
        description="Real-time multi-gas sentinel monitoring O2, LEL, H2S, and CO atmospheric levels in mills and sumps.",
        department=DepartmentEnum.SAFETY_OHSE_ESG,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Industrial Hygienist",
        apqc_code="10.1.2",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="Gas Limits: LEL < 10%, O2 in [19.5, 23.5]%, H2S < 10ppm",
        hitl_required=True,
        source_tables=["safety_telemetry"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D39",
        name="Carbon Scope 1/2 Tracker",
        description="GHG Protocol emissions calculator determining Scope 1 diesel and Scope 2 grid carbon intensity per tonne Cu.",
        department=DepartmentEnum.SAFETY_OHSE_ESG,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Sustainability Lead",
        apqc_code="10.3.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_B_METRIC,
        model_id="gemini-3.7-flash",
        governing_equation="GHG Protocol: CO2e = sum(Fuel * EF) + (Grid_MWh * EF)",
        source_tables=["fleet_telemetry", "plant_telemetry"],
        is_externally_callable=True
    ),
    AgentCard(
        agent_id="D40",
        name="Statutory Permit Guardian",
        description="Monitors tenement lease expiry, EPA environmental licenses, and water abstraction statutory rights.",
        department=DepartmentEnum.SAFETY_OHSE_ESG,
        endpoint_type=EndpointTypeEnum.CLOUD_RUN,
        pattern=PatternEnum.B_DEEP,
        persona="Legal Counsel & Compliance Officer",
        apqc_code="10.2.1",
        authority_level=AuthorityLevelEnum.L1_ADVISORY,
        value_class=ValueClassEnum.CLASS_C_RISK,
        model_id="gemini-3.7-flash",
        governing_equation="Regulatory Obligation NLP Entity Matcher & Tenement Lease Auditor",
        hitl_required=True,
        source_tables=["tenement_leases", "safety_permits"],
        is_externally_callable=True
    ),
]

# Master Lookup Dictionary: Agent ID -> AgentCard
AGENT_MAP: Dict[str, AgentCard] = {a.agent_id.upper(): a for a in CATALOG}
