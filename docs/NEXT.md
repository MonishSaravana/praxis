# What to work on next

Status: ideas list, 2026-10-17. **Nothing here is built.** These are the founder's four ideas plus privacy (item 5), checked against what
the code and docs say today. Sizes are my rough guesses, not measurements. Nothing here needs to be built before
the 2026-10-20 interview.

Rules every item has to follow (from the product principles):
- Unobtrusive, voice-first UI. The step graph is never shown to the wearer. Cards only for mistakes and view requests.
- Real-time first. Slow model calls stay off the live path.
- Claims only if backed by actual runs. All results so far are on cooking (CaptainCook4D) and assembly
  (IndustReal) footage. Nothing is measured on factory or maintenance footage.
- Spend gate: an itemized cost estimate and a yes (or a hard cap) before any paid run.

## At a glance

| # | Idea | What the repo already has | What's missing | Size | Biggest risk |
|---|---|---|---|---|---|
| 1 | Voice both ways | Speaks: browser speech in Studio, macOS `say` in `live.py`. The policy decides when to speak | Listening, better voices, barge-in, "why?" answers | S–M | Loud workplaces; hearing protection |
| 2 | Generated visuals on screen | Code-drawn HUD (`render/hud.py`, `studio/static/hud.js`). Per-step `end_state` and `view_hint` text | Any picture of an end state; a safe way to show model-made SVG | M–L | A wrong diagram on a maintenance task |
| 3 | Personal profile and memory | In-session `UserModel` (skill, repeats, mistakes) that resets every session | Accounts, a profile picker, memory that persists, the privacy rules | M | Workers distrust it if the employer sees everything |
| 4 | Knowledge portal and locked procedures | Studio compiles pasted text to a typed task graph (`studio/tasks.py`, `tasks/compiler.py`). `drafter.py` drafts a plan from video | File/video upload, admin review of the graph, org libraries, a "locked" mode | M–L | A wrong compiled graph means wrong coaching |
| 5 | Privacy: where the video and documents go | Fast layers run locally. Only event-triggered keyframes and crops leave (12.9% of frames in the eval). Studio keeps nothing unless you press Save | Face and badge blur, vendor terms, customer-cloud and local-model tiers, a written data policy | S–M (blur); L (local tier) | Enterprise buyers may refuse cloud video |

## 1. Voice, both ways ("it speaks out")

**Status (2026-10-17).** Voice input is **confirmed for the final product and deliberately not built before the
2026-10-20 interview**, to save time. Describe it as designed and not yet built (`VOICE.md`, Appendix C).

**Today.** Praxis speaks, but with stock voices. Studio uses the browser's speech synthesis; `live.py` shells out to
macOS `say`. An urgent line (a mistake, a view request) cancels the queue. It does not listen yet
(`POSITIONING.md`, "Voice and screen"). `VOICE.md` section 1 audits it from the run logs: the task announcement and
the first instruction start at the same moment (so they talk over each other), the default instruction is long
(about 5 s), and the "more detail" hint speaks one short sentence.

**Next steps.**
- **Better output voice.** A neural voice instead of the stock one. Options: a local model ($0, offline), or the
  OpenAI TTS credits you already have. Measure time to first audio before picking. Speak sentence by sentence so
  audio starts early.
- **Barge-in.** Stop talking when the wearer speaks or the step changes.
- **Voice input, in natural language.** Speech-to-text (Apple on-device or local Whisper, $0), then a language model reads
  what the person said together with the task: "skip that part", "I don't want the tomatoes", "no, I'm still on the
  belt" (never step numbers), "why?", "use the other knife". A short list of common commands ("done", "next", "repeat")
  has a fast path so it answers instantly, but it is a shortcut, not a limit. Each utterance enters the state tracker as
  capped evidence, and a correction is also a free human-confirmed training label. Cost is pennies per session even if
  every utterance goes to a model. Changing the plan by voice ("no tomatoes") needs a new capability: editing the task
  graph during a session. The full design is `VOICE.md` section 2.
- **"Why?" and "show me" answers.** One Claude call with the current step as context. For a locked procedure
  (item 4), answers come from the uploaded documents and cite them.
- **Trigger (recommended default).** Push-to-talk, plus a short listening window (about 7 s) right after Praxis asks a
  question. No wake word, and no always-on microphone as the default: false accepts are unmeasured ("done", "next" and
  "okay" are common in shop talk), an always-on microphone raises workplace-consent and privacy questions that push-to-talk
  mostly avoids, and on Meta glasses an open microphone lowers the speaker quality for the whole session.
