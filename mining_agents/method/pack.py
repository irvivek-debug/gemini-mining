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

#: Whether a diagnostic exists for this driver, and NOTHING about what that
#: diagnostic will show.
#:
#: `unevidenced` used to live here, and it was a verdict written before the
#: query ran: the bypass driver declared it while carrying `sql`, so the pack
#: had already decided what its own diagnostic would find. That reaches the
#: model twice — through the method_lookup projection and again in every
#: run_diagnostic result — and on a fork whose data holds plenty of bypass
#: events the pack would still have said "unevidenced". Evidenced or not is a
#: conclusion the agent draws from the rows it was actually returned.
STATUSES = frozenset({"instrumented", "not_instrumented"})

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
    if not isinstance(raw, dict):
        raise PackError(
            f"driver #{index} is {type(raw).__name__}, not a mapping; "
            "each list entry under 'drivers' is a block of keys"
        )
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
    if raw["status"] == "instrumented":
        if not raw.get("sql"):
            raise PackError(f"{where}: an instrumented driver must carry 'sql'")
    else:
        if raw.get("sql"):
            # The converse, and it matters because two consumers read the two
            # fields: run_diagnostic decides DRIVER_NOT_INSTRUMENTED on `sql`,
            # method_lookup reports `status`. A driver that declares one and
            # carries the other tells the agent two different things about
            # itself.
            raise PackError(
                f"{where}: status is not_instrumented but 'sql' is set; a "
                "driver with a diagnostic behind it is instrumented"
            )
        if raw.get("compare") is not None:
            # A comparison on a driver with no diagnostic behind it is a claim
            # the pack cannot honour. Left to load, it tells an author a
            # comparison is happening when nothing computes one.
            raise PackError(
                f"{where}: compare is set but status is {raw['status']!r}; "
                "only an instrumented driver compares anything"
            )
    if raw.get("compare") is not None and raw["compare"] not in COMPARISONS:
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
    if not isinstance(raw, dict):
        raise PackError(
            f"pack is a {type(raw).__name__}, not a mapping; a pack is a block "
            "with 'metric', 'root' and 'drivers' at the top level"
        )
    for required in ("metric", "root", "drivers"):
        if required not in raw:
            raise PackError(f"pack is missing {required!r}")
    if not isinstance(raw["drivers"], list):
        raise PackError(
            f"'drivers' is a {type(raw['drivers']).__name__}, not a list; "
            "a pack with one driver still writes it as a list of one"
        )
    if not raw["drivers"]:
        raise PackError("pack declares no driver; a tree with no branch is not a method")
    drivers = [_driver(d, i) for i, d in enumerate(raw["drivers"])]
    seen = [d.id for d in drivers]
    if len(set(seen)) != len(seen):
        raise PackError(f"duplicate driver ids: {seen}")
    return Pack(metric=raw["metric"], root=raw["root"], drivers=drivers)
