"""Rebuild the Agent Engines that 404 on their own model.

THE FAULT
All 101 agents specify model_id "the catalogue's model". That model is real and
reachable from this project, but only on the `global` endpoint -- probed across
twelve locations, global returns 200 and eleven regions return 404. An Agent
Engine deployed in us-central1 resolves publisher models regionally, so it asks
us-central1 for a model served only from global. Every engine built that way
fails on every invocation.

A second fault sits behind it: engines built from an unpinned
google-cloud-aiplatform[agent_engines,adk]>=1.70.0 fail with
`TypeError: 'NoneType' object is not subscriptable` even once the model
resolves. Pinned versions clear it.

Neither is fixed by editing the catalogue, and neither is fixed in place: model
location and requirements are baked in at build time, so a broken engine has to
be replaced rather than patched.

WHY THIS DELETES BEFORE IT CREATES, ONE AT A TIME
ReasoningEngineEntitiesPerProjectPerRegion is capped at 100 and the project
sits near it. Creating first would 429 immediately. Each agent is therefore
deleted and rebuilt in place, which keeps the count flat and means an
interrupted run leaves the estate smaller, never over quota.

The Gemini Enterprise entry is repointed at the new engine after the rebuild,
so the assistant never holds a reference to a resource that has been deleted.
Verification is per agent and immediate: an engine that does not answer is
reported and the run continues rather than stopping the whole estate.

Usage:
    python scripts/rebuild_engines.py --check           # who is broken
    python scripts/rebuild_engines.py --agents A,B      # dry run
    python scripts/rebuild_engines.py --all --confirm yes-rebuild-for-real
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor" / "agent_registry"))
sys.path.insert(0, str(ROOT / "scripts"))
import catalog_definitions as C  # noqa: E402
import verify_grounded  # noqa: E402
from register_agents import (  # noqa: E402
    GE_AGENTS, PROJECT, REGION, api, create_engine, create_ge_entry, paged,
)

CONFIRM = "yes-rebuild-for-real"


def health(agent_id: str, resource: str) -> tuple[bool, str]:
    """Is this engine grounded? Falls back to liveness only when unverifiable.

    An agent with no probe cannot be checked for grounding. Saying so out loud
    matters: silently treating it as healthy is how untested agents get
    counted as passes.
    """
    try:
        verify_grounded.probe_for(agent_id)
    except verify_grounded.NoProbe:
        good, detail = invoke(resource)
        return good, f"{detail} (LIVENESS ONLY — no probe; grounding unverified)"
    return verify_grounded.verify(agent_id, resource)
ENGINE_API = (f"https://{REGION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT}"
              f"/locations/{REGION}/reasoningEngines")
CATALOGUE_ID = re.compile(r"\(([A-Z0-9][A-Z0-9\-]*)\)\s*$")


def invoke(resource: str, message: str = "Reply with the single word: ok") -> tuple[bool, str]:
    """Call an engine and say plainly whether it answered."""
    url = f"https://{REGION}-aiplatform.googleapis.com/v1beta1/{resource}:streamQuery?alt=sse"
    tok = subprocess.run(["gcloud", "auth", "print-access-token"],
                         capture_output=True, text=True).stdout.strip()
    h = {"Authorization": f"Bearer {tok}", "X-Goog-User-Project": PROJECT,
         "Content-Type": "application/json"}
    body = {"class_method": "stream_query",
            "input": {"message": message, "user_id": "rebuild-verify"}}
    try:
        raw = urllib.request.urlopen(
            urllib.request.Request(url, data=json.dumps(body).encode(), headers=h, method="POST"),
            timeout=240).read().decode()
    except urllib.error.HTTPError as e:
        return False, f"HTTP{e.code}"
    except Exception as e:
        return False, type(e).__name__
    if '"error_code"' in raw:
        m = re.search(r'"error_message":\s*"([^"]{0,90})', raw)
        return False, (m.group(1) if m else "error")[:90]
    texts = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        for p in (ev.get("content") or {}).get("parts", []) or []:
            if p.get("text"):
                texts.append(p["text"])
    reply = " ".join(texts).strip()
    return bool(reply), reply[:70] or "empty reply"


def state() -> tuple[dict, dict]:
    engines, ge = {}, {}
    for e in paged(ENGINE_API, "reasoningEngines"):
        m = CATALOGUE_ID.search(e.get("displayName", ""))
        if m:
            engines[m.group(1)] = e
    for a in paged(GE_AGENTS, "agents"):
        m = CATALOGUE_ID.search(a.get("displayName", ""))
        if m:
            ge[m.group(1)] = a
    return engines, ge


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents", default="")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--confirm", default="")
    args = ap.parse_args()

    by_id = {a.agent_id: a for a in C.CATALOG}
    engines, ge = state()

    if args.check:
        broken, ok = [], []
        for aid, e in sorted(engines.items()):
            good, detail = health(aid, e["name"])
            (ok if good else broken).append((aid, detail))
            print(f"  {'OK  ' if good else 'FAIL'} {aid:<20} {detail}")
        print(f"\ngrounded {len(ok)} | not grounded {len(broken)} | total {len(engines)}")
        return 0

    if args.all:
        # Probe before selecting. An engine that is already grounded is left
        # alone: --all means "every broken one", not "every one". Rebuilding a
        # working agent would delete a good engine to replace it with an
        # identical one, and would burn a quota slot mid-run for nothing.
        #
        # This selection used the liveness ping, which a toolless agent passes.
        # Run against an estate of toolless agents it printed
        # "already answering" for every one of them and reported broken: 0 --
        # the repair tool was blind to the defect it exists to repair.
        print("probing to find which engines are not grounded…")
        targets = []
        for aid in sorted(engines):
            if aid not in by_id:
                continue
            good, detail = health(aid, engines[aid]["name"])
            if not good:
                targets.append(aid)
            else:
                print(f"  skipping {aid} — grounded ({detail[:48]})")
        print(f"broken: {len(targets)}\n")
    else:
        targets = [a.strip() for a in args.agents.split(",") if a.strip()]
    if not targets:
        raise SystemExit("pass --agents, --all or --check")

    if args.confirm != CONFIRM:
        print(f"DRY RUN — {len(targets)} agents would be deleted and rebuilt.")
        print(f"Pass --confirm {CONFIRM} to proceed.\n")
        for aid in targets[:12]:
            print(f"  {aid:<20} engine {engines.get(aid,{}).get('name','—').split('/')[-1]}")
        if len(targets) > 12:
            print(f"  … and {len(targets)-12} more")
        return 0

    done = failed = 0
    for i, aid in enumerate(targets, 1):
        agent, old = by_id.get(aid), engines.get(aid)
        if not agent or not old:
            print(f"[{i}/{len(targets)}] {aid}: not in catalogue or has no engine — skipped")
            continue
        print(f"\n[{i}/{len(targets)}] {aid} — {agent.name}")

        entry = ge.get(aid)
        if entry:
            api(f"https://discoveryengine.googleapis.com/v1alpha/{entry['name']}", "DELETE")
        r = api(f"https://{REGION}-aiplatform.googleapis.com/v1beta1/{old['name']}?force=true", "DELETE")
        if "_http" in r:
            print(f"  delete failed {r['_http']} — leaving this agent alone")
            failed += 1
            continue

        try:
            res = create_engine(agent)
        except Exception as e:
            print(f"  rebuild FAILED: {type(e).__name__}: {str(e)[:140]}")
            failed += 1
            continue

        # Verify the property the rebuild exists to restore: that the agent
        # reads data. The old check sent "Reply with the single word: ok",
        # which a toolless agent -- the exact defect being rebuilt away --
        # passes cleanly, and then logged "verified".
        good, detail = verify_grounded.verify(agent.agent_id, res)
        print(f"  {'GROUNDED' if good else 'BUILT BUT NOT GROUNDED'}: {detail}")
        g = create_ge_entry(agent, res)
        print("  gemini enterprise repointed" if "_http" not in g
              else f"  GE FAILED {g['_http']}: {g['_body'][:120]}")
        done += good
        failed += (not good)

    print(f"\nrebuilt and grounded {done} | failed {failed} | of {len(targets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
