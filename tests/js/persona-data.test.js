const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const D = require("../../apps/workspace/persona-data.js");

function loadData() {
  const file = path.join(__dirname, "..", "..", "apps", "shared", "data", "bundle.js");
  const text = fs.readFileSync(file, "utf8");
  return JSON.parse(text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1));
}

const DATA = loadData();
const CODES = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"];

test("branchesOf normalises both shapes value_branch takes", () => {
  assert.deepEqual(D.branchesOf(DATA.personas.personas.P1.value_branch),
    ["asset_reliability"]);
  assert.deepEqual(D.branchesOf(DATA.personas.personas.P4.value_branch),
    ["supply_chain", "procurement"]);
});

test("branchCodesFor returns the branch codes from the data, not from value_branch", () => {
  // P1 belongs to exactly one branch (B1); confirmed against real bundle data.
  assert.deepEqual(D.branchCodesFor("P1", DATA), ["B1"]);
});

test("P1–P7 each yield at least one evidence row, P8 yields zero", () => {
  for (const code of ["P1", "P2", "P3", "P4", "P5", "P6", "P7"]) {
    const rows = D.branchEvidenceFor(code, DATA);
    assert.ok(Array.isArray(rows), `${code} returned a non-array`);
    assert.ok(rows.length > 0, `${code} unexpectedly returned no evidence rows`);
  }
  assert.deepEqual(D.branchEvidenceFor("P8", DATA), [],
    "P8 belongs to no branch and must return an empty array");
});

test("seven personas have branch evidence and P8 has none", () => {
  const withEvidence = CODES.filter((c) => D.branchEvidenceFor(c, DATA).length > 0);
  assert.deepEqual(withEvidence, ["P1", "P2", "P3", "P4", "P5", "P6", "P7"]);
  assert.deepEqual(D.branchEvidenceFor("P8", DATA), []);
});

test("every evidence declares a kind, and carries that kind's fields", () => {
  for (const code of CODES) {
    for (const row of D.branchEvidenceFor(code, DATA)) {
      assert.ok(row.code && row.branch && row.evidence, `${code} returned a partial row`);
      assert.strictEqual(row.branch.code, row.code,
        `${code}/${row.code} byCode lookup returned the wrong branch object`);
      const e = row.evidence;
      assert.ok(["series", "distribution", "share"].includes(e.kind),
        `${code}/${row.code} has kind ${e.kind}`);
      if (e.kind === "series") {
        for (const f of ["points", "min", "max", "readings"]) {
          assert.ok(e[f] !== undefined, `${row.code} series is missing ${f}`);
        }
      } else if (e.kind === "distribution") {
        for (const f of ["bins", "edges", "n"]) {
          assert.ok(e[f] !== undefined, `${row.code} distribution is missing ${f}`);
        }
      } else {
        for (const f of ["part", "whole"]) {
          assert.ok(e[f] !== undefined, `${row.code} share is missing ${f}`);
        }
      }
      assert.ok(typeof e.caption === "string" && e.caption.length > 0,
        `${row.code} has no caption, and the caption must render verbatim`);
    }
  }
});

test("gapRowsFor reproduces the source-table rule exactly", () => {
  const expected = {
    P1: ["feed_rate", "payload", "conveyor_load"],
    P2: [],
    P3: [],
    P4: [],
    P5: ["recovery"],
    P6: ["recovery", "feed_rate", "payload", "conveyor_load"],
    P7: [],
    P8: ["recovery", "feed_rate", "payload", "conveyor_load"],
  };
  for (const code of CODES) {
    const split = D.gapRowsFor(code, DATA);
    assert.deepEqual(split.reached.map((r) => r.id).sort(), expected[code].slice().sort(),
      `${code} reached the wrong rows`);
  }
});

test("no gap row is dropped or double-counted, for any persona", () => {
  const all = DATA.signals.gap.rows.map((r) => r.id).sort();
  for (const code of CODES) {
    const split = D.gapRowsFor(code, DATA);
    const reached = split.reached.map((r) => r.id);
    const other = split.other.map((r) => r.id);
    assert.deepEqual(reached.concat(other).sort(), all, `${code} lost or repeated a row`);
    for (const id of reached) {
      assert.ok(!other.includes(id), `${code} put ${id} in both groups`);
    }
  }
});

test("an unknown persona code returns empty results rather than throwing", () => {
  assert.deepEqual(D.branchCodesFor("P99", DATA), []);
  assert.deepEqual(D.branchEvidenceFor("P99", DATA), []);
  const split = D.gapRowsFor("P99", DATA);
  assert.deepEqual(split.reached, []);
  assert.equal(split.other.length, DATA.signals.gap.rows.length);
});

test("missing router.js throws a self-explaining load-order error", () => {
  // Simulate the browser case where router.js was not loaded first: eval the
  // source in a minimal sandbox that has no require (so ROUTER becomes null)
  // and no global branchesOf. The new guard must throw before any function
  // body executes, naming both files.
  const src = fs.readFileSync(
    path.join(__dirname, "..", "..", "apps", "workspace", "persona-data.js"),
    "utf8"
  );
  // Wrap in a function that supplies a fake `require` returning null (simulating
  // missing router) and no branchesOf global — matching the bad browser state.
  const fn = new Function("require", "module", "exports", src);
  assert.throws(
    () => fn(() => null, { exports: {} }, {}),
    (err) => {
      assert.ok(err instanceof Error, "expected an Error");
      assert.ok(
        err.message.includes("router.js"),
        `error message must name router.js — got: ${err.message}`
      );
      return true;
    }
  );
});
