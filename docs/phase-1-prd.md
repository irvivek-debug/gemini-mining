# Phase 1 PRD — Mining Agent Suite (100 ADK Agents)

**Cloud:** `your-gcp-project-id` · BigQuery `mining_data` (US)
**Build framework:** ADK throughout. Deploy to Agent Runtime, register in Agent Registry.
**Intent:** demo / sales showcase **and** reference solution accelerator.
**Counting convention:** Option 1 — ADK agent instances. 12 swarms × (1 coordinator + 4 specialists) = 60 Pattern A agents, plus 40 Pattern B deep agents = **100**.

> **GATE.** Approve this PRD before Phase 2 (UX). No implementation code is written until Phases 1–4 are all approved.

---

## 1. Problem statement

Realised value per ton of ore at the site is below plan. The gap is not one failure — it is six, and no single role can see across them. Evidence drawn from the live dataset, not assumed:

| Signal | Measured value | Source |
|---|---|---|
| Work orders at CRITICAL priority | **101 of 500** | `erp_work_orders` |
| Work orders CANCELLED (deferred, will resurface) | **104 of 500**, $617k booked repair cost | `erp_work_orders` |
| Spare parts below reorder point | **28 of 140**, against 21.6-day mean lead time | `inventory_levels` |
| Concentrator recovery spread | **88.2% – 95.2%** (mean 92.2%) at `CONC-01` | `metallurgical_recovery` |
| Safety incidents on record | **60**, including fatality-class events | `safety_incidents` |
| Fatigue readings unreviewed per operator population | **3,340** across 20 operators | `biometric_fatigue_logs` |

Each of these is owned by a different person, sits in a different table, and is worked in a different tool. The cost is not any one number — it is that a predicted mill failure and an out-of-stock bearing are the same event, discovered six weeks apart.

## 2. Personas

Carried forward from Phase 0 unchanged.

| # | Persona | Owns | Core pain |
|---|---|---|---|
| P1 | Reliability Engineer | `telemetry_stream`, `crusher_states`, `asset_dependencies`, `simulation_runs`, `MiningAssetGraph` | No automated link from a vibration excursion to the dependent asset it will take down. |
| P2 | Maintenance Planner | `erp_work_orders`, `maintenance_logs`, `work_order_parts_edge` | Cannot tell which of 104 cancellations were deferrals that will return worse. |
| P3 | Mine Safety & Health Manager | `safety_incidents`, `biometric_fatigue_logs`, `radio_communications`, `incident_involvements` | Fatigue and radio signals arrive faster than any human can triage; incidents are reconstructed after the fact. |
| P4 | Supply Chain / Procurement Manager | `inventory_levels`, `rfp_items`, `procurement_bids`, `MiningSupplyChainGraph` | 300 bids to evaluate with no link back to the work orders that need the parts. |
| P5 | Resource Geologist | `drill_holes`, `drill_assay_logs`, `geological_block_models` | 295 assay intervals vs 1,000 modelled blocks; reconciliation is manual and episodic. |
| P6 | Metallurgist / Concentrator Superintendent | `metallurgical_recovery`, `crusher_states` | No closed loop from crusher settings to recovery outcome. |
| P7 | Mine Ops / Dispatch Supervisor | `fleet_vehicles`, `haulage_routes`, `operator_vehicle_assignments` | Route congestion is recorded but not acted on within the shift. |
| P8 | Shift Superintendent | escalation target for P1–P7 | Assembles handover by hand from seven sources. |

## 3. Jobs to be done

| JTBD | Persona |
|---|---|
| When a critical asset shows degradation, tell me what else it takes down and whether I can survive to the next planned window. | P1 |
| When I plan a shutdown, tell me which work orders I can actually close given the parts I have. | P2 |
| When an operator is unfit, tell me before they get in the truck, and tell me who covers the shift. | P3 |
| When a part goes below reorder point, tell me which work orders and which assets are exposed, in dollars. | P4 |
| When the plant misses recovery, tell me whether geology delivered what the model promised. | P5, P6 |
| When cycle times inflate mid-shift, give me a re-plan I can commit before the shift ends. | P7 |
| At handover, give me one brief that is complete and admits what it does not know. | P8 |

