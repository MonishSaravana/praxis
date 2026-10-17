// Praxis Studio: choose input and task, run the live engine, flag problems, save or discard, replay saved sessions.
import { LogState, Hud, EngineerPanel, speakable } from "./hud.js";

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const money = (x) => (x < 0.1 ? x.toFixed(4) : x.toFixed(2));
const fmtT = (t) => `${Math.floor(t / 60)}:${(t % 60).toFixed(0).padStart(2, "0")}`;
const params = new URLSearchParams(location.search);
// Static export (praxis.site): saved sessions only, read from JSON files next to the page instead of the server.
const STATIC = document.body.dataset.static === "1";
const api = (p) => !STATIC ? p : p === "/api/status" ? "data/status.json" : p === "/api/sessions" ? "data/sessions.json"
  : p.startsWith("/api/sessions/") ? `data/sessions/${p.slice(14)}.json` : p.slice(1);

const S = {
  status: null, ws: null, running: false, input: "camera", stream: null, mediaStart: 0, mediaEnd: null,
  t0: 0, st: new LogState(), hud: null, eng: null, speech: true, engOpen: false, jobId: null, compiled: null,
  lastSentT: -1, pending: false, timer: null, raf: null, flagT: null, flagKind: null, lastStatus: null,
};

// ------------------------------------------------------------------ boot
async function boot() {
  const r = await fetch(api("/api/status"));
  S.status = await r.json();
  const m = S.status.models;
  setPill("#p-jev", m.jev ? "Jev ready" : "Jev key missing", m.jev ? "ok" : "bad");
  setPill("#p-claude", m.claude ? "Claude ready" : "Claude key missing", m.claude ? "ok" : "bad");
  $("#lib").innerHTML = S.status.library.map((t) =>
    `<option value="${t.task_id}">${esc(t.title)}${t.source === "pasted" ? " (pasted)" : ""} · ${t.n_steps} steps</option>`).join("");
  $("#clip").innerHTML = S.status.clips.map((c) =>
    `<option value="${c.clip_id}">${esc(c.clip_id)} · ${esc(c.task_id.replace("cc4d_", ""))}${c.split === "heldout_type" ? " (not in library)" : ""}</option>`).join("");
  S.hud = new Hud($("#stage"), S.status.label + " · Praxis Studio");
  S.hud.onAsk = (text) => describe(text);
  S.eng = new EngineerPanel($("#engineer"));
  if (STATIC) { window.addEventListener("hashchange", route); route(); return; }
  if (params.get("clip")) { $("#in-clip").checked = true; $("#clip").value = params.get("clip"); }
  if (params.get("fakecam")) $("#in-camera").checked = true;
  bindUI();
  if (!params.get("clip")) await listCameras();
  route();
}

function setPill(sel, text, cls) { const el = $(sel); el.textContent = text; el.className = `pill-s ${cls}`; }

async function listCameras() {
  if (!navigator.mediaDevices?.enumerateDevices) return;
  const devs = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "videoinput");
  $("#cam").innerHTML = devs.length
    ? devs.map((d, i) => `<option value="${d.deviceId}">${esc(d.label || `Camera ${i + 1}`)}</option>`).join("")
    : `<option value="">(allow camera access to list cameras)</option>`;
}

