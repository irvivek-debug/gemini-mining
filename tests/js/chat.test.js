/* The sidecar, in two halves.
 *
 * The pure half — which agent is named, which alternatives are offered, what the
 * cold start looks like — is checked directly. The half that touches the DOM is
 * checked through a stub surface, because the one behaviour worth pinning there
 * is not the markup but the stream lifecycle: EventSource reconnects by itself
 * when a connection closes, so a sidecar that abandons a stream without closing
 * it re-asks a hundred-second question forever and bills for every repeat.
 */
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const C = require("../../apps/workspace/chat.js");

function loadData() {
  const file = path.join(__dirname, "..", "..", "apps", "shared", "data", "bundle.js");
  const text = fs.readFileSync(file, "utf8");
  return JSON.parse(text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1));
}

const DATA = loadData();

test("the pick line names the agent and gives the reason", () => {
  const line = C.pickLine(
    { agent_id: "S01", reason: "It reads sensor readings.", runners_up: [] },
    DATA
  );
  assert.ok(line.includes("Cascading Failure Impact & Recovery Coordinator"),
    `the line does not name the agent: ${line}`);
  assert.ok(line.includes("It reads sensor readings."));
});

test("the pick line survives an agent id the catalogue does not hold", () => {
  const line = C.pickLine({ agent_id: "NOPE", reason: "because", runners_up: [] }, DATA);
  assert.ok(line.includes("NOPE"));
});

test("the pick line never prints an agent id when a name exists", () => {
  const line = C.pickLine(
    { agent_id: "S01", reason: "It reads sensor readings.", runners_up: [] },
    DATA
  );
  assert.ok(!line.includes("S01"), `the id is jargon and leaked into: ${line}`);
});

test("every persona's sidecar opens with three starters and a valid first pick", () => {
  const R = require("../../apps/workspace/router.js");
  for (const code of Object.keys(DATA.personas.personas)) {
    const opening = C.opening(code, DATA);
    assert.equal(opening.starters.length, 3, `${code} opened with ${opening.starters.length}`);
    assert.equal(opening.title, DATA.personas.personas[code].title,
      `${code} opened under a title that is not its own`);

    // The pick the reader gets if they click the first starter, which is the
    // most likely first thing to happen on this screen.
    const decision = R.route(opening.starters[0], code, DATA);
    assert.ok(DATA.personas.personas[code].agents.includes(decision.agent_id),
      `${code}: its own first starter routed to ${decision.agent_id}`);
    const line = C.pickLine(decision, DATA);
    const name = DATA.catalog.agents
      .find((a) => a.agent_id === decision.agent_id).display_name;
    assert.equal(line, `Asking ${name}. ${decision.reason}`);
    assert.ok(!line.includes(decision.agent_id),
      `${code}: the agent id is jargon and leaked into: ${line}`);
  }
});

test("the pick line names the agent once, not once per clause", () => {
  const R = require("../../apps/workspace/router.js");
  for (const code of Object.keys(DATA.personas.personas)) {
    for (const q of C.opening(code, DATA).starters.concat([
      "What should I look at first?",
      "Which assets are most at risk right now?",
      "Is anything waiting on my sign-off?",
    ])) {
      const decision = R.route(q, code, DATA);
      const name = DATA.catalog.agents
        .find((a) => a.agent_id === decision.agent_id).display_name;
      const line = C.pickLine(decision, DATA);
      assert.equal(line.split(name).length - 1, 1,
        `${code}: "${q}" produced a line that says the agent's name twice: ${line}`);
    }
  }
});

test("P8 is offered nothing to change to, because it has one agent", () => {
  const R = require("../../apps/workspace/router.js");
  const decision = R.route("what happened last shift?", "P8", DATA);
  assert.deepEqual(C.alternatives(decision, DATA), []);
});

test("a persona with several agents is offered named alternatives", () => {
  const R = require("../../apps/workspace/router.js");
  const decision = R.route("which assets are most at risk?", "P1", DATA);
  const alts = C.alternatives(decision, DATA);
  assert.equal(alts.length, decision.runners_up.length);
  assert.ok(alts.length > 0, "P1 has several agents and offered no alternative at all");
  for (const alt of alts) {
    assert.ok(alt.agent_id && alt.label,
      "an alternative must carry both the id it asks and the name it shows");
    assert.notEqual(alt.label, alt.agent_id,
      "the button shows the agent's name, not its id — the id is jargon");
  }
});

/* ---------- the stream lifecycle ---------- */

