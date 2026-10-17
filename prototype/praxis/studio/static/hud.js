// User-view HUD and engineer panel, drawn only from run-log records (the same rules as praxis/render/hud.py).
// The user view never shows the step graph: a progress pill, a short instruction chip, a check pulse, an amber
// mistake card and a view-request card with an arrow. The engineer panel is a separate, optional view.

export const CARD_DUR = { announce_task: 3.6, instruct: 4.0, hint: 6.5, mistake: 6.5, view_request: 5.5, done: 4.0, ask: 1e9 };
const PRIORITY = { mistake: 3, view_request: 3, ask: 3, hint: 2, announce_task: 1, instruct: 1, done: 1 };
const HEAD = {
  announce_task: "Task recognized", instruct: null, hint: "Here's a closer walkthrough",
  mistake: "Something looks off", view_request: "I can't see that clearly", done: "Done", ask: "What are you working on?",
};
const SPEAK = new Set(["announce_task", "instruct", "mistake", "view_request", "hint", "done"]);

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// Everything the HUD needs, accumulated from records (live: as they arrive; replay: the whole log).
export class LogState {
  constructor() { this.reset(); }
  reset() {
    this.records = []; this.cards = []; this.commits = []; this.beliefs = []; this.fast = []; this.calls = [];
    this.actions = []; this.task = null; this.nSteps = null; this.recog = null; this.flags = []; this.tasks = []; this.recogs = [];
  }
  add(r, shownAt = null) {
    this.records.push(r);
    const k = r.kind;
    if (k === "action") {
      this.actions.push(r);
      if (CARD_DUR[r.action] !== undefined) {
        const d = r.detail || {};
        let head = HEAD[r.action];
        if (r.action === "announce_task" && d.how && d.how !== "recognized") head = d.draft ? "Drafted a plan" : "Got it";
        if (r.action === "announce_task" && d.draft) head = "Drafted a plan";
        this.cards.push({ t: shownAt ?? r.t, kind: r.action, text: r.text, detail: d, node: r.node, head });
      }
    } else if (k === "commit") this.commits.push(r);
    else if (k === "belief") this.beliefs.push(r);
    else if (k === "fast") this.fast.push(r);
    else if (k === "task") { this.task = r; this.nSteps = r.n_steps; this.tasks.push(r); }
    else if (k === "recognizer") { this.recog = r; this.recogs.push(r); }
    else if (k === "flag") this.flags.push(r);
    if (k === "verdict" || k === "step_choice" || k === "task_check" || k === "task_draft") this.calls.push(r);
  }
  addAsk(t) { this.cards.push({ t, kind: "ask", text: "Tell me what you're doing and I'll make a plan for it.", detail: {}, head: HEAD.ask }); }
  clearAsk() { this.cards = this.cards.filter((c) => c.kind !== "ask"); }
  taskAt(tau) { let t = null; for (const x of this.tasks) { if (x.t <= tau) t = x; } return t; }
  progress(tau) {
    const t0 = this.taskAt(tau)?.t ?? -1;
    return new Set(this.commits.filter((c) => c.t <= tau && c.t >= t0).map((c) => c.node)).size;
  }
  card(tau) {
    const live = this.cards.filter((c) => c.t <= tau && tau < c.t + CARD_DUR[c.kind]);
    if (!live.length) return [null, 0];
    const top = Math.max(...live.map((c) => PRIORITY[c.kind]));
    const c = live.filter((x) => PRIORITY[x.kind] === top).at(-1);
    const age = tau - c.t, dur = CARD_DUR[c.kind];
    return [c, Math.max(0, Math.min(1, age / 0.25, (dur - age) / 0.4))];
  }
  chip(tau, names) {
    const ins = this.cards.filter((c) => c.kind === "instruct" && c.t <= tau);
    if (!ins.length || this.actions.some((a) => a.action === "done" && a.t <= tau)) return null;
    const last = ins.at(-1);
    return last.detail.chip || (names && names[last.node]) || last.text;
  }
  pulse(tau) {
    const v = this.actions.filter((a) => a.action === "verified" && tau - a.t >= 0 && tau - a.t < 0.9);
    return v.length ? 1 - (tau - v.at(-1).t) / 0.9 : 0;
  }
  belief(tau) { let b = null; for (const x of this.beliefs) { if (x.t <= tau) b = x; else break; } return b; }
}

export function speakable(r) { return r.kind === "action" && SPEAK.has(r.action); }

