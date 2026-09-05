/* The handover sheet, loaded the way a browser loads it.
 *
 * Two claims are worth pinning here and neither can be pinned from source text.
 * The first is that no block on the page states anything about the connection
 * before /api/runtime has answered — the bug this replaces printed NOT
 * CONNECTED from a constant baked into bundle.js, and read as a working system
 * reporting itself broken. The second is the stream lifecycle behind the Run
 * button: EventSource reconnects by itself whenever a connection closes, so an
 * abandoned stream re-asks a question measured at a little under two minutes of
 * real model time, over and over, and bills for every repeat.
 *
 * So the page scripts are run in a vm against a document small enough to reason
 * about. It is not a browser and does not pretend to be: it resolves ids, keeps
 * text, and forgets the ids belonging to a node whose innerHTML was replaced —
 * which is exactly the fault that would occur if the run control and the sheet
 * were mounted on the same element.
 *
 * The cockpit rides along in one test because it is the other page that says
 * something about the connection in two places at once.
 */
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.join(__dirname, "..", "..");
const app = (...parts) => path.join(ROOT, "apps", ...parts);

const DATA = (() => {
  const text = fs.readFileSync(app("shared", "data", "bundle.js"), "utf8");
  return JSON.parse(text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1));
})();

const ENTRYPOINTS = DATA.catalog.counts.entrypoints;

/* The document the page is run against lives in tests/js/screen-dom.js, because
 * tests/js/screen-render.js needs the same one: a screen that renders under one
 * harness and not the other proves nothing about the screen. */
const { makeDom } = require("./screen-dom.js");

/* The script tags a page carries, read off the page rather than listed here, so
 * a file added to the markup is a file the harness loads. */
function scriptsOf(pageHtml) {
  return [...pageHtml.matchAll(/<script src="([^"]+)"><\/script>/g)].map((m) =>
    path.join(ROOT, "apps", "workspace", m[1])
  );
}

/** Load a workspace page the way a browser loads it: its own script tags, in
 *  their own order. */
function loadPage(options) {
  const opts = options || {};
  const page = app("workspace", opts.page || "handover.html");
  const pageHtml = fs.readFileSync(page, "utf8");
  const dom = makeDom(pageHtml);

  const fetches = [];
  const sources = [];
  const windowHandlers = {};

  class FakeSource {
    constructor(url) {
      this.url = url;
      this.closed = false;
      this.handlers = {};
      sources.push(this);
    }
    addEventListener(type, fn) {
      (this.handlers[type] = this.handlers[type] || []).push(fn);
    }
    close() {
      this.closed = true;
    }
    emit(type, data) {
      const message = { data: data === undefined ? "" : data };
      if (type === "message" && this.onmessage) this.onmessage(message);
      if (type === "error" && this.onerror) this.onerror(message);
      (this.handlers[type] || []).forEach((fn) => fn(message));
    }
  }

  const sandbox = {
    console,
    URLSearchParams,
    EventSource: FakeSource,
    document: dom.document,
    location: { search: "" },
    addEventListener(type, fn) {
      (windowHandlers[type] = windowHandlers[type] || []).push(fn);
    },
    fetch(url) {
      fetches.push(url);
      if (opts.runtime === "offline") {
        return Promise.reject(new TypeError("Failed to fetch"));
      }
      // Deviation 3: the server is there and answering, but what it answers is
      // not an answer. A FastAPI 500, or a proxy's HTML error page where JSON
      // was expected. Neither is a not-connected estate.
      if (opts.runtime === "unreadable") {
        return Promise.resolve({
          status: 500,
          json: () => Promise.reject(new SyntaxError("Unexpected token < in JSON at position 0")),
        });
      }
      return Promise.resolve({
        status: 200,
        json: () => Promise.resolve(opts.runtime),
      });
    },
  };

  const context = vm.createContext(sandbox);
  vm.runInContext("var window = globalThis;", context);
  for (const file of scriptsOf(pageHtml)) {
    vm.runInContext(fs.readFileSync(file, "utf8"), context, { filename: file });
  }

  return {
    context,
    dom,
    fetches,
    sources,
    fire: (type) => (windowHandlers[type] || []).forEach((fn) => fn({})),
    el: (id) => dom.registry.get(id),
    // Every block that renders where an agent's words would go.
    blocks: () =>
      [...dom.registry.values()].filter((n) => String(n.id).startsWith("nc-")),
    runtimeLine: () =>
      [...dom.registry.values()].filter((n) => String(n.id).startsWith("rt-")),
    /* Everything on the page, in one string.
     *
     * Mount points do not nest — each id in the markup is written to once, and
     * a node created inside another node's innerHTML gets its own entry only
     * when something later writes into it. So the join is the document, and
     * counting a summary in it counts the summaries a reader would see. */
    rendered: () =>
      [...dom.registry.values()].map((n) => n.innerHTML).join("\n"),
  };
}

