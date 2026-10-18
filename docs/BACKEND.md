# Company backend: knowledge portal and locked procedures

Status, 2026-10-17 (evening). This is `NEXT.md` item 4, first version, built into Praxis Studio (`uv run praxis studio`,
then **Company admin**). The founder approved the downloads and paid runs in section 8; their results are there.
Everything marked **ran** below was run on this machine.

| Part | State |
|---|---|
| Company profiles (create, select, settings), stored locally | **Ran** (three companies on disk: Hydro Plant Demo, Test Kitchen, Test Co) |
| Upload PDF / .txt / .md / .docx; video as reference | **Ran** for PDF (three real manuals), Markdown, text and Word (tests). Video upload not run on a real video |
| Ingest once, locally | **Ran** on three public manuals: 97, 222 and 125 pages, 0.5–1.8 s each, $0 |
| Find procedures (headings, bookmarks, numbered steps) | **Ran**; tuned on the real manuals (section 3). Precision is not measured |
| Compile one procedure from only its section (Opus 5.5, cached) | **Ran**: FIST 4-1A §2.8.2 (11 steps, $0.164) and a recipe card (17 steps, $0.188) |
| Knowledge cards per step (quoted from the source, with page) | **Ran** (both compiled procedures, plus tests) |
| Runtime: company library, locked mode, step cards, safety banner | **Ran** live with real verifiers on a local test clip (section 8, P3 and its re-run): locked start worked; on the re-run steps committed and instructions advanced through 12 of 17 steps, with some back-and-forth. Both runs shared the GPU with other jobs; tracking accuracy is **not measured** |
| Questions: card answer, local retrieval, Claude answer with citation | **Ran**: three Claude answers with page or section citations, $0.0065–0.0128 each |
| Admin page (redesigned): overview, documents, sections, compile estimate, review with source and page preview, approve, safety flags, versions, live deployment, ask, videos | **Ran** in the browser at 1024 and 1440 px wide and phone width |
| Reference keyframes from a video | Built; alignment unit-tested on synthetic similarities; **not run on a video** |

## 1. The rule this is built around

**A document is never sent to a model during a live run.** It is parsed once on this machine. Only the procedures a
manager picks are compiled, each from its own section's text (the estimate screen shows "sends 409 of 612
characters"). The live engine gets the compiled graph and short cards. A question sends five short excerpts, not
the document.

## 2. Data model (all local, gitignored: `sessions/orgs/<org_id>/`)

```
sessions/orgs/
  spend.json                     backend spend ledger (every paid call, its tokens and cost); enforces the cap
  <org_id>/
    org.json                     {id, name, created, settings: {locked, assigned: [proc ids], qa_model, retrieval}}
    documents.json               logical document (by file name) -> versions [{version, hash, filename, uploaded_at}]
    docs/<sha256>/               one uploaded file, ingested once, never overwritten
      source.pdf|.md|.txt|.docx  the file as uploaded
      meta.json                  status, pages, parser, paged (real page numbers?), counts, ingest time
      parsed.json                text per page (or per part) + PDF bookmarks
      sections.json              lines with page numbers, section tree, numbered step runs, procedure scores
      index.json                 chunks (about 900 chars; section path; page range) + BM25 tokens
      dense.npz                  SigLIP2 text vectors (only when hybrid retrieval is on)
      pages/p0012.png            page renders, made on demand for citations
    procedures/<proc_id>/
      proc.json                  {task_id, versions: [...], approved_version}
      v<N>/graph.json            TaskGraph the live engine uses (graph.compiled.json = untouched compiler output)
      v<N>/cards.json            {node_id: [cards], "_procedure": [cards]}
      v<N>/review.json           {safety: [node ids], safety_suggested, notes, edited}
      v<N>/source.txt            exactly the section text the compiler saw
      v<N>/emb.npz               SigLIP2 end-state embeddings (zero-shot step matching)
      v<N>/refs/                 reference keyframes per step + refs.json
    compile_cache/<hash>.json    compiler output by content hash (same text again = $0)
    qa_cache/<hash>.json         answers by (question, step, excerpts, model)
    videos/<sha256>/             reference videos
```

- **Versions.** Re-uploading a file with the same name adds a version; the old file and its index stay. A procedure
  version is never edited once approved: editing it creates a new draft version (`parent` recorded). The live engine
  uses `approved_version` until a newer one is approved. When the source document gets a new version, the admin
  page shows "document updated" and offers a recompile of the same section (matched by title) as a new draft.