const ARROW_ANG = { right: 0, "down-right": 45, down: 90, "down-left": 135, left: 180, "up-left": 225, up: 270, "up-right": 315 };
function arrowSvg(dir) {
  if (dir === "rotate") return `<svg viewBox="-40 -40 80 80"><path d="M 25 -15 A 30 30 0 1 0 28 10" fill="none" stroke="currentColor" stroke-width="7" stroke-linecap="round"/><path d="M 16 -27 L 30 -14 L 12 -8 Z" fill="currentColor"/></svg>`;
  if (!(dir in ARROW_ANG)) return `<svg viewBox="-40 -40 80 80"><circle r="32" fill="none" stroke="currentColor" stroke-width="5"/><circle r="17" fill="none" stroke="currentColor" stroke-width="5"/></svg>`;
  return `<svg viewBox="-40 -40 80 80" style="transform:rotate(${ARROW_ANG[dir]}deg)"><line x1="-28" y1="0" x2="20" y2="0" stroke="currentColor" stroke-width="8" stroke-linecap="round"/><path d="M 34 0 L 12 -16 L 12 16 Z" fill="currentColor"/></svg>`;
}

// The user view: DOM overlay on the video stage.
export class Hud {
  constructor(stage, badge) {
    this.el = document.createElement("div");
    this.el.className = "hud";
    this.el.innerHTML = `
      <div class="pill hidden"><div class="pulse"><svg viewBox="-12 -12 24 24"><circle r="10" class="ring"/><path d="M-5 0 L-1.5 3.6 L5.5 -4" class="tick"/></svg></div>
        <span class="k">0/0</span><div class="bar"><div class="fill"></div></div></div>
      <div class="card hidden"><div class="accent"></div><div class="body"><div class="head"></div><div class="text"></div><ol class="subs"></ol>
        <form class="ask hidden"><input type="text" placeholder="e.g. making pour-over coffee" /><button>Make a plan</button></form></div><div class="arrow"></div></div>
      <div class="chip hidden"></div>
      <div class="badge">${esc(badge)}</div>`;
    stage.appendChild(this.el);
    this.$ = (s) => this.el.querySelector(s);
    this.names = {};
    this.onAsk = null;
    this.$(".ask").addEventListener("submit", (e) => {
      e.preventDefault();
      const v = this.$(".ask input").value.trim();
      if (v && this.onAsk) this.onAsk(v);
    });
  }
  setNames(names) { this.names = names || {}; }
  draw(st, tau) {
    const pill = this.$(".pill");
    const task = st.taskAt(tau);
    if (task && task.n_steps) {
      const k = st.progress(tau), n = task.n_steps;
      pill.classList.remove("hidden");
      this.$(".pill .k").textContent = `${k}/${n}`;
      this.$(".pill .fill").style.width = `${Math.max(4, (100 * k) / n)}%`;
      const p = st.pulse(tau);
      const pu = this.$(".pulse");
      pu.style.opacity = p > 0 ? p : 0;
      pu.style.transform = `scale(${1 + 0.9 * (1 - p)})`;
    } else pill.classList.add("hidden");
    const [c, a] = st.card(tau);
    const card = this.$(".card"), chip = this.$(".chip");
    if (c && a > 0.02) {
      chip.classList.add("hidden");
      card.classList.remove("hidden");
      if (card.dataset.key !== `${c.kind}@${c.t}`) {
        card.dataset.key = `${c.kind}@${c.t}`;
        card.className = `card ${c.kind} ${["mistake", "view_request", "ask"].includes(c.kind) ? "prominent" : ""}`;
        this.$(".card .head").textContent = c.head || "";
        this.$(".card .head").style.display = c.head ? "" : "none";
        const subs = c.kind === "hint" ? (c.detail.substeps || []).slice(0, 4) : [];
        this.$(".card .text").textContent = c.kind === "hint" ? (c.detail.parts_line || "") : c.text;
        this.$(".card .subs").innerHTML = subs.map((s) => `<li>${esc(s)}</li>`).join("");
        this.$(".card .arrow").innerHTML = c.kind === "view_request" ? arrowSvg(c.detail.direction || "closer") : "";
        this.$(".card .ask").classList.toggle("hidden", c.kind !== "ask");
        if (c.kind === "ask") setTimeout(() => this.$(".ask input").focus(), 50);
      }
      card.style.opacity = a;
    } else {
      card.classList.add("hidden");
      card.dataset.key = "";
      const t = st.chip(tau, this.names);
      if (t) { chip.textContent = t.length < 60 ? t : t.slice(0, 57) + "…"; chip.classList.remove("hidden"); }
      else chip.classList.add("hidden");
    }
  }
}