/* Deployed and expected are deliberately different numbers. When both were
 * ENTRYPOINTS, "52 of 52" passed whether the screen counted the list the wire
 * sent or printed `expected` twice, and printing `expected` twice is a screen
 * that reports a full estate however many services are actually there. */
const DEPLOYED = ENTRYPOINTS - 2;
const CONNECTED = {
  connected: true,
  expected: ENTRYPOINTS,
  deployed: Array.from({ length: DEPLOYED }, (_, i) => `A${i}`),
  missing: ["A50", "A51"],
};

// A microtask drain: runtimeState() resolves through two chained thens.
const settled = () => new Promise((resolve) => setImmediate(resolve));

test("nothing on the page states the connection before the wire answers", () => {
  const page = loadPage({ runtime: CONNECTED });
  const sheet = page.el("brief").innerHTML;
  assert.ok(page.blocks().length >= 3, `only ${page.blocks().length} blocks asked`);
  assert.match(sheet, /CHECKING/);
  assert.doesNotMatch(sheet, /NOT CONNECTED/);
  assert.doesNotMatch(sheet, /READY/);
  // And the sheet is not quietly carrying the build's opinion either.
  assert.ok(!sheet.includes(DATA.workspace.runtime.reason.slice(0, 40)));
});

/* The frame is the first thing read and the last thing checked. A block whose
 * text says one state and whose border says another has told the reader the
 * border's answer, because that is the one they got from across the room. */
test("the block that has not heard back is not framed as a warning", () => {
  const page = loadPage({ runtime: CONNECTED });
  for (const block of page.blocks()) {
    assert.match(block.className, /\bnc-checking\b/);
    assert.doesNotMatch(block.className, /\bnc-not-connected\b/);
  }
});

test("a connected runtime turns every block over to READY, counting from the wire", async () => {
  const page = loadPage({ runtime: CONNECTED });
  await settled();
  const blocks = page.blocks();
  assert.ok(blocks.length >= 3);
  for (const block of blocks) {
    assert.match(block.innerHTML, /READY/);
    assert.doesNotMatch(block.innerHTML, /NOT CONNECTED/);
    // The class moves with the content. Left behind, ✓ READY renders inside
    // the amber dashed absence box — a working system framed as a broken one.
    assert.match(block.className, /\bnc-ready\b/);
    assert.doesNotMatch(block.className, /\bnc-not-connected\b/);
    assert.doesNotMatch(block.className, /\bnc-checking\b/);
    assert.ok(
      block.innerHTML.includes(`${DEPLOYED} of ${ENTRYPOINTS}`),
      `the block did not report the wire's count: ${block.innerHTML}`
    );
  }
  const lines = page.runtimeLine();
  assert.ok(lines.length >= 2, "the sheet lost a runtime line it used to carry");
  for (const line of lines) {
    assert.ok(
      line.textContent.includes(`${DEPLOYED} of ${ENTRYPOINTS}`),
      `a runtime line ignored the wire: ${line.textContent}`
    );
    assert.ok(!line.textContent.includes(DATA.workspace.runtime.reason.slice(0, 40)));
  }
});

test("one page asks /api/runtime once, however many blocks want the answer", async () => {
  const page = loadPage({ runtime: CONNECTED });
  await settled();
  assert.ok(page.blocks().length + page.runtimeLine().length > 1);
  assert.deepEqual(page.fetches, ["/api/runtime"]);
});

/* The cockpit is the other page with more than one thing to say about the
 * connection: a Runtime card at the top and a provenance row at the foot. Two
 * fetches would let one screen print two different answers to one question. */
