"""Record the four BigQuery Data Agent showcase scenarios, on video.

One conversation per scenario in the console's Chat-with-your-data surface,
driving the prompt arcs from reports/bq_data_agent_showcase_prd.md. Each
video ends with the guided review scroll. The transcript of every
conversation is saved beside the video for the ground-truth cross-check —
a number spoken in a sales video must match SQL, or the video is re-cut.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROFILE = ROOT / "data" / "uat" / ".profile"
OUT = ROOT / "data" / "uat" / "bq_scenarios"


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"{name} is unset. Copy .env.example to .env and fill it in "
            "(see docs/RECREATE.md)."
        )
    return value


PROJECT = _required("GOOGLE_CLOUD_PROJECT")
BQ_URL = ("https://console.cloud.google.com/bigquery/agents_hub;"
          f"agentsPath=%2Fbq%2Fagents-catalog?project={PROJECT}")
AGENT_CARD = "Mining Operations Insight Agent"

SCENARIOS = {
  "S1-grade-reconciliation": [
    "What is our planned head grade by rock type, and how many blocks does the resource model hold?",
    "What head grades did the assay lab actually measure, by logged rock type?",
    "Reconcile planned against assayed head grade by rock type. Where is the resource model most wrong, in percentage points?",
    "For that rock type: how many blocks are affected, and what is the estimated contained metal at risk if the assayed grade is the truth? Show the calculation step by step in plain numbers — no formula notation.",
    "Three sentences for the mine GM: what is misestimated, by how much, and the first corrective action.",
  ],
  "S2-anomaly-hunt": [
    "What does our plant telemetry cover, and how many readings per instrument metric?",
    "Trend the busiest metric as a daily average. Any drift a reliability engineer should worry about?",
    "Hunt for anomalous readings across the plant: anything beyond three standard deviations for its metric. How many, and which assets are the worst offenders?",
    "For the worst offender: show its anomalies in time order. Developing fault or bad sensor? Argue from the data.",
    "Write tomorrow morning's shift-handover paragraph for the plant supervisor.",
  ],
  "S3-parts-failure-graph": [
    "Which spare parts are at stock-out risk right now, and what are their supplier lead times?",
    "Which maintenance work orders historically consumed those at-risk parts?",
    "Which assets did that maintenance repair, and what has each asset cost us in repairs through those parts?",
    "Rank the assets most exposed if we stock out this week — weigh the number of at-risk parts, the repair cost history, and the longest supplier lead time. Explain the ranking.",
    "We can expedite three purchase orders. Which parts, and why those three?",
  ],
  "S4-pit-to-port-cascade": [
    "What is the crusher's average feed rate, and how often is it running in bypass?",
    "A six-hour crusher outage at that feed rate: how many tonnes of production do we lose?",
    "How many hours of reclaim buffer does each stockpile hold before running empty, and which run out first?",
    "For the stockpile that runs out first, trace the exposure downstream: which rail consists load from it, and which vessels do those consists feed?",
    "For those vessels: demurrage days on record, tonnes loaded, and the demurrage exposure if loading slips a day — state your day-rate assumption as a range.",
    "Five lines for the logistics manager: the chain from crusher to vessel, the first bottleneck, and the single action that buys the most time.",
  ],
}


REVIEW_JS = r"""async () => {
  let sc = null;
  const walk = (root) => {
    for (const el of root.querySelectorAll('*')) {
      if (el.scrollHeight > el.clientHeight + 200 &&
          /message|chat|conversation|scroll|content/i.test((el.className||'').toString()))
        sc = el;
      if (el.shadowRoot) walk(el.shadowRoot);
    }
  };
  walk(document);
  if (!sc) sc = document.scrollingElement;
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  sc.scrollTo({top: 0, behavior: 'smooth'}); await sleep(3000);
  // Page-by-page, holding each screen STATIC: a continuous crawl makes the
  // viewer read moving text (the v1 pass at 110px/600ms was unreadable).
  // Guards: a zero-height scroller must not zero the step (infinite loop),
  // and a runaway page count must not stall the recording forever.
  const step = Math.max(200, Math.floor(sc.clientHeight * 0.85));
  const bottom = Math.max(0, sc.scrollHeight - sc.clientHeight);
  let pages = 0;
  for (let y = 0; y < bottom && pages < 25; y += step, pages++) {
    sc.scrollTo({top: Math.min(y, bottom), behavior: 'smooth'});
    await sleep(700); await sleep(4800);
  }
  sc.scrollTo({top: bottom, behavior: 'smooth'});
  await sleep(5000); return true;
}"""


def frame_with(pg, text):
    """The console renders this product inside iframes: text visible in a
    screenshot is invisible to main-frame locators. Search every frame."""
    for f in pg.frames:
        try:
            if f.get_by_text(text).count():
                return f
        except Exception:
            continue
    return None


def find_input(pg):
    for f in pg.frames:
        try:
            loc = f.locator("textarea")
            for i in range(loc.count()):
                el = loc.nth(i)
                ph = (el.get_attribute("placeholder") or el.get_attribute("aria-label") or "")
                if el.is_visible() and ("ask" in ph.lower() or "question" in ph.lower()):
                    return f, el
        except Exception:
            continue
    return None, None


BUSY_JS = """() => {
  const t = document.body.innerText;
  if (/Working on|Generating|Running a query|Analyzing/i.test(t.slice(-2500))) return true;
  for (const el of document.querySelectorAll('[role=progressbar], .mat-mdc-progress-spinner, mat-spinner'))
    if (el.offsetParent !== null) return true;
  return false;
}"""


def wait_reply(frame, prev_len, timeout_s=300):
    """Done means: grown, busy indicators CLEARED, then stable for 20s, and
    substantive. Stability alone fired while charts were still rendering."""
    deadline, stable, last = time.time() + timeout_s, 0, prev_len
    grown = False
    while time.time() < deadline:
        time.sleep(5)
        try:
            n = frame.evaluate("() => document.body.innerText.length")
            busy = frame.evaluate(BUSY_JS)
        except Exception:
            continue
        grown = grown or n > prev_len + 80
        if grown and not busy and n == last:
            stable += 1
            if stable >= 4:
                return n
        else:
            stable = 0
        last = n
    return last


SCROLLER_H_JS = """() => {
  let sc = null;
  const walk = (root) => {
    for (const el of root.querySelectorAll('*')) {
      if (el.scrollHeight > el.clientHeight + 200) sc = el;
      if (el.shadowRoot) walk(el.shadowRoot);
    }
  };
  walk(document);
  return (sc || document.scrollingElement).scrollHeight;
}"""


def dwell_on_answer(pg, frame, start_px=None, hold_s=5, max_pages=6):
    """Let the viewer READ the answer before the next prompt buries it.

    v1 jumped to the bottom and held: any answer taller than one screen showed
    only its tail, and the headline finding was never on screen as static,
    readable text. Instead, start where this turn's answer begins (the
    scroller height captured before the prompt was sent, minus a small
    overlap so the question stays visible) and step one viewport at a time,
    holding each screen still. Dwell time now scales with answer length.
    """
    try:
        frame.evaluate("""([startPx, holdMs, maxPages]) => {
          let sc = null;
          const walk = (root) => {
            for (const el of root.querySelectorAll('*')) {
              if (el.scrollHeight > el.clientHeight + 200) sc = el;
              if (el.shadowRoot) walk(el.shadowRoot);
            }
          };
          walk(document);
          sc = sc || document.scrollingElement;
          const sleep = (ms) => new Promise(r => setTimeout(r, ms));
          const bottom = sc.scrollHeight - sc.clientHeight;
          const step = Math.floor(sc.clientHeight * 0.85);
          let y = startPx === null ? bottom
                : Math.min(Math.max(0, startPx - 120), bottom);
          return (async () => {
            for (let p = 0; p < maxPages; p++) {
              sc.scrollTo({top: y, behavior: 'smooth'});
              await sleep(700); await sleep(holdMs);
              if (y >= bottom) break;
              y = Math.min(y + step, bottom);
            }
          })();
        }""", [start_px, int(hold_s * 1000), max_pages])
    except Exception:
        pg.wait_for_timeout(10000)   # degraded: at least hold the tail still


def record(name, prompts):
    OUT.mkdir(parents=True, exist_ok=True)
    vdir = OUT / name
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), headless=True,
            viewport={"width": 1440, "height": 900},
            record_video_dir=str(vdir),
            record_video_size={"width": 1440, "height": 900})
        pg = ctx.new_page()
        pg.goto(BQ_URL, timeout=120000, wait_until="domcontentloaded")
        pg.wait_for_timeout(20000)
        card_frame = None
        for attempt in range(10):
            card_frame = frame_with(pg, AGENT_CARD)
            if card_frame:
                break
            print(f"  [{name}] card not rendered (attempt {attempt+1})", flush=True)
            if attempt % 2 == 1:      # a stuck fetch needs a fresh page, not patience
                pg.reload(timeout=120000, wait_until="domcontentloaded")
                pg.wait_for_timeout(20000)
            else:
                pg.wait_for_timeout(15000)
        if not card_frame:
            pg.screenshot(path=str(vdir / "no_agent_card.png"))
            raise RuntimeError(f"{name}: agent card never rendered in any frame")
        card_frame.get_by_text(AGENT_CARD).first.click()
        pg.wait_for_timeout(10000)
        pg.wait_for_timeout(8000)   # the card click navigates; let frames settle

        def send(q):
            """Send AND verify: the S3/S4 closers were typed, logged 'sent',
            and never appeared on screen. A send that is not visible in the
            chat log did not happen."""
            last_err = None
            for _ in range(4):
                f, b = find_input(pg)
                if b is None:
                    pg.wait_for_timeout(5000)
                    continue
                try:
                    b.fill(q, timeout=20000)
                    pg.wait_for_timeout(400)
                    b.press("Enter")
                    pg.wait_for_timeout(2500)
                    landed = f.evaluate(
                        "(k) => document.body.innerText.includes(k)", q[:60])
                    cleared = (b.input_value() or "") == "" if b.evaluate(
                        "el => el.tagName") == "TEXTAREA" else True
                    if landed and cleared:
                        return f
                    last_err = RuntimeError("typed but not landed")
                except Exception as e:
                    last_err = e
                pg.wait_for_timeout(5000)
            pg.screenshot(path=str(vdir / "send_failed.png"))
            raise RuntimeError(f"{name}: prompt did not land after 4 attempts "
                               f"({type(last_err).__name__ if last_err else 'no input'})")

        chat_frame = None
        turn_report = []
        for i, q in enumerate(prompts, 1):
            probe_frame = chat_frame or pg.main_frame
            try:
                n0 = probe_frame.evaluate("() => document.body.innerText.length")
            except Exception:
                n0 = 0
            try:                       # where this turn's content will begin
                h0 = (chat_frame.evaluate(SCROLLER_H_JS) if chat_frame else None)
            except Exception:
                h0 = None
            chat_frame = send(q)
            print(f"  [{name}] prompt {i}/{len(prompts)} sent", flush=True)
            n1 = wait_reply(chat_frame, n0)
            grew = max(0, n1 - n0 - len(q))
            turn_report.append({"turn": i, "answer_chars": grew})
            pg.screenshot(path=str(vdir / f"turn{i}.png"))
            dwell_on_answer(pg, chat_frame, start_px=h0)
            print(f"  [{name}] turn {i}: answer ~{grew} chars, dwelled", flush=True)
        transcript = chat_frame.evaluate("() => document.body.innerText")
        (vdir / "transcript.txt").write_text(transcript)
        import json as _json
        (vdir / "turns.json").write_text(_json.dumps(turn_report, indent=1))
        thin = [t["turn"] for t in turn_report if t["answer_chars"] < 120]
        missing = [i + 1 for i, q in enumerate(prompts) if q[:60] not in transcript]
        if thin or missing:
            raise RuntimeError(
                f"{name}: RECORDING REJECTED — thin turns {thin}, "
                f"prompts missing from page {missing}")
        try:
            chat_frame.evaluate(REVIEW_JS)
        except Exception as e:
            print(f"  [{name}] review scroll failed: "
                  f"{type(e).__name__}: {str(e)[:160]}", flush=True)
        ctx.close()
    print(f"  [{name}] DONE — video + transcript in {vdir}", flush=True)


if __name__ == "__main__":
    names = sys.argv[1:] or list(SCENARIOS)
    failed = []
    for n in names:
        for attempt in (1, 2):
            try:
                record(n, SCENARIOS[n])
                break
            except Exception as e:
                print(f"  [{n}] attempt {attempt} failed: {e}", flush=True)
                time.sleep(30)
        else:
            failed.append(n)
    if failed:
        print(f"SCENARIOS_FAILED: {','.join(failed)}", flush=True)
        sys.exit(1)
    print("ALL_SCENARIOS_RECORDED", flush=True)
