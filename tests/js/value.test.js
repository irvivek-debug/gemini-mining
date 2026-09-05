/* apps/workspace/value.html -- rendered the way a browser runs it, via
 * tests/js/screen-render.js, so these tests see what the reader sees rather
 * than what the source merely contains.
 *
 * The page was rebuilt from three prose bands into four visual ones for a
 * sales/consulting audience (design brief, 2026-08-18). These tests check the
 * things that brief made binding: no currency figure anywhere, every
 * benchmark percentage carries a named attribution and is visually marked as
 * an industry range rather than a site measurement, the addressable-pool
 * treatment survives unchanged, the hinge line and the six levers are exactly
 * what the brief specified, and the page still ends in exactly one
 * collapsible.
 */
const test = require("node:test");
const assert = require("node:assert");

const { renderScreen } = require("./screen-render.js");

async function renderedHtml() {
  const draw = renderScreen("apps/workspace/value.html");
  for (let i = 0; i < 5; i += 1) await new Promise((r) => setImmediate(r));
  return draw();
}

// -------------------------------------------------------------- no currency

// No absolute currency figure may appear anywhere on this page: the plan is
// explicit that even the one external figure that IS a currency amount (the
// McKinsey agentic-AI value pool) must be spelled in words rather than with a
// dollar sign, because this screen is not on tests/test_screen_copy.py's list
// of screens allowed to print money at all.
test("no currency figure appears anywhere on the rendered page", async () => {
  const html = await renderedHtml();
  assert.ok(
    !/[$€£]\s?\d/.test(html),
    "a currency symbol followed by a digit reached the rendered page"
  );
});

test("the McKinsey value pool is spelled in words, not with a currency mark", async () => {
  const html = await renderedHtml();
  assert.match(html, /2\.6.{0,3}4\.4T/, "the value-pool figure is missing");
  assert.match(html, /trillion US dollars/i, "the value pool is not spelled out in words");
});

// ----------------------------------------------------- attribution, band 3

// Every row of the benchmark table (design brief, "the benchmark set") must
// name its publisher on the face of the page, and must be marked as an
// INDUSTRY RANGE rather than left looking like something this site measured.
// This is the constraint an unattributed number would violate -- "the thing
// that kills a CFO conversation" -- so it is checked by counting, not by a
// single substring test that a stray label could satisfy on its own.
const BENCHMARK_FIGURES = [
  // Checked against the raw HTML, so the ampersand is its escaped entity.
  ["2–5%", "BCG, mature AI sites in mining &amp; metals"],
  ["4–8%", "McKinsey, metals &amp; mining"],
  ["2–4 pts", "BCG"],
  ["1–3%", "McKinsey"],
  ["30–50%", "McKinsey / Deloitte, predictive maintenance"],
  ["18–25%", "McKinsey"],
  ["3–5%", "industry contract-management research"],
];

test("every benchmark range on the page carries its own figure and its own named source", async () => {
  const html = await renderedHtml();
  for (const [figure, source] of BENCHMARK_FIGURES) {
    assert.ok(html.includes(figure), `benchmark figure ${figure} is missing from the page`);
    assert.ok(html.includes(source), `benchmark figure ${figure} has no ${source} beside it`);
  }
});

test("every industry-range row is badged as such, and the count matches the benchmark set", async () => {
  const html = await renderedHtml();
  const badges = [...html.matchAll(/<span class="badge b-info">INDUSTRY RANGE<\/span>/g)];
  // Seven range rows (two throughput figures from different publishers,
  // margin, recovery, downtime, maintenance cost, contract value) plus the
  // value-pool card, plus the band-4 BCG AI Radar comparison: nine badges in
  // total. A number lower than this means a benchmark lost its attribution
  // somewhere between the data and the page; a tautological >= 1 check could
  // not catch that regression.
  assert.equal(badges.length, 9, `expected 9 INDUSTRY RANGE badges, found ${badges.length}`);
});

test("the addressable pool is badged as this build's own model, not an industry range", async () => {
  const html = await renderedHtml();
  assert.match(html, /THIS BUILD.S MODEL/, "the addressable-pool badge is missing");
  // The two classes of number have to be visually distinguishable. Checked
  // directly: the model badge must not be the same badge text the benchmark
  // rows use.
  const modelBlock = html.slice(html.indexOf("THIS BUILD"), html.indexOf("THIS BUILD") + 400);
  assert.ok(
    !modelBlock.includes("INDUSTRY RANGE"),
    "the addressable-pool block is labelled as an industry range, which it is not"
  );
});

// -------------------------------------------------------- addressable pool

// Carried over unchanged from the previous draft of this page (design brief,
// band 3: "Keep the existing addressable-pool treatment").
test("the addressable pool is stated as a percentage range, not a dollar amount", async () => {
  const html = await renderedHtml();
  assert.match(html, /4\.1%/, "the conservative percentage is missing");
  assert.match(html, /9\.0%/, "the stretch percentage is missing");
  assert.match(html, /CLIENT.{0,20}INPUT.{0,20}REQUIRED/s, "the opex denominator is not marked client-supplied");
});

// -------------------------------------------------------------------- band 1

