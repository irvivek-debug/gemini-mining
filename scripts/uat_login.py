"""Open a Playwright-owned browser and wait for a human to sign in.

WHY A SEPARATE PROFILE
Video recording requires Playwright to own the browser context -- record_video_dir
is set at context creation and cannot be attached to a browser someone else
launched. So the MCP browser that was signed into by hand cannot be recorded,
and this script brings up its own Chromium with a persistent profile instead.

The profile is what makes one sign-in enough: the session lives in
data/uat/.profile and is reused by every later run, including after a restart.
No credential is read, stored or transmitted by this script -- the human types
into a real Google page and Chromium keeps the cookie exactly as it would
normally.
"""
from __future__ import annotations

import pathlib
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
import sys
# Optional target dir: a second parallel worker needs its own independently
# minted session — Google invalidates cloned profiles, and signing in again
# to the same account can rotate older sessions out.
PROFILE = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "uat" / ".profile"
HOME = ("https://vertexaisearch.cloud.google.com/home/cid/"
        "YOUR_AGENTSPACE_CID?hl=en_US")
DEADLINE_SECONDS = 900


def main() -> int:
    PROFILE.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
            headless=False,
            viewport={"width": 1440, "height": 900},
            args=["--window-size=1460,980"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(HOME, wait_until="domcontentloaded")

        print("A browser window is open. Sign in there.")
        print("Waiting for the Gemini Enterprise home page…", flush=True)

        started = time.time()
        while time.time() - started < DEADLINE_SECONDS:
            url = page.url
            if "accounts.google.com" not in url and "vertexaisearch" in url:
                # Landing on the app URL is necessary but not sufficient -- the
                # shell renders before the agent list does. Wait for something
                # only a signed-in session shows.
                try:
                    page.get_by_role("link", name="Agents").first.wait_for(timeout=8000)
                    print(f"SIGNED IN — session stored in {PROFILE.relative_to(ROOT)}")
                    ctx.close()
                    return 0
                except Exception:
                    pass
            time.sleep(3)

        print("TIMED OUT waiting for sign-in; nothing was stored.")
        ctx.close()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
