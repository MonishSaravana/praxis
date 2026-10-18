# Prompt: outside review of the Praxis architecture (for ChatGPT / Codex)

How to use it:
- **Codex (repo access):** open this repo as the project and paste everything below the line. It's a read-only
  review: no file edits, no API calls.
- **ChatGPT (no repo):** paste everything below the line and attach `docs/ARCHITECTURE.md`, `docs/MULTITASK.md`,
  `results/RESULTS.md` and `results/WHAT_DIDNT_WORK.md`.

---

You are reviewing the architecture of **Praxis**, a real-time AI coach for physical tasks. A person wears a camera,
Praxis works out which task they're doing and which step they're on, says the next instruction, and catches
mistakes. Find what we're overlooking: flaws in the method or the evaluation, strategies we haven't tried, and better
architectures. Be blunt and concrete. I want ideas I can test cheaply, not a literature survey.

## Constraints (these are fixed)

- **Real time** on a laptop (Apple M4, 24 GB) or later on glasses: the per-frame path has to run in milliseconds. Big
  model calls (~0.2–4 s) can only happen at events.
- **Low cost:** today $0.018 per video-minute. The goal is to stay near that. A frontier model every few seconds is
  ~$0.085/min.
- **Product rules:** auto-recognize the task, coach proactively, voice-first, unobtrusive. The step graph is never
  shown to the user.
- **Honesty:** every claimed number comes from a measured run. Design choices and thresholds are chosen on the
  dataset's **train split only**; the 48 eval clips are for the final measurement. Don't propose tuning on the eval
  clips.
- **Wedge:** new maintenance and repair technicians. The current data is cooking video, because that's what has
  labels.

## Architecture (see `docs/ARCHITECTURE.md`)

Layered. Only the L5 verifier is a rented frontier model, and it runs only at events.

