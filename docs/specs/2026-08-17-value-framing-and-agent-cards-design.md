# Value framing and agent cards — design

**Status:** approved in conversation 2026-08-17. Spec review gate waived by the
user ("you can go ahead and code. I want to see the deployed screen").

**Goal:** bring the problem framing, value framing and agent framing of the
*Agentic Operations Platform for Mining* PRD and its CEO/CFO/COO decks into this
build, without discarding what already works.

**Source artefacts** (read, not guessed): `Agentic-Mining-PRD.md` (714 lines),
and the CEO (35 slides), CFO (42) and COO (51) decks, all in `~/Downloads`.

---

## Why this exists

The documents and the build disagree about what the product is. The PRD says a
**pattern factory** — six archetypes repeated cheaply across 21 agents. The
build says a **method library** — five driver trees, hand-authored against real
data. Both are defensible; they are not the same product.

The build already holds the strongest asset in either artefact and the PRD does
not name it: **declared coverage**. A driver with no diagnostic behind it is
reported as a gap in the agent's own answer rather than dropped. That mechanism
is the direct answer to the CFO deck's opening question — "Is the number real,
and how exactly will I know?" — and it survives this whole design unchanged.

The sharpest gap found in review: the CFO deck picks four agents *"chosen for
how the value is proven"* — AGT-11, AGT-13, AGT-14, AGT-19 — and three of the
four are archetypes with no reference implementation anywhere in the build. The
deck the economic buyer reads leans hardest on what the platform cannot show.

## Approach

Approach B of three, chosen by the user: **framing and cards first, then data,
then agents.** The four agent specifications ship immediately, with three of
them honestly declaring zero coverage. Generator work lands later against packs
that already name the exact tables and columns they need — a far better
generator spec than a blank page.

---

## Section 1 — The business-framing page

New screen `apps/workspace/value.html`, added as the **first** item of
`WORK_NAV` in `apps/shared/shell.js`, before Cockpit. Rationale: the user asked
for "both audiences, sequenced", and sequenced means the value argument is the
surface a CEO meets first. `index.html` remains the default entry point; this is
a nav destination, not a new landing page.

Three bands, top to bottom.

**Band 1 — The leak taxonomy.** The PRD's five leaks (Latency, Blind spot,
Variance, Coordination, Assurance), each with its one-line definition, and
**the number of agents in this build that claim it**. That count is derived from
the catalog at build time, never authored, so the page cannot drift from what
ships.

**Band 2 — Where the money goes.** The PRD's addressable pool, 4.1% of
operating cost in the conservative case and 9.0% in the stretch case, expressed
as a range against an opex denominator marked `[CLIENT INPUT REQUIRED]`. The
page ships with the denominator absent, not with US$1.5bn hard-coded. A reader
sees the mechanism and supplies their own figure. This is the band most likely
to get the platform dismissed if it carried a fabricated point estimate, so it
structurally cannot: no absolute currency figure appears anywhere on this page.

**Band 3 — The evidence ladder.** Class A / B / C from PRD §7, and the rule that
funding rests on A and B only, never on risk-adjusted value. This is what makes
the page a CFO artefact rather than a marketing one.

**Explicitly NOT on this page:** the six archetypes. The user cut this band. It
would leak internal taxonomy at a CFO. Archetype belongs on the agent card,
where an engineer reading one agent is the right audience.

## Section 2 — The agent card

Rendered on the persona page beneath the governing question, one per agent that
carries a method pack.

| Field | Source | Example — AGT-11 / P1 |
|---|---|---|
| Decision it owns | catalog | Which asset comes down, when, and on what evidence |
| Leak | catalog | Blind spot · Latency |
| Archetype | catalog | Diagnostician |
| Authority | catalog | L1 — Recommend |
| Financial line | catalog | Unplanned repair cost → C1 cash cost |
| Evidence class | catalog, **per line** | B |
| Coverage | **derived from the pack** | 5 of 7 drivers instrumented |
| Honest limit | catalog | per agent |

**Coverage is the load-bearing row** and the only computed one. Read from the
pack, by the same mechanism that already refuses to let a driver be silently
dropped. It is what makes the card unable to overclaim: an agent whose drivers
are mostly uninstrumented says so on its own card, in front of the buyer.

Two constraints held deliberately:

- **Authority is declared, not enforced.** PRD §8.1's ladder is a real feature;
  this build has no authority engine. The card states L1 and must not imply the
  platform enforces it. Writing "L1" beside an agent that could act at any level
  would be exactly the class of latent lie removed elsewhere in this branch.
- **Evidence class belongs to the financial line, not the agent.** PRD §7 is
  explicit that one agent can carry an A line and a B line.

New fields go on `AgentDef` in `mining_agents/catalog/definitions.py`, so the
loader and `tests/catalog/test_definitions.py` gate them and a missing field
fails the build rather than rendering blank.

## Section 3 — The four CFO agents

Each gets a real method pack with real drivers. Drivers whose data does not
exist are `not_instrumented` — verified: `load_pack` already accepts a pack in
which nothing is instrumented, so no schema change is required.

| Agent | Pack | Instrumented at ship | Archetype | Surfaced on |
|---|---|---|---|---|
| AGT-11 Asset Reliability | `p1-reliability.yaml` (exists) | **5 of 7** | Diagnostician | P1 |
| AGT-13 Warranty & OEM Claims | `agt13-warranty.yaml` (new) | 0 | Negotiator | P1 |
| AGT-14 Procurement & Contract Integrity | `agt14-contract-integrity.yaml` (new) | 0 | Negotiator | P4 |
| AGT-19 Strategic Planning Advisor | `agt19-strategic-planning.yaml` (new) | 0 | Optimiser | value page |

**Data reality, measured against BigQuery before this spec was written.** Only
AGT-11 is buildable today:

- `procurement_bids` (300 rows) holds *bids* — vendor, proposed cost, bid status,
  technical rating. There are **no contracts**: no terms, no clauses, no agreed
  price schedules. AGT-14 is "the agent that reads the contract the transaction
  was raised against", and that contract does not exist in this dataset.
- There is **no warranty table at all**. `maintenance_logs` (152) records
  repairs with no entitlement or claim state.
- There is **no price deck, capital pipeline or NPV model** for AGT-19.

Each `not_instrumented` driver's `question` must therefore name the table and
columns it would need, so the pack doubles as the generator's specification.

**AGT-19 is the weakest of the four and this is stated, not hidden.** Its inputs
are a customer's most confidential data, and the PRD caps it permanently at L1
with no promotion path. Its drivers will stay uninstrumented for a long time.

**Persona mapping decision.** The repo keys `PACKS` by persona; the PRD keys
packs by agent, with a persona holding several. Rather than restructure
`PACKS` — which would break `personas.json`, the router and their tests — the
four agents are declared as **agent cards in the catalog**, each optionally
referencing a pack file. PRD §4.1 assigns AGT-11 and AGT-13 to the Reliability
Engineer, and AGT-14 to the Category Manager (P4). AGT-19 is group-level and has
no persona in this build; its card is surfaced on the value page rather than
inventing a ninth persona.

---

## Testing

- The value page's leak counts must equal the catalog's. A test asserts this, so
  the page and the build cannot disagree — the discipline already used by
  `tests/fixtures/driver-ids.json`.
- No absolute currency figure may appear on the value page. Assert it.
- Every new `AgentDef` field must be present on every agent that declares a
  card; a missing field fails the build.
- Coverage on a card must be computed from the pack, not authored. A test must
  prove a card's coverage changes when its pack changes.
- Tests must be able to fail. No tautologies (assertions true by construction),
  and no floors sitting at or below the value they guard — both recurred
  repeatedly earlier in this branch.

## Constraints inherited

- Commodity-neutral: "contained metal", never a named metal.
- Money as ranges, never a point figure.
- Every number from real data or marked `[CLIENT INPUT REQUIRED]`.
- No reference to this repo's data generator, "synthetic data", or the demo
  dataset — a fork inherits that text.
- Verify in a real browser against the deployed revision before claiming done.
  Editing `apps/**` changes nothing until `scripts/deploy_apps.py::apply()` runs.
- Nothing pushed to any remote.

## Out of scope

- Building an authority engine.
- Restructuring `PACKS` to be agent-keyed.
- Generating contract, warranty or price-deck data (the next piece of work,
  specified by the packs this design ships).
- The remaining five archetypes beyond Negotiator and Optimiser declarations.
