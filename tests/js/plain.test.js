const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const P = require("../../apps/shared/plain.js");

// The bundle is a browser file: `window.MINING_DATA = {...};`. Node has no
// window, so the object is cut out and parsed rather than required.
function loadData() {
  const file = path.join(__dirname, "..", "..", "apps", "shared", "data", "bundle.js");
  const text = fs.readFileSync(file, "utf8");
  return JSON.parse(text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1));
}

test("bareTable strips the dataset prefix and backticks", () => {
  assert.equal(P.bareTable("mining_data.telemetry_stream"), "telemetry_stream");
  assert.equal(P.bareTable("`mining_data.telemetry_stream`"), "telemetry_stream");
  assert.equal(P.bareTable("telemetry_stream"), "telemetry_stream");
});

test("the map covers every tool, traversal and table in the catalogue", () => {
  const missing = P.unmapped(loadData());
  assert.deepEqual(missing, { tables: [], tools: [], traversals: [] });
});

test("a bq_query naming a table composes verb plus noun", () => {
  const line = P.callLine("bq_query", {
    sql: "SELECT * FROM `mining_data.telemetry_stream` LIMIT 10",
  });
  assert.equal(line, "Reading the sensor readings");
});

test("a graph_traverse names the traversal it runs", () => {
  assert.equal(
    P.callLine("graph_traverse", { traversal: "blast_radius" }),
    "Tracing what else stops if this stops"
  );
});

test("a call with no recognisable noun degrades to the tool verb alone", () => {
  assert.equal(P.callLine("operational_math", { expression: "1+1" }),
    "Working out the numbers");
  assert.equal(P.callLine("bq_query", {}), "Looking up records");
});

test("an unknown id renders its raw value rather than a guess", () => {
  assert.equal(P.plainTable("no_such_table"), "no_such_table");
  assert.equal(P.plainTool("no_such_tool"), "no_such_tool");
  assert.equal(P.plainTraversal("no_such_traversal"), "no_such_traversal");
  assert.equal(P.callLine("no_such_tool", {}), "no_such_tool");
});

/* Caught on a live run, not reasoned about in advance.
 *
 * A specialist asked the warehouse what columns exist before it queried
 * anything, which it does several times per run, and every one of those steps
 * printed "Reading the INFORMATION_SCHEMA" into the reader's activity log — six
 * occurrences, the most repeated string on the screen. bareTable strips the
 * dataset prefix and plainTable then finds no entry, so the identifier passed
 * straight through the one function whose job is to stop exactly that.
 *
 * It is a family of names rather than one, because the catalogue is several
 * tables and the agent picks whichever answers its question. To a reader they
 * are one thing: the list of what tables and columns exist. */
test("the warehouse catalogue is named in the reader's words, not BigQuery's", () => {
  const said = "list of tables and columns";
  assert.equal(P.plainTable("mining_data.INFORMATION_SCHEMA.COLUMNS"), said);
  assert.equal(P.plainTable("INFORMATION_SCHEMA.TABLES"), said);
  assert.equal(P.plainTable("`mining_data.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS`"), said);
});

test("a catalogue lookup reads as a sentence in the activity log", () => {
  assert.equal(
    P.callLine("bq_query", { table: "mining_data.INFORMATION_SCHEMA.COLUMNS" }),
    "Reading the list of tables and columns"
  );
  assert.equal(
    P.failLine("bq_query", { table: "mining_data.INFORMATION_SCHEMA.COLUMNS" }),
    "Couldn't read the list of tables and columns — that lookup failed."
  );
});

test("a real table whose name merely contains a schema word is untouched", () => {
  // The rule must key on the catalogue, not on the word "schema" appearing.
  assert.equal(P.plainTable("schema_change_log"), "schema_change_log");
});

test("a failed response names what failed", () => {
  assert.equal(
    P.failLine("graph_traverse", { traversal: "blast_radius" }),
    "Couldn't trace what else stops if this stops — that lookup failed."
  );
  assert.equal(
    P.failLine("bq_query", { sql: "SELECT 1 FROM `mining_data.assets`" }),
    "Couldn't read the machine register — that lookup failed."
  );
});

test("failLine bq_query on a non-articled table still carries the article", () => {
  assert.equal(
    P.failLine("bq_query", { sql: "SELECT * FROM `mining_data.telemetry_stream` LIMIT 10" }),
    "Couldn't read the sensor readings — that lookup failed."
  );
});

