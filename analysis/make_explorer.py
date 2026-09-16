#!/usr/bin/env python3
"""Build an interactive HTML explorer of every candidate site, for manual triage.

Reads outputs/all_scored_sites.csv (+ outputs/housing_screen.json for the housing
status) and writes explorer.html — a self-contained, sortable, filterable table.
No libraries, data inlined; opens in any browser and publishes as an Artifact.

Run:  python3 analysis/make_explorer.py
"""

import csv
import json
import os
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SCORED = os.path.join(HERE, "..", "outputs", "all_scored_sites.csv")
SCREEN = os.path.join(HERE, "..", "outputs", "housing_screen.json")
OUT = os.path.join(HERE, "..", "explorer.html")            # standalone document (shareable)
FRAGMENT = os.path.join(HERE, "..", "explorer_artifact.html")  # fragment for the Artifact tool

HOUSING_GAP_M = 50


def num(x):
    try:
        return round(float(x), 2)
    except (TypeError, ValueError):
        return None


def coord(x):
    """Full-precision coordinate — never round these (satellite/map alignment)."""
    try:
        return round(float(x), 6)
    except (TypeError, ValueError):
        return None


def load_rows():
    screen = {}
    if os.path.exists(SCREEN):
        with open(SCREEN) as f:
            screen = json.load(f)

    rows = []
    with open(SCORED, newline="") as f:
        for r in csv.DictReader(f):
            code = r["site_code"]
            entry = screen.get(code)
            home_m, status = None, "pending"
            if entry and "error" not in entry:
                home_m = entry.get("nearest_home_m")
                if home_m is None:
                    status = "ok"
                elif home_m < HOUSING_GAP_M:
                    status = "violation"
                else:
                    status = "ok"
            rows.append({
                "score": int(r["score"]),
                "name": r["site_name"].strip() or r["address"].strip() or "(unnamed)",
                "council": r["council"],
                "size": num(r["size_ha"]),
                "type": r["site_type"],
                "dev": r["development_potential"],
                "prev": r["previous_use"],
                "member_km": num(r["mean_member_km"]),
                "home_m": home_m,
                "status": status,
                "frz": r["in_airport_frz"] == "True",
                "centre_km": num(r["km_from_glasgow_centre"]),
                "lat": coord(r["lat"]),
                "lon": coord(r["lon"]),
                "code": code,
                "map": r["map_url"],
            })
    return rows


