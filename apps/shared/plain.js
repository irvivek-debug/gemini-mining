/* One vocabulary, two consumers.
 *
 * The live activity log (chat.js) and the static copy (every screen) both name
 * the same machinery. A screen that calls graph_traverse "a connection trace"
 * while the stream calls it "a traversal" would be worse than either alone, so
 * both read this file.
 *
 * Nothing here guesses. An id absent from a map renders as itself, and
 * unmapped() exists so a test can prove the maps still cover the catalogue as
 * the catalogue grows.
 */

/* The noun phrase for a tool, used in prose. */
var TOOLS = {
  bq_query: "looking up records",
  bqml_predict: "running a prediction",
  doc_search: "searching the site's documents",
  graph_traverse: "tracing connections",
  method_lookup: "listing the known causes",
  operational_math: "working out the numbers",
  request_approval: "asking for your sign-off",
  run_diagnostic: "checking one cause against the data",
};

/* The present-participle headline for a tool, used in the activity log where a
 * line reads as something happening now. */
var TOOL_DOING = {
  bq_query: "Looking up records",
  bqml_predict: "Running a prediction",
  doc_search: "Searching the site's documents",
  graph_traverse: "Tracing connections",
  method_lookup: "Listing the known causes",
  operational_math: "Working out the numbers",
  request_approval: "Asking for your sign-off",
  run_diagnostic: "Checking one cause against the data",
};

/* The bare-verb phrase for a tool, used after a modal — "It can look up
 * records". TOOLS is the gerund and reads wrong in that position. */
var TOOL_ABILITY = {
  bq_query: "look up records",
  bqml_predict: "run a prediction",
  doc_search: "search the site's documents",
  graph_traverse: "trace connections",
  method_lookup: "list the known causes",
  operational_math: "work out the numbers",
  request_approval: "ask for your sign-off",
  run_diagnostic: "check one cause against the data",
};

/* The verb for the composed form, "Reading the sensor readings". Only a tool
 * whose arguments carry a noun needs one — method_lookup takes no argument at
 * all, so there is nothing for it to name and it keeps its TOOL_DOING line,
 * which it prints once. The article is not part of the verb: see articleFor.
 *
 * run_diagnostic and doc_search were missing from here, and the omission was
 * loudest exactly where the method is: working a five-driver tree printed
 * "Checking one cause against the data" five times, and a document search
 * never said what it looked for. The activity log is where the reader watches
 * the method being worked; five identical lines say a spinner would have done.
 */
var TOOL_VERB = {
  bq_query: "Reading",
  doc_search: "Searching the site's documents for",
  graph_traverse: "Tracing",
  run_diagnostic: "Checking",
};
var TOOL_FAILED = {
  bq_query: "Couldn't read",
  doc_search: "Couldn't search the site's documents for",
  graph_traverse: "Couldn't trace",
  run_diagnostic: "Couldn't check",
};

/* What each driver in a method pack asks, in the words a reader uses.
 *
 * The ids come from method/*.yaml and reach this file as the run_diagnostic
 * argument. The phrases are the pack's own questions said plainly — "costing
 * liberation" is the plant's word and becomes "costing recovery" — and they
 * carry no article, like the traversal phrases, because "Checking whether …"
 * frames them already. An id with no entry here degrades to the tool's own
 * line rather than printing the identifier, and a test over the shipped packs
 * is what reports the gap.
 *
 * Named for the method pack rather than called DRIVERS, because these files
 * load as script tags into one shared global scope and apps/case/graph.js
 * already holds a DRIVERS — the operators who drive a vehicle, an unrelated
 * sense of the same word. A second `var` of that name is not a shadow; it is a
 * SyntaxError that takes the whole screen down. */
