# Agent Context Implementation Plan

> **For agentic workers:** implement this plan task-by-task, in order. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every one of the 100 agents its schema, its column meanings, its data coverage and the site clock inside its system instruction, so that no agent spends a round-trip rediscovering facts and no agent reports an empty result as an absence of findings.

**Architecture:** A curated YAML file carries human-authored column and table meaning. A script writes that meaning into BigQuery as real table and column descriptions, so the console and the prompt cannot diverge. A second script reads BigQuery back and writes a committed JSON snapshot that also carries row counts, time coverage and low-cardinality value sets. Pure render functions turn that snapshot into one instruction block per agent, filtered to the tables the agent declared. `build_instruction` in `patterns/deep.py` is the single funnel every Pattern B agent and every swarm node already routes through, so one edit reaches all 100.

**Tech Stack:** Python 3.12, pydantic 2, PyYAML 6, `google-cloud-bigquery`, google-adk 2.x, pytest.

---

## Global Constraints

Every task's requirements implicitly include this section.

**Interpreter and commands.** The interpreter is `python3`. All commands in this plan run from the repo root `.`. Bash working directory persists between calls in this environment — use absolute paths or `cd` to the repo root first in the same command.

**Branch.** `feat/agents-phase-5`. Commit after each task. Never push to a remote.

**Denied commands.** `git reset --hard`, `git clean`, `git branch -D`, `git checkout --`, `rm -rf`, `sudo`, and `curl` are blocked by settings. Use `urllib.request` from Python instead of `curl`.

**Tests hit live BigQuery.** This repo has no mocks, no skip markers and no integration markers. `pyproject.toml` sets `addopts = "--import-mode=importlib"` and `testpaths = ["tests", "data/generator/tests", "data/models/tests"]`. Project `your-gcp-project-id`, dataset `mining_data`, location `US`.

**House assertion rules.** Any assertion that would also pass on empty input is a defect — assert the collection is non-empty before asserting properties of its members. A test may not hardcode the value it validates; derive the expected value from an independent source.

**MECE / APQC organisation (binds `agentic-product-workflow`).** `docs/column-semantics.yaml` is a client-facing deliverable that a subject-matter expert reviews, not an alphabetical data dictionary. It is organised into six domain sections. The six are **mutually exclusive and collectively exhaustive over the 25 agent-referenced tables**: every table appears in exactly one section, and 4 + 3 + 4 + 4 + 5 + 5 = 25. Each section header states the section name and the APQC process codes the catalog already assigns to the agents that read those tables. Do not invent APQC codes — the codes in play are exactly those in `mining_agents/catalog/definitions.py`: `2.0.1`, `4.1.2`, `4.2.2`, `4.3.1`, `5.2.1`, `9.1.2`, `11.0.3`. The canonical section-to-table assignment is in the File Structure section below and must not be changed by any task.

**Human-readable output (binds `ui-ux-design-system`).** This plan builds no screen. It does produce two artifacts a human reads: `docs/column-semantics.yaml` and the rendered `DATA SCOPE` / `SITE CLOCK` instruction block. Both follow the design system's content rules: no emoji, no decorative rules or ASCII art, sentence case in prose, and a unit named wherever a number is reported. The site-clock string produced here will later be surfaced verbatim in the demo application, so it must read as a sentence a CEO could be shown, not as a debug dump. If a task finds itself editing CSS or HTML, it is out of scope — stop and report.

**Grounding rule — no description may assert a fact that neither the generator nor the data supports.** Consult sources in this order:

1. The generator module in `data/generator/` that writes the table, if one exists. Ten of the 25 tables are generated — `biometric_fatigue_logs`, `crusher_states`, `drill_assay_logs`, `erp_work_orders`, `fatigue_logs_node`, `geological_block_models`, `inventory_levels`, `maintenance_logs`, `metallurgical_recovery`, `telemetry_stream` — one parquet each under `data/generated/`. The other fifteen pre-date the generators and have no generator of record.
2. `data/profile/stats.json` (a calibration profile captured 2026-08-10) and a live profiling query against the table.
3. The comment blocks above each swarm and agent in `mining_agents/catalog/definitions.py`, which state the business purpose of the tables that agent reads.

Where the generator's stated intent and the loaded data disagree, that is a defect to **raise in your report**, not a wording choice to smooth over. Where none of the three sources establishes a column's unit or meaning, the description states the observable fact only and says the unit is not established. Do not guess a unit.

**Two documented deviations from the approved spec.** Both are deliberate; do not "fix" them back.

- The spec (§3.3) names `data/context_snapshot.json`. This plan writes `mining_agents/context/snapshot.json` instead. Reason: `scripts/packages.py` copies only `SHARED_TREES = ("mining_agents", "references")` into each of the 52 deploy packages, because `adk deploy cloud_run` has no `--extra_packages` and ships nothing but the agent directory. A snapshot under `data/` would not travel, and the agents would die on their first request with `FileNotFoundError` inside the container — the exact failure `scripts/packages.py`'s docstring documents for `references/`. Putting the snapshot inside `mining_agents/context/` makes it travel with zero deploy change.
- The spec (§3.2, §3.3) names `ALTER TABLE ... SET OPTIONS(description=...)` and the `TABLE_OPTIONS` / `COLUMN_FIELD_PATHS` views. The write path and the builder's read path use the `google-cloud-bigquery` client API (`get_table`, `update_table`) instead, because hand-built DDL requires quoting arbitrary prose into a SQL literal and `TABLE_OPTIONS.option_value` returns a SQL literal that must be unquoted on the way back. The **round-trip test** still reads through `INFORMATION_SCHEMA.COLUMN_FIELD_PATHS` and `TABLE_OPTIONS` — deliberately a different path from the write, so the test can catch a write that silently dropped a description.

**Never modify the dataset's rows.** This work adds metadata only. It does not touch the `*_original_20260810` backup tables at all.

---

## File Structure

**Created:**

| Path | Responsibility |
|---|---|
| `docs/column-semantics.yaml` | The human-owned, SME-reviewable source of table and column meaning. Six MECE domain sections, 25 tables, 141 columns. No code reads it at agent runtime. |
| `scripts/semantics.py` | Build-time loader and validator for the YAML. Lives in `scripts/` rather than `mining_agents/` so that PyYAML never becomes a container runtime dependency. |
| `scripts/annotate_bigquery.py` | Writes the YAML into BigQuery as real table and column descriptions. Idempotent, `--dry-run`. |
| `scripts/build_context.py` | Reads BigQuery back — structure, descriptions, row counts, time coverage, low-cardinality value sets, site clock — and writes the snapshot. `--check` mode fails on drift. |
| `mining_agents/context/__init__.py` | Package marker. |
| `mining_agents/context/models.py` | `ColumnFact`, `TableFact`, `Snapshot` pydantic models plus `load_snapshot()`. Standard library and pydantic only — no network, no YAML. |
| `mining_agents/context/snapshot.json` | The committed, diffable snapshot. Travels into every deploy package. |
| `mining_agents/context/render.py` | `render_data_scope`, `render_site_clock`. Pure functions over a loaded `Snapshot`. |
| `scripts/verify_context.py` | Calls a deployed agent and counts orientation queries in the returned events. The primary acceptance gate. |
| `tests/context/__init__.py` | Package marker. |
| `tests/context/test_semantics.py` | YAML structure, per-table column agreement with live BigQuery, and the dataset-wide completeness gate. |
| `tests/context/test_annotate.py` | Annotation round-trip through `INFORMATION_SCHEMA`. |
| `tests/context/test_build_context.py` | Snapshot drift, site-clock derivation, profiling correctness. |
| `tests/context/test_render.py` | Render output shape and filtering. |

**Modified:**

| Path | Change |
|---|---|
| `requirements.txt` | Add `pyyaml>=6.0`. |
| `scripts/packages.py:62` | Rename `_TEST_ONLY` to `_TOOLING_ONLY`, add `"pyyaml"`. |
| `tests/test_packages.py:113-116` | Extend the runtime-requirements assertion to pyyaml. |
| `mining_agents/patterns/deep.py:50-60` | `build_instruction` renders the injected data scope and site clock instead of a bare table list. |
| `tests/patterns/test_deep.py` | Assertions on the injected instruction. |
| `mining_agents/patterns/swarm.py:59-112` | Critic and coordinator get stage instructions that stop them re-exploring. |
| `tests/patterns/test_swarm.py` | Assertions on the stage instructions. |

**The canonical six-section, 25-table assignment.** Column counts are verified against live BigQuery as of 2026-08-12 and sum to 141.

**Section 1 — Asset and Telemetry (APQC 11.0.3).** 4 tables, 22 columns.
```
mining_data.assets                     8 columns
mining_data.asset_dependencies         4 columns
mining_data.telemetry_stream           4 columns
mining_data.simulation_runs            6 columns
```

**Section 2 — Maintenance and Work Management (APQC 11.0.3, 4.1.2).** 3 tables, 16 columns.
```
mining_data.erp_work_orders            7 columns
mining_data.maintenance_logs           6 columns
mining_data.work_order_parts_edge      3 columns
```

**Section 3 — Supply Chain and Procurement (APQC 4.1.2, 5.2.1).** 4 tables, 18 columns.
```
mining_data.inventory_levels           6 columns
mining_data.procurement_bids           7 columns
mining_data.rfp_items                  2 columns
mining_data.bid_parts_edge             3 columns
```

**Section 4 — Mine Operations and Haulage (APQC 4.3.1).** 4 tables, 20 columns.
```
mining_data.fleet_vehicles             7 columns
mining_data.haulage_routes             6 columns
mining_data.operator_vehicle_assignments  5 columns
mining_data.operators_node             2 columns
```

**Section 5 — Safety and Human Factors (APQC 9.1.2).** 5 tables, 31 columns.
```
mining_data.biometric_fatigue_logs     6 columns
mining_data.fatigue_logs_node          7 columns
mining_data.safety_incidents           8 columns
mining_data.incident_involvements      4 columns
mining_data.radio_communications       6 columns
```

**Section 6 — Geology and Processing (APQC 2.0.1, 4.2.2).** 5 tables, 34 columns.
```
mining_data.drill_holes                7 columns
mining_data.drill_assay_logs           7 columns
mining_data.geological_block_models    8 columns
mining_data.metallurgical_recovery     6 columns
mining_data.crusher_states             6 columns
```

---

### Task 1: Semantics loader, the YAML's first entry, and the PyYAML dependency

**Files:**
- Create: `docs/column-semantics.yaml`
- Create: `scripts/semantics.py`
- Create: `tests/context/__init__.py`
- Create: `tests/context/test_semantics.py`
- Modify: `requirements.txt`
- Modify: `scripts/packages.py:59-62`
- Modify: `tests/test_packages.py:113-116`

**Interfaces:**
- Consumes: `mining_agents.catalog.definitions.ALL_AGENTS` (list of `AgentDef`; the field used here is `source_tables: list[str]`, each entry a `mining_data.<table>` string).
- Produces: `scripts.semantics.agent_tables() -> frozenset[str]`, `scripts.semantics.load_semantics(path: pathlib.Path | None = None) -> dict[str, TableSemantics]`, `scripts.semantics.SEMANTICS_PATH: pathlib.Path`, `scripts.semantics.TableSemantics` (pydantic model with `description: str` and `columns: dict[str, str]`). Tasks 2–6 add entries to the YAML; Task 7 reads `load_semantics()` to write BigQuery.

**Context you need:** `scripts/` is already a Python package (`scripts/__init__.py` exists, alongside `deploy.py` and `packages.py`), so `python -m scripts.semantics` and `from scripts.semantics import ...` both work from the repo root.

- [ ] **Step 1: Add the PyYAML dependency and keep it out of the containers**

`requirements.txt` gains one line after `db-dtypes>=1.2`:

```
pyyaml>=6.0
```

In `scripts/packages.py`, rename the tuple and add pyyaml. The existing block at lines 59-62 reads:

```python
# Packages the container does not need because nothing in `mining_agents/` imports
# them at runtime. Everything else in the repo's requirements.txt travels, so
# adding a runtime dependency there is enough — this module needs no edit.
_TEST_ONLY = ("pytest",)
```

Replace it with:

```python
# Packages the container does not need because nothing in `mining_agents/` imports
# them at runtime. Everything else in the repo's requirements.txt travels, so
# adding a runtime dependency there is enough — this module needs no edit.
# pyyaml is read only by scripts/semantics.py, which is build-time tooling and
# is deliberately not under mining_agents/ for exactly this reason.
_TOOLING_ONLY = ("pytest", "pyyaml")
```

Then update the single use site, currently line 107:

```python
        and not line.split("=")[0].split(">")[0].split("<")[0].strip() in _TOOLING_ONLY
```

- [ ] **Step 2: Write the failing test**

Create `tests/context/__init__.py` as an empty file. Create `tests/context/test_semantics.py`:

```python
"""The YAML is the human-owned half of the context pipeline. These tests hold it
to the only two things a machine can check: that it parses into the declared
shape, and that the columns it names are the columns BigQuery actually has.

Whether a description is TRUE is a review question, not a test question. What a
test can stop is a description attached to a column that does not exist, which
would be invisible until an agent read a prompt describing a phantom field.
"""
from __future__ import annotations

import pytest
from google.cloud import bigquery

from mining_agents.config import settings
from scripts.semantics import (
    MIN_DESCRIPTION_CHARS,
    TableSemantics,
    agent_tables,
    load_semantics,
)


@pytest.fixture(scope="module")
def semantics() -> dict[str, TableSemantics]:
    return load_semantics()


@pytest.fixture(scope="module")
def live_columns() -> dict[str, set[str]]:
    """Top-level column names per table, straight from BigQuery."""
    s = settings()
    client = bigquery.Client(project=s.project_id, location=s.location)
    sql = f"""
        SELECT table_name, field_path
        FROM `{s.project_id}.{s.dataset}.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS`
        WHERE NOT CONTAINS_SUBSTR(field_path, '.')
    """
    found: dict[str, set[str]] = {}
    for row in client.query(sql).result():
        found.setdefault(f"{s.dataset}.{row['table_name']}", set()).add(row["field_path"])
    assert found, "INFORMATION_SCHEMA returned no columns at all; the rest of this file would pass vacuously"
    return found


def test_agent_tables_is_the_25_table_surface():
    tables = agent_tables()
    assert len(tables) == 25, (
        f"the catalog now declares {len(tables)} distinct tables, not 25. "
        "The plan's six MECE sections were sized against 25 — re-derive them "
        f"before continuing. Tables: {sorted(tables)}"
    )
    for table in tables:
        assert table.startswith("mining_data."), (
            f"{table!r} is not in mining_data; the annotate and build scripts "
            "assume a single dataset"
        )


def test_yaml_parses_and_declares_only_agent_tables(semantics):
    assert semantics, "load_semantics() returned nothing"
    unknown = set(semantics) - agent_tables()
    assert not unknown, f"described but read by no agent: {sorted(unknown)}"


def test_every_described_column_exists_in_bigquery(semantics, live_columns):
    assert semantics, "no tables described yet; this test would pass vacuously"
    for table, entry in semantics.items():
        assert table in live_columns, f"{table} is described but not in BigQuery"
        phantom = set(entry.columns) - live_columns[table]
        assert not phantom, (
            f"{table}: described columns that do not exist: {sorted(phantom)}"
        )


def test_each_described_table_is_described_completely(semantics, live_columns):
    """Partial coverage of a table is worse than none: the agent cannot tell
    which of the columns in front of it were reviewed."""
    assert semantics, "no tables described yet; this test would pass vacuously"
    for table, entry in semantics.items():
        missing = live_columns[table] - set(entry.columns)
        assert not missing, f"{table}: columns present in BigQuery but undescribed: {sorted(missing)}"


def test_a_short_description_is_refused():
    with pytest.raises(ValueError):
        TableSemantics.model_validate(
            {"description": "x" * MIN_DESCRIPTION_CHARS, "columns": {"a": "too short"}}
        )


def test_a_table_with_no_columns_is_refused():
    with pytest.raises(ValueError):
        TableSemantics.model_validate({"description": "y" * 40, "columns": {}})


def test_a_time_column_naming_a_column_that_does_not_exist_is_refused():
    with pytest.raises(ValueError):
        TableSemantics.model_validate({
            "description": "y" * 40,
            "columns": {"observed_at": "z" * 40},
            "time_column": "recorded_at",
        })
```

- [ ] **Step 3: Run the test to verify it fails**

```bash
cd . && \
  python3 -m pytest tests/context/test_semantics.py -v
```

Expected: collection error, `ModuleNotFoundError: No module named 'scripts.semantics'`.

- [ ] **Step 4: Write the loader**

Create `scripts/semantics.py`:

```python
"""Load and validate docs/column-semantics.yaml.

Build-time only. This module lives in `scripts/` rather than under
`mining_agents/` so that PyYAML never becomes a runtime dependency of the 52
deploy packages. `scripts/packages.py` copies `mining_agents/` verbatim into
every container, and a runtime import of a package the container does not have
is a failure that costs a full container build to discover.
"""
from __future__ import annotations

import pathlib

import yaml
from pydantic import BaseModel, field_validator, model_validator

from mining_agents.catalog.definitions import ALL_AGENTS

SEMANTICS_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "docs" / "column-semantics.yaml"
)

# Long enough that "the asset id" cannot pass as a description. A column
# description that only restates the column name teaches an agent nothing and
# costs the same tokens as one that does.
MIN_DESCRIPTION_CHARS = 25


class TableSemantics(BaseModel):
    description: str
    columns: dict[str, str]
    # Only needed for a table carrying more than one TIMESTAMP/DATETIME/DATE
    # column. Verified 2026-08-12: of the 25 agent-referenced tables, sixteen
    # have exactly one and nine have none — none has two — so every entry
    # currently omits this and scripts/build_context.py infers the column. The
    # field exists so that a future ambiguity is DECLARED rather than guessed
    # at; the builder raises rather than picking one.
    time_column: str | None = None

    @model_validator(mode="after")
    def _time_column_is_a_real_column(self) -> "TableSemantics":
        if self.time_column is not None and self.time_column not in self.columns:
            raise ValueError(
                f"time_column {self.time_column!r} is not one of this table's "
                f"described columns: {sorted(self.columns)}"
            )
        return self

    @field_validator("description")
    @classmethod
    def _substantive(cls, value: str) -> str:
        text = " ".join(value.split())
        if len(text) < MIN_DESCRIPTION_CHARS:
            raise ValueError(
                f"table description is {len(text)} characters; at least "
                f"{MIN_DESCRIPTION_CHARS} are needed to say anything an agent "
                f"could use: {text!r}"
            )
        return text

    @field_validator("columns")
    @classmethod
    def _all_columns_described(cls, value: dict[str, str]) -> dict[str, str]:
        if not value:
            raise ValueError("a table entry with no columns describes nothing")
        cleaned: dict[str, str] = {}
        for name, description in value.items():
            text = " ".join(str(description).split())
            if len(text) < MIN_DESCRIPTION_CHARS:
                raise ValueError(
                    f"column {name!r} description is {len(text)} characters; at "
                    f"least {MIN_DESCRIPTION_CHARS} are needed: {text!r}"
                )
            cleaned[name] = text
        return cleaned


def agent_tables() -> frozenset[str]:
    """Every table any of the 100 agents declares — the scope of this work.

    Derived from the catalog rather than listed here, so that adding a table to
    an agent's source_tables makes the completeness test fail loudly instead of
    leaving the new table silently undescribed.
    """
    return frozenset(t for a in ALL_AGENTS for t in a.source_tables)


def load_semantics(path: pathlib.Path | None = None) -> dict[str, TableSemantics]:
    """Parse the YAML. Refuses any table no agent reads."""
    source = path or SEMANTICS_PATH
    raw = yaml.safe_load(source.read_text())
    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"{source} did not parse to a non-empty mapping")

    allowed = agent_tables()
    parsed: dict[str, TableSemantics] = {}
    for table, body in raw.items():
        if table not in allowed:
            raise ValueError(
                f"{table!r} is described but no agent declares it, so no agent "
                "would ever see the description. Remove it, or fix the name."
            )
        parsed[table] = TableSemantics.model_validate(body)
    return parsed
```

- [ ] **Step 5: Write the YAML's first entry**

Create `docs/column-semantics.yaml`. This file is read by a subject-matter expert, so the section comments matter as much as the content. Tasks 2–6 fill in the remaining sections in place.

Note the cadence claim below: `stats.json` and a live check both show readings every **two hours** — 1,993 to 1,998 rows per asset-metric pair across 2026-01-01 00:00 to 2026-06-16 22:00 — not hourly. The spec's illustrative example said "per hour" and was wrong. This is the grounding rule doing its job; do not copy the spec's example text.

```yaml
# Column semantics for the mining_data tables the 100 agents read.
#
# This file is the human-owned source of meaning. scripts/annotate_bigquery.py
# writes it into BigQuery as real table and column descriptions, and
# scripts/build_context.py reads BigQuery back into the snapshot the agents are
# given. Editing BigQuery by hand instead of editing this file will be undone
# by the next annotate run.
#
# Every statement here is grounded in the generator that writes the table
# (data/generator/*.py), in the loaded data, or in the catalog's own comments.
# Where a unit is not established by one of those, the description says so.
#
# Organised into six sections. Every one of the 25 agent-referenced tables
# appears in exactly one section: 4 + 3 + 4 + 4 + 5 + 5 = 25.

# ---------------------------------------------------------------------------
# Section 1 — Asset and Telemetry.  APQC 11.0.3.
# Read by the asset-reliability and site-wide agents (persona P1, P8).
# ---------------------------------------------------------------------------

mining_data.telemetry_stream:
  description: >
    Continuous sensor readings from fixed plant and mobile assets, in long
    format: one row per asset per metric per reading. Readings are taken every
    two hours, not hourly, and a small number of slots are missing.
  columns:
    asset_id: >
      The asset this reading was taken from. Joins mining_data.assets.asset_id.
    metric_name: >
      Which sensor channel this row reports. The unit is the suffix of the name
      itself — _c is Celsius, _kmh kilometres per hour, _mps metres per second,
      _hz hertz, _mw megawatts, _rpm revolutions per minute, _nm newton-metres,
      _tph tonnes per hour, _kn kilonewtons, _tons tonnes, _pct percent. There
      is no separate unit column.
    metric_value: >
      The reading itself, in the unit implied by metric_name. Comparing values
      across different metric_name values is meaningless.
    timestamp: >
      The instant the reading was taken, UTC. This is the table's only time
      column.
```

- [ ] **Step 6: Extend the packages test**

In `tests/test_packages.py`, the existing block at lines 113-116 is:

```python
    assert "pytest" in (_repo_root() / "requirements.txt").read_text(), (
        "requirements.txt no longer pins pytest — this test would pass vacuously"
    )
    assert "pytest" not in runtime_requirements()
```

Extend it in place:

```python
    requirements = (_repo_root() / "requirements.txt").read_text()
    for package in ("pytest", "pyyaml"):
        assert package in requirements, (
            f"requirements.txt no longer pins {package} — this test would pass "
            "vacuously"
        )
        assert package not in runtime_requirements(), (
            f"{package} reached the container requirements. Nothing under "
            "mining_agents/ imports it; shipping it means a container "
            "dependency no code needs."
        )
```

- [ ] **Step 7: Run the tests to verify they pass**

```bash
cd . && \
  python3 -m pytest \
  tests/context/test_semantics.py tests/test_packages.py -v
```

Expected: all PASS. `test_agent_tables_is_the_25_table_surface` confirms 25 tables; `test_each_described_table_is_described_completely` confirms all 4 telemetry columns are covered.

- [ ] **Step 8: Commit**

```bash
cd . && \
  git add docs/column-semantics.yaml scripts/semantics.py tests/context/__init__.py \
    tests/context/test_semantics.py requirements.txt scripts/packages.py \
    tests/test_packages.py && \
  git commit -m "feat(context): semantics loader and the first described table

Agents are told table names and nothing else, so each one rediscovers the
schema every request. This is the human-owned half of the fix: a YAML of
column meaning, validated against the columns BigQuery actually has."
```

---

## A note on Tasks 2 to 5

These four tasks write the remaining 137 column descriptions. Their content is
research output, not transcription: the exact wording depends on what the
generator and the data say, and neither this plan nor its author may assert a
fact on their behalf. What each task specifies exactly is the table and column
list, the grounding sources to read, the profiling command that produces the
facts, the YAML shape (see Task 1's `mining_data.telemetry_stream` entry — copy
its structure precisely), and the test that gates the result. Nothing is
deferred to a later task and nothing is left to taste.

**The profiling command**, used by all four tasks. Substitute the task's own
table list:

```bash
cd . && \
python3 - <<'EOF'
from google.cloud import bigquery
from mining_agents.config import settings

TABLES = ["assets", "asset_dependencies"]  # <- this task's tables, bare names

s = settings()
client = bigquery.Client(project=s.project_id, location=s.location)
for name in TABLES:
    table = client.get_table(f"{s.project_id}.{s.dataset}.{name}")
    print(f"\n=== {s.dataset}.{name}  ({table.num_rows} rows) ===")
    print(f"existing table description: {table.description!r}")
    for field in table.schema:
        print(f"  {field.name:<28} {field.field_type:<12} "
              f"mode={field.mode:<10} existing={field.description!r}")
    rows = list(client.query(
        f"SELECT * FROM `{s.project_id}.{s.dataset}.{name}` LIMIT 5"
    ).result())
    for row in rows:
        print("   ", dict(row))
EOF
```

**Three rules that apply to all four tasks.**

1. **Existing descriptions are not authority.** Eleven columns in `mining_data`
   already carry a description — four in `incident_involvements`, five in
   `operator_vehicle_assignments`, two in `rfp_items`. Read them, then decide.
   Adopt one only if the generator or the data supports it. If you change one,
   say so in your report and say why. No table carries a description at all.
2. **Say when a unit is not established.** If neither the generator nor the
   data settles what `impact_score` or `congestion_factor` is measured in, the
   description states what the column contains and states plainly that the unit
   is not established. A guessed unit is worse than an absent one, because an
   agent will compute with it.
3. **A join is a fact worth stating.** Where a column is a foreign key, name the
   table and column it joins. That is the single highest-value thing these
   descriptions can carry, because it is what an agent would otherwise spend a
   round-trip inferring.

---

### Task 2: Semantics for Asset and Telemetry (remainder) and Maintenance

