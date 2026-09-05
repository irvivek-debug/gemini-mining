"""Every agent invocation writes exactly one agent_run_log row.

Schema (infra/ddl/agent_tables.sql):
  run_id        STRING NOT NULL
  agent_id      STRING NOT NULL
  parent_run_id STRING                     -- A2A lineage
  pattern       STRING NOT NULL            -- A | B  (derived from catalog)
  status        STRING NOT NULL            -- DONE | BLOCKED | ERROR
  blocked_reason STRING                    -- scrubbed via output_filter.scrub
  started_at    TIMESTAMP NOT NULL
  ended_at      TIMESTAMP
  tables_read   ARRAY<STRING>
  rows_scanned  INT64

Rules applied:
  - Ruling A: ended_at (not finished_at), blocked_reason (not error_message),
              no duration_ms (derivable from timestamps).
  - Ruling B: status vocabulary is DONE / BLOCKED / ERROR; no SUCCESS.
  - Ruling C: pattern is derived from mining_agents.catalog.definitions.ALL_AGENTS;
              an unknown agent_id raises ValueError before writing any row.
  - Ruling D: blocked_reason is passed through mining_agents.safety.output_filter.scrub
              before it is written.
  - Ruling E: RunRecord carries mutable rows_scanned (default 0), and
              logged_run / record_run accept an optional parent_run_id.
  - Ruling F: RunRecord.block(reason) marks status BLOCKED with a reason.
"""
from __future__ import annotations

import contextlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from google.cloud import bigquery

from mining_agents.catalog.definitions import ALL_AGENTS
from mining_agents.config import settings
from mining_agents.safety.output_filter import scrub

TABLE = "mining_data.agent_run_log"

# Fast-lookup index: agent_id -> pattern letter
_CATALOG: dict[str, str] = {a.agent_id: a.pattern for a in ALL_AGENTS}

_client: bigquery.Client | None = None


def _bq() -> bigquery.Client:
    global _client
    if _client is None:
        s = settings()
        _client = bigquery.Client(project=s.project_id, location=s.location)
    return _client


def _pattern_for(agent_id: str) -> str:
    """Return the catalog pattern (A|B) for agent_id, or raise ValueError."""
    try:
        return _CATALOG[agent_id]
    except KeyError:
        raise ValueError(
            f"agent_id {agent_id!r} is not in the catalog; "
            "every run log row must be attributable to a real catalogued agent"
        )


@dataclass
class RunRecord:
    """Mutable state accumulated during a single agent invocation."""

    agent_id: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tables_read: list[str] = field(default_factory=list)
    rows_scanned: int = 0
    _status: str = field(default="DONE", init=False, repr=False)
    _blocked_reason: str | None = field(default=None, init=False, repr=False)

    def block(self, reason: str) -> None:
        """Mark this run as BLOCKED with a reason (not an unhandled exception)."""
        self._status = "BLOCKED"
        self._blocked_reason = reason


def record_run(
    agent_id: str,
    status: str,
    *,
    tables_read: list[str],
    run_id: str | None = None,
    parent_run_id: str | None = None,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
    blocked_reason: str | None = None,
    rows_scanned: int = 0,
) -> str:
    """Write one run-log row and return the run_id.

    blocked_reason is scrubbed before it is stored.
    Raises ValueError if agent_id is not in the catalog.
    """
    pattern = _pattern_for(agent_id)  # raises ValueError for unknown ids
    run_id = run_id or str(uuid.uuid4())
    started = started_at or datetime.now(timezone.utc)
    ended = ended_at or datetime.now(timezone.utc)

    row: dict = {
        "run_id": run_id,
        "agent_id": agent_id,
        "pattern": pattern,
        "status": status,
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "tables_read": list(tables_read),
        "rows_scanned": rows_scanned,
    }
    if parent_run_id is not None:
        row["parent_run_id"] = parent_run_id
    if blocked_reason is not None:
        row["blocked_reason"] = scrub(blocked_reason)

    s = settings()
    errors = _bq().insert_rows_json(
        f"{s.project_id}.{s.dataset}.agent_run_log", [row]
    )
    if errors:
        raise RuntimeError(f"agent_run_log insert rejected: {errors}")
    return run_id


@contextlib.contextmanager
def logged_run(agent_id: str, *, parent_run_id: str | None = None):
    """Context manager that times an invocation and logs it exactly once.

    Yields a RunRecord so the caller can set tables_read, rows_scanned, and
    call .block(reason) to mark the run as BLOCKED.

    On an unhandled exception the status is ERROR and the exception message
    is stored as the (scrubbed) blocked_reason; the exception is re-raised.

    Ruling C: raises ValueError immediately if agent_id is not in the catalog.
    """
    # Validate catalog membership before yielding (Ruling C).
    _pattern_for(agent_id)  # raises ValueError for unknown ids

    record = RunRecord(agent_id=agent_id)
    started = datetime.now(timezone.utc)
    try:
        yield record
    except Exception as exc:
        record_run(
            agent_id,
            "ERROR",
            run_id=record.run_id,
            parent_run_id=parent_run_id,
            tables_read=record.tables_read,
            rows_scanned=record.rows_scanned,
            started_at=started,
            blocked_reason=str(exc),
        )
        raise

    record_run(
        agent_id,
        record._status,
        run_id=record.run_id,
        parent_run_id=parent_run_id,
        tables_read=record.tables_read,
        rows_scanned=record.rows_scanned,
        started_at=started,
        blocked_reason=record._blocked_reason,
    )
