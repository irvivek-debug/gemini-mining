const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const R = require("../../apps/workspace/router.js");

function loadData() {
  const file = path.join(__dirname, "..", "..", "apps", "shared", "data", "bundle.js");
  const text = fs.readFileSync(file, "utf8");
  return JSON.parse(text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1));
}

const DATA = loadData();
const CODES = Object.keys(DATA.personas.personas).sort();

test("there are eight personas, so the table-driven tests below cover them all", () => {
  assert.deepEqual(CODES, ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]);
});

test("branchesOf normalises a bare string and a list alike", () => {
  assert.deepEqual(R.branchesOf("asset_reliability"), ["asset_reliability"]);
  assert.deepEqual(R.branchesOf(["supply_chain", "procurement"]),
    ["supply_chain", "procurement"]);
  assert.deepEqual(R.branchesOf(undefined), []);
});

test("every persona's routing stays inside that persona's own agents", () => {
  const questions = [
    "Which assets are most at risk right now?",
    "What runs out if this part runs out?",
    "Show me crew fatigue against incidents",
    "How is recovery tracking against the ordinary day?",
    "What should I sign off before the shift ends?",
  ];
  for (const code of CODES) {
    const allowed = new Set(DATA.personas.personas[code].agents);
    for (const q of questions) {
      const pick = R.route(q, code, DATA);
      assert.ok(allowed.has(pick.agent_id),
        `${code} routed "${q}" to ${pick.agent_id}, which is not one of its agents`);
      assert.ok(pick.reason.length > 0, `${code} gave no reason for "${q}"`);
      for (const up of pick.runners_up) {
        assert.ok(allowed.has(up.agent_id));
        assert.notEqual(up.agent_id, pick.agent_id);
      }
    }
  }
});

/* The reason is a clause, and chat.js prints it after "Asking <agent>." — so a
 * reason that names the agent itself says the name twice, and the names on this
 * catalogue run to seven words. */
test("no reason ever names an agent, because the caller already has", () => {
  const questions = [
    "What should I look at first?",
    "What changed since yesterday?",
    "Which assets are most at risk right now?",
    "Show me the crew fatigue readings",
    "Is anything waiting on my sign-off?",
    "the and of a to is it",
  ];
  const names = DATA.catalog.agents
    .map((a) => a.display_name)
    .filter((n) => n && n.length);
  for (const code of CODES) {
    for (const q of questions.concat(R.starterQuestions(code, DATA))) {
      const reason = R.route(q, code, DATA).reason;
      for (const name of names) {
        assert.ok(!reason.includes(name),
          `${code}: the reason for "${q}" names ${name}: ${reason}`);
      }
    }
  }
});

test("a question that named no capability says so, without naming the agent", () => {
  const pick = R.route("What should I look at first?", "P1", DATA);
  assert.equal(pick.reason,
    "Nothing in the question named a capability, so it goes to the agent " +
    "this role leads with.");
});

test("a table in the reason carries the article its phrase does not", () => {
  // TABLES phrases hold no leading article, because the frame that uses them
  // owns it — "Reading the machine register", "What's in the machine register".
  assert.equal(R.route("What does the machine register say?", "P1", DATA).reason,
    "It reads the machine register.");
});

test("a table phrase that is already a clause takes no article", () => {
  assert.equal(R.route("Show me who drove what.", "P7", DATA).reason,
    "It reads who drove what.");
});

test("two matches sharing a verb say the verb once", () => {
  assert.equal(R.route("What's in the parts on hand right now?", "P2", DATA).reason,
    "It reads the parts each work order needs and the parts on hand.");
});

test("a tool in the reason reads as an ability, not as a bare gerund", () => {
  // TOOLS phrases are gerunds for prose elsewhere; "It asking for your
  // sign-off." is not a sentence.
  assert.equal(R.route("Is anything waiting on my sign-off?", "P1", DATA).reason,
    "It can ask for your sign-off.");
});

test("a match on the agent's own name does not restate the name as a capability", () => {
  // "risk" is a word of Fatigue Risk Scorer's name and of nothing else it has.
  const pick = R.route("Which assets are most at risk right now?", "P3", DATA);
  assert.equal(
    DATA.catalog.agents.find((a) => a.agent_id === pick.agent_id).display_name,
    "Fatigue Risk Scorer");
  assert.equal(pick.reason, "Your question matched its name and nothing more specific.");
});

