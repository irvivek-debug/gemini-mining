"""Parameterised BigQuery reads, constrained to each agent's declared tables.

The access control here is enforced by BigQuery, not by reading the SQL. Every
query is submitted twice: once with `dry_run=True` to ask BigQuery which tables
the statement actually resolves to, and again for real only if that set is a
subset of the caller's declared tables. Asking the engine that will run the
query is the point — a parser or a regex is a second opinion about what SQL
means, and the gap between the two opinions is the vulnerability.

Three checks, in order, all derived from the dry run:

  1. statement_type must be SELECT. This is what stops `EXECUTE IMMEDIATE` and
     multi-statement scripts, which BigQuery reports as SCRIPT with an EMPTY
     referenced_tables list — a subset check alone would pass them silently.
  2. referenced_tables must be non-empty. A read that resolves to no table is
     either a mistake or an evasion (EXTERNAL_QUERY, UNNEST-only construction),
     and it would make meta.tables_read a lie. Use operational_math to compute
     without reading.
  3. referenced_tables must be a subset of the declared tables.

Note for anyone routing agents through a masking view: BigQuery's dry run
expands a plain view to its BASE tables, so `SELECT * FROM v_fatigue_scored`
reports `biometric_fatigue_logs`. That is good — access cannot be laundered
through a view — but it means this control CANNOT distinguish "read the masked
view" from "read the raw table". Column-level masking has to be enforced
somewhere else.

`assert_no_interpolation` below is a lint, not a security control. See its
docstring.
"""
from __future__ import annotations

import datetime
import decimal
import re

from google.cloud import bigquery

from mining_agents.config import settings
from mining_agents.safety.output_filter import mask_rows
from mining_agents.safety.untrusted import wrap_rows
from mining_agents.tools.base import ToolFailure, tool

# A quoted literal or a bare number appearing on the right of a comparison or
# inside an IN list. Table names in backticks and @parameters are unaffected.
_LITERAL_PREDICATE = re.compile(
    r"""(?ix)
    (?: =\s*|<\s*|>\s*|<=\s*|>=\s*|!=\s*|<>\s*|\bLIKE\s+|\bIN\s*\(\s* )
    (?: '[^']*' | "[^"]*" | \d+(?:\.\d+)? )
    """
)

# The only statement type this tool will execute. Everything else — DML, DDL,
# and the SCRIPT type that covers EXECUTE IMMEDIATE — is refused.
READ_ONLY_STATEMENT_TYPES = frozenset({"SELECT"})

_client: bigquery.Client | None = None
_home_projects: frozenset[str] | None = None


class SqlInterpolationError(ToolFailure):
    def __init__(self, message: str, **details):
        super().__init__("SQL_INTERPOLATION", message, **details)


class UndeclaredTableError(ToolFailure):
    """The query resolves to a table the caller did not declare."""

    def __init__(self, message: str, **details):
        super().__init__("UNDECLARED_TABLE", message, **details)


def assert_no_interpolation(sql: str) -> None:
    """Flag a literal used where an @parameter belongs. A LINT, NOT A CONTROL.

    This catches the common careless case — `WHERE asset_id = 'PUMP-104A'` —
    and nothing more. It is trivially avoided by `STARTS_WITH(asset_id, ...)`,
    `CONCAT(...)`, `BETWEEN`, `REGEXP_CONTAINS(...)`, or by not filtering at
    all, and it says nothing whatever about which tables a query reads.

    Do not treat a passing call as evidence that SQL is safe. The control that
    actually constrains what a query can reach is
    assert_reads_only_declared_tables, which asks BigQuery rather than guessing.
    """
    match = _LITERAL_PREDICATE.search(sql)
    if match:
        raise SqlInterpolationError(
            "literal value in a predicate; use an @parameter instead",
            fragment=match.group(0).strip(),
        )


