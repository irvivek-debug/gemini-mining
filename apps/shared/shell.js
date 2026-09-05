/* Shared chrome and helpers for both applications.
 *
 * The data arrives as window.MINING_DATA from data/bundle.js, which is a
 * script tag rather than a fetch so the screens also work when opened straight
 * off disk. Everything here reads that object; nothing here holds a figure of
 * its own, because a helper with a hardcoded count is how a screen starts
 * disagreeing with the catalog it claims to describe.
 */

/* `typeof window` rather than plain `window`: this file is also `require`d from
 * Node by the JS tests, which need esc/fig/num/rowPlaces without a DOM. In a
 * browser both guards are true and nothing below changes. */
const DATA = typeof window !== "undefined" ? window.MINING_DATA : undefined;
if (!DATA && typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    document.body.innerHTML =
      '<div class="wrap"><div class="note"><strong>Data missing</strong><br>' +
      "data/bundle.js did not load. Run <code>python -m scripts.build_app_data</code>." +
      "</div></div>";
  });
}

/* Application 1, in the order the argument is made: what the problem is, how
   big it is here, what closing it is worth, how it is closed, and only then
   what it is built on. The labels are the argument, not the file names. */
const CASE_NAV = [
  { href: "index.html", label: "1 · The case" },
  { href: "scenario.html", label: "2 · The gap" },
  { href: "value.html", label: "3 · The prize" },
  { href: "solution.html", label: "4 · The solution" },
  { href: "graph.html", label: "5 · The graph" },
];

/* Application 2. The five destinations are the five standing screens; the
   approval sheet is deliberately absent because it is a modal raised from an
   agent team or a role page and never a place you navigate to on its own.
   Value is first, before Cockpit: the user asked for "both audiences,
   sequenced", and sequenced means the value argument is the surface a CEO
   meets first (design doc, section 1). index.html remains the default entry
   point this nav is rendered on top of; Value is a destination, not a new
   landing page. */
const WORK_NAV = [
  { href: "value.html", label: "Value" },
  { href: "index.html", label: "Cockpit" },
  { href: "swarm.html", label: "Agent teams" },
  { href: "persona.html", label: "My role" },
  { href: "handover.html", label: "Handover" },
];

/* The pill in the corner of every screen. It differs between the two
   applications because the two applications are addressed to different
   readers: the case is read by someone deciding whether the gap is real, and
   the workspace by someone who has already decided and wants to know what is
   deployed. An entrypoint count in the corner of screen one answers a question
   that has not been asked yet, and quietly changes what the screen is about. */
const NAVS = {
  case: {
    items: CASE_NAV,
    brand: "Mining Agents · The case for change",
    pill: () => {
      const row = DATA.signals.gap.rows[0];
      const dp = rowPlaces(row);
      return {
        text: `Recovery ${fig(row.median, row.unit, dp)} → ${fig(row.p90, row.unit, dp)}`,
        title: `${row.label}: this site's ordinary day against its own best day, over ${row.days} days`,
      };
    },
  },
  workspace: {
    items: WORK_NAV,
    brand: "Mining Agents · Site workspace",
    /* The two figures are a distinction, not a pair. "52 entrypoints · 100
       agents" reads as a hundred things to talk to and fifty-two of something
       technical; the truth is the other way round, and it is the fact a reader
       most needs before they start looking for the right agent. */
    pill: () => ({
      text:
        `${DATA.catalog.counts.entrypoints} agents you can talk to · ` +
        `${DATA.catalog.counts.agent_nodes} in the teams behind them`,
      title: "Source of every figure on this page",
    }),
  },
};

/** Escape before interpolation. Part descriptions and technician notes are
 *  free text from the warehouse, and they land inside innerHTML. */
