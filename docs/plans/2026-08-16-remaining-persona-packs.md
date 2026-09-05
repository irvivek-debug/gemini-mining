# Method packs for P1, P2, P3 and P5 — Implementation Plan

> **For agentic workers:** implement this plan task-by-task, in order. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give four more personas a method pack, so each one's page opens with a
problem-solving question and answers it by working a driver tree instead of
returning a table.

**Architecture:** No new architecture. The P6 build is already general — there
are zero hardcoded references to P6 or S07-SP3 in the tools, instruction builder,
data build, router or packaging. A persona is added by writing
`method/<persona>.yaml` plus its diagnostic SQL, registering it in the `PACKS`
dict, and granting the holding agent the three method tools and the tables its
diagnostics read.

**Tech Stack:** Python 3.12, PyYAML, google-cloud-bigquery, pytest;
plain-JS front end tested with `node --test`.

**Spec:** `docs/specs/2026-08-16-remaining-persona-packs-design.md`

## Global Constraints

Every task's requirements implicitly include this section.

- **Commodity-neutral.** Never name a metal in a metric, driver question, guard,
  or any rendered copy. Say "contained metal". Warehouse column names such as
  `copper_grade_pct` are exempt — they are the warehouse's names, not ours.
- **Money as ranges.** Never quote a single point figure for a monetary
  magnitude in rendered copy; use a range or `[CLIENT INPUT REQUIRED]`.
- **A guard may not contain a verdict.** `tests/method/test_p6_pack.py::test_no_driver_decides_in_advance_what_its_own_diagnostic_will_show`
  forbids the substrings `too few`, `too many`, `unevidenced`, `no signal`,
  `insufficient` in any guard. A guard states what a measurement can and cannot
  establish — true before any row is read. It never states the finding.
- **`status` is instrumentation and nothing else.** `instrumented` requires
  `sql`; `not_instrumented` forbids both `sql` and `compare`. Enforced by
  `mining_agents/method/pack.py`.
- **SQL uses named parameters, never interpolation.** Enforced by
  `assert_no_interpolation` from `mining_agents.tools.bq_query`.
- **A diagnostic may only read tables its holding agent declares** in
  `source_tables`. `run_diagnostic` rejects the query at runtime otherwise.
- **`compare` may only be `setting_band`.** Comparing against outcome
  percentiles is refused by the schema — the pack compares against a band the
  site itself ran, not against its own best days.
- **Nothing is pushed to any remote.**

**Environment:**
- Python: `python3`
- Tests: `PYTHONPATH=. <python> -m pytest -q` (full suite ~6 min)
- JS tests: `node --test 'tests/js/*.test.js'` — **the quotes are required**;
  unquoted, the glob silently matches nothing and reports success.
- BigQuery: project `your-gcp-project-id`, dataset `mining_data`, US region.
  `bq query --use_legacy_sql=false --format=csv '...'` is authenticated.
- Branch: `feat/persona-method-packs`, already created off `main`.

**Reference implementation — read these before starting any task:**
- `method/p6-metallurgist.yaml` — pack shape and the voice of a guard
- `method/sql/p6/liberation.sql` — a banded comparison diagnostic
- `method/sql/p6/bypass.sql` — a count diagnostic
- `tests/method/test_p6_pack.py` — the testing bar. Note that it pins
  magnitudes, not signs: `[23, 116, 28]` day counts and a separation floor of
  3.0 points. A test that only checks ordering would pass on a query that
  dropped 100 days.

---

### Task 1: Author the site standards the guards will cite

**Why first:** a guard written before the document it cites is grounded in
nothing. P2, P3 and P5 have no usable documents in the corpus — P3 has no safety
document at all — so their standards must exist and be retrievable before their
packs are written.

**Files:**
- Create: `method/sop/fatigue-management-standard.md`
- Create: `method/sop/work-order-prioritisation-standard.md`
- Create: `method/sop/grade-reconciliation-standard.md`
- Modify: `scripts/build_doc_chunks.py`
- Test: `tests/scripts/test_build_doc_chunks.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: rows in `mining_data.doc_chunks` and
  `mining_data.doc_chunks_embedded` carrying `folder = "site-standards"`, which
  `doc_search` retrieves. Later tasks write `doc_query` strings that must hit
  these documents.

- [ ] **Step 1: Write the failing test**

Create `tests/scripts/test_build_doc_chunks.py`:

```python
"""The authored site standards must reach the corpus.

The PDF corpus has no safety document, no maintenance policy and nothing on
reconciliation practice, so three guards would otherwise cite documents that do
not exist. These are authored as markdown in the repository rather than as PDFs
in the bucket, so that a reviewer can read them in a diff.
"""
from pathlib import Path

from scripts.build_doc_chunks import SOP_DIR, sop_rows

ROOT = Path(__file__).resolve().parents[2]


def test_every_authored_standard_is_picked_up():
    names = {r["file_name"] for r in sop_rows()}
    assert names == {
        "fatigue-management-standard.md",
        "work-order-prioritisation-standard.md",
        "grade-reconciliation-standard.md",
    }


