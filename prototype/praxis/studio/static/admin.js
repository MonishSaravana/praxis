// Praxis Studio · company admin (internal view). Pages: overview, documents (upload, local ingest), a document's
// sections (find procedures, compile one with the cost shown first), procedures (review / edit / approve, safety
// flags, versions, the exact source text side by side), live deployment (open coach vs locked, assignment), ask the
// documents, reference videos. Routes: #/<org>/<page>[/<id>[/<version>]].
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const usd = (x) => `$${(x || 0) < 0.1 ? (x || 0).toFixed(3) : (x || 0).toFixed(2)}`;
const n = (x) => (x ?? 0).toLocaleString();
const date = (s) => s ? new Date(s).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "";
const pages = (p, paged = true) => !paged || !p ? "" : p[0] === p[1] ? `p. ${p[0]}` : `pp. ${p[0]}–${p[1]}`;
const A = { orgs: [], org: null, d: null, route: { page: "overview" }, dirty: false, proc: null };
const api = (p) => `/api/orgs/${encodeURIComponent(A.org)}${p}`;
const href = (...parts) => `#/${[A.org, ...parts].map((x) => encodeURIComponent(x)).join("/")}`;

const ICON = {
  overview: '<path d="M3 3h7v7H3zM14 3h7v4h-7zM14 11h7v10h-7zM3 14h7v7H3z"/>',
  docs: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
  procs: '<path d="M9 6h11M9 12h11M9 18h11"/><path d="m3 6 1.5 1.5L7 5M3 12l1.5 1.5L7 11M3 18l1.5 1.5L7 17"/>',
  live: '<circle cx="12" cy="12" r="3"/><path d="M5.6 5.6a9 9 0 0 0 0 12.8M18.4 5.6a9 9 0 0 1 0 12.8M8.5 8.5a5 5 0 0 0 0 7M15.5 8.5a5 5 0 0 1 0 7"/>',
  ask: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .8-1 1.5M12 16.5h.01"/>',
  videos: '<rect x="3" y="5" width="13" height="14" rx="2"/><path d="m16 10 5-3v10l-5-3z"/>',
  upload: '<path d="M12 16V4M7 9l5-5 5 5M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
  chev: '<path d="m9 6 6 6-6 6"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  alert: '<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17h.01"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
};
const icon = (k) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[k]}</svg>`;

async function j(url, opts) {
  const r = await fetch(url, opts);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.detail || `request failed (${r.status})`);
  return body;
}
const post = (url, body) => j(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
async function poll(id, onTick) {
  for (;;) {
    const s = await j(`/api/jobs/${id}`);
    onTick?.(s);
    if (s.state === "done" || s.state === "error") return s;
    await new Promise((ok) => setTimeout(ok, 700));
  }
}
let toastT;
function toast(msg, bad = false) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = `toast show${bad ? " bad" : ""}`;
  clearTimeout(toastT);
  toastT = setTimeout(() => { t.className = "toast"; }, 3800);
}
function busy(btn, on, label) {
  if (!btn) return;
  if (on) { btn.dataset.label = btn.innerHTML; btn.disabled = true; btn.innerHTML = `<span class="spin"></span>${esc(label || "Working…")}`; }
  else { btn.disabled = false; if (btn.dataset.label) btn.innerHTML = btn.dataset.label; }
}
function spend(b) {
  if (!b) return;
  $("#spend-val").textContent = usd(b.spent_usd);
  $("#spend-cap").textContent = `of ${usd(b.cap_usd)} cap · ${b.calls} call${b.calls === 1 ? "" : "s"}`;
  const f = Math.min(1, b.spent_usd / Math.max(b.cap_usd, 1e-9));
  $("#spend-bar").style.transform = `scaleX(${Math.max(f, b.spent_usd > 0 ? 0.02 : 0)})`;
  $("#spend-bar").parentElement.className = `meter${f >= 1 ? " bad" : f > 0.8 ? " warn" : ""}`;
}

// ------------------------------------------------------------------ boot, routing, shell
async function boot() {
  $("#org").addEventListener("change", () => { location.hash = `#/${encodeURIComponent($("#org").value)}/overview`; });
  $("#new-org-open").addEventListener("click", () => { $("#new-org").classList.remove("hidden"); $("#new-org-open").classList.add("hidden"); $("#new-org-name").focus(); });
  $("#new-org-cancel").addEventListener("click", () => { $("#new-org").classList.add("hidden"); $("#new-org-open").classList.remove("hidden"); });
  $("#new-org").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = $("#new-org-name").value.trim();
    if (!name) return;
    try { const o = await post("/api/orgs", { name }); $("#new-org-name").value = ""; $("#new-org-cancel").click(); location.hash = `#/${o.id}/documents`; await loadOrgs(); }
    catch (err) { toast(err.message, true); }
  });
  window.addEventListener("hashchange", () => route());
  window.addEventListener("beforeunload", (e) => { if (A.dirty) { e.preventDefault(); e.returnValue = ""; } });
  await loadOrgs();
}

async function loadOrgs() {
  const d = await j("/api/orgs");
  A.orgs = d.orgs;
  spend(d.budget);
  $("#org").innerHTML = d.orgs.length ? d.orgs.map((o) => `<option value="${esc(o.id)}">${esc(o.name)}</option>`).join("")
    : `<option value="">No companies yet</option>`;
  await route(true);
}

function parseHash() {
  const p = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  return { org: p[0] || null, page: p[1] || "overview", id: p[2] || null, sub: p[3] || null };
}

async function route(force = false) {
  if (A.dirty && !force && !confirmLeave()) return;
  const r = parseHash();
  if (!r.org || !A.orgs.some((o) => o.id === r.org)) {
    if (!A.orgs.length) return renderNoOrg();
    location.replace(`#/${encodeURIComponent(A.orgs[0].id)}/overview`);
    return;
  }
  const changed = r.org !== A.org;
  A.org = r.org; A.route = r; A.dirty = false;
  $("#org").value = r.org;
  const tok = (A.tok = (A.tok || 0) + 1);
  const skel = setTimeout(() => { if (A.tok === tok) $("#main").innerHTML = SKELETON; }, 120);   // only if it's slow
  if (changed || force || !A.d) await refresh(false);
  if (A.tok !== tok) return;                       // a newer navigation took over
  renderNav();
  const pg = { overview: pageOverview, documents: r.id ? pageDocument : pageDocuments, procedures: r.id ? pageProcedure : pageProcedures,
    live: pageLive, ask: pageAsk, videos: pageVideos }[r.page] || pageOverview;
  try { await pg(); } catch (e) { if (A.tok === tok) $("#main").innerHTML = `<div class="callout warn">${icon("alert")}<div class="grow">${esc(e.message)}</div></div>`; }
  clearTimeout(skel);
  if (changed) window.scrollTo(0, 0);
  $("#main").focus({ preventScroll: true });
}
const SKELETON = `<div class="page-loading"><div class="skel w40"></div><div class="skel w70"></div><div class="skel w100 tall"></div></div>`;
function confirmLeave() {
  if (window.confirm("Discard unsaved changes to this procedure?")) { A.dirty = false; return true; }
  history.replaceState(null, "", A.lastHash || location.hash);
  return false;
}

