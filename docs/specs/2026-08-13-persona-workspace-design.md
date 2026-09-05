# Persona workspace and plain language — design

**Date:** 2026-08-13
**Scope:** one new screen, one new backend route, two new shared modules, and a
copy rewrite across all ten screens of both applications.

---

## 1. The complaint

Two faults were reported, and the second makes the first worse.

**"It just feels like static agents."** The screens state that 52 agents are
deployed and callable, and then give the reader no way to call one. This is
literally true of the code: across all of `apps/` there is exactly one `fetch(`,
at `apps/workspace/workspace.js:95`, and it calls `/api/runtime` — the status
endpoint. `POST /api/invoke/{agent_id}` exists in `apps/workspace/server.py`,
works against the deployed agents, and is never called by any screen.

Worse, `notConnected()` in `workspace.js` renders from `DATA.workspace.runtime`,
a **build-time constant** baked into `bundle.js`. Five call sites
(`handover.js:67`, `hitl.js:111`, `hitl.js:209`, `workbench.js:161`,
`swarm.js:126`) therefore print "NOT CONNECTED" in production, where the service
is in fact connected to all 52 agents. The screen is not merely silent; it is
wrong in the pessimistic direction.

**"Too technical and too jargony."** The screens speak in the vocabulary of the
thing that built them — entrypoint, HITL, APQC, traversal, Pattern A, model
tier, p90, blast radius, SC-3. A functional reader needs the answer in their own
words, with tables, and the machinery available afterwards if they want it.

The instruction was explicit: plain language and tables first, technical detail
at the end, hidden behind a collapsible.

---

## 2. What gets built

**A persona page with a chat sidecar.** `apps/workspace/workbench.html` is
replaced by `apps/workspace/persona.html`. The reader picks a persona — the role
they hold — and gets one screen: on the left, what is true right now for that
role, drawn from the record and rendered instantly; on the right, a chat sidecar
that talks to that persona's own agents.

The left panel answers without being asked. The right panel answers when asked.
Neither invents a number.

Three screens are kept and de-jargoned rather than replaced: the cockpit
(`workspace/index.html`), the swarms screen (`swarm.html`), and the handover
sheet (`handover.html`). Handover additionally gains a Run button, because a
handover that cannot be run is a document about a capability rather than the
capability.

---

## 3. Architecture

```
browser                                  container                 Cloud Run
───────                                  ─────────                 ─────────
persona.html
 ├─ persona-panel.js ─ persona-data.js ─ bundle.js (no network — instant)
 └─ chat.js
      ├─ router.js      pick agent from this persona's own list
      └─ agent-stream.js ──► GET /api/stream/{id} ──► GET {svc}/run_sse
                                   (server.py)          (OIDC identity token)
                             ◄── text/event-stream ◄──
           plain.js  translates each event into one plain line
```

**Nothing new enters the container.** `/api/stream` uses `httpx`, already a
declared dependency, and the same `_services()` / `_identity_token()` functions
`/api/invoke` uses. `tests/test_workspace_image.py` continues to guarantee no
agent SDK reaches the image.

**Routing runs in the browser.** Deciding which of a persona's agents should take
a question is a string-matching problem over catalogue metadata already present
in `bundle.js`. Doing it server-side would mean either a model call — which puts
a model SDK in a container that exists to avoid one — or a network round trip for
a decision that needs no network.

---

## 4. The left panel — what's true now, from the record

Five blocks, all rendered synchronously from `window.MINING_DATA`. No spinner, no
fetch, no possibility of an empty state caused by the network.

Persona records live at `DATA.personas.personas[code]` with fields:
`code, title, accountable_for, pain_points, jobs_to_be_done, journey, agents,
value_branch, agent_count, hitl_agents`.

| # | Block | Heading on screen | Source |
|---|---|---|---|
| 1 | Accountability | "What you're answerable for" | `persona.accountable_for` (prose) |
| 2a | Branch signal | "What your part of the mine is doing" | `DATA.signals.branch_evidence[Bx]` |
| 2b | The gap | "An ordinary day against the best day" | `DATA.signals.gap.rows` |
| 3 | Machines | "The five machines this site instruments" | `DATA.signals.assets` |
| 4 | Sign-offs | "Waiting on your sign-off" | `persona.hitl_agents` |
| 5 | Jobs | "What you're trying to get done" | `persona.jobs_to_be_done` (collapsed) |

