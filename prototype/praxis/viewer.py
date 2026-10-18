"""Local web viewer (screen-shareable): video + synced step belief over the task graph + event log + metrics.

    uv run python -m praxis.viewer fused            # writes renders/viewer/index.html + one page per clip
    cd .. && python3 -m http.server 8765            # then open http://localhost:8765/renders/viewer/

Pages are generated from run logs + GT only (no live computation), and reference the source videos by path.
"""
from __future__ import annotations

import html
import json
import os
import sys
from pathlib import Path

from .data.cc4d import Clip, load_manifest
from .paths import RENDERS, RESULTS, ROOT, RUNS
from .runlog import read_log
from .tasks.compiler import load_library

PAGE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Praxis viewer · {title}</title>
<style>
:root{{--ink:#1c1e22;--sub:#5c6068;--bg:#f6f7f9;--card:#fff;--green:#2bb673;--amber:#f5a623;--blue:#3b82f6;--line:#e3e5e9}}
body{{margin:0;font:14px/1.4 -apple-system,BlinkMacSystemFont,"Avenir Next",sans-serif;background:var(--bg);color:var(--ink)}}
header{{padding:14px 20px;border-bottom:1px solid var(--line);background:var(--card)}}
header b{{font-size:17px}} header span{{color:var(--sub);margin-left:10px}}
main{{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(280px,1fr);gap:16px;padding:16px 20px}}
@media (max-width:900px){{main{{grid-template-columns:1fr}}}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}}
video{{width:100%;border-radius:10px;background:#000}}
.row{{display:flex;align-items:center;gap:8px;margin:3px 0}}
.row .n{{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--sub)}}
.row.map .n{{color:var(--ink);font-weight:600}}
.bar{{width:42%;height:10px;background:#eceef2;border-radius:5px;overflow:hidden}}
.bar i{{display:block;height:100%;background:#9aa0a8}} .row.map .bar i{{background:var(--blue)}} .row.done .bar i{{background:var(--green)}}
#gt{{font-weight:600;margin:6px 0}} .muted{{color:var(--sub)}}
#log{{max-height:360px;overflow:auto;font:12px/1.5 Menlo,monospace}}
#log div{{padding:2px 0;border-bottom:1px dashed #eee}} #log .now{{background:#fff7e6}}
.k-mistake{{color:#b26b00}} .k-view_request{{color:var(--blue)}} .k-verified{{color:var(--green)}}
table{{border-collapse:collapse;width:100%}} td{{padding:3px 6px;border-bottom:1px solid #f0f0f0}}
</style></head><body>
<header><b>Praxis</b><span>Instructions that can finally see how you're doing · real model output · {dataset}</span></header>
<main>
<div>
 <div class="card"><video id="v" controls preload="metadata" src="{video}#t={start}"></video>
 <div id="gt"></div><div class="muted" id="ent"></div></div>
 <div class="card" style="margin-top:16px"><b>Event log</b> <span class="muted">(verifier calls, policy actions)</span><div id="log"></div></div>
</div>
<div>
 <div class="card"><b>L4 belief over the task graph</b><div id="bel"></div></div>
 <div class="card" style="margin-top:16px"><b>Clip metrics</b><table id="met"></table></div>
</div>
</main>
<script>
const D = {data};
const v = document.getElementById('v');
const names = D.names;
function at(arr, t){{let r=null; for(const x of arr){{ if(x.t<=t) r=x; else break;}} return r;}}
function draw(){{
  const t = v.currentTime - D.start;
  const b = at(D.beliefs, t);
  const el = document.getElementById('bel'); el.innerHTML='';
  if(b){{ for(const [id,p] of Object.entries(b.p)){{
      const d=document.createElement('div'); d.className='row'+(id===b.map?' map':'')+(b.completed.includes(id)?' done':'');
      d.innerHTML='<span class="n">'+(names[id]||id)+'</span><span class="bar"><i style="width:'+(100*p).toFixed(1)+'%"></i></span>';
      el.appendChild(d);}}
    document.getElementById('ent').textContent='entropy '+b.entropy.toFixed(2)+' · time on step '+b.time_on_step.toFixed(0)+'s · completed '+b.completed.length+'/'+D.n_steps;
  }} else {{ el.innerHTML='<div class="muted">recognizing task…</div>'; }}
  const g = D.gt.find(s=>s[0]<=t && t<s[1]);
  document.getElementById('gt').textContent='t='+t.toFixed(1)+'s · GT: '+(g?(names[g[2]]||g[2])+(g[3]?' (annotated error)':''):'(between steps)')+' · Praxis: '+(b?(names[b.map]||b.map):'—');
  for(const row of document.querySelectorAll('#log div')) row.classList.toggle('now', Math.abs(parseFloat(row.dataset.t)-t)<1.0);
}}
const log = document.getElementById('log');
for(const e of D.events){{ const d=document.createElement('div'); d.dataset.t=e.t; d.className='k-'+e.k;
  d.textContent=e.t.toFixed(1).padStart(6)+'s  '+e.text; d.onclick=()=>{{v.currentTime=D.start+e.t;}}; log.appendChild(d);}}
const met=document.getElementById('met');
for(const [k,val] of Object.entries(D.metrics)) met.insertAdjacentHTML('beforeend','<tr><td>'+k+'</td><td>'+val+'</td></tr>');
v.addEventListener('timeupdate', draw); v.addEventListener('seeked', draw); draw();
</script></body></html>"""


def recipe(task_id: str) -> str:
    return task_id.replace("cc4d_", "")


def wrong_recipe_note(row: dict) -> str:
    """Why a clip of a task-not-given run scores 0%: the engine committed to the wrong recipe (or none) and never revises."""
    if not row or row.get("task_correct", True):
        return ""
    return f"wrong recipe (guessed {recipe(row['recognized_task'])})" if row.get("recognized_task") else "no recipe recognized"


def page(run: str, clip: Clip, metrics_row: dict | None, out_dir: Path) -> Path:
    recs = read_log(RUNS / run / f"{clip.clip_id}.jsonl")
    g = load_library()[clip.task_id]
    beliefs = [{"t": r["t"], "p": r["p"], "map": r["map"], "entropy": r["entropy"], "time_on_step": r["time_on_step"],
                "completed": r["completed"]} for r in recs if r["kind"] == "belief"]
    events = []
    for r in recs:
        if r["kind"] == "verdict":
            events.append({"t": r["t"], "k": "verdict", "text": f"L5 {r['model']} {r['reason']}: {r['status']} p={r['confidence']:.2f} "
                                                              f"({r['latency_ms']:.0f} ms){' view insufficient' if r['visibility'] != 'ok' else ''}"})
        elif r["kind"] == "action":
            events.append({"t": r["t"], "k": r["action"], "text": f"L6 {r['action']}: {r['text']}"})
        elif r["kind"] == "task":
            events.append({"t": r["t"], "k": "task", "text": f"L3b recognized: {r['title']}"})
    events.sort(key=lambda e: e["t"])
    mr = metrics_row or {}
    if not mr:
        recognized = "n/a"
    elif mr.get("recognized_task") is None:
        recognized = "none"
    else:
        recognized = f"{recipe(mr['recognized_task'])} at {mr.get('t_recognize')} s"
        if not mr.get("task_correct"):
            recognized += f" (wrong recipe: the clip is {recipe(clip.task_id)})"
    metrics = {"step accuracy": f"{100 * mr.get('step_acc', 0):.0f}%" if mr else "n/a",
               "task recognized": recognized,
               "mistake alerts (TP/FP/FN)": f"{mr['mistakes']['tp']}/{mr['mistakes']['fp']}/{mr['mistakes']['fn']}" if mr else "n/a",
               "verifier calls": str(mr.get("verifier_calls", "n/a")), "cost": f"${mr.get('cost_usd', 0):.4f}" if mr else "n/a"}
    data = {"start": clip.start, "n_steps": len(g.nodes), "names": {n.id: n.name for n in g.nodes}, "beliefs": beliefs,
            "events": events, "gt": [[s.start, s.end, s.step, s.has_error] for s in clip.segments], "metrics": metrics}
    video_rel = os.path.relpath(clip.video, out_dir)
    out = out_dir / f"{run}_{clip.clip_id}.html"
    out.write_text(PAGE.format(title=html.escape(f"{g.title} · {clip.clip_id}"), dataset="CaptainCook4D", video=video_rel,
                               start=clip.start, data=json.dumps(data)))
    return out


def main(run: str = "fused") -> Path:
    out_dir = RENDERS / "viewer"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = {}
    p = RESULTS / "runs" / f"{run}.json"
    if p.exists():
        rows = {r["clip"]: r for r in json.loads(p.read_text())["per_clip"]}
    dev = set(json.loads((RESULTS / "dev_clips.json").read_text())["dev_clips"]) if (RESULTS / "dev_clips.json").exists() else set()
    links = []
    for cj in load_manifest()["eval"]:
        c = Clip.from_json(cj)
        if (RUNS / run / f"{c.clip_id}.jsonl").exists():
            f = page(run, c, rows.get(c.clip_id), out_dir)
            r = rows.get(c.clip_id, {})
            note = wrong_recipe_note(r)
            links.append(f"<tr><td><a href='{f.name}'>{c.clip_id}</a>{' (dev clip)' if c.clip_id in dev else ''}</td>"
                         f"<td>{recipe(c.task_id)}</td>"
                         f"<td>{100 * r.get('step_acc', 0):.0f}%{f' · {html.escape(note)}' if note else ''}</td>"
                         f"<td>{r.get('mistakes', {}).get('tp', '')}</td></tr>")
    legend = ("Step acc. is the share of moments inside an annotated step where Praxis named the step the person was on.")
    if any(wrong_recipe_note(r) for r in rows.values()):
        legend += (" In this run Praxis is not told the recipe and must recognize it. Once it picks a recipe it does not "
                   "reconsider yet, so a clip where it picked the wrong one scores 0%.")
    idx = out_dir / "index.html"
    idx.write_text("<!doctype html><meta charset='utf-8'><title>Praxis viewer</title><body style='font:14px -apple-system,sans-serif;"
                   "margin:24px'><h2>Praxis viewer · run " + html.escape(run) + "</h2><p>AI guidance for the physical world · "
                   "real model output</p><p style='max-width:760px;color:#555'>" + html.escape(legend) + "</p>"
                   "<table cellpadding=4><tr><th>clip</th><th>procedure</th><th>step acc.</th><th>mistake alerts near an annotated error (time-window)</th></tr>"
                   + "".join(links) + "</table></body>")
    return idx


if __name__ == "__main__":
    print(main(sys.argv[1] if len(sys.argv) > 1 else "fused"))