**Files:**
- Modify: `docs/column-semantics.yaml` (append sections; keep Task 1's header comments and telemetry entry unchanged)
- Test: `tests/context/test_semantics.py` (no change; it grows stricter as the YAML grows)

**Interfaces:**
- Consumes: the YAML shape and the `TableSemantics` model from Task 1.
- Produces: entries for six tables that Task 7 writes into BigQuery.

**Scope — six tables, 34 columns.** Complete the Section 1 comment block Task 1
opened, then open the Section 2 block.

Section 1 — Asset and Telemetry, APQC 11.0.3 (`mining_data.telemetry_stream` is
already done):
```
mining_data.assets                8: asset_id, asset_name, asset_type,
                                     criticality_rating, current_state,
                                     installation_date, location_gis,
                                     physics_parameters
mining_data.asset_dependencies    4: source_id, target_id, dependency_type,
                                     impact_score
mining_data.simulation_runs       6: run_id, asset_id, timestamp,
                                     projected_cooling_curve,
                                     recalculated_parameters, nba_executed
```

Section 2 — Maintenance and Work Management, APQC 11.0.3 and 4.1.2:
```
mining_data.erp_work_orders       7: work_order_id, asset_id, created_at,
                                     description, priority, repair_cost, status
mining_data.maintenance_logs      6: log_entry_id, work_order_id, asset_id,
                                     technician_notes, parts_replaced,
                                     actual_duration_hours
mining_data.work_order_parts_edge 3: edge_id, work_order_id, part_number
```

**Grounding sources for this task.** `data/generator/maintenance.py` writes
`erp_work_orders`, `maintenance_logs` and `work_order_parts_edge` — read it in
full. `data/generator/supply_chain.py` also touches `assets` and
`work_order_parts_edge`; read the parts that do. `assets`,
`asset_dependencies` and `simulation_runs` have **no generator of record** —
ground them in the profiling output and in the S01 and S02 comment blocks in
`mining_agents/catalog/definitions.py`, which state what the cascading-failure
and simulation agents use them for.

**Two things to get right.** `maintenance_logs.technician_notes` and
`erp_work_orders.description` are free text written by humans and are in
`FREE_TEXT_FIELDS` (`mining_agents/safety/untrusted.py`) — the description
should say the field is operator-authored free text, because that is what makes
the untrusted-content instruction meaningful. `maintenance_logs.parts_replaced`
is `ARRAY<STRING>`; say so and say what the elements are.

- [ ] **Step 1: Profile the six tables**

Run the profiling command from the note above with
`TABLES = ["assets", "asset_dependencies", "simulation_runs", "erp_work_orders", "maintenance_logs", "work_order_parts_edge"]`.

- [ ] **Step 2: Read the generators**

```bash
cd . && \
  wc -l data/generator/maintenance.py data/generator/supply_chain.py
```

Read `data/generator/maintenance.py` in full and the `assets` and
`work_order_parts_edge` sections of `data/generator/supply_chain.py`.

- [ ] **Step 3: Write the entries**

Append to `docs/column-semantics.yaml`, following Task 1's structure exactly —
a `description:` block scalar and a `columns:` mapping of column name to block
scalar, one entry per column, in the order the columns appear in the table's
BigQuery schema. Open Section 2 with a comment block in the same form as Task
1's Section 1 header, naming the section, its APQC codes and the personas that
read it (Section 2 is read by persona P2, maintenance execution).

- [ ] **Step 4: Run the tests**

```bash
cd . && \
  python3 -m pytest \
  tests/context/test_semantics.py -v
```

Expected: all PASS. `test_each_described_table_is_described_completely` fails if
any of the 34 columns was missed, and `test_every_described_column_exists_in_bigquery`
fails on a typo in a column name.

- [ ] **Step 5: Commit**

```bash
cd . && \
  git add docs/column-semantics.yaml && \
  git commit -m "docs(context): semantics for asset, telemetry and maintenance tables

Six tables, 34 columns, grounded in data/generator/maintenance.py and in the
loaded data. assets, asset_dependencies and simulation_runs have no generator
of record and are grounded in the profile and the catalog."
```

---

### Task 3: Semantics for Supply Chain, Procurement, Mine Operations and Haulage

**Files:**
- Modify: `docs/column-semantics.yaml`
- Test: `tests/context/test_semantics.py` (no change)

**Interfaces:**
- Consumes: the YAML shape and the `TableSemantics` model from Task 1.
- Produces: entries for eight tables that Task 7 writes into BigQuery.

**Scope — eight tables, 38 columns.**

Section 3 — Supply Chain and Procurement, APQC 4.1.2 and 5.2.1, personas P4:
```
mining_data.inventory_levels      6: part_number, part_description, stock_level,
                                     reorder_point_limit, lead_time_days,
                                     unit_price_usd
mining_data.procurement_bids      7: bid_id, rfp_id, vendor_name, proposed_cost,
                                     technical_rating_score, compliance_checked,
                                     bid_status
mining_data.rfp_items             2: rfp_id, part_number
mining_data.bid_parts_edge        3: edge_id, bid_id, part_number
```

Section 4 — Mine Operations and Haulage, APQC 4.3.1, persona P7:
```
mining_data.fleet_vehicles        7: vehicle_id, model, operational_status,
                                     payload_capacity_tons,
                                     current_payload_tons, gps_location,
                                     last_telemetry_sync
mining_data.haulage_routes        6: route_id, source_location,
                                     destination_location, distance_meters,
                                     average_cycle_time_mins, congestion_factor
mining_data.operator_vehicle_assignments 5: assignment_id, operator_id,
                                     vehicle_id, shift_date, shift_type
mining_data.operators_node        2: operator_id, operator_role
```

**Grounding sources for this task.** `data/generator/supply_chain.py` writes
`inventory_levels` and `work_order_parts_edge` and reads `assets` — read it in
full for the inventory columns. `data/generator/fatigue.py` writes
`operators_node` and the operator assignments — read the parts that do.
`procurement_bids`, `rfp_items`, `bid_parts_edge`, `fleet_vehicles` and
`haulage_routes` have **no generator of record**; ground them in the profiling
output and in the S07, S09 and S11 comment blocks in
`mining_agents/catalog/definitions.py`.

**Three things to get right.**

- `operator_vehicle_assignments` already carries five column descriptions and
  `rfp_items` already carries two. Apply rule 1 from the note above: read them,
  adopt only what the data supports, and report any you change.
- `inventory_levels.unit_price_usd` names its unit; `reorder_point_limit` and
  `stock_level` are counts — say of what. `lead_time_days` is in days.
  `haulage_routes.congestion_factor` almost certainly has no established unit;
  apply rule 2 rather than inventing one.
- **Flag the `rfp_items` open item.** `docs/personas-and-value-tree.md` §5.2
  records "no draft-RFP data exists in `mining_data`" as a job orphan, but
  `rfp_items` is in the dataset with `rfp_id` and `part_number`. While
  profiling, record how many rows and how many distinct `rfp_id` values it
  holds, and state in your report whether the table is sufficient for the job
  the personas document describes. Do not edit the personas document — the
  finding goes in the report.

- [ ] **Step 1: Profile the eight tables**

Run the profiling command from the note above with
`TABLES = ["inventory_levels", "procurement_bids", "rfp_items", "bid_parts_edge", "fleet_vehicles", "haulage_routes", "operator_vehicle_assignments", "operators_node"]`.

- [ ] **Step 2: Count the rfp_items rows for the open item**

```bash
cd . && \
python3 - <<'EOF'
from google.cloud import bigquery
from mining_agents.config import settings
s = settings()
client = bigquery.Client(project=s.project_id, location=s.location)
sql = f"""
  SELECT COUNT(*) AS n_rows,
         COUNT(DISTINCT rfp_id) AS n_rfps,
         COUNT(DISTINCT part_number) AS n_parts
  FROM `{s.project_id}.{s.dataset}.rfp_items`
"""
print(dict(next(iter(client.query(sql).result()))))
EOF
```

- [ ] **Step 3: Read the generators**

Read `data/generator/supply_chain.py` in full, and the `operators_node` and
operator-assignment sections of `data/generator/fatigue.py`.

- [ ] **Step 4: Write the entries**

Append to `docs/column-semantics.yaml`, opening Section 3 and Section 4 with
comment blocks in the same form as Task 1's Section 1 header.

- [ ] **Step 5: Run the tests**

```bash
cd . && \
  python3 -m pytest \
  tests/context/test_semantics.py -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
cd . && \
  git add docs/column-semantics.yaml && \
  git commit -m "docs(context): semantics for supply chain, procurement and mine ops

Eight tables, 38 columns. Replaces the seven pre-existing column descriptions
on operator_vehicle_assignments and rfp_items with text grounded in the
generators and the loaded data."
```

---

### Task 4: Semantics for Safety and Human Factors

**Files:**
- Modify: `docs/column-semantics.yaml`
- Test: `tests/context/test_semantics.py` (no change)

**Interfaces:**
- Consumes: the YAML shape and the `TableSemantics` model from Task 1.
- Produces: entries for five tables that Task 7 writes into BigQuery.

**Scope — five tables, 31 columns.** Section 5 — Safety and Human Factors,
APQC 9.1.2, persona P3:
```
mining_data.biometric_fatigue_logs  6: operator_id, timestamp, heart_rate_bpm,
                                       sleep_deficit_hours,
                                       microsleep_events_detected,
                                       fatigue_alert_triggered
mining_data.fatigue_logs_node       7: log_id, operator_id, timestamp,
                                       heart_rate_bpm, sleep_deficit_hours,
                                       microsleep_events_detected,
                                       fatigue_alert_triggered
mining_data.safety_incidents        8: incident_id, timestamp, severity_level,
                                       description, root_cause,
                                       location_description, gps_location,
                                       investigation_status
mining_data.incident_involvements   4: involvement_id, incident_id, operator_id,
                                       vehicle_id
mining_data.radio_communications    6: channel_id, timestamp, transcript,
                                       audio_gcs_path, sentiment_score,
                                       emergency_keyword_flag
```

**Grounding sources for this task.** `data/generator/fatigue.py` writes
`biometric_fatigue_logs` and `fatigue_logs_node` and links operators to
incidents — read it in full. `safety_incidents`, `incident_involvements` and
`radio_communications` have **no generator of record**; ground them in the
profiling output and in the S03 and S10 comment blocks in
`mining_agents/catalog/definitions.py`.

**Four things to get right.**

- **`biometric_fatigue_logs` and `fatigue_logs_node` hold the same three
  biometric measures.** `mining_agents/patterns/deep.py:23` names both in
  `BIOMETRIC_TABLES` — the first is the primary operational table, the second
  is the graph-facing node table in the safety property graph. Say which is
  which, and say that they carry the same measures, because an agent that
  cannot tell them apart will read both and double-count.
- **The three biometric columns are `heart_rate_bpm`, `sleep_deficit_hours` and
  `microsleep_events_detected`** (`mining_agents/safety/output_filter.py:40`).
  Their descriptions must state that the value is never reported raw — fatigue
  is reported as a band, LOW / ELEVATED / HIGH — because an agent reading only
  the column description should already know the constraint. The description
  states the rule; it does not enumerate example readings.
- **`incident_involvements` already carries four column descriptions** — all
  four of its columns. Apply rule 1 from the note above.
- **Three columns here are untrusted free text**:
  `safety_incidents.description`, `safety_incidents.root_cause` and
  `radio_communications.transcript` (`mining_agents/safety/untrusted.py:25`).
  Each description must say the field is human-authored free text that arrives
  wrapped and is to be treated strictly as data. `radio_communications.transcript`
  is a transcription of radio audio, so it also carries transcription error —
  say so if the data supports it.

- [ ] **Step 1: Profile the five tables**

Run the profiling command from the note above with
`TABLES = ["biometric_fatigue_logs", "fatigue_logs_node", "safety_incidents", "incident_involvements", "radio_communications"]`.

- [ ] **Step 2: Compare the two fatigue tables**

```bash
cd . && \
python3 - <<'EOF'
from google.cloud import bigquery
from mining_agents.config import settings
s = settings()
client = bigquery.Client(project=s.project_id, location=s.location)
sql = f"""
  SELECT 'biometric_fatigue_logs' AS t, COUNT(*) AS n,
         COUNT(DISTINCT operator_id) AS operators,
         MIN(timestamp) AS t0, MAX(timestamp) AS t1
  FROM `{s.project_id}.{s.dataset}.biometric_fatigue_logs`
  UNION ALL
  SELECT 'fatigue_logs_node', COUNT(*), COUNT(DISTINCT operator_id),
         MIN(timestamp), MAX(timestamp)
  FROM `{s.project_id}.{s.dataset}.fatigue_logs_node`
"""
for row in client.query(sql).result():
    print(dict(row))
EOF
```

Whatever this shows — the same rows in both, or different populations — is what
the two descriptions must say. If the generator's stated intent and this result
disagree, raise it in your report rather than writing around it.

- [ ] **Step 3: Read the generator**

Read `data/generator/fatigue.py` in full.

- [ ] **Step 4: Write the entries**

Append to `docs/column-semantics.yaml`, opening Section 5 with a comment block
in the same form as Task 1's Section 1 header.

- [ ] **Step 5: Run the tests**

```bash
cd . && \
  python3 -m pytest \
  tests/context/test_semantics.py -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
cd . && \
  git add docs/column-semantics.yaml && \
  git commit -m "docs(context): semantics for safety and human factors tables

Five tables, 31 columns. The three biometric columns carry the band-only
reporting rule in their own descriptions, and the two fatigue tables state
which is the operational table and which the graph node."
```

---

### Task 5: Semantics for Geology and Processing

**Files:**
- Modify: `docs/column-semantics.yaml`
- Test: `tests/context/test_semantics.py` (no change)

**Interfaces:**
- Consumes: the YAML shape and the `TableSemantics` model from Task 1.
- Produces: entries for five tables. After this task all 25 tables and all 141
  columns are described, which Task 6 then gates.

**Scope — five tables, 34 columns.** Section 6 — Geology and Processing,
APQC 2.0.1 and 4.2.2, personas P5 and P6:
```
mining_data.drill_holes             7: drill_hole_id, collar_easting,
                                       collar_northing, collar_elevation,
                                       azimuth_degrees, dip_degrees,
                                       total_depth_meters
mining_data.drill_assay_logs        7: drill_hole_id, depth_start_meters,
                                       depth_end_meters, copper_grade_pct,
                                       gold_grade_gpt, geology_code, logged_at
mining_data.geological_block_models 8: block_id, centroid_x, centroid_y,
                                       centroid_z, copper_grade_pct_est,
                                       gold_grade_gpt_est, lithology_type,
                                       specific_gravity
mining_data.metallurgical_recovery  6: concentrator_id, timestamp,
                                       feed_grade_pct, concentrate_grade_pct,
                                       tailings_grade_pct, recovery_rate_pct
mining_data.crusher_states          6: asset_id, timestamp, feed_rate_tph,
                                       rotational_torque_nm,
                                       gap_size_setting_mm, bypass_valve_open
```

**Grounding sources for this task.** `data/generator/geology.py` writes
`drill_holes`, `drill_assay_logs` and `geological_block_models`.
`data/generator/metallurgy.py` writes `metallurgical_recovery` and
`crusher_states`. Read both in full. Every table in this section has a
generator of record, so there is no excuse for an ungrounded claim here.

**Four things to get right.**

- **Units are the whole point of this section.** `_pct` is percent, `_gpt` is
  grams per tonne, `_meters`, `_degrees`, `_tph`, `_nm`, `_mm`. State each one.
  `specific_gravity` is dimensionless — say so explicitly rather than leaving
  it unsaid, so an agent does not go looking for a unit.
- **Measured versus estimated.** `drill_assay_logs.copper_grade_pct` and
  `gold_grade_gpt` are assayed measurements from physical core;
  `geological_block_models.copper_grade_pct_est` and `gold_grade_gpt_est` are
  model estimates interpolated from them. Confirm that against
  `data/generator/geology.py` and then say it. Conflating the two is the
  single most consequential mistake a geology agent could make, and the `_est`
  suffix alone will not stop it.
- **The recovery identity.** `feed_grade_pct`, `concentrate_grade_pct`,
  `tailings_grade_pct` and `recovery_rate_pct` are related by a mass balance in
  `data/generator/metallurgy.py`. State the relationship if the generator
  establishes it, so an agent computes recovery from the stated identity
  instead of inventing one. If the generator does not establish it, say only
  what each column contains.
- **`crusher_states` overlaps `telemetry_stream`.** Both carry
  `feed_rate_tph` and `rotational_torque_nm` for crusher assets. Establish from
  the generators whether they are the same readings surfaced twice or two
  independent series, and say which. An agent that averages across both without
  knowing will double-weight.

- [ ] **Step 1: Profile the five tables**

Run the profiling command from the note above with
`TABLES = ["drill_holes", "drill_assay_logs", "geological_block_models", "metallurgical_recovery", "crusher_states"]`.

- [ ] **Step 2: Check the crusher_states / telemetry_stream overlap**

```bash
cd . && \
python3 - <<'EOF'
from google.cloud import bigquery
from mining_agents.config import settings
s = settings()
client = bigquery.Client(project=s.project_id, location=s.location)
sql = f"""
  SELECT c.asset_id, COUNT(*) AS matched_instants,
         COUNTIF(ABS(c.feed_rate_tph - t.metric_value) < 0.0001) AS identical
  FROM `{s.project_id}.{s.dataset}.crusher_states` c
  JOIN `{s.project_id}.{s.dataset}.telemetry_stream` t
    ON t.asset_id = c.asset_id
   AND t.timestamp = c.timestamp
   AND t.metric_name = 'feed_rate_tph'
  GROUP BY 1 ORDER BY 1
"""
for row in client.query(sql).result():
    print(dict(row))
EOF
```

Zero matched instants means two independent series. Matched instants where
`identical` equals `matched_instants` means the same readings surfaced twice.
Anything in between is a finding to raise in your report.

- [ ] **Step 3: Read the generators**

Read `data/generator/geology.py` and `data/generator/metallurgy.py` in full.

- [ ] **Step 4: Write the entries**

Append to `docs/column-semantics.yaml`, opening Section 6 with a comment block
in the same form as Task 1's Section 1 header.

- [ ] **Step 5: Run the tests and confirm the full surface is covered**

```bash
cd . && \
  python3 -m pytest \
  tests/context/test_semantics.py -v && \
  python3 -c "
from scripts.semantics import agent_tables, load_semantics
s = load_semantics()
print('tables described:', len(s), 'of', len(agent_tables()))
print('columns described:', sum(len(t.columns) for t in s.values()))
missing = sorted(agent_tables() - set(s))
print('missing:', missing)
"
```

Expected: all tests PASS, then `tables described: 25 of 25`,
`columns described: 141`, `missing: []`.

- [ ] **Step 6: Commit**

```bash
cd . && \
  git add docs/column-semantics.yaml && \
  git commit -m "docs(context): semantics for geology and processing tables

Five tables, 34 columns, completing all 25 tables and 141 columns of the
agent-referenced surface. Distinguishes assayed grades from model estimates,
which the _est suffix alone does not."
```

---

### Task 6: Write the semantics into BigQuery

**Files:**
- Create: `scripts/annotate_bigquery.py`
- Create: `tests/context/test_annotate.py`

**Interfaces:**
- Consumes: `scripts.semantics.load_semantics()` and `TableSemantics` from Task 1; all 25 entries from Tasks 1–5.
- Produces: `scripts.annotate_bigquery.apply(dry_run: bool = True) -> list[str]` returning the qualified names of the tables it changed (empty on a no-op run, which is what makes idempotence testable). Task 7's builder reads the descriptions this writes.

**Why the read-back path differs from the write path.** This script writes with
the `google-cloud-bigquery` client API. The test reads back through
`INFORMATION_SCHEMA.COLUMN_FIELD_PATHS` and `INFORMATION_SCHEMA.TABLE_OPTIONS`
— deliberately a different path, so a write that silently dropped a description
cannot be confirmed by the same code that dropped it. `TABLE_OPTIONS.option_value`
comes back as a **SQL string literal**, quotes and all, so it must be unquoted;
`COLUMN_FIELD_PATHS.description` comes back as a plain string and must not be.

- [ ] **Step 1: Write the failing test**

Create `tests/context/test_annotate.py`:

```python
"""The whole design rests on one guarantee: what the agent is told and what the
BigQuery console shows are the same fact rendered twice. That guarantee is only
as good as this file.

The read-back goes through INFORMATION_SCHEMA rather than through the client
API the annotator writes with. Reading back through the write path would
confirm the annotator's own opinion of what it wrote.
"""
from __future__ import annotations

import ast

import pytest
from google.cloud import bigquery

from mining_agents.config import settings
from scripts.annotate_bigquery import apply
from scripts.semantics import agent_tables, load_semantics


@pytest.fixture(scope="module")
def annotated() -> None:
    """Apply the semantics once for this module. Idempotent by construction."""
    apply(dry_run=False)


@pytest.fixture(scope="module")
def live_column_descriptions(annotated) -> dict[tuple[str, str], str | None]:
    s = settings()
    client = bigquery.Client(project=s.project_id, location=s.location)
    sql = f"""
        SELECT table_name, field_path, description
        FROM `{s.project_id}.{s.dataset}.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS`
        WHERE NOT CONTAINS_SUBSTR(field_path, '.')
    """
    found = {
        (f"{s.dataset}.{row['table_name']}", row["field_path"]): row["description"]
        for row in client.query(sql).result()
    }
    assert found, "COLUMN_FIELD_PATHS returned nothing; every assertion below would pass vacuously"
    return found


@pytest.fixture(scope="module")
def live_table_descriptions(annotated) -> dict[str, str]:
    s = settings()
    client = bigquery.Client(project=s.project_id, location=s.location)
    sql = f"""
        SELECT table_name, option_value
        FROM `{s.project_id}.{s.dataset}.INFORMATION_SCHEMA.TABLE_OPTIONS`
        WHERE option_name = 'description'
    """
    # option_value is a SQL string literal — quotes included — not a plain
    # string. COLUMN_FIELD_PATHS.description is the opposite. Unquoting the
    # wrong one is the failure this comment exists to prevent.
    found = {
        f"{s.dataset}.{row['table_name']}": ast.literal_eval(row["option_value"])
        for row in client.query(sql).result()
    }
    assert found, "no table in the dataset carries a description; the assertions below would pass vacuously"
    return found


def test_every_agent_table_carries_a_table_description(live_table_descriptions):
    missing = sorted(agent_tables() - set(live_table_descriptions))
    assert not missing, f"tables with no description in BigQuery: {missing}"


def test_table_descriptions_match_the_yaml(live_table_descriptions):
    semantics = load_semantics()
    assert semantics, "the YAML is empty; this test would pass vacuously"
    for table, entry in semantics.items():
        assert live_table_descriptions[table] == entry.description, (
            f"{table}: BigQuery and the YAML disagree. The console would show "
            f"{live_table_descriptions[table]!r} while the agent is told "
            f"{entry.description!r}"
        )


def test_every_agent_column_carries_a_description(live_column_descriptions):
    semantics = load_semantics()
    described = {
        (table, column)
        for table, entry in semantics.items()
        for column in entry.columns
    }
    assert len(described) == 141, (
        f"the YAML describes {len(described)} columns, not the 141 of the "
        "agent-referenced surface"
    )
    for table, column in sorted(described):
        live = live_column_descriptions.get((table, column))
        assert live, f"{table}.{column} has no description in BigQuery"


def test_column_descriptions_match_the_yaml(live_column_descriptions):
    semantics = load_semantics()
    assert semantics, "the YAML is empty; this test would pass vacuously"
    for table, entry in semantics.items():
        for column, text in entry.columns.items():
            assert live_column_descriptions[(table, column)] == text, (
                f"{table}.{column}: BigQuery and the YAML disagree"
            )


def test_applying_twice_changes_nothing_the_second_time(annotated):
    """An annotator that rewrites unconditionally cannot be run safely from CI,
    and its output tells you nothing about whether anything drifted."""
    assert apply(dry_run=False) == [], (
        "a second apply reported changes; the annotator is not idempotent"
    )


def test_dry_run_reports_without_writing():
    """A dry run on an already-annotated dataset must find nothing to do."""
    assert apply(dry_run=True) == []


def test_backup_tables_are_untouched(live_table_descriptions):
    backups = [t for t in live_table_descriptions if t.endswith("_original_20260810")]
    assert not backups, (
        f"the annotator wrote to backup snapshots: {backups}. Backups are "
        "explicitly out of scope."
    )
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd . && \
  python3 -m pytest \
  tests/context/test_annotate.py -v
```

Expected: collection error, `ModuleNotFoundError: No module named 'scripts.annotate_bigquery'`.

- [ ] **Step 3: Write the annotator**

Create `scripts/annotate_bigquery.py`:

```python
"""Write docs/column-semantics.yaml into BigQuery as real table and column
descriptions.

The point of writing them into BigQuery rather than rendering the YAML straight
into the prompt is that the BigQuery console may be opened live, mid-demo. What
the agent is told and what the console shows have to be the same fact rendered
twice, and generating one FROM the other is what makes divergence structurally
impossible rather than a matter of discipline.

Uses the client API rather than ALTER TABLE ... SET OPTIONS because the
descriptions are arbitrary prose and hand-quoting prose into a SQL literal is a
correctness problem with no upside. Reads nothing back — the round-trip check
lives in tests/context/test_annotate.py and deliberately uses a different path.

Run:  python -m scripts.annotate_bigquery --dry-run
      python -m scripts.annotate_bigquery --write
"""
from __future__ import annotations

import argparse

from google.cloud import bigquery

from mining_agents.config import settings
from scripts.semantics import TableSemantics, load_semantics


def _redescribed(field: bigquery.SchemaField, text: str) -> bigquery.SchemaField:
    """Copy a schema field with a new description, preserving everything else.

    Goes through the API representation rather than reconstructing the field
    from its properties, so that nested fields, modes and policy tags survive a
    description change untouched.
    """
    api = field.to_api_repr()
    api["description"] = text
    return bigquery.SchemaField.from_api_repr(api)


def _pending(table: bigquery.Table, entry: TableSemantics) -> tuple[bool, list[str]]:
    """What would change for this table: (table description, column names)."""
    table_changes = table.description != entry.description
    column_changes = [
        field.name
        for field in table.schema
        if field.name in entry.columns
        and field.description != entry.columns[field.name]
    ]
    return table_changes, column_changes


def apply(dry_run: bool = True) -> list[str]:
    """Push the YAML into BigQuery. Returns the qualified names changed.

    Idempotent: a table whose description and columns already match is skipped
    entirely, so a second run returns an empty list. That emptiness is the
    signal — it is what lets this be run from CI to detect drift rather than
    only to repair it.
    """
    s = settings()
    client = bigquery.Client(project=s.project_id, location=s.location)
    semantics = load_semantics()

    changed: list[str] = []
    for qualified, entry in sorted(semantics.items()):
        dataset, table_name = qualified.split(".", 1)
        if dataset != s.dataset:
            raise ValueError(
                f"{qualified} is not in {s.dataset}; this script annotates one "
                "dataset and would otherwise write somewhere unreviewed"
            )
        if table_name.endswith("_original_20260810"):
            raise ValueError(
                f"{qualified} is a backup snapshot and is out of scope; it "
                "should not be in the YAML at all"
            )

        table = client.get_table(f"{s.project_id}.{dataset}.{table_name}")
        table_changes, column_changes = _pending(table, entry)
        if not table_changes and not column_changes:
            continue

        if dry_run:
            print(f"{qualified}:")
            if table_changes:
                print(f"  table description: {table.description!r} -> {entry.description!r}")
            for name in column_changes:
                current = next(f for f in table.schema if f.name == name).description
                print(f"  {name}: {current!r} -> {entry.columns[name]!r}")
            changed.append(qualified)
            continue

        table.description = entry.description
        table.schema = [
            _redescribed(field, entry.columns[field.name])
            if field.name in entry.columns
            else field
            for field in table.schema
        ]
        client.update_table(table, ["description", "schema"])
        changed.append(qualified)

    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true",
                       help="print what would change and write nothing")
    group.add_argument("--write", action="store_true",
                       help="write the descriptions into BigQuery")
    args = parser.parse_args()

    changed = apply(dry_run=args.dry_run)
    verb = "would change" if args.dry_run else "changed"
    print(f"{verb} {len(changed)} tables" + (f": {changed}" if changed else ""))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Dry-run it before writing anything**

```bash
cd . && \
  python3 -m scripts.annotate_bigquery --dry-run
```

Expected: a per-table diff, ending in `would change 25 tables`. Read the diff.
Seven columns will show a non-`None` current value — the four on
`incident_involvements`, plus `operator_vehicle_assignments` and `rfp_items`
handled in Task 3. Every other current value is `None`.

- [ ] **Step 5: Write, then re-dry-run to confirm idempotence**

```bash
cd . && \
  python3 -m scripts.annotate_bigquery --write && \
  python3 -m scripts.annotate_bigquery --dry-run
```

Expected: `changed 25 tables: [...]` then `would change 0 tables`.

- [ ] **Step 6: Run the tests to verify they pass**

```bash
cd . && \
  python3 -m pytest \
  tests/context/ -v
```

Expected: all PASS, including `test_every_agent_column_carries_a_description`
asserting exactly 141 columns.

- [ ] **Step 7: Confirm the console story by hand**

```bash
cd . && \
python3 - <<'EOF'
from google.cloud import bigquery
from mining_agents.config import settings
s = settings()
client = bigquery.Client(project=s.project_id, location=s.location)
table = client.get_table(f"{s.project_id}.{s.dataset}.telemetry_stream")
print(table.description)
for field in table.schema:
    print(f"  {field.name:<16} {field.description}")
EOF
```

This is what the client sees if they open the table mid-demo. Read it as they
would. If it reads as machine output rather than as something a person wrote,
that is a defect to report, not to ship.

- [ ] **Step 8: Commit**

```bash
cd . && \
  git add scripts/annotate_bigquery.py tests/context/test_annotate.py && \
  git commit -m "feat(context): write column semantics into BigQuery

The console may be opened live mid-demo, so what the agent is told and what
the console shows must be one fact rendered twice. The round-trip test reads
back through INFORMATION_SCHEMA rather than through the write path."
```

---

### Task 7: Build the committed context snapshot

**Files:**
- Create: `mining_agents/context/__init__.py`
- Create: `mining_agents/context/models.py`
- Create: `mining_agents/context/snapshot.json`
- Create: `scripts/build_context.py`
- Create: `tests/context/test_build_context.py`

**Interfaces:**
- Consumes: the descriptions Task 6 wrote into BigQuery; `scripts.semantics.agent_tables()` and `load_semantics()` from Task 1.
- Produces:
  - `mining_agents.context.models.ColumnFact` — fields `name: str`, `type: str`, `description: str`, `distinct_values: list[str] | None`.
  - `mining_agents.context.models.TableFact` — fields `description: str`, `row_count: int`, `time_column: str | None`, `coverage_start: str | None`, `coverage_end: str | None`, `columns: list[ColumnFact]`.
  - `mining_agents.context.models.Snapshot` — fields `generated_at: str`, `project_id: str`, `dataset: str`, `site_clock: str`, `tables: dict[str, TableFact]`.
  - `mining_agents.context.models.load_snapshot(path: pathlib.Path | None = None) -> Snapshot`, cached.
  - `mining_agents.context.models.SNAPSHOT_PATH: pathlib.Path`.
  - `scripts.build_context.build() -> Snapshot`, `scripts.build_context.site_clock(tables: dict[str, TableFact]) -> str`, `scripts.build_context.serialise(snapshot: Snapshot) -> str`, `scripts.build_context.CLOCK_EXCLUDED: frozenset[str]`, `scripts.build_context.MAX_DISTINCT_VALUES: int`.

  Task 8 renders from `Snapshot`, `TableFact` and `ColumnFact` and calls `load_snapshot()`.

**Why the snapshot lives under `mining_agents/`.** See the Global Constraints
deviation note. `scripts/packages.py` copies only `mining_agents/` and
`references/` into each deploy package, so a snapshot under `data/` would not
reach the container.

**Why `models.py` may not import yaml or the BigQuery client.** It is imported
at agent build time inside all 52 containers. Standard library and pydantic
only. The builder that needs BigQuery lives in `scripts/`.

- [ ] **Step 1: Write the failing test**

Create `tests/context/test_build_context.py`:

```python
"""The snapshot is baked context: it is right until BigQuery moves underneath
it and then it is confidently wrong. These tests cover the two things that
matter — that a rebuild reproduces the committed file, and that the site clock
is derived from operational data rather than from tables the agents write."""
from __future__ import annotations

import json

import pytest

from mining_agents.context.models import SNAPSHOT_PATH, ColumnFact, TableFact, load_snapshot
from scripts.build_context import (
    CLOCK_EXCLUDED,
    MAX_DISTINCT_VALUES,
    build,
    serialise,
    site_clock,
)
from scripts.semantics import agent_tables


def _table(coverage_end: str | None, time_column: str | None = "timestamp") -> TableFact:
    return TableFact(
        description="a table used only to exercise clock derivation" ,
        row_count=1,
        time_column=time_column,
        coverage_start=coverage_end,
        coverage_end=coverage_end,
        columns=[ColumnFact(name="timestamp", type="TIMESTAMP",
                            description="when the row was observed")],
    )


def test_clock_excludes_the_tables_the_agents_write_themselves():
    """agent_approvals and agent_run_log are written by the agents at run time.
    Include them and the clock reads 'now', which silently restores the exact
    behaviour this whole change exists to remove."""
    assert CLOCK_EXCLUDED, "the exclusion set is empty; this test would pass vacuously"
    tables = {"mining_data.telemetry_stream": _table("2026-06-16T22:00:00+00:00")}
    for excluded in CLOCK_EXCLUDED:
        tables[excluded] = _table("2026-08-12T09:00:00+00:00")
    assert site_clock(tables) == "2026-06-16T22:00:00+00:00"


def test_clock_ignores_tables_with_no_time_column():
    tables = {
        "mining_data.telemetry_stream": _table("2026-06-16T22:00:00+00:00"),
        "mining_data.operators_node": _table(None, time_column=None),
    }
    assert site_clock(tables) == "2026-06-16T22:00:00+00:00"


def test_clock_refuses_to_invent_one_when_nothing_is_datable():
    with pytest.raises(ValueError):
        site_clock({"mining_data.operators_node": _table(None, time_column=None)})


def test_committed_snapshot_covers_the_whole_agent_surface():
    snapshot = load_snapshot()
    assert set(snapshot.tables) == agent_tables(), (
        "the snapshot and the catalog disagree about which tables exist. "
        f"Only in snapshot: {sorted(set(snapshot.tables) - agent_tables())}. "
        f"Only in catalog: {sorted(agent_tables() - set(snapshot.tables))}"
    )
    total_columns = sum(len(t.columns) for t in snapshot.tables.values())
    assert total_columns == 141, f"snapshot carries {total_columns} columns, not 141"


def test_every_snapshot_column_carries_a_description():
    snapshot = load_snapshot()
    assert snapshot.tables, "empty snapshot; this test would pass vacuously"
    for name, table in snapshot.tables.items():
        assert table.description.strip(), f"{name} has no table description"
        assert table.columns, f"{name} has no columns"
        for column in table.columns:
            assert column.description.strip(), f"{name}.{column.name} has no description"


def test_distinct_value_sets_are_bounded():
    snapshot = load_snapshot()
    enumerated = [
        (name, c.name, len(c.distinct_values))
        for name, table in snapshot.tables.items()
        for c in table.columns
        if c.distinct_values is not None
    ]
    assert enumerated, (
        "no column in the snapshot enumerates its values. metric_name alone has "
        "twelve, so something is wrong with the profiler"
    )
    for table_name, column_name, count in enumerated:
        assert 0 < count <= MAX_DISTINCT_VALUES, (
            f"{table_name}.{column_name} enumerates {count} values"
        )


def test_biometric_values_are_never_enumerated():
    """A distinct-value list is a fine thing for a status column and a bad thing
    for a heart rate. Enumerating one would put raw biometric readings into
    every prompt of every agent that reads the table."""
    from mining_agents.safety.output_filter import BIOMETRIC_FIELDS

    snapshot = load_snapshot()
    for name, table in snapshot.tables.items():
        for column in table.columns:
            if column.name in BIOMETRIC_FIELDS:
                assert column.distinct_values is None, (
                    f"{name}.{column.name} enumerates raw biometric readings"
                )


def test_site_clock_is_the_latest_operational_instant():
    snapshot = load_snapshot()
    expected = max(
        table.coverage_end
        for name, table in snapshot.tables.items()
        if table.coverage_end and name not in CLOCK_EXCLUDED
    )
    assert snapshot.site_clock == expected


def test_rebuilding_reproduces_the_committed_file():
    """This is the drift gate. If BigQuery has moved, this fails and the
    snapshot gets rebuilt and reviewed — rather than the agents being told
    something that stopped being true."""
    committed = json.loads(SNAPSHOT_PATH.read_text())
    rebuilt = json.loads(serialise(build()))
    committed.pop("generated_at")
    rebuilt.pop("generated_at")
    assert rebuilt == committed, (
        "the snapshot no longer matches BigQuery. Run "
        "`python -m scripts.build_context --write`, read the diff, and commit it."
    )
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd . && \
  python3 -m pytest \
  tests/context/test_build_context.py -v
```

Expected: collection error, `ModuleNotFoundError: No module named 'mining_agents.context'`.

- [ ] **Step 3: Write the runtime models**

Create `mining_agents/context/__init__.py` as an empty file. Create
`mining_agents/context/models.py`:

```python
"""The shape of the baked context, and how an agent loads it.

Imported at agent build time inside all 52 containers, so this module uses the
standard library and pydantic only — no BigQuery client, no YAML. Everything
that needs those lives in scripts/, which does not travel.
"""
from __future__ import annotations

import functools
import pathlib

from pydantic import BaseModel

SNAPSHOT_PATH = pathlib.Path(__file__).resolve().parent / "snapshot.json"


class ColumnFact(BaseModel):
    name: str
    type: str
    description: str
    # Present only where the column has few enough distinct values to be worth
    # listing. Its absence is not "unknown" — it means "too many to enumerate",
    # which is itself a useful thing for an agent to know.
    distinct_values: list[str] | None = None


class TableFact(BaseModel):
    description: str
    row_count: int
    time_column: str | None = None
    coverage_start: str | None = None
    coverage_end: str | None = None
    columns: list[ColumnFact]


class Snapshot(BaseModel):
    generated_at: str
    project_id: str
    dataset: str
    site_clock: str
    tables: dict[str, TableFact]


@functools.lru_cache(maxsize=None)
def load_snapshot(path: pathlib.Path | None = None) -> Snapshot:
    """Read and parse the snapshot. Cached: build_all() calls this 100 times."""
    return Snapshot.model_validate_json((path or SNAPSHOT_PATH).read_text())
```

- [ ] **Step 4: Write the builder**

Create `scripts/build_context.py`:

```python
"""Read BigQuery back and write the snapshot the agents are given.

Reading BACK is the point. Rendering the YAML straight into the prompt would be
simpler and would pass silently if the annotation step had never run. Going
through BigQuery is what proves the console and the prompt agree.

Run:  python -m scripts.build_context --check
      python -m scripts.build_context --write
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys

from google.cloud import bigquery

from mining_agents.config import settings
from mining_agents.context.models import (
    SNAPSHOT_PATH,
    ColumnFact,
    Snapshot,
    TableFact,
)
from mining_agents.safety.output_filter import BIOMETRIC_FIELDS
from scripts.semantics import agent_tables, load_semantics

# Written by the agents themselves at run time, via request_approval and the
# run log. Including them would pull the site clock to the present and tell
# every agent that today's date is a date for which no operational data exists
# — the exact failure this snapshot is built to prevent.
CLOCK_EXCLUDED = frozenset({
    "mining_data.agent_approvals",
    "mining_data.agent_run_log",
})

# Above this, a value list stops being orientation and starts being a data
# dump that crowds out the instruction around it.
MAX_DISTINCT_VALUES = 25

# Types worth enumerating. A FLOAT64 with few distinct values is a coincidence,
# not a category, and a TIMESTAMP list is just the coverage range spelled out.
_ENUMERABLE = frozenset({"STRING", "BOOLEAN", "INTEGER"})
_TEMPORAL = frozenset({"TIMESTAMP", "DATETIME", "DATE"})

# The clock is an OBSERVATION time, so it comes only from TIMESTAMP/DATETIME
# columns. A DATE column such as assets.installation_date records an attribute
# of a thing, not a moment something was measured, and would move the clock for
# a reason that has nothing to do with data freshness.
_CLOCK_TYPES = frozenset({"TIMESTAMP", "DATETIME"})

_SQL_TYPE = {
    "INTEGER": "INT64",
    "FLOAT": "FLOAT64",
    "BOOLEAN": "BOOL",
    "RECORD": "STRUCT",
}


def _sql_type(field: bigquery.SchemaField) -> str:
    """The name a reader of GoogleSQL would recognise, not the legacy name."""
    base = _SQL_TYPE.get(field.field_type, field.field_type)
    return f"ARRAY<{base}>" if field.mode == "REPEATED" else base


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None


def site_clock(tables: dict[str, TableFact]) -> str:
    """The latest instant for which operational data exists.

    Raises rather than falling back to the wall clock. A wrong clock here is
    worse than no clock: it produces an agent that confidently reports "no
    anomalies" when it means "no data".
    """
    candidates = [
        table.coverage_end
        for name, table in tables.items()
        if table.coverage_end is not None and name not in CLOCK_EXCLUDED
    ]
    if not candidates:
        raise ValueError(
            "no operational table carries a time range, so there is no site "
            "clock to state. Refusing to fall back to the wall clock."
        )
    return max(candidates)


def _time_column(table: bigquery.Table, declared: str | None) -> str | None:
    """The table's single observation-time column, or None.

    Two temporal columns is an ambiguity, not a coin toss: the range the agent
    is shown would depend on which one this function happened to pick.
    """
    if declared is not None:
        return declared
    temporal = [
        f.name for f in table.schema
        if f.field_type in _TEMPORAL and f.mode != "REPEATED"
    ]
    if len(temporal) > 1:
        raise ValueError(
            f"{table.table_id} has more than one temporal column {temporal}; "
            "add `time_column: <name>` to its entry in "
            "docs/column-semantics.yaml so the choice is declared, not guessed"
        )
    return temporal[0] if temporal else None


def _profile(client: bigquery.Client, table: bigquery.Table,
             time_column: str | None,
             enumerable: list[str]) -> dict:
    """One query per table: row count, time coverage, and candidate value sets.

    The table name is interpolated because an identifier cannot be a query
    parameter. Every name reaching here came from agent_tables(), which is
    derived from the catalog — no caller-supplied string reaches this string
    format.
    """
    selects = ["COUNT(*) AS row_count"]
    if time_column:
        selects += [
            f"MIN(`{time_column}`) AS coverage_start",
            f"MAX(`{time_column}`) AS coverage_end",
        ]
    for name in enumerable:
        selects.append(
            f"ARRAY_AGG(DISTINCT CAST(`{name}` AS STRING) IGNORE NULLS "
            f"ORDER BY CAST(`{name}` AS STRING) "
            f"LIMIT {MAX_DISTINCT_VALUES + 1}) AS `d_{name}`"
        )
    sql = (
        "SELECT " + ", ".join(selects)
        + f" FROM `{table.project}.{table.dataset_id}.{table.table_id}`"
    )
    return dict(next(iter(client.query(sql).result())))


def build() -> Snapshot:
    s = settings()
    client = bigquery.Client(project=s.project_id, location=s.location)
    semantics = load_semantics()

    missing = sorted(agent_tables() - set(semantics))
    if missing:
        raise ValueError(
            f"{len(missing)} agent-referenced tables have no semantics: {missing}"
        )

    tables: dict[str, TableFact] = {}
    for qualified in sorted(agent_tables()):
        dataset, table_name = qualified.split(".", 1)
        table = client.get_table(f"{s.project_id}.{dataset}.{table_name}")

        if not table.description:
            raise ValueError(
                f"{qualified} has no description in BigQuery. Run "
                "`python -m scripts.annotate_bigquery --write` first."
            )

        time_column = _time_column(table, semantics[qualified].time_column)
        enumerable = [
            f.name for f in table.schema
            if f.field_type in _ENUMERABLE
            and f.mode != "REPEATED"
            and f.name not in BIOMETRIC_FIELDS
        ]
        profile = _profile(client, table, time_column, enumerable)

        columns: list[ColumnFact] = []
        for field in table.schema:
            if not field.description:
                raise ValueError(
                    f"{qualified}.{field.name} has no description in BigQuery. "
                    "Run `python -m scripts.annotate_bigquery --write` first."
                )
            values = profile.get(f"d_{field.name}")
            columns.append(ColumnFact(
                name=field.name,
                type=_sql_type(field),
                description=field.description,
                distinct_values=(
                    sorted(values)
                    if values is not None and len(values) <= MAX_DISTINCT_VALUES
                    else None
                ),
            ))

        tables[qualified] = TableFact(
            description=table.description,
            row_count=profile["row_count"],
            time_column=time_column,
            coverage_start=_iso(profile.get("coverage_start")),
            coverage_end=_iso(profile.get("coverage_end")),
            columns=columns,
        )

    return Snapshot(
        generated_at=datetime.datetime.now(datetime.UTC).isoformat(),
        project_id=s.project_id,
        dataset=s.dataset,
        site_clock=site_clock(tables),
        tables=tables,
    )


def serialise(snapshot: Snapshot) -> str:
    """Stable, diffable JSON. Sorted keys so a rebuild produces a clean diff."""
    return json.dumps(
        snapshot.model_dump(), indent=2, sort_keys=True, ensure_ascii=False
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true",
                       help="rebuild and overwrite the committed snapshot")
    group.add_argument("--check", action="store_true",
                       help="rebuild and exit non-zero if it differs")
    args = parser.parse_args()

    rebuilt = serialise(build())
    if args.write:
        SNAPSHOT_PATH.write_text(rebuilt)
        print(f"wrote {SNAPSHOT_PATH}")
        return

    # generated_at moves on every run by design; comparing it would make
    # --check always fail and therefore always be ignored.
    committed = json.loads(SNAPSHOT_PATH.read_text())
    current = json.loads(rebuilt)
    committed.pop("generated_at", None)
    current.pop("generated_at", None)
    if committed != current:
        print(
            "snapshot is stale: BigQuery no longer matches the committed file. "
            "Run `python -m scripts.build_context --write` and review the diff.",
            file=sys.stderr,
        )
        sys.exit(1)
    print("snapshot matches BigQuery")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Build the snapshot and read it**

```bash
cd . && \
  python3 -m scripts.build_context --write && \
  python3 -c "
from mining_agents.context.models import load_snapshot
s = load_snapshot()
print('site clock:', s.site_clock)
print('tables:', len(s.tables), 'columns:', sum(len(t.columns) for t in s.tables.values()))
t = s.tables['mining_data.telemetry_stream']
print(t.row_count, t.coverage_start, '->', t.coverage_end)
print([c.distinct_values for c in t.columns if c.name == 'metric_name'])
"
```

Expected: `tables: 25 columns: 141`; `telemetry_stream` shows 25,946 rows
covering `2026-01-01T00:00:00+00:00 -> 2026-06-16T22:00:00+00:00`; and
`metric_name` enumerates the twelve values `belt_tension_kn, engine_temp_c,
feed_rate_tph, load_pct, payload_tons, power_draw_mw, rotational_speed_rpm,
rotational_torque_nm, speed_kmh, speed_mps, temperature_c, vibration_hz`.

- [ ] **Step 6: Confirm `--check` is honest in both directions**

```bash
cd . && \
  python3 -m scripts.build_context --check && \
  echo "PASS: clean check exits 0"
```

Expected: `snapshot matches BigQuery`, then `PASS: clean check exits 0`.

Now prove it can fail. Edit `mining_agents/context/snapshot.json` by hand,
changing any `row_count` to `1`, re-run `--check`, and confirm it prints the
stale message and exits 1. Then restore the file with
`python -m scripts.build_context --write`. A drift check that has never been
seen to fail is not evidence of anything.

- [ ] **Step 7: Run the tests to verify they pass**

```bash
cd . && \
  python3 -m pytest tests/context/ -v
```

Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
cd . && \
  git add mining_agents/context/__init__.py mining_agents/context/models.py \
    mining_agents/context/snapshot.json scripts/build_context.py \
    tests/context/test_build_context.py && \
  git commit -m "feat(context): build the committed context snapshot from BigQuery

Reads structure, descriptions, row counts, coverage and low-cardinality value
sets back out of BigQuery. The site clock comes only from observation-time
columns and excludes the tables the agents write themselves — include those
and the clock reads 'now', restoring the behaviour this change removes."
```

---

### Task 8: Render the context into every agent's instruction

**Files:**
- Create: `mining_agents/context/render.py`
- Create: `tests/context/test_render.py`
- Modify: `mining_agents/patterns/deep.py:50-60`
- Modify: `tests/patterns/test_deep.py`

**Interfaces:**
- Consumes: `mining_agents.context.models.Snapshot`, `TableFact`, `ColumnFact`, `load_snapshot` from Task 7; `AgentDef.source_tables`.
- Produces: `mining_agents.context.render.render_data_scope(source_tables: Sequence[str], snapshot: Snapshot) -> str` and `mining_agents.context.render.render_site_clock(snapshot: Snapshot) -> str`. Task 9's swarm instructions build on the output of `build_instruction`, which now carries both.

**This is the task that reaches all 100 agents.** `build_instruction` in
`patterns/deep.py` is called by `build_deep_agent` for every Pattern B agent
and by `swarm.py` for all five nodes of every swarm — the three specialists
directly, and the critic and coordinator through `critic_instruction` and
`coordinator_instruction`. One edit, 100 agents.

**Rendering is pure.** `render_data_scope` and `render_site_clock` take a
loaded `Snapshot` and do no I/O. Only `build_instruction` calls
`load_snapshot()`, which is cached.

- [ ] **Step 1: Write the failing test**

Create `tests/context/test_render.py`:

```python
"""The rendered block is what an agent actually reads, so these tests are about
what is IN it and what is NOT.

The single most important case is the empty scope. An agent handed no tables is
a defect — it will answer from the model's own knowledge of mining and cite
nothing — so rendering must raise rather than emit a heading with nothing under
it, which reads like a legitimate instruction.
"""
from __future__ import annotations

import pytest

from mining_agents.context.models import ColumnFact, Snapshot, TableFact, load_snapshot
from mining_agents.context.render import render_data_scope, render_site_clock


@pytest.fixture
def snapshot() -> Snapshot:
    return Snapshot(
        generated_at="2026-08-12T00:00:00+00:00",
        project_id="test-project",
        dataset="mining_data",
        site_clock="2026-06-16T22:00:00+00:00",
        tables={
            "mining_data.telemetry_stream": TableFact(
                description="Continuous sensor readings from plant and mobile assets.",
                row_count=25946,
                time_column="timestamp",
                coverage_start="2026-01-01T00:00:00+00:00",
                coverage_end="2026-06-16T22:00:00+00:00",
                columns=[
                    ColumnFact(name="asset_id", type="STRING",
                               description="The asset this reading was taken from."),
                    ColumnFact(name="metric_name", type="STRING",
                               description="Which sensor channel this row reports.",
                               distinct_values=["engine_temp_c", "vibration_hz"]),
                ],
            ),
            "mining_data.operators_node": TableFact(
                description="One row per operator in the safety property graph.",
                row_count=48,
                time_column=None,
                coverage_start=None,
                coverage_end=None,
                columns=[
                    ColumnFact(name="operator_id", type="STRING",
                               description="Pseudonymous operator identifier."),
                ],
            ),
        },
    )


def test_renders_only_the_requested_tables(snapshot):
    rendered = render_data_scope(["mining_data.telemetry_stream"], snapshot)
    assert "mining_data.telemetry_stream" in rendered
    assert "mining_data.operators_node" not in rendered, (
        "an undeclared table leaked into the prompt; the agent would be told "
        "about data its bq_query tool will refuse to read"
    )


def test_carries_the_facts_that_would_otherwise_cost_a_round_trip(snapshot):
    rendered = render_data_scope(["mining_data.telemetry_stream"], snapshot)
    assert "25,946" in rendered, "row count missing"
    assert "2026-01-01" in rendered and "2026-06-16" in rendered, "coverage missing"
    assert "asset_id" in rendered and "STRING" in rendered, "schema missing"
    assert "Which sensor channel" in rendered, "column meaning missing"
    assert "engine_temp_c" in rendered and "vibration_hz" in rendered, (
        "distinct values missing — these are what a DISTINCT probe would cost"
    )


def test_a_table_with_no_time_column_renders_without_a_coverage_range(snapshot):
    rendered = render_data_scope(["mining_data.operators_node"], snapshot)
    assert "48 rows" in rendered
    assert "covering" not in rendered, (
        "a table with no time column must not claim a coverage range"
    )


def test_an_unknown_table_raises(snapshot):
    with pytest.raises(KeyError):
        render_data_scope(["mining_data.not_a_table"], snapshot)


def test_an_empty_scope_raises(snapshot):
    """Silently rendering an empty scope produces a heading with nothing under
    it, which reads to the model like a legitimate instruction to proceed."""
    with pytest.raises(ValueError):
        render_data_scope([], snapshot)


def test_site_clock_states_the_instant_and_what_to_do_with_it(snapshot):
    rendered = render_site_clock(snapshot)
    assert "2026-06-16 22:00 UTC" in rendered
    assert "last 24 hours" in rendered.lower()


def test_the_real_snapshot_renders_for_a_real_agent():
    """D01 declares exactly one table. Its rendered scope is the thing that has
    to make five orientation queries unnecessary."""
    from mining_agents.catalog.definitions import ALL_AGENTS

    d01 = next(a for a in ALL_AGENTS if a.agent_id == "D01")
    assert d01.source_tables == ["mining_data.telemetry_stream"], (
        f"D01 now declares {d01.source_tables}; this test was written against "
        "a single-table scope"
    )
    rendered = render_data_scope(d01.source_tables, load_snapshot())
    for value in ("vibration_hz", "engine_temp_c", "metric_value", "FLOAT64"):
        assert value in rendered, f"{value} missing from D01's rendered scope"
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd . && \
  python3 -m pytest \
  tests/context/test_render.py -v
```

Expected: collection error, `ModuleNotFoundError: No module named 'mining_agents.context.render'`.

- [ ] **Step 3: Write the renderer**

Create `mining_agents/context/render.py`:

```python
"""Turn the snapshot into the text an agent reads.

Pure functions over a loaded Snapshot — no I/O, no network, no caching. The one
caller that touches the filesystem is build_instruction, so these can be tested
against a hand-built snapshot with no BigQuery in the loop.
"""
from __future__ import annotations

import datetime
import textwrap
from typing import Sequence

from mining_agents.context.models import ColumnFact, Snapshot, TableFact

_INDENT = "      "
_NAME_WIDTH = 22
_TYPE_WIDTH = 14
_WIDTH = 96


def _readable(iso: str) -> str:
    """An instant a person can read. ISO-8601 in the snapshot, prose in the prompt."""
    value = datetime.datetime.fromisoformat(iso)
    if "T" not in iso:
        return value.strftime("%Y-%m-%d")
    return value.strftime("%Y-%m-%d %H:%M UTC")


def _column_lines(column: ColumnFact) -> list[str]:
    text = column.description
    if column.distinct_values:
        text = f"{text} One of: {', '.join(column.distinct_values)}."
    prefix = f"{_INDENT}{column.name:<{_NAME_WIDTH}}{column.type:<{_TYPE_WIDTH}}"
    hanging = " " * len(prefix)
    return textwrap.wrap(
        text, width=_WIDTH, initial_indent=prefix, subsequent_indent=hanging
    )


def _table_lines(name: str, table: TableFact) -> list[str]:
    lines = textwrap.wrap(
        f"{name} — {table.description}",
        width=_WIDTH, initial_indent="  ", subsequent_indent="  ",
    )
    counted = f"{table.row_count:,} rows"
    if table.coverage_start and table.coverage_end:
        counted += (
            f", covering {_readable(table.coverage_start)} to "
            f"{_readable(table.coverage_end)}"
        )
    lines.append(f"  {counted}.")
    for column in table.columns:
        lines += _column_lines(column)
    return lines


def render_data_scope(source_tables: Sequence[str], snapshot: Snapshot) -> str:
    """The tables this agent may read, with everything it would otherwise ask for.

    Raises on an unknown or empty scope rather than degrading. A heading with
    nothing under it reads to the model like a legitimate instruction, and an
    agent with no data to cite answers from the model's general knowledge of
    mining — which is the failure mode the citation mandate exists to prevent.
    """
    if not source_tables:
        raise ValueError(
            "an agent with no declared tables has nothing to cite and must not "
            "be built"
        )

    lines = ["DATA SCOPE — you may read only these objects:"]
    for name in source_tables:
        if name not in snapshot.tables:
            raise KeyError(
                f"{name} is declared by an agent but absent from the context "
                "snapshot. Run `python -m scripts.build_context --write`."
            )
        lines.append("")
        lines += _table_lines(name, snapshot.tables[name])
    return "\n".join(lines)


def render_site_clock(snapshot: Snapshot) -> str:
    """State the clock, and state what to do about it.

    Naming the instant is not enough on its own. Without the second sentence a
    model reads "data ends 2026-06-16" and still writes
    `WHERE timestamp > CURRENT_TIMESTAMP() - INTERVAL 24 HOUR`, gets zero rows,
    and reports no anomalies — which sounds like good news and is not.
    """
    instant = _readable(snapshot.site_clock)
    return "\n".join(textwrap.wrap(
        f"SITE CLOCK — operational data ends {instant}. Treat that instant as "
        f'"now". A request for "the last 24 hours" means the last 24 hours of '
        "available data, not of wall-clock time. Anchor every time filter to "
        "that instant, and say in your answer which window you used.",
        width=_WIDTH,
    ))
```

- [ ] **Step 4: Run the render tests to verify they pass**

```bash
cd . && \
  python3 -m pytest \
  tests/context/test_render.py -v
```

Expected: all PASS.

- [ ] **Step 5: Write the failing instruction test**

Append to `tests/patterns/test_deep.py`:

```python
def test_instruction_carries_the_data_scope_instead_of_a_bare_table_list():
    """The measured cause of D01's 48 seconds was five orientation queries
    against a prompt that named the table and nothing else."""
    from mining_agents.catalog.definitions import ALL_AGENTS

    d01 = next(a for a in ALL_AGENTS if a.agent_id == "D01")
    instruction = build_instruction(d01)

    assert "  - mining_data.telemetry_stream" not in instruction, (
        "the bare table list survived; the agent still has nothing but a name"
    )
    for value in ("rows", "covering", "metric_name", "vibration_hz", "FLOAT64"):
        assert value in instruction, f"{value} missing from D01's instruction"


def test_instruction_states_the_site_clock():
    from mining_agents.catalog.definitions import ALL_AGENTS
    from mining_agents.context.models import load_snapshot

    d01 = next(a for a in ALL_AGENTS if a.agent_id == "D01")
    instruction = build_instruction(d01)

    assert "SITE CLOCK" in instruction
    # Derived from the snapshot rather than written in, so this cannot pass by
    # agreeing with a stale hardcoded date.
    assert load_snapshot().site_clock[:10] in instruction


def test_every_agent_builds_an_instruction():
    """100 agents, every one of which must render. A table an agent declares but
    the snapshot lacks would fail here rather than in a container."""
    from mining_agents.catalog.definitions import ALL_AGENTS

    assert len(ALL_AGENTS) == 100, f"catalog holds {len(ALL_AGENTS)} agents, not 100"
    for agent in ALL_AGENTS:
        instruction = build_instruction(agent)
        assert "DATA SCOPE" in instruction and "SITE CLOCK" in instruction, (
            f"{agent.agent_id} rendered an incomplete instruction"
        )
```

- [ ] **Step 6: Run it to verify it fails**

```bash
cd . && \
  python3 -m pytest \
  tests/patterns/test_deep.py -v
```

Expected: the three new tests FAIL — the bare table list is still there and
`SITE CLOCK` does not appear.

- [ ] **Step 7: Wire the renderer into `build_instruction`**

In `mining_agents/patterns/deep.py`, add to the imports after the
`mining_agents.config` import:

```python
from mining_agents.context.models import load_snapshot
from mining_agents.context.render import render_data_scope, render_site_clock
```

Then replace lines 52-60, currently:

```python
    parts = [
        f"You are {agent.display_name} (agent {agent.agent_id}), a Pattern B "
        f"departmental analyst for a mining operation.",
        f"APQC process {agent.apqc_code}. Primary persona: {agent.persona}. "
        f"Value branch: {agent.value_branch}.",
        "",
        "DATA SCOPE — you may read only these objects:",
        *(f"  - {table}" for table in agent.source_tables),
    ]
```

with:

```python
    # The scope used to be a list of table names and nothing else, which cost
    # every agent five orientation round-trips per request — 55% of D01's
    # measured 48 seconds — and told it nothing about what the numbers meant.
    # load_snapshot() is cached, so building all 100 agents reads the file once.
    snapshot = load_snapshot()
    parts = [
        f"You are {agent.display_name} (agent {agent.agent_id}), a Pattern B "
        f"departmental analyst for a mining operation.",
        f"APQC process {agent.apqc_code}. Primary persona: {agent.persona}. "
        f"Value branch: {agent.value_branch}.",
        "",
        render_data_scope(agent.source_tables, snapshot),
        "",
        render_site_clock(snapshot),
    ]
```

Everything after that line — traversals, models, the citation mandate, tool
failure, computation, SQL, untrusted content, biometrics, HITL — is unchanged.

- [ ] **Step 8: Run the whole suite**

```bash
cd . && \
  python3 -m pytest -q
```

Expected: all PASS. Read any failure in `tests/patterns/` or `tests/safety/`
carefully — an existing test asserting on the old bare-list format is a test to
update, but an existing test about biometrics or untrusted content failing means
the wiring broke a safety clause and must be fixed, not amended.

- [ ] **Step 9: Read one instruction end to end**

```bash
cd . && \
  python3 -c "
from mining_agents.catalog.definitions import ALL_AGENTS
from mining_agents.patterns.deep import build_instruction
d01 = next(a for a in ALL_AGENTS if a.agent_id == 'D01')
print(build_instruction(d01))
"
```

Read it as the model will. Columns should line up, no line should exceed 96
characters, and every one of the five orientation queries listed in the spec
should now be answerable from the text alone.

- [ ] **Step 10: Commit**

```bash
cd . && \
  git add mining_agents/context/render.py tests/context/test_render.py \
    mining_agents/patterns/deep.py tests/patterns/test_deep.py && \
  git commit -m "feat(context): inject schema, meaning and the site clock into every agent

build_instruction is the single funnel all 100 agents route through, so this
one edit replaces the bare table list everywhere. Rendering raises on an empty
or unknown scope rather than emitting a heading with nothing under it."
```

---

### Task 9: Stop the critic and the coordinator re-exploring

**Files:**
- Modify: `mining_agents/patterns/swarm.py:59-112`
- Modify: `tests/patterns/test_swarm.py`

**Interfaces:**
- Consumes: `build_instruction` from Task 8, which both `critic_instruction` and `coordinator_instruction` already call as their first line.
- Produces: no new interface. `critic_instruction(swarm) -> str` and `coordinator_instruction(swarm) -> str` keep their signatures.

**Why this is a separate change from Task 8.** Task 8 gives all five swarm
nodes the injected context. That removes the *reason* to explore but not the
*habit*: a critic given a rich schema block can still spend three round-trips
re-deriving what a specialist already reported. S01 measured 191.6s across 76
events, and its five nodes each paid the orientation cost independently. The
stage ordering is not touched — the three specialists already fan out in
parallel (`swarm.py:158`), the critic must follow the `JoinNode` barrier, and
the coordinator must follow the critic. That sequence is the product.

- [ ] **Step 1: Write the failing test**

Append to `tests/patterns/test_swarm.py`:

```python
def test_critic_is_told_to_stop_surveying():
    from mining_agents.catalog.definitions import SWARMS
    from mining_agents.patterns.swarm import critic_instruction

    assert SWARMS, "no swarms in the catalog; this test would pass vacuously"
    for swarm in SWARMS:
        instruction = critic_instruction(swarm)
        assert "STAGE DISCIPLINE" in instruction, (
            f"{swarm.swarm_id}: critic has no stage instruction"
        )
        assert "DATA SCOPE" in instruction and "SITE CLOCK" in instruction, (
            f"{swarm.swarm_id}: critic lost the injected context"
        )


def test_coordinator_is_told_to_conclude_rather_than_re_query():
    from mining_agents.catalog.definitions import SWARMS
    from mining_agents.patterns.swarm import coordinator_instruction

    assert SWARMS, "no swarms in the catalog; this test would pass vacuously"
    for swarm in SWARMS:
        instruction = coordinator_instruction(swarm)
        assert "STAGE DISCIPLINE" in instruction, (
            f"{swarm.swarm_id}: coordinator has no stage instruction"
        )
        assert "DATA SCOPE" in instruction and "SITE CLOCK" in instruction, (
            f"{swarm.swarm_id}: coordinator lost the injected context"
        )


def test_specialists_are_not_told_to_stop_exploring():
    """The specialists are the stage that is SUPPOSED to query. Giving them the
    critic's restraint would produce a swarm that reports nothing."""
    from mining_agents.catalog.definitions import SWARMS
    from mining_agents.patterns.deep import build_instruction

    for swarm in SWARMS:
        for specialist in swarm.specialists:
            assert "STAGE DISCIPLINE" not in build_instruction(specialist), (
                f"{specialist.agent_id} was given a synthesis-stage restriction"
            )


def test_the_dlp_audit_clause_survives():
    """A swarm reaching biometrics must still carry the mandatory DLP audit."""
    from mining_agents.catalog.definitions import SWARMS
    from mining_agents.patterns.deep import BIOMETRIC_TABLES
    from mining_agents.patterns.swarm import critic_instruction

    biometric_swarms = [
        s for s in SWARMS
        if {t for a in s.agents for t in a.source_tables} & BIOMETRIC_TABLES
    ]
    assert biometric_swarms, "no swarm reads a biometric table; this test would pass vacuously"
    for swarm in biometric_swarms:
        assert "DLP AUDIT" in critic_instruction(swarm), (
            f"{swarm.swarm_id}: DLP audit clause lost"
        )
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd . && \
  python3 -m pytest \
  tests/patterns/test_swarm.py -v
```

Expected: the two `STAGE DISCIPLINE` tests FAIL; the specialist and DLP tests PASS.

- [ ] **Step 3: Add the critic's stage instruction**

In `mining_agents/patterns/swarm.py`, inside `critic_instruction`, the parts
list currently begins:

```python
    parts = [
        build_instruction(swarm.critic),
        "",
        "YOU ARE THE CRITIC for swarm "
        f"{swarm.swarm_id} — {swarm.display_name}.",
        "You receive the outputs of all three specialists together, after they "
        "have all reported. Audit them; do not repeat their work.",
        "",
```

Insert the stage instruction immediately after that last blank string, before
the BLOCKED-specialist paragraph:

```python
        # The specialists are the stage that queries; the critic is the stage
        # that judges. Without this, a critic handed a rich schema block still
        # re-derives what a specialist already cited — which is where a large
        # share of S01's measured 191.6 seconds went.
        "STAGE DISCIPLINE — your DATA SCOPE above already carries the schema, "
        "the row counts, the coverage window and the meaning of every column, "
        "so there is nothing left to discover. Query only to verify a specific "
        "claim you intend to challenge, and name that claim when you do. Do "
        "not survey the schema, do not sample rows, and do not re-derive a "
        "figure a specialist has already cited.",
        "",
```

- [ ] **Step 4: Add the coordinator's stage instruction**

`coordinator_instruction` currently returns:

```python
    return "\n".join([
        build_instruction(swarm.coordinator),
        "",
        f"YOU COORDINATE swarm {swarm.swarm_id} — {swarm.display_name}.",
        "Your three specialists run in parallel. Wait for all three to report "
        "DONE or BLOCKED before you proceed. Then the critic audits their "
        "combined output. Only after the critic reports do you conclude.",
        "",
        "A BLOCKED specialist does not stop you. State what is unverified and "
        "what that means for your confidence.",
    ])
```

Add the stage instruction as the final element:

```python
    return "\n".join([
        build_instruction(swarm.coordinator),
        "",
        f"YOU COORDINATE swarm {swarm.swarm_id} — {swarm.display_name}.",
        "Your three specialists run in parallel. Wait for all three to report "
        "DONE or BLOCKED before you proceed. Then the critic audits their "
        "combined output. Only after the critic reports do you conclude.",
        "",
        "A BLOCKED specialist does not stop you. State what is unverified and "
        "what that means for your confidence.",
        "",
        "STAGE DISCIPLINE — you hold the critic's audit and the specialists' "
        "findings. Conclude from them; do not re-query. Anything you would go "
        "and look up has either already been reported to you, or is a gap in "
        "what the swarm established — and a gap is something to state, not "
        "something to fill in yourself.",
    ])
```

- [ ] **Step 5: Run the suite**

```bash
cd . && \
  python3 -m pytest -q
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
cd . && \
  git add mining_agents/patterns/swarm.py tests/patterns/test_swarm.py && \
  git commit -m "feat(context): give the critic and coordinator stage discipline

Injected context removes the reason to explore but not the habit. The critic
queries only to challenge a named claim; the coordinator concludes from what
it holds. Stage ordering is unchanged — specialists still fan out in parallel."
```

---

### Task 10: Redeploy and measure

**Files:**
- Create: `scripts/verify_context.py`
- Create: `docs/plans/2026-08-12-agent-context-results.md`

**Interfaces:**
- Consumes: the 52 deployed Cloud Run services; `scripts.packages.write_packages`; `scripts.deploy.deploy`.
- Produces: `scripts.verify_context.orientation_queries(sql_seen: list[str]) -> list[tuple[str, str]]` returning `(reason, sql)` pairs, and `scripts.verify_context.probe(agent_id: str, question: str) -> dict`.

**This task holds the acceptance gate.** Success criterion 1 and 2 from the
spec: `D01` and `S01` complete with **zero orientation queries**. Latency is
recorded but not gated — it drifts with model behaviour, the query count does
not.

**Two facts about the deployed surface that will cost an hour if missed.**

- The ADK api_server takes two calls: `POST /apps/<APP_ID>/users/<uid>/sessions/<sid>`
  to open a session, then `POST /run`. `app_name` is the **uppercase** agent id.
  Service URL is `https://mag-<agentid-lowercase>-cv6vy2fnnq-uc.a.run.app`.
- Event content part keys are **camelCase**: `functionCall`, `functionResponse`,
  `text`. An earlier probe in this project used `function_call` and silently
  reported every tool event as empty. The SQL is at
  `part["functionCall"]["args"]["sql"]`.
- Cloud Run needs an **OIDC identity token**, not an OAuth access token:
  `gcloud auth print-identity-token`. `curl` is denied by settings — use
  `urllib.request`.

- [ ] **Step 1: Write the verifier**

Create `scripts/verify_context.py`:

```python
"""Call a deployed agent and count the orientation queries in its response.

This is the acceptance gate for the context work. Latency is reported but not
asserted: it drifts with model behaviour and a wall-clock threshold would be
flaky. The number of round-trips the agent spends rediscovering its own schema
does not drift, and it is what the change is actually for.

Run:  python -m scripts.verify_context D01
      python -m scripts.verify_context S01 --question "..."
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.request

URL_TEMPLATE = "https://mag-{agent}-cv6vy2fnnq-uc.a.run.app"

DEFAULT_QUESTIONS = {
    "D01": "Which assets show abnormal telemetry in the last 24 hours?",
    "S01": "A critical pump has failed. Assess the cascading impact.",
}

# Each pattern is one of the five orientation queries measured against D01 on
# 2026-08-12. They are matched against whitespace-collapsed, lowercased SQL.
_SAMPLE = re.compile(r"^select \* from \S+( limit \d+)?$")
_DISTINCT_PROBE = re.compile(r"^select distinct [\w`.]+ from \S+$")
_TIME_PROBE = re.compile(
    r"^select (min|max)\([\w`.]+\)( as \w+)?"
    r"(, (min|max)\([\w`.]+\)( as \w+)?)* from \S+$"
)


def _normalise(sql: str) -> str:
    return " ".join(sql.split()).strip().rstrip(";").lower()


def orientation_queries(sql_seen: list[str]) -> list[tuple[str, str]]:
    """Which of these queries were the agent orienting itself rather than working."""
    found: list[tuple[str, str]] = []
    for sql in sql_seen:
        text = _normalise(sql)
        if "information_schema" in text:
            found.append(("schema survey", sql))
        elif _SAMPLE.match(text):
            found.append(("row sample", sql))
        elif _DISTINCT_PROBE.match(text):
            found.append(("distinct-value probe", sql))
        elif _TIME_PROBE.match(text):
            found.append(("coverage probe", sql))
    return found


def _token() -> str:
    return subprocess.run(
        ["gcloud", "auth", "print-identity-token"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def _post(url: str, token: str, payload: dict):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.loads(response.read().decode())


def probe(agent_id: str, question: str) -> dict:
    token = _token()
    base = URL_TEMPLATE.format(agent=agent_id.lower())
    session = f"v{int(time.time() * 1000)}"
    _post(f"{base}/apps/{agent_id}/users/verify/sessions/{session}", token, {})

    start = time.monotonic()
    events = _post(f"{base}/run", token, {
        "app_name": agent_id,
        "user_id": "verify",
        "session_id": session,
        "new_message": {"role": "user", "parts": [{"text": question}]},
    })
    wall = time.monotonic() - start

    sql_seen: list[str] = []
    tool_calls: list[str] = []
    for event in events:
        for part in event.get("content", {}).get("parts", []):
            # camelCase. An earlier probe used function_call and silently saw
            # nothing at all.
            call = part.get("functionCall")
            if not call:
                continue
            tool_calls.append(call.get("name", "?"))
            sql = (call.get("args") or {}).get("sql")
            if sql:
                sql_seen.append(sql)

    return {
        "agent_id": agent_id,
        "wall_seconds": round(wall, 1),
        "events": len(events),
        "authors": sorted({e.get("author", "?") for e in events}),
        "tool_calls": tool_calls,
        "sql": sql_seen,
        "orientation": orientation_queries(sql_seen),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("agent_id")
    parser.add_argument("--question", default=None)
    args = parser.parse_args()

    question = args.question or DEFAULT_QUESTIONS.get(args.agent_id)
    if question is None:
        parser.error(f"no default question for {args.agent_id}; pass --question")

    result = probe(args.agent_id, question)
    print(f"{result['agent_id']}: {result['wall_seconds']}s wall, "
          f"{result['events']} events, {len(result['tool_calls'])} tool calls")
    print(f"  authors: {result['authors']}")
    for sql in result["sql"]:
        print(f"  sql: {' '.join(sql.split())[:120]}")
    if result["orientation"]:
        print(f"\nFAIL: {len(result['orientation'])} orientation queries")
        for reason, sql in result["orientation"]:
            print(f"  [{reason}] {' '.join(sql.split())[:120]}")
        sys.exit(1)
    print("\nPASS: no orientation queries")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Prove the detector detects**

A detector that has only ever returned an empty list is not evidence.

```bash
cd . && \
python3 -c "
from scripts.verify_context import orientation_queries
five = [
  'SELECT column_name, data_type FROM mining_data.INFORMATION_SCHEMA.COLUMNS',
  'SELECT * FROM mining_data.telemetry_stream LIMIT 5',
  'SELECT MAX(timestamp) AS mx, MIN(timestamp) AS mn FROM mining_data.telemetry_stream',
  'SELECT DISTINCT metric_name FROM mining_data.telemetry_stream',
]
real = [
  'SELECT asset_id, AVG(metric_value) FROM mining_data.telemetry_stream '
  'WHERE metric_name = @m AND timestamp > @t GROUP BY asset_id',
]
print('orientation detected:', len(orientation_queries(five)), 'of 4')
print('false positives on real work:', len(orientation_queries(real)))
"
```

Expected: `orientation detected: 4 of 4`, `false positives on real work: 0`.

- [ ] **Step 3: Regenerate the deploy packages**

The snapshot lives under `mining_agents/`, so it travels with `SHARED_TREES`.
Confirm that rather than assuming it.

```bash
cd . && \
  python3 -m scripts.packages && \
  ls packages/D01/mining_agents/context/snapshot.json && \
  grep -c "pyyaml" packages/D01/requirements.txt
```

Expected: the snapshot path lists, and `grep -c` prints `0` — pyyaml must NOT
be in the container requirements.

- [ ] **Step 4: Redeploy all 52 entrypoints**

This builds 52 containers and takes a long time. Run it in the background.

```bash
cd . && \
  python3 -c "
from scripts.deploy import deploy
deploy(dry_run=False, confirm='yes-deploy-for-real')
"
```

Expected on completion: 52 deployed, 0 failed.

- [ ] **Step 5: Measure D01**

```bash
cd . && \
  python3 -m scripts.verify_context D01 && \
  python3 -m scripts.verify_context D01
```

Run twice: the first call lands on a cold container (measured at 4.6s of cold
start), the second on a warm one. Both must print `PASS: no orientation
queries`. The baseline to beat is 48.0s warm with 9 tool calls of which 5 were
orientation; the spec's target is under 25s.

If any orientation query appears, do not adjust the detector. Read the SQL,
work out what the agent still could not find in its instruction, and fix the
instruction — that is a real gap in the injected context.

- [ ] **Step 6: Measure S01**

```bash
cd . && \
  python3 -m scripts.verify_context S01
```

Expected: `PASS: no orientation queries`, five authors (`s01`, `s01_sp1`,
`s01_sp2`, `s01_sp3`, `s01_critic`). Baseline 191.6s over 76 events; the
spec's target is under 100s.

- [ ] **Step 7: Check the correctness criterion by hand**

Success criterion 3 is not a query count — it is whether the agent says which
window it used.

```bash
cd . && \
python3 -c "
from scripts.verify_context import probe
import json
r = probe('D01', 'Which assets show abnormal telemetry in the last 24 hours?')
print(json.dumps(r['sql'], indent=2))
"
```

Read the SQL the agent wrote. It must anchor its time filter to the site clock
rather than to `CURRENT_TIMESTAMP()`. An agent that queried the real last 24
hours, got zero rows and reported "no anomalies" is the failure this whole
change exists to prevent — if that happens, the site clock wording is not
strong enough and Task 8's `render_site_clock` needs another sentence.

- [ ] **Step 8: Record the results**

Create `docs/plans/2026-08-12-agent-context-results.md` with the
measured numbers, in this shape, filled in from what the runs actually printed:

```markdown
# Agent Context: measured results

**Date:** <date the runs were made>
**Method:** `python -m scripts.verify_context <agent>` against the deployed
Cloud Run services, after the redeploy in Task 10.

| | Before (2026-08-12) | After |
|---|---|---|
| D01 wall, warm | 48.0s | |
| D01 tool calls | 9 | |
| D01 orientation queries | 5 | |
| S01 wall | 191.6s | |
| S01 events | 76 | |
| S01 orientation queries | (not separately counted) | |

## The SQL D01 wrote

<the queries, verbatim>

## Whether it stated its window

<the answer, quoted>

## What did not improve, and why
```

Report what was measured, including anything that did not improve. A results
document that only records the wins is not a measurement.

- [ ] **Step 9: Commit**

```bash
cd . && \
  git add scripts/verify_context.py \
    docs/plans/2026-08-12-agent-context-results.md && \
  git commit -m "test(context): orientation-query gate and the measured results

The gate is the count of queries the agent spends rediscovering its schema,
not latency: latency drifts with model behaviour, the count does not."
```

---

## Self-Review

Run against the spec at `docs/specs/2026-08-12-agent-context-design.md`.

**Spec coverage.**

| Spec section | Task |
|---|---|
| §3.1 `docs/column-semantics.yaml` | 1–5 |
| §3.2 `scripts/annotate_bigquery.py`, idempotent, `--dry-run`, no backups | 6 |
| §3.3 `build_context.py`, structure, meaning, statistics, site clock, two-time-column raise | 7 |
| §3.4 `render_data_scope`, `render_site_clock`, wired into `build_instruction` | 8 |
| §3.5 swarm stage instructions, ordering unchanged | 9 |
| §4 discovery-query count gate | 10 |
| §4 snapshot drift `--check` | 7 |
| §4 annotation round-trip | 6 |
| §4 render unit tests, empty scope raises | 8 |
| §4 site clock excludes `agent_approvals` / `agent_run_log` | 7 |
| §4 latency measured not asserted | 10 |
| §5.1, §5.2 zero orientation queries on D01 and S01 | 10 |
| §5.3 agent states the window it used | 10 step 7 |
| §5.4 console shows descriptions | 6 step 7 |
| §5.5 all 141 columns and 25 tables described | 5 step 5, 6 step 6 |
| §5.6 CI fails on snapshot drift | 7 |
| §7 `rfp_items` open item | 3 step 2 |
| §7 unit conventions — say when a unit is not established | Global Constraints, and 3, 5 |

**Not carried into this plan, deliberately.** §6's out-of-scope list — the demo
application, adopting MCP, Knowledge Catalog AI descriptions, `min-instances`,
and modifying the dataset — has no task, which is correct.

**One gap the spec leaves and this plan closes:** the spec's §4 lists the
snapshot drift check as running "in CI", but this repo has no CI configuration.
Task 7 delivers `--check` as a command and a test; wiring it into a pipeline is
a separate piece of work and is not in this plan. Flag it rather than pretend.

**Two documented deviations**, both in Global Constraints with reasons: the
snapshot path (`mining_agents/context/snapshot.json`, not `data/`) and the
BigQuery write path (client API, not hand-built DDL).

**One spec error corrected by measurement:** §3.1's example says
`telemetry_stream` holds "one row per asset per metric per hour". It is every
**two** hours — 1,993 to 1,998 rows per asset-metric pair across a 4,006-hour
span, confirmed against the table on 2026-08-12. Task 1 carries the corrected
text and says why.

---
