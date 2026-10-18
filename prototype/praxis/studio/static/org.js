// Praxis Studio · company profile on the Live page: pick a company (its approved procedures become the library; in
// locked mode only the assigned one runs), see the current step and its knowledge cards (operator panel), a safety
// banner on the video for steps a manager marked safety-critical, and a question box answered from the company's
// documents. app.js calls window.praxisOrg.startFields() when starting and window.praxisOrg.onMessage(m) per message.
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const KEY = "praxis.org";
const O = { orgs: [], org: null, lib: null, origLib: null, step: null, sessionId: null };

const css = document.createElement("style");
css.textContent = `
.org-setup { margin-bottom: 4px; }
.org-status { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin: 8px 0 2px; font-size: 12px; color: var(--sub); }
.org-status a { color: var(--sub); }
.org-st { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 500; padding: 2px 8px; border-radius: 999px; }
.org-st::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; opacity: .8; }
.org-st.ok { background: #e6f6ee; color: #17784a; } .org-st.lock { background: #e8effd; color: #1d4ed8; } .org-st.warn { background: #fdf3e1; color: #8a5800; }
.org-note { font-size: 12px; color: #33363c; background: #f6f7f8; border-radius: 8px; padding: 8px 10px; margin-top: 8px; line-height: 1.45; }
.orgp { border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px; margin-bottom: 12px; background: #fff; }
.orgp-h { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.orgp-h b { flex: 1; font-size: 14px; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.orgp-h .sub { font-size: 12px; color: var(--sub); font-weight: 400; }
.orgp-step { display: flex; gap: 10px; align-items: flex-start; }
.orgp-step .no { width: 26px; height: 26px; border-radius: 50%; background: #f6f7f8; display: grid; place-items: center; font-size: 12px;
  font-weight: 600; color: #33363c; flex: none; font-variant-numeric: tabular-nums; }
.orgp-step.safety .no { background: #fdf3e1; color: #8a5800; }
.orgp-step .nm { font-weight: 600; font-size: 13px; line-height: 1.35; }
.orgp-step .in { font-size: 12px; color: var(--sub); margin-top: 2px; line-height: 1.4; }
.orgp-step .of { font-size: 11px; color: var(--sub); font-weight: 500; margin-bottom: 2px; }
.orgp .wait { font-size: 12px; color: var(--sub); }
.orgp-cards { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 8px; }
.orgp-card { font-size: 12px; padding: 3px 8px; border-radius: 7px; background: #f6f7f8; border: 1px solid #eceef1; color: #33363c; max-width: 100%;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.orgp-card b { font-weight: 600; color: var(--ink); margin-right: 4px; }
.orgp-card.warning, .orgp-card.safety { background: #fdf3e1; border-color: #f5dcae; }
.orgp-ref { width: 100%; border-radius: 8px; margin-top: 8px; border: 1px solid var(--line); }
.orgp-ask { display: flex; gap: 6px; margin-top: 12px; padding-top: 12px; border-top: 1px solid #eceef1; }
.orgp-ask input { flex: 1; min-width: 0; }
.orgp-ask button { background: var(--ink); color: #fff; border-color: var(--ink); font-weight: 600; }
.orgp-opt { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--sub); margin-top: 6px; cursor: pointer; }
.orgp-ans { margin-top: 10px; font-size: 13px; line-height: 1.45; color: var(--ink); }
.orgp-ans .meta { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-top: 6px; font-size: 11.5px; color: var(--sub); }
.orgp-cite { display: inline-flex; padding: 2px 7px; border-radius: 999px; background: #e8effd; color: #1d4ed8; text-decoration: none; font-weight: 500; }
.orgp-cite:hover { text-decoration: underline; }
.org-safety { position: absolute; left: 50%; top: 2.2cqw; transform: translateX(-50%); z-index: 5; width: 46cqw; display: flex; align-items: center;
  padding: 1.5cqw 1.9cqw 1.5cqw 2.6cqw; border-radius: 1.7cqw; background: rgba(255, 255, 255, .86); color: var(--ink);
  -webkit-backdrop-filter: blur(18px); backdrop-filter: blur(18px); box-shadow: 0 .8cqw 2.4cqw rgba(0, 0, 0, .28);
  animation: orgIn .25s cubic-bezier(.22, 1, .36, 1); }
.org-safety .accent { position: absolute; left: .8cqw; top: 1.5cqw; bottom: 1.5cqw; width: .5cqw; border-radius: .3cqw; background: var(--amber); }
.org-safety .head { font-weight: 600; font-size: 2.1cqw; color: #b77400; margin-bottom: .4cqw; }
.org-safety .text { font-size: 1.85cqw; line-height: 1.32; }
.org-safety.notice .accent { background: var(--blue); } .org-safety.notice .head { color: var(--blue); }
@keyframes orgIn { from { opacity: 0; transform: translate(-50%, -.6cqw); } }
@media (prefers-reduced-motion: reduce) { .org-safety { animation: none; } }
`;
document.head.appendChild(css);

