# BigQuery Data Agent Showcase — PRD & Prompt Scripts (v2)

**What changed in v2.** The data catalog now carries business descriptions
for all 10 tables and 59 key columns (`scripts/enrich_catalog.py`), and the
agent's instruction includes a mining glossary (head grade, CSS, reclaim
buffer, stock-out risk, laycan, TML, demurrage). The v2 prompts therefore
speak pure business language — no prompt names a column — and the catalog
does the translating on camera. That is itself the governance story: the
catalog teaches the agent the business's vocabulary.

**What this is.** Four demo scenarios run *entirely inside BigQuery Data
Agents* — conversational prompts over `mining_data`, no custom agents, no
code. The star is BigQuery: grounded answers, native forecasting/anomaly
detection, and multi-table reasoning, live.

**Format per scenario:** the business setup a presenter says aloud, the
prompt script (typed verbatim into the data agent), the data it exercises,
impact and feasibility ratings, and the demo-day cross-check (a ground-truth
query whose numbers the agent's answers must reconcile with — computed live,
never memorised).

---

## S1 · Grade Reconciliation — "Where is the block model lying to us?"
*(catalogue A1 · Impact: $5–15M/yr class · Complexity: L2 multi-table reconciliation)*

**Setup line.** "The block model told us what we'd dig. The assay lab told
us what we actually dug. The gap between them is misclassified ore — sent
to the wrong destination at real cost. Watch the data agent find it."

**Prompt script** *(v2 — business language; the catalog does the translating)*
1. `What is our planned head grade by rock type, and how many blocks does the resource model hold?`
2. `What head grades did the assay lab actually measure, by logged rock type?`
3. `Reconcile planned against assayed head grade by rock type. Where is the resource model most wrong, in percentage points?`
4. `For that rock type: how many blocks are affected, and what is the estimated contained metal at risk if the assayed grade is the truth? Show the calculation.`
5. `Three sentences for the mine GM: what is misestimated, by how much, and the first corrective action.`

**Data:** `geological_block_models` (1,000) ⟷ `drill_assay_logs` (295) via lithology/geology code.
**Feasibility:** HIGH — both tables populated, shared categorical key, simple aggregates.
**Cross-check:** est-vs-actual mean grade per lithology; the gap the agent names must match SQL to 2dp.

---

## S2 · Live Anomaly Hunt — "25,946 sensor readings, one question"
*(catalogue C2 · Impact: $2–10M/yr class · Complexity: L3 native anomaly detection)*

**Setup line.** "This is the largest table on the site — every sensor
reading from the plant. Nobody reads it. The data agent does."

**Prompt script** *(v2 — business language; the catalog does the translating)*
1. `What does our plant telemetry cover, and how many readings per instrument metric?`
2. `Trend the busiest metric as a daily average. Any drift a reliability engineer should worry about?`
3. `Hunt for anomalous readings across the plant: anything beyond three standard deviations for its metric. How many, and which assets are the worst offenders?`
4. `For the worst offender: show its anomalies in time order. Developing fault or bad sensor? Argue from the data.`
5. `Write tomorrow morning's shift-handover paragraph for the plant supervisor.`

**Data:** `telemetry_stream` (25,946).
**Feasibility:** HIGH — single wide table; statistical outliers verified to exist before demo.
**Cross-check:** outlier count at z>3 per metric; the agent's count must match SQL.

---

## S3 · Parts-to-Failure Graph — "Which stock-out stops which machine?"
*(catalogue D2 · Impact: $2–8M/yr class · Complexity: L4 graph traversal in SQL)*

**Setup line.** "This is a graph question: parts connect to work orders,
work orders connect to machines. A stock-out on a $200 part can idle a
$20M asset. The agent walks the graph."

**Prompt script** *(v2 — business language; the catalog does the translating)*
1. `Which spare parts are at stock-out risk right now, and what are their supplier lead times?`
2. `Which maintenance work orders historically consumed those at-risk parts?`
3. `Which assets did that maintenance repair, and what has each asset cost us in repairs through those parts?`
4. `Rank the assets most exposed if we stock out this week — weigh the number of at-risk parts, the repair cost history, and the longest supplier lead time. Explain the ranking.`
5. `We can expedite three purchase orders. Which parts, and why those three?`

