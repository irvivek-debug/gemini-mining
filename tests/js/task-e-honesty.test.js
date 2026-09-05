/* Task E (plan 2026-08-18) cut prose across five screens. The brief drew one
 * hard line around the cut: guards, honest limits, benchmark attribution and
 * [CLIENT INPUT REQUIRED] markers are disclosure, not explanation, and none
 * of them may be cut. This file is the check that the line held -- run
 * against the screens actually rendered, after the cuts, not against the
 * source text a reviewer might skim.
 *
 * Two harnesses are needed because the copy involved was written two ways.
 * Where a screen builds its answer with `el(id).innerHTML =`, screen-render.js's
 * renderScreen() sees it, because it joins every mount point's innerHTML.
 * Where a screen writes `el(id).textContent =` instead -- true of every lede
 * this file cut -- screen-render.js's own join comes back empty for that node
 * (tests/js/screen-dom.js's node() keeps `_html` and `_text` apart, exactly as
 * a browser does), so those are read directly off the DOM registry's
 * `.textContent`, the way tests/js/cockpit.test.js already reads
 * `impact-note`.
 */
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const { makeDom } = require("./screen-dom.js");
const { renderScreen } = require("./screen-render.js");

const ROOT = path.join(__dirname, "..", "..");
const APP = (...parts) => path.join(ROOT, "apps", "workspace", ...parts);

/** Run a workspace screen's own script tags against a small DOM, connected,
 *  and hand back the registry so a test can read any mount point's
 *  `.textContent` directly -- the one thing renderScreen()'s joined string
 *  cannot show for a node filled with `textContent =` rather than
 *  `innerHTML =`. */
function loadConnected(page) {
  const pageHtml = fs.readFileSync(APP(page), "utf8");
  const dom = makeDom(pageHtml);
  const noop = () => {};
  const RUNTIME = {
    connected: true, expected: 1, deployed: ["A0"], missing: [], note: "",
  };
  const sandbox = {
    console, URLSearchParams, setTimeout, clearTimeout, setInterval, clearInterval,
    matchMedia: () => ({ matches: true, addEventListener: noop, addListener: noop }),
    EventSource: class { addEventListener() {} close() {} },
    document: dom.document,
    location: { search: "", href: `http://localhost/apps/workspace/${page}`, hash: "" },
    history: { pushState: noop, replaceState: noop },
    getComputedStyle: () => ({ getPropertyValue: () => "" }),
    addEventListener: noop, removeEventListener: noop,
    devicePixelRatio: 1, innerWidth: 1280, innerHeight: 900,
    fetch: () => Promise.resolve({ status: 200, json: () => Promise.resolve(RUNTIME) }),
  };
  const context = vm.createContext(sandbox);
  vm.runInContext("var window = globalThis;", context);
  for (const m of pageHtml.matchAll(/<script src="([^"]+)"><\/script>/g)) {
    const file = path.resolve(path.dirname(APP(page)), m[1]);
    vm.runInContext(fs.readFileSync(file, "utf8"), context, { filename: file });
  }
  return dom;
}

async function rendered(screen, search) {
  const draw = renderScreen(screen, search || "");
  for (let i = 0; i < 5; i += 1) await new Promise((r) => setImmediate(r));
  return draw();
}

// ------------------------------------------------------------ the cockpit

test("the cockpit's sign-off cut still discloses that only a person can commit", () => {
  const dom = loadConnected("index.html");
  const text = dom.registry.get("signoff-lede").textContent;
  assert.match(text, /needs your sign-off/, `the sign-off guarantee was cut along with the prose: ${text}`);
  assert.match(text, /\d+ of \d+ agents/, `the count that makes the claim checkable was cut: ${text}`);
});

test("the cockpit's lede survived its own cut with the plain phrase for 'entrypoint' intact", () => {
  // Not decoration: tests/test_screen_copy.py requires this exact phrase
  // somewhere on the page, standing in for the jargon word "entrypoint". A
  // verbosity cut that dropped it would pass every other check here and
  // still fail that one -- pinned again, on the source of the phrase now
  // rather than only on the gate that bans its absence.
  const dom = loadConnected("index.html");
  const text = dom.registry.get("lede").textContent;
  assert.match(text, /agent you can talk to/, `the plain phrase for "entrypoint" is gone: ${text}`);
});

