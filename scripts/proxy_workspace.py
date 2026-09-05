"""Open the deployed, private workspace in a local browser.

WHY THIS EXISTS
---------------
`scripts/deploy_apps.py` puts the workspace on Cloud Run behind an invoker
check, because the org policy `constraints/iam.allowedPolicyMemberDomains`
refuses the `allUsers` binding that would make it public. An authenticated
Cloud Run service does not redirect a browser to a sign-in page — it answers
403 and stops — so the deployed URL cannot simply be opened or sent to
someone, even by a person who holds run.invoker on it.

What is missing is not permission. It is a way to put a Google-signed token on
a request that a browser will not attach by itself. This module is that: a
loopback HTTP server that accepts an ordinary browser request, adds the
Authorization header, forwards it to the real service, and returns the real
response. Everything the browser renders came from the deployed revision, not
from the checkout — which is the whole point, since a static file server on
this laptop would show the same pages while proving nothing about the deploy.

`gcloud run services proxy` does the same job. It is the better tool when it
works; it is not usable here because it authenticates with the gcloud CLI
credential, which on this machine needs an interactive reauth that a
non-interactive session cannot answer. Application Default Credentials, which
this module uses instead, are valid.

WHY IT MINTS THE TOKEN ITSELF
------------------------------
Cloud Run rejects an OAuth access token with 401. It requires an OIDC identity
token, and `gcloud auth print-identity-token` reads the same CLI credential
that is unusable here. So the token is minted directly from the ADC refresh
grant: Google's token endpoint returns an `id_token` alongside the access
token when the request carries the ADC client id and secret, and that is what
the invoker check accepts.

Tokens last an hour, which is shorter than a demo. The cache below re-mints
one when it has under five minutes left, so a session does not fail halfway
through with a 401 that looks like a broken deploy.

    python scripts/proxy_workspace.py            # http://127.0.0.1:8804
    python scripts/proxy_workspace.py --port 9000
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

ADC_PATH = (
    pathlib.Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
)

# Re-mint this long before expiry. An agent call through /api/invoke can run
# for minutes, and a token that expires mid-flight surfaces as a 401 from the
# agent — indistinguishable, from the screen, from the agent being down.
REFRESH_MARGIN_SECONDS = 300

DEFAULT_PORT = 8804

# Headers that describe the hop, not the message. Forwarding them corrupts the
# response: a Content-Length copied from the upstream reply will not match a
# body the http.server layer re-frames, and a Transfer-Encoding we do not
# perform makes the browser wait for chunks that never come.
_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "transfer-encoding",
    "content-length",
    "content-encoding",
    "te",
    "trailer",
    "upgrade",
    "proxy-authorization",
    "proxy-authenticate",
    "host",
}


class _TokenCache:
    """One identity token, re-minted when it is close to expiring."""

    def __init__(self) -> None:
        self._token = ""
        self._expires_at = 0.0

    def get(self) -> str:
        if self._token and time.time() < self._expires_at - REFRESH_MARGIN_SECONDS:
            return self._token
        self._token, lifetime = _mint_identity_token()
        self._expires_at = time.time() + lifetime
        return self._token


def _mint_identity_token() -> tuple[str, float]:
    """Exchange the ADC refresh token for an OIDC identity token.

    Returns the token and its lifetime in seconds. Raises with a legible
    message rather than a traceback into urllib, because the two realistic
    failures here — no ADC file, and an ADC file whose refresh token has been
    revoked — both have a one-line fix the reader needs to see.
    """
    if not ADC_PATH.is_file():
        raise SystemExit(
            f"No application default credentials at {ADC_PATH}.\n"
            "Run: gcloud auth application-default login"
        )
    adc = json.loads(ADC_PATH.read_text())
    missing = [k for k in ("client_id", "client_secret", "refresh_token") if k not in adc]
    if missing:
        raise SystemExit(
            f"{ADC_PATH} has no {', '.join(missing)}. This module needs the user "
            "refresh grant; a service-account ADC file cannot mint an identity "
            "token this way."
        )

    body = urllib.parse.urlencode(
        {
            "client_id": adc["client_id"],
            "client_secret": adc["client_secret"],
            "refresh_token": adc["refresh_token"],
            "grant_type": "refresh_token",
        }
    ).encode()
    request = urllib.request.Request(
        TOKEN_ENDPOINT,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as error:  # pragma: no cover - network path
        raise SystemExit(
            f"Token endpoint refused the refresh grant ({error.code}). "
            "Re-run: gcloud auth application-default login\n"
            f"{error.read().decode(errors='replace')}"
        ) from error

    if "id_token" not in payload:
        raise SystemExit(
            "The token response carried no id_token. Cloud Run rejects the "
            "access token this returned instead, so there is nothing usable "
            "here."
        )
    return payload["id_token"], float(payload.get("expires_in", 3600))


# Small, because the unit that matters is one server-sent event and those are
# a few hundred bytes. This only bounds a single read; it does not make the
# relay wait for that many bytes to exist.
_STREAM_CHUNK_BYTES = 1024


def _is_stream(headers) -> bool:
    """Whether this reply is a live stream rather than a finished document.

    Decided on the content type alone. Every other reply these screens make —
    HTML, JS, JSON, the fonts — is a complete document that benefits from being
    relayed whole with its length intact, and only `/api/stream/{id}` declares
    `text/event-stream`. Widening this to "anything without a Content-Length"
    would drag in replies that merely arrived chunked and cost them a length
    they could have kept.
    """
    return "text/event-stream" in (headers.get("Content-Type") or "").lower()


def make_handler(target: str, tokens: _TokenCache) -> type[BaseHTTPRequestHandler]:
    """Build the request handler bound to one upstream service."""

    class Handler(BaseHTTPRequestHandler):
        # Cloud Run answers HTTP/1.1 and the browser opens several connections
        # for one page; the default HTTP/1.0 closes each after a single
        # response and makes a ten-asset page ten sequential round trips.
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:  # noqa: N802 - name fixed by BaseHTTPRequestHandler
            self._forward("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._forward("POST")

        def _forward(self, method: str) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else None

            headers = {
                key: value
                for key, value in self.headers.items()
                if key.lower() not in _HOP_BY_HOP
            }
            headers["Authorization"] = f"Bearer {tokens.get()}"

            request = urllib.request.Request(
                target + self.path, data=body, headers=headers, method=method
            )
            try:
                # No timeout. /api/invoke waits on an agent that may think for
                # minutes; a shorter one here would cut off a working call and
                # report it as a proxy failure.
                #
                # This comment used to claim the service was deployed with a
                # 600s ceiling. It never was — nothing set a timeout, so Cloud
                # Run's 300s default applied, and an S07 swarm run was measured
                # being cut off at 293.99s with no answer written. The ceiling
                # is now real and is set at the deploy, in
                # `scripts/deploy.py::deploy_command` (`--timeout=3600`), which
                # is the only place it can be stated as a fact rather than an
                # assumption.
                with urllib.request.urlopen(request) as response:
                    if _is_stream(response.headers):
                        self._relay_stream(response.status, response.headers, response)
                    else:
                        self._relay(response.status, response.headers, response.read())
            except urllib.error.HTTPError as error:
                # A 403 here is the interesting one: it means the identity is
                # authenticated but not an invoker on this service, which is a
                # different fix from a 401.
                self._relay(error.code, error.headers, error.read())
            except urllib.error.URLError as error:  # pragma: no cover - network
                self._relay(
                    502,
                    {"Content-Type": "text/plain; charset=utf-8"},
                    f"proxy could not reach {target}: {error.reason}".encode(),
                )

        def _relay_stream(self, status: int, headers, response) -> None:
            """Pass an event stream through as it arrives, not once it ends.

            `/api/stream/{id}` reports each step while the agent is still
            working, and that running commentary is the feature — a reader who
            asked a question that takes a hundred seconds is told what is
            happening for those hundred seconds. Collecting the body first
            would deliver every step at the end, after the wait it existed to
            explain.

            The body is therefore delimited by the connection closing rather
            than by a length: the length is unknowable until the agent has
            finished, which is the very thing not being waited for. That is why
            `Connection: close` goes out with it, and why each write is
            flushed — anything still sitting in a buffer has not been streamed.
            """
            self.send_response(status)
            for key, value in headers.items():
                if key.lower() not in _HOP_BY_HOP:
                    self.send_header(key, value)
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            while True:
                # read1, not read: read blocks until it can fill the buffer,
                # which for a slow stream means holding events back until
                # enough of them exist to fill it.
                chunk = response.read1(_STREAM_CHUNK_BYTES)
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    # The reader navigated away or asked something else. The
                    # upstream call is already billed and cannot be recalled;
                    # what matters is that this thread stops rather than
                    # writing into a closed socket for the rest of the run.
                    break

        def _relay(self, status: int, headers, body: bytes) -> None:
            self.send_response(status)
            for key, value in (
                headers.items() if hasattr(headers, "items") else headers
            ):
                if key.lower() not in _HOP_BY_HOP:
                    self.send_header(key, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:
            # One line per request, on stderr, without the date noise the
            # default format prints. Useful because a 404 on an asset is the
            # failure this proxy is most often used to diagnose.
            sys.stderr.write(f"{self.command} {self.path} -> {args[1]}\n")

    return Handler


def serve(target: str, port: int = DEFAULT_PORT) -> None:
    """Run the proxy until interrupted."""
    tokens = _TokenCache()
    # Mint once up front so a bad credential fails here, with its own message,
    # rather than as a 502 on the first page load.
    tokens.get()

    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(target, tokens))
    print(f"proxying {target}")
    print(f"open http://127.0.0.1:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()


def _default_target() -> str:
    """The deployed workspace URL, read from Cloud Run rather than hardcoded.

    Imported lazily and tolerantly: the URL is stable enough that a caller who
    passes --target should not need gcloud on PATH at all.
    """
    import subprocess

    from mining_agents.config import settings
    from scripts.deploy_apps import SERVICE
    from scripts.deploy import REGION

    result = subprocess.run(
        [
            "gcloud", "run", "services", "describe", SERVICE,
            f"--region={REGION}",
            f"--project={settings().project_id}",
            "--format=value(status.url)",
        ],
        capture_output=True,
        text=True,
    )
    url = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    if not url.startswith("https://"):
        raise SystemExit(
            f"Could not read the URL of {SERVICE} from Cloud Run.\n"
            f"{result.stderr.strip()}\n"
            "Pass it explicitly: --target https://...run.app"
        )
    return url


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--target",
        default="",
        help="Upstream service URL. Read from Cloud Run when omitted.",
    )
    args = parser.parse_args()
    serve(args.target or _default_target(), args.port)
