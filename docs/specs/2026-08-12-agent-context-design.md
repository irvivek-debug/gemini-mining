# Agent Context: Schema, Semantics and the Site Clock

**Date:** 2026-08-12
**Status:** approved design, ready for planning
**Scope:** the 100-agent ADK build in this repo. Not the demo application — that
is designed separately, after this lands.

---

## 1. The problem, as measured

Every agent is told the *names* of the tables it may read and nothing else.
`mining_agents/patterns/deep.py:58`:

```python
"DATA SCOPE — you may read only these objects:",
*(f"  - {table}" for table in agent.source_tables),
```

So each agent begins every request by rediscovering facts it rediscovered on
the previous request. Measured against the deployed `D01` on 2026-08-12, warm
container, question *"Which assets show abnormal telemetry in the last 24
hours?"*:

| | |
|---|---|
| Wall time | **48.0s** warm, 52.6s cold |
| Cold-start cost | 4.6s — not the problem |
| `bq_query` calls | 9 |
| Of which are orientation | **5** |

The five:

```
q1  SELECT column_name, data_type FROM INFORMATION_SCHEMA.COLUMNS    what columns exist
q2  SELECT column_name, data_type FROM INFORMATION_SCHEMA.COLUMNS    asked twice
q3  SELECT * FROM telemetry_stream LIMIT 5                           what a row looks like
q4  SELECT MAX(timestamp), MIN(timestamp) FROM telemetry_stream      what dates are covered
q5  SELECT DISTINCT metric_name FROM telemetry_stream                what metrics exist
```

Each round-trip is a full model-writes-SQL → BigQuery-executes →
model-reads-result cycle, roughly five seconds. Fifty-five percent of the
agent's work is orientation.

`S01`, a Pattern A swarm, measured **191.6s** over 76 events with authors
`s01`, `s01_sp1`, `s01_sp2`, `s01_sp3`, `s01_critic`. Its three specialists
already run in parallel (`swarm.py:158`), so its time is three *stages* —
specialists together, then critic, then coordinator — and every one of the
five nodes pays the orientation cost independently.

### 1.1 The correctness half of the problem

Every operational table in `mining_data` ends 2026-06-16 to 2026-06-18. Today
is 2026-08-12. The dataset is **57 days stale**. Only `agent_approvals` and
`agent_run_log` are current, because the agents write those themselves.

So `q4` is not the model being cautious for no reason. A literal "last 24
hours" query returns zero rows. An agent that reports *"no anomalies detected"*
when the truth is *"there is no data for that window"* is the most dangerous
failure this build can produce in front of a client, because it sounds like
good news.

This is a correctness defect that happens to also cost latency.

### 1.2 There is nothing to discover even if it asked well

`mining_data` has 258 columns in total, of which **eleven carry a description
and no table carries one at all.** The eleven are clustered in
`incident_involvements` (4), `operator_vehicle_assignments` (5) and
`rfp_items` (2).

The surface that actually matters is smaller. Across all 100 agents only **25
distinct tables are ever declared, totalling 141 columns** — the remaining 117
belong to backup snapshots and tables no agent reads. Those 25 tables and 141
columns are the scope of the semantics work.

So schema discovery today returns names and types with no meaning attached.
`metric_value FLOAT64` does not tell an agent whether 4.2 is a normal bearing
vibration. Removing the round-trips without adding meaning would make the
agents faster at being uninformed.

---

## 2. Decisions taken

**The data is not modified.** Rolling every timestamp forward was considered
and rejected: this system will be demonstrated over roughly six months, so any
roll needs a recurring job, and a recurring job is a thing that can fail
silently and leave a broken demo. The dataset stays as generated.

**The agent is told the clock instead.** Stated in the instruction, surfaced in
the UI, and consistent with what the BigQuery console shows — because nothing
was mutated, there is nothing to explain.

**Context is generated from BigQuery, not hand-authored.** The governing
constraint is that the BigQuery console may be opened live, mid-demo. So:

> What the agent knows and what the console shows must be the same fact
> rendered twice. Generating the agent's context *from* BigQuery metadata makes
> divergence structurally impossible rather than a discipline problem.

**MCP is not the answer to this problem.** Google ships two BigQuery MCP
surfaces — the MCP Toolbox for Databases (`googleapis/genai-toolbox`, v1.8.0,
2026-07-28) and a first-party managed BigQuery MCP server (Preview, doc updated
2026-08-11). Both expose `get_table_info` and `get_dataset_info` as *runtime
tool calls*. They would consolidate five discovery queries into one or two,
which is an improvement, but the agent still stops and waits. MCP changes who
owns and governs the integration; it does not change whether the round-trip
happens. Only what is already in the context window is free.