test("the cockpit asks once too, and its card agrees with its footer", async () => {
  const page = loadPage({ page: "index.html", runtime: CONNECTED });
  await settled();
  assert.deepEqual(page.fetches, ["/api/runtime"]);
  assert.match(page.el("runtime").innerHTML, new RegExp(`${DEPLOYED} / ${ENTRYPOINTS} DEPLOYED`));
  assert.doesNotMatch(page.el("runtime").innerHTML, /NOT CONNECTED/);
  assert.equal(page.runtimeLine().length, 1);
  assert.ok(page.runtimeLine()[0].textContent.includes(`${DEPLOYED} of ${ENTRYPOINTS}`));
});

/* One page, one closed disclosure — however many blocks want to disclose.
 *
 * This sheet has a section per summariser and each one asks whether the agents
 * are reachable, so a connection block that carries its own drawer put three
 * identical "Technical detail" boxes down one page the moment the answer was
 * no. Three identical disclosures is not disclosure, it is repetition, and it
 * is exactly what the "technical detail at the end, collapsed" instruction was
 * asking to be spared. The stage and the exception are facts about the page,
 * so the page holds them once, at the foot, where everything else technical
 * about this screen already lives.
 */
function disclosures(page) {
  return (page.rendered().match(/<summary>Technical detail/g) || []).length;
}

for (const state of ["disconnected", "unknown", "connected"]) {
  test(`the ${state} sheet offers one technical disclosure, not one per block`, async () => {
    const page = loadPage({
      runtime:
        state === "connected"
          ? CONNECTED
          : state === "unknown"
          ? "unreadable"
          : {
              connected: false,
              stage: "cloud run services.list",
              detail: "HTTP 403: caller lacks run.services.list",
              expected: ENTRYPOINTS,
            },
    });
    await settled();
    assert.ok(page.blocks().length >= 3, "the sheet stopped asking in several places");
    assert.equal(
      disclosures(page),
      1,
      `${state}: the sheet renders ${disclosures(page)} technical disclosures`
    );
  });
}

/* The reader of this sheet is a Shift Supervisor. What they need in the body is
 * a sentence they can act on; the stage the check stopped at and the exception
 * it caught are for whoever repairs it, and belong in the one closed drawer at
 * the foot of the page. The version this replaces printed
 * "RefreshError: Reauthentication is needed…" as the loudest text on the page. */
test("a server that says no is explained in words, with the exception in the drawer", async () => {
  const page = loadPage({
    runtime: {
      connected: false,
      stage: "cloud run services.list",
      detail: "HTTP 403: caller lacks run.services.list",
      expected: ENTRYPOINTS,
    },
  });
  await settled();
  for (const block of page.blocks()) {
    assert.match(block.innerHTML, /NOT CONNECTED/);
    assert.match(block.className, /\bnc-not-connected\b/);
    assert.doesNotMatch(block.innerHTML, /READY/);

    const why = [...block.innerHTML.matchAll(/<p class="nc-why">([^<]*)<\/p>/g)].map(
      (m) => m[1]
    );
    assert.ok(why.length >= 2, `the block explained nothing: ${block.innerHTML}`);
    assert.ok(
      why[0].startsWith("This workspace could not reach the deployed agents"),
      `the body copy is not a written sentence: ${why[0]}`
    );
    for (const line of why) {
      assert.ok(
        !line.includes("run.services.list") && !line.includes("HTTP 403"),
        `the server's exception text is the reader-facing copy: ${line}`
      );
    }
    assert.ok(
      !block.innerHTML.includes("cloud run services.list"),
      "the block repeated the stage that the page already files once"
    );
  }

  const drawer = page.rendered().slice(page.rendered().indexOf('class="drawer-body"'));
  assert.ok(drawer.includes("cloud run services.list"), "the stage is not recorded anywhere");
  assert.ok(
    drawer.includes("HTTP 403: caller lacks run.services.list"),
    "the detail an administrator needs was dropped rather than filed"
  );
  assert.match(page.runtimeLine()[0].textContent, /^Not connected/);
});

/* Deviation 3. The server answered, and what it answered is not an answer.
 * Reported as a no it sends a reader looking for a fault in the estate; the
 * fault is in the endpoint, and the honest state is that nothing is known. */
