# Two Applications — Design

**Date:** 2026-08-13
**Status:** draft for review. Written while the backend workstream is blocked on
Google Cloud re-authentication.

## What was asked for

Two applications, each with several screens — not two screens.

1. **The case for change.** Value proposition of agentic transformation in
   mining, the current scenario for the demo, value unlock, the overall
   solution, and an interactive visualisation of the graph relationships, using
   an open-source graph library.
2. **The agentic application itself.** Persona-level, helping each key player
   solve their pain areas and unlock value.

Standing constraint: no AI slop. Every number and label on screen comes from the
catalog or the data, or it renders `[CLIENT INPUT REQUIRED]`.

## The single most important design constraint

**Only one dollar figure exists in this repo: $145,000 per hour of mill
downtime.** Every other value number in `docs/personas-and-value-tree.md` is
marked `[CLIENT INPUT REQUIRED]`.

The demo guides quote other figures — $85,000/day lease penalty, $420,000
downtime, $1.1M/day deferred revenue — but those belong to a **previous
generation of personas** that the Phase 0 work replaced. Reusing them would be
inventing a business case out of a superseded document.

So the value screens do not show a fabricated ROI. They show the mechanism of
value precisely, and the magnitude as `[CLIENT INPUT REQUIRED]`. This is a
feature, not an apology: `docs/ux/tokens.css` already ships a `.metric.gap`
style — warning orange, 15px mono instead of the 30px display metric — built
for exactly this. A CEO who sees a number they did not supply stops trusting the
screen. A CEO who sees a clearly marked gap knows where to put their own number.

## What is real, verified 2026-08-13

Counted from `mining_agents/catalog/definitions.py`, not from documentation.

- **100 agent nodes, 52 externally callable entrypoints.**
- **Personas and their entrypoint counts:** P1 Reliability Engineer 8, P2
  Maintenance Planner 5, P3 HSE Lead 9, P4 Supply Planner and Procurement Lead
  10, P5 Mine Geologist 6, P6 Metallurgist 7, P7 Mine Controller 6, P8 Shift
  Supervisor 1. Sums to 52.
- **Nine value branches:** safety 9, asset_reliability 8, processing 7,
  mine_ops 6, geology 6, supply_chain 6, maintenance_execution 5, procurement 4,
  site_wide 1.
- **Seven APQC codes**, several agents carrying a compound code such as
  `4.3.1 / 9.1.2`.
- **14 entrypoints require human approval:** D07, D14, D25, D30, D37, S01, S02,
  S04, S05, S07, S08, S09, S10, S11.
- **Tool usage across entrypoints:** bq_query 50, request_approval 14,
  operational_math 10, graph_traverse 7, bqml_predict 3.

**Numbering caution.** `docs/personas-and-value-tree.md` narrates the Mine
Controller as "Persona 3" and the HSE Lead as "Persona 1", while the catalog
assigns P7 and P3 respectively. **The catalog is authoritative**; the prose is a
prior draft. Screens use catalog codes.

## The graph, honestly

`mining_agents/tools/graph_traverse.py` defines four BigQuery property graphs,
but only **three are traversed by any deployed agent**. Seven entrypoints (12
agent nodes counting specialists) hold `graph_traverse`:

| Graph | Node and edge labels | Traversal | Entrypoints |
|---|---|---|---|
| `MiningAssetGraph` | `assets` -[`DEPENDS_ON`]-> `assets` | `blast_radius`, 1 to 3 hops | D05, S01 |
| `MiningSupplyChainGraph` | `SparePart` <-[`REPLACED_PART`]- `WorkOrder` <-[`HAS_WORK_ORDER`]- `Asset` | `stockout_exposure` | D31, S02, S08 |
| `MiningOperationsSafetyGraph` | `FatigueLog` -[`LOGGED_FOR`]-> `Operator` -[`OPERATES`]-> `Vehicle` -[`INVOLVED_IN`]-> `Incident` | `fatigue_to_incident` | S05, S11 |

The fourth, `MiningOntologyGraph` / `ontology_related`, is granted to **zero
agents** — `tests/test_demo_scenarios.py` pins that at exactly zero, and
`ontology_concepts.concept_type` is NULL for all 25 rows. It is therefore **not
exported and not shown**. Rendering a graph no agent reads would be scenery, and
the standing constraint rules out scenery as firmly as it rules out invented
numbers.

