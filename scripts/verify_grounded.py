"""Post-rebuild verification that an engine actually reads data.

rebuild_engines.py verifies a new engine by sending it
`Reply with the single word: ok` and checking that something comes back.
That proves the engine is alive. It does not prove the agent can read
anything -- an agent with no tools attached answers it perfectly, which is
how 100 agents shipped answering confidently for weeks while unable to
query a single table.

This module verifies the property we actually care about: the engine calls
its tools and returns a number that matches live BigQuery.
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grounding_test import evaluate, load_probes  # noqa: E402


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

# A healthy agent makes 4-8 tool calls in ~25s. A toolless one answers in ~8s
# with none at all, which is the signature this exists to catch.
MIN_TOOL_CALLS = 1


class NoProbe(Exception):
    """No probe is defined for this agent, so it cannot be verified."""


def probe_for(agent_id: str):
    for p in load_probes():
        if p.agent_id == agent_id:
            return p
    raise NoProbe(agent_id)


def _token() -> str:
    return subprocess.run(["gcloud", "auth", "print-access-token"],
                          capture_output=True, text=True).stdout.strip()


def call(resource: str, message: str, timeout: int = 240) -> tuple[list[str], str]:
    """Returns (tool_call_names, reply_text). Raises on transport failure."""
    url = f"https://{REGION}-aiplatform.googleapis.com/v1beta1/{resource}:streamQuery?alt=sse"
    h = {"Authorization": f"Bearer {_token()}", "X-Goog-User-Project": PROJECT,
         "Content-Type": "application/json"}
    body = {"class_method": "stream_query",
            "input": {"message": message, "user_id": "rebuild-verify"}}
    raw = urllib.request.urlopen(
        urllib.request.Request(url, data=json.dumps(body).encode(), headers=h,
                               method="POST"), timeout=timeout).read().decode()
    calls, texts = [], []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        for prt in (ev.get("content") or {}).get("parts", []) or []:
            if prt.get("text"):
                texts.append(prt["text"])
            fc = prt.get("functionCall") or prt.get("function_call")
            if fc:
                calls.append(fc.get("name"))
    return calls, " ".join(texts)


def verdict(agent_id: str, calls: list[str], reply: str) -> tuple[bool, str]:
    """Score a captured response. Pure, so it is testable without a network."""
    if not calls:
        return False, ("NO TOOL CALLS — the agent answered without reading "
                       "anything; tools are not attached")
    if len(calls) < MIN_TOOL_CALLS:
        return False, f"only {len(calls)} tool call(s)"
    if not reply.strip():
        return False, f"{len(calls)} tool calls but an empty reply"
    r = evaluate(probe_for(agent_id), reply)
    if r.get("passed"):
        return True, f"grounded — {len(calls)} tool calls, matched {r['matched_number']}"
    failed = [k for k, v in r.get("checks", {}).items() if not v]
    return False, (f"{len(calls)} tool calls but ungrounded: {','.join(failed)} "
                   f"(live={r.get('truth')} answered={r.get('matched_number')})")


def verify(agent_id: str, resource: str) -> tuple[bool, str]:
    """Verify one freshly built engine. Never raises."""
    try:
        p = probe_for(agent_id)
    except NoProbe:
        return False, "no probe defined — cannot verify this agent reads data"
    try:
        calls, reply = call(resource, p.question)
    except urllib.error.HTTPError as e:
        return False, f"HTTP{e.code}"
    except Exception as e:
        return False, type(e).__name__
    return verdict(agent_id, calls, reply)
