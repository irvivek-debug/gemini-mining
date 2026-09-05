"""Gate: /api/stream relays the agent's event stream without editing it.

A fake upstream, never Cloud Run. The two things worth proving here are that
chunks arrive byte-for-byte in order — a proxy that reframes SSE breaks the
browser's parser in ways that only show up under load — and that every failure
mode reaches the screen as something the screen can render, including the one
that happens after the status code has already been sent.
"""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from apps.workspace import server

CHUNKS = [
    b'data: {"content": {"parts": [{"text": "Looking"}]}}\n\n',
    b'data: {"content": {"parts": [{"functionCall": {"id": "1", "name": "bq_query", '
    b'"args": {"sql": "SELECT 1 FROM `mining_data.assets`"}}}]}}\n\n',
    b'data: {"content": {"parts": [{"text": " done."}]}}\n\n',
]


@pytest.fixture
def upstream(monkeypatch):
    """A fake agent container, plus a record of what the proxy asked it."""
    seen = {"requests": [], "closed": False, "session_status": 200, "run_status": 200}

    async def body():
        try:
            for chunk in CHUNKS:
                yield chunk
        finally:
            seen["closed"] = True

    def handle(request: httpx.Request) -> httpx.Response:
        seen["requests"].append((request.method, request.url.path))
        if request.url.path.endswith("/run_sse"):
            seen["run_body"] = json.loads(request.content)
            if seen["run_status"] != 200:
                return httpx.Response(seen["run_status"], text="upstream said no")
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream; charset=utf-8"},
                content=body(),
            )
        return httpx.Response(seen["session_status"], json={})

    def fake_client(base, token, timeout):
        seen["timeout"] = timeout
        return httpx.AsyncClient(
            base_url=base,
            timeout=timeout,
            headers={"Authorization": f"Bearer {token}"},
            transport=httpx.MockTransport(handle),
        )

    monkeypatch.setattr(server, "_agent_client", fake_client)
    monkeypatch.setattr(server, "_services", lambda: {"mag-s01": "https://fake.invalid"})
    monkeypatch.setattr(server, "_identity_token", lambda audience: "fake-token")
    return seen


@pytest.fixture
def client():
    return TestClient(server.app)


def test_the_chunks_arrive_byte_for_byte_in_order(client, upstream):
    with client.stream("GET", "/api/stream/S01?prompt=hello") as reply:
        assert reply.status_code == 200
        assert reply.headers["content-type"].startswith("text/event-stream")
        body = b"".join(reply.iter_raw())
    assert b"".join(CHUNKS) in body


def test_the_stream_ends_with_one_terminal_event(client, upstream):
    """EventSource reconnects on close, so the client needs an explicit end."""
    with client.stream("GET", "/api/stream/S01?prompt=hello") as reply:
        body = b"".join(reply.iter_raw())
    assert body.count(b"event: proxy-done") == 1
    assert body.endswith(b"event: proxy-done\ndata: {}\n\n")


def test_the_session_is_created_before_the_run(client, upstream):
    with client.stream("GET", "/api/stream/S01?prompt=hello") as reply:
        b"".join(reply.iter_raw())
    paths = [path for _, path in upstream["requests"]]
    assert paths[0].startswith("/apps/S01/users/")
    assert paths[1] == "/run_sse"
    assert upstream["run_body"]["app_name"] == "S01"
    assert upstream["run_body"]["new_message"]["parts"][0]["text"] == "hello"


def test_a_400_on_session_creation_is_not_an_error(client, upstream):
    """Re-creating an existing session answers 400. It means it is already there."""
    upstream["session_status"] = 400
    with client.stream("GET", "/api/stream/S01?prompt=hello") as reply:
        assert reply.status_code == 200
        body = b"".join(reply.iter_raw())
    assert b"".join(CHUNKS) in body


def test_no_credentials_answers_503_in_the_shape_invoke_uses(client, monkeypatch):
    def refuse():
        raise server.NotConnected("identity token", "no credentials here")

    monkeypatch.setattr(server, "_services", refuse)
    reply = client.get("/api/stream/S01?prompt=hello")
    assert reply.status_code == 503
    assert reply.json() == {
        "connected": False,
        "stage": "identity token",
        "detail": "no credentials here",
    }


