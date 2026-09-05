# Problem-solving agents — design

**Status:** approved for planning
**Persona in scope:** P6, Metallurgist
**Branch:** `feat/agents-phase-5`

## Why this exists

The agents retrieve. Asked a question they find a table, run a query, cite it,
and stop. That is a natural-language interface to BigQuery, and it is not what
the engagement promised.

The gap is provable from one function. `mining_agents/patterns/deep.py`,
`build_instruction()`, composes every Pattern B agent's system prompt, and
every clause in it governs retrieval or honesty: data scope, citation mandate,
tool-failure handling, never-invent-a-value. Not one clause asks the agent to
diagnose, to rank by impact, or to resolve. Each agent is even handed its
`value_branch` — and the string is decorative. Nothing reasons with it.

What is wanted instead, in the words of the request: *for a governing metric,
what are the top problems degrading it, and how do I solve them* — grounded in
how the problem is actually resolved rather than in what a table contains.

The thinking already exists in this repository and never reached the product.
`docs/personas-and-value-tree.md` roots the estate on all-in sustaining cost
per tonne with six MECE branches, each mapped to personas and entrypoints. It
is a value tree nobody executes.

## Scope

All eight personas, **one at a time, each taken end to end** before the next
begins. A persona is done when its method skeleton, its retrieval and its
agent behaviour produce a complete diagnosis with a guarded recommendation.

The architecture supports this natively: the skeleton is one file per persona
(`method/p6-metallurgist.yaml`), so each persona is an increment rather than a
rewrite. Tools and the instruction block are built once, with P6.

**The order is not a preference — it is set by whether the data can carry a
diagnosis at all.** Every persona below was checked against the live dataset
during design.

| # | Persona | Governing metric | Feasibility |
|---|---|---|---|
| 1 | **P6 Metallurgist** | Unit cost per tonne of contained metal | **Strong** — worked example below |
| 2 | **P1 Reliability Engineer** | Availability; cost per tonne | **Strongest** — 500 work orders over the period carrying real `repair_cost`, 25,946 telemetry rows, `maintenance_logs` joins 152/152 to work-order dates |
| 3 | **P2 Maintenance Planner** | Planned vs unplanned ratio; schedule compliance | **Good** — shares P1's data, so it is a cheap follow-on. `priority` × `status` gives the planned/unplanned split |
| 4 | **P3 HSE Lead** | Incident and fatigue exposure | **Good** — 3,340 fatigue rows against 60 incidents with severity and root cause. 60 is thin for statistics and the method must say so |
| 5 | **P5 Mine Geologist** | Grade reconciliation | **Moderate** — 295 assays and 1,000 block estimates are both present, but they share no key. Reconciliation needs a spatial join, which is real work |
| 6 | **P8 Shift Supervisor** | Cross-cutting | **Derivative** — draws on the branches above, so it must come after them |
| 7 | **P4 Supply Planner** | Inventory turns | **Blocked** — `inventory_levels` is a 105-row snapshot with no timestamp and no consumption history. **Turns is not computable.** Needs generator work first |
| 8 | **P7 Mine Controller** | Cycle time; fleet utilisation | **Blocked** — `fleet_vehicles` is a snapshot and `haulage_routes` holds cycle time as a static attribute across 10 rows. **No time series exists.** Needs generator work first |

**P1 carries real money.** Its work orders hold `repair_cost`, so its prize can
be stated in currency directly from the data rather than waiting on a
`[CLIENT INPUT REQUIRED]` price. That makes P1 the most valuable persona to
demonstrate, and it is the reason it follows P6 immediately.

**Two personas cannot be done as specified.** P4 and P7 require data
generation before the method has anything to work with. They are sequenced
last so that discovery does not stall the personas that are ready, and the
generator work is scoped as its own effort rather than smuggled into this one.

## The shape of an answer

Five steps, in order. The order is the method; a step skipped silently is the
failure this design exists to prevent.

1. **Size the gap.** What is the metric now, against what the site has itself
   demonstrated?
2. **Attribute the loss.** Where is the value physically going?
3. **Separate controllable from uncontrollable.** An orebody is not a lever.
4. **Ask why it is not already happening.** The obvious lever is usually
   un-pulled for a reason, and a recommendation that cannot answer this is
   naive advice.
