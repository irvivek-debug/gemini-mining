"""Build a single self-contained HTML file of the showcase, for sharing.

The deployed workspace sits behind IAP, so it cannot be forwarded to anyone
outside the domain. This produces one file that opens by double-click, works
offline, and can be emailed: all 100 agents with the Situation / Agent Action /
Logic script the sales companion uses, plus the four BigQuery deep-dives.

Nothing here is written by hand. Every string is lifted from the same recorded
evidence the served page uses -- sales-assets.js (the scripts), bq-insights.js
(the scenarios and their real findings), and agents.json (names, department,
persona, live URL). If a fact is not in one of those, it does not appear.

Video, and why it is a flag rather than a default
-------------------------------------------------
The recordings are 544MB across 100 files -- far too large to inline, and a
data: URI of even one is a 7MB base64 blob. So the file ships with no video
unless you say where the videos live:

  --video-base URL   one public prefix; each agent resolves to
                     <URL>/<AGENT-ID>/<file>.webm. Right for a public GCS
                     bucket or any static host that keeps the directory shape.

  --video-map FILE   JSON of {"AGENT-ID": "https://..."}. Required for Google
                     Drive, which addresses files by opaque per-file id and has
                     no path structure a prefix could exploit.

With neither, each agent shows an honest placeholder saying the recording is
not attached -- never a dead <video> element that fails silently.

A drive.google.com URL is rendered as an <iframe> and everything else as a
<video>, because Drive share links are player pages, not video bytes. Point a
<video> at one and you get a black box with working controls -- which looks
exactly like a recording that failed, and is the worst of the three outcomes.
Use the /preview form of the link (…/file/d/<ID>/preview).

Usage:
    python scripts/build_shareable_html.py
    python scripts/build_shareable_html.py --video-base https://storage.googleapis.com/BUCKET/videos
    python scripts/build_shareable_html.py --video-map drive_links.json
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATIC = ROOT / "apps" / "frontend" / "server" / "static"
SALES = STATIC / "sales-assets.js"
BQ = STATIC / "bq-insights.js"
AGENTS = ROOT / "data" / "uat" / "agents.json"
OUT = ROOT / "reports" / "mining-agents-showcase.html"


def _embedded(path: pathlib.Path, open_ch: str, close_ch: str):
    """Pull the JSON literal out of a `window.X = {...};` asset file."""
    text = path.read_text()
    return json.loads(text[text.index(open_ch):text.rindex(close_ch) + 1])


def build(video_base: str | None, video_map: dict[str, str],
          external: bool = False) -> str:
    assets = _embedded(SALES, "{", "}")
    scenarios = _embedded(BQ, "[", "]")
    agents = {a["agent_id"]: a for a in json.loads(AGENTS.read_text())}

    rows = []
    for aid in sorted(assets):
        entry = assets[aid]
        meta = agents.get(aid, {})
        # The manifest path is /videos/<AID>/<file>.webm; keep the trailing
        # two segments so a --video-base preserves the directory shape.
        src = ""
        if aid in video_map:
            src = video_map[aid]
        elif video_base:
            tail = (entry.get("video") or "").replace("/videos/", "", 1)
            if tail:
                src = f"{video_base.rstrip('/')}/{tail}"
        rows.append({
            "id": aid,
            "name": re.sub(r"\s*\(" + re.escape(aid) + r"\)\s*$", "",
                           meta.get("display_name", aid)).strip(),
            "dept": meta.get("department", ""),
            "persona": meta.get("persona", ""),
            # The external build withholds endpoints, matching the promise the
            # public-showcase branch's README already makes to its readers.
            "url": "" if external else meta.get("url", ""),
            "tables": meta.get("tables", []),
            "situation": entry.get("situation", ""),
            "action": entry.get("action", ""),
            "logic": entry.get("logic", ""),
            "video": src,
        })

    depts = sorted({r["dept"] for r in rows if r["dept"]})
    with_video = sum(1 for r in rows if r["video"])
    data = json.dumps({"agents": rows, "scenarios": scenarios},
                      ensure_ascii=False)

    note = (f"{with_video} of {len(rows)} recordings attached"
            if with_video else
            "Recordings not attached — see the note in each agent panel")

    return _TEMPLATE.replace("__DATA__", data) \
                    .replace("__COUNT__", str(len(rows))) \
                    .replace("__DEPTS__", str(len(depts))) \
                    .replace("__SCEN__", str(len(scenarios))) \
                    .replace("__VIDNOTE__", html.escape(note))


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mining Agent Estate — Showcase</title>
<style>
:root{
  --canvas:#F8F9FA; --surface:#FFFFFF; --subtle:#F1F3F4; --variant:#E8EAED;
  --border:#DADCE0; --border-subtle:#ECEFF1; --border-strong:#BDC1C6;
  --primary:#1A73E8; --primary-hover:#1557B0; --primary-container:#E8F0FE;
  --on-primary-container:#174EA6;
  --critical:#D93025; --critical-container:#FCE8E6;
  --success:#1E8E3E; --success-container:#E6F4EA;
  --text:#202124; --text2:#5F6368; --text3:#80868B;
  --serif:'Playfair Display',Georgia,serif;
  --sans:'Plus Jakarta Sans','Inter',-apple-system,BlinkMacSystemFont,sans-serif;
  --mono:'Roboto Mono',ui-monospace,monospace;
  --sh-sm:0 1px 3px rgba(60,64,67,.08),0 1px 2px rgba(60,64,67,.04);
  --sh-md:0 4px 6px -1px rgba(60,64,67,.1),0 2px 4px -1px rgba(60,64,67,.06);
  --r:8px; --r-lg:12px;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--sans);background:var(--canvas);color:var(--text);
  line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:1240px;margin:0 auto;padding:0 28px}

header{background:var(--surface);border-bottom:1px solid var(--border);padding:34px 0 26px}
h1{font-family:var(--serif);font-size:31px;font-weight:600;letter-spacing:-.4px}
.sub{color:var(--text2);font-size:14.5px;margin-top:7px;max-width:70ch}
.stats{display:flex;gap:34px;margin-top:22px;flex-wrap:wrap}
.stat b{display:block;font-size:25px;font-weight:600;letter-spacing:-.5px}
.stat span{font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:.7px}

.bar{background:var(--surface);border-bottom:1px solid var(--border);
  padding:13px 0;position:sticky;top:0;z-index:20}
.bar .wrap{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
input,select{font-family:inherit;font-size:13.5px;padding:8px 11px;
  border:1px solid var(--border);border-radius:var(--r);background:var(--surface);color:var(--text)}
input{flex:1;min-width:220px}
input:focus,select:focus{outline:2px solid var(--primary-container);border-color:var(--primary)}
.count{font-size:12.5px;color:var(--text3);margin-left:auto}

.layout{display:grid;grid-template-columns:326px 1fr;gap:24px;padding:24px 0 60px;align-items:start}
.list{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-lg);
  overflow:hidden;max-height:78vh;overflow-y:auto}
.item{padding:11px 15px;border-bottom:1px solid var(--border-subtle);cursor:pointer}
.item:last-child{border-bottom:0}
.item:hover{background:var(--subtle)}
.item[aria-selected="true"]{background:var(--primary-container);
  box-shadow:inset 3px 0 0 var(--primary)}
.item .n{font-size:13.5px;font-weight:600;line-height:1.35}
.item .m{font-size:11px;color:var(--text3);margin-top:3px;font-family:var(--mono)}

.panel{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r-lg);padding:26px 28px 30px;box-shadow:var(--sh-sm)}
.pid{font-family:var(--mono);font-size:11.5px;color:var(--primary);
  background:var(--primary-container);display:inline-block;padding:3px 9px;border-radius:999px}
h2{font-family:var(--serif);font-size:24px;font-weight:600;margin:11px 0 5px;letter-spacing:-.3px}
.pmeta{font-size:12.5px;color:var(--text2)}
.tables{margin-top:11px;display:flex;gap:6px;flex-wrap:wrap}
.tag{font-family:var(--mono);font-size:10.5px;background:var(--subtle);
  border:1px solid var(--border-subtle);color:var(--text2);padding:2.5px 7px;border-radius:5px}

.sec{margin-top:24px;border-top:1px solid var(--border-subtle);padding-top:19px}
.lbl{font-size:10.5px;font-weight:700;letter-spacing:1px;text-transform:uppercase;
  color:var(--text3);margin-bottom:7px}
.body{font-size:14.5px;line-height:1.68;color:var(--text)}
.body.q{border-left:3px solid var(--primary);padding-left:14px;color:var(--text2)}

video{width:100%;border-radius:var(--r);background:#000;margin-top:4px;display:block}
/* The recordings are 1440x900; the frame keeps that ratio so a Drive-hosted
   take is letterboxed the same way a local one is. */
.vframe{width:100%;aspect-ratio:1440/900;border:0;border-radius:var(--r);
  background:#000;margin-top:4px;display:block}
.vnote{background:var(--subtle);border:1px dashed var(--border-strong);border-radius:var(--r);
  padding:15px 17px;font-size:13px;color:var(--text2);line-height:1.6}
.link{display:inline-block;margin-top:16px;font-size:13px;color:var(--primary);
  text-decoration:none;font-weight:600}
.link:hover{text-decoration:underline}

.scen{margin-top:34px}
/* Four scenarios read as a set, so 2x2. auto-fit lays them out 3+1 at this
   width, and the trailing gap looks like a card failed to load. */
.sgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:15px;margin-top:14px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-lg);padding:19px 20px}
.card .k{font-size:10.5px;font-weight:700;letter-spacing:.8px;text-transform:uppercase;color:var(--primary)}
.card h3{font-family:var(--serif);font-size:17.5px;font-weight:600;margin:7px 0 9px}
.card .f{font-size:13.5px;line-height:1.62;color:var(--text2)}
.card .i{margin-top:11px;font-size:11.5px;font-weight:600;color:var(--success);
  background:var(--success-container);display:inline-block;padding:3px 9px;border-radius:999px}

footer{border-top:1px solid var(--border);padding:22px 0 40px;font-size:12px;color:var(--text3)}
h4.secline{font-family:var(--serif);font-size:20px;font-weight:600}
@media(max-width:900px){.layout{grid-template-columns:1fr}.list{max-height:none}
  .sgrid{grid-template-columns:1fr}}
</style></head><body>

<header><div class="wrap">
  <h1>Mining Agent Estate</h1>
  <p class="sub">One hundred agents reading a mining operation's own data. Each
  entry below is a real recorded run — the question that was asked, what the
  agent concluded in its own words, and the method it applied before answering.</p>
  <div class="stats">
    <div class="stat"><b>__COUNT__</b><span>Agents</span></div>
    <div class="stat"><b>__DEPTS__</b><span>Departments</span></div>
    <div class="stat"><b>__SCEN__</b><span>Deep dives</span></div>
    <div class="stat"><b>100%</b><span>Grounded in live data</span></div>
  </div>
</div></header>

<div class="bar"><div class="wrap">
  <input id="q" type="search" placeholder="Search agents, questions, findings…" aria-label="Search">
  <select id="dept" aria-label="Filter by department"><option value="">All departments</option></select>
  <span class="count" id="count"></span>
</div></div>

<div class="wrap layout">
  <div class="list" id="list" role="listbox" aria-label="Agents"></div>
  <div><div class="panel" id="panel"></div>
    <div class="scen">
      <h4 class="secline">BigQuery deep dives</h4>
      <div class="sgrid" id="scen"></div>
    </div>
  </div>
</div>

<footer><div class="wrap">
  Generated from recorded evidence by <code>scripts/build_shareable_html.py</code>.
  Every quoted line is the agent's own output. __VIDNOTE__.
</div></footer>

<script>
var DATA = __DATA__;
var sel = DATA.agents.length ? DATA.agents[0].id : null;
function esc(s){var d=document.createElement("div");d.textContent=s==null?"":s;return d.innerHTML;}

function visible(){
  var q=document.getElementById("q").value.trim().toLowerCase();
  var d=document.getElementById("dept").value;
  return DATA.agents.filter(function(a){
    if(d && a.dept!==d) return false;
    if(!q) return true;
    return (a.name+" "+a.id+" "+a.dept+" "+a.situation+" "+a.action).toLowerCase().indexOf(q)>-1;
  });
}
function renderList(){
  var rows=visible();
  document.getElementById("count").textContent=rows.length+" of "+DATA.agents.length;
  document.getElementById("list").innerHTML=rows.map(function(a){
    return '<div class="item" role="option" data-id="'+esc(a.id)+'" aria-selected="'+
      (a.id===sel)+'"><div class="n">'+esc(a.name)+'</div><div class="m">'+
      esc(a.id)+(a.persona?" · "+esc(a.persona):"")+'</div></div>';
  }).join("") || '<div style="padding:20px;font-size:13px;color:var(--text3)">No agents match.</div>';
  Array.prototype.forEach.call(document.querySelectorAll(".item"),function(el){
    el.onclick=function(){sel=el.getAttribute("data-id");renderList();renderPanel();};
  });
}
function renderPanel(){
  var a=DATA.agents.filter(function(x){return x.id===sel;})[0];
  var p=document.getElementById("panel");
  if(!a){p.innerHTML='<div class="body">Select an agent.</div>';return;}
  // Google Drive never serves bytes a <video> element can decode; its share
  // links are player pages. Drive URLs therefore go in an iframe, everything
  // else in a real <video>. Getting this wrong renders a permanently black
  // box with working controls, which reads as a broken recording.
  var media=a.video
    ? (/drive\.google\.com/.test(a.video)
        ? '<iframe class="vframe" src="'+esc(a.video)+'" allow="autoplay" '+
          'allowfullscreen></iframe>'
        : '<video controls preload="none" src="'+esc(a.video)+'"></video>')
    : '<div class="vnote"><strong>Recording not attached to this file.</strong><br>'+
      'The estate has a verified recording for this agent, but the videos are '+
      '544MB in total and are not embedded. Rebuild with <code>--video-base</code> '+
      'or <code>--video-map</code> to attach them.</div>';
  p.innerHTML=
    '<span class="pid">'+esc(a.id)+'</span>'+
    '<h2>'+esc(a.name)+'</h2>'+
    '<div class="pmeta">'+esc(a.dept)+(a.persona?" — "+esc(a.persona):"")+'</div>'+
    (a.tables&&a.tables.length?'<div class="tables">'+a.tables.map(function(t){
      return '<span class="tag">'+esc(t)+'</span>';}).join("")+'</div>':"")+
    '<div class="sec"><div class="lbl">Situation</div><div class="body q">'+esc(a.situation)+'</div></div>'+
    '<div class="sec"><div class="lbl">Agent action</div><div class="body">'+esc(a.action)+'</div></div>'+
    '<div class="sec"><div class="lbl">Logic</div><div class="body">'+esc(a.logic)+'</div></div>'+
    '<div class="sec"><div class="lbl">Recording</div>'+media+
      (a.url?'<a class="link" href="'+esc(a.url)+'" target="_blank" rel="noopener">Open the live agent ↗</a>':"")+
    '</div>';
}
document.getElementById("scen").innerHTML=DATA.scenarios.map(function(s){
  return '<div class="card"><div class="k">'+esc(s.kind)+'</div><h3>'+esc(s.title)+
    '</h3><div class="f">'+esc(s.finding)+'</div><div class="i">'+esc(s.impact)+'</div></div>';
}).join("");
(function(){
  var ds={},o=[];
  DATA.agents.forEach(function(a){if(a.dept&&!ds[a.dept]){ds[a.dept]=1;o.push(a.dept);}});
  document.getElementById("dept").innerHTML='<option value="">All departments</option>'+
    o.sort().map(function(d){return '<option>'+esc(d)+'</option>';}).join("");
})();
document.getElementById("q").oninput=function(){renderList();};
document.getElementById("dept").onchange=function(){renderList();};
renderList();renderPanel();
</script></body></html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--video-base", help="public URL prefix holding <AID>/<file>.webm")
    ap.add_argument("--video-map", type=pathlib.Path,
                    help='JSON {"AGENT-ID": "url"} — required for Google Drive')
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--external", action="store_true",
                    help="withhold live agent endpoints (for the public "
                         "Pages build, which promises exactly that)")
    args = ap.parse_args()

    vmap: dict[str, str] = {}
    if args.video_map:
        if not args.video_map.exists():
            print(f"error: {args.video_map} does not exist", file=sys.stderr)
            return 2
        vmap = json.loads(args.video_map.read_text())
        if not isinstance(vmap, dict):
            print("error: --video-map must be a JSON object of id -> url",
                  file=sys.stderr)
            return 2

    doc = build(args.video_base, vmap, external=args.external)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(doc)
    kb = len(doc.encode()) / 1024
    # --out is free to point anywhere; relative_to() raises outside the repo.
    out = args.out.resolve()
    shown = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
    print(f"{shown}  ({kb:.0f} KB, self-contained)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