def test_the_standards_are_filed_under_their_own_folder():
    # Not 'oem-equipment-manuals': a document this repository wrote must not be
    # indistinguishable from one the site supplied.
    assert {r["folder"] for r in sop_rows()} == {"site-standards"}


def test_each_standard_carries_a_retrievable_threshold():
    # A standard with no number in it cannot fence a recommendation.
    for row in sop_rows():
        assert any(ch.isdigit() for ch in row["chunk_text"]), row["file_name"]


def test_chunk_indexes_are_contiguous_per_file():
    by_file: dict[str, list[int]] = {}
    for row in sop_rows():
        by_file.setdefault(row["file_name"], []).append(row["chunk_index"])
    for name, idx in by_file.items():
        assert sorted(idx) == list(range(len(idx))), name


def test_the_sop_directory_is_where_the_standards_live():
    assert SOP_DIR == ROOT / "method" / "sop"
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `PYTHONPATH=. python3 -m pytest tests/scripts/test_build_doc_chunks.py -q`
Expected: FAIL — `ImportError: cannot import name 'SOP_DIR'`

- [ ] **Step 3: Write the three standards**

Each must read as a site document — a standard with clauses and numbers — not as
a restatement of the pack. Each needs at least one retrievable threshold, because
a guard's job is to fence a recommendation against a documented limit.

`method/sop/fatigue-management-standard.md`: covers the biometric alert
threshold, the sleep-deficit level at which a stand-down is required, the
microsleep count that triggers immediate removal from task, and who authorises
return to work. Must state that a biometric alert is an exposure indicator and
not, on its own, evidence of an incident cause.

`method/sop/work-order-prioritisation-standard.md`: covers the priority
definitions, the age at which an open work order must be reviewed for escalation,
the lead-time threshold above which a part must be ordered before the work is
scheduled, and the rule that a priority may not be raised to obtain parts.

`method/sop/grade-reconciliation-standard.md`: covers the acceptable variance
tolerance between modelled and assayed grade, the minimum paired-sample count
below which a reconciliation is reported as indicative only, the search radius
convention for pairing a sample to a block, and the requirement to report
variance by domain rather than in aggregate.

Write them in the repository's voice: plain, specific, and free of the verdict
words listed in Global Constraints.

- [ ] **Step 4: Extend the chunker**

In `scripts/build_doc_chunks.py`, add alongside the existing GCS extraction:

```python
SOP_DIR = Path(__file__).resolve().parents[1] / "method" / "sop"
SOP_FOLDER = "site-standards"


def sop_rows() -> list[dict]:
    """Chunk the standards this repository authored.

    They are markdown in the repository rather than PDFs in the bucket so that
    a reviewer can read them in a diff, and they are filed under their own
    folder so that a document we wrote is never mistaken for one the site
    supplied.
    """
    out: list[dict] = []
    for path in sorted(SOP_DIR.glob("*.md")):
        for index, chunk in enumerate(chunk_text(path.read_text())):
            out.append({
                "doc_id": f"repo://method/sop/{path.name}",
                "folder": SOP_FOLDER,
                "file_name": path.name,
                "chunk_index": index,
                "chunk_text": chunk,
            })
    return out
```

Add `from pathlib import Path` if absent, and include `sop_rows()` in whatever
the module already loads to BigQuery, so one run loads both sources.

- [ ] **Step 5: Run the test to verify it passes**

Run: `PYTHONPATH=. python3 -m pytest tests/scripts/test_build_doc_chunks.py -q`
Expected: PASS, 5 tests

- [ ] **Step 6: Load and embed**

Run the chunk build, then the embedding build:
`PYTHONPATH=. <python> -m scripts.build_doc_chunks`
`PYTHONPATH=. <python> -m scripts.build_doc_embeddings`

Verify the standards are retrievable:
```bash
bq query --use_legacy_sql=false --format=csv \
 'SELECT folder, COUNT(*) FROM `your-gcp-project-id.mining_data.doc_chunks_embedded` GROUP BY folder'
```
Expected: a `site-standards` row with a non-zero count, and the six original
folders unchanged.

- [ ] **Step 7: Commit**

```bash
git add method/sop scripts/build_doc_chunks.py tests/scripts/test_build_doc_chunks.py
git commit -m "feat: author the site standards P2, P3 and P5 guards must cite"
```

---

### Task 2: The P5 pack — contained-metal variance

**Why first among the packs:** P5 has the strongest data in the repository after
P6. The desurvey join is verified — 142 paired samples inside a 25 m box, 279 of
295 within 100 m — and the model under-calls delivered grade by roughly a
quarter, which is a real finding for an agent to diagnose four ways.

**Files:**
- Create: `method/p5-geologist.yaml`
- Create: `method/sql/p5/model_bias.sql`, `bias_by_lithology.sql`,
  `bias_by_depth.sql`, `bias_by_elevation.sql`, `feed_grade_vs_model.sql`
