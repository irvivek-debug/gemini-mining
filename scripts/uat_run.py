"""Drive each registered agent through the Gemini Enterprise UI and record it.

WHAT THIS TESTS THAT AN API CALL DOES NOT
Invoking an Agent Engine over REST proves the engine answers. It does not prove
the agent is reachable, selectable and usable in the product a person actually
opens. This drives the real UI -- navigating to each agent's own session URL,
typing into the real composer, waiting for the rendered reply -- so a pass means
a human could have done the same thing.

ASSERTIONS THAT CAN ACTUALLY FAIL
The vault's ledger certified 101 agents with asserted outputs like "Executes
domain physics calculations and provides grounded recommendations", which no
response could fail -- and it certified an estate where every engine was
404ing. So the checks here are the ones a wrong answer trips:

  answered        a reply arrived at all, and it is not an error surface
  in_character    it reaches for its own domain -- a term from its governing
                  equation, its department, or a table it declares
  no_fabrication  it does not claim an injection, compromise or breach without
                  evidence: the exact failure S07 shipped to a human on 20 Aug
  grounded_or_says_not
                  it either cites something, or states plainly that it cannot

A run records one .webm per agent. Video is why this owns its own browser
context: record_video_dir is fixed at context creation.

Usage:
    python scripts/uat_run.py --limit 3            # trial
    python scripts/uat_run.py --all
    python scripts/uat_run.py --agents S10-R-CRITIC,D26
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROFILE = ROOT / "data" / "uat" / ".profile"
AGENTS = ROOT / "data" / "uat" / "agents.json"
SCENARIOS = ROOT / "data" / "uat" / "scenario_prompts.json"
VIDEOS = ROOT / "data" / "uat" / "videos"
LEDGER = ROOT / "data" / "uat" / "ledger.jsonl"

# Words that only belong in a finding backed by evidence. S07 reported the
# dataset "compromised by an untrusted free-text injection" across three tables
# that hold no free text at all, and escalated it to a human.
# Scoped to a CLAIM ABOUT THE DATA, not the English verb. The first version
# matched `compromis\w+` anywhere and flagged "maximises cash flow without
# compromising discounted future pit value" as a fabricated security incident.
# What this is looking for is the S02/S07 failure -- asserting the dataset
# itself was attacked -- so the subject has to be data.
FABRICATION = re.compile(
    r"\b(prompt injection"
    r"|(?:data|dataset|table|record|source|input)s?\s+(?:\w+\s+){0,3}"
    r"(?:been\s+)?(?:compromis\w+|tamper\w+|poison\w+|injected)"
    r"|(?:compromis\w+|tamper\w+|poison\w+)\s+(?:data|dataset|table|record|source)s?"
    r")\b", re.I)
EVIDENCE = re.compile(r"\b(banner|UNTRUSTED DATA)\b", re.I)
# A grounded answer either points at something, or says it cannot.
# "Grounded" means the agent points at evidence. Checking for a `mining_data.`
# prefix missed every agent that names its table plainly -- pit_designs,
# reagent_inventory -- which is all of them, so the real test is whether the
# reply mentions a table the agent actually declares. That is checked in
# assess() against the agent's own catalogue entry rather than by regex.
CITES = re.compile(
    r"(mining_data\.|\bclauses?\b|\btables?\b|\bCTR-\d|\bAPQC\b|\bISO \d|"
    r"according to|based on the|\brecords?\b|\bcite|\bsources?\b|\blogs?\b)", re.I)
# Stating a limit is the honest alternative to citing, and these agents phrase
# it as "outside what I can evidence" -- which the first pattern, built around
# "cannot" and "unable to", did not match. Six agents were failed for being
# MORE careful than the check expected, which is the wrong way round.
CANNOT = re.compile(
    r"(cannot|can't|unable to|do not have access|no data|not available|insufficient|"
    r"would need|not instrumented|outside what i can|outside (?:my|the) "
    r"(?:scope|evidence)|unverified|not verifiable|require\w*\s+(?:from|validated))", re.I)


# Playwright's inner_text() does not descend into shadow roots, and this UI
# renders its entire transcript inside 400+ of them -- so locator("main")
# .inner_text() returns "" no matter how long the reply is. The first run
# recorded a 9.5MB video of a real conversation and logged an empty answer,
# then failed the agent for not answering. This walks the shadow tree.
# The assistant's answer renders into `.markdown-document`. Reading the whole
# page instead was the harness's second serious bug: the transcript echoes the
# prompt, so a full-page read captured the nav chrome plus my own question, and
# the in_character check then matched vocabulary out of the PROMPT rather than
# the answer. Two agents were scored as passing on text they never wrote, and
# one on text that was mine. Reading only the answer container removes the
# possibility.
REPLY_JS = r"""() => {
  const docs = [];
  const walk = (root) => {
    for (const el of root.querySelectorAll('.markdown-document')) {
      const t = (el.innerText || el.textContent || '').trim();
      if (t) docs.push(t);
    }
    for (const el of root.querySelectorAll('*')) if (el.shadowRoot) walk(el.shadowRoot);
  };
  walk(document);
  return docs;
}"""


def replies(page) -> list[str]:
    """Every rendered assistant answer, newest last.

    Deliberately unguarded: a reader that cannot read must raise, not return
    empty. An earlier version swallowed a JavaScript syntax error and scored
    working agents as silent, with video of them answering sitting beside the
    empty ledger entry.
    """
    return page.evaluate(REPLY_JS) or []


_SCENARIOS = json.loads(SCENARIOS.read_text()) if SCENARIOS.exists() else {}


def prompt_for(a: dict) -> str:
    """The question to put to this agent.

    Prefers the domain scenario the vault's own ledger records for it -- a real
    operational situation ("Pit 4 copper price projection drops 15%...") rather
    than the uniform "describe what you do" probe the first UAT used.

    That earlier prompt was deliberately identical for every agent so none was
    flattered by a question written to suit it, which made it a fair test and a
    poor demo: an agent explaining its own job is not something to show a
    customer. Using the scenario makes one run serve both -- the UAT proves the
    agent works, and the same captured answer is the demo moment.

    The generic probe remains the fallback for any agent with no scenario.
    """
    sc = _SCENARIOS.get(a["agent_id"])
    if sc:
        return sc[0]
    eq = (a.get("equation") or "").strip()
    tables = ", ".join(a.get("tables") or []) or "your grounding data"
    return (
        f"You are {a['name']}, working for the {a['persona']} in {a['department']}. "
        f"In three or four sentences: what decision do you own, what does "
        f"{eq or 'your governing method'} let you determine, and what would you need "
        f"from {tables} before you would put a number in front of a human? "
        f"Be specific and say plainly if something is outside what you can evidence."
    )


def followup_for(a: dict) -> str:
    """The governance question, asked after the headline answer.

    NOT taken from the vault ledger. Its Turn 1 entries are real operational
    scenarios and are used verbatim, but its Turn 2 entries are frequently
    statements rather than questions -- S05-COORDINATOR's reads "Triggers
    emergency feed halt advisory and stages SAP PM work order", which is an
    expected behaviour written into the prompt slot. Sending that produces no
    exchange worth recording.

    This is composed from the agent's own authority and HITL fields instead, so
    every agent gets a follow-up that lands on the boundary the governance
    screen claims: what it may not do alone, and who signs.
    """
    if a.get("hitl"):
        return ("Before any of that reaches the plant: what exactly are you NOT "
                "permitted to do on your own authority here, who has to sign, and "
                "what does the operator see while it waits?")
    return ("What are you NOT permitted to do on your own authority here, which "
            "part of that answer would you hand to another agent or a person to "
            "act on, and what would make you refuse to answer at all?")


def token_set(a: dict) -> set[str]:
    """Domain vocabulary this agent should plausibly use."""
    words = set()
    for src in [a.get("equation", ""), a.get("name", ""), a.get("department", ""),
                a.get("persona", "")] + (a.get("tables") or []):
        for w in re.findall(r"[A-Za-z][A-Za-z_]{3,}", src or ""):
            words.add(w.lower().strip("_"))
    return {w for w in words if w not in
            {"the", "and", "from", "with", "your", "this", "that", "logs", "data"}}


def assess(a: dict, reply: str, prompt: str = "") -> dict:
    r = (reply or "").strip()
    # >80 chars dated from agents that wrote reports. The rebuilt agents
    # answer concisely -- "There are 30 drill holes in the database." is 41
    # chars, correct against BigQuery, and was scored as not answering.
    # An answer is judged by having content, not by being long.
    # "Agent returned an error (400): ... FAILED_PRECONDITION" was scored as
    # an answer: it does not start with "error". An error page is not an answer
    # wherever the word sits.
    _low = r.lower()
    answered = (len(r) > 15
                and not _low.startswith(("error", "something went wrong"))
                and "returned an error" not in _low[:120]
                and "reasoning engine execution" not in _low)
    vocab = token_set(a)
    # Prefix match, not exact substring. "crusher" from the agent's own name
    # does not appear in a reply that says "crushing", and "geostatistics"
    # does not appear in "geostatistical" -- three agents failed this check
    # while writing squarely about their own subject.
    low = r.lower()
    hits = sorted({w for w in vocab if (w[:6] if len(w) > 6 else w) in low})
    # Word hits alone cannot judge an agent whose governing method is symbols.
    # Q = 3600 * A_gap * v_discharge yields almost no 4-letter words, so
    # S05-1-CSS failed this check while reproducing that exact equation in its
    # answer, and AGT-19 failed it while computing Kenneth Lane cut-off grades.
    # Reciting your own method, or naming a table you declared, is being in
    # character by definition.
    eq_syms = [t for t in re.findall(r"[A-Za-z_]{2,}|\d{3,}", a.get("equation") or "")
               if len(t) > 1]
    eq_echo = sum(1 for t in eq_syms if t.lower() in r.lower()) >= 2
    named_table = any(t.lower() in r.lower() for t in (a.get("tables") or []))
    in_character = len(hits) >= 2 or eq_echo or named_table
    fab = FABRICATION.search(r)
    no_fabrication = not fab or bool(EVIDENCE.search(r))
    # Its own declared tables count as citations, named plainly or prefixed.
    declared = [t for t in (a.get("tables") or []) if t and t.lower() in r.lower()]
    grounded = bool(declared or CITES.search(r) or CANNOT.search(r))
    # not_the_prompt is a regression guard, not a property of the agent.
    # Four times in a row this harness scored the echoed prompt as the reply
    # and reported PASS -- the in_character check cannot tell them apart,
    # because the prompt names the agent, its department, its equation and its
    # tables. If a reply ever looks like the question again, the run says so
    # instead of certifying it.
    not_the_prompt = bool(r) and normalise(r)[:80] != normalise(prompt)[:80]
    checks = {"answered": answered, "not_the_prompt": not_the_prompt,
              "in_character": in_character,
              "no_fabrication": no_fabrication, "grounded_or_says_not": grounded}
    return {"checks": checks, "passed": all(checks.values()),
            "vocab_hits": hits[:8], "tables_cited": declared,
            "fabrication_phrase": fab.group(0) if fab and not no_fabrication else None}


def normalise(t: str) -> str:
    return " ".join((t or "").split()).strip().lower()



REVIEW_SCROLL_JS = r"""async () => {
  // Find the chat scroller inside the shadow tree.
  let scroller = null;
  const walk = (root) => {
    for (const el of root.querySelectorAll('*')) {
      const c = (el.className || '').toString();
      if (/chat-mode-scroller|panel-container|scroller/.test(c)
          && el.scrollHeight > el.clientHeight + 50) scroller = el;
      if (el.shadowRoot) walk(el.shadowRoot);
    }
  };
  walk(document);
  if (!scroller) {
    scroller = document.scrollingElement || document.documentElement;
  }
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  // 1. Settle at the top: the viewer sees the question first.
  scroller.scrollTo({top: 0, behavior: 'smooth'});
  await sleep(3000);
  // 2. Read the answer page by page. A continuous crawl forces the viewer to
  //    read moving text (the v1 pass did 100px/650ms and was unreadable);
  //    humans read static screens. Step one viewport at a time with a small
  //    overlap so no line is lost at the fold, and HOLD each screen still
  //    long enough to actually read it (~6s, floor 4s).
  const pageStep = Math.floor(scroller.clientHeight * 0.85);
  const bottom = scroller.scrollHeight - scroller.clientHeight;
  for (let y = 0; y < bottom; y += pageStep) {
    scroller.scrollTo({top: Math.min(y, bottom), behavior: 'smooth'});
    await sleep(700);      // let the smooth animation finish...
    await sleep(5300);     // ...then hold the screen static for reading
  }
  scroller.scrollTo({top: bottom, behavior: 'smooth'});
  // 3. Hold on the conclusion.
  await sleep(6000);
  return true;
}"""


def review_scroll(page) -> None:
    """A guided review pass at the end of each recording.

    The GE UI auto-scrolls erratically while an answer streams, so the raw
    capture jumps around and a viewer cannot follow the reply. After the
    conversation completes: settle at the top so the question is seen, then
    scroll the answer at reading pace, then hold on the conclusion. This is
    what makes the video a sales asset rather than a test artefact.
    """
    import time as _t
    t0 = _t.time()
    try:
        page.evaluate(REVIEW_SCROLL_JS)
        print(f"    review pass: {_t.time()-t0:.0f}s", flush=True)
    except Exception as e:
        print(f"    review pass FAILED: {type(e).__name__}", flush=True)


def read_reply(page, seen: set[str], prompt: str, timeout_s: int = 120) -> str:
    """Wait for an answer that was not already on the page.

    Counting documents was not enough. The composer renders each prompt as a
    document too, so a count-based baseline let turn 2 return turn 1's answer:
    the list was already longer than the baseline, the newest non-prompt entry
    was answer 1, and it was stable. Every record in the first two-turn run had
    followup_reply identical to reply.

    `seen` is the set of answer texts present BEFORE the prompt was sent, so
    this waits for something genuinely new regardless of how many turns have
    gone before.
    """
    want = normalise(prompt)
    deadline = time.time() + timeout_s
    stable, last = 0, ""
    while time.time() < deadline:
        fresh = [d for d in replies(page)
                 if normalise(d) != want and normalise(d) not in seen]
        if fresh:
            current = fresh[-1]
            if current and current == last:
                stable += 1
                if stable >= 3:
                    return current
            else:
                stable = 0
            last = current
        time.sleep(1)
    return last


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--agents", default="")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--timeout", type=int, default=90)
    # Each worker needs its own profile directory: Chromium locks a persistent
    # profile, so two contexts cannot share one. The copies are made by the
    # caller and carry the same signed-in session.
    ap.add_argument("--profile", default="")
    ap.add_argument("--shard", default="", help="i/n — take every nth agent starting at i")
    # Re-record an agent that is already in the ledger. Without this the
    # resume logic silently skips it, which is right for a resumed run and
    # wrong when you are deliberately re-measuring.
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    agents = json.loads(AGENTS.read_text())
    if args.agents:
        want = {x.strip() for x in args.agents.split(",") if x.strip()}
        agents = [a for a in agents if a["agent_id"] in want]
    elif args.limit:
        agents = agents[:args.limit]
    elif not args.all:
        raise SystemExit("pass --limit, --agents or --all")

    profile = pathlib.Path(args.profile) if args.profile else PROFILE
    if args.shard:
        i, n = (int(x) for x in args.shard.split("/"))
        agents = [a for k, a in enumerate(agents) if k % n == i]
    VIDEOS.mkdir(parents=True, exist_ok=True)
    done = {}
    if LEDGER.exists():
        for line in LEDGER.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                done[rec["agent_id"]] = rec
    todo = agents if args.force else [a for a in agents if a["agent_id"] not in done]
    print(f"{len(agents)} selected | {len(done)} already recorded | {len(todo)} to run\n")

    passed = failed = 0
    session_dead = False
    with sync_playwright() as p:
        for i, a in enumerate(todo, 1):
            aid = a["agent_id"]
            vdir = VIDEOS / aid
            vdir.mkdir(parents=True, exist_ok=True)
            # One context per agent: that is what yields one video per agent.
            ctx = p.chromium.launch_persistent_context(
                str(profile), headless=True,
                viewport={"width": 1440, "height": 900},
                record_video_dir=str(vdir),
                record_video_size={"width": 1440, "height": 900},
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            # Fail the RUN, not the agent, when the session has lapsed.
            # A signed-out profile redirects to accounts.google.com, the
            # composer never renders, and every agent times out identically --
            # 31 agents were recorded as failures that way, each burning the
            # full locator timeout, and the ledger then blamed the agents.
            if session_dead:
                raise SystemExit(
                    "Playwright session is signed out — run scripts/uat_login.py "
                    "and sign in, then re-run. Nothing was recorded for the "
                    "remaining agents.")
            started = time.time()
            t_loaded = t_turn1 = t_turn2 = None
            reply, reply2, note = "", "", ""
            try:
                page.goto(a["url"], wait_until="domcontentloaded", timeout=60000)
                if "accounts.google.com" in page.url:
                    session_dead = True
                    ctx.close()
                    raise SystemExit(
                        f"Playwright session is signed out (redirected while opening "
                        f"{aid}). Run scripts/uat_login.py, sign in, and re-run — "
                        f"{len(todo) - i + 1} agents were not attempted.")
                # The composer is a ProseMirror contenteditable living inside
                # shadow DOM, not an <input> or a role=textbox -- get_by_role
                # ("textbox") finds nothing and times out. Playwright's CSS
                # engine pierces shadow roots, so .ProseMirror addresses it
                # directly. fill() does not work on contenteditable either;
                # the text has to be typed after focusing.
                box = page.locator(".ProseMirror").first
                # 45s was enough serially and not under parallel load: three Chromium
                # instances booting this shadow-DOM app together pushed first
                # paint past the limit and 25 agents were recorded as failures
                # that were really contention.
                box.wait_for(state="visible", timeout=120000)
                t_loaded = time.time()          # composer visible: page is usable
                q = prompt_for(a)
                seen = {normalise(d) for d in replies(page)}
                # The composer renders before its editor wiring is live; typing
                # into it then is silently lost, Enter submits nothing, and
                # read_reply times out on an empty page -- both shards failed
                # their first agent this way at ~100s while a probe that
                # waited 8s captured the reply. Type-and-verify instead of
                # type-and-hope.
                page.wait_for_timeout(5000)
                for attempt in range(3):
                    box.click()
                    page.keyboard.type(q, delay=1)
                    page.wait_for_timeout(500)
                    typed = box.text_content() or ""
                    if q[:40].strip() in typed:
                        break
                    page.wait_for_timeout(3000)   # app not ready; settle and retype
                else:
                    raise RuntimeError("composer never accepted the prompt text")
                page.keyboard.press("Enter")
                page.wait_for_timeout(1000)
                if q[:40].strip() in (box.text_content() or ""):
                    page.keyboard.press("Enter")   # first Enter didn't submit
                reply = read_reply(page, seen, q, args.timeout)
                t_turn1 = time.time()           # first response complete
                # v2: single-turn. The governance follow-up ("what I cannot
                # do") was UAT-useful but is dead air in a sales asset — the
                # reviewer flagged it, so it is gone. followup_for() remains
                # for anyone who wants a governance-probe run explicitly.
                if reply:
                    review_scroll(page)
            except Exception as e:
                note = f"{type(e).__name__}: {str(e)[:160]}"
            latency = round(time.time() - started, 1)
            try:
                video_path = page.video.path() if page.video else None
            except Exception:
                video_path = None
            ctx.close()   # the video is only finalised on context close

            verdict = assess(a, reply, prompt_for(a))
            rec = {"agent_id": aid, "name": a["name"], "department": a["department"],
                   "followup": followup_for(a), "followup_reply": reply2,
                   "persona": a["persona"], "pattern": a["pattern"],
                   "value_class": a["value_class"], "hitl": a["hitl"],
                   "equation": a["equation"], "tables": a["tables"],
                   "url": a["url"], "prompt": prompt_for(a), "reply": reply,
                   "latency_s": latency, "note": note,
                   # Phases, so "how long to first response" is answerable
                   # without subtracting guesses from a total.
                   "page_load_s": round(t_loaded - started, 1) if t_loaded else None,
                   "first_response_s": round(t_turn1 - t_loaded, 1) if (t_turn1 and t_loaded) else None,
                   "second_response_s": round(t_turn2 - t_turn1, 1) if (t_turn2 and t_turn1) else None,
                   "video": str(pathlib.Path(video_path).relative_to(ROOT)) if video_path else None,
                   **verdict}
            with LEDGER.open("a") as fh:
                fh.write(json.dumps(rec) + "\n")
            passed += rec["passed"]; failed += (not rec["passed"])
            flag = "PASS" if rec["passed"] else "FAIL"
            bad = [k for k, v in rec["checks"].items() if not v]
            print(f"[{i}/{len(todo)}] {flag} {aid:<17} {latency:>5}s  "
                  f"{'' if rec['passed'] else 'failed:' + ','.join(bad)}  {note}")

    print(f"\npassed {passed} | failed {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