function esc(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function num(value) {
  return typeof value === "number" ? value.toLocaleString("en-US") : esc(value);
}

/** How many decimals a figure of this size deserves. A plant does not run to
 *  four decimal places, and an export that carries them because it averaged
 *  something is not a licence to print them. */
function places(v) {
  return Math.abs(v) >= 100 ? 0 : Math.abs(v) >= 10 ? 1 : 2;
}

function fig(v, unit, dp) {
  const step = dp === undefined ? places(v) : dp;
  const n = v.toLocaleString("en-US", {
    minimumFractionDigits: step,
    maximumFractionDigits: step,
  });
  if (!unit) return n;
  // A per-cent sign closes up against its number in English setting; a tonne
  // or a megawatt takes the space. Handling it here rather than at each call
  // site is what keeps "92.32%" and "204.5 t" both right on the same row.
  return unit === "%" ? `${n}%` : `${n} ${unit}`;
}

/** The precision a whole gap row must be printed at.
 *
 *  A gap row prints three numbers that have to survive a reader subtracting
 *  them: 92.3, 94.3 and a gap of 1.96 is a screen caught out by mental
 *  arithmetic. So a row is printed at whatever precision makes its own
 *  subtraction come out, starting from the least that could work — the
 *  cheapest fix is more decimals, and more decimals than the measurement
 *  deserves is its own dishonesty.
 */
function rowPlaces(row) {
  // Where the gap is an absolute difference it is the subject of the row, so
  // it sets the precision too. Rounding a 1.96-point gap to 2.0 because it
  // sits on a 92 discards the measurement to suit its neighbour, and then
  // overstates it by two percent on the way past.
  const start =
    row.delta_kind === "points"
      ? Math.max(places(row.median), places(row.delta))
      : places(row.median);
  for (let dp = start; dp <= 4; dp += 1) {
    const shown = +row.p90.toFixed(dp) - +row.median.toFixed(dp);
    if (Math.abs(shown - +row.delta.toFixed(dp)) < Math.pow(10, -dp) / 2) return dp;
  }
  return 4;
}

/** A magnitude this repository does not establish. Rendered as words, never as
 *  a number, so it cannot be misread as one at a glance. */
function clientInput() {
  return '<div class="metric gap">[CLIENT&nbsp;INPUT<br>REQUIRED]</div>';
}

function mountNav(app, current) {
  const nav = NAVS[app];
  if (!nav) throw new Error(`no nav defined for app ${app}`);
  const links = nav.items
    .map(
      (i) =>
        `<a href="${i.href}"${
          i.href === current ? ' aria-current="page" style="color:var(--fg);border-color:var(--border)"' : ""
        }>${esc(i.label)}</a>`
    )
    .join("");
  const pill = nav.pill();
  const bar = document.createElement("div");
  bar.className = "topbar";
  bar.innerHTML =
    `<span class="brand">${esc(nav.brand)}</span>` +
    `<nav>${links}</nav>` +
    '<span style="flex:1"></span>' +
    `<span class="pill" title="${esc(pill.title)}">${esc(pill.text)}</span>`;
  document.body.prepend(bar);
}

/** The one collapsible every screen ends with.
 *
 *  The instruction was explicit: plain language and tables first, technical
 *  detail at the end, behind something the reader opens on purpose. One helper
 *  rather than ten hand-written <details> blocks, because ten of them is ten
 *  chances for one screen to call it something else and break the pattern the
 *  reader has just learned.
 */
function drawer(title, bodyHtml, hint) {
  return (
    '<details class="tbl drawer">' +
    `<summary>${esc(title)}` +
    (hint ? `<span class="dim">${esc(hint)}</span>` : "") +
    "</summary>" +
    `<div class="drawer-body">${bodyHtml}</div>` +
    "</details>"
  );
}

/** The drawer for plumbing: agent ids, tables, model tiers.
 *
 *  Kept as its own function because the title is a promise. Across every
 *  screen "Technical detail" has come to mean the same thing to the reader —
 *  material they may skip without losing the argument — and that promise only
 *  holds while one name has one meaning. A chat answer briefly filed the
 *  specialists' and critic's reasoning here, which broke the promise in both
 *  directions: it hid the substance of the swarm behind the skip-me label, and
 *  it put two identically-titled controls at the foot of one answer. Anything
 *  that is not plumbing calls `drawer` with its own noun. */
function technicalDrawer(bodyHtml, hint) {
  return drawer("Technical detail", bodyHtml, hint);
}

/** The footer every screen carries: when the data was generated and from what.
 *  A screen that cannot say where its numbers came from is a screen that
 *  cannot be checked. */
function provenance(extra) {
  return (
    '<hr class="rule">' +
    '<div class="card"><div class="card-cap">Provenance</div>' +
    // A dl, not a div: these are dt/dd pairs, which are only valid inside one.
    // The extra class is what lets the stylesheet stack them on a phone, where
    // the two-column form leaves too little room for a dotted module path.
    '<dl class="kv prov">' +
    `<dt>Catalog</dt><dd>${esc(DATA.catalog.source)}</dd>` +
    `<dt>Generated</dt><dd class="mono">${esc(DATA.catalog.generated_at)}</dd>` +
    (extra || "") +
    "</dl></div>"
  );
}

function el(id) {
  const node = document.getElementById(id);
  if (!node) throw new Error(`no element #${id} on this page`);
  return node;
}

/* Whether the deployed agents can be reached is Application 2's question, and
 * it is asked and worded in apps/shared/runtime.js. runtimeState() and
 * connectionCopy() were here, and this file is loaded by both applications, so
 * every screen of the case for change was carrying the workspace's backend
 * logic in order to get a nav bar. */

/* The pure half only. mountNav, provenance and el read the document or the
 * bundle global, and exporting them would invite a test to call one and get a
 * DOM error instead of an answer. Everything below is a function of its
 * arguments alone, which is what makes it worth pinning from Node. */
if (typeof module !== "undefined") {
  module.exports = { esc, num, places, fig, rowPlaces, clientInput, drawer, technicalDrawer };
}