test("callLine bq_query on an articled table does not double the article", () => {
  assert.equal(
    P.callLine("bq_query", { sql: "SELECT * FROM `mining_data.assets` LIMIT 10" }),
    "Reading the machine register"
  );
});

test("a table phrase that is a relative clause is framed without an article", () => {
  // "Reading the which parts each supplier quoted" is not English. Five of the
  // twenty-five table phrases are clauses, not noun phrases.
  assert.equal(P.articleFor("machine register"), "the ");
  assert.equal(P.articleFor("which parts each supplier quoted"), "");
  assert.equal(P.articleFor("who was involved in each incident"), "");
  assert.equal(
    P.callLine("bq_query", { sql: "SELECT * FROM `mining_data.bid_parts_edge`" }),
    "Reading which parts each supplier quoted"
  );
  assert.equal(
    P.failLine("bq_query", { sql: "SELECT * FROM `mining_data.incident_involvements`" }),
    "Couldn't read who was involved in each incident — that lookup failed."
  );
});

test("every tool has a bare-verb phrase for the ability frame", () => {
  for (const id of Object.keys(P.TOOLS)) {
    assert.notEqual(P.TOOL_ABILITY[id], undefined, `${id} has no ability phrase`);
    assert.equal(P.plainToolAbility(id), P.TOOL_ABILITY[id]);
  }
  assert.equal(P.plainToolAbility("no_such_tool"), "no_such_tool");
});

test("tableFromSql finds the first qualified table and nothing else", () => {
  assert.equal(
    P.tableFromSql("SELECT a FROM `mining_data.assets` JOIN `mining_data.maintenance_logs`"),
    "assets"
  );
  assert.equal(P.tableFromSql("SELECT 1"), "");
  assert.equal(P.tableFromSql(undefined), "");
});

test("jargon substitutions are available to the copy rewrite", () => {
  assert.equal(P.plainJargon("entrypoint"), "agent you can talk to");
  assert.equal(P.plainJargon("blast radius"), "what else stops");
  assert.equal(P.plainJargon("not a jargon term"), "not a jargon term");
});

/* The screens do not write all of their own copy. Three of them print a
 * persona's accountable_for straight out of the catalogue, and that prose was
 * written by the people who built the estate, in their words: "must approve or
 * decline HITL prompts from D37 and S11". A de-jargoning pass that rewrites
 * every sentence a screen composes and prints that one untouched has not
 * finished. */
test("the prose the catalogue supplies is said in the reader's words too", () => {
  const said = P.plainProse(
    "The HSE Lead must approve or decline HITL prompts from D37 and S11."
  );
  assert.equal(
    said,
    "The HSE Lead must approve or decline sign-off requests from D37 and S11."
  );
  assert.equal(
    P.plainProse("is also the HITL approver for crusher setpoint changes"),
    "is also the sign-off authority for crusher setpoint changes"
  );
  assert.equal(P.plainProse(""), "");
  assert.equal(P.plainProse(undefined), "");
});

/* accountable_for was one field written by the people who built the estate and
 * printed whole. It was not the only one. facts.json's `why` and graph.json's
 * `source` reach the scenario and graph screens by the same route, and they
 * carry the other half of the estate's vocabulary: a file path, a dataset, a
 * table identifier and a product name, in one sentence, at a shift supervisor.
 *
 * Run over the generated data itself rather than over a transcription of it, so
 * this fails when the build starts writing something new — which is the moment
 * it would actually happen. */
