# Phase 0 — Personas, MECE Decomposition, Candidate Agents

**Engagement:** 100 ADK agents for a Mining scenario.
**Cloud:** `your-gcp-project-id` · BigQuery `mining_data` (US).
**Intent:** demo / sales showcase **and** reference solution accelerator.
**Scope constraint:** Pattern A (swarm) and Pattern B (deep departmental) only.
Pattern C (low-code GE App search) is explicitly out of scope — existing assets cover it.

---

## Step 0 — Intake

| Field | Value | Source |
|---|---|---|
| **Operating context** | Single integrated mine site: open pit + haulage + primary crushing + SAG milling + one concentrator (`CONC-01`). Owner-operator, autonomous haulage present (`Waymo-AHS Autonomous Haul Truck 08`). | `assets`, `fleet_vehicles`, `metallurgical_recovery` |
| **The human** | Seven operating roles, below. | derived from table ownership |
| **The gap** | Realised value per ton of ore is below plan. Evidenced in-dataset: 15 of 103 spare parts below reorder point; 102 of 500 work orders CRITICAL; recovery swings 88.0–96.0% at one concentrator; 60 safety incidents including fatalities. | live queries |
| **Systems of record** | BigQuery `mining_data` — 28 tables, 4 property graphs, 7 BQML models. All populated; all four graphs verified to traverse and return rows. | `INFORMATION_SCHEMA`, `GRAPH_TABLE` probes |

### Assumption ledger

* **ASSUMPTION**: The five `assets` rows represent asset *classes* to be shown at demo scale, not the site's true asset register. — If wrong and this is meant to reflect a real register, per-asset agents collapse to five instances and the swarm topology should be re-cut by process area instead of by asset.
* **ASSUMPTION**: Telemetry covering only `PUMP-104A`, `CRUSHER-03`, `MILL-01` (hourly, 2026-01-01 → 2026-06-16) is a deliberate demo subset. — If wrong, every condition-monitoring agent scoped to `CONVEYOR-02` or `TRUCK-08` has no signal to read and must be re-grounded or dropped.
* **ASSUMPTION**: `safety_incidents.root_cause` is pre-populated because the data is synthetic; in a real deployment root cause is the *output* of investigation, not an input. — If wrong, several safety agents are reading their own answer key, and the demo narrative must present them as validating rather than deriving root cause.
* **ASSUMPTION**: No tailings/piezometer, LOTO permit, or EPC contractor schedule data exists, so the pre-built playbook branches that depend on them are not buildable here. — Confirmed absent by table inventory; those three playbook agents are dropped rather than faked.

---

## Personas

Derived from which tables a role actually owns and writes to.

| # | Persona | Owns / reads | Core pain visible in the data |
|---|---|---|---|
| P1 | **Reliability Engineer** | `telemetry_stream`, `crusher_states`, `asset_dependencies`, `MiningAssetGraph`, `simulation_runs` | Sees 5 metrics × 3 critical assets hourly, but no automated link from a vibration excursion to the dependent asset it will take down. |
| P2 | **Maintenance Planner** | `erp_work_orders`, `maintenance_logs`, `work_order_parts_edge` | 102 CRITICAL work orders; 104 CANCELLED. Cannot tell which cancellations were deferrals that will resurface. |
| P3 | **Mine Safety & Health Manager** | `safety_incidents`, `biometric_fatigue_logs`, `radio_communications`, `incident_involvements` | 3,340 fatigue readings and 573 radio transcripts arrive faster than any human can triage; incidents are reconstructed after the fact. |
| P4 | **Supply Chain / Procurement Manager** | `inventory_levels`, `rfp_items`, `procurement_bids`, `bid_parts_edge`, `MiningSupplyChainGraph` | 15 parts below ROP against 15.3-day average lead time; 300 bids to evaluate with no linkage back to the work orders that need the parts. |
| P5 | **Resource Geologist** | `drill_holes`, `drill_assay_logs`, `geological_block_models` | 295 assay intervals vs 1,000 modelled blocks — reconciliation is manual and episodic. |
| P6 | **Metallurgist / Concentrator Superintendent** | `metallurgical_recovery`, `crusher_states` | Recovery ranges 88–96% with feed and tailings grade recorded, but no closed loop from crusher settings to recovery outcome. |
| P7 | **Mine Ops / Dispatch Supervisor** | `fleet_vehicles`, `haulage_routes`, `operator_vehicle_assignments` | `congestion_factor` and `average_cycle_time_mins` exist per route but are not acted on within the shift. |

