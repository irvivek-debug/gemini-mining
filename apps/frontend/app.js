/* Agentic AI Mining — five-screen front end.
 *
 * WHY THIS FILE IS NAMESPACED
 * The two handover files each defined switchScreen, inspectNode, selectPersona,
 * initParticleCanvas, copyAgentUrn and fallbackCopyText — six names, two
 * different bodies each. Concatenating them would have let the second
 * definition silently win, and the failure mode is a screen that renders but
 * behaves as though it belongs to the other file. Each screen therefore owns a
 * closure (S1..S5) and exposes only what the router calls. Nothing is global
 * except App.
 *
 * The markup carries no inline onclick. Every binding is attached here, so a
 * renamed function fails loudly at wire-up instead of quietly at click time.
 */
(function () {
  "use strict";

  var SCREENS = ["macro", "schematic", "personas", "ecosystem", "architecture"];

  /* The fifth screen was called "governance" until it became the logical
     architecture. Links to #governance are already in circulation, so the old
     name resolves rather than silently falling back to the first screen. */
  var LEGACY_SCREEN = { governance: "architecture" };

  function el(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#039;");
  }
  function on(id, evt, fn) { var e = el(id); if (e) e.addEventListener(evt, fn); }

  /* ------------------------------------------------------------- clipboard */
  var Clip = (function () {
    function toast(text) {
      var t = el("copy-toast");
      if (!t) return;
      t.textContent = text;
      t.style.display = "block";
      setTimeout(function () { t.style.display = "none"; }, 2200);
    }
    function fallback(text) {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.cssText = "position:fixed;top:0;left:0;width:2em;height:2em;border:none;background:transparent;";
      document.body.appendChild(ta);
      ta.focus(); ta.select();
      try { document.execCommand("copy"); } catch (e) { /* clipboard unavailable */ }
      document.body.removeChild(ta);
    }
    return {
      copy: function (text, btn) {
        if (!text) return;
        var span = btn && btn.querySelector("span");
        if (span) {
          var prev = span.textContent;
          span.textContent = "Copied";
          setTimeout(function () { span.textContent = prev; }, 1600);
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text)
            .then(function () { toast("Copied: " + text); })
            .catch(function () { fallback(text); toast("Copied: " + text); });
        } else {
          fallback(text); toast("Copied: " + text);
        }
      }
    };
  })();

  /* Two addresses, and they are not interchangeable. geminiUrl is the ONE
     Gemini Enterprise workspace the whole estate is published into -- it is the
     same URL for all 101 agents. invokeUrl is that agent's own gateway
     endpoint. Both are rendered wherever an agent is named, so "invoke it
     directly" reaches the agent the card is about rather than a workspace that
     merely contains it. stopPropagation keeps a launch click from also firing
     the card's own open-deep-dive handler. */
  function launchLinks(agent, compact) {
    if (!agent) return "";
    var gem = agent.geminiUrl || window.geminiEnterpriseUrl || "";
    var inv = agent.invokeUrl || "";
    var out = '<div class="agent-launch-row" data-launch-row="1">';
    if (gem) {
      out += '<a class="agent-launch-chip chip-gemini" href="' + esc(gem) + '" target="_blank" rel="noopener noreferrer"' +
        ' title="Open the Gemini Enterprise workspace this agent is published into">&#10022; Gemini Enterprise</a>';
    }
    if (inv && !compact) {
      out += '<a class="agent-launch-chip" href="' + esc(inv) + '" target="_blank" rel="noopener noreferrer"' +
        ' title="' + esc(inv) + '">&#8599; Invoke ' + esc(agent.id) + "</a>";
    }
    return out + "</div>";
  }

  /* Launch anchors live inside clickable cards. Without this every launch
     click would also open the deep dive behind the new tab. */
  function bindLaunchRows(root) {
    if (!root) return;
    Array.prototype.forEach.call(root.querySelectorAll("[data-launch-row] a"), function (a) {
      a.addEventListener("click", function (e) { e.stopPropagation(); });
    });
  }

  /* Entry animations are applied by adding a class and removing it once the
     run is over. Leaving the class on is what made the architecture stack
     replay -- and briefly vanish -- every time its tab was clicked: hiding a
     pane with display:none restarts any CSS animation on its children, so a
     rule holding opacity:0 before its delay elapses re-applies on every
     return. Removing the class leaves the elements simply visible. */
  function playOnce(node, count, stepMs, durationMs) {
    if (!node) return;
    node.classList.add("motion-playing");
    setTimeout(function () {
      node.classList.remove("motion-playing");
    }, count * stepMs + durationMs + 80);
  }

  /* =========================================================== S1 — Macro */
  var S1 = (function () {
    var HEADWINDS = [
      { label: "ORE GRADE DECAY",      val: "0.48%", cmp: "0.82%", unit: null,   desc: "Industry average decline over 10 years", fill: 45 },
      { label: "SPECIFIC ENERGY",      val: "18.4",  cmp: null,    unit: "kWh/t", desc: "Up from 12 kWh/t baseline",              fill: 82 },
      { label: "DEMURRAGE PENALTIES",  val: "$24M",  cmp: null,    unit: "YTD",   desc: "Port bottleneck inefficiencies",         fill: 68 }
    ];
    var LEVERS = [
      { tag: "CAPEX DISCIPLINE",       desc: "Marginal returns diminishing",   fill: 90, status: "EXHAUSTED" },
      { tag: "VENDOR SQUEEZE",         desc: "Contractual floors reached",     fill: 85, status: "EXHAUSTED" },
      { tag: "HEADCOUNT FREEZES",      desc: "Impacting operational safety",   fill: 95, status: "HARD CEILING" },
      { tag: "AGENTIC DECISION LAYER", desc: "Software-defined optimization",  fill: 100, status: "HIGH GROWTH", extra: "UNCAPPED", highlight: true }
    ];
    var OUTCOMES = [
      { label: "THROUGHPUT UPLIFT",   val: "2-5%",  sub: "Mine-to-market volume" },
      { label: "MAINTENANCE OPEX",    val: "5-15%", sub: "Cost reduction run-rate" },
      { label: "OUTBOUND SCHEDULING", val: "2x",    sub: "Productivity multiplier" },
      { label: "EBITDA IMPACT",       val: "2-4%",  sub: "Percentage point gain" }
    ];

    function render() {
      el("s1-headwinds").innerHTML = HEADWINDS.map(function (h) {
        var right = h.cmp
          ? '<span class="headwind-baseline">' + esc(h.cmp) + "</span>"
          : '<span class="headwind-unit">' + esc(h.unit) + "</span>";
        return '<div class="headwind-card">' +
          '<div class="headwind-header"><span>' + esc(h.label) + "</span>" +
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#D93025" stroke-width="2"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/></svg>' +
          "</div>" +
          '<div class="headwind-val-row"><span class="headwind-val">' + esc(h.val) + "</span>" + right + "</div>" +
          '<div class="headwind-desc">' + esc(h.desc) + "</div>" +
          '<div class="red-bar-fill"><div class="fill-inner" style="width:' + h.fill + '%"></div></div>' +
          "</div>";
      }).join("");

      el("s1-levers").innerHTML = LEVERS.map(function (l) {
        var bar = l.highlight
          ? '<div class="lever-track-blue"><span></span></div>'
          : '<div class="red-bar-fill"><div class="fill-inner" style="width:' + l.fill + '%"></div></div>';
        var status = l.highlight
          ? '<span class="status-active">' + esc(l.status) + "</span><span class=\"status-active\">" + esc(l.extra) + "</span>"
          : '<span class="status-exhausted">' + esc(l.status) + "</span>";
        return '<div class="lever-col' + (l.highlight ? " highlight" : "") + '">' +
          '<div class="lever-tag">' + esc(l.tag) + "</div>" +
          '<div class="lever-desc">' + esc(l.desc) + "</div>" + bar +
          '<div class="lever-status-row">' + status + "</div></div>";
      }).join("");

      el("s1-outcomes").innerHTML = OUTCOMES.map(function (o) {
        return '<div class="outcome-kpi-block">' +
          '<div class="outcome-label">' + esc(o.label) + "</div>" +
          '<div class="outcome-val">' + esc(o.val) + "</div>" +
          '<div class="outcome-subtext">' + esc(o.sub) + "</div></div>";
      }).join("");
    }
    return { render: render };
  })();

  /* ======================================================= S2 — Schematic */
  var S2 = (function () {
    var TELEMETRY = [
      { node: "pita",     name: "Pit Alpha Operations", badge: "badge-optimal",  badgeText: "OPTIMAL",  a: ["Extraction Rate", "6,204", "TPH"],  b: ["Active Fleet", "42", "Units"] },
      { node: "crusher",  name: "Crusher-03",           badge: "badge-critical", badgeText: "CRITICAL", a: ["Bearing Temp", "104.2", "°C"], b: ["Throughput", "4,152", "TPH"], critical: true },
      { node: "sag",      name: "SAG Mill Circuit",     badge: "badge-optimal",  badgeText: "OPTIMAL",  a: ["Power Draw", "14.21", "MW"],        b: ["P80 Size", "125", "µm"] },
      { node: "flot",     name: "Flotation Cells",      badge: "badge-stable",   badgeText: "STABLE",   a: ["Recovery Rate", "88.42", "%"],      b: ["Reagent Dose", "12.5", "g/t"] },
      { node: "tailings", name: "Tailings Facility",    badge: "badge-stable",   badgeText: "STABLE",   a: ["Water Return", "65.2", "%"],        b: ["Seepage", "0.02", "L/s"] },
      { node: "port",     name: "Port Berth",           badge: "badge-optimal",  badgeText: "OPTIMAL",  a: ["Stockpile", "124.4k", "t"],         b: ["Demurrage", "0", "Days"] }
    ];

    /* GEOMETRY IS MEASURED, NOT DECLARED.
     *
     * The handover file carried the connector paths and particle conduits as
     * hard-coded coordinates in a 1100x460 space. The nodes, however, are laid
     * out by a CSS grid (1.1fr 2fr 1.5fr), so their real positions are decided
     * by the browser, not by that constant. Measured on this build the two
     * disagreed by 45-144px, worsening left to right, and every responsive
     * breakpoint widened the gap further -- particles drifting through empty
     * canvas while the nodes they were meant to connect sat elsewhere.
     *
     * So the topology is declared as node-id pairs and the geometry is read
     * from the live element rects each time the canvas starts. The streams
     * land on the nodes at any viewport, and adding a node to the markup is
     * enough to route flow through it. */
    var EDGES = [
      { a: "pita",     b: "sh05",     type: "material", color: "#C28B53", size: 3.5, speed: 0.006, bend: -18 },
      { a: "pitb",     b: "sh05",     type: "material", color: "#C28B53", size: 3.5, speed: 0.005, bend:  18 },
      { a: "sh05",     b: "trks",     type: "material", color: "#C28B53", size: 4.0, speed: 0.015, bend: 0 },
      { a: "trks",     b: "crusher",  type: "material", color: "#C28B53", size: 4.5, speed: 0.012, bend: 0 },
      { a: "crusher",  b: "conveyor", type: "material", color: "#F59E0B", size: 3.5, speed: 0.015, bend: 0 },
      { a: "conveyor", b: "sag",      type: "material", color: "#F59E0B", size: 3.5, speed: 0.015, bend: 0 },
      { a: "sag",      b: "ball",     type: "material", color: "#00ACC1", size: 3.0, speed: 0.008, bend: -14 },
      { a: "sag",      b: "flot",     type: "material", color: "#00ACC1", size: 3.2, speed: 0.009, bend:  14 },
      { a: "flot",     b: "rail",     type: "material", color: "#FFB300", size: 3.0, speed: 0.007, bend: -22 },
      { a: "rail",     b: "port",     type: "material", color: "#FFB300", size: 4.0, speed: 0.014, bend: 0 },
      { a: "flot",     b: "tailings", type: "material", color: "#78909C", size: 3.2, speed: 0.006, bend:  22 },
      { a: "tailings", b: "water",    type: "water",    color: "#29B6F6", size: 2.8, speed: 0.008, bend: 0 },
      { a: "water",    b: "sag",      type: "water",    color: "#29B6F6", size: 2.5, speed: 0.005, bend:  70 }
    ];

    var geometry = [];
    var particles = [];
    var rafId = null;
    var activeNode = null;

    /* Centre of a node in canvas space, or null if it is not laid out. */
    function centre(id, box) {
      var n = el("node-" + id);
      if (!n) return null;
      var r = n.getBoundingClientRect();
      if (!r.width) return null;
      return { x: r.left - box.left + r.width / 2, y: r.top - box.top + r.height / 2 };
    }

    function measure() {
      var host = el("schematic-container");
      if (!host) return false;
      var box = host.getBoundingClientRect();
      geometry = [];
      EDGES.forEach(function (e) {
        var from = centre(e.a, box), to = centre(e.b, box);
        if (!from || !to) return;
        var mx = (from.x + to.x) / 2, my = (from.y + to.y) / 2;
        var dx = to.x - from.x, dy = to.y - from.y;
        var len = Math.hypot(dx, dy) || 1;
        geometry.push({
          edge: e, from: from, to: to,
          ctrl: { x: mx + (-dy / len) * e.bend, y: my + (dx / len) * e.bend }
        });
      });

      particles = [];
      if (!geometry.length) return false;
      for (var i = 0; i < 70; i++) {
        var g = geometry[i % geometry.length];
        particles.push({
          g: g, t: Math.random(),
          speed: g.edge.speed * (0.8 + Math.random() * 0.4),
          telem: (i % 3 === 0)
        });
      }
      return true;
    }

    function point(p0, p1, ctrl, t) {
      var u = 1 - t;
      return { x: u*u*p0.x + 2*u*t*ctrl.x + t*t*p1.x, y: u*u*p0.y + 2*u*t*ctrl.y + t*t*p1.y };
    }

    function startCanvas() {
      var canvas = el("schematic-particle-canvas");
      var host = el("schematic-container");
      if (!canvas || !host) return;
      var rect = host.getBoundingClientRect();
      if (!rect.width) return;
      canvas.width = rect.width;
      canvas.height = rect.height;
      if (!measure()) return;
      var ctx = canvas.getContext("2d");

      function frame(now) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        /* Connectors are drawn here rather than left to the static SVG: the
           SVG paths carried the same fixed coordinates the particles did, so
           they missed the nodes by the same margin. Drawing both from one
           measured geometry keeps the line and the flow on top of each other. */
        geometry.forEach(function (g) {
          ctx.beginPath();
          ctx.moveTo(g.from.x, g.from.y);
          ctx.quadraticCurveTo(g.ctrl.x, g.ctrl.y, g.to.x, g.to.y);
          ctx.strokeStyle = g.edge.type === "water" ? "rgba(41,182,246,0.45)" : "#BDC1C6";
          ctx.lineWidth = 1.5;
          if (g.edge.type === "water") { ctx.setLineDash([4, 4]); } else { ctx.setLineDash([]); }
          ctx.stroke();
          ctx.setLineDash([]);
        });

        var pulse = (Math.sin(now * 0.005) + 1) * 0.5;
        var crush = centre("crusher", host.getBoundingClientRect());
        if (crush) {
          ctx.beginPath();
          ctx.arc(crush.x, crush.y, 54 + pulse * 14, 0, Math.PI * 2);
          ctx.strokeStyle = "rgba(217,48,37," + (0.4 - pulse * 0.28) + ")";
          ctx.lineWidth = 2.5;
          ctx.stroke();
        }

        particles.forEach(function (p) {
          p.t += p.speed;
          if (p.t > 1) p.t = 0;
          var pt = point(p.g.from, p.g.to, p.g.ctrl, p.t);
          ctx.beginPath();
          if (p.telem) {
            var id = p.g.edge.a + "-" + p.g.edge.b;
            var alert = id.indexOf("crusher") !== -1 || id.indexOf("sag") !== -1;
            ctx.fillStyle = alert ? "#FF1744" : "#00E5FF";
            ctx.fillRect(pt.x - 2.5, pt.y - 2.5, 5, 5);
          } else {
            ctx.fillStyle = p.g.edge.color;
            ctx.arc(pt.x, pt.y, p.g.edge.size, 0, Math.PI * 2);
            ctx.fill();
          }
        });

        rafId = requestAnimationFrame(frame);
      }

      if (rafId) cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(frame);
    }

    function stopCanvas() { if (rafId) { cancelAnimationFrame(rafId); rafId = null; } }

    /* Named inspect() rather than inspectNode(): the two source files defined
       inspectNode differently and this closure must not be mistaken for either. */
    function inspect(key) {
      var d = window.nodePRDData[key];
      if (!d) return;
      activeNode = key;
      Array.prototype.forEach.call(
        document.querySelectorAll(".schematic-node, .node-crusher-critical"),
        function (n) { n.classList.remove("node-active-selected"); }
      );
      var node = el("node-" + key);
      if (node) node.classList.add("node-active-selected");

      el("drawer-node-title").textContent = d.title;
      el("drawer-isa95-tag").textContent = d.tag;
      var hb = el("drawer-badge-health");
      hb.className = "badge " + d.healthClass;
      hb.textContent = d.health;
      el("drawer-swarm-id").textContent = d.swarm;
      el("drawer-swarm-coord").textContent = d.coord;
      el("drawer-solver-id").textContent = d.solver;
      el("drawer-formula-code").textContent = d.formula;
      el("drawer-sap-id").textContent = d.sap;
      el("drawer-telemetry-metrics").innerHTML = d.metrics.map(function (m) {
        return '<div class="drawer-keyval-row"><span class="drawer-key">' + esc(m.key) +
          ':</span><span class="drawer-val">' + esc(m.val) + "</span></div>";
      }).join("");
      el("schematic-inspector-drawer").classList.add("open");
    }

    function close() {
      el("schematic-inspector-drawer").classList.remove("open");
      Array.prototype.forEach.call(
        document.querySelectorAll(".schematic-node, .node-crusher-critical"),
        function (n) { n.classList.remove("node-active-selected"); }
      );
      activeNode = null;
    }

    function render() {
      el("s2-telemetry").innerHTML = TELEMETRY.map(function (t) {
        return '<div class="telemetry-card' + (t.critical ? " card-border-critical" : "") +
          '" data-node="' + t.node + '">' +
          '<div class="telemetry-card-header"><span' + (t.critical ? ' style="color:var(--m3-critical)"' : "") + ">" +
            esc(t.name) + '</span><span class="badge ' + t.badge + '">' + esc(t.badgeText) + "</span></div>" +
          '<div class="telemetry-values-row">' +
            '<div><div class="telemetry-stat-label">' + esc(t.a[0]) + "</div>" +
              '<div class="telemetry-stat-num' + (t.critical ? " critical-text" : "") + '">' + esc(t.a[1]) +
              ' <span class="telemetry-unit">' + esc(t.a[2]) + "</span></div></div>" +
            '<div><div class="telemetry-stat-label">' + esc(t.b[0]) + "</div>" +
              '<div class="telemetry-stat-num">' + esc(t.b[1]) +
              ' <span class="telemetry-unit">' + esc(t.b[2]) + "</span></div></div>" +
          "</div></div>";
      }).join("");

      Array.prototype.forEach.call(document.querySelectorAll("[data-node]"), function (n) {
        n.addEventListener("click", function () { inspect(n.getAttribute("data-node")); });
      });
      on("btn-close-drawer", "click", close);
      on("btn-drawer-dismiss", "click", close);
      on("btn-drawer-to-studio", "click", function () {
        var d = activeNode && window.nodePRDData[activeNode];
        close();
        App.go("ecosystem");
        if (d) S4.openDeepDive(d.coord.split(" ")[0]);
      });
    }

    return { render: render, enter: startCanvas, leave: stopCanvas, resize: startCanvas };
  })();

  /* ======================================================== S3 — Personas */
  var S3 = (function () {
    var ORDER = ["elena", "marcus", "dave", "sarah", "tariq", "priya", "chen", "claire"];
    var current = "elena";

    /* Named select() not selectPersona(): both source files defined
       selectPersona over different persona sets. */
    function select(key) {
      var p = window.personaPRDData[key];
      if (!p) return;
      current = key;

      Array.prototype.forEach.call(document.querySelectorAll(".persona-tab-btn"), function (b) {
        var on = b.getAttribute("data-persona") === key;
        b.classList.toggle("active", on);
        b.setAttribute("aria-selected", on ? "true" : "false");
      });

      /* The portrait is remote. Initials sit behind it so a blocked or slow
         image degrades to a legible monogram, never an empty grey tile. */
      var name = p.title.split(",")[0].trim();
      var initials = name.split(/\s+/).map(function (w) { return w.charAt(0); }).join("").slice(0, 2).toUpperCase();
      el("persona-hero-initials").textContent = initials;
      el("persona-hero-img").style.backgroundImage = p.avatar ? "url('" + p.avatar + "')" : "";
      el("persona-hero-caption").textContent = p.code.split("\u2022")[0].trim();

      el("persona-code-badge").textContent = p.code;
      el("persona-title-display").textContent = p.title;
      el("persona-mandate-display").textContent = p.mandate;
      el("persona-jtbd-display").textContent = p.jtbd;
      el("persona-broken-text").textContent = p.broken;
      el("persona-agentic-text").textContent = p.agentic;

      el("squad-list-container").innerHTML =
        '<div class="agent-cards-grid">' + p.squad.map(function (s) {
          var critic = s.auth.indexOf("CRITIC") !== -1;
          var registered = !!(window.agentCatalogData || {})[s.id];
          return '<div class="eco-agent-card' + (registered ? "" : " card-unregistered") + '"' +
            (registered ? ' data-agent="' + esc(s.id) + '"' : "") + ">" +
            "<div><div class=\"eco-agent-header\">" +
              '<span class="badge-agent-id">' + esc(s.id) + "</span>" +
              '<span class="badge ' + (critic ? "badge-critical" : "badge-optimal") + '">' + esc(s.auth) + "</span>" +
            "</div>" +
            '<div class="eco-agent-title">' + esc(s.name) + "</div>" +
            '<div class="eco-agent-desc">' + esc(s.desc) + "</div></div>" +
            (registered
              ? launchLinks((window.agentCatalogData || {})[s.id], true)
              : '<div class="agent-launch-row"><span class="agent-launch-chip chip-unregistered" ' +
                'title="This arbiter is named in the persona narrative but is not one of the registered agents.">' +
                "Not in the agent registry</span></div>") +
            '<div class="eco-agent-footer">' +
              '<span style="font-size:11px; font-weight:700; color:#137333;">' + esc(s.val) + "</span>" +
              (registered
                ? '<span style="font-size:11.5px; font-weight:700; color:var(--m3-primary);">Open deep dive &rsaquo;</span>'
                : '<span style="font-size:11.5px; font-weight:600; color:var(--m3-text-tertiary);">No card to open</span>') +
            "</div></div>";
        }).join("") + "</div>";

      bindLaunchRows(el("squad-list-container"));
      Array.prototype.forEach.call(el("squad-list-container").querySelectorAll("[data-agent]"), function (c) {
        c.addEventListener("click", function () {
          App.go("ecosystem");
          S4.openDeepDive(c.getAttribute("data-agent"));
        });
      });
    }

    function render() {
      el("persona-tabs").innerHTML = ORDER.map(function (k) {
        var p = window.personaPRDData[k];
        var label = p.code.split("•")[0].trim() + ": " + p.title.split(",")[0];
        var av = p.avatar ? '<span class="tab-avatar" style="background-image:url(\'' + p.avatar + '\');"></span>' : "";
        return '<button class="persona-tab-btn" role="tab" data-persona="' + k + '">' + av + esc(label) + "</button>";
      }).join("");

      Array.prototype.forEach.call(document.querySelectorAll(".persona-tab-btn"), function (b) {
        b.addEventListener("click", function () { select(b.getAttribute("data-persona")); });
      });

      on("btn-persona-studio", "click", function () {
        var p = window.personaPRDData[current];
        App.go("ecosystem");
        if (p) S4.openDeepDive(p.coordinatorId);
      });

      select("elena");
    }
    return { render: render };
  })();

  /* ======================================================= S4 — Ecosystem */
  var S4 = (function () {
    var TIERS = [
      { key: "L0", title: "Strategic Governance (NPV Optimization)", badge: "badge-primary",
        desc: "The apex node. Translates macro-economic directives into actionable mining constraints. Focuses on maximizing Net Present Value." },
      { key: "L2", title: "Domain Swarms (Specialized automation)", badge: "badge-critical",
        desc: "Coordinators, specialists and adversarial critics executing heuristics and predictive analysis across the pit-to-port value chain." },
      { key: "L3", title: "Physics Solvers (Deterministic truth)", badge: "badge-stable",
        desc: "The immutable ground truth. Hard-coded thermodynamic, kinetic and geospatial engines. Agents propose; solvers dispose." }
    ];
    var ids = [];
    var active = null;

    function agents() { return window.agentCatalogData || {}; }

    function cardHtml(a) {
      var critic = a.id.indexOf("CRITIC") !== -1;
      return '<div class="eco-agent-card" data-agent="' + esc(a.id) + '">' +
        '<div><div class="eco-agent-header">' +
          '<div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">' +
            '<span class="badge-agent-id">' + esc(a.id) + "</span>" +
            '<span class="badge badge-stable" style="font-size:9.5px;">' + esc(a.apqc) + "</span>" +
          "</div>" +
          '<span class="badge ' + (critic ? "badge-critical" : "badge-optimal") + '" style="font-size:9.5px;">' + esc(a.authority) + "</span>" +
        "</div>" +
        '<div class="eco-agent-title">' + esc(a.name) + "</div>" +
        '<div class="eco-agent-desc">' + esc(String(a.mechanism || "").slice(0, 115)) + "…</div></div>" +
        launchLinks(a, true) +
        '<div class="eco-agent-footer">' +
          '<span style="font-size:11px; font-weight:700; color:#137333;">' + esc(a.valueClass) + "</span>" +
          '<span style="font-size:11.5px; font-weight:700; color:var(--m3-primary);">Inspect &rsaquo;</span>' +
        "</div></div>";
    }

    function bindCards(root) {
      bindLaunchRows(root);
      Array.prototype.forEach.call(root.querySelectorAll("[data-agent]"), function (c) {
        c.addEventListener("click", function () { openDeepDive(c.getAttribute("data-agent")); });
      });
    }

    function renderTopology() {
      var all = agents();
      var counts = window.agentTierCounts || {};
      el("eco-hero-count").textContent = String(Object.keys(all).length);

      el("eco-filter-chips").innerHTML =
        '<button class="filter-chip active" data-tier="ALL">All (' + Object.keys(all).length + ")</button>" +
        TIERS.map(function (t) {
          return '<button class="filter-chip" data-tier="' + t.key + '">' + t.key + " (" + (counts[t.key] || 0) + ")</button>";
        }).join("");

      el("topology-stack").innerHTML = TIERS.map(function (t) {
        var members = Object.keys(all).map(function (k) { return all[k]; })
          .filter(function (a) { return a.tierKey === t.key; });

        var body;
        if (t.key === "L2") {
          var groups = {};
          members.forEach(function (a) {
            var g = a.id.slice(0, 3);
            (groups[g] = groups[g] || []).push(a);
          });
          body = Object.keys(groups).sort().map(function (g) {
            return '<div class="swarm-group-block">' +
              '<div class="swarm-group-title"><span>' + esc(g) + " Domain Swarm</span>" +
                '<span class="badge badge-primary" style="font-size:10px;">' + groups[g].length + " agents</span></div>" +
              '<div class="agent-cards-grid">' + groups[g].map(cardHtml).join("") + "</div></div>";
          }).join("");
        } else {
          body = '<div class="agent-cards-grid">' + members.map(cardHtml).join("") + "</div>";
        }

        return '<div class="topology-timeline-item" data-tier-row="' + t.key + '">' +
          '<div class="timeline-badge-node">' + t.key + "</div>" +
          '<div class="timeline-card-wrapper expanded" data-tier-card="' + t.key + '">' +
            '<div class="tier-header-bar" data-tier-toggle="' + t.key + '">' +
              '<div class="tier-title-cluster"><div class="tier-main-title">' + esc(t.title) + "</div>" +
                '<div class="tier-main-desc">' + esc(t.desc) + "</div></div>" +
              '<div class="tier-right-cluster">' +
                '<span class="badge ' + t.badge + '" style="font-size:11px;">' + members.length + " agents</span>" +
                '<svg class="tier-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>' +
              "</div></div>" +
            '<div class="tier-accordion-body">' + body + "</div>" +
          "</div></div>";
      }).join("");

      bindCards(el("topology-stack"));

      Array.prototype.forEach.call(document.querySelectorAll("[data-tier-toggle]"), function (h) {
        h.addEventListener("click", function () {
          var w = document.querySelector('[data-tier-card="' + h.getAttribute("data-tier-toggle") + '"]');
          if (w) w.classList.toggle("expanded");
        });
      });
      Array.prototype.forEach.call(document.querySelectorAll("[data-tier]"), function (chip) {
        chip.addEventListener("click", function () {
          var tier = chip.getAttribute("data-tier");
          Array.prototype.forEach.call(document.querySelectorAll("[data-tier]"), function (c) {
            c.classList.toggle("active", c === chip);
          });
          TIERS.forEach(function (t) {
            var row = document.querySelector('[data-tier-row="' + t.key + '"]');
            if (row) row.style.display = (tier === "ALL" || tier === t.key) ? "flex" : "none";
          });
        });
      });

      var sel = el("agent-quick-select");
      ids = Object.keys(all);
      sel.innerHTML = ids.map(function (k) {
        return '<option value="' + esc(k) + '">' + esc(k) + " — " + esc(all[k].name) + "</option>";
      }).join("");
    }

    function search(q) {
      q = (q || "").toLowerCase().trim();
      var results = el("eco-search-results"), stack = el("topology-stack");
      if (!q) { results.style.display = "none"; stack.style.display = "block"; return; }
      var all = agents();
      var hits = Object.keys(all).map(function (k) { return all[k]; }).filter(function (a) {
        return (a.id + " " + a.name + " " + a.apqc + " " + a.department + " " + a.persona + " " + a.mechanism)
          .toLowerCase().indexOf(q) !== -1;
      });
      stack.style.display = "none";
      results.style.display = "block";
      el("search-results-count").textContent = hits.length + " matching agents and solvers";
      el("search-cards-container").innerHTML = hits.length
        ? hits.map(cardHtml).join("")
        : '<div style="padding:20px; font-size:13px; color:var(--m3-text-secondary);">No matching agents. Try "geology", "crusher", "NPV", "D01" or "S05".</div>';
      bindCards(el("search-cards-container"));
    }

    function openDeepDive(agentId) {
      var all = agents();
      /* Falling back to ids[0] is right when nothing was asked for. When a
         specific ID was asked for and is not in the registry, showing a
         different agent's card under that ID is worse than showing nothing. */
      var a = agentId ? all[agentId] : all[ids[0]];
      if (!a) return;
      active = a.id;

      el("dd-badge-id").textContent = a.id;
      el("dd-badge-apqc").textContent = a.apqc;
      el("dd-badge-status").textContent = a.hitl ? "HUMAN APPROVAL REQUIRED" : "ADVISORY";
      el("dd-title").textContent = a.name;
      el("dd-process").textContent = "Persona: " + a.persona + " · " + a.department;
      el("dd-value-amount").textContent = a.valueClass;
      el("dd-value-period").textContent = a.hitl ? "Dual-key human release required" : "Advisory output, human executes";
      el("dd-authority-text").textContent =
        "Authority " + a.authority + ". " +
        (a.hitl
          ? "This agent cannot release its own action: a named human holds the key."
          : "Advisory by default — every recommendation lands with a named human.") +
        " Endpoint: " + a.endpoint + ".";
      el("dd-mechanism-text").textContent = a.mechanism || "—";
      el("dd-code-lang").textContent = a.model || "";
      el("dd-code-box").textContent = a.governingEquation || "—";
      el("dd-btn-urn").setAttribute("data-urn",
        "urn:agent:your-gcp-project-id:us-central1:" + a.id.toLowerCase());

      // The recording and its sales script replace the simulated terminal:
      // a real agent answering its real scenario beats a fake one every time.
      var asset = (window.SALES_ASSETS || {})[a.id];
      var recCard = el("dd-recording-card");
      if (recCard) {
        if (asset && asset.video) {
          recCard.style.display = "";
          var v = el("dd-video");
          if (v.getAttribute("src") !== asset.video) {
            v.setAttribute("src", asset.video);
            v.load();
          }
          el("dd-sales-situation").textContent = asset.situation || "";
          el("dd-sales-action").textContent = asset.action || "";
          el("dd-sales-logic").textContent = asset.logic || "";
        } else {
          recCard.style.display = "none";
        }
      }

      el("dd-provenance-list").innerHTML = (a.provenance || []).length
        ? a.provenance.map(function (p) {
            return '<div class="prov-item-row"><div class="prov-left">' +
              '<span class="prov-dot ' + (p.type === "SAP" ? "prov-dot-amber" : "prov-dot-blue") + '"></span>' +
              '<span>' + esc(p.name) + "</span></div>" +
              '<span class="prov-badge">' + esc(p.type) + "</span></div>";
          }).join("")
        : '<div style="font-size:11.5px; color:var(--m3-text-secondary);">No grounding tables declared.</div>';

      /* Business logic, in the language of the person who signs the cheque.
         Every line is a catalogue field put into plain English by the
         generator -- see build_frontend_data.py. Nothing is composed here. */
      var b = a.business || {};
      el("dd-biz-stake").textContent = b.boardStake || "";
      el("dd-biz-owns").textContent = b.owns || "";
      el("dd-biz-answers").textContent = b.answersTo || "";
      el("dd-biz-pl").textContent = b.plMove || "";
      el("dd-biz-cannot").textContent = b.cannot || "";
      el("dd-biz-failure").textContent = b.onFailure || "";

      el("dd-flow").innerHTML = (a.flow || []).map(function (st, i) {
        return '<div class="flow-stage" data-stage="' + esc(st.key) + '" style="--motion-i:' + i + ';">' +
          '<div class="flow-rail"><div class="flow-marker">' + esc(st.label.charAt(0)) + "</div>" +
          '<div class="flow-connector"></div></div>' +
          '<div class="flow-body">' +
            '<div class="flow-label">' + esc(st.label) + "</div>" +
            '<div class="flow-value">' + esc(st.value) + "</div>" +
            /* Two registers per stage, deliberately: what happens, then why a
               person who does not read SQL should care. The business line is
               generated from the same fields as the mechanism, never written
               about an agent one at a time. */
            (st.business ? '<div class="flow-business">' + esc(st.business) + "</div>" : "") +
            '<div class="flow-detail">' + esc(st.detail) + "</div>" +
          "</div></div>";
      }).join("");
      /* Runs on each deep dive because each one is a different decision --
         but not when the tab is merely revisited. */
      playOnce(el("dd-flow"), (a.flow || []).length, 45, 240);

      var gemini = a.geminiUrl || window.geminiEnterpriseUrl || "";
      var gemLink = el("dd-link-gemini");
      gemLink.href = gemini || "#";
      gemLink.style.display = gemini ? "" : "none";

      var invLink = el("dd-link-invoke");
      invLink.href = a.invokeUrl || "#";
      invLink.style.display = a.invokeUrl ? "" : "none";
      el("dd-invoke-label").textContent = "Invoke " + a.id + " directly";

      /* Said out loud rather than left for someone to discover: the Gemini
         Enterprise button opens the workspace all 101 agents share, so it is
         not by itself a link to THIS agent. The endpoint button is. */
      el("dd-launch-note").textContent = a.urn
        ? "Gemini Enterprise opens the shared workspace. The endpoint button addresses this agent alone — " + a.urn
        : "Gemini Enterprise opens the shared workspace for all agents in this estate.";

      el("agent-quick-select").value = a.id;
      el("view-ecosystem-overview").classList.remove("active");
      el("view-agent-deepdive").classList.add("active");
      window.scrollTo({ top: 0, behavior: "smooth" });
    }

    function backToOverview() {
      el("view-agent-deepdive").classList.remove("active");
      el("view-ecosystem-overview").classList.add("active");
      window.scrollTo({ top: 0, behavior: "smooth" });
    }

    function cycle(step) {
      var i = ids.indexOf(active);
      if (i === -1) i = 0;
      openDeepDive(ids[(i + step + ids.length) % ids.length]);
    }

    function render() {
      renderTopology();
      on("eco-search-input", "input", function (e) { search(e.target.value); });
      on("btn-clear-search", "click", function () { el("eco-search-input").value = ""; search(""); });
      on("btn-back-topology", "click", backToOverview);
      on("btn-agent-prev", "click", function () { cycle(-1); });
      on("btn-agent-next", "click", function () { cycle(1); });
      on("agent-quick-select", "change", function (e) { openDeepDive(e.target.value); });
      on("dd-btn-urn", "click", function (e) {
        Clip.copy(e.currentTarget.getAttribute("data-urn"), e.currentTarget);
      });
      on("btn-lineage-trace", "click", function () {
        var a = agents()[active];
        el("lineage-modal-title").textContent = "Lineage: " + (a ? a.id : "");
        el("lineage-steps").innerHTML = [
          ["1. Physical sensors", "OT INGRESS"], ["2. Air-gap diode", "IEC-62443 SL4"],
          ["3. BigQuery grounding", "BIGQUERY"], ["4. Swarm + solver", "ZERO-HALLUCINATION"],
          ["5. Staged payload", "DUAL-KEY"]
        ].map(function (s, i, arr) {
          return '<div style="background:var(--m3-surface-subtle); padding:10px 14px; border-radius:4px; display:flex; justify-content:space-between; gap:10px;">' +
            "<span><strong>" + esc(s[0]) + "</strong></span>" +
            '<span class="badge badge-primary">' + esc(s[1]) + "</span></div>" +
            (i < arr.length - 1 ? '<div style="text-align:center; color:var(--m3-primary);">&darr;</div>' : "");
        }).join("");
        el("modal-lineage").classList.add("active");
      });
      on("btn-close-sim", "click", function () { el("modal-sim").classList.remove("active"); });
      on("btn-done-sim", "click", function () { el("modal-sim").classList.remove("active"); });
      on("btn-close-lineage", "click", function () { el("modal-lineage").classList.remove("active"); });
      on("btn-done-lineage", "click", function () { el("modal-lineage").classList.remove("active"); });

      openDeepDive(ids[0]);
      backToOverview();
    }

    return { render: render, openDeepDive: openDeepDive, backToOverview: backToOverview };
  })();

  /* =========================================== S5 — Logical & data architecture
   * Two halves. The upper half is the logical stack: eight layers between the
   * screen a person looks at and the byte that answers them, with the request
   * descending and evidence returning. The lower half is the data estate as an
   * interactive graph, drawn from apps/frontend/data-graph.js -- real tables,
   * real row counts, real shared join keys, generated against live BigQuery.
   *
   * The graph runs a force layout to settlement and then STOPS. It is not an
   * animation: an architecture diagram that never stops moving is harder to
   * read, and a permanent rAF loop on an off-screen pane burns frames nobody
   * sees. Dragging re-heats it for a few steps and lets it settle again.
   * ======================================================================== */
  var S5 = (function () {
    /* One colour per layer, all of them already in the design language --
       nothing new is introduced for this chart. */
    var LAYER_COLOR = {
      operational: "#1A73E8",
      semantic:    "#3F51B5",
      corpus:      "#80868B",
      simulation:  "#F59E0B",
      control:     "#D93025",
      serving:     "#1E8E3E",
      model:       "#137333"
    };
    var SVG_NS = "http://www.w3.org/2000/svg";

    var nodes = [], edges = [], adjacency = {}, byId = {};
    var svg = null, gEdges = null, gNodes = null;
    var width = 900, height = 520;
    var selectedId = null, hoveredId = null;
    var domainFilter = "ALL", hiddenLayers = {};
    var laidOut = false, dragging = null, pending = null, swallowNextClick = false;
    var stackAnimated = false;

    /* ---------------------------------------------------- logical stack */

    /* Chip labels carry {tokens} so a count on the architecture screen is read
       from the same data the count describes. A token with no value renders as
       an em dash rather than leaking its braces onto the page. */
    function tokens() {
      var cat = window.agentCatalogData || {};
      var list = Object.keys(cat).map(function (k) { return cat[k]; });
      var byPattern = function (pat) {
        return list.filter(function (a) { return a.pattern === pat; }).length;
      };
      var g = window.dataGraph || { nodes: [], meta: {} };
      var meta = g.meta || {};
      var n = function (v) { return typeof v === "number" ? v.toLocaleString() : v; };
      return {
        personas: Object.keys(window.personaPRDData || {}).length,
        agents: list.length,
        coordinators: byPattern("A_COORDINATOR"),
        specialists: byPattern("A_SPECIALIST"),
        critics: byPattern("A_CRITIC"),
        solvers: byPattern("B_DEEP"),
        tables: meta.tableCount,
        columns: meta.columnCount,
        rows: n(meta.rowCount),
        edges: meta.edgeCount,
        models: (g.nodes || []).filter(function (x) { return x.layer === "model"; }).length
      };
    }

    function fill(text, t) {
      return String(text).replace(/\{(\w+)\}/g, function (_, key) {
        var v = t[key];
        return (v === undefined || v === null || v === "") ? "—" : String(v);
      });
    }

    function renderStack() {
      var model = window.architectureModel;
      if (!model) return;
      var t = tokens();

      el("arch-stack").innerHTML = model.layers.map(function (layer, i) {
        /* --motion-i drives the stagger. Blocks and seams alternate, so the
           index counts both and the stack assembles in document order. */
        var block =
          '<div class="arch-block" data-layer="' + esc(layer.key) + '" style="--motion-i:' + (i * 2) + ';">' +
            '<div class="arch-block-band">' + esc(layer.band) + "</div>" +
            "<div>" +
              '<div class="arch-block-name">' + esc(layer.name) + "</div>" +
              '<div class="arch-block-blurb">' + esc(fill(layer.blurb, t)) + "</div>" +
              '<div class="arch-chip-row">' + layer.chips.map(function (c) {
                return '<span class="arch-chip">' + esc(fill(c, t)) + "</span>";
              }).join("") + "</div>" +
            "</div>" +
            '<div class="arch-traffic">' +
              '<div class="arch-traffic-line arch-traffic-down"><span class="arch-traffic-arrow">&darr;</span><span>' + esc(layer.request) + "</span></div>" +
              '<div class="arch-traffic-line arch-traffic-up"><span class="arch-traffic-arrow">&uarr;</span><span>' + esc(layer.evidence) + "</span></div>" +
            "</div>" +
          "</div>";
        var seam = i < model.layers.length - 1
          ? '<div class="arch-seam" style="--motion-i:' + (i * 2 + 1) + ';">' +
              '<span class="arch-seam-down">&#9660;</span><span class="arch-seam-up">&#9650;</span></div>'
          : "";
        return block + seam;
      }).join("");

      el("arch-controls").innerHTML = model.controls.map(function (c) {
        return '<div class="arch-control-card">' +
          '<div class="arch-control-name">' + esc(c.name) + "</div>" +
          '<div class="arch-control-rule">' + esc(c.rule) + "</div>" +
          '<div class="arch-control-spans">' + esc(c.spans) + "</div>" +
        "</div>";
      }).join("");
    }

    /* ------------------------------------------------------- data graph */

    function buildGraph() {
      var g = window.dataGraph;
      if (!g) return false;

      byId = {};
      /* Deterministic seeding: a golden-angle spiral, not a random scatter, so
         the same dataset draws the same picture on every reload. */
      var golden = Math.PI * (3 - Math.sqrt(5));
      nodes = g.nodes.map(function (n, i) {
        var r = 30 + 190 * Math.sqrt(i / Math.max(1, g.nodes.length));
        var node = {
          id: n.id, layer: n.layer, layerLabel: n.layerLabel,
          domain: n.domain, domainLabel: n.domainLabel,
          rows: n.rows, columns: n.columns, columnCount: n.columnCount,
          readBy: n.readBy || [],
          radius: 4.5 + (n.weight || 0) * 2.3,
          x: r * Math.cos(i * golden), y: r * Math.sin(i * golden),
          vx: 0, vy: 0, degree: 0
        };
        byId[n.id] = node;
        return node;
      });

      adjacency = {};
      edges = g.edges.filter(function (e) { return byId[e.source] && byId[e.target]; })
        .map(function (e) {
          byId[e.source].degree++; byId[e.target].degree++;
          (adjacency[e.source] = adjacency[e.source] || []).push({ other: e.target, keys: e.keys });
          (adjacency[e.target] = adjacency[e.target] || []).push({ other: e.source, keys: e.keys });
          return { s: byId[e.source], t: byId[e.target], keys: e.keys, weight: e.weight };
        });
      return true;
    }

    /* Domain centroids sit on a circle so each part of the value chain forms a
       visible neighbourhood; the join edges then show how much those
       neighbourhoods actually depend on one another. */
    function domainAnchors() {
      var g = window.dataGraph || { domains: [] };
      var list = g.domains || [];
      var anchors = {};
      var rx = width * 0.34, ry = height * 0.36;
      list.forEach(function (d, i) {
        var a = (i / Math.max(1, list.length)) * Math.PI * 2 - Math.PI / 2;
        anchors[d.key] = { x: width / 2 + rx * Math.cos(a), y: height / 2 + ry * Math.sin(a) };
      });
      return anchors;
    }

    function step(anchors, alpha) {
      var i, j, a, b, dx, dy, d2, d, f;

      for (i = 0; i < nodes.length; i++) {
        for (j = i + 1; j < nodes.length; j++) {
          a = nodes[i]; b = nodes[j];
          dx = b.x - a.x; dy = b.y - a.y;
          d2 = dx * dx + dy * dy;
          if (d2 < 1) { d2 = 1; dx = (i - j) * 0.5; dy = 0.5; }
          f = 3000 / d2;
          d = Math.sqrt(d2);
          a.vx -= (dx / d) * f; a.vy -= (dy / d) * f;
          b.vx += (dx / d) * f; b.vy += (dy / d) * f;
        }
      }

      edges.forEach(function (e) {
        dx = e.t.x - e.s.x; dy = e.t.y - e.s.y;
        d = Math.sqrt(dx * dx + dy * dy) || 1;
        f = (d - 92) * 0.030;
        e.s.vx += (dx / d) * f; e.s.vy += (dy / d) * f;
        e.t.vx -= (dx / d) * f; e.t.vy -= (dy / d) * f;
      });

      nodes.forEach(function (n) {
        var anchor = anchors[n.domain] || { x: width / 2, y: height / 2 };
        n.vx += (anchor.x - n.x) * 0.018;
        n.vy += (anchor.y - n.y) * 0.018;
        if (dragging === n) { n.vx = 0; n.vy = 0; return; }
        n.x += n.vx * alpha; n.y += n.vy * alpha;
        n.vx *= 0.82; n.vy *= 0.82;
        var pad = n.radius + 14;
        n.x = Math.max(pad, Math.min(width - pad, n.x));
        n.y = Math.max(pad, Math.min(height - pad, n.y));
      });
    }

    function layout(iterations) {
      var anchors = domainAnchors();
      for (var k = 0; k < iterations; k++) {
        step(anchors, 0.55 * (1 - k / iterations) + 0.08);
      }
    }

    function draw() {
      if (!svg) return;
      while (gEdges.firstChild) gEdges.removeChild(gEdges.firstChild);
      while (gNodes.firstChild) gNodes.removeChild(gNodes.firstChild);

      edges.forEach(function (e) {
        var line = document.createElementNS(SVG_NS, "line");
        line.setAttribute("class", "dg-edge");
        line.setAttribute("stroke-width", String(Math.min(3, e.weight)));
        line.setAttribute("x1", e.s.x); line.setAttribute("y1", e.s.y);
        line.setAttribute("x2", e.t.x); line.setAttribute("y2", e.t.y);
        e.node = line;
        gEdges.appendChild(line);
      });

      nodes.forEach(function (n) {
        var g = document.createElementNS(SVG_NS, "g");
        g.setAttribute("class", "dg-node");
        g.setAttribute("transform", "translate(" + n.x + "," + n.y + ")");

        var c = document.createElementNS(SVG_NS, "circle");
        c.setAttribute("r", String(n.radius));
        c.setAttribute("fill", LAYER_COLOR[n.layer] || "#80868B");
        g.appendChild(c);

        var label = document.createElementNS(SVG_NS, "text");
        label.setAttribute("y", String(n.radius + 8));
        label.setAttribute("text-anchor", "middle");
        label.textContent = n.id;
        if (!(n.degree >= 4 || n.rows >= 900)) g.classList.add("dg-quiet");
        g.appendChild(label);

        var title = document.createElementNS(SVG_NS, "title");
        title.textContent = n.id + " — " + n.layerLabel + " · " + n.domainLabel +
          " · " + n.rows.toLocaleString() + " rows · " + n.columnCount + " columns";
        g.appendChild(title);

        g.addEventListener("mouseenter", function () { hoveredId = n.id; applyEmphasis(); });
        g.addEventListener("mouseleave", function () { hoveredId = null; applyEmphasis(); });
        g.addEventListener("pointerdown", function (ev) {
          ev.preventDefault();
          pending = { node: n, x: ev.clientX, y: ev.clientY, pointerId: ev.pointerId };
        });

        n.node = g;
        gNodes.appendChild(g);
      });

      applyEmphasis();
    }

    function reposition() {
      edges.forEach(function (e) {
        if (!e.node) return;
        e.node.setAttribute("x1", e.s.x); e.node.setAttribute("y1", e.s.y);
        e.node.setAttribute("x2", e.t.x); e.node.setAttribute("y2", e.t.y);
      });
      nodes.forEach(function (n) {
        if (n.node) n.node.setAttribute("transform", "translate(" + n.x + "," + n.y + ")");
      });
    }

    function isFiltered(n) {
      if (hiddenLayers[n.layer]) return true;
      if (domainFilter !== "ALL" && n.domain !== domainFilter) return true;
      return false;
    }

    /* Filtering dims rather than removes. Pulling nodes out would relayout the
       whole picture on every chip click, and the shape of the estate is the
       thing the chart is for. */
    function applyEmphasis() {
      var focus = hoveredId || selectedId;
      if (focus && byId[focus] && isFiltered(byId[focus])) focus = null;
      var near = {};
      if (focus) {
        near[focus] = true;
        (adjacency[focus] || []).forEach(function (a) { near[a.other] = true; });
      }
      nodes.forEach(function (n) {
        if (!n.node) return;
        var dim = isFiltered(n) || (focus && !near[n.id]);
        n.node.classList.toggle("dg-dim", !!dim);
        n.node.classList.toggle("dg-selected", n.id === selectedId);
        n.node.classList.toggle("dg-named", !!(focus && near[n.id]));
      });
      edges.forEach(function (e) {
        if (!e.node) return;
        var visible = !isFiltered(e.s) && !isFiltered(e.t);
        var touches = focus && (e.s.id === focus || e.t.id === focus);
        e.node.classList.toggle("dg-dim", !visible || (focus && !touches));
        e.node.classList.toggle("dg-hot", !!(visible && touches));
      });
    }

    function selectNode(id) {
      selectedId = (selectedId === id) ? null : id;
      applyEmphasis();
      renderDetail(selectedId ? byId[selectedId] : null);
    }

    function renderDetail(n) {
      var box = el("datagraph-detail");
      if (!n) {
        var t = tokens();
        box.innerHTML = '<div class="dg-detail-empty"><strong>' + esc(String(t.tables)) +
          " objects, " + esc(String(t.edges)) + " join paths.</strong><br><br>" +
          "Each circle is a table, sized by row count and coloured by architectural layer. " +
          "A line means the two tables share a key-shaped column, so the join is derived from " +
          "the schema rather than asserted.<br><br>Click any table to read its columns and its joins.</div>";
        return;
      }
      var joins = (adjacency[n.id] || []).slice().sort(function (a, b) {
        return a.other < b.other ? -1 : 1;
      });
      box.innerHTML =
        '<div class="dg-detail-title">' + esc(n.id) + "</div>" +
        '<div class="dg-detail-meta">' +
          '<span class="badge" style="background:' + (LAYER_COLOR[n.layer] || "#80868B") + '1A; color:' + (LAYER_COLOR[n.layer] || "#80868B") + ';">' + esc(n.layerLabel) + "</span>" +
          '<span class="badge badge-stable">' + esc(n.domainLabel) + "</span>" +
        "</div>" +
        '<div class="dg-detail-stats">' +
          '<div class="dg-detail-stat"><div class="dg-detail-stat-value">' + n.rows.toLocaleString() + '</div><div class="dg-detail-stat-label">Rows</div></div>' +
          '<div class="dg-detail-stat"><div class="dg-detail-stat-value">' + n.columnCount + '</div><div class="dg-detail-stat-label">Columns</div></div>' +
          '<div class="dg-detail-stat"><div class="dg-detail-stat-value">' + joins.length + '</div><div class="dg-detail-stat-label">Join paths</div></div>' +
          '<div class="dg-detail-stat"><div class="dg-detail-stat-value">' + n.readBy.length + '</div><div class="dg-detail-stat-label">Declared by</div></div>' +
        "</div>" +
        (joins.length
          ? '<div class="dg-detail-section-label">Joins to</div>' + joins.map(function (j) {
              return '<div class="dg-join-row" data-jump="' + esc(j.other) + '">' + esc(j.other) +
                '<div class="dg-join-keys">on ' + esc(j.keys.join(", ")) + "</div></div>";
            }).join("")
          : '<div class="dg-detail-section-label">Joins to</div><div class="dg-detail-empty">No shared key columns. This table stands alone in the schema.</div>') +
        '<div class="dg-detail-section-label">Columns</div>' +
        n.columns.map(function (c) {
          return '<div class="dg-col-row"><span>' + esc(c.name) + '</span><span class="dg-col-type">' + esc(c.type) + "</span></div>";
        }).join("") +
        (n.readBy.length
          ? '<div class="dg-detail-section-label">Declared by</div><div class="dg-detail-empty" style="font-family:var(--font-mono); font-size:10.5px;">' + esc(n.readBy.join(", ")) + "</div>"
          : "");

      Array.prototype.forEach.call(box.querySelectorAll("[data-jump]"), function (row) {
        row.addEventListener("click", function () { selectNode(row.getAttribute("data-jump")); });
      });
    }

    function renderChrome() {
      var g = window.dataGraph;
      if (!g) return;
      var m = g.meta || {};

      el("datagraph-subtitle").textContent =
        "Every table in " + m.project + "." + m.dataset + ", sized by row count and joined on shared keys. " +
        m.excludedCount + " snapshot and probe copies are set aside so the architecture reads as the architecture.";

      el("datagraph-stats").innerHTML = [
        { v: m.tableCount, l: "Objects" },
        { v: m.columnCount, l: "Columns" },
        { v: (m.rowCount || 0).toLocaleString(), l: "Rows" },
        { v: m.edgeCount, l: "Join paths" }
      ].map(function (s) {
        return '<div><div class="datagraph-stat-value">' + esc(String(s.v)) + '</div>' +
          '<div class="datagraph-stat-label">' + esc(s.l) + "</div></div>";
      }).join("");

      el("datagraph-toolbar").innerHTML =
        '<button class="filter-chip active" data-domain="ALL">All domains</button>' +
        (g.domains || []).map(function (d) {
          var count = g.nodes.filter(function (n) { return n.domain === d.key; }).length;
          return '<button class="filter-chip" data-domain="' + esc(d.key) + '">' + esc(d.label) + " (" + count + ")</button>";
        }).join("");

      Array.prototype.forEach.call(el("datagraph-toolbar").querySelectorAll("[data-domain]"), function (chip) {
        chip.addEventListener("click", function () {
          domainFilter = chip.getAttribute("data-domain");
          Array.prototype.forEach.call(el("datagraph-toolbar").querySelectorAll("[data-domain]"), function (c) {
            c.classList.toggle("active", c === chip);
          });
          if (selectedId && byId[selectedId] && isFiltered(byId[selectedId])) {
            selectedId = null;
            renderDetail(null);
          }
          applyEmphasis();
        });
      });

      el("datagraph-legend").innerHTML = (g.layers || []).map(function (l) {
        var count = g.nodes.filter(function (n) { return n.layer === l.key; }).length;
        return '<div class="dg-legend-item" data-layer-toggle="' + esc(l.key) + '">' +
          '<span class="dg-legend-dot" style="background:' + (LAYER_COLOR[l.key] || "#80868B") + ';"></span>' +
          esc(l.label) + " (" + count + ")</div>";
      }).join("");

      Array.prototype.forEach.call(el("datagraph-legend").querySelectorAll("[data-layer-toggle]"), function (item) {
        item.addEventListener("click", function () {
          var key = item.getAttribute("data-layer-toggle");
          hiddenLayers[key] = !hiddenLayers[key];
          item.classList.toggle("dg-legend-off", !!hiddenLayers[key]);
          if (selectedId && byId[selectedId] && isFiltered(byId[selectedId])) {
            selectedId = null;
            renderDetail(null);
          }
          applyEmphasis();
        });
      });
    }

    function bindSurface() {
      svg = el("datagraph-svg");
      if (!svg) return;
      gEdges = document.createElementNS(SVG_NS, "g");
      gNodes = document.createElementNS(SVG_NS, "g");
      svg.appendChild(gEdges);
      svg.appendChild(gNodes);

      svg.addEventListener("click", function () {
        if (swallowNextClick) { swallowNextClick = false; return; }
        selectNode(null);
      });

      /* 4px of travel separates a click from a drag. Below it the press is a
         request to inspect the table; above it, to move it. */
      var DRAG_THRESHOLD = 4;

      svg.addEventListener("pointermove", function (ev) {
        if (pending && !dragging) {
          if (Math.abs(ev.clientX - pending.x) + Math.abs(ev.clientY - pending.y) < DRAG_THRESHOLD) return;
          dragging = pending.node;
          svg.classList.add("is-dragging");
          if (svg.setPointerCapture) { try { svg.setPointerCapture(ev.pointerId); } catch (e) { /* no capture */ } }
        }
        if (!dragging) return;
        var r = svg.getBoundingClientRect();
        dragging.x = (ev.clientX - r.left) * (width / r.width);
        dragging.y = (ev.clientY - r.top) * (height / r.height);
        /* A few relaxation steps per move so neighbours follow the dragged
           table instead of the line snapping across a static picture. */
        var anchors = domainAnchors();
        for (var i = 0; i < 3; i++) step(anchors, 0.25);
        reposition();
      });

      var release = function (ev) {
        if (!pending && !dragging) return;
        var wasDragging = !!dragging;
        var node = dragging || (pending && pending.node);
        dragging = null;
        pending = null;
        svg.classList.remove("is-dragging");
        if (ev && ev.pointerId !== undefined && svg.hasPointerCapture && svg.hasPointerCapture(ev.pointerId)) {
          svg.releasePointerCapture(ev.pointerId);
        }
        if (wasDragging) {
          var anchors = domainAnchors();
          for (var i = 0; i < 40; i++) step(anchors, 0.2);
          reposition();
        } else if (node) {
          selectNode(node.id);
        }
        /* Either way a click event follows this pointerup and would reach the
           SVG's deselect handler. */
        swallowNextClick = true;
      };
      svg.addEventListener("pointerup", release);
      svg.addEventListener("pointercancel", release);
    }

    function measure() {
      if (!svg) return;
      var r = svg.getBoundingClientRect();
      width = Math.max(320, Math.round(r.width) || 900);
      height = Math.max(360, Math.round(r.height) || 520);
      svg.setAttribute("viewBox", "0 0 " + width + " " + height);
      svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    }

    function enter() {
      /* The stack assembles on first sight only. Replaying it on every tab
         click would be decoration rather than explanation. */
      if (!stackAnimated) {
        stackAnimated = true;
        var stack = el("arch-stack");
        var items = stack ? stack.children.length : 0;
        playOnce(stack, items, 38, 280);
      }

      if (!svg || laidOut) return;
      measure();
      if (!nodes.length) return;
      layout(420);
      draw();
      playOnce(svg, 0, 0, 320);
      laidOut = true;
    }

    function resize() {
      if (!laidOut) return;
      var before = width;
      measure();
      if (Math.abs(before - width) < 24) return;
      layout(120);
      reposition();
    }

    function render() {
      renderStack();

      if (buildGraph()) {
        renderChrome();
        bindSurface();
        renderDetail(null);
      } else {
        el("datagraph-detail").innerHTML =
          '<div class="dg-detail-empty">The data graph has not been generated. ' +
          "Run <code>python scripts/build_data_graph.py</code> to build it from the live dataset.</div>";
      }

      /* Stamped at render, not hard-coded: a frozen date on an architecture
         screen reads as a stale audit, which is worse than no date at all. */
      var now = new Date();
      el("arch-audit-line").innerHTML =
        "LAST RENDER: " + now.toISOString().slice(0, 16).replace("T", " ") + "Z<br>POSTURE: ENFORCED";
    }

    return { render: render, enter: enter, resize: resize };
  })();

  /* ============================================================== ROUTER */
  var App = {
    go: function (screen) {
      if (LEGACY_SCREEN[screen]) screen = LEGACY_SCREEN[screen];
      if (SCREENS.indexOf(screen) === -1) screen = "macro";

      SCREENS.forEach(function (s) {
        var pane = el("pane-" + s), tab = el("tab-" + s);
        if (pane) pane.classList.toggle("active", s === screen);
        if (tab) {
          tab.classList.toggle("active", s === screen);
          tab.setAttribute("aria-selected", s === screen ? "true" : "false");
        }
      });

      /* Only Screen 2 animates. Leaving its rAF loop running while another
         screen is showing burns a frame budget on a canvas nobody can see, so
         the router starts and stops it explicitly rather than letting it idle. */
      if (screen === "schematic") { setTimeout(S2.enter, 50); } else { S2.leave(); }

      /* Screen 5's graph is laid out on first sight, not at init: a hidden pane
         measures zero wide, and a force layout against a zero-width box puts
         every node in the same place. */
      if (screen === "architecture") { setTimeout(S5.enter, 50); }

      try {
        if (window.history && window.history.pushState) {
          window.history.pushState(null, "", "#" + screen);
        }
      } catch (e) { /* restricted embedding context */ }

      window.scrollTo({ top: 0, behavior: "smooth" });
    },

    init: function () {
      S1.render(); S2.render(); S3.render(); S4.render(); S5.render();

      SCREENS.forEach(function (s) {
        var tab = el("tab-" + s);
        if (tab) tab.addEventListener("click", function (e) { e.preventDefault(); App.go(s); });
      });

      on("btn-header-search", "click", function () {
        App.go("ecosystem");
        var input = el("eco-search-input");
        if (input) input.focus();
      });

      window.addEventListener("hashchange", function () {
        App.go((window.location.hash || "").replace(/^#/, ""));
      });
      window.addEventListener("resize", function () {
        if (el("pane-schematic").classList.contains("active")) S2.resize();
        if (el("pane-architecture").classList.contains("active")) S5.resize();
      });

      var initial = (window.location.hash || "").replace(/^#/, "");
      if (LEGACY_SCREEN[initial]) initial = LEGACY_SCREEN[initial];
      App.go(SCREENS.indexOf(initial) !== -1 ? initial : "macro");
    }
  };

  window.App = App;
  document.addEventListener("DOMContentLoaded", App.init);
})();


/* --------------------------------------------------- data insights (BQ) */
/* Self-contained: runs outside the app IIFE, so it owns its helpers. */
(function renderBqInsights() {
  var grid = document.getElementById("bq-insights-grid");
  if (!grid || !window.BQ_INSIGHTS) return;
  var esc = function (t) {
    var d = document.createElement("div");
    d.textContent = String(t == null ? "" : t);
    return d.innerHTML;
  };
  grid.innerHTML = window.BQ_INSIGHTS.map(function (c) {
    return '<div class="bq-insight-card">' +
      '<div class="bq-insight-meta"><span class="bq-insight-kind">' + esc(c.kind) + '</span>' +
      '<span class="bq-insight-impact">' + esc(c.impact) + '</span></div>' +
      '<div class="bq-insight-title">' + esc(c.title) + '</div>' +
      '<div class="bq-insight-question">\u201c' + esc(c.question) + '\u201d</div>' +
      '<div class="bq-insight-finding">' + esc(c.finding) + '</div>' +
      (c.video ? '<video controls preload="metadata" playsinline src="' + esc(c.video) + '"></video>' : '') +
      '</div>';
  }).join("");
})();