## 4. Success metrics

Two classes, because this asset is judged twice — once in a demo room, once by an engineer forking it.

**Business metrics the demo claims** (baseline → target, baselines measured above):

| Metric | Baseline | Target |
|---|---|---|
| Recovery rate variance at `CONC-01` | 7.0 pt spread (88.2–95.2) | ≤ 4.0 pt spread |
| Parts below reorder point | 28 of 140 (20.0%) | ≤ 12 of 140 (8.6%) † |
| CRITICAL work orders open at any time | 21 OPEN of 101 CRITICAL | ≤ 10 OPEN |
| Fatigue events reaching an operator before shift start | 0% (post-hoc only) | 100% of `fatigue_alert_triggered` |
| Mean time from telemetry anomaly to dependency-impact assessment | manual, hours | < 60 seconds |

† The below-ROP target is split by lead time, because lead time is a physical
constraint no agent can compress. Of the 28 parts below reorder point, **18 sit
at a lead time of ≤ 21 days** (of 94 such parts) and are addressable by earlier
detection and a faster purchase-order raise — target **≤ 5**. The other **10 sit
above 21 days** (of 46 such parts; 5 of them beyond 45 days), where the
achievable gain is *detecting the approach to ROP sooner*, not eliminating the
breach inside one cycle — target **≤ 7**. Hence ≤ 12 in total. A single blended
target of ≤ 5 would implicitly claim we can stop stocking out on 45-day-lead
items, which is the first thing an experienced planner will challenge.

**Accelerator metrics** — what makes it reusable rather than a one-off:

| Metric | Target |
|---|---|
| Agents whose grounding resolves to a real table/column | 100 of 100 |
| Agents reachable from a persona JTBD in §3 | 100 of 100 |
| Swarms demonstrating genuine A2A delegation + peer critique | 12 of 12 |
| Agents with a hardcoded model ID | 0 |
| Agents requiring data that does not exist in `mining_data` | 0 |

## 5. Agent inventory

### 5.1 Pattern A — Multi-Agent Swarms (12 swarms · 60 agents)

Every swarm carries a **Critic** as its fourth specialist. That is not padding: peer critique is the mechanism that makes a swarm defensible rather than a fan-out, and it is what a technical buyer will look for.