def test_an_unknown_agent_is_refused_before_any_upstream_call(client, upstream):
    reply = client.get("/api/stream/S01-SP1?prompt=hello")
    assert reply.status_code == 404
    assert reply.json()["connected"] is False
    assert upstream["requests"] == []


def test_an_empty_prompt_is_refused(client, upstream):
    reply = client.get("/api/stream/S01?prompt=%20")
    assert reply.status_code == 400
    assert upstream["requests"] == []


def test_a_failure_after_the_stream_opened_arrives_as_an_event(client, upstream):
    """The status code is already sent by then, so the failure has to be data."""
    upstream["run_status"] = 500
    with client.stream("GET", "/api/stream/S01?prompt=hello") as reply:
        assert reply.status_code == 200
        body = b"".join(reply.iter_raw())
    assert b"event: proxy-error" in body
    assert b"upstream said no" in body
    assert body.endswith(b"event: proxy-done\ndata: {}\n\n")


def test_a_client_that_leaves_closes_the_upstream_connection(client, upstream):
    with client.stream("GET", "/api/stream/S01?prompt=hello") as reply:
        next(reply.iter_raw())
    assert upstream["closed"] is True


# --- Finding 1: each route's timeout is explicit and correct ---

def test_stream_route_uses_unbounded_timeout(client, upstream):
    """The streaming route must not impose a finite socket timeout.

    A 100-second answer would be cut off by any shorter ceiling here, and the
    browser would see a proxy failure rather than a complete response. The real
    ceiling is the Cloud Run service's own request timeout.
    """
    with client.stream("GET", "/api/stream/S01?prompt=hello") as reply:
        b"".join(reply.iter_raw())
    assert upstream["timeout"] is None


def test_invoke_route_uses_300s_timeout(client, upstream, monkeypatch):
    """The buffered invoke route must keep a finite socket timeout.

    Without it a half-open TCP connection to a hung upstream would never
    be recovered from the proxy's side. Cloud Run's request timeout bounds
    the upstream's *execution*; it does not close the proxy's outbound socket.
    """
    monkeypatch.setattr(server, "_services", lambda: {"mag-s01": "https://fake.invalid"})
    monkeypatch.setattr(server, "_identity_token", lambda audience: "fake-token")
    client.post(
        "/api/invoke/S01",
        json={"prompt": "hello", "user_id": "u1", "session_id": "s1"},
    )
    assert upstream["timeout"] == 300


# --- Finding 2: proxy-done fires even when an exception raises mid-stream ---

def test_proxy_done_fires_after_mid_stream_exception(client, monkeypatch):
    """An exception raised after chunks have already been relayed must not
    suppress proxy-done. Without it EventSource silently re-asks the same
    100-second question forever, burning real model tokens on every loop.

    The realistic shape is a network-level error (httpx.ReadError) raised
    partway through aiter_raw(), after the status code is already sent.
    """
    seen = {"requests": [], "closed": False}

    async def body_that_explodes():
        try:
            yield CHUNKS[0]
            yield CHUNKS[1]
            raise httpx.ReadError("simulated mid-stream network failure", request=None)
        finally:
            seen["closed"] = True

    def handle(request: httpx.Request) -> httpx.Response:
        seen["requests"].append((request.method, request.url.path))
        if request.url.path.endswith("/run_sse"):
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream; charset=utf-8"},
                content=body_that_explodes(),
            )
        return httpx.Response(200, json={})

    def fake_client(base, token, timeout):
        return httpx.AsyncClient(
            base_url=base,
            timeout=timeout,
            headers={"Authorization": f"Bearer {token}"},
            transport=httpx.MockTransport(handle),
        )

    monkeypatch.setattr(server, "_agent_client", fake_client)
    monkeypatch.setattr(server, "_services", lambda: {"mag-s01": "https://fake.invalid"})
    monkeypatch.setattr(server, "_identity_token", lambda audience: "fake-token")

    tc = TestClient(server.app)
    with tc.stream("GET", "/api/stream/S01?prompt=hello") as reply:
        assert reply.status_code == 200
        body = b"".join(reply.iter_raw())

    # The error event must arrive so the browser knows something went wrong.
    assert b"event: proxy-error" in body
    assert b"simulated mid-stream network failure" in body

    # proxy-done must fire exactly once as the last event, so EventSource does
    # not reconnect and silently re-ask the question.
    assert body.count(b"event: proxy-done") == 1
    assert body.endswith(b"event: proxy-done\ndata: {}\n\n")
