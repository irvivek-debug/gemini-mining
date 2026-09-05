/* The answer pane, checked against what an agent actually said.
 *
 * Every other gate in this repository reads source. None of them can see a
 * sentence a model writes at runtime, and the answer pane is the largest body
 * text on the role page. So the fixture here is not invented: it is the 8,239
 * characters S01 returned from Cloud Run, saved off the page verbatim.
 *
 * The first test is the one that matters most. Agent text is untrusted and it
 * is on its way to innerHTML, so escaping has to happen before any markdown is
 * applied — the other order turns a model's <script> into an element.
 */
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const P = require("../../apps/shared/plain.js");

const LIVE = fs.readFileSync(
  path.join(__dirname, "fixtures", "s01-live-answer.txt"),
  "utf8"
);

/* What a reader sees: the rendered markup with its tags taken off and its
 * entities put back. A token that only survives as &lt;…&gt; is still a token
 * the reader meets, which is why the entities are decoded rather than dropped. */
function readerText(html) {
  return String(html)
    .replace(/<[^>]*>/g, " ")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ");
}

// ------------------------------------------------------------------ safety

test("a script tag in an agent's answer renders inert", () => {
  const said = P.plainAnswer("Here is the risk: <script>alert(1)</script> and more.");
  assert.ok(
    !/<script/i.test(said.html),
    `an agent's script tag became an element: ${said.html}`
  );
  assert.ok(
    said.html.includes("&lt;script&gt;alert(1)&lt;/script&gt;"),
    `the tag was not escaped as text: ${said.html}`
  );
});

test("escaping runs before markdown, not after", () => {
  // If markdown ran first, the ** would already be <strong> and esc() would
  // then turn that into &lt;strong&gt; — the bold would print as literal tags.
  const said = P.plainAnswer("**bold** and <b>not bold</b>");
  assert.ok(said.html.includes("<strong>bold</strong>"), said.html);
  assert.ok(said.html.includes("&lt;b&gt;not bold&lt;/b&gt;"), said.html);
  assert.ok(!said.html.includes("<b>"), `raw markup survived: ${said.html}`);
});

test("an img with an onerror handler cannot reach the DOM as an element", () => {
  const said = P.plainAnswer('<img src=x onerror="alert(1)">');
  assert.ok(!/<img/i.test(said.html), said.html);
  assert.ok(said.html.includes("&lt;img"), said.html);
  assert.ok(!said.html.includes('onerror="'), `an attribute survived: ${said.html}`);
});

// ------------------------------------------------------------- vocabulary

const BANNED = [
  "INVALID_ARGUMENT",
  "QUERY_FAILED",
  "SQL_INTERPOLATION",
  "Job ID",
  "bigquery.googleapis.com",
  "ML.PREDICT",
  "@parameter",
  "rows_scanned",
  "default_api:",
];

test("no machine vocabulary from the live answer survives into body copy", () => {
  const body = readerText(P.plainAnswer(LIVE).html);
  const found = BANNED.filter((token) => body.includes(token));
  assert.deepEqual(found, [], `the reader still meets: ${found.join(", ")}`);
});

test("the live answer's table identifiers are said the way the rest of the estate says them", () => {
  const body = readerText(P.plainAnswer(LIVE).html);
  assert.ok(!body.includes("mining_data."), `a qualified table id survived: ${body.slice(0, 400)}`);
  assert.ok(!body.includes("telemetry_stream"), "the sensor readings table id survived");
  assert.ok(!body.includes("maintenance_logs"), "the maintenance history table id survived");
  assert.ok(body.includes(P.TABLES.telemetry_stream), "the plain phrase is not the one plain.js publishes");
  assert.ok(body.includes(P.TABLES.maintenance_logs), "the plain phrase is not the one plain.js publishes");
});

test("a failed tool call collapses to the vocabulary the activity log already uses", () => {
  const body = readerText(P.plainAnswer(LIVE).html);
  // failLine() is what turned graph_traverse into this sentence in the step
  // log. The answer pane must not invent a second way of saying it.
  assert.ok(
    body.includes(P.failLine("graph_traverse", { traversal: "blast_radius" })),
    `the plain failure sentence is missing from:\n${body}`
  );
  assert.ok(
    body.includes(P.failLine("bqml_predict", {})),
    "the prediction failure was not said in plain words"
  );
  assert.ok(
    body.includes(P.failLine("bq_query", { sql: "`mining_data.telemetry_stream`" })),
    "the lookup failure was not said in plain words"
  );
});

