/* Whether the deployed agents can be reached, and how to say so.
 *
 * This is Application 2's question. The case screens make an argument about a
 * gap and have nothing to ask a Cloud Run service about, so they do not load
 * this file; it lived in apps/shared/shell.js, which both applications load,
 * and every case screen was carrying the workspace's backend logic to get the
 * chrome. Shared between the four workspace screens, not shared with the case.
 *
 * apps/shared/shell.js loads first and stays first: DATA and esc() come from it.
 */

/* One /api/runtime call per page, shared by every block that needs the answer.
 *
 * Screens used to render DATA.workspace.runtime — a constant baked into
 * bundle.js when it was generated — so five call sites printed NOT CONNECTED in
 * production while the service was connected to all 52 agents. Being wrong in
 * the pessimistic direction is still being wrong, and it is the more expensive
 * kind here: it says the thing does not work.
 *
 * One file rather than one per screen because the role page had a second copy of
 * the same fetch, guarded differently — one read a 500 with a JSON body as a
 * not-connected runtime, the other as an unreadable reply — and two answers to
 * one question is how two screens in one application come to disagree.
 *
 * Four outcomes, kept apart because they are four different problems. The
 * server answered yes; the server answered no and said why; the server answered
 * with something that is not an answer, so the state is unknown and must not be
 * rendered as either extreme; or there was no server to ask, which is the only
 * case where the baked constant is the true answer.
 */
let _runtimePromise = null;

function runtimeState() {
  if (!_runtimePromise) {
    _runtimePromise = fetch("/api/runtime")
      .then((reply) =>
        reply
          .json()
          .then((body) => {
            // A FastAPI 500 answers {"detail": "Internal Server Error"} — valid
            // JSON, with no `connected` field — and a connected reply with no
            // deployed list cannot support the count every screen prints from
            // it. Neither is a not-connected runtime, and reporting them as one
            // sends a reader looking for a fault in the estate that is really a
            // fault in the endpoint.
            const answered =
              typeof body.connected === "boolean" &&
              (!body.connected || Array.isArray(body.deployed));
            if (!answered) throw new Error("the reply carried no usable answer");
            return body;
          })
          .catch((err) => ({
            connected: false,
            unreadable: true,
            stage: `/api/runtime answered HTTP ${reply.status}`,
            detail: err.message,
          }))
      )
      // The one case where the baked constant is the true answer: no API to
      // ask, because the page is open off disk or behind a static file server.
      .catch(() => ({ ...DATA.workspace.runtime, connected: false, offline: true }));
  }
  return _runtimePromise;
}

/* What the server said, escaped before it becomes markup.
 *
 * In a browser this is shell.js's esc(), already on the page. Required from
 * Node — where this file is on its own — it is fetched from the same place
 * rather than kept here as a second copy free to drift from the first. */
const escapeForRuntime =
  typeof esc === "function" ? esc : require("./shell.js").esc;

/** The three answers in words, written once for every screen that shows one.
 *
 *  The reader here is a supervisor, not an engineer. The stage the check
 *  stopped at and the exception it caught are the two things they can do
 *  nothing with and an administrator cannot do without, so they come back
 *  separately, as drawer markup, rather than as the body copy. A page whose
 *  loudest sentence is `RefreshError: Reauthentication is needed…` has told its
 *  reader nothing they can act on.
 */
function connectionCopy(state) {
  const rows = (pairs) => {
    const kept = pairs.filter((pair) => pair[1]);
    if (!kept.length) return "";
    return (
      "<dl>" +
      kept
        .map(
          ([term, value]) =>
            `<dt>${escapeForRuntime(term)}</dt>` +
            `<dd class="mono">${escapeForRuntime(value)}</dd>`
        )
        .join("") +
      "</dl>"
    );
  };

  if (state.connected) {
    return {
      key: "ready",
      cls: "b-ok",
      badge: "✓ READY",
      // Scoped to the load, like every other state here: this is one fetch, and
      // it is never revalidated, so the present tense would be a claim about a
      // moment the page has no way of standing behind.
      //
      // The second sentence is about what this build does, not about what is
      // currently on the screen. "Nothing here was written by an agent" is
      // false the moment a reader uses the handover sheet's Run button, and
      // this block is drawn once and never drawn again.
      lines: [
        `${state.deployed.length} of ${state.expected} agents were deployed and ` +
          "reachable when this page loaded.",
        "Nothing on this page is written on an agent's behalf. Where one has not " +
          "been asked, the space is left empty rather than filled in for it.",
      ],
      detail: "",
    };
  }

  if (state.unreadable) {
    return {
      key: "unknown",
      cls: "b-idle",
      badge: "○ CONNECTION UNKNOWN",
      lines: [
        "The workspace server answered the connection check with something this " +
          "page could not read, so whether the deployed agents can be reached is " +
          "not known. This is neither a yes nor a no.",
        "Nothing on this page is written on an agent's behalf either way. The " +
          "check itself is worth reporting to whoever administers this workspace.",
      ],
      detail: rows([
        ["What was asked", "/api/runtime"],
        ["What came back", state.stage],
        ["Why it could not be read", state.detail],
      ]),
    };
  }

  if (state.offline) {
    return {
      key: "not-connected",
      cls: "b-warn",
      badge: "⚠ NOT CONNECTED",
      lines: [
        "These screens are open without the workspace server, so nothing on this " +
          "page has asked the deployed agents anything.",
        state.reason,
        state.consequence,
      ].filter(Boolean),
      detail: "",
    };
  }

  return {
    key: "not-connected",
    cls: "b-warn",
    badge: "⚠ NOT CONNECTED",
    lines: [
      "This workspace could not reach the deployed agents when the page loaded, " +
        "so nothing here has been written by one.",
      "Everything else on the screen — the tables, the method and the counts — " +
        "is read from the deployed catalog and is unaffected. Restoring the " +
        "connection is a job for whoever administers this workspace.",
    ],
    detail: rows([
      ["Where the check stopped", state.stage],
      ["What it reported", state.detail],
    ]),
  };
}

/* The pure half only, as in apps/shared/shell.js. runtimeState() is a fetch and
 * a promise cached across a page's lifetime; exporting it would invite a test to
 * call it and get whichever answer a previous test had already cached. */
if (typeof module !== "undefined") {
  module.exports = { connectionCopy };
}