function speak(text) {
  if (!$("#speech")?.checked || !window.speechSynthesis) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 1.05;
  speechSynthesis.speak(u);
}

async function boot() {
  const box = $("#org-setup");
  if (!box) return;
  const r = await fetch("/api/orgs");
  if (!r.ok) return;
  O.orgs = (await r.json()).orgs;
  for (let i = 0; i < 150 && !$("#lib")?.options.length; i++) await new Promise((ok) => setTimeout(ok, 100));  // app.js fills it
  O.origLib = $("#lib")?.innerHTML;
  box.className = "org-setup";
  box.innerHTML = `<h2>Company</h2>
    <select id="org-sel" aria-label="Company profile"><option value="">None · open coach on the built-in library</option>${O.orgs.map((o) =>
      `<option value="${esc(o.id)}">${esc(o.name)}</option>`).join("")}</select>
    <div id="org-info"></div>`;
  $("#org-sel").addEventListener("change", () => choose($("#org-sel").value));
  let saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) { /* storage off */ }
  if (saved && O.orgs.some((o) => o.id === saved)) { $("#org-sel").value = saved; await choose(saved); }
  else if (!O.orgs.length) $("#org-info").innerHTML = `<div class="org-status"><a href="/admin">Set up a company</a> to coach from its own manuals.</div>`;
}

async function choose(id) {
  try { localStorage.setItem(KEY, id); } catch (e) { /* storage off */ }
  O.org = id || null;
  const paste = $("input[name=task][value=paste]")?.closest("label");
  const radios = [...document.querySelectorAll("input[name=task]")];
  radios.forEach((x) => { x.disabled = false; x.closest("label").style.opacity = ""; });
  if (!id) {
    O.lib = null;
    if (O.origLib != null) $("#lib").innerHTML = O.origLib;
    paste?.classList.remove("hidden");
    $("#org-info").innerHTML = "";
    return;
  }
  const lib = await (await fetch(`/api/orgs/${encodeURIComponent(id)}/library`)).json();
  O.lib = lib;
  $("#lib").innerHTML = lib.procedures.map((p) => `<option value="${esc(p.task_id)}">${esc(p.title)} · v${p.version}</option>`).join("")
    || `<option value="">No approved procedures yet</option>`;
  paste?.classList.add("hidden");
  if ($("input[name=task][value=paste]")?.checked) { const a = $("input[name=task][value=auto]"); a.checked = true; a.dispatchEvent(new Event("change")); }
  const k = lib.procedures.length;
  const admin = `<a href="/admin#/${encodeURIComponent(id)}/live">Manage</a>`;
  let html;
  if (lib.locked && k) {
    html = `<div class="org-status"><span class="org-st lock">Locked</span><span>${k === 1 ? esc(lib.procedures[0].title) : `${k} assigned procedures`}</span>${admin}</div>
      <div class="org-note">${k === 1 ? "Starts this procedure as soon as you press Start." : "Recognizes only the assigned procedures."} No other task, no drafted plans.</div>`;
    if (k === 1) radios.forEach((x) => { x.disabled = true; x.closest("label").style.opacity = ".5"; });
  } else if (lib.locked) {
    html = `<div class="org-status"><span class="org-st warn">Locked, nothing assigned</span>${admin}</div>`;
  } else if (k) {
    html = `<div class="org-status"><span class="org-st ok">Open coach</span><span>${k} approved procedure${k === 1 ? "" : "s"}</span>${admin}</div>`;
  } else {
    html = `<div class="org-status"><span class="org-st warn">No approved procedures</span><a href="/admin#/${encodeURIComponent(id)}/procedures">Review procedures</a></div>`;
  }
  $("#org-info").innerHTML = html;
}

function startFields() { return O.org ? { org_id: O.org } : {}; }

function runPanel() {
  const el = $("#org-run");
  if (!el) return null;
  if (!el.dataset.ready) {
    el.innerHTML = `<div class="orgp"><div class="orgp-h"><b id="orgp-name"></b><span id="orgp-mode"></span></div>
      <div id="orgp-step"><div class="wait">Waiting for the first step…</div></div>
      <form class="orgp-ask" id="orgp-ask"><input id="orgp-q" placeholder="Ask: what's the torque? why this step?" autocomplete="off" aria-label="Question"><button>Ask</button></form>
      <label class="orgp-opt"><input type="checkbox" id="orgp-model"> Answer with Claude · about $0.02 (off: quote the manual)</label>
      <div id="orgp-ans" class="orgp-ans" aria-live="polite"></div></div>`;
    $("#orgp-ask").addEventListener("submit", (e) => { e.preventDefault(); ask($("#orgp-q").value); });
    el.dataset.ready = "1";
  }
  return el;
}

const card = (c) => `<span class="orgp-card ${esc(c.kind)}" title="${esc(c.text)}"><b>${esc(c.label)}</b>${esc(c.text)}${c.page ? ` · p. ${c.page}` : ""}</span>`;