- **What a worker followed** stays on record: saved Studio sessions already store the exact `taskgraph.json`, and
  `config.json` now also stores `org_procedures` (procedure id and version per task).
- **Deleting a company** is deleting its folder.

## 3. Ingest pipeline (local, $0, once per file hash)

Code: `prototype/praxis/knowledge/` (`parse.py`, `sections.py`, `chunk.py`, `index.py`, `ingest.py`).

1. **Hash** the upload (SHA-256). Same bytes again: nothing new.
2. **Parse.** PDF through macOS PDFKit, via a small Swift tool built once into `cache/bin/` (no new Python package).
   Word is read from its XML (a .docx is a zip). Text and Markdown are split at form feeds or into ~4,000-character
   parts. PDFs with almost no text layer are refused with "OCR is not built yet".
3. **Section map, local heuristics.** Running headers and footers removed (lines repeated on 40%+ of pages);
   headings from PDF bookmarks, numbered headings ("4.2 Replacing the filter"), "Chapter/Section/Procedure N",
   Markdown `#`, short ALL-CAPS lines; table-of-contents lines skipped. Sections nest (a section runs to the next
   heading at its level or above). **Procedure finder:** numbered step runs ("1.", "Step 2:"), with
   WARNING/CAUTION/NOTE lines attached to the step they precede; each section scored 0–1 on step count, imperative
   verbs and a procedure-like title. A manager can still compile any section.
   - The optional cheap model call for a section map is **not built**: the local scan comes first, and it is only
     worth adding if real manuals defeat it (unmeasured until a real manual is ingested).
4. **Chunk**: about 900 characters, never across a section boundary, each with its page range and section path.
5. **Index**: BM25 tokens with unit and part-number normalization ("9 N·m" = "9 Nm", "P/N"). Optional SigLIP2
   text vectors (the text tower already in the stack; it reads at most 64 tokens, so it sees the section title and
   the chunk's start) fused by reciprocal rank. BM25 is the default; hybrid is **not yet measured** to help.

Timing (BM25, measured): 97 pages in 0.5 s, 125 pages in 0.7 s, 222 pages in 1.2–1.8 s. Dense SigLIP2 vectors are
only built when a company turns on hybrid search (17.9 s for a 3-page file, almost all of it the first SigLIP2 call;
not timed on a large manual).

## 4. Compile per procedure (paid, cached)

Code: `knowledge/compile.py`, using the existing compiler (`tasks/compiler.py`). One small addition there: when the
compiler drops steps it now attaches the call's usage and output to the error, so the cost is still recorded.

1. The manager picks a section; the page shows what will be sent (characters sent vs the whole document, the first
   1,200 characters, step source, token estimate, $ estimate and upper bound, spend so far).
2. Steps: the manual's own numbering when it has 3–20 steps (free, and `s4` is the manual's step 4); otherwise
   Studio's split prompt (one small Opus call, effort low).
3. Compile with Opus 5.5 (effort medium) from **only that section's text**. The request needs `confirm_usd` at least
   the upper estimate, the ledger checks a worst case (32,000 output tokens) against the cap first, and the real
   token cost is recorded after. Cached by content hash.
4. **Knowledge cards**, local, verbatim: specs (torque, pressure, temperature, electrical, volume, dimension,
   interval), part numbers, tools lists, WARNING/CAUTION/DANGER/NOTE lines, figure/table references, each with its
   page. With the manual's numbering, a step's cards come from that step's lines plus the warnings just before it;
   otherwise each compiled step is matched to its best lines by BM25.
5. **Safety-critical suggestions**: steps with a WARNING/DANGER card or safety wording (lockout, tag out,
   de-energize, depressurize, PPE...). Only suggestions; the manager ticks the box.
6. SigLIP2 end-state embeddings (local), so the tracker can match steps zero-shot.

## 5. Runtime flow (Studio live session)

Code: `studio/org_session.py`, `studio/static/org.js`, two one-line hooks in `app.js`, three in `server.py`.

1. Live page → **0 · Company** picker. The start message carries `org_id`.
2. The session's library is that company's **approved** procedures (approved versions only). Recognition among them
   uses the harness's zero-shot recognizer (SigLIP2 frame vs each graph's title) plus the verifier's typed "which
   task?" check, whose options are only these procedures.