- Modify: `mining_agents/tools/method_lookup.py` (the `PACKS` dict)
- Modify: `mining_agents/catalog/definitions.py` (agent `S06-SP1`)
- Test: `tests/method/test_p5_pack.py`

**Interfaces:**
- Consumes: `load_pack` from `mining_agents.method.pack`; `run_query` and
  `assert_no_interpolation` from `mining_agents.tools.bq_query`; the
  `site-standards` corpus rows from Task 1.
- Produces: `PACKS["P5"] = "p5-geologist.yaml"`, which Task 6 reads to carry the
  metric into `personas.json`.

- [ ] **Step 1: Grant the holder its tools and tables**

In `mining_agents/catalog/definitions.py`, find agent `S06-SP1` ("Assay-to-Block
Variance Analyst"). It currently declares
`tools = ["bq_query"]` and
`source_tables = ["mining_data.drill_assay_logs", "mining_data.geological_block_models"]`.

Change to:
```python
tools=["bq_query", "method_lookup", "run_diagnostic", "doc_search"],
source_tables=[
    "mining_data.drill_assay_logs",
    "mining_data.geological_block_models",
    "mining_data.drill_holes",
    "mining_data.metallurgical_recovery",
],
```
`drill_holes` carries the collar position, dip and azimuth the desurvey needs;
`metallurgical_recovery` carries delivered feed grade for the fifth driver.
Without both, `run_diagnostic` rejects those queries at runtime.

- [ ] **Step 2: Write the failing pack test**

Create `tests/method/test_p5_pack.py`, modelled on `test_p6_pack.py`:

```python
"""The shipped P5 pack, checked for structure and against the live data."""
from pathlib import Path

import pytest

from mining_agents.method.pack import load_pack
from mining_agents.tools.bq_query import assert_no_interpolation, run_query

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "method" / "p5-geologist.yaml"
TABLES = [
    "mining_data.drill_assay_logs",
    "mining_data.geological_block_models",
    "mining_data.drill_holes",
    "mining_data.metallurgical_recovery",
]


def test_the_shipped_pack_loads():
    pack = load_pack(PACK)
    assert pack.metric == "contained-metal variance between the block model and realised grade"
    assert {d.id for d in pack.drivers} == {
        "model_bias", "bias_by_lithology", "bias_by_depth",
        "bias_by_elevation", "feed_grade_vs_model",
        "tonnage_reconciliation", "qaqc_bias",
    }


def test_every_named_sql_file_exists():
    for driver in load_pack(PACK).drivers:
        if driver.sql:
            assert (ROOT / "method" / driver.sql).is_file(), driver.sql


def test_every_diagnostic_uses_parameters_not_literals():
    for driver in load_pack(PACK).drivers:
        if driver.sql:
            assert_no_interpolation((ROOT / "method" / driver.sql).read_text())


def test_the_uninstrumented_drivers_are_declared_not_omitted():
    statuses = {d.id: d.status for d in load_pack(PACK).drivers}
    assert statuses["tonnage_reconciliation"] == "not_instrumented"
    assert statuses["qaqc_bias"] == "not_instrumented"


def test_no_driver_decides_in_advance_what_its_own_diagnostic_will_show():
    verdicts = ("too few", "too many", "unevidenced", "no signal", "insufficient")
    for driver in load_pack(PACK).drivers:
        assert driver.status in ("instrumented", "not_instrumented"), driver.id
        said = (driver.guard or "").lower()
        for verdict in verdicts:
            assert verdict not in said, (
                f"{driver.id}: the guard says {verdict!r}, which decides the "
                "diagnostic's result before it runs"
            )


def test_the_root_does_not_state_the_direction_of_the_variance():
    """The model under-calls in this data. The pack must not say so.

    Writing the direction into the root turns the pack into a precomputed
    report: the agent would carry the answer into the diagnostic instead of
    reading it out of the rows, and on a fork whose model over-calls the pack
    would ship a wrong answer in a YAML file.
    """
    root = load_pack(PACK).root.lower()
    for leak in ("under", "over", "optimistic", "pessimistic", "understate", "overstate"):
        assert leak not in root, root


@pytest.mark.integration
def test_the_model_bias_diagnostic_pairs_samples_to_blocks():
    driver = next(d for d in load_pack(PACK).drivers if d.id == "model_bias")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, TABLES
    )
    assert rows, "the desurvey join returned nothing"
    row = rows[0]
    # The pairing is the whole diagnostic: assert it found the pairs the design
    # was built on, not merely that a query ran.
    assert row["paired_samples"] >= 100, row
    assert row["modelled_grade"] > 0 and row["assayed_grade"] > 0
```

- [ ] **Step 3: Run it to verify it fails**

Run: `PYTHONPATH=. <python> -m pytest tests/method/test_p5_pack.py -q`
Expected: FAIL — the pack file does not exist.

- [ ] **Step 4: Write the desurvey diagnostic**

Create `method/sql/p5/model_bias.sql`. The desurvey is verified; parameterise the
search radius rather than hardcoding it:

```sql
-- Assays and blocks share no key. The join is derived: a sample's midpoint is
-- desurveyed from its hole's collar, dip and azimuth, then matched to the
-- nearest block centroid within a cubic tolerance. The radius is a parameter
-- because it is a judgement about how far a sample may speak for a block, and
-- that judgement belongs to the site's reconciliation standard, not to us.
WITH sample AS (
  SELECT
    a.copper_grade_pct AS assayed,
    d.collar_easting  + (a.depth_start_meters + a.depth_end_meters) / 2
      * COS(ACOS(-1) * d.dip_degrees / 180)
      * SIN(ACOS(-1) * d.azimuth_degrees / 180) AS x,
    d.collar_northing + (a.depth_start_meters + a.depth_end_meters) / 2
      * COS(ACOS(-1) * d.dip_degrees / 180)
      * COS(ACOS(-1) * d.azimuth_degrees / 180) AS y,
    d.collar_elevation - (a.depth_start_meters + a.depth_end_meters) / 2
      * SIN(ACOS(-1) * ABS(d.dip_degrees) / 180) AS z
  FROM `mining_data.drill_assay_logs` a
  JOIN `mining_data.drill_holes` d USING (drill_hole_id)
)
SELECT
  COUNT(*)                                        AS paired_samples,
  ROUND(AVG(b.copper_grade_pct_est), 4)           AS modelled_grade,
  ROUND(AVG(s.assayed), 4)                        AS assayed_grade,
  ROUND(AVG(s.assayed) - AVG(b.copper_grade_pct_est), 4) AS variance,
  ROUND(SAFE_DIVIDE(AVG(s.assayed) - AVG(b.copper_grade_pct_est),
                    AVG(b.copper_grade_pct_est)) * 100, 1) AS variance_pct
FROM sample s
JOIN `mining_data.geological_block_models` b
  ON ABS(b.centroid_x - s.x) <= @radius_m
 AND ABS(b.centroid_y - s.y) <= @radius_m
 AND ABS(b.centroid_z - s.z) <= @radius_m
```

Validate it against BigQuery before continuing:
```bash
bq query --use_legacy_sql=false --parameter=radius_m:INT64:25 --format=csv "$(cat method/sql/p5/model_bias.sql)"
```
Expected: one row, `paired_samples` around 142.

- [ ] **Step 5: Write the four remaining diagnostics**

Each reuses the `sample` CTE above. Do not copy it blindly — verify each returns
rows before moving on.

- `bias_by_lithology.sql` — group the paired result by
  `b.lithology_type`; return the domain, paired count, modelled mean, assayed
  mean and variance per domain. Five domains exist.
- `bias_by_depth.sql` — band the sample by `(depth_start_meters +
  depth_end_meters) / 2` into parameterised bands (`@shallow_max`,
  `@deep_min`), and return the same measures per band. Depths run 10–448 m.
- `bias_by_elevation.sql` — band by `b.centroid_z` (range 325–550) with
  parameterised cut points, same measures per band.
- `feed_grade_vs_model.sql` — compare `metallurgical_recovery.feed_grade_pct`
  over its 167 daily rows against the block-model mean; return the daily mean
  delivered grade, the modelled mean, and the count of days.

Validate each with `bq query` as in Step 4.

- [ ] **Step 6: Write the pack**

Create `method/p5-geologist.yaml` following `p6-metallurgist.yaml`. The metric
is `contained-metal variance between the block model and realised grade`. The
root must be direction-neutral — `grade delivered differs from grade modelled` —
because the test in Step 2 forbids stating which way.

Each instrumented driver needs a `doc_query` that will retrieve the grade
reconciliation standard from Task 1, and a `guard` that fences the
recommendation. The guards must state what the measurement cannot establish. For
`model_bias` that includes: the pairing is a spatial approximation at the
declared radius, so a variance is evidence about the paired subset and not about
the deposit; and the pairing count must be reported alongside the variance.

`tonnage_reconciliation` and `qaqc_bias` are `not_instrumented` with no `sql`
and no `compare`.

- [ ] **Step 7: Register the pack**

In `mining_agents/tools/method_lookup.py`, change the `PACKS` dict and update the
comment above it, which currently says only P6 has a pack:

```python
#: Personas whose method is encoded. A persona without a pack must fail loudly
#: rather than return an empty tree.
PACKS = {
    "P5": "p5-geologist.yaml",
    "P6": "p6-metallurgist.yaml",
}
```

- [ ] **Step 8: Run the tests**

Run: `PYTHONPATH=. <python> -m pytest tests/method/ tests/tools/test_method_lookup.py tests/patterns/ -q`
Expected: PASS. If `test_method_lookup.py` asserts that a persona other than P6
has no pack, that assertion is now wrong for P5 — update it to name a persona
that still has none, such as P4.

- [ ] **Step 9: Commit**

```bash
git add method/p5-geologist.yaml method/sql/p5 tests/method/test_p5_pack.py \
        mining_agents/tools/method_lookup.py mining_agents/catalog/definitions.py
git commit -m "feat: the geologist's driver tree for contained-metal variance"
```

---

### Task 3: The P1 pack — unplanned repair cost

**Files:**
- Create: `method/p1-reliability.yaml`
- Create: `method/sql/p1/cost_concentration.sql`, `criticality_load.sql`,
  `excursion_rate.sql`, `repair_duration.sql`, `condition_precursors.sql`
- Modify: `mining_agents/tools/method_lookup.py`
- Modify: `mining_agents/catalog/definitions.py` (agent `S01-SP3`)
- Test: `tests/method/test_p1_pack.py`

**Interfaces:**
- Consumes: the same pack machinery as Task 2.
- Produces: `PACKS["P1"] = "p1-reliability.yaml"`.

- [ ] **Step 1: Grant the holder its tools and tables**

Agent `S01-SP3` ("Downtime Duration Forecaster") currently declares
`tools = ["bq_query", "bqml_predict"]` and
`source_tables = ["mining_data.maintenance_logs"]`. Change to:

```python
tools=["bq_query", "bqml_predict", "method_lookup", "run_diagnostic", "doc_search"],
source_tables=[
    "mining_data.maintenance_logs",
    "mining_data.erp_work_orders",
    "mining_data.assets",
    "mining_data.telemetry_stream",
],
```

- [ ] **Step 2: Write the failing pack test**

Create `tests/method/test_p1_pack.py` following the Task 2 template, with:
- metric `unplanned repair cost per asset`
- driver ids `{cost_concentration, criticality_load, excursion_rate,
  repair_duration, condition_precursors, availability, mtbf}`
- `availability` and `mtbf` asserted `not_instrumented`
- `condition_precursors` asserted `instrumented` — it has a diagnostic that
  runs; whether its bands separate is decided by the rows
- the verdict-word test, verbatim from Task 2
- an integration test asserting `cost_concentration` returns all five assets and
  that repair cost varies across them

Add one test specific to this pack:

```python
def test_the_precursor_guard_refuses_a_recommendation_the_bands_do_not_support():
    """This driver measures flat in the shipped data.

    That is a finding, not a reason to hide the driver — but an agent that
    reads a flat result and still recommends condition-based intervention has
    invented a relationship. The guard is the only thing standing between the
    two, so its presence is asserted rather than assumed.
    """
    driver = next(d for d in load_pack(PACK).drivers if d.id == "condition_precursors")
    said = (driver.guard or "").lower()
    assert "separation" in said or "separate" in said, driver.guard
    assert "recommend" in said, driver.guard
```

- [ ] **Step 3: Run it to verify it fails**

Run: `PYTHONPATH=. <python> -m pytest tests/method/test_p1_pack.py -q`
Expected: FAIL — pack file missing.

- [ ] **Step 4: Write the five diagnostics**

Validate each against BigQuery with `bq query` before moving on.

- `cost_concentration.sql` — repair cost by asset from `erp_work_orders` joined
  to `assets`; return asset name, work order count, total and mean repair cost,
  and each asset's share of total cost. 500 work orders across 5 assets, totals
  in the $498k–706k range.
- `criticality_load.sql` — work order count and cost grouped by
  `assets.criticality_rating`, so disproportionate load on the most critical
  assets is visible.
- `excursion_rate.sql` — per `asset_id` and `metric_name` in
  `telemetry_stream`, the count of readings beyond a parameterised number of
  standard deviations from that series' own mean (`@sigma`), and the rate per
  1,000 readings. 13 series, roughly 1,995 rows each.
- `repair_duration.sql` — mean, median and maximum `actual_duration_hours` by
  asset from `maintenance_logs`, with the log count. 152 logs, 1–19 h.
- `condition_precursors.sql` — per asset-day, whether an excursion occurred in
  `telemetry_stream` (banded by `@sigma`) against the count of work orders
  raised on that asset within `@window_days`; return the work-order rate per
  band so the separation between bands is legible.

- [ ] **Step 5: Write the pack**

Metric `unplanned repair cost per asset`; root `failures reaching repair that
condition data could have anticipated`.

`doc_query` values should retrieve the OEM equipment manuals — the corpus holds
manuals for the mill, crusher, conveyor and slurry pump, and P6 already proved a
guard can be fenced by one of them.

The `condition_precursors` guard must require the agent to state the separation
between bands and forbid recommending condition-based intervention when the
bands do not separate — without stating what the separation is.

`availability` and `mtbf` are `not_instrumented`.

- [ ] **Step 6: Register the pack**

Add `"P1": "p1-reliability.yaml"` to `PACKS`.

- [ ] **Step 7: Run the tests**

Run: `PYTHONPATH=. <python> -m pytest tests/method/ tests/tools/ tests/patterns/ -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add method/p1-reliability.yaml method/sql/p1 tests/method/test_p1_pack.py \
        mining_agents/tools/method_lookup.py mining_agents/catalog/definitions.py
git commit -m "feat: the reliability engineer's driver tree for unplanned repair cost"
```

---

### Task 4: The P2 pack — maintenance cost per completed work order

**Files:**
- Create: `method/p2-planner.yaml`
- Create: `method/sql/p2/priority_cost_escalation.sql`, `backlog_aging.sql`,
  `parts_stockout.sql`, `parts_demand_cover.sql`
- Modify: `mining_agents/tools/method_lookup.py`
- Modify: `mining_agents/catalog/definitions.py` (agent `S02-SP2`)
- Test: `tests/method/test_p2_pack.py`

**Interfaces:**
- Consumes: the same pack machinery.
- Produces: `PACKS["P2"] = "p2-planner.yaml"`.

- [ ] **Step 1: Grant the holder its tools**

Agent `S02-SP2` ("Parts Availability Checker") already declares every table this
tree reads — `inventory_levels`, `erp_work_orders`, `work_order_parts_edge`,
`assets` — so `source_tables` does not change. Its `tools` currently read
`["graph_traverse"]`; change to:

```python
tools=["graph_traverse", "bq_query", "method_lookup", "run_diagnostic", "doc_search"],
```

- [ ] **Step 2: Write the failing pack test**

Create `tests/method/test_p2_pack.py` following the Task 2 template, with:
- metric `maintenance cost per completed work order`
- driver ids `{priority_cost_escalation, backlog_aging, parts_stockout,
  parts_demand_cover, schedule_compliance, planned_ratio}`
- `schedule_compliance` and `planned_ratio` asserted `not_instrumented`
- the verdict-word test, verbatim

Add two tests specific to this pack:

```python
def test_the_metric_is_not_schedule_compliance():
    """There is no planned or due date anywhere in erp_work_orders.

    Schedule compliance is what a maintenance planner is actually judged on,
    which makes it exactly the metric someone will reach for in a later edit.
    This test is the note explaining why it cannot be the governing metric
    here, placed where an editor will trip over it.
    """
    metric = load_pack(PACK).metric.lower()
    assert "compliance" not in metric and "schedule" not in metric, metric


def test_the_parts_cover_guard_states_how_narrow_the_demand_record_is():
    # work_order_parts_edge names only 5 distinct SKUs out of 105 in stock, so
    # a cover finding speaks for a sliver of the catalogue. The guard must say
    # the demand record is partial without saying what the finding will be.
    driver = next(d for d in load_pack(PACK).drivers if d.id == "parts_demand_cover")
    said = (driver.guard or "").lower()
    assert "distinct" in said or "catalogue" in said or "subset" in said, driver.guard
```

- [ ] **Step 3: Run it to verify it fails**

Run: `PYTHONPATH=. <python> -m pytest tests/method/test_p2_pack.py -q`
Expected: FAIL — pack file missing.

- [ ] **Step 4: Write the four diagnostics**

- `priority_cost_escalation.sql` — mean and total `repair_cost` and work order
  count grouped by `priority` from `erp_work_orders`, ordered LOW → CRITICAL.
  Cost rises monotonically across the four priorities in the shipped data.
- `backlog_aging.sql` — for work orders not COMPLETED, age in days from
  `created_at` to the dataset's maximum date, banded by a parameterised
  threshold (`@stale_days`), with counts and mean cost per band and status.
  117 OPEN and 127 IN_PROGRESS exist.
- `parts_stockout.sql` — parts at or below `reorder_point_limit` from
  `inventory_levels`, with `stock_level`, `reorder_point_limit`,
  `lead_time_days` and `unit_price_usd`. 15 of 105 SKUs qualify; one is at zero;
  lead times run 2–30 days.
- `parts_demand_cover.sql` — join `work_order_parts_edge` to `inventory_levels`
  to give demanded quantity per part against stock on hand and lead time. The
  join is complete (186 of 186) but names only 5 distinct parts.

- [ ] **Step 5: Write the pack**

Metric `maintenance cost per completed work order`; root `work escalating in
priority before it is done`.

`doc_query` values must retrieve the work-order prioritisation standard authored
in Task 1.

- [ ] **Step 6: Register, test, commit**

Add `"P2": "p2-planner.yaml"` to `PACKS`.
Run: `PYTHONPATH=. <python> -m pytest tests/method/ tests/tools/ tests/patterns/ -q`
Expected: PASS.

```bash
git add method/p2-planner.yaml method/sql/p2 tests/method/test_p2_pack.py \
        mining_agents/tools/method_lookup.py mining_agents/catalog/definitions.py
git commit -m "feat: the maintenance planner's driver tree for cost per work order"
```

---

### Task 5: The P3 pack — severity-weighted incident exposure

**Files:**
- Create: `method/p3-hse.yaml`
- Create: `method/sql/p3/location_concentration.sql`, `severity_mix.sql`,
  `fatigue_exposure.sql`, `radio_distress.sql`
- Modify: `mining_agents/tools/method_lookup.py`
- Modify: `mining_agents/catalog/definitions.py` (agent `S05-SP2`)
- Test: `tests/method/test_p3_pack.py`

**Interfaces:**
- Consumes: the same pack machinery.
- Produces: `PACKS["P3"] = "p3-hse.yaml"`.

- [ ] **Step 1: Grant the holder its tools and one table**

Agent `S05-SP2` ("Operator Fatigue Cross-Check") declares seven tables but not
`mining_data.radio_communications`, which the fourth driver reads. Add it, and
change `tools` from `["graph_traverse"]` to:

```python
tools=["graph_traverse", "bq_query", "method_lookup", "run_diagnostic", "doc_search"],
```

- [ ] **Step 2: Write the failing pack test**

Create `tests/method/test_p3_pack.py` following the Task 2 template, with:
- metric `severity-weighted incident exposure`
- driver ids `{location_concentration, severity_mix, fatigue_exposure,
  radio_distress, fatigue_to_incident, shift_pattern}`
- `fatigue_to_incident` and `shift_pattern` asserted `not_instrumented`
- the verdict-word test, verbatim

Add one test specific to this pack:

```python
def test_every_instrumented_driver_guards_the_cell_count():
    """Sixty incidents is the ceiling on this persona.

    Any two-way split gives cells of three to five, so a finding read off a
    thin cell is the failure mode here. Each guard must require the count to be
    reported beside the finding — without saying what the count will be, which
    the verdict test forbids.
    """
    for driver in load_pack(PACK).drivers:
        if driver.status != "instrumented":
            continue
        said = (driver.guard or "").lower()
        assert "count" in said, f"{driver.id}: {driver.guard}"
```

- [ ] **Step 3: Run it to verify it fails**

Run: `PYTHONPATH=. <python> -m pytest tests/method/test_p3_pack.py -q`
Expected: FAIL — pack file missing.

- [ ] **Step 4: Write the four diagnostics**

- `location_concentration.sql` — incident count by `location_description` from
  `safety_incidents`, with the severity breakdown per location. Counts run
  17/12/12/10/9 — the only one-dimensional split with usable cells.
- `severity_mix.sql` — incident count by `severity_level`, with each level's
  share of the total. HAZARD 16, MTI 14, FATALITY 14, NEAR_MISS 11, LTI 5.
- `fatigue_exposure.sql` — from `biometric_fatigue_logs`: the alert count,
  mean and maximum `sleep_deficit_hours`, the microsleep distribution, and the
  count of distinct operators, banded by a parameterised deficit threshold
  (`@deficit_hours`). 3,340 logs; 117 alerts.
- `radio_distress.sql` — from `radio_communications`: emergency-flagged count
  against total, and mean `sentiment_score` by time bucket. 164 of 573 flagged.

- [ ] **Step 5: Write the pack**

Metric `severity-weighted incident exposure`; root `exposure concentrated where
controls are weakest`.

`doc_query` values must retrieve the fatigue management standard from Task 1.

Every instrumented guard must require the cell count be reported beside the
finding. `fatigue_to_incident` is `not_instrumented` — only 5 of 60 incidents
carry an operator link, so the attributing join does not exist at usable scale.
`shift_pattern` is `not_instrumented` — incident and fatigue timestamps are all
00:00.

- [ ] **Step 6: Register, test, commit**

Add `"P3": "p3-hse.yaml"` to `PACKS`.
Run: `PYTHONPATH=. <python> -m pytest tests/method/ tests/tools/ tests/patterns/ -q`
Expected: PASS.

```bash
git add method/p3-hse.yaml method/sql/p3 tests/method/test_p3_pack.py \
        mining_agents/tools/method_lookup.py mining_agents/catalog/definitions.py
git commit -m "feat: the HSE lead's driver tree for incident exposure"
```

---

### Task 6: Carry four more metrics to the screens

**Files:**
- Modify: `scripts/build_app_data.py` only if it does not already generalise
- Modify: `apps/shared/plain.js` (driver phrases for the new driver ids)
- Test: `tests/js/plain.test.js`, `tests/js/router.test.js`
- Test: `tests/scripts/test_build_app_data.py`

**Interfaces:**
- Consumes: `PACKS` with five entries after Tasks 2–5.
- Produces: `apps/shared/data/personas.json` carrying `method.metric` for P1,
  P2, P3, P5 and P6.

- [ ] **Step 1: Write the failing tests**

In `tests/scripts/test_build_app_data.py`, add:

```python
def test_every_persona_with_a_pack_carries_its_metric_to_the_screens():
    from mining_agents.tools.method_lookup import PACKS
    personas = json.loads((ROOT / "apps/shared/data/personas.json").read_text())["personas"]
    for code in PACKS:
        assert personas[code].get("method", {}).get("metric"), code


def test_a_persona_without_a_pack_carries_no_method_block():
    # A method block on a persona with no tree would put a problem-solving
    # question on a page that cannot answer it.
    from mining_agents.tools.method_lookup import PACKS
    personas = json.loads((ROOT / "apps/shared/data/personas.json").read_text())["personas"]
    for code, persona in personas.items():
        if code not in PACKS:
            assert not persona.get("method"), code
```

In `tests/js/plain.test.js`, add a test asserting every driver id across all
shipped packs has a plain phrase — the activity log must never print a raw
driver id at a reader:

```js
test("every driver id in every pack has a plain phrase", () => {
  const ids = require("../fixtures/driver-ids.json"); // written in step 3
  for (const id of ids) {
    const line = plain.callLine("run_diagnostic", { driver_id: id });
    assert.ok(line && !line.includes(id), `no plain phrase for ${id}: ${line}`);
  }
});
```

- [ ] **Step 2: Run them to verify they fail**

Run: `PYTHONPATH=. <python> -m pytest tests/scripts/test_build_app_data.py -q`
and `node --test 'tests/js/*.test.js'`
Expected: FAIL on the new tests.

- [ ] **Step 3: Add the plain phrases**

In `apps/shared/plain.js`, extend `METHOD_DRIVERS` with a phrase for each of the
19 new driver ids, in the same voice as the P6 entries — a phrase that names the
cause in a reader's language, such as "Checking whether repair cost is
concentrated in a few assets". Generate `tests/fixtures/driver-ids.json` from the
packs so the list cannot drift from what ships.

- [ ] **Step 4: Rebuild the app data**

Run: `PYTHONPATH=. <python> -m scripts.build_app_data`

Verify:
```bash
<python> -c "import json; d=json.load(open('apps/shared/data/personas.json'))['personas']; print({k: v.get('method') for k,v in d.items()})"
```
Expected: a metric for P1, P2, P3, P5, P6; `None` for P4, P7, P8.

- [ ] **Step 5: Run both suites**

Run: `PYTHONPATH=. <python> -m pytest -q` and `node --test 'tests/js/*.test.js'`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/shared/data/personas.json apps/shared/plain.js tests/
git commit -m "feat: carry four more governing metrics to the persona pages"
```

---

### Task 7: Deploy and verify each persona live

**Why this task exists:** the workspace is served from Cloud Run through a
reverse proxy. Editing `apps/**` on disk changes nothing in the browser until
`scripts/deploy_apps.py::apply()` re-runs. During the P6 build, browser
verification found a real defect — two drawers on one answer both titled
"Technical detail" — that every unit test had passed over.

**Files:** none created; this task verifies.

- [ ] **Step 1: Deploy**

```python
from scripts.deploy_apps import apply, CONFIRM_PHRASE
apply(dry_run=False, confirm=CONFIRM_PHRASE)
```

Confirm a new revision reaches Ready:
```bash
gcloud run revisions list --service mag-workspace --region us-central1 --limit 3 \
  --format='value(name,status.conditions[0].status)'
```

- [ ] **Step 2: Verify the served assets are fresh**

In the browser at `http://localhost:8805`, fetch with `{cache: "reload"}` and
confirm the served `personas.json` carries the five metrics. Verifying the file
on disk proves nothing about what the browser is running.

- [ ] **Step 3: Verify each persona's lead question**

For each of `?p=P1`, `?p=P2`, `?p=P3`, `?p=P5` on
`http://localhost:8805/workspace/persona.html`, assert the first starter
question is built from that persona's governing metric and is a problem-solving
question — not "What's in the … right now?".

- [ ] **Step 4: Verify one full diagnosis per persona**

Ask each persona's governing question and measure the **rendered DOM**, not the
event stream:
- the answer pane holds the coordinator's conclusion, not the specialists' working
- uninstrumented drivers are named in the answer rather than silently dropped
- no recommendation appears without a document retrieved first
- no ADK node names leak into rendered copy
- no metal is named anywhere in the rendered copy

Record the measured character counts and heading lists in the progress ledger, as
was done for P6.

- [ ] **Step 5: Record and commit**

Append the measurements to a progress ledger and commit.

---

## Self-review

**Spec coverage.** Every section of the spec maps to a task: the four trees to
Tasks 2–5, the authored SOPs to Task 1, the catalogue changes to the first step
of each pack task, the `personas.json` and router path to Task 6, and the live
verification requirement to Task 7. P8, P4 and P7 are out of scope in the spec
and absent here, correctly.

**Placeholders.** None. Where a diagnostic's exact SQL is not written out, the
task states the tables, columns, grouping, parameters and the measured row counts
the query must reproduce, and requires validation against BigQuery before the
step completes. This is deliberate: SQL written into a plan without being run is
SQL that will be wrong, and the P6 tests set the precedent that a diagnostic is
pinned by the magnitudes it returns rather than by its text.

**Type consistency.** `PACKS` is a `dict[str, str]` keyed by persona code
throughout. Driver ids are used identically in the pack YAML, the SQL filenames,
the pack tests and `METHOD_DRIVERS`. `load_pack`, `run_query` and
`assert_no_interpolation` are imported from the same modules the P6 tests use.

**Known risk carried deliberately.** P1's `condition_precursors` will return a
flat result on the shipped data, and P3's thin cells mean several findings will
be reported with counts that do not support a strong conclusion. Both are the
spec's approved position: declare honestly now, fix the generator later.