// Engineer panel: step belief over the graph, L2 trace, verifier calls, policy decisions, cost.
export class EngineerPanel {
  constructor(el) {
    this.el = el;
    el.innerHTML = `
      <h3>L4 state tracker · P(step)</h3><div class="beliefs"></div><div class="bmeta mono"></div>
      <h3>L2 event detector · P(step boundary)</h3><canvas class="trace" width="560" height="90"></canvas>
      <h3>L5 verifier calls</h3><div class="calls mono"></div>
      <h3>L6 policy decisions</h3><div class="acts mono"></div>`;
    this.$ = (s) => el.querySelector(s);
    this.nodes = [];
  }
  setNodes(nodes) { this.nodes = nodes || []; }
  draw(st, tau) {
    const b = st.belief(tau), names = Object.fromEntries(this.nodes.map((n) => [n.id, n.name]));
    if (b && this.nodes.length) {
      const done = new Set(b.completed || []);
      this.$(".beliefs").innerHTML = this.nodes.map((n) => {
        const p = (b.p || {})[n.id] || 0, cls = n.id === b.map ? "map" : done.has(n.id) ? "done" : "";
        return `<div class="brow ${cls}"><span class="bn">${done.has(n.id) ? "✓ " : ""}${esc(n.name)}</span><span class="bb"><i style="width:${(100 * p).toFixed(1)}%"></i></span></div>`;
      }).join("");
      this.$(".bmeta").textContent = `entropy ${b.entropy?.toFixed(2)}   time on step ${b.time_on_step?.toFixed(0)}s   profile ${b.user?.profile ?? "-"}`;
    } else if (st.recogs.some((x) => x.t <= tau && x.posterior)) {
      const rec = st.recogs.filter((x) => x.t <= tau && x.posterior).at(-1);
      const top = Object.entries(rec.posterior).sort((x, y) => y[1] - x[1]).slice(0, 5);
      this.$(".beliefs").innerHTML = `<div class="sub">L3b task recognizer (no task yet)</div>` + top.map(([k, v]) =>
        `<div class="brow"><span class="bn">${esc(k.replace("cc4d_", ""))}</span><span class="bb"><i style="width:${(100 * v).toFixed(1)}%"></i></span></div>`).join("");
      this.$(".bmeta").textContent = "";
    }
    const cv = this.$(".trace"), g = cv.getContext("2d");
    g.clearRect(0, 0, cv.width, cv.height);
    const win = 60, f = st.fast.filter((x) => x.t <= tau && x.t > tau - win);
    g.strokeStyle = "#3b82f6"; g.lineWidth = 2; g.beginPath();
    f.forEach((x, i) => { const X = cv.width * (1 - (tau - x.t) / win), Y = cv.height - 6 - (cv.height - 12) * x.boundary; i ? g.lineTo(X, Y) : g.moveTo(X, Y); });
    g.stroke();
    g.fillStyle = "#f5a623";
    st.calls.filter((x) => x.t <= tau && x.t > tau - win).forEach((x) => g.fillRect(cv.width * (1 - (tau - x.t) / win) - 1, cv.height - 6, 2, 6));
    const calls = st.calls.filter((x) => x.t <= tau + 0.01).slice(-9).reverse();
    this.$(".calls").innerHTML = calls.map((r) => {
      const m = (r.model || "?").replace("claude-", "").replace("-1.14.0", "");
      if (r.error) return `<div class="err">${r.t.toFixed(1)}s ${esc(m)} error: ${esc(r.error.slice(0, 60))}</div>`;
      const lat = r.latency_ms ? `${Math.round(r.latency_ms)} ms` : r.latency_s ? `${r.latency_s.toFixed(1)} s` : "";
      let what = "";
      if (r.kind === "verdict") what = `${r.reason}: ${r.status} p=${(r.confidence ?? 0).toFixed(2)}`;
      else if (r.kind === "step_choice") what = `which step? ${esc(names[r.choice] || r.choice)}`;
      else if (r.kind === "task_check") what = `which task? ${esc((r.choice || "").replace("cc4d_", ""))}`;
      else what = `draft: ${esc(r.title || "")}`;
      return `<div>${r.t.toFixed(1)}s ${esc(m)} ${lat} · ${what}</div>`;
    }).join("");
    this.$(".acts").innerHTML = st.actions.filter((a) => a.t <= tau + 0.01).slice(-7).reverse()
      .map((a) => `<div>${a.t.toFixed(1)}s ${a.action}: ${esc(a.text.slice(0, 70))}</div>`).join("");
  }
}
