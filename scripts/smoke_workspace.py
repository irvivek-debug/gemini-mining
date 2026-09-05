"""Functional gate: the deployed workspace can actually serve what it advertises.

Every check in the unit suite reads local files. None of them can see the
failure that actually reaches a viewer: the page ships a video filename, the
object was never uploaded under that name, and the browser gets a 404 on a
recording the sales script is describing out loud. That failure is invisible
locally -- `sales-assets.js` is correct, the file exists in `data/uat/videos/`,
and only the GCS object is missing. It is the expected state after every
re-record, because each new capture gets a new content hash.

Two stages, because they fail for different reasons:

  manifest -> GCS   every recording the served manifest names exists as an
                    object. This is the check that catches the 404.
  serving           the Flask app, run in-process against the real bucket,
                    returns the page, the manifest, and ranged video bytes.
                    This exercises the streaming code path, not just storage.

The app driven here -- apps/frontend/server/main.py -- is deployed as the Cloud
Run service `mining-agents-showcase`, NOT `mag-workspace`. The two are easy to
confuse: mag-workspace runs apps.workspace.server (FastAPI, no /videos route)
and is the service scripts/deploy_apps.py targets. Deploying mag-workspace does
nothing for the recordings. Redeploy this one with:

    gcloud run deploy mining-agents-showcase \
        --source apps/frontend/server --region us-central1 \
        --no-allow-unauthenticated

The deployed service sits behind IAP, so an end-to-end HTTPS check would need
either a service-account key or an interactive IAP sign-in. Neither belongs in
a script, so this deliberately stops at the bucket and the app, and says so.
Confirming the IAP sign-in itself is a human loading the page.

Usage:
    python scripts/smoke_workspace.py
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATIC = ROOT / "apps" / "frontend" / "server" / "static"
SERVED = STATIC / "sales-assets.js"
# The BigQuery-insight deep-dive ships its own four recordings. They are a
# separate capture harness with its own re-record cycle, so they break the
# same way and on a different schedule -- covering only sales-assets.js left
# four videos that no gate would have caught going missing.
BQ_SERVED = STATIC / "bq-insights.js"


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"{name} is unset. Copy .env.example to .env and fill it in "
            "(see docs/RECREATE.md)."
        )
    return value


BUCKET = _required("VIDEO_BUCKET")
EXPECTED = 100
BQ_EXPECTED = 4


def manifest() -> dict[str, dict]:
    text = SERVED.read_text()
    return json.loads(text[text.index("{"):text.rindex("}") + 1])


def bq_manifest() -> dict[str, dict]:
    """The bq deep-dive's scenarios, keyed by id, in the same shape."""
    text = BQ_SERVED.read_text()
    blob = json.loads(text[text.index("["):text.rindex("]") + 1])
    return {s.get("id") or s.get("slug") or str(i): s
            for i, s in enumerate(blob)}


def check_objects(assets: dict[str, dict]) -> list[str]:
    """Every /videos/<aid>/<file> in the manifest must exist in the bucket."""
    from google.cloud import storage

    bucket = storage.Client().bucket(BUCKET)
    bad: list[str] = []

    def probe(item: tuple[str, dict]) -> str | None:
        aid, entry = item
        path = entry.get("video") or ""
        if not path.startswith("/videos/"):
            return f"{aid}: manifest video path is {path!r}, expected /videos/..."
        if not bucket.blob(path.lstrip("/")).exists():
            return f"{aid}: gs://{BUCKET}{path} does not exist"
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        for res in pool.map(probe, sorted(assets.items())):
            if res:
                bad.append(res)
    return bad


def check_serving(assets: dict[str, dict]) -> list[str]:
    """Drive the real Flask app in-process: page, manifest, ranged video."""
    sys.path.insert(0, str(ROOT / "apps" / "frontend" / "server"))
    import main  # noqa: E402  -- imports google.cloud.storage and binds the bucket

    bad: list[str] = []
    client = main.app.test_client()

    r = client.get("/")
    if r.status_code != 200:
        bad.append(f"GET / -> {r.status_code}")

    r = client.get("/sales-assets.js")
    if r.status_code != 200:
        bad.append(f"GET /sales-assets.js -> {r.status_code}")

    # A ranged read of one real recording proves the GCS streaming path works,
    # including the 206 + Content-Range headers the <video> element needs.
    aid = sorted(assets)[0]
    path = assets[aid]["video"]
    r = client.get(path, headers={"Range": "bytes=0-1023"})
    if r.status_code != 206:
        bad.append(f"GET {path} Range:0-1023 -> {r.status_code}, expected 206")
    elif not r.headers.get("Content-Range"):
        bad.append(f"GET {path} returned 206 without a Content-Range header")
    else:
        print(f"      ranged read of {aid}: {r.headers['Content-Range']}")

    # A path that cannot exist must 404, not 200-with-empty-body.
    r = client.get("/videos/NOPE/does-not-exist.webm")
    if r.status_code != 404:
        bad.append(f"absent video -> {r.status_code}, expected 404")

    return bad


def main() -> int:
    assets = manifest()
    bq = bq_manifest()
    print(f"manifest: {len(assets)} agents from {SERVED.relative_to(ROOT)}")
    print(f"manifest: {len(bq)} bq scenarios from {BQ_SERVED.relative_to(ROOT)}")
    failures: list[str] = []
    if len(assets) != EXPECTED:
        failures.append(f"manifest carries {len(assets)} agents, expected {EXPECTED}")
    if len(bq) != BQ_EXPECTED:
        failures.append(f"bq manifest carries {len(bq)} scenarios, "
                        f"expected {BQ_EXPECTED}")

    missing = check_objects(assets)
    print(f"{'ok   ' if not missing else 'FAIL '} objects in GCS: "
          f"{len(assets) - len(missing)}/{len(assets)}")
    failures += missing

    bq_missing = check_objects(bq)
    print(f"{'ok   ' if not bq_missing else 'FAIL '} bq objects in GCS: "
          f"{len(bq) - len(bq_missing)}/{len(bq)}")
    failures += bq_missing

    serving = check_serving(assets)
    print(f"{'ok   ' if not serving else 'FAIL '} app serving "
          f"(page, manifest, ranged video, 404)")
    failures += serving

    if failures:
        print(f"\n{len(failures)} failure(s):")
        for f in failures[:20]:
            print("  " + f)
        if len(failures) > 20:
            print(f"  ... and {len(failures) - 20} more")
        return 1
    print("\nSMOKE_PASS  (IAP sign-in itself is verified by loading the page "
          "in a browser)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
