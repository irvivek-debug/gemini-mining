# P6 Problem-Solving Agents Implementation Plan

> **For agentic workers:** implement this plan task-by-task, in order. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Metallurgist (P6) agents diagnose and resolve rather than retrieve — for the governing metric, produce the ranked problems, the controllable lever, the constraint that bounds it, and a guarded recommendation.

**Architecture:** Three parts. A *method skeleton* (one YAML per persona) holds the driver tree, its diagnostics and its guards, and is inspectable and complete. A *document retrieval* tool backed by BigQuery vector search supplies resolution constraints from the real corpus, cited. The *agent* sequences the tree, catches confounds, and writes the narrative. Structure never comes from retrieval, because top-k search cannot guarantee completeness and a silently skipped driver reads as "no problem found".

**Tech Stack:** Python 3.12, Google ADK, BigQuery (`ML.GENERATE_EMBEDDING` + `VECTOR_SEARCH`, model `text-embedding-005` over connection `us.gemini-connection`), PyYAML 6, pypdf, `node:test` for the JS vocabulary layer.

## Global Constraints

- **Commodity-neutral.** Say "contained metal". Never name a metal in prose or copy.
- **Money as ranges, never a point figure.**
- **No invented numbers.** Every figure traces to the catalogue or the data, or is marked `[CLIENT INPUT REQUIRED]`.
- **Python:** `python3`. Run pytest as `PYTHONPATH=. <python> -m pytest`.
- **JS tests need a quoted glob:** `node --test 'tests/js/*.test.js'`. The bare directory form fails on Node 24.
- **Dual export in shared JS:** `if (typeof module !== "undefined") module.exports = { … };`
- **All SQL uses `@parameters`.** `run_query` applies `assert_no_interpolation` to author-written SQL too. **`top_k => 5` is flagged** — the `>` of `=>` followed by a digit matches the literal-predicate regex. Use `top_k => @k`. This is verified, not theoretical.
- **`run_query` enforces declared tables** via BigQuery dry run. A tool must declare every table its SQL resolves to.
- **Never push to a remote** without explicit go-ahead. Commit locally freely.
- **A driver is never silently absent** from an answer. It is evidenced, unevidenced, or not instrumented.
- **Comparison is on setting-bands, never outcome percentiles.** Outcome-decile comparison banks noise as achievable.
- Project `your-gcp-project-id`, dataset `mining_data`, location `US`.

## File Structure

| Path | Responsibility |
|---|---|
| `scripts/build_doc_chunks.py` | Extract text from the GCS PDF corpus, chunk it, load to BigQuery |
| `mining_agents/method/__init__.py` | Package marker |
| `mining_agents/method/pack.py` | Load and validate a method pack; the validation gates live here |
| `method/p6-metallurgist.yaml` | The P6 driver tree — data, not code |
| `method/sql/p6/*.sql` | Diagnostic SQL, one file per driver, parameterised |
| `mining_agents/tools/doc_search.py` | Vector search over the corpus, returning cited passages |
| `mining_agents/tools/method_lookup.py` | Return the driver tree for an agent's persona |
| `mining_agents/patterns/deep.py` | Gains the METHOD instruction block and two tool builders |
| `mining_agents/catalog/definitions.py` | P6 agents gain the two new tools |
| `apps/shared/plain.js` | Reader-facing vocabulary for the two new tools |
| `tests/tools/test_doc_search.py`, `tests/method/test_pack.py`, `tests/method/test_p6_pack.py`, `tests/patterns/test_method_instruction.py`, `tests/js/plain.test.js` | Gates |

---

### Task 1: Extract the document corpus into BigQuery

**Files:**
- Create: `scripts/build_doc_chunks.py`
- Create: `tests/test_doc_chunks.py`
- Modify: `requirements.txt`, `pyproject.toml`

**Interfaces:**
- Produces: `chunk_text(text: str, size: int = 800, overlap: int = 100) -> list[str]`; BigQuery table `mining_data.doc_chunks` with columns `doc_id STRING, folder STRING, file_name STRING, chunk_index INT64, chunk_text STRING`.

**Context:** The corpus is `gs://mining-knowledge-base/` — 40 PDFs across six folders, 30,755 characters of extracted text in total. It is small; that is expected and recorded in the spec. Do **not** use `mining_data.unstructured_docs_metadata` for anything: every `file_path` in it resolves to nothing and its `chunk_count` overstates the corpus about ninetyfold. Read GCS directly.

- [ ] **Step 1: Register the `integration` marker**

Later tasks mark tests that need live BigQuery with `@pytest.mark.integration` and run the rest with `-m "not integration"`. `pyproject.toml` has a `[tool.pytest.ini_options]` block but no `markers` key, so the marker would raise `PytestUnknownMarkWarning` on every run. Add the key beside the existing `testpaths`:

```toml
markers = [
  "integration: needs live BigQuery; excluded with -m 'not integration'",
]
```

- [ ] **Step 2: Add the two dependencies**

Append to `requirements.txt`:

```
pypdf>=5.0
google-cloud-storage>=2.18
```

`google-cloud-storage` is not currently in `requirements.txt` and this script reads GCS directly.

- [ ] **Step 3: Write the failing test**

`tests/test_doc_chunks.py`:

```python
"""Chunking is pure, so it is tested without GCS or BigQuery."""
from scripts.build_doc_chunks import chunk_text


def test_short_text_is_one_chunk():
    assert chunk_text("a short manual page") == ["a short manual page"]


def test_long_text_splits_with_overlap():
    body = "x" * 2000
    chunks = chunk_text(body, size=800, overlap=100)
    assert len(chunks) == 3, chunks
    assert all(len(c) <= 800 for c in chunks)
    # Overlap exists so a sentence spanning a boundary is retrievable.
    assert chunks[0][-100:] == chunks[1][:100]


def test_empty_text_yields_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []
```

- [ ] **Step 4: Run it and watch it fail**

Run: `PYTHONPATH=. python3 -m pytest tests/test_doc_chunks.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'scripts.build_doc_chunks'`

- [ ] **Step 5: Write the script**

`scripts/build_doc_chunks.py`:

```python
"""Extract the GCS PDF corpus into mining_data.doc_chunks.

The corpus is read from GCS directly. mining_data.unstructured_docs_metadata
is NOT used: every file_path it carries resolves to nothing, and its
chunk_count sums to 3,392 against a real corpus of roughly 38 chunks.
"""
from __future__ import annotations

import io

from google.cloud import bigquery, storage
from pypdf import PdfReader

BUCKET = "mining-knowledge-base"
TABLE = "mining_data.doc_chunks"
SCHEMA = [
    bigquery.SchemaField("doc_id", "STRING"),
    bigquery.SchemaField("folder", "STRING"),
    bigquery.SchemaField("file_name", "STRING"),
    bigquery.SchemaField("chunk_index", "INT64"),
    bigquery.SchemaField("chunk_text", "STRING"),
]


def chunk_text(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    """Split text into overlapping windows. Overlap keeps a sentence that
    spans a boundary retrievable from either side."""
    body = text.strip()
    if not body:
        return []
    if len(body) <= size:
        return [body]
    step = size - overlap
    return [body[i:i + size] for i in range(0, len(body) - overlap, step)]


def extract(blob) -> str:
    reader = PdfReader(io.BytesIO(blob.download_as_bytes()))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def rows() -> list[dict]:
    client = storage.Client()
    out = []
    for blob in client.list_blobs(BUCKET):
        if not blob.name.lower().endswith(".pdf"):
            continue
        folder, _, file_name = blob.name.rpartition("/")
        for index, chunk in enumerate(chunk_text(extract(blob))):
            out.append({
                "doc_id": blob.name,
                "folder": folder,
                "file_name": file_name,
                "chunk_index": index,
                "chunk_text": chunk,
            })
    return out


def main() -> None:
    data = rows()
    if not data:
        raise SystemExit("no chunks extracted; refusing to write an empty table")
    client = bigquery.Client(location="US")
    job = client.load_table_from_json(
        data,
        TABLE,
        job_config=bigquery.LoadJobConfig(
            schema=SCHEMA, write_disposition="WRITE_TRUNCATE"
        ),
    )
    job.result()
    print(f"loaded {len(data)} chunks from {len({r['doc_id'] for r in data})} documents")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run the test and watch it pass**

Run: `PYTHONPATH=. python3 -m pytest tests/test_doc_chunks.py -v`
Expected: PASS, 3 tests

- [ ] **Step 7: Build the real table**

Run: `PYTHONPATH=. python3 scripts/build_doc_chunks.py`
Expected: `loaded <N> chunks from 40 documents`, with N between 30 and 80. If N is outside that range, stop and report — the corpus measured 30,755 characters, so anything far outside that band means extraction changed.

- [ ] **Step 8: Commit**

```bash
git add requirements.txt pyproject.toml scripts/build_doc_chunks.py tests/test_doc_chunks.py
git commit -m "feat: extract the document corpus into mining_data.doc_chunks"
```

---

### Task 2: Embed the chunks

**Files:**
- Create: `scripts/build_doc_embeddings.py`
- Create: `tests/test_doc_embeddings.py`

**Interfaces:**
- Consumes: `mining_data.doc_chunks` from Task 1.
- Produces: model `mining_data.text_embedding_model`; table `mining_data.doc_chunks_embedded` carrying every column of `doc_chunks` plus `ml_generate_embedding_result ARRAY<FLOAT64>` of 768 dimensions.

**Context:** The connection `projects/your-gcp-project-id/locations/us/connections/gemini-connection` holds `roles/aiplatform.user`, and `text-embedding-005` returns 768 dimensions through it. Both facts are verified — if either fails, stop and report rather than switching endpoints.

- [ ] **Step 1: Write the failing test**

`tests/test_doc_embeddings.py`:

```python
"""The embedded table is what doc_search reads, so its shape is a gate."""
import pytest
from google.cloud import bigquery

pytestmark = pytest.mark.integration


def test_every_chunk_has_a_768_dim_embedding():
    client = bigquery.Client(location="US")
    row = next(iter(client.query("""
        SELECT COUNT(*) AS n,
               COUNTIF(ARRAY_LENGTH(ml_generate_embedding_result) = 768) AS good
        FROM `mining_data.doc_chunks_embedded`
    """).result()))
    assert row["n"] > 0, "the embedded table is empty"
    assert row["good"] == row["n"], f"{row['n'] - row['good']} chunks embedded badly"


def test_embedded_row_count_matches_source():
    client = bigquery.Client(location="US")
    row = next(iter(client.query("""
        SELECT (SELECT COUNT(*) FROM `mining_data.doc_chunks`) AS src,
               (SELECT COUNT(*) FROM `mining_data.doc_chunks_embedded`) AS emb
    """).result()))
    assert row["src"] == row["emb"], "embedding dropped rows"
```

- [ ] **Step 2: Run it and watch it fail**

Run: `PYTHONPATH=. python3 -m pytest tests/test_doc_embeddings.py -v`
Expected: FAIL, `NotFound: 404 ... doc_chunks_embedded`

- [ ] **Step 3: Write the script**

`scripts/build_doc_embeddings.py`:

```python
"""Create the remote embedding model and embed mining_data.doc_chunks."""
from __future__ import annotations

from google.cloud import bigquery

CONNECTION = (
    "projects/your-gcp-project-id/locations/us/connections/gemini-connection"
)

MODEL_DDL = f"""
CREATE OR REPLACE MODEL `mining_data.text_embedding_model`
REMOTE WITH CONNECTION `{CONNECTION}`
OPTIONS (ENDPOINT = 'text-embedding-005')
"""

EMBED_DDL = """
CREATE OR REPLACE TABLE `mining_data.doc_chunks_embedded` AS
SELECT * EXCEPT (content), content AS chunk_text
FROM ML.GENERATE_EMBEDDING(
  MODEL `mining_data.text_embedding_model`,
  (SELECT doc_id, folder, file_name, chunk_index, chunk_text AS content
     FROM `mining_data.doc_chunks`),
  STRUCT(TRUE AS flatten_json_output, 'RETRIEVAL_DOCUMENT' AS task_type)
)
"""


def main() -> None:
    client = bigquery.Client(location="US")
    client.query(MODEL_DDL).result()
    client.query(EMBED_DDL).result()
    row = next(iter(client.query(
        "SELECT COUNT(*) AS n FROM `mining_data.doc_chunks_embedded`"
    ).result()))
    print(f"embedded {row['n']} chunks")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run it**

Run: `PYTHONPATH=. python3 scripts/build_doc_embeddings.py`
Expected: `embedded <N> chunks`, N matching Task 1.

If `ML.GENERATE_EMBEDDING` reports a column error, check the output column name with `SELECT * FROM mining_data.doc_chunks_embedded LIMIT 1` before changing the DDL — the flattened result column is `ml_generate_embedding_result` and the tests depend on that name.

- [ ] **Step 5: Run the tests and watch them pass**

Run: `PYTHONPATH=. python3 -m pytest tests/test_doc_embeddings.py -v`
Expected: PASS, 2 tests

- [ ] **Step 6: Commit**

```bash
git add scripts/build_doc_embeddings.py tests/test_doc_embeddings.py
git commit -m "feat: embed the document corpus for vector search"
```

---

### Task 3: The `doc_search` tool

**Files:**
- Create: `mining_agents/tools/doc_search.py`
- Create: `tests/tools/test_doc_search.py`

**Interfaces:**
- Consumes: `mining_data.doc_chunks_embedded` from Task 2; `run_query` and `tool` from the existing tool layer.
- Produces: `doc_search(query: str, k: int = 5)` returning the standard envelope with `data = {"query": str, "passages": [{"file_name": str, "folder": str, "chunk_text": str, "distance": float}]}`; `TABLES = ["mining_data.doc_chunks_embedded", "mining_data.text_embedding_model"]`.

**Context:** Every tool in this repo returns the envelope built by the `@tool` decorator and routes its SQL through `run_query`, which enforces declared tables via a BigQuery dry run and lints for literal predicates. Follow `mining_agents/tools/ontology_lookup.py` for the shape.