5. **Retrieve the constraint, then guard.** What does the equipment
   documentation permit, and does this site's data show the recommendation is
   safe here?

Step 4 and step 5 are the steps that separate this from a dashboard.

## Architecture

Three parts. One structured, one retrieved, one generative — and the split
between them is the whole design.

### 1. Method skeleton — `method/p6-metallurgist.yaml`

The driver tree and nothing else: for each driver, the question it answers,
the diagnostic to run, the comparison basis, whether it is controllable, the
guard that must clear before it can be recommended, and the document query
that fetches its resolution.

**It contains no resolution prose.** Authoring the resolution in YAML would
make the recommendation ours, which is the failure mode identified during
design review.

Two rules bind this file:

- **Comparison is on setting-bands, never outcome percentiles.** Comparing to
  the best decile of an outcome series banks noise as achievable — regression
  to the mean guarantees the prize is overstated. Comparison must be across
  bands of a controllable setting.
- **Completeness is inspectable.** Every driver in the file is either
  evidenced, or reported as unevidenced, or reported as not instrumented. A
  driver is never silently absent from an answer.

### 2. Document retrieval — BigQuery vector search

`ML.GENERATE_EMBEDDING` and `VECTOR_SEARCH` over the corpus in
`gs://mining-knowledge-base/` — 40 real PDFs across six folders:

| Folder | PDFs | Extracted text |
|---|---:|---:|
| field-progress-reports | 24 | 16,218 chars |
| macroeconomic-analyst-reports | 6 | 3,992 chars |
| oem-equipment-manuals | 4 | 3,201 chars |
| exploration-legacy-reports | 2 | 3,059 chars |
| capital-works-archives | 2 | 2,351 chars |
| legal-procurement-policies | 2 | 1,243 chars |
| **Total** | **40** | **30,755 chars** |

BigQuery native rather than Vertex AI Vector Search or RAG Engine: everything
else already lives in `mining_data`, and this adds no index infrastructure to
provision or keep warm on an Argolis sandbox. Vector Search earns its
complexity at millions of vectors.

**The corpus is very small — roughly 38 chunks at 800 characters.** At this
size retrieval is not a performance necessity; the whole corpus would fit in a
single prompt. It is built anyway, for three reasons that survive the size:
it is the forkable pattern a customer replaces with their own corpus, it keeps
the agent's context small and its citations precise, and the accelerator is
meant to demonstrate the capability. **The spec states this plainly so that
nobody mistakes 38 chunks for a working knowledge base.**

The four OEM manuals average roughly 800 characters each — one page apiece.
The crusher manual happens to contain exactly the operating envelope this
design needs. That is fortunate, not representative, and the corpus needs
enriching before the demonstration is credible beyond P6.

**Retrieval carries resolution content; it must never carry method
structure.** Top-k semantic search returns passages ranked by similarity with
no ordering guarantee and no completeness guarantee. A driver whose chunk
fails to retrieve would be silently skipped, and a silently skipped branch is
indistinguishable from "no problem found."

**SOPs are authored only where the real corpus leaves a gap**, after the index
is built and its coverage measured — not before. Any authored SOP is phrased
as a general standing rule with thresholds and sign-off levels. **No authored
document may encode a conclusion or reference a specific scenario.**

### 3. Agent behaviour

Two new tools, registered in `bind_tools()`'s `builders` dict alongside the
existing six:

- `method_lookup` — returns the driver tree for the agent's persona. Returns
  method, never site data.
- `doc_search` — returns cited passages from the corpus.

`build_instruction()` gains a METHOD block for agents whose persona has a
pack. `value_branch`, today a decorative string, becomes the key that loads
it. The block instructs: work the tree in order; retrieve the constraint
before recommending; rank by value at stake; report an unevidenced driver as
unevidenced rather than dropping it.

The agent chooses which branches the evidence justifies, catches confounds,
and writes the narrative. The skeleton constrains the shape of good
reasoning, not the conclusion.