async function refresh(rerender = true) {
  A.d = await j(api(""));
  spend(A.d.budget);
  renderNav();
  if (rerender) await route(true);
}

function renderNav() {
  const d = A.d || { documents: [], procedures: [], videos: [], settings: {} };
  const approved = d.procedures.filter((p) => p.approved_version).length;
  const items = [
    ["overview", "Overview", ""], ["documents", "Documents", d.documents.length], ["procedures", "Procedures", d.procedures.length],
    ["live", "Live deployment", d.settings?.locked ? "Locked" : approved ? "Open" : ""], ["sep"],
    ["ask", "Ask the documents", ""], ["videos", "Reference videos", d.videos.length || ""],
  ];
  $("#side-nav").innerHTML = items.map(([k, label, c]) => k === "sep" ? '<div class="sep"></div>'
    : `<a href="${href(k)}" aria-label="${esc(label)}" class="${A.route.page === k ? "on" : ""}" ${A.route.page === k ? 'aria-current="page"' : ""}>${icon({ documents: "docs", procedures: "procs" }[k] || k)}<span>${esc(label)}</span><span class="count">${esc(c)}</span></a>`).join("");
  A.lastHash = location.hash;
}

function renderNoOrg() {
  renderNav();
  $("#main").innerHTML = `<div class="surface"><div class="empty"><div class="ico">${icon("overview")}</div><b>Create your first company</b>
    <p>A company holds its manuals and procedures, which procedures are approved, and whether technicians run in locked mode.</p>
    <button class="btn primary" id="first-org">+ New company</button></div></div>`;
  $("#first-org").addEventListener("click", () => $("#new-org-open").click());
}

const head = (title, sub, actions = "", crumbs = "") => `${crumbs ? `<div class="crumbs">${crumbs}</div>` : ""}
  <div class="page-head"><div class="titles"><h1>${title}</h1>${sub ? `<p>${sub}</p>` : ""}</div><div class="actions">${actions}</div></div>`;

// ------------------------------------------------------------------ overview
async function pageOverview() {
  const d = A.d, s = d.settings, st = d.stats;
  const approved = d.procedures.filter((p) => p.approved_version);
  const safety = d.procedures.reduce((a, p) => a + (p.n_safety || 0), 0);
  const assigned = d.procedures.filter((p) => s.assigned.includes(p.id));
  const live = s.locked ? (assigned.length ? `Locked to <b>${esc(assigned.map((p) => p.title).join(", "))}</b>` : "Locked, but nothing assigned yet")
    : approved.length ? `Open coach over <b>${approved.length}</b> approved procedure${approved.length === 1 ? "" : "s"}` : "Nothing approved yet";
  $("#main").innerHTML = head(esc(d.name), `Created ${date(d.created)}. From uploaded manuals to what a technician hears, in three steps.`) + `
    <div class="surface pipeline">
      <div class="stage-col"><span class="n">1</span><h3>Documents</h3>
        <div class="facts"><span><b>${d.documents.length}</b> document${d.documents.length === 1 ? "" : "s"}, <b>${n(st.pages)}</b> pages indexed on this machine</span>
          <span><b>${n(st.candidates)}</b> likely procedures found locally</span></div>
        <a class="btn go" href="${href("documents")}">${d.documents.length ? "Open documents" : "Upload a manual"}</a></div>
      <div class="stage-col"><span class="n">2</span><h3>Procedures</h3>
        <div class="facts"><span><b>${d.procedures.length}</b> compiled, <b>${approved.length}</b> approved</span>
          <span><b>${safety}</b> safety-critical step${safety === 1 ? "" : "s"} marked</span></div>
        <a class="btn go" href="${href("procedures")}">Review procedures</a></div>
      <div class="stage-col"><span class="n">3</span><h3>Live</h3>
        <div class="facts"><span>${live}</span><span>Technicians see steps and cards, never the graph</span></div>
        <a class="btn go" href="${href("live")}">Deployment settings</a></div>
    </div>
    <h2 class="sec">What leaves this machine</h2>
    <div class="callout">${icon("info")}<div class="grow">Uploading and indexing are local: nothing is sent anywhere. Compiling sends only the one section you
      choose, after showing its size and cost. A question answered by Claude sends five short excerpts and the current step. Live coaching
      never sends document text.</div></div>`;
}

// ------------------------------------------------------------------ documents
function dropZone(id = "drop") {
  return `<label class="drop" id="${id}"><span class="ico">${icon("upload")}</span><span class="txt"><b>Upload manuals and procedures</b>
    PDF with a text layer, Word (.docx), text or Markdown. Parsed and indexed on this machine, once per file. Re-uploading a file with the same
    name adds a version and keeps the old one.</span><span class="btn">Choose files</span>
    <input type="file" multiple accept=".pdf,.txt,.md,.markdown,.docx" hidden></label><div class="uploads" id="uploads"></div>`;
}
function bindDrop(id = "drop", onDone) {
  const z = $(`#${id}`);
  if (!z) return;
  const go = (files) => uploadFiles([...files], onDone);
  $("input", z).addEventListener("change", (e) => { go(e.target.files); e.target.value = ""; });
  z.addEventListener("dragover", (e) => { e.preventDefault(); z.classList.add("over"); });
  z.addEventListener("dragleave", () => z.classList.remove("over"));
  z.addEventListener("drop", (e) => { e.preventDefault(); z.classList.remove("over"); go(e.dataTransfer.files); });
}
async function uploadFiles(files, onDone) {
  for (const f of files) {
    const row = document.createElement("div");
    row.className = "upl";
    row.innerHTML = `<span class="name">${esc(f.name)}</span><span class="msg">Uploading…</span><span class="st info busy">Uploading</span>`;
    $("#uploads")?.prepend(row);
    const set = (msg, cls, label) => { $(".msg", row).textContent = msg; const p = $(".st", row); p.className = `st ${cls}`; p.textContent = label; };
    try {
      const fd = new FormData();
      fd.append("file", f);
      const r = await j(api("/upload"), { method: "POST", body: fd });
      if (r.kind === "video") { set(`Stored · ${r.duration_s ?? "?"} s`, "ok", "Stored"); continue; }
      if (!r.new) set(`Same content as v${r.version}, already indexed`, "plain", "Unchanged");
      const s = await poll(r.job.id, (x) => set(`${x.state === "queued" ? "Queued" : x.state[0].toUpperCase() + x.state.slice(1)}… ${x.elapsed_s}s`, "info busy", "Indexing"));
      if (s.state === "done") {
        const x = s.result;
        set(`${n(x.pages)} pages · ${n(x.n_sections)} sections · ${n(x.n_procedures)} likely procedures · indexed in ${x.ingest_s}s`, "ok", "Ready");
        toast(`${f.name} is indexed. ${x.n_procedures} likely procedures found.`);
      } else set(s.error, "bad", "Failed");
    } catch (e) { set(e.message, "bad", "Failed"); }
  }
  await refresh(false);
  onDone?.();
}

