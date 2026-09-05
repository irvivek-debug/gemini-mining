# Phase 2 — UX Screens

**Scope:** screens for the 100-agent inventory approved in Phase 1.
**Design system:** `ui-ux-design-system` — dark-mode-first, ultra-matte, M3 tokens. All token names below are literal.

> **GATE.** Approve before Phase 3 (design doc / data model / access model).

---

## 1. The screen-count decision

100 agents does not mean 100 screens. Applying the per-agent test from the workflow:

| Condition | Agents | Screen? |
|---|---|---|
| Pattern A | 60 (12 swarms) | Yes — swarm console |
| Pattern B, operator in the loop | 40 | Yes — departmental workbench |
| Pattern B, headless/scheduled | 0 | — |
| `hitl_required: true` | 14 | Yes, always — approval surface mandatory |

Every agent needs a surface, but they collapse into **5 screen archetypes**. For a reference accelerator this is the load-bearing decision: 100 bespoke screens is unmaintainable and unforkable; 5 templates with data-driven configuration is the thing a customer can actually adopt.

| # | Archetype | Instances | Serves |
|---|---|---|---|
| **SC-1** | Site Cockpit | 1 | Entry point; navigation across all 100 agents |
| **SC-2** | Swarm Console | 12 configs | All 12 Pattern A swarms (60 agents) |
| **SC-3** | Departmental Workbench | 7 configs | All 40 Pattern B agents, grouped by persona |
| **SC-4** | HITL Approval Sheet | 14 bindings | Every `hitl_required: true` agent |
| **SC-5** | Shift Handover Brief | 1 | S12 only — read-only, cross-branch |

SC-4 is a modal sheet invoked from SC-2 and SC-3, not a standalone destination. An approval that lives on a separate page separates the decision from its evidence, which is exactly the failure Hold-to-Confirm exists to prevent.

---

## 2. Journey Scaffolding Briefs

Environmental constraints per persona. These drive layout, not preference.

| Persona | Operational context | Device real estate | Stress profile | Design consequence |
|---|---|---|---|---|
| P1 Reliability Engineer | Control room, quiet, conditioned | Dual desktop monitor | **Low–Medium** | Dense multi-panel bento; hover permitted |
| P2 Maintenance Planner | Planning office | Desktop monitor | **Low** | Dense tables, bulk selection |
| P3 Safety & Health Manager | Mixed — office, pit, muster point. Variable lighting, PPE gloves | 10" rugged tablet **and** desktop | **HIGH** | Single-column on tablet; no hover-dependent controls; ≥ 44×44px targets enforced hard; fewest choices per screen of any persona |
| P4 Supply Chain / Procurement | Office | Desktop monitor | **Low** | Dense tables, comparison views |
| P5 Resource Geologist | Core shed + office | Laptop / desktop | **Low** | Chart-heavy, spatial |
| P6 Metallurgist | Plant control room + concentrator floor. **High ambient noise**, hearing protection | Control-room monitor + handheld | **Medium** | No audio-only alerts, ever; setpoint changes gated |
| P7 Dispatch Supervisor | Control room, 24/7, rotating shift | Overhead display + handheld | **HIGH** | Overhead-legible type scale; glanceable state; single decisive action per card |
| P8 Shift Superintendent | Handover room, time-boxed | Desktop + mobile | **Medium** | Print/export must work; state must persist across shifts |

**Two constraints bind the whole design:**

1. **P3 and P7 are high-stress and partly handheld.** Their screens set the floor for the design system, not the average. Where P3 or P7 touch a surface, it degrades to single-column and hover-free.
2. **P6 works in hearing protection.** No agent may signal state through sound alone anywhere in the suite — a rule that costs nothing to honour and is invisible until it is violated.

---

## 3. SC-1 — Site Cockpit