**Measured scale, so the visual treatment is honest:** 5 assets joined by 3
`DEPENDS_ON` edges in a chain — CONVEYOR-02 → CRUSHER-03 → MILL-01 → PUMP-104A,
impact scores 0.90, 0.95, 0.80 — with TRUCK-08 unattached. 500 work orders
across those 5 assets, of which 126 consume parts, over 186 work-order-to-part
edges touching only **5 distinct** part numbers out of 105 in inventory. 20
operators, 15 vehicles, 5 assignments, 5 incident involvements.

This is a small, dense, multi-typed graph, not a hairball. Two consequences:

1. **A force-directed hairball would be dishonest.** Spring layouts exist to
   find structure in thousands of undifferentiated edges. Applied to 3 edges
   they manufacture the appearance of complexity. The complexity here is in the
   **typing** — four graphs, distinct node labels, distinct edge semantics — not
   in the cardinality.
2. **The interesting thing to show is the traversal, not the topology.** The
   screen's job is to let someone watch a blast radius propagate from a failed
   asset, or a stockout expose the work orders it will block. That is what the
   agents actually do.

**Library: Cytoscape.js**, MIT-licensed, vendored as a single file. Chosen over
React Flow (a node-editor, not a graph library — no traversal, no graph
algorithms) and Sigma.js (a WebGL renderer that wins above roughly 50,000
elements and costs clarity below that). Cytoscape gives typed node classes,
labelled edges, deterministic layouts suited to small graphs, and — the reason
it matters here — programmatic traversal and element highlighting, which is how
the blast radius animates.

## Architecture

Two applications, one design system, no build step.

```
apps/
  case/                 Application 1. Static HTML. No backend.
    index.html          Screen shell and navigation
    screens/*.html
  workspace/            Application 2. FastAPI + static HTML.
    server.py           Serves the screens; proxies to Cloud Run with an OIDC token
    static/
  shared/
    tokens.css          Symlink or import of docs/ux/tokens.css
    cytoscape.min.js    Vendored, MIT
    data/
      catalog.json      Generated from mining_agents/catalog/definitions.py
      graph.json        Generated from the four property graphs
```

**No npm, no bundler, no framework.** The existing `docs/ux/` artifacts are
plain HTML against `tokens.css`, and this artifact is a reference accelerator a
customer forks. A build step is a tax on every future reader of this repo for
benefit these screens do not need. Cytoscape is one vendored file.

**Application 1 needs no backend at all** — it is narrative over generated JSON,
so it can be opened from disk or served by any static host.

**Application 2 needs a thin backend** for exactly one reason: the 52 Cloud Run
services require a Google-signed OIDC identity token, and a browser page cannot
mint one. `apps/workspace/server.py` serves the static screens and exposes a
single proxy route that attaches the token. FastAPI is already installed. This
is also what a customer forking the accelerator needs on day one.

### Data generation

One script, `scripts/build_app_data.py`, writes `catalog.json` and `graph.json`.

`catalog.json` is derived entirely from `mining_agents/catalog/definitions.py`,
so it cannot drift from what is deployed — the same source that builds the
agents builds the screens.

`graph.json` is derived from BigQuery when credentials are available, and from
`data/profile/stats.json` plus `data/generated/*.parquet` otherwise. Both paths
produce the same shape. The file records which source it used and when, and the
screen displays that provenance, because a graph rendered from a cache is a
different claim from a graph rendered from the warehouse.

## Application 1 — the case for change

Executive audience. Linear. Someone presents *at* an audience with it. Five
screens, navigable in order, each standing alone if opened cold.

**1.1 The proposition.** What agentic transformation means for a mine, stated
without hedging: 52 places where a question a person asks today gets answered by
an agent that already knows the schema, the process, and who is accountable.
Anchored on the one real figure — $145,000 per hour of mill downtime — as the
unit of consequence.

**1.2 The current scenario.** The mine as the demo actually has it: 5 assets, 20
operators, 15 vehicles, 500 work orders, 105 stocked parts, 25,946 telemetry
readings every two hours across 12 metrics. Then what breaks: the personas'
own words. "I need three systems open at once just to answer one question."
"The part was supposed to be in stores, the technician showed up and it wasn't
there." Quoted, attributed, not paraphrased into marketing copy.

