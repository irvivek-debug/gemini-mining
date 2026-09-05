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
