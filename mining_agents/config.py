"""Environment-driven settings and tier-to-model resolution."""
from __future__ import annotations

import os
import pathlib
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from google.adk.models import Gemini

_VALID_TIERS = ("reasoning", "balanced")

# Both tiered models are published only in the `global` location. An agent
# deployed to a regional Agent Engine gets a regionally-scoped genai client by
# default, and the regional endpoint answers 404 for these models — "was not
# found or your project does not have access", which reads like a typo in the
# policy table or a missing grant rather than a location mismatch.
#
# Only model calls move to `global`. The session store stays regional, because
# it lives under the reasoning engine resource, which is regional.
MODEL_LOCATION = "global"
_ROW = re.compile(r"^\|\s*`(?P<tier>[a-z-]+)`\s*\|\s*`(?P<model>[^`]+)`\s*\|")


@dataclass(frozen=True)
class Settings:
    project_id: str
    dataset: str
    location: str
    bq_binary: str
    model_policy_path: pathlib.Path


def _repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[1]


def _required_project_id() -> str:
    """The project is never guessed: a placeholder default would surface as a
    confusing BigQuery 404 in whichever query happened to run first."""
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
    if not project_id:
        raise RuntimeError(
            "GOOGLE_CLOUD_PROJECT is unset. Copy .env.example to .env and set "
            "it to your own GCP project ID (see docs/RECREATE.md)."
        )
    return project_id


def settings() -> Settings:
    return Settings(
        project_id=_required_project_id(),
        dataset=os.environ.get("MINING_DATASET", "mining_data"),
        location=os.environ.get("MINING_LOCATION", "US"),
        # Resolved from PATH by default. Hardcoding an absolute path here bakes
        # one machine's install convention into everyone else's checkout; set
        # BQ_BINARY when the CLI lives somewhere PATH does not reach.
        bq_binary=os.environ.get("BQ_BINARY", "bq"),
        model_policy_path=_repo_root() / "references" / "model-policy.md",
    )


def model_for_tier(tier: str) -> str:
    """Resolve a model tier to a concrete model ID via references/model-policy.md."""
    if tier not in _VALID_TIERS:
        raise ValueError(
            f"unknown model tier {tier!r}; valid tiers are {_VALID_TIERS}"
        )
    text = settings().model_policy_path.read_text()
    for line in text.splitlines():
        match = _ROW.match(line.strip())
        if match and match.group("tier") == tier:
            return match.group("model")
    raise ValueError(f"tier {tier!r} not found in model-policy.md")


def llm_for_tier(tier: str) -> "Gemini":
    """The model object an agent of *tier* runs on, pinned to `global`.

    Agents take this rather than the bare id from `model_for_tier` so that the
    endpoint choice is made once here instead of being inherited from whatever
    region the agent happens to be deployed in.

    The ADK import is deliberately inside the function. Almost everything that
    imports this module wants `settings()` and nothing else — the deploy
    script, the IAM plan, the DDL runner, the workspace server — and a
    module-level `from google.adk.models import Gemini` made every one of them
    require the whole ADK and Vertex SDK to read a project id. Only the two
    pattern builders construct a model, and they pay for it here.
    """
    from google.adk.models import Gemini

    return Gemini(
        model=model_for_tier(tier),
        client_kwargs={"vertexai": True, "location": MODEL_LOCATION},
    )
