"""ML.PREDICT over the allowlisted BQML models in mining_data.

The model name is a SQL identifier (not a bindable parameter), so it must be
validated against the explicit allowlist *before* it is interpolated into the
query string.  The allowlist is the only guard against identifier injection.
"""
from __future__ import annotations

import re
import subprocess

from mining_agents.config import settings
from mining_agents.tools.base import ToolFailure, tool
from mining_agents.tools.bq_query import run_query

# Matches a mining_data table reference inside backticks or bare, e.g.
# `mining_data.telemetry_stream` or mining_data.telemetry_stream
_TABLE_REF = re.compile(r"`?(?:[\w-]+\.)?(mining_data\.\w+)`?")


def list_models() -> list[str]:
    """Return the live BQML model IDs registered in mining_data."""
    s = settings()
    result = subprocess.run(
        [
            s.bq_binary,
            "ls",
            "--models",
            "--max_results=1000",
            f"{s.project_id}:{s.dataset}",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    names: list[str] = []
    for line in result.stdout.splitlines()[2:]:  # skip header and divider rows
        parts = line.split()
        if parts:
            names.append(parts[0])
    return names


def _referenced_tables(sql: str) -> list[str]:
    """Extract distinct mining_data table references from a SQL string."""
    return sorted(set(_TABLE_REF.findall(sql)))


def make_bqml_predict(allowed_models: list[str]):
    """Build an enveloped bqml_predict bound to the models an agent may call.

    The returned callable accepts (model, input_sql, params) and returns a
    standard tool envelope.  The model name is validated against the allowlist
    by exact match before it touches the SQL string.

    meta.tables_read always includes:
    - the model's fully qualified reference (mining_data.<model>)
    - every mining_data table referenced in input_sql (for provenance)
    """
    declared = [f"mining_data.{m}" for m in allowed_models]

    @tool(declared)
    def bqml_predict(model: str, input_sql: str, params: dict | None = None):
        """Run ML.PREDICT for one allowlisted model over parameterised input SQL."""
        # Validate model identity before it ever reaches the SQL string.
        if model not in allowed_models:
            raise ToolFailure(
                "MODEL_NOT_PERMITTED",
                f"this agent may predict with {sorted(allowed_models)}",
                requested=model,
            )
        s = settings()
        sql = (
            f"SELECT * FROM ML.PREDICT("
            f"MODEL `{s.project_id}.{s.dataset}.{model}`, ({input_sql}))"
        )
        tables = [f"mining_data.{model}", *_referenced_tables(input_sql)]
        rows, scanned = run_query(sql, params or {}, tables)
        return {"model": model, "rows": rows}, scanned

    # The @tool decorator fixes tables_read to `declared` at decoration time.
    # For a successful call we enrich meta.tables_read with the runtime input
    # tables so provenance tracks both the model and its input source.
    _decorated = bqml_predict

    def wrapper(model: str, input_sql: str, params: dict | None = None):
        env = _decorated(model, input_sql, params)
        if env["success"]:
            merged = sorted(
                set(env["meta"]["tables_read"]) | set(_referenced_tables(input_sql))
            )
            env["meta"]["tables_read"] = merged
        return env

    wrapper.tables_read = declared
    wrapper.__name__ = "bqml_predict"
    wrapper.__doc__ = _decorated.__doc__
    return wrapper
