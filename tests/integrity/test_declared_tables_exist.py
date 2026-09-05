"""Gates on the claims the agent catalogue makes about the world.

WHY THIS FILE EXISTS
The repo already enforces honesty on its own SQL: assert_reads_only_declared_
tables checks that every method-pack query reads only what it declared, and all
40 SQL files pass it. Nothing applied the same standard to the VAULT catalogue,
which is imported as trusted data but is really a set of assertions -- and
assertions need tests.

Unguarded, it drifted badly. 26 of 34 declared tables did not exist, 65 of 101
agents had zero surviving grounding, and the front end published "Data
provenance" for tables nobody could query. None of that failed a test, a build
or a deploy. It surfaced only when agents were driven through the UI and the
careful ones said they could not evidence their answers.

These are integration tests: they ask BigQuery and Vertex rather than guessing.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"{name} is unset. Copy .env.example to .env and fill it in "
            "(see docs/RECREATE.md)."
        )
    return value


PROJECT = _required("GOOGLE_CLOUD_PROJECT")
sys.path.insert(0, str(ROOT / "vendor" / "agent_registry"))


def _query(sql: str) -> list[dict]:
    p = subprocess.run(["bq", f"--project_id={PROJECT}", "query", "--nouse_legacy_sql",
                        "--format=json", "--max_rows=1000", sql],
                       capture_output=True, text=True)
    if p.returncode != 0:
        pytest.fail(f"BigQuery unavailable or unauthenticated:\n{p.stderr.strip()[:300]}")
    return json.loads(p.stdout or "[]")


def _real_objects() -> set[str]:
    rows = _query(f"SELECT table_name FROM `{PROJECT}.mining_data.INFORMATION_SCHEMA.TABLES`")
    assert len(rows) > 30, f"only {len(rows)} objects returned — the query looks broken"
    return {r["table_name"] for r in rows}


@pytest.mark.integration
def test_every_declared_source_table_exists():
    """The check whose absence let 26 dead tables ship.

    An agent that declares a table it cannot read is not a smaller agent — it
    is an agent whose stated grounding is fiction, and the product will render
    that fiction as 'Data provenance' on a customer-facing screen.
    """
    import catalog_definitions as C

    real = _real_objects()
    missing = {}
    for a in C.CATALOG:
        for t in a.source_tables:
            if t not in real:
                missing.setdefault(t, []).append(a.agent_id)
    assert not missing, (
        f"{len(missing)} declared tables do not exist in {PROJECT}.mining_data: "
        + "; ".join(f"{t} ({len(v)} agents)" for t, v in sorted(missing.items()))
    )


@pytest.mark.integration
def test_no_agent_is_left_without_grounding():
    """Every agent that declares tables can read at least one of them."""
    import catalog_definitions as C

    real = _real_objects()
    orphans = [a.agent_id for a in C.CATALOG
               if a.source_tables and not (set(a.source_tables) & real)]
    assert not orphans, f"{len(orphans)} agents have no readable table: {orphans[:10]}"


@pytest.mark.integration
def test_no_declared_table_is_empty():
    """A table that exists but holds nothing is the subtler version of the same
    failure: the agent stops saying "no such table" and starts reporting "no
    data", which reads as a finding about the mine rather than a gap in the
    build. Three filtered views were withdrawn during this work for exactly
    that reason."""
    import catalog_definitions as C

    declared = sorted({t for a in C.CATALOG for t in a.source_tables})
    sel = " UNION ALL ".join(
        f"SELECT '{t}' AS t, COUNT(*) AS n FROM `{PROJECT}.mining_data.{t}`" for t in declared)
    counts = {r["t"]: int(r["n"]) for r in _query(sel)}
    empty = sorted(t for t, n in counts.items() if n == 0)
    assert not empty, f"declared tables exist but return no rows: {empty}"


@pytest.mark.integration
def test_the_front_end_publishes_only_real_provenance():
    """Screen 4 renders each agent's grounding tables. It is generated from the
    catalogue, so it inherited the fiction faithfully — 65 of 101 agents showed
    provenance nobody could query."""
    real = _real_objects()
    text = (ROOT / "apps" / "frontend" / "data.js").read_text()
    blob = text.split("window.agentCatalogData =")[1].split("window.agentTierCounts")[0]
    agents = json.loads(blob.strip().rstrip(";"))
    bad = {aid: [p["name"] for p in a["provenance"] if p["name"] not in real]
           for aid, a in agents.items()
           if any(p["name"] not in real for p in a["provenance"])}
    assert not bad, (
        f"{len(bad)} agents on Screen 4 publish tables that do not exist, e.g. "
        + "; ".join(f"{k}: {v}" for k, v in list(bad.items())[:4])
    )


@pytest.mark.integration
def test_the_catalogue_model_resolves_in_this_project():
    """Every Agent Engine was built on a model the project could not reach.

    the catalogue's model is real and correct, but it is served ONLY from the global
    endpoint — eleven regions return 404. Engines in us-central1 resolve
    publisher models regionally, so all 91 failed on every invocation and
    nothing caught it. This asserts the model the catalogue names can actually
    be called where the registration points it.
    """
    import catalog_definitions as C

    models = {a.model_id for a in C.CATALOG}
    sys.path.insert(0, str(ROOT / "scripts"))
    from register_agents import MODEL_LOCATION  # noqa: PLC0415

    host = ("https://aiplatform.googleapis.com" if MODEL_LOCATION == "global"
            else f"https://{MODEL_LOCATION}-aiplatform.googleapis.com")
    tok = subprocess.run(["gcloud", "auth", "print-access-token"],
                         capture_output=True, text=True).stdout.strip()
    if not tok:
        pytest.skip("no gcloud credential available")
    import urllib.error
    import urllib.request

    for m in sorted(models):
        url = (f"{host}/v1/projects/{PROJECT}/locations/{MODEL_LOCATION}"
               f"/publishers/google/models/{m}:generateContent")
        body = json.dumps({"contents": [{"role": "user", "parts": [{"text": "ok"}]}]}).encode()
        req = urllib.request.Request(url, data=body, method="POST", headers={
            "Authorization": f"Bearer {tok}", "X-Goog-User-Project": PROJECT,
            "Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=90)
        except urllib.error.HTTPError as e:
            pytest.fail(f"model {m} is not reachable at location "
                        f"{MODEL_LOCATION!r}: HTTP {e.code}. Agent Engines built "
                        f"against it will 404 on every invocation.")