- **Hands-free mode (idea: AirPods with the microphone always on, Praxis filtering for speech meant for it).** A good
  *opt-in* for quiet places, since not everyone will own a boom-mic headset, but not the default. It runs on the phone: a
  score for "was that for me" from the voice, the recognizer's confidence, whether the words fit the current step, the
  listening window, and an optional "Praxis, ..." name. Never speaker identification (voiceprints count as biometric
  data in some states). Before it can be offered, show: a low rate of stray commands in a recorded test of shop chatter and
  radio; written consent and legal sign-off at the site; a full-shift battery test (AirPods Pro 2 are rated about 4.5 h of
  talk time); and that Meta's camera stream keeps running with AirPods as the audio device (undocumented). AirPods Pro's
  "Hearing Protection" is not something to rely on at work: Apple frames it for sports and fitness classes, gives no
  attenuation figure, and OSHA makes the employer evaluate protectors for the specific noise. In loud plants the
  protection headset stays the answer.
- **How much a misheard "done" can hurt.** I ran the real tracker (`VOICE.md` section 6.5.2). My first draft gave spoken
  claims so much weight that one utterance would have advanced the step and switched off the engine's own self-check, so
  the weight is now capped: a single utterance bends the belief but cannot advance a step the engine is confident
  about, and each accepted claim triggers a fast camera check (median 144 ms, about $0.0001). A tap on the glasses is **not** an option on camera-only Meta
  glasses (the docs treat a tap as pause/resume for the session, and give apps no tap event). On the Meta Ray-Ban Display
  a tap on a button on the card does reach the app, so a "Talk" button works there.

**Recommended setup (from `VOICE.md` section 6; nothing here is tested on hardware).**
- **Quiet bench or training lab.** A tablet or phone with earbuds, a full screen, and an on-screen talk button. The
  easiest place to run the first voice tests.
- **Loud plant (85 dBA and up, hearing protection worn).** Put audio and the microphone on the technician's own
  Bluetooth protection headset (a Peltor-class headset with a boom mic and a push-to-talk button on the earcup), and use
  the glasses for the camera only. Open-ear glasses speakers are likely inaudible there. The card is the main channel
  and voice repeats it. Lines stay under about eight words, and safety-critical steps get a card plus a spoken
  confirmation. No microphone accuracy at these noise levels has been measured by us, and the vendors' own claims
  (RealWear says 100 dBA) have no independent test that I found.
- **How the glasses and the headset connect.** They don't, directly. The phone is the hub: the glasses send camera frames to
  an iPhone app over Meta's toolkit, and the phone talks to the headset over ordinary Bluetooth audio. Nothing runs on the
  glasses. The one unknown is whether camera streaming keeps working while the phone's audio goes to a separate
  headset (`VOICE.md` section 6.6).
- **By device.** Meta camera glasses: camera only, headset for audio. Meta Ray-Ban Display: same, with the card and a
  "Talk" button. Android XR glasses: built-in speech recognizer, with the camera button or touchpad as the trigger
  (preview API). RealWear: its own microphones and voice commands.
- **First hardware tests** (all pass/fail): does camera streaming keep working while the phone's audio goes to a
  separate headset; does a headset button reach the app while its microphone is on; does a tap on the Display card
  start listening; do Neural Band gestures reach an app at all.

