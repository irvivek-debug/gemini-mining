"""v2: register an A2A swarm coordinator alongside the v1 estate.

The v1 estate stays untouched. A v2 coordinator (id <SWARM>-COORDINATOR-V2)
gets, in addition to its BigQuery tools, one `consult_*` tool per teammate —
each a thin client for the teammate's LIVE v1 reasoning engine, so there is
exactly one deployed definition of every specialist and the coordinator
consults the same agents a user would.

Verification is delegation-aware: "wired" is not "used". After creation the
coordinator is probed with a question that requires its team, and the trace
must contain consult_* calls, or the build fails.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "vendor" / "agent_registry"))
import catalog_definitions as C  # noqa: E402
from register_agents import (  # noqa: E402
    DATASET, ENGINE_API, PROJECT, REGION, STAGING_BUCKET, _bigquery_tools,
    create_ge_entry, paged,
)
import probe_set  # noqa: E402

CONFIRM = "yes-register-v2-for-real"


def live_engines() -> dict[str, str]:
    out = {}
    for e in paged(ENGINE_API, "reasoningEngines"):
        m = re.search(r"\(([A-Z0-9][A-Z0-9\-]*)\)\s*$", e.get("displayName", ""))
        if m:
            out[m.group(1)] = e["name"]
    return out


def make_consult_tool(teammate_id: str, teammate_name: str, resource: str):
    """A picklable tool: ask a live teammate engine and return its answer.

    Uses the runtime metadata-server credential (never a pickled human one)
    and degrades to an explicit UNAVAILABLE answer on failure so one slow
    teammate cannot hang the coordinator.
    """
    fn_name = "consult_" + teammate_id.lower().replace("-", "_")

    def consult(question: str) -> str:
        import json as _json
        import urllib.request as _rq
        import google.auth
        import google.auth.transport.requests
        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"])
        creds.refresh(google.auth.transport.requests.Request())
        url = (f"https://{REGION}-aiplatform.googleapis.com/v1beta1/"
               f"{resource}:streamQuery?alt=sse")
        body = {"class_method": "stream_query",
                "input": {"message": question, "user_id": "swarm-coordinator"}}
        try:
            raw = _rq.urlopen(_rq.Request(
                url, data=_json.dumps(body).encode(),
                headers={"Authorization": f"Bearer {creds.token}",
                         "Content-Type": "application/json"},
                method="POST"), timeout=180).read().decode()
        except Exception as e:  # noqa: BLE001
            return (f"SPECIALIST UNAVAILABLE ({teammate_id}): "
                    f"{type(e).__name__}. State this plainly and proceed "
                    f"with what you can evidence yourself.")
        texts = []
        for line in raw.splitlines():
            try:
                ev = _json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            for prt in (ev.get("content") or {}).get("parts", []) or []:
                if prt.get("text"):
                    texts.append(prt["text"])
        return " ".join(texts) or f"SPECIALIST {teammate_id} returned no text."

    consult.__name__ = fn_name
    consult.__doc__ = (f"Consult {teammate_name} ({teammate_id}) — a live "
                       f"specialist agent — with a specific question. "
                       f"Returns their grounded answer.")
    return consult


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--swarm", required=True, help="e.g. S01")
    ap.add_argument("--confirm", default="")
    args = ap.parse_args()

    ids = probe_set.select_group(args.swarm)
    coord_id = next(a for a in ids if a.endswith("-COORDINATOR"))
    teammates = [a for a in ids if a != coord_id]
    by_id = {a.agent_id: a for a in C.CATALOG}
    coord = by_id[coord_id]
    engines = live_engines()
    missing = [t for t in teammates if t not in engines]
    if missing:
        raise SystemExit(f"teammates without live engines: {missing}")

    v2_id = f"{coord_id}-V2"
    print(f"  {v2_id}: consults {teammates}")
    if args.confirm != CONFIRM:
        print(f"  DRY RUN — pass --confirm {CONFIRM}")
        return 0

    import vertexai
    from vertexai import agent_engines
    from vertexai.preview.reasoning_engines import AdkApp
    from google.adk.agents import llm_agent
    vertexai.init(project=PROJECT, location=REGION, staging_bucket=STAGING_BUCKET)

    tools = [_bigquery_tools(coord)]
    for t in teammates:
        tools.append(make_consult_tool(t, by_id[t].name, engines[t]))

    tables = ", ".join(coord.source_tables) or "your declared sources"
    instruction = (
        f"Your data lives in BigQuery project `{PROJECT}`, dataset `{DATASET}`. "
        f"`{DATASET}` is the dataset, never the project.\n"
        f"You are {coord.name}, the coordinator of a specialist team. For any "
        f"question touching a specialist's depth, CONSULT the relevant "
        f"consult_* tools — ask each a specific sub-question — then synthesize "
        f"their answers, attributing findings to the specialist who made them. "
        f"Query {tables} yourself only for cross-domain joins no specialist "
        f"owns. If a specialist is unavailable, say so plainly. Cite the table "
        f"behind every figure; reconcile any assumptions the question supplies "
        f"against the data; quote money as ranges, never single points."
    )
    app = AdkApp(agent=llm_agent.LlmAgent(
        name=v2_id.replace("-", "_").lower(), model=coord.model_id,
        instruction=instruction, tools=tools))
    remote = agent_engines.create(
        agent_engine=app,
        display_name=f"{coord.name} v2 Swarm ({v2_id})",
        requirements=["google-adk==2.6.3", "google-cloud-dataplex",
                      "google-genai==2.17.0",
                      "google-cloud-aiplatform[agent_engines,adk]>=1.70.0",
                      "pydantic>=2.0.0", "cloudpickle==3.1.2"],
        service_account=f"mag-agent-coordinator@{PROJECT}.iam.gserviceaccount.com",
        env_vars={"GOOGLE_CLOUD_LOCATION": "global"})
    res = remote.resource_name
    print(f"  engine: {res.split('/')[-1]}")

    # delegation probe: wired is not used
    import subprocess
    tok = subprocess.run(["gcloud", "auth", "print-access-token"],
                         capture_output=True, text=True).stdout.strip()
    url = f"https://{REGION}-aiplatform.googleapis.com/v1beta1/{res}:streamQuery?alt=sse"
    q = ("Consult your specialists: ask each one for the single most "
         "important current finding in their area, then synthesize the "
         "three biggest risks for this swarm's domain, attributing each "
         "finding to the specialist who reported it.")
    raw = urllib.request.urlopen(urllib.request.Request(
        url, data=json.dumps({"class_method": "stream_query",
                              "input": {"message": q, "user_id": "delegation-probe"}}).encode(),
        headers={"Authorization": f"Bearer {tok}",
                 "X-Goog-User-Project": PROJECT,
                 "Content-Type": "application/json"},
        method="POST"), timeout=600).read().decode()
    calls = re.findall(r'"name":\s*"(consult_[a-z0-9_]+)"', raw)
    texts = len(raw)
    print(f"  delegation probe: {len(calls)} consult calls {sorted(set(calls))}")
    if not calls:
        raise SystemExit(f"{v2_id}: DELEGATION NOT OBSERVED — wired is not used; failing the build")
    g = create_ge_entry(coord, res)
    if "_http" in g:
        print(f"  GE entry FAILED {g['_http']}")
    else:
        print("  registered in Gemini Enterprise (v2 entry)")
    print(f"  {v2_id} LIVE with observed delegation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