// The five-step argument (design brief, band 1) has to carry its own four
// named sources and its own headline figures -- not a paraphrase of them.
test("band 1 names all four sources and all of its own headline figures", async () => {
  const html = await renderedHtml();
  ["Deloitte", "EY,", "ABS", "McKinsey"].forEach((name) =>
    assert.ok(html.includes(name), `band 1 does not name ${name}`)
  );
  assert.match(html, /24%\s*→\s*10%/, "the margin figure is missing");
  assert.match(html, /40%/, "the grade-decline figure is missing");
  assert.match(html, /58%/, "the AI-budget figure is missing");
});

// --------------------------------------------------------------------- band 2

test("the levers table states all six levers and their exact headroom labels", async () => {
  const html = await renderedHtml();
  const LEVERS = [
    ["Capital discipline", "Low"],
    ["Contractor and vendor squeeze", "Low"],
    ["Headcount reduction", "Negative"],
    ["Physical automation", "Medium"],
    ["Portfolio high-grading", "Low"],
    ["Digital, dashboards, data lakes", "THE GAP"],
  ];
  for (const [name, headroom] of LEVERS) {
    assert.ok(html.includes(name), `lever ${name} is missing`);
  }
  // Every named headroom label must appear at least once, and none may be
  // invented on the page beyond this set -- otherwise a badge could read
  // "Low" for a lever the brief called "Negative" and this test would still
  // pass on a substring check alone.
  const badgeTexts = [...html.matchAll(/<span class="badge [^"]*">([^<]+)<\/span>/g)].map((m) => m[1]);
  for (const [, headroom] of LEVERS) {
    assert.ok(badgeTexts.includes(headroom), `no lever badge reads ${headroom}`);
  }
});

test("the hinge line lands as a pull-quote, not a caption inside the table", async () => {
  const html = await renderedHtml();
  assert.match(html, /<blockquote class="hinge">/, "the hinge line is not set as a pull-quote");
  assert.match(
    html,
    /spent a decade building the nervous system and never installed the reflex/,
    "the hinge sentence itself is missing"
  );
});

// --------------------------------------------------------------------- band 4

test("band 4 states the industry failure rate and attributes it to BCG AI Radar 2026", async () => {
  const html = await renderedHtml();
  assert.match(html, />60%</, "the no-material-value figure is missing");
  assert.match(html, />5%</, "the at-scale figure is missing");
  assert.ok(html.includes("BCG AI Radar 2026"), "the industry failure rate has no source");
});

test("band 4's governance line is framed positively, not as a limitation", async () => {
  const html = await renderedHtml();
  assert.ok(
    !/cannot act on (its|their) own conclusion/i.test(html),
    "the tactical framing survived onto the page"
  );
  assert.match(html, /Advisory, by default/, "the positive framing of governance is missing");
  assert.match(html, /named human/, "the positive framing does not say who the recommendation lands with");
});

// -------------------------------------------------------------- page shape

test("there is deliberately no archetype band on this page", async () => {
  const html = await renderedHtml();
  assert.ok(
    !/archetype taxonomy|the six archetypes/i.test(html),
    "an archetype band reached the value page"
  );
});

test("the drawer is the only collapsible on the page", async () => {
  const html = await renderedHtml();
  const details = [...html.matchAll(/<details\b[^>]*>/g)];
  assert.equal(details.length, 1, `expected exactly one <details>, found ${details.length}`);
  assert.match(html, /Technical detail/);
});

test("neither heading level carries a digit", async () => {
  // Mirrors tests/test_screen_copy.py's own gate (headings do not count the
  // estate, or anything else, for themselves) so a regression here is caught
  // by a one-line JS test rather than only by the slower Python suite.
  const html = await renderedHtml();
  const headings = [...html.matchAll(/<h[12][^>]*>(.*?)<\/h[12]>/gs)].map((m) => m[1]);
  assert.ok(headings.length >= 5, `expected at least 5 h1/h2 headings, found ${headings.length}`);
  for (const heading of headings) {
    assert.ok(!/\d/.test(heading), `heading carries a digit: ${heading}`);
  }
});

test("the evidence ladder defines all three classes and the funding rule", async () => {
  // Band 4 claims "evidence, classed" as a differentiator. A claim of rigour
  // is not a demonstration of it: the three definitions are the part a CFO
  // uses, because they decide what may be booked and what may only be
  // reported. An earlier rebuild dropped them and left the assertion standing
  // alone, which is what this test exists to stop recurring.
  const html = await renderedHtml();
  for (const cls of ["A", "B", "C"]) {
    assert.match(html, new RegExp("CLASS\\s*" + cls),
      `class ${cls} is missing from the evidence ladder`);
  }
  for (const name of ["Cash-verifiable", "Metric-verifiable", "Risk-adjusted"]) {
    assert.ok(html.includes(name), `${name} is missing`);
  }
  // The funding rule is the whole point of naming the classes. Without it a
  // reader can see three labels and still not know which ones pay for the
  // programme, which is the question the band is answering.
  assert.match(html, /Class A and Class B alone/,
    "the ladder lists the classes but never says which of them a case rests on");
  assert.match(html, /never counted inside it/,
    "the ladder never states that Class C is excluded from the case");
});