3. **Locked mode**: only the assigned procedure(s). One assigned: it starts at t=0 ("assigned"), no recognition, no
   drafting. Several: closed-set recognition among them. Typing an unrelated task never drafts a plan or switches;
   the wearer hears "This job is locked to: …". Pasted instructions are refused with a company profile.
   - **Ran** ($0, verifier calls off, fixture company on a local CaptainCook4D clip): one assigned → started at
     t=0; step cards sent per step; the safety banner fired once on the flagged step; an unrelated description in
     locked mode with two assigned gave the notice and no drafter. Closed-set accuracy is **not measured**.
4. **What the live engine sees**: the compiled graph only (the same verifier prompts as before, built from step
   names, checks and mistakes). Cards go to the browser: the operator panel shows the current step's cards and
   reference frame; the wearer view shows only a short safety banner (and speaks it) on steps a manager marked
   safety-critical. The graph is still never shown to the wearer.
5. **Questions** (text box for now; voice is another session's work): the current step's cards first (a torque,
   part, warning, tool or figure question a card answers: $0, about 0 ms, cited by page); otherwise top-5 chunks
   by local search plus the current step go to Claude, which must cite excerpt ids or say the documents don't cover
   it; answers are cached. With "Answer with Claude" off (the default until approved) or no budget left, the best
   matching line of the top excerpts is quoted with its page. Every question is written to the session's run log.

## 5b. Admin page (Studio → Company admin)

Internal view for a maintenance manager; technicians never see it. Left sidebar: company switcher, sections, model
spend against the cap. Pages, in workflow order:
- **Overview**: the three steps (documents → procedures → live) with real counts, and what leaves the machine.
- **Documents**: drag-and-drop upload with per-file progress, then a table (pages, sections, likely procedures, index).
- **A document**: its section map, filtered to likely procedures or all sections, with a five-bar likelihood and the
  first steps. "Compile…" opens an inline estimate (characters sent and share of the document, step source, cost and
  upper bound, spend so far, a preview of the exact text) before anything is sent. Rename and re-index.
- **Procedures**: status (approved / draft, which version is live), source, steps, safety count, live assignment.
- **A procedure**: editable steps (name, spoken instruction, expert cue, end state, checks), safety-critical switch,
  knowledge cards with page links, compiled mistakes, reference frame; beside them the exact text the compiler saw,
  with page markers that open the rendered manual page. Edits collect in a save bar; saving an approved version makes
  a new draft; approving asks for an inline confirmation. Version picker; recompile when the document has a new
  version.
- **Live deployment**: open coach or locked procedure, assignment of approved procedures, and a plain sentence saying
  what a technician gets.
- **Ask the documents**: the question box with optional step context, Claude on/off, search mode, the answer with
  citation chips that open the page, and the passages found locally.
- **Reference videos**: upload and per-step frames.

## 6. What runs locally vs what is sent to a model

| Step | Where | What leaves the machine |
|---|---|---|
| Upload, parse, section map, procedure finder, chunking, BM25, page renders | Local | Nothing |
| SigLIP2 vectors (hybrid retrieval, step embeddings), reference keyframes | Local | Nothing |
| Knowledge cards and safety suggestions | Local | Nothing |
| Compile one procedure | Claude Opus 5.5 | That section's text only (plus the step list) |
| Split steps (only if the section has no usable numbering) | Claude Opus 5.5, effort low | That section's text only |
| Live coaching | Unchanged | Event-triggered keyframes and crops to the verifier, as before. No document text |
| Question answered by a card or a quote | Local | Nothing |
| Question answered by Claude | Claude (Opus 5.5 by default) | The question, the current step's name and instruction, five excerpts (about 900 characters each) |

## 7. Cost (Opus 5.5: $4 / M input, $20 / M output, from `praxis/verify/common.py`)

**Per document: ingest is $0.** You pay only for the procedures you compile, once each.

Compile estimate per procedure, from Studio's first Opus 5.5 compile (9 steps, 687 source characters: 2,291 input and
5,602 output tokens, $0.121, plus a $0.0056 split call): input ≈ 2,000 + characters/3.3 + 15 per step tokens; output ≈
650 per step + 500 tokens; upper bound shown = 1.5× the estimate. Checked against the two approved compiles: 11 steps
from 5,148 characters came in at 3,893 / 6,786 tokens, $0.151 (estimate $0.181); 17 steps from 1,320 characters at
2,846 / 8,828, $0.188 (estimate $0.242).

| Section | Input tok | Output tok | Estimate | Upper |
|---|---|---|---|---|
| 6 steps, 409 chars (the synthetic test section, as shown in Studio) | 2,214 | 4,400 | $0.097 | $0.15 |
| 12 steps, 6,000 chars | ~4,000 | ~8,300 | ~$0.18 | ~$0.27 |
| 20 steps, 15,000 chars | ~6,800 | ~13,500 | ~$0.30 | ~$0.45 |
| + split call, only without usable numbering (6,000 chars) | ~2,100 | ~700 | ~$0.02 | |

