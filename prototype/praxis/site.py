"""Static public site (praxis.monishsaravana.com): a landing page with the measured results, the showcase renders, the
48-clip viewer with its CaptainCook4D videos, and Praxis Studio's saved sessions as a replay-only export. Nothing on it
calls a model, so it costs nothing to visit.

    uv run python -m praxis.site build                  # -> ../site/ (gitignored; videos are symlinks)
    uv run python -m praxis.site build --session <id>   # also publish a saved camera/upload session (personal video)
    uv run python -m praxis.site deploy                 # S3 sync + CloudFront invalidation (AWS CLI credentials)

Every number on the landing page is read from results/metrics.json (each figure names its source file) and every clip
from results/renders_index.json, so a re-run of the harness followed by a build keeps the site in step with RESULTS.md.
Only Studio sessions that ran on a test clip are exported unless one is named with --session.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from .paths import RENDERS, RESULTS, ROOT

SITE = ROOT / "site"
DOMAIN = "praxis.monishsaravana.com"
BUCKET = "praxis-monishsaravana-site"
DISTRIBUTION = "E2WTNW9W6MV1LC"                     # CloudFront, alias praxis.monishsaravana.com
VIDEO_REF = re.compile(r"\.\./\.\./data/raw/cc4d/videos/([\w.-]+\.mp4)")
e = html.escape


def _link(src: Path, dst: Path) -> None:
    """Large files are symlinked into the build; `aws s3 sync` follows the links."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(src.resolve(), dst)


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(obj if isinstance(obj, str) else json.dumps(obj, default=str))


# ---------------------------------------------------------------------------------------------- viewer
def build_viewer() -> int:
    """renders/viewer/*.html with the video paths pointed at /videos/ and a way back to the landing page."""
    src_dir, out = RENDERS / "viewer", SITE / "viewer"
    videos: set[str] = set()
    n = 0
    for p in sorted(src_dir.glob("*.html")):
        s = p.read_text()
        videos.update(VIDEO_REF.findall(s))
        s = VIDEO_REF.sub(r"../videos/\1", s)
        if p.name == "index.html":
            s = s.replace("<body style='", "<body style='max-width:980px;", 1)
            s = s.replace("<h2>", "<p><a href='/'>← Praxis</a></p><h2>", 1)
        else:
            s = s.replace("<header><b>Praxis</b>", "<header><a href=\"/\" style=\"color:inherit;text-decoration:none\"><b>Praxis</b></a>", 1)
            s = s.replace("</span></header>", " · <a href=\"./\">all clips</a></span></header>", 1)
            n += 1
        _write(out / p.name, s)
    for name in sorted(videos):
        src = ROOT / "data/raw/cc4d/videos" / name
        if not src.exists():
            raise FileNotFoundError(f"{src} (run `praxis.cli download --split eval`)")
        _link(src, SITE / "videos" / name)
    return n


# ---------------------------------------------------------------------------------------------- studio replays
STUDIO_CSS = """<style>
body[data-static] #view-live, body[data-static] nav a[href="#/live"], body[data-static] .pills { display: none !important; }
.static-note { margin: 0; padding: 10px 20px; background: #eef7f2; border-bottom: 1px solid #d5ecdf; font-size: 13px; color: #24543c; }
</style>
"""
STUDIO_NOTE = ("<p class=\"static-note\">Saved Praxis Studio sessions, replayed from their run logs. Everything on the video "
               "is live engine output recorded during the session. Live mode runs on a local machine with the models, so "
               "it isn't hosted here. <a href=\"/\">Praxis home</a></p>")