async function pageDocuments() {
  const docs = A.d.documents;
  const rows = docs.map((d) => {
    const v = d.versions.at(-1);
    const stc = v.status === "ready" ? "ok" : v.status === "error" ? "bad" : "info busy";
    return `<tr class="click" data-go="${href("documents", v.hash)}">
      <td><div class="t1">${esc(d.title)}</div><div class="t2">${esc(v.filename)} · v${v.version}${d.versions.length > 1 ? ` · ${d.versions.length - 1} older version${d.versions.length > 2 ? "s" : ""} kept` : ""}</div></td>
      <td class="num">${v.pages != null ? n(v.pages) : "–"}${v.paged === false ? '<div class="t2">parts</div>' : ""}</td>
      <td class="num">${v.n_sections != null ? n(v.n_sections) : "–"}</td>
      <td class="num">${v.n_procedures != null ? n(v.n_procedures) : "–"}</td>
      <td class="nowrap"><span class="st ${stc}">${esc(v.status === "ready" ? "Indexed" : v.status || "")}</span>${v.error ? `<div class="errors">${esc(v.error)}</div>` : ""}
        ${v.ingest_s != null ? `<div class="t2">${n(v.n_chunks)} passages · ${v.ingest_s}s</div>` : ""}</td>
      <td class="acts"><a class="btn sm" href="${href("documents", v.hash)}">Find procedures</a></td></tr>`;
  }).join("");
  $("#main").innerHTML = head("Documents", "Manuals and procedures for this company. Each file is parsed into pages, sections and searchable passages on this machine.") +
    dropZone() + (docs.length ? `<h2 class="sec">${docs.length} document${docs.length === 1 ? "" : "s"}</h2>
    <div class="surface"><table class="tbl"><thead><tr><th>Document</th><th class="num">Pages</th><th class="num">Sections</th><th class="num">Likely procedures</th><th>Index</th><th></th></tr></thead>
    <tbody>${rows}</tbody></table></div>` : `<div class="surface" style="margin-top:14px"><div class="empty"><div class="ico">${icon("docs")}</div><b>No documents yet</b>
    <p>Upload a maintenance manual. Praxis finds its procedures by their headings and numbered steps; you then pick which ones to compile.</p></div></div>`);
  bindDrop("drop", () => pageDocuments());
  $$("tr[data-go]").forEach((tr) => tr.addEventListener("click", (e) => { if (!e.target.closest("a,button")) location.hash = tr.dataset.go; }));
}

const scoreBars = (x) => `<span class="score" title="Procedure likelihood ${Math.round(x * 100)}%">${[0.2, 0.4, 0.55, 0.7, 0.85].map((t) => `<i class="${x >= t ? "on" : ""}"></i>`).join("")}</span>`;

async function pageDocument() {
  const h = A.route.id;
  const doc = A.d.documents.find((d) => d.versions.some((v) => v.hash === h));
  const v = doc?.versions.find((x) => x.hash === h);
  const d = await j(api(`/docs/${h}/sections`));
  const procs = Object.fromEntries(A.d.procedures.map((p) => [p.id, p]));
  const state = { filter: "likely", q: "" };
  const crumbs = `<a href="${href("documents")}">Documents</a> / ${esc(doc?.title || d.meta.filename)}`;
  const sub = `${d.meta.filename} · v${d.meta.version} · ${n(d.meta.pages)} ${d.meta.paged ? "pages" : "parts"} · ${n(d.sections.length)} sections · indexed in ${d.meta.ingest_s}s` +
    (doc && doc.current !== h ? " · an older version (kept on record)" : "");
  $("#main").innerHTML = head(`<span id="doc-title-text">${esc(doc?.title || d.meta.filename)}</span><input class="title-input hidden" id="doc-title" value="${esc(doc?.title || d.meta.filename)}" aria-label="Document title">`,
    esc(sub), `${doc ? '<button class="btn sm ghost" id="rename">Rename</button>' : ""}<button class="btn sm ghost" id="reindex">Re-index</button>`, crumbs) + `
    <div class="toolbar"><div class="seg" role="tablist"><button data-f="likely" class="on">Likely procedures</button><button data-f="all">All sections</button></div>
      <input class="search" id="sec-q" placeholder="Filter sections" type="search"><span class="muted small" id="sec-count"></span></div>
    <div class="surface"><table class="tbl fixed" id="sec-tbl"><colgroup><col><col style="width:104px"><col style="width:64px"><col style="width:92px"><col style="width:236px"></colgroup>
      <thead><tr><th>Section</th><th>Pages</th><th class="num">Steps</th><th>Procedure</th><th></th></tr></thead><tbody></tbody></table></div>
    <p class="hint" style="margin-top:10px">Found from the document's headings and numbered steps, without a model. Compiling sends only that section's text.</p>`;
  const draw = () => {
    const q = state.q.toLowerCase();
    const rows = d.sections.filter((s) => (state.filter === "all" || s.proc_score >= 0.5 || s.procedure) && (!q || s.title.toLowerCase().includes(q)));
    $("#sec-count").textContent = `${rows.length} of ${d.sections.length}`;
    $("#sec-tbl tbody").innerHTML = rows.map((s) => {
      const p = s.procedure && procs[s.procedure];
      const status = p ? (p.approved_version ? `<span class="st ok">Approved v${p.approved_version}</span>` : `<span class="st warn">Draft v${p.latest_version}</span>`) : "";
      return `<tr data-sid="${s.id}"><td><div class="t1" style="padding-left:${(s.level - 1) * 16}px">${esc(s.title)}</div>
          <div class="t2" style="padding-left:${(s.level - 1) * 16}px">${esc(s.why)}</div>
          ${s.first_steps.length ? `<ul class="first-steps" style="padding-left:${(s.level - 1) * 16}px">${s.first_steps.map((x, i) => `<li>${i + 1}. ${esc(x)}</li>`).join("")}</ul>` : ""}</td>
        <td class="nowrap">${d.meta.paged ? `<a href="${api(`/docs/${h}/page/${s.page_start}.png`)}" target="_blank" rel="noopener">${esc(pages([s.page_start, s.page_end]))}</a>` : "–"}</td>
        <td class="num">${s.n_steps || "–"}</td><td>${scoreBars(s.proc_score)}</td>
        <td class="acts">${status ? `<div class="acts-st">${status}</div>` : ""}<div class="acts-b">${p ? `<a class="btn sm" href="${href("procedures", p.id)}">Review</a>` : ""}
          <button class="btn sm ${p ? "ghost" : ""}" data-plan="${s.id}">${p ? "Recompile" : "Compile…"}</button></div></td></tr>
        <tr class="expand hidden" id="plan-${s.id}"><td colspan="5"></td></tr>`;
    }).join("") || `<tr><td colspan="5"><div class="empty"><b>No sections match</b><p>Try "All sections", or another filter.</p></div></td></tr>`;
    $$("[data-plan]").forEach((b) => b.addEventListener("click", () => planCompile(h, b.dataset.plan, $(`#plan-${b.dataset.plan}`), procs)));
  };
  $$(".seg button").forEach((b) => b.addEventListener("click", () => { $$(".seg button").forEach((x) => x.classList.toggle("on", x === b)); state.filter = b.dataset.f; draw(); }));
  $("#sec-q").addEventListener("input", (e) => { state.q = e.target.value; draw(); });
  const editing = (on) => { $("#doc-title").classList.toggle("hidden", !on); $("#doc-title-text").classList.toggle("hidden", on); if (on) { $("#doc-title").focus(); $("#doc-title").select(); } };
  const rename = async () => {
    const t = $("#doc-title").value.trim();
    editing(false);
    if (!doc || !t || t === doc.title) return;
    try { await post(api(`/documents/${encodeURIComponent(doc.name)}`), { title: t }); doc.title = t; $("#doc-title-text").textContent = t; await refresh(false); toast("Renamed."); }
    catch (err) { toast(err.message, true); }
  };
  $("#rename")?.addEventListener("click", () => editing(true));
  $("#doc-title").addEventListener("blur", rename);
  $("#doc-title").addEventListener("keydown", (e) => { if (e.key === "Enter") e.target.blur(); if (e.key === "Escape") { e.target.value = doc.title; editing(false); } });
  $("#reindex").addEventListener("click", async (e) => {
    busy(e.currentTarget, true, "Re-indexing");
    const job = await post(api(`/docs/${h}/reingest`), {});
    const s = await poll(job.id);
    toast(s.state === "done" ? "Re-indexed." : s.error, s.state !== "done");
    await refresh();
  });
  draw();
}