**Two traps, both verified against the live warehouse — neither is a guess.**

1. `top_k => 5` is refused by `assert_no_interpolation`, because the `>` of `=>` followed by a digit matches the literal-predicate regex. Pass `top_k => @k`. Step 1 tests this directly.
2. **A BQML model counts as a referenced table.** A dry run of `ML.GENERATE_EMBEDDING(MODEL \`mining_data.text_embedding_model\`, …)` reports `referenced_tables = [mining_data.text_embedding_model]`. So `assert_reads_only_declared_tables` refuses the query unless the model is declared alongside the data table. `TABLES` therefore has **two** entries. Do not solve this by relaxing the check.

- [ ] **Step 1: Write the failing test**

`tests/tools/test_doc_search.py`:

```python
"""doc_search returns cited passages, and its SQL survives the literal lint."""
import pytest

from mining_agents.tools.bq_query import assert_no_interpolation
from mining_agents.tools.doc_search import SEARCH_SQL, doc_search


def test_the_sql_carries_no_literal_predicate():
    # top_k => 5 would be refused: the '>' of '=>' plus a digit matches the
    # literal-predicate regex. This gate is why the tool passes top_k => @k.
    assert_no_interpolation(SEARCH_SQL)


def test_the_sql_declares_the_model_as_well_as_the_table():
    # A BQML model is reported by the dry run as a referenced table, so
    # assert_reads_only_declared_tables refuses the query unless it is declared.
    from mining_agents.tools.doc_search import TABLES
    assert TABLES == [
        "mining_data.doc_chunks_embedded",
        "mining_data.text_embedding_model",
    ]


@pytest.mark.integration
def test_a_crusher_query_retrieves_the_crusher_manual():
    said = doc_search("crusher gap size aperture torque limit", k=5)
    assert said["success"], said.get("error")
    names = [p["file_name"] for p in said["data"]["passages"]]
    assert any("crusher" in n for n in names), names


@pytest.mark.integration
def test_passages_carry_their_source_for_citation():
    said = doc_search("closed side setting", k=3)
    assert said["success"], said.get("error")
    for passage in said["data"]["passages"]:
        assert passage["file_name"], "a passage with no source cannot be cited"
        assert passage["chunk_text"].strip()
```

- [ ] **Step 2: Run it and watch it fail**

Run: `PYTHONPATH=. python3 -m pytest tests/tools/test_doc_search.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'mining_agents.tools.doc_search'`

- [ ] **Step 3: Write the tool**

`mining_agents/tools/doc_search.py`:

```python
"""Semantic search over the document corpus, returning citable passages.

Retrieval supplies resolution CONTENT — what a manual or a standard permits.
It must never supply method STRUCTURE: top-k search has no completeness
guarantee, and a driver whose chunk fails to retrieve would be silently
skipped, which reads to an operator as "no problem found".
"""
from __future__ import annotations

from mining_agents.tools.base import tool
from mining_agents.tools.bq_query import run_query

# The model is listed because a BigQuery dry run reports it among
# referenced_tables, so assert_reads_only_declared_tables refuses the query
# without it. Verified, not assumed.
TABLES = [
    "mining_data.doc_chunks_embedded",
    "mining_data.text_embedding_model",
]

# top_k is bound as @k deliberately. Written as `top_k => 5` this SQL is
# refused by assert_no_interpolation, because the '>' of '=>' followed by a
# digit matches the literal-predicate regex.
SEARCH_SQL = """
SELECT
  base.file_name  AS file_name,
  base.folder     AS folder,
  base.chunk_text AS chunk_text,
  distance
FROM VECTOR_SEARCH(
  TABLE `mining_data.doc_chunks_embedded`,
  'ml_generate_embedding_result',
  (SELECT ml_generate_embedding_result
     FROM ML.GENERATE_EMBEDDING(
       MODEL `mining_data.text_embedding_model`,
       (SELECT @query AS content),
       STRUCT(TRUE AS flatten_json_output, 'RETRIEVAL_QUERY' AS task_type))),
  top_k => @k)
ORDER BY distance
"""


@tool(TABLES)
def doc_search(query: str, k: int = 5):
    """Search manuals, standards and reports. Returns passages with sources."""
    passages, scanned = run_query(
        SEARCH_SQL, {"query": query, "k": int(k)}, TABLES
    )
    return {"query": query, "passages": passages}, scanned
```

- [ ] **Step 4: Run the unit tests**

Run: `PYTHONPATH=. python3 -m pytest tests/tools/test_doc_search.py -v -m "not integration"`
Expected: PASS, 2 tests

- [ ] **Step 5: Run the integration tests**

Run: `PYTHONPATH=. python3 -m pytest tests/tools/test_doc_search.py -v`
Expected: PASS, 4 tests.

If the dry run reports the query resolves to no table, the `VECTOR_SEARCH` table argument is not being seen — report rather than relaxing the check in `bq_query.py`. That check is a security control.

- [ ] **Step 6: Commit**

```bash
git add mining_agents/tools/doc_search.py tests/tools/test_doc_search.py
git commit -m "feat: add doc_search over the corpus with cited passages"
```

---

### Task 4: The method pack format and its gates

**Files:**
- Create: `mining_agents/method/__init__.py`
- Create: `mining_agents/method/pack.py`
- Create: `tests/method/test_pack.py`
- Create: `tests/method/fixtures/valid.yaml`, `tests/method/fixtures/outcome-decile.yaml`

**Interfaces:**
- Produces: `load_pack(path: str | Path) -> Pack`; `Pack` with `.metric: str`, `.root: str`, `.drivers: list[Driver]`; `Driver` with `.id`, `.question`, `.status` (one of `evidenced`, `unevidenced`, `not_instrumented`), `.controllable: bool`, `.compare: str | None`, `.sql: str | None`, `.params: dict`, `.doc_query: str | None`, `.guard: str | None`. `PackError` is raised on any violation.

**Context:** This is the structure that retrieval cannot supply. Two rules from the spec are enforced here as gates, not conventions: comparison is on setting-bands rather than outcome percentiles, and every driver declares a status so none can be silently absent from an answer.

- [ ] **Step 1: Write the fixtures**

`tests/method/fixtures/valid.yaml`:

```yaml
metric: unit cost per tonne of contained metal
root: contained metal lost to tailings
drivers:
  - id: liberation
    question: Is the crusher setting costing recovery?
    status: evidenced
    controllable: true
    compare: setting_band
    sql: sql/p6/liberation.sql
    params:
      tight_max: 117
      wide_min: 123
    doc_query: crusher gap size aperture torque limit
    guard: throughput neutrality and torque headroom
  - id: reagent_regime
    question: Is the reagent regime costing recovery?
    status: not_instrumented
    controllable: false
```

`tests/method/fixtures/outcome-decile.yaml` — identical to `valid.yaml` except the first driver's `compare` is `outcome_decile`.

- [ ] **Step 2: Write the failing test**

`tests/method/test_pack.py`:

```python
"""The pack is the part of the method that must be complete and inspectable."""
from pathlib import Path

import pytest

from mining_agents.method.pack import PackError, load_pack

FIXTURES = Path(__file__).parent / "fixtures"


def test_a_valid_pack_loads_its_drivers():
    pack = load_pack(FIXTURES / "valid.yaml")
    assert pack.metric == "unit cost per tonne of contained metal"
    assert [d.id for d in pack.drivers] == ["liberation", "reagent_regime"]
    assert pack.drivers[0].controllable is True
    assert pack.drivers[0].params == {"tight_max": 117, "wide_min": 123}


def test_an_outcome_decile_comparison_is_refused():
    # Comparing to the best decile of an outcome banks noise as achievable;
    # regression to the mean guarantees the prize is overstated.
    with pytest.raises(PackError, match="setting_band"):
        load_pack(FIXTURES / "outcome-decile.yaml")


def test_a_driver_without_a_status_is_refused(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "metric: m\nroot: r\ndrivers:\n  - id: d\n    question: q\n"
        "    controllable: false\n"
    )
    with pytest.raises(PackError, match="status"):
        load_pack(bad)


def test_an_unknown_status_is_refused(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "metric: m\nroot: r\ndrivers:\n  - id: d\n    question: q\n"
        "    status: probably\n    controllable: false\n"
    )
    with pytest.raises(PackError, match="probably"):
        load_pack(bad)


def test_an_evidenced_driver_must_carry_a_diagnostic(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "metric: m\nroot: r\ndrivers:\n  - id: d\n    question: q\n"
        "    status: evidenced\n    controllable: true\n    compare: setting_band\n"
    )
    with pytest.raises(PackError, match="sql"):
        load_pack(bad)


def test_a_pack_with_no_drivers_is_refused(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("metric: m\nroot: r\ndrivers: []\n")
    with pytest.raises(PackError, match="driver"):
        load_pack(bad)
```

- [ ] **Step 3: Run it and watch it fail**

Run: `PYTHONPATH=. python3 -m pytest tests/method/test_pack.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'mining_agents.method'`

- [ ] **Step 4: Write the loader**

`mining_agents/method/__init__.py`: empty file.

`mining_agents/method/pack.py`:

```python
"""Load and validate a persona's method pack.

The pack is the method's SKELETON: which drivers exist, in what order, which
are controllable, and what guards a recommendation. It deliberately carries no
resolution prose — resolution content comes from the document corpus, so that
a recommendation is the customer's own standard rather than ours.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

#: A driver is never silently absent from an answer. It is one of these.
STATUSES = frozenset({"evidenced", "unevidenced", "not_instrumented"})

#: Comparison is across bands of a controllable SETTING. Comparing to the best
#: decile of an OUTCOME banks noise as achievable, because the top decile of a
#: noisy series is partly luck.
COMPARISONS = frozenset({"setting_band"})


class PackError(ValueError):
    """The pack violates a rule the method depends on."""


@dataclass(frozen=True)
class Driver:
    id: str
    question: str
    status: str
    controllable: bool
    compare: str | None = None
    sql: str | None = None
    params: dict = field(default_factory=dict)
    doc_query: str | None = None
    guard: str | None = None


@dataclass(frozen=True)
class Pack:
    metric: str
    root: str
    drivers: list[Driver]


def _driver(raw: dict, index: int) -> Driver:
    where = raw.get("id") or f"driver #{index}"
    for required in ("id", "question", "controllable"):
        if required not in raw:
            raise PackError(f"{where}: missing {required!r}")
    if "status" not in raw:
        raise PackError(f"{where}: missing 'status'; every driver declares one")
    if raw["status"] not in STATUSES:
        raise PackError(
            f"{where}: status {raw['status']!r} is not one of {sorted(STATUSES)}"
        )
    if raw["status"] == "evidenced":
        if not raw.get("sql"):
            raise PackError(f"{where}: an evidenced driver must carry 'sql'")
        if raw.get("compare") not in COMPARISONS:
            raise PackError(
                f"{where}: compare must be one of {sorted(COMPARISONS)}; "
                "outcome-percentile comparison overstates the prize"
            )
    return Driver(
        id=raw["id"],
        question=raw["question"],
        status=raw["status"],
        controllable=bool(raw["controllable"]),
        compare=raw.get("compare"),
        sql=raw.get("sql"),
        params=dict(raw.get("params") or {}),
        doc_query=raw.get("doc_query"),
        guard=raw.get("guard"),
    )


def load_pack(path: str | Path) -> Pack:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    for required in ("metric", "root", "drivers"):
        if required not in raw:
            raise PackError(f"pack is missing {required!r}")
    if not raw["drivers"]:
        raise PackError("pack declares no driver; a tree with no branch is not a method")
    drivers = [_driver(d, i) for i, d in enumerate(raw["drivers"])]
    seen = [d.id for d in drivers]
    if len(set(seen)) != len(seen):
        raise PackError(f"duplicate driver ids: {seen}")
    return Pack(metric=raw["metric"], root=raw["root"], drivers=drivers)
```

- [ ] **Step 5: Run the tests and watch them pass**

Run: `PYTHONPATH=. python3 -m pytest tests/method/test_pack.py -v`
Expected: PASS, 6 tests

- [ ] **Step 6: Commit**

```bash
git add mining_agents/method tests/method
git commit -m "feat: add the method pack format with its completeness gates"
```

---

### Task 5: The P6 driver tree and its diagnostics

**Files:**
- Create: `method/p6-metallurgist.yaml`
- Create: `method/sql/p6/liberation.sql`, `method/sql/p6/feed_variability.sql`, `method/sql/p6/bypass.sql`
- Create: `tests/method/test_p6_pack.py`

**Interfaces:**
- Consumes: `load_pack` from Task 4.
- Produces: the P6 pack at `method/p6-metallurgist.yaml`, loadable and with every `sql` path resolving and executing.

**Context — the finding this tree must be able to produce.** Verified against the live dataset during design, and the numbers below are the acceptance target:

- Recovery averages 92.21% against 93.77% in the tight-gap band the site itself ran.
- Closed-side setting correlates −0.66 with recovery and +0.53 with tailings grade.
- The effect holds in all three feed-grade terciles (+3.40, +4.00, +3.07 points), and corr(gap, feed grade) is −0.14, so it is not a feed-grade artefact.
- Throughput is flat across bands: 1,158 / 1,159 / 1,124 tph.
- Bypass has one interval in 167 days — no signal is possible, so its status is `unevidenced`.
- Reagent regime and grind size P80 have no data at all — status `not_instrumented`.

**Table access matters here.** `metallurgical_recovery` and `crusher_states` are both declared only by `S07`, `S07-SP3` and `S07-CRITIC`. `D21` and `D23` declare recovery alone; `D25` and `D26` declare crusher states alone. A diagnostic that joins the two therefore runs on `S07-SP3`, and `run_query` will refuse it anywhere else. Do not widen any agent's `source_tables` to work around this.

- [ ] **Step 1: Write the diagnostic SQL**