def _home_project_aliases() -> frozenset[str]:
    """Every spelling of "this project" that normalisation has to absorb.

    `settings().project_id` is whatever GOOGLE_CLOUD_PROJECT holds, and Agent
    Engine sets that variable to the project NUMBER, not the project id.
    BigQuery accepts the number when a job is submitted — it posts to
    `bigquery/v2/projects/<number>/jobs` quite happily — but it reports
    `referenced_tables` with the project ID. A prefix strip keyed on the
    number alone therefore strips nothing from the referenced side while the
    declared side is already short-form, so the subset check refuses every
    query an agent makes. That is not hypothetical: it is what the first live
    run did, raising UNDECLARED_TABLE naming the very table the agent declared.

    `SELECT @@project_id` resolves the id from the same engine that resolves
    `referenced_tables`, which is the move this whole module is built on — ask
    the thing that will run the query rather than deriving the answer. The
    result is cached for the process, and the probe scans zero bytes.
    """
    global _home_projects
    if _home_projects is None:
        rows = _bq_client().query("SELECT @@project_id AS project_id").result()
        resolved = next(iter(rows))["project_id"]
        _home_projects = frozenset({settings().project_id, resolved})
    return _home_projects


def _strip_home_project(name: str) -> str:
    """Reduce `<this project>.dataset.table` to `dataset.table`, leave the rest.

    Applied to BOTH sides of the subset check so the comparison is like for
    like. Stripping only our own project is what keeps a cross-project read
    refusable: `other-project.mining_data.assets` survives normalisation with
    its prefix intact and therefore matches no declaration, while a declaration
    written either way resolves to the same string as the query that reads it.

    A prefix strip is used rather than counting dotted parts because the part
    count is ambiguous: `mining_data.INFORMATION_SCHEMA.TABLES` has three.
    """
    for alias in _home_project_aliases():
        prefix = f"{alias}."
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def _table_name(ref) -> str:
    """Normalise a BigQuery TableReference to the form the catalog declares."""
    return _strip_home_project(f"{ref.project}.{ref.dataset_id}.{ref.table_id}")