**Cross-cutting:** P1–P7 all escalate to a Shift Superintendent. That escalation path is what the Pattern A swarms model.

---

## MECE issue tree

**Root (re-rooted):** *Realised value per ton of ore is below plan.*

The published playbook roots Mining at "Unplanned Mill Downtime & Ore Recovery Margin Loss," which is one branch of this problem, not its root. Because the ask spans the whole site rather than the mill, the root is promoted and re-decomposed. Per the re-rooting rule, codes are taken **up then down** from published PCF parents rather than sub-indexed off a leaf.

Every dollar of the value gap lands in exactly one branch:

```
Realised value per ton below plan
├── B1  Ore not moved            — asset unavailable                    APQC 11.0.3
├── B2  Ore moved inefficiently  — asset available, under-producing     APQC 4.3.1
├── B3  Wrong ore moved          — grade/block model misprediction      APQC 2.0.1
├── B4  Metal lost in processing — recovery below achievable            APQC 4.2.2
├── B5  Cost of keeping it running — spares, procurement, contractors   APQC 4.1.2 / 5.2.1
└── B6  Licence to operate lost  — safety, fatigue, environmental       APQC 9.1.2
```

**MECE check.** B1 and B2 are disjoint on availability: B1 is the asset being down, B2 is the asset being up and under-performing. B3 is disjoint from B4 on locus: B3 is value never delivered to the plant, B4 is value delivered and then lost inside it. B5 is spend, not tons — no overlap with B1–B4. B6 is stoppage by consequence rather than by mechanism, and is the only branch whose trigger is regulatory or human rather than physical.

| Branch | Root-cause driver | APQC | Owning persona | Grounding tables | Graph | BQML |
|---|---|---|---|---|---|---|
| **B1** | Bearing/vibration degradation and cascading dependency trips | 11.0.3 | P1, P2 | `telemetry_stream`, `crusher_states`, `asset_dependencies`, `maintenance_logs`, `simulation_runs` | `MiningAssetGraph` | `downtime_regression_model` (+ `_crusher`/`_mill`/`_pump`) |
| **B2** | Haul cycle time inflation and route congestion | 4.3.1 | P7 | `fleet_vehicles`, `haulage_routes`, `operator_vehicle_assignments` | — | `asset_clustering_model` |
| **B3** | Assay-to-block-model grade variance and dilution | 2.0.1 | P5 | `drill_holes`, `drill_assay_logs`, `geological_block_models` | — | — |
| **B4** | Feed-grade/crusher-setting drift against recovery | 4.2.2 | P6 | `metallurgical_recovery`, `crusher_states` | — | — |
| **B5** | Stockout-driven work-order delay and bid mis-award | 4.1.2 / 5.2.1 | P4, P2 | `inventory_levels`, `erp_work_orders`, `procurement_bids`, `rfp_items`, edge tables | `MiningSupplyChainGraph` (711 edges) | `inventory_impact_model` |
| **B6** | Operator fatigue and procedural non-compliance | 9.1.2 | P3 | `safety_incidents`, `biometric_fatigue_logs`, `radio_communications`, `incident_involvements` | `MiningOperationsSafetyGraph` (3,350 edges) | `safety_model` |