### 4.1 Block 2a — the branch signal

This is the one signal that maps to a persona **from the data rather than from a
guess**: `DATA.value_tree.branches[Bx].personas` names the personas of each
branch, and `DATA.signals.branch_evidence[Bx]` holds that branch's evidence.

| Branch | Personas | Evidence | Kind |
|---|---|---|---|
| B1 Asset availability and unplanned downtime | P1, P2 | MILL-01 power draw, MW, 1,996 readings, 3.6429–4.5323 | `series` |
| B2 Ore realisation — grade and dilution | P5 | Estimated grade across the block model, %, n=1000, 24 bins over 0.064–3.399 | `distribution` |
| B3 Processing recovery and throughput | P6 | Concentrator recovery rate, %, 167 readings, 89.1933–94.7133 | `series` |
| B4 Haulage productivity and cycle efficiency | P7 | TRUCK-08 payload, t, 1,997 readings, 165.8726–229.4862 | `series` |
| B5 Materials and procurement cost leakage | P4 | SKUs at or below reorder point, 17 of 105 | `share` |
| B6 Safety, fatigue and licence to operate | P3 | Fatigue alerts raised, 3,340 readings, 0–7 | `series` |

**Three render kinds, all of which must be handled** — a `kind` switch, not an
assumption that everything is a line:

- `series` → sparkline from `points`, with `min`/`max`/`readings`/`from`/`to`
- `distribution` → histogram from `bins` and `edges`, with `n`
- `share` → `part` of `whole`

