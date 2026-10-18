# Praxis: the long game

> **Status: strategy, not results.** Product numbers come from `results/` (via [`CLAIMS.md`](CLAIMS.md)). Market
> numbers are cited in [Sources](#sources), with the date each was reported. Anything that is a plan is written as a
> plan. Phase 0 is the only phase that has happened.

## The one line

Praxis is building a model of how physical work gets done correctly, step by step: what each step looks like
when it's done, the mistakes people actually make, and the fix that works. We start by coaching people through
their work. Robots will need the same layer to learn that work and to be checked while they do it.

**Short version:** *Today we coach the people. Next we train and check the robots that work next to them.*

## The 60-second version (to say out loud)

> Every physical skill is still taught by manuals and videos that can't see you. Praxis closes the loop, built on
> one belief: coaching is a tracking problem, not a seeing problem. On public first-person video, it tracks where
> someone is in a procedure better than a frontier model called every few seconds, at about a fifth of the cost.
>
> We start with new maintenance technicians. They learn by shadowing a senior tech for weeks. The work moves around
> the machine, where a camera bolted to a workstation can't follow. And their procedures already live on their
> phones: Autodesk is paying $3.6 billion for one maintenance app. We give those procedures eyes.
>
> Every session becomes data nobody else has: first-person video lined up to the procedure, with verified steps,
> real mistakes and the fixes that worked. It trains our own models, so the product gets cheaper and better.
>
> And robot companies now pay people to film themselves working, because robots learn from that video and need to
> know whether each step succeeded. That's our data and our checker, and our customers pay us to collect it. Today
> we coach the people. Next we train and check the robots that work next to them.

---

## Why now: three curves are crossing

**1. Cameras are moving onto faces, and the platforms are opening to developers.**
- EssilorLuxottica sold more than 7M AI glasses in 2025 [G1]. Omdia counts 8.7M AI-glasses shipments in 2025
  (+322%) and forecasts more than 15M in 2026 [G2]. IDC forecasts 13.6M display-less smart glasses in 2026, rising
  to 27.3M in 2030, plus display glasses growing from 3M to 12.2M [G3].
- Meta's Wearables Device Access Toolkit 1.0 (Sept 2026) gives a third-party phone app the glasses' camera, mic and
  speakers [G4]. Open App Store publishing is **not confirmed yet**. Samsung/Google Android XR glasses are reported
  for November 2026 [G5]. Apple's glasses are reported for 2027 [G6].
- **What it means for us.** Meta, Google and Apple are paying to put the camera on people's faces. We don't build
  hardware. Consumer distribution isn't fully open yet, though, so our first market can't depend on glasses.

**2. Reasoning about video keeps getting cheaper.**
- At a fixed capability level, LLM inference prices have been falling about 10× per year (a16z) [C1]. Epoch AI
  measures 9× to 900× per year, depending on the benchmark [C2].
- Our own numbers: the stateful engine costs $0.018 per video-minute vs $0.085 for calling the frontier model every
  5 s. With the distilled local student on routine checks, it costs $0.008 (`results/runs/`).
- **What it means for us.** Calling a frontier model on every frame is a bad business. The product is deciding
  *when* a model needs to look, and that decision layer is ours.

**3. Robots are learning physical work from human first-person video, and the industry pays for that video.**
- Figure trains robot navigation "exclusively on egocentric human video" (Project Go-Big) [R1]. Its paid capture
  app, Index, has paid creators $15M so far. Figure says it has committed more than $1B to data and compute over the
  next 12 months [R2]. It reports that pretraining on Index footage raised zero-shot success in 30 unseen homes from
  9% to 56%, with loss falling predictably each time the data doubled [R3]. (Figure's own claims.)
- Physical Intelligence reports that adding egocentric human video gave about 2× performance on scenarios that
  appear only in the human data [R4]. NVIDIA's EgoScale trained on 20,854 hours of egocentric human video and found
  log-linear scaling [R5]. Tesla reportedly moved Optimus training to filming humans in mid-2025 [R6].
- Buyers are already paying. Micro1's CEO estimates robotics companies spend more than $100M a year buying
  real-world data [R7]. DoorDash pays couriers to film chores [R8]. Scale AI reports more than 100k hours of
  physical-AI production data [R9]. Mecka AI raised a $60M Series B (Sequoia) to turn human motion into robot
  training data [R10].
- Robots also need a checker. Google DeepMind calls success detection "a cornerstone of autonomy" [R11]. Physical
  Intelligence's π\*0.6 learns from a value function that estimates progress toward task completion [R12].
  RoboReward and GVL are progress and reward models built from VLMs [R13].
- **What it means for us.** *Raw* first-person footage is turning into a commodity: gig recorders are paid
  $3–10/h [R14], and base pay is $1/h at one Indian vendor [R15]. What stays scarce: footage of **skilled** work in
  real workplaces, **aligned to a plan**, with **verified step completions**, **real mistakes and the corrections
  that fixed them**, plus a reliable "did this step succeed?" model. Praxis produces all of that as a by-product of
  coaching, and the customer pays for the coaching.

---

## The staircase

Each step is chosen because it already has paying demand, and because it produces the asset the next step needs.
Years are counted from the first paid pilot. **Each gate is a condition we have to hit, not a date.**

| Phase | When | Who pays | Demand already proven by | What it produces for the next step | Moat it adds | Gate to move on |
|---|---|---|---|---|---|---|
| **0. Proof** | Done (Oct 2026) | Nobody yet | n/a | Engine, eval harness, measured numbers | Eval and calibration discipline | Done: tracks steps better than stateless calls (54% vs 48%) at ~1/5 the cost |
| **1. Wedge: a second pair of eyes for new technicians** | Years 0–1.5 | Maintenance and service managers at plants, facilities and equipment-service companies; technical training programs | Autodesk is buying MaintainX, a phone app for maintenance procedures, for $3.6B [D19]; about 51,900 US maintenance-mechanic openings a year [D20]; 47% of maintenance teams lost know-how they couldn't recover when someone left [D16] | Our first proprietary sessions on real maintenance procedures; procedures compiled from existing checklists and work orders; reference customers | None yet; differentiation only (see [`COMPETITORS.md`](COMPETITORS.md)) | Paid pilots hit a metric agreed **before** the pilot; customer expands to more technicians or sites |
| **2. System of record for physical work** | Years 1.5–3 | Same buyers plus quality and compliance; then field service, assembly lines and regulated maintenance | Tulip at $1.3B with published per-station pricing [D3]; 5 acquisitions in the category since 2023 [D7]; Boeing projects 728k new aircraft maintenance technicians needed by 2045 [D17]; KKR put $230M into XOi, which captures field-technician know-how [D18] | A cross-vertical library of procedures, mistakes and fixes; verified work records | Switching costs | Customers add procedures without our help; expansion revenue from existing accounts |
| **3. Own the models** | Years 2–4 | (internal; widens margin) | Cost curve above | An in-house procedural verifier and tracker that runs on device | Scale economies | In-house model matches or beats the rented one on our domains at ≤1/10 the cost |
| **4. Physical AI: train and check robots** | Years 3–6 | Robot foundation-model labs; companies deploying robots | Figure Index, data vendors, >$100M/yr data spend (curve 3) | Robotics revenue; robot sessions in the same task graphs | Cornered resource (the data and its rights) | First paid robotics design partner, for data or for the verifier |
| **5. The operating layer for physical work** | Year 6+ | Brands, workers, robot fleets, consumers on glasses | Glasses volume (curve 1) | n/a | Network effects; "Praxis-verified" as a trust mark | n/a |

---

## Phase by phase

### Phase 0. Proof (done, October 2026)
What's real today, each from `results/` (see [`CLAIMS.md`](CLAIMS.md)):
- With the task known, the stateful engine tracked the current step 54% of the time, against 48% for the same
  frontier model called every 5 s without state. It costs $0.018 vs $0.085 per video-minute.
- With no setup at all, it recognized the procedure on 73% of held-out clips (median 40 s).
- When the view was degraded, it asked for a better view on 77–98% of checks and was never confidently wrong.
- A distilled local student agrees with the frontier verifier on 69% of held-out checks, removes 34% of frontier
  calls, and runs in 0.03 ms on a laptop CPU.
- It runs live in real time on a laptop, with the local layers taking about 50 ms per frame. Model calls run in the
  background, so the live loop never waits for the network.

What it did **not** prove:
- Mistake detection is weak: 4 of 17 alerts named a real annotated error.
- Every metric comes from cooking video, because the labels for the assembly-and-maintenance dataset were
  unreachable.
- Nothing has run on glasses.

Those three gaps are the job of Phase 1.

### Phase 1. Wedge: a second pair of eyes for new technicians (years 0–1.5)

**Beachhead: new technicians learning maintenance and repair procedures.** That means:
- maintenance teams at plants and facilities
- equipment-service companies
- technical training programs (HVAC, industrial maintenance)

The grant application promised to "identify the initial task category where adaptive guidance creates the largest
measurable improvement." This is the category we test first. It replaced an earlier pick, high-mix assembly, after
the competitor check: fixed cameras already serve assembly stations well, and maintenance work moves.
[`USE_CASES.md`](USE_CASES.md) compares it with the other two markets we considered (older adults with dementia, and
general consumers). [`POSITIONING.md`](POSITIONING.md) has the competitor map, pricing and unit economics.

**Our conviction:** *coaching physical work is a tracking problem, not a seeing problem.* We keep a running belief
about where the person is in the procedure, speak only when confident, and ask for a better view when we're not.

How we chose it. A first market has to pass all seven of these tests:

| Test | Why it matters | Maintenance and repair (chosen) | Assembly stations | Field service in homes | Consumer DIY |
|---|---|---|---|---|---|
| Procedures already written down | The compiler turns existing procedures into task graphs, so there's no authoring step | Yes. Preventive-maintenance checklists and work orders, often already on phones | Yes (work instructions are standard) | Partly | Manuals, uneven quality |
| Mistakes are costly and countable | ROI can be proven in a 30-day pilot | Yes (repeat work, downtime, safety) | Yes (rework, scrap) | Yes (repeat visits) | Weak (returns, frustration) |
| Same procedure repeated often | Data density makes the models good fast | Yes. The same checklist runs on every machine every month, and building blocks (lockout, filters, belts, fasteners) repeat across procedures | Yes (hundreds per week) | Low (every site differs) | Very low |
| A camera is acceptable | Privacy and adoption | Plant floors and service shops | Workstations are already supervised | Customer homes | Homes |
| Works without glasses | Glasses distribution isn't open yet | A tablet at the bench. On the move, display headsets such as RealWear are already common in industrial maintenance | Phone or tablet on a gooseneck | Needs to be worn | Needs glasses or a propped-up phone |
| Budget and an owner | Someone signs | Maintenance and service managers | Training and quality leads | Service managers | The consumer (unproven) |
| **Needs a camera that follows the person** | This is where our edge matters | **Yes.** The work moves around the machine | **No.** Fixed cameras already do it; Retrocausal says setup takes "a couple hours" [K1] | Yes | Yes |

**The demand is already proven.**
- **The budget exists, and the procedures are already on phones.**
  - Autodesk agreed to buy MaintainX for about $3.6B (May 2026). MaintainX is a mobile-first app for maintenance
    work orders, inspections and procedures, and it expects more than $135M ARR in 2026 [D19].
  - Praxis gives those procedures eyes. MaintainX-style apps are an input and an integration partner, not a
    competitor.
- **New technicians keep arriving.**
  - BLS projects about 51,900 openings a year for industrial machinery mechanics, maintenance workers and
    millwrights (2024–34) [D20], and about 40,600 a year for HVAC mechanics [D21].
  - The plants around them churn too: US manufacturing recorded about 3.7M separations in 2025 [D1].
- **Know-how walks out the door.**
  - In a 686-person vendor survey, 47% of maintenance teams lost knowledge they couldn't recover when someone left,
    and 74% have critical assets that depend on one person [D16].
  - New technicians learn by shadowing that one person, so every hire costs senior time.
- **Buyers already pay for frontline procedure software, and the category is consolidating.**
  - Tulip lists $100–250 per station interface per month and is valued at $1.3B [D3].
  - Squint says a Fortune 500 company is rolling it out to 10,000 field technicians (co.) [D5].
  - Recent deals: IFS bought Poka, STG bought Parsable, Flatirons bought Scope AR, and Schneider Electric agreed to
    buy PTC for $22.6B [D7].
- **The headset generation is ending.**
  - Microsoft ends Dynamics 365 Guides and Remote Assist, its remote-expert tool for frontline technicians, on
    Dec 31, 2026 [D9].
  - PTC retired Vuforia Chalk, its remote-expert tool, in Oct 2025 [D10].
  - Those customers are choosing what comes next right now.
- **Why not consumer first.**
  - Willingness to pay looks weak: Frontdoor's expert-video plan dropped from $99 a year (2023) to $25 a year for
    unlimited chats (2024) [D15].
  - Open App Store publishing for glasses isn't confirmed yet [G4].

**First pilot targets** (reachable this fall):
1. A plant or facilities maintenance team that is onboarding new technicians.
2. An equipment-service shop (HVAC, industrial equipment).
3. A technical training program that wants a second pair of eyes on every student.
4. A Dynamics 365 Remote Assist or Guides customer that needs a replacement before Dec 31, 2026.

**What we sell.**
- At the bench: a tablet on an arm, with the camera on the work and the screen facing the technician.
- On the move: a display wearable plus an earpiece. That's RealWear (about $3,000, already used in industrial
  maintenance), Meta Ray-Ban Display ($799), or Android XR display glasses (2027). Camera-only Ray-Ban Meta and
  Viture Helix work voice-only. None has been tested on hardware yet. See
  [`POSITIONING.md`](POSITIONING.md#what-a-technician-actually-wears).
- Praxis loads the site's existing procedures (checklists, work orders, manuals) and coaches the new technician
  step by step.
- It verifies critical steps and logs a verified record.
- It flags mistakes only when it's confident.
- **Buyer:** the maintenance or service manager. **User:** the new technician.

**Pricing (hypothesis).**
- Per active trainee seat per month, around $150–250. That anchors on what buyers already pay: Tulip lists
  $100–250 per station a month [D3], and one AWS Marketplace listing puts Retrocausal at about $500 per station a
  month (`COMPETITORS.md`).
- Our cost to serve, at 2 hours of coaching a day, is about $45 per trainee a month today, or about $20 with the
  distilled local model. Streaming to a frontier model the whole time would cost about $214
  (see [`POSITIONING.md`](POSITIONING.md)).
- Before any subscription, a short paid pilot with a metric agreed in advance: time until the new technician works
  alone, senior-technician hours spent shadowing, or repeat work.

**Why we win here.** We checked each competitor's public pages on 2026-10-17. The full table and URLs are in
[`COMPETITORS.md`](COMPETITORS.md). What follows are design differences. We haven't measured any of them on
maintenance, on assembly, or against these products.
- **What we can't claim.**
  - "We compile existing instructions." Tulip, Augmentir and Squint already do [K2][K3][K4].
  - "Incumbents can't copy this." Tulip is already testing camera checks built on vision-language models (Factory
    Playback, "whether a procedure was followed") [K5].
  - "Nobody tracks a whole procedure by camera." Retrocausal does, on fixed cameras [K1].
  - "We're the only first-person system." Strivr (early access) and Viture with NVIDIA (ships Q1 2027) are
    first-person and coach against SOPs [K6][K7].
  - Live mistake detection. We're behind: 4 of our 17 alerts named a real error (`CLAIMS.md`), and Retrocausal,
    Arkite and Invisible AI sell it [K1][K8][K9].
- **Against fixed-camera verifiers** (Retrocausal, Arkite, Invisible AI, Spot AI).
  - They're built to error-proof a production station. Retrocausal sells "poka-yoke" and rework reduction, not
    training [K1].
  - Maintenance work doesn't happen at one station, so a camera bolted to a bench can't follow it.
  - We ask for a better view when unsure, and none of them documents anything like that. (That's absence of
    documentation, not proof.)
- **Against procedure apps** (MaintainX, Tulip, Augmentir, Squint). They deliver the steps and collect sign-offs and
  photos [K10]. We watch the work. The plan is to read their procedures as input, not replace them.
- **Against the first-person entrants** (Strivr, Viture with NVIDIA). They're the closest by design.
  - Viture sells $600+ safety glasses with real-time SOP coaching built in, on NVIDIA's toolkit. They ship in
    Q1 2027, with invite-only pilots aimed at labs and pharma first [K7].
  - Strivr builds a per-customer model from footage its own team captures [K6].
  - We run now, on hardware a shop already owns, and we publish accuracy. Neither of them does.
  - We'd rather run on Helix than fight it. Whether it accepts outside apps isn't documented.
- **Against a general assistant ("hey Meta, help me").** It has no plan, no state and no calibration. Our own
  ablation measures that gap: 54% vs 48% step tracking at about 1/5 the cost (cooking video, against our own
  stateless baseline).

**Set up from day one for later phases.**
- Contracts include the right to use de-identified procedural data to improve the models, with a price discount
  for sharing. A customer can opt out and get a model trained only on its own data.
- Every session is written as a training-ready record (`praxis.record/1`, already built).
- **Safety-critical steps.** Steps such as lockout/tagout stay the technician's responsibility. Praxis prompts and
  records them, and never "approves" them.

**Gate.** Paid pilots hit their pre-agreed metric, and a customer expands to more technicians or sites. If that
fails, we test the next category on the list (field service, then assembly stations), not a new product.

### Phase 2. System of record for physical work (years 1.5–3)
Once Praxis is with a customer's technicians, three products grow out of the same engine:
1. **Expert capture.** Record your best technician doing the job once. Praxis compiles it into a procedure, with
   the steps, what "done" looks like, and the mistakes to watch for. This saves know-how before experienced people
   retire.
2. **Verified work records.** Proof that each critical step was done, with keyframes. Quality, audit, warranty
   and insurance teams pay for this, and once it's the record, nobody rips it out.
3. **Process insight.** Data on where people struggle across hundreds of sessions, so engineers can fix the
   process rather than blame the person.

**Expansion path.**
1. Maintenance and repair.
2. Field service (HVAC, equipment).
3. Assembly lines, such as the US drone makers scaling up under Executive Order 14307 [D11][D12][D13].
4. Regulated maintenance (aviation, medical devices).

These share the same physical building blocks: fasteners, connectors, cable routing, orientation, torque. So each
new vertical starts with part of its library already built.

**Moat.** Switching costs: the records live with us, and we're integrated with the customer's maintenance
(CMMS), quality and training systems. The library of procedures and mistakes keeps growing.

### Phase 3. Own the models (years 2–4)
- Train our own procedural verifier and state tracker on our session records. They run on the phone or the
  glasses, and the frontier model is kept only for unfamiliar tasks.
- The first step is already measured. The distilled student handles routine checks: $0.008 vs $0.018 per
  video-minute, at 52% vs 54% step accuracy.
- **Results.**
  - Gross margins look like software margins, while anyone renting a frontier model per frame pays per frame.
  - Routine checks never send video off the device, which opens sensitive sites such as defense and medical.
  - Accuracy improves where generalist models are weakest: fine, domain-specific checks and real mistakes.

### Phase 4. Physical AI: train and check the robots (years 3–6)
This is the trend we're positioned for. It's also why the beachhead is on plant floors and not in kitchens.

**Three products, one engine:**
1. **Procedural data.** Skilled-work episodes from real workplaces, aligned to a task graph, with step boundaries,
   verified completions, mistakes and recoveries. That structure is the scarce part of curve 3. Raw footage is
   becoming cheap.
2. **Verifier API.** Our "did this step succeed, and which step is this?" model, sold as a reward model for robot
   training, an evaluator for robot policies, and a monitor for deployed fleets.
3. **Robot supervision in the cells we already know.**
   - The same engine runs on a robot's camera, with the same task graphs. A procedure compiled to coach a person
     becomes the robot's plan and its checkpoints.
   - In mixed cells, Praxis tracks the state of one procedure across people and robots.

**Why us.**
- Figure pays creators to collect video; our customers pay us to collect ours.
- Humanoids got their first paying jobs in factories and warehouses. Figure's robots worked 11 months at BMW Spartanburg, loading
  90,000+ parts toward 30,000+ X3s [R16]. GXO signed a multi-year robots-as-a-service agreement for Agility's
  Digit humanoids in 2024 [R17].
  The plants where we coach technicians in Phase 1 are the ones buying robots in Phase 4, and every robot on
  those floors will need maintaining too.
- Founder fit. The grant application's alternative project was a system that predicts which human demonstrations
  would most improve a robot's policy. Phase 4 is that project, with the data collected for free.

**Honest risk.** Robot labs may prefer to collect data themselves. If they do, the data stays our internal edge
for coaching, the verifier API still applies, and nothing in Phases 1–3 depends on Phase 4.

**The option this opens: our own robot intelligence (added 2026-10-17).** Selling data and the checker is the
low-risk version of Phase 4. The bigger version is to become a robotics intelligence company ourselves: train the
robot "brain" (the skills and policies) for the procedures we know best, and let the checker grade it while it
works. This is the market investors are already paying for (Figure, Physical Intelligence, Skild; see "Exit
paths").
- **Why we'd have a right to do it.** By then we'd hold years of skilled maintenance and repair work, recorded at
  real sites, lined up to the procedure step by step, with real mistakes and the fixes that worked. Few companies
  have that, because most robot data today is collected by paid crowds doing staged tasks [R7][R8]. We'd also own
  the checker, which robot training needs as a reward signal.
- **The order to do it in.** Software skills first, on partners' robots. Start with the routine, repetitive steps we've
  watched thousands of times (inspection, part swaps, cleaning), not the hardest repairs. Don't build robot
  hardware.
- **Gate.** Only after a robot partner has paid for our data or our checker, and a policy trained on our data
  beats one trained without it on a task we know.
- **Honest risks.**
  - Human video doesn't transfer straight to robots: their hands and bodies differ from ours. Labs are reporting
    progress at learning from human video [R4][R5], but it isn't solved.
  - Robot policy work is capital-heavy, and it puts us against very well-funded labs.
  - The people we coach may hear "you're automating me". With customers and workers, the story stays "robots
    work next to you, and someone has to maintain them". Automation is the investor story for the long run, not
    the sales pitch.

### Phase 5. The operating layer for physical work (year 6+)
- **Every procedure in one format.** Any human or robot can follow it, and Praxis can check it.
- **Brands publish "seeing manuals".** Every product can ship with instructions that watch you do it. This is where
  consumer comes back: by then mass-market glasses distribution is open and our models run on device, so coaching
  a consumer costs almost nothing.
- **Workers own verified-skill records.** They become portable proof of what someone can actually do.
- **Robot fleets** run Praxis procedures with Praxis checks.
- **Network effects.** More published procedures make the glasses app more useful, which brings more sessions,
  which makes the models better.

---

## Moats, honestly

**Today there is no moat.** A good team could rebuild v0 in a few months. What they can't copy quickly is what
compounds. Here it is mapped to Hamilton Helmer's *7 Powers*:

| Power | When | Why it's real for us | What would break it |
|---|---|---|---|
| Counter-positioning | Phase 1 | **Not established.** We assumed incumbents' authoring revenue would stop them compiling existing documents. It hasn't: Tulip, Augmentir and Squint already ship it [K2][K3][K4]. | Already broken for document compiling; untested for camera checks |
| Switching costs | Phase 2 | Verified records plus integrations become the record of how work was done | Records that are exportable and easy to rebuild elsewhere |
| Scale economies (learning) | Phase 3 | Each session makes our models cheaper and more accurate. The first step is measured: the student takes over routine checks at less than half the cost | Frontier models get good and cheap enough that ours stop mattering on fine checks |
| Cornered resource | Phase 4 | Skilled-work episodes, plan-aligned and mistake-labeled, with the rights to use them. Nobody else is in the loop while that work happens | Customers refuse data rights (mitigated by the price discount and per-customer models) |
| Network economies | Phase 5 | Publishers and performers (human and robot) on one procedure format | Glasses platforms close the camera APIs to third parties |

**The skeptic's line on "data moats":** data network effects are usually weaker than founders claim. Our answer
has three parts:
1. This data only exists if you're **in the loop while the work happens**. Passive cameras don't know the plan.
   YouTube has no mistakes or fixes labeled. Gig footage is chores, not skilled work.
2. The product labels its own data for free. Every verified step is a boundary label, and every caught mistake
   plus its fix is a failure-and-recovery pair.
3. We have already measured the data lowering cost. Distillation removed 34% of frontier calls, and with the
   student on routine checks the engine runs at $0.008 vs $0.018 per video-minute.

---

## The plays (the strategy moves)

1. **Wedge, then system of record.** Land with one painful job, then become where the records live. Samsara did
   this for physical operations and now reports $2.1B in ARR [M1].
2. **Get paid to collect the data.** This is the reverse of the robot labs, which pay people to film. Tesla's fleet
   worked the same way: customers paid to drive the cars that collected the data.
3. **Commoditize the complements.** Cameras (any glasses, phone or head camera) and frontier models (a swappable
   verifier) are both complements. Their price wars widen our margin.
4. **Be ready for the platform, but don't depend on it.** When glasses distribution opens, be the best app that
   uses the camera. Until then, the business runs on phones and head cameras.
5. **Picks and shovels for physical AI.** Scale AI started by labeling data for self-driving cars. Meta's 2025 deal
   valued it at more than $29B [M2]. We aim to be the procedural data and verification layer for robots.
6. **Land where the robots land.** Pick the beachhead for where it leads (plant floors), not only for how easy it
   is to sell into.
7. **Partner with the platforms, not against them.** Meta and Google need killer apps for camera glasses. DAT
   exists so third parties can build them. The platforms are also the natural acquirers (Meta bought the
   AI-wearable startup Limitless in Dec 2025 [M3]).

## What we won't do
- **Build glasses, cameras or robot hardware.**
- **Train a foundation model before we own the data for it.**
- **Lead with a consumer app** before distribution opens and the engine is proven in one vertical. Consumer is
  where we end up, not where we start.
- **Sell surveillance.** The worker is the user. Coaching comes first, and the records serve quality, not
  discipline.

## Hard questions (and short answers)
- **"Won't Meta just build this?"**
  - Meta builds a general assistant that sells glasses. It doesn't do per-site calibration, SOP integration,
    vertical data or enterprise sales.
  - Our ablation shows stateless frontier calls track worse and cost about 5× more.
  - Meta opened the camera to third parties so apps like ours exist. If we win, Meta is a buyer.
- **"NVIDIA open-sourced a toolkit for glasses agents. Doesn't that replace you?"**
  - It's plumbing, small open models, and demos (including a guided tea-making sample). It isn't a coach anyone
    can trust on real work.
  - Its docs don't describe tracking where someone is in a procedure, deciding when to speak, or any accuracy.
  - Like ROS in robotics, it makes everyone faster to start, us included. The moat was never the demo.
  - Honest risk: Siemens is evaluating it for factory maintenance. Details:
    [`POSITIONING.md`](POSITIONING.md#why-nvidias-free-toolkit-doesnt-replace-praxis).
- **"What if Google ships Gemini on its glasses with coaching built in?"**
  - Assume it will. Gemini Live and Meta AI already answer questions about what the camera sees.
  - **"Just put the model on it" is our baseline.** The same frontier model, called every 5 s without state, tracked
    steps at 48% vs. our 54%, at about 5× the cost (cooking video). Better models raise both numbers, because our
    verifier is a swappable part. Gemini can be our verifier.
  - **A built-in assistant doesn't do the vertical job:**
    - loading a site's own procedures from its maintenance system
    - verified work records
    - per-site calibration of when to speak
    - enterprise rollout across mixed hardware (RealWear, Meta, Google, tablets)
  - **The pattern.** General models didn't remove vertical AI companies in law or medicine. They became their
    engine.
  - **Honest risk.** For consumer tasks (cooking, flat-pack furniture), the built-in assistant probably wins. That's
    one more reason the wedge is maintenance teams, not consumers.
- **"Isn't this a wrapper?"** Most layers are ours: the event detector, compiler, recognizer, Bayesian tracker,
  calibration, policy and distilled student. The frontier model is one swappable part of the verifier. Only 14% of
  frames leave the local layers, and the fast tier answers 88% of those calls.
- **"Your application said consumer smart glasses. Why maintenance technicians?"**
  - The six-month plan was to "identify the initial task category where adaptive guidance creates the largest
    measurable improvement."
  - The evidence points to the workplace first: proven budgets (Autodesk–MaintainX), repeated procedures, and no
    dependence on glasses distribution.
  - Within the workplace, maintenance beat assembly. Fixed cameras already serve assembly stations, while
    maintenance work moves around the machine. A coach that follows the person is the only kind that works there.
  - Consumer is the endgame (Phase 5), once glasses distribution opens and the models run on device.
- **"Isn't this space crowded (Tulip, Augmentir, Squint, Retrocausal, Viture)?"** Around assembly stations, yes,
  and more than we first assumed.
  - Tulip, Augmentir and Squint already compile existing documents into instructions [K2][K3][K4].
  - Retrocausal, Arkite, Invisible AI and Spot AI check work by fixed camera today [K1][K8][K9].
  - Strivr and Viture with NVIDIA are bringing first-person camera checks to glasses [K6][K7], and Tulip is testing
    vision-language-model checks [K5].
  - Buyers paying the category, and five acquisitions since 2023, prove demand. They don't prove the camera layer is
    open.
  - That's why we start in maintenance, where the work moves and the fixed-camera tools don't fit.
  - Our bet is narrower: a first-person engine that tracks a procedure compiled from existing instructions and asks
    for a better view when it can't tell. That is measured on cooking video only, and not against these products.
  - Full table: [`COMPETITORS.md`](COMPETITORS.md). Positioning against Viture and NVIDIA:
    [`POSITIONING.md`](POSITIONING.md).
- **"Your mistake detection is weak."** Yes, 4 of 17 alerts were strictly correct. All 4 were order errors, which
  you can only see if you know where the person is in the task. So better tracking and in-vertical data should
  mean more catches. Phase 1 leads with step verification and coaching, and mistake alerts only fire at high
  precision.
- **"Why would robot companies buy from you?"** They already buy raw footage. Ours comes plan-aligned,
  success-labeled and mistake-labeled, from skilled work. If they won't buy, the data still powers our own models.
- **"Will technicians accept a camera? Will customers share data?"**
  - Coaching is for the worker, and routine checks move on-device in Phase 3.
  - Data rights are in the contract with a discount for sharing. Customers who don't share get a model trained only
    on their own data.
- **"You're one person."** That's what the grant is for: picking and validating the beachhead with real pilots.
  The first hires are a forward-deployed engineer for pilots and an ML engineer for the in-house models.

## Exit paths and comparables
| Path | Comparable | What it shows |
|---|---|---|
| System of record for physical work (IPO-scale) | Samsara: $2.125B ARR, ~$24B market cap (Oct 2026) [M1] | Software for physical operations can be a large public company |
| Physical-AI data and evaluation | Scale AI: valued at more than $29B in Meta's 2025 deal [M2] | Data infrastructure for a new AI wave becomes strategic |
| Robot intelligence | Figure: $39B post-money (Sept 2025) [M4]; Physical Intelligence: $5.6B (Nov 2025) [M5]; Skild AI: more than $14B (Jan 2026) [M6] | Investors are paying for the robot brain. Its inputs (data, rewards) are what we sell |
| Strategic acquisition | Glasses platforms: Meta bought Limitless [M3], Apple bought Drishti's assets [D8]. Industrial software: Schneider–PTC ($22.6B), IFS–Poka, STG–Parsable [D7]. Robot companies | Natural buyers at every phase, and the category is already consolidating |

## Vision edition of CLAIMS: what to say about all this
- **Safe:** "We plan to…", "Our leading hypothesis for the beachhead is…", plus the cited market facts above, with
  the source and date.
- **Don't say:**
  - "We have customers or pilots."
  - "Robot companies want our data." We haven't talked to any yet.
  - Any dollar value for our data.
  - "Praxis works on maintenance or assembly." Every metric is from cooking.
  - "Praxis runs on glasses."

## Sources
All were checked 2026-10-17. Company claims are marked (co.).

**Glasses**
- [G1] EssilorLuxottica Q4/FY2025 results, Feb 2026: https://www.biospace.com/press-releases/essilorluxottica-q4-fy-2025-results-revenue-growing-18-4-in-q4-and-11-2-in-the-fy-adj-operating-margin-at-16-0-in-the-fy
- [G2] Omdia, Mar 2026: https://omdia.tech.informa.com/pr/2026/mar/global-ai-glasses-shipments-reach-8point7-million-units-with-mainland-china-emerging-as-the-fastest-growing-market
- [G3] IDC, Jun 2026: https://www.idc.com/resource-center/blog/smart-glasses-surge-the-xr-market-is-rewriting-its-own-rules/
- [G4] Meta DAT changelog and FAQ: https://github.com/facebook/meta-wearables-dat-android/blob/main/CHANGELOG.md · https://developers.meta.com/wearables/faq/ (see also [`GLASSES.md`](GLASSES.md))
- [G5] 9to5Google, Oct 2026: https://9to5google.com/2026/10/01/samsung-android-xr-glasses-release-date-report/
- [G6] Road to VR on the Bloomberg report, Jul 2026: https://roadtovr.com/apples-smart-glasses-unveil-wwdc-2027-release-date/

**Inference cost**
- [C1] a16z, "LLMflation", Nov 2024: https://a16z.com/llmflation-llm-inference-cost/
- [C2] Epoch AI, Mar 2025: https://epoch.ai/data-insights/llm-inference-price-trends

**Robotics**
- [R1] Figure, Project Go-Big (co.), Sept 2025: https://www.figure.ai/news/project-go-big
- [R2] Figure, Introducing Index (co.), Aug 2026: https://www.figure.ai/news/introducing-index
- [R3] Figure, Helix 2.5 (co.), Sept 2026: https://www.figure.ai/news/helix-2-5-zero-shot-30-home-generalization
- [R4] Physical Intelligence, Dec 2025: https://www.pi.website/research/human_to_robot
- [R5] NVIDIA et al., EgoScale, Feb 2026: https://arxiv.org/abs/2602.16710
- [R6] Business Insider, via Yahoo, Aug 2025: https://finance.yahoo.com/news/tesla-shifted-optimus-training-strategy-092502233.html
- [R7] MIT Technology Review, Apr 2026: https://www.technologyreview.com/2026/04/01/1134863/humanoid-data-training-gig-economy-2026-breakthrough-technology/
- [R8] TechCrunch, DoorDash Tasks, Mar 2026: https://techcrunch.com/2026/03/19/doordash-launches-a-new-tasks-app-that-pays-couriers-to-submit-videos-to-train-ai/
- [R9] Scale AI (co.), Sept 2025: https://scale.com/blog/physical-ai
- [R10] Dealroom, Mecka AI, Oct 2026: https://dealroom.co/news/160699-mecka-raises-60m-series-b-to-turn-human-motion-into-robot-training-data/
- [R11] Google DeepMind, Gemini Robotics-ER 1.6, Apr 2026: https://deepmind.google/blog/gemini-robotics-er-1-6
- [R12] Physical Intelligence, π\*0.6, Nov 2025: https://arxiv.org/abs/2511.14759
- [R13] RoboReward, Jan 2026: https://arxiv.org/abs/2601.00675 · GVL, ICLR 2025: https://arxiv.org/abs/2411.04549
- [R14] ABC News, Sept 2026: https://www.abc.net.au/news/2026-09-20/egocentric-training-gig-workers-helping-robots-learn-tasks/107135216
- [R15] TechCrunch, Human Archive, May 2026: https://techcrunch.com/2026/05/26/human-archive-taps-into-indias-services-startups-to-collect-data-for-physical-ai/
- [R16] heise, Nov 2025: https://heise.de/-11085687 · Interesting Engineering: https://interestingengineering.com/ai-robotics/figure-humanoid-robots-retires-bmw
- [R17] GXO investor release, Jun 27, 2024: https://investors.gxo.com/news-releases/news-release-details/gxo-signs-industry-first-multi-year-agreement-agility-robotics

**Beachhead demand**
- [D1] BLS JOLTS, manufacturing separations (tables 19–20): https://www.bls.gov/news.release/jolts.t20.htm
- [D2] Manufacturing Institute / Deloitte, Apr 2024: https://themanufacturinginstitute.org/manufacturers-need-as-many-as-3-8-million-new-employees-by-2033/
- [D3] Tulip Series D, Jan 2026: https://www.calcalistech.com/ctechnews/article/hjuzln2rzl · pricing: https://tulip.co/plans/
- [D4] Augmentir (co.), Mar 2025: https://www.prnewswire.com/news-releases/augmentir-expands-amidst-rapid-growth-announces-new-product-updates-for-industrial-frontline-operations-302398383.html
- [D5] Squint Series B (co.), Aug 2025: https://www.prnewswire.com/news-releases/squint-raises-40m-series-b-to-expand-agentic-manufacturing-and-accelerate-human-potential-with-ai-302527083.html
- [D6] Verdantix, Dec 2023: https://www.verdantix.com/insights/blogs/connected-worker-solutions-market-to-reach-3.24-billion-dollars-by-2028-overcoming-initial-slow-growth
- [D7] IFS–Poka: https://reliabilityweb.com/ifs-acquires-poka · STG–Parsable: https://stg.com/news/cai-software-llc-acquires-parsable-inc-a-leading-connected-worker-platform-for-manufacturers/ · L2L–SwipeGuide: https://www.l2l.com/swipeguide · Flatirons–Scope AR: https://www.flatironssolutions.com/flatirons-solutions-acquires-scope-ar-to-create-an-ai-powered-end-to-end-content-to-execution-platform/ · Schneider–PTC, Oct 2026: https://www.bostonglobe.com/2026/10/05/business/schneider-electric-ptc/
- [D8] MLex, Apple–Drishti, Sept 2024: https://www.mlex.com/mlex/articles/2118053/apple-reports-acquisition-of-drishti-assets-staff-to-eu-regulators
- [D9] Microsoft lifecycle notice: https://learn.microsoft.com/en-us/lifecycle/announcements/dynamics-365-guides-remote-assist-end-of-support · HoloLens release notes: https://learn.microsoft.com/en-us/hololens/hololens-release-notes
- [D10] PTC, Vuforia Chalk end of service: https://community.ptc.com/t5/Vuforia-Chalk/Vuforia-Chalk-end-of-service-notice/td-p/972878
- [D11] EO 14307, Jun 2025: https://www.govinfo.gov/content/pkg/DCPD-202500670/html/DCPD-202500670.htm
- [D12] Breaking Defense, Nov 2025: https://breakingdefense.com/2025/11/service-wants-to-buy-one-million-drones-over-next-2-to-3-years-army-secretary/
- [D13] DefenseScoop, Dec 2025: https://defensescoop.com/2025/12/02/hegseth-drone-dominance-program-ddp-gauntlets-website-rfi/
- [D14] Janes, Sept 2026: https://www.janes.com/defence-intelligence-insights/defence-news/air/us-armys-skyfoundry-suas-initiative-selects-magnet-supplier-for-motors
- [D15] Frontdoor app pricing: https://www.localogy.com/2023/05/frontdoor-launches-remote-home-services-app/ · https://www.silicon.co.uk/press-release/gift-a-frontdoor-unlimited-membership-for-25-and-get-another-one-for-just-1
- [D16] Limble State of Maintenance (vendor survey, 686 respondents), Oct 2026: https://limble.com/news/state-of-maintenance-report
- [D17] Boeing, Jul 2026: https://boeing.mediaroom.com/2026-07-17-Boeing-Forecasts-4-9-Trillion-Commercial-Aviation-Support-and-Services-Market-and-Demand-for-more-than-2-4-Million-New-Aviation-Personnel-Over-20-Years
- [D18] XOi / KKR, Feb 2025: https://www.bassberry.com/experience/xoi-funding-round-from-kkr/
- [D19] Autodesk to acquire MaintainX, May 28, 2026: https://www.streetinsider.com/PRNewswire/Autodesk+to+acquire+MaintainX%2C+advancing+unified+platform+in+operations/26566203.html · SiliconANGLE: https://siliconangle.com/2026/05/28/autodesk-acquire-maintainx-3-6-billion-push-operations/
- [D20] BLS Occupational Outlook, industrial machinery mechanics, maintenance workers and millwrights (2024–34): https://www.bls.gov/ooh/installation-maintenance-and-repair/industrial-machinery-mechanics-and-maintenance-workers-and-millwrights.htm
- [D21] BLS Occupational Outlook, HVAC mechanics and installers: https://www.bls.gov/ooh/installation-maintenance-and-repair/heating-air-conditioning-and-refrigeration-mechanics-and-installers.htm

**Competitors** (checked 2026-10-17; full table and more sources in [`COMPETITORS.md`](COMPETITORS.md))
- [K1] Retrocausal, how it works: https://retrocausal.ai/how-it-works/ · homepage: https://retrocausal.ai
- [K2] Tulip AI Composer, Apr 2025: https://tulip.co/press/ai-composer-announcement/
- [K3] Augmentir Procedure Studio: https://www.augmentir.ai/product/augie-procedure-studio · video-to-procedure release, Mar 2025: https://www.prnewswire.com/news-releases/augmentir-expands-amidst-rapid-growth-announces-new-product-updates-for-industrial-frontline-operations-302398383.html
- [K4] Squint platform: https://www.squint.ai/platform
- [K5] Tulip Factory Playback, release 6 Oct 2026: https://tulip.co/press/tulip-brings-ai-to-the-factory-floor-at-operations-calling-2026/ · status ("Now in customer testing"): https://keynote-2026.tulip.co/
- [K6] Strivr Frontline Intelligence FAQ: https://www.strivr.com/faqs · platform: https://www.strivr.com/platform · independent review, 13 Jul 2026: https://www.uctoday.com/strivr-frontline-intelligence-immersive-workplace-review
- [K7] Viture Helix with NVIDIA XR AI, 16 Jun 2026: https://www.prnewswire.com/news-releases/viture-unveils-helix-the-first-ai-safety-glasses-built-on-nvidias-xr-ai-solution-at-awe-2026-302802005.html
- [K8] Invisible AI, how it works: https://www.invisible.ai/how-it-works/ · quality: https://www.invisible.ai/quality/
- [K9] Arkite: https://arkite.com/ · Spot AI, SOP adherence: https://www.spot.ai/blog/sop-adherence-monitoring-ensuring-consistency-across-all-production-shifts
- [K10] Tulip Vision docs: https://support.tulip.co/docs/vision · Augmentir AI step verification: https://www.augmentir.ai/product/augie-generative-ai-suite · Squint quality and scrap: https://www.squint.ai/solutions/quality-scrap

**Market and comparables**
- [M1] Samsara Q2 FY27 results, Sept 2026: https://secure.businesswire.com/news/home/20260903120692/en/Samsara-Reports-Second-Quarter-Fiscal-Year-2027-Financial-Results · market cap: https://www.investing.com/equities/samsara
- [M2] Scale AI (co.), Jun 2025: https://scale.com/blog/scale-ai-announces-next-phase-of-company-evolution
- [M3] Meta acquires Limitless, Dec 2025: https://www.investing.com/news/stock-market-news/meta-acquiresaiwearables-startup-limitless-4394080
- [M4] Figure Series C (co.), Sept 2025: https://www.figure.ai/news/series-c
- [M5] Bloomberg Law, Nov 2025: https://news.bloomberglaw.com/private-equity/robotics-startup-physical-intelligence-valued-at-5-6-billion
- [M6] BusinessWire, Skild AI, Jan 2026: https://www.businesswire.com/news/home/20260114335623/en/Skild-AI-Raises-$1.4B-Now-Valued-Over-$14B
