/* The site cockpit's metric-impact band (Task C, plan 2026-08-18), rendered
 * the way a browser renders it -- top-to-bottom script execution against a
 * DOM small enough to reason about -- because cockpit.js writes into the
 * page immediately at load time and has no module boundary a plain require()
 * could pin.
 *
 * The harness below is a trimmed copy of tests/js/screen-render.js's own
 * sandbox (same stubs: fetch, matchMedia, EventSource, no animation), kept
 * separate rather than imported because this file needs one thing that
 * screen-render.js does not expose: direct access to one element's own
 * innerHTML (`el("impacts")`), so a check can be scoped to the metrics band
 * and not cross-contaminated by an agent id that legitimately appears
 * elsewhere on the same cockpit (the "three ways in" rosters chip every
 * agent, S03 and S05 included). tests/test_screen_copy.py's `rendered()`
 * only ever needed the whole joined page, which is why that capability
 * never had to exist there.
 */
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const { makeDom } = require("./screen-dom.js");
const { esc } = require("../../apps/shared/shell.js");

const REPO = path.join(__dirname, "..", "..");
const app = (...parts) => path.join(REPO, "apps", ...parts);

function bundle() {
  const text = fs.readFileSync(app("shared", "data", "bundle.js"), "utf8");
  return JSON.parse(text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1));
}

const DATA = bundle();
const IMPACTS = DATA.catalog.metric_impact_summary;

const noop = () => {};
const RUNTIME = { connected: true, expected: 1, deployed: ["A0"], missing: [], note: "" };

function loadCockpit() {
  const page = app("workspace", "index.html");
  const pageHtml = fs.readFileSync(page, "utf8");
  const dom = makeDom(pageHtml);

  const sandbox = {
    console,
    URLSearchParams,
    setTimeout, clearTimeout, setInterval, clearInterval,
    matchMedia: () => ({ matches: true, addEventListener: noop, addListener: noop }),
    EventSource: class { addEventListener() {} close() {} },
    document: dom.document,
    location: { search: "", href: "http://localhost/apps/workspace/index.html", hash: "" },
    history: { pushState: noop, replaceState: noop },
    getComputedStyle: () => ({ getPropertyValue: () => "" }),
    addEventListener: noop,
    removeEventListener: noop,
    devicePixelRatio: 1,
    innerWidth: 1280,
    innerHeight: 900,
    fetch: () => Promise.resolve({ status: 200, json: () => Promise.resolve(RUNTIME) }),
  };

  const context = vm.createContext(sandbox);
  vm.runInContext("var window = globalThis;", context);
  for (const match of pageHtml.matchAll(/<script src="([^"]+)"><\/script>/g)) {
    const file = path.resolve(path.dirname(page), match[1]);
    vm.runInContext(fs.readFileSync(file, "utf8"), context, { filename: file });
  }
  return dom;
}

// The runtime block resolves through chained thens; draining lets it settle
// before assertions run, the same wait screen-render.js's own CLI does.
const drain = async () => {
  for (let i = 0; i < 5; i += 1) await new Promise((r) => setImmediate(r));
};

async function impactsHtml() {
  const dom = loadCockpit();
  await drain();
  const node = dom.registry.get("impacts");
  assert.ok(node, "#impacts never mounted -- the metrics band did not render at all");
  return node.innerHTML;
}

test("metric_impact_summary is non-empty, so this whole file has something to prove", () => {
  assert.ok(IMPACTS.length > 0, "fixture assumption broke: the bundle carries no metric impacts");
});

test("the cockpit renders exactly one metric card per entry in metric_impact_summary", async () => {
  const html = await impactsHtml();
  const cardCount = (html.match(/<div class="card c6">/g) || []).length;
  assert.equal(
    cardCount, IMPACTS.length,
    `rendered ${cardCount} metric cards for ${IMPACTS.length} entries in metric_impact_summary`
  );
  IMPACTS.forEach((entry) => assert.ok(html.includes(entry.metric), `${entry.metric} does not appear on the cockpit`));
});