**Risks to check before promising anything.**
- Maintenance and factory floors are loud, and workers often wear ear defenders. OSHA's action level is 85 dBA over
  8 hours, and typical plant levels run from the mid-80s into the 90s and above. Open-ear glasses speakers may be
  inaudible there. The voice-first assumption needs a test in the wedge environment, with a fallback (screen card,
  vibration on the phone, or audio through the technician's protection headset as above).
- On Meta glasses, the documented microphone mode (8 kHz) degrades speaker audio for as long as it's on, and it has to
  be on before the camera stream starts, so it is on for the whole session (`GLASSES.md`, `VOICE.md` section 4).
  Unknown until tested on hardware.
- Speculative, low priority: maintenance work has sound cues (a connector clicking in, a bearing grinding). Audio
  could become one more piece of evidence for the verifier. Nobody has measured this.

## 2. Dynamic UI: pictures generated on the spot

**Idea.** Claude draws an SVG (an end-state sketch, a part callout, a bolt-tightening order, a tiny animation) and
the screen shows it when the wearer is stuck or asks "show me".

**Two timings, and the split matters.**
- **Precomputed, at compile time.** The compiler already writes an `end_state` and a `view_hint` for every step.
  Add a `visual` per step. It's generated once, an admin can review it in the portal (item 4), and it costs nothing
  at runtime. This is the one to build first.
- **On demand.** The wearer asks "show me" or the policy sees a long hesitation. Speak first, and let the picture
  arrive a few seconds later. It's off the live path and cached by (task, step, question). Latency and cost are
  unmeasured, so measure before committing to it.

**Where it shows.** Studio and a phone now. On glasses only the Meta Ray-Ban Display has a screen (600×600, one
eye, documented but untested by us). On voice-only glasses it shows on the phone. Per the UI rules it never
appears on its own, only for a hesitation, a mistake, or a request.

**Risks.**
- A wrong diagram is worse than none. A bolt order or a wiring sketch that is subtly wrong is a safety problem in
  maintenance. My expectation, not a measurement: generated sketches are fine for schematic things and unreliable for
  a specific real machine.
- Proposed rule: for locked procedures, show **figures taken from the uploaded manual itself**, not generated
  ones. Generated visuals are labeled "illustrative" and never used for torque values, wiring, or lockout steps
  unless the source document supplies them.
- The SVG comes from a model, so treat it as untrusted. Strip scripts and render it as an image in a sandbox, never
  as inline markup in the page.
- Small aside from the existing docs: the strong evidence that showing beats telling (an 82% drop in assembly errors)
  came from overlays pinned to the real parts. A corner card is not that, so the honest claim is "we use a screen
  when there is one" (`POSITIONING.md`).

## 3. Personal profile and memory

**Today.** `policy/user_model.py` tracks one number (skill, 0 to 1) from time-on-step versus the typical time,
plus mistakes and repeats. It picks novice, standard or expert phrasing. It starts fresh every session, and it
isn't tied to a person.

**Next steps.**
- **Accounts and a persistent profile.** Skill per domain or task type, not one scalar. Which steps this person
  keeps getting wrong. Tasks completed. Preferred speaking speed, verbosity and language. For consumers, the tools
  and equipment they own.
- **Memory.** Structured facts plus session summaries that Claude can write. The wearer can see, edit and delete
  all of it.
- **Choosing a profile when the glasses go on.** Shared glasses on a shift are common, so it has to take seconds.
  Options: a picker on the phone, scanning a badge QR code, or saying your name and confirming on the phone.
  Recommendation: not face recognition.
- **Cold start.** Keep the automatic adaptation we have. A new profile starts at "standard" and adjusts.
- **Link to the flywheel.** Corrections and outcomes already go into the training-ready records (`praxis.record/1`).
  The profile is a per-person view of the same data.

**The trust question comes first.** If the employer can see every mistake a worker made, workers will probably resist or
game the tool (my expectation, not measured). `ARCHITECTURE.md` already notes that people abandon coaching tools
over false alarms, so trust is a known adoption risk. Proposed default: the memory belongs to the worker, and the employer sees aggregates (step-level
completion and time, not named mistakes) unless the worker shares more. Employee-monitoring and biometric rules
vary by place; check them before any pilot rather than assuming.

## 4. Knowledge portal and locked procedures

**Status (2026-10-17, evening): first version built in Studio, see `BACKEND.md`.** Ran: company profiles, upload
and local ingest of three public maintenance manuals (97–222 pages, under 2 s each), procedure finding, compiling one
FIST 4-1A procedure ($0.164) and a recipe card ($0.188) from their sections only, review/approve/lock in the admin
page, a locked live run on a test clip, and three Claude answers with page citations. On a locked re-run, steps committed and
instructions advanced through 12 of 17 steps (with some back-and-forth; GPU shared with other jobs). On ENIGMA-51 repair footage (a hyper-specific procedure),
the general model answered 0 of 4 procedure questions and Praxis 4 of 4; live tracking of the document-only procedure was
weak (proxy 0.29). Marking steps on one reference recording took a company procedure from 0.20 to 0.40 step accuracy
offline (cooking clips); not yet tested on maintenance footage.

**Why this matters most for the wedge.** Claude is general. It does not know a specific plant's machines,
torque specs or safety steps. A maintenance org's own procedures are exactly what turns "a model with a camera"
into a coach for their work, and they accumulate per organization (the task-graph library moat in `ARCHITECTURE.md`).

**What exists.** Studio's compile flow: paste instructions, Opus 5.5 splits and compiles them into a typed task
graph (steps, end states, checks, mistakes, duration priors), cached by text hash under `sessions/library/`
(gitignored). `drafter.py` can draft a plan from a few seconds of video plus a hint. Studio's compile box takes
pasted text only.

**Portal, next steps.**
- **More inputs.** PDF, Word, slides, images and diagrams. Then video: sample frames plus a transcript of the
  narration, through the compiler.
- **Admin review before publishing.** The compiled graph is internal for wearers, but the manager should be able to
  see and edit it: steps, checks, known mistakes, and a flag for safety-critical steps. A wrong graph means wrong
  coaching, so a human signs off. Add a round-trip check (re-read the document against the graph and flag any step
  the document doesn't support); the compiler prompt already says never to invent steps.
- **Org libraries and versions.** Per-organization namespaces with logins. When an SOP is revised, the version a
  worker followed stays on record.
- **Grounded answers.** Retrieval over the org's own documents for "why?" questions, with a citation to the step or
  page.

**Two modes.**
- **Open coach (today).** Recognizes any task from the library, drafts a plan for unseen ones, and adapts detail.
- **Locked procedure.** The library is the one or few tasks the org assigned. Praxis only detects that task and
  guides the wearer through it. It does **not** revise, shortcut or suggest another method. It tracks, confirms,
  and flags deviations from the document (wrong order, missing step, wrong part) with the step cited, and stays
  silent otherwise.
  - Closed-set recognition is an easier problem than open-set (skip the recognizer's guessing and the drafter),
    but nothing is measured yet, so no accuracy claim until it's run on real footage.
  - It still needs the "away" state from `MULTITASK.md` (3.1 to 3.4, designed, not built): a worker who walks off
    to fetch a tool or takes a call must pause the task, not trigger false mistakes.
  - Natural extension: a manager assigns today's tasks to a worker profile (item 3), and the worker hears
    "Today: replace the filter on line 3" when they put the glasses on.
  - A signed-off step log is a likely ask. Whether it stores frames is a privacy decision (item 3), so decide that
    before offering it.

## 5. Privacy: where the video and documents go

Added later the same day, when the founder asked whether sending customer data to frontier models is a problem.
**It is a real concern, and today's docs don't mention privacy at all.**

**What leaves the machine today (from the code).**
- **Live path.** The local layers (SigLIP2, V-JEPA 2, MediaPipe hands, the event detector, the state tracker) run
  on our own machine, with model-hub access forced offline (`prototype/README.md`). Only the slow path sends anything.
- **What the slow path sends.** When something happens (a step boundary, high uncertainty, a long hesitation), the
  engine sends a few JPEG keyframes (long side at most 640 px) and zoomed crops (512 px) to the verifier API:
  Claude (Anthropic) or Jev (TypeSafe, `api.typesafe.ai`, where image input is flagged experimental). In the
  48-clip eval, 12.9% of frames went to the slow path (`results/RESULTS.md`).
- **Documents and video for setup.** The compiler sends uploaded procedure text to Claude Opus once per document.
  The drafter sends a few seconds of frames plus the person's words.
- **What is kept.** Studio keeps nothing unless the person presses Save (it lives in `sessions/.pending/` until
  then). The training records hold features, beliefs and verdicts rather than raw video (per `ARCHITECTURE.md`; I
  haven't checked the code for stray frames).
- **What is not built.** Nothing is anonymized or blurred today.

**Why it matters for the wedge.** First-person video of maintenance work can show coworkers' faces, badges, screens
and whiteboards, a customer's property, and the process itself, which may be a trade secret. Some sites may refuse
cloud transfer outright (my guesses, not researched: defense and export-controlled work, hospitals with patients in
view). Enterprise buyers and investors will probably ask "where does the video go?" early.

**Can it be anonymized? Partly.**
- **People (faces, badges, name tags, screens): yes.** Blur them on the device before anything is uploaded.
  MediaPipe is already in the stack for hands, and a face detector from the same library would be a small addition.
  Verifying a step rarely needs a face, so the accuracy cost should be small. That is unmeasured, and the dataset
  clips probably contain few faces, so a real test needs new footage (Studio sessions could supply it).
- **The work itself (the machine, the part, the process): no.** That is exactly what the verifier has to look at.
  Blurring it defeats the purpose. So anonymization protects bystanders, not confidentiality. Confidentiality
  needs the options below.

**Options, cheapest first. They stack.**
1. **Send less.** Already event-triggered. Push further: crops instead of full frames when the check allows it,
   lower resolution, no audio, and delete after the verdict.
2. **Blur people on-device** before upload (above).
3. **Vendor terms.** Use enterprise API terms with no training on the data and minimal or zero retention. I haven't
   verified either vendor's current retention terms. Read them. Jev is a small vendor and its image input is
   experimental, so get its terms in writing before any customer footage goes there.
4. **The customer's own cloud.** Reach Claude through the customer's cloud account (for example AWS Bedrock or
   Google Vertex AI), so the data stays under their agreement and region. Availability and terms to be confirmed.
5. **A model on the customer's hardware.** This is the distillation layer, and privacy is a second reason for it
   (speed and cost are the first). `verifier.primary: distilled` is already a one-line config change, and the first
   step is measured in `results/l7/`. Limits: today the student covers only routine checks it learned to imitate,
   and the frontier model is still the teacher and the fallback. A fully offline tier needs an open-weight
   vision model that is good enough, and that is unmeasured. Any test of one goes through the spend gate.
6. **Air-gapped tier.** Local models only. Sellable to regulated sites. Accuracy will probably be lower than with
   a frontier verifier, so measure that trade-off and state it.

**Policy side.**
- A visible signal that the camera is on, and a clear off switch. (Taking the glasses off already counts as "no
  view", `GLASSES.md`.)
- A notice for coworkers at the site.
- Keep derived data (step times, events) by default and raw frames only when someone presses Save. This matches
  the item 3 default of aggregates for the employer.

**What to say if asked (for the interview).** "The fast layers run locally. Only event-triggered crops go to a
model API. Today nothing is anonymized. The plan is on-device blur of people, enterprise terms, and moving routine
checks to a model on the customer's own hardware, which our distillation layer is built for." Say "plan", not
"feature", until it is built.

## How they fit together

A manager uploads an SOP in the portal (4), reviews the compiled steps, and assigns it to a worker's profile (3).
The worker puts the glasses on and picks their profile. They hear the steps (1) and, when stuck, see the manual's own
figure for that step (2). Corrections flow back to the profile and the training records.

## Suggested order (my recommendation)

1. **Portal plus locked procedure (4).** Highest value for the wedge, and the compile flow already exists, so the
   first slice is small: upload PDF, compile, review in a plain page, run in locked mode in Studio.
2. **Voice in and out (1).** Cheap ($0 options), very visible in a demo. Test the noise and ear-defender question
   early, because it may change the design.
3. **Persistent profile (3).** Start with the minimum: a profile that stores skill and preferences. Decide the privacy
   rules first.
4. **Generated visuals (2).** Most exciting and most risky. Start with manual-sourced figures and precomputed
   visuals, and add on-demand generation last.

Privacy (5) runs through all of these. Write the data policy and add on-device blur of people before the first
customer pilot. Verifying the vendors' terms costs nothing and can happen any time.

## Decisions I need from you

1. **Profile data.** Does the worker own their memory, with the employer seeing aggregates? (Recommended: yes.)
2. **Locked mode.** A per-assignment flag, or a whole-workspace setting? (Recommended: a per-assignment flag, with an
   option to lock a whole workspace.)
3. **Generated visuals.** Never for safety-critical content unless the uploaded document supplies it? (Recommended: yes.)
4. **Voice trigger.** Tap-to-talk or always listening? (Recommended: tap-to-talk first.)
5. **Privacy tiers for the wedge.** Which do we offer first: cloud with blur and enterprise terms, the customer's own
   cloud, or a model on their hardware? (Recommended: cloud with blur and terms for pilots, and design for the
   on-hardware tier.)

## Also on the board (already known, not in your four)

- **Multi-task and the "away" state.** Fully designed in `MULTITASK.md`, not built. Locked mode depends on part of it.
- **Real glasses.** `MetaGlassesSource` is a stub on purpose. Glass-to-engine latency is the biggest unknown
  (`GLASSES.md`).
- **Maintenance footage.** Everything measured so far is cooking and assembly. Real or realistic maintenance clips
  are needed before any claim about the wedge. Pilot sessions in Studio would produce them.
- **Distillation.** Replacing routine verifier calls with a local student model (first step measured in
  `results/l7/`) is what makes the coach cheap and fast at scale.