The navigation problem is real: 100 agents will not fit in a list a human can scan. Three axes are provided, matching how the three audiences actually think.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  MINING AGENT SUITE          Project: your-gcp-project-id             │  ← control stack
│  Dataset: mining_data · US   Agents: 100 (60 swarm / 40 deep)            │     bg-base
├──────────────────────────────────────────────────────────────────────────┤
│  [ BY PERSONA ]  [ BY PROCESS ]  [ BY VALUE BRANCH ]        ⌕ search     │  ← 3 nav axes
├──────────────────────────────────────────────────────────────────────────┤
│ ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐    │
│ │ ● P3 SAFETY        │ │ ● P4 SUPPLY CHAIN  │ │ ● P1 RELIABILITY   │    │  ← bento grid
│ │ 21 agents          │ │ 18 agents          │ │ 16 agents          │    │     gap: 16px
│ │ 6 deep · 3 swarms  │ │ 8 deep · 2 swarms  │ │ 6 deep · 2 swarms  │    │     surface-container
│ │ ⚠ 4 HITL pending   │ │   1 HITL pending   │ │   0 HITL pending   │    │     border-crisp 1px
│ │ APQC 9.1.2         │ │ APQC 4.1.2 / 5.2.1 │ │ APQC 11.0.3        │    │
│ └────────────────────┘ └────────────────────┘ └────────────────────┘    │
│ ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐    │
│ │ ● P6 METALLURGY 11 │ │ ● P5 GEOLOGY    10 │ │ ● P7 DISPATCH   10 │    │
│ └────────────────────┘ └────────────────────┘ └────────────────────┘    │
│ ┌────────────────────┐ ┌────────────────────┐                           │
│ │ ● P2 MAINTENANCE 9 │ │ ● P8 SHIFT SUPT  5 │                           │
│ └────────────────────┘ └────────────────────┘                           │
└──────────────────────────────────────────────────────────────────────────┘
```

- Cards ordered by agent count descending — Safety leads, which is the correct thing for a mine site to see first.
- `⚠ N HITL pending` uses `status-warning` **plus** the ⚠ glyph **plus** the word "pending". Three redundant channels, per the colour-independence rule.
- Card roundedness `0px` (structural). Status pills `Full`. Search field `4px`.
- Type: header `Bricolage Grotesque` 24px/700; counts `JetBrains Mono` 13px/500; label caps `JetBrains Mono` 11px/700 uppercase.

**BY PROCESS** re-buckets the same 100 into the seven APQC codes. **BY VALUE BRANCH** buckets into B1–B6. Same data, three lenses — a customer forking this maps their own org onto one of the three without touching agent code.

---

## 4. SC-2 — Swarm Console (12 configurations)

Pattern A's non-negotiable requirement: **the operator must be able to tell which agent is blocked and why.** A swarm that reports only its final answer is indistinguishable from a single agent, which defeats the entire demo.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ← Site Cockpit    S01 · CASCADING FAILURE IMPACT & RECOVERY              │
│                   APQC 11.0.3 · P1 Reliability · ⚠ HITL REQUIRED         │  ← status-warning
├───────────────────────────────────┬──────────────────────────────────────┤
│  AGENT STATE & HANDOFFS           │  EXECUTION TRACE                     │
│                                   │  JetBrains Mono 12px                 │
│  ┌─ Coordinator ────────────────┐ │  surface-container                   │
│  │ ● RUNNING   step 3 of 4      │ │                                      │
│  └──────────────┬───────────────┘ │  10:04:11 [coord] plan: 4 specialists│
│                 │ A2A             │  10:04:12 [S1] BigQuery:             │
│    ┌────────────┼────────────┐    │    SELECT asset_id, metric_value     │
│    ▼            ▼            ▼    │    FROM mining_data.telemetry_stream │
│  ┌──────┐  ┌──────┐  ┌──────┐    │    WHERE metric_name='vibration_hz'  │
│  │  S1  │  │  S2  │  │  S3  │    │    → 4008 rows                       │
│  │ ✓DONE│  │ ✓DONE│  │●BLOCK│    │  10:04:15 [S1] anomaly PUMP-104A     │
│  │Anomly│  │Blast │  │Fcast │    │    vibration 12.5→19.8 Hz (+58%)     │
│  │ 1.2s │  │Radius│  │ ⚠    │    │  10:04:16 [S2] GRAPH_TABLE(          │
│  └──────┘  │ 0.9s │  └──┬───┘    │    MiningAssetGraph) → 3 dependents   │
│            └──────┘     │        │  10:04:19 [S3] ⚠ BLOCKED             │
│                 ┌───────▼──────┐ │    downtime_regression_model_pump:    │
│                 │  S4 CRITIC   │ │    no rows for asset in window        │
│                 │  ○ WAITING   │ │  10:04:19 [coord] awaiting S3         │
│                 │  on S3       │ │                                      │
│                 └──────────────┘ │  [ ⏸ pause ]  [ ⧉ copy trace ]       │
├───────────────────────────────────┴──────────────────────────────────────┤
│  ⚠ S3 BLOCKED — Downtime Duration Forecaster                             │
│  Reason: BQML model returned no rows for PUMP-104A in the requested       │
│  window. Coordinator cannot produce a recovery plan without a duration.   │
│  [ retry with widened window ]   [ proceed without forecast ]            │
└──────────────────────────────────────────────────────────────────────────┘
```

