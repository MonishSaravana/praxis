# Build brief: Praxis prototype v0 + evaluation harness

## Context
Read `context/APPLICATION.md` first. Praxis is a software layer for consumer smart glasses that tracks a user's progress through a physical procedure, catches mistakes, and asks for a better view when it's unsure. I have a grant interview on **Tuesday Oct 20, 2026**. In the application I said I was "building an evaluation pipeline around 48 real procedural videos spanning 8 categories and 192 labeled action states" and would next "benchmark step recognition, mistake detection, and latency." This build makes that true.

Goal: by **Sunday night (Oct 18)**, have a working prototype of the task-state engine, run on real first-person procedural video, with **measured** results and demo clips rendered from the engine's actual outputs. The deck and pitch video will be built from what this produces.

## What it should feel like to the user
A coach watching over your shoulder, working on its own with no setup:
1. **Recognizes the task by itself.** Within the first several seconds: "Looks like you're assembling a toy truck. Want me to walk you through it?" It also works if the user starts partway through, by figuring out which step they're already on.
2. **Coaches proactively.** It says the next step when the current one is done, without waiting to be asked.
3. **Catches mistakes as they happen**, with a specific fix: "That wheel is on backwards, flip it before you screw it in." When possible, it catches them early, e.g. when the wrong part gets picked up.
4. **Asks for a better view when it can't tell**, instead of guessing.
5. **Adjusts how much detail it gives, automatically.** The main signal is **time on step versus the typical time for that step**, taken from the task graph's duration priors and the dataset's step durations. Mistakes and repeats count too.
   - When someone is taking abnormally long, the explanation expands: the step gets broken into sub-steps, Praxis says which part to grab and where it goes, and it offers a hint.
   - When someone is moving fast, instructions stay terse, in expert style.

Brand lines: **"Instructions that can finally see how you're doing."** and **"AI guidance for the physical world."** Use them in the README, the viewer title, and the end card of renders.

### Two views, kept separate
- **User view (what a wearer sees).** Unobtrusive and voice-first. The task graph, beliefs, and confidences are **never** shown.
  - A small persistent progress indicator (e.g. a thin progress bar with "4/7" in a corner) that updates as the person works.
  - The current instruction appears as a short card, then collapses to a one-line chip.
  - Verification is a brief subtle check pulse, not a big card.
  - Only mistakes and view requests get a prominent card. A view request includes a directional arrow.
  - At most one card on screen at a time, and cards fade on their own.
  - Showcase renders use this view, starting with a brief "Task recognized" card.
- **Engineer view ("under the hood," for the technical part of the pitch only).** Shows the same run with the step-belief bars over the task graph, the event-detector trace, the point tracks, each verifier call with its latency and confidence, and the policy decision. Render at least one showcase clip in both views so they can be cut side by side.

## Non-negotiable integrity rules
Everything here goes in front of grant reviewers who will ask follow-up questions.
1. Every number comes from code that ran and was saved under `results/`. Never type a metric in by hand, round it up, or estimate it.
2. A clip labeled "model output" is rendered **only** from a saved event log the pipeline produced. No hand-placed overlays on those clips.
3. Picking the best runs for showcase clips is fine. They have to be shown alongside the aggregate metrics, plus at least one clearly labeled failure case.
4. Don't claim glasses support. Build a camera-agnostic input layer; the glasses adapter stays a documented stub until it's actually tested on hardware.
5. Write down what didn't work. A modest honest number with a clear failure analysis is more useful to me than a polished one I can't defend.

## What to build: a layered engine, not a prompt
This must not be "a Claude wrapper with a nice prompt." Build it as layers with clean interfaces, where most of the layers are **ours** and the frontier model is one swappable part. The strategy is an MVP that leans on a frontier model for the hard judgment calls today, and that logs everything so we can replace that model with our own faster, cheaper, specialized models over time. Show the first step of that replacement this weekend.

It runs at two speeds: local layers run on every frame in milliseconds, and the verifier only runs when something happens.

**L0 · Input (ours).** `FrameSource` interface with `FileSource`, `WebcamSource` (a Mac sees an iPhone as a webcam through Continuity Camera, which works as a stand-in for a head-mounted view), and a `MetaGlassesSource` stub. Research the current state of Meta's wearables developer toolkit (camera access through a companion phone app) and write `docs/GLASSES.md`: what the adapter needs, the expected latency/resolution/bandwidth limits, and what's unknown until there's hardware.