Each carries a `caption` stating how it was reduced (e.g. *"1,996 readings
reduced to 64 points of equal duration; each point is the mean of its bucket"*).
**The caption renders verbatim.** A bucketed mean drawn without saying it is
bucketed invites the reader to read a precision that is not there.

**P8 (Shift Supervisor, `site_wide`) appears in no branch's `personas` list** and
therefore has no branch evidence. The block says so and falls through to 2b,
which is site-wide and does cover P8.

### 4.2 Block 2b — the gap, and the integrity rule that governs it

**The ordinary→best figures come from `DATA.signals.gap.rows` and nowhere else.**

`branch_evidence` is 64 bucket means. A p90 computed from 64 bucket means is
**not** the p90 of the underlying days, and printing it as one would be a
fabricated number wearing a statistic's clothes. `signals.gap` carries the real
figures, computed over the full record, with its own `method` string:

> "Each figure is a daily mean. The best day is the 90th percentile day and the
> ordinary day is the median day, across 167 days of recorded operation."

The four rows, verbatim (each also carries `column`, `days: 167`, a 167-point
`ladder`, a `benchmark`, and a `source`):

| id | label | asset | unit | ordinary (median) | best (p90) | delta | source table |
|---|---|---|---|---|---|---|---|
| `recovery` | Metallurgical recovery | — | % | 92.32 | 94.278 | 1.958 pts | `metallurgical_recovery` |
| `feed_rate` | Crusher feed rate | CRUSHER-03 | t/h | 1149.552 | 1247.7618 | +8.5433% | `telemetry_stream` |
| `payload` | Truck payload | TRUCK-08 | t | 204.5038 | 223.0208 | +9.0546% | `telemetry_stream` |
| `conveyor_load` | Conveyor load | CONVEYOR-02 | % | 77.7011 | 86.0013 | +10.6822% | `telemetry_stream` |

`gap.caveat` renders verbatim as a footnote — *"The gap is the size of the
opportunity, not a promise. Some of it is ore variability, weather and planned
work, and no amount of software recovers that part."* — as does `gap.excluded`
(PUMP-104A, held out because its widest-in-the-data 45% gap is a bearing
degrading, not an achievement). Excluding a series without saying so is the same
fault as inventing one.

**Gap rows carry no branch or persona field.** They have `asset_id`, `column` and
`source`. Attaching `payload` to the Mine Controller because a truck feels like
haulage would be exactly the guess §4.3 refuses for assets. The relevance rule is
therefore **derived**: a row is *yours* when at least one of your persona's agents
declares the row's source table in its `source_tables`. This is checkable, and it
is the same catalogue field the router scores on.

Computed against the live catalogue:

| Persona | Rows reached by that persona's agents |
|---|---|
| P1 Reliability Engineer | `feed_rate`, `payload`, `conveyor_load` |
| P2 Maintenance Planner | *none* |
| P3 HSE Lead | *none* |
| P4 Supply Planner / Procurement Lead | *none* |
| P5 Mine Geologist | `recovery` |
| P6 Metallurgist | all four |
| P7 Mine Controller | *none* |
| P8 Shift Supervisor | all four |

**No persona sees an empty block.** Rows the persona's agents reach render first
under "Your agents read these"; the remainder render below under "Also recorded
at this site", visibly separated. Four of eight personas have an empty first
group, and the copy says so plainly rather than promoting a site-wide row into a
personal one. That P7 does not reach the truck payload row is a real fact about
the catalogue — no P7 agent declares `telemetry_stream` — and surfacing it is
more useful than hiding it.

### 4.3 Block 3 — the machines, labelled as the site's

`DATA.signals.assets` holds exactly five entries:

| Asset | Metric | Unit | Field |
|---|---|---|---|
| MILL-01 | Power draw | MW | `power_draw_mw` |
| CRUSHER-03 | Feed rate | t/h | `feed_rate_tph` |
| CONVEYOR-02 | Belt tension | kN | `belt_tension_kn` |
| TRUCK-08 | Payload | t | `payload_tons` |
| PUMP-104A | Vibration | Hz | `vibration_hz` |

**No persona→asset mapping exists in the repository.** The heading therefore says
"the five machines this site instruments", not "your machines". Assigning
MILL-01 to the Reliability Engineer would be a plausible guess presented as a
fact, which is the specific failure this project keeps refusing.

### 4.4 Block 4 — sign-offs

`persona.hitl_agents` is a list of agent ids (P1 → `["S01"]`). Each renders as
the agent's plain purpose plus a one-click "Ask this one" that seeds the chat
sidecar. Where the list is empty (P5 Mine Geologist, P8 Shift Supervisor), the
block says so in a sentence rather than rendering an empty container.

### 4.5 Persona coverage and the two shape hazards

| ID | Title | value_branch | agents | hitl |
|---|---|---|---|---|
| P1 | Reliability Engineer | `asset_reliability` | 8 | 1 |
| P2 | Maintenance Planner | `maintenance_execution` | 5 | 2 |
| P3 | HSE Lead | `safety` | 9 | 4 |
| P4 | Supply Planner / Procurement Lead | `["supply_chain","procurement"]` | 10 | 3 |
| P5 | Mine Geologist | `geology` | 6 | 0 |
| P6 | Metallurgist | `processing` | 7 | 2 |
| P7 | Mine Controller | `mine_ops` | 6 | 2 |
| P8 | Shift Supervisor | `site_wide` | 1 | 0 |

**Hazard 1 — `value_branch` may be a string or a list.** P4 alone holds a list,
`["supply_chain","procurement"]`. Every read of `value_branch` — persona records
and agent records alike — goes through one helper,
`branchesOf(x) → string[]`, which wraps a bare string in an array. This is
stated because it already crashed an inspection script during design. It applies
to router scoring (§5.1); block 2a does **not** use it, because the B-code for a
persona comes from the reverse lookup `value_tree.branches[Bx].personas`, which
is uniformly a list of persona codes.

**Hazard 2 — P8 has exactly one agent.** The router's candidate set is then a
single element. It must still name its pick and state the reason; it must not
render a "change agent" control with nothing to change to.

### 4.6 `persona-data.js` — the derivations, separated from the rendering

Blocks 2a and 2b are two derivation rules with edge cases in every persona.
Leaving them inside the rendering code would make them testable only through the
DOM. They move into one pure module, no I/O and no DOM, taking `DATA` as an
argument so a test can pass a fixture:

```
branchesOf(x)                      -> string[]      // string-or-list normaliser (§4.5)
branchCodesFor(personaCode, DATA)  -> string[]      // reverse lookup via value_tree
branchEvidenceFor(personaCode, DATA)
    -> [{ code, branch, evidence }]                 // evidence.kind ∈ series|distribution|share
gapRowsFor(personaCode, DATA)
    -> { reached: row[], other: row[] }             // by source-table rule (§4.2)
starterQuestionsFor(personaCode, DATA)
    -> string[3]                                    // derived, never authored (§5.1)
```

`persona-panel.js` calls these and renders; it holds no rule of its own.

---

## 5. The chat sidecar

### 5.1 Router — `apps/workspace/router.js`

Pure function, no I/O, no DOM:

```
route(question, personaCode, DATA) -> { agent_id, reason, runners_up: [{agent_id, score}] }
```

Candidates are **only** the agents in `persona.agents`. A question asked from the
Reliability Engineer's page never routes to a procurement agent, because the
persona page is a claim about scope and silently leaving scope would break it.

Scoring is deterministic, over fields already in `DATA.catalog.agents[]`
(`display_name, apqc_names, source_tables, tools, traversals, value_branch,
hitl_required, swarm_role`). Question tokens are lowercased, stripped of
punctuation, and stop-worded; each token contributes to a candidate's score when
it matches that candidate's plain-language vocabulary (§6), weighted so a
traversal match outranks a table match, which outranks a tool match. Ties break
toward the swarm coordinator, then lowest agent id — so the function is total
and stable.

`reason` is a sentence built from the highest-weighted matched term, in plain
language: *"It reads the sensor readings and traces what else stops if a machine
stops."* The screen prints the pick, prints the reason, and offers a one-click
change to the runners-up. The user chose visible reasoning over a hidden
decision; when the router is wrong, being wrong in the open with a one-click fix
is the recovery path.

**Cold start.** No example questions exist anywhere in the catalogue. Starter
prompts are therefore **derived**, not authored: `starterQuestionsFor` (§4.6)
generates three per persona from that persona's agents' `traversals` and
`source_tables` via the same vocabulary map, so a starter can never reference a
capability the agent does not have. Because starters are built from the same
vocabulary the router scores on, a starter always routes to the agent it came
from — a property `router.test.js` asserts.

### 5.2 Streaming — `apps/workspace/agent-stream.js` + `/api/stream/{agent_id}`

A real question against S01 ("Which assets are most at risk right now?") was
measured over the wire at **103.8 seconds across 26 SSE events** — 10
`functionCall`, 10 `functionResponse`, 5 `text`, and `thoughtSignature` riding
along on 15 parts. A request/response spinner over that is indistinguishable
from a hang.

The agents' ADK containers expose `POST /run_sse` (`content-type:
text/event-stream; charset=utf-8`; a trivial prompt returns its first chunk at
8.8s warm). **The body is the same snake_case shape `/api/invoke` already
sends** — `{app_name, user_id, session_id, new_message, streaming:false}` —
verified against the deployed S12 and S01. ADK's OpenAPI advertises camelCase
(`appName`, `newMessage`), and the model accepts both; the existing snake_case
spelling is kept so the two routes do not disagree.

Each SSE line is `data: {json}`, and each event carries `content.parts[]` whose
members are:

```
{ functionCall:     { id, name, args } }          // args.sql holds the SELECT
{ functionResponse: { id, name, response: { success, data } } }
{ text: "…" }
{ thoughtSignature: "…" }                          // rides alongside; ignored
```

`server.py` gains:

```
GET /api/stream/{agent_id}?prompt=…&user_id=…&session_id=…
  → StreamingResponse(media_type="text/event-stream")
```

It creates the ADK session (a 400 on an existing session is success, as in
`/api/invoke`), opens `client.stream("POST", "/run_sse", …)` against the agent's
URL with the OIDC identity token, and relays chunks unchanged. `NotConnected`
before the stream opens returns 503 JSON exactly as `/api/invoke` does; a failure
after the stream has opened is emitted as a terminal SSE event, because a
half-written stream cannot change its status code.

`GET` with query parameters, not `POST`, so the browser's built-in `EventSource`
can be used and no streaming-fetch parser is needed.

`/api/invoke` stays. It is the non-streaming contract, it is what the deployment
verification exercises, and removing a working route to avoid having two is
churn.

### 5.3 The activity log, and not editing the agent

Each SSE event becomes one line via `plain.js`:

- `functionCall` → "Reading the sensor readings…" / "Tracing what else stops if this stops…"
- `functionResponse` with `response.success !== false` → the same line, ticked
- `functionResponse` with `response.success === false` → **"Couldn't trace what else stops — that lookup failed."** Named, not hidden.
- `text` parts → streamed into the answer body
- `thoughtSignature` → ignored; it rides alongside the other three and is not a step

The table a call touched is read from `functionCall.args.sql` — the observed
`bq_query` argument is a literal SELECT naming its table in backticks, e.g.
``SELECT * FROM `mining_data.telemetry_stream` LIMIT 10``. `plain.js` extracts
the first `mining_data.<name>` it finds. Where a call carries no recognisable
table (any non-`bq_query` tool), the line degrades to the tool's verb alone
rather than guessing a noun.

**The model's own prose is passed through unaltered.** The agents currently leak
plumbing into their answers — S01 emits `The tool call \`graph_traverse\` failed
with \`success=false\`` in its own text, because `blast_radius` is genuinely
broken on S01. Filtering that string would put the frontend in the business of
editing what the agent said, which is the same objection `server.py` already
records against reshaping the event list. The honest fix is upstream.

> **Logged, out of scope:** `blast_radius` returns `success=false` on S01. A
> backend defect, tracked separately from this work.

### 5.4 Connection state — from the wire, not from the build

`notConnected()` stops reading `DATA.workspace.runtime`. On load, `persona.js`
calls `/api/runtime` and renders the real answer. The build-time constant is kept
only as the fallback for the case where `/api/runtime` itself is unreachable —
i.e. the file:// and static-server cases, which is the one situation where the
baked message is true.

---

## 6. The vocabulary module — `apps/shared/plain.js`

This is the hinge of the design. One map serves two consumers: the live activity
log (§5.3) and the copy rewrite (§7). A screen and a stream that disagree about
what `graph_traverse` means would be worse than either alone.

**Tools (5):**

| id | plain |
|---|---|
| `bq_query` | looking up records |
| `bqml_predict` | running a prediction |
| `graph_traverse` | tracing connections |
| `operational_math` | working out the numbers |
| `request_approval` | asking for your sign-off |

**Traversals (3):**

| id | plain |
|---|---|
| `blast_radius` | what else stops if this stops |
| `fatigue_to_incident` | how crew fatigue connects to incidents |
| `stockout_exposure` | what runs out if this part runs out |

**Tables (25, all `mining_data.*`):**

| table | plain |
|---|---|
| `asset_dependencies` | which machines depend on which |
| `assets` | the machine register |
| `bid_parts_edge` | which parts each supplier quoted |
| `biometric_fatigue_logs` | crew fatigue readings |
| `crusher_states` | crusher run states |
| `drill_assay_logs` | drill sample assays |
| `drill_holes` | drill hole records |
| `erp_work_orders` | work orders in the ERP |
| `fatigue_logs_node` | crew fatigue records |
| `fleet_vehicles` | the truck and loader fleet |
| `geological_block_models` | the ore body block model |
| `haulage_routes` | haul routes |
| `incident_involvements` | who was involved in each incident |
| `inventory_levels` | parts on hand |
| `maintenance_logs` | maintenance history |
| `metallurgical_recovery` | plant recovery records |
| `operator_vehicle_assignments` | who drove what |
| `operators_node` | the operator roster |
| `procurement_bids` | supplier bids |
| `radio_communications` | radio traffic |
| `rfp_items` | items out to tender |
| `safety_incidents` | safety incidents |
| `simulation_runs` | scenario simulation runs |
| `telemetry_stream` | sensor readings |
| `work_order_parts_edge` | parts each work order needs |

**Composition.** A `bq_query` call whose arguments name `mining_data.telemetry_stream`
renders as **"Reading the sensor readings"** — tool verb plus table noun. A tool
or table absent from the map renders its raw id rather than a guess, and
`plain.js` exports `unmapped()` so a test can assert the map covers the
catalogue.

**Jargon substitutions** (the same module, used by the copy rewrite):

| term on screen today | plain replacement |
|---|---|
| entrypoint | agent you can talk to |
| HITL / human-in-the-loop | needs your sign-off |
| swarm | agent team |
| traversal | connection trace |
| Pattern A / Pattern B | team agent / specialist agent |
| model tier, reasoning, flash | *(technical drawer only)* |
| value branch | where the money is |
| APQC code | standard process area *(code in drawer)* |
| provenance | where this came from |
| p90 | the best day |
| median | the ordinary day |
| node / edge | machine / link |
| blast radius | what else stops |
| SC-1 … SC-4 | *(removed from headings)* |

---

## 7. The copy rewrite — ten screens

Two rules, applied to every screen.

**Rule 1 — the first screenful is plain.** Headings, ledes and table headers use
the right-hand column of the table above. Tables are preferred to prose wherever
the content is comparative, because the instruction was explicit that a
functional reader reads tables.

**Rule 2 — technical detail moves to the end, behind one collapsible.** Each
screen ends with a single `<details class="tbl">` titled **"Technical detail"**,
closed by default, holding the agent ids, APQC codes, model tiers, table names,
tool names, patterns and screen codes stripped from the body.

**The collapsible component already exists and is reused:** `details.tbl` in
`apps/workspace/workspace.css:78–96` — custom `▸`/`▾` marker, 44px touch target,
focus ring — already used by `workspace.js` `inputs()` and `workbench.js`
`department()`, and already handled by `handover.js:145–153`, which opens every
`<details>` before printing so the drawer never hides content from paper.

**One structural change is required:** those rules live in `workspace.css`, which
the case application does not load. They move to `apps/shared/app.css` so both
applications share one component. `workspace.css` keeps only what is genuinely
workspace-specific (`.tbl-desc`, `.cols`, `.col-meaning`).

**The ten screens:**

| # | File | Change |
|---|---|---|
| 1 | `apps/index.html` | chooser copy |
| 2 | `apps/case/index.html` | copy + drawer |
| 3 | `apps/case/scenario.html` | copy + drawer |
| 4 | `apps/case/value.html` | copy + drawer |
| 5 | `apps/case/solution.html` | copy + drawer |
| 6 | `apps/case/graph.html` | copy + drawer (node/edge → machine/link) |
| 7 | `apps/workspace/index.html` | cockpit copy + drawer |
| 8 | `apps/workspace/swarm.html` | copy + drawer ("agent teams") |
| 9 | `apps/workspace/persona.html` | **new** — replaces `workbench.html` |
| 10 | `apps/workspace/handover.html` | copy + drawer + **Run button** |

### 7.1 The handover Run button

`handover.html` is the shift handover brief. It renders four sections — three
summarisers (availability, production, safety) and the Omission Critic — each
currently a `notConnected()` block reading *"It has not run."*

**Only S12 can be run.** `DATA.catalog.swarms.S12` is
`{coordinator:"S12", specialists:["S12-SP1","S12-SP2","S12-SP3"], critic:"S12-CRITIC"}`,
and of those five only `S12` has `is_entrypoint: true` — the catalogue holds 100
agents of which 52 are callable. The four sections are the swarm's internal
decomposition, not four things the reader may invoke.

So the Run button issues **one** streamed call to S12, via the same
`agent-stream.js` and `/api/stream/S12` the sidecar uses, with a prompt composed
from the page's own subject (the shift handover brief). The brief streams into a
single region at the top of the sheet, with the activity log beneath it. The four
existing sections stay, and their `notConnected()` blocks are replaced by a line
naming which tables that summariser is entitled to draw on — which is what those
blocks were already documenting, minus the false "not connected" claim.

The `beforeprint` hook at `handover.js:145–153` already opens every `<details>`,
so a printed handover carries the streamed brief and the technical drawer in
full. The Run button and the activity log are `@media print { display: none }`.

`WORK_NAV` in `apps/shared/shell.js:34–39` changes `workbench.html / "Workbench"`
to `persona.html / "My role"`. `workbench.html` and `workbench.js` are deleted;
`workbench.js`'s department rendering is not carried over, because the persona
page addresses the same content from the reader's role rather than from the org
chart.

**Commodity neutrality and money hold.** Copy says "contained metal", never names
a metal, and expresses money as ranges. `facts.mill_downtime_usd_per_hour`
(145,000) is the only monetary figure the repository establishes; everything else
stays `[CLIENT INPUT REQUIRED]`.

---

## 8. Files

**New**

| Path | Responsibility |
|---|---|
| `apps/workspace/persona.html` | markup and script tags only |
| `apps/workspace/persona.js` | persona selection, layout, `/api/runtime` |
| `apps/workspace/persona-data.js` | the derivations — pure, tested (below) |
| `apps/workspace/persona-panel.js` | rendering of the five left-hand blocks |
| `apps/workspace/chat.js` | sidecar UI, transcript, agent-change control |
| `apps/workspace/router.js` | `route()` — pure, tested |
| `apps/workspace/agent-stream.js` | `EventSource` lifecycle, reconnect, abort |
| `apps/shared/plain.js` | vocabulary map — pure, tested |
| `tests/test_stream_route.py` | `/api/stream/{agent_id}` against a fake upstream |
| `tests/js/router.test.js` | `node --test` |
| `tests/js/plain.test.js` | `node --test` |
| `tests/js/persona-data.test.js` | `node --test` |

**Modified:** `apps/workspace/server.py` (+`/api/stream`), `apps/shared/shell.js`
(nav), `apps/shared/app.css` (+`details.tbl`), `apps/workspace/workspace.css`
(−`details.tbl`, +sidecar), `apps/workspace/workspace.js`
(`notConnected()` from the wire), `apps/workspace/handover.js` (+Run), plus copy
in the eight remaining screens.

**Deleted:** `apps/workspace/workbench.html`, `apps/workspace/workbench.js`.

---

## 9. Testing

**No build step, and none is introduced.** `router.js` and `plain.js` end with a
dual export — `if (typeof module !== "undefined") module.exports = {...}` — so the
browser loads them as plain script tags and Node's built-in `node --test` runner
requires them. Zero dependencies, no package.json, no bundler. Node v24.15.0 is
present.

**`tests/js/router.test.js`**
- Every persona's routing stays inside `persona.agents` — all 8 personas, table-driven.
- P8's single-agent case returns `S12` with a reason and an empty `runners_up`.
- P4's list-valued `value_branch` does not throw.
- A question of pure stop-words still returns a valid agent (totality).
- Identical inputs give identical output (determinism).
- Every generated starter question routes to the agent it was derived from, for all 8 personas (§5.1).

**`tests/js/plain.test.js`**
- `unmapped()` is empty against the live catalogue: all 25 tables, 5 tools and 3 traversals are covered. This is the test that keeps the map honest as the catalogue grows.
- Composition: `bq_query` + `mining_data.telemetry_stream` → "Reading the sensor readings".
- An unknown id renders its raw value, not a guess.

**`tests/js/persona-data.test.js`**
- `branchesOf` normalises P4's `["supply_chain","procurement"]` and P1's bare `"asset_reliability"` to arrays.
- All eight personas produce a defined result from `branchEvidenceFor` — seven with evidence, P8 with an empty array (no branch lists P8).
- Every returned evidence has a `kind` in `{series, distribution, share}`, and each kind's required fields are present: `points/min/max/readings` for `series`, `bins/edges/n` for `distribution`, `part/whole` for `share`.
- `gapRowsFor` reproduces the table in §4.2 exactly: P1 → 3 reached, P5 → 1, P6 and P8 → 4, P2/P3/P4/P7 → 0. `reached ∪ other` is always all four rows, and the two are disjoint — no row is dropped or double-counted.
- `starterQuestionsFor` returns 3 questions for every persona, and every capability named in them exists on one of that persona's agents.

**`tests/test_stream_route.py`** — a fake upstream, no Cloud Run:
- Happy path: session created, `/run_sse` chunks relayed byte-for-byte in order.
- `NotConnected` before the stream opens → 503 JSON matching `/api/invoke`'s shape.
- A 400 on session creation is treated as success.
- Client disconnect mid-stream closes the upstream connection.
- Unknown `agent_id` → 404 before any upstream call.

**Existing gates stay green:** `tests/test_workspace_image.py` (no agent SDK in
the image; 52 entrypoints) must pass unchanged — `/api/stream` adds no import
that would break it.

**Browser verification before "done":** the deployed revision, through
`scripts/proxy_workspace.py`, with a real question asked of a real agent and the
activity log watched to completion. Ten screens checked at 390px and 1440px.

---

## 10. Risks

**100 seconds is still 100 seconds.** The activity log makes the wait legible,
not short. Mitigation is honesty: the log names each step as it happens, so the
reader can see the agent reading records rather than watch a spinner.

**The router will sometimes pick wrong.** Deterministic string matching over
catalogue metadata is not comprehension. Mitigation is the visible reason plus
one-click change — chosen deliberately over a hidden decision.

**Deleting `workbench.html` loses the department view.** Accepted: the user chose
"persona page replaces the workbench", and the department framing is the org
chart the copy rewrite is removing.

**Browser access to the deployed URL remains unresolved.** The org policy
`constraints/iam.allowedPolicyMemberDomains` still blocks a sendable URL;
`scripts/proxy_workspace.py` remains the way in. Out of scope here, and not to be
touched without explicit go-ahead.

---

## 11. Non-goals

- Fixing `blast_radius` on S01 (backend defect, logged).
- Filtering or rewriting model output.
- Any change to the 52 agent services, the catalogue, or BigQuery.
- Making the deployed URL publicly reachable.
- Adding a build step, a framework, or any external dependency.
