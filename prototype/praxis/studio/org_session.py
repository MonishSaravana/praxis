"""A Studio live session for one company profile.

The engine's library is that company's approved procedures (each at its approved version); in locked mode only the
assigned ones, and a single assigned procedure starts at once with no recognition or drafting. Recognition over the
company library uses the same zero-shot recognizer the harness falls back to (SigLIP2 frame vs each graph's title)
plus the verifier's typed "which task?" check. The live engine sees compiled graphs only; knowledge cards are sent
to the browser per step (a safety banner for steps a manager marked safety-critical) and back the question box.
"""
from __future__ import annotations

import json

import numpy as np

from ..knowledge.store import Org
from .session import StudioSession

LIVE: dict[str, "OrgStudioSession"] = {}         # running company sessions by session id (for the question box)


def runtime_library(org: Org, texts, only: list[str] | None = None):
    """(graphs, evidence, info) for the engine: approved versions only. info[task_id] = proc id, version, cards,
    safety steps, source document."""
    from ..evidence import ZeroShotEvidence
    from ..knowledge.compile import embed_version
    from ..knowledge.refs import load_probe
    graphs, evidence, info = {}, {}, {}
    for tid, x in org.library(only).items():
        g = x["graph"]
        if not x["emb"].exists():
            embed_version(org, x["proc_id"], x["version"], texts)
        z = np.load(x["emb"])
        graphs[tid] = g
        probe = load_probe(org, x["proc_id"], x["version"])      # trained on marked reference recordings, if any
        evidence[tid] = probe if probe is not None else ZeroShotEvidence(g, {k: z[k] for k in z.files})
        ver = next(v for v in x["proc"]["versions"] if v["version"] == x["version"])
        info[tid] = {"proc_id": x["proc_id"], "version": x["version"], "cards": x["cards"],
                     "local": "reference recordings" if probe is not None else "document only",
                     "safety": x["review"].get("safety", []), "doc": ver.get("doc_hash"), "paged": ver.get("paged", True),
                     "refs": x.get("refs") or {}, "task_emb": np.asarray(z["task"], np.float32).reshape(1, -1)}
    return graphs, evidence, info


class OrgCoreView:
    """StudioCore as one company's session sees it: same models and engine config, the company's library."""

    def __init__(self, core, org: Org, only: list[str] | None):
        self.core, self.org = core, org
        self.graphs, self.evidence, self.info = runtime_library(org, core.texts(), only)

    def __getattr__(self, name):
        return getattr(self.core, name)

    def session_stack(self) -> dict:
        from ..tasks.recognizer import TaskRecognizer
        st = dict(self.core.stack)
        tids = sorted(self.graphs)
        te = np.concatenate([self.info[t]["task_emb"] for t in tids])
        rec = TaskRecognizer(task_ids=tids, text_emb=te)
        rec.reset()
        st.update(library=dict(self.graphs), evidence=dict(self.evidence), recognizer=rec)
        return st

    def library(self) -> list[dict]:
        return [{"task_id": t, "title": g.title, "domain": g.domain, "n_steps": len(g.nodes), "source": "company",
                 "trained": False} for t, g in self.graphs.items()]

    def graph(self, task_id: str):
        return self.graphs.get(task_id)