test("the machinery's own names are said in the reader's words too", () => {
  const read = (name) =>
    JSON.parse(
      fs.readFileSync(
        path.join(__dirname, "..", "..", "apps", "shared", "data", name),
        "utf8"
      )
    );

  const machinery = /[\w*.-]+(?:\/[\w*.-]+)+\.[a-z]{2,8}|\b[a-z][a-z0-9]*_[a-z0-9_]+\b|\bBigQuery\b/;
  const lines = read("facts.json")
    .not_locally_derivable.map((u) => u.why)
    .concat(read("graph.json").source);

  assert.ok(lines.length >= 2, "the generated data no longer carries these fields");
  for (const before of lines) {
    assert.ok(machinery.test(before), `nothing to rewrite in ${before}`);
    const after = P.plainProse(before);
    assert.ok(!machinery.test(after), `still says the machinery's name: ${after}`);
    // Substitution, not deletion, as with the HITL prose above: the sentence
    // has to survive at roughly the length it arrived, or the fact went with
    // the vocabulary.
    assert.ok(
      after.length > before.length * 0.7,
      `the rewrite dropped most of the sentence: ${after}`
    );
  }

  // A replacement landing at the head of a sentence takes the capital that was
  // there; one landing mid-string does not invent one, because these fields are
  // also printed after an em dash.
  assert.match(P.plainProse("BigQuery settles it."), /^The warehouse settles it\.$/);
  assert.match(
    P.plainProse("is settled by BigQuery"),
    /^is settled by the warehouse$/
  );
});

/* The graph screen prints three lines the build wrote — "All 5 assets and all 3
 * dependency edges. Nothing filtered." — on the one screen whose whole subject
 * is edges and nodes. The rewriter that was supposed to fix them knew the word
 * "traversal" and neither of the other two, so it ran over every line and
 * changed nothing on any of them. */
test("plainScope says the three structural words in the reader's terms", () => {
  assert.equal(
    P.plainScope("All 5 assets and all 3 dependency edges. Nothing filtered."),
    "All 5 assets and all 3 dependency links. Nothing filtered."
  );
  assert.equal(
    P.plainScope("The traversal returns one row per node it reaches."),
    "The connection trace returns one row per machine it reaches."
  );
  // A leading capital belongs to the sentence, not to the word, so it survives.
  assert.equal(P.plainScope("Edges only."), "Links only.");
  assert.equal(P.plainScope(""), "");
  assert.equal(P.plainScope(undefined), "");
});

test("plainScope substitutes, and never quietly drops", () => {
  // Same shape as the prose test below: strike the jargon out of the original
  // and its replacement out of the rewrite, and the remainders must be
  // identical. A rewriter that deleted the sentence would satisfy "no edges
  // left" and fail here.
  const lines = Object.values(loadData().graph.graphs).map((g) => g.scope);
  assert.ok(lines.length >= 3, "the graph export no longer carries scope lines");
  const terms = [
    ["traversals?", "connection traces?"],
    ["edges?", "links?"],
    ["nodes?", "machines?"],
  ];
  for (const before of lines) {
    const after = P.plainScope(before);
    assert.ok(
      !/\b(traversals?|edges?|nodes?)\b/i.test(after),
      `still the build's words: ${after}`
    );
    const strip = (text) =>
      terms
        .reduce((t, [jargon, plain]) => t.replace(new RegExp(`\\b(${jargon}|${plain})\\b`, "gi"), ""), text)
        .replace(/\s+/g, " ")
        .trim();
    assert.equal(strip(after), strip(before), `text lost rewriting: ${before}`);
  }
});

/* plainType and plainLink are what stop "FatigueLog" and "REPLACED_PART"
 * reaching a reader who opened this screen to avoid exactly that. They are here
 * rather than in graph.js because the estate has one vocabulary, and a second
 * copy of it inside one screen is a copy free to drift. */
test("every record type and link the graph draws has a plain name", () => {
  const graphs = loadData().graph.graphs;
  for (const [name, g] of Object.entries(graphs)) {
    for (const label of Object.keys(g.node_types)) {
      assert.notEqual(P.NODE_TYPES[label], undefined, `${name}: ${label} unnamed`);
      assert.equal(P.plainType(label), P.NODE_TYPES[label]);
      assert.ok(!/[A-Z_]/.test(P.plainType(label)), `${name}: ${label} still reads as a label`);
    }
    for (const label of Object.keys(g.edge_labels)) {
      assert.notEqual(P.LINK_LABELS[label], undefined, `${name}: ${label} unnamed`);
      assert.equal(P.plainLink(label), P.LINK_LABELS[label]);
      assert.ok(!/[A-Z_]/.test(P.plainLink(label)), `${name}: ${label} still reads as a label`);
    }
  }
});

test("an unnamed record type or link renders its raw label rather than nothing", () => {
  // Blank is worse than the label: an empty cell in the estate table reads as
  // "this graph has no such records", which is a false statement about the mine.
  assert.equal(P.plainType("NoSuchLabel"), "NoSuchLabel");
  assert.equal(P.plainLink("NO_SUCH_EDGE"), "NO_SUCH_EDGE");
  assert.equal(P.plainType(undefined), "");
});