var METHOD_DRIVERS = {
  /* P1 — Reliability Engineer (governing metric: unplanned repair cost per asset) */
  cost_concentration: "whether a handful of assets are carrying most of the repair bill",
  criticality_load: "whether the highest-consequence assets are also the costliest to repair",
  excursion_rate: "whether telemetry is flagging which assets are running outside their normal range",
  repair_duration: "whether repair time varies enough across assets to explain the cost spread",
  condition_precursors: "whether telemetry excursions reliably precede a work order on the same asset",
  availability: "whether uptime is being tracked and which assets are running the fewest operating hours",
  mtbf: "whether mean time between failures is trending in the right direction per asset",

  /* P2 — Maintenance Planner (governing metric: maintenance cost per completed work order) */
  priority_cost_escalation: "whether repair cost rises as work-order priority rises",
  backlog_aging: "whether stale work orders are sitting in the backlog long enough to inflate cost",
  parts_stockout: "which parts are below their reorder point and how long it takes to restock them",
  parts_demand_cover: "whether parts on hand are enough to cover what open work orders need",
  schedule_compliance: "what proportion of work orders were completed within their scheduled window",
  planned_ratio: "whether preventive work is growing as a share of the total maintenance programme",

  /* P3 — HSE Lead (governing metric: severity-weighted incident exposure) */
  location_concentration: "whether incident burden is concentrated in specific operational areas",
  severity_mix: "whether the distribution of incident severity levels signals any pattern worth acting on",
  fatigue_exposure: "whether the biometric monitoring record shows sleep-deficit exposure across the workforce",
  radio_distress: "whether emergency radio traffic concentrates in any particular operational period",
  /* fatigue_to_incident appears in TRAVERSALS as a graph edge walk — "how crew fatigue
   * connects to incidents". Here it is a diagnostic question declared not_instrumented
   * in the P3 pack: whether attributing specific incidents to measured fatigue is
   * possible with the current data. The two are different operations asking different
   * questions; identical wording would mislead a reader watching the activity log,
   * because "Checking how crew fatigue connects to incidents" reads as a graph walk
   * while this is a data-coverage verdict. The phrasing here names the coverage gap
   * rather than the graph edge, so the distinction is visible in the log. */
  fatigue_to_incident: "whether fatigue readings can be reliably linked to specific incidents in the data",
  shift_pattern: "whether incidents or fatigue alerts concentrate in a particular shift window",

  /* P5 — Geologist (governing metric: contained-metal variance between the block model and realised grade) */
  model_bias: "whether the block model differs systematically from assayed grade across the dataset",
  bias_by_lithology: "whether the grade variance is concentrated in one or more geological domains",
  bias_by_depth: "whether grade variance changes with depth, pointing to a depth-dependent model error",
  bias_by_elevation: "whether grade variance changes with elevation, suggesting a weathering or structural control",
  feed_grade_vs_model: "whether the grade arriving at the plant matches what the block model predicted",
  tonnage_reconciliation: "whether modelled tonnage matches the tonnes actually mined and delivered",
  qaqc_bias: "whether laboratory QA/QC failures are introducing a systematic assay bias",

  /* P6 — Metallurgist (governing metric: unit cost per tonne of contained metal) */
  liberation: "whether the crusher setting is costing recovery",
  feed_variability: "whether feed grade explains the recovery gap",
  bypass: "whether the crusher's divert valve is costing recovery",
  reagent_regime: "whether the reagent regime is costing recovery",
  grind_size_p80: "whether grind size is costing recovery",

  /* AGT-13 — Warranty & OEM Claims (recovered value from warranty and OEM claims) */
  entitlement_coverage: "whether the assets on site have their warranty terms recorded at all",
  expired_unclaimed: "whether cover lapsed on failures that were never claimed",
  own_cost_repairs: "whether repairs still under cover were paid for out of the site's own budget",
  evidence_completeness: "whether a claim carries the evidence a manufacturer will accept",
  claim_cycle_time: "whether claims take so long to assemble that the window closes first",

  /* AGT-14 — Procurement & Contract Integrity (recovered value from post-signature leakage) */
  price_variance: "whether the price paid matches the price the contract agreed",
  contract_coverage: "whether purchases are being raised against a live contract at all",
  bid_to_contract_terms: "whether the signed terms are the ones the winning bid offered",
  rebate_entitlement: "whether volume rebates the site is entitled to were ever claimed",
  duplicate_payment: "whether the same invoice has been paid more than once",
  clause_attribution: "which clause a breach falls under, and what it is worth",

  /* AGT-19 — Strategic Planning Advisor (value lost to a plan re-tested on the calendar) */
  assumption_staleness: "whether the assumptions the group plan was approved on still hold",
  reversal_cost: "what it would cost to reverse a commitment the plan has already made",
  local_vs_group_divergence: "whether the site plans and the group plan still describe the same year",
  capital_option_dominance: "whether one capital option now clearly beats another on the current outlook",
  plan_output_completeness: "whether the plan states the trigger that would make it change",

  /* P7 — Mine Controller (Optimiser: which dispatch choice serves the shift's objective) */
  congestion_cycle_time: "whether trucks are queuing long enough to cost the shift its tonnes",
  queue_buildup_leading_indicator: "whether a queue is building before it shows up in cycle time",
  payload_utilization: "whether trucks are leaving the face carrying less than they could",
  operator_behaviour_variance: "how much of the cycle-time spread is down to how the fleet is being run",
  breakdown_reassignment_effectiveness: "whether the fleet is being re-dispatched well when a truck goes down",

  /* P8 — Shift Supervisor (Sentinel: what changed since last shift, and whether it matters now) */
  fatigue_signal_shift_delta: "whether crew fatigue readings have moved since the last comparable period",
  safety_signal_shift_delta: "whether the safety picture has moved since the last comparable period",
  radio_emergency_shift_delta: "whether emergency radio traffic has moved since the last comparable period",
  maintenance_demand_shift_delta: "whether the maintenance load coming at the shift has moved",
  production_output_shift_delta: "whether output has moved since the last comparable period",
  fleet_availability_shift_delta: "whether the fleet available to the shift has moved",
  dispatch_performance_shift_delta: "whether haulage performance has moved since the last comparable period",
};