| Swarm | Coordinator (registry entrypoint) | Specialists (sub-agents) | APQC | Lead persona | `hitl_required` | Data |
|---|---|---|---|---|---|---|
| **S01** Cascading Failure Impact & Recovery | `s01-cascading-failure-coordinator` | Telemetry Anomaly Detector · Dependency Blast-Radius Tracer · Downtime Duration Forecaster · Recovery Plan Critic | 11.0.3 | P1 | **true** — shutdown recommendation | `telemetry_stream`, `asset_dependencies`, `MiningAssetGraph`, `downtime_regression_model*`, `maintenance_logs` |
| **S02** Planned Shutdown Readiness | `s02-shutdown-readiness-coordinator` | Work Order Bundler · Parts Availability Checker · Lead-Time Feasibility Analyst · Readiness Critic | 11.0.3 / 4.1.2 | P2 | **true** — shutdown window commit | `erp_work_orders`, `work_order_parts_edge`, `inventory_levels`, `MiningSupplyChainGraph` |
| **S03** Fleet Reliability & Availability | `s03-fleet-reliability-coordinator` | Vehicle Health Screener · Duty-Cycle Analyst · Maintenance History Correlator · Availability Forecast Critic | 11.0.3 / 4.3.1 | P1 | false | `fleet_vehicles`, `maintenance_logs`, `erp_work_orders` |
| **S04** Shift Dispatch Re-plan | `s04-dispatch-replan-coordinator` | Cycle Time Variance Analyst · Route Congestion Modeller · Operator Assignment Fit · Dispatch Plan Critic | 4.3.1 | P7 | **true** — re-plan commit | `haulage_routes`, `operator_vehicle_assignments`, `operators_node`, `fleet_vehicles` |
| **S05** Autonomous Haulage Safety Interlock | `s05-ahs-interlock-coordinator` | Proximity & Incident History Screener · Operator Fatigue Cross-Check · Radio Emergency Listener · Interlock Critic | 4.3.1 / 9.1.2 | P3 | **true** — halt autonomous fleet | `safety_incidents`, `incident_involvements`, `biometric_fatigue_logs`, `radio_communications`, `MiningOperationsSafetyGraph` |
| **S06** Grade-to-Recovery Reconciliation | `s06-grade-recovery-coordinator` | Assay-to-Block Variance Analyst · Delivered Feed Grade Tracer · Recovery Attribution Analyst · Reconciliation Critic | 2.0.1 / 4.2.2 | P5 | false | `drill_assay_logs`, `geological_block_models`, `metallurgical_recovery` |
| **S07** Crusher–Mill Throughput Balance | `s07-throughput-balance-coordinator` | Crusher Setting Analyst · Mill Load Analyst · Recovery Sensitivity Modeller · Setpoint Safety Critic | 4.2.2 / 11.0.3 | P6 | **true** — setpoint change | `crusher_states`, `telemetry_stream` (`MILL-01`), `metallurgical_recovery` |
| **S08** Stockout-to-Work-Order Impact | `s08-stockout-impact-coordinator` | Below-ROP Screener · Work Order Exposure Tracer · Downtime Cost Modeller · Stocking Critic | 4.1.2 / 11.0.3 | P4 | **true** — purchase order raise | `inventory_levels`, `MiningSupplyChainGraph`, `erp_work_orders`, `inventory_impact_model` |
| **S09** RFP & Bid Award Evaluation | `s09-bid-award-coordinator` | Bid Compliance Checker · Technical Scoring Analyst · Cost & Spend Anomaly Analyst · Award Critic | 5.2.1 | P4 | **true** — bid award | `procurement_bids`, `rfp_items`, `bid_parts_edge`, `inventory_levels` |
| **S10** Fatigue Intervention & Stand-down | `s10-fatigue-intervention-coordinator` | Biometric Fatigue Scorer · Microsleep Event Escalator · Shift Coverage Impact Analyst · Intervention Critic | 9.1.2 / 4.3.1 | P3 | **true** — stand down operator | `biometric_fatigue_logs`, `operator_vehicle_assignments`, `safety_model` |
| **S11** Incident Investigation & Corroboration | `s11-incident-investigation-coordinator` | Incident Clustering Analyst · Involvement Tracer · Radio Transcript Corroborator · Root-Cause Challenge Critic | 9.1.2 | P3 | **true** — incident escalation | `safety_incidents`, `incident_involvements`, `radio_communications`, `MiningOperationsSafetyGraph` |
| **S12** Shift Handover & Site Value Briefing | `s12-shift-handover-coordinator` | Availability Summariser · Production & Recovery Summariser · Safety & Compliance Summariser · Omission Critic | 4.3.1 | P8 | false | all six branches, read-only |

### 5.2 Pattern B — Deep Departmental Agents (40 agents)

