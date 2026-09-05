const test = require("node:test");
const assert = require("node:assert");

const S = require("../../apps/workspace/agent-stream.js");

test("a text part becomes answer text, not a step", () => {
  const steps = S.eventToSteps({ content: { parts: [{ text: "Hello." }] } });
  assert.deepEqual(steps, [{ kind: "text", text: "Hello." }]);
});

/* The swarm authorship rules.
 *
 * A Pattern A swarm streams five authors over one connection: three
 * specialists, a critic, then the coordinator. Measured on S07 against the
 * governing P6 question, they wrote 4,898 / 7,195 / 5,982 / 3,421 characters
 * of prose before the coordinator wrote a word. Rendered without regard to
 * author, all of it lands in the answer pane as one document, in finish order
 * — so the reader meets two specialists improvising off tables the critic then
 * rejects as out of scope, and meets them BEFORE the answer.
 *
 * The swarm's own design says which one is the answer: the coordinator
 * concludes last, after the critic has audited the rest. Everything before it
 * is working material.
 */
test("only the agent that was asked writes the answer", () => {
  const steps = S.eventToSteps(
    { author: "s07", content: { parts: [{ text: "Here is the answer." }] } },
    {},
    { agentId: "S07" }
  );
  assert.deepEqual(steps, [{ kind: "text", text: "Here is the answer." }]);
});

test("a delegate's prose becomes an aside attributed to it, not answer text", () => {
  // Not dropped. The critic's audit is the most load-bearing prose in the run —
  // it is what caught SP2 querying a table outside its scope — and deleting it
  // would leave the reader unable to see why a specialist's numbers vanished.
  // It is demoted from the answer, and named, so the reader knows whose voice
  // they are reading.
  const steps = S.eventToSteps(
    { author: "s07_critic", content: { parts: [{ text: "SP2 is out of scope." }] } },
    {},
    { agentId: "S07" }
  );
  assert.deepEqual(steps, [
    { kind: "aside", author: "s07_critic", text: "SP2 is out of scope." },
  ]);
});

test("author matching survives the id-to-node-name transform", () => {
  // ADK names every node `agent_id.lower().replace("-", "_")`. A swarm's
  // coordinator carries the swarm's own id, so S07's coordinator is "s07" —
  // but a hyphenated id would arrive underscored, and comparing the raw id
  // would classify the answer itself as a delegate.
  const steps = S.eventToSteps(
    { author: "d07_a", content: { parts: [{ text: "Answer." }] } },
    {},
    { agentId: "D07-A" }
  );
  assert.equal(steps[0].kind, "text");
});

test("without an agentId nothing is demoted", () => {
  // The rule needs to know who was asked. Absent that, treating the first
  // author as a delegate would silently blank the answer — so the safe
  // default is the old behaviour: all text is answer text.
  const steps = S.eventToSteps(
    { author: "s07_sp1", content: { parts: [{ text: "Working." }] } },
    {}
  );
  assert.deepEqual(steps, [{ kind: "text", text: "Working." }]);
});

test("a delegate's tool calls stay in the activity log as ordinary steps", () => {
  // The demotion is about prose. A specialist reading the sensor readings is
  // the swarm visibly working, and that is exactly what the activity log is
  // for — hiding it would make the parallel phase look like a hang.
  const steps = S.eventToSteps(
    { author: "s07_sp1", content: { parts: [{ functionCall: { id: "1",
      name: "bq_query", args: { sql: "SELECT 1 FROM `mining_data.assets`" } } }] } },
    {},
    { agentId: "S07" }
  );
  assert.deepEqual(steps, [{ kind: "step", text: "Reading the machine register" }]);
});

test("a function call becomes one named step", () => {
  const steps = S.eventToSteps({
    content: { parts: [{ functionCall: { id: "1", name: "bq_query",
      args: { sql: "SELECT * FROM `mining_data.telemetry_stream` LIMIT 10" } } }] },
  });
  assert.deepEqual(steps, [{ kind: "step", text: "Reading the sensor readings" }]);
});