def build_studio(extra: list[str]) -> list[dict]:
    from .studio import server
    from .studio.core import SESSIONS
    out = SITE / "studio"
    static = Path(server.STATIC)
    for f in ("app.js", "hud.js", "style.css"):
        _write(out / "static" / f, (static / f).read_text())
    page = (static / "index.html").read_text()
    page = page.replace('"/static/', '"static/').replace("</head>", STUDIO_CSS + "</head>", 1)
    page = page.replace("<body>", '<body data-static="1">', 1).replace("</header>", "</header>\n" + STUDIO_NOTE, 1)
    _write(out / "index.html", page)

    keep = [s for s in server.sessions() if s.get("input") == "clip" or s["id"] in extra]
    _write(out / "data/status.json", {"models": {}, "library": [], "clips": [], "label": server.LABEL})
    _write(out / "data/sessions.json", keep)
    for s in keep:
        sid = s["id"]
        _write(out / "data/sessions" / f"{sid}.json", server.session_detail(sid))
        for name in sorted(server.SESSION_FILES):
            if (SESSIONS / sid / name).exists():
                _link(SESSIONS / sid / name, out / "files" / sid / name)
    return keep


# ---------------------------------------------------------------------------------------------- landing page
CLIP_TITLES = {
    "caught_mistake": "Catches a mistake, with the fix",
    "caught_mistake_2": "Catches the wrong ingredient",
    "step_tracking": "Follows you step by step",
    "recognition_and_tracking": "Recognizes the task by itself",
    "view_request": "Asks for a better view instead of guessing",
    "failure_false_alarm": "Failure case: a false alarm",
    "failure_wrong_task": "Failure case: the wrong task",
}
CLIP_ORDER = ["caught_mistake", "caught_mistake_2", "step_tracking", "recognition_and_tracking", "view_request",
              "failure_false_alarm", "failure_wrong_task"]


def pct(x: float) -> str:
    return f"{round(100 * x)}%"


def _clip_card(r: dict) -> str:
    user = next(f for f in r["files"] if f.endswith("_user.mp4"))
    eng = next((f for f in r["files"] if f.endswith("_engineer.mp4")), None)
    said = f'<p class="said">“{e(r["text"])}”</p>' if r.get("text") else ""
    gt = f'<p class="gt">Annotated error in the dataset: <b>{e("; ".join(r["gt"]))}</b></p>' if r.get("gt") else ""
    fail = " fail" if r["kind"].startswith("failure") else ""
    links = f' · <a href="/{e(eng)}">engineer view</a>' if eng else ""
    return f"""<article class="clip{fail}">
  <video src="/{e(user)}#t=0.1" controls muted playsinline preload="metadata"></video>
  <div class="clip-body"><h3>{e(CLIP_TITLES.get(r["kind"], r["kind"]))}</h3>{said}{gt}
  <p class="meta">Clip {e(r["clip"])} · chosen by rule: {e(r["selection"])}{links}</p></div>
</article>"""