test("rewriting the catalogue's prose substitutes, and never quietly drops", () => {
  const data = loadData();
  const personas = data.personas.personas || data.personas;
  for (const [code, persona] of Object.entries(personas)) {
    const before = String(persona.accountable_for || "");
    const after = P.plainProse(before);
    assert.ok(!/\bHITL\b/i.test(after), `${code} still says HITL: ${after}`);
    // Substitution, not deletion: strike the jargon out of the original and the
    // replacement out of the rewrite, and what is left has to be identical. A
    // rewriter that dropped the clause would pass the check above and fail this
    // one, which is the failure worth having.
    const strip = (text) =>
      text
        .replace(/HITL prompts?/gi, "")
        .replace(/HITL approver/gi, "")
        .replace(/sign-off requests?/gi, "")
        .replace(/sign-off authority/gi, "")
        .replace(/\s+/g, " ")
        .trim();
    assert.equal(strip(after), strip(before), `${code} lost text in the rewrite`);
  }
});

/* Working a driver tree is five calls to one tool, and the activity log is the
 * only place the reader can see the method being worked rather than a spinner.
 * Before this, run_diagnostic had no TOOL_VERB entry, so every one of those
 * five steps fell through to the same generic headline — "Checking one cause
 * against the data", five times in a row — and doc_search never said what it
 * searched for, although the query was in the arguments the whole time. */
test("each driver in the tree names the cause it is checking", () => {
  assert.equal(P.callLine("run_diagnostic", { driver_id: "liberation" }),
    "Checking whether the crusher setting is costing recovery");
  assert.equal(P.callLine("run_diagnostic", { driver_id: "bypass" }),
    "Checking whether the crusher's divert valve is costing recovery");
  // Five drivers, five distinct lines: the repetition is the defect.
  const ids = ["liberation", "feed_variability", "bypass", "reagent_regime",
               "grind_size_p80"];
  const lines = ids.map((id) => P.callLine("run_diagnostic", { driver_id: id }));
  assert.equal(new Set(lines).size, ids.length, lines.join(" | "));
});

test("a doc_search says what it searched the documents for", () => {
  assert.equal(
    P.callLine("doc_search", { query: "crusher bypass valve clog", k: 5 }),
    "Searching the site's documents for “crusher bypass valve clog”");
});

test("a long search query is cut rather than filling the log with a paragraph", () => {
  const line = P.callLine("doc_search", { query: "a".repeat(200) });
  assert.ok(line.length < 110, `an activity line ran to ${line.length} characters`);
  assert.ok(line.endsWith("…”"), line);
});

test("a failed method step says which cause or query it was on", () => {
  assert.equal(P.failLine("run_diagnostic", { driver_id: "liberation" }),
    "Couldn't check whether the crusher setting is costing recovery — " +
    "that lookup failed.");
  assert.equal(P.failLine("doc_search", { query: "torque limit" }),
    "Couldn't search the site's documents for “torque limit” — that lookup failed.");
});

/* run_diagnostic returns success: true for a driver the pack declares but has
 * no diagnostic behind it — see mining_agents/tools/run_diagnostic.py. Before
 * that fix it returned a failure envelope, and the activity log rendered
 * failLine's "that lookup failed" for a call that had not failed at all. The
 * new gapLine() must read as neither a failure nor an ordinary success: it has
 * to say plainly that the driver is declared and uninstrumented. */
test("a not-instrumented driver reads as a declared gap, not a failure", () => {
  const line = P.gapLine("run_diagnostic", { driver_id: "reagent_regime" });
  assert.equal(
    line,
    "Checking whether the reagent regime is costing recovery — no diagnostic " +
    "covers this driver; it is declared in the tree, not instrumented."
  );
  assert.ok(!line.includes("failed"), `gapLine must not say "failed": ${line}`);
  assert.ok(!line.includes("Couldn't"), `gapLine must not open like a failure: ${line}`);
});