A 300-page manual with 25 procedures compiled would be about 25 × $0.2 ≈ $5, once (arithmetic, not measured).
For comparison, sending a 300-page manual (very roughly 150,000 tokens) with every question would cost about $0.60 in
input alone per question.

**Per question** (estimates; no Claude answer has run yet):

| Path | Tokens | Cost |
|---|---|---|
| Answered from the step's card, or quoted from the manual | none | $0 |
| Claude Opus 5.5, effort low (default) | ~1,700 in, ~400 out (thinking at low effort is unmeasured) | ~$0.015 (cap per call: 1,500 out = $0.037) |
| Claude Sonnet 5.5 (setting) | same | ~$0.007 |
| Claude Haiku 5.5 (setting) | same | ~$0.0004 |

**Guards.** `knowledge/budget.py`: the existing `Budget(max_calls, max_usd)` with its total kept in
`sessions/orgs/spend.json`, so the cap holds across restarts. Default $5 and 200 calls in total
(`PRAXIS_BACKEND_CAP_USD`, `PRAXIS_BACKEND_MAX_CALLS`). Each call checks a worst case first. A compile needs an
explicit `confirm_usd` (the admin page asks). Claude answers are off by default in the question box. Live sessions
keep their own per-session cap as before.

## 8. Approved runs and results (2026-10-17)

The founder approved downloads D1–D3 and paid runs P1–P4 (estimate ~$0.48, at most ~$0.94).

**Downloads** (public US-government documents, public domain, born-digital), stored under `data/manuals/`
(gitignored): FIST 1-1 *Hazardous Energy Control Program* (3.2 MB, 97 pages), FIST 4-1A *Maintenance Scheduling
for Mechanical Equipment* (4.3 MB, 222 pages), FIST 3-8 *Protective Relays* (2.1 MB, 125 pages), all from
usbr.gov. Ingested locally into the company "Hydro Plant Demo" in 0.5–1.8 s each (444 pages, 998 passages).

**What the real manuals changed in the section finder** (all local): headings printed without their numbers
("Request clearance." for bookmark "11.3.1 Request clearance.") are now matched; numbered requirement lists and
inspection checklists no longer outrank real procedures (steps count only as far as they are actions, including
role steps like "The Job Supervisor must: a. Determine …"); table-of-contents lines are not steps; sections whose
numbering restarts (face readings 1–3, then rim readings 1–3) use the split call so no steps are lost. Cards now read
fractions ("1/2-inch") and angles ("90-degree", "360 degrees").

**Paid runs** (spend ledger `sessions/orgs/spend.json`; Studio session `cost.json`):

| # | Run | Result | Cost |
|---|---|---|---|
| P1 | Compile FIST 4-1A §2.8.2 *Face and Rim Alignment Method* (pp. 64–69). Sent 5,148 of 430,303 characters (1.2%) | 11 steps; 3,893 input and 6,786 output tokens (estimate was ~3,700 and ~8,300), 56 s. Approved v1 | $0.151 + $0.013 split |
| P1 (first attempt) | Same section. The split call ran ($0.013); the compile call returned only 2 of 12 steps and the shared compiler raised before reporting its cost | **That call's cost was not recorded** (bounded by its 32,000-token limit at $0.66; likely far less). The failure path now records cost and keeps the split result | $0.013 + unrecorded |
| P2 | Recipe card written from CaptainCook4D's public recipe text (17 numbered steps, no download), compiled with the manual's own numbering | 17 steps; 2,846 in, 8,828 out, 72 s. Approved v1 and locked | $0.188 |
| P3 | Studio session, Test Kitchen locked to that procedure, local pinwheels test clip 10_18_0, 299 s, Jev + Opus escalations, cap $0.25 | Locked start worked (task started at t=0, "assigned"). The tracker moved from step 1 to step 3 by ~94 s but committed no step, so only one instruction was spoken. The engine processed only 180 of 1,200 frames: local encoders took 1,431 ms per frame (median) versus ~43 ms in earlier Studio sessions, because other sessions were running GPU feature extraction at the same time. This run does not measure tracking | $0.034 |
| P3 re-run (approved, cap $0.10, 2026-10-18 03:39) | Same clip and company, started after the feature jobs ended | **Steps committed and instructions advanced**: 6 commits (s3, s6, s7 verified by the verifier; s2, s1, s4 by belief switch) and spoken instructions for 12 of the 17 steps in order (s1 → s12) over 5 minutes, plus 2 hints. Not clean: an early hint for s4 at 67 s, a late commit of s1 at 209 s, and s8's instruction repeated at 291 s after s12, so the tracker jumped back and forth near the end. Still not an idle machine: another session's multitask training job (4 workers) was running, encoders took 731 ms per frame (median) and the engine processed 486 of 1,200 frames. One clip, no ground-truth comparison: not an accuracy figure | $0.091 |
| P4 | Three questions answered by Claude, effort low | See below | $0.029 |
| | **Recorded total** | | **$0.519** + one unrecorded call |