**Rules this encodes:**

- **Blocked is a first-class state**, surfaced in the graph *and* explained in a dedicated band with named remedies. "Which agent is blocked and why" is answered without reading the trace.
- Agent states are `✓ DONE` (`status-success`), `● RUNNING` (`accent-primary`), `⚠ BLOCKED` (`status-critical`), `○ WAITING` (`on-surface-variant`). Glyph + word + colour on every one.
- The **Critic is drawn downstream of the specialists it audits**, not as a peer. The topology itself communicates that critique happens after analysis.
- The execution trace shows **real SQL and real row counts**. This is what converts "we used a graph" from a claim into a demonstration, and it is the single highest-value element on the screen for a technical buyer.
- Trace is `JetBrains Mono` 12px/500 on `surface-container`, target 7:1 contrast (critical telemetry).

Nine of twelve swarms carry HITL; on those the coordinator's terminal step opens **SC-4** rather than writing directly.

---

## 5. SC-3 — Departmental Workbench (7 configurations)

Pattern B's non-negotiable requirement: **show the computed result and its inputs.** A number with no provenance is not actionable in an industrial setting.

Shown for P4 Supply Chain, D27 Safety Stock & Reorder Point Calculator — the clearest case, because the output is a deterministic number an engineer will challenge.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ← Site Cockpit   P4 SUPPLY CHAIN WORKBENCH            8 deep · 2 swarms  │
├──────────┬───────────────────────────────────────────────────────────────┤
│ AGENTS   │  D27 · SAFETY STOCK & REORDER POINT CALCULATOR               │
│          │  APQC 4.1.2 · deterministic · read-only                       │
│ ▸ D27 ●  ├───────────────────────────────────────────────────────────────┤
│   D28    │  RESULT                          INPUTS  (provenance)         │
│   D29    │  ┌─────────────────────────┐    ┌────────────────────────────┐│
│   D30 ⚠  │  │ 15 of 103 parts         │    │ mining_data.inventory_levels││
│   D31    │  │ below reorder point     │    │  stock_level               ││
│   D32    │  │                         │    │  reorder_point_limit       ││
│   D33    │  │ 6 are CRITICAL-asset    │    │  lead_time_days   μ = 15.3 ││
│   D34    │  │ parts                   │    │ mining_data.assets         ││
│          │  └─────────────────────────┘    │  criticality_rating        ││
│ SWARMS   │                                  │ work_order_parts_edge      ││
│   S08 ⚠  │  METHOD                          │  → demand rate μd          ││
│   S09 ⚠  │  ROP = μd × LT + SS              └────────────────────────────┘│
│          │  SS  = Z(0.95) × σd × √LT                                     │
│          │  Z = 1.645 · service level 95%                                │
│          ├───────────────────────────────────────────────────────────────┤
│          │  PART      STOCK  ROP  GAP  LEAD  ASSET CRIT   EXPOSURE       │
│          │  PN-4471      12   28  -16   21d  MILL-01  ●   $84,200        │
│          │  PN-0912       3   19  -16   30d  CRUSH-03 ●   $61,400        │
│          │  …                                                            │
│          ├───────────────────────────────────────────────────────────────┤
│          │  EXECUTION TRACE          JetBrains Mono 12px                 │
│          │  10:12:03 SELECT part_number, stock_level, reorder_point_limit│
│          │           FROM mining_data.inventory_levels → 103 rows        │
│          │  10:12:04 JOIN assets ON criticality_rating → 6 CRITICAL      │
└──────────┴───────────────────────────────────────────────────────────────┘
```

**Rules this encodes:**

- **The formula is on screen.** For deterministic agents (D27, D28, and the Cpk/OEE/Little's Law family) the method is the provenance. Hiding it behind "the agent calculated" is what makes an engineer distrust the whole suite.
- **Inputs panel names table and column**, not "inventory data". Every claim resolves to `dataset.table.column`.
- Left rail lists the persona's agents with `⚠` on the HITL ones, so an operator knows before clicking which agents can change something.
- Same execution-trace console as SC-2 — one component, two hosts.

Seven configurations, one per persona. P3's and P7's configurations collapse the three-panel layout to **single column** on tablet and drop the left rail into a top selector, per their journey briefs.

---

## 6. SC-4 — HITL Approval Sheet (14 bindings)

Invoked as a modal over SC-2 or SC-3. `surface-highest`.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  APPROVAL REQUIRED                                              [ esc ✕ ] │
│  S10 · Fatigue Intervention — STAND DOWN OPERATOR                        │
├──────────────────────────────────────────────────────────────────────────┤
│  ACTION                                                                  │
│  Remove OP-014 from HAUL-07 for the remainder of NIGHT shift 2026-06-16. │
│  This writes to operator_vehicle_assignments and notifies dispatch.       │
│                                                                          │
│  AGENT REASONING             ← CoT exposed BEFORE confirmation (required) │
│  S1 Fatigue Scorer: sleep_deficit_hours 6.4 (P95 threshold 4.0)          │
│  S2 Microsleep Escalator: 3 events in trailing 2h; fatigue_alert = true  │
│  S3 Shift Coverage: OP-019 available, certified HAUL-07, 0 fatigue flags │
│  S4 Critic: CONCURS. Notes S3 coverage assumes OP-019 has not exceeded   │
│     consecutive-shift limit — not verifiable from available data.        │
│                                                                          │
│  ⚠ UNVERIFIED: consecutive-shift limit for OP-019                        │
│                                                                          │
│  SOURCES  biometric_fatigue_logs · operator_vehicle_assignments ·        │
│           safety_model                                                   │
├──────────────────────────────────────────────────────────────────────────┤
│         ┌──────────────────────────────────┐                            │
│   [ Cancel ]   │ ⏻  HOLD TO STAND DOWN     │  ← 2s hold, progress stroke │
│                └──────────────────────────────┘     around perimeter     │
│                                                                          │
│  Approving as: reliability.lead@example.com · logged to audit trail      │
└──────────────────────────────────────────────────────────────────────────┘
```

