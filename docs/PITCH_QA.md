# Pitch Q&A: every hard question, and our answer

> **What this is.** Every question and objection raised while preparing the 2026-10-20 interview, plus the usual
> investor objections and a playbook for each competitor. Use it to build the deck and rehearse Q&A.
>
> **Rules.**
> - Product numbers come only from [`CLAIMS.md`](CLAIMS.md).
> - Market facts are cited in [`VISION.md`](VISION.md), [`POSITIONING.md`](POSITIONING.md),
>   [`USE_CASES.md`](USE_CASES.md) and [`COMPETITORS.md`](COMPETITORS.md). Citation tags like [P3] or [D19] point
>   to those files' source lists.
> - Anything marked *plan* isn't built.
> - Checked 2026-10-17.

## The six lines to memorize

1. **What it is.** "Praxis is an AI coach for physical work. It watches through a first-person camera, knows where
   you are in a procedure, checks your work, and talks you through it."
2. **Conviction.** "Coaching is a tracking problem, not a seeing problem." Calling the same frontier model every 5 s
   without state tracked steps 48% of the time. Our stateful engine got 54%, at about a fifth of the cost
   (cooking video, `CLAIMS.md`).
3. **Wedge.** "New maintenance and repair technicians. Today they shadow a senior tech for weeks, and the work moves
   around the machine, where a bolted-on camera can't follow."
4. **Why now.** "In four months: Viture and NVIDIA launched coaching glasses, NVIDIA open-sourced the toolkit, Meta
   opened its glasses' camera to apps, and Google and Samsung ship glasses this fall. The hardware and plumbing are
   being built around us. The part nobody has proven is the coach."
5. **Platforms.** "Designed to run on every pair of glasses, with or without a screen: a voice coach on camera
   glasses, plus a heads-up card on display glasses." Say "designed to run on" until an adapter has run on that
   device.
6. **Long game.** "Today we coach the people. Next we train and check the robots that work next to them."

---

## Part 1: The questions we asked ourselves

### A. Market and wedge

**Which market first: new workers, dementia care, or consumers?**
- **New maintenance technicians.**
  - They win on who pays, how often the same task repeats, and working without consumer glasses.
  - Autodesk is buying MaintainX, a phone app for maintenance procedures, for $3.6B [D19].
  - BLS projects about 51,900 maintenance-mechanic openings a year [D20].
  - 47% of maintenance teams lost know-how when someone left (vendor survey) [D16].
- **Dementia: the mission market, later.** A 2008 camera-based coach (COACH) cut the help people needed from a
  caregiver by 60%, but only in 6 participants. Three things block it today: who pays, consent for the data, and
  wearing glasses. CrossSense won £1M for this in Mar 2026. Details: `USE_CASES.md`.