Questions (P4), every answer real output:
- During P3, "Why do I leave half an inch uncovered at the edges?": "The recipe card says to leave 1/2 inch uncovered at
  the edges but doesn't explain why … check with a supervisor." Cited the recipe card section; it did not invent a
  reason. 1,167 in / 92 out, $0.0065.
- "What should the dial indicator read at 360 degrees, and what do I do if it doesn't?": "It should read zero at 360
  degrees. If it doesn't, re-zero the indicator and retake the readings." Cited FIST 4-1A p. 68 and pp. 71–72.
  2,760 in / 88 out, $0.0128, 3.2 s.
- "Before a clearance is issued, who has to check and sign the switching program?": answered from §11.3.3 (Job
  Supervisor verifies and signs to accept; Operations Supervisor signs, dates and logs to issue), cited FIST 1-1 p. 41.
  Correct for that page, but retrieval missed the more relevant §11.3.2 step on pp. 39–40 (a second Operations
  Supervisor checks and signs). One example; retrieval quality is not measured. 1,808 in / 112 out, $0.0095.

Per-question cost came in under the estimate (88–112 output tokens, not ~400). Network note: from this sandbox, calls
to the Anthropic API failed TLS through the proxy and were run outside it; nothing about that affects Studio itself.

## 9. How a device adapter passes a company profile

The glasses (or a phone) adapter speaks the same WebSocket as the Studio page (`/ws`, protocol in
`studio/server.py`):

1. At setup, the device is given a company id (later: scanned from a QR code on the admin page, with a device token;
   **auth is not built**, Studio binds to 127.0.0.1 only).
2. Session start: `{"type": "start", "org_id": "acme-pumps", "input": "glasses", "task_mode": "auto",
   "escalation": true, "cost_cap": 1.0}`. The server builds the company's library; locked mode and the assigned
   procedure come from the company settings, so the device doesn't need to know them. (Per-worker assignment waits
   for profiles, `NEXT.md` item 3.)
3. Frames: binary messages, 8-byte little-endian session time + one JPEG, as now.
4. Server messages the adapter can use besides the existing ones: `org_task`, `org_step` (current step and cards),
   `org_safety` (speak and show), `org_notice`.
5. Questions: `POST /api/orgs/<org_id>/ask {"question", "session_id", "use_model"}` with the `session` id from the
   `started` message; a voice adapter transcribes and posts the text. The reply has `answer`, `citations` (page or
   section) and `source` (card, excerpt, model).

## 10. Not built yet

OCR for scanned PDFs; figures as images (only page renders); slides and legacy .doc; logins and multi-user orgs;
the round-trip check (re-read the document against the graph); per-worker assignment; the model section-map
fallback; measured retrieval quality (BM25 vs hybrid) on a real manual; tested reference-keyframe alignment;
closed-set recognition accuracy; anything on maintenance footage.

## Files

New: `prototype/praxis/knowledge/` (`__init__`, `parse`, `pdfkit_tool.swift`, `sections`, `chunk`, `index`, `cards`,
`store`, `ingest`, `budget`, `compile`, `qa`, `video`), `prototype/praxis/studio/org_api.py`,
`prototype/praxis/studio/org_session.py`, `prototype/praxis/studio/static/{admin.html, admin.css, admin.js, org.js}`,
`prototype/tests/test_knowledge.py` (17 tests; the full suite, 47 tests, passes). Small additive edits:
`studio/server.py`, `studio/static/app.js`, `studio/static/index.html`, `tasks/compiler.py` (error carries usage),
`.claude/launch.json` (a Studio entry on port 8801), `docs/NEXT.md` (item 4 status line). Data (gitignored):
`data/manuals/` (three FIST PDFs and the recipe card), `sessions/orgs/` (three companies, spend ledger),
`sessions/20261017_233645_making-pinwheels/` (the P3 session, with its HUD replay).
