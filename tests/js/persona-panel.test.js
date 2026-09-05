/* What the left panel actually renders, against the real bundle.
 *
 * Every other test of this page is a substring search over the source, which
 * cannot see a number come out wrong — only a line of code go missing. These
 * run renderPanel over the shipped data and read the result, so a change to
 * _evidence or _gapTable that still compiles has something to answer to.
 *
 * The panel is a classic script that reads esc/fig/num from the global scope in
 * the browser; requiring it resolves those through require instead (see the
 * bootstrap at the top of persona-panel.js), so nothing needs setting up here.
 */
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const PANEL = require("../../apps/workspace/persona-panel.js");
const D = require("../../apps/workspace/persona-data.js");

function loadData() {
  const file = path.join(__dirname, "..", "..", "apps", "shared", "data", "bundle.js");
  const text = fs.readFileSync(file, "utf8");
  return JSON.parse(text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1));
}

const DATA = loadData();
const CODES = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"];

function rangeSentence(code) {
  const found = /<p class="ev-range">([^<]*)<\/p>/.exec(PANEL.renderPanel(code, DATA));
  return found ? found[1] : "";
}

test("every persona renders without throwing and with nothing missing", () => {
  for (const code of CODES) {
    const html = PANEL.renderPanel(code, DATA);
    assert.ok(html.length > 0, `${code} rendered nothing`);
    assert.ok(!/undefined/.test(html), `${code} rendered the word undefined`);
    assert.ok(!/NaN/.test(html), `${code} rendered NaN`);
  }
});

test("P4's evidence is a share, so it draws a bar and not a line", () => {
  // Two of the eight personas render nothing at all if the panel assumes every
  // kind of evidence is a series.
  const html = PANEL.renderPanel("P4", DATA);
  assert.match(html, /class="share-bar"/, "the share branch drew no bar");
  assert.ok(!/class="spark"/.test(html), "a share was drawn as a sparkline");
  assert.match(rangeSentence("P4"), /\d+ of \d+/);
});

test("P5's evidence is a distribution, so it draws a histogram", () => {
  const html = PANEL.renderPanel("P5", DATA);
  assert.match(html, /<rect /, "the distribution branch drew no bars");
  assert.match(rangeSentence("P5"), /values$/);
});

test("a count is not printed to two decimal places", () => {
  // P3's series is a count of fatigue alerts. Rendered by magnitude alone it
  // read "0.00 alerts to 7.00 alerts", asserting a precision a count of events
  // cannot have. This is the regression guard for that fix.
  const sentence = rangeSentence("P3");
  assert.match(sentence, /alerts/, "P3's evidence is no longer the alert count");
  const range = sentence.slice(0, sentence.indexOf(" over "));
  assert.ok(!range.includes("."), `P3's range prints a decimal point: ${range}`);
});

test("both ends of a range are printed at the same precision", () => {
  for (const code of CODES) {
    const sentence = rangeSentence(code);
    if (!sentence.includes(" to ")) continue;
    const [lo, hi] = sentence
      .slice(sentence.indexOf(" · ") + 3, sentence.indexOf(" over "))
      .split(" to ")
      .map((part) => {
        const dot = part.replace(/[^\d.]/g, "").indexOf(".");
        return dot === -1 ? 0 : part.replace(/[^\d.]/g, "").length - dot - 1;
      });
    assert.equal(lo, hi, `${code} prints its two ends at different precisions: ${sentence}`);
  }
});

test("the machines table renders one row per instrumented asset", () => {
  // The heading is verbatim-mandated and says "five". The table beneath it
  // renders whatever the bundle holds, so the two are only in agreement by
  // accident unless something checks.
  const html = PANEL.renderPanel("P1", DATA);
  const table = html.slice(html.indexOf("this site instruments"));
  const body = table.slice(table.indexOf("<tbody>"), table.indexOf("</tbody>"));
  assert.equal(
    (body.match(/<tr>/g) || []).length,
    DATA.signals.assets.length,
    "the machines table is not one row per entry in DATA.signals.assets"
  );
  for (const asset of DATA.signals.assets) {
    assert.ok(table.includes(asset.asset_id), `${asset.asset_id} is not on the screen`);
  }
});

test("the bundle instruments exactly the five machines the heading claims", () => {
  assert.equal(DATA.signals.assets.length, 5,
    "the heading 'The five machines this site instruments' is verbatim-mandated; " +
    "if the bundle no longer holds five, the screen is lying and the wording " +
    "has to be renegotiated rather than quietly outgrown");
});