| Layer | What it is | Trained by us? |
|---|---|---|
| L1 perception | Frozen SigLIP2 (per frame), V-JEPA 2 (2 s windows), MediaPipe hands; 4 fps | No (off-the-shelf, frozen) |
| L2 event detector | Small causal TCN over L1 features → P(step boundary) | Yes, train split |
| L3 compiler | Claude turns a recipe/manual into a typed task graph (steps, end states, checks, mistakes, order) | No (prompted) |
| L3b task recognizer | Linear probe over L1 features + a typed Jev "which task?" question | Probe yes; Jev prompted |
| L4 state tracker | Explicit-duration HMM (HSMM) over the graph: duration priors, graph-constrained transitions; fuses per-frame step-probe likelihoods, boundaries and verifier verdicts | Step probes + duration priors yes |
| L5 verifier | Typed questions: "is step X done?", "which of these steps?", "which task?". Fast tier Jev 1.14 (~0.2 s); strong tier Claude Opus 5.5 (~3.6 s) for ambiguity, possible mistakes and poor views | No (prompted); outputs calibrated on train |
| L6 policy | When to verify, speak, flag a mistake, ask for a better view, expand detail; precision-first calibrated thresholds | Thresholds yes, train split |
| Multi-task (new, `docs/MULTITASK.md`) | Task set (active / paused / done enough); an "away" belief from zero-shot landmark matching (SigLIP2 frame vs each recipe's ingredient/tool text); re-asks "which task?" on poor fit; switch / resume / interruption logic | Off-task model yes, train split |

So it's prompting plus routing, with small trained "glue" models that run every frame for free, keep track between
big-model calls, and decide when a big call is worth it.

## Data

CaptainCook4D egocentric cooking. 8 recipes in the library, plus 1 assembly task. 48 held-out eval clips (234.9 min,
first 5 min of each recording). Train split: 71 recordings, but **only 24 (264 of 705 min, ~3 per recipe) had
features**, so every trained piece learned from ~3 videos per recipe. We're now extracting the rest. 4 more recipe
types are held out for open-set tests.

## Measured results (eval split unless marked)

- **Task given, step accuracy** (at every 0.5 s inside an annotated step, is the predicted step exactly right):
  - Praxis 54%;
  - stateless Opus every 5 s with the step list 48%;
  - local evidence only 41%;
  - verifier only every 5 s 36%.
- **Automatic** (Praxis must recognize the task):
  - task top-1 73%, median 40 s to recognize;
  - step accuracy 30% (37% after recognition);
  - **13 of 48 clips score 0%** because the wrong recipe (or none) was committed. With the recipe given, those same
    clips score 30–93%.
- **Mistakes** (task given):
  - time-window scoring: 13 of 170 annotated errors caught, 4 false alarms;
  - strict, judged by a model: precision 24%, recall 2.4%.
- **"Is this step done?" checks** (100 labeled train checks, temporal-span framing):

  | Model | Accuracy | AUROC | Latency | Cost / check |
  |---|---|---|---|---|
  | Jev | 58% | 0.67 | 152 ms | $0.00011 |
  | Claude Haiku 5.5 | 55% | 0.59 | — | — |
  | Claude Sonnet 5.5 | 71% | 0.73 | 1.9 s | $0.0037 |
  | Claude Opus 5.5 | 82% | 0.86 | 3.6 s | $0.0096 |

  On 469 held-out checks, AUROC was Haiku 0.62, Jev 0.70, Opus 0.84.
- **Fast-tier swaps** (task given):
  - Jev without escalation 53%;
  - Haiku fast tier + Opus 47%;
  - distilled student + Jev localization + Opus 52%.
- **Cost:** Opus escalations are most of the spend, though most calls are Jev.
- **Latency:**
  - verifier call p50 192 ms;
  - feedback after a step ends, p50 4.7 s / p95 139 s (long tail from a "stuck" belief).
- **Multi-task (train split, Jev only, SYNTHETIC splices of recordings), chosen config vs today's single-task
  engine:**
  - single-task recordings: step accuracy 46.5% vs 43.3%, final task correct 96% vs 83%, zero wrong switches;
  - splices: step accuracy 39.1% vs 30.5%;
  - switches: 16 of 24 caught, median latency 73 s, 3 wrong;
  - resume: the paused task came back 5 of 10 times, but at the exact step only once.
- **Landmark signal (train):** zero-shot "objects in view" names the right recipe in 60% of 30-s windows (chance
  12.5%). As an on-task vs off-task score: AUC 0.87 (20 s window).

## Known problems, in plain words

1. Steps look alike, the head camera is blurry, people do steps out of order or in parallel, and the annotated step
   boundaries are fuzzy. So the frame-level step score is low for every system.
2. One wrong recipe guess at the start zeroes that clip. Confusions are between similar recipes (burritos vs
   pinwheels vs omelet).
3. The "which task?" decision has only ever been asked to Jev, the weakest model, and it drives recognition and
   switching.
4. Switch detection is slow (~70 s): the cheap landmark signal is weak, and the expensive check only runs when the
   cheap one fires.
5. Small trained models learned from ~3 videos per recipe.
6. The completion verifier is unreliable at single moments (AUROC 0.67–0.86), so the tracker leans on priors and
   local evidence.

Already tried (see `results/WHAT_DIDNT_WORK.md`): zero-shot title matching for recognition (locked onto wrong
recipes), three recent frames as evidence (replaced by sharpness-picked temporal span), point-tracked crops (didn't
help enough), time-on-step as an error predictor (doesn't predict errors here), small models as completion judges
(weak).

## What I want from you

1. **The 5–10 changes most likely to raise accuracy**, ranked by expected gain per dollar and per day of work. For
   each one:
   - what to change, and the mechanism (why it should help here);
   - what evidence makes you think so, with sources only if you're sure (say "speculative" otherwise);
   - cost: extra $/video-min, latency, engineering days;
   - the cheapest test on the **train split**, and the metric that would show it worked.
2. **Flaws in our method or evaluation** that would make an expert distrust the numbers, or make us optimize the wrong
   thing. For example: frame-level exact-step accuracy vs segment-level or edit metrics, boundary tolerance, the
   5-minute clips, the train-only selection protocol, the synthetic splices.
3. **Model choices:** where in the stack a different model would beat what we use, at what cost and latency. Cover
   OpenAI GPT models with vision, open models (e.g. Qwen-VL, InternVL) and on-device options. Be specific about
   which question (completion / which step / which task / mistakes) each would answer, and how to test it against
   Jev and Opus on our labeled checks. Don't assume a newer model is better: say what you'd measure.
4. **Training data:**
   - which public egocentric procedural datasets (with step labels, ideally with errors) would help, how, and how
     much work to use them;
   - how to bootstrap for technician tasks where there are no labels yet.
5. **Architecture alternatives** worth a prototype: temporal action segmentation models, streaming video-LLMs with
   memory, fine-tuning a video encoder, better HSMM observation models, anything else. Say what each would replace,
   and whether it fits the real-time and cost constraints.
6. **What not to do:** ideas that sound good but are likely traps here.

Format: a ranked table first (change, expected gain, cost, risk, cheapest test), then short sections for 2–6. Don't
invent numbers about our system. If something depends on a number you don't have, say what to measure.
