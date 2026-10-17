# Model roadmap: the frontier model is a placeholder, the foundation is ours

For each layer: what runs today, what in-house model replaces it, what data that model needs, and how the
flywheel (L7 session records, `praxis.record/1`) already collects that data. "Measured" items point to
files under `results/`. Anything not measured is labeled as a plan.

| Layer | Today (v0) | Next in-house model | Data it needs | How the flywheel collects it |
|---|---|---|---|---|
| L0 input | File; recorded video replayed in real time through the live loop (tested, `results/live/`); webcam (same loop, not run in this build); glasses stub | Glasses adapter (Meta DAT phone app → engine) | none (systems work) | Session records already store capture timestamps, so per-device latency shows up in the data |
| L1 perception | Frozen SigLIP2, DINOv2-small, V-JEPA 2 ViT-L, MediaPipe hands; TAPNext++ point tracking runs **offline only** (well below real time on the M4; see `results/l1/tapnext_speed.json`) | Same backbones, then a smaller procedural backbone distilled from them (V-JEPA 2 → ViT-S video student) for phone/glasses compute. For point tracking: fewer query points plus an ANE/CoreML export, or server-side tracking on keyframe bursts | Raw first-person video of procedures | Every session stores clip refs + L1 features (`features.path`) |
| L2 event detector | **Ours, trained** causal TCN on frozen features (boundary + onset heads) | Same head on more procedures, plus hand-object contact and grasp labels | Step boundaries and grasp moments | Verified steps (`commit` events) and verifier `complete` verdicts are free boundary labels in every session |
| L3 compiler | Frontier model offline (Claude Opus 5.5 by default; the current 9 graphs were compiled with Fable 5.1), output cached as typed JSON | Fine-tuned smaller model for graph compilation, then graphs learned from executions (re-ordered steps, real durations, mistakes people actually make) | (instruction text → graph) pairs; real executions per graph | The library *is* that dataset; records hold per-step durations, mistakes and orders |
| L3b recognizer | **Ours**: linear probe over frozen features + zero-shot text match | Open-vocabulary procedural recognizer over the growing library (contrastive video ↔ graph embedding) | Labeled starts of many procedures | Every session's recognized task + user confirmation is a label |
| L4 state tracker | **Ours**: HSMM, hand-set temperatures, train-split duration priors, per-procedure step probes | Learned observation model shared across procedures (step-end-state matching conditioned on graph text), learned durations per user | (frame, node, in-progress/complete) tuples | Timeline records: belief + GT/verified step at 1 Hz |
| L5 verifier | **Rented**: Jev typed questions as the fast tier (completion checks, "which step?", "which task?"); Claude Opus for escalations. Claude Haiku in the fast slot was measured and was less accurate (`results/runs/fused_claude_fast.json`) | (1) **Distilled student** (ours, measured in `results/l7/`) for routine "is step complete?" checks → (2) in-house multimodal verifier fine-tuned on procedural sessions for mistakes and fine checks → frontier model only for open-set | Typed (frames, node, question) → verdict, with outcomes | Every verifier call is logged with frames refs, typed question, verdict, calibrated score and later outcome/GT |
| Calibration | **Ours**: isotonic/temperature per verifier (`results/l5/`) | Per-procedure / per-check-type calibration | Verdicts + outcomes | Same records |
| L6 policy | **Ours**: thresholds tuned on train split for precision, rule-based user model | Learned intervention policy (when to speak) optimizing task success and false-alarm rate per user | Interventions + what happened next (corrected? ignored? repeated step?) | Actions + following timeline in each record |
| TTS / voice | macOS `say` | On-device TTS, user-specific phrasing | none | none |

## Replacement path for the verifier
1. **Now.** Routine checks, step localization and task checks go to the fast tier: Jev typed questions,
   ~0.15 s each (`results/l5/`). Ambiguous checks, possible mistakes and poor views escalate to Claude Opus.
2. **Step 1, shown this weekend.** A local student learns routine "is step k complete?" checks from teacher
   verdicts plus ground truth, on frozen L1 features plus the node's end-state text embedding.
   - Its agreement with the teacher, accuracy against GT, latency and cost are in `results/l7/distill.json`.
   - Policy: route a check to the student when its calibrated confidence is high, and call the frontier
     model only otherwise.
3. **Step 2.** Fine-tune an open multimodal model (a small VLM) on the accumulated typed verifier calls, so
   mistakes and fine checks run in-house. The data is the L7 records.
4. **Step 3.** The frontier model is kept for open-set procedures and rare escalations. Open-set drafting already
   works in a first form (`praxis/tasks/drafter.py`, measured in `results/open_set/`): a draft graph from what the
   camera has seen, tracked zero-shot until the full compiler or real executions refine it.

## Live loop: next systems step
The live loop runs the slow path (verifier calls) inline, so a frontier-model escalation stalls the fast path for a
few seconds (`results/live/`). Next: run verification on its own thread and fold each verdict into the tracker at
the time its frames were taken, so local layers never wait on the network.

## Why the data is training-ready
`praxis.record/1` (see `prototype/praxis/flywheel/records.py`) stores, per session:
- feature references at fixed rates (4 fps frames; one V-JEPA 2 embedding per second over the trailing 2 s);
- the 1 Hz belief timeline;
- every typed question with its typed answer and calibrated probability;
- policy actions;
- outcomes / GT.

No re-decoding or re-labeling is needed to train any of the next models above. One honest caveat: v0
records come from public datasets, not real users, so the "user model" data does not exist yet.
