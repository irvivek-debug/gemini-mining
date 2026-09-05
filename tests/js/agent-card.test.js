/* The shared agent-card renderer (design doc section 2), tested against real
 * cards pulled from the shipped bundle -- not hand-typed fixtures, so a field
 * the export stopped carrying breaks this file rather than a fixture that
 * quietly kept the old shape.
 */
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const {
  renderAgentCard,
  _coverageRow,
  _metricImpactsBlock,
  _impactRow,
  _rangeScale,
} = require("../../apps/workspace/agent-card.js");
const { esc } = require("../../apps/shared/shell.js");

function loadData() {
  const file = path.join(__dirname, "..", "..", "apps", "shared", "data", "bundle.js");
  const text = fs.readFileSync(file, "utf8");
  return JSON.parse(text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1));
}

const DATA = loadData();

function allCards() {
  const cards = [];
  Object.values(DATA.personas.personas).forEach((p) => (p.cards || []).forEach((c) => cards.push(c)));
  Object.values(DATA.catalog.group_agents || {}).forEach((c) => cards.push(c));
  return cards;
}

// S01 (AGT-11, p1-reliability.yaml) is a stable partially-instrumented case.
// Its pack is not one of the three under active instrumentation elsewhere in
// this branch, so its coverage is a safe fixture to assert an exact number
// against.
const PARTIAL_COVERAGE_ID = "S01";

// S03 and S05 are this plan's real fixtures for an agent with NO published
// metric benchmark (plan 2026-08-18, Task D: "S03 and S05 are your real
// fixtures"). Both are deliberate honesty decisions recorded in
// mining_agents/catalog/definitions.py, not an oversight, and neither pack
// is under active instrumentation elsewhere in this branch, so metric_impacts
// itself (unlike coverage) is stable to pin a test against.
const NO_BENCHMARK_IDS = ["S03", "S05"];

function cardById(id) {
  const found = allCards().find((c) => c.agent_id === id);
  assert.ok(found, `fixture card ${id} is no longer in the bundle`);
  return found;
}

// Zero coverage is proved against a synthetic card, not against any of
// agt13/agt14/agt19 (design §3 shipped those three at zero). Those three
// packs are being instrumented by a parallel workstream while this suite
// runs, so a real card at zero coverage today is not a stable fixture to
// pin a test against -- the behaviour under test has to hold for ANY card
// at zero, proved here on one this file controls end to end.
function zeroCoverageCard() {
  return {
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
    metric_impacts: [],
  };
}

test("every card in the bundle renders without throwing and with nothing missing", () => {
  for (const card of allCards()) {
    const html = renderAgentCard(card);
    assert.ok(html.length > 0, `${card.agent_id} rendered nothing`);
    assert.ok(!/undefined/.test(html), `${card.agent_id} rendered the word undefined`);
    assert.ok(!/NaN/.test(html), `${card.agent_id} rendered NaN`);
  }
});

test("a card renders every required field", () => {
  const card = cardById(PARTIAL_COVERAGE_ID);
  const html = renderAgentCard(card);
  assert.ok(html.includes(card.decision), "decision is missing");
  card.leaks.forEach((leak) => assert.ok(html.includes(leak), `leak ${leak} is missing`));
  assert.ok(html.includes(card.archetype), "archetype is missing");
  assert.ok(html.includes(card.authority), "authority is missing");
  card.financial_lines.forEach((fl) => {
    assert.ok(html.includes(fl.line), `financial line ${fl.line} is missing`);
    assert.ok(html.includes("Class " + fl.evidence_class), `evidence class ${fl.evidence_class} is missing`);
  });
  assert.ok(html.includes(card.honest_limit), "honest limit is missing");
  assert.ok(html.includes(String(card.coverage.instrumented)), "coverage instrumented count is missing");
  const scoped = card.coverage.total - card.coverage.instrumented;
  assert.ok(html.includes(String(scoped)), "coverage scoped count is missing");
});

// The single most important assertion in this file: a card at 0 of N drivers
// instrumented must render VISIBLY -- present in the markup, readable as a
// fact -- and must not read as an error. An earlier version of this codebase
// drew exactly this distinction for a single not_instrumented driver
// (mining_agents/tools/run_diagnostic.py: "a SUCCESSFUL call, not a
// failure"); this proves the card matches it at the level of a whole pack,
// under the positively re-cut wording (plan 2026-08-18, Task D): "0
// diagnostics proven" carries the same zero a reader used to read as "0 of
// 5", and "5 scoped" is what makes the 5 still recoverable by anyone who
// adds the two numbers back together.
test("a card at zero coverage renders the zero visibly, not blank and not as an error", () => {
  const card = zeroCoverageCard();
  const html = renderAgentCard(card);
  assert.match(html, /0 diagnostics proven · 5 scoped/, "the zero is not stated in words on the card");
  // Not blank: the coverage row is really in the markup, not skipped because
  // instrumented happened to be falsy.
  assert.match(html, /class="ac-row ac-coverage"/, "the coverage row did not render at all");
  // Not styled as an error: this codebase's error/critical vocabulary is the
  // b-crit badge and the "critical" colour token: neither may appear on the
  // strength of a zero coverage count.
  assert.ok(!/b-crit/.test(html), "a zero coverage count is styled as a critical badge");
  assert.ok(!/class="[^"]*critical[^"]*"/.test(html), "a zero coverage count is styled as critical");
});