test("P8 has one agent, so it names it and offers nothing to change to", () => {
  assert.deepEqual(DATA.personas.personas.P8.agents, ["S12"]);
  const pick = R.route("What happened on the last shift?", "P8", DATA);
  assert.equal(pick.agent_id, "S12");
  assert.ok(pick.reason.length > 0);
  assert.deepEqual(pick.runners_up, []);
});

test("P4's list-valued value_branch does not throw", () => {
  assert.deepEqual(DATA.personas.personas.P4.value_branch,
    ["supply_chain", "procurement"]);
  const pick = R.route("Which suppliers quoted for this part?", "P4", DATA);
  assert.ok(DATA.personas.personas.P4.agents.includes(pick.agent_id));
});

test("a question of pure stop-words still returns a valid agent", () => {
  for (const code of CODES) {
    const pick = R.route("the and of a to is it", code, DATA);
    assert.ok(DATA.personas.personas[code].agents.includes(pick.agent_id));
    assert.ok(pick.reason.length > 0);
  }
});

test("an empty question returns a valid agent", () => {
  const pick = R.route("", "P1", DATA);
  assert.ok(DATA.personas.personas.P1.agents.includes(pick.agent_id));
});

test("identical inputs give identical output", () => {
  const a = R.route("Which assets are most at risk right now?", "P1", DATA);
  const b = R.route("Which assets are most at risk right now?", "P1", DATA);
  assert.deepEqual(a, b);
});

test("every persona gets exactly three starter questions", () => {
  for (const code of CODES) {
    const starters = R.starterQuestions(code, DATA);
    assert.equal(starters.length, 3, `${code} produced ${starters.length}`);
    assert.equal(new Set(starters).size, 3, `${code} repeated a starter`);
    for (const q of starters) assert.ok(q.trim().length > 0);
  }
});

test("a starter always routes to the agent it was derived from", () => {
  for (const code of CODES) {
    const items = R._starterItems(code, DATA);
    for (const item of items) {
      const pick = R.route(item.q, code, DATA);
      assert.ok(DATA.personas.personas[code].agents.includes(pick.agent_id),
        `${code}: starter "${item.q}" routed outside the persona`);
      if (!item.agent) {
        // Two kinds are not derived from an agent and so cannot round-trip to
        // one: the generic backstops, and the governing question, which comes
        // from the persona's method rather than from any single agent's
        // capabilities. Both are still held to routing inside the persona,
        // asserted above. Anything else carrying no agent is a bug in
        // _starterItems that would otherwise pass here silently.
        assert.ok(item.isGeneric || item.isMethod,
          `${code}: starter "${item.q}" names no agent and no reason for it`);
      } else {
        // The core guarantee: the starter must route to the exact agent it was
        // derived from, not merely any agent in the persona.
        assert.strictEqual(pick.agent_id, item.agent.agent_id,
          `${code}: starter "${item.q}" was derived from ${item.agent.agent_id} ` +
          `but routed to ${pick.agent_id}`);
      }
    }
  }
});

test("a starter never names a capability its agent does not have", () => {
  const P = require("../../apps/shared/plain.js");
  const phrases = Object.values(P.TABLES)
    .concat(Object.values(P.TRAVERSALS))
    .concat(Object.values(P.TOOLS));
  for (const code of CODES) {
    const items = R._starterItems(code, DATA);
    for (const item of items) {
      if (item.isGeneric) {
        // Generic backstops name no capability by construction — assert that
        // explicitly rather than passing vacuously through the phrase loop.
        for (const phrase of phrases) {
          assert.ok(!item.q.toLowerCase().includes(phrase.toLowerCase()),
            `${code}: generic starter "${item.q}" contains capability phrase "${phrase}"`);
        }
        continue;
      }
      const pick = R.route(item.q, code, DATA);
      const agent = DATA.catalog.agents.find((a) => a.agent_id === pick.agent_id);
      const owned = new Set(
        (agent.source_tables || []).map((t) => P.plainTable(t))
          .concat((agent.traversals || []).map((t) => P.plainTraversal(t)))
          .concat((agent.tools || []).map((t) => P.plainTool(t)))
      );
      for (const phrase of phrases) {
        if (item.q.toLowerCase().includes(phrase.toLowerCase())) {
          assert.ok(owned.has(phrase),
            `${code}: starter "${item.q}" names "${phrase}", which ${pick.agent_id} does not have`);
        }
      }
    }
  }
});