`MiningOntologyGraph` and `unstructured_docs_metadata` are **not** a seventh branch. They are cross-cutting grounding, exposed as ADK tools to agents in every branch — which is how Pattern C capability enters this build without Pattern C agents.

---

## Candidate agents and pattern classification

Applying the decision tree in `agent-patterns.md` to each branch.

### Where Pattern A is genuinely earned

A swarm is justified only where the problem needs **more than one department's data and judgement**. Three places in this dataset clear that bar on structure, not assertion:

- **B1 → B5:** a predicted mill failure is worthless without knowing whether the spare exists. The path `Asset → WorkOrder → SparePart → ProcurementBid` is a real traversal in `MiningSupplyChainGraph`, crossing reliability, maintenance, and procurement.
- **B6 → B2:** a fatigued operator is a safety fact and a dispatch decision. `Operator → Vehicle → Incident` traverses `MiningOperationsSafetyGraph`, crossing safety and operations.
- **B3 → B4:** grade delivered versus metal recovered spans geology and metallurgy, joined on nothing but the ore itself.

### Candidate inventory by branch

| Branch | Pattern A swarms | Pattern B deep agents | `hitl_required` cases |
|---|---|---|---|
| B1 Availability | Cascading Failure & Recovery swarm; Shutdown Readiness swarm | Vibration anomaly, thermal drift, torque signature, dependency-impact, downtime forecast, work-order triage, deferral-risk | Shutdown trigger, work-order release |
| B2 Haulage | Shift Dispatch Re-plan swarm | Cycle-time variance, congestion, payload utilisation, route optimiser, operator-assignment fit | Dispatch re-plan commit |
| B3 Geology | Reconciliation swarm (with B4) | Assay-to-block variance, dilution, lithology classifier, drill-coverage gap, grade-confidence scorer | — (read-only) |
| B4 Processing | *(shares B3 swarm)* | Recovery variance, feed-grade sensitivity, tailings-loss, crusher-setting optimiser, concentrate-quality | Crusher setpoint change |
| B5 Supply chain | Stockout-to-Award swarm; Bid Evaluation swarm | Safety stock/ROP, EOQ, lead-time risk, criticality-weighted stocking, bid compliance, bid scoring, spend anomaly | PO raise, bid award |
| B6 Safety | Fatigue Intervention swarm; Incident Investigation swarm | Fatigue scoring, microsleep detection, radio sentiment/emergency triage, incident clustering, root-cause corroboration, compliance-drift | Stand-down of operator, incident escalation |

Every candidate above traces to a persona pain in the table at the top. There are no agents in this list that exist because they sound impressive; the three playbook agents whose data does not exist here (tailings piezometer, LOTO permit, EPC contractor overrun) were dropped rather than carried forward on invented data.

---

## The counting convention — decision required before Phase 1

This is the one structural choice that changes the entire build, so it is stated rather than assumed.

The dataset richly supports roughly **40–50 genuinely differentiated top-level agents**. Reaching 100 is achievable two ways:

| | **Option 1 — count ADK agent instances** *(recommended)* | **Option 2 — 100 top-level agents** |
|---|---|---|
| Structure | ~12 swarms × (1 coordinator + 4 specialists) = 60, plus ~40 Pattern B deep agents | 100 independently registered agents |
| Honesty at demo | Every agent has real grounding and a real job inside its swarm | ~50 agents would be thin slices of the same query |
| Reference-accelerator value | High — shows genuine A2A delegation and peer critique, which is what a swarm demo must prove | Low — a wide registry that reviewers will read as padding |
| Registry footprint | 12 swarm entrypoints + 40 deep agents registered; specialists are sub-agents | 100 registry entries |

Option 1 is the recommendation. It reaches 100 ADK agents without a single fabricated grounding, and it is the structure that makes the swarm story demonstrable rather than asserted — which matters because swarms are half of what you asked to showcase.

**Open question for the gate:** confirm Option 1, or state the counting rule you want, before the Phase 1 PRD fixes the inventory.