class OrgStudioSession(StudioSession):
    def __init__(self, core, cfg: dict, send):
        org = Org(cfg["org_id"])
        s = org.settings()
        self.org, self.locked = org, bool(s["locked"])
        assigned = [p for p in s["assigned"] if p]
        if self.locked and not assigned:
            raise ValueError("locked mode is on but no procedure is assigned (admin page)")
        view = OrgCoreView(core, org, assigned if self.locked else None)
        if not view.graphs:
            raise ValueError("this company has no approved procedures yet (approve one on the admin page)"
                             if not self.locked else "the assigned procedure has no approved version yet")
        cfg = dict(cfg)
        if cfg.get("task_mode") == "paste":
            raise ValueError("with a company profile, procedures come from the admin page, not pasted text")
        if self.locked:
            if len(view.graphs) == 1:
                cfg["task_mode"], cfg["task_id"] = "assigned", next(iter(view.graphs))
            elif cfg.get("task_mode") == "library" and cfg.get("task_id") in view.graphs:
                cfg["task_mode"] = "assigned"
            else:
                cfg["task_mode"] = "auto"           # several assigned: closed-set recognition among them only
        elif cfg.get("task_mode") == "library" and cfg.get("task_id") not in view.graphs:
            raise ValueError("pick one of this company's approved procedures")
        cfg["org_name"] = org.meta["name"]
        cfg["org_locked"] = self.locked
        cfg["org_procedures"] = {t: {"proc_id": i["proc_id"], "version": i["version"], "local_tracking": i["local"]}
                                 for t, i in view.info.items()}
        self.view = view
        self.cur: dict = {"task_id": None, "node": None}
        self.warned: set = set()
        super().__init__(view, cfg, send)
        LIVE[self.id] = self
        self.log.write("org", 0.0, org=org.id, locked=self.locked, procedures=cfg["org_procedures"])

    # ---------------------------------------------------------------- task choice
    def _apply_task_choice(self) -> None:
        if self.cfg.get("task_mode") == "assigned":
            self.eng.start_task(0.0, self.cfg["task_id"], how="assigned")
        else:
            super()._apply_task_choice()

    def _describe(self, text: str, t: float, at_s: float = 0.0) -> None:
        if not self.locked:
            return super()._describe(text, t, at_s)
        from .tasks import match_library
        m = match_library(text, self.core.library())
        self.log.write("described", t, text=text, matched=m, locked=True)
        if m:
            self.eng.start_task(t, m, how="described")
        else:                                       # locked: never draft or switch to an unassigned task
            names = ", ".join(g.title for g in self.view.graphs.values())
            self.send({"type": "org_notice", "text": f"This job is locked to: {names}."})

    # ---------------------------------------------------------------- records -> browser
    def _on_line(self, line: str) -> None:
        super()._on_line(line)
        r = json.loads(line)
        k = r["kind"]
        if k == "task" or (k == "task_state" and r.get("to") == "active"):
            if r.get("task_id") in self.view.info and r["task_id"] != self.cur["task_id"]:
                self.cur = {"task_id": r["task_id"], "node": None}
                info = self.view.info[r["task_id"]]
                self.send({"type": "org_task", "task_id": r["task_id"], "title": self.view.graphs[r["task_id"]].title,
                           "version": info["version"], "procedure_cards": info["cards"].get("_procedure", [])})
        if k == "action" and r.get("node") and self.cur["task_id"] in self.view.info and r["node"] != self.cur["node"]:
            self.cur["node"] = r["node"]
            self.send({"type": "org_step", **self.step_context()})
            info = self.view.info[self.cur["task_id"]]
            if r["node"] in info["safety"] and (self.cur["task_id"], r["node"]) not in self.warned:
                self.warned.add((self.cur["task_id"], r["node"]))
                ctx = self.step_context()
                warn = [c for c in ctx["cards"] if c["kind"] in ("warning", "safety")]
                specs = [c for c in ctx["cards"] if c["kind"] == "spec"]
                if warn:
                    text, page = warn[0]["text"], warn[0].get("page")
                elif specs:                         # no written warning: say the step's own spec, as the procedure states it
                    c = specs[0]
                    text = f"{ctx['name']}. The procedure says: {c['text']}" + (f" (step {c['step_no']})" if c.get("step_no") else "")
                    page = c.get("page")
                else:
                    text, page = f"{ctx['name']}. Follow the procedure exactly.", None
                self.log.write("org_safety", r["t"], node=r["node"], text=text, page=page)
                self.send({"type": "org_safety", "node": r["node"], "name": ctx["name"], "text": text,
                           "page": page if info["paged"] else None})

    def step_context(self) -> dict | None:
        """The current step as the question box sees it: names, instruction and cards (never document text)."""
        tid, nid = self.cur["task_id"], self.cur["node"]
        if tid not in self.view.info:
            return None
        g, info = self.view.graphs[tid], self.view.info[tid]
        n = g.node(nid) if nid in g.ids else None
        return {"task_id": tid, "task": g.title, "node": nid, "name": n.name if n else "",
                "instruction": n.instruction_novice if n else "", "cards": info["cards"].get(nid, []) if n else [],
                "procedure_cards": info["cards"].get("_procedure", []), "safety": bool(n and nid in info["safety"]),
                "doc": info["doc"], "paged": info["paged"], "version": info["version"], "proc_id": info["proc_id"],
                "ref": (info["refs"].get(nid) or {}).get("file") if n else None,
                "index": g.ids.index(nid) + 1 if n else None, "n_steps": len(g.nodes)}

    def stop(self) -> dict:
        out = super().stop()
        LIVE.pop(self.id, None)
        return out


def latest_live(org_id: str | None = None) -> OrgStudioSession | None:
    live = [s for s in LIVE.values() if not s.stopped and (org_id is None or s.org.id == org_id)]
    return max(live, key=lambda s: s.t_start) if live else None