/* A surface, not a DOM. mountChat writes its shell with innerHTML and then only
 * ever appends elements it made itself, so a stub that records appends is enough
 * to follow a conversation. Selectors resolve to a stub apiece, remembered, so
 * two lookups of #transcript are the same node — which is the only structural
 * assumption mountChat makes. */
function stubElement(tag) {
  return {
    tagName: tag,
    className: "",
    type: "",
    children: [],
    listeners: {},
    _text: "",
    _html: "",
    get textContent() { return this._text; },
    set textContent(value) { this._text = String(value); },
    /* A browser reparses on assignment, so setting innerHTML changes what
     * textContent reads back. The answer pane is now written as markup and the
     * end-of-stream check reads text, so a stub that let the two disagree would
     * pass on behaviour a browser does not have. */
    get innerHTML() { return this._html; },
    set innerHTML(value) {
      this._html = String(value);
      this._text = String(value).replace(/<[^>]*>/g, "");
    },
    appendChild(child) { this.children.push(child); return child; },
    addEventListener(name, fn) {
      (this.listeners[name] = this.listeners[name] || []).push(fn);
    },
  };
}

/* The selectors persona.html actually contains. A stub that minted a node for
 * anything asked of it would let `#transcirpt` pass here and fail in a browser,
 * which is the one direction a stub must never be wrong in. */
const SELECTORS = ["#transcript", "#composer", "#question"];

/* The inverse of shell.js's esc(). A browser decodes entities as it parses the
 * markup, so the text on a starter button is the question, not its escaped
 * source — and the button's text is what gets sent when it is clicked. */
function unesc(text) {
  return String(text)
    .replace(/&quot;/g, '"')
    .replace(/&gt;/g, ">")
    .replace(/&lt;/g, "<")
    .replace(/&amp;/g, "&");
}

function stubRoot() {
  const found = {};
  let starters = null;
  const root = stubElement("aside");
  root.querySelector = function (selector) {
    if (!SELECTORS.includes(selector)) return null;
    if (!found[selector]) found[selector] = stubElement("div");
    return found[selector];
  };
  root.querySelectorAll = function (selector) {
    if (selector !== ".starter") return [];
    if (starters) return starters;      // the same nodes, so listeners survive
    starters = [];
    const re = /<button class="starter" type="button">([\s\S]*?)<\/button>/g;
    let match;
    while ((match = re.exec(root.innerHTML))) {
      const button = stubElement("button");
      button.className = "starter";
      button.textContent = unesc(match[1]);
      starters.push(button);
    }
    return starters;
  };
  return root;
}

/* A stream that never finishes on its own, so a test can say when it ends. */
function recorder() {
  const opened = [];
  function streamAgent(options) {
    const handle = {
      options: options,
      closed: false,
      close() { this.closed = true; },
    };
    opened.push(handle);
    return handle;
  }
  return { opened, streamAgent };
}

function mount(code, rec) {
  const root = stubRoot();
  global.document = { createElement: stubElement };
  const chat = C.mountChat(root, code, DATA, { streamAgent: rec.streamAgent });
  return { root, chat, transcript: root.querySelector("#transcript") };
}

test("asking a second question closes the first stream", () => {
  const rec = recorder();
  const { chat } = mount("P1", rec);

  chat.ask("which assets are most at risk?");
  chat.ask("what changed since yesterday?");

  assert.equal(rec.opened.length, 2, "the second question never reached an agent");
  assert.equal(rec.opened[0].closed, true,
    "the first stream is still open — EventSource will keep re-asking it");
  assert.equal(rec.opened[1].closed, false, "the live stream was closed too");
});

test("closing the sidecar closes the stream it left running", () => {
  const rec = recorder();
  const { chat } = mount("P1", rec);
  chat.ask("which assets are most at risk?");
  chat.close();
  assert.equal(rec.opened[0].closed, true);
});

test("an abandoned stream does not write into the transcript it left behind", () => {
  const rec = recorder();
  const { chat, transcript } = mount("P1", rec);

  chat.ask("which assets are most at risk?");
  chat.ask("what changed since yesterday?");
  // agent-stream's close() calls onDone, and a late frame can do the same.
  rec.opened[0].options.onDone();
  rec.opened[0].options.onStep({ kind: "text", text: "half an answer" });

  const answers = transcript.children.filter((c) => c.className === "answer");
  assert.equal(answers.length, 2);
  assert.equal(answers[0].textContent, "",
    "the abandoned answer took text from a stream the reader stopped");

  chat.ask("a third question");
  assert.equal(rec.opened[1].closed, true,
    "a late onDone from the abandoned stream lost track of the live one");
});