`method/sql/p6/liberation.sql` — the band comparison, parameterised:

```sql
WITH cs AS (
  SELECT DATE(timestamp) AS d, AVG(gap_size_setting_mm) AS gap,
         AVG(feed_rate_tph) AS tph, MAX(rotational_torque_nm) AS torque_max
  FROM `mining_data.crusher_states` GROUP BY d
),
m AS (
  SELECT DATE(timestamp) AS d, AVG(recovery_rate_pct) AS rec,
         AVG(tailings_grade_pct) AS tails, AVG(feed_grade_pct) AS feed
  FROM `mining_data.metallurgical_recovery` GROUP BY d
)
SELECT
  CASE WHEN gap <= @tight_max THEN 'tight'
       WHEN gap >= @wide_min  THEN 'wide'
       ELSE 'mid' END AS band,
  COUNT(*) AS days,
  ROUND(AVG(gap), 1)    AS gap_mm,
  ROUND(AVG(rec), 2)    AS recovery_pct,
  ROUND(AVG(tails), 4)  AS tailings_pct,
  ROUND(AVG(feed), 3)   AS feed_pct,
  ROUND(AVG(tph), 0)    AS throughput_tph,
  ROUND(MAX(torque_max), 0) AS torque_max_nm
FROM m JOIN cs USING (d)
GROUP BY band
ORDER BY gap_mm
```

`method/sql/p6/feed_variability.sql` — the confound control, stratified:

```sql
WITH cs AS (
  SELECT DATE(timestamp) AS d, AVG(gap_size_setting_mm) AS gap
  FROM `mining_data.crusher_states` GROUP BY d
),
m AS (
  SELECT DATE(timestamp) AS d, AVG(recovery_rate_pct) AS rec,
         AVG(feed_grade_pct) AS feed
  FROM `mining_data.metallurgical_recovery` GROUP BY d
),
j AS (
  SELECT m.d, m.rec, m.feed, cs.gap,
         NTILE(3) OVER (ORDER BY m.feed) AS feed_tercile
  FROM m JOIN cs USING (d)
)
SELECT
  feed_tercile,
  ROUND(MIN(feed), 3) AS feed_lo,
  ROUND(MAX(feed), 3) AS feed_hi,
  COUNTIF(gap <= @tight_max) AS tight_days,
  ROUND(AVG(IF(gap <= @tight_max, rec, NULL)), 2) AS recovery_tight,
  COUNTIF(gap >= @wide_min) AS wide_days,
  ROUND(AVG(IF(gap >= @wide_min, rec, NULL)), 2) AS recovery_wide
FROM j
GROUP BY feed_tercile
ORDER BY feed_tercile
```

`method/sql/p6/bypass.sql` — the driver that has no signal, which must still be asked:

```sql
SELECT
  COUNTIF(bypass_valve_open) AS bypass_intervals,
  COUNT(*)                   AS intervals,
  COUNT(DISTINCT DATE(timestamp)) AS days
FROM `mining_data.crusher_states`
```

- [ ] **Step 2: Write the pack**

`method/p6-metallurgist.yaml`:

```yaml
# The Metallurgist's driver tree. Skeleton only: no resolution prose lives
# here. Resolution content is retrieved from the document corpus so that a
# recommendation is the site's own standard rather than ours.
metric: unit cost per tonne of contained metal
root: contained metal lost to tailings

drivers:
  - id: liberation
    question: Is the crusher closed-side setting costing recovery?
    status: evidenced
    controllable: true
    compare: setting_band
    sql: sql/p6/liberation.sql
    params:
      tight_max: 117
      wide_min: 123
    doc_query: crusher gap size aperture torque limit feed rate
    guard: >-
      Confirm throughput neutrality across bands and torque headroom under the
      documented critical alarm before recommending any setting change.

  - id: feed_variability
    question: Does feed grade explain the recovery gap instead of the setting?
    status: evidenced
    controllable: false
    compare: setting_band
    sql: sql/p6/feed_variability.sql
    params:
      tight_max: 117
      wide_min: 123
    doc_query: feed grade blending stockpile variability
    guard: >-
      The setting effect must hold within every feed-grade stratum. If it does
      not, the finding is a feed-grade artefact and must not be recommended.

  - id: bypass
    question: Are bypass events costing recovery?
    status: unevidenced
    controllable: true
    sql: sql/p6/bypass.sql
    doc_query: crusher bypass valve clog abnormal situation
    guard: >-
      Report the observed count. Too few events to support a conclusion is a
      finding; silence is not.

  - id: reagent_regime
    question: Is the reagent regime costing recovery?
    status: not_instrumented
    controllable: false

  - id: grind_size_p80
    question: Is grind size costing liberation?
    status: not_instrumented
    controllable: true
```

- [ ] **Step 3: Write the failing test**

`tests/method/test_p6_pack.py`:

```python
"""The shipped P6 pack, checked for structure and against the live data."""
from pathlib import Path

import pytest

from mining_agents.method.pack import load_pack
from mining_agents.tools.bq_query import assert_no_interpolation, run_query

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "method" / "p6-metallurgist.yaml"
BOTH = ["mining_data.metallurgical_recovery", "mining_data.crusher_states"]


def test_the_shipped_pack_loads():
    pack = load_pack(PACK)
    assert pack.metric == "unit cost per tonne of contained metal"
    assert {d.id for d in pack.drivers} == {
        "liberation", "feed_variability", "bypass",
        "reagent_regime", "grind_size_p80",
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
    # Dropping them would let the answer imply the tree was fully explored.
    statuses = {d.id: d.status for d in load_pack(PACK).drivers}
    assert statuses["reagent_regime"] == "not_instrumented"
    assert statuses["grind_size_p80"] == "not_instrumented"
    assert statuses["bypass"] == "unevidenced"


@pytest.mark.integration
def test_the_liberation_diagnostic_reproduces_the_design_finding():
    driver = next(d for d in load_pack(PACK).drivers if d.id == "liberation")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, BOTH
    )
    bands = {r["band"]: r for r in rows}
    assert set(bands) == {"tight", "mid", "wide"}
    # Recovery falls monotonically as the gap opens.
    assert bands["tight"]["recovery_pct"] > bands["mid"]["recovery_pct"]
    assert bands["mid"]["recovery_pct"] > bands["wide"]["recovery_pct"]
    # Throughput does not improve when the gap opens — this is what kills the
    # "but you will lose tonnes" objection, so it is a gate.
    assert bands["wide"]["throughput_tph"] <= bands["tight"]["throughput_tph"]
    # Torque stays under the documented 4500 Nm critical alarm in every band.
    assert max(b["torque_max_nm"] for b in bands.values()) < 4500


@pytest.mark.integration
def test_the_setting_effect_survives_the_feed_grade_control():
    driver = next(d for d in load_pack(PACK).drivers if d.id == "feed_variability")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params, BOTH
    )
    assert len(rows) == 3
    for row in rows:
        assert row["recovery_tight"] > row["recovery_wide"], (
            f"tercile {row['feed_tercile']} does not hold; the finding would "
            "be a feed-grade artefact"
        )
```

