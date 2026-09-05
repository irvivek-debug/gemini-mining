/* The left column: what is true right now for this role, from the record.
 *
 * Rendered synchronously from window.MINING_DATA, so there is no spinner and no
 * empty state that the network can cause. Every rule this file appears to have
 * lives in persona-data.js instead; this file decides only how a result looks.
 *
 * The headings are careful in one specific way. Block 3 says "this site
 * instruments" rather than attributing the five machines to the reader, because
 * no persona-to-asset mapping exists anywhere in the repository and inventing
 * one is the failure this project keeps refusing. The gate on that phrasing is
 * a substring check, so this comment cannot spell out the wording it forbids
 * without failing the check that enforces it.
 */

/* esc/fig/num/places/rowPlaces come from shell.js, branchEvidenceFor/gapRowsFor
 * from persona-data.js, starterQuestions from router.js, renderAgentCard from
 * agent-card.js, and plainProse from plain.js. In the browser those are
 * globals, because classic script tags share one scope and persona.html loads
 * all of them before this file. Node gives every module its own scope, so the
 * same names are resolved through require and published where the function
 * bodies below already look for them. Guarded on the absence of a window so
 * the browser path is untouched. */
if (typeof require !== "undefined" && typeof window === "undefined") {
  Object.assign(globalThis, require("../shared/shell.js"));
  Object.assign(globalThis, require("./router.js"));
  Object.assign(globalThis, require("./persona-data.js"));
  Object.assign(globalThis, require("./agent-card.js"));
  Object.assign(globalThis, require("../shared/plain.js"));
}

function _sparkline(points) {
  if (!points || points.length < 2) return "";
  var lo = Math.min.apply(null, points);
  var hi = Math.max.apply(null, points);
  var span = hi - lo || 1;
  var step = 100 / (points.length - 1);
  var path = points
    .map(function (v, i) {
      return (i ? "L" : "M") + (i * step).toFixed(2) + " " +
        (28 - ((v - lo) / span) * 26).toFixed(2);
    })
    .join(" ");
  return (
    '<svg class="spark" viewBox="0 0 100 28" preserveAspectRatio="none" ' +
    'role="img" aria-hidden="true" focusable="false">' +
    '<path d="' + path + '" fill="none" stroke="var(--accent)" stroke-width="1"/>' +
    "</svg>"
  );
}

function _histogram(bins) {
  if (!bins || !bins.length) return "";
  var hi = Math.max.apply(null, bins) || 1;
  var w = 100 / bins.length;
  var bars = bins
    .map(function (v, i) {
      var h = (v / hi) * 26;
      // Four fifths of the slot, so the bars read as bars rather than as a
      // filled area. Written as a fraction of integers because this file must
      // hold no decimal literal — see test_no_measurement_is_typed_into_the_page.
      return '<rect x="' + (i * w).toFixed(2) + '" y="' + (28 - h).toFixed(2) +
        '" width="' + ((w * 4) / 5).toFixed(2) + '" height="' + h.toFixed(2) +
        '" fill="var(--accent)"/>';
    })
    .join("");
  return (
    '<svg class="spark" viewBox="0 0 100 28" preserveAspectRatio="none" ' +
    'role="img" aria-hidden="true" focusable="false">' + bars + "</svg>"
  );
}

function _shareBar(part, whole) {
  var pct = whole ? (part / whole) * 100 : 0;
  return (
    '<div class="share-bar" role="img" aria-hidden="true">' +
    '<span style="width:' + pct.toFixed(1) + '%"></span></div>'
  );
}

/* Three kinds, all of which must be handled: two of the eight personas would
 * render nothing if this assumed everything was a line. */