test("an unreadable answer is reported as unknown, not as a no", async () => {
  const page = loadPage({ runtime: "unreadable" });
  await settled();
  for (const block of page.blocks()) {
    assert.match(block.innerHTML, /CONNECTION UNKNOWN/);
    assert.doesNotMatch(block.innerHTML, /NOT CONNECTED/);
    assert.doesNotMatch(block.innerHTML, /READY/);
    assert.match(block.className, /\bnc-unknown\b/);
    assert.doesNotMatch(block.className, /\bnc-not-connected\b/);
    assert.ok(
      block.innerHTML.includes("neither a yes nor a no"),
      `the unknown state was not stated as unknown: ${block.innerHTML}`
    );
  }
  const drawer = page.rendered().slice(page.rendered().indexOf('class="drawer-body"'));
  assert.ok(drawer.includes("HTTP 500"), "the status the server answered with is lost");
  assert.doesNotMatch(page.runtimeLine()[0].textContent, /^Not connected/);
});

/* A connected reply with no deployed list cannot support the count every screen
 * prints from it. The count used to throw on it, which left every block reading
 * CHECKING… for good behind an unhandled rejection. It fails to unknown now,
 * which is the direction a connection check is allowed to fail in. */
test("a connected reply with nothing to count is unknown, not a silent 0 of 52", async () => {
  const page = loadPage({ runtime: { connected: true, expected: ENTRYPOINTS } });
  await settled();
  for (const block of page.blocks()) {
    assert.match(block.innerHTML, /CONNECTION UNKNOWN/);
    assert.doesNotMatch(block.innerHTML, /CHECKING/);
    assert.ok(!block.innerHTML.includes(`0 of ${ENTRYPOINTS}`));
  }
});

test("off disk, with no server to ask, the baked constant is the fallback", async () => {
  const page = loadPage({ runtime: "offline" });
  await settled();
  const first = page.blocks()[0].innerHTML;
  assert.match(first, /NOT CONNECTED/);
  assert.ok(
    first.includes(DATA.workspace.runtime.reason.slice(0, 40)),
    "the off-disk case lost the one explanation it does have"
  );
});

test("the run control and the sheet are mounted on different elements", async () => {
  const page = loadPage({ runtime: CONNECTED });
  assert.ok(page.el("run-brief"), "the Run button is not on the page");
  // The band the run handler rewrites is anchored on its id rather than on its
  // heading, so renaming the heading cannot break this and losing the anchor
  // the handler reaches for cannot pass it.
  assert.match(page.el("brief").innerHTML, /id="omission-head"/);
  assert.ok(!page.el("run").innerHTML.includes('id="omission-head"'));
  assert.ok(page.el("run").innerHTML.includes("Write this brief now"));
});

test("the run button asks the one agent the catalogue permits, once", () => {
  const page = loadPage({ runtime: CONNECTED });
  page.el("run-brief").click();
  assert.equal(page.sources.length, 1);
  assert.ok(
    page.sources[0].url.startsWith("/api/stream/S12?"),
    `the brief was asked of ${page.sources[0].url}`
  );
  for (const internal of ["S12-SP1", "S12-SP2", "S12-SP3", "S12-CRITIC"]) {
    assert.ok(!page.sources[0].url.includes(internal));
  }
});

test("the agent's steps and prose land in different places", () => {
  const page = loadPage({ runtime: CONNECTED });
  page.el("run-brief").click();
  const source = page.sources[0];
  source.emit(
    "message",
    JSON.stringify({
      content: { parts: [{ functionCall: { id: "1", name: "bq_query", args: {} } }] },
    })
  );
  source.emit("message", JSON.stringify({ content: { parts: [{ text: "Crusher 2 " }] } }));
  source.emit("message", JSON.stringify({ content: { parts: [{ text: "tripped." }] } }));
  assert.equal(page.el("brief-answer").textContent, "Crusher 2 tripped.");
  assert.equal(page.el("brief-log").children.length, 1);
  assert.equal(page.el("brief-log").children[0].className, "step");
});

test("a second run closes the first, rather than leaving it to reconnect", () => {
  const page = loadPage({ runtime: CONNECTED });
  page.el("run-brief").click();
  page.el("run-brief").click();
  assert.equal(page.sources.length, 2);
  assert.equal(page.sources[0].closed, true, "the abandoned stream was left open");
  assert.equal(page.sources[1].closed, false);
});

test("the stream closes when the agent finishes", () => {
  const page = loadPage({ runtime: CONNECTED });
  page.el("run-brief").click();
  page.sources[0].emit("proxy-done");
  assert.equal(page.sources[0].closed, true);
});

