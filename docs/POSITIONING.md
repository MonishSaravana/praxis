# Positioning: what makes Praxis different, and where we start

> **Status: working positioning for the 2026-10-20 interview.** Facts are cited in [Sources](#sources). Competitor
> details come from [`COMPETITORS.md`](COMPETITORS.md). Product numbers come from [`CLAIMS.md`](CLAIMS.md). This
> sharpened Phase 1 of [`VISION.md`](VISION.md) from "high-mix assembly" to maintenance and repair. That change was
> agreed on 2026-10-17, and `VISION.md` and `USE_CASES.md` now match it.

## Our conviction, in one sentence

> **Coaching someone through physical work is a tracking problem, not a seeing problem.**

Most competitors pick one of two designs:
- **Stream video to a big model and hope it sees well enough.** Viture with NVIDIA, and Strivr.
- **Bolt a camera to a workstation and teach it one procedure.** Retrocausal and the other fixed-camera tools.

Our design works differently:
- We keep a running belief about where the person is in the procedure.
- Cheap local models watch every frame. A big model is called only when something happens.
- We speak only when confident, and ask for a better view when we're not.

That's the difference between a coach people keep wearing and one they take off.

**Why we believe it:**
- **Same model, better result.** Given the same frontier model, adding our state tracking raised step accuracy from
  48% to 54% and cut the cost to about a fifth ($0.018 vs $0.085 per video-minute) (`CLAIMS.md`).
- **It doesn't guess on bad views.** When the view was degraded, Praxis asked for a better one on 77–98% of checks
  and was never confidently wrong (`CLAIMS.md`).
- **The structure has helped people before.** In 2008, COACH used the same design (a probabilistic tracker over the
  task, plus graded prompts) to cut the help people with dementia needed from a caregiver by 60%. That study had 6
  participants ([`USE_CASES.md`](USE_CASES.md) E2).
- **The economics only work this way.** See [Pricing](#pricing-and-unit-economics).

## The competitor map: who does what job, for whom

| Category | Examples | Their job | Who buys | Camera | Us vs them |
|---|---|---|---|---|---|
| Instruction platforms | Tulip apps, Augmentir, Squint, Dozuki | Turn documents into step-by-step instructions on a tablet. Checking = sign-offs and photos | Ops excellence, training | None, or operator photos | They show the steps; we watch the work. Could integrate |
| Line error-proofing and analytics | Retrocausal, Invisible AI, Arkite, Spot AI, Tulip Vision | Catch missed steps on a **production line**, plus time studies | Industrial and quality engineers | Fixed at the station | **A different job.** Retrocausal sells "poka-yoke" and rework reduction, not training [P1]. Fixed cameras can't follow a person who moves |
| First-person AI coaching | Strivr Frontline Intelligence (early access), Viture Helix + NVIDIA (ships Q1 2027), Rana LabOS (labs) | Coach through the wearer's eyes | Large enterprises; labs and pharma | Worn | **Closest competitors.** Different first market, and they are hardware-led or high-touch (see below) |
| Toolkits and platforms | NVIDIA XR AI (open source), Meta's camera toolkit (DAT), Android XR | Plumbing that lets apps get video and call models | Developers | Any | **Complements.** We build on them |
| General assistants | Meta AI, Gemini Live | Answer questions about what the camera sees | Consumers (free) | Glasses or phone | No plan, no state, no calibration |
| Dementia support | CrossSense (won the £1M Longitude Prize) | Coach daily tasks at home | Families, care providers | Glasses or phone | A later market for us ([`USE_CASES.md`](USE_CASES.md)) |

**How to say it:**
> "Instruction tools show the steps. Line cameras police a production station. We're a coach that follows the person,
> knows where they are in the procedure, and only speaks when it's sure."

## Meta vs. Viture vs. NVIDIA: what each one actually is

| | Meta Ray-Ban / Oakley Meta | Viture Helix | NVIDIA XR AI |
|---|---|---|---|
| What it is | Consumer AI glasses; a general assistant, no procedure coaching | Enterprise AI **safety** glasses **with AI coaching built in**: a hardware-plus-coaching bundle that coaches workers on SOPs in real time [P3] | An open-source (Apache-2.0) developer library in public beta, not a product. It ships small open models and sample agents. Viture's coaching is built on it [P4] |
| Price | from $299 (Meta-branded), $379 (Ray-Ban Gen 2), $449 (Ray-Ban Gen 3), $399–499 (Oakley), $799 (Ray-Ban Display) [P2] | From $600 [P3] | Free to download. Running it needs NVIDIA GPUs (cloud, data center, workstation or edge), which is how NVIDIA earns [P4] |
| Available | Now. More than 7M sold in 2025 ([`VISION.md`](VISION.md) G1) | Ships Q1 2027; enterprise pilots are invite-only [P3] | Public beta (Aug 2026) [P4] |
| Workplace safety | **Not** rated as safety eyewear (ANSI Z87.1), per a Meta community manager [P5] | Built to ANSI Z87.1-2025; certification "in progress" [P3] | n/a |
| How the AI works | Our app on the phone gets the camera through Meta's toolkit (not tested on hardware yet) | Streams the wearer's view over Wi-Fi to a multimodal model on NVIDIA's stack. No phone needed [P3] | Routes live video and audio to model services: Cosmos-Reason1-7B for vision, Nemotron Nano for language and tools, Parakeet for speech [P4] |
| First markets | Consumers | Labs, clinical and pharma, plus an industrial pilot [P3] | Anyone building agents for glasses. Siemens is evaluating it for factory maintenance [P4] |
| Published accuracy | n/a | None [P3] | None |

### What Helix's coaching actually does (public information only)

| | What's known | Source |
|---|---|---|
| **Inputs and outputs** | First-person 12MP camera and a 4-mic array in, audio out, no display. It streams the view to "a multimodal AI engine": it sees, hears and talks | [P3][P10] |
| **Hands-on demo** (AWE, Jun 2026) | In a simulated clinical lab, it recognized test tubes and guided the reviewer through a centrifuge sequence. The guidance "wasn't strictly scripted": the user could ask open-ended questions | [P10] |
| **Claimed scope** | Coaching for repetitive and for "dynamic, non-repetitive" tasks; SOP coaching; safety warnings; a full record ("provenance") of every shift; the model "improves with each shift worn" | [P3][P10] |
| **Use cases named** | Clinical and wet labs first, pharma next, and industrial assembly | [P3][P10] |
| **The research behind it** | LabOS (Stanford's Cong Lab, Princeton's Wang Lab, with NVIDIA researchers). It uses XR glasses for step-by-step lab guidance with "error detection and correction cues". It built a benchmark of 240+ first-person lab videos, found leading models "struggled" on it, and post-trained a lab-specialized vision-language model | [P11] |
| **Price** | Glasses from $600 (some coverage says a $599 reservation). **Software or AI pricing: not published.** Enterprise pilots are invite-only | [P3][P10] |
| **Unknown** | Where the AI runs (cloud, on-site server, or glasses). Which chip is in the glasses (coverage only says it "integrates NVIDIA's XR processing capabilities"). Whether third-party apps can run on it. Mistake-detection accuracy. Latency. Battery for a full shift | [P3][P10] |

**What this means for us:**
- Helix is a **direct competitor**: glasses plus multimodal coaching, sold as one bundle.
- Its research arm (LabOS) runs the same playbook we plan for Phase 3: collect first-person data, find that general models struggle, then train a specialist. They're doing it in labs. That's one more reason we stay in maintenance.
- **Where they're ahead of our prototype:**
  - **Voice input.** You can ask Helix questions. Praxis today only *speaks*; it doesn't listen yet.
  - **Purpose-built safety glasses.**
- **Where we differ:**
  - Any camera, available now.
  - Tracking state across a whole procedure, with a calibrated "when to speak" policy and a measured "ask for a better view".
  - Cost per minute.
  - A different first market.

### Where Viture + NVIDIA are weak (and strong)

**Weak:**
- **It's not shipping.** Helix ships Q1 2027, pilots are invite-only, and the safety certification is pending [P3].
- **Hardware first.** A customer must buy a $600+ device per worker to get the AI. A hardware company's software
  exists to sell its glasses.
- **Battery.** The release lists "60+ minutes" of battery in charge-while-using mode. A full shift isn't
  documented [P3].
- **A general-purpose pipeline.**
  - NVIDIA's library streams video and voice from the glasses to models on NVIDIA GPUs [P4].
  - Its samples include a guided tea-making workflow "with visual evidence".
  - Its docs don't describe:
    - task-state tracking across a procedure
    - step verification or mistake detection as built-in features
    - calibration, or a "when to speak" policy
  - Streaming continuously to a model is the costly design. Our stateless baseline was that design, and it cost
    about 5× more.
  - **Inference:** Viture's exact architecture and costs aren't public.
- **No accuracy published.**

**Strong:**
- Purpose-built safety-glasses hardware, which factory floors require.
- NVIDIA's backing and models.
- Standalone, with no phone needed.
- Voice input: workers can ask it open-ended questions. Our prototype doesn't listen yet.
- Viture already sells a lot of display glasses (company-cited IDC ranking [P3]).
- They could add state tracking later.

### What the NVIDIA–Viture partnership is

- **Launch partner.** Helix is billed as "the first AI safety eyewear platform built on NVIDIA's XR AI solution" [P3].
- **Who does what, in their words.** NVIDIA provides "the AI infrastructure". Viture supplies "the smart hardware and
  edge software" [P3].
- **A joint launch.** It was unveiled at AWE 2026 in June, with demos in an NVIDIA and Dell meeting room. Both
  companies point to work with Stanford's Cong Lab and Princeton's Wang Lab [P3][P4]. Money terms aren't public.
- **Why each side does it** (our inference):
  - NVIDIA gives the software away so the models run on NVIDIA GPUs (cloud, data center, or a desk-side DGX Spark),
    and a flagship device shows the toolkit working.
  - Viture gets models, engineering help and NVIDIA's name for its enterprise glasses.
- **Watch this one.** Siemens is also evaluating XR AI, with DGX Spark, "in a research context" for **factory
  maintenance and troubleshooting** [P4]. That's our wedge.

### Why NVIDIA's free toolkit doesn't replace Praxis

**What's free:**
- the plumbing (glasses video and voice → models → tools)
- small open models (Cosmos-Reason1-7B for vision, Nemotron Nano for language, Parakeet for speech)
- sample agents, including a guided tea-making workflow "with visual evidence" and a procedure-recording demo [P4]

Anyone can now build a coaching *demo* in days, including us.

**What isn't in it.** Its public docs don't describe the parts that make a coach trustworthy on real work [P4]:
1. **Knowing where the person is** in a long procedure. That's our state tracker.
2. **Deciding when to speak and when to stay quiet,** and asking for a better view instead of guessing. That's our
   calibrated policy.
3. **Turning a site's own procedures into checks.** That's our compiler, step checks and mistake library.
4. **Staying affordable.** Only 14% of our frames leave the cheap local layers (`CLAIMS.md`). A pipeline that
   streams everything to a model pays for every second.
5. **Measured accuracy,** plus customers, integrations and data in one vertical.

**How to say it:**
> "NVIDIA's toolkit is like ROS for robotics: free and useful. It didn't replace robotics companies; it made them
> faster to start. It makes a demo cheap for everyone, including us, so the demo was never the moat. The moat is
> accuracy on real work, the procedures and data for one vertical, and the customers. And we can use NVIDIA's free
> models too: our verifier is a swappable part."

The last point hasn't been tested: we haven't run Cosmos-Reason as a verifier.

**Honest risk.** The free toolkit lowers the bar for competitors too, and Siemens is already exploring maintenance
with it. Our answer:
- **Speed and published, measured results.**
- **Size of customer.** We start with mid-size maintenance teams, service shops and training programs. Siemens
  sells mostly to large enterprises.
- **Siemens could also be a partner or a buyer.**

## Why now: the category is forming this year

All dates are 2026 unless noted.

| When | What happened |
|---|---|
| Jun 16 | Viture and NVIDIA announce Helix: safety glasses that coach workers on SOPs in real time [P3] |
| Aug | NVIDIA's open-source XR AI toolkit for glasses agents enters public beta [P4] |
| Sept 23–30 | Meta's camera toolkit for third-party apps reaches 1.0 ([`VISION.md`](VISION.md) G4). Ray-Ban Meta Gen 3 launches [P2] |
| Oct 6 | Tulip announces Factory Playback: vision-language checks of "whether a procedure was followed", now in customer testing ([`COMPETITORS.md`](COMPETITORS.md) TU6–TU7) |
| Nov (reported) | Samsung and Google's Android XR glasses ([`VISION.md`](VISION.md) G5) |
| Dec 31 | Microsoft ends Dynamics 365 Guides and Remote Assist; headset-era customers lose their tools ([`VISION.md`](VISION.md) D9) |
| Q1 2027 | Helix ships [P3]. Apple's glasses are reported for 2027 ([`VISION.md`](VISION.md) G6) |

**What it means:**
- The big players are building the hardware and the plumbing.
- Nobody has proven the coaching layer yet: knowing where someone is in a procedure and when to speak. None of them
  publishes accuracy.
- The other side of good timing: well-funded players are moving at the same time. So speed and measured results
  matter more than ideas.

**How to say it:**
> "In the last four months, Viture and NVIDIA launched coaching glasses, NVIDIA open-sourced the toolkit, Meta
> opened its glasses' camera to apps, and Tulip started testing camera checks of procedures. The hardware and
> plumbing are being built around us. The part nobody has proven is the coach itself, and that's the part we've
> measured."

## Why we stand a chance (the investor answer)

1. **NVIDIA isn't selling this product.**
   - It ships plumbing and demos so that many companies build products that run on its GPUs.
   - NVIDIA wins when apps like ours exist.
   - We can build on its library.
   - See [Why NVIDIA's free toolkit doesn't replace Praxis](#why-nvidias-free-toolkit-doesnt-replace-praxis).
2. **Viture's coaching only comes with Viture's glasses. Ours runs on any camera.**
   - Helix bundles real-time SOP coaching with a $600+ device, built on NVIDIA's toolkit [P3]. That makes it a real
     competitor, and also proof that the category is real.
   - Our difference is that no new device is needed (a phone works today), plus the layer that decides where the
     person is and when to speak.
   - If Helix becomes standard on factory floors, we'd still want Praxis running on it. Whether Helix accepts
     outside apps isn't documented, so check before saying it.
3. **We win on the layer they haven't shown.** That layer is tracking, timing and asking for a better view. We
   publish accuracy and false-alarm numbers; they publish none.
4. **The economics.** Our design costs about a fifth as much to run as streaming to a frontier model, and the
   distilled local model halves that again. That decides who can sell at $100–250 a seat and keep a margin.
5. **A different first market.** They start in labs, pharma and large enterprises. We start with maintenance and
   repair technicians, where we can run a pilot this month on hardware people already own.

**Honest risk.** A well-funded player could add state tracking. Our protection over time is the data and the
in-house models (`VISION.md`, Phases 2–3), plus running on every camera rather than one.

## What we can say about glasses (and how to get to "connect it and it runs")

**Can't say yet: "plug and play on Meta glasses, Viture, or any glasses with NVIDIA chips."**
- Nothing has run on glasses. `MetaGlassesSource` is a stub ([`GLASSES.md`](GLASSES.md)).
- Helix doesn't ship until Q1 2027, and whether it accepts outside apps isn't documented.
- **"Glasses with NVIDIA chips" isn't a category.** The glasses don't run the AI. They are a camera, microphones and
  speakers that stream to a server, and NVIDIA's software and models run on NVIDIA GPUs there: in the cloud, a data
  center, or a desk-side box such as DGX Spark [P4].
  - That's how Helix uses NVIDIA's library without an NVIDIA chip in the frame. No chip in Helix has been named
    [P10].
  - Meta glasses work the same way, except they stream to the phone.
- **"The software is done."** Investors will poke at it:
  - mistake catching is weak (4 of 17 alerts were right)
  - every metric is from cooking
  - there's no voice input yet

  It also makes Praxis sound like an integration project, which undercuts the data-and-models vision.

**The target state, and it's reachable without glasses.** Meta's toolkit ships an official **Mock Device Kit**
[P13]. It pairs a simulated Ray-Ban Meta, simulates putting them on, taps and permissions, and streams a camera
feed loaded from a file. So the whole path can be built and tested now:
- recorded video → mock glasses → our iPhone app → engine on the laptop → spoken prompts back
- The only parts left untested are the real-hardware unknowns: latency, image quality, field of view and battery.

**The line, once that's done:**
> "The engine runs live in real time. Glasses are just a camera and a speaker, so connecting them is an adapter, not
> a rebuild. Our Meta adapter is written against Meta's official toolkit and tested end to end on Meta's mock
> device. What's left is running it on real glasses and measuring latency, and hardware is a line item in this
> grant."

The application's budget includes $2,500 for smart-glasses hardware and capture equipment.

**The line before it's done:**
> "The engine is camera-agnostic and runs live on a video stream. Each pair of glasses is an input adapter, and the
> Meta adapter is next."

**Other platforms, so we don't live or die on Meta.** One engine, with a thin adapter per device. The interface
already exists: `FrameSource`, plus speech out.

| Platform | How an outside app gets the camera | Can it be tested without hardware? | Status for us |
|---|---|---|---|
| Phones, tablets, head or chest cameras | Directly | Yes (a webcam, or iPhone Continuity Camera) | Works today (replay tested; live webcam is the demo plan) |
| Industrial head-mounted displays (RealWear) | A normal Android app with the standard camera API [P15] | Partly (an Android emulator, without the real optics) | Not started |
| Meta (Ray-Ban, Oakley, Display) | A phone app through Meta's toolkit (DAT 1.0) | **Yes, with the Mock Device Kit** [P13] | Adapter not built |
| Android XR glasses (Samsung/Google, reported for Nov 2026) | A phone app through Jetpack Projected ([`GLASSES.md`](GLASSES.md)) | Partly. Android Studio has an AI-glasses emulator; whether it emulates the camera is unconfirmed [P14] | Not started |
| Glasses built on NVIDIA XR AI (Viture Helix, LabOS-compatible glasses) | The glasses stream to an XR AI hub. Praxis would run as a service behind it | Unknown until we check whether the hub runs without NVIDIA GPUs | Not evaluated |
| Snap Specs | Lens Studio camera module, on the device ([`GLASSES.md`](GLASSES.md)) | Lens Studio has a preview | Not started |

**If Meta builds this itself.** Meta builds general assistants for consumers. It doesn't do procedure ingestion,
maintenance-system integration, per-site calibration or enterprise sales for one vertical.
- **The real risk** is Meta restricting camera access.
- **Mitigation:**
  - Start phone-first, where nobody can switch us off.
  - Keep adapters for every platform that opens up.
  - Meta also stays a natural acquirer.

**"The visuals" means the camera, not a screen.**
- Praxis's value is that it *sees* the work. Our own design is voice-first, and a screen is optional.
- Most AI glasses have a camera and no screen. IDC expects 13.6M display-less versus 3M display glasses in 2026
  ([`VISION.md`](VISION.md) G3).
- A camera pair is $299–449. Only the Display model is $799 [P2].

**Is the hardware too expensive? Not in the wedge.**
- The employer buys the devices, the way it buys tablets and scanners.
- A training kit of a few shared pairs per site gets reused for every new hire.
- A tablet at the bench works on day one, and maintenance teams already buy head-mounted displays (see
  [What a technician actually wears](#what-a-technician-actually-wears)).
- Whether a few hundred dollars per shared device is small next to weeks of senior-tech shadowing is exactly
  what question 1 of the outreach email measures ([`OUTREACH.md`](OUTREACH.md)).
- None of this needs mass consumer AR adoption.

## What a technician actually wears

**A phone strapped to a head is not the product.** At most it's a pilot rig. Two kinds of setup are real.

| Where | Setup | Screen? | Price | Status for us |
|---|---|---|---|---|
| Repair bench, training lab, workshop | A tablet or phone on an arm at the bench: camera on the work, screen facing the technician, earbuds | **Yes, full screen** | A tablet they already own | Possible today. **Caveat:** the view is over the shoulder, not first-person, and our numbers come from head-mounted video |
| On the move, industrial | **RealWear Navigator 520**: a head-mounted Android computer with a small display on a boom arm, voice control, rugged (IP66, MIL-STD-810H), hot-swappable batteries [P15] | **Yes**, a small display | about $2,900–3,150 [P15] | Runs standard Android, so Praxis would be an ordinary Android app. Not built |
| On the move, light | **Meta Ray-Ban Display**: a 600×600 display in the right lens, about 20° field of view, up to 5,000 nits, about 6 h battery, Neural Band wristband [P16] | **Yes**, a heads-up card | $799 [P2] | Third-party apps can draw text, images, buttons, icons and short video. The phone sends a full layout over Bluetooth [P17]. **Not documented:** whether camera streaming and the display work at the same time. Not safety-rated |
| On the move, camera only | Ray-Ban Meta Gen 3, Oakley Meta Vanguard | No (voice only) | $379–499 [P2] | Adapter not built. Meta's mock glasses kit exists [P13] |
| Safety glasses | Viture Helix | No (voice only) | from $600, Q1 2027 [P3] | Unknown whether outside apps can run on it |
| Android XR | Samsung Galaxy Glasses (reported for Nov 2026, no display). Display models in 2027 | 2027 | Not confirmed | See below |

**How the tablet setup works.**
- Nobody holds it. It sits on a stand or a clamp arm at the bench or machine, with the camera on the work and the
  screen turned toward the technician.
- Audio goes to the technician's earbuds or Bluetooth hearing protection, not out loud to the room.
- It only works for stationary jobs: bench repairs, rebuilds, training-lab exercises. If the job moves around a
  machine, it has to be a wearable.

**Meta Ray-Ban Display limits, for reference images and video** [P16][P17]:
- **Size.** One 600×600 screen in the right eye, about 20° wide (roughly a small card floating at arm's length).
  Images larger than 600×600 bring no benefit.
- **Video.** Clips must stay under 400 px per side and 70,000 pixels in total (about 264×264), short, and loaded
  from a URL.
- **Updates.** Each update resends the whole layout over Bluetooth, and big images can lag.
- **Compared with our renders.** Our renders are 1280×720. On the glasses, a reference shows up as a still image
  (up to 600×600) or a thumbnail-sized clip, not as full video.

**What this tells investors.** Industrial maintenance teams already pay about $3,000 per head for a voice-controlled
display headset with a camera. RealWear says it has shipped to more than 3,000 enterprise customers, including
Shell, Colgate-Palmolive and BMW (a 2021 figure) [P18]. The hardware habit exists in exactly our wedge, and Meta's
Display does a lighter version for $799. A site buys a few shared units for whoever is in training.

**Voice vs. screen, honestly.**
- **Voice carries the core loop:** the step, "verified", a mistake, a view request. Turn-by-turn navigation works
  mostly by voice for the same reason.
- **A screen matters for:**
  - what "done" looks like (a reference image)
  - numbers (torque values, part numbers)
  - the checklist
  - loud plants, where audio fails. Ask managers about hearing protection; Bluetooth earmuffs exist.
- **So the design is voice first, glance second.** For the wedge, the target hardware is display wearables
  (RealWear now, Meta Display now, Android XR display glasses in 2027) plus a tablet at the bench. Camera-only
  glasses are the low end.

**Android XR (Google + Samsung): what's known.**
- **The glasses.** The first are Samsung's, reported for November 2026, with no display. Display models come in
  2027 (Google, I/O 2026), with Gentle Monster and Warby Parker designs. Price not confirmed; leaks say $379–499
  [P19].
- **How apps work.**
  - The app runs on the Android phone and "projects" to the glasses (Jetpack Projected).
  - The camera is available through a projected context, after a runtime permission.
  - Display glasses get their UI through Jetpack Compose Glimmer.
  - Android Studio has an AI-glasses emulator [P14][P19].
- **Distribution.** A July 2026 third-party developer guide says there's no public app channel for these glasses
  yet [P19].
- **Risk.** Gemini is built in, the same competitor risk as Meta's assistant. The answer is in
  [`VISION.md`](VISION.md) under hard questions ("What if Google ships Gemini…").

**The wearables line (true today):**
> "Every major platform is shipping AI glasses: Meta now, Google and Samsung this fall, Apple reportedly next
> year. Praxis is designed to run on all of them, with or without a screen: a voice coach on camera glasses, plus a
> heads-up card on display glasses. We start where the hardware already exists, on industrial headsets and in
> maintenance teams, so we're not waiting for consumers to adopt glasses."

Say "designed to run on". Don't say "runs on" until an adapter has run on that device.

**Platform option (not decided).** One Android companion app could cover most of the table:
- Meta glasses (Meta's toolkit has an Android SDK)
- Android XR glasses
- RealWear (standard Android)
- tablets

The iPhone path stays for the Continuity Camera demo. Building an Android app costs more time before Tuesday than
it saves, so this is a post-interview decision.

## Voice and screen: what to add, and what a screen is really worth

**Voice input (planned; not built).** Praxis today speaks but doesn't listen. Adding listening is a speech-to-text
step plus a few intents, and each one feeds the state tracker as one more piece of evidence:

| The technician says | What Praxis does with it |
|---|---|
| "I'm replacing the pump seal" | Sets the task. On unseen tasks, video alone named 0 of 7. When the person said what they were making, Praxis drafted a plan on 7 of 8 (`CLAIMS.md`) |
| "Done", "next", "skip", "I already did that" | Strong evidence for the step tracker |
| "No, I'm on step 4" | A correction, and a free human-confirmed training label for the flywheel |
| "Why?" or "What should it look like?" | One model call, with the current step as context |

**Meta glasses and voice.**
- The glasses have microphones and open-ear speakers. Meta's toolkit lets our phone app use the mic.
- **Catch:** the documented Bluetooth mic mode (8 kHz) degrades speaker audio while it's on ([`GLASSES.md`](GLASSES.md)).
- Meta doesn't give apps its own assistant, so we'd run our own speech-to-text. Apple's on-device recognizer or a
  local Whisper model would cost $0.

**A screen, when there is one.**
- Only Meta Ray-Ban Display ($799) has one: 600×600, in one eye. Meta's toolkit documents sending simple UI to it
  from the phone. We haven't tested this.
- We could show a step card, or a picture of what "done" should look like. Voice-only Helix can't do that.
- **How big an advantage that is.** The classic evidence for showing over telling (Tang et al., CHI 2003: an 82%
  drop in assembly errors versus a printed manual) came from 3D instructions overlaid on the actual work pieces
  [P12]. That needs AR glasses that track the room. Meta's display is a heads-up card in the corner, not an overlay.
- So the honest claim is "we use a screen when the glasses have one," not "showing is our moat." Any app built on
  Meta's toolkit gets the same screen.

**How the overlays in our videos are made.** Not by AI.
- The engine decides *what* to say: the step, the instruction, a mistake, a view request.
- Ordinary graphics code (`prototype/praxis/render/hud.py`, PIL/OpenCV) draws the cards and progress bar from the
  saved run log.
- Live, the laptop draws the same cards. On Meta's Display, the phone would send a simple layout and the glasses
  would draw it. Overlays pinned to real objects would need the glasses' own room tracking.
- The concept video's HUD was generated by a video model. That's why it had garbled text.

## Why software, not glasses

- **Capital.** Meta's Reality Labs posted a $4.62B operating loss in Q2 2026 alone [P6]. Hardware takes tens of
  millions and years, and that's not what $10k is for.
- **Hardware is crowding and getting cheaper.**
  - Omdia expects more than 15M AI glasses in 2026.
  - IDC expects the average price of display-less glasses to fall from $376 to $229 by 2030 ([`VISION.md`](VISION.md) G2–G3).
  - Meta, Google and Samsung, Apple (2027), Viture, Rokid, Alibaba, Xiaomi and Snap are all making glasses.
- **Customers need different devices.** Safety-rated for factories, consumer frames for homes, prescription lenses,
  a phone for today. A software layer serves all of them. One pair of glasses can't.
- **The scarce part is the brain and the data.** That's where software margins and the robotics path live (`VISION.md`).
- **Platforms want this.** Meta opened its camera to apps, NVIDIA open-sourced XR AI, and Viture built on NVIDIA's
  stack.
- **Risk.** A platform could close its camera access. The mitigation is to run on several platforms and on phones.

## The short-term wedge: new technicians on maintenance and repair

**Why this, and not assembly benches.** Fixed cameras and instruction platforms already serve assembly stations
well. Retrocausal says setup takes "a couple hours" (`COMPETITORS.md`). Maintenance and repair work moves around the
machine, varies by asset, and is often learned by shadowing one senior technician. A coach that follows the person is
the only kind that works there.

**Evidence of demand:**
- **The budget is proven.** Autodesk agreed to buy MaintainX, a mobile-first app for maintenance work orders and
  procedures, for about $3.6B (May 2026). MaintainX expects more than $135M ARR in 2026 [P7]. The procedures are
  already on technicians' phones. We add eyes. MaintainX is also a natural integration partner.
- **New technicians keep coming.**
  - US openings average about 51,900 a year for industrial machinery mechanics, maintenance workers and millwrights
    [P8].
  - HVAC mechanics add about 40,600 openings a year [P9].
- **Knowledge walks out the door.** 47% of maintenance teams lost knowledge they couldn't recover when someone left.
  74% have critical assets that depend on one person. (Vendor survey, [`VISION.md`](VISION.md) D16.)

**What we sell.**
- At the bench: a tablet on an arm, with the camera on the work. On the move: a display headset or glasses
  (RealWear today, Meta Ray-Ban Display, Android XR display glasses in 2027). Phone mounts are only for pilots.
- Praxis loads the site's existing procedures, coaches the new technician step by step, verifies critical steps, and
  logs a verified record.
- **Buyer:** the maintenance or service manager. **User:** the new technician.
- **Metric agreed before the pilot:** time until the new technician works alone, senior-technician hours spent
  shadowing, or repeat work.

**First pilots** (reachable this fall):
- A facilities or maintenance team.
- An equipment service shop.
- A technical training program (HVAC, industrial maintenance) that wants a second pair of eyes on every student.

**How we compete with Viture here:**
1. We work now, on hardware they already own. Helix ships next year.
2. No $600 device is required to try us.
3. We publish accuracy.
4. They're focused on labs and pharma.
5. If a site needs safety glasses, we aim to run on Helix rather than fight it.

**Where it leads.** The same customers need expert capture and verified work records (Phase 2). Maintenance
technicians are a known labor shortage. And factories are where robots arrive (`VISION.md`).

## Pricing and unit economics

**The customer pays for two things:**
1. **Hardware, the customer's choice.** A phone they own, Ray-Ban Meta ($379–449, not safety-rated), Oakley Meta
   Vanguard ($499), or Viture Helix (from $600, once shipping) [P2][P3].
2. **Praxis.** Per active trainee seat per month. Before that, a short paid pilot.

**What the market already pays:**
- Tulip lists $100–250 per station per month ([`VISION.md`](VISION.md) D3).
- One AWS Marketplace listing shows Retrocausal at $150,000 a year for 25 stations, about $500 per station per month
  (`COMPETITORS.md` RC4).
- **Our hypothesis:** $150–250 per trainee per month, to be tested in discovery.

**What it costs us to serve one trainee.** Assumption: 2 hours of coached work a day, 21 workdays a month (2,520
video-minutes). Costs per minute are from `CLAIMS.md`.

| Design | Cost per video-minute | Cost per trainee per month | Gross margin at $200 |
|---|---|---|---|
| Stream to a frontier model every 5 s (our stateless baseline) | $0.085 | about $214 | **negative** |
| Praxis engine today | $0.018 | about $45 | about 77% |
| Praxis with the distilled local model | $0.008 | about $20 | about 90% |

**The line for investors:** *the architecture is the business model.* Streaming everything to a big model can't be
sold profitably at what buyers already pay. Phase 3's in-house models push our cost toward zero.

### What training a technician costs today, and what an hour of Praxis costs (added 2026-10-17)

**What the sources say.**
- **Pay.** Median pay for industrial machinery mechanics, maintenance workers and millwrights is $30.82 an hour
  (May 2025) [P8]. Wages are 70.2% of what private employers pay per hour worked; the rest is benefits (June 2025)
  [P21]. So a fully loaded hour of a median technician costs about **$44**. Senior techs earn more, so $44 is low for
  the person doing the training.
- **How long it takes.** BLS says on-the-job training for these jobs "typically lasts more than a year" [P8]. In an
  aviation-maintenance survey (35 repair stations, 2017), new hires took 9–14 months on average to become profitable,
  and some took 24 [P22].
- **What gets counted.** The average company spends $1,254 per employee a year on formal training, for 13.7 hours
  (2024 data) [P23]. ATD's numbers leave out coaching and mentoring. Shadowing a senior tech, which is most of how a
  technician learns, isn't in anyone's training budget. It shows up as lost senior-tech hours.
- No source I found measures what shadowing costs per technician. The numbers below that depend on it are labeled
  as assumptions.

**What an hour costs.** Model cost per video-minute comes from `CLAIMS.md`, multiplied by 60.

| | Cost per hour |
|---|---|
| A senior tech's time, fully loaded (median wage, so low) | about $44 |
| Praxis price at $200 per trainee-month, 2 h/day (42 h/month) | about $4.76 |
| Our cost to serve, stateless frontier baseline (every 5 s) | about $5.10 |
| **Our cost to serve, Praxis engine today** | **about $1.08** |
| Our cost to serve, with the distilled local model | about $0.48 |

**Lines that hold up:**
- "Running Praxis costs us about a dollar an hour. Calling a frontier model every 5 seconds costs about five dollars."
  (Cost to serve, not the price.)
- "An hour of Praxis coaching costs the customer about what six minutes of a senior tech's time costs."
- "At $200 a month, Praxis pays for itself if it saves a senior tech about one hour a week." ($2,400 a year ÷ 52 ÷ $44.)
  This is the ROI claim to test in a pilot. It's small enough to be believable.

**Assumptions, labeled.** If a senior tech spends 50% of their time on a new hire for the first 3 months, that costs
about $11,400 in senior-tech time. At 25% over a 12-month ramp, it's about $22,800. Neither split comes from a source.
Ask the people we interview what theirs is.

**A pricing risk.** A flat per-seat price breaks if trainees wear it all shift. At 8 h/day (168 h/month), $200 is
$1.19 an hour, and our cost today is $1.08 an hour, so the margin is about 9%. With the distilled model ($0.48/h) it's
about 60%. Price by coached hours or tiers (for example, $200 includes 40 hours), or move the routine checks to the local
model before offering unlimited use.

## What talking to people actually gets you

Desk research can't tell you:
1. **Whether the pain is ranked high enough.** How do they train a new technician today? How long until that
   technician works alone? Whose time does that eat?
2. **What they use now and hate.** Binders, MaintainX checklists, shadowing, videos.
3. **Hard constraints.**
   - Are safety glasses mandatory?
   - Are cameras allowed?
   - Is there Wi-Fi?
   - Can video leave the site?
   - Is there a union?
4. **Who signs, from which budget, and what price feels small.**
5. **Which result after a pilot would make them buy.**
6. **Whether our edge matters to them:** following the person, setup from their own procedures, asking for a better
   view.

**For Tuesday,** one real quote ("a maintenance manager told me shadowing costs her senior tech two weeks per hire")
beats any statistic. It also shows the reviewers you talk to customers, and that's what a grant for experiments
rewards.

**How to ask.** Ask about the past, not about the idea:
- "Walk me through the last time you onboarded a technician."
- "What went wrong?"
- "What did that cost?"
- "What have you tried?"
- Show the demo only at the end.

## What we can't claim yet
- **Any accuracy on maintenance or assembly.** Every metric is from cooking.
- **That Praxis runs on glasses or on Helix.** It hasn't been tested, and Helix's openness to third-party apps is
  unknown.
- **That we beat Viture, Strivr or NVIDIA's pipeline.** We beat *our own* stateless baseline. A head-to-head
  comparison is possible later: NVIDIA's library is open source.
- **The $150–250 price.** It's a hypothesis until a buyer says it.

## Sources
All checked 2026-10-17.
- [P1] Retrocausal homepage (Assembly Copilot: "Poka Yoke", "Minimize Rework and Scrap Costs"): https://retrocausal.ai
- [P2] Meta glasses prices:
  - Meta shop: https://www.meta.com/ai-glasses/shop-all/
  - Ray-Ban Meta Gen 3 at $449: https://vr-expert.com/en-us/meta-connect-2026-recap-vr-glasses-ray-ban-meta-gen-3/
  - Ray-Ban Display at $799: https://www.engadget.com/wearables/meta-ray-ban-display-glasses-offer-an-ar-display-for-799-002921925.html
  - Meta-branded line from $299: https://about.fb.com/news/2026/06/meta-essilorluxottica-partner-launch-meta-glasses/
- [P3] Viture Helix:
  - Release, Jun 16, 2026: https://www.prnewswire.com/news-releases/viture-unveils-helix-the-first-ai-safety-glasses-built-on-nvidias-xr-ai-solution-at-awe-2026-302802005.html
  - Product page: https://www.viture.com/helix
- [P4] NVIDIA XR AI:
  - Developer blog: https://developer.nvidia.com/blog/building-ai-agents-for-ar-glasses-and-xr-devices-with-nvidia-xr-ai/
  - Docs: https://nvidia.github.io/xr-ai/v0.1.0-beta/
  - Repository (Apache-2.0, sample agents): https://github.com/NVIDIA/xr-ai
  - Public beta coverage: https://auganix.org/xr-news-nvidia-xr-ai-public-beta
- [P10] AR Insider, hands-on with Helix, Jun 18, 2026: https://arinsider.co/2026/06/18/vitures-enterprise-expansion-hands-on-with-helix/ · NVIDIA XR AI page (use cases include "Standard Operating Procedure Monitoring and Guidance"): https://developer.nvidia.com/xr/xr-ai
- [P11] LabOS: "The AI-XR Co-Scientist That Sees and Works With Humans," Oct 2025: https://arxiv.org/abs/2510.14861
- [P12] Tang, Owen, Biocca and Mou, "Comparative effectiveness of augmented reality in object assembly," CHI 2003: https://researchwith.njit.edu/en/publications/comparative-effectiveness-of-augmented-reality-in-object-assembly/
- [P13] Meta Wearables, testing with the Mock Device Kit (iOS): https://wearables.developer.meta.com/docs/develop/dat/testing-mdk-ios/ · FAQ: https://developers.meta.com/wearables/faq
- [P14] Android XR AI-glasses emulator: https://developer.android.com/develop/xr/jetpack-xr-sdk/run/emulator/ai-glasses · Developer Preview update, Jun 2026: https://android-developers.googleblog.com/2026/06/what-is-new-android-xr.html
- [P15] RealWear Navigator 520: store listing https://shop.realwear.com/products/realwear-navigator-520 · specs https://vr-compare.com/headset/realwearnavigator520
- [P16] Meta Ray-Ban Display specs: Road to VR https://roadtovr.com/meta-ray-ban-smart-glasses-display-price-release-date-specs/ · UploadVR https://www.uploadvr.com/meta-ray-ban-display-glasses-officially-announced/
- [P17] Meta Wearables, display access overview: https://wearables.developer.meta.com/docs/develop/dat/display-overview/
- [P18] RealWear release, Mar 2021 (3,000+ enterprise customers): https://www.businesswire.com/news/home/20210316005683/en/RealWear-Accelerates-Leadership-Position-in-Industrial-Wearables-Market
- [P19] Android XR:
  - 9to5Google, May 2026: https://9to5google.com/2026/05/19/google-samsung-android-xr-glasses-styles-release-date/
  - Projected context (camera): https://developer.android.com/develop/xr/jetpack-xr-sdk/access-hardware-projected-context
  - Compose Glimmer: https://developer.android.com/agents/skills/xr/display-glasses-with-jetpack-compose-glimmer/skill
  - Distribution note (third-party): https://extentos.com/docs/ecosystem/platforms/android-xr
- [P20] 9to5Google, Google Glass Enterprise Edition discontinued (sales end Mar 15, 2023; support to Sept 15, 2023): https://9to5google.com/2023/03/15/google-glass-enterprise-edition-discontinued/
- [P5] Meta community forum, safety rating: https://communityforums.atmeta.com/discussions/ai-tips-tricks/safety-glasses-for-meta-vision-glasses/1350134
- [P6] Reality Labs Q2 2026 (secondary): https://www.shacknews.com/article/150184/facebook-meta-reality-labs-q2-2026-losses
- [P7] Autodesk to acquire MaintainX:
  - Release, May 28, 2026: https://www.streetinsider.com/PRNewswire/Autodesk+to+acquire+MaintainX%2C+advancing+unified+platform+in+operations/26566203.html
  - SiliconANGLE: https://siliconangle.com/2026/05/28/autodesk-acquire-maintainx-3-6-billion-push-operations/
- [P8] BLS Occupational Outlook, industrial machinery mechanics, maintenance workers and millwrights (2025–35 projections, May 2025 wages): https://www.bls.gov/ooh/installation-maintenance-and-repair/industrial-machinery-mechanics-and-maintenance-workers-and-millwrights.htm
- [P21] BLS Employer Costs for Employee Compensation, June 2025 (private industry: wages 70.2% of compensation): https://www.bls.gov/news.release/archives/ecec_09122025.htm
- [P22] ARSA, "Time to onboard a new technician," member survey of 35, May 16, 2017: https://arsa.org/?p=12666
- [P23] ATD, 2025 State of the Industry (2024 data: $1,254 and 13.7 formal hours per employee; excludes coaching and mentoring): https://www.td.org/content/atd-blog/benchmarks-and-trends-from-the-2025-state-of-the-industry-report
- [P9] BLS Occupational Outlook, HVAC mechanics and installers: https://www.bls.gov/ooh/installation-maintenance-and-repair/heating-air-conditioning-and-refrigeration-mechanics-and-installers.htm
