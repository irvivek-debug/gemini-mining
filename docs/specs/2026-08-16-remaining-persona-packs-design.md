# Method packs for the remaining personas

**Date:** 2026-08-16
**Status:** approved
**Predecessor:** `2026-08-13-persona-workspace-design.md` (P6 Metallurgist, shipped and
verified live on `mag-workspace-00009`)

## Why this exists

The client's critique of the original build was that the agents "just seem to be
pulling out data from the database — more like a natural-language-to-SQL thing as
opposed to agents that are able to really replicate the best performing
practices." P6 answered that critique for one persona. This spec extends the
answer to the personas whose data can carry it.

The unit of work is a **method pack**: a YAML file naming a governing metric and
the driver tree beneath it, where each driver either has a fixed diagnostic query
or is honestly declared uninstrumented. The agent reads the pack with
`method_lookup`, executes drivers with `run_diagnostic`, and retrieves the site's
own documented constraint with `doc_search` before it recommends anything.

## Scope

**In scope:** P1 Reliability Engineer, P2 Maintenance Planner, P3 HSE Lead,
P5 Mine Geologist. Four packs, their diagnostic SQL, the catalogue changes their
holding agents need, and the authored SOPs that give P2 and P3 something to
ground a guard in.

**Out of scope, deliberately:**

- **P8 Shift Supervisor.** Agreed with the client that P8 must not be forced into
  a driver tree. It is a single agent with a site-wide remit whose job is
  assembling the other personas' findings into a shift briefing. It needs its own
  design and gets its own spec.
- **P4 Supply Planner and P7 Mine Controller.** Blocked on data, not on method,
  and the block is measured rather than assumed. `inventory_levels` is a 105-row
  snapshot with no timestamp and no consumption history, so inventory turns —
  consumption over average inventory — is not computable. `fleet_vehicles` is a
  single-date snapshot and `haulage_routes` holds cycle time as a static attribute
  across 10 rows, so there is no temporal variation for a cycle-time metric to
  diagnose. Both need generator work, which is a separate workstream.
- **Cross-domain causal structure.** See "The flat relationships" below.

## What was measured before anything was designed

Every claim in this spec was checked against the warehouse rather than inferred
from table names. Three findings changed the design:

1. **Six table names in circulation do not exist.** The real names are
   `erp_work_orders`, `safety_incidents`, `radio_communications`,
   `operator_vehicle_assignments`, `operators_node` and `work_order_parts_edge`.

2. **P5's join was said to be impossible and is not.** An earlier pass reported
   that `drill_assay_logs` and `geological_block_models` share no key. True as
   stated, but a derived spatial join works: desurveying assay midpoints from the
   collar position, dip and azimuth in `drill_holes` lands them inside the block
   grid. 142 paired rows within a 25 m box; 279 of 295 samples within 100 m. This
   makes P5 the strongest persona in the repository after P6.

3. **P2's natural metric is not evidenceable.** There is no planned/unplanned
   flag and no scheduled or due date anywhere in `erp_work_orders`. Schedule
   compliance and planned-versus-unplanned ratio — the two things a maintenance
   planner is actually judged on — cannot be computed. The governing metric is
   therefore reframed onto what the data does carry.

## The flat relationships

Two cross-domain relationships were measured rather than assumed, and both are
flat:

- **Fatigue to incidents.** Days with zero fatigue alerts average 0.354 incidents;
  one alert, 0.350; two or more, 0.360.
- **Telemetry excursions to work orders.** 0.598 / 0.645 / 0.364 work orders per
  asset-day across vibration and temperature bands.

The domains were generated independently, so the causal link a reliability
engineer and an HSE lead most want is not in the data.

**Decision (client-approved): declare honestly now, fix the generator later.**
These packs ship with those drivers declared `not_instrumented`, or instrumented
with a guard that forbids asserting a relationship the rows do not support. A
later generator workstream — the same one that unblocks P4 and P7 — will inject
genuine cross-domain structure, at which point these drivers can be upgraded
without touching pack format, tools or application code.

This is not a workaround. An agent that refuses to assert a correlation it cannot
evidence is the behaviour the whole redesign exists to produce. But it must be a
deliberate, recorded choice rather than an accident of the generator.

**The two are treated differently, and the asymmetry is intentional.** P1's
`condition_precursors` is marked `instrumented`: the query can be written —
telemetry excursions against work orders per asset-day — and it returns rows, so
the pack's own rule applies, which is that `status` says only whether a
diagnostic exists and the rows decide what it means. Its guard requires the agent
to state the band separation and forbids recommending condition-based
intervention when the bands do not separate. P3's `fatigue_to_incident` is marked
`not_instrumented` for a second and independent reason: only 5 of 60 incidents
carry an operator link, so the join that would attribute an incident to a fatigued
operator does not exist at usable scale. One driver has a diagnostic that returns
a null finding; the other has no diagnostic to run.

## Architecture

No new architecture. The P6 build is already general: there are **zero hardcoded
references to P6 or S07-SP3** in the tools, the instruction builder, the data
build, the router or the packaging. Adding a persona touches:

1. `method/<persona>.yaml` — the pack (new file)
2. `method/sql/<persona>/*.sql` — one file per instrumented driver (new files)
3. `mining_agents/tools/method_lookup.py` — one line in the `PACKS` registry
4. `mining_agents/catalog/definitions.py` — the holding agent gains
   `method_lookup`, `run_diagnostic`, `doc_search`, and whatever `source_tables`
   its diagnostics read

`scripts/build_app_data.py` carries the metric into `personas.json` through the
registry, `apps/workspace/router.js` turns it into the persona page's lead
question, and the Dockerfile copies `method/` wholesale. None of them change.

### Why the catalogue change is required and not optional

`run_diagnostic` refuses to execute SQL that reads a table the holding agent has
not declared in `source_tables`. This is a governance guard, and it means a pack
whose diagnostics reach past its holder's declaration fails at runtime rather
than at build time. The table expansions below are therefore part of the
deliverable, not an afterthought.

| Persona | Holder | Chosen because | Tables to add |
|---|---|---|---|
| P1 | `S01-SP3` Downtime Duration Forecaster | the specialist in the flagship reliability swarm that already reasons about failure consequence | `erp_work_orders`, `assets`, `telemetry_stream` |
| P2 | `S02-SP2` Parts Availability Checker | already declares all four tables the tree reads | none |
| P3 | `S05-SP2` Operator Fatigue Cross-Check | holds the incident, fatigue and involvement tables | `radio_communications` |
| P5 | `S06-SP1` Assay-to-Block Variance Analyst | its remit *is* the governing metric | `drill_holes`, `metallurgical_recovery` |

## The four driver trees

Every `instrumented` driver below has been checked to have sufficient rows and
real variance. Cell counts are stated where they are thin, because a driver whose
split gives single-digit cells must say so in its guard.

### P1 Reliability Engineer

- **metric:** unplanned repair cost per asset
- **root:** failures reaching repair that condition data could have anticipated

| id | question | status | notes |
|---|---|---|---|
| `cost_concentration` | Is repair cost concentrated in a few assets? | instrumented | 500 work orders, 5 assets, $498k–706k spread |
| `criticality_load` | Are the most critical assets absorbing disproportionate work? | instrumented | criticality ratings present on all 5 assets |
| `excursion_rate` | Are telemetry excursions rising on any asset-metric series? | instrumented | 13 series, ~1,995 rows each, non-zero stddev on all |
| `repair_duration` | Is repair time drifting by asset? | instrumented | 152 completed logs, 1–19 h |
| `condition_precursors` | Do excursions precede work orders? | instrumented | **measured flat**; guard forbids asserting a link the bands do not show |
| `availability` | Is availability falling? | not_instrumented | no downtime start/end, no state history |
| `mtbf` | Is time between failures shortening? | not_instrumented | `maintenance_logs` has no timestamp |

### P2 Maintenance Planner

- **metric:** maintenance cost per completed work order
- **root:** work escalating in priority before it is done

The causal story is measured, not asserted: mean repair cost rises monotonically
with priority — LOW $3,429, MEDIUM, HIGH, CRITICAL $8,361 — so work that ages in
the backlog and escalates costs more when it is finally executed.

| id | question | status | notes |
|---|---|---|---|
| `priority_cost_escalation` | Does cost rise with priority? | instrumented | monotonic across all four priorities |
| `backlog_aging` | Is work ageing in the backlog? | instrumented | 117 OPEN + 127 IN_PROGRESS, age from `created_at` |
| `parts_stockout` | Are parts below reorder point holding work up? | instrumented | 15 of 105 SKUs below reorder, one at zero, lead time 2–30 d |
| `parts_demand_cover` | Is demanded stock covered? | instrumented | 186/186 join; **guard must state that only 5 distinct SKUs appear in demand** |
| `schedule_compliance` | Is work done when scheduled? | not_instrumented | no scheduled or due date exists |
| `planned_ratio` | What share of work is planned? | not_instrumented | no planned/unplanned flag exists |

### P3 HSE Lead

- **metric:** severity-weighted incident exposure
- **root:** exposure concentrated where controls are weakest

60 incidents is the ceiling on this persona. Any two-way split gives cells of
three to five, so only one-dimensional splits are instrumented, and their guards
must state the cell counts.

| id | question | status | notes |
|---|---|---|---|
| `location_concentration` | Is exposure concentrated by location? | instrumented | 17/12/12/10/9 — the only split with usable cells |
| `severity_mix` | Is the severity mix worsening? | instrumented | HAZARD 16, MTI 14, FATALITY 14, NEAR_MISS 11, LTI 5 |
| `fatigue_exposure` | Is the workforce carrying fatigue risk? | instrumented | 3,340 logs, sleep deficit 0–7.98 h, 117 alerts — strong standalone |
| `radio_distress` | Is radio traffic signalling distress? | instrumented | 164 of 573 emergency-flagged, sentiment −0.7 to +0.4 |
| `fatigue_to_incident` | Does fatigue drive incidents here? | not_instrumented | measured flat, and only 5 of 60 incidents carry an operator link |
| `shift_pattern` | Does exposure vary by shift? | not_instrumented | incident and fatigue timestamps are all 00:00 |

