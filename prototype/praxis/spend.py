"""Tracked API spend for this build, summed only from recorded costs (results/*.json and data/verdicts/*.jsonl).
Cached re-runs are counted once (the first live call). Smoke tests run by hand (fewer than ~100 calls, cents) were
not recorded and are listed as untracked rather than estimated. The provider consoles are the source of truth."""
from __future__ import annotations

import json

from .paths import DATA, RESULTS


def _sum_jsonl(p, key=lambda r: r["verdict"]["raw"].get("orig_cost_usd", r["verdict"].get("cost_usd", 0.0))) -> float:
    tot = 0.0
    for line in p.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            if not r["verdict"]["raw"].get("cached", False):
                tot += key(r) or 0.0
    return tot


def main() -> dict:
    items = {}
    c = json.loads((RESULTS / "l3" / "compile_summary.json").read_text())
    items["L3 compile (8 recipes, Fable 5.1)"] = sum(v["compiler"]["cost_usd"] for v in c.values())
    ir = RESULTS.parent / "prototype" / "taskgraphs" / "industreal_assy.json"
    if ir.exists():
        items["L3 compile (IndustReal graph)"] = json.loads(ir.read_text())["compiler"]["cost_usd"]
    vd = DATA / "verdicts"
    groups = {"GT check runs (Jev/Haiku/Opus, train+eval)": [], "framing ablation": [], "crops experiment": []}
    for p in sorted(vd.glob("*.jsonl")):
        n = p.stem
        if n.startswith("framing_"):
            groups["framing ablation"].append(p)
        elif n.startswith("uncert_"):
            continue      # counted via the uncertainty runs' own budget totals below (avoids double counting)
        elif n.endswith("_crops"):
            groups["crops experiment"].append(p)
        elif n.startswith(("jev_", "claude_")):
            groups["GT check runs (Jev/Haiku/Opus, train+eval)"].append(p)
    for k, ps in groups.items():
        items[k] = sum(_sum_jsonl(p) for p in ps)
    ul = DATA / "uncert.log"     # first full uncertainty run (its results file was later overwritten by a cached re-run)
    if ul.exists():
        import re
        m = re.findall(r"UNCERT_DONE ([0-9.]+)", ul.read_text())
        if m:
            items["visual-uncertainty first run (from data/uncert.log)"] = float(m[0])
    u = RESULTS / "l5" / "visual_uncertainty.json"
    if u.exists():
        items["visual-uncertainty (last re-run, new calls only)"] = json.loads(u.read_text()).get("spend_usd", 0.0)
    for f in sorted((RESULTS / "runs").glob("*.json")):
        r = json.loads(f.read_text())
        items[f"engine run: {f.stem}"] = r.get("spend_usd", r.get("aggregate", {}).get("cost_usd", 0.0))
    for f in sorted((RESULTS / "dev").glob("design_selection_v*.json")):
        r = json.loads(f.read_text())
        items[f"design selection (train split): {f.stem}"] = sum(d.get("spend_usd", 0.0) for d in r["designs"].values())
    for f in sorted((RESULTS / "invalid_runs").glob("*.json")):
        items[f"invalid engine run (quarantined): {f.stem}"] = json.loads(f.read_text()).get("spend_usd", 0.0)
    # mistake judge: each call is paid once, so sum the cost stored with each cached answer
    from .paths import CACHE
    judge = [json.loads(f.read_text()) for f in sorted((CACHE / "api").glob("judge_*/*.json"))]
    items["mistake judge (Opus 5.5)"] = sum(j.get("_cost_usd", 0.0) for j in judge)
    n_judge_unrecorded = sum("_cost_usd" not in j for j in judge)
    # open-set drafting: engine runs (new calls only) + each draft and each draft-judge call once, from their caches
    for f in sorted((RESULTS / "open_set").glob("*.json")):
        items[f"open-set engine runs: {f.stem}"] = json.loads(f.read_text()).get("engine_spend_usd", 0.0)
    items["open-set drafts (Opus 5.5)"] = sum(json.loads(f.read_text()).get("cost_usd", 0.0)
                                              for f in (CACHE / "api").glob("draft_*/*.json"))
    items["open-set draft judge (Opus 5.5)"] = sum(json.loads(f.read_text()).get("_cost_usd", 0.0)
                                                   for f in (CACHE / "api").glob("draftjudge_*/*.json"))
    for f in ("industreal_demo.json", "policy_demo.json"):
        p = RESULTS / f
        if p.exists():
            items[f"demo: {f}"] = json.loads(p.read_text()).get("spend_usd", 0.0)
    for f in sorted((RESULTS / "live").glob("*.json")):
        items[f"live mode: {f.stem}"] = json.loads(f.read_text()).get("spend_usd", 0.0)
    for f in sorted((RESULTS / "live" / "checks").glob("*.json")):     # replay checks (live calls on cache misses)
        items[f"live mode check: {f.stem}"] = json.loads(f.read_text()).get("spend_usd", 0.0)
    m2 = RESULTS / "m2" / "two_clip_test.json"
    if m2.exists():
        items["M2 two-clip test"] = json.loads(m2.read_text()).get("spend", 0.0)
    out = {"total_usd": sum(items.values()), "items": items,
           "untracked": ["hand-run smoke tests and pilots on 2026-10-17 (model pings, Jev image probe, three 24-100 check "
                         "prompt/framing pilots before the framing ablation was formalized, early 3-clip engine tests): not "
                         "recorded per call; small relative to the total",
                         f"{n_judge_unrecorded} mistake-judge calls (Opus 5.5, effort low, one short text prompt each) made "
                         "before the judge stored per-call cost",
                         "design-selection runs deleted after two processes wrote the same logs (WHAT_DIDNT_WORK.md); "
                         "their re-runs reused the cached answers, so those calls' original cost is not in the total"],
           "note": "Cached re-runs are counted once. The Anthropic and TypeSafe consoles are the source of truth."}
    (RESULTS / "spend.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    o = main()
    print(round(o["total_usd"], 2))
    for k, v in sorted(o["items"].items(), key=lambda x: -x[1]):
        print(f"{v:8.3f}  {k}")
