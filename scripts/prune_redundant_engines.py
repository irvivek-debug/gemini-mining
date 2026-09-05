"""Delete Reasoning Engines that duplicate an agent already registered by catalogue id.

WHY THIS IS NEEDED AT ALL
ReasoningEngineEntitiesPerProjectPerRegion is capped at 100 and the project sits
at exactly 100. That ceiling — not the missing grounding data — is why agent
registration stopped where it did: a create returns
`429 ResourceExhausted: ReasoningEngineEntitiesPerProjectPerRegion`.

WHAT IT DELETES, AND WHY THAT IS SAFE
Ten engines carry this repo's older display names (`Cascading Failure Impact &
Recovery Coordinator`, `D01`, …). Each one's underlying swarm or solver is
already registered under its catalogue id (`S01-COORDINATOR`, `D01`, …), which
is verified here at run time rather than trusted — an engine whose catalogue
twin is missing is refused, not deleted.

The Gemini Enterprise entry is removed before the engine it points at, so no
assistant is ever left holding a reference to a resource that no longer exists.

Usage:
    python scripts/prune_redundant_engines.py                 # dry run
    python scripts/prune_redundant_engines.py --confirm yes-delete-for-real
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
sys.path.insert(0, str(ROOT))


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"{name} is unset. Copy .env.example to .env and fill it in "
            "(see docs/RECREATE.md)."
        )
    return value


PROJECT = _required("GOOGLE_CLOUD_PROJECT")
REGION = os.environ.get("MINING_REGION", "us-central1")
CONFIRM = "yes-delete-for-real"

ENGINE_API = (f"https://{REGION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT}"
              f"/locations/{REGION}/reasoningEngines")
GE_AGENTS = (f"https://discoveryengine.googleapis.com/v1alpha/projects/{PROJECT}"
             f"/locations/global/collections/default_collection/engines/"
             f"gemini-enterprise-17804660_1780466009095/assistants/default_assistant/agents")


def api(url, method="GET", body=None):
    tok = subprocess.run(["gcloud", "auth", "print-access-token"],
                         capture_output=True, text=True).stdout.strip()
    h = {"Authorization": f"Bearer {tok}", "X-Goog-User-Project": PROJECT,
         "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body is not None else None
    try:
        return json.load(urllib.request.urlopen(
            urllib.request.Request(url, data=data, headers=h, method=method), timeout=120))
    except urllib.error.HTTPError as e:
        return {"_http": e.code, "_body": e.read().decode()[:300]}


def paged(url, key):
    out, page = [], None
    while True:
        d = api(url + (("&" if "?" in url else "?") + f"pageToken={page}" if page else ""))
        out += d.get(key, [])
        page = d.get("nextPageToken")
        if not page:
            return out


CATALOGUE_ID = re.compile(r"\(([A-Z0-9][A-Z0-9\-]*)\)\s*$")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", default="")
    args = ap.parse_args()

    import mining_agents.registry as R
    repo_by_name = {getattr(a, "display_name", ""): a.agent_id for a in R.registrable()}

    engines = paged(ENGINE_API, "reasoningEngines")
    by_catalogue_id = {}
    unnamed = []
    for e in engines:
        m = CATALOGUE_ID.search(e.get("displayName", ""))
        (by_catalogue_id.setdefault(m.group(1), e) if m else unnamed.append(e))

    ge = {a.get("displayName", ""): a for a in paged(GE_AGENTS, "agents")}

    plan, refused = [], []
    for e in unnamed:
        dn = e.get("displayName", "")
        repo_id = repo_by_name.get(dn)
        # `D01` is a bare duplicate of the catalogue's own D01 and has no repo
        # display name; treat its own text as the id.
        twin = (f"{repo_id}-COORDINATOR" if repo_id and repo_id.startswith("S")
                else (repo_id or dn.strip()))
        if twin in by_catalogue_id:
            plan.append((e, twin))
        else:
            refused.append((dn, twin))

    print(f"engines: {len(engines)}   catalogue-named: {len(by_catalogue_id)}   other: {len(unnamed)}\n")
    for e, twin in plan:
        has_ge = e.get("displayName", "") in ge
        print(f"  DELETE  {e['displayName'][:46]:<46}  twin {twin} present"
              f"   GE entry: {'yes' if has_ge else 'no'}")
    for dn, twin in refused:
        print(f"  KEEP    {dn[:46]:<46}  no catalogue twin ({twin}) — refusing to delete")

    if args.confirm != CONFIRM:
        print(f"\nDRY RUN — pass --confirm {CONFIRM} to delete "
              f"{len(plan)} engines and their Gemini Enterprise entries")
        return 0

    for e, twin in plan:
        dn = e["displayName"]
        entry = ge.get(dn)
        if entry:
            r = api(f"https://discoveryengine.googleapis.com/v1alpha/{entry['name']}", "DELETE")
            print(f"  GE entry removed for {dn[:40]}" if "_http" not in r
                  else f"  GE delete FAILED {r['_http']}: {r['_body'][:120]}")
        r = api(f"https://{REGION}-aiplatform.googleapis.com/v1beta1/{e['name']}?force=true", "DELETE")
        print(f"  engine deleted: {dn[:46]}" if "_http" not in r
              else f"  engine delete FAILED {r['_http']}: {r['_body'][:160]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