def assert_reads_only_declared_tables(
    sql: str, params: dict, declared: list[str]
) -> list[str]:
    """Refuse any query that reaches beyond `declared`. Returns the tables read.

    Enforced by a BigQuery dry run — see the module docstring for why, and for
    what the three checks each stop. Dry runs are free and do not execute.
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[_to_param(k, v) for k, v in params.items()],
        dry_run=True,
        use_query_cache=False,
    )
    try:
        job = _bq_client().query(sql, job_config=job_config)
    except Exception as exc:  # noqa: BLE001 - boundary with BigQuery
        # A dry run rejects malformed SQL, unknown columns, and unknown tables.
        raise ToolFailure(
            "QUERY_FAILED", str(exc), tables_read=list(declared)
        ) from exc

    if job.statement_type not in READ_ONLY_STATEMENT_TYPES:
        raise UndeclaredTableError(
            f"only {sorted(READ_ONLY_STATEMENT_TYPES)} statements may run; "
            f"BigQuery resolved this to {job.statement_type}",
            statement_type=job.statement_type,
            tables_read=list(declared),
        )

    allowed = {_strip_home_project(t) for t in declared}
    referenced = sorted({_table_name(t) for t in (job.referenced_tables or [])})
    if not referenced:
        raise UndeclaredTableError(
            "query resolves to no table at all; a read tool must read a "
            "declared table. Use operational_math to compute without reading.",
            tables_read=list(declared),
        )

    undeclared = sorted(set(referenced) - allowed)
    if undeclared:
        raise UndeclaredTableError(
            f"query reads {undeclared}, which this agent has not declared",
            undeclared=undeclared,
            declared=sorted(allowed),
            tables_read=list(declared),
        )
    return referenced


def _bq_client() -> bigquery.Client:
    global _client
    if _client is None:
        s = settings()
        _client = bigquery.Client(project=s.project_id, location=s.location)
    return _client


def _to_param(name: str, value):
    if isinstance(value, (list, tuple)):
        element = value[0] if value else ""
        return bigquery.ArrayQueryParameter(name, _bq_type(element), list(value))
    return bigquery.ScalarQueryParameter(name, _bq_type(value), value)


def _bq_type(value) -> str:
    if isinstance(value, bool):
        return "BOOL"
    if isinstance(value, int):
        return "INT64"
    if isinstance(value, float):
        return "FLOAT64"
    return "STRING"


def _json_safe(value):
    """Coerce a BigQuery cell into something the model API can serialise.

    The client returns native Python objects — `datetime.date` for DATE,
    `decimal.Decimal` for NUMERIC, `bytes` for BYTES — and the tool response is
    ultimately JSON-encoded on its way to the model. Anything the encoder does
    not recognise raises TypeError from inside the SDK, which surfaces as a
    bare HTTP 500 with no indication that a column type was the cause.

    That is exactly how this was found: S01 answered one question and 500'd on
    the next, because the second query touched `assets.installation_date`. Only
    three DATE columns exist in this dataset, so the failure is invisible until
    a query happens to select one — a demo-day defect by construction.

    Temporal values become ISO-8601 strings; Decimal becomes a string rather
    than a float because NUMERIC is used for money and float would silently
    round it. Containers recurse: a query returning ARRAY<DATE> or a STRUCT is
    just as unserialisable as a bare DATE.
    """
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def run_query(sql: str, params: dict, tables_read: list[str]) -> tuple[list[dict], int]:
    """Execute parameterised SQL. Returns (rows, row_count). No envelope.

    Every caller passes through here — the agent-authored `bq_query` tool and
    the six tools whose SQL is written in this repo (`bqml_predict`,
    `doc_search`, `graph_traverse`, `ontology_lookup`, `request_approval` and
    `run_diagnostic`) — so this is the single place the declared-table
    constraint has to hold. Author-written SQL is checked too, deliberately: a
    tool whose SQL drifts away from the tables it declares is a provenance bug,
    and `meta.tables_read` should not be able to say one thing while the query
    does another.

    One qualification the bare count hid. This check compares a query against
    the list its caller passes in, so it is only a constraint on the AGENT when
    that list is the agent's declaration. `run_diagnostic` derives its list
    from the diagnostic's own SQL — that is what makes meta.tables_read honest
    there — and so checks the agent's grant itself before calling in.
    """
    assert_no_interpolation(sql)
    referenced = assert_reads_only_declared_tables(sql, params, tables_read)
    job_config = bigquery.QueryJobConfig(
        query_parameters=[_to_param(k, v) for k, v in params.items()],
        use_query_cache=False,
    )
    try:
        rows = [
            {k: _json_safe(v) for k, v in dict(r).items()}
            for r in _bq_client().query(sql, job_config=job_config).result()
        ]
    except Exception as exc:  # noqa: BLE001 - boundary with BigQuery
        raise ToolFailure(
            "QUERY_FAILED", str(exc), tables_read=list(tables_read)
        ) from exc
    # Masking and untrusted-text wrapping happen here, not in each tool, for
    # the same reason the declared-table check does: every path that returns
    # BigQuery rows to a model goes through this function. Both are keyed on
    # `referenced` — what the query actually read — not on what was declared.
    # row_count is taken before either, since neither adds or removes a row.
    return wrap_rows(mask_rows(rows), referenced), len(rows)


def make_bq_query(tables_read: list[str]):
    """Build an enveloped bq_query tool bound to the tables an agent may read."""

    @tool(tables_read)
    def bq_query(sql: str, params: dict | None = None):
        """Run a parameterised read against mining_data. Use @parameters only."""
        rows, scanned = run_query(sql, params or {}, tables_read)
        return {"rows": rows}, scanned

    return bq_query