test("a persona whose agents reach no gap table is told so, not shown a guess", () => {
  // P2, P3, P4 and P7 reach nothing under the source-table rule. The failure to
  // guard against is promoting a site-wide row into a personal one.
  for (const code of ["P2", "P3", "P4", "P7"]) {
    assert.equal(D.gapRowsFor(code, DATA).reached.length, 0, `${code} now reaches rows`);
    assert.match(
      PANEL.renderPanel(code, DATA),
      /None of this role's agents read the tables/,
      `${code} is not told that it reaches none of the gap tables`
    );
  }
  assert.ok(D.gapRowsFor("P6", DATA).reached.length > 0, "P6 should reach rows");
  assert.match(PANEL.renderPanel("P6", DATA), /Your agents read these/);
});

test("every gap row prints its measure, its median, its best day and its gap", () => {
  const html = PANEL.renderPanel("P1", DATA);
  for (const row of DATA.signals.gap.rows) {
    assert.ok(html.includes(row.label), `gap row ${row.label} is not on the screen`);
  }
  // Both halves of the split are on the page: nothing is dropped on the floor.
  const split = D.gapRowsFor("P1", DATA);
  assert.equal(
    (html.match(/<table class="tbl-plain tbl-gap">/g) || []).length,
    (split.reached.length ? 1 : 0) + (split.other.length ? 1 : 0)
  );
});

test("the caveats and the exclusions reach the screen verbatim", () => {
  const html = PANEL.renderPanel("P1", DATA);
  const gap = DATA.signals.gap;
  assert.ok(html.includes(gap.method), "gap.method is not rendered");
  assert.ok(html.includes(gap.caveat), "gap.caveat is not rendered");
  assert.ok(gap.excluded.length > 0, "the bundle excludes nothing, so this proves nothing");
  for (const row of gap.excluded) {
    assert.ok(html.includes(row.reason), `the reason ${row.asset_id} was excluded is not shown`);
  }
});

test("every evidence caption reaches the screen", () => {
  // A bucketed mean drawn without saying it is bucketed invites the reader to
  // read a precision that is not there.
  for (const code of CODES) {
    for (const row of D.branchEvidenceFor(code, DATA)) {
      assert.ok(
        PANEL.renderPanel(code, DATA).includes(row.evidence.caption),
        `${code}'s ${row.code} chart is drawn without its caption`
      );
    }
  }
});

test("free text from the warehouse is escaped before it lands in innerHTML", () => {
  const hostile = JSON.parse(JSON.stringify(DATA));
  hostile.personas.personas.P1.accountable_for = '<img src=x onerror="alert(1)">';
  const html = PANEL.renderPanel("P1", hostile);
  assert.ok(!html.includes("<img src=x"), "an unescaped tag reached the output");
  assert.match(html, /&lt;img src=x/);
});