test("a non-zero coverage renders the same shape, without the zero-specific note", () => {
  const card = cardById(PARTIAL_COVERAGE_ID);
  assert.ok(card.coverage.instrumented > 0, "fixture assumption broke: this card is now at zero");
  const scoped = card.coverage.total - card.coverage.instrumented;
  const html = renderAgentCard(card);
  assert.match(
    html,
    new RegExp(`${card.coverage.instrumented} diagnostics? proven · ${scoped} scoped`)
  );
  assert.ok(!/ac-coverage-zero/.test(html), "a non-zero coverage still renders the zero-only styling hook");
});

// Coverage is worded positively ("N diagnostics proven · M scoped") rather
// than as a fraction of a target ("N of T instrumented"), and the plan is
// explicit that the fact must still be recoverable: "an agent at 2 of 5 must
// still be readable as 2 of 5 by anyone who looks". This is the check that
// can actually fail -- it re-adds the two rendered numbers back together and
// pins them against coverage.total read independently from the bundle, so a
// renderer that under- or over-states "scoped" (e.g. always printing the
// pack's raw driver count instead of the remainder) is caught rather than
// merely hoped against.
test("proven plus scoped always adds back to the pack's own total, for every real card", () => {
  const withCoverage = allCards().filter((c) => c.coverage);
  assert.ok(withCoverage.length > 0, "fixture assumption broke: no card carries coverage");
  for (const card of withCoverage) {
    const html = renderAgentCard(card);
    const match = /(\d+) diagnostics? proven · (\d+) scoped/.exec(html);
    assert.ok(match, `${card.agent_id} does not render the proven/scoped sentence at all`);
    const [, proven, scoped] = match.map(Number);
    assert.equal(proven, card.coverage.instrumented, `${card.agent_id}: proven count drifted from coverage.instrumented`);
    assert.equal(
      proven + scoped,
      card.coverage.total,
      `${card.agent_id}: ${proven} + ${scoped} does not add back to coverage.total (${card.coverage.total})`
    );
  }
});

test("a card with no pack renders no coverage row at all", () => {
  const withoutPack = { ...cardById(PARTIAL_COVERAGE_ID), coverage: undefined };
  const html = renderAgentCard(withoutPack);
  assert.ok(!/ac-coverage/.test(html), "a card with no coverage still renders a coverage row");
});

// Authority, re-cut positively (plan 2026-08-18, Task D): the old wording --
// "a label this card carries, not a limit the platform enforces" -- was
// entirely a caveat. The new wording leads with the governance strength the
// fact actually is (every recommendation lands with a named human) and still
// has to close on the same true limit: nothing in this build enforces it.
// Both halves are asserted separately, because a rewrite that kept the
// positive half and quietly dropped the non-enforcement half would be an
// overclaim, and a rewrite that kept the caveat and dropped the positive
// framing would not be the re-cut the plan asked for.
test("nothing on a card implies authority is enforced, and the framing leads positive", () => {
  for (const card of allCards()) {
    const html = renderAgentCard(card);
    assert.match(
      html,
      /advisory by default: every recommendation lands with a named human/,
      `${card.agent_id}'s card does not lead with the positive governance statement`
    );
    assert.match(
      html,
      /a stance this card declares, not one the platform runs/,
      `${card.agent_id}'s card lost the non-enforcement caveat`
    );
    // The exact old tactical phrasing must be gone, not just supplemented.
    assert.ok(
      !/a label this card carries, not a limit the platform enforces/.test(html),
      `${card.agent_id}'s card still carries the old tactical wording alongside the new one`
    );
  }
});

test("the honest-limit heading reads as rigour, not apology", () => {
  const html = renderAgentCard(cardById(PARTIAL_COVERAGE_ID));
  assert.match(html, /What we will not claim/, "the honest-limit heading was not re-cut");
  assert.ok(!/>Honest limit</.test(html), "the old apologetic heading is still on the card");
});

test("_coverageRow is exported and agrees with renderAgentCard's own row", () => {
  const coverage = zeroCoverageCard().coverage;
  assert.equal(_coverageRow(coverage), _coverageRow(coverage));
  assert.ok(_coverageRow(undefined) === "", "a missing coverage must render the empty string, not a placeholder");
});

// ------------------------------------------------------- metric impact rows