async function planCompile(h, sid, row, procs, procId = null) {
  const cell = row.firstElementChild || row;
  row.classList.remove("hidden");
  cell.innerHTML = `<div class="est"><div class="skel w70"></div><div class="skel w40"></div></div>`;
  let p;
  try { p = await j(api(`/docs/${h}/sections/${sid}/plan`)); }
  catch (e) { cell.innerHTML = `<div class="est"><span class="errors">${esc(e.message)}</span></div>`; return; }
  const e = p.estimate, pct = p.doc_chars_total ? (100 * p.chars_sent / p.doc_chars_total) : 100;
  cell.innerHTML = `<div class="est">
    <div class="est-grid">
      <div class="kv"><div class="k">Sent to the model</div><div class="v">${n(p.chars_sent)} chars</div><div class="s">${pct < 1 ? pct.toFixed(1) : Math.round(pct)}% of the document · ${esc(pages(p.pages))}</div></div>
      <div class="kv"><div class="k">Steps</div><div class="v">${p.steps_from === "manual numbering" ? n(p.n_steps) : `about ${n(p.n_steps)}`}</div><div class="s">${p.steps_from === "manual numbering" ? "from the manual's own numbering" : "named by one small split call"}</div></div>
      <div class="kv"><div class="k">Estimated cost</div><div class="v">${p.cached ? "$0 · cached" : usd(e.total_usd)}</div><div class="s">${p.cached ? "compiled before from this exact text" : `at most ${usd(e.upper_usd)} · Opus 5.5, effort ${esc(e.effort)}`}</div></div>
      <div class="kv"><div class="k">Spend so far</div><div class="v">${usd(p.budget.spent_usd)}</div><div class="s">of the ${usd(p.budget.cap_usd)} cap</div></div>
    </div>
    ${p.too_long ? `<div class="callout warn">${icon("alert")}<div class="grow">This section is too long to compile in one piece. Pick one of its sub-sections.</div></div>` : ""}
    <details class="peek"><summary>Preview the text that will be sent</summary><div class="srcbox">${esc(p.preview)}${p.chars_sent > 1200 ? "\n…" : ""}</div></details>
    <div class="row">${p.too_long ? "" : `<button class="btn primary" data-go>${p.cached ? "Create version from cache ($0)" : `Compile · up to ${usd(e.upper_usd)}`}</button>`}
      <button class="btn ghost" data-cancel>Cancel</button><span class="muted small" data-msg></span></div></div>`;
  $("[data-cancel]", cell).addEventListener("click", () => { row.classList.add("hidden"); cell.innerHTML = ""; });
  $("[data-go]", cell)?.addEventListener("click", async (ev) => {
    const btn = ev.currentTarget;
    busy(btn, true, "Compiling");
    $("[data-cancel]", cell).disabled = true;
    try {
      const job = await post(api(`/docs/${h}/sections/${sid}/compile`), { confirm_usd: e.upper_usd, effort: e.effort, proc_id: procId });
      const s = await poll(job.id, (x) => {
        const what = { splitting: "Naming the steps", compiling: "Compiling steps, checks and mistakes", cards: "Attaching knowledge cards", embedding: "Embedding end states", queued: "Queued" }[x.state] || x.state;
        $("[data-msg]", cell).textContent = `${what}${x.state === "compiling" && x.detail ? ` · ${n(+x.detail)} characters received` : ""} · ${x.elapsed_s}s`;
      });
      if (s.state === "error") throw new Error(s.error);
      await refresh(false);
      toast("Compiled. Review it before approving.");
      location.hash = href("procedures", s.result.proc_id, s.result.version);
    } catch (err) { busy(btn, false); $("[data-cancel]", cell).disabled = false; $("[data-msg]", cell).innerHTML = `<span class="errors">${esc(err.message)}</span>`; }
  });
}

