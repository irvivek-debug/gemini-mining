/* One agent's event stream, turned into lines a reader can follow.
 *
 * A real question was measured at 103.8 seconds across 26 events. The point of
 * this module is that those 103 seconds read as work happening — reading the
 * sensor readings, tracing what else stops — rather than as a spinner that
 * cannot be told from a hang.
 *
 * The agent's own prose is never edited. The agents currently leak plumbing
 * into their answers, and filtering that here would put this file in the
 * business of deciding what the agent said. The honest fix is upstream.
 */
var PLAIN = typeof require !== "undefined" ? require("../shared/plain.js") : window;

/* The four part shapes, as measured on the wire.
 *
 * Two details here are worth more than they look. First, success is nested under
 * response — read at the top level it is undefined, which is not false, and a
 * failed lookup would then never be reported at all. Second, a functionResponse
 * carries only {id, name, response}: it has no arguments, so the noun the call
 * was about has to be remembered from the matching functionCall by id. Without
 * that, every failure reads "Couldn't finish tracing connections" instead of
 * naming what could not be traced, which is the whole point of the line.
 *
 * `calls` is that memory. It belongs to one conversation and is passed in, so
 * this function stays pure with respect to module state and a test can hand it
 * a fresh one.
 */
/* The node name ADK gives an agent, derived from its catalog id.
 *
 * `_llm` in both patterns builds every node as
 * `agent.agent_id.lower().replace("-", "_")`, and that name is what arrives on
 * the wire as `author`. Comparing the raw id would miss on any hyphenated one.
 */
function nodeName(agentId) {
  return String(agentId || "").toLowerCase().replace(/-/g, "_");
}

/* Whether this event came from someone the asked-for agent delegated to.
 *
 * Unknown counts as no. The rule needs to know who was asked; without that,
 * guessing would blank the answer pane, which is a far worse failure than
 * showing a delegate's prose.
 */
function isDelegate(adkEvent, options) {
  var asked = options && options.agentId;
  if (!asked) return false;
  var author = adkEvent && adkEvent.author;
  if (!author) return false;
  return author !== nodeName(asked);
}

/* Text is attributed; steps are not.
 *
 * A Pattern A swarm streams five authors down one connection — three
 * specialists, the critic, then the coordinator. Measured on S07 against the
 * governing P6 question, the four delegates wrote 21,496 characters of prose
 * before the coordinator wrote its first. Rendered without regard to author,
 * all of it lands in the answer pane as a single document in finish order, so
 * the reader meets two specialists improvising off a table the critic then
 * rejects as out of scope — and meets them before the answer.
 *
 * The swarm's own design settles which one is the answer: the coordinator
 * concludes last, after the critic has audited the rest. So prose from anyone
 * else is demoted to an aside and attributed, never deleted — the critic's
 * audit is the only place the reader can learn why a specialist's numbers are
 * absent from the conclusion.
 *
 * Tool calls are left alone deliberately. A specialist reading the sensor
 * readings is the swarm visibly working, which is what the activity log exists
 * to show; suppressing it would make the whole parallel phase look like a hang.
 */
function eventToSteps(adkEvent, calls, options) {
  var parts = (adkEvent && adkEvent.content && adkEvent.content.parts) || [];
  var seen = calls || {};
  var steps = [];
  var delegate = isDelegate(adkEvent, options);
  parts.forEach(function (part) {
    if (!part) return;
    if (typeof part.text === "string" && part.text.length) {
      steps.push(
        delegate
          ? { kind: "aside", author: adkEvent.author, text: part.text }
          : { kind: "text", text: part.text }
      );
      return;
    }
    if (part.functionCall) {
      var args = part.functionCall.args || {};
      if (part.functionCall.id) seen[part.functionCall.id] = args;
      steps.push({ kind: "step", text: PLAIN.callLine(part.functionCall.name, args) });
      return;
    }
    if (part.functionResponse) {
      var reply = part.functionResponse.response || {};
      var recalled = seen[part.functionResponse.id] || {};
      var failed = reply.success === false;
      // run_diagnostic succeeds (success: true) on a driver with no
      // diagnostic behind it — see mining_agents/tools/run_diagnostic.py.
      // That is a declared gap, not a failure, and it must read as neither:
      // not "that lookup failed" (it is success: true) and not silence (the
      // reader learns nothing). reply.data carries status on this one shape;
      // every other tool's success payload has no such field, so this check
      // only ever fires for run_diagnostic's not_instrumented result.
      var gap = !failed && reply.data && reply.data.status === "not_instrumented";
      steps.push({
        kind: failed ? "step-failed" : "step",
        text: failed
          ? PLAIN.failLine(part.functionResponse.name, recalled)
          : gap
          ? PLAIN.gapLine(part.functionResponse.name, recalled)
          : PLAIN.callLine(part.functionResponse.name, recalled),
      });
    }
    // thoughtSignature rides alongside the other three and is not a step.
  });
  return steps;
}

function streamUrl(options) {
  var q = new URLSearchParams({
    prompt: options.prompt || "",
    user_id: options.userId || "workspace",
    session_id: options.sessionId || "workspace-session",
  });
  return "/api/stream/" + encodeURIComponent(options.agentId) + "?" + q.toString();
}

/* EventSource, with the one behaviour that would otherwise bite: it reconnects
 * by itself when the connection closes, so without the server's explicit
 * proxy-done event the browser would silently re-ask the agent the same
 * hundred-second question, forever. */

/* Seam: accepts a pre-built source so tests can inject a fake EventSource
 * without touching the browser global. streamAgent() is the real entry point
 * and constructs the EventSource itself before delegating here. */
function _streamAgentWithSource(source, options) {
  var finished = false;
  // One call memory per stream, so a response can name what its call was about.
  var calls = {};

  function finish() {
    if (finished) return;
    finished = true;
    source.close();
    if (options.onDone) options.onDone();
  }

  source.onmessage = function (message) {
    var parsed;
    try {
      parsed = JSON.parse(message.data);
    } catch (err) {
      return; // A frame this module cannot read is not a frame worth guessing at.
    }
    eventToSteps(parsed, calls, options).forEach(function (step) {
      if (options.onStep) options.onStep(step);
    });
  };

  source.addEventListener("proxy-error", function (message) {
    var detail = message.data;
    try {
      detail = JSON.parse(message.data).detail || message.data;
    } catch (err) { /* the raw text is better than nothing */ }
    if (options.onError) options.onError(detail);
  });

  source.addEventListener("proxy-done", finish);

  source.onerror = function () {
    // Reached when the connection drops before proxy-done — a dropped network
    // or a proxy that died. Reconnecting would re-run the agent, so it stops.
    if (finished) return;
    if (options.onError) options.onError("The connection to the agent dropped.");
    finish();
  };

  return { close: finish };
}

function streamAgent(options) {
  var source = new EventSource(streamUrl(options));
  return _streamAgentWithSource(source, options);
}

if (typeof module !== "undefined") {
  module.exports = { eventToSteps, streamUrl, streamAgent, _streamAgentWithSource };
}