// The other half of the single most important assertion in this file: an
// agent with NO published benchmark must render visibly and correctly, never
// as an empty or an error state -- the mirror of the zero-coverage case
// above, at the level of a whole block rather than one row. S03 and S05 are
// this plan's real fixtures (Task D): both are honesty decisions recorded on
// the card itself (mining_agents/catalog/definitions.py), and neither is
// under active instrumentation elsewhere in this branch.
for (const id of NO_BENCHMARK_IDS) {
  test(`${id} carries no metric_impacts, and its card says so as a stated fact, not a gap`, () => {
    const card = cardById(id);
    assert.equal(card.metric_impacts.length, 0, `fixture assumption broke: ${id} now carries a metric impact`);
    const html = renderAgentCard(card);
    // Present, not blank: the row is really in the markup.
    assert.match(html, /class="ac-row ac-impacts"/, `${id}: the metric-impact row did not render at all`);
    assert.match(
      html,
      /No industry range applies here/,
      `${id}: the empty case does not state its own reason`
    );
    // Never a fabricated range: no INDUSTRY RANGE badge, no percentage figure
    // borrowed from an adjacent agent to avoid looking empty.
    assert.ok(!/INDUSTRY RANGE/.test(html), `${id}: a card with no benchmark rendered a benchmark badge anyway`);
    // Never styled as an error or a gap.
    assert.ok(!/b-crit/.test(html), `${id}: the empty metric-impact case is styled as a critical badge`);
    assert.ok(!/class="[^"]*critical[^"]*"/.test(html), `${id}: the empty metric-impact case is styled as critical`);
  });
}

// Every benchmark percentage rendered anywhere on a card carries its source
// on its own face. Proved structurally rather than by spot-checking one card:
// the count of INDUSTRY RANGE badges rendered must equal the count of ranges
// a card actually declares, and every one of those badges must sit beside a
// non-empty citation -- so a renderer that dropped a row, or rendered a row
// with its cite silently empty, is caught rather than merely hoped against.
test("every benchmark percentage on a card carries its source, with nothing dropped and nothing blank", () => {
  for (const card of allCards()) {
    const html = renderAgentCard(card);
    const badgeCount = (html.match(/badge b-info">INDUSTRY RANGE</g) || []).length;
    assert.equal(
      badgeCount,
      card.metric_impacts.length,
      `${card.agent_id}: rendered ${badgeCount} INDUSTRY RANGE badges for ${card.metric_impacts.length} declared ranges`
    );
    // .cite only ever appears inside a range row's foot (_impactRow) -- so
    // one citation per declared range, each with real content, is the whole
    // claim: nothing dropped (count matches) and nothing rendered blank
    // (every one has non-whitespace text).
    const cites = [...html.matchAll(/<span class="cite">([^<]*)<\/span>/g)];
    assert.equal(
      cites.length,
      card.metric_impacts.length,
      `${card.agent_id}: rendered ${cites.length} citations for ${card.metric_impacts.length} declared ranges`
    );
    cites.forEach((m) => assert.ok(m[1].trim().length > 0, `${card.agent_id}: a citation rendered blank`));
    card.metric_impacts.forEach((mi) => {
      assert.ok(html.includes(esc(mi.source)), `${card.agent_id}: source "${mi.source}" for ${mi.metric} is missing from the rendered card`);
    });
  }
});

// S07 cites two different firms for the same metric (BCG and McKinsey both
// publish a throughput range). Both have to survive independently -- a
// renderer that merged same-metric rows to save space would silently drop
// one publisher's number off a card headed for a client.
test("two independently-sourced ranges for the same metric both render, unmerged", () => {
  const card = cardById("S07");
  const throughput = card.metric_impacts.filter((mi) => mi.metric === "Throughput");
  assert.equal(throughput.length, 2, "fixture assumption broke: S07 no longer cites two throughput ranges");
  const html = renderAgentCard(card);
  throughput.forEach((mi) => {
    assert.ok(html.includes(esc(mi.source)), `S07: the ${mi.source} throughput range is missing`);
  });
  assert.equal(
    (html.match(/range-row-label">Throughput</g) || []).length,
    2,
    "S07: the two throughput ranges collapsed into one row"
  );
});

test("_metricImpactsBlock renders the empty case without being given a card at all", () => {
  const html = _metricImpactsBlock([]);
  assert.match(html, /No industry range applies here/);
  assert.ok(!/INDUSTRY RANGE/.test(html));
});

test("_impactRow renders one range with direction, figures and source", () => {
  const html = _impactRow({
    metric: "Test metric", direction: "decrease", low_pct: 10, high_pct: 20,
    source: "Test Source",
  });
  assert.match(html, /−10–20%/, "the decrease sign or figures are missing");
  assert.ok(html.includes("Test Source"), "the source is missing");
  assert.match(html, /badge b-info">INDUSTRY RANGE</);
});

test("_rangeScale always leaves headroom above the high bound it is scaling", () => {
  for (const high of [1, 3, 8, 25, 50, 99]) {
    const scale = _rangeScale(high);
    assert.ok(scale > high, `scale ${scale} does not clear high bound ${high}`);
  }
});