/* A search term is the model's own text, so its length is not ours to trust:
 * one line of the activity log is one step, and a paragraph pasted into the
 * query would take the log apart. Cut at a length that still shows what was
 * asked for. */
var QUERY_MAX = 60;

var TRAVERSALS = {
  blast_radius: "what else stops if this stops",
  fatigue_to_incident: "how crew fatigue connects to incidents",
  stockout_exposure: "what runs out if this part runs out",
};

var TABLES = {
  asset_dependencies: "which machines depend on which others",
  assets: "machine register",
  bid_parts_edge: "which parts each supplier quoted",
  biometric_fatigue_logs: "crew fatigue readings",
  crusher_states: "crusher run states",
  drill_assay_logs: "drill sample assays",
  drill_holes: "drill hole records",
  erp_work_orders: "work orders in the ERP",
  fatigue_logs_node: "crew fatigue records",
  fleet_vehicles: "truck and loader fleet",
  geological_block_models: "ore body block model",
  haulage_routes: "haul routes",
  incident_involvements: "who was involved in each incident",
  inventory_levels: "parts on hand",
  maintenance_logs: "maintenance history",
  metallurgical_recovery: "plant recovery records",
  operator_vehicle_assignments: "who drove what",
  operators_node: "operator roster",
  procurement_bids: "supplier bids",
  radio_communications: "radio traffic",
  rfp_items: "items out to tender",
  safety_incidents: "safety incidents",
  simulation_runs: "scenario simulation runs",
  telemetry_stream: "sensor readings",
  work_order_parts_edge: "parts each work order needs",
};

/* What each kind of record in the property graph is, in the words the site uses
 * for it. These are the ontology's node labels; the graph screen is the only one
 * that draws them today, but a screen that names one has to name it the way this
 * one does, which is what this file is for. */
var NODE_TYPES = {
  Asset: "machines",
  WorkOrder: "work orders",
  SparePart: "spare parts",
  Operator: "operators",
  Vehicle: "vehicles",
  Incident: "incidents",
  FatigueLog: "crew fatigue readings",
};

/* And what each link between two records means, read in the direction it is
 * drawn. "REPLACED_PART" runs from a work order to the part it consumed. */
var LINK_LABELS = {
  DEPENDS_ON: "depends on",
  HAS_WORK_ORDER: "raised work order",
  REPLACED_PART: "consumed part",
  LOGGED_FOR: "logged against",
  OPERATES: "was driving",
  INVOLVED_IN: "involved in",
};

/* Used by the copy rewrite. Keys are lowercased as they appear on screen. */
var JARGON = {
  entrypoint: "agent you can talk to",
  /* The spaced spelling is the one that reaches a screen: "of 52 entry points
     placed". Banning the closed-up form alone left the term readable in the
     copy while the gate reported it gone. */
  "entry point": "agent you can talk to",
  hitl: "needs your sign-off",
  "human-in-the-loop": "needs your sign-off",
  swarm: "agent team",
  traversal: "connection trace",
  "pattern a": "team agent",
  "pattern b": "specialist agent",
  "value branch": "where the money is",
  "apqc code": "standard process area",
  provenance: "where this came from",
  p90: "the best day",
  median: "the ordinary day",
  node: "machine",
  edge: "link",
  "blast radius": "what else stops",
};