- [ ] **Step 4: Run it and watch it fail, then pass**

Run: `PYTHONPATH=. python3 -m pytest tests/method/test_p6_pack.py -v`
Expected before Steps 1–2 exist: FAIL on the missing pack. After: PASS, 6 tests.

- [ ] **Step 5: Commit**

```bash
git add method tests/method/test_p6_pack.py
git commit -m "feat: add the P6 driver tree with its diagnostics"
```

---

### Task 6: The `method_lookup` tool

**Files:**
- Create: `mining_agents/tools/method_lookup.py`
- Create: `tests/tools/test_method_lookup.py`

**Interfaces:**
- Consumes: `load_pack` from Task 4; the P6 pack from Task 5.
- Produces: `make_method_lookup(persona: str)` returning a `method_lookup()` tool whose envelope `data` is `{"metric": str, "root": str, "drivers": [ ... ]}` with each driver carrying `id`, `question`, `status`, `controllable`, `guard`, `doc_query`.

**Context:** Every other tool declares tables it reads. This one reads no site data at all — it returns method. The `@tool` decorator refuses an empty `tables_read`, so this tool cannot use it: build the envelope through `ok()` from `mining_agents.envelope` directly, with `tables_read=[]` and `rows_scanned=0`, and say why in the docstring.

The signatures in `mining_agents/envelope.py` are `ok(data: dict, tables_read: list[str], rows_scanned: int = 0) -> dict` and `fail(code: str, message: str, details: dict, tables_read: list[str]) -> dict`. Neither refuses an empty `tables_read` — this is read, not assumed. Do not invent a placeholder table name; a fake provenance entry is worse than a missing one.

The tool does **not** return the SQL. The agent asks for a diagnostic by driver id and the runtime supplies it; exposing raw SQL to the model invites it to edit the method.

- [ ] **Step 1: Write the failing test**

`tests/tools/test_method_lookup.py`:

```python
from mining_agents.tools.method_lookup import make_method_lookup


def test_p6_returns_its_metric_and_every_driver():
    said = make_method_lookup("P6")()
    assert said["success"], said.get("error")
    data = said["data"]
    assert data["metric"] == "unit cost per tonne of contained metal"
    assert len(data["drivers"]) == 5


def test_uninstrumented_drivers_are_returned_not_filtered():
    # The agent must be able to say a driver was not instrumented. Filtering
    # them here would make that impossible and the answer would imply the
    # tree was fully explored.
    drivers = make_method_lookup("P6")()["data"]["drivers"]
    assert {d["status"] for d in drivers} == {
        "evidenced", "unevidenced", "not_instrumented"
    }


def test_the_sql_is_not_exposed_to_the_model():
    for driver in make_method_lookup("P6")()["data"]["drivers"]:
        assert "sql" not in driver, "exposing SQL invites the model to edit the method"


def test_a_persona_with_no_pack_fails_honestly():
    said = make_method_lookup("P4")()
    assert said["success"] is False
    assert said["error"]["code"] == "NO_METHOD_PACK"


def test_the_tool_reads_no_site_data():
    said = make_method_lookup("P6")()
    assert said["meta"]["tables_read"] == []
    assert said["meta"]["rows_scanned"] == 0
```

- [ ] **Step 2: Run it and watch it fail**

Run: `PYTHONPATH=. python3 -m pytest tests/tools/test_method_lookup.py -v`
Expected: FAIL, `ModuleNotFoundError`

- [ ] **Step 3: Write the tool**

`mining_agents/tools/method_lookup.py`:

```python
"""Return the driver tree for a persona's governing metric.

This tool reads no site data, so it does not use the @tool decorator: that
decorator refuses an empty tables_read, correctly, because a tool that reads
BigQuery must declare what it read. This one returns METHOD, and naming a
table here would put a false entry in the provenance panel.

The SQL behind each driver is deliberately withheld. The agent asks for a
diagnostic by driver id; handing it the query text invites it to edit the
method it is supposed to be following.
"""
from __future__ import annotations

from pathlib import Path

from mining_agents.envelope import fail, ok
from mining_agents.method.pack import PackError, load_pack

PACK_DIR = Path(__file__).resolve().parents[2] / "method"

#: Only P6 has a pack. The others are sequenced in the spec, and a persona
#: without one must fail loudly rather than return an empty tree.
PACKS = {"P6": "p6-metallurgist.yaml"}


def make_method_lookup(persona: str):
    """Build a method_lookup tool bound to one persona's pack."""

    def method_lookup():
        """Return the governing metric and the ordered driver tree."""
        name = PACKS.get(persona)
        if name is None:
            return fail(
                "NO_METHOD_PACK",
                f"no method pack exists for persona {persona}",
                {"persona": persona},
                [],
            )
        try:
            pack = load_pack(PACK_DIR / name)
        except (OSError, PackError) as exc:
            return fail("NO_METHOD_PACK", str(exc), {"persona": persona}, [])
        return ok(
            {
                "metric": pack.metric,
                "root": pack.root,
                "drivers": [
                    {
                        "id": d.id,
                        "question": d.question,
                        "status": d.status,
                        "controllable": d.controllable,
                        "guard": d.guard,
                        "doc_query": d.doc_query,
                    }
                    for d in pack.drivers
                ],
            },
            [],
            0,
        )

    return method_lookup
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `PYTHONPATH=. python3 -m pytest tests/tools/test_method_lookup.py -v`
Expected: PASS, 5 tests

- [ ] **Step 5: Commit**

```bash
git add mining_agents/tools/method_lookup.py tests/tools/test_method_lookup.py
git commit -m "feat: add method_lookup returning the persona driver tree"
```

---

### Task 7: The METHOD instruction block

**Files:**
- Modify: `mining_agents/patterns/deep.py` — `bind_tools` and `build_instruction`
- Modify: `mining_agents/catalog/definitions.py` — the `S07` swarm
- Create: `tests/patterns/test_method_instruction.py`

**Interfaces:**
- Consumes: `make_method_lookup` from Task 6, `doc_search` from Task 3.
- Produces: `bind_tools` resolves `"method_lookup"` and `"doc_search"`; `build_instruction` emits a METHOD block when `"method_lookup"` is in `agent.tools`; `S07-SP3` holds `["bq_query", "method_lookup", "doc_search"]` and `S07-CRITIC` holds `["bq_query", "operational_math", "doc_search"]`.

The catalogue edit lives in this task rather than the next one because the instruction tests read real agents out of `ALL_AGENTS`. Splitting them would make each half untestable on its own. It does not break the JS vocabulary gate, because that gate reads the generated `apps/shared/data/bundle.js`, which Task 8 rebuilds.

**Context:** `build_instruction` composes every Pattern B prompt, and today every clause governs retrieval or honesty — data scope, citation, tool failure, never-invent. Nothing asks the agent to diagnose. `agent.value_branch` is interpolated as a decorative string. This task is the change the whole redesign turns on.

Existing clauses are conditional on the agent's tools (`if "operational_math" in agent.tools:`). Follow that pattern exactly — naming a tool an agent does not hold invites a call that cannot resolve.

- [ ] **Step 1: Write the failing test**

`tests/patterns/test_method_instruction.py`:

```python
from mining_agents.catalog.definitions import ALL_AGENTS
from mining_agents.patterns.deep import bind_tools, build_instruction