function _evidence(row) {
  var e = row.evidence;
  var body = "";
  if (e.kind === "series") {
    // One precision for the pair, not one each. Left to itself fig() reads
    // magnitude alone, which prints a whole-number count of alerts as "0.00 to
    // 7.00" — a precision the count does not have — and, for a range straddling
    // ten, prints the same measurement two ways: "9.85 t to 12.4 t".
    var dp = Number.isInteger(e.min) && Number.isInteger(e.max)
      ? 0
      : Math.max(places(e.min), places(e.max));
    body =
      _sparkline(e.points) +
      '<p class="ev-range">' + esc(e.label || row.branch.title) + " · " +
      fig(e.min, e.unit, dp) + " to " + fig(e.max, e.unit, dp) +
      " over " + num(e.readings) + " readings</p>";
  } else if (e.kind === "distribution") {
    body =
      _histogram(e.bins) +
      '<p class="ev-range">' + esc(e.label || row.branch.title) + " · " +
      num(e.n) + " values</p>";
  } else if (e.kind === "share") {
    body =
      _shareBar(e.part, e.whole) +
      '<p class="ev-range">' + esc(e.label || row.branch.title) + " · " +
      num(e.part) + " of " + num(e.whole) + "</p>";
  }
  return (
    '<div class="ev">' + body +
    // Verbatim. A bucketed mean drawn without saying it is bucketed invites the
    // reader to read a precision that is not there.
    '<p class="ev-caption">' + esc(e.caption) + "</p></div>"
  );
}

function _blockBranch(code, DATA) {
  var rows = branchEvidenceFor(code, DATA);
  if (!rows.length) {
    return (
      '<section class="pblock"><h2>What your part of the mine is doing</h2>' +
      '<p class="pnote">No part of the site is specific to this role — the ' +
      "figures below are site-wide.</p>" +
      "</section>"
    );
  }
  return (
    '<section class="pblock"><h2>What your part of the mine is doing</h2>' +
    rows.map(function (row) {
      return '<h3 class="ev-head">' + esc(row.branch.title) + "</h3>" + _evidence(row);
    }).join("") +
    "</section>"
  );
}

function _gapTable(rows) {
  return (
    // tbl-gap as well as tbl-plain: this block prints two of these one above the
    // other, and they have to share a column grid or the pair reads as broken.
    '<table class="tbl-plain tbl-gap"><thead><tr>' +
    "<th>Measure</th><th>Machine</th><th>An ordinary day</th>" +
    "<th>The best day</th><th>The gap</th></tr></thead><tbody>" +
    rows.map(function (row) {
      var dp = rowPlaces(row);
      var gap = row.delta_kind === "points"
        ? fig(row.delta, "", dp) + " pts"
        : fig(row.delta_pct, "%", 1);
      return "<tr><td>" + esc(row.label) + "</td>" +
        "<td>" + (row.asset_id ? esc(row.asset_id) : "—") + "</td>" +
        "<td>" + fig(row.median, row.unit, dp) + "</td>" +
        "<td>" + fig(row.p90, row.unit, dp) + "</td>" +
        "<td>" + gap + "</td></tr>";
    }).join("") +
    "</tbody></table>"
  );
}

function _blockGap(code, DATA) {
  var split = gapRowsFor(code, DATA);
  var gap = DATA.signals.gap;
  var reached = split.reached.length
    ? "<h3>Your agents read these</h3>" + _gapTable(split.reached)
    : '<p class="pnote">None of this role\'s agents read the tables behind the ' +
      "figures below, so none of them is this role's to act on directly.</p>";
  var other = split.other.length
    ? "<h3>Also recorded at this site</h3>" + _gapTable(split.other)
    : "";
  return (
    '<section class="pblock"><h2>An ordinary day against the best day</h2>' +
    '<p class="pnote">' + esc(gap.method) + "</p>" +
    reached + other +
    '<p class="pcaveat">' + esc(gap.caveat) + "</p>" +
    // gap.excluded is a LIST of {asset_id, reason}. Excluding a series without
    // saying so is the same fault as inventing one, so every entry prints.
    gap.excluded.map(function (row) {
      return '<p class="pcaveat">' + esc(row.asset_id) + ": " + esc(row.reason) + "</p>";
    }).join("") +
    "</section>"
  );
}

function _blockAssets(DATA) {
  return (
    // The count is in the table underneath, which is read from the signals
    // build. Spelled out in the heading it was a hardcoded figure sitting on
    // top of a derived one, free to go stale the day the site instruments a
    // sixth machine and nothing to notice when it did.
    '<section class="pblock"><h2>The machines this site instruments</h2>' +
    '<table class="tbl-plain"><thead><tr><th>Machine</th><th>What is measured</th>' +
    "<th>Unit</th></tr></thead><tbody>" +
    DATA.signals.assets.map(function (a) {
      return "<tr><td>" + esc(a.asset_id) + "</td><td>" + esc(a.label) +
        "</td><td>" + esc(a.unit) + "</td></tr>";
    }).join("") +
    "</tbody></table></section>"
  );
}