test("the stream closes when the connection breaks", () => {
  const page = loadPage({ runtime: CONNECTED });
  page.el("run-brief").click();
  page.sources[0].emit("error");
  assert.equal(page.sources[0].closed, true);
  assert.equal(page.el("brief-log").children[0].className, "step failed");
});

test("the stream closes when the reader leaves the page", () => {
  const page = loadPage({ runtime: CONNECTED });
  page.el("run-brief").click();
  page.fire("pagehide");
  assert.equal(page.sources[0].closed, true);
});

/* The two sentences the Run button can falsify.
 *
 * A screen whose purpose is to tell the truth about the connection cannot ship
 * a claim that its own new feature makes false the moment it is used. Both were
 * written before the button existed, and both are checked here in the state
 * that used to break them: after an answer has arrived. */
test("the omission band stops claiming coverage is unchecked once the brief is written", () => {
  const page = loadPage({ runtime: CONNECTED });
  const head = page.el("omission-head");
  // The harness keeps ids and classes out of markup but not text, so the
  // sentence the sheet renders with is read from the sheet.
  assert.match(page.el("brief").innerHTML, /id="omission-head">Coverage has not been checked/);

  page.el("run-brief").click();
  assert.doesNotMatch(head.textContent, /has not been checked/);
  assert.match(head.textContent, /being written now/);

  page.sources[0].emit(
    "message",
    JSON.stringify({ content: { parts: [{ text: "Crusher 2 tripped at 03:10." }] } })
  );
  // Three states, not two: a sentence that stops at "being written now" is
  // still wrong once the brief is sitting above it and the stream has ended.
  assert.doesNotMatch(head.textContent, /has not been checked/);
  assert.doesNotMatch(head.textContent, /being written now/);
  assert.match(head.textContent, /has been written/);
  // The agent that checks the brief for omissions is called a reviewer on this
  // page, in the roster, and in the sentence above the button. It was "the
  // critic" here and nowhere else on the screen, which asks a reader to hold
  // two names for one thing.
  assert.match(head.textContent, /reviewer/);
  assert.doesNotMatch(head.textContent, /critic/i);
});

test("a run that fails before writing anything leaves the band saying so", () => {
  const page = loadPage({ runtime: CONNECTED });
  page.el("run-brief").click();
  page.sources[0].emit("error");
  assert.match(page.el("omission-head").textContent, /Coverage has not been checked/);
});

test("the unverified band's prose flag is true after the brief has been written", () => {
  const page = loadPage({ runtime: CONNECTED });
  const sheet = page.el("brief").innerHTML;
  page.el("run-brief").click();
  page.sources[0].emit(
    "message",
    JSON.stringify({ content: { parts: [{ text: "Crusher 2 tripped at 03:10." }] } })
  );
  assert.ok(page.el("brief-answer").textContent.length > 0, "no agent prose arrived");
  // The band renders once, before the run, and is never redrawn — so the claim
  // it makes has to hold in both states rather than only in the first.
  assert.doesNotMatch(sheet, /No sentence on this page was written by an agent/);
  assert.match(sheet, /Nothing the agents themselves would say is recorded in this build/);
});

test("a late frame from an abandoned stream does not write into the new answer", () => {
  const page = loadPage({ runtime: CONNECTED });
  page.el("run-brief").click();
  const first = page.sources[0];
  page.el("run-brief").click();
  first.emit("message", JSON.stringify({ content: { parts: [{ text: "stale" }] } }));
  assert.equal(page.el("brief-answer").textContent, "");
});

/* plainAnswer wiring — the same defect that chat.js fixed, applied to the
 * handover sheet.
 *
 * The brief is read by a Shift Supervisor, so raw markdown and tool-failure
 * passages must not reach the body copy. plainAnswer() is already in the
 * page's script list; these tests pin the wiring. */

test("the handover answer renders markdown rather than printing its punctuation", () => {
  const page = loadPage({ runtime: CONNECTED });
  page.el("run-brief").click();
  const source = page.sources[0];
  source.emit(
    "message",
    JSON.stringify({ content: { parts: [{ text: "### Findings\n\n**Crusher 2** tripped." }] } })
  );
  const html = page.el("brief-answer").innerHTML;
  assert.ok(html.includes("<h3>"), `heading not rendered: ${html}`);
  assert.ok(html.includes("<strong>"), `bold not rendered: ${html}`);
  assert.ok(!html.includes("###"), `literal ### reached the pane: ${html}`);
  assert.ok(!html.includes("**"), `literal ** reached the pane: ${html}`);
});