def landing(m: dict, ridx: dict, n_viewer: int, sessions: list[dict], live: dict) -> str:
    d, o, b = m["data"], m["run_fused_oracle"], m["run_baseline_stateless"]
    rec, mix, sem, semb = m["recognition"], m["call_mix_fused_oracle"], m["semantic_fused_oracle"], m["semantic_baseline_stateless"]
    jev = m["verifier_compare"]["by_verifier"]["jev"]
    src = m["_sources"]
    t_live = live["task_recognized"][0]["t"] if live.get("task_recognized") else None
    lag = live["summary"]["tick_lag_s"]["max"]
    l1_ms = live["summary"]["l1_frame_ms"]["p50"]
    degraded = [v for k, v in m["uncertainty"]["modes"].items() if k != "none"]
    ask = [v["engine_view_request_rate"] for v in degraded]
    wrong = [v["threshold_sweep"]["0.5"]["baseline_confident_wrong_step"] for v in degraded]
    never = max(v["engine_confident_wrong_rate"] for v in degraded) == 0
    rendered = {r["kind"]: r for r in ridx["rendered"]}
    hero = rendered["caught_mistake"]
    hero_user = next(f for f in hero["files"] if f.endswith("_user.mp4"))
    cards = "\n".join(_clip_card(rendered[k]) for k in CLIP_ORDER if k in rendered)

    def stat(big: str, label: str, sub: str, source: str) -> str:
        return (f'<div class="stat"><div class="big">{big}</div><div class="label">{label}</div>'
                f'<div class="sub">{sub}</div><div class="src">{e(source)}</div></div>')

    stats = "".join([
        stat(pct(o["step_acc"]), "step accuracy, task known",
             f'A frontier model called every 5 s without state: {pct(b["step_acc"])}.', src["run_fused_oracle"]),
        stat(f'${o["cost_usd_per_video_min"]:.3f}', "per minute of video",
             f'The stateless baseline costs ${b["cost_usd_per_video_min"]:.3f}. Most checks are fast typed questions.',
             src["run_fused_oracle"]),
        stat(pct(rec["top1"]), "recipes recognized with no setup",
             f'Median time to recognize: {rec["t_recognize_s"]["p50"]:.0f} s.', src["recognition"]),
        stat(pct(mix["fast_tier_share"]), "of model calls answered by the fast tier",
             f'Jev answers in {jev["latency_ms"]["p50"]:.0f} ms (median). Only {pct(o["escalated_frame_share"])} of frames '
             f'leave the local layers at all.', "results/metrics.json (call mix, from the run logs)"),
        stat(f"{lag:.1f} s", "worst lag running live",
             f'A recording fed through the live loop at real-time speed. Local layers: {l1_ms:.0f} ms per frame'
             + (f'; recipe recognized at {t_live:.0f} s.' if t_live is not None else "."),
             "results/live/live_replay_async.json"),
        stat(f"{pct(min(ask))[:-1]}–{pct(max(ask))}", "asked for a better view when the view was bad",
             f'Blur, occlusion or the step cropped out, on {m["uncertainty"]["n"]} checks'
             + ("; it was never confidently wrong." if never else ".")
             + f' The stateless baseline named the wrong step at 50%+ confidence on {pct(min(wrong))[:-1]}–{pct(max(wrong))}.',
             src["uncertainty"]),
    ])
    n_sessions = len(sessions)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Praxis · AI guidance for the physical world</title>
<meta name="description" content="Praxis watches a first-person video stream, tracks where you are in a task and coaches you through it. Prototype v0, measured on public data.">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%231c1e22'/%3E%3Ccircle cx='16' cy='16' r='6' fill='%232bb673'/%3E%3C/svg%3E">
<link rel="stylesheet" href="/site.css">
</head>
<body>
<header class="top"><div class="wrap">
  <a class="mark" href="/"><span class="dot"></span>Praxis</a>
  <nav><a href="#results">Results</a><a href="#clips">Clips</a><a href="/viewer/">Viewer</a><a href="/studio/">Studio replays</a></nav>
</div></header>

<section class="hero"><div class="wrap hero-grid">
  <div>
    <p class="eyebrow">Prototype v0 · real model output on public data</p>
    <h1>Instructions that can finally see how you're doing.</h1>
    <p class="lede">AI guidance for the physical world. Praxis watches a first-person video stream, works out the task,
    tracks which step you're on and coaches you through it, catching mistakes with a specific fix.</p>
    <div class="cta"><a class="btn primary" href="#clips">Watch the clips</a><a class="btn" href="/viewer/">Browse all {n_viewer} evaluation clips</a></div>
  </div>
  <figure class="hero-video">
    <video src="/{e(hero_user)}" autoplay muted loop playsinline preload="auto"></video>
    <figcaption>Engine output on held-out clip {e(hero["clip"])}. Praxis said “{e(hero["text"])}” The dataset's annotation
    for that moment: “{e("; ".join(hero["gt"]))}”.</figcaption>
  </figure>
</div></section>

<section id="results" class="band"><div class="wrap">
  <h2>Measured on {d["eval_clips"]} held-out clips</h2>
  <p class="intro">{d["eval_minutes"]:.0f} minutes of first-person video from the public CaptainCook4D dataset: {d["procedure_types"]} recipes,
  {d["eval_gt_step_segments"]} annotated steps and {d["eval_gt_timed_mistakes"]} annotated mistakes. All labels are the dataset's.
  Each figure names the results file it comes from.</p>
  <div class="stats">{stats}</div>
  <div class="weak">
    <h3>Where it's still weak</h3>
    <ul>
      <li><b>Mistakes.</b> Strictly judged, {sem["semantic_yes"]} of Praxis's {sem["n_alerts"]} mistake alerts named the actual
      annotated error; the stateless baseline managed {semb["semantic_yes"]} of {semb["n_alerts"]}. Both catch only a small share of
      the {sem["n_gt_mistakes"]} annotated errors. <span class="src">{e(src["semantic_fused_oracle"])}</span></li>
      <li><b>Recognition.</b> {pct(1 - rec["top1"])} of clips were announced as the wrong recipe or not recognized. One is in the clips below.</li>
      <li><b>Hardware.</b> Not tested on smart glasses yet. It runs live on a camera stream; glasses are one more input adapter.</li>
    </ul>
  </div>