- **Consumers: the endgame.** Willingness to pay is weak (Frontdoor's expert-video plan fell from $99 to $25 a year).
  App-store distribution for glasses isn't open. Meta's and Google's own assistants win on generic tasks.

**Why maintenance and not assembly lines?**
- Fixed-camera tools already serve assembly stations, and setup takes "a couple hours" (Retrocausal) [K1].
- Maintenance work moves around the machine, every asset differs, and new techs learn by shadowing. A coach that
  follows the person is the only kind that works there.
- Assembly stays as a later expansion (`VISION.md`, Phase 2).

**Who do we sell to: managers or workers?**
- **Managers pay.** Maintenance managers and supervisors, service-shop owners and technical-program instructors feel
  the training cost and sign.
- **Workers use it.** Their trust decides whether it stays on. So the coach is for the worker, and memory belongs to
  the worker (*plan*, `NEXT.md` item 3).

**Is there demand for *our* fix, not just a training problem?**
- Unproven. That's why the outreach email asks three things:
  1. how they train new techs now and how long it takes
  2. roughly what that costs
  3. whether they'd try a tool like this on one job
- Quote replies honestly. A reply is never a "customer" or a "pilot" (`OUTREACH.md`).

### B. Product and hardware

**What does the technician actually wear? Who straps a phone to their head?**
- Nobody. Phone mounts are pilot rigs only.
- **Main product: glasses or a head-mounted display.**
  - RealWear Navigator 520: a rugged Android headset with a small display, about $3,000, already used in industrial
    maintenance [P15][P18].
  - Meta Ray-Ban Display: $799, with a screen.
  - Camera-only Ray-Ban Meta: $379–449.
  - Android XR glasses: no screen this fall, display models in 2027.
- **Fallback for stationary bench and training-lab jobs:** a tablet on a clamp arm, with the camera on the work and
  audio to earbuds. It can't see what the user sees, so it's secondary.

**Doesn't coaching need a screen? Most glasses don't have one.**
- What Praxis needs is the **camera**. Nearly all AI glasses have one; only some have a screen. IDC expects 13.6M
  screenless vs. 3M display glasses in 2026 (`VISION.md` G3).
- **The design is voice first, glance second.**
  - Voice carries the core loop: the step, "verified", a mistake, "show me the underside". Turn-by-turn
    navigation works the same way.
  - A screen adds a reference image, numbers (torque, part numbers) and a checklist.
  - In loud plants, a screen or vibration may be needed. Test this with customers.
- **What a screen is worth.** The 82% error drop often quoted for AR came from overlays pinned to real parts
  (CHI 2003) [P12]. Meta's screen is a corner card, so the honest claim is "we use a screen when there is one".

**What can Meta Ray-Ban Display actually show?**
- **Screen:** 600×600 pixels, in the right eye, about 20° wide.
- **What apps can draw:** text, images, buttons, icons and short video.
- **Video limits:** under 400 px per side and 70,000 pixels in total.
- **Updates:** each one resends the full layout over Bluetooth [P16][P17].
- **What that means for us:** a short instruction card plus a still image of what "done" looks like. Not
  full-resolution video.
- **Unknown:** whether an app can stream the camera and use the display at the same time. Needs hardware.

**Is voice built?**
- **Output: yes.** Live mode speaks its actions: the task, each instruction, "verified", mistakes, view requests,
  done. It uses macOS `say` on the Mac, and Studio uses the browser's voice.
- **Input: no.** The *plan* is for the technician to talk naturally: "done with the filter", "what's next?",
  "I already did that", "no, I'm still on the belt". The engine already knows the procedure, so the person never
  needs step numbers. Each utterance becomes evidence for the tracker, and each correction becomes a free training
  label. Design and build plan: [`VOICE.md`](VOICE.md).

**How does a company make the glasses "learn" its procedures?**
- **Knowledge portal and locked procedures** (*plan*; `NEXT.md` item 4):
  1. A manager uploads SOPs, manuals and training videos.
  2. Praxis compiles them into steps, end states, checks and known mistakes.
  3. A human reviews and signs off.
  4. Versions are kept.
  5. In **locked mode**, Praxis only guides the assigned procedure, flags deviations with the step cited, and never
     improvises.
- **What exists today:** compiling pasted text into a typed task graph (Studio, `tasks/compiler.py`).
- **Why it matters:** this is what turns "a model with a camera" into "a coach for *your* machines". It's also the
  answer to "why not Gemini" (Part 3).

**Is the hardware too expensive?**
- The employer buys a few shared units for whoever is in training. RealWear at about $3,000 each shows maintenance
  teams already pay for head-mounted displays. Meta Display at $799 is cheap next to that.
- None of this needs consumers to adopt AR.

**Can we say it's "plug and play" on Meta, Viture and every pair of glasses?**
- **Not yet.** Nothing has run on glasses. `MetaGlassesSource` is a stub, Viture ships in Q1 2027, and whether
  Helix accepts outside apps isn't documented.
- **What we can make true without hardware:** build the Meta adapter against Meta's official Mock Device Kit,
  which simulates the glasses and streams a recorded camera feed, and test it end to end [P13].
- **The line once that's done:**
  > "Our Meta adapter is written against Meta's toolkit and tested end to end on Meta's mock device. What's left is
  > real glasses and a latency measurement, and hardware is a line item in this grant."
- **Don't say "the software is done."** Mistake catching is weak (4 of 17), every metric is from cooking, and
  there's no voice input yet.

**"Glasses with NVIDIA chips": is that a thing?**
- No. Glasses like Helix are a camera, microphones and speakers. They stream to NVIDIA GPUs in the cloud or on a
  server, where NVIDIA's software runs [P4]. No chip in Helix has been named [P10].
- Meta glasses work the same way, except they stream to the phone.

**Why build software and not glasses?**
- **Capital.** Meta's Reality Labs lost $4.62B in one quarter (Q2 2026) [P6].
- **Hardware is crowded and getting cheaper.** Meta, Google/Samsung, Viture, Rokid, Alibaba, Xiaomi and Snap
  are shipping glasses, and IDC expects the average
  price of screenless glasses to fall from $376 to $229 by 2030.
- **Customers need different devices.** Safety-rated, consumer, prescription, tablets. A software layer runs on all
  of them, and the margins and data live in the software.
- **Risk:** a platform closes its camera access. **Mitigation:** run on several platforms, plus phones and tablets.

### C. Competition (short answers; full playbook in Part 3)

**Viture + NVIDIA: how do we compete?**
- **Viture Helix is glasses and coaching sold together:** $600+ safety glasses, voice-only, shipping in Q1 2027
  with invite-only pilots, aimed at labs and pharma first [P3][P10]. No accuracy published. No state tracking or
  "when to speak" logic described.
- **NVIDIA is a supplier, not a competitor.** XR AI is a free, open-source toolkit (plumbing, small models,
  samples) that runs on NVIDIA GPUs [P4].
- **Our answer:**
  - We run now, on hardware a shop already owns, with no $600 device.
  - The tracking and calibration layer is measured.
  - We start in maintenance.
  - We'd rather also run on Helix than fight it.
  - We can use NVIDIA's free models as our verifier (untested).

**Why doesn't NVIDIA's free toolkit replace Praxis?**
- It makes a coaching *demo* cheap for everyone, us included. Its public docs don't describe tracking a long
  procedure, deciding when to speak, asking for a better view, checking a site's own procedures, or accuracy [P4].
- "It's like ROS for robotics: it made robotics companies faster to start; it didn't replace them."

**Retrocausal is a different product, right?**
- Yes. It's error-proofing for production lines: a fixed camera per station, sold to industrial engineers to cut
  rework ("poka-yoke") [P1]. It isn't built for training, or for work that moves.

### D. Business

**What do we charge, and does it make money?**
- **Hypothesis:** $150–250 per active trainee per month, after a paid pilot. Tulip lists $100–250 per station a
  month [D3]. One AWS Marketplace listing puts Retrocausal at about $500 per station a month.
- **Cost to serve at 2 hours a day:**
  - about $214 a month if we streamed to a frontier model every 5 s (gross margin negative)
  - about $45 a month for our engine today (about 77% margin)
  - about $20 a month with the distilled local model (about 90% margin)
  - (`POSITIONING.md`)
- **"The architecture is the business model."**

**What's the moat?**
- **Today, none that can't be copied,** and we say so.
- **What compounds:**
  - the procedure and mistake library per vertical
  - verified work records (switching costs)
  - in-house models trained on our own sessions (the cost curve is already measured: the student cuts cost to
    $0.008 from $0.018 per video-minute)
  - plan-aligned, mistake-labeled data of skilled work (`VISION.md`, "Moats, honestly")

---

## Part 2: Common investor objections

| Objection | Short answer | Backup |
|---|---|---|
| "Isn't this a wrapper?" | Most layers are ours: event detector, compiler, recognizer, Bayesian tracker, calibration, policy, distilled student. Only 14% of frames leave the local layers, and the fast tier answers 88% of those calls | `CLAIMS.md` |
| "Isn't this a feature Meta or Google will add?" | They'll add general coaching. The vertical job (your procedures, locked mode, records, integrations, mixed hardware) isn't a feature of a consumer assistant | Part 3, Google and Meta rows |
| "Your mistake detection is weak." | Yes: 4 of 17 alerts were strictly correct. All 4 were order errors, which need task state. Phase 1 leads with step tracking and verification; mistake alerts fire only at high precision | `CLAIMS.md`, `VISION.md` |
| "Every number is from cooking." | True. Maintenance footage is the first use of the grant: real procedures at one or two friendly sites. Assembly clips were qualitative only | `CLAIMS.md`, `USE_CASES.md` |
| "Has it run on glasses?" | No. The engine runs live on a video stream; glasses are an input adapter. The Meta adapter can be tested on Meta's mock device now, and hardware is in the grant budget ($2,500) | `GLASSES.md`, `APPLICATION.md` |
| "Why now?" | Four launches in four months (see the six lines). Microsoft also ends Dynamics 365 Guides and Remote Assist on Dec 31, 2026, so those customers need a replacement | `POSITIONING.md`, "Why now" |
| "Why you?" | Seven years of competitive robotics, real-time vision work (LipTrac), and a working, measured engine built in a weekend. The long game (robots) is the founder's home field | `APPLICATION.md` |
| "You're solo." | That's what the grant tests: discovery and a first pilot. First hires: a forward-deployed engineer for pilots, then an ML engineer | `VISION.md` |
| "How do you reach customers?" | Direct outreach to maintenance managers and technical programs. Then expansion within an account (more techs, more sites), and integrations with maintenance software (MaintainX-style) | `OUTREACH.md` |
| "Will workers accept a camera?" | Coaching is for the worker. Memory belongs to the worker, and the employer sees aggregates (*plan*). Visible camera indicator. On-device blur of people (*plan*) | `NEXT.md` items 3 and 5 |
| "Where does the video go?" | The fast layers run locally. Only event-triggered keyframes and crops go to a model API (about 14% of frames, `CLAIMS.md`). *Plan:* blur people on device, enterprise terms, then a model on the customer's hardware | `NEXT.md` item 5 |
| "What if it gives a wrong instruction on a safety step?" | Locked mode follows only the customer's signed-off procedure. Safety-critical steps (lockout/tagout) are prompted and recorded, never "approved" by Praxis. Generated visuals are never used for torque, wiring or lockout | `VISION.md` Phase 1, `NEXT.md` item 2 |
| "How big is this?" | The wedge is maintenance training, priced like Tulip. The expansion is a system of record for physical work, the way Samsara built one for fleets ($2.1B ARR). The long game is data and a checker for robots | `VISION.md` |
| "What does the money buy?" | Ten customer conversations, the first maintenance footage and metrics, a pilot with a pre-agreed metric, glasses hardware, and a kill rule if buyers don't care about the first-person edge | `USE_CASES.md` |
| "What if the pilot fails?" | Switch to the next category (field service, then assembly stations), not a new product | `VISION.md` |
| "Isn't hardware adoption too slow?" | We don't need consumers. Industrial teams already buy head-mounted displays, and a site needs only a few shared units | `POSITIONING.md` |

---

## Part 3: The competitor playbook

What each one is, what it can and can't do (as far as public information shows), its likely move, and our response.

| Competitor | What it is | Can do | Can't do / hasn't shown | Likely move | Our response |
|---|---|---|---|---|---|
| **Google / Samsung (Android XR + Gemini)** | Platform plus a general assistant. Samsung glasses reported for Nov 2026 (no screen); display models in 2027 [P19] | Gemini built in; huge model and engineering team; distribution on Android phones | A vertical maintenance product: loading a site's procedures, locked mode, records, CMMS integration, enterprise rollout on mixed hardware. No public app channel for these glasses yet | Gemini Live gets better at "look and help". Maybe a "follow this document" feature | Use Gemini as our verifier if it's best. Win on the vertical job and on every device. Build the Android XR adapter early (*plan*). Google is a likely partner or acquirer |
| **Meta (Ray-Ban, Oakley, Display + Meta AI)** | Market leader in AI glasses (more than 7M sold in 2025) | Camera, mic and speakers to apps via DAT 1.0; screen access on Display; Meta AI | Enterprise sales; procedure ingestion; safety-rated frames [P5] | Better Meta AI "Live" help; more app access | Build on DAT (mock-tested *plan*). Stay multi-platform in case access tightens. Meta is a possible acquirer |
| **Apple** | Glasses reported for 2027, no display [G6] | Ecosystem, privacy brand | Nothing shipped | A developer platform in 2027–28 | Same adapter pattern when it opens |
| **NVIDIA (XR AI)** | A free open-source toolkit plus models that run on NVIDIA GPUs [P4] | Streaming, Cosmos/Nemotron models, sample agents (a guided tea-making sample) | Product, sales, procedure state tracking, accuracy. Siemens is evaluating it for factory maintenance [P4] | More partners (Viture, Siemens), more samples | Treat it as a supplier. Plug Praxis in behind the XR AI hub so we run on XR AI glasses (*plan*). Possibly use its free models |
| **Viture Helix** | $600+ safety glasses with real-time SOP coaching, built on NVIDIA. Ships Q1 2027 [P3] | Voice in and out, safety form factor (certification pending), NVIDIA backing, LabOS research | Shipping; a screen; published accuracy; state tracking; full-shift battery (documented "60+ minutes" charge-while-using) | Pilots in labs and pharma, then industry | Run now on owned hardware; maintenance focus; measured tracking. Try to run on Helix if it opens |
| **Strivr Frontline Intelligence** | Early-access smart-glasses error detection; a per-customer model built from footage its team captures [K6] | Enterprise relationships from its VR-training days | Published accuracy; zero-footage setup | Sell to its existing VR customers | Faster setup from existing procedures; publish numbers; mid-size maintenance teams |
| **Retrocausal, Invisible AI, Arkite, Spot AI** | Fixed-camera line error-proofing and analytics [K1][K8][K9] | Live missed-step alerts on stationary stations; quick setup | Following a moving worker; training focus | Deeper into quality and analytics | Don't fight on the line. Own moving maintenance work |
| **Tulip (incl. Factory Playback)** | App platform for frontline work, $1.3B. Testing vision-language checks of "whether a procedure was followed" [K5] | Huge install base, procedure apps, AI Composer | First-person, wearable coaching (not documented) | Ship Factory Playback broadly | Integrate (Tulip apps as procedure input). Stay first-person and mobile |
| **MaintainX (→ Autodesk), Augmentir, Squint** | Procedure and work-order apps on phones; some photo checks [K10][D19] | The procedures and the customer relationships | Watching the work continuously | Add AI photo checks | Partner. Their procedures are our input, and we're their eyes. Autodesk could be an acquirer |
| **Siemens** | Evaluating NVIDIA XR AI for factory maintenance, "in a research context" [P4] | Big industrial customers | A shipped product (none found) | A pilot product for large plants | Speed, published numbers, and mid-size customers first. A partner or acquirer later |
| **RealWear** | Industrial head-mounted display, about $3k [P15] | Hardware already in maintenance teams; Android | Our coaching layer | Partner apps | A target platform (a standard Android app, *plan*) |
| **CrossSense (dementia)** | £1M Longitude Prize winner; AI glasses that coach daily tasks [E3] | Mission market lead | Industrial use | Phone version late 2026, glasses 2027 | Not our wedge. We revisit dementia later |
| **Frontier labs (OpenAI, Anthropic, Google DeepMind)** | General models | Better vision and reasoning every year | Products for physical work | Cheaper, faster models | They're our engine. A swappable verifier means their progress lowers our cost |

### If they do X, we do Y

| If… | Then… |
|---|---|
| Google ships Gemini coaching on its glasses | We put Gemini in as our verifier if it's best, and compete on procedures, locked mode, records, integrations and mixed hardware. For consumer tasks, we concede and stay vertical |
| Meta restricts camera access | We still have phones and tablets, RealWear and Android XR. We don't rely on a single platform |
| Viture Helix becomes the standard safety glasses | We run on it (via XR AI or its app path) or beside it. The coach matters more than the frame |
| NVIDIA adds procedure tracking to XR AI | We use it if it's good, and compete on accuracy, data, customers and integrations. Our tracker was never the only moat |
| Tulip or MaintainX adds camera checks | They have procedures; we have first-person continuous verification. Integrate or partner; they're also natural acquirers |
| A well-funded team copies us | Speed, published numbers, maintenance data and customer records. The data and records compound; code doesn't |
| Frontier models get 10× cheaper | Good for us. The cost per trainee falls, and margins grow |
| Robot labs collect their own data | The data stays our edge for coaching. The verifier API still applies. Phases 1–3 don't depend on robots |

### Why our system beats a big team fine-tuning Gemini (the honest version)

- **We don't try to beat Gemini as a model.** We use the best model available, Gemini included, as one swappable
  part.
- **What wins inside a maintenance team isn't the model.** It's:
  - the site's own procedures, loaded, reviewed, versioned and locked
  - checks and signed records
  - when to speak, tuned per site
  - working on every device the site owns
  - a team that runs the pilot and takes responsibility
- **Our measured hint.** A frontier model in a loop without state tracked steps worse (48% vs. 54%) and cost about
  5× more.
- **Risk.** If Google builds a dedicated maintenance product, it's a race. Focus, speed, customer data and records
  are what we'd have. Google is also the natural buyer.
- **Inference, not sourced:** big platforms tend to ship general assistants and leave vertical workflows to
  partners.

---

## Part 4: Platform readiness, as much as we can do before having hardware

**The plan (nothing is built).**
- **One engine** on a laptop or server now, on device later.
- **One small client protocol:** frames with capture timestamps in; speech text plus an optional card layout out.
- **A thin adapter per platform.**

| Platform | Path | Testable without hardware? | Blockers | Status |
|---|---|---|---|---|
| Phone / tablet / webcam | Directly; Studio in a browser | Yes | None | Engine replay tested. Studio runs on a camera; live webcam metrics not claimed |
| **Meta** (Ray-Ban: voice; Display: voice + card) | DAT 1.0 (iOS or Android) | **Yes: Mock Device Kit** for the camera [P13]. Mock support for the Display isn't confirmed | Free developer account (Monish signs up); camera + display together unverified | *Plan*, about 6–10 h, $2 cap. Not started |
| **Google Android XR** (voice now, display 2027) | Jetpack Projected (camera through a projected context), Compose Glimmer for display [P19] | Partly: Android Studio glasses emulator; camera emulation unconfirmed [P14] | No public app channel yet; devices from Nov 2026 | *Plan*, about 6–10 h. Not started |
| **NVIDIA XR AI → Viture Helix and other XR AI glasses** | Praxis as an agent or service behind the XR AI hub | Unknown: XR AI expects NVIDIA GPUs, so a test means a rented cloud GPU | GPU cost (estimate before renting); Helix app access undocumented; Helix ships Q1 2027 | *Plan*: a read-only evaluation first (about 2–4 h, $0) |
| **RealWear** (and other Android headsets) | A standard Android app | Partly (Android emulator, without the optics) | Device about $3k | *Plan*; shares code with the Android XR adapter |

**Suggested order:**
1. The protocol plus Meta (mock-testable today).
2. Android XR (devices ship this fall).
3. The XR AI evaluation, then Helix when it ships.

Every build goes through the spend gate: an itemized estimate and Monish's yes first.

---

## Part 5: Our known weaknesses, said before they ask

| Weakness | What we say | What fixes it |
|---|---|---|
| Mistake detection: 4 of 17 strict | "Our weakest number, and it needs task state, which is what we built" | Maintenance data and locked procedures |
| All metrics from cooking | "First use of the grant: maintenance footage" | Pilot sites, Studio sessions |
| Never run on glasses | "Glasses are an input adapter; hardware is in the budget" | Meta mock adapter, then real glasses |
| No voice input | "It speaks today; listening is next" | Voice input ([`VOICE.md`](VOICE.md)) |
| Solo founder | "The grant tests the market before hiring" | First hires after the pilot |
| No customers yet | "Here's what managers told me this weekend" (only if they replied) | Outreach, then a pilot |
| Privacy | "Fast layers are local; blur and a local-model tier are next" | `NEXT.md` item 5 |
| Big platforms moving in | "They're building our hardware and plumbing; the coach is the open layer" | Speed, data, records |

## Part 6: Say / don't say

**Say:**
- "designed to run on"
- "tested on Meta's mock device" (only after it is)
- "54% vs. 48% against the same model without state, on cooking video"
- "a coach for your procedures"
- "we use a screen when the glasses have one"
- "hypothesis" for the price

**Don't say:**
- "plug and play"
- "the software is done"
- "runs on Viture / NVIDIA glasses"
- "works on maintenance or assembly"
- "customers" or "pilots" (we have none)
- "we beat Viture / Strivr / Gemini" (never compared)
- "nobody else verifies by camera"
- any dollar value for our data
- that the concept video is model output
- before the provisional patent is filed: the mechanism details (verification trigger rules, the tracker
  math, async replay). Results and the product story are fine

## Part 7: More questions investors may ask (added 2026-10-17)

### How big is the market, in numbers? (rough bottom-up, US only)

| Group (BLS) | Jobs | Openings a year |
|---|---|---|
| General maintenance and repair workers | 1,503,150 (May 2023) | about 159,800 (2024–34) |
| Industrial machinery mechanics, maintenance workers, millwrights | about 547,300 (2025) | about 51,900 (2025–35) [D20] |
| HVAC mechanics and installers | 440,900 (2025) | about 40,600 [D21] |
| **Total** | **about 2.47M** | **about 255,000** |

- **The wedge alone** (new techs only, coached for 3–6 months at $200 a month): **about $150–300M a year.**
- **Every tech** (verification and records for the whole workforce at about $50 a month): **about $1.5B a year.**
- **Not included:** electricians (821k jobs), aviation maintenance, field service, assembly lines, other countries,
  and the robotics phase.
- **Assumptions to state out loud:** the prices are our hypothesis, openings include people moving between jobs,
  and the per-tech price for the whole workforce is a guess.
- **The honest line:** "The wedge is a beachhead in the low hundreds of millions. The prize is every technician,
  then every physical procedure."
- Sources: BLS OEWS 2023 and the BLS Occupational Outlook Handbook for general maintenance and repair workers
  (https://www.bls.gov/ooh/installation-maintenance-and-repair/general-maintenance-and-repair-workers.htm), plus
  [D20] and [D21].

### More objections

| Question | Short answer | Status |
|---|---|---|
| "54% step accuracy sounds low." | It is low in absolute terms, and it's an honest first measurement. It's the share of frames inside annotated steps where Praxis named the right step. It counts the lag after each step change, on open recipes. The same model without state got 48%. Locked procedures (a closed set), the person saying "done", and per-site data should all raise it. The pilot is judged on a business result (time until a new tech works alone), not on frame accuracy | True today; the improvements aren't measured |
| "That's very little training data. Isn't it just memorizing?" | No. Every test uses recordings it never trained on, and the step-change detector also works on procedure types it never saw. We also retrained each learned layer on growing slices of the data. Step accuracy on the 3 procedures with 9 recordings went from about 31% with 1 recording to about 51% with 9. The student went from about 63% to 72.5% on 469 held-out checks. Neither curve has leveled off (`results/scaling/learning_curve.json`). If they ask for counts, give them: 3–9 recordings per procedure, 24 for the detector, 30 for the student. Don't say "exponential": the gains are steady per doubling | Measured (2026-10-17) |
| "Where does it actually run? A laptop on every tech?" | Today the local layers run on an M4 laptop at about 3× real time, and model calls go to an API. For pilots: one shared box at the site, with glasses → phone → box over the site Wi-Fi. Later: a small distilled model on the phone (`MODEL_ROADMAP.md`). The $45 a month figure covers model calls only. A site box is a one-time cost on top | Pilot setup is a *plan* |
| "Enterprise AR already failed: Google Glass Enterprise, HoloLens." | Google stopped selling Glass Enterprise in Mar 2023 [P20]. HoloLens 2 stopped production in Dec 2024 and Microsoft ends Guides on Dec 31, 2026 [D9]. Those were hardware-first and showed instructions; buyers couldn't measure the value. We're software on cheap or already-owned hardware, we verify the work, and every pilot has a metric agreed in advance. And their customers need a replacement now | Argument; no pilot yet |
| "What if the plant Wi-Fi is bad?" | The local layers keep tracking without a network, and model calls queue up. A site box on the local network avoids the internet. Fully on-device is the Phase 3 goal | *Plan* |
| "You depend on a small vendor (Jev)." | The verifier is swappable. Claude Haiku in the same slot measured 47% at $0.007 per video-minute (vs. 54% with Jev), and the local student already handles routine checks. Get Jev's data terms in writing before any customer footage goes there | Measured swap; terms not checked |
| "Latency on glasses?" | Unknown, and it's the first thing we measure with hardware. The live loop never waits on the network (worst tick lag 0.8 s with async calls, `CLAIMS.md`) | Glasses untested |
| "How long are your sales cycles? What does a customer cost to win?" | Unknown. Start with mid-size maintenance teams and training programs, and short paid pilots. Discovery measures this | Unknown |
| "Why would managers pay if checklists in an app are good enough?" | Checklists don't see the work, and shadowing still costs senior-tech time. Outreach question 2 tests exactly this | Testing now |
| "Many technicians don't speak English as a first language." | Speech and text models handle many languages, so a procedure can be coached in the tech's language. This could be an advantage; it's unmeasured | Opportunity, unmeasured |
| "Is there IP?" | Only say "a provisional patent is filed" once the filing receipt exists. Until then: "we're filing a provisional." See Part 6 | Draft in `patent/` |
| "Unions and monitoring laws?" | Coaching for the worker, aggregates for the employer, no face recognition, a visible camera-on signal. Rules vary by state and country, so check them before each pilot | *Plan* (`NEXT.md` items 3 and 5) |
| "When is first revenue?" | Proposed goal: one paid pilot within six months of the grant. That's Monish's call | Proposal |

### Questions only you can answer (prepare these yourself)

1. **Commitment.** Are you full-time on this, during school and after? Is there a plan to take time off if a pilot
   works? Student founders always get this question.
2. **Why this problem, personally.** The robotics-mentoring story is in the application. Is there a maintenance or
   trades connection (a family member, a job, a shop you know)? One real story beats statistics.
3. **What you'll do with the money in the first 30 days,** in your own words.
4. **The patent filing date,** if filed by Tuesday.
5. **Who you've talked to.** Have the replies to the outreach emails ready, or the honest "sent N, heard back from M".

## Where the details live

| Topic | Doc |
|---|---|
| Long-term staircase, moats, exits, hard questions | [`VISION.md`](VISION.md) |
| Conviction, competitor map, Meta vs. Viture vs. NVIDIA, hardware, pricing | [`POSITIONING.md`](POSITIONING.md) |
| Why maintenance vs. dementia vs. consumer | [`USE_CASES.md`](USE_CASES.md) |
| Competitor feature table with sources | [`COMPETITORS.md`](COMPETITORS.md) |
| Future features: voice, visuals, profiles, knowledge portal, privacy | [`NEXT.md`](NEXT.md) |
| Voice: audit of today's speech, voice-input design, build plan | [`VOICE.md`](VOICE.md) |
| The outreach email | [`OUTREACH.md`](OUTREACH.md) |
| Exact safe sentences and numbers | [`CLAIMS.md`](CLAIMS.md) |