// ------------------------------------------------------------------ procedures
function procStatus(p) {
  if (p.approved_version && p.approved_version === p.latest_version) return `<span class="st ok">Approved v${p.approved_version}</span>`;
  if (p.approved_version) return `<span class="st warn">Draft v${p.latest_version}</span> <span class="t2">v${p.approved_version} is live</span>`;
  return `<span class="st warn">Draft v${p.latest_version}</span>`;
}
async function pageProcedures() {
  const ps = A.d.procedures;
  $("#main").innerHTML = head("Procedures", "Compiled from your documents. A procedure coaches technicians only after someone approves it; an approved version is never edited in place.") +
    (ps.length ? `<div class="surface"><table class="tbl"><thead><tr><th>Procedure</th><th>Source</th><th class="num">Steps</th><th>Status</th><th>Live</th><th class="num">Compiled</th></tr></thead><tbody>
    ${ps.map((p) => `<tr class="click" data-go="${href("procedures", p.id)}">
      <td><div class="t1">${esc(p.title)}</div><div class="t2">${esc(p.section || "")}</div></td>
      <td><div>${esc(p.doc_title)}</div><div class="t2">v${p.doc_version}${p.paged ? ` · ${esc(pages(p.pages))}` : ""}${p.source_updated ? ' · <span class="st bad plain">document updated</span>' : ""}</div></td>
      <td class="num">${p.n_steps}${p.n_safety ? `<div class="t2">${p.n_safety} safety</div>` : ""}</td>
      <td>${procStatus(p)}</td>
      <td>${A.d.settings.locked && p.assigned ? `<span class="st info">${icon("lock").replace("<svg", '<svg width="11" height="11"')} Locked</span>` : p.assigned ? '<span class="st plain">Assigned</span>' : p.approved_version ? '<span class="muted small">In library</span>' : '<span class="muted small">–</span>'}</td>
      <td class="num">${date(p.created)}</td></tr>`).join("")}</tbody></table></div>`
    : `<div class="surface"><div class="empty"><div class="ico">${icon("procs")}</div><b>No procedures yet</b>
      <p>Open a document, pick one of its likely procedures and compile it. You'll see what will be sent and what it costs first.</p>
      <a class="btn primary" href="${href("documents")}">Go to documents</a></div></div>`);
  $$("tr[data-go]").forEach((tr) => tr.addEventListener("click", () => { location.hash = tr.dataset.go; }));
}