**L1 · Perception (off-the-shelf, frozen, local, every frame).**
- Hand tracking (e.g. MediaPipe Hands).
- Fast per-frame embeddings (DINOv2-small and/or SigLIP).
- A motion-aware clip encoder: **V-JEPA 2** (Meta; HF `facebook/vjepa2-vitl-fpc64-256`, strong on egocentric action anticipation).
- Benchmark speed and quality on MPS and pick a per-frame backbone and a per-window backbone.
- **Point tracking: TAPNext++** (Google DeepMind, `google-deepmind/tapnet`). An online point tracker built for long videos and for re-detecting points after occlusion. Use it to:
  - follow the parts being worked on through hand occlusion
  - produce **region-of-interest crops** for the verifier, so fine calls like orientation get zoomed-in, high-resolution evidence and fewer tokens
  - give a motion-completion signal (tracked points on a placed part stop moving)
  - measure simple physical state (rotation, alignment)

  Check whether it runs on MPS at a usable speed; the published speeds are from datacenter hardware. If it's too slow or isn't PyTorch-ready, run it offline on the eval clips to show the value of crops (verifier accuracy with crops vs. without), and document the real-time plan.

**L2 · Event detector (ours, trained).**
- A small temporal head (1D conv or GRU) over the L1 features, predicting **action/step boundaries** ("something just finished, worth checking"). Labels come from the datasets' step timestamps.
- Task-agnostic: split by video and **hold out whole procedure types** at test time.
- Baseline: frame differencing / SSIM.
- Target ≥10 fps on this Mac.
- If training isn't working by the M3 deadline, fall back to the heuristic and say so in RESULTS.md.

**L3 · Procedure compiler (ours; uses the strongest Claude model offline, cached).**
- Instructions / recipe / manual text → a **typed task graph** with a schema. Each node has: id, novice and expert instructions, expected end-state description, verification checks phrased as typed questions, a common-mistake library, and successors.
- Also embed each expected end state with the SigLIP text encoder, so L4 can do zero-shot local matching.

**L3b · Task recognizer (ours).**
- From the first ~5–15 s, and continuously after that, identify which procedure is happening.
- Match against the task-graph library, using L1 clip embeddings plus a verifier check.
- If nothing matches (open set), have Claude name the task and draft a task graph from its own knowledge, flagged as a draft. Then confirm with the user by voice.
- Also handle joining mid-task: localize the current step without having seen the earlier ones.

**L4 · State tracker (ours; the core engine).**
- A probabilistic belief over task-graph nodes: an HMM / Bayesian filter whose transitions are constrained by the graph, with step-duration priors.
- It fuses cheap local evidence (frame-to-expected-state similarity from SigLIP, L2 boundary probability, elapsed time) with verifier verdicts, which count as high-weight observations.
- It outputs a step distribution and its entropy. High entropy triggers either the verifier or a view request.
- This is the file I'll walk interviewers through (`state_tracker.py`), so keep it clean.

**L5 · Verifier (rented today, swappable by design).**
- Typed interface: `verify(frames, node, checks) -> Verdict`, with a fixed schema `{step_status: in_progress|complete|deviation, confidence, mistake?: {type, description, correction}, visibility: ok|insufficient, view_request?}`.
- Implementations:
  - `ClaudeVerifier`: a fast model for routine checks (also the head-to-head comparison against Jev), and a stronger model for deviations, ambiguity, and open-set cases. Load the `claude-api` skill for current model ids, and make the model per role configurable.
  - `StatelessBaseline`: the same model, with no graph and no state.
  - `DistilledVerifier`: ours, see L7.
  - `JevVerifier`, **the primary fast verifier.** I have a TypeSafe AI subscription; ask me to set the key in the environment. Jev takes a `state` plus named `questions` at its `/v1/systemone` endpoint and returns typed answers with calibrated confidence (claimed 70–500 ms). Read the official docs at docs.typesafe.ai first.
    - Image input is reportedly **experimental** (Jev 1.14, behind header flags; see docs.typesafe.ai/go/images), so verify it actually works before relying on it.
    - Map our checks to Jev questions: is the step complete; which mistake from the node's mistake library, if any (a typed choice, so the correction text comes straight from the task graph); is the view sufficient.
    - Claude handles escalations: deviations Jev can't classify, free-form corrections for mistakes that aren't in the library, and task drafting.
    - If Jev's image input doesn't work, use Claude for vision, and use Jev for typed policy decisions over the structured state (speak now? which intervention?). Document what happened.