TEMPLATE = r"""<title>Drone Site Explorer</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700&family=IBM+Plex+Mono:wght@500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
:root{
  --ground:#f0f3ee; --surface:#ffffff; --surface-2:#e7ebe4; --surface-3:#eef1ec;
  --ink:#1a211c; --muted:#5c665f; --line:#d9ded4; --line-soft:#e6eae1;
  --accent:#2f6b5e; --accent-ink:#ffffff;
  --ok:#2e7d46; --ok-bg:#e4f0e6; --warn:#a4690f; --warn-bg:#f4e9d4;
  --bad:#b23b2e; --bad-bg:#f6e0dc; --pending:#7a837c; --pending-bg:#e7ebe4;
  --shadow:0 1px 2px rgba(20,30,24,.06),0 8px 24px rgba(20,30,24,.06);
}
@media (prefers-color-scheme:dark){ :root:not([data-theme="light"]){
  --ground:#10140f; --surface:#171c15; --surface-2:#1f261d; --surface-3:#1b211a;
  --ink:#e7ece3; --muted:#95a099; --line:#2a3127; --line-soft:#222a1f;
  --accent:#5cb6a1; --accent-ink:#08150f;
  --ok:#63c07a; --ok-bg:#183123; --warn:#e0aa4b; --warn-bg:#33280f;
  --bad:#e37a6a; --bad-bg:#3a1f1a; --pending:#8b948b; --pending-bg:#222a1f;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35);
}}
:root[data-theme="dark"]{
  --ground:#10140f; --surface:#171c15; --surface-2:#1f261d; --surface-3:#1b211a;
  --ink:#e7ece3; --muted:#95a099; --line:#2a3127; --line-soft:#222a1f;
  --accent:#5cb6a1; --accent-ink:#08150f;
  --ok:#63c07a; --ok-bg:#183123; --warn:#e0aa4b; --warn-bg:#33280f;
  --bad:#e37a6a; --bad-bg:#3a1f1a; --pending:#8b948b; --pending-bg:#222a1f;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35);
}
*{box-sizing:border-box}
[hidden]{display:none!important}
body{margin:0;background:var(--ground);color:var(--ink);
  font-family:"IBM Plex Sans",system-ui,-apple-system,sans-serif;line-height:1.45;}
.wrap{max-width:1240px;margin:0 auto;padding:clamp(16px,3vw,34px);}
.mono{font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums;}

header.top{display:flex;flex-wrap:wrap;align-items:baseline;gap:10px 16px;margin-bottom:4px;}
h1{font-family:"Archivo",sans-serif;font-weight:700;letter-spacing:-.01em;
  font-size:clamp(1.5rem,3.4vw,2.1rem);margin:0;text-wrap:balance;}
.sub{color:var(--muted);font-size:.92rem;max-width:64ch;margin:.2rem 0 0;}
.eyebrow{font-family:"Archivo",sans-serif;text-transform:uppercase;letter-spacing:.14em;
  font-size:.7rem;font-weight:700;color:var(--accent);}

.controls{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--ground) 90%,transparent);
  backdrop-filter:blur(8px);border:1px solid var(--line);border-radius:14px;
  padding:12px 14px;margin:16px 0;box-shadow:var(--shadow);}
.row1{display:flex;flex-wrap:wrap;gap:10px;align-items:center;}
.field{display:flex;flex-direction:column;gap:3px;}
.field label{font-size:.66rem;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);font-weight:600;}
input[type=text],input[type=number],select{
  font:inherit;font-size:.9rem;color:var(--ink);background:var(--surface);
  border:1px solid var(--line);border-radius:9px;padding:7px 10px;}
input[type=text]{min-width:210px;}
input[type=number]{width:78px;}
input:focus-visible,select:focus-visible,button:focus-visible{outline:2px solid var(--accent);outline-offset:1px;}
.search{flex:1 1 220px;}
.toggles{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;}
.chip{display:inline-flex;align-items:center;gap:7px;font-size:.82rem;
  border:1px solid var(--line);border-radius:999px;padding:6px 12px;cursor:pointer;
  background:var(--surface);user-select:none;transition:.12s;}
.chip:hover{border-color:var(--accent);}
.chip input{accent-color:var(--accent);margin:0;}
.chip.on{background:var(--accent);color:var(--accent-ink);border-color:var(--accent);}
.btn-reset{margin-left:auto;font:inherit;font-size:.82rem;background:none;border:1px solid var(--line);
  border-radius:999px;padding:6px 14px;color:var(--muted);cursor:pointer;}
.btn-reset:hover{color:var(--ink);border-color:var(--accent);}

.summary{display:flex;flex-wrap:wrap;gap:8px 20px;align-items:baseline;margin:0 2px 12px;
  font-size:.9rem;color:var(--muted);}
.summary b{color:var(--ink);font-weight:600;}
.dot{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:5px;vertical-align:baseline;}
.dot.ok{background:var(--ok)} .dot.violation{background:var(--bad)} .dot.pending{background:var(--pending)}

.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:14px;background:var(--surface);box-shadow:var(--shadow);}
table{border-collapse:collapse;width:100%;font-size:.87rem;}
thead th{position:sticky;top:0;background:var(--surface-2);z-index:2;text-align:left;
  font-family:"Archivo",sans-serif;font-weight:600;font-size:.72rem;text-transform:uppercase;
  letter-spacing:.05em;color:var(--muted);padding:11px 12px;white-space:nowrap;cursor:pointer;
  border-bottom:1px solid var(--line);}
thead th:hover{color:var(--ink);}
thead th .ar{opacity:0;margin-left:4px;font-size:.8em;}
thead th.sorted .ar{opacity:1;color:var(--accent);}
thead th.num,td.num{text-align:right;}
tbody td{padding:10px 12px;border-bottom:1px solid var(--line-soft);vertical-align:top;}
tbody tr{border-left:4px solid transparent;}
tbody tr.st-ok{border-left-color:var(--ok);}
tbody tr.st-violation{border-left-color:var(--bad);}
tbody tr.st-pending{border-left-color:var(--pending);}
tbody tr:hover td{background:var(--surface-3);}
.site{font-weight:600;line-height:1.3;}
.addr{color:var(--muted);font-size:.78rem;font-weight:400;}
.scorecell{font-family:"Archivo",sans-serif;font-weight:700;font-size:1rem;}
.pill{display:inline-block;font-size:.72rem;font-weight:600;padding:2px 9px;border-radius:999px;white-space:nowrap;}
.pill.ok{background:var(--ok-bg);color:var(--ok);}
.pill.violation{background:var(--bad-bg);color:var(--bad);}
.pill.pending{background:var(--pending-bg);color:var(--pending);}
.pill.frz{background:var(--bad-bg);color:var(--bad);margin-left:5px;}
.maplink{color:var(--accent);text-decoration:none;font-weight:600;font-size:.8rem;white-space:nowrap;}
.maplink:hover{text-decoration:underline;}
tbody tr.data{cursor:pointer;}
tbody tr.data td:first-child{position:relative;}
tbody tr.data td:first-child::before{content:"▸";position:absolute;left:2px;color:var(--muted);font-size:.7rem;transition:transform .12s;}
tbody tr.data.open td:first-child::before{transform:rotate(90deg);color:var(--accent);}
tbody tr.data .scorecell{margin-left:9px;}
tr.detail>td{padding:0;border-left:4px solid var(--accent);background:var(--surface-3);}
.detail-inner{display:flex;flex-wrap:wrap;gap:18px;padding:14px 16px;}
.sat{position:relative;flex:0 0 auto;width:min(420px,88vw);}
.sat img{width:100%;aspect-ratio:1/1;object-fit:cover;border-radius:10px;border:1px solid var(--line);display:block;background:var(--surface-2);}
.sat .cross{position:absolute;top:calc(50% - 13px);left:50%;width:24px;height:24px;transform:translateX(-50%);pointer-events:none;}
.sat .cross::before,.sat .cross::after{content:"";position:absolute;background:#ff3b3b;box-shadow:0 0 2px rgba(0,0,0,.6);}
.sat .cross::before{left:11px;top:0;width:2px;height:100%;}
.sat .cross::after{top:11px;left:0;height:2px;width:100%;}
.sat .cap{font-size:.72rem;color:var(--muted);margin-top:6px;}
.facts{flex:1 1 230px;display:grid;grid-template-columns:auto 1fr;gap:6px 14px;align-content:start;
  font-size:.87rem;margin:0;}
.facts dt{color:var(--muted);white-space:nowrap;}
.facts dd{margin:0;font-weight:500;}
.facts dd.full{grid-column:1/-1;margin-top:8px;}
.tag{font-size:.78rem;color:var(--muted);}
.empty{padding:40px;text-align:center;color:var(--muted);}
footer{margin:16px 2px 4px;font-size:.76rem;color:var(--muted);}
footer a{color:var(--accent);}
@media (max-width:640px){ .sub{font-size:.85rem} input[type=text]{min-width:150px} }
</style>

<div class="wrap">
  <header class="top">
    <div>
      <div class="eyebrow">FPV drone racing &middot; Glasgow land search</div>
      <h1>Candidate Site Explorer</h1>
    </div>
  </header>
  <p class="sub">Every council-owned vacant/derelict site in the Glasgow area, football-pitch
  sized. Sort and filter to help triage by hand. Housing status flags homes within
  <b>__GAP__&nbsp;m</b> of the (approximate) site edge &mdash; a BMFA/CAA screen, not a legal boundary.
  <b>Click any row</b> for its satellite view.</p>

  <div class="controls">
    <div class="row1">
      <div class="field search"><label for="q">Search name / council / address</label>
        <input type="text" id="q" placeholder="e.g. pitch, Cambuslang, recreation&hellip;"></div>
      <div class="field"><label for="council">Council</label>
        <select id="council"><option value="">All councils</option></select></div>
      <div class="field"><label for="use">Former use</label>
        <select id="use"><option value="">Any use</option></select></div>
      <div class="field"><label for="smin">Size min (ha)</label><input type="number" id="smin" step="0.1" min="0" placeholder="0.4"></div>
      <div class="field"><label for="smax">Size max (ha)</label><input type="number" id="smax" step="0.1" min="0" placeholder="3.0"></div>
      <div class="field"><label for="scoremin">Score &ge;</label><input type="number" id="scoremin" step="1" placeholder="any"></div>
    </div>
    <div class="toggles">
      <label class="chip"><input type="checkbox" id="tClear"> Clear of homes (&ge;__GAP__ m)</label>
      <label class="chip"><input type="checkbox" id="tFrz" checked> Exclude airport FRZ</label>
      <label class="chip"><input type="checkbox" id="tVacant"> Vacant land only</label>
      <label class="chip"><input type="checkbox" id="tScreened"> Housing-screened only</label>
      <button class="btn-reset" id="reset">Reset filters</button>
    </div>
  </div>

  <div class="summary" id="summary"></div>

  <div class="tablewrap">
    <table>
      <thead><tr id="head"></tr></thead>
      <tbody id="body"></tbody>
    </table>
    <div class="empty" id="empty" hidden>No sites match these filters.</div>
  </div>

  <footer>
    __TOTAL__ sites &middot; generated __DATE__ from the Scottish Vacant &amp; Derelict Land Survey
    (Open Government Licence). Housing footprints &copy; OpenStreetMap. Distances are straight-line
    means; site extent is approximated from the recorded area. Always verify airspace and boundaries
    before flying.
  </footer>
</div>

<script>
const DATA = __DATA__;
const GAP = __GAP__;
const COLS = [
  {k:"score", label:"Score", num:true, cell:r=>`<span class="scorecell">${r.score>0?"+":""}${r.score}</span>`},
  {k:"name", label:"Site", cell:r=>`<div class="site">${esc(r.name)}</div><div class="addr">${esc(r.council)}</div>`},
  {k:"size", label:"Size ha", num:true, cell:r=>fmt(r.size)},
  {k:"type", label:"Type", cell:r=>`<span class="tag">${esc(r.type)}</span>`},
  {k:"dev", label:"Development", cell:r=>`<span class="tag">${esc(r.dev.replace("Developable - ",""))}</span>`},
  {k:"prev", label:"Former use", cell:r=>`<span class="tag">${esc(r.prev)}</span>`},
  {k:"member_km", label:"Member km", num:true, cell:r=>r.member_km==null?"&mdash;":`<span class="mono">${fmt(r.member_km)}</span>`},
  {k:"home_m", label:"Nearest home", num:true, cell:r=>homeCell(r)},
  {k:"centre_km", label:"To centre km", num:true, cell:r=>r.centre_km==null?"&mdash;":`<span class="mono">${fmt(r.centre_km)}</span>`},
  {k:"map", label:"Map", sortable:false, cell:r=>`<a class="maplink" href="${r.map}" target="_blank" rel="noopener">Open &nearr;</a>`},
];
let sortKey="score", sortDir=-1;

const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const fmt=v=>v==null?"&mdash;":`<span class="mono">${v}</span>`;
function homeCell(r){
  if(r.status==="pending") return `<span class="pill pending">pending</span>`;
  const label = r.home_m==null ? "none &lt;175 m" : r.home_m+" m";
  const cls = r.status==="violation" ? "violation":"ok";
  let out = `<span class="mono">${r.home_m==null?"":r.home_m}</span> <span class="pill ${cls}">${r.status==="violation"?"&lt;"+GAP+" m":"clear"}</span>`;
  if(r.home_m==null) out = `<span class="pill ok">clear</span>`;
  return out;
}
function homeText(r){
  if(r.status==="pending") return "not yet screened";
  if(r.home_m==null) return "no home within 175 m";
  return r.home_m+" m &mdash; "+(r.status==="violation"?"within "+GAP+" m":"clear of "+GAP+" m");
}
// Live centred satellite image from Esri World Imagery (no key), ~500 m across.
function bbox(lat,lon){const h=250,dlat=h/111320,dlon=h/(111320*Math.cos(lat*Math.PI/180));
  return [lon-dlon,lat-dlat,lon+dlon,lat+dlat].join(",");}
function satUrl(r){return "https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/export?bbox="
  +bbox(r.lat,r.lon)+"&bboxSR=4326&imageSR=3857&size=480,480&format=jpg&f=image";}
function detailRow(r){
  const img=(r.lat!=null&&r.lon!=null)
    ? `<div class="sat"><img loading="lazy" data-src="${satUrl(r)}" alt="Satellite view of ${esc(r.name)}" onerror="this.closest('.sat').style.display='none'">`
      +`<div class="cross"></div><div class="cap">Esri satellite &middot; red mark = site centroid</div></div>` : "";
  return `<tr class="detail" hidden><td colspan="${COLS.length}"><div class="detail-inner">`+img
    +`<dl class="facts">`
    +`<dt>Former use</dt><dd>${esc(r.prev)}</dd>`
    +`<dt>Development</dt><dd>${esc(r.dev)}</dd>`
    +`<dt>Type</dt><dd>${esc(r.type)}</dd>`
    +`<dt>Nearest home</dt><dd>${homeText(r)}</dd>`
    +`<dt>Size</dt><dd>${r.size==null?"&mdash;":r.size+" ha"}</dd>`
    +`<dt>Avg member</dt><dd>${r.member_km==null?"&mdash;":r.member_km+" km"}</dd>`
    +`<dt>SVDLS code</dt><dd class="mono">${esc(r.code)}</dd>`
    +`<dd class="full"><a class="maplink" href="${r.map}" target="_blank" rel="noopener">Open in Google Maps (satellite) &nearr;</a></dd>`
    +`</dl></div></td></tr>`;
}

const $=id=>document.getElementById(id);
function buildHead(){
  $("head").innerHTML = COLS.map(c=>{
    const sortable = c.sortable!==false;
    return `<th data-k="${c.k}" class="${c.num?"num":""} ${sortable?"":"nosort"} ${c.k===sortKey?"sorted":""}"${sortable?"":' style="cursor:default"'}>${c.label}${sortable?`<span class="ar">${c.k===sortKey?(sortDir<0?"▼":"▲"):"▸"}</span>`:""}</th>`;
  }).join("");
  $("head").querySelectorAll("th:not(.nosort)").forEach(th=>th.onclick=()=>{
    const k=th.dataset.k;
    if(k===sortKey) sortDir*=-1; else {sortKey=k; sortDir=(k==="name"||k==="type"||k==="dev"||k==="prev")?1:-1;}
    render();
  });
}
function fillSelect(id,vals){ const s=$(id); vals.sort().forEach(v=>{const o=document.createElement("option");o.value=v;o.textContent=v;s.appendChild(o);}); }

function filtered(){
  const q=$("q").value.trim().toLowerCase();
  const council=$("council").value, use=$("use").value;
  const smin=parseFloat($("smin").value), smax=parseFloat($("smax").value);
  const scoremin=parseInt($("scoremin").value,10);
  const clear=$("tClear").checked, noFrz=$("tFrz").checked, vac=$("tVacant").checked, scr=$("tScreened").checked;
  return DATA.filter(r=>{
    if(q && !(r.name.toLowerCase().includes(q)||r.council.toLowerCase().includes(q))) return false;
    if(council && r.council!==council) return false;
    if(use && r.prev!==use) return false;
    if(!isNaN(smin) && (r.size==null||r.size<smin)) return false;
    if(!isNaN(smax) && (r.size==null||r.size>smax)) return false;
    if(!isNaN(scoremin) && r.score<scoremin) return false;
    if(noFrz && r.frz) return false;
    if(vac && r.type!=="Vacant Land") return false;
    if(scr && r.status==="pending") return false;
    if(clear && r.status!=="ok") return false;
    return true;
  });
}
function sortRows(rows){
  return rows.slice().sort((a,b)=>{
    let x=a[sortKey], y=b[sortKey];
    if(x==null) x=(typeof y==="number")?-Infinity:""; if(y==null) y=(typeof x==="number")?-Infinity:"";
    if(typeof x==="number"||typeof y==="number") return (x-y)*sortDir;
    return String(x).localeCompare(String(y))*sortDir;
  });
}
function render(){
  buildHead();
  const rows=sortRows(filtered());
  $("body").innerHTML = rows.map(r=>{
    const cells=COLS.map(c=>{
      let v=c.cell(r);
      if(c.k==="name" && r.frz) v+=` <span class="pill frz">FRZ</span>`;
      return `<td class="${c.num?"num":""}">${v}</td>`;
    }).join("");
    return `<tr class="data st-${r.status}">${cells}</tr>`+detailRow(r);
  }).join("");
  $("empty").hidden = rows.length>0;
  const clear=DATA.filter(r=>r.status==="ok").length;
  const viol=DATA.filter(r=>r.status==="violation").length;
  const pend=DATA.filter(r=>r.status==="pending").length;
  $("summary").innerHTML =
    `Showing <b>${rows.length}</b> of ${DATA.length} sites`+
    ` &nbsp;&middot;&nbsp; <span class="dot ok"></span><b>${clear}</b> clear of homes`+
    ` &nbsp;&middot;&nbsp; <span class="dot violation"></span><b>${viol}</b> within ${GAP} m`+
    (pend?` &nbsp;&middot;&nbsp; <span class="dot pending"></span><b>${pend}</b> not yet screened`:"");
}
["q","council","use","smin","smax","scoremin"].forEach(id=>$(id).addEventListener("input",render));
["tClear","tFrz","tVacant","tScreened"].forEach(id=>$(id).addEventListener("change",e=>{
  e.target.closest(".chip").classList.toggle("on",e.target.checked); render();
}));
$("reset").onclick=()=>{
  ["q","smin","smax","scoremin"].forEach(id=>$(id).value="");
  ["council","use"].forEach(id=>$(id).value="");
  $("tClear").checked=false; $("tVacant").checked=false; $("tScreened").checked=false; $("tFrz").checked=true;
  document.querySelectorAll(".chip").forEach(c=>c.classList.remove("on"));
  $("tFrz").closest(".chip").classList.add("on");
  render();
};
// Expand a row to its satellite view (image loads lazily on first open).
$("body").addEventListener("click",e=>{
  if(e.target.closest("a")) return;
  const tr=e.target.closest("tr.data"); if(!tr) return;
  const d=tr.nextElementSibling; if(!d||!d.classList.contains("detail")) return;
  const opening=d.hidden;
  d.hidden=!d.hidden; tr.classList.toggle("open",opening);
  if(opening){const img=d.querySelector("img"); if(img&&!img.src) img.src=img.dataset.src;}
});
fillSelect("council",[...new Set(DATA.map(r=>r.council))]);
fillSelect("use",[...new Set(DATA.map(r=>r.prev))]);
$("tFrz").closest(".chip").classList.add("on");
render();
</script>
"""


def main():
    rows = load_rows()
    fragment = (TEMPLATE
                .replace("__DATA__", json.dumps(rows, separators=(",", ":")))
                .replace("__GAP__", str(HOUSING_GAP_M))
                .replace("__TOTAL__", str(len(rows)))
                .replace("__DATE__", date.today().isoformat()))

    # Split the fragment into head-ish (title/fonts/style) and body (content/script)
    # so the standalone document is well-formed.
    cut = fragment.index('<div class="wrap">')
    head, body = fragment[:cut], fragment[cut:]
    standalone = ('<!doctype html>\n<html lang="en">\n<head>\n'
                  '<meta charset="utf-8">\n'
                  '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                  + head + '</head>\n<body>\n' + body + '\n</body>\n</html>\n')

    with open(OUT, "w") as f:
        f.write(standalone)
    with open(FRAGMENT, "w") as f:
        f.write(fragment)

    screened = sum(1 for r in rows if r["status"] != "pending")
    print(f"Wrote {os.path.relpath(OUT)} (standalone) and "
          f"{os.path.relpath(FRAGMENT)} — {len(rows)} sites, {screened} housing-screened.")


if __name__ == "__main__":
    main()