**Data:** `spares_inventory` (105) → `work_order_parts_edge` (186) → `erp_work_orders` (500).
**Feasibility:** MEDIUM-HIGH — the two-hop chain is verified non-empty; graph is shallow (186 edges) so depth is honest, not implied.
**Cross-check:** exposed-asset list from the two-hop SQL join; agent's ranking keys must appear in it.

---

## S4 · Pit-to-Port Cascade — "Crusher down six hours: who pays at the port?"
*(catalogue G1 · Impact: $5–20M/event class · Complexity: L5 four-hop cross-domain chain)*

**Setup line.** "One machine hiccups at the pit; three weeks later a ship
owner sends a demurrage invoice. Four systems apart. Watch one question
walk the whole chain."

**Prompt script** *(v2 — business language; the catalog does the translating)*
1. `What is the crusher's average feed rate, and how often is it running in bypass?`
2. `A six-hour crusher outage at that feed rate: how many tonnes of production do we lose?`
3. `How many hours of reclaim buffer does each stockpile hold before running empty, and which run out first?`
4. `Trace the exposure downstream: which rail consists load from the at-risk stockpiles, and which vessels do those consists feed?`
5. `For those vessels: demurrage days on record, tonnes loaded, and the demurrage exposure if loading slips a day — state your day-rate assumption as a range.`
6. `Five lines for the logistics manager: the chain from crusher to vessel, the first bottleneck, and the single action that buys the most time.`

**Data:** `crusher_states` (167) → `stockpiles` (60) → `rail_schedules` (120) → `port_vessels` (via `UNNEST(consist_ids)`).
**Feasibility:** MEDIUM — the chain is real (array join verified); the 6-hour outage is a stated hypothetical, and the prompt makes the agent state its rate assumption as a range rather than invent a price.
**Cross-check:** the stockpile→consist→vessel chain from SQL; every vessel the agent names must appear in the chain, and demurrage_days must match.

---

## Evaluation gates (per scenario, before demo day)
1. **Unit tests** (`tests/showcase/test_bq_scenarios.py`): tables populated,
   join paths non-empty, signal exists (a gap / outliers / exposed assets /
   a complete chain), ground truth computable. No hardcoded expectations —
   properties only, computed live.
2. **Business-lens review**: run the ground truth, read the actual numbers,
   and answer: would a GM/plant super/logistics manager act on this? If the
   numbers are trivial or absurd, the scenario is rewritten before it is
   ever demoed.

---

## Validation results (gates run 2026-08-26 — recompute live on demo day)

**Unit tests: 10/10 pass** (`tests/showcase/test_bq_scenarios.py`). One data
defect found and repaired en route: `rail_schedules.origin_stockpile_id`
carried unpadded IDs (`SP-01-1`) against zero-padded stockpiles (`SP-01-01`)
— the stockpile deepening re-minted IDs and the rail table never followed.
The four-hop cascade was silently empty until the key was canonicalised.

**Business-lens verdicts (live numbers at validation):**

- **S1 — CREDIBLE.** The model *underestimates* BASALT: 1.087% est vs
  1.192% assayed across 182 blocks (~10% relative). Story: ore risked
  being routed as waste — the right direction of error for a demo, and a
  believable magnitude.
- **S2 — CREDIBLE.** 37 vibration_hz readings beyond 3σ, concentrated on
  one asset — reads as a developing mechanical fault, not sensor noise.
- **S3 — ACTIONABLE.** CRUSHER-03 tops the exposure ranking: 5 at-risk
  parts, ~$277k historical repair cost through those parts, 14-day worst
  lead time. A maintenance manager would expedite exactly this.
- **S4 — THE DEMO MOMENT.** SP-02-01 holds 6.2 hours of reclaim buffer —
  against the scenario's 6-hour crusher outage. Razor-thin by nature, not
  by design. It feeds 9 vessels with 10 demurrage-days already on record
  downstream. The presenter's line writes itself: *"your buffer is six
  hours; the outage is six hours."*

All four proceed. Prompts are demo-ready as written.