test("a response with no matching call degrades gracefully to the tool's doing line", () => {
  // When a functionResponse arrives whose functionCall was never seen (e.g. the
  // stream started mid-conversation), the calls map is empty and recalled is {}.
  // callLine falls through to TOOL_DOING, which is the most honest fallback: the
  // reader still sees what the agent was doing, even without the specific noun.
  const steps = S.eventToSteps({
    content: { parts: [{ functionResponse: { id: "1", name: "bq_query",
      response: { success: true, data: [] } } }] },
  });
  assert.equal(steps.length, 1);
  assert.equal(steps[0].kind, "step");
  assert.equal(steps[0].text, "Looking up records");
});

test("a failed response is named, not hidden", () => {
  // success is nested under response. At the top level it would read as
  // undefined, which is not false, and the failure would never be reported.
  const steps = S.eventToSteps({
    content: { parts: [{ functionResponse: { id: "9", name: "graph_traverse",
      response: { success: false } } }] },
  });
  assert.equal(steps.length, 1);
  assert.equal(steps[0].kind, "step-failed");
  assert.match(steps[0].text, /Couldn't/);
});

test("a failure names what failed, recalled from the matching call", () => {
  // A functionResponse carries only {id, name, response} — no arguments. The
  // noun has to come from the functionCall that shares its id, or every failure
  // degrades to the tool's verb and the reader learns nothing.
  const calls = {};
  S.eventToSteps({
    content: { parts: [{ functionCall: { id: "7", name: "graph_traverse",
      args: { traversal: "blast_radius" } } }] },
  }, calls);
  const steps = S.eventToSteps({
    content: { parts: [{ functionResponse: { id: "7", name: "graph_traverse",
      response: { success: false } } }] },
  }, calls);
  assert.equal(
    steps[0].text,
    "Couldn't trace what else stops if this stops — that lookup failed."
  );
});

test("a successful response repeats the call's own line, not a generic one", () => {
  const calls = {};
  S.eventToSteps({
    content: { parts: [{ functionCall: { id: "3", name: "bq_query",
      args: { sql: "SELECT 1 FROM `mining_data.assets`" } } }] },
  }, calls);
  const steps = S.eventToSteps({
    content: { parts: [{ functionResponse: { id: "3", name: "bq_query",
      response: { success: true, data: [] } } }] },
  }, calls);
  assert.equal(steps[0].text, "Reading the machine register");
});

test("a not-instrumented driver reads as a declared gap, not a failure", () => {
  // run_diagnostic returns success: true with data.status ==
  // "not_instrumented" for a driver the pack declares but has no diagnostic
  // behind it. Before the fix this was success: false, and it rendered as
  // "step-failed" / "that lookup failed" — the exact defect this test guards
  // against regressing. A wrong fix that left this branch alone (e.g. only
  // changing the Python side) would still fail this test, because the JS
  // would keep treating success: true as an ordinary call and never mention
  // the gap at all.
  const calls = {};
  S.eventToSteps({
    content: { parts: [{ functionCall: { id: "5", name: "run_diagnostic",
      args: { driver_id: "reagent_regime" } } }] },
  }, calls);
  const steps = S.eventToSteps({
    content: { parts: [{ functionResponse: { id: "5", name: "run_diagnostic",
      response: {
        success: true,
        data: { driver: "reagent_regime", status: "not_instrumented", rows: [] },
      } } }] },
  }, calls);
  assert.equal(steps.length, 1);
  // Not a failure step: the call succeeded.
  assert.equal(steps[0].kind, "step");
  assert.match(steps[0].text, /declared in the tree, not instrumented/);
  assert.doesNotMatch(steps[0].text, /failed/);
});

test("an instrumented driver's success is unaffected by the gap check", () => {
  // The gap branch keys on data.status === "not_instrumented" specifically,
  // so an ordinary instrumented result — which carries status: "instrumented"
  // — must still render as the plain call line, not the gap line.
  const calls = {};
  S.eventToSteps({
    content: { parts: [{ functionCall: { id: "6", name: "run_diagnostic",
      args: { driver_id: "liberation" } } }] },
  }, calls);
  const steps = S.eventToSteps({
    content: { parts: [{ functionResponse: { id: "6", name: "run_diagnostic",
      response: {
        success: true,
        data: { driver: "liberation", status: "instrumented", rows: [{ band: "tight" }] },
      } } }] },
  }, calls);
  assert.equal(steps[0].kind, "step");
  assert.equal(steps[0].text, "Checking whether the crusher setting is costing recovery");
});

test("a thoughtSignature is not a step", () => {
  const steps = S.eventToSteps({
    content: { parts: [{ thoughtSignature: "abc" }, { text: "Right." }] },
  });
  assert.deepEqual(steps, [{ kind: "text", text: "Right." }]);
});

test("an event with no content yields nothing rather than throwing", () => {
  assert.deepEqual(S.eventToSteps({}), []);
  assert.deepEqual(S.eventToSteps({ content: {} }), []);
  assert.deepEqual(S.eventToSteps(null), []);
});

test("the model's own prose is passed through unaltered", () => {
  const leak = "The tool call `graph_traverse` failed with `success=false`";
  const steps = S.eventToSteps({ content: { parts: [{ text: leak }] } });
  assert.equal(steps[0].text, leak);
});

test("the stream url carries the prompt and the session as query parameters", () => {
  const url = S.streamUrl({
    agentId: "S01", prompt: "what now?", userId: "u", sessionId: "s",
  });
  assert.ok(url.startsWith("/api/stream/S01?"));
  assert.ok(url.includes("prompt=what+now%3F") || url.includes("prompt=what%20now%3F"));
  assert.ok(url.includes("user_id=u"));
  assert.ok(url.includes("session_id=s"));
});

/* Minimal fake EventSource — just enough to exercise the lifecycle.
 * close() records that it was called; _emit() drives the registered handlers;
 * onerror is the slot the module assigns directly. Assertions stay on
 * observable effects: was the source closed, did the callbacks fire. */
class FakeEventSource {
  constructor() {
    this._listeners = {};
    this._closed = false;
    this.onerror = null;
  }
  addEventListener(type, fn) {
    if (!this._listeners[type]) this._listeners[type] = [];
    this._listeners[type].push(fn);
  }
  close() { this._closed = true; }
  _emit(type, data) {
    const msg = { data: typeof data === "string" ? data : JSON.stringify(data) };
    (this._listeners[type] || []).forEach(function (fn) { fn(msg); });
  }
}

test("proxy-done closes the source and fires onDone exactly once", () => {
  const src = new FakeEventSource();
  let doneCount = 0;
  S._streamAgentWithSource(src, { onDone: () => { doneCount++; } });

  src._emit("proxy-done", "");
  assert.equal(src._closed, true, "source should be closed after proxy-done");
  assert.equal(doneCount, 1, "onDone should fire exactly once");

  // A second proxy-done must be a no-op — finished flag guards re-entry.
  src._closed = false; // reset sentinel to detect any spurious second close
  src._emit("proxy-done", "");
  assert.equal(src._closed, false, "second proxy-done should not re-close");
  assert.equal(doneCount, 1, "onDone should still have fired exactly once");
});

test("onerror before any event closes the source and fires onError", () => {
  const src = new FakeEventSource();
  let errorMsg = null;
  S._streamAgentWithSource(src, { onError: (msg) => { errorMsg = msg; } });

  src.onerror();
  assert.equal(src._closed, true, "source should be closed after onerror");
  assert.ok(errorMsg && errorMsg.length > 0, "onError should receive a message");
});

test("proxy-error then proxy-done fires onDone exactly once; proxy-error alone does not close", () => {
  // proxy-error must not close the source — proxy-done is guaranteed to follow
  // and the error detail would otherwise be the last thing the user sees.
  const src = new FakeEventSource();
  let errorMsg = null;
  let doneCount = 0;
  S._streamAgentWithSource(src, {
    onError: (msg) => { errorMsg = msg; },
    onDone: () => { doneCount++; },
  });

  src._emit("proxy-error", JSON.stringify({ detail: "quota exceeded" }));
  assert.equal(src._closed, false, "proxy-error alone must not close the source");
  assert.equal(errorMsg, "quota exceeded", "onError should receive the detail text");
  assert.equal(doneCount, 0, "onDone must not fire from proxy-error");

  src._emit("proxy-done", "");
  assert.equal(src._closed, true, "source should be closed after proxy-done");
  assert.equal(doneCount, 1, "onDone should fire exactly once after proxy-done");
});
