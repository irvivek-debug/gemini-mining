"""The proxy must stream a stream, not collect it and hand over the total.

WHY THIS FILE EXISTS
--------------------
`scripts/proxy_workspace.py` is how the private, deployed workspace is opened
in a browser, so every live check of the chat sidecar goes through it. It read
the upstream reply with a single `response.read()`, which returns when the
upstream body is *complete*. For a page that is fine. For `/api/stream/{id}`,
whose whole purpose is to say "reading the machine register" while the agent is
still thinking, it is not: the reader watches an empty pane for the entire run
and then receives every step at once, at the end, if at all.

That failure is invisible to a test that only checks the final bytes — the
totals match either way. So what is asserted here is *timing*: a fake upstream
holds its connection open after the first event, and the assertion is that the
proxy has already delivered that event. Only a streaming relay can pass.
"""
from __future__ import annotations

import http.client
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from scripts.proxy_workspace import make_handler


class _StubTokens:
    """Stands in for the ADC-backed cache; no network, no credentials."""

    def get(self) -> str:
        return "stub-identity-token"


def _free_port(server: ThreadingHTTPServer) -> int:
    return server.server_address[1]


@pytest.fixture()
def upstream():
    """An SSE source that emits one event, then stalls until released.

    The stall is the point. It reproduces the state a real agent is in for most
    of a run: the first step has been reported and the answer has not.
    """
    released = threading.Event()
    finished = threading.Event()

    class Upstream(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:  # noqa: N802 - name fixed by the base class
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(b'data: {"kind":"step","text":"first"}\n\n')
            self.wfile.flush()
            # Held open exactly as a thinking agent holds it open.
            released.wait(timeout=10)
            self.wfile.write(b'data: {"kind":"text","text":"done"}\n\n')
            self.wfile.flush()
            finished.set()

        def log_message(self, format: str, *args) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server, released, finished
    released.set()
    server.shutdown()
    server.server_close()


@pytest.fixture()
def proxy(upstream):
    server, released, finished = upstream
    target = f"http://127.0.0.1:{_free_port(server)}"
    proxy_server = ThreadingHTTPServer(
        ("127.0.0.1", 0), make_handler(target, _StubTokens())
    )
    threading.Thread(target=proxy_server.serve_forever, daemon=True).start()
    yield proxy_server, released, finished
    proxy_server.shutdown()
    proxy_server.server_close()


def test_first_event_arrives_before_the_upstream_finishes(proxy):
    """The reader sees step one while the agent is still working on step two."""
    proxy_server, released, finished = proxy
    connection = http.client.HTTPConnection("127.0.0.1", _free_port(proxy_server))
    connection.request("GET", "/api/stream/S01?prompt=hello")
    response = connection.getresponse()

    assert response.status == 200
    assert response.getheader("Content-Type") == "text/event-stream"

    # Nothing has released the upstream, so it is still mid-run. A buffering
    # relay blocks here until the read timeout; a streaming one answers now.
    response.fp.raw._sock.settimeout(5)
    first = response.fp.readline()

    assert not finished.is_set(), (
        "the upstream had already finished, so this proves nothing about "
        "streaming — the fixture is broken, not the proxy"
    )
    assert b'"first"' in first

    released.set()
    connection.close()


def test_a_streamed_reply_carries_no_content_length(proxy):
    """Content-Length on a stream is the tell that the whole body was collected.

    It cannot be computed without reading to the end, so its presence means the
    relay waited. Length-delimited is also the one framing a browser's
    EventSource cannot begin parsing early.
    """
    proxy_server, released, _finished = proxy
    connection = http.client.HTTPConnection("127.0.0.1", _free_port(proxy_server))
    connection.request("GET", "/api/stream/S01?prompt=hello")
    response = connection.getresponse()

    assert response.getheader("Content-Length") is None

    released.set()
    connection.close()


def test_an_ordinary_page_is_still_relayed_whole(proxy):
    """The streaming path must not cost the pages their Content-Length.

    Every asset on these screens is length-delimited today, and a browser uses
    that to know a file arrived intact rather than truncated by a dropped
    connection. Only the stream gives that up, and only because it must.
    """
    proxy_server, released, _finished = proxy
    released.set()  # this fixture's upstream is SSE; released so it completes

    body = b"<!doctype html><title>page</title>"

    class Page(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:
            pass

    page_server = ThreadingHTTPServer(("127.0.0.1", 0), Page)
    threading.Thread(target=page_server.serve_forever, daemon=True).start()
    page_proxy = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        make_handler(f"http://127.0.0.1:{_free_port(page_server)}", _StubTokens()),
    )
    threading.Thread(target=page_proxy.serve_forever, daemon=True).start()
    try:
        connection = http.client.HTTPConnection("127.0.0.1", _free_port(page_proxy))
        connection.request("GET", "/workspace/persona.html")
        response = connection.getresponse()
        assert response.getheader("Content-Length") == str(len(body))
        assert response.read() == body
        connection.close()
    finally:
        page_proxy.shutdown()
        page_proxy.server_close()
        page_server.shutdown()
        page_server.server_close()
