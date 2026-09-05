"""Every sales asset must point at the recording its text describes.

The builder used to choose a video with `sorted(dir.glob("*.webm"))[0]`.
Agent directories accumulate takes -- 37 stale ones were on disk after the
estate re-record -- so the alphabetically-first file is frequently from an
older run. Fourteen of a hundred entries ended up pairing a fresh
transcript with a different capture, and two of those captures were failed
runs that show a blank answer pane. Nothing in the artifact reveals this:
the page plays, the text reads well, and only the video is wrong.

The ledger row is the single source of truth -- it holds the reply the
entry quotes and the video recorded in the same session.
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
ASSETS = ROOT / "apps" / "frontend" / "sales-assets.js"
LEDGER = ROOT / "data" / "uat" / "ledger.jsonl"


def _ledger_last() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for line in LEDGER.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            rows[r["agent_id"]] = r
    return rows


def _assets() -> dict[str, dict]:
    text = ASSETS.read_text()
    return json.loads(text[text.index("{"):text.rindex("}") + 1])


def test_every_asset_names_the_ledger_video() -> None:
    assets, ledger = _assets(), _ledger_last()
    assert len(assets) > 50, f"only {len(assets)} assets — the build looks truncated"

    wrong = []
    for aid, entry in assets.items():
        row = ledger.get(aid)
        assert row is not None, f"{aid} has an asset but no ledger row"
        want = pathlib.Path(row["video"]).name
        got = pathlib.Path(entry["video"]).name
        if want != got:
            wrong.append(f"{aid}: shows {got}, ledger recorded {want}")

    assert wrong == [], (
        "sales assets reference a video other than the one whose reply they "
        "quote:\n  " + "\n  ".join(wrong)
    )


def test_every_asset_video_exists_on_disk() -> None:
    """A named-but-absent file 404s in the browser and passes every text check."""
    missing = [
        f"{aid}: {entry['video']}"
        for aid, entry in _assets().items()
        if not (ROOT / "apps" / "frontend" / entry["video"]).resolve().exists()
    ]
    assert missing == [], "sales assets name videos that do not exist:\n  " + \
        "\n  ".join(missing)