test("a persona with no sign-offs says so rather than rendering an empty list", () => {
  const html = PANEL.renderPanel("P8", DATA);
  assert.match(html, /Nothing on this role's list needs a sign-off/);
  assert.ok(!/<ul class="signoffs">/.test(html));
});

// ---------------------------------------------------------------- Task 5:
// agent cards beneath the governing question.

test("P1 renders both of its agent cards, beneath the governing question", () => {
  const html = PANEL.renderPanel("P1", DATA);
  const cards = DATA.personas.personas.P1.cards;
  assert.equal(cards.length, 2, "fixture assumption broke: P1 no longer carries two cards");
  const questionAt = html.indexOf("Your governing question");
  assert.ok(questionAt !== -1, "the governing-question heading is missing on P1");
  for (const card of cards) {
    const cardAt = html.indexOf(card.decision);
    assert.ok(cardAt !== -1, `${card.agent_id}'s card did not render at all`);
    assert.ok(cardAt > questionAt, `${card.agent_id}'s card renders above the governing question, not beneath it`);
  }
});

// The single most important assertion in this file (Task 5): a card at 0 of
// N drivers instrumented must render as a visible fact, not as a blank and
// not as an error -- the same distinction this build already draws for a
// single not_instrumented driver.
//
// Proved end to end through renderPanel() against a synthetic card, not
// against S03 (agt13-warranty.yaml): that pack is under active instrumentation
// by a parallel workstream while this suite runs and is not a stable "always
// zero" fixture. Cloning DATA and injecting one card is the same technique
// this file already uses below to test escaping.
test("a zero-coverage card renders visibly on the persona page, not blank and not as an error", () => {
  const synthetic = JSON.parse(JSON.stringify(DATA));
  synthetic.personas.personas.P1.cards = [{
    agent_id: "TEST-0",
    display_name: "Test Agent",
    decision: "test decision",
    leaks: ["Latency"],
    archetype: "Optimiser",
    authority: "L1 — Recommend",
    financial_lines: [{ line: "test line", evidence_class: "C" }],
    honest_limit: "test limit",
    pack: "_test.yaml",
    coverage: { instrumented: 0, total: 5 },
  }];
  const html = PANEL.renderPanel("P1", synthetic);
  assert.match(html, /0 diagnostics proven · 5 scoped/, "the zero coverage did not render");
  assert.ok(!/b-crit/.test(html), "the zero coverage renders as a critical badge");
});

test("a persona with a card but no method pack of its own still gets its card", () => {
  // P4 carries AGT-14's card (S09) but no persona.method entry: PACKS in
  // mining_agents/tools/method_lookup.py has no P4 pack. The heading has to
  // hold up without a governing question underneath it.
  const p4 = DATA.personas.personas.P4;
  assert.ok(!p4.method, "fixture assumption broke: P4 now has a method pack");
  assert.ok((p4.cards || []).length > 0, "fixture assumption broke: P4 no longer carries a card");
  const html = PANEL.renderPanel("P4", DATA);
  assert.ok(html.includes(p4.cards[0].decision), "P4's card did not render");
  assert.ok(!html.includes("Your governing question"), "P4 has no method, so no governing question exists to head the block");
});

test("a persona with neither a method nor a card renders no card block at all", () => {
  // Proved on a synthetic persona, not on P7 or P8 as it once was.
  //
  // Those two were the last personas carrying neither, and both were given a
  // pack and a card to close the empty screens in the demo. Every shipped
  // persona now has both, so there is no live fixture left for this behaviour
  // — and the behaviour still matters: a fork that adds a role before it adds
  // that role's agents must not get a stray card block. Pinning it to whichever
  // persona happens to be unfinished this week is what broke this test, so it
  // is pinned to a persona the test owns outright instead.
  const synthetic = JSON.parse(JSON.stringify(DATA));
  synthetic.personas.personas.P1.method = null;
  delete synthetic.personas.personas.P1.cards;
  const html = PANEL.renderPanel("P1", synthetic);
  assert.ok(!html.includes("business-framing card"),
    "a persona with no method and no cards still rendered a card block");

  // The string above is the NO-CARD NOTE, not a marker on a card, so the
  // assertion is that a persona with nothing to show says nothing rather than
  // announcing an absence. Two converse checks keep it from passing vacuously.
  //
  // First: a persona that HAS cards renders them, so an empty render would not
  // sail through the assertion above.
  const withCards = PANEL.renderPanel("P1", DATA);
  assert.ok(withCards.includes("agent-card"),
    "P1 carries cards but rendered none, so the negative assertion above "
    + "proves nothing");

  // Second: the note itself must still be reachable. It exists for a persona
  // that has a governing question but no card yet — delete the note and the
  // first assertion passes forever while the real behaviour is gone.
  const questionNoCards = JSON.parse(JSON.stringify(DATA));
  delete questionNoCards.personas.personas.P1.cards;
  const noteHtml = PANEL.renderPanel("P1", questionNoCards);
  assert.ok(noteHtml.includes("business-framing card"),
    "a persona with a governing question but no card no longer says so; the "
    + "note has been lost rather than suppressed");
});

test("nothing on the persona page implies authority is enforced", () => {
  for (const code of ["P1", "P2", "P3", "P4", "P5", "P6"]) {
    const html = PANEL.renderPanel(code, DATA);
    const cards = DATA.personas.personas[code].cards || [];
    if (!cards.length) continue;
    assert.match(
      html,
      /advisory by default: every recommendation lands with a named human/,
      `${code}'s card does not carry the positively-framed authority statement`
    );
    assert.match(
      html,
      /a stance this card declares, not one the platform runs/,
      `${code}'s card lost the non-enforcement caveat while gaining the positive framing`
    );
  }
});

test("each sign-off carries the agent id the sidecar will need", () => {
  const withSignoffs = CODES.filter(
    (c) => (DATA.personas.personas[c].hitl_agents || []).length > 0
  );
  assert.ok(withSignoffs.length > 0, "no persona has a sign-off, so this proves nothing");
  for (const code of withSignoffs) {
    const html = PANEL.renderPanel(code, DATA);
    for (const id of DATA.personas.personas[code].hitl_agents) {
      assert.ok(
        html.includes(`data-agent="${id}"`),
        `${code}'s sign-off for ${id} carries no agent id`
      );
    }
  }
});