function onMessage(m) {
  if (m.type === "started") {
    O.sessionId = m.session;
    const el = runPanel();
    if (!el) return;
    el.classList.toggle("hidden", !O.org);
    const name = O.orgs.find((o) => o.id === O.org)?.name || O.org || "";
    $("#orgp-name").textContent = name;
    $("#orgp-name").title = `${name} · operator view (the wearer sees only the HUD on the video)`;
    $("#orgp-mode").innerHTML = O.lib?.locked ? '<span class="org-st lock">Locked</span>' : '<span class="org-st ok">Open coach</span>';
    $("#orgp-step").innerHTML = `<div class="wait">Waiting for the first step…</div>`;
    $("#orgp-ans").innerHTML = "";
  } else if (m.type === "org_task") {
    runPanel();
    $("#orgp-step").innerHTML = `<div class="wait">${esc(m.title)} · v${m.version}</div>${(m.procedure_cards || []).length ? `<div class="orgp-cards">${m.procedure_cards.map(card).join("")}</div>` : ""}`;
  } else if (m.type === "org_step") {
    O.step = m;
    runPanel();
    const cards = (m.cards || []).filter((c) => c.kind !== "source");
    const ref = m.ref ? `<img class="orgp-ref" src="/api/orgs/${encodeURIComponent(O.org)}/procedures/${encodeURIComponent(m.proc_id)}/v/${m.version}/refs/${encodeURIComponent(m.ref)}" alt="Reference: what this step looks like when done">` : "";
    $("#orgp-step").innerHTML = `<div class="orgp-step ${m.safety ? "safety" : ""}"><span class="no">${m.index ?? ""}</span><div>
        <div class="of">${esc(m.task)}${m.n_steps ? ` · step ${m.index} of ${m.n_steps}` : ""}${m.safety ? " · safety-critical" : ""}</div>
        <div class="nm">${esc(m.name)}</div><div class="in">${esc(m.instruction)}</div></div></div>
      ${cards.length ? `<div class="orgp-cards">${cards.map(card).join("")}</div>` : ""}${ref}`;
  } else if (m.type === "org_safety") {
    banner("Safety-critical step", m.text + (m.page ? ` (manual page ${m.page})` : ""));
    speak(`Safety: ${m.text}`);
  } else if (m.type === "org_notice") {
    banner("Locked procedure", m.text, "notice");
    speak(m.text);
  }
}

function banner(head, text, kind = "") {
  const stage = $("#stage");
  if (!stage) return;
  stage.querySelector(".org-safety")?.remove();
  const el = document.createElement("div");
  el.className = `org-safety ${kind}`;
  el.setAttribute("role", "alert");
  el.innerHTML = `<span class="accent"></span><div><div class="head">${esc(head)}</div><div class="text">${esc(text)}</div></div>`;
  stage.appendChild(el);
  setTimeout(() => el.remove(), 9000);
}

async function ask(q) {
  q = (q || "").trim();
  if (!q || !O.org) return;
  const btn = $("#orgp-ask button");
  btn.disabled = true;
  $("#orgp-ans").innerHTML = `<span class="wait">Looking it up…</span>`;
  try {
    const r = await fetch(`/api/orgs/${encodeURIComponent(O.org)}/ask`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q, session_id: O.sessionId, use_model: $("#orgp-model").checked }),
    });
    const a = await r.json();
    if (!r.ok) throw new Error(a.detail || "error");
    const src = { card: "from this step's card", model: `Claude${a.cached ? " · cached" : ""}`, excerpt: "quoted from the manual", none: "no match" }[a.source] || a.source;
    const seen = new Set();
    a.citations = (a.citations || []).filter((c) => { const k = c.where || c.label; if (seen.has(k)) return false; seen.add(k); return true; });
    const cites = (a.citations || []).map((c) => c.page && c.doc
      ? `<a class="orgp-cite" target="_blank" rel="noopener" title="${esc(c.where || "")}" href="/api/orgs/${encodeURIComponent(O.org)}/docs/${c.doc}/page/${c.page}.png">${esc(`${(c.title || "").split(" · ")[0]}, p. ${c.page}`)}</a>`
      : `<span class="orgp-cite">${esc(c.where || c.label || "")}</span>`).join("");
    $("#orgp-ans").innerHTML = `<div>${esc(a.answer)}</div><div class="meta">${cites}<span>${esc(src)}</span>${a.cost_usd ? `<span>$${a.cost_usd.toFixed(4)}</span>` : ""}<span>${Math.round(a.latency_ms)} ms</span></div>`;
    speak(a.answer + (a.citations?.[0]?.page ? `. Manual page ${a.citations[0].page}.` : ""));
  } catch (e) {
    $("#orgp-ans").innerHTML = `<span class="errors">${esc(e.message)}</span>`;
  }
  btn.disabled = false;
}

window.praxisOrg = { startFields, onMessage, ask };
boot();
