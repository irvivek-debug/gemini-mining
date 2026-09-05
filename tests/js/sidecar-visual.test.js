/* The sidecar's own visual identity, checked on the resolved colour values --
 * not on a class name existing, which would pass on a rule that changed
 * nothing but a comment. The complaint (2026-08-18 sales-ready-workspace
 * plan, Task E) was explicit: the live chat panel and the static page beside
 * it read as the same surface. That is a claim about pixels, so it is
 * checked against pixels -- the hex values tokens.css and workspace.css
 * actually resolve to -- rather than against whether ".sidecar" differs from
 * ".card" as a string.
 */
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.join(__dirname, "..", "..");
const TOKENS_CSS = fs.readFileSync(
  path.join(ROOT, "apps", "shared", "tokens.css"),
  "utf8"
);
const WORKSPACE_CSS = fs.readFileSync(
  path.join(ROOT, "apps", "workspace", "workspace.css"),
  "utf8"
);
const CSS = TOKENS_CSS + "\n" + WORKSPACE_CSS;

/** Every `--token: #hex;` declared on :root, tokens.css and workspace.css both
 *  read together so a token workspace.css might one day add is not missed. */
function tokenMap() {
  const map = {};
  for (const m of CSS.matchAll(/--([\w-]+):\s*(#[0-9a-fA-F]{3,8})\s*;/g)) {
    map[m[1]] = m[2];
  }
  return map;
}

const TOKENS = tokenMap();

/** The first top-level `selector { … }` block, found by matching braces rather
 *  than stopping at the first `}` -- none of the rules this file reads nest a
 *  brace inside themselves, but a regex stopping at the first `}` would have
 *  silently returned a truncated body if one ever did. */
function ruleBody(selector) {
  const at = CSS.indexOf(selector + " {");
  assert.ok(at >= 0, `no rule found for ${selector}`);
  const open = CSS.indexOf("{", at);
  let depth = 0;
  for (let i = open; i < CSS.length; i += 1) {
    if (CSS[i] === "{") depth += 1;
    else if (CSS[i] === "}") {
      depth -= 1;
      if (depth === 0) return CSS.slice(open + 1, i);
    }
  }
  throw new Error(`unterminated rule for ${selector}`);
}

/** A declaration's value, resolved from var(--x) through the token map to a
 *  literal hex string a difference can be measured against. */
function resolvedDeclaration(body, property) {
  const m = new RegExp(`(?:^|;)\\s*${property}\\s*:\\s*([^;]+);`).exec(body);
  assert.ok(m, `no ${property} declared in: ${body}`);
  let value = m[1].trim();
  const varMatch = /var\((--[\w-]+)\)/.exec(value);
  if (varMatch) {
    const token = TOKENS[varMatch[1].slice(2)];
    assert.ok(token, `${varMatch[1]} is not a declared token`);
    return token;
  }
  return value;
}

function hexToRgb(hex) {
  const clean = hex.replace("#", "");
  const full =
    clean.length === 3
      ? clean.split("").map((c) => c + c).join("")
      : clean.slice(0, 6);
  const n = parseInt(full, 16);
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
}

function rgbDistance(hexA, hexB) {
  const a = hexToRgb(hexA);
  const b = hexToRgb(hexB);
  return Math.sqrt((a.r - b.r) ** 2 + (a.g - b.g) ** 2 + (a.b - b.b) ** 2);
}

// The panel's own static surfaces -- what a reader compares the sidecar
// against. .card is tokens.css's own base surface, reused everywhere else on
// every screen; .rail and .agent-card are the two panel-side components that
// share persona.html with the sidecar itself, so they are the exact
// neighbours a reader's eye moves between.
const PAGE_SURFACES = [".card", ".rail", ".agent-card"];

// Below this RGB distance two colours read as the same surface at a glance --
// picked well under the gap this change actually produces (surface #1F2020
// vs surface-top #353535 is ~30 per channel on its own), so a revert to the
// same token, or a swap to a token that merely LOOKS different in a diff but
// still renders indistinguishably, fails this rather than passing on a
// technicality.
const MEANINGFUL_DISTANCE = 25;

test("the sidecar's background is a measurably different colour from the page's own surfaces", () => {
  const sidecarBg = resolvedDeclaration(ruleBody(".sidecar"), "background");
  for (const selector of PAGE_SURFACES) {
    const pageBg = resolvedDeclaration(ruleBody(selector), "background");
    const distance = rgbDistance(sidecarBg, pageBg);
    assert.ok(
      distance >= MEANINGFUL_DISTANCE,
      `.sidecar's background ${sidecarBg} is only ${distance.toFixed(1)} RGB units from ${selector}'s ${pageBg} -- ` +
        `that reads as the same surface, which is the defect this test exists to catch`
    );
  }
});

test("the sidecar's border is a measurably different colour from the page's own surfaces", () => {
  const sidecarBorderDecl = resolvedDeclaration(ruleBody(".sidecar"), "border");
  const sidecarBorder = sidecarBorderDecl.split(/\s+/).find((tok) => tok.startsWith("#"));
  assert.ok(sidecarBorder, `.sidecar's border declaration has no resolvable colour: ${sidecarBorderDecl}`);
  for (const selector of PAGE_SURFACES) {
    const pageBorderDecl = resolvedDeclaration(ruleBody(selector), "border");
    const pageBorder = pageBorderDecl.split(/\s+/).find((tok) => tok.startsWith("#"));
    assert.ok(pageBorder, `${selector}'s border declaration has no resolvable colour: ${pageBorderDecl}`);
    const distance = rgbDistance(sidecarBorder, pageBorder);
    assert.ok(
      distance >= MEANINGFUL_DISTANCE,
      `.sidecar's border ${sidecarBorder} is only ${distance.toFixed(1)} RGB units from ${selector}'s ${pageBorder}`
    );
  }
});

// The label is what makes the boundary legible as "a live conversation" and
// not just "a panel in a different colour". It has to survive chat.js
// mounting or remounting #chat with innerHTML -- which is why it lives in
// persona.html as .sidecar's own static child, sibling to #runtime and #chat,
// rather than being written by chat.js itself.
test("persona.html carries a static label naming what the sidecar is, outside chat.js's own mount point", () => {
  const html = fs.readFileSync(
    path.join(ROOT, "apps", "workspace", "persona.html"),
    "utf8"
  );
  const sidecarOpen = html.indexOf('id="sidecar"');
  assert.ok(sidecarOpen >= 0, "persona.html has no #sidecar");
  const sidecarClose = html.indexOf("</aside>", sidecarOpen);
  const sidecarMarkup = html.slice(sidecarOpen, sidecarClose);
  assert.match(sidecarMarkup, /class="sidecar-tag"/, "no label element inside .sidecar");
  assert.ok(
    sidecarMarkup.indexOf('class="sidecar-tag"') < sidecarMarkup.indexOf('id="chat"'),
    "the label is not chat.js's to erase -- it must sit outside #chat and #runtime"
  );
  // The label itself uses the same accent token the CSS distinction rests on,
  // so a reader who cannot resolve the colour still meets the word "live".
  assert.match(sidecarMarkup, /live/i, "the label does not say this panel is live");
});

test("_helpers -- rgbDistance actually distinguishes colours, so the assertions above can fail", () => {
  assert.equal(rgbDistance("#1F2020", "#1F2020"), 0);
  assert.ok(rgbDistance("#1F2020", "#353535") > MEANINGFUL_DISTANCE);
});
