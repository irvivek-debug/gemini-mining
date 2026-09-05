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
from mining_agents.method.pack import load_pack

PACK_DIR = Path(__file__).resolve().parents[2] / "method"

#: Personas whose method is encoded. A persona without a pack must fail loudly
#: rather than return an empty tree.
PACKS = {
    "P1": "p1-reliability.yaml",
    "P2": "p2-planner.yaml",
    "P3": "p3-hse.yaml",
    "P5": "p5-geologist.yaml",
    "P6": "p6-metallurgist.yaml",
    "P7": "p7-mine-controller.yaml",
    "P8": "p8-shift-supervisor.yaml",
}


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
        except Exception:  # noqa: BLE001 — must never propagate; see module docstring
            # An unhandled exception here reaches the ADK runtime as a
            # traceback, bypassing every structured-error path the caller
            # has.  yaml.YAMLError is the most common non-(OSError, PackError)
            # case: a malformed pack raises ParserError, which is neither.
            # The bare filename (not the absolute path) goes in details so
            # support can identify the pack without the model seeing host paths.
            return fail(
                "NO_METHOD_PACK",
                f"method pack for persona {persona!r} could not be loaded",
                {"persona": persona, "pack_file": name},
                [],
            )
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