function _blockSignoffs(persona, DATA) {
  var byId = {};
  DATA.catalog.agents.forEach(function (a) { byId[a.agent_id] = a; });
  var ids = persona.hitl_agents || [];
  if (!ids.length) {
    return (
      '<section class="pblock"><h2>Waiting on your sign-off</h2>' +
      '<p class="pnote">Nothing on this role\'s list needs a sign-off.</p></section>'
    );
  }
  return (
    '<section class="pblock"><h2>Waiting on your sign-off</h2>' +
    '<ul class="signoffs">' +
    ids.map(function (id) {
      var agent = byId[id];
      if (!agent) return "";
      return "<li><span>" + esc(agent.display_name) + "</span>" +
        '<button class="ask" type="button" data-agent="' + esc(id) + '">Ask this one</button></li>';
    }).join("") +
    "</ul></section>"
  );
}

/* What this role is trying to get done, open on the page.
 *
 * This was a closed <details> wearing the same class as the technical drawer at
 * the foot of the screen, which put the reader's own work behind the affordance
 * this suite uses for machinery — and gave the role page two things to open
 * where the instruction asks for one. It is not machinery. It is the list this
 * person came to the page holding, and it reads as a section like the four
 * above it. */
function _blockJobs(persona) {
  return (
    '<section class="pblock"><h2>What you\'re trying to get done</h2>' +
    '<ul class="jobs">' +
    (persona.jobs_to_be_done || []).map(function (job) {
      return "<li>" + esc(job) + "</li>";
    }).join("") +
    "</ul></section>"
  );
}

/* The same sentence the chat sidecar's first starter button asks, read the
 * same way it builds it: starterQuestions() always puts the method-derived
 * question first when the persona has one (see router.js's _starterItems),
 * so its first element IS the governing question whenever one exists. Reusing
 * that function rather than re-deriving the sentence here is what keeps the
 * panel and the sidecar from ever disagreeing about what the question is. */
function _governingQuestion(code, DATA) {
  var persona = DATA.personas.personas[code];
  if (!persona || !persona.method || !persona.method.metric) return null;
  var starters = starterQuestions(code, DATA);
  return starters.length ? starters[0] : null;
}

/* The agent card block (design doc section 2), rendered beneath the role's
 * governing question -- one card per agent of this persona that carries one.
 *
 * A persona with no cards at all (P7, P8 in this build) still gets the
 * governing-question paragraph when it has a method, and says plainly that no
 * agent here carries a card yet, rather than rendering nothing: the same
 * "declared, not silently dropped" rule the rest of this codebase already
 * applies to a driver with no diagnostic behind it.
 */
function _blockCards(code, DATA) {
  var persona = DATA.personas.personas[code];
  var cards = (persona && persona.cards) || [];
  var question = _governingQuestion(code, DATA);
  // Nothing to say: no method (so no governing question) and no card. Most
  // roles never get one and a block asserting the absence on every page
  // would be noise -- P4 is the one persona in this build with a card
  // (AGT-14) but no method pack of its own, so the heading has to hold up
  // without a question underneath it.
  if (!question && !cards.length) return "";
  var heading = question ? "Your governing question" : "What your agents can already prove";
  return (
    '<section class="pblock"><h2>' + heading + "</h2>" +
    (question ? '<p class="lede">' + esc(question) + "</p>" : "") +
    (cards.length
      ? cards.map(function (c) { return renderAgentCard(c); }).join("")
      : '<p class="pnote">No agent answering to this role carries a ' +
        "business-framing card yet.</p>") +
    "</section>"
  );
}

function renderPanel(code, DATA) {
  var persona = DATA.personas.personas[code];
  return (
    '<section class="pblock"><h2>What you\'re answerable for</h2>' +
    '<p class="lede">' + esc(plainProse(persona.accountable_for)) + "</p></section>" +
    _blockCards(code, DATA) +
    _blockBranch(code, DATA) +
    _blockGap(code, DATA) +
    _blockAssets(DATA) +
    _blockSignoffs(persona, DATA) +
    _blockJobs(persona)
  );
}

if (typeof module !== "undefined") {
  module.exports = { renderPanel, _evidence, _gapTable, _blockCards, _governingQuestion };
}