</div></section>

<section id="clips"><div class="wrap">
  <h2>Real engine output</h2>
  <p class="intro">Every clip is drawn from a saved run log, and the rule that picked it is written under it. Development clips
  were excluded from selection. The two failure cases are picked by rule too.</p>
  <div class="clips">{cards}
    <article class="clip">
      <video src="/renders/live_replay_user.mp4#t=0.1" controls muted playsinline preload="metadata"></video>
      <div class="clip-body"><h3>Running live, in real time</h3>
      <p class="meta">A recorded clip fed through the live loop at wall-clock speed, with model calls running in the
      background so the loop never waits on the network. Source: results/live/live_replay_async.json</p></div>
    </article>
  </div>
</div></section>

<section class="band"><div class="wrap">
  <h2>Look closer</h2>
  <div class="explore">
    <a class="card" href="/viewer/"><h3>Clip viewer →</h3><p>All {n_viewer} evaluation clips. Each page syncs the video with the
    engine's belief over the task's steps, the event log (verifier calls and coaching actions) and the clip's metrics.</p></a>
    <a class="card" href="/studio/"><h3>Studio session replays →</h3><p>{n_sessions} session{'s' if n_sessions != 1 else ''} run through Praxis
    Studio's live loop on test clips: the coaching HUD, the engineer panel, flags and the full run log.</p></a>
  </div>
</div></section>

<section><div class="wrap">
  <h2>How it works</h2>
  <p class="intro">Layers of our own run on the laptop on every frame. A frontier model is a swappable verifier, only asked
  when the local layers aren't sure.</p>
  <ol class="layers">
    <li><span>L1</span><div><b>Perception.</b> SigLIP 2 and V-JEPA 2 features and hand landmarks, computed locally.</div></li>
    <li><span>L2</span><div><b>Events.</b> A learned detector for step boundaries and grasps.</div></li>
    <li><span>L3</span><div><b>Task graphs.</b> Instructions compiled into typed steps, visual end states, checks and common mistakes. A recognizer picks the task from video.</div></li>
    <li><span>L4</span><div><b>State tracker.</b> A Bayesian belief over where you are in the task, updated from local evidence and verifier answers.</div></li>
    <li><span>L5</span><div><b>Verifier.</b> Fast typed checks (Jev, calibrated), with ambiguous ones escalated to Claude Opus in the background.</div></li>
    <li><span>L6</span><div><b>Policy.</b> When to speak, how much detail, when to flag a mistake, when to ask for a better view.</div></li>
    <li><span>L7</span><div><b>Flywheel.</b> Run logs become training records; a local student distilled from the verifier takes routine checks.</div></li>
  </ol>
</div></section>

<footer><div class="wrap">
  <p>Praxis · Monish Saravana · <a href="https://monishsaravana.com">monishsaravana.com</a></p>
  <p class="small">Videos: CaptainCook4D (Peddi et al., <i>CaptainCook4D: A dataset for understanding errors in procedural
  activities</i>, arXiv:2312.14556), Apache-2.0; HUD overlays added by Praxis. This site is static: it replays recorded output
  and calls no model.</p>