BY_ID = {a.agent_id: a for a in ALL_AGENTS}


def test_an_agent_with_a_pack_is_told_to_work_the_tree():
    said = build_instruction(BY_ID["S07-SP3"])
    assert "METHOD" in said
    assert "method_lookup" in said
    # The five steps that separate a diagnosis from a retrieval.
    for step in ("size", "attribute", "controllable", "why", "guard"):
        assert step in said.lower(), f"the {step!r} step is missing"


def test_the_agent_is_told_not_to_drop_a_driver():
    said = build_instruction(BY_ID["S07-SP3"])
    assert "unevidenced" in said.lower()


def test_the_agent_is_told_to_retrieve_the_constraint_before_recommending():
    said = build_instruction(BY_ID["S07-SP3"])
    assert "doc_search" in said
    assert "before" in said.lower()


def test_an_agent_without_the_tool_gets_no_method_block():
    # Naming a tool an agent does not hold invites a call that cannot resolve.
    said = build_instruction(BY_ID["D22"])
    assert "METHOD" not in said


def test_both_new_tools_bind():
    bound = bind_tools(BY_ID["S07-SP3"])
    assert len(bound) == len(BY_ID["S07-SP3"].tools)
```

- [ ] **Step 2: Run it and watch it fail**

Run: `PYTHONPATH=. python3 -m pytest tests/patterns/test_method_instruction.py -v`
Expected: FAIL — `METHOD` is not in the instruction.

- [ ] **Step 3: Give the P6 agents the tools**

In `mining_agents/catalog/definitions.py`, in the `S07` swarm, change only the two `tools=` lists.

`S07-SP3` is the one agent that declares both `metallurgical_recovery` and `crusher_states`, so it is the only place the joined diagnostics can run:

```python
        _a("S07-SP3", "Recovery Sensitivity Modeller", "S07", "specialist",
           apqc="4.2.2 / 11.0.3", persona="P6", branch="processing",
           tables=["mining_data.metallurgical_recovery", "mining_data.crusher_states"],
           tools=["bq_query", "method_lookup", "doc_search"]),
```

`S07-CRITIC` is the guard, and needs `doc_search` to read the operating envelope it is guarding against:

```python
    critic=_a(
        "S07-CRITIC", "Setpoint Safety Critic", "S07", "critic",
        apqc="4.2.2 / 11.0.3", persona="P6", branch="processing",
        tables=["mining_data.crusher_states", "mining_data.metallurgical_recovery"],
        tools=["bq_query", "operational_math", "doc_search"],
    ),
```

Do not change any `tables` list. Widening `source_tables` to make a query work would defeat the declared-table control.

- [ ] **Step 4: Add the tool builders**

In `mining_agents/patterns/deep.py`, add the imports:

```python
from mining_agents.tools.doc_search import doc_search
from mining_agents.tools.method_lookup import make_method_lookup
```

and extend the `builders` dict inside `bind_tools`:

```python
        "doc_search": lambda: doc_search,
        "method_lookup": lambda: make_method_lookup(agent.persona),
```

- [ ] **Step 5: Add the METHOD block**

In `build_instruction`, after the `if "bq_query" in agent.tools:` block, insert:

```python
    if "method_lookup" in agent.tools:
        parts += [
            "",
            "METHOD — you are not a query service. Before answering a question "
            "about your governing metric, call method_lookup and work the "
            "driver tree it returns, in order:",
            "  1. SIZE the gap — the metric now, against a band the site has "
            "itself run. Never against the best decile of an outcome; the top "
            "decile of a noisy series is partly luck and overstates the prize.",
            "  2. ATTRIBUTE the loss — where the value is physically going.",
            "  3. Separate CONTROLLABLE drivers from ones you cannot change. An "
            "orebody is not a lever.",
            "  4. Ask WHY it is not already happening. The obvious lever is "
            "usually un-pulled for a reason, and a recommendation that cannot "
            "answer this is naive advice. Look for the decision in the data.",
            "  5. GUARD it — retrieve the operating constraint with doc_search "
            "BEFORE you recommend anything, cite the document, and show from "
            "the data that this site stays inside it.",
            "",
            "Rank problems by what they cost the metric, not by how "
            "interesting they are.",
            "A driver you cannot evidence is reported as unevidenced, and one "
            "with no data behind it is reported as not instrumented. Never drop "
            "a driver from your answer — a missing driver reads as 'no problem "
            "found', which is a different and false claim.",
        ]
