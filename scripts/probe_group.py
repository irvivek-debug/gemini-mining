"""Run the grounding probe against every agent in a group."""
import sys, json, subprocess, urllib.request, re, time
sys.path.insert(0, "scripts")
from grounding_test import load_probes, evaluate
from register_agents import ENGINE_API, PROJECT, PROJECT_NUMBER, paged
import probe_set

group = sys.argv[1] if len(sys.argv) > 1 else ""
eng = {}
for e in paged(ENGINE_API, "reasoningEngines"):
    m = re.search(r"\(([A-Z0-9][A-Z0-9\-]*)\)\s*$", e.get("displayName", ""))
    if m:
        eng[m.group(1)] = e["name"].split("/")[-1]
# Google access tokens last about an hour. This was fetched once at startup
# and reused for the whole run, so any run longer than the token's life 401'd
# partway through -- which is what killed the deep-solver rebuild overnight
# and failed D39/D40 here at 1.3s. Re-fetch on a TTL well inside that hour.
_TOKEN_TTL_S = 45 * 60
_tok_cache: dict[str, float | str] = {}


def auth_headers() -> dict:
    now = time.time()
    if not _tok_cache or now - _tok_cache.get("at", 0) > _TOKEN_TTL_S:
        t = subprocess.run(["gcloud", "auth", "print-access-token"],
                           capture_output=True, text=True).stdout.strip()
        if not t:
            raise RuntimeError("no access token — run `gcloud auth login`")
        _tok_cache.update({"tok": t, "at": now})
    return {"Authorization": f"Bearer {_tok_cache['tok']}",
            "X-Goog-User-Project": PROJECT,
            "Content-Type": "application/json"}


H = auth_headers()
OUT = __import__("pathlib").Path("data/grounding/results.jsonl")
OUT.parent.mkdir(parents=True, exist_ok=True)
results = []


def probe_once(p, eng, H):
    """One probe attempt against one agent. Never raises."""
    url = (f"https://us-central1-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_NUMBER}"
           f"/locations/us-central1/reasoningEngines/{eng[p.agent_id]}:streamQuery?alt=sse")
    body = {"class_method": "stream_query",
            "input": {"message": p.question, "user_id": "grounding"}}
    t0 = time.time()
    try:
        raw = urllib.request.urlopen(urllib.request.Request(
            url, data=json.dumps(body).encode(), headers=auth_headers(),
            method="POST"),
            timeout=300).read().decode()
    except Exception as e:
        return {"agent_id": p.agent_id, "passed": False,
                "checks": {"transport": False},
                "transport_error": f"{type(e).__name__}: {str(e)[:300]}",
                "latency_s": round(time.time() - t0, 1),
                "question": p.question, "tool_calls": 0, "tool_names": [],
                "tool_errors": [], "reply_chars": 0, "reply": "",
                "truth": None, "matched_number": None, "tables_named": [],
                "derived": []}
    calls, txt, tool_errors = [], [], []
    for ln in raw.splitlines():
        if not ln.strip():
            continue
        try:
            ev = json.loads(ln)
        except Exception:
            continue
        for prt in (ev.get("content") or {}).get("parts", []) or []:
            if prt.get("text"):
                txt.append(prt["text"])
            fc = prt.get("functionCall") or prt.get("function_call")
            if fc:
                calls.append(fc.get("name"))
            fr = prt.get("functionResponse") or prt.get("function_response")
            if fr:
                blob = json.dumps(fr.get("response") or {})[:400]
                if any(w in blob.lower() for w in
                       ("error", "denied", "not found", "invalid", "exceed")):
                    tool_errors.append(f"{fr.get('name')}: {blob}")
    reply = " ".join(txt)
    r = evaluate(p, reply)
    # Evidence, so a failure is diagnosable without re-running it. The first
    # version of this harness stored only pass/fail and a number.
    r.update({"agent_id": p.agent_id, "tool_calls": len(calls),
              "latency_s": round(time.time() - t0, 1),
              "question": p.question, "tool_names": calls,
              "tool_errors": tool_errors, "reply_chars": len(reply),
              "reply": reply[:4000]})
    return r

# probes.json holds every group now, so select rather than scan-and-skip.
# A bare startswith() also lets a short group id swallow a longer one.
_want = set(probe_set.select_group(group)) if group else None
for p in load_probes():
    if _want is not None and p.agent_id not in _want:
        continue
    if p.agent_id not in eng:
        print(f"  SKIP {p.agent_id}: not registered"); continue
    r = probe_once(p, eng, H)
    # A single failure cannot tell a broken agent from a bad minute. An agent
    # that stalled after one tool call in 67s passed the identical probe
    # minutes later. Retry once, and record which kind of failure it was.
    if not r.get("passed"):
        first = {"tool_calls": r.get("tool_calls"), "latency_s": r.get("latency_s"),
                 "checks": r.get("checks"), "reply_chars": r.get("reply_chars"),
                 "tool_errors": r.get("tool_errors")}
        time.sleep(20)
        r2 = probe_once(p, eng, H)
        r2["first_attempt"] = first
        r2["failure_kind"] = "transient" if r2.get("passed") else "persistent"
        r = r2
    results.append(r)
    with OUT.open("a") as fh:
        fh.write(json.dumps(r) + "\n")
        fh.flush()
    bad = [k for k, v in r.get("checks", {}).items() if not v]
    kind = r.get("failure_kind", "")
    print(f"  {'PASS' if r.get('passed') else 'FAIL'} {p.agent_id:<18} "
          f"tools={r.get('tool_calls', 0):<2} {r.get('latency_s', 0):>5}s  "
          f"truth={r.get('truth')} got={r.get('matched_number')}  "
          f"{','.join(bad)}{' [' + kind + ']' if kind else ''}", flush=True)
print(f"\n  {sum(r['passed'] for r in results)}/{len(results)} grounded")