async function pageProcedure() {
  const pid = A.route.id, ver = A.route.sub ? +A.route.sub : null;
  const d = await j(api(`/procedures/${encodeURIComponent(pid)}${ver ? `?v=${ver}` : ""}`));
  A.proc = d;
  const g = d.graph, info = d.info, rev = d.review, paged = info.paged !== false;
  const safety = new Set(rev.safety || []), sugg = new Set(rev.safety_suggested || []);
  const cards = JSON.parse(JSON.stringify(d.cards));
  const isApproved = d.proc.approved_version === d.version;
  const liveV = d.proc.approved_version;
  const docTitle = (A.d.documents.find((x) => x.name === info.doc_name) || {}).title || info.doc_name;
  const docMeta = A.d.documents.flatMap((x) => x.versions).find((x) => x.hash === info.doc_hash) || {};
  const pageBtn = (pg) => paged && pg ? `<button class="pg" data-page="${pg}">p. ${pg}</button>` : "";
  const chip = (c, nid, i) => `<span class="kcard ${esc(c.kind)}" data-card="${esc(nid)}:${i}"><span class="k">${esc(c.label)}</span><span class="t" title="${esc(c.text)}">${esc(c.text)}</span>${pageBtn(c.page)}<button class="x" title="Remove this card" aria-label="Remove card">×</button></span>`;
  const vers = d.proc.versions.map((x) => `<option value="${x.version}" ${x.version === d.version ? "selected" : ""}>v${x.version}${x.approved ? " · approved" : ""}${x.version === liveV ? " · live" : ""}${x.edited_from ? ` · edited from v${x.edited_from}` : ""}</option>`).join("");
  const total = docMeta.pages ? ` of a ${n(docMeta.pages)}-page document` : "";
  const sent = info.chars_sent ? `${n(info.chars_sent)} chars${total}` : "";
  const crumbs = `<a href="${href("procedures")}">Procedures</a> / ${esc(g.title)}`;
  const headActions = `<select id="p-ver" aria-label="Version" style="width:auto">${vers}</select>
    ${isApproved ? `<span class="st ok">Approved · live</span>` : `<span id="approve-wrap"><button class="btn approve" id="p-approve">Approve v${d.version}</button></span>`}`;
  $("#main").innerHTML = `<div class="crumbs">${crumbs}</div>
    <div class="page-head"><div class="titles"><input class="title-input" id="p-title" value="${esc(g.title)}" aria-label="Procedure title"></div><div class="actions">${headActions}</div></div>
    <div class="meta-strip"><span>Source <b>${esc(docTitle)}</b> v${esc(info.doc_version)}</span><span>${esc(info.section_title)}${paged ? ` · ${esc(pages(info.pages))}` : ""}</span>
      <span>Steps from ${esc(info.steps_from)}</span>${sent ? `<span>Sent ${sent}</span>` : ""}
      <span>${info.cached ? "Cached, $0" : `Cost ${usd(info.cost_usd)}`}</span><span>${esc(g.compiler.model || "")}</span><span>${date(info.created)}</span></div>
    ${!isApproved && liveV ? `<div class="callout info" style="margin-bottom:12px">${icon("info")}<div class="grow">Technicians are coached from v${liveV} until this version is approved.</div><a class="btn sm" href="${href("procedures", pid, liveV)}">Open v${liveV}</a></div>` : ""}
    ${!liveV ? `<div class="callout warn" style="margin-bottom:12px">${icon("alert")}<div class="grow">Not approved yet. Read each step against the source on the right; a wrong step means wrong coaching.</div></div>` : ""}
    ${d.newer_doc ? `<div class="callout warn" style="margin-bottom:12px">${icon("alert")}<div class="grow">The source document has a newer version (v${d.newer_doc.version}, ${esc(d.newer_doc.filename)}). This version stays on record.</div><button class="btn sm" id="p-recompile">Plan a recompile</button></div><div id="recompile-box"></div>` : ""}
    <div class="review">
      <div>
        ${(cards._procedure || []).length ? `<h2 class="sec">Whole procedure</h2><div class="cards" style="margin-bottom:6px">${cards._procedure.map((c, i) => chip(c, "_procedure", i)).join("")}</div>` : ""}
        <h2 class="sec">Steps <span class="muted">${g.nodes.length} · ${safety.size} safety-critical</span> <button class="btn link" id="toggle-all" style="float:right">Expand all</button></h2>
        <div class="steps">${g.nodes.map((nd, k) => `<div class="step-item ${safety.has(nd.id) ? "safety" : ""}" data-n="${esc(nd.id)}">
          <div class="step-row" role="button" tabindex="0" aria-expanded="false"><span class="no">${k + 1}</span>
            <span class="nm">${esc(nd.name)}<span class="sub">${esc(nd.instruction_novice)}</span></span>
            ${safety.has(nd.id) ? '<span class="st warn">Safety-critical</span>' : sugg.has(nd.id) ? '<span class="st plain">Safety wording in source</span>' : ""}
            ${(cards[nd.id] || []).filter((c) => c.kind !== "source").length ? `<span class="st plain">${(cards[nd.id] || []).filter((c) => c.kind !== "source").length} card${(cards[nd.id] || []).filter((c) => c.kind !== "source").length === 1 ? "" : "s"}</span>` : ""}
            ${d.refs[nd.id] ? '<span class="st plain">frame</span>' : ""}
            <svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${ICON.chev}</svg></div>
          <div class="step-body"><div class="fields">
            <div class="field"><label>Step name</label><input data-f="name" value="${esc(nd.name)}"></div>
            <div class="field"><label>Expert cue <span class="help">· a few words</span></label><input data-f="instruction_expert" value="${esc(nd.instruction_expert)}"></div>
            <div class="field full"><label>Spoken instruction <span class="help">· for a first-timer</span></label><textarea data-f="instruction_novice" rows="2">${esc(nd.instruction_novice)}</textarea></div>
            <div class="field"><label>What done looks like <span class="help">· matched against the camera</span></label><textarea data-f="end_state" rows="3">${esc(nd.end_state)}</textarea></div>
            <div class="field"><label>Checks <span class="help">· one yes/no question per line</span></label><textarea data-f="checks" rows="3">${esc(nd.checks.map((c) => c.question).join("\n"))}</textarea></div>
            <div class="field full"><label class="switch"><input type="checkbox" class="amber" data-safety ${safety.has(nd.id) ? "checked" : ""}> Safety-critical step <span class="help">· shows and speaks a safety banner when the step starts${sugg.has(nd.id) ? "; the source has safety wording here" : ""}</span></label></div>
            <div class="field full"><label>Knowledge cards <span class="help">· quoted from the source</span></label>
              <div class="cards">${(cards[nd.id] || []).map((c, i) => chip(c, nd.id, i)).join("") || '<span class="muted small">None found in the source for this step.</span>'}</div></div>
            <div class="field full"><label>Known mistakes and corrections <span class="help">· compiled</span></label>
              <div class="mist">${nd.mistakes.map((m) => `<div>${esc(m.description)} <em>→ “${esc(m.correction)}”</em></div>`).join("") || '<span class="muted small">None</span>'}</div></div>
            ${d.refs[nd.id] ? `<div class="field full ref"><label>Reference frame <span class="help">· ${esc(d.refs[nd.id].status)}, ${d.refs[nd.id].t}s into the video</span></label>
              <img src="${api(`/procedures/${encodeURIComponent(pid)}/v/${d.version}/refs/${encodeURIComponent(d.refs[nd.id].file)}`)}" alt="What this step looks like when done">
              <button class="btn sm ghost" data-clearref="${esc(nd.id)}">Remove frame</button></div>` : ""}
          </div></div></div>`).join("")}</div>
        <div class="savebar" id="savebar"><span>Unsaved changes${isApproved ? `. Saving creates draft v${d.proc.versions.length + 1}; v${d.version} stays live.` : ""}</span>
          <button class="btn ghost sm" id="p-discard">Discard</button><button class="btn sm" id="p-save">${isApproved ? "Save as new draft" : "Save changes"}</button></div>
      </div>
      <aside class="surface source" aria-label="Source text"><div class="hd"><b id="src-title">What the compiler saw</b><span class="muted small" id="src-sub">${n((d.source || "").length)} chars</span>
        <button class="btn sm ghost hidden" id="src-back">Back to text</button></div><div class="bd" id="src-bd"></div></aside>
    </div>`;

  const srcText = () => {
    $("#src-title").textContent = "What the compiler saw";
    $("#src-sub").textContent = `${n((d.source || "").length)} chars`;
    $("#src-back").classList.add("hidden");
    $("#src-bd").innerHTML = esc(reflow(d.source || "")).replace(/\[page (\d+)\]\n?/g, (_, pg) => `<span class="pm" data-page="${pg}">Page ${pg} ↗</span>`);
    $$("#src-bd [data-page]").forEach((b) => b.addEventListener("click", () => showPage(+b.dataset.page)));
  };
  const showPage = (pg) => {
    if (!paged) return;
    $("#src-title").textContent = `${docTitle}, page ${pg}`;
    $("#src-sub").textContent = "";
    $("#src-back").classList.remove("hidden");
    $("#src-bd").innerHTML = `<div class="skel w100 tall"></div>`;
    const img = new Image();
    img.alt = `Page ${pg}`;
    img.onload = () => { $("#src-bd").innerHTML = ""; $("#src-bd").appendChild(img); };
    img.onerror = () => { $("#src-bd").innerHTML = '<span class="errors">Could not render this page.</span>'; };
    img.src = api(`/docs/${info.doc_hash}/page/${pg}.png`);
  };
  $("#src-back").addEventListener("click", srcText);
  srcText();

  const markDirty = () => { A.dirty = true; $("#savebar").classList.add("show"); };
  $$(".step-row").forEach((r) => {
    const toggle = () => { const it = r.parentElement; it.classList.toggle("open"); r.setAttribute("aria-expanded", it.classList.contains("open")); };
    r.addEventListener("click", toggle);
    r.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } });
  });
  $("#toggle-all").addEventListener("click", (e) => {
    const open = !$$(".step-item").every((x) => x.classList.contains("open"));
    $$(".step-item").forEach((x) => x.classList.toggle("open", open));
    e.currentTarget.textContent = open ? "Collapse all" : "Expand all";
  });
  $$("#main input[data-f], #main textarea[data-f], #p-title").forEach((x) => x.addEventListener("input", markDirty));
  $$("[data-safety]").forEach((x) => x.addEventListener("change", () => { x.closest(".step-item").classList.toggle("safety", x.checked); markDirty(); }));
  $$(".kcard .x").forEach((b) => b.addEventListener("click", (e) => {
    e.stopPropagation();
    const el = b.closest(".kcard"); const [nid, i] = el.dataset.card.split(":");
    const removed = el.classList.toggle("removed");
    cards[nid][+i] = removed ? null : d.cards[nid][+i];
    markDirty();
  }));
  $$(".kcard .pg").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); showPage(+b.dataset.page); }));
  $$("[data-clearref]").forEach((b) => b.addEventListener("click", async () => {
    await post(api(`/procedures/${encodeURIComponent(pid)}/refs/clear`), { version: d.version, node: b.dataset.clearref });
    toast("Frame removed."); pageProcedure();
  }));
  $("#p-ver").addEventListener("change", (e) => { location.hash = href("procedures", pid, e.target.value); });
  $("#p-discard").addEventListener("click", () => { A.dirty = false; pageProcedure(); });
  $("#p-save").addEventListener("click", async (e) => {
    const nodes = {};
    $$(".step-item").forEach((s) => {
      const o = {};
      $$("[data-f]", s).forEach((f) => { o[f.dataset.f] = f.dataset.f === "checks" ? f.value.split("\n") : f.value; });
      nodes[s.dataset.n] = o;
    });
    const edits = { title: $("#p-title").value, nodes, safety: $$(".step-item").filter((s) => $("[data-safety]", s).checked).map((s) => s.dataset.n),
      cards: Object.fromEntries(Object.entries(cards).map(([k, v]) => [k, v.filter(Boolean)])) };
    busy(e.currentTarget, true, "Saving");
    try {
      const r = await post(api(`/procedures/${encodeURIComponent(pid)}/edit`), { version: d.version, edits });
      A.dirty = false;
      await refresh(false);
      toast(r.version !== d.version ? `Saved as draft v${r.version}. v${d.version} stays live.` : "Saved.");
      if (r.version !== d.version) location.hash = href("procedures", pid, r.version); else pageProcedure();
    } catch (err) { busy(e.currentTarget, false); toast(err.message, true); }
  });
  $("#p-approve")?.addEventListener("click", () => {
    if (A.dirty) { toast("Save or discard your changes first.", true); return; }
    $("#approve-wrap").innerHTML = `<span class="confirm-inline">Coach technicians from v${d.version}? <button class="btn approve sm" id="p-approve-yes">Approve</button><button class="btn ghost sm" id="p-approve-no">Cancel</button></span>`;
    $("#p-approve-no").addEventListener("click", () => pageProcedure());
    $("#p-approve-yes").addEventListener("click", async (e) => {
      busy(e.currentTarget, true, "Approving");
      await post(api(`/procedures/${encodeURIComponent(pid)}/approve`), { version: d.version });
      await refresh(false);
      toast(`v${d.version} approved. Assign it on Live deployment to lock technicians to it.`);
      pageProcedure();
    });
  });
  $("#p-recompile")?.addEventListener("click", async () => {
    try {
      const r = await j(api(`/procedures/${encodeURIComponent(pid)}/recompile`));
      const box = $("#recompile-box"); box.className = "surface"; box.style.marginBottom = "12px";
      await planCompile(r.doc, r.section_id, box, {}, pid);
    } catch (err) { toast(err.message, true); }
  });
}