/* The failure sentence is built from the passage itself, because by the time an
 * answer reaches plainAnswer the call that failed is only described in prose.
 * That makes the passage the argument list, and doc_search is the one tool
 * whose argument is free text: a branch that took the first string it found
 * would quote the model's whole failure report — error codes and all — into
 * the sentence written to remove exactly that.
 */
test("a failed document search does not quote the model's own prose back", () => {
  // Shaped like the live fixture's passages: an announcement naming the tool
  // in backticks, then the machine detail underneath it.
  const passage = [
    "The call to `doc_search` failed.",
    "- **Error Code:** `QUERY_FAILED` (`INVALID_ARGUMENT`), job 4f9c-11ee.",
  ].join("\n");
  const said = P.plainAnswer(passage);
  const body = readerText(said.html);
  for (const token of ["QUERY_FAILED", "INVALID_ARGUMENT", "4f9c-11ee", "doc_search"]) {
    assert.ok(!body.includes(token), `the reader still meets ${token}: ${body}`);
  }
  assert.ok(body.includes("Couldn't finish"), `no plain failure sentence in: ${body}`);
  assert.ok(said.technical.includes("QUERY_FAILED"), "the raw passage was not kept");
});

test("the honest fact that a step failed and the answer is short survives", () => {
  const body = readerText(P.plainAnswer(LIVE).html);
  assert.ok(/failed/i.test(body), "the answer no longer admits anything failed");
  assert.ok(/incomplete/i.test(body), "the answer no longer admits it is incomplete");
  // The agents themselves reported BLOCKED and rated their confidence low.
  // De-jargoning must not quietly upgrade that.
  assert.ok(body.includes("BLOCKED"), "the specialists' BLOCKED verdict was dropped");
  assert.ok(/confidence[^.]*\blow\b/i.test(body), "the low-confidence verdict was dropped");
});

test("the raw passage is kept for the drawer rather than discarded", () => {
  const said = P.plainAnswer(LIVE);
  assert.ok(said.technical, "nothing was kept for the drawer");
  for (const token of ["INVALID_ARGUMENT", "QUERY_FAILED", "SQL_INTERPOLATION", "Job ID"]) {
    assert.ok(
      said.technical.includes(token),
      `${token} was deleted instead of filed: ${said.technical.slice(0, 300)}`
    );
  }
});

test("an answer with nothing to hide keeps the drawer empty", () => {
  const said = P.plainAnswer("### Findings\n\nAll five machines are inside their limits.");
  assert.equal(said.technical, "");
});

// ----------------------------------------------------------------- markdown

test("headings, bold, lists and code spans render as elements", () => {
  const said = P.plainAnswer(
    "### Telemetry\n\n" +
      "#### Detail\n\n" +
      "- **Vibration**: the reading is `vibration_hz`\n" +
      "* A second point\n"
  );
  assert.ok(said.html.includes("<h3>Telemetry</h3>"), said.html);
  assert.ok(said.html.includes("<h4>Detail</h4>"), said.html);
  assert.ok(said.html.includes("<ul>"), said.html);
  assert.equal((said.html.match(/<li>/g) || []).length, 2, said.html);
  assert.ok(said.html.includes("<strong>Vibration</strong>"), said.html);
  assert.ok(said.html.includes("<code>vibration_hz</code>"), said.html);
});

test("no literal markdown punctuation is left for the reader to decode", () => {
  const body = readerText(P.plainAnswer(LIVE).html);
  assert.ok(!body.includes("###"), "a heading printed as hashes");
  assert.ok(!body.includes("**"), "bold printed as asterisks");
  assert.ok(!body.includes("`"), "a code span printed as backticks");
});

test("plain prose is a paragraph, not a bare string", () => {
  const said = P.plainAnswer("The pump is running hot.");
  assert.equal(said.html, "<p>The pump is running hot.</p>");
});

test("an empty answer renders as nothing at all", () => {
  const said = P.plainAnswer("");
  assert.equal(said.html, "");
  assert.equal(said.technical, "");
  assert.equal(P.plainAnswer(null).html, "");
});

test("a partial answer mid-stream renders without throwing", () => {
  // The pane re-renders on every text frame, so plainAnswer sees the answer
  // cut at an arbitrary character — including inside a code span.
  for (let cut = 0; cut < LIVE.length; cut += 97) {
    assert.doesNotThrow(() => P.plainAnswer(LIVE.slice(0, cut)), `cut at ${cut}`);
  }
});