| ID | Agent | APQC | Persona | HITL | Data / deterministic method |
|---|---|---|---|---|---|
| D01 | Vibration Signature Diagnostic | 11.0.3 | P1 | false | `telemetry_stream.vibration_hz` (`PUMP-104A`) |
| D02 | Thermal Drift Diagnostic | 11.0.3 | P1 | false | `telemetry_stream.temperature_c` — `PUMP-104A` and `MILL-01`; MILL-01 added by data injection A3 (see Phase 3 §0.2) |
| D03 | Torque Signature Diagnostic | 11.0.3 | P1 | false | `telemetry_stream.rotational_torque_nm`, `crusher_states` |
| D04 | Power Draw Efficiency Analyst | 11.0.3 | P1 | false | `telemetry_stream.power_draw_mw` (`MILL-01`) |
| D05 | Asset Dependency Criticality Ranker | 11.0.3 | P1 | false | `asset_dependencies.impact_score`, `MiningAssetGraph` |
| D06 | Digital Twin Simulation Replay Analyst | 11.0.3 | P1 | false | `simulation_runs` (`projected_cooling_curve`, `nba_executed`) |
| D07 | Work Order Triage & Prioritisation | 11.0.3 | P2 | **true** — WO release | `erp_work_orders` (status × priority) |
| D08 | Deferral & Cancellation Risk Analyst | 11.0.3 | P2 | false | 104 CANCELLED `erp_work_orders` vs `maintenance_logs` |
| D09 | Repair Cost Variance Analyst | 11.0.3 | P2 | false | `repair_cost` vs `maintenance_logs.actual_duration_hours` |
| D10 | Maintenance Effectiveness / Repeat-Failure Analyst | 11.0.3 | P2 | false | `maintenance_logs.parts_replaced`, `work_order_parts_edge` |
| D11 | Haul Cycle Time Analyst | 4.3.1 | P7 | false | `haulage_routes.average_cycle_time_mins`; Little's Law |
| D12 | Route Congestion Analyst | 4.3.1 | P7 | false | `congestion_factor`, `distance_meters` |
| D13 | Payload Utilisation Analyst | 4.3.1 | P7 | false | `current_payload_tons` / `payload_capacity_tons` |
| D14 | Fleet Assignment Optimiser | 4.3.1 | P7 | **true** — assignment change | `operator_vehicle_assignments`, `fleet_vehicles` |
| D15 | Route Network Cluster Analyst | 4.3.1 | P7 | false | `asset_clustering_model`, `haulage_routes` |
| D16 | Assay-to-Block Model Variance Analyst | 2.0.1 | P5 | false | `drill_assay_logs` vs `geological_block_models` |
| D17 | Ore Dilution Estimator | 2.0.1 | P5 | false | `specific_gravity`, grade estimates vs assayed intervals |
| D18 | Lithology Classification Auditor | 2.0.1 | P5 | false | `geology_code` vs `lithology_type` |
| D19 | Drill Coverage Gap Analyst | 2.0.1 | P5 | false | `drill_holes` collar coords vs block model centroids |
| D20 | Grade Confidence Scorer | 2.0.1 | P5 | false | assay density per block neighbourhood |
| D21 | Recovery Rate Variance Analyst | 4.2.2 | P6 | false | `metallurgical_recovery.recovery_rate_pct` |
| D22 | Feed Grade Sensitivity Analyst | 4.2.2 | P6 | false | `feed_grade_pct` vs `recovery_rate_pct` |
| D23 | Tailings Loss Analyst | 4.2.2 | P6 | false | `tailings_grade_pct` × throughput |
| D24 | Concentrate Quality Analyst | 4.2.2 | P6 | false | `concentrate_grade_pct` |
| D25 | Crusher Setpoint Optimiser | 4.2.2 | P6 | **true** — setpoint change | `crusher_states.gap_size_setting_mm`, `feed_rate_tph` |
| D26 | Crusher Bypass Event Analyst | 4.2.2 | P6 | false | `crusher_states.bypass_valve_open` |
| D27 | Safety Stock & Reorder Point Calculator | 4.1.2 | P4 | false | `inventory_levels`; deterministic ROP = μd·LT + SS |
| D28 | Economic Order Quantity Optimiser | 4.1.2 | P4 | false | `unit_price_usd`, demand from `work_order_parts_edge`; EOQ |
| D29 | Lead Time Risk Analyst | 4.1.2 | P4 | false | `lead_time_days` distribution vs WO urgency |
| D30 | Criticality-Weighted Stocking Policy | 4.1.2 | P4 | **true** — policy change | `inventory_levels` × `assets.criticality_rating` |
| D31 | Stockout Exposure Analyst | 4.1.2 | P4 | false | 28 below-ROP parts × `MiningSupplyChainGraph` |
| D32 | Bid Compliance Auditor | 5.2.1 | P4 | false | `procurement_bids.compliance_checked` |
| D33 | Vendor Performance & Concentration Analyst | 5.2.1 | P4 | false | `vendor_name`, `bid_status` distribution |
| D34 | Procurement Spend Anomaly Analyst | 5.2.1 | P4 | false | `proposed_cost` vs `unit_price_usd` baseline |
| D35 | Fatigue Risk Scorer | 9.1.2 | P3 | false | `sleep_deficit_hours`, `heart_rate_bpm`, `safety_model` |
| D36 | Microsleep Trend Analyst | 9.1.2 | P3 | false | `microsleep_events_detected` over shift history |
| D37 | Radio Sentiment & Emergency Triage | 9.1.2 | P3 | **true** — emergency escalation | `radio_communications` (`emergency_keyword_flag`, `sentiment_score`) |
| D38 | Incident Severity Trend Analyst | 9.1.2 | P3 | false | `safety_incidents.severity_level` over time |
| D39 | Procedural Compliance Drift Analyst | 9.1.2 | P3 | false | `root_cause = 'Procedural non-compliance'` cohort |
| D40 | Operator Exposure Profile Analyst | 9.1.2 | P3 | false | `incident_involvements` × `operator_vehicle_assignments` |