test("the abandoned question says it was stopped rather than trailing off", () => {
  const rec = recorder();
  const { chat, transcript } = mount("P1", rec);
  chat.ask("which assets are most at risk?");
  chat.ask("what changed since yesterday?");

  const logs = transcript.children.filter((c) => c.className === "log");
  const stopped = logs[0].children.map((line) => line.textContent);
  assert.ok(stopped.includes("Stopped — you asked something else."),
    `the abandoned log ends without saying why: ${JSON.stringify(stopped)}`);
});

test("clicking a starter asks that starter's question, as the reader sees it", () => {
  const rec = recorder();
  const { root } = mount("P1", rec);
  const buttons = root.querySelectorAll(".starter");
  const starters = C.opening("P1", DATA).starters;

  assert.equal(buttons.length, 3, "the starter buttons were never written or never found");
  buttons[1].listeners.click[0]();

  assert.equal(rec.opened.length, 1, "clicking a starter reached no agent");
  assert.equal(rec.opened[0].options.prompt, starters[1],
    "the question that reached the agent is not the one on the button");
});

test("a question reaches the agent the router picked, with the reader's words", () => {
  const R = require("../../apps/workspace/router.js");
  const rec = recorder();
  const { chat } = mount("P1", rec);
  const question = "which assets are most at risk?";

  chat.ask(question);

  assert.equal(rec.opened[0].options.agentId, R.route(question, "P1", DATA).agent_id);
  assert.equal(rec.opened[0].options.prompt, question);
});

test("picking an agent from the panel overrides the router", () => {
  const rec = recorder();
  const { chat } = mount("P1", rec);
  chat.pick("S01");
  assert.equal(rec.opened[0].options.agentId, "S01");
});

test("a finished stream leaves nothing open and says the answer was empty", () => {
  const rec = recorder();
  const { chat, transcript } = mount("P8", rec);
  chat.ask("what happened last shift?");
  rec.opened[0].options.onDone();

  const answers = transcript.children.filter((c) => c.className === "answer");
  assert.equal(answers[0].textContent, "The agent finished without writing an answer.",
    "an agent that wrote nothing leaves the reader with an empty box");

  chat.close();
  assert.equal(rec.opened[0].closed, false,
    "close() re-closed a stream that had already finished");
});

test("one tool call is one line, though it crosses the wire twice", () => {
  const rec = recorder();
  const { chat, transcript } = mount("P1", rec);
  chat.ask("which assets are most at risk?");
  const on = rec.opened[0].options.onStep;
  // A call and its response render to the same sentence: the response frame
  // carries no arguments, so there is nothing more for it to say.
  on({ kind: "step", text: "Reading the sensor readings." });
  on({ kind: "step", text: "Reading the sensor readings." });
  on({ kind: "step", text: "Tracing what else stops if this stops." });
  on({ kind: "step-failed", text: "Couldn't trace what else stops if this stops." });

  const log = transcript.children.filter((c) => c.className === "log")[0];
  assert.deepEqual(log.children.map((p) => p.textContent), [
    "Reading the sensor readings.",
    "Tracing what else stops if this stops.",
    "Couldn't trace what else stops if this stops.",
  ]);
});

test("two calls of the same tool are two lines, not one", () => {
  // operational_math renders the same sentence whatever it is given, so the
  // only thing separating one invocation from the next is that the pair
  // arrives twice. A suppressor that swallowed every repeat would report two
  // pieces of work as one — and the measured run made ten calls.
  const rec = recorder();
  const { chat, transcript } = mount("P1", rec);
  chat.ask("which assets are most at risk?");
  const on = rec.opened[0].options.onStep;
  on({ kind: "step", text: "Working out the numbers." });   // first call
  on({ kind: "step", text: "Working out the numbers." });   // its response
  on({ kind: "step", text: "Working out the numbers." });   // second call
  on({ kind: "step", text: "Working out the numbers." });   // its response

  const log = transcript.children.filter((c) => c.className === "log")[0];
  assert.deepEqual(log.children.map((p) => p.textContent), [
    "Working out the numbers.",
    "Working out the numbers.",
  ]);
});

