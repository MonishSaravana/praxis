# Praxis: how the whole system works (study guide)

Written 2026-10-20 for the S@H interview. Every number comes from `results/` or a cited source. Anything that hasn't
been measured is labeled as an estimate or a plan.

## 1. The 30-second version

A company uploads a manual. The **procedure compiler** turns each procedure into a structured **task graph**: steps,
order, typical time, what "done" looks like, what to check, and likely mistakes. A manager approves it.

The new tech wears glasses. Every frame goes through **open vision models** that turn video into numbers. **Our own
small models** read those numbers: an **event detector** notices "something just happened", and a **task
recognizer** works out which procedure it is. The core is our **state tracker**, a probabilistic model that always
holds a belief about which step you're on, for how long, and what comes next.

The system asks a question only when something happens, cheapest first: our **local student** answers, then a
**fast rented model** (Jev), and only the hard cases go to **Claude Opus 5.5**. A **calibrator** turns each answer
into an honest probability. A **policy** decides whether to say the next step, confirm a step, flag a mistake, stay
quiet, or ask for a better view. The **coach** says it out loud or shows it on the glasses. Everything is logged as
labeled training data, and with customer permission that data trains the next models.

**One line for the wrapper question:** "The frontier model is one swappable part that's asked a typed question
about 1 in 7 frames. The tracking, the compiled procedure, the decision of when to ask and when to speak, and the data
are ours."

## 2. The pipeline, stage by stage

| # | Stage | What it is | Output |
|---|---|---|---|
| 0 | Input | Camera frames at 4 per second (glasses → phone → engine). Tested on recorded first-person video replayed in real time | Frames + timestamps |
| 1 | Backend indexing | Parses the company's PDFs and finds the likely procedures. No model is involved; a 97-page manual takes 0.34 s on a laptop, for $0 | Searchable manual, candidate procedures |
| 2 | Procedure compiler | Claude Opus 5.5, run once per procedure, offline, with a strict JSON schema we wrote | A typed task graph (section 3) |
| 3 | Perception (open, frozen) | SigLIP 2 on each frame; V-JEPA 2 on each 2-second window; MediaPipe hand tracking | 768 numbers per frame, 1,024 per second, hand positions |
| 4 | Event detector (ours, trained) | Small causal convolutional network over time | Two scores per frame: "a step just ended", "a step just started" |
| 5 | Task recognizer (ours) | Linear classifier on frame features + text matching against procedure names + one quick "which task?" question | Probability of each procedure |
| 6 | Step models (ours, trained) | One linear classifier per procedure: frame → which step it looks like | Per-frame "looks like step k" evidence |
| 7 | State tracker (ours, the core) | Hidden semi-Markov model (Bayesian filter) over the task graph | Belief over steps, time on step, uncertainty, most likely step |
| 8 | Verifier (rented + ours) | Typed questions to local student → Jev → Claude Opus 5.5 | A typed verdict |
| 9 | Calibration (ours) | Rescales each model's confidence so "80%" really means 80% | An honest probability |
| 10 | Policy (ours) | Rules + thresholds tuned on training data, plus a simple novice/expert user model | One action: instruct, verified, mistake, view request, hint, done |
| 11 | Coach | Text-to-speech + heads-up cards (on glasses with a screen) | What the tech hears and sees |
| 12 | Records (ours) | Every frame's features, the belief each second, every question and answer, every action, outcomes | Training data, with the customer's permission |

## 3. The procedure compiler (is it a GPT wrapper?)

**How it works:**
1. The backend indexes the manual locally (no model).
2. One Claude Opus 5.5 call splits the chosen procedure into steps.
3. A second Claude Opus 5.5 call fills a **strict JSON schema** we designed. For each step it gives:
   - a novice instruction and a terse expert instruction
   - 2–4 substeps (used when someone is stuck), and the parts and tools
   - the **end state**: what the camera sees when the step is done
   - a **view hint**: where to look to verify it
   - 1–3 yes/no **visual checks** (completion, orientation, part identity, presence, alignment, quantity)
   - 1–4 **likely mistakes**, each with what it looks like, an early warning sign, and a specific spoken correction
   - which steps can come next, and a typical duration
4. We validate it into a typed task graph and add our own pieces:
   - SigLIP 2 text embeddings of each end state, so the system can match frames to steps with **no training video**
   - duration priors for the tracker
   - knowledge cards quoted from the manual, with page numbers