### 5.3 Agents by persona

| Persona | Pattern B | Pattern A (swarms led) | Total agents |
|---|---|---|---|
| P1 Reliability Engineer | 6 (D01–D06) | S01, S03 → 10 | **16** |
| P2 Maintenance Planner | 4 (D07–D10) | S02 → 5 | **9** |
| P3 Safety & Health Manager | 6 (D35–D40) | S05, S10, S11 → 15 | **21** |
| P4 Supply Chain / Procurement | 8 (D27–D34) | S08, S09 → 10 | **18** |
| P5 Resource Geologist | 5 (D16–D20) | S06 → 5 | **10** |
| P6 Metallurgist | 6 (D21–D26) | S07 → 5 | **11** |
| P7 Dispatch Supervisor | 5 (D11–D15) | S04 → 5 | **10** |
| P8 Shift Superintendent | 0 | S12 → 5 | **5** |
| | **40** | **60** | **100** |

Safety (P3) carries the largest share at 21. That is deliberate and defensible: it is the only branch in the dataset with fatality-class outcomes, and it holds the richest graph (3,350 edges).

### 5.4 Agents by process (APQC)

| APQC | Process | Branch | Pattern B | Pattern A | Total |
|---|---|---|---|---|---|
| **11.0.3** | Maintain production equipment | B1 | 10 | S01, S02, S03 → 15 | **25** |
| **4.3.1** | Manage logistics & dispatch | B2 | 5 | S04, S05, S12 → 15 | **20** |
| **9.1.2** | Manage environment, health & safety | B6 | 6 | S10, S11 → 10 | **16** |
| **4.2.2** | Manage production / processing | B4 | 6 | S07 → 5 | **11** |
| **2.0.1** | Manage exploration & resource definition | B3 | 5 | S06 → 5 | **10** |
| **4.1.2** | Manage materials & inventory | B5 | 5 | S08 → 5 | **10** |
| **5.2.1** | Manage procurement & sourcing | B5 | 3 | S09 → 5 | **8** |
| | | | **40** | **60** | **100** |

Swarms spanning two processes are counted once, under the process of the coordinator's owning department, to keep the total at exactly 100.

### 5.5 HITL summary

**14 agents carry `hitl_required: true`** — 9 swarm coordinators (S01, S02, S04, S05, S07, S08, S09, S10, S11) and 5 deep agents (D07, D14, D25, D30, D37). Every one of them either writes to a system of record, changes a physical setpoint, commits spend, or removes a person from duty. All 14 require Hold-to-Confirm plus an audit trail in Phase 2 UX. The remaining 86 are read-only analysis and need no confirmation gate.