test("a stream that broke is not also reported as having finished", () => {
  // agent-stream reports the error and then closes, so onDone always follows
  // onError. Both messages on screen at once contradict each other.
  const rec = recorder();
  const { chat, transcript } = mount("P1", rec);
  chat.ask("which assets are most at risk?");
  rec.opened[0].options.onError("The connection to the agent dropped.");
  rec.opened[0].options.onDone();

  const answer = transcript.children.filter((c) => c.className === "answer")[0];
  assert.equal(answer.textContent, "",
    "the page says the agent finished next to the error saying it did not");
  assert.equal(transcript.children.filter((c) => c.className === "error").length, 1);
});

test("a failed step is marked as failed, and answer text is not logged as a step", () => {
  const rec = recorder();
  const { chat, transcript } = mount("P1", rec);
  chat.ask("which assets are most at risk?");
  const on = rec.opened[0].options.onStep;
  on({ kind: "step", text: "Reading the sensor readings." });
  on({ kind: "step-failed", text: "Couldn't trace what else stops if this stops." });
  on({ kind: "text", text: "Three assets are at risk." });

  const log = transcript.children.filter((c) => c.className === "log")[0];
  assert.equal(log.children.length, 2, "answer text was appended to the activity log");
  assert.ok(log.children[1].className.includes("failed"));

  const answer = transcript.children.filter((c) => c.className === "answer")[0];
  assert.equal(answer.textContent, "Three assets are at risk.");
});

/* ---------- the answer pane ---------- */

const LIVE = fs.readFileSync(
  path.join(__dirname, "fixtures", "s01-live-answer.txt"),
  "utf8"
);

function answerAfter(frames) {
  const rec = recorder();
  const { chat, transcript } = mount("P1", rec);
  chat.ask("which assets are most at risk?");
  frames.forEach((text) => rec.opened[0].options.onStep({ kind: "text", text }));
  return transcript.children.filter((c) => c.className === "answer")[0];
}

test("the answer pane renders what the agent wrote instead of printing its punctuation", () => {
  const answer = answerAfter([LIVE]);
  assert.ok(answer.innerHTML.includes("<h3>"), "a heading printed as hashes");
  assert.ok(answer.innerHTML.includes("<strong>"), "bold printed as asterisks");
  assert.ok(answer.innerHTML.includes("<li>"), "a list printed as dashes");
  assert.ok(!answer.textContent.includes("###"), answer.textContent.slice(0, 200));
});

test("the machine vocabulary a live agent emitted does not reach the body copy", () => {
  const answer = answerAfter([LIVE]);
  // Only the body. The drawer is where every one of these is allowed to be.
  const body = answer.innerHTML.split("<details")[0];
  assert.ok(body.includes("<p>"), "there is no body copy for this test to check");
  for (const token of ["INVALID_ARGUMENT", "QUERY_FAILED", "SQL_INTERPOLATION",
    "Job ID", "bigquery.googleapis.com", "ML.PREDICT", "@parameter",
    "rows_scanned", "default_api:"]) {
    assert.ok(!body.includes(token), `the reader still meets ${token}`);
  }
});

test("the raw failure text is filed in the technical drawer, not deleted", () => {
  const answer = answerAfter([LIVE]);
  assert.ok(answer.innerHTML.includes('<details class="tbl drawer">'),
    "the removed text has nowhere a reader can reach it");
  const drawer = answer.innerHTML.slice(answer.innerHTML.indexOf("<details"));
  for (const token of ["INVALID_ARGUMENT", "QUERY_FAILED", "Job ID"]) {
    assert.ok(drawer.includes(token), `${token} was discarded rather than filed`);
  }
});

test("a script tag streamed by an agent never reaches the pane as markup", () => {
  const answer = answerAfter(["Risk: <script>alert(1)</script>"]);
  assert.ok(!/<script/i.test(answer.innerHTML), answer.innerHTML);
  assert.ok(answer.innerHTML.includes("&lt;script&gt;"), answer.innerHTML);
});

test("the pane re-renders the whole answer, so a token split across frames survives", () => {
  // Text arrives in frames the model chose, not in ones this renderer would
  // like. Appending rendered fragments would leave "**bo" on the page forever.
  const answer = answerAfter(["The reading is **bo", "ld** now."]);
  assert.ok(answer.innerHTML.includes("<strong>bold</strong>"), answer.innerHTML);
  assert.ok(!answer.textContent.includes("**"), answer.textContent);
});

test("an answer with nothing to hide carries no drawer", () => {
  const answer = answerAfter(["### Findings\n\nAll five machines are inside their limits."]);
  assert.ok(answer.innerHTML.includes("<h3>Findings</h3>"), answer.innerHTML);
  assert.ok(!answer.innerHTML.includes("<details"),
    "an empty drawer is a control that opens on nothing");
});

