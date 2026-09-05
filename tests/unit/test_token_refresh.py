"""A long run must not outlive its access token.

probe_group.py fetched the token once at import and reused it for the whole
run. Google access tokens last about an hour; the deep-solver group alone
takes longer than that. The overnight rebuild 401'd partway through and
lost 19 agents, and a later rescore failed D39 and D40 at 1.3s each with
HTTP 401 -- read as "the credential expired" both times, when the real
cause was our own one-shot token.
"""
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "scripts" / "probe_group.py"


def test_headers_are_rebuilt_per_request_not_captured_once():
    src = SRC.read_text()
    # the request must call the accessor, not close over a startup snapshot
    assert re.search(r"headers=auth_headers\(\)", src), \
        "requests use a token captured at import; a long run will 401 partway"


def test_a_ttl_shorter_than_the_token_lifetime():
    src = SRC.read_text()
    m = re.search(r"_TOKEN_TTL_S\s*=\s*(\d+)\s*\*\s*60", src)
    assert m, "no TTL on the cached token"
    minutes = int(m.group(1))
    assert minutes < 60, f"TTL {minutes}m does not renew inside the ~60m token life"
    assert minutes >= 5, "TTL so short it shells out to gcloud on nearly every call"


def test_an_empty_token_raises_rather_than_sending_bearer_none():
    """Silently sending `Bearer ` yields a 401 that reads as expiry, not as
    'you are not logged in' -- the same misdiagnosis this file exists for."""
    src = SRC.read_text()
    fn = next(n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "auth_headers")
    body = ast.get_source_segment(src, fn)
    assert "raise" in body, "an empty token is passed through as a Bearer header"
    assert "gcloud auth login" in body, "the error does not say how to fix it"


def test_the_cache_is_actually_reused_within_the_ttl(monkeypatch):
    """Otherwise every request shells out to gcloud -- 95 agents x 2 calls."""
    import importlib.util
    calls = {"n": 0}

    src = SRC.read_text()
    fn_src = ast.get_source_segment(src, next(
        n for n in ast.walk(ast.parse(src))
        if isinstance(n, ast.FunctionDef) and n.name == "auth_headers"))

    # PROJECT is a module-level free variable of auth_headers (it fills the
    # X-Goog-User-Project header), so the exec namespace must supply it.
    ns = {"time": __import__("time"), "_TOKEN_TTL_S": 45 * 60, "_tok_cache": {},
          "PROJECT": "test-project",
          "subprocess": type("S", (), {"run": staticmethod(
              lambda *a, **k: calls.update(n=calls["n"] + 1) or
              type("R", (), {"stdout": "tok-value\n"})())})}
    exec(fn_src, ns)
    ns["auth_headers"]()
    ns["auth_headers"]()
    ns["auth_headers"]()
    assert calls["n"] == 1, f"token fetched {calls['n']} times inside the TTL"


def test_cache_expires_past_the_ttl():
    import ast as _ast
    src = SRC.read_text()
    fn_src = _ast.get_source_segment(src, next(
        n for n in _ast.walk(_ast.parse(src))
        if isinstance(n, _ast.FunctionDef) and n.name == "auth_headers"))
    calls = {"n": 0}
    clock = {"t": 1000.0}
    ns = {"time": type("T", (), {"time": staticmethod(lambda: clock["t"])}),
          "_TOKEN_TTL_S": 45 * 60, "_tok_cache": {},
          "PROJECT": "test-project",
          "subprocess": type("S", (), {"run": staticmethod(
              lambda *a, **k: calls.update(n=calls["n"] + 1) or
              type("R", (), {"stdout": "tok\n"})())})}
    exec(fn_src, ns)
    ns["auth_headers"]()
    clock["t"] += 46 * 60          # past the TTL, inside a long run
    ns["auth_headers"]()
    assert calls["n"] == 2, "token was not renewed after the TTL elapsed"