test("machine vocabulary from a tool failure does not reach the handover body copy", () => {
  const page = loadPage({ runtime: CONNECTED });
  page.el("run-brief").click();
  const source = page.sources[0];
  // Simulates the failure passage the live run emitted.
  source.emit(
    "message",
    JSON.stringify({
      content: {
        parts: [
          {
            text:
              "The call to `default_api:graph_traverse` failed.\n\n" +
              "- **Error Code:** `INVALID_ARGUMENT`\n\n" +
              "Because this tool failed, the blast radius cannot be assessed.\n\n" +
              "Crusher 2 tripped at 03:10.",
          },
        ],
      },
    })
  );
  const html = page.el("brief-answer").innerHTML;
  // The drawer is expected to hold the raw text. Extract the body copy — the
  // part of the pane before the collapsible — so the assertions only check
  // what a reader would see as body copy.
  const drawerStart = html.indexOf("<details");
  const bodyCopy = drawerStart >= 0 ? html.slice(0, drawerStart) : html;
  // The failure passage is collapsed to a plain sentence in the body.
  assert.ok(!bodyCopy.includes("default_api:"), `machine token in body: ${bodyCopy}`);
  assert.ok(!bodyCopy.includes("INVALID_ARGUMENT"), `error code in body: ${bodyCopy}`);
  // The mine fact that follows the failure is still on the page.
  assert.ok(bodyCopy.includes("Crusher 2"), `mine fact was dropped: ${bodyCopy}`);
});

test("a tool failure in the handover answer is filed in a technical drawer", () => {
  const page = loadPage({ runtime: CONNECTED });
  page.el("run-brief").click();
  const source = page.sources[0];
  source.emit(
    "message",
    JSON.stringify({
      content: {
        parts: [
          {
            text:
              "The call to `default_api:graph_traverse` failed.\n\n" +
              "- **Error Code:** `INVALID_ARGUMENT`\n\n" +
              "Because this tool failed, the blast radius cannot be assessed.\n\n" +
              "Crusher 2 tripped.",
          },
        ],
      },
    })
  );
  const html = page.el("brief-answer").innerHTML;
  // The raw passage is preserved for whoever investigates.
  assert.ok(html.includes("INVALID_ARGUMENT"), `failure text not in drawer: ${html}`);
  // It is behind a details/summary element, not in the body.
  assert.ok(html.includes("<details"), `no collapsible wrapping the failure: ${html}`);
});

test("a script tag in an agent handover answer renders inert", () => {
  const page = loadPage({ runtime: CONNECTED });
  page.el("run-brief").click();
  const source = page.sources[0];
  source.emit(
    "message",
    JSON.stringify({
      content: { parts: [{ text: "<script>alert(1)<\/script> Crusher 2 tripped." }] },
    })
  );
  const html = page.el("brief-answer").innerHTML;
  assert.ok(!html.includes("<script>"), `script element reached the pane: ${html}`);
  assert.ok(html.includes("&lt;script&gt;") || html.includes("Crusher 2"), `content lost: ${html}`);
});

test("the handover pane re-renders from accumulated text so a token split across frames survives", () => {
  const page = loadPage({ runtime: CONNECTED });
  page.el("run-brief").click();
  const source = page.sources[0];
  // Split "**bold**" across two frames — the old textContent append would leave "**b" then "old**".
  source.emit(
    "message",
    JSON.stringify({ content: { parts: [{ text: "**b" }] } })
  );
  source.emit(
    "message",
    JSON.stringify({ content: { parts: [{ text: "old**" }] } })
  );
  const html = page.el("brief-answer").innerHTML;
  assert.ok(html.includes("<strong>"), `bold span not rendered after split: ${html}`);
  assert.ok(!html.includes("**"), `literal asterisks left in pane: ${html}`);
});

test("the handover empty-answer fallback still fires when the agent writes nothing", () => {
  const page = loadPage({ runtime: CONNECTED });
  page.el("run-brief").click();
  const source = page.sources[0];
  // Fire onDone with no text frames — the pane should say something, not stay blank.
  source.emit("proxy-done");
  const text = page.el("brief-answer").textContent;
  assert.ok(text.trim().length > 0, `pane is empty after an agent that wrote nothing: "${text}"`);
});