// PDF text keeps the page's line breaks; join wrapped lines into paragraphs for reading (display only).
function reflow(text) {
  const out = [];
  for (const line of text.split("\n")) {
    const prev = out.length ? out[out.length - 1] : null;
    const starts = /^(\[page \d+\]|\d+[.)]\s|[a-h][.)]\s|[-•–]\s|(figure|table|note|warning|caution|danger)\b)/i.test(line);
    if (prev !== null && !/\[page \d+\]$/.test(prev) && !/[.:;!?]$/.test(prev) && !starts && line.trim()) out[out.length - 1] = `${prev} ${line.trim()}`;
    else out.push(line);
  }
  return out.join("\n");
}

// ------------------------------------------------------------------ live deployment
async function pageLive() {
  const s = A.d.settings, ps = A.d.procedures;
  const approved = ps.filter((p) => p.approved_version);
  const assigned = approved.filter((p) => s.assigned.includes(p.id));
  const what = s.locked
    ? assigned.length === 1 ? `Starts <b>${esc(assigned[0].title)}</b> (v${assigned[0].approved_version}) as soon as the session begins. No recognition, no other task, no drafted plans; Praxis tracks, confirms and flags deviations with the step cited.`
      : assigned.length ? `Recognizes only these ${assigned.length} assigned procedures. Anything else gets "This job is locked to …" and no drafted plan.`
      : "Nothing is assigned, so a locked session can't start. Assign an approved procedure below."
    : approved.length ? `Recognizes any of the ${approved.length} approved procedure${approved.length === 1 ? "" : "s"} from the camera, and drafts a plan for unknown tasks.`
      : "Approve a procedure first; until then this company has nothing to coach.";
  $("#main").innerHTML = head("Live deployment", "What happens when a technician starts Praxis with this company. Approved versions only.",
    `<a class="btn" href="/#/live">Open Studio Live</a>`) + `
    <div class="modes">
      <button class="mode ${!s.locked ? "on" : ""}" data-locked="0"><b><span class="dot"></span>Open coach</b><span>Recognizes the task from the company's approved procedures and adapts detail to the person.</span></button>
      <button class="mode ${s.locked ? "on" : ""}" data-locked="1"><b><span class="dot"></span>Locked procedure</b><span>Only the assigned procedure. Praxis does not revise, shortcut or suggest another method.</span></button>
    </div>
    <div class="callout ${s.locked && !assigned.length ? "warn" : "info"}" style="margin-top:12px">${icon(s.locked ? "lock" : "info")}<div class="grow">${what}</div></div>
    <h2 class="sec">Assigned procedures <span class="muted">used in locked mode</span></h2>
    <div class="surface assign-list">${ps.length ? ps.map((p) => `<label class="assign ${p.approved_version ? "" : "disabled"}">
      <input type="checkbox" value="${esc(p.id)}" ${s.assigned.includes(p.id) ? "checked" : ""} ${p.approved_version ? "" : "disabled"}>
      <span class="grow"><span class="t1">${esc(p.title)}</span><div class="t2">${esc(p.doc_title)} · ${esc(p.section || "")} · ${p.n_steps} steps${p.n_safety ? ` · ${p.n_safety} safety-critical` : ""}</div></span>
      ${p.approved_version ? `<span class="st ok">v${p.approved_version}</span>` : '<span class="muted small">approve first</span>'}</label>`).join("")
      : `<div class="empty"><b>No procedures yet</b><p>Compile and approve a procedure first.</p></div>`}</div>`;
  $$(".mode").forEach((b) => b.addEventListener("click", () => saveSettings({ locked: b.dataset.locked === "1" }, b.dataset.locked === "1" ? "Locked mode on." : "Open coach mode on.")));
  $$(".assign input").forEach((x) => x.addEventListener("change", () => saveSettings({ assigned: $$(".assign input:checked").map((y) => y.value) }, "Assignment saved.")));
}
async function saveSettings(body, msg) {
  try { await post(api("/settings"), body); await refresh(); if (msg) toast(msg); } catch (e) { toast(e.message, true); await refresh(); }
}