Recorded as the productionisation path for a customer who forks this repo and
needs one governed query tool across many agents. Not adopted here.

**Injection, not retrieval.** Google's own documented guidance for the
Conversational Analytics API "authored context" (doc updated 2026-07-29) is to
supply tables, columns and example queries as structured context at
agent-configuration time. At 258 columns — roughly 5–8k tokens for the whole
dataset, and each agent sees only its own 1–4 tables — injection is
comfortable. Retrieval over a catalog becomes necessary when a single agent's
scope reaches hundreds of tables.

Worth stating explicitly because it is a good answer to "does this scale":
**the declared-scope security model is also the context-budget model.** The
same constraint that stops an agent reading a table it did not declare is what
keeps its context small.

---

## 3. Architecture

One direction of truth, four small components:

```
docs/column-semantics.yaml          curated domain text, reviewed in a PR
        │
        │  scripts/annotate_bigquery.py
        ▼
BigQuery column + table descriptions        ← what the console shows
        │
        │  scripts/build_context.py   (COLUMN_FIELD_PATHS + TABLE_OPTIONS + profile)
        ▼
data/context_snapshot.json          committed, versioned, diffable
        │
        │  mining_agents/context/render.py
        ▼
one instruction block per agent, filtered to its declared tables
```

The read-back through BigQuery is deliberate. Rendering from the YAML directly
would be simpler and would silently pass if the annotation step never ran.
Reading back proves the console and the prompt agree.

### 3.1 `docs/column-semantics.yaml`

The human-owned artifact. One entry per table, one per column.

```yaml
mining_data.telemetry_stream:
  description: >
    Continuous sensor readings from fixed plant and mobile assets. One row per
    asset per metric per hour.
  columns:
    asset_id:     Asset this reading belongs to. Joins assets.asset_id.
    metric_name:  Which sensor channel this row reports.
    metric_value: The reading, in the unit given by `unit`.
    timestamp:    Hour the reading was taken, UTC.
```

**Grounding rule.** Every description is derived from the generator that
produced the column (`data/generator/*.py`, 5,372 lines across seven domain
modules) and cross-checked against the loaded data. Where the generator's
intent and the data disagree, that is a defect to raise — not a wording choice
to smooth over. No description may assert a fact that neither the generator nor
the data supports.

This file is also a client-facing deliverable: it is what a subject-matter
expert would review.

### 3.2 `scripts/annotate_bigquery.py`

Applies the YAML to BigQuery as real table and column descriptions, via
`ALTER TABLE ... SET OPTIONS(description=...)` and schema updates. Idempotent.
Supports `--dry-run`, which prints the diff without writing.

Does not touch the `*_original_20260810` backup tables.

### 3.3 `scripts/build_context.py`

Reads back from BigQuery and writes `data/context_snapshot.json`:

- **Structure** — from `mining_data.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS`.
  Note this is *not* the view the agents currently query.
  `INFORMATION_SCHEMA.COLUMNS` has no `description` column at all;
  `COLUMN_FIELD_PATHS` has one and covers every column, not only nested fields.
- **Meaning** — the descriptions, from the same view and from `TABLE_OPTIONS`.
- **Statistics** — row count; min/max of the table's time column; and the
  distinct values of any column whose cardinality is ≤ 25. The time column is
  the table's single TIMESTAMP/DATETIME/DATE column. Verified 2026-08-12: of
  the 25 agent-referenced tables, sixteen have exactly one and nine have none.
  None has two. A table with no time column simply carries no coverage range.
  If a future table carries two, that is an error rather than a guess — the
  builder raises and the YAML must declare `time_column`.
- **Site clock** — the maximum timestamp across operational tables, excluding
  `agent_approvals` and `agent_run_log`, which the agents write themselves and
  which would otherwise pull the clock to the present.

### 3.4 `mining_agents/context/render.py`

```python
def render_data_scope(source_tables: Sequence[str], snapshot: Snapshot) -> str
def render_site_clock(snapshot: Snapshot) -> str
```

Pure functions over the loaded snapshot; no network. Called by
`build_instruction` in `patterns/deep.py`, which every Pattern B agent and
every swarm node already routes through — so one change reaches all 100 agents.

Rendered output replaces the bare table list:

```
DATA SCOPE — you may read only these objects:

  mining_data.telemetry_stream — continuous sensor readings from fixed plant
  and mobile assets, one row per asset per metric per hour.
  25,946 rows, covering 2026-01-01 → 2026-06-16 22:00.
      asset_id      STRING     asset this reading belongs to; joins assets.asset_id
      metric_name   STRING     sensor channel. The unit is the name's suffix
                               (_c Celsius, _kmh, _hz, _mw, _rpm, _tph, _kn,
                               _mps, _tons, _pct). One of: belt_tension_kn,
                               engine_temp_c, feed_rate_tph, load_pct,
                               payload_tons, power_draw_mw, rotational_speed_rpm,
                               rotational_torque_nm, speed_kmh, speed_mps,
                               temperature_c, vibration_hz
      metric_value  FLOAT64    the reading, in the unit implied by metric_name
      timestamp     TIMESTAMP  hour the reading was taken, UTC

SITE CLOCK — operational data ends 2026-06-16 22:00 UTC. Treat that instant as
"now". "Last 24 hours" means the last 24 hours of available data, not of
wall-clock time. State that you have done so.
```

### 3.5 Swarm stage instructions

All five nodes get the injected context. Additionally, the critic and the
coordinator are synthesis roles and must stop exploring:

- **Critic** — "You hold the specialists' findings. Query only to verify a
  specific claim you intend to challenge. Do not survey the schema."
- **Coordinator** — "You hold the critic's audit and the specialists'
  findings. Conclude from them. Do not re-query."

The stage *ordering* is not changed. Specialists already fan out in parallel;
the critic must follow the barrier and the coordinator must follow the critic.
That sequence is the product, not overhead.

---

## 4. Testing

**Discovery-query count — the primary gate.** After a live run of `D01`, no
`bq_query` call may reference `INFORMATION_SCHEMA`, and no call may be a bare
`SELECT * ... LIMIT n` or a lone `MAX(timestamp)` probe. This is the assertion
that actually proves the fix: latency drifts with model behaviour, the count
does not. A test that only asserted "faster" would pass on a lucky run.

**Snapshot drift.** `scripts/build_context.py --check` regenerates the snapshot
and fails if it differs from the committed file. This is what stops baked-in
context going stale when BigQuery changes underneath it. Runs in CI.

**Annotation round-trip.** After `annotate_bigquery.py` runs, every table and
column named in the YAML has a matching description in
`COLUMN_FIELD_PATHS` / `TABLE_OPTIONS`. Asserts the console and the prompt
agree — the guarantee the whole design rests on.

**Render unit tests.** `render_data_scope` returns only the requested tables;
asking for a table absent from the snapshot raises rather than silently
omitting. An agent given an empty scope is a defect, not a default.

**Site clock derivation.** Asserts the clock excludes `agent_approvals` and
`agent_run_log`. Without that exclusion the clock reads "now" and the whole
mechanism silently reverts to the current broken behaviour.

**Latency, measured not asserted.** Re-run the probes and record the numbers.
Reported, not gated — a wall-clock threshold in CI would be flaky.

---

## 5. Success criteria

1. `D01` completes with zero orientation queries. Target under 25s, from 48s.
2. `S01` completes with zero orientation queries on any of its five nodes.
   Target under 100s, from 192s.
3. Asked about "the last 24 hours", an agent states which window it actually
   used and why, rather than reporting an empty result as an absence of
   findings.
4. Opening any `mining_data` table in the BigQuery console shows a table
   description and described columns.
5. Every one of the 141 columns across the 25 agent-referenced tables carries a
   description, and every one of those 25 tables carries a table description,
   each traceable to the generator or to the data. Backup snapshots and tables
   no agent reads are out of scope.
6. CI fails if the committed snapshot no longer matches BigQuery.

---

## 6. Out of scope

- The demo application. Designed after this lands.
- Adopting MCP. Documented above as the productionisation path, not built.
- Knowledge Catalog AI-generated descriptions. We have the generators, which
  are a better source than inference over the data.
- `min-instances` to remove the 4.6s cold start. Real but small, and it costs
  money on an idle project.
- Modifying the dataset in any way.

---

## 7. Open items

- **`rfp_items` exists.** `docs/personas-and-value-tree.md` §5.2 records "no
  draft-RFP data exists in `mining_data`" as a job orphan. `rfp_items` is in
  the dataset, with `rfp_id` and `part_number`. The orphan finding needs
  re-examination — it may be wrong, or the table may be insufficient for the
  job described. Not resolved here; flagged so it is not forgotten.
- **Unit conventions.** Where a numeric column's unit is not established by the
  generator, the description says so rather than guessing.
