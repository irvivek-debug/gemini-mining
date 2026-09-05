"""Execute a driver's fixed query, returning the diagnostic result.

`method_lookup` hands the agent its driver tree but withholds each driver's
SQL, on the reasoning that a model handed a query will paraphrase or mutate the
diagnostic.  `run_diagnostic` closes the loop: the agent names a driver by id,
the runtime resolves the SQL, runs it under the declared-table constraint, and
returns the result.  The diagnostic that ships is the diagnostic that runs, and
`method/sql/p6/*.sql` is executed in production rather than only in tests.

Why not `@tool`?  `@tool` fixes `tables_read` at decoration time, but the
tables this tool reads depend on which driver is asked for.  The alternative —
declaring all tables from all drivers at decoration — would widen access to
every query in the pack regardless of which driver the agent named, defeating
the declared-table constraint that the provenance panel relies on.  Instead,
the tables are derived from the SQL text at call time via `_TABLE_REF`, passed
to `run_query` directly, and returned in `meta.tables_read` so the panel shows
the real sources.  If `_TABLE_REF` under-extracts, the BigQuery dry run fails
loudly rather than silently widening access — BigQuery is the control.

That derivation is why the tool ALSO takes the agent's own `source_tables` and
refuses any driver that reaches past them.  `run_query`'s declared-table check
compares the query against the list handed to it, so a list derived from that
same query satisfies itself: on this path alone, the check proves nothing about
what the agent was granted.  No shipped diagnostic reaches past its agent today
— but a pack that added one over `biometric_fatigue_logs` would obtain the rows
AND bypass the BIOMETRIC instruction section, which keys on `source_tables`,
with no test failing.  A driver that does not fit its agent is a finding for
the pack author; widening the agent to accommodate it hands that agent every
other query in the same reach.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from mining_agents.envelope import fail, ok
from mining_agents.tools.bq_query import run_query
from mining_agents.tools.method_lookup import PACK_DIR, PACKS, load_pack

# Matches `mining_data.<name>` references inside backticks, following the same
# pattern as bqml_predict._TABLE_REF.  The regex is a declaration, not a
# security control; the dry run is the control.
_TABLE_REF = re.compile(r"`?(?:[\w-]+\.)?(mining_data\.\w+)`?")

LOG = logging.getLogger(__name__)


def _referenced_tables(sql: str) -> list[str]:
    """Extract distinct mining_data table references from a SQL string."""
    return sorted(set(_TABLE_REF.findall(sql)))


def _declared_tables(tables) -> set[str]:
    """Normalise declared names to the form `_referenced_tables` yields.

    The catalog writes `mining_data.crusher_states`, and the same regex absorbs
    a project prefix on either side, so a declaration written either way
    compares like for like against the query.  A name the regex does not
    recognise is kept verbatim rather than dropped: a declaration this function
    could not read must still be able to authorise the table it names.
    """
    out: set[str] = set()
    for name in tables or ():
        out.update(_TABLE_REF.findall(name) or [name])
    return out


def make_run_diagnostic(persona: str, source_tables: list[str]):
    """Build a run_diagnostic tool bound to one persona's pack.

    `source_tables` is the holding agent's own declaration.  It is required,
    not optional: a default would let a fork bind the tool without saying what
    the agent may read, and the failure of that omission is silent.
    """

    def run_diagnostic(driver_id: str):
        """Execute the fixed diagnostic query for a named driver.

        Returns the result rows, the driver's status, and the guard that
        fences any recommendation.  Never returns the SQL text or file path.
        """
        name = PACKS.get(persona)
        if name is None:
            return fail(
                "NO_METHOD_PACK",
                f"no method pack exists for persona {persona!r}",
                {"persona": persona},
                [],
            )
        try:
            pack = load_pack(PACK_DIR / name)
        except Exception:  # noqa: BLE001 — must never propagate as a traceback
            return fail(
                "NO_METHOD_PACK",
                f"method pack for persona {persona!r} could not be loaded",
                {"persona": persona, "pack_file": name},
                [],
            )

        driver_by_id = {d.id: d for d in pack.drivers}
        if driver_id not in driver_by_id:
            valid = sorted(driver_by_id.keys())
            return fail(
                "NO_SUCH_DRIVER",
                f"driver {driver_id!r} does not exist; valid ids are {valid}",
                {"requested": driver_id, "valid_ids": valid},
                [],
            )

        driver = driver_by_id[driver_id]
        if not driver.sql:
            # A driver with no diagnostic is a SUCCESSFUL call, not a failure.
            # The tool did exactly what it was asked: it looked up the driver
            # and reported, truthfully, that the method has no query for it.
            # Nothing errored.
            #
            # This used to be `fail("DRIVER_NOT_INSTRUMENTED", ...)`. That was
            # wrong: the workspace UI renders every success:false identically,
            # so a real run rendered "that lookup failed" in the activity log
            # for a driver the pack deliberately DECLARES rather than drops
            # (see tests/method/test_p6_pack.py::
            # test_the_uninstrumented_drivers_are_declared_not_omitted). Worse,
            # an agent reading success:false has every reason to drop the
            # driver from its answer rather than report the gap — the inverse
            # of what the pack means, and it defeats the declared-not-omitted
            # mechanism from the tool's own output.
            #
            # The payload shape below matches the instrumented path on purpose
            # — driver, status, guard, rows — so a caller branches on `status`
            # rather than on the presence of an error. `rows` is `[]` because
            # no query ran, not because one ran and found nothing; `guard` is
            # whatever the pack declares for this driver (never set for a
            # not_instrumented one today, but nothing here assumes that).
            # `question` and `note` carry the two things the agent needs to
            # report the gap instead of silently omitting the driver.
            return ok(
                {
                    "driver": driver_id,
                    "status": driver.status,
                    "guard": driver.guard,
                    "rows": [],
                    "question": driver.question,
                    "note": (
                        f"Driver {driver_id!r} exists in the method pack but "
                        "no diagnostic query covers it yet. This is a "
                        "declared gap, not an error: report this driver as "
                        "part of the tree with no diagnostic behind it. Do "
                        "not omit it, and do not report this call as "
                        "unsuccessful — it succeeded."
                    ),
                },
                [],
                0,
            )

        try:
            sql = (PACK_DIR / driver.sql).read_text()
        except OSError as exc:  # noqa: BLE001 — boundary with the filesystem
            # The pack YAML and its SQL are two trees, and they can ship apart:
            # `method/` was once missing from SHARED_TREES entirely, and a
            # packaging ignore pattern could still drop `*.sql` while leaving
            # the YAML in place. In that layout every driver resolves and every
            # read raises, so an unguarded read_text puts a FileNotFoundError
            # into the ADK runtime rather than into the agent's hands — which
            # bypasses every structured-error path the instruction teaches it
            # to report. The path is deliberately not in the failure: it would
            # hand back the location method_lookup withholds.
            LOG.exception(
                "diagnostic %s could not be read for persona %s", driver_id, persona
            )
            return fail(
                "QUERY_FAILED",
                f"the {driver_id!r} diagnostic could not be completed",
                {"driver": driver_id, "reason": type(exc).__name__},
                [],
            )

        tables = _referenced_tables(sql)
        undeclared = sorted(_declared_tables(tables) - _declared_tables(source_tables))
        if undeclared:
            # Refused before the query runs, and refused on the AGENT's grant
            # rather than on the diagnostic's own reading of itself. See the
            # module docstring for why the second is not a check at all.
            return fail(
                "UNDECLARED_TABLE",
                f"the {driver_id!r} diagnostic reads {undeclared}, which this "
                "agent has not declared",
                {
                    "driver": driver_id,
                    "undeclared": undeclared,
                    "declared": sorted(_declared_tables(source_tables)),
                },
                [],
            )

        try:
            rows, scanned = run_query(sql, driver.params, tables)
        except Exception as exc:  # noqa: BLE001 — boundary with BigQuery
            # str(exc) is deliberately NOT returned. BigQuery echoes fragments
            # of the failing statement in its error text, so passing it through
            # would hand the model the SQL by the back door — the one thing
            # this tool and method_lookup exist to prevent. The type name is
            # enough for the agent to know the diagnostic did not run; the
            # detail belongs in the server log, where it is not a leak.
            LOG.exception("diagnostic %s failed for persona %s", driver_id, persona)
            return fail(
                "QUERY_FAILED",
                f"the {driver_id!r} diagnostic could not be completed",
                {"driver": driver_id, "reason": type(exc).__name__},
                tables,
            )

        return ok(
            {
                "driver": driver_id,
                "status": driver.status,
                "guard": driver.guard,
                "rows": rows,
            },
            tables,
            scanned,
        )

    return run_diagnostic