// ------------------------------------------------------------------ setup UI
function bindUI() {
  $$("input[name=input]").forEach((el) => el.addEventListener("change", () => setInput(el.value)));
  $$("input[name=task]").forEach((el) => el.addEventListener("change", () => setTask(el.value)));
  $("#cam-allow").addEventListener("click", async () => { await openCamera(); await listCameras(); });
  $("#cam").addEventListener("change", () => openCamera());
  $("#file").addEventListener("change", () => {
    const f = $("#file").files[0];
    if (f) { const v = $("#video"); stopStream(); v.srcObject = null; v.src = URL.createObjectURL(f); v.muted = true; S.mediaStart = 0; S.mediaEnd = null; }
  });
  $("#clip").addEventListener("change", () => loadClip());
  $("#compile").addEventListener("click", compile);
  $("#start").addEventListener("click", start);
  $("#stop").addEventListener("click", stop);
  $("#save").addEventListener("click", () => send({ type: "save" }));
  $("#discard").addEventListener("click", () => send({ type: "discard" }));
  $("#again").addEventListener("click", () => showPanel("setup"));
  $("#f-wrong").addEventListener("click", () => openFlag("wrong"));
  $("#f-missed").addEventListener("click", () => openFlag("missed"));
  $("#flag-form").addEventListener("submit", (e) => { e.preventDefault(); submitFlag(); });
  $("#retask").addEventListener("submit", (e) => {
    e.preventDefault();
    const v = $("#retask-text").value.trim();
    if (v && S.running) { describe(v); $("#retask-text").value = ""; $("#retask-text").blur(); }
  });
  $("#speech").addEventListener("change", (e) => { S.speech = e.target.checked; if (!S.speech) speechSynthesis.cancel(); });
  $("#eng-toggle").addEventListener("change", (e) => { S.engOpen = e.target.checked; $("#engineer").classList.toggle("hidden", !S.engOpen); });
  document.addEventListener("keydown", (e) => {
    if (!S.running || e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") {
      if (e.key === "Escape" && !$("#flag-box").classList.contains("hidden")) submitFlag(true);
      return;
    }
    if (e.key === "w" || e.key === "W") { e.preventDefault(); openFlag("wrong"); }
    if (e.key === "m" || e.key === "M") { e.preventDefault(); openFlag("missed"); }
  });
  window.addEventListener("hashchange", route);
  setInput($("input[name=input]:checked").value);
  setTask($("input[name=task]:checked").value);
}

function setInput(v) {
  S.input = v;
  $$(".in-opt").forEach((el) => el.classList.toggle("hidden", el.dataset.for !== v));
  const vid = $("#video");
  if (v === "camera") openCamera();
  else { stopStream(); vid.srcObject = null; if (v === "clip") loadClip(); else vid.removeAttribute("src"); }
}

function setTask(v) { $$(".task-opt").forEach((el) => el.classList.toggle("hidden", el.dataset.for !== v)); }

function stopStream() { if (S.stream) { S.stream.getTracks().forEach((t) => t.stop()); S.stream = null; } }

async function openCamera() {
  const vid = $("#video");
  vid.removeAttribute("src");
  stopStream();
  const fake = params.get("fakecam");
  try {
    if (fake) {
      // test path: a looping local clip played through captureStream() stands in for getUserMedia
      const src = document.createElement("video");
      src.src = `/dev/video/${fake}`; src.muted = true; src.loop = true; src.playsInline = true;
      src.style.display = "none"; document.body.appendChild(src);
      await src.play();
      S.stream = src.captureStream();
      $("#cam").innerHTML = `<option>Test camera: ${esc(fake)} (looped file)</option>`;
    } else {
      const id = $("#cam").value;
      S.stream = await navigator.mediaDevices.getUserMedia({ video: id ? { deviceId: { exact: id }, width: 1280, height: 720 } : { width: 1280, height: 720 }, audio: false });
    }
    vid.srcObject = S.stream; vid.muted = true;
    await vid.play();
    $("#cam-msg").textContent = "";
  } catch (e) {
    $("#cam-msg").textContent = `Camera unavailable: ${e.message || e}. Allow camera access in the browser, or use Upload.`;
  }
}

function loadClip() {
  const c = S.status.clips.find((x) => x.clip_id === $("#clip").value);
  if (!c) return;
  const v = $("#video");
  v.srcObject = null; v.muted = true;
  v.src = c.url; S.mediaStart = c.start; S.mediaEnd = c.end;
  v.addEventListener("loadedmetadata", () => { v.currentTime = c.start; }, { once: true });
}