### P5 Mine Geologist

- **metric:** contained-metal variance between the block model and realised grade
- **root:** grade delivered differs from grade modelled

The root is worded neutrally on purpose. The measured direction is that the model
under-calls by roughly a quarter, but stating that in the pack would be the
conclusion leak corrected during the P6 build: the pack says what to test, and
the rows decide the answer.

| id | question | status | notes |
|---|---|---|---|
| `model_bias` | Does modelled grade match assayed grade? | instrumented | 142 desurveyed pairs inside a 25 m box |
| `bias_by_lithology` | Is the variance confined to certain domains? | instrumented | 5 domains, n = 95/70/53/45/32 |
| `bias_by_depth` | Does the variance change with depth? | instrumented | 10–448 m |
| `bias_by_elevation` | Does the variance change with elevation? | instrumented | centroid_z 325–550 |
| `feed_grade_vs_model` | Does delivered feed grade track the model? | instrumented | 167 daily rows |
| `tonnage_reconciliation` | Does mined tonnage reconcile? | not_instrumented | no mined-tonnage table |
| `qaqc_bias` | Do standards and duplicates show sampling bias? | not_instrumented | no QA/QC flag on samples |

## Documents and authored SOPs

`doc_search` grounds each guard in the site's own documented constraint. The
corpus was measured directly: `mining_data.doc_chunks_embedded` holds 48 chunks
from 40 files across 6 folders, and the source bucket is 178 KiB, so the PDFs are
genuinely one-pagers. Extraction is not broken; the corpus is small.

| Folder | Files | Serves |
|---|---|---|
| `field-progress-reports` | 24 | P8 |
| `oem-equipment-manuals` | 4 | P1, P6 |
| `macroeconomic-analyst-reports` | 6 | commodity context |
| `exploration-legacy-reports` | 2 | P5, thin |
| `capital-works-archives` | 2 | — |
| `legal-procurement-policies` | 2 | P4 |

P1 is well served: the four OEM manuals are asset documents, and P6 already
proved a guard can be fenced by one of them. P3 has **no safety document at
all**; P2 has nothing on maintenance policy; P5 has two historic exploration
reports and nothing on reconciliation practice.

Per the standing decision — index the real PDFs, author SOPs only where there is
a gap — three short SOPs are authored as part of this work, written as site
standards and loaded through the existing chunk-and-embed pipeline:

- **P3:** a fatigue management standard naming the alert threshold and the
  stand-down rule
- **P2:** a work-order prioritisation and deferral standard
- **P5:** a grade reconciliation standard naming an acceptable variance tolerance

Each must be visibly a site document rather than a restatement of the pack, or
the guard is grounded in nothing but itself.

## Sequence

**P5, then P1, then P2, then P3.** Strongest first, deliberately: P5 and P1 have
the best data and the best document grounding, so they prove that a second and
third pack cost content plus a catalogue line rather than architecture. P2 and P3
follow, each preceded by its authored SOP, because a guard written before the
document it cites is a guard grounded in nothing.

## Standing constraints

These bind every deliverable and are carried from the engagement, not invented
here:

- **Commodity-neutral.** Say "contained metal". Never name a metal in a metric,
  a driver question, a guard or any rendered copy. Column names in SQL are
  exempt because they are the warehouse's, not ours.
- **Value as ranges, never a point figure.** Any monetary magnitude is quoted as
  a range or marked `[CLIENT INPUT REQUIRED]`.
- **No figure without provenance.** Every number rendered on a screen comes from
  the data or is marked as client input.
- **The pack states what to test, never what the answer is.** The conclusion leak
  corrected during the P6 build must not reappear: `status` says whether a
  diagnostic exists and nothing more.
- **Nothing is pushed to any remote** without an explicit instruction.

## Testing

Mirroring the P6 build:

- Every pack loads and passes the existing validation gates in
  `mining_agents/method/pack.py` — required fields, valid `status`, SQL present
  exactly when instrumented, unique driver ids.
- Every instrumented driver's SQL executes against BigQuery and returns rows.
- Every instrumented driver's SQL reads only tables its holding agent declares,
  asserted in a test rather than trusted, since `run_diagnostic` enforces it at
  runtime and a mismatch would otherwise surface only in a live session.
- `build_app_data` carries each metric into `personas.json`.
- The persona page leads with the governing question for all five packs.
- Live browser verification per persona, as with P6: the rendered DOM, not the
  event stream.

## Success criteria

1. Each of P1, P2, P3, P5 opens its persona page with a problem-solving question
   built from its governing metric, not an offer to dump a table.
2. Asking that question produces a diagnosis worked across the driver tree, with
   uninstrumented drivers named rather than silently dropped.
3. No recommendation is made without the site's documented constraint retrieved
   first.
4. Drivers whose data cannot support a conclusion say so, including the two flat
   cross-domain relationships.
5. Full suites green; nothing pushed without explicit instruction.