test("gapLine names the driver the same way callLine does", () => {
  // Both success-with-rows and success-with-a-gap name the driver through the
  // same noun/verb machinery, so a reader sees the same driver name whichever
  // path the call took.
  const ids = ["liberation", "feed_variability", "bypass", "reagent_regime",
               "grind_size_p80"];
  for (const id of ids) {
    const called = P.callLine("run_diagnostic", { driver_id: id });
    const gapped = P.gapLine("run_diagnostic", { driver_id: id });
    assert.ok(gapped.startsWith(called),
      `gapLine for ${id} does not build on callLine's own phrasing: ${gapped}`);
  }
});

test("an unknown driver id renders the tool's own line rather than the id", () => {
  // Same rule as everywhere else in this file: an id with no phrase is not
  // guessed at. A fork's new driver reads as the generic headline until
  // somebody writes its phrase — which the coverage test below is what
  // notices.
  assert.equal(P.callLine("run_diagnostic", { driver_id: "no_such_driver" }),
    "Checking one cause against the data");
});

test("every driver in every shipped method pack has a phrase", () => {
  // The driver ids live in method/*.yaml, which this file cannot see and the
  // bundle does not carry, so unmapped() cannot report them. Read the packs.
  const dir = path.join(__dirname, "..", "..", "method");
  const packs = fs.readdirSync(dir).filter((f) => f.endsWith(".yaml"));
  assert.ok(packs.length, "no method pack found — this test would prove nothing");
  for (const pack of packs) {
    const text = fs.readFileSync(path.join(dir, pack), "utf8");
    const ids = [...text.matchAll(/^\s*-\s*id:\s*(\S+)/gm)].map((m) => m[1]);
    assert.ok(ids.length, `${pack} declares no driver`);
    for (const id of ids) {
      assert.ok(P.METHOD_DRIVERS[id],
        `${pack}: driver "${id}" has no reader-facing phrase, so the activity ` +
        "log will print the identifier at someone who came here to avoid one");
    }
  }
});

/* fatigue_to_incident exists twice: as a graph traversal and as a P3 driver.
 * The traversal walks a graph edge ("how crew fatigue connects to incidents").
 * The driver asks whether the data supports attributing incidents to fatigue at all.
 * They are different operations; identical wording would mislead a reader watching
 * the activity log. This test pins the distinction so a later edit that collapses
 * them fails loudly. */
test("fatigue_to_incident has distinct phrasings as a traversal and as a driver", () => {
  const traversalPhrase = P.TRAVERSALS.fatigue_to_incident;
  const driverPhrase = P.METHOD_DRIVERS.fatigue_to_incident;
  assert.ok(traversalPhrase, "fatigue_to_incident must have a traversal phrase");
  assert.ok(driverPhrase, "fatigue_to_incident must have a driver phrase");
  assert.notEqual(traversalPhrase, driverPhrase,
    "the traversal and driver phrases must differ: the traversal walks a graph " +
    "edge; the driver asks a coverage question the data cannot yet answer");
});

test("every driver id in every pack has a plain phrase", () => {
  // The fixture is a committed JSON file generated by scripts/gen_driver_ids.py.
  // tests/scripts/test_driver_ids_fixture.py fails if the fixture drifts from
  // method/*.yaml, so that test is what catches a new driver added without
  // re-running the generator. This test's job is narrower: given the ids the
  // fixture lists, every one must have a callLine output that does not print the
  // raw id at a reader. A phrase that is present but still contains the id
  // (e.g., "Checking cost_concentration") would pass a map-key test and fail
  // here, which is the failure worth having.
  const ids = require("../fixtures/driver-ids.json"); // written in step 3
  for (const id of ids) {
    const line = P.callLine("run_diagnostic", { driver_id: id });
    assert.ok(line && !line.includes(id), `no plain phrase for ${id}: ${line}`);
  }
});

test("every tool with a composed verb can also say that it failed", () => {
  // unmapped() checks TOOLS, TOOL_DOING and TOOL_ABILITY, and cannot see this
  // pair: TOOL_VERB is deliberately partial — only the tools whose arguments
  // carry a noun have one — so "missing from TOOL_VERB" is not a defect the
  // catalogue can define. What IS a defect is a tool that names its noun while
  // running and loses it the moment it fails, which is exactly the moment the
  // reader most needs to know which step broke.
  assert.deepEqual(Object.keys(P.TOOL_VERB).sort(), Object.keys(P.TOOL_FAILED).sort());
});