/* Asides: what a swarm's delegates wrote, kept but demoted.
 *
 * These test the pane, not the classifier — agent-stream.test.js owns the
 * question of which author is a delegate. What matters here is that a step
 * arriving as kind:"aside" lands below the answer, attributed, and folded.
 */
function paneAfter(steps) {
  const rec = recorder();
  const { chat, transcript } = mount("P1", rec);
  chat.ask("which assets are most at risk?");
  steps.forEach((step) => rec.opened[0].options.onStep(step));
  return transcript.children.filter((c) => c.className === "answer")[0];
}

test("a delegate's prose lands below the answer, not inside it", () => {
  const pane = paneAfter([
    { kind: "aside", author: "s07_sp2", text: "PUMP-104A peaked at 17.11 Hz." },
    { kind: "text", text: "Widen the gap to 115 mm." },
  ]);
  const body = pane.innerHTML.split("<details")[0];
  assert.ok(body.includes("Widen the gap"), body);
  assert.ok(!body.includes("17.11"),
    "a specialist's working note was rendered as the answer");
  assert.ok(pane.innerHTML.includes("17.11"),
    "the working note was deleted rather than filed");
});

test("an aside is attributed by display name, never by ADK node name", () => {
  const pane = paneAfter([
    { kind: "aside", author: "s07_critic", text: "SP2 is out of scope." },
    { kind: "text", text: "Widen the gap." },
  ]);
  assert.ok(pane.innerHTML.includes("Setpoint Safety Critic (critic)"),
    pane.innerHTML);
  assert.ok(!pane.innerHTML.includes("s07_critic"),
    "the reader was shown an ADK node name");
});

test("one heading per delegate, however many frames it wrote in", () => {
  // Prose arrives in as many frames as the model chose. A heading per frame
  // would read as five agents saying one sentence each.
  const pane = paneAfter([
    { kind: "aside", author: "s07_sp1", text: "The 115 mm setting ran " },
    { kind: "aside", author: "s07_sp1", text: "23 days." },
    { kind: "text", text: "Widen the gap." },
  ]);
  const headings = pane.innerHTML.split("Crusher Setting Analyst").length - 1;
  assert.equal(headings, 1, pane.innerHTML);
  assert.ok(pane.innerHTML.includes("The 115 mm setting ran 23 days."),
    "a delegate's sentence was split across two headings");
});

test("an answer with no delegates carries no aside drawer", () => {
  const pane = paneAfter([{ kind: "text", text: "All five machines are inside their limits." }]);
  assert.ok(!pane.innerHTML.includes("what each agent reported"),
    "an empty drawer is a control that opens on nothing");
});

test("the delegates' drawer is not called Technical detail", () => {
  // Browser verification of the live P6 run caught this. `technicalDrawer`
  // hardcodes the summary "Technical detail", so routing the asides through it
  // produced two consequences, both bad. The reader has been taught across
  // every screen that "Technical detail" means agent ids, tables and model
  // tiers — plumbing they may safely ignore. The specialists' and critic's
  // reasoning is the opposite of that: it is the substance of the swarm, and
  // the whole reason this workstream exists is to show the reader how the
  // problem was worked rather than what was queried. Filing it under the
  // ignore-me noun buries the thing it was surfaced to reveal.
  //
  // And when a run produces both drawers — a failed step plus delegates, which
  // is the common case, not the corner — the answer ends with two collapsibles
  // whose summaries read identically, so the only way to tell them apart is to
  // open both.
  const pane = paneAfter([
    { kind: "aside", author: "s07_critic", text: "SP2 is out of scope." },
    { kind: "text", text: "Widen the gap." },
  ]);
  const summaries = (pane.innerHTML.match(/<summary>/g) || []).length;
  const technical = pane.innerHTML.split("Technical detail").length - 1;
  assert.equal(summaries, 1, "expected exactly one drawer here");
  assert.equal(technical, 0,
    "the delegates' reasoning was filed under the drawer readers are taught to skip");
});

/* A delegate's failed step.
 *
 * plainAnswer cuts a failure passage out of prose and hands the raw text back
 * as `.technical` so the pane can file it; the aside drawer ran that cut and
 * threw the result away. A specialist whose lookup failed therefore left the
 * reader a sentence saying a lookup failed and nowhere at all to find out
 * which one — the same material that is carefully preserved when the agent
 * that was asked is the one whose step broke.
 */