**The honest test of this design:** the agent must be the thing that catches
the confound and asks why-not-already. If those are hardcoded, this is a
report generator with a chat interface.

## No new agents are required

Eleven agents already exist for P6 with the right scopes and the right names.
What is missing is the method that sequences them.

| Agent | Role in the method |
|---|---|
| D21 Recovery Rate Variance Analyst | Size the gap |
| D23 Tailings Loss Analyst | Attribute the loss |
| D22 Feed Grade Sensitivity Analyst | Isolate the uncontrollable driver |
| D25 Crusher Setpoint Optimiser | Size the controllable lever |
| D26 Crusher Bypass Event Analyst | Second driver |
| S07 Crusher–Mill Throughput Balance Coordinator | Orchestration |
| S07-CRITIC Setpoint Safety Critic | The guard |

## The driver tree

Governing metric: unit cost per tonne of contained metal. Root driver:
contained metal lost to tailings.

| # | Driver | Status | Controllable |
|---|---|---|---|
| 1 | Liberation — crusher closed-side setting | Evidenced | Yes |
| 2 | Feed grade variability | Evidenced | No — orebody |
| 3 | Bypass events | No signal — 1 interval in 167 days | — |
| 4 | Reagent regime | Not instrumented — no reagent data exists | — |
| 5 | Grind size (P80) | Not instrumented — closed-side setting is a proxy | — |

Two drivers carry evidence, one has no signal, two are not instrumented.
**That ratio is the design.** A method pack showing five green drivers on this
data would be lying, and the existing honesty machinery — the plain-language
failure lines and the "this part of the answer is incomplete" notice — is what
renders rows 3 to 5.

## Worked example — the answer this must produce

Every figure below was computed against the live dataset during design.

| Step | Finding | Source |
|---|---|---|
| Problem | Recovery averaging 92.21%, against 93.77% the site has itself run | data |
| Attribution | Metal reporting to tails; tails grade correlates −0.65 with recovery | data |
| Driver | Closed-side setting correlates −0.66 with recovery and +0.53 with tails grade | data |
| Confound tested | Effect holds in all three feed-grade terciles (+3.40, +4.00, +3.07 points); corr(gap, feed grade) = −0.14 | data |
| Why not already | The wide-gap campaign opened the crusher 10 mm to chase throughput. Throughput *fell* — 1,124 tph against 1,158 — and recovery cost 2.2 points | data |
| Constraint | 115 mm is the manufacturer's floor; below it with hard rock, torque exceeds the 4,500 Nm critical alarm | **OEM manual, retrieved** |
| Safe here? | Across three separate trials at 115 mm: max torque 4,273 Nm, 227 Nm of headroom, zero critical excursions, zero bypasses. **Caveat:** 9 of 23 days ran above the 4,000 Nm nominal limit | data ∩ document |
| Prize | ≈ +790 t contained metal over 167 days, ~1,700 t annualised, throughput-neutral | data |
| Money | `[CLIENT INPUT REQUIRED]` — metal price. Quoted as a range, never a point figure | — |
| Unexplained | The single bypass event occurred at 120 mm with torque at 3,760 Nm, matching no documented failure mode. Flagged, not narrated over | data |

The evidence at 115 mm is three separate trials of 8, 8 and 7 days rather than
one contiguous run. Independent replication, which is materially stronger than
a single block.

**Retrieval is load-bearing.** Without the manual the agent does not know that
115 mm is a floor or that 4,500 Nm is the limit, and would recommend
tightening further — which the manual says causes torque spikes and forces a
bypass. Retrieval is what turns a correlation into a safe recommendation.

## Framing — the scenario is authored

`data/generator/metallurgy.py` contains an authored campaign schedule. The
wide-gap excursion is a designed scenario, commented as such in the generator.
Recovery is computed through the genuine two-product recovery identity, so the
physics is real, but **the scenario was written to be found.**

This is legitimate for a reference accelerator: the customer forks it and runs
the method against their own data, and a planted scenario is how the machinery
is proved. It is **not** legitimate to present as *"look what our agents
discovered"* in a sales setting. That claim invites "did you put it there?",
and the answer is yes.