**Mandated behaviour:**

| Requirement | Implementation |
|---|---|
| Hold duration | **2 seconds**, animated progress stroke around button perimeter |
| CoT + telemetry exposed before confirm | Full specialist reasoning shown above the button, not behind a disclosure |
| Colour independence | Icon `⏻` + literal verb "HOLD TO STAND DOWN" + `status-critical` |
| Touch target | ≥ 44×44px; ≥ 8px safety gutter between Cancel and the hold button |
| Keyboard | Focusable; `Space` held for 2s; visible 1px `accent-primary` focus outline |
| No safe colour on dangerous action | The confirm control is **never** `status-success` |
| No confirmshaming | Cancel reads "Cancel" — not "No, I don't care about safety" |

**Audit trail record** (schema is our latitude; the design system mandates the exposure, not the format):

```
approval_id · agent_id · action_type · target_entity · decision (APPROVED|CANCELLED)
approver_principal · decided_at · hold_duration_ms · agent_reasoning_snapshot
unverified_flags[] · source_tables[]
```

`agent_reasoning_snapshot` is stored, not re-derived. Six months later the question is *what did the agent say at the time*, and a re-run against changed data cannot answer it.

**The `⚠ UNVERIFIED` band is the most important element on this sheet.** When the Critic cannot confirm something, it surfaces above the confirm control rather than being smoothed away. This is what stops the suite from being a confidence machine — and it is the concrete answer to the `root_cause` risk flagged in the PRD.