// The binding constraint, checked structurally: every published range shown
// on the cockpit is badged INDUSTRY RANGE and carries a non-empty citation,
// and the count of each matches the number of ranges the bundle actually
// declares -- so a row silently dropped, or rendered with its source blank,
// is caught rather than merely hoped against.
test("every benchmark number rendered on the cockpit carries an attribution", async () => {
  const html = await impactsHtml();
  const totalRanges = IMPACTS.reduce((n, entry) => n + entry.ranges.length, 0);
  const badgeCount = (html.match(/badge b-info">INDUSTRY RANGE</g) || []).length;
  assert.equal(badgeCount, totalRanges, `${badgeCount} INDUSTRY RANGE badges rendered for ${totalRanges} declared ranges`);

  const cites = [...html.matchAll(/<span class="cite">([^<]*)<\/span>/g)].map((m) => m[1]);
  IMPACTS.forEach((entry) =>
    entry.ranges.forEach((r) => {
      assert.ok(
        cites.some((c) => c.includes(esc(r.source))),
        `${entry.metric}: source "${r.source}" is not cited anywhere on the cockpit`
      );
    })
  );
});

// The two kinds of number have to be visually distinct, not just textually
// different. b-info (industry) and b-ok (site) are already two different
// badge classes with two different colour tokens (tokens.css); this pins
// that the cockpit actually uses both, and never crosses them.
test("industry ranges and this site's own measurements use two different badge classes", async () => {
  const html = await impactsHtml();
  assert.match(html, /badge b-info">INDUSTRY RANGE</, "no industry-range badge rendered at all");
  assert.match(html, /badge b-ok">SITE MEASURED</, "no site-measured badge rendered at all");
  assert.ok(!/badge b-ok">INDUSTRY RANGE</.test(html), "a site figure wore the industry badge");
  assert.ok(!/badge b-info">SITE MEASURED</.test(html), "an industry figure wore the site badge");
});

// SITE MEASURED appears once per metric card, not once per published range --
// Throughput carries two ranges (BCG, McKinsey) and one site measurement, and
// repeating the same measured figure under both firms' rows would read as
// two facts instead of the one it is.
test("a metric with several published ranges still states its site figure once, not once per range", async () => {
  const html = await impactsHtml();
  const throughput = IMPACTS.find((entry) => entry.metric === "Throughput");
  assert.ok(throughput, "fixture assumption broke: Throughput is no longer in metric_impact_summary");
  assert.ok(throughput.ranges.length > 1, "fixture assumption broke: Throughput now carries only one range");
  const siteBadges = (html.match(/badge b-ok">SITE MEASURED</g) || []).length;
  // Mineral recovery is this build's other site-matched metric (cockpit.js,
  // SITE_GAP_FOR_METRIC) -- so the total is exactly two, not one per range.
  assert.equal(
    siteBadges, 2,
    `rendered ${siteBadges} SITE MEASURED badges; expected one per matched metric (2), not one per range`
  );
});

// Unplanned downtime, maintenance cost and contract value recovered have no
// comparable measurement anywhere in this build's own data. They must render
// as industry ranges only -- never filled with an adjacent number to avoid
// looking incomplete, the same rule S03 and S05 are held to on their cards.
test("a metric with no comparable site measurement renders no site-measured badge at all", async () => {
  const html = await impactsHtml();
  for (const metric of ["Unplanned downtime", "Maintenance cost", "Contract value recovered"]) {
    assert.ok(
      IMPACTS.some((e) => e.metric === metric),
      `fixture assumption broke: ${metric} is no longer in metric_impact_summary`
    );
    const cardStart = html.indexOf('<div class="card-cap">' + metric + "</div>");
    assert.ok(cardStart !== -1, `${metric}'s card did not render`);
    const nextCard = html.indexOf('<div class="card c6">', cardStart + 1);
    const cardHtml = html.slice(cardStart, nextCard === -1 ? undefined : nextCard);
    assert.ok(!/SITE MEASURED/.test(cardHtml), `${metric}'s card wears a SITE MEASURED badge it has no measurement for`);
  }
});

// The honesty note under the band: the count of agents that earn a place
// here, plus the count that don't, must add back to the total number of
// carded agents in the build -- read independently from the bundle rather
// than from the note's own arithmetic, so a note that over- or under-counts
// either side is caught.
test("the note under the metrics band accounts for every carded agent, legibly", async () => {
  const dom = loadCockpit();
  await drain();
  const noteText = dom.registry.get("impact-note").textContent;

  const allCardIds = new Set([
    ...Object.values(DATA.personas.personas).flatMap((p) => (p.cards || []).map((c) => c.agent_id)),
    ...Object.keys(DATA.catalog.group_agents || {}),
  ]);
  const withImpact = new Set();
  IMPACTS.forEach((entry) => entry.agents.forEach((id) => withImpact.add(id)));

  const match = /(\d+) of the (\d+) agents carrying a business case move a metric/.exec(noteText);
  assert.ok(match, `the note does not state how many carded agents earn a place: ${noteText}`);
  const [, withCount, totalCount] = match.map(Number);
  assert.equal(withCount, withImpact.size, "the note's 'with a range' count drifted from the bundle");
  assert.equal(totalCount, allCardIds.size, "the note's total carded-agent count drifted from the bundle");

  const otherMatch = /the other (\d+) earn their place on evidence class and coverage/.exec(noteText);
  assert.ok(otherMatch, `the note does not say how the remaining agents earn their place: ${noteText}`);
  assert.equal(withCount + Number(otherMatch[1]), totalCount, "the note's two counts do not add back to its own total");
});

// S03 and S05 carry no benchmark (mining_agents/catalog/definitions.py). This
// is the check that they never appear as a contributor to a metric card on
// the actual rendered cockpit -- not just in the bundle's own summary, which
// tests/scripts/test_build_app_data.py already covers, but in what a reader
// of this exact screen would see.
test("an agent with no metric_impacts never appears as a contributing chip on the cockpit", async () => {
  const html = await impactsHtml();
  for (const id of ["S03", "S05"]) {
    assert.ok(
      !new RegExp(`>${id}<`).test(html),
      `${id} appears inside the metrics band, but it carries no metric_impacts to contribute`
    );
  }
});