test("a delegate's failed step is filed rather than dropped", () => {
  const pane = paneAfter([
    {
      kind: "aside", author: "s07_sp1",
      text: "I checked the setting.\n\nThe call to `bq_query` failed.\n" +
        "- **Error Code:** `INVALID_ARGUMENT` on job 4f9c-11ee.",
    },
    { kind: "text", text: "Widen the gap." },
  ]);
  const parts = pane.innerHTML.split("How the agents got here");
  assert.equal(parts.length, 2, "the delegates' drawer is missing");
  assert.ok(parts[0].includes("INVALID_ARGUMENT") && parts[0].includes("4f9c-11ee"),
    "the delegate's raw failure text was dropped rather than filed");
  assert.ok(parts[0].includes("Technical detail"),
    "it was filed somewhere other than the drawer for plumbing");
  assert.ok(!parts[1].includes("INVALID_ARGUMENT"),
    "an error code was left in the reader-facing prose");
  assert.ok(parts[1].includes("that lookup failed"),
    "the delegate's prose no longer admits the step failed");
});

test("a filed passage says which agent's step it was", () => {
  const pane = paneAfter([
    {
      kind: "aside", author: "s07_sp1",
      text: "The call to `bq_query` failed.\n- **Error Code:** `INVALID_ARGUMENT`.",
    },
    { kind: "text", text: "Widen the gap.\n\nThe call to `bqml_predict` failed." },
  ]);
  const plumbing = pane.innerHTML
    .slice(pane.innerHTML.indexOf("Technical detail"))
    .split("How the agents got here")[0];
  // Two agents' steps failed. Stacked unlabelled they read as one agent's run,
  // so both passages are named — the asked agent's included.
  const labels = (plumbing.match(/<p class="dim">([^<]*)<\/p>/g) || [])
    .map((p) => p.replace(/<[^>]*>/g, "").replace(/&amp;/g, "&"));
  assert.equal(labels.length, 2, `expected a name over each passage: ${plumbing}`);
  assert.equal(labels[1], "Crusher Setting Analyst (specialist)", plumbing);
  // The asked agent is named the way the pick line above the answer names it,
  // rather than by an id the reader has no way to interpret.
  const asked = require("../../apps/workspace/router.js")
    .route("which assets are most at risk?", "P1", DATA).agent_id;
  const name = DATA.catalog.agents.find((a) => a.agent_id === asked).display_name;
  assert.equal(labels[0], name, plumbing);
});

test("filing a delegate's failure adds no third drawer to open", () => {
  const pane = paneAfter([
    {
      kind: "aside", author: "s07_critic",
      text: "The call to `bq_query` failed.\n- **Error Code:** `INVALID_ARGUMENT`.",
    },
    { kind: "text", text: "Widen the gap.\n\nThe call to `bqml_predict` failed." },
  ]);
  assert.equal((pane.innerHTML.match(/<summary>/g) || []).length, 2, pane.innerHTML);
  // A drawer inside a drawer is a control the reader has to open twice to
  // reach one passage.
  const bodies = pane.innerHTML.split('<div class="drawer-body">').slice(1);
  for (const body of bodies) {
    assert.ok(!body.split("</details>")[0].includes("<details"),
      "a drawer was nested inside another drawer");
  }
});

test("a failed step and a delegate produce two drawers a reader can tell apart", () => {
  // The two drawers answer different questions — "which step broke" versus
  // "what did each agent conclude" — so their summaries must differ. Before
  // this, both rendered the string "Technical detail" and the reader had to
  // open each one to find out which was which.
  const pane = paneAfter([
    { kind: "aside", author: "s07_critic", text: "SP2 is out of scope." },
    { kind: "text", text: "Widen the gap.\n\nThe call to `bq_query` failed." },
  ]);
  // Assert on the TITLE — the text before the dim hint — not on the whole
  // summary. Comparing whole summaries passes while the defect is present,
  // because the two hints differ; the reader still meets two controls both
  // announcing themselves as "Technical detail".
  const titles = (pane.innerHTML.match(/<summary>[\s\S]*?<\/summary>/g) || [])
    .map((s) => s.replace(/<summary>/, "").replace(/<span[\s\S]*/, ""));
  assert.equal(titles.length, 2, pane.innerHTML);
  assert.notEqual(titles[0], titles[1],
    "two drawers on one answer announced themselves with the same title");
});