Any demonstration of this work presents it as a **worked scenario**, not a
discovery. This paragraph exists so that nobody has to rediscover the
distinction under questioning.

## Constraints

- **Commodity-neutral.** "Contained metal", never a named metal.
- **Money as ranges.** Never a point figure.
- **No invented numbers.** Every figure traces to the catalogue or the data,
  or is marked `[CLIENT INPUT REQUIRED]`.
- **Verified in a browser.** No completion claim rests on the test suite
  alone; runtime agent text is invisible to every static gate in this repo.
- Tests: `node --test 'tests/js/*.test.js'` — the quoted glob is required.

## Out of scope

- **Generating the data P4 and P7 need.** Inventory consumption history and a
  fleet cycle-time series are both absent. That is generator work, scoped
  separately, and until it lands those two personas cannot be built as
  specified.
- The three known agent tool defects in `docs/agent-tool-defects.md`.
- The top-navigation confusion between the wordmark and the tabs.
- The column-vocabulary decision for identifiers in body copy.

## Defect found during design — to be logged, not fixed here

`mining_data.unstructured_docs_metadata` is fiction. All 50 rows give a
`file_path` under `gs://mining-knowledge-base/oem-manuals/`, named
`manual_N.pdf`. The real folder is `oem-equipment-manuals/` and the real files
are named `crusher_03_manual.pdf`, `mill_01_manual.pdf` and similar. **Every
path in that table resolves to nothing**, and it claims 50 documents against
40 real objects. Its category counts claim 12 SOPs that do not exist.

Its `chunk_count` column is fiction too, and by a wide margin: it sums to
3,392 chunks against a real corpus of 30,755 characters — roughly 38 chunks.
The table overstates the knowledge base by about ninety times.

Any agent citing that table today cites a document that is not there. It is
recorded alongside the three tool defects.

## Risks

**The first persona was chosen because its data is good.**
`metallurgical_recovery` is close to a purpose-built metallurgical accounting
table. P6 therefore proves the method works where the data is rich; it does
not prove the method survives thin data. **P1 is the real test** — it is the
first persona the method meets that was not chosen for its convenience, and if
the pattern is going to break, it breaks there rather than on P6.

**Personas not yet reached still behave the old way**, so the contrast is
visible in any demonstration that ranges beyond the completed set. This is
transient by design, but it is at its worst early, when seven of eight are
untouched.

**Two personas will look complete in the catalogue and are not.** P4 and P7
have 18 and 10 agents respectively — more than P6 — and every one of them will
keep retrieving rather than diagnosing until the underlying data exists. Agent
count is not capability, and nothing in the workspace currently says so.

**The order front-loads the wins.** P6, P1 and P2 share the strongest data and
come first, which flatters early progress and defers every hard case. The
schedule should be read as three easy personas, two moderate, one derivative,
and two blocked — not as eight comparable increments.

**The corpus is thin, and thinner than it looks.** 40 documents totalling
30,755 characters, of which 24 documents are field progress reports and only 4
are OEM manuals. The crusher manual carries exactly the operating envelope
this design needs; the other three manuals are a page each and may carry
nothing comparable. The scope of SOP authoring therefore cannot be fixed until
the index is built and its coverage measured, and it is likely to be
substantial rather than a gap-fill. This is a known unknown carried
deliberately, per the decision to index what exists before authoring anything.

**A demonstration that leans on retrieval is one lucky document deep.** If the
crusher manual were absent, this design would produce an unsafe
recommendation. That is an argument for enriching the corpus, not for trusting
the current one.

**The method skeleton could become a script.** If it grows to encode
conclusions rather than the shape of reasoning, this collapses into a
precomputed report with a chat interface — the thing the redesign is meant to
replace.

## Testing

- The method pack is well-formed, and every diagnostic it names executes.
- Comparison bases are setting-bands; an outcome-percentile comparison fails
  the gate.
- Every driver in the pack appears in an answer as evidenced, unevidenced, or
  not instrumented — never absent.
- A retrieval failure degrades to a reported gap, never to a silent omission
  and never to a recommendation made without its constraint.
- The safety guard blocks a recommendation whose torque headroom is
  unevidenced.
- Live browser verification on P6 before any completion claim.