> **Corrected 2026-08-12.** This paragraph read "20 agents — 9 swarm coordinators and 11 deep agents". The 9 was right; the 11 was not. The per-agent tables in §5.1 and §5.2 above — which are what the build was written from — mark exactly 5 deep agents `true` and 35 `false`, and have done since the first draft. The prose was the only place the number 20 appeared. Counting the tables is authoritative; `tests/catalog/test_definitions.py::test_exactly_fourteen_agents_are_hitl` pins the result so the two cannot drift apart again.

## 6. Citation Mandate

**Not applicable.** The Citation Mandate is required only when the inventory contains at least one Pattern C agent. This inventory contains **zero Pattern C agents** by explicit scope decision — Pattern C assets already exist and were excluded.

Grounding discipline is not abandoned, only relocated: `MiningOntologyGraph` and `unstructured_docs_metadata` are exposed as **ADK tools** consumed by Pattern A and B agents, and every agent's output must name the tables it read. That requirement is specified as a tool contract in Phase 3, not as a Citation Mandate string.

## 7. Assumptions and open questions

Carried forward verbatim from Phase 0, plus two that arose while building the inventory.

* **ASSUMPTION**: The five `assets` rows represent asset *classes* to be shown at demo scale, not the site's true asset register. — If wrong, per-asset agents collapse to five instances and the swarm topology should be re-cut by process area instead of by asset.
* **ASSUMPTION**: Telemetry covers all five `assets` rows — `CONVEYOR-02`, `CRUSHER-03`, `MILL-01`, `PUMP-104A`, `TRUCK-08` (two-hourly, 2026-01-01 → 2026-06-16) — at a deliberate demo sampling rate rather than a production historian rate. — If wrong, the two-hourly interval is too coarse for D01–D04 and S01 to resolve a fast-developing fault and the series must be regenerated at a finer cadence. Coverage for `CONVEYOR-02` and `TRUCK-08` was added by data injections A2/A3; before that only three assets were instrumented, which is what the earlier revision of this assumption recorded.
* **ASSUMPTION**: `safety_incidents.root_cause` is pre-populated because the data is synthetic; in a real deployment root cause is the *output* of investigation, not an input. — If wrong, S11 and D39 are reading their own answer key. **Mitigated in design**: S11's fourth specialist is a *Root-Cause Challenge Critic* that must corroborate the stated cause against `radio_communications` and `incident_involvements` independently, and report disagreement. Do not demo S11 as deriving root cause from scratch.
* **ASSUMPTION**: No tailings/piezometer, LOTO permit, or EPC contractor schedule data exists. — Confirmed absent. The three corresponding playbook agents are dropped rather than built on invented data.
* **OPEN QUESTION**: `metallurgical_recovery` has a single concentrator (`CONC-01`). D21–D24 therefore compare against time, not against peer units. If a second concentrator is expected, say so now — it changes those four agents from trend analysis to benchmarking.
* **OPEN QUESTION**: Should swarm specialists be individually registered in Agent Registry, or only the 12 coordinators? The metrics above assume **coordinators only** (52 registry entries: 12 + 40). Registering all 100 is possible but makes the registry harder to navigate for a buyer.

## 8. Out of scope

- **Pattern C / GE App low-code agents** — excluded by explicit instruction; existing assets cover this.
- **New data generation.** The build grounds in the 28 tables that exist. No table is created to make an agent possible; agents that would need one were dropped (see §7).
- **Production hardening** — SLOs, multi-region, DR, quota management, cost controls. This is a showcase and accelerator, not a production pilot.
- **Repo remediation of `agent_manifest.json`** — the existing 4-agent petroleum-flavoured manifest and the 6 non-existent table references in `docs/` are superseded by this PRD. Cleanup is tracked separately.
- **Real-time streaming ingestion.** All agents read BigQuery at rest.
- **UX screens, data model, and access model** — Phases 2 and 3.

---

## Gate

Approve, or tell me what to change. Phase 2 (UX) does not start until this is approved.