async function compile() {
  const text = $("#instructions").value.trim();
  $("#compile-msg").textContent = "";
  const r = await fetch("/api/compile", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
  if (!r.ok) { $("#compile-msg").textContent = (await r.json()).detail; return; }
  let js = await r.json();
  S.jobId = js.id; S.compiled = null;
  $("#compile").disabled = true;
  const words = { queued: "Starting", splitting: "Splitting into steps", compiling: "Compiling steps, checks and fixes", embedding: "Embedding end states" };
  while (js.state !== "done" && js.state !== "error") {
    $("#compile-msg").textContent = `${words[js.state] || js.state}… ${js.elapsed_s}s${js.chars ? ` · ${js.chars.toLocaleString()} characters` : ""}`;
    $("#compile-bar").style.width = `${{ queued: 3, splitting: 12, compiling: 15 + Math.min(75, js.chars / 160), embedding: 95 }[js.state] || 5}%`;
    await new Promise((res) => setTimeout(res, 700));
    js = await (await fetch(`/api/compile/${S.jobId}`)).json();
  }
  $("#compile").disabled = false;
  if (js.state === "error") { $("#compile-msg").textContent = `Couldn't compile: ${js.error}`; $("#compile-bar").style.width = "0"; return; }
  S.compiled = js;
  $("#compile-bar").style.width = "100%";
  $("#compile-msg").textContent = `Ready: "${js.title}", ${js.n_steps} steps${js.cached ? " (compiled before)" : ` · ${js.elapsed_s}s · $${js.cost_usd.toFixed(3)}`}`;
}

// ------------------------------------------------------------------ live session
function wsConnect() {
  return new Promise((res, rej) => {
    const ws = new WebSocket(`ws://${location.host}/ws`);
    ws.binaryType = "arraybuffer";
    ws.onopen = () => { setPill("#p-conn", "Connected", "ok"); res(ws); };
    ws.onerror = () => rej(new Error("websocket error"));
    ws.onclose = () => { setPill("#p-conn", "Disconnected", "bad"); if (S.running) endRun(); };
    ws.onmessage = (ev) => onMessage(JSON.parse(ev.data));
  });
}

function send(obj) { if (S.ws && S.ws.readyState === 1) S.ws.send(JSON.stringify(obj)); }

async function start() {
  const task = $("input[name=task]:checked").value;
  const cfg = {
    type: "start", input: S.input, task_mode: task, escalation: $("#opus").checked,
    cost_cap: parseFloat($("#cap").value) || 1.0, speech: $("#speech").checked,
  };
  if (S.input === "camera") cfg.source_label = $("#cam").selectedOptions[0]?.textContent || "camera";
  else if (S.input === "upload") cfg.source_label = $("#file").files[0]?.name || "upload";
  else cfg.source_label = `test clip ${$("#clip").value}`;
  if (task === "library") cfg.task_id = $("#lib").value;
  if (task === "describe") cfg.description = $("#describe").value.trim();
  if (task === "paste") {
    if (!S.compiled) { alert("Compile the instructions first."); return; }
    cfg.job_id = S.jobId;
  }
  if (task === "describe" && !cfg.description) { alert("Type what you're doing, or pick Auto-recognize."); return; }
  if (S.input !== "camera" && !$("#video").src) { alert("Choose a video first."); return; }
  $("#start").disabled = true;
  try { S.ws = S.ws && S.ws.readyState === 1 ? S.ws : await wsConnect(); }
  catch (e) { alert("Can't reach the Studio server."); $("#start").disabled = false; return; }
  S.st.reset(); S.hud.setNames({}); S.eng.setNodes([]);
  $("#log").innerHTML = "";
  send(cfg);
}

function beginRun() {
  S.running = true;
  showPanel("run");
  const v = $("#video");
  if (S.input === "camera") S.t0 = performance.now();
  else {
    v.currentTime = S.mediaStart;
    v.play();
    v.onended = () => { if (S.running) stop(); };
  }
  S.lastSentT = -1;
  S.timer = setInterval(pumpFrame, 100);       // up to 10 fps; the server runs the engine at its 4 fps cadence
  const loop = () => { if (!S.running) return; drawNow(); S.raf = requestAnimationFrame(loop); };
  S.raf = requestAnimationFrame(loop);
}

function sessionTime() {
  const v = $("#video");
  return S.input === "camera" ? (performance.now() - S.t0) / 1000 : Math.max(0, v.currentTime - S.mediaStart);
}

const canvas = document.createElement("canvas");
function pumpFrame() {
  const v = $("#video");
  if (!S.running || S.pending || !v.videoWidth || S.ws.readyState !== 1 || S.ws.bufferedAmount > 1.5e6) return;
  if (S.input !== "camera" && S.mediaEnd && v.currentTime >= S.mediaEnd) { stop(); return; }
  const t = sessionTime();
  if (t <= S.lastSentT) return;
  const s = Math.min(1, 960 / Math.max(v.videoWidth, v.videoHeight));
  canvas.width = Math.round(v.videoWidth * s); canvas.height = Math.round(v.videoHeight * s);
  canvas.getContext("2d").drawImage(v, 0, 0, canvas.width, canvas.height);
  S.pending = true;
  canvas.toBlob(async (blob) => {
    S.pending = false;
    if (!blob || !S.running) return;
    const jpg = new Uint8Array(await blob.arrayBuffer());
    const buf = new ArrayBuffer(8 + jpg.length);
    new DataView(buf).setFloat64(0, t, true);
    new Uint8Array(buf, 8).set(jpg);
    S.ws.send(buf);
    S.lastSentT = t;
  }, "image/jpeg", 0.78);
}

function drawNow() {
  const tau = sessionTime();
  S.hud.draw(S.st, tau);
  if (S.engOpen) S.eng.draw(S.st, tau);
  $("#clock").textContent = fmtT(tau);
}

function onMessage(m) {
  if (m.type === "started") {
    setPill("#p-cost", `$0.000 / $${money(m.cost_cap_usd)}`, "ok");
    setPill("#p-opus", m.models.escalation ? "Opus on" : "Opus off", m.models.escalation ? "ok" : "off");
    beginRun();
  } else if (m.type === "rec") {
    const r = m.r;
    const tau = S.running ? sessionTime() : r.t;
    S.st.add(r, r.kind === "action" ? Math.max(r.t, tau - 0.05) : null);
    if (r.kind === "task") S.st.clearAsk();
    if (speakable(r)) { speak(r); logLine(r); }
  } else if (m.type === "graph") {
    const names = Object.fromEntries(m.nodes.map((n) => [n.id, n.name]));
    S.hud.setNames(names); S.eng.setNodes(m.nodes);
    $("#task-now").textContent = `${m.title}${m.draft ? " (drafted plan)" : ""}`;
  } else if (m.type === "status") {
    S.lastStatus = m;
    const cls = m.cap_hit ? "bad" : m.cost_usd > 0.8 * m.cost_cap_usd ? "warn" : "ok";
    setPill("#p-cost", `$${m.cost_usd.toFixed(3)} / $${money(m.cost_cap_usd)}${m.cap_hit ? " · cap reached" : ""}`, cls);
    const f = m.models.fast, o = m.models.strong;
    setPill("#p-jev", m.cap_hit ? "Jev paused (cost cap) · tracking locally" : f === "ok" ? "Jev ok" : "Jev offline · tracking locally",
      f === "ok" && !m.cap_hit ? "ok" : "bad");
    setPill("#p-opus", o === "off" ? "Opus off" : m.cap_hit ? "Opus paused (cost cap)" : o === "ok" ? "Opus ok" : "Opus offline",
      o === "ok" && !m.cap_hit ? "ok" : o === "off" ? "off" : "bad");
    if (m.last_error && f !== "ok") $("#errors").textContent = `Verifier error: ${m.last_error}`;
    $("#engstats").textContent = `engine ${m.frames_engine} frames · ${m.calls} model calls · ${m.pending_calls} out${m.lag_s != null ? ` · lag ${m.lag_s.toFixed(2)}s` : ""}`;
    if (!m.task) $("#task-now").textContent = "Recognizing the task…";
  } else if (m.type === "ask_task") {
    S.st.addAsk(sessionTime());
    if (S.speech) say("I don't recognize this task yet. What are you working on?", true);
  } else if (m.type === "stopped") {
    showEnd(m);
  } else if (m.type === "saved") {
    $("#end-msg").innerHTML = `Saved as <a href="#/sessions/${encodeURIComponent(m.id)}">${esc(m.id)}</a>. The HUD replay video renders in the background.`;
    $("#save").disabled = $("#discard").disabled = true;
  } else if (m.type === "discarded") {
    $("#end-msg").textContent = "Discarded. Nothing was kept.";
    $("#save").disabled = $("#discard").disabled = true;
  } else if (m.type === "error") {
    $("#errors").textContent = m.message;
    if (!S.running) $("#start").disabled = false;
  }
}

function describe(text) {
  send({ type: "describe", text });
  S.st.clearAsk();
  logLine({ t: sessionTime(), action: "you", text: `"${text}"` });
}

function speak(r) {
  if (!S.speech) return;
  say(r.text, r.action === "mistake" || r.action === "view_request");
}
function say(text, urgent) {
  if (urgent) speechSynthesis.cancel();
  else if (speechSynthesis.pending) return;           // don't queue up: real time beats completeness
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 1.05;
  speechSynthesis.speak(u);
}

function logLine(r) {
  const el = document.createElement("div");
  el.className = `ll ${r.action}`;
  el.innerHTML = `<b>${fmtT(r.t)}</b> ${esc(r.action === "announce_task" ? "task" : r.action)} · ${esc(r.text)}`;
  $("#log").prepend(el);
}

function openFlag(kind) {
  if (!S.running) return;
  S.flagT = sessionTime(); S.flagKind = kind;
  $("#flag-box").classList.remove("hidden");
  $("#flag-kind").textContent = kind === "wrong" ? "That's wrong" : "It missed something";
  $("#flag-note").value = "";
  $("#flag-note").focus();
  S.flagTimer = setTimeout(() => submitFlag(), 12000);
}
function submitFlag(skipNote = false) {
  if (S.flagT == null) return;
  clearTimeout(S.flagTimer);
  send({ type: "flag", kind: S.flagKind, note: skipNote ? "" : $("#flag-note").value.trim(), t: S.flagT });
  logLine({ t: S.flagT, action: "flag", text: `${S.flagKind === "wrong" ? "That's wrong" : "It missed something"}${$("#flag-note").value && !skipNote ? `: ${$("#flag-note").value}` : ""}` });
  S.flagT = null;
  $("#flag-box").classList.add("hidden");
}

function stop() {
  if (!S.running) return;
  endRun();
  send({ type: "stop" });
  $("#end-msg").textContent = "Stopping: waiting for model answers still out…";
  showPanel("end");
}
function endRun() {
  S.running = false;
  clearInterval(S.timer);
  cancelAnimationFrame(S.raf);
  $("#video").pause();
  speechSynthesis.cancel();
  $("#start").disabled = false;
}

function showEnd(m) {
  showPanel("end");
  const acts = Object.entries(m.actions || {}).map(([k, v]) => `${v} ${k.replace("_", " ")}`).join(", ") || "nothing";
  $("#end-sum").innerHTML = `<div><b>${esc(m.task?.title || "No task recognized")}</b></div>
    <div>${fmtT(m.duration_s)} · ${acts} · ${m.flags} flag${m.flags === 1 ? "" : "s"} · $${m.cost_usd.toFixed(3)}</div>`;
  $("#end-msg").textContent = "Save keeps the video, run log, flags and a summary in sessions/ (gitignored). Discard keeps nothing.";
  $("#save").disabled = $("#discard").disabled = false;
}

function showPanel(name) {
  $$(".panel").forEach((p) => p.classList.toggle("hidden", p.id !== `panel-${name}`));
  $("#runbar").classList.toggle("hidden", name !== "run");
  $("#retask").classList.toggle("hidden", name !== "run");
}

// ------------------------------------------------------------------ sessions
function route() {
  const h = location.hash;
  if (STATIC && !h.startsWith("#/sessions")) { location.replace("#/sessions"); return; }
  $("#view-live").classList.toggle("hidden", h.startsWith("#/sessions"));
  $("#view-sessions").classList.toggle("hidden", !h.startsWith("#/sessions"));
  $$("nav a").forEach((a) => a.classList.toggle("on", (a.getAttribute("href") === "#/sessions") === h.startsWith("#/sessions")));
  if (h.startsWith("#/sessions/")) openSession(decodeURIComponent(h.slice(11)));
  else if (h.startsWith("#/sessions")) listSessions();
}

async function listSessions() {
  $("#replay").classList.add("hidden");
  const list = await (await fetch(api("/api/sessions"))).json();
  $("#sessions").classList.remove("hidden");
  $("#sessions").innerHTML = list.length ? `<table><tr><th>When</th><th>Task</th><th>Length</th><th>Praxis said</th><th>Flags</th><th>Cost</th><th>Replay video</th></tr>` +
    list.map((s) => {
      const a = s.actions || {}, c = s.cost || {};
      const cost = (c.verifier_usd || 0) + (c.draft_usd || 0) + (c.compile_usd || 0);
      return `<tr><td><a href="#/sessions/${encodeURIComponent(s.id)}">${esc(s.created)}</a></td><td>${esc(s.task?.title || "none")}${s.task?.draft ? " (draft)" : ""}</td>
        <td>${fmtT(s.duration_s)}</td><td>${a.instruct || 0} steps, ${a.mistake || 0} mistakes, ${a.view_request || 0} view requests</td>
        <td>${s.flags}</td><td>$${cost.toFixed(3)}</td><td>${esc(s.replay?.status || "-")}</td></tr>`;
    }).join("") + `</table>` : `<p class="muted">No saved sessions yet. Run one and press Save.</p>`;
}

async function openSession(sid) {
  $("#sessions").classList.add("hidden");
  const d = await (await fetch(api(`/api/sessions/${encodeURIComponent(sid)}`))).json();
  const s = d.session;
  $("#replay").classList.remove("hidden");
  const st = new LogState();
  d.records.forEach((r) => st.add(r));
  const names = Object.fromEntries(d.nodes.map((n) => [n.id, n.name]));
  const stage = $("#rstage");
  stage.querySelectorAll(".hud").forEach((x) => x.remove());
  const hud = new Hud(stage, `${S.status?.label || "Praxis prototype v0 · real model output"} · Praxis Studio replay`);
  hud.setNames(names);
  const eng = new EngineerPanel($("#rengineer"));
  eng.setNodes(d.nodes);
  const v = $("#rvideo");
  v.src = api(`/files/${encodeURIComponent(sid)}/camera.mp4`);
  const dur = Math.max(1, s.duration_s);
  $("#rmeta").innerHTML = `<b>${esc(s.task?.title || "No task")}</b> · ${esc(s.created)} · ${fmtT(s.duration_s)} · input ${esc(s.input)} (${esc(s.source || "")})
    · <a href="${api(`/files/${encodeURIComponent(sid)}/SUMMARY.md`)}" target="_blank">SUMMARY.md</a>
    · <a href="${api(`/files/${encodeURIComponent(sid)}/live.jsonl`)}" target="_blank">run log</a>
    ${s.replay?.status === "ready" ? ` · <a href="${api(`/files/${encodeURIComponent(sid)}/hud_replay.mp4`)}" target="_blank">HUD replay MP4</a>` : ` · HUD replay: ${esc(s.replay?.status || "-")}`}`;
  $("#rflags").innerHTML = d.flags.map((f) =>
    `<button class="fl ${f.kind}" style="left:${(100 * f.t) / dur}%" title="${esc(f.note || "")}" data-t="${f.t}">${f.kind === "wrong" ? "✕" : "?"}</button>`).join("");
  $$("#rflags .fl").forEach((b) => b.addEventListener("click", () => { v.currentTime = Math.max(0, +b.dataset.t - 4); v.play(); }));
  $("#rflaglist").innerHTML = d.flags.length ? d.flags.map((f) => `<div><a href="#" data-t="${f.t}">${fmtT(f.t)}</a> ${f.kind === "wrong" ? "That's wrong" : "It missed something"}${f.note ? `: ${esc(f.note)}` : ""}</div>`).join("") : `<span class="muted">No flags.</span>`;
  $$("#rflaglist a").forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); v.currentTime = Math.max(0, +a.dataset.t - 4); v.play(); }));
  const loop = () => {
    if ($("#replay").classList.contains("hidden")) return;
    hud.draw(st, v.currentTime);
    eng.draw(st, v.currentTime);
    $("#rcursor").style.left = `${(100 * v.currentTime) / dur}%`;
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
}

boot();
