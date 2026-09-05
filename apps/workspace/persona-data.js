/* What the left panel may say about a role, derived rather than asserted.
 *
 * Two of the five blocks are derivation rules with an edge case in almost every
 * persona, and a rule that lives inside a render function is only testable
 * through the DOM. These take DATA as an argument, touch no globals and return
 * plain objects, so a test drives them directly.
 *
 * Nothing here invents a mapping. Where the record does not connect a persona to
 * a signal, these functions return an empty result and the panel says so.
 */

/* branchesOf is defined in router.js and is deliberately NOT redefined here.
 *
 * In the browser these are classic scripts sharing one global scope, so a second
 * `function branchesOf` in this file would overwrite the router's on window —
 * and a body of `return window.branchesOf(x)` would then call itself forever.
 * router.js is loaded before this file, so the name is already in scope; under
 * Node it arrives through require. */
var ROUTER = typeof require !== "undefined" ? require("./router.js") : null;
var _branchesOf =
  (ROUTER && ROUTER.branchesOf) ||
  (typeof branchesOf !== "undefined" ? branchesOf : null);

if (!_branchesOf) {
  throw new Error(
    "persona-data.js needs router.js loaded first — no branchesOf in scope"
  );
}

/* The one signal that maps to a persona from the data rather than from a guess:
 * each branch names its own personas, so the lookup is a reverse index over
 * value_tree, not an interpretation of the persona's value_branch string.
 *
 * value_tree.branches is a LIST of branch objects, each carrying its own `code`
 * and `title` — not a dictionary keyed B1..B6, which is what the shape of
 * signals.branch_evidence invites you to assume. Read as a dictionary it yields
 * the array indices "0".."5" and every lookup after it silently misses. */
function _branchList(DATA) {
  var branches = (DATA.value_tree && DATA.value_tree.branches) || [];
  return Array.isArray(branches)
    ? branches
    : Object.keys(branches).map(function (k) { return branches[k]; });
}

function branchCodesFor(personaCode, DATA) {
  return _branchList(DATA)
    .filter(function (branch) {
      return (branch.personas || []).indexOf(personaCode) !== -1;
    })
    .map(function (branch) { return branch.code; })
    .sort();
}

function branchEvidenceFor(personaCode, DATA) {
  var byCode = {};
  _branchList(DATA).forEach(function (branch) { byCode[branch.code] = branch; });
  var evidence = (DATA.signals && DATA.signals.branch_evidence) || {};
  return branchCodesFor(personaCode, DATA)
    .filter(function (code) { return evidence[code]; })
    .map(function (code) {
      return { code: code, branch: byCode[code], evidence: evidence[code] };
    });
}

/* Gap rows carry asset_id, column and source — no branch and no persona. A row
 * is this persona's when one of its agents declares the row's source table.
 * That is checkable against the catalogue, and it is the same field the router
 * scores on, so the page and the chat agree about what a role can see.
 *
 * Four of the eight personas reach nothing. The panel renders the remainder
 * under "Also recorded at this site" rather than promoting a site-wide row into
 * a personal one.
 *
 * Agent source_tables carry a "mining_data." prefix ("mining_data.telemetry_stream").
 * Gap row source fields are parquet paths ("data/generated/telemetry_stream.parquet").
 * Both normalise to the bare table name by stripping their respective prefixes. */
function gapRowsFor(personaCode, DATA) {
  var persona = (DATA.personas && DATA.personas.personas &&
                 DATA.personas.personas[personaCode]) || null;
  var rows = (DATA.signals && DATA.signals.gap && DATA.signals.gap.rows) || [];
  if (!persona) return { reached: [], other: rows.slice() };

  var byId = {};
  (DATA.catalog.agents || []).forEach(function (a) { byId[a.agent_id] = a; });

  /* Build the set of bare table names readable by this persona's agents.
   * Agent source_tables: "mining_data.telemetry_stream" -> "telemetry_stream" */
  var readable = {};
  (persona.agents || []).forEach(function (id) {
    var agent = byId[id];
    if (!agent) return;
    (agent.source_tables || []).forEach(function (t) {
      var bare = String(t).replace(/`/g, "").replace(/^mining_data\./, "");
      readable[bare] = true;
    });
  });

  /* Match gap rows: their source is a parquet path.
   * "data/generated/telemetry_stream.parquet" -> "telemetry_stream" */
  var reached = [];
  var other = [];
  rows.forEach(function (row) {
    var src = String(row.source || "");
    var bare = src.replace(/^.*\//, "").replace(/\.parquet$/, "");
    (readable[bare] ? reached : other).push(row);
  });
  return { reached: reached, other: other };
}

if (typeof module !== "undefined") {
  module.exports = {
    branchesOf: _branchesOf, branchCodesFor, branchEvidenceFor, gapRowsFor,
  };
}
