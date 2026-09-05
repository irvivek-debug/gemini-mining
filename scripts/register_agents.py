"""Register agents as Vertex AI Reasoning Engines and into Gemini Enterprise.

WHY THIS EXISTS RATHER THAN THE VAULT'S SCRIPT
`deployment/register_all_agents_to_agent_registry.py` in the vault is a 30-line
shim that dynamically loads a root script which is not in the bucket, so it
cannot run. The vault's other lead -- Mendel forced_flags -- is Google-internal
experiment plumbing, not a customer-runnable API. Neither is needed: the 90
agents already registered were created through the Discovery Engine `agents`
endpoint, and this reproduces that path.

TWO STEPS PER AGENT, AND THE SECOND DEPENDS ON THE FIRST
  1. ReasoningEngine.create() -- the A2A / Agent Registry entry
  2. an `agents` entry on the Gemini Enterprise assistant, whose
     adkAgentDefinition.provisionedReasoningEngine points at step 1

Both are idempotent: an agent already carrying a reasoning engine, or already
present on the assistant, is skipped rather than duplicated. Re-running after a
partial failure resumes instead of creating a second copy.

Usage:
    python scripts/register_agents.py --list
    python scripts/register_agents.py --agents S10-R-CRITIC,S11-COORDINATOR
    python scripts/register_agents.py --agents ... --confirm yes-register-for-real
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor" / "agent_registry"))
import catalog_definitions as C  # noqa: E402

def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"{name} is unset. Copy .env.example to .env and fill it in "
            "(see docs/RECREATE.md)."
        )
    return value


PROJECT = _required("GOOGLE_CLOUD_PROJECT")
DATASET = os.environ.get("MINING_DATASET", "mining_data")
PROJECT_NUMBER = _required("GOOGLE_CLOUD_PROJECT_NUMBER")
REGION = os.environ.get("MINING_REGION", "us-central1")
CONFIRM_PHRASE = "yes-register-for-real"

# Agent Engine stages the packaged agent through this bucket. It must already
# exist and be writable by the caller; Agent Engine does not create it.
STAGING_BUCKET = _required("VERTEX_STAGING_BUCKET")

# The identity the engine runs as, and therefore what its BigQuery tool can
# read. Left unset, Agent Engine falls back to the project's default compute
# account, which holds aiplatform and run roles and NO BigQuery role at all --
# so the toolset resolved, called execute_sql, and was refused at the IAM
# boundary with 403. The agent reported that accurately rather than inventing
# a figure, which is the behaviour we want, but it could not answer.
#
# This is the account the mag-* Cloud Run agents already run as: aiplatform.user,
# bigquery.jobUser, bigquery.connectionUser, and now bigquery.dataViewer.
ENGINE_CAP = 100  # ReasoningEngineEntitiesPerProjectPerRegion
ENGINE_SERVICE_ACCOUNT = os.environ.get(
    "ENGINE_SERVICE_ACCOUNT",
    f"mag-agent-coordinator@{PROJECT}.iam.gserviceaccount.com",
)

# WHY EVERY EXISTING ENGINE 404s ON ITS OWN MODEL
# The catalogue gives all 101 agents model_id "the catalogue's model". That model is
# real and this project can reach it -- but ONLY on the global endpoint.
# Probed across twelve locations: global returns 200, and us-central1,
# us-east1/4/5, us-west1/4, northamerica-northeast1, europe-west1/4,
# asia-southeast1 and australia-southeast1 all return 404.
#
# An Agent Engine in us-central1 resolves publisher models regionally, so it
# asks us-central1 for a model served only from global and gets a 404. The
# model name was never wrong and the catalogue is not edited here; the ENGINE
# is told where to look instead.
MODEL_LOCATION = "global"

# Pinned rather than ranged. The 90 failing engines were built from an
# unpinned google-cloud-aiplatform[agent_engines,adk]>=1.70.0, and an engine
# built that way fails with `TypeError: 'NoneType' object is not subscriptable`
# even once its model resolves -- a second fault behind the first. These are
# the versions verified working, locally and then deployed.
REQUIREMENTS = [
    "google-adk==2.6.3",
    # BigQueryToolset imports google.cloud.dataplex_v1 transitively. Without
    # this the toolset raises ImportError inside the engine at first tool use,
    # which surfaces as an agent that mysteriously stops answering -- found
    # locally before it could be found in production.
    "google-cloud-dataplex",
    "google-genai==2.17.0",
    "google-cloud-aiplatform[agent_engines,adk]>=1.70.0",
    "pydantic>=2.0.0",
]

ENGINE_API = (f"https://{REGION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT}"
              f"/locations/{REGION}/reasoningEngines")
GE_AGENTS = (f"https://discoveryengine.googleapis.com/v1alpha/projects/{PROJECT}"
             f"/locations/global/collections/default_collection/engines/"
             f"gemini-enterprise-17804660_1780466009095/assistants/default_assistant/agents")


def token() -> str:
    return subprocess.run(["gcloud", "auth", "print-access-token"],
                          capture_output=True, text=True).stdout.strip()


def api(url: str, method: str = "GET", body: dict | None = None) -> dict:
    h = {"Authorization": f"Bearer {token()}", "X-Goog-User-Project": PROJECT,
         "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body is not None else None
    try:
        return json.load(urllib.request.urlopen(
            urllib.request.Request(url, data=data, headers=h, method=method), timeout=120))
    except urllib.error.HTTPError as e:
        return {"_http": e.code, "_body": e.read().decode()[:400]}


def paged(url: str, key: str) -> list[dict]:
    """List every page, raising rather than returning an empty list on error.

    This used to do `out += d.get(key, [])` unconditionally. An expired
    credential returns {"_http": 401, ...}, which has no `key`, so the function
    returned [] and the caller read it as "there are no agents registered" --
    an auth failure wearing the costume of a legitimate empty result. It
    reported "0 agents mapped" against an estate of 96.
    """
    out, page = [], None
    while True:
        d = api(url + (("&" if "?" in url else "?") + f"pageToken={page}" if page else ""))
        if "_http" in d:
            raise SystemExit(
                f"listing {key} failed with HTTP {d['_http']}: {d['_body'][:200]}\n"
                f"If this is 401, the credential has expired — run `gcloud auth login`."
            )
        out += d.get(key, [])
        page = d.get("nextPageToken")
        if not page:
            return out


def id_of(display_name: str) -> str | None:
    m = re.search(r"\(([A-Z0-9][A-Z0-9\-]*)\)\s*$", display_name or "")
    return m.group(1) if m else None


def current_state() -> tuple[dict, dict]:
    """What is already registered, keyed by agent id."""
    engines = {id_of(e.get("displayName", "")): e for e in paged(ENGINE_API, "reasoningEngines")}
    ge = {id_of(a.get("displayName", "")): a for a in paged(GE_AGENTS, "agents")}
    engines.pop(None, None)
    ge.pop(None, None)
    return engines, ge


def _bigquery_tools(agent):
    """Read-only BigQuery access whose credential holds no secret.

    THE CONSTRAINT
    Whatever is passed here is cloudpickled into the deployed artefact. Passing
    the local ADC put a developer refresh token inside it -- measured, 1,107
    bytes with the token present -- which would place a human's Google
    credential into a Cloud resource.

    THE FIX
    compute_engine.Credentials() carries no refresh token, no client secret and
    no token value: 742 bytes of nothing but a resolution strategy. It fetches
    a token from the host metadata server at call time, which on Agent Engine
    is the engine's own service account. So the artefact is credential-free AND
    the agent reads exactly what its own identity is granted -- which is what
    makes per-tier IAM scoping real rather than decorative.

    A previous attempt deferred construction behind a BaseToolset subclass that
    nulled itself on pickle. The artefact was clean, but the engine never
    called get_tools() on it and the agent reported having no BigQuery tool at
    all. Credential safety was verified; tool delivery was not. Both are
    checked now.

    WriteMode.BLOCKED because no agent in this estate may write, enforced by
    the toolset rather than by asking the model nicely.
    """
    from google.auth import compute_engine
    from google.adk.integrations.bigquery import BigQueryToolset, BigQueryCredentialsConfig
    from google.adk.integrations.bigquery.config import BigQueryToolConfig, WriteMode

    return BigQueryToolset(
        credentials_config=BigQueryCredentialsConfig(
            credentials=compute_engine.Credentials()),
        bigquery_tool_config=BigQueryToolConfig(
            write_mode=WriteMode.BLOCKED,
            compute_project_id=PROJECT,
            maximum_bytes_billed=2_000_000_000,
            max_query_result_rows=200,
        ),
    )


def create_engine(agent) -> str:
    """Deploy one agent as an Agent Engine and return its resource name.

    vertexai.agent_engines.create rather than the preview ReasoningEngine.create
    because only the former takes env_vars, and env_vars is what carries the
    model-location fix into the running engine.
    """
    import vertexai
    from vertexai import agent_engines
    from vertexai.preview.reasoning_engines import AdkApp
    from google.adk.agents import llm_agent

    vertexai.init(project=PROJECT, location=REGION, staging_bucket=STAGING_BUCKET)
    # 99 of the 101 carry an empty system_instruction, so a usable one is
    # composed from the fields that are populated rather than shipping a blank.
    # WHY THE INSTRUCTION NAMES THE TABLES AND DEMANDS RECONCILIATION
    # AGT-19 answered a cut-off grade question with flawless arithmetic --
    # every figure recomputed exactly -- but took recovery, price and costs
    # straight from the question and never opened its own data. The prompt
    # assumed 89.5% recovery; metallurgical_recovery averages 92.21%. A
    # correct answer to a hypothetical, presented as strategic guidance.
    #
    # "cite the table behind every figure" was not enough, because the model
    # can satisfy it by citing nothing when it cites nothing. So the tables are
    # named, and reconciling supplied assumptions against them is made an
    # explicit step with a required disclosure when they diverge.
    tables = ", ".join(agent.source_tables) or "your declared sources"

    # WHY THE INSTRUCTION NAMES THE PROJECT
    # No agent was ever told which BigQuery project it lives in, so every
    # query began with a guessing game: passing the dataset name `mining_data`
    # as a project id (400, invalid project), calling search_catalog without
    # its mandatory project_id, trying a project literally named `test`
    # (refused -- the toolset is locked to one project). All 95 agents did
    # this on every run. Most recovered after burning three or four calls,
    # which inflated latency; occasionally one exhausted its budget and
    # returned nothing at all.
    #
    # This is prepended to BOTH branches below. The two agents that carry
    # their own system_instruction would otherwise skip it and keep guessing.
    data_access = (
        f"Your data lives in BigQuery project `{PROJECT}`, dataset "
        f"`{DATASET}`. Fully qualified, a table is "
        f"`{PROJECT}.{DATASET}.<table>`.\n"
        f"`{DATASET}` is the dataset, never the project. Tools that require a "
        f"project_id take `{PROJECT}`. Do not guess a project name and do not "
        f"omit project_id -- both fail, and the retries cost you the answer.\n"
    )

    # The reconciliation demand must reach BOTH branches. It lived only in
    # the composed branch, so the two agents carrying a custom
    # system_instruction (AGT-19, S01-COORDINATOR) never received it -- and
    # they were exactly the two UAT content failures: fluent answers computed
    # from the question's own numbers, citing nothing.
    grounding_demand = (
        f"\nIf the question supplies its own assumptions — a price, a "
        f"recovery, a cost, a rate — reconcile each one against {tables} and "
        f"state plainly where they differ and which you used. Never present "
        f"a figure computed only from numbers in the question as if it were "
        f"grounded in the operation. Cite the table behind every figure you "
        f"report; where you cannot evidence something, say so explicitly."
    )
    custom = (agent.system_instruction or "").strip()
    if custom:
        instruction = (data_access + custom + grounding_demand).strip()
    else:
        instruction = (data_access +
            f"You are {agent.name}. {agent.description or ''}\n"
            f"Your governing method is {agent.governing_equation}.\n"
            f"Your data is {tables}. Read it before you answer."
            + grounding_demand).strip()

    app = AdkApp(agent=llm_agent.LlmAgent(
        name=agent.agent_id.replace("-", "_").lower(),
        model=agent.model_id,
        instruction=instruction,
        # Without tools these agents cannot read anything. All 100 were
        # registered that way and answered fluently from model knowledge --
        # correct-sounding, ungrounded, and invisible to a UAT that only
        # checked whether an answer looked right.
        tools=[_bigquery_tools(agent)],
    ))
    # Deleting an engine does not free its quota slot immediately, so a create
    # issued straight after a delete 429s at the cap. The naive fix -- retry the
    # create with backoff -- works but is wasteful: agent_engines.create()
    # uploads the pickle, the requirements and a dependency tarball to GCS
    # BEFORE the quota check rejects it, so six retries meant six full uploads
    # per agent. Across 100 agents that is hundreds of pointless uploads.
    #
    # So wait for the slot to actually free by polling the cheap list call,
    # then create once. A list is a metadata read; a create is megabytes.
    import time as _t
    from google.api_core import exceptions as _gexc

    for wait in (0, 15, 30, 30, 60, 60, 90):
        if wait:
            _t.sleep(wait)
        try:
            in_use = len(paged(ENGINE_API, "reasoningEngines"))
        except SystemExit:
            break                      # listing failed; fall through and try
        if in_use < ENGINE_CAP:
            break
        print(f"  {in_use}/{ENGINE_CAP} engines — waiting {wait or 15}s for the "
              f"slot to release before uploading", flush=True)
    else:
        raise SystemExit(f"no engine slot freed after ~5 minutes; refusing to "
                         f"upload into a create that will 429. The estate may be "
                         f"short an agent — re-run to finish it.")

    try:
        return _create(agent_engines, app, agent)
    except _gexc.ResourceExhausted as e:
        # One belt-and-braces retry: the slot can be taken between the poll and
        # the create by anything else touching the project.
        print("  create raced another consumer; waiting 60s and retrying once", flush=True)
        _t.sleep(60)
        return _create(agent_engines, app, agent)


def _create(agent_engines, app, agent) -> str:
    remote = agent_engines.create(
        agent_engine=app,
        display_name=f"{agent.name} ({agent.agent_id})",
        description=(agent.description or agent.name)[:900],
        service_account=ENGINE_SERVICE_ACCOUNT,
        env_vars={"GOOGLE_CLOUD_LOCATION": MODEL_LOCATION,
                  "GOOGLE_GENAI_USE_VERTEXAI": "TRUE"},
        requirements=REQUIREMENTS,
    )
    return remote.resource_name


def create_ge_entry(agent, engine_resource: str) -> dict:
    return api(GE_AGENTS, "POST", {
        "displayName": f"{agent.name} ({agent.agent_id})",
        "description": (f"Mining Operations Agent {agent.agent_id} - "
                        f"APQC {agent.apqc_code} - {agent.name}")[:900],
        "adkAgentDefinition": {
            "toolSettings": {},
            "provisionedReasoningEngine": {"reasoningEngine": engine_resource},
        },
        "state": "ENABLED",
        "sharingConfig": {"scope": "ALL_USERS"},
    })


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents", default="", help="comma-separated agent ids")
    ap.add_argument("--list", action="store_true", help="show what is and is not registered")
    ap.add_argument("--confirm", default="")
    args = ap.parse_args()

    by_id = {a.agent_id: a for a in C.CATALOG}
    engines, ge = current_state()

    if args.list:
        missing_e = sorted(set(by_id) - set(engines))
        missing_g = sorted(set(by_id) - set(ge))
        print(f"catalogue {len(by_id)} | engines {len(engines)} | gemini enterprise {len(ge)}")
        print(f"no reasoning engine ({len(missing_e)}): {missing_e}")
        print(f"not in gemini enterprise ({len(missing_g)}): {missing_g}")
        return 0

    wanted = [a.strip() for a in args.agents.split(",") if a.strip()]
    unknown = [a for a in wanted if a not in by_id]
    if unknown:
        raise SystemExit(f"not in the catalogue: {unknown}")
    if not wanted:
        raise SystemExit("pass --agents or --list")

    if args.confirm != CONFIRM_PHRASE:
        print(f"DRY RUN — pass --confirm {CONFIRM_PHRASE} to create resources\n")
        for aid in wanted:
            a = by_id[aid]
            print(f"  {aid:<18} engine={'present' if aid in engines else 'CREATE'}  "
                  f"gemini={'present' if aid in ge else 'CREATE'}  |  {a.name}")
        return 0

    for aid in wanted:
        a = by_id[aid]
        print(f"\n=== {aid} — {a.name}")
        res = engines.get(aid, {}).get("name")
        if res:
            print(f"  engine already exists: {res.split('/')[-1]}")
        else:
            print(f"  creating agent engine on {a.model_id} "
                  f"(models resolved from {MODEL_LOCATION}) — several minutes…")
            res = create_engine(a)
            print(f"  engine: {res.split('/')[-1]}")

        if aid in ge:
            print("  already on the Gemini Enterprise assistant")
            continue
        r = create_ge_entry(a, res)
        if "_http" in r:
            print(f"  GE registration FAILED {r['_http']}: {r['_body'][:200]}")
        else:
            print(f"  registered in Gemini Enterprise: {r.get('name','').split('/')[-1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
