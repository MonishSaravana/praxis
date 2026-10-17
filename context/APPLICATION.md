# Praxis — S@H Grant Application (as submitted)

Startups @ Harvard non-dilutive grant (funded by Xfund), $5k+ for pre/early-revenue member startups.
Interview: **Tuesday, Oct 20, 2026**. An optional slide deck is allowed. Format otherwise unknown.

Applicant: Monish Saravana (solo; no team members listed). No website. Attachments: `Praxis Demo.mp4` + resume.

## One-liner
Praxis is an AI layer for smart glasses that watches you perform a physical task, keeps track of what you've done, catches mistakes, and gives personalized guidance until the task is complete.

Tagline: "Instructions that can finally see how you're doing." Descriptor: "AI guidance for the physical world."

## Submitted answers

**Two sentences.** Praxis is an AI co-pilot for the physical world: a software layer for consumer smart glasses that sees what a user sees, understands what they are doing, and guides them through unfamiliar physical tasks in real time. It tracks progress, catches mistakes, personalizes instructions, and actively asks the user to reveal more visual context when uncertain.

**Why you / why this.** AI has made online learning increasingly personalized because it can observe how someone performs on questions, projects, and benchmarks, then adapt its feedback. Physical learning remains largely one-way: a video, manual, or course explains what should happen without knowing what the learner is actually doing. Consumer smart glasses and multimodal models can finally close that loop. After seven years in competitive robotics, I learned how difficult it is to mentor someone without seeing exactly what they see. My research has also centered on extracting useful information from messy real-world visual data: I developed autonomous path-planning systems for oil-cleanup boats using aerial imagery and built LipTrac, a real-time lip-reading system trained on unstandardized video. I want to combine that experience in robotics and computer vision to build AI that continuously understands and responds to human actions in the physical world.

**Traction.** I've built the initial product interaction prototype and am building an evaluation pipeline around 48 real procedural videos spanning 8 categories and 192 labeled action states. The system is designed to maintain the user's current task state, generate context-specific guidance, detect deviations from expected progress, and request additional visual information when uncertain. The next step is benchmarking step recognition, mistake detection, and latency before testing the experience directly through consumer smart glasses.

**$10k.** ~$3,000 model/API + GPU experimentation; $2,500 consumer smart-glasses hardware + capture equipment; $2,000 collecting + evaluating real task demonstrations; $1,500 inference/storage infrastructure; $1,000 company formation + prototype expenses — to validate continuous task understanding and error detection.

**Six months.** Build a robust software layer for consumer smart glasses that can maintain task state over long procedures, detect mistakes with high precision, personalize feedback, and actively resolve visual uncertainty. Benchmark step-recognition accuracy, intervention precision, and end-to-end latency, then identify the initial task category where adaptive guidance creates the largest measurable improvement.

**Coolest thing.** LipTrac: a computer-vision system that reads lip movements in real time from ordinary video. Conv3D + Bi-GRU architecture, 60,000+ video frames, tested with 12 participants, provisional patent filed. The hard part was real people under changing lighting, camera angles, and uncontrolled conditions while preserving temporal context.

**Alternative project.** An embodied-AI data system that analyzes robot deployment failures and predicts which additional human demonstrations would most improve the robot's policy — testing whether failure-targeted data collection beats collecting more demonstrations at random.

## Product loop
observe → understand task state → instruct → verify → catch mistakes → ask for more visual info if uncertain → continue

Key differentiator: **active perception**: when the view is ambiguous, Praxis asks the user to move ("look down and to the right", "show me the underside") instead of guessing.

## Architecture thesis
instruction source (manual / tutorial / goal) → structured task graph → first-person video → object/action/state tracking → persistent task state → uncertainty + error detection → personalized intervention → verify → advance.

Latency answer: hierarchy, not every frame to a giant model. Cheap local perception (tracking, change detection) gates a larger multimodal model that only runs on keyframes/events for semantic reasoning, ambiguous state, and mistake diagnosis.

Generalization answer: Praxis doesn't hand-encode tasks; it compiles arbitrary instructional content into a task graph, then grounds it visually.

## Competition / moat
- Enterprise "guided worker" is validated: Augmentir, Scope AR, TaqTile. They require companies to author SOPs; Praxis is consumer-first and works from arbitrary tutorials/manuals/goals.
- Meta is the existential risk ("hey Meta, walk me through this"). Answer: the model is a component; the company is the task-state engine: persistent temporal state, verification, error detection, uncertainty handling, personalization, task graphs, and accumulated procedural data.

## Status at submission (what was and was not claimed)
Had: concept, product UX/story, concept-prototype demo video (labeled "Concept Prototype"), founder-fit story, architecture hypothesis, proposed eval pipeline and sizing, use of funds.
Did NOT have (and did not claim): customers, pilots, revenue, glasses integration, measured accuracy/latency, a production system, a team.
As of Oct 16, 2026: nothing new built since submission.

## Existing demo video (`~/Downloads/Praxis Demo.mp4`)
17.6s, 1280×720, AI-generated drone-assembly footage with baked-in HUD cards: Task recognized: Assemble drone → Step 3 of 7: Attach front-right propeller → Watching / Checking orientation → Step 4 of 7: Secure retaining nut → Step verified → "Something looks off: front-right propeller appears reversed, rotate 180°" → "I can't see the mounting point clearly. Look slightly down and to the right." → Got it → Alignment verified → "Praxis: AI guidance for the physical world." Watermarked "Concept Prototype."
Known flaws: garbled AI text in one card ("wake itnolellyou"), "Step verified" appears *before* the reversed-propeller warning (logic contradiction), step numbering jumps 3→4 mid-action, hands/props morph between shots.
