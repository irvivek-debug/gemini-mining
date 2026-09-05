/* The page: pick a role, render its panel, and say honestly whether the agents
 * are reachable.
 *
 * The connection state comes from /api/runtime, not from the build. The old
 * screens rendered DATA.workspace.runtime — a constant baked into bundle.js at
 * build time — and therefore printed NOT CONNECTED in production while the
 * service was connected to all 52. Being wrong in the pessimistic direction is
 * still being wrong.
 */
const PERSONAS = DATA.personas.personas;
const CODES = Object.keys(PERSONAS).sort();

function currentCode() {
  const asked = new URLSearchParams(location.search).get("p");
  return PERSONAS[asked] ? asked : CODES[0];
}

function mountPicker(code) {
  const select = el("role-select");
  select.innerHTML = CODES.map(
    (c) => `<option value="${esc(c)}"${c === code ? " selected" : ""}>${esc(PERSONAS[c].title)}</option>`
  ).join("");
  select.addEventListener("change", () => {
    location.search = `?p=${encodeURIComponent(select.value)}`;
  });
}

function drawerBody(code) {
  const persona = PERSONAS[code];
  const byId = {};
  DATA.catalog.agents.forEach((a) => (byId[a.agent_id] = a));
  const rows = (persona.agents || [])
    .map((id) => byId[id])
    .filter(Boolean)
    .map(
      (a) =>
        `<dt class="mono">${esc(a.agent_id)} · ${esc(a.display_name)}</dt>` +
        `<dd>Pattern ${esc(a.pattern)} · ${esc(a.model_tier)} · APQC ${esc(a.apqc_code)}<br>` +
        `<span class="mono">${esc((a.source_tables || []).join(", "))}</span><br>` +
        `<span class="mono">${esc((a.tools || []).concat(a.traversals || []).join(", "))}</span></dd>`
    )
    .join("");
  return (
    `<dl>${rows}</dl>` +
    `<p>${esc(persona.code)} · value branch ` +
    `<span class="mono">${esc(branchesOf(persona.value_branch).join(", "))}</span></p>`
  );
}

/* The honest answer to "can this page reach the agents", asked of the wire.
 *
 * This page used to run a fetch of its own, guarded on reply.ok while the
 * workspace screens guarded on the shape of the body — so a 500 carrying a JSON
 * body was a not-connected runtime here and an unreadable reply there, which is
 * two answers to one question. Both now come from runtimeState() in
 * apps/shared/runtime.js, and the words come from connectionCopy(), so this
 * screen cannot drift from the other five.
 *
 * The state and the exception behind it go to the console, not to the box: the
 * reader of this page picked a role from a dropdown, and a Google auth stack
 * line is not something they can act on. */
async function showRuntime() {
  const box = document.createElement("div");
  box.className = "runtime-state";
  box.textContent = "Checking whether the agents are reachable…";
  // #runtime, not #sidecar: the sidecar's other child is written by chat.js with
  // innerHTML, which would erase anything sharing that node.
  el("runtime").appendChild(box);
  const state = await runtimeState();
  const copy = connectionCopy(state);
  box.className = `runtime-state ${copy.key}`;
  box.textContent = copy.lines.join(" ");
  if (state.detail) console.warn("/api/runtime:", state.stage || "", state.detail);
}

const CODE = currentCode();
mountNav("workspace", "persona.html");
mountPicker(CODE);
el("role-lede").textContent = PERSONAS[CODE].title;

/* A7: the Mine Controller reads this from the control room's overhead display
 * rather than at a desk, where the audit measured 14px body text as illegible.
 * The whole page steps up together, applied by persona so that the person does
 * not have to know to ask for it. The screen this one replaced carried the same
 * accommodation and this is the one P7 opens daily, so it belongs here.
 *
 * The note says what the scale is for and not what it is: the factor lives in
 * .scale-lg, and a ratio quoted in copy is a number that goes stale the first
 * time the stylesheet is touched. It is also a figure nothing on this page can
 * check, which is the whole objection this screen exists to answer.
 */
if (CODE === "P7") {
  el("wrap").classList.add("scale-lg");
  el("scale-note").textContent =
    "Overhead type scale — this role's page is read from the control room " +
    "display rather than at a desk.";
}

el("panel").innerHTML = renderPanel(CODE, DATA);
el("foot").innerHTML = technicalDrawer(drawerBody(CODE), "agent ids, tables, model tiers") +
  provenance();
showRuntime().catch((err) => console.error("the connection check failed to render:", err));

const CHAT = mountChat(el("chat"), CODE, DATA);

/* The "Ask this one" buttons in the sign-off block are handled by delegation on
   the panel, so they keep working however the panel is re-rendered. */

el("panel").addEventListener("click", (event) => {
  const button = event.target.closest("button.ask[data-agent]");
  if (!button) return;
  CHAT.pick(button.dataset.agent);
  el("chat").scrollIntoView({ behavior: "smooth", block: "start" });
});

/* EventSource reconnects by itself when a connection closes. A page left with
   one open while it is torn down can re-ask a question that costs a minute or
   two of model time, and nobody is watching by then. */
window.addEventListener("pagehide", () => CHAT.close());