---

## 7. SC-5 — Shift Handover Brief (S12)

Read-only, `hitl_required: false`, must print and must persist across shifts.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  SHIFT HANDOVER   NIGHT → DAY   2026-06-16 06:00      [ ⎙ print ][ export ]│
├──────────────────────────────────────────────────────────────────────────┤
│  AVAILABILITY (B1)        PRODUCTION (B2/B3/B4)      SAFETY (B6)         │
│  ● PUMP-104A degrading    Recovery 91.4% (−0.8 pt)   ⚠ 1 stand-down      │
│    vibration +58%           feed grade within model    OP-014 fatigue     │
│  ○ 21 CRITICAL WO open    Cycle time +6% RT-03       ○ 0 incidents       │
│                             congestion_factor 1.34                       │
├──────────────────────────────────────────────────────────────────────────┤
│  ⚠ OMISSION CRITIC — what this brief does NOT cover                      │
│  · CONVEYOR-02 and TRUCK-08 have no telemetry in this window.            │
│    Their availability is UNKNOWN, not nominal.                           │
│  · Recovery compared against time only; single concentrator, no peer.    │
└──────────────────────────────────────────────────────────────────────────┘
```

The **Omission Critic band is the point of this screen.** A handover that silently omits two assets is more dangerous than one that reports nothing, because the reader assumes coverage. The fourth specialist in S12 exists to produce this band, and it renders even when empty ("no known gaps").

---

## 8. Design chamber — 3-persona review

Run per the design system. Stage 3 is the stage that changed the design, so it is recorded rather than asserted.

**Stage 1 — Sr. UX (Journey Scaffolding):** §2. Established P3/P7 high-stress handheld as the binding constraint and P6's hearing protection as a suite-wide rule.

**Stage 2 — Jr. UX (Component & Layout):** §§3–7. Bento grid, 16px gap, `surface-container` cards, 1px `border-crisp`, no shadows, no gradients, dark-mode-first.

**Stage 3 — UX Auditor (Usability & Friction).** Findings and resolutions:

| # | Finding | Severity | Resolution |
|---|---|---|---|
| A1 | SC-2 three-panel layout is unusable on P7's handheld during a shift re-plan | High | S04/S05 configs collapse to single column; agent graph becomes a vertical stack; left rail → top selector |
| A2 | SC-3 left rail relies on hover to reveal agent descriptions — fails on tablet and for P3 | High | Descriptions inline; no hover-dependent content anywhere in the suite |
| A3 | Hold-to-Confirm placed adjacent to Cancel risks mis-tap in gloves | High | 8px minimum safety gutter enforced; Cancel is text-only, confirm is filled — different visual weight, not just different colour |
| A4 | Execution trace at 12px `JetBrains Mono` fails 7:1 on `surface-container` at the lighter grey | Medium | Trace body uses `on-surface` `#E4E2E1`, not `on-surface-variant`; only timestamps use the variant |
| A5 | `⚠ N HITL pending` on SC-1 could be read as an error rather than a queue | Medium | Copy fixed to "N awaiting approval"; `status-warning` not `status-critical` |
| A6 | SC-5 renders nothing when the Omission Critic finds no gaps — reads as a missing feature | Medium | Band always renders; empty state reads "No known coverage gaps in this window" |
| A7 | Overhead display for P7 at 14px body is illegible at distance | Medium | P7 config uses a 1.5× type scale; body 21px, telemetry 18px |
| A8 | Nothing indicates which of 100 agents are currently running | Low | SC-1 cards carry a live running count; `accent-primary` dot |

**Stage 4 — Handoff:** the 5 archetypes above, with token names literal and the 8 audit resolutions incorporated.

---

## 9. Explicitly not done here

- No colour beyond the token palette; no glassmorphism, gradients, drop shadows, or decorative illustration.
- No per-agent bespoke screens — 100 agents, 5 templates, data-driven configuration.
- No data model or access model — Phase 3.
- No component code — Phase 5.

---

## Gate

Approve, or tell me what to re-cut. Phase 3 does not start until this is approved.