- **Calibrate confidence**: fit temperature/isotonic scaling on the train split and report expected calibration error (ECE) before and after. Calibrated confidence is what lets the policy be precise.

**L6 · Intervention policy + user model (ours).**
- Decides whether to say "verified," flag a mistake with a specific correction, ask for a different view, or stay quiet. Tune thresholds on the train split for precision, since false alarms are the thing that would make people hate this.
- Proactive coaching loop: announce the next step as soon as the current one is verified. Detect hesitation (idle hands, or time on the step well past the prior) and offer a more detailed hint.
- Early warnings: train L2 to also fire on grasp/pick-up events, and check the grasped part against the next step's expected part.
- Active perception: view requests aim at what's actually missing ("show me the left side of the bracket").
- Speak interventions with macOS `say` (live mode), and show them on screen as HUD cards.
- Personalization: a simple user model built from errors, hesitation (time on step versus the prior), and repeats. It picks novice or expert phrasing and adjusts how detailed instructions are. Demo it by running one clip with a novice profile and an expert profile, and label that render as a policy demo.

**L7 · Data flywheel + distillation (ours; the moat proof).**
- Every session writes a **training-ready dataset record** in a versioned schema: clip references, L1 features, point tracks, events, belief states, verifier questions and typed verdicts, policy actions, and outcomes or ground truth. A future in-house model can then train directly from logs with no re-processing.
- Experiment: train a small local **student** (MLP or attentive probe on frozen L1 features plus the node's text embedding) on teacher verdicts plus ground truth, to handle routine "is this step complete?" checks.
- Report student-vs-teacher agreement, student-vs-GT accuracy, latency (ms vs. s), and cost, on held-out videos.
- Whatever it shows, this is the slide that answers "isn't this just a wrapper?": the frontier model teaches our model, and our model gets the cheap, fast cases.

**Logging and rendering.**
- Every run writes timestamped JSONL: model id, prompt version, per-call latency, tokens, cost, belief state.
- The renderer draws the HUD onto the source video **only from that log** (OpenCV/Pillow + ffmpeg). It renders the two views described above. Keep the concept video's visual language (frosted light cards, green for verified, amber for mistakes), but follow the user-view rules for how restrained it is.
- Add a persistent badge: `Praxis prototype v0 · real model output · <dataset>`.
- Eval renders can optionally include a ground-truth strip (`GT: step 4 | Praxis: step 4`).

**Live mode.** Run the full engine on `WebcamSource` in real time, speak instructions with macOS `say`, and record the output.

`docs/MODEL_ROADMAP.md`: for each layer, what runs today (off-the-shelf, frontier, or ours), what in-house model replaces it later, what data that model needs, and how the flywheel collects that data. Example: the verifier moves from frontier/Jev to a distilled student to an in-house multimodal model fine-tuned on procedural sessions. This is the "the frontier model is a placeholder, the foundation is ours" story, so make it concrete, not aspirational.

`docs/ARCHITECTURE.md` gets a layer diagram that marks each layer as **ours / off-the-shelf / rented-and-swappable**, plus a short moat section explaining which layers compound over time: the task-graph library, the state tracker, the calibrated policy, the distilled models, and the procedural data.

## Data
Use public **egocentric procedural datasets that come with step and mistake annotations**, so the ground truth isn't something I labeled myself. Candidates to check (verify availability, size, and license before committing): CaptainCook4D, EgoPER, IndustReal, EPIC-Tent, HoloAssist, Assembly101. Prefer whatever downloads **this weekend without an approval process**. Skip Ego4D/Ego-Exo4D, since their license approval takes days. If a dataset needs a form, tell me and I'll fill it out myself.
- Assembly-style data (toy-vehicle assembly with labeled mistakes, e.g. Assembly101 / IndustReal) is the closest real match to the drone concept video, so prioritize it for showcase clips if access allows. Cooking datasets (CaptainCook4D, EgoPER) can cover breadth.
- Download only a subset: trimmed clips of roughly 1–5 minutes, chosen to include annotated mistakes.
- Target around 48 clips across up to 8 procedure types, if that falls out naturally. Report whatever the real counts end up being. Matching my application numbers is nice but not required. Being accurate is required.
- Record each dataset's license and citation in `docs/DATA.md`, and flag any non-commercial terms.
- Put raw video under `data/` and keep it out of git.

## Evaluation (the most important output)
Build `praxis eval` to compute, per clip and in aggregate:
- **Step tracking**: frame- or segment-level accuracy against ground truth, plus step-transition timing error.
- **Mistake detection**: event-level precision, recall, and F1 within a time tolerance, plus time-to-detect.
- **False alarms per minute**: the number users would actually feel.
- **Latency**: per-call and end-to-end p50/p95. The headline number is **feedback latency**: time from when an action actually ends (ground truth) to when Praxis says "verified" or flags a mistake. Also report fast-layer fps and the share of frames escalated to the reasoning layer.
- **Task recognition (L3b)**: top-1 accuracy and time-to-recognize on held-out clips, plus how accurately it localizes the current step when joining mid-task.
- **Jev vs. Claude (L5)**: on the same routine checks, compare accuracy, latency, calibration, and cost.
- **Point-tracking crops (L1)**: verifier accuracy on fine-grained checks with TAPNext++ crops vs. full frames.
- **Adaptive detail (L6)**: show on held-out clips that the time-on-step signal fires on steps where the ground truth shows the person struggling or making errors. Report this honestly as a correlation, not as proof that it helps users.
- **Event detector (L2)**: boundary-detection F1 on held-out videos and on held-out procedure types, versus the heuristic baseline.
- **State tracker (L4) ablation**: local evidence only, verifier only, and fused.
- **Calibration (L5)**: ECE and a reliability diagram, before and after calibration.
- **Distillation (L7)**: student-vs-teacher agreement, student accuracy against GT, latency, and cost per check.
- **Cost per minute of video.**
- **Key ablation, stateful vs. stateless**: run the same model frame-window by frame-window with no task graph and no persistent state. This baseline vs. the full engine is the central technical claim of the pitch. Measure it and report it whichever way it comes out.
- **Visual-uncertainty test**: artificially degrade a set of windows (crop away or occlude the key region, blur them). Measure how often the engine asks for a new view versus how often the baseline makes a confident wrong call.
- Per-category breakdown, plus a short qualitative failure analysis with example frames.

Budget: spend what the work needs, and use the fast layers to avoid wasting calls. Test on two clips first and report the projected total. Proceed without asking unless the projected total is over **$150**, and set a hard per-run cap in config so a bug can't loop calls.

## Deliverables (I'll build the deck and video from these)
- `prototype/`: the code, with a README containing exact commands to reproduce every result.
- `results/metrics.json` and `results/RESULTS.md`: setup, dataset and subset selection, models, all metrics including the baseline, failure analysis, and limitations.
- `results/figures/`: clean PNG charts (stateful vs. stateless, latency distribution, per-category results, calibration, student vs. teacher). Legible on a slide, white or transparent background.
- `renders/`: user-view and engineer-view versions; 3–5 showcase clips of 15–40 seconds (step tracking, a caught mistake with a correction, a view request), one honest failure clip, and the live-mode recording if that got done.
- `docs/ARCHITECTURE.md` with a diagram, plus `docs/MODEL_ROADMAP.md`, `docs/GLASSES.md`, and `docs/DATA.md`.
- `docs/CLAIMS.md`: a list of exact sentences I can safely say in the interview (e.g. "On N clips from <dataset>, the stateful engine cut false alarms per minute from X to Y versus a stateless baseline"), each linked to the file that backs it. Also a list of things I should **not** claim yet.

## How to work
- Initialize a git repo and commit at each milestone. Use Python with `uv`; ffmpeg is already installed.
- Milestones:
  - **M1**: dataset chosen, subset downloaded, L1 features extracted, task graphs compiled.
  - **M2**: one clip end to end through L0–L6 with the heuristic gate, with a render.
  - **M3**: L2 trained and swapped in, verifier calibrated, full eval plus baselines.
  - **M4**: L7 distillation experiment, figures, RESULTS.md, ARCHITECTURE.md, MODEL_ROADMAP.md, CLAIMS.md, showcase renders in both views.
  - **M5 (stretch, in priority order)**: live webcam mode; then the personalization render; then a simple local web viewer (video + synced belief/task graph + event log + metrics) I could screen-share; then the open-set task-drafting path.
- Training data can come from more of the dataset than the 48 eval clips. Download more if it's needed to train the fast layer, but keep the train/test split clean.
- If time gets tight, cut M5 before you cut M3/M4.
- Ask me to set `ANTHROPIC_API_KEY` and the TypeSafe/Jev key in the environment or a `.env`. Never print them or commit them.
- Keep the code clean enough that I can walk an interviewer through `state_tracker.py` and explain why it works.
- Each layer gets its own module and a typed interface, so a later layer swap (e.g. a distilled verifier replacing Claude) is a one-line config change.