**1.3 Value unlock.** The nine value branches against the six-branch value tree,
each with its agent count, its personas, and its APQC process code. Mechanism
stated precisely; magnitude rendered `[CLIENT INPUT REQUIRED]` except where the
$145,000/hr anchor applies. This screen is where the discipline shows.

**1.4 The solution.** How 100 agents are assembled: Pattern A, 12 swarms of a
coordinator, three specialists and a critic; Pattern B, 40 departmental deep
agents; 52 externally callable entrypoints; 14 of them gated on human approval;
five tools; three service accounts. Deployment shown as it is, on Cloud Run.

**1.5 The graph.** The three traversed property graphs, rendered and live. Default
view is the asset graph with its 5 nodes and 3 typed edges. Pick an asset, run
the blast radius, watch it propagate one to three hops with impact scores on the
edges. Switch to the supply chain graph and watch a below-reorder-point part
expose the work orders it blocks. Every traversal on screen is one an agent
runs, named as the agent names it.

## Application 2 — the agent workspace

Operator audience. Non-linear. Someone *works* in it.

`docs/phase-2-ux.md` already decided five screen archetypes and eight auditor
findings against them, and `docs/ux/wireframes.html` renders them. **This
application implements that existing design rather than inventing a new one.**
Contradicting it would discard settled work and be exactly the kind of
regeneration that produces slop.

The archetypes, and what each becomes here:

**2.1 Site cockpit (SC-1).** Entry. The 52 entrypoints under three navigation
axes — by persona, by APQC process, by value branch — because the same agents
answer to three different questions about who owns what.

**2.2 Persona home.** A filtered cockpit: my agents, my pain points in my own
words, the value branch I am accountable for. Eight of these, one per persona,
generated from the catalog rather than hand-built, so P4's ten agents and P8's
single one both render correctly.

**2.3 Departmental workbench (SC-3).** A single Pattern B agent answering a real
question: the result, the inputs and their provenance, the formula where the
agent is deterministic, and the execution trace. For agents like D27 the method
*is* the provenance, so the formula appears literally on screen.

**2.4 Swarm console (SC-2).** A Pattern A swarm on one incident: the coordinator,
the three specialists fanning out in parallel, the critic, and the blocked-state
band when approval is outstanding.

**2.5 Approval sheet (SC-4).** The human-in-the-loop gate for the 14 agents that
require it. A modal, not a screen. Two-second hold to confirm with an animated
stroke; reasoning and telemetry exposed above the button rather than behind a
disclosure; the confirm button never styled as success; Cancel reads "Cancel".

**2.6 Shift handover (SC-5).** S12, the single site-wide entrypoint, rolling up
across branches with the omission critic band that always renders.

### Accessibility floor, inherited and non-negotiable

From `docs/phase-2-ux.md`: P3 (HSE Lead) and P7 (Mine Controller) work on rugged
tablets, under stress, sometimes gloved. Every screen they touch is single
column on tablet, has no hover-dependent information, and has touch targets of
at least 44 by 44 pixels. P6 (Metallurgist) works in hearing protection, so
**no audio-only signal anywhere in either application**.

## What "done" means

- Every figure on screen traceable to the catalog, `data/profile/`, or the
  generated parquet — or rendered `[CLIENT INPUT REQUIRED]`.
- Both applications loaded in a real browser and checked at desktop and tablet
  widths before either is called finished.
- The graph screen runs a real traversal, not a canned animation.
- No emoji, no gradient hero, no three-column feature cards, no invented
  statistics.

## Open questions for review

1. **The value screen is mostly `[CLIENT INPUT REQUIRED]`.** That is the honest
   position given one real dollar figure. If baseline figures exist outside this
   repo, supplying them turns 1.3 from a framework into a business case.
2. **Application 2 against live agents.** Wiring the workspace to the 52
   endpoints needs the Cloud Run identity token, so it is gated behind the same
   re-authentication as the backend tasks. Until then the workspace renders the
   catalog and the archetypes with recorded rather than live responses, clearly
   labelled as recorded.
3. **Scenario selection.** `docs/personas-and-value-tree.md` storyboards four
   flows well enough to build: the P1 overnight bearing thermal event, the P2
   mid-shift cascading failure, the P8 07:45 interlock decision, and the P4
   two-persona expedite. The workspace demonstrates the P1 and P2 flows first.