5. A manager reviews and approves it before any tech sees it.

**Cost:** about $0.16–0.26 per procedure, run once.

**What to say:** "It's not text back for a person to read. It compiles a typed program that our engine runs live.
The tracker follows its order and timings, the verifier asks its checks, and the policy speaks its instructions and
corrections. The schema, and how it drives the tracker, are ours. The model that fills it is swappable."

## 4. The models: what kind each one is

**Open, pretrained, frozen (we don't train these):**
- **SigLIP 2** (Google, `siglip2-base-patch16-224`).
  - What it is: a vision transformer trained on image–text pairs, so images and sentences land in the same number
    space.
  - Output: 768 numbers per frame, about 20 ms per frame on a laptop.
  - Why: it was the best backbone in our test. A simple classifier on it reached 44% held-out step accuracy, vs
    DINOv2 32% and V-JEPA 2 25%.
  - Its text side lets us compare a frame to the manual's "what done looks like", so a new procedure works from the
    manual alone.
  - License: Apache-2.0, so commercial use is fine.
- **V-JEPA 2** (Meta, ViT-L).
  - What it is: a video transformer that learns how things move by predicting the hidden parts of a clip.
  - Output: one 1,024-number vector per second, over the last 2 seconds.
  - Why: single frames can't see motion. It's weak at naming a step on its own, but it helps the detector and the
    student notice actions starting and stopping.
  - License: MIT, so commercial use is fine.
- **MediaPipe hands** (Google): hand position and motion. Apache-2.0.

**Ours, trained:**
- **Event detector.**
  - Architecture: a **causal dilated temporal convolutional network (TCN)**. Five residual blocks, dilations 1, 2,
    4, 8 and 16, hidden size 64.
  - It sees about the last 16 seconds and never looks ahead, so it works live.
  - **179k parameters.**
  - Inputs: frame features, video-window features and hand motion. Outputs: two heads, "a step ended" and "a step
    started".
  - Trained on the dataset's step-boundary labels from 24 recordings.
  - Its main job is deciding **when to ask a question**.
- **Step models:** one logistic-regression classifier per procedure. Trained on 3 recordings per procedure (9 in
  the learning-curve test).
- **Task recognizer:** a logistic-regression classifier + text match + a "which task?" question. Recognized the
  procedure on 73% of held-out clips, median 40 seconds.
- **State tracker: a hidden semi-Markov model (HSMM).**
  - Hidden state = (which step, how long you've been on it). It's filtered forward every second.
  - **Predict:** a step that has run about as long as it usually takes becomes likely to end (from a duration
    prior), and the next step must be allowed by the task graph (with a small chance of skipping, for robustness).
  - **Update:** it multiplies in the evidence: the step models' match on each frame (weak, every frame), the
    detector (when used), and verifier answers (strong, only at events).
  - **Read out:** probability of each step, uncertainty, most likely step, and expected time on step.
  - **Why it works:** each signal alone is weak. The graph says what can come next, the duration says when, and the
    verifier settles it when it matters.
  - It also handles late answers. A slow answer is applied at the moment its frames were taken, and the filter
    re-runs forward from there.
- **Local student (distilled checker).**
  - What it is: a small 2-layer neural net, **859k parameters**.
  - Input: the frame (SigLIP 2), the 2-second video window (V-JEPA 2), a text vector of "what step k done looks
    like", and their product. That's 3,328 numbers.
  - Output: "is step k done?"
  - Training: a mix of copying Claude Opus 5.5's answers and matching ground truth (50/50), on about 500–600 labeled
    checks from 30 recordings. It trains in about 7 seconds.
  - Results: 72% accurate vs. Claude Opus 5.5's 80%, and agrees with Claude Opus 5.5 69% of the time.
  - Speed and cost: 0.03 ms per check, free.
  - When its confidence is high it answers; otherwise the check goes up the chain. That removed 34% of frontier
    calls at the teacher's accuracy, and the full engine with it runs at $0.008 per video-minute with 52% step
    accuracy.
  - More data helps: 63% → 72% as training went from 4 to 30 recordings.
- **Calibration:** per-model rescaling fitted on training checks. Jev's calibration error went from 0.22 to 0.02.

**Rented, swappable in one config line:**
- **Jev 1.14 (TypeSafe AI),** the fast verifier. It answers typed questions with probabilities. Image input is
  experimental on their side.
- **Claude Opus 5.5,** the escalation tier.

## 5. When does it ask a question, and when does it escalate?

**Most frames never reach a model.** Only about 14% leave the local layers. The policy asks only when:
- the detector fires ("a step just ended" or "something was just grabbed"), or
- the belief becomes uncertain. Then a cheap "which of these steps?" question goes first. Or
- the tech has been on a step much longer than usual (about 1.6× its typical time).

There's at least 3 seconds between checks.

**The chain:** local student (if confident) → **Jev** (~0.15 s, ~$0.0001 per check) → **Claude Opus 5.5** (~3.8 s,
~$0.011 per check).

**It escalates to Claude Opus 5.5 when the fast answer:**
- says possible mistake or deviation, or
- says it can't see, or
- has a calibrated confidence between 30% and 70% (unsure).

In the evaluation, that was 351 of 3,030 calls (12%).

**How the fast verifier was chosen.** We tested on the same 469 labeled checks:

| Model | AUROC | Speed |
|---|---|---|
| Jev | 0.70 | 151 ms |
| Claude Haiku | 0.62 | |
| Claude Opus 5.5 | 0.84 | 3.8 s |

Inside the full engine, Jev gave 54% step accuracy vs. Haiku's 47%. So Jev is the fast tier, and Claude Opus 5.5 is
the referee.

**What escalation buys:** mostly fewer false alarms. With it, 4 of 17 mistake alerts were real; without it, 3 of 24.
Step accuracy barely changes (54% vs 53%), but cost rises from $0.001 to $0.018 per video-minute.

**What a verdict contains:**
- status: complete / in progress / deviation / not started
- confidence
- the mistake: its type, description and spoken correction
- visibility: can see / can't see
- the view request (e.g. "Look closely at the soldering station display, upper right")

## 6. What was measured (know these cold)

**Main benchmark.**
- Data: 48 held-out first-person clips from CaptainCook4D, a public procedure dataset (cooking). That's 235 minutes,
  8 procedures, 302 steps and 170 annotated mistakes. Train and test never overlap.
- Baseline: Claude Opus 5.5 asked every 5 seconds, no memory of the task, the task given.

| | Step tracking | Claude Opus 5.5 calls | Cost per video-minute |
|---|---|---|---|
| Praxis | 54% | 351 (plus 2,679 Jev calls) | $0.018 |
| Baseline | 48% | 2,817 | $0.085 |

  So Praxis makes 8× fewer frontier calls and is 5× cheaper. Lead with the relative numbers; give the raw ones if
  asked.
- With no model calls at all, our local layers alone reach 41%, or 49% after retraining on all the training data.

**Blurred or blocked views:**
- Praxis asked for a better view 77–98% of the time and was never confidently wrong.
- The baseline named the wrong step with confidence on 12–73% of the same checks.

**Mistakes (the weakest number; say it plainly):**
- 4 of 17 Praxis alerts named a real annotated error; the baseline managed 2 of 3.
- All 4 errors Praxis caught were order errors, the most common type (96 of 170). Those need step tracking more than
  vision.
- About 1 strict false alarm every 18 minutes.

**Learning curves:**
- Step models: 31% → 51% going from 1 to 9 recordings per procedure, still rising.
- Student: 63% → 72% going from 4 to 30 recordings.
- Say "steady gains each time the data doubles", never "exponential".

**Real repair footage (ENIGMA-51):**
- 66 moments: right step 45%, right or adjacent step 74%, vs. 36% and 45% for a general vision assistant given the
  same procedure.
- 11 of 15 technician questions answered correctly from the uploaded procedures.
- The live 16:40 session cost $0.17 in total. It confirmed 1 of 19 steps over the session and agreed with proxy step
  labels 29% of the time. The demo shows selected moments.

**Live speed:**
- The local layers take about 50 ms per frame on a laptop.
- Model calls run in the background, so the worst lag went from 4.4 s to 0.8 s.
- An answer still takes as long as the model, so a Claude Opus 5.5 escalation reaches the tech seconds later.

**Unseen procedures:** given the name of an unseen recipe, it drafted a plan in about 16 s. The draft covered 64% of
the steps and tracked 36% of the time, with no training video.

## 7. Training data: what we used, what we need, where we get it

**Used:**
- Public datasets only; we hand-labeled nothing.
- CaptainCook4D: Apache-2.0 data, MIT annotations, so commercial use is fine.
- The detector used 24 recordings; the step models 3 per procedure; the student about 500–600 checks from 30
  recordings.
- Why so little works: everything we train sits on top of large pretrained models, so our parts are small.

**Commercially usable datasets:** CaptainCook4D, IndustReal (assembly, Apache-2.0) and HoloAssist
(CDLA-Permissive). **Not usable commercially:** Assembly101 and EPIC-Tent (non-commercial licenses). **ENIGMA-51:**
check its license before training on it.

**What "good enough to deploy" means.** We earn trust in stages:
1. **Shadow mode:** silent, compared against the senior tech's sign-offs.
2. **Coach mode:** speaks next steps, flags mistakes only when highly confident.
3. **Full use,** once the measured numbers clear an agreed bar.

The bar is a proposal, not measured: the agreed step accuracy on their own procedures, fewer than about 1 false
alarm per hour, and no confident wrong calls on safety-critical steps. Safety-critical steps (like lockout) always
keep a human sign-off. Praxis prompts and records them but never approves them.

**What data we need:**
1. **Normal runs of each procedure** for the step models and timings. The learning curve was still climbing at 9
   runs, so plan for about 10. **Estimate, not measured:** ~10 procedures × ~10 runs × ~20 min ≈ 30 hours per
   site. The detector and student pool data across all sites, so each new site needs less.
2. **Mistakes, the hard part.** Real ones are rare, so:
   - staged mistakes: deliberately skip, reorder, or use the wrong setting (how the public datasets got theirs)
   - trade-school labs, where students naturally make many mistakes
   - the compiler's list of likely mistakes for each step
   - every alert a pilot confirms or rejects becomes a label

   The target is a few dozen examples of each common mistake type (an assumption).
3. **Hard conditions:** gloves, glare, occlusion and motion, recorded on site, plus synthetic blur and occlusion.
4. **Labels:** mostly cheap. Step boundaries come from our step-marking tool, routine checks are labeled by Claude
   Opus 5.5 automatically, and humans review only the mistakes.

**Where maintenance footage comes from, if not real jobs:**
- trade schools and community colleges (HVAC, industrial maintenance and electrical labs). The Fiber School is open
  to a test.
- union apprenticeship centers and equipment-maker training centers
- paid, consented contributors at about $25/hour (estimate): $2k buys about 80 hours
- the commercially licensed public datasets above
- later, pilot customers who **opt in by contract**

**Retraining plan:**
- We don't train foundation models from scratch; SigLIP 2 and V-JEPA 2 stay frozen.
- Shrink V-JEPA 2 into a small video model that runs on the glasses or phone.
- Retrain the detector, step models and student on maintenance footage.
- Learn one shared observation model for the tracker across procedures.
- Fine-tune a small open vision-language model on our logged verifier questions, so mistakes and fine checks stop
  needing a rented model.
- Fine-tune a smaller model for the compiler.

## 8. Economics and pricing

**Cost to serve:** $0.018 per video-minute ≈ **$1.08 per coached hour**. At ~2 coached hours a day for 6 months
(≈250 hours), that's **~$270 per new tech**. With the local model it's $0.008 per minute ≈ $0.48/hour ≈ **~$120**.

**Price (a hypothesis):**
- **One active-trainee license** = one employee being onboarded: $200 a month, unlimited sessions. That's **$1,200**
  over 6 months.
- Margin: **~77% today, ~90%** with the local model.
- Five techs onboarding at once = five licenses. When one finishes, the license moves to the next hire.
- **Glasses** are shared site equipment: 10 licenses with 3 people coached at the same time needs about 3 pairs. We
  don't resell hardware.
  - Ray-Ban Meta: $379–449
  - Ray-Ban Display: $799
  - Viture Helix: from $600
- **Path:** paid pilot → annual agreement → optional setup → later, team skill records.

**Buyer math:**
- A new tech carries a **$10–15k total hire-and-ramp burden** (Reliability magazine). That includes recruiting fees,
  which Praxis doesn't touch.
- Praxis pays for itself if it removes roughly **8–12%** of that burden.
- **50-tech team:** about 1 in 10 maintenance jobs opens each year (BLS: ~255k openings on ~2.47M jobs), so about 5
  hires a year. That's $50–75k of burden vs $6k of Praxis.
- The pilot measures the real effect: senior-tech hours, days until a new tech works alone, and rework.

**Evidence the ramp is long and costly:**
- **ARSA, 2017:** 35 aviation repair stations; 14 months to profitability for non-certificated techs, 9 for
  certificated, some 24.
- **Eptura:** the main hidden cost is senior staff supervising and double-checking new hires; ~25% productivity in
  month one, up to ~26 weeks to full performance.
- Generic corporate training spend (ATD, ~$846 per employee in 2025) isn't the right comparison. It leaves out the
  shadowing.

**Who the buyer is:**
- the maintenance manager at a plant (food, packaging, plastics)
- a facilities director (property managers, the largest employer of general maintenance workers; hotels; schools;
  towns; universities; hospitals)
- a service manager at an HVAC, elevator or equipment-service contractor

**Market:** ~255k new maintenance techs × $200 × ~6 months ≈ $306M a year at our pricing. Then all maintenance and
field service, then technical onboarding broadly. (~$1.8B and ~$9.2B are in the appendix, with assumptions.)

## 9. Hardware and platforms

- **AI glasses shipped:** 2.1M (2024) → 8.7M (2025) → 15M+ forecast for 2026 (Omdia).
- **Meta:** a developer preview opened outside apps to the glasses camera, and the toolkit reached 1.0 in Sept 2026
  (camera, microphones, speakers). Our phone app gets the frames; no code runs on the glasses. Public app-store
  publishing isn't open yet, but test builds are fine for a pilot.
- **Google:** first Android XR glasses this fall (audio, with a camera); display models later.
- **Viture Helix + NVIDIA:** safety glasses with real-time procedure coaching, from $600, Q1 2027. The closest
  competitor. We want to run on it too.
- **Adapter status:**
  - camera/upload path: tested
  - Meta adapter: built, not device-tested
  - Viture/NVIDIA adapter: built, not device-tested
  - Android XR: planned
  - Don't say "plug and play".

## 10. Likely questions, short answers

- **"Isn't this a ChatGPT wrapper?"** No. The frontier model is asked on about 1 in 7 frames, swappable in one line.
  The tracker, compiled procedures, policy, local models and data are ours. Same model inside our system: 8× fewer
  frontier calls, 5× cheaper, better tracking.
- **"What's the moat?"**
  - Consented, step-labeled data of skilled work, which nobody sells.
  - Models trained on it that get cheaper and better.
  - Each company's compiled procedures and records.
  - Later, skill records and certification partners.
- **"Why won't Meta or Google do it?"** They sell hardware and one general assistant. We run on their glasses; each
  new device is another adapter for us.
- **"How accurate is it?"** Tracking beats the frontier baseline at a fifth of the cost. Mistake detection is weak
  (4 of 17), and that's what maintenance data fixes. We deploy in shadow mode first.
- **"What if it's wrong on a safety step?"** It prompts and records those steps, never approves them. A person signs
  off. When it can't see, it asks instead of guessing.
- **"Privacy and unions?"** The customer owns the footage. Shared training needs a separate opt-in. The fast layers
  can run locally; only event keyframes go to a model. Coaching goes to the worker, aggregates to the employer. Face
  and badge blur is next.
- **"Why maintenance first?"**
  - a clear buyer
  - repeated procedures
  - senior knowledge is the bottleneck
  - the manuals already exist
  - hands-busy work, where glasses fit
  - long ramps
- **"Why not consumers?"** No budget owner, tasks don't repeat, and the platforms give consumer help away free.
- **"What does $10k buy?"**
  - $3k: retrain our models on maintenance footage
  - $2.5k: glasses and capture at a real site
  - $2k: about 80 hours of consented maintenance footage
  - $1.5k: about 1,400 coached hours of pilot inference
  - $1k: company formation and contracts

  By April: models retrained, running on real glasses at a real site, and a first paid pilot with an agreed metric.

## 11. What we haven't proven yet (say it before they do)

- Accuracy on real maintenance footage (the benchmark is cooking video).
- Glasses tested end to end on a device.
- How many senior-tech hours Praxis actually saves (that's the pilot).
- Mistake detection (4 of 17 alerts were real).
- Customers: none yet. Outreach started Oct 17. Casey Czarnowski (HSPA) and Sonny Hunt (The Fiber School) replied,
  and The Fiber School is open to a test.

**Patent:** if the provisional isn't filed yet, describe how the tracker decides when to ask and when to request a
view at the level above, not line by line.
