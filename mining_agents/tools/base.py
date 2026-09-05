"""The @tool decorator: the only place a tool envelope is constructed."""
from __future__ import annotations

import functools
import logging

from mining_agents.envelope import fail, ok

log = logging.getLogger(__name__)


class ToolFailure(Exception):
    """An expected failure. Becomes an RFC 7807 error envelope."""

    def __init__(self, code: str, message: str, **details):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


def tool(tables_read: list[str]):
    """Wrap a function returning (data, rows_scanned) into the SOP envelope.

    tables_read is declared at decoration time so that it is present even when
    the call fails before touching BigQuery.
    """
    if not tables_read:
        raise ValueError(
            "every tool must declare a non-empty tables_read; "
            "meta.tables_read feeds the UX provenance panel"
        )

    def decorate(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                # --- Phase 1: call the underlying tool function ---
                try:
                    data, rows_scanned = fn(*args, **kwargs)
                except ToolFailure as exc:
                    return fail(exc.code, exc.message, exc.details, tables_read)
                except Exception as exc:  # noqa: BLE001
                    # Deliberately catching Exception, not BaseException.
                    # KeyboardInterrupt, SystemExit, and GeneratorExit must
                    # propagate so that Ctrl-C and interpreter shutdown work
                    # normally. Swallowing them here would be a worse bug than
                    # a tool that crashes.
                    log.exception("unhandled error in tool %s", fn.__name__)
                    return fail("INTERNAL", str(exc), {"tool": fn.__name__}, tables_read)

                # --- Phase 2: construct the success envelope ---
                # This is outside the inner try so that a failure here (e.g.
                # ok() raising ValidationError because the tool returned a
                # non-dict or non-int) is caught by the outer try below.
                return ok(data, tables_read, rows_scanned)
            except Exception:
                # Envelope construction itself failed (ok() or fail() raised).
                # Do NOT call ok() or fail() here — they are what just failed.
                # Build the minimum valid Envelope dict by hand so the ADK
                # runtime always receives a structured response.
                log.exception("envelope construction failed in tool %s", fn.__name__)
                from mining_agents.envelope import _now  # local import avoids circularity risk
                return {
                    "success": False,
                    "data": {},
                    "error": {
                        "code": "ENVELOPE_ERROR",
                        "message": "envelope construction failed",
                        "details": {"tool": fn.__name__},
                    },
                    "meta": {
                        "timestamp": _now(),
                        "tables_read": list(tables_read),
                        "rows_scanned": 0,
                    },
                }

        wrapper.tables_read = list(tables_read)
        return wrapper

    return decorate