function bareTable(id) {
  if (!id) return "";
  return String(id).replace(/`/g, "").replace(/^mining_data\./, "");
}

/* The warehouse's own catalogue of what tables and columns exist.
 *
 * Matched as a family rather than listed in TABLES, because it is several
 * tables — COLUMNS, TABLES, COLUMN_FIELD_PATHS, TABLE_OPTIONS — and an agent
 * picks whichever answers its question. To the reader they are one thing, so
 * they get one phrase; naming them separately would tell a supervisor about a
 * distinction that exists only inside the query engine.
 *
 * Anchored to the start of a path segment so it keys on the catalogue itself.
 * A real table called `schema_change_log` merely contains the word and must
 * come through untouched. */
var CATALOGUE = /(^|\.)INFORMATION_SCHEMA(\.|$)/;

function plainTable(id) {
  var bare = bareTable(id);
  if (CATALOGUE.test(bare)) return "list of tables and columns";
  return TABLES[bare] || bare;
}

function plainTool(id) {
  return TOOLS[id] || String(id || "");
}

function plainToolAbility(id) {
  return TOOL_ABILITY[id] || plainTool(id);
}

/* The article a table phrase needs from whatever frames it, and the one place
 * that decides. Most phrases here are noun phrases and read as "the machine
 * register". A few are relative clauses — they begin with which/who/what and
 * are already complete — and "the which parts each supplier quoted" is not
 * English. The phrases themselves carry no article so that a frame which wants
 * none ("Show me who drove what") can have none. */
function articleFor(phrase) {
  return /^(?:which|who|what)\b/i.test(String(phrase || "")) ? "" : "the ";
}

function plainTraversal(id) {
  return TRAVERSALS[id] || String(id || "");
}

function plainType(label) {
  return NODE_TYPES[label] || String(label || "");
}

function plainLink(label) {
  return LINK_LABELS[label] || String(label || "");
}

/* The scope lines under the graph are written by the build, in the build's own
 * words: "All 5 assets and all 3 dependency edges", "so the traversal returns
 * rows for those". Three structural nouns and no more — this is not a general
 * rewriter over JARGON, because "provenance" and "median" carry their meaning
 * mid-sentence and swapping them blind would produce worse English than the
 * word it removed. The plural is the captured "s": every replacement here takes
 * one, and a leading capital survives. */
var SCOPE_TERMS = ["traversal", "edge", "node"];

function plainScope(text) {
  var out = String(text || "");
  SCOPE_TERMS.forEach(function (term) {
    out = out.replace(new RegExp("\\b" + term + "(s?)\\b", "gi"), function (hit, plural) {
      var said = JARGON[term] + plural;
      return hit[0] === hit[0].toUpperCase()
        ? said.charAt(0).toUpperCase() + said.slice(1)
        : said;
    });
  });
  return out;
}

function plainJargon(term) {
  var key = String(term || "").toLowerCase();
  return JARGON[key] || String(term || "");
}

/* Prose the screens print but did not write.
 *
 * A persona's accountable_for is a paragraph out of the catalogue, and three
 * screens print it whole: the cockpit under each role, the role page as its
 * lede, and the sign-off sheet under "Who is accountable". It was written by
 * the people who built the estate, so it says "must approve or decline HITL
 * prompts". Every sentence around it now says "needs your sign-off", and one
 * paragraph in the reader's own screen still using the acronym undoes the
 * lesson the rest of the page is teaching.
 *
 * The rule is a phrase substitution and not a word one, because "HITL" is never
 * alone: it qualifies a noun, and which noun decides what reads well in its
 * place. Longest first, so "HITL approval request" is not left as "sign-off
 * request request". The list is deliberately short — every entry was checked
 * against the actual occurrences in the catalogue rather than imagined.
 *
 * What this is NOT applied to is a quotation. A journey summary and a pain
 * point are printed with a source line against them, and prose carrying a
 * citation has to be the prose at that line. Where those still use the estate's
 * words, the fix is to the document, not to a regex on the way to the screen.
 */
var PROSE = [
  [/\bHITL approval (?:request|prompt|step)s?\b/gi, "sign-off request"],
  [/\bHITL (?:approval )?prompts\b/gi, "sign-off requests"],
  [/\bHITL (?:approval )?prompt\b/gi, "sign-off request"],
  [/\bHITL approver\b/gi, "sign-off authority"],
  [/\bHITL approvals?\b/gi, "sign-off"],
  [/\bHITL\b/gi, "sign-off"],
];

/* The machinery's own names, arriving by the same channel and fixed the same
 * way.
 *
 * accountable_for was one field. It is not the only one. The build writes
 * facts.json's `why` and graph.json's `source` in the build's own words —
 * "data/profile/stats.json keeps a three-row sample of fleet_vehicles, not the
 * table… BigQuery settles it" — and the scenario and graph screens print them
 * whole, at a shift supervisor. No gate reading source could see either, for
 * the same reason none could see HITL in accountable_for: nobody typed them
 * onto a screen.
 *
 * Table identifiers are deliberately absent from this list. They are read from
 * TABLES above, so renaming a table moves this rewrite with it instead of
 * leaving a stale entry behind. What is listed is what has no other home: the
 * product, the dataset it lives in, and the two file locations the build
 * actually names. Every entry was checked against the generated data rather
 * than imagined, and the longest path is matched first so a rewrite of the
 * directory cannot strand the file name.
 *
 * None of this deletes the fact. The unrewritten string is still on each of
 * these screens — inside the technical drawer, which is where a path, a script
 * name and a product name are allowed to be.
 */
var MACHINE_PROSE = [
  [/\bdata\/profile\/stats\.json\b/g, "a profile taken before this build"],
  [/\bdata\/generated\/\*\.parquet\b/g, "the files this build generated"],
  [/\bmining_data\b/g, "the warehouse's own dataset"],
  [/\bBigQuery\b/g, "the warehouse"],
];

/* A table identifier loose in a sentence, said the way the rest of the estate
 * says it. Only ids TABLES knows are touched: an unmapped one is left alone
 * rather than mangled, and unmapped() is what reports it. */
function _tablesInProse(text) {
  return text.replace(/\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b/g, function (id) {
    var said = TABLES[id];
    return said ? articleFor(said) + said : id;
  });
}

/* A replacement that lands at the start of a sentence arrives lowercase — "…
 * known locally. the warehouse settles it."
 *
 * The head of the string is a separate question and is only touched when the
 * head is itself what changed. These fields are not all whole sentences: a
 * persona's accountable_for is printed after an em dash as "— is also the
 * sign-off authority for…", and capitalising every rewritten string would put
 * a capital in the middle of that line. So "data/profile/stats.json keeps…"
 * becomes "A profile taken before this build keeps…" because position zero was
 * rewritten, and "is also the…" is left alone because it was not.
 */
function _sentenceCase(before, after) {
  var out = after.replace(/([.!?]\s+)([a-z])/g, function (hit, lead, letter) {
    return lead + letter.toUpperCase();
  });
  if (out.charAt(0) !== before.charAt(0)) {
    out = out.charAt(0).toUpperCase() + out.slice(1);
  }
  return out;
}

function plainProse(text) {
  var out = String(text || "");
  var before = out;
  for (var i = 0; i < PROSE.length; i++) {
    out = out.replace(PROSE[i][0], PROSE[i][1]);
  }
  for (i = 0; i < MACHINE_PROSE.length; i++) {
    out = out.replace(MACHINE_PROSE[i][0], MACHINE_PROSE[i][1]);
  }
  out = _tablesInProse(out);
  return out === before ? out : _sentenceCase(before, out);
}

/* The observed bq_query argument is a literal SELECT naming its table in
 * backticks. Only the first qualified name is taken: a join names two, and the
 * first is the one the query is about. */
function tableFromSql(sql) {
  var found = /mining_data\.([a-z0-9_]+)/i.exec(String(sql || ""));
  return found ? found[1] : "";
}

/* The noun a call is about, if the arguments carry one. Any string argument may
 * hold the SQL, and any argument may name a traversal, because the argument
 * names differ by tool and guessing a key is how this breaks silently. */
function _noun(name, args) {
  var values = Object.keys(args || {}).map(function (k) { return args[k]; });
  var i;
  if (name === "bq_query") {
    for (i = 0; i < values.length; i++) {
      var table = tableFromSql(values[i]);
      if (table) return { kind: "table", plain: plainTable(table) };
    }
  }
  if (name === "run_diagnostic") {
    for (i = 0; i < values.length; i++) {
      if (METHOD_DRIVERS[values[i]]) {
        return { kind: "driver", plain: METHOD_DRIVERS[values[i]] };
      }
    }
  }
  if (name === "doc_search" && args && typeof args.query === "string" && args.query.trim()) {
    /* The one place a key is read rather than a value, and deliberately.
     *
     * A table id and a traversal id can be recognised by their shape, so the
     * scans around this one can afford to look at every value. A search term
     * is free text and cannot: any string would satisfy it. Two things follow.
     * The key is safe to name — doc_search(query, k) is a signature written in
     * this repository, not a guess about someone else's — and taking the first
     * string instead would let _failSentence below hand this branch a whole
     * passage of the model's prose to quote back at the reader, machine
     * vocabulary and all, which is what the answer rules exist to remove.
     *
     * Quoted because the words are the model's and not this screen's. */
    var asked = args.query.trim();
    if (asked.length > QUERY_MAX) asked = asked.slice(0, QUERY_MAX) + "…";
    return { kind: "query", plain: "“" + asked + "”" };
  }
  for (i = 0; i < values.length; i++) {
    if (typeof values[i] === "string" && TRAVERSALS[values[i]]) {
      return { kind: "traversal", plain: TRAVERSALS[values[i]] };
    }
  }
  return null;
}

/* A traversal phrase is a clause and never takes an article; a table phrase
 * takes whichever articleFor says. */
function _framed(verb, noun) {
  var article = noun.kind === "table" ? articleFor(noun.plain) : "";
  return verb + " " + article + noun.plain;
}

function callLine(name, args) {
  var noun = _noun(name, args);
  if (noun && TOOL_VERB[name]) return _framed(TOOL_VERB[name], noun);
  return TOOL_DOING[name] || String(name || "");
}

function failLine(name, args) {
  var noun = _noun(name, args);
  var head = noun && TOOL_FAILED[name]
    ? _framed(TOOL_FAILED[name], noun)
    : "Couldn't finish " + (TOOLS[name] || String(name || ""));
  return head + " — that lookup failed.";
}

/* A driver the method pack declares but has no diagnostic behind it. This is
 * NOT a failure: the call succeeded, and the method truthfully reported a gap
 * in its own coverage. Saying so plainly — "declared in the tree, not
 * instrumented" — is the point: silence here would read as "no problem
 * found", and the ordinary success line would read as if a diagnostic had
 * actually run. Built on callLine's own verb/noun so the driver is named the
 * same way whether the call succeeded with rows or succeeded with a gap. */
function gapLine(name, args) {
  return callLine(name, args) +
    " — no diagnostic covers this driver; it is declared in the tree, not instrumented.";
}

/* The honesty check. Every tool, traversal and table the catalogue declares
 * must have a plain phrase, or the activity log will print an identifier at a
 * reader who came here to avoid identifiers. */
/* ------------------------------------------------------------------ answers
 *
 * Everything above rewrites text this repository wrote. This last section
 * rewrites text a deployed model wrote, arriving over the wire while a reader
 * watches, and that is a different problem in two ways.
 *
 * It is untrusted. The answer is going into innerHTML, so it is escaped before
 * a single markdown rule is applied. The other order — render, then escape —
 * is the one defect worth naming: it turns a <script> the model emitted into
 * an element, and it also double-escapes the tags the renderer just made, so
 * it fails loudly in one direction and silently in the other.
 *
 * And it is not ours to edit. A live run of S01 opened its answer with "The
 * call to `default_api:graph_traverse` failed", listed an INVALID_ARGUMENT and
 * a required `asset_id`, and put all of it in the largest body text on the role
 * page. Three specialists, a critic and a coordinator write into one stream, so
 * that arrives butted against the next agent's first sentence with no break.
 *
 * The rules below are narrow on purpose. Nothing here invents a phrase: a
 * failed call is said with failLine(), the same sentence the activity log
 * prints, and a table is said with TABLES. Where no mapping exists — a column
 * name, a part number, an agent id — the term is left alone rather than
 * guessed at, because a reader who meets `actual_duration_hours` has met an
 * identifier, and a reader who meets an invented synonym for it has been
 * misled.
 */

/* esc lives in shell.js: a global in the browser, where every page loads
 * shell.js before this file, and a require under Node. Same shape as chat.js,
 * so nothing here writes into a scope it does not own. */
var PLAIN_SHELL = typeof require !== "undefined" ? require("./shell.js") : window;

/* What the honest fact reduces to once its vocabulary is gone. The step failed
 * and the answer is therefore short of something: this branch is built on not
 * papering over that, and a de-jargoned answer that reads as complete would be
 * a worse lie than the identifier it removed. */
var ANSWER_INCOMPLETE = "This part of the answer is incomplete.";

/* A token that means the machinery rather than the mine. Anything the model
 * put in brackets or backticks around one of these is detail for the drawer.
 *
 * The third alternative is the general shape of an error constant —
 * INVALID_ARGUMENT, QUERY_FAILED, SQL_INTERPOLATION — written as a shape and
 * not as a list, because the backend raises these and the frontend cannot
 * enumerate what it has not seen yet. It is deliberately narrower than "all
 * capitals": SKU-BELT-SPLICE-G2 and PUMP-104A are things on the site that a
 * supervisor says out loud, and neither carries an underscore.
 */
var MACHINE_TOKEN = new RegExp(
  [
    "default_api:",
    "rows_scanned",
    "success:\\s*(?:true|false)",
    "\\berror\\.(?:code|message)\\b",
    "\\b[A-Z][A-Z0-9]+_[A-Z0-9_]+\\b",
    "\\bJob ID\\b",
    "https?://",
    "\\bML\\.[A-Z]+",
    "@parameter",
    "\\bAPQC\\b",
    "\\b[A-Z]\\d{2}-[A-Z]+\\b",
  ].join("|")
);

var TOOL_IDS = Object.keys(TOOLS).join("|");

/* "SP1's call to `default_api:graph_traverse` failed" wants the bare verb —
 * "call to trace connections" — and every other position wants the gerund.
 * Two rules rather than one because "call to tracing connections" is not
 * English and the reader would notice before the vocabulary registered. */
var TOOL_AFTER_CALL = new RegExp(
  "(\\bcalls? to\\s+)`?(?:default_api:)?(" + TOOL_IDS + ")`?", "g"
);
var TOOL_ANYWHERE = new RegExp("`?(?:default_api:)?\\b(" + TOOL_IDS + ")\\b`?", "g");

/* The three shapes a failed call took in the live run. An announcement, the
 * bullets under it, and the sentence that draws the consequence — the model
 * wrote all three, in that order, three times, in two different bullet
 * dialects. Matching the shape rather than the wording is what lets one rule
 * cover "**Error Code:**", "**Error Code**:" and "**error.code**:". */
var FAIL_ANNOUNCE = /^(?:the|a|an)\b[^\n]*\bcalls? to\b[^\n]*\bfailed\b[^\n]*$/i;
var FAIL_BULLET =
  /^\s*[-*]\s+\*\*\s*(?:failed(?:\s+tool)?\s+call|error[\s.]?code|error[\s.]?message)\s*:?\s*\*\*\s*:?/i;
var FAIL_BECAUSE = /^because this tool\b[^\n]*\bfailed\b/i;

/* An announcement is only an announcement if it names something in backticks.
 * "The call to shut down the mill failed" is a fact about the mine and belongs
 * on the page; "The call to `bqml_predict` failed" is a fact about the
 * machinery and belongs behind the drawer. */
function _startsFailure(line) {
  return FAIL_ANNOUNCE.test(line) && line.indexOf("`") >= 0;
}

function _isFailLine(line) {
  return _startsFailure(line) || FAIL_BULLET.test(line) || FAIL_BECAUSE.test(line);
}

/* Five agents write into one stream and their frames arrive butted together,
 * so a heading, a failure announcement or a whole new sentence can begin in
 * the middle of a line: "…can be provided.The call to `bqml_predict` failed."
 * Three joins were observed live and each gets one rule.
 *
 * Backticks are handled in one pass over the spans, not two. A separate
 * lookahead pass gets this wrong in a way that is invisible until it is run on
 * a real answer: the engine restarts at every offset, so after failing on
 * `default_api:graph_traverse` it matches from that span's *closing* backtick
 * to the *opening* one of `INVALID_ARGUMENT`, and splits a bullet in half.
 * Scanning left to right pairs the backticks the way the model wrote them.
 *
 * The heading rule excludes a preceding '#' for the same class of reason: a
 * '###' contains a '##', so a rule that only asks what comes before the hash
 * breaks every heading into two empty paragraphs and a heading. */
function _unglue(text) {
  return String(text)
    .replace(/`[^`]*`([A-Z]?)/g, function (hit, next) {
      var span = hit.slice(0, hit.length - next.length).replace(/\s*\n\s*/g, " ");
      return next ? span + "\n\n" + next : span;
    })
    .replace(/([^\n#])(?=#{1,6} )/g, "$1\n\n")
    .replace(/([a-z,)])\.(?=[A-Z])/g, "$1.\n\n");
}

/* The plain sentence a whole failure passage becomes.
 *
 * The tool and the noun are read out of the passage rather than passed in,
 * because by the time the answer reaches this file the call that failed is
 * only described in prose. failLine() then says it in exactly the words the
 * activity log used a few lines further up the same page. */
function _failSentence(passage) {
  var name = "";
  var at = passage.length;
  Object.keys(TOOLS).forEach(function (id) {
    var found = passage.indexOf(id);
    if (found >= 0 && found < at) { at = found; name = id; }
  });
  if (!name) return "A step failed, so " + ANSWER_INCOMPLETE.charAt(0).toLowerCase() +
    ANSWER_INCOMPLETE.slice(1);
  var args = { sql: passage };
  Object.keys(TRAVERSALS).forEach(function (id) {
    if (!args.traversal && passage.indexOf(id) >= 0) args.traversal = id;
  });
  return failLine(name, args) + " " + ANSWER_INCOMPLETE;
}

/* Cut every failure passage out of the answer, leaving one plain sentence in
 * its place and handing the raw text back for the drawer.
 *
 * A passage runs across the blank lines inside it — announcement, blank,
 * bullets, blank, consequence is one passage and one sentence, not three — and
 * stops at the first line that is about the mine again.
 *
 * It also stops at the next announcement, which is the whole reason this is a
 * loop and not one regex. Two of the three failures in the live run were
 * written back to back by two different specialists, and run together they
 * collapsed to a single sentence naming one tool: the reader would have been
 * told one step failed when two had. */
function _cutFailures(lines) {
  var out = [];
  var kept = [];
  var i = 0;
  while (i < lines.length) {
    if (!_isFailLine(lines[i])) { out.push(lines[i]); i++; continue; }
    var passage = [];
    var j = i;
    while (j < lines.length) {
      if (j > i && _startsFailure(lines[j])) break;
      if (_isFailLine(lines[j])) { passage.push(lines[j]); j++; continue; }
      if (lines[j].trim() === "") {
        var k = j;
        while (k < lines.length && lines[k].trim() === "") k++;
        if (k < lines.length && _isFailLine(lines[k]) && !_startsFailure(lines[k])) {
          j = k;
          continue;
        }
      }
      break;
    }
    kept.push(passage.join("\n"));
    out.push("", _failSentence(passage.join("\n")), "");
    i = j;
  }
  return { lines: out, technical: kept.join("\n\n") };
}

/* What is left after the passages are gone, said in the estate's own words.
 *
 * Order is load-bearing. Brackets go first, so that a bracket holding an error
 * constant takes the constant with it before anything tries to rewrite inside
 * it. Tables go next and qualified before bare, so `mining_data.telemetry_stream`
 * becomes "the sensor readings" rather than two half-rewrites colliding.
 */
function _dejargon(line) {
  var out = line;

  out = out.replace(/\s*\(([^()]*)\)/g, function (whole, inside) {
    return MACHINE_TOKEN.test(inside) ? "" : whole;
  });

  out = out.replace(/`?\bmining_data\.([a-z0-9_]+)`?/g, function (hit, id) {
    var said = TABLES[id];
    return said ? articleFor(said) + said : id;
  });
  out = out.replace(/`([a-z][a-z0-9_]*)`/g, function (hit, id) {
    var said = TABLES[id];
    return said ? articleFor(said) + said : hit;
  });

  out = out.replace(TOOL_AFTER_CALL, function (hit, lead, id) {
    return lead + plainToolAbility(id);
  });
  out = out.replace(TOOL_ANYWHERE, function (hit, id) { return plainTool(id); });

  /* One word, not the whole JARGON map. "traversal" has no other meaning in a
   * sentence about a mine, so it is safe to swap wherever it lands. "node",
   * "edge" and "median" do have one, and a blind swap of those produces worse
   * English than the word it removed — see plainScope above for the same
   * argument made about the build's own prose. */
  out = out.replace(/\btraversals?\b/gi, function (hit) {
    var said = JARGON.traversal + (hit.charAt(hit.length - 1).toLowerCase() === "s" ? "s" : "");
    return hit.charAt(0) === hit.charAt(0).toUpperCase()
      ? said.charAt(0).toUpperCase() + said.slice(1)
      : said;
  });

  /* The backstop. A code span still holding machine vocabulary after all of
   * the above is one this file has no mapping for, and printing it would put
   * the identifier back on the page the rules just cleared. */
  return out.replace(/`([^`]*)`/g, function (hit, inner) {
    return MACHINE_TOKEN.test(inner) ? "" : hit;
  });
}

/* Bold before code, so that "**`vibration_hz`**" — which the live run wrote
 * five times — comes out as a bold code span rather than a code span with two
 * asterisks inside it. */
function _inline(escaped) {
  return escaped
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

/* The whole of the markdown this renderer supports: headings, unordered lists,
 * bold, code spans, paragraphs. No links, no images, no tables — a link in
 * text a model wrote is an attack surface, and the agents do not emit any of
 * the three.
 *
 * Headings clamp to h3 and h4 whatever the model asked for. The pane sits
 * under the sidecar's own h2, and an answer that opens an h1 outranks the
 * page it is printed on for anyone reading by heading order.
 */
function _markdown(lines) {
  var html = [];
  var para = [];
  var list = [];

  function flush() {
    if (para.length) { html.push("<p>" + _inline(para.join(" ")) + "</p>"); para = []; }
    if (list.length) {
      html.push("<ul>" + list.map(function (item) {
        return "<li>" + _inline(item) + "</li>";
      }).join("") + "</ul>");
      list = [];
    }
  }

  lines.forEach(function (raw) {
    var line = PLAIN_SHELL.esc(raw).trim();
    if (!line || /^-{3,}$/.test(line)) { flush(); return; }

    var heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      flush();
      var level = heading[1].length >= 4 ? "h4" : "h3";
      html.push("<" + level + ">" + _inline(heading[2]) + "</" + level + ">");
      return;
    }

    var item = /^[-*]\s+(.*)$/.exec(line);
    if (item) {
      if (para.length) { html.push("<p>" + _inline(para.join(" ")) + "</p>"); para = []; }
      list.push(item[1]);
      return;
    }

    if (list.length) flush();
    para.push(line);
  });

  flush();
  return html.join("");
}

/* The answer pane's one entry point.
 *
 * Returns the body copy as markup and the raw passages it removed as text, so
 * that the caller can file the second behind the technical drawer. Nothing is
 * discarded: a step that failed is still on the page, in the reader's words in
 * the body and in the model's own words one click away.
 */
function plainAnswer(rawText) {
  var text = _unglue(String(rawText || ""));
  if (!text.trim()) return { html: "", technical: "" };
  var cut = _cutFailures(text.split("\n"));
  return {
    html: _markdown(cut.lines.map(_dejargon)),
    technical: cut.technical,
  };
}

function unmapped(DATA) {
  var tables = {}, tools = {}, traversals = {};
  (DATA.catalog.agents || []).forEach(function (agent) {
    (agent.source_tables || []).forEach(function (t) {
      var bare = bareTable(t);
      if (!TABLES[bare]) tables[bare] = true;
    });
    /* All three tool maps, not just TOOLS. TOOL_DOING is what the live
     * activity log renders, so a tool missing only from that map prints its
     * own identifier at a reader in the most visible place on the screen —
     * and checking TOOLS alone would not notice. */
    (agent.tools || []).forEach(function (t) {
      if (!TOOLS[t] || !TOOL_DOING[t] || !TOOL_ABILITY[t]) tools[t] = true;
    });
    (agent.traversals || []).forEach(function (t) {
      if (!TRAVERSALS[t]) traversals[t] = true;
    });
  });
  return {
    tables: Object.keys(tables).sort(),
    tools: Object.keys(tools).sort(),
    traversals: Object.keys(traversals).sort(),
  };
}

if (typeof module !== "undefined") {
  module.exports = {
    TOOLS, TOOL_ABILITY, TRAVERSALS, TABLES, JARGON, NODE_TYPES, LINK_LABELS,
    TOOL_VERB, TOOL_FAILED, METHOD_DRIVERS,
    bareTable, plainTable, plainTool, plainToolAbility, plainTraversal, plainJargon,
    plainType, plainLink, plainScope, plainProse,
    articleFor, tableFromSql, callLine, failLine, gapLine, plainAnswer, unmapped,
  };
}
