"""Showcase server: static front end + GCS-backed video streaming.

Reference pattern: the application runs on Cloud Run behind IAP; the
recordings live in GCS. The browser never talks to the bucket — this app
streams /videos/* from GCS using its runtime service account, so access
control lives in exactly one place (IAP's domain policy) and video range
requests (seeking) work.
"""
from __future__ import annotations

import os

from flask import Flask, Response, abort, request, send_from_directory
from google.cloud import storage

def _required_bucket() -> str:
    """The video bucket is never guessed: a placeholder default would surface
    as a confusing 404 on every recording instead of a clear startup error."""
    bucket = os.environ.get("VIDEO_BUCKET", "").strip()
    if not bucket:
        raise RuntimeError(
            "VIDEO_BUCKET is unset. Copy .env.example to .env and set it to "
            "your own GCS bucket name (see docs/RECREATE.md)."
        )
    return bucket


BUCKET = _required_bucket()
STATIC = os.path.join(os.path.dirname(__file__), "static")
CHUNK = 4 * 1024 * 1024

app = Flask(__name__)
_client = storage.Client()
_bucket = _client.bucket(BUCKET)


@app.get("/")
def index():
    return send_from_directory(STATIC, "index.html")


@app.get("/<path:name>")
def assets(name: str):
    if name.startswith("videos/"):
        return video(name[len("videos/"):])
    return send_from_directory(STATIC, name)


def video(path: str):
    if ".." in path:
        abort(404)
    blob = _bucket.blob(f"videos/{path}")
    if not blob.exists():
        abort(404)
    blob.reload()
    size = blob.size
    rng = request.headers.get("Range")
    start, end = 0, size - 1
    status = 200
    if rng and rng.startswith("bytes="):
        part = rng.split("=", 1)[1].split("-")
        start = int(part[0]) if part[0] else 0
        end = int(part[1]) if len(part) > 1 and part[1] else min(start + CHUNK - 1, size - 1)
        end = min(end, size - 1)
        status = 206
    data = blob.download_as_bytes(start=start, end=end)
    headers = {
        "Content-Type": "video/webm",
        "Accept-Ranges": "bytes",
        "Content-Length": str(len(data)),
        "Cache-Control": "private, max-age=3600",
    }
    if status == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    return Response(data, status=status, headers=headers)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