```

- [ ] **Step 6: Run the tests and watch them pass**

Run: `PYTHONPATH=. python3 -m pytest tests/patterns/test_method_instruction.py tests/patterns/test_deep.py tests/catalog -v`
Expected: PASS. The existing pattern and catalogue suites are included because this task edits the two files they cover.

- [ ] **Step 7: Commit**

```bash
git add mining_agents/patterns/deep.py mining_agents/catalog/definitions.py tests/patterns/test_method_instruction.py
git commit -m "feat: instruct P6 agents to work the driver tree"
```

---

### Task 8: Say the two new tools in the reader's language

**Files:**
- Modify: `apps/shared/plain.js` — three tool-name maps
- Modify: `tests/js/plain.test.js`
- Regenerate: `apps/shared/data/*.json` and `apps/shared/data/bundle.js`

**Interfaces:**
- Consumes: the tool names `method_lookup` and `doc_search`, which Task 7 put on `S07-SP3` and `S07-CRITIC`.
- Produces: `callLine` and `failLine` render both tools without leaking an identifier; `unmapped()` stays empty against the rebuilt bundle.

**Context — the three maps, and the two to leave alone.** `plain.js` is the single source of reader-facing vocabulary. A tool missing from it surfaces its raw name in the activity log, which is the defect class this file exists to prevent. Three maps are keyed by tool name and all three need an entry:

- `TOOLS` (line ~14) — the gerund noun phrase used in prose: `bq_query: "looking up records"`.
- `TOOL_DOING` (line ~24) — the capitalised present participle the activity log prints: `"Looking up records"`. `callLine` falls back to this.
- `TOOL_ABILITY` (line ~34) — the bare verb after a modal: `"look up records"`.

**Do not add either tool to `TOOL_VERB` or `TOOL_FAILED`.** Those maps are consulted only when `_noun()` finds a table or a traversal in the call's arguments, and `_noun()` inspects SQL (for `bq_query`) and traversal ids only. Neither new tool supplies either, so entries there would be unreachable. `failLine` already falls back to `"Couldn't finish " + TOOLS[name]`, which reads correctly.

The exported helpers are `callLine(name, args)` and `failLine(name, args)` — there is no `stepLine`. Read the `module.exports` block at the foot of the file rather than assuming a name.

**Why the bundle is rebuilt here.** `tests/js/plain.test.js` already asserts `unmapped(loadData())` is empty, and `loadData()` parses the generated `apps/shared/data/bundle.js`. Task 7 added two tool names to `ALL_AGENTS`; the bundle is how the JS side learns about them, and `unmapped` will not actually exercise the new names until it is regenerated.

- [ ] **Step 1: Write the failing JS test**

Append to `tests/js/plain.test.js`:

```javascript
test("the two method tools are said in the reader's language", () => {
  for (const name of ["method_lookup", "doc_search"]) {
    const said = P.callLine(name, { query: "crusher gap size" });
    assert.ok(!said.includes(name), `the raw tool name reached the reader: ${said}`);
    assert.ok(said.length > 0, `${name} has no plain phrase`);
    const failed = P.failLine(name, { query: "crusher gap size" });
    assert.ok(!failed.includes(name), `the raw tool name reached the reader: ${failed}`);
  }
});

test("the two method tools have a gerund and a bare-verb phrase too", () => {
  for (const name of ["method_lookup", "doc_search"]) {
    assert.notEqual(P.plainTool(name), name, `${name} is missing from TOOLS`);
    assert.notEqual(P.plainToolAbility(name), name, `${name} is missing from TOOL_ABILITY`);
  }
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `node --test 'tests/js/*.test.js'`
Expected: FAIL — the raw tool name reaches the reader.

- [ ] **Step 3: Add the vocabulary**

In `apps/shared/plain.js`, add one line per tool to each of the three maps, keeping each map's existing ordering and style.

To `TOOLS`:

```javascript
  doc_search: "reading the manuals",
  method_lookup: "checking how this is diagnosed",
```

To `TOOL_DOING`:

```javascript
  doc_search: "Reading the manuals",
  method_lookup: "Checking how this is diagnosed",
```

To `TOOL_ABILITY`:

```javascript
  doc_search: "read the manuals",
  method_lookup: "check how this is diagnosed",
```

- [ ] **Step 4: Rebuild the bundle**

The generator is `scripts/build_app_data.py`. It reads `ALL_AGENTS` directly, so it picks up Task 7's change with no other step. (`scripts/build_workspace_data.py` also exists but is imported by that one, never run on its own — its own docstring says so.)

Run: `PYTHONPATH=. python3 scripts/build_app_data.py`
Expected: a `wrote apps/shared/data/…` line per payload, ending with `bundle.js`.

Confirm the new names reached it:

Run: `node -e "const t=require('fs').readFileSync('apps/shared/data/bundle.js','utf8'); console.log(t.includes('method_lookup'), t.includes('doc_search'))"`
Expected: `true true`

Do not hand-edit the bundle. It is generated and carries a "Do not edit" banner.

- [ ] **Step 5: Run every gate**

Run: `node --test 'tests/js/*.test.js'`
Expected: PASS, no failures. The `unmapped` test is the one proving the maps and the rebuilt bundle agree.

Run: `PYTHONPATH=. python3 -m pytest -q -m "not integration"`
Expected: PASS. `tests/test_screen_copy.py` and `tests/test_runtime_honesty.py` both read the bundle, so they are the ones most likely to react to the rebuild.

- [ ] **Step 6: Commit**

```bash
git add apps/shared/plain.js apps/shared/data tests/js/plain.test.js
git commit -m "feat: say the method tools in the reader's language"
```

---

### Task 9: Verify live, in a browser

**Files:**
- Modify: `docs/agent-tool-defects.md` — add the metadata defect

**Context:** Every static gate in this repository reads source. None can see a sentence a model writes at runtime, which is how the last two defects in this area were found. A passing suite is not evidence that this worked.

The workspace is served by `scripts/proxy_workspace.py` at `/workspace/persona.html` — note the path, it is not `/apps/workspace/...`. Deploy with:

```
PYTHONPATH=. python -c "from scripts.deploy_apps import apply, CONFIRM_PHRASE; apply(dry_run=False, allow_unauthenticated=False, confirm=CONFIRM_PHRASE)"
```

- [ ] **Step 1: Publish the catalogue and deploy**

Publish the definitions so `mining_data.agent_catalog` matches them — `mining_agents/catalog/loader.py` exposes `upsert_catalog()` and runs as a module:

```
PYTHONPATH=. python3 -m mining_agents.catalog.loader
```

Expected: `loaded <N> agents into agent_catalog`.

Then redeploy the P6 agents and the workspace with the `deploy_apps` verb quoted above.

- [ ] **Step 2: Ask P6 the governing question in a browser**

Open the workspace on the P6 role page and ask: *"Our unit cost per tonne of contained metal is drifting. What are the top problems and how do I fix them?"*

- [ ] **Step 3: Check the answer against the design finding**

The answer must contain, in the reader's language:

- The recovery gap, sized against a setting band the site has run.
- The closed-side setting named as the controllable driver.
- The feed-grade control, showing the effect is not a feed-grade artefact.
- Why it is not already happening — the wide-gap campaign chased throughput and did not get it.
- The operating constraint, **cited to the crusher manual**, with the torque limit.
- The throughput-neutrality and torque-headroom guard.
- `bypass` reported as unevidenced, and `reagent_regime` and `grind_size_p80` reported as not instrumented — **none of them silently absent**.

- [ ] **Step 4: Check the vocabulary gates hold at runtime**

No raw tool name, no `INVALID_ARGUMENT`-style constant, no qualified table id such as `mining_data.` in body copy. Machine strings belong in the collapsed technical drawer.

Say "contained metal". If the model names a metal, that is a finding to record, not something to fix by editing the answer.

- [ ] **Step 5: Record what actually happened**

Write down the answer verbatim. If a step of the method was skipped, or a driver was dropped, or a citation was missing, record it — including if the agent produced a worse answer than before. A redesign that does not survive live contact is a finding, not a failure to hide.

- [ ] **Step 6: Log the metadata defect**

Add to `docs/agent-tool-defects.md` a section recording that `mining_data.unstructured_docs_metadata` carries 50 rows whose `file_path` values all resolve to nothing (they name `oem-manuals/manual_N.pdf`; the real folder is `oem-equipment-manuals/` with names like `crusher_03_manual.pdf`), against 40 real objects, and that its `chunk_count` sums to 3,392 against a real corpus of roughly 38 chunks. Note that `ontology_lookup.py` already abandoned document linking for a related reason.

- [ ] **Step 7: Commit**

```bash
git add docs/agent-tool-defects.md
git commit -m "docs: record the unstructured_docs_metadata defect"
```

---

## Notes for whoever executes this

**Do not fix the three known tool defects** in `docs/agent-tool-defects.md` on the way past. They are a separate workstream.

**Do not widen any agent's `source_tables`.** If a diagnostic cannot run because an agent has not declared a table, the diagnostic belongs on a different agent.

**Do not relax `assert_no_interpolation` or the declared-table check.** Both are security controls; the first is documented as a lint but the second is load-bearing.

**If the method pack starts accumulating conclusions**, stop and say so. A skeleton that encodes the answer turns this into a precomputed report with a chat interface, which is the thing the redesign exists to replace.