</div></footer>
</body>
</html>
"""


SITE_CSS = """:root {
  --ink: #1c1e22; --sub: #5c6068; --line: #e3e5e8; --bg: #f6f7f8; --card: #fff; --green: #2bb673; --green-ink: #17784a;
  --amber: #f5a623; --font: "Avenir Next", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Helvetica, Arial, sans-serif;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin: 0; font-family: var(--font); color: var(--ink); background: var(--card); font-size: 16px; line-height: 1.55; }
a { color: var(--green-ink); }
.wrap { max-width: 1120px; margin: 0 auto; padding: 0 24px; }
.top { position: sticky; top: 0; z-index: 5; background: rgba(255,255,255,.92); backdrop-filter: blur(8px); border-bottom: 1px solid var(--line); }
.top .wrap { display: flex; align-items: center; justify-content: space-between; height: 56px; gap: 16px; }
.mark { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 18px; color: var(--ink); text-decoration: none; }
.mark .dot { width: 12px; height: 12px; border-radius: 50%; background: var(--green); box-shadow: 0 0 0 4px #2bb67326; }
nav { display: flex; gap: 20px; }
nav a { color: var(--sub); text-decoration: none; font-weight: 500; font-size: 14px; white-space: nowrap; }
nav a:hover { color: var(--ink); }
section { padding: 72px 0; }
.band { background: var(--bg); border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
h1 { font-size: clamp(32px, 4.4vw, 50px); line-height: 1.08; letter-spacing: -.02em; margin: 10px 0 18px; }
h2 { font-size: clamp(24px, 3vw, 32px); letter-spacing: -.01em; margin: 0 0 10px; }
h3 { font-size: 17px; margin: 0 0 6px; }
.eyebrow { margin: 0; font-size: 13px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--green-ink); }
.lede { font-size: 18px; color: var(--sub); max-width: 34em; }
.intro { color: var(--sub); max-width: 46em; margin: 0 0 28px; }
.hero { padding: 56px 0 72px; }
.hero-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.15fr); gap: 48px; align-items: center; }
.hero-video { margin: 0; }
.hero-video video { width: 100%; aspect-ratio: 16 / 9; object-fit: cover; border-radius: 14px; background: #000; box-shadow: 0 18px 50px -18px #1c1e2266; }
figcaption { font-size: 13px; color: var(--sub); margin-top: 10px; }
.cta { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 26px; }
.btn { display: inline-block; padding: 11px 18px; border-radius: 10px; border: 1px solid #c9ccd1; color: var(--ink); text-decoration: none; font-weight: 600; font-size: 15px; background: #fff; }
.btn.primary { background: var(--ink); border-color: var(--ink); color: #fff; }
.btn:hover { border-color: var(--ink); }
.stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
.stat { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 18px 18px 14px; display: flex; flex-direction: column; }
.stat .big { font-size: 38px; font-weight: 700; letter-spacing: -.02em; line-height: 1.1; font-variant-numeric: tabular-nums; }
.stat .label { font-weight: 600; margin: 4px 0 8px; }
.stat .sub { color: var(--sub); font-size: 14px; flex: 1; }
.src { display: block; margin-top: 10px; font: 11px/1.4 Menlo, ui-monospace, monospace; color: #8a8f97; word-break: break-word; }
.weak { margin-top: 22px; background: var(--card); border: 1px solid var(--line); border-left: 4px solid var(--amber); border-radius: 10px; padding: 16px 20px; }
.weak ul { margin: 6px 0 0; padding-left: 18px; color: var(--sub); }
.weak li { margin: 6px 0; }
.weak b { color: var(--ink); }
.weak .src { display: inline; margin: 0 0 0 4px; }
.clips { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }
.clip { border: 1px solid var(--line); border-radius: 14px; overflow: hidden; background: var(--card); display: flex; flex-direction: column; }
.clip video { width: 100%; aspect-ratio: 16 / 9; background: #000; display: block; }
.clip-body { padding: 14px 16px 16px; }
.clip.fail h3 { color: #b42318; }
.said { margin: 4px 0; font-style: italic; }
.gt { margin: 4px 0; font-size: 14px; color: var(--sub); }
.meta { margin: 8px 0 0; font-size: 13px; color: #80858d; }
.explore { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.card { display: block; background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 22px; color: var(--ink); text-decoration: none; transition: border-color .15s, transform .15s; }
.card:hover { border-color: var(--ink); transform: translateY(-2px); }
.card p { margin: 0; color: var(--sub); }
.layers { list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 10px 32px; }
.layers li { display: flex; gap: 14px; align-items: baseline; padding: 10px 0; border-bottom: 1px solid var(--line); }
.layers span { font: 600 12px Menlo, ui-monospace, monospace; color: var(--green-ink); background: #e6f6ee; border-radius: 6px; padding: 2px 6px; }
.layers div { color: var(--sub); }
.layers b { color: var(--ink); }
footer { border-top: 1px solid var(--line); padding: 28px 0 40px; color: var(--sub); font-size: 14px; }
footer .small { font-size: 12px; max-width: 60em; }
@media (max-width: 960px) { .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 560px) { .stats { grid-template-columns: 1fr; } }
@media (max-width: 860px) {
  .hero-grid, .explore, .layers { grid-template-columns: 1fr; }
  .hero-grid { gap: 28px; }
  section { padding: 52px 0; }
  .wrap { padding: 0 16px; }
  nav { gap: 14px; }
  nav a[href="#results"], nav a[href="#clips"] { display: none; }
  .clips { grid-template-columns: 1fr; }
}
"""


def build(extra_sessions: list[str] | None = None) -> Path:
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()
    m = json.loads((RESULTS / "metrics.json").read_text())
    ridx = json.loads((RESULTS / "renders_index.json").read_text())
    live = json.loads((RESULTS / "live/live_replay_async.json").read_text())
    for r in ridx["rendered"]:
        for f in r["files"]:
            _link(ROOT / f, SITE / f)
    _link(RENDERS / "live_replay_user.mp4", SITE / "renders/live_replay_user.mp4")
    n_viewer = build_viewer()
    sessions = build_studio(extra_sessions or [])
    _write(SITE / "site.css", SITE_CSS)
    _write(SITE / "index.html", landing(m, ridx, n_viewer, sessions, live))
    _write(SITE / "404.html", "<!doctype html><meta charset='utf-8'><title>Not found · Praxis</title><body style='font:16px "
           "-apple-system,sans-serif;margin:48px'><h2>Not found</h2><p><a href='/'>Praxis home</a></p>")
    print(f"site: {SITE} · {n_viewer} viewer clips · {len(sessions)} Studio sessions")
    return SITE


# ---------------------------------------------------------------------------------------------- deploy
TEXT_TYPES = {".md": "text/plain; charset=utf-8", ".jsonl": "text/plain; charset=utf-8"}


def deploy() -> None:
    """Pages and data revalidate on every visit; videos are cached for a day. Text files that browsers would download
    (.md, .jsonl) are served as plain text."""
    def aws(*args: str) -> None:
        print("aws", " ".join(args), flush=True)
        subprocess.run(["aws", *args], check=True)

    if not (SITE / "index.html").exists():
        raise SystemExit("build first: python -m praxis.site build")
    if not DISTRIBUTION:
        raise SystemExit("set DISTRIBUTION in praxis/site.py")
    dest = f"s3://{BUCKET}"
    aws("s3", "sync", str(SITE), dest, "--delete", "--exclude", "*.DS_Store", "--exclude", "*.mp4", "--exclude", "*.md",
        "--exclude", "*.jsonl", "--cache-control", "no-cache")
    for ext, ctype in TEXT_TYPES.items():
        aws("s3", "sync", str(SITE), dest, "--exclude", "*", "--include", f"*{ext}", "--content-type", ctype,
            "--cache-control", "no-cache")
    aws("s3", "sync", str(SITE), dest, "--exclude", "*", "--include", "*.mp4", "--content-type", "video/mp4",
        "--cache-control", "public, max-age=86400")
    aws("cloudfront", "create-invalidation", "--distribution-id", DISTRIBUTION, "--paths", "/*", "--query", "Invalidation.Id",
        "--output", "text")
    print(f"deployed: https://{DOMAIN}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--session", action="append", default=[], help="also export this saved session (camera/upload)")
    sub.add_parser("deploy")
    a = ap.parse_args()
    if a.cmd == "build":
        build(a.session)
    else:
        deploy()


if __name__ == "__main__":
    main()