// -------------------------------------------------------------- value.html

test("AGT-19's honest limit survives on the value page, in full, unedited", async () => {
  const html = await rendered("apps/workspace/value.html");
  assert.ok(
    html.includes(
      "The least measurable agent in the portfolio, and the easiest to " +
        "oversell: it inherits every weakness of the assumption set it is " +
        "given, and a committee price deck can be optimised very precisely " +
        "while still being wrong. It contributes nothing to a funding case " +
        "and must not be added to one."
    ),
    "AGT-19's honest_limit did not reach the rendered value page verbatim"
  );
  assert.match(html, /What we will not claim/, "the honest-limit heading is missing from AGT-19's card");
});

test("AGT-19's authority caveat -- declared, not enforced -- survives on the value page", async () => {
  const html = await rendered("apps/workspace/value.html");
  assert.match(
    html,
    /advisory by default: every recommendation lands with a named human/,
    "AGT-19's card lost the positive governance statement"
  );
  assert.match(
    html,
    /a stance this card declares, not one the platform runs/,
    "AGT-19's card lost the non-enforcement caveat"
  );
});

test("AGT-19's coverage renders as a real bar plus the proven/scoped count, not a bare claim", async () => {
  const html = await rendered("apps/workspace/value.html");
  const match = /(\d+) diagnostics? proven · (\d+) scoped/.exec(html);
  assert.ok(match, "AGT-19's coverage sentence did not render on the value page");
  assert.match(html, /class="share-bar"/, "AGT-19's coverage rendered no visual bar");
});

test("band 1's cut kept the sourced figures and their attribution, even though the prose that stated them was removed", async () => {
  const html = await rendered("apps/workspace/value.html");
  // Task E cut Step 1's body sentences ("margin fell from 24% to 10%…",
  // "grades are down roughly 40%…") because the stat blocks beneath them
  // already carry the same figures. The figures and the citation that used
  // to sit in the sentence must still be on the page -- moved, not deleted.
  assert.match(html, /24%\s*→\s*10%/, "the margin figure was lost along with the sentence it used to sit in");
  assert.match(html, />−40%</, "the grade-decline figure was lost along with the sentence it used to sit in");
  assert.ok(
    html.includes("Deloitte, Tracking the Trends 2026") && html.includes("EY, Top 10 Business Risks in Mining &amp; Metals 2026"),
    "step 1's attribution did not survive the cut"
  );
});

test("the opex denominator is still [CLIENT INPUT REQUIRED], not filled in to make the page read shorter", async () => {
  const html = await rendered("apps/workspace/value.html");
  assert.match(html, /CLIENT.{0,20}INPUT.{0,20}REQUIRED/s, "the opex denominator lost its client-input marker");
});

// ------------------------------------------------------------ handover.html

test("the handover sheet's per-section disclosure of what an agent reads survives its own cut", async () => {
  const html = await rendered("apps/workspace/handover.html");
  assert.match(
    html,
    /Writes this section from/,
    "cutting the notConnected() placeholder text also cut the sentence naming what each agent reads"
  );
});

test("the handover sheet's omission band keeps its guarantee that an empty result is stated, not hidden", async () => {
  const html = await rendered("apps/workspace/handover.html");
  assert.match(
    html,
    /never hides an empty result/,
    "the reviewer band's honesty guarantee was cut along with its surrounding prose"
  );
  assert.match(
    html,
    /What it checks the brief against/,
    "the independence of the reviewer's check was cut"
  );
});

// --------------------------------------------------------------- swarm.html

test("the agent-teams screen's unverified band -- workspace.js's own guard machinery -- is untouched by the verbosity pass", async () => {
  const html = await rendered("apps/workspace/swarm.html");
  assert.match(html, /class="unverified"/, "the unverified band did not render at all");
  assert.match(html, /Remedy:/, "the remedy a reader needs to close a gap was cut");
});