/* The governing starter.
 *
 * A persona whose method pack names a governing metric leads with a question
 * about improving it. Before this, P6's three starters were "What's in the
 * sensor readings right now?", "What's in the crusher run states right now?"
 * and "What's in the plant recovery records right now?" — three table dumps on
 * the landing screen for the one role this branch redesigned around problem
 * solving, and the customer's exact criticism ("more like a natural-language-
 * to-SQL thing than agents that replicate best-performing practice") printed
 * back at them in their own words.
 */
test("a persona with a governing metric leads with it, not with a table", () => {
  const metric = DATA.personas.personas.P6.method.metric;
  assert.ok(metric, "P6 lost its governing metric from the export");
  const first = R.starterQuestions("P6", DATA)[0];
  assert.ok(first.includes(metric),
    `P6's first starter does not name "${metric}": ${first}`);
  assert.ok(!/^What's in the /.test(first),
    `P6 still opens with a table question: ${first}`);
  // It has to be a problem-solving question, not a metric-shaped table dump.
  assert.ok(/problems/i.test(first) && /resolve/i.test(first), first);
});

test("the governing starter routes into the persona that owns the metric", () => {
  // A starter that routed elsewhere would teach the reader the wrong thing
  // about what the page does, which is why every derived starter is checked by
  // routing it back. This one is derived from the persona's method rather than
  // from an agent's capabilities, so it gets the check the others get.
  const first = R.starterQuestions("P6", DATA)[0];
  const pick = R.route(first, "P6", DATA);
  assert.ok(DATA.personas.personas.P6.agents.includes(pick.agent_id), pick.agent_id);
  assert.equal(pick.agent_id, "S07",
    "the governing question no longer reaches the swarm that holds the method");
});

test("the governing starter claims no direction for any persona's metric", () => {
  /* Found in a browser, not here, which is why this test exists.
   *
   * The frame was "I want to improve X … the top problems dragging it down".
   * Against P6's unit cost that passes a reading; against the four metrics
   * added since, it does not. The HSE Lead's page rendered "I want to improve
   * severity-weighted incident exposure" — on the one role whose subject is
   * people getting hurt, a sentence asking for more of it. The Geologist's
   * rendered "improve contained-metal variance", which you close, not grow.
   * And "dragging it down" was backwards even for the cost metrics it was
   * written for, since a problem drives cost up.
   *
   * Every test above passed throughout, because they check that the starter
   * names the metric and asks about problems — never that the sentence means
   * what it says. A metric-shaped hole: the frame is written once and read
   * against whichever metric a fork adds, so it must assert nothing about
   * which way good lies.
   */
  const directional = [
    "improve", "increase", "reduce", "raise", "lower",
    "dragging it down", "pushing it up", "maximise", "minimise",
  ];
  let checked = 0;
  for (const code of CODES) {
    const method = DATA.personas.personas[code].method;
    if (!method) continue;
    checked += 1;
    const first = R.starterQuestions(code, DATA)[0];
    assert.ok(first.includes(method.metric),
      `${code}'s governing starter does not name its metric: ${first}`);
    for (const word of directional) {
      assert.ok(!first.toLowerCase().includes(word),
        `${code}: the governing starter says "${word}", which asserts which ` +
        `way good lies for "${method.metric}" — a claim the frame cannot ` +
        `make, because it is written once for every metric: ${first}`);
    }
  }
  // Without this the loop is vacuous the moment the export drops its packs,
  // and a green suite would mean nothing was checked at all.
  assert.ok(checked >= 5,
    `expected at least 5 personas carrying a method pack, saw ${checked}`);
});

test("a persona with no method pack keeps exactly the starters it had", () => {
  // The metric is the only thing that changes this, so a persona without one
  // must be untouched — including the three the reader has already seen.
  for (const code of CODES) {
    if (DATA.personas.personas[code].method) continue;
    const items = R._starterItems(code, DATA);
    assert.equal(items.length, 3, code);
    for (const item of items) assert.ok(!item.isMethod, `${code}: ${item.q}`);
  }
  assert.deepEqual(R.starterQuestions("P1", DATA).length, 3);
});