// ------------------------------------------------------------------ ask
async function pageAsk() {
  const ps = A.d.procedures, s = A.d.settings;
  $("#main").innerHTML = head("Ask the documents", "What a technician gets when they ask a question mid-job. The current step's cards answer first; otherwise the best passages are found on this machine.") + `
    <div class="surface pad">
      <form class="askbar" id="ask-form"><input id="ask-q" placeholder="e.g. What should the dial indicator read at 360 degrees?" autocomplete="off"><button class="btn primary">Ask</button></form>
      <div class="ask-opts">
        <label class="switch"><input type="checkbox" id="ask-model"> Answer with Claude <span class="muted">· about $0.02, sends the top five passages</span></label>
        <label>Step context <select id="ask-proc"><option value="">None</option>${ps.map((p) => `<option value="${esc(p.id)}">${esc(p.title)}</option>`).join("")}</select></label>
        <select id="ask-step" class="hidden" aria-label="Step"></select>
        <label>Search <select id="ask-mode"><option value="bm25" ${s.retrieval === "bm25" ? "selected" : ""}>Exact terms (BM25)</option><option value="hybrid" ${s.retrieval === "hybrid" ? "selected" : ""}>Exact terms + SigLIP2 (hybrid)</option></select></label>
      </div>
      <div id="ask-out"></div>
    </div>`;
  $("#ask-proc").addEventListener("change", async (e) => {
    const sel = $("#ask-step");
    if (!e.target.value) { sel.classList.add("hidden"); return; }
    const d = await j(api(`/procedures/${encodeURIComponent(e.target.value)}`));
    sel.innerHTML = d.graph.nodes.map((nd, i) => `<option value="${esc(nd.id)}">${i + 1}. ${esc(nd.name)}</option>`).join("");
    sel.dataset.version = d.version;
    sel.classList.remove("hidden");
  });
  $("#ask-mode").addEventListener("change", (e) => saveSettings({ retrieval: e.target.value }, e.target.value === "hybrid" ? "Hybrid search on. Documents are re-indexed with SigLIP2 vectors (local)." : "Exact-term search on."));
  $("#ask-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const q = $("#ask-q").value.trim();
    if (!q) return;
    const btn = $("button", e.target);
    busy(btn, true, "Asking");
    $("#ask-out").innerHTML = `<div class="answer"><div class="skel w70"></div></div>`;
    try {
      const body = { question: q, use_model: $("#ask-model").checked };
      if ($("#ask-proc").value) { body.proc_id = $("#ask-proc").value; body.node = $("#ask-step").value; body.version = +$("#ask-step").dataset.version; }
      const a = await post(api("/ask"), body);
      spend(a.budget);
      const src = { card: "From the step's knowledge card", model: `Claude${a.cached ? " · cached" : ""}`, excerpt: "Quoted from the best matching passage · no model", none: "No match" }[a.source] || a.source;
      const short = (c) => c.page ? `${(c.title || "").split(" · ")[0]}, p. ${c.page}${c.page_end && c.page_end !== c.page ? `–${c.page_end}` : ""}` : (c.where || c.label || "");
      const cite = (c) => {
        const url = c.page && c.doc ? api(`/docs/${c.doc}/page/${c.page}.png`) : null;
        return url ? `<a class="cite" href="${url}" target="_blank" rel="noopener" title="${esc(c.where || "")}">${esc(short(c))}</a>` : `<span class="cite" title="${esc(c.where || "")}">${esc(short(c))}</span>`;
      };
      const seen = new Set();
      a.citations = (a.citations || []).filter((c) => { const k = short(c); if (seen.has(k)) return false; seen.add(k); return true; });
      $("#ask-out").innerHTML = `<div class="answer"><div class="a">${esc(a.answer)}</div>
        <div class="meta">${(a.citations || []).map(cite).join("")}<span>${esc(src)}</span><span>${a.cost_usd ? usd(a.cost_usd) : "$0"}</span><span>${Math.round(a.latency_ms)} ms</span>
        ${a.step ? `<span>Step: ${esc(a.step.name)}</span>` : ""}</div></div>
        ${(a.excerpts || []).length ? `<h2 class="sec">${a.source === "model" ? "Passages sent to the model" : "Best matching passages"} <span class="muted">found on this machine</span></h2>
        <div class="excerpts">${a.excerpts.map((x, i) => `<div class="excerpt"><div class="h"><span class="rk">${i + 1}</span>${x.page && x.doc ? `<a href="${api(`/docs/${x.doc}/page/${x.page}.png`)}" target="_blank" rel="noopener">${esc(x.where)}</a>` : esc(x.where)}<span>${esc(x.section)}</span></div><p>${esc(reflow(x.text))}</p></div>`).join("")}</div>` : ""}`;
    } catch (err) { $("#ask-out").innerHTML = `<div class="answer errors">${esc(err.message)}</div>`; }
    busy(btn, false);
  });
}

// ------------------------------------------------------------------ reference videos
async function pageVideos() {
  const vs = A.d.videos, ps = A.d.procedures;
  $("#main").innerHTML = head("Reference videos", "A demonstration of a procedure. Praxis picks one “what done looks like” frame per step on this machine ($0). The alignment is untested on maintenance video, so review every frame.") + `
    <label class="drop" id="vdrop"><span class="ico">${icon("videos")}</span><span class="txt"><b>Upload a demonstration video</b>MP4 or MOV. Stored with this company only.</span>
      <span class="btn">Choose video</span><input type="file" accept="video/*" hidden></label><div class="uploads" id="uploads"></div>
    ${vs.length ? `<h2 class="sec">${vs.length} video${vs.length === 1 ? "" : "s"}</h2><div class="surface"><table class="tbl"><thead><tr><th>Video</th><th class="num">Length</th><th>Make reference frames for</th><th></th></tr></thead><tbody>
      ${vs.map((v) => `<tr><td><div class="t1">${esc(v.filename)}</div><div class="t2">${date(v.uploaded_at)} · ${v.width || "?"}×${v.height || "?"}</div></td><td class="num">${v.duration_s ?? "?"} s</td>
        <td><select data-vp="${v.hash}">${ps.map((p) => `<option value="${esc(p.id)}:${p.latest_version}">${esc(p.title)} · v${p.latest_version}</option>`).join("") || "<option>No procedures yet</option>"}</select></td>
        <td class="acts"><button class="btn sm" data-vgo="${v.hash}" ${ps.length ? "" : "disabled"}>Make frames</button></td></tr>`).join("")}</tbody></table></div>`
      : `<div class="surface" style="margin-top:14px"><div class="empty"><b>No videos yet</b><p>Optional. Without a video, procedures still run; frames just help reviewers and trainees see the end state.</p></div></div>`}`;
  const z = $("#vdrop");
  $("input", z).addEventListener("change", (e) => uploadFiles([...e.target.files], () => pageVideos()));
  z.addEventListener("dragover", (e) => { e.preventDefault(); z.classList.add("over"); });
  z.addEventListener("dragleave", () => z.classList.remove("over"));
  z.addEventListener("drop", (e) => { e.preventDefault(); z.classList.remove("over"); uploadFiles([...e.dataTransfer.files], () => pageVideos()); });
  $$("[data-vgo]").forEach((b) => b.addEventListener("click", async () => {
    const [pid, ver] = $(`[data-vp="${b.dataset.vgo}"]`).value.split(":");
    busy(b, true, "Matching frames");
    try {
      const job = await post(api(`/procedures/${encodeURIComponent(pid)}/refs`), { version: +ver, video: b.dataset.vgo });
      const s = await poll(job.id);
      if (s.state !== "done") throw new Error(s.error);
      toast(`Saved ${s.result.n} reference frames. Review them on the procedure.`);
      location.hash = href("procedures", pid, ver);
    } catch (err) { busy(b, false); toast(err.message, true); }
  }));
}

boot();
