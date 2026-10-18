# Competitors: what each one verifies by camera today

> **Checked 2026-10-17, from public pages only.** I did not run or demo any of these products. Every statement is what
> the vendor (or a named third party) says publicly, with a link in [Sources](#sources). "Not documented" means I
> looked and the public pages don't say, which is **not** proof the feature is missing. Vendor claims are vendor
> claims: none of these companies publishes accuracy or false-alarm numbers for camera checks. Sources marked † could
> not be downloaded raw (bot protection or a JS-rendered page), so I read them through a summarizing fetch tool; check
> those by eye before quoting them.

## Bottom line

1. **"Compiles existing SOPs" is not a differentiator.** Tulip (AI Composer), Augmentir (Procedure Studio) and Squint
   already turn PDFs, Word files and video into procedures [TU5][AU3][SQ1].
2. **Camera-based step verification already ships on fixed cameras.** Retrocausal, Arkite, Invisible AI, Spot AI and
   PTC's Vuforia Step Check all do some version of it [RC1][AR1][IN3][SP2][PT1]. Retrocausal tracks a whole ordered
   procedure live [RC1].
3. **First-person is not empty either.** Strivr (early access) and Viture + NVIDIA (ships Q1 2027) sell smart glasses
   that watch the work through the wearer's eyes and coach against SOPs [ST1][ST5][VI1].
4. **The incumbents are moving toward us.** Tulip's Factory Playback (vision-language models on camera streams,
   "whether a procedure was followed") is in customer testing as of Oct 2026 [TU6][TU7].
5. **What I found nobody documenting:** asking the worker for a better view when the camera can't tell. That is
   narrow, and it is unproven on assembly (see [Where Praxis actually differs](#where-praxis-actually-differs-and-where-it-doesnt)).

## Comparison

Cell refs like [RC1] point to the [Sources](#sources). "Station camera" means a camera added to a workstation; none of
the fixed-camera vendors describe a worn camera.

| Company (status) | Camera | Procedure source: compiled or authored? | Whole-procedure state or single steps? | Live mistake detection | Asks for a better view | Pricing | Named customers |
|---|---|---|---|---|---|---|---|
| **Tulip Vision** (shipping) | Station cameras: USB/IP RGB, plus Intel RealSense depth for the Change Detector. No official mounting guidance [TU2][TU3][TU4] | Authored in Tulip's no-code apps; detectors set up per app [TU1]. AI Composer (Apr 2025) turns PDF docs into apps, but the announcement doesn't mention vision checks [TU5] | Detectors (change, jig, color, barcode, OCR) fire events inside an app. No whole-procedure visual state documented [TU2] | Narrow: kitting "highlight incorrect or missing items"; anomaly detection with a custom trained model [TU1]. No general "step done wrong" detection documented | Not documented | Apps: $100/mo (Essentials) or $250/mo (Professional) per interface, annual, 10 minimum. Computer Vision is listed as an add-on with no price [TU4]. Docs say both "Professional and above" and "all accounts" [TU2] | Laerdal (Vision case study) [TU8] |
| **Tulip Factory Playback** (customer testing) | "Local edge server camera streams"; placement not stated [TU6] | Not described | Not described | "Human activity detection … whether a procedure was followed, and whether a part was assembled to spec", using vision-language models. Introduced with NVIDIA in 2025 [TU6]. Status "Now in customer testing" [TU7] | Not documented | Not published | None named |
| **Retrocausal Assembly Copilot** (shipping) | Fixed: "mount a camera … on the workstation". Success depends on "positioning the camera such that it is able to observe all the steps", with parts picked from fixed locations [RC1][RC2] | Authored: SOP typed in step by step, or fetched from an MES. Then record cycles, label one cycle, train in the cloud ("a couple hours of user's time") [RC1] | **Whole procedure.** Tracks individual steps; steps can be ordered, mandatory or optional; end-states can confirm a step achieved its goal [RC1][RC2] | Yes (vendor claim): real-time alerts on missed mandatory steps; light towers, projectors, line stop via OPC UA [RC1][RC2] | Not documented. Occlusion handling not addressed in sources | No price list. An AWS Marketplace listing shows a 12-month "$150,000" private-offer price, units "typically" = stations, 25-station minimum on-prem [RC4] | No named *Assembly Copilot* customer: its 13 case studies are anonymous except 3M, which is for Kaizen Copilot (time studies) [RC3]. Homepage testimonials: Alliance Laundry Systems (about Pathfinder analytics), Honda Innovations (about a proof of concept), Siemens Digital Industries Software [RC2] |
| **Augmentir** (shipping) † | No fixed or worn camera feed documented. "Operator-captured photos or video frames" [AU2] | **Compiled:** bulk import of PDFs, Word, spreadsheets, SharePoint sync; video-to-procedure since Mar 2025 [AU3][AU4] | Single steps: "AI step verification & photo verification" compares a photo or frame to "expected state" [AU2]. No whole-procedure tracking documented | "Instant feedback" on a submitted photo [AU2]. Not continuous watching, as far as the page says | Not documented | Not published [AU1]. One third-party directory lists $30/user/month; unverified [AU5] | Colgate-Palmolive, Mondelēz, Duracell, Hitachi Energy, Graphic Packaging, Sargento, Hunter Industries, Müller Group, Armstrong World Industries (company release; not specific to the vision feature) [AU4] |
| **Squint** (shipping) | **No camera step verification documented.** Verification = operator-entered photos, readings and sign-offs; skipped steps block completion [SQ2]. Video is used to *create* instructions and time studies [SQ1][SQ3] | **Compiled:** upload SOPs, schematics, OEM manuals, handwritten notes; or record an operator and get instructions [SQ1] | Workflow logic driven by what the operator reports, not vision [SQ2] | No | n/a | Not published ("Book a demo") [SQ1] | None named on its pages; release uses "Fortune 50 / Global Fortune 500" [SQ4] |
| **Invisible AI** (shipping) | Fixed edge devices (Intel RealSense 3D camera + NVIDIA chip); several devices calibrate into a 3D twin to handle occlusion. Placement not stated [IN2] | Authored by example: "<5 examples", "Gold Standards", no labeling [IN2][IN3]. Studio (early access, approved users) turns uploaded video into standard work [IN5]† | Cycle-level. Flags outlier cycles and "missed steps" [IN3]. The homepage sells cycle-time analytics for industrial engineers [IN1] | Lists "Auto-Detect: micro-stops, missed steps, downtime" [IN3] without saying real-time. A 2020 interview describes a live "we think you missed step 8" prompt [IN4] | No: solves occlusion by adding devices [IN2] | Not published [IN1] | Homepage logos: Mercedes-Benz, Ford, Toyota, BMW, GM, Nissan [IN1]. Toyota named as an early partner in 2020 [IN4] |
| **Instrumental** (shipping) † | Station cameras that image the **product units** on electronics lines; works with existing AOI and cobot cameras [IM1] | n/a (inspection models trained on production datasets) [IM2] | n/a. Not worker steps | "Intercepts defects before test": product defects, not procedure errors [IM1] | Not documented | Not published [IM1] | NVIDIA, Meta, Toast (case studies) [IM1] |
| **Arkite** (shipping) | Workstation "embedded smart-sensor" plus projected instructions; a vision add-on checks small screws and bolts (>0.5 cm) are present and oriented right. Mounting not stated [AR1] | Not stated | Validates "the correctness of execution" per operation [AR1] | "Immediate feedback" during assembly [AR1] | Not documented | Not published [AR1] | Homepage logos "already using our platform": Ford, Bosch, Hilti, Liebherr, Schindler, Celestica, Cisco, others [AR1] |
| **Spot AI** (shipping) | Any existing IP camera (CCTV style) [SP1][SP2] | "Teach the system a good process with video and the written SOP" [SP2] | Benchmarks each run, flags drift "on timing or sequence" [SP2] | Homepage: "flagging deviations the instant they appear" [SP1]. Its SOP article describes scorecards "soon after each run" [SP2] | Not documented. Covers "every run the camera can see" [SP2] | Not published [SP1] | Duramatic Manufacturing, Allied Stone, Wayne Transports (testimonials) [SP1] |
| **PTC Vuforia Step Check** (shipping) | Not stated in the doc; runs inside Vuforia Vantage [PT1] | Authored: author enables it per step, reviews collected sample images, trains, tests, activates, republishes [PT1] | Per step ("enabled for at least one step") [PT1] | Pass/fail shown to the worker [PT1] | Not documented | Not checked | Not checked |
| **Strivr Frontline Intelligence** (early access) | **First-person smart glasses:** Vuzix, Ray-Ban Meta, XREAL, RealWear; also phones and tablets [ST3]. "Smart glasses allow Strivr AI to see what your workers see" [ST1] | Strivr's data-science team captures images and video of your procedures plus SOPs, guides and manuals, then trains a per-customer VLM [ST1][ST3] | Claims "workflow progress" and "out-of-sequence" detection; how state is kept isn't described [ST2] | Claims real-time detection and voice correction [ST2][ST4]. Independent review (13 Jul 2026): early access, no accuracy benchmarks, no first-party outcome data [ST5] | Not documented | Not published [ST1] | None for this product. One anonymous "Fortune 1000 Manufacturing Company (Design Partner)" [ST1]. The big logos on its blog are VR-training customers [ST5] |
| **Viture Helix + NVIDIA XR AI** (ships Q1 2027) | **First-person:** 12MP camera in safety glasses, streams to a multimodal AI [VI1] | "Coach operators on standard operating procedures in real time"; how SOPs get in isn't described [VI1] | Not documented | Not documented ("coaching, compliance") [VI1] | Not documented | Glasses from $600; enterprise pilots invite-only; AI service price not stated [VI1] | None named; the release credits research-lab collaborators at Stanford and Princeton [VI1] |

**Also looked at, not in the table.** Mentra sells worker glasses with a head camera, audio guidance and photo
documentation, and documents no step verification, prices or customers [MT1]. Drishti, which did camera action
recognition on assembly lines, is reported to have been absorbed by Apple (assets and staff) [DR1]. Seen in search
results but not verified from a primary page, so I excluded them: LumiBot (a fixed overhead camera on the bench,
per an aggregator) [LB1].

## Where Praxis actually differs, and where it doesn't

### Where it doesn't

- **Compiling existing instructions.** Tulip, Augmentir and Squint all do it today, and Strivr and Spot AI learn
  from the written SOP too [TU5][AU3][SQ1][ST3][SP2]. We can't sell this as ours.
- **Tracking a whole procedure.** Retrocausal does it: ordered steps, optional steps, end-states [RC1]. Strivr and
  Spot AI claim sequence checks [ST2][SP2]. Our 54% vs 48% result beats *our own* baseline (a frontier model called
  every 5 s with no state), not any of these products. We haven't compared against any of them.
- **Catching mistakes live.** We are behind. Our own alerts named a real annotated error 4 times in 17
  (`results/l6/`). Retrocausal, Arkite and Invisible AI sell live mistake alerts [RC2][AR1][IN3]. None publishes
  accuracy, so we can't say they're better, but we can't say we're competitive either.
- **"Incumbents can't copy this without undercutting their authoring revenue."** This was in `VISION.md` and it's
  wrong for document compiling: Tulip, Augmentir and Squint already ship it. On checking by camera, Tulip is adding it
  (Factory Playback, vision-language models, customer testing) [TU6][TU7], and PTC and Augmentir already have
  per-step image checks [PT1][AU2].
- **"Glasses are our edge."** Strivr already supports Ray-Ban Meta glasses [ST3], and Viture + NVIDIA ship in Q1 2027
  [VI1]. Both are early and unproven, but they are there.
- **"Fixed-camera analytics must be trained per station, so they can't handle change."** True that most need a
  recorded example, but the effort is small: Retrocausal says "a couple hours of user's time" [RC1], Invisible AI
  says fewer than five examples and no labeling [IN2]. Instrumental isn't in this group at all: it inspects
  products, not worker steps [IM1].

### Where it does

All three differences below are **design differences, not measured wins**. Every Praxis metric is from cooking
video (`docs/CLAIMS.md`).

1. **First-person view, against the established vendors.** Tulip, Retrocausal, Invisible AI, Arkite and Spot AI
   all describe cameras added to a station or already on the site, and none documents a worn camera
   [TU4][RC1][IN2][AR1][SP2]. For small-parts work, Retrocausal says success depends on positioning the camera to see
   every tracked step and on parts being picked from fixed locations [RC2]. My inference: that is a constraint for
   high-mix work. This argument does **not** hold against Strivr or Viture, who are also first-person.
2. **Asking for a better view when unsure.** No company in the table documents anything like this. Invisible AI
   handles occlusion by adding more devices [IN2]. In our tests on degraded video, Praxis asked for a better view on
   77–98% of checks and was never confidently wrong (`results/l5/visual_uncertainty.json`; the views were degraded
   synthetically with blur, occlusion and cropping). Caveat: this is absence of documentation, not proof, and we
   haven't tested their products on bad views.
3. **Setup from the SOP, with no footage of that procedure.** This is narrower than "compiles SOPs". The
   document-compilers (Tulip, Augmentir, Squint) don't offer continuous camera checking: they check with event
   detectors, operator photos, or nothing [TU2][AU2][SQ2]. The vendors that do check continuously each document a
   per-procedure capture or training step: Retrocausal (record, label, train) [RC1], Invisible AI (examples) [IN2],
   Spot AI (a recording of a good run) [SP2], Vuforia (collected images, trained per step) [PT1], Strivr (captured
   video, per-customer VLM) [ST1]. Praxis's measured numbers for zero-footage setup are modest: 36% step tracking
   from drafted plans on unseen recipes, 73% recipe recognition (`results/open_set/`, `results/runs/fused.json`). And a
   buyer who can set up Retrocausal in a couple of hours may not pay much for "no setup".

### What we can safely say

> "Camera-based step checking already exists on fixed cameras. Strivr and Viture are bringing it to glasses. We're
> building a first-person engine that tracks a procedure compiled from existing instructions, and asks for a better
> view when it can't tell. We've measured that on cooking video, not yet on assembly, and we haven't compared against
> these products."

Don't say: "nobody verifies by camera", "nobody compiles from existing SOPs", "incumbents can't copy this", or
"we're the only first-person system".

## What I couldn't verify

- **Accuracy of any competitor's camera checks.** None publishes it. Strivr's independent review says the same [ST5].
- **Whether Retrocausal, Spot AI or Strivr handle occlusion or ask for a better view.** The pages don't say.
- **Whether Augmentir's photo check can run on a live feed.** The page says "operator-captured" input only [AU2].
- **Tulip Factory Playback:** camera placement, what the activity detection really does, release date, price. The
  Oct 2026 release gives the claim; the keynote page gives the status [TU6][TU7].
- **Prices for most of them.** Only Tulip (apps), Viture (glasses) and one Retrocausal marketplace listing publish a
  number. The Augmentir $30 figure is third-party and unverified [AU5].
- **Squint's named customers**, and **Vuforia Step Check's price and customers.** Not found / not checked.
- **Strivr's status beyond early access**, and whether it works on Ray-Ban Meta glasses in practice.

## Sources

All checked 2026-10-17. † = read through a summarizing fetch tool only.

**Tulip**
- [TU1] Tulip Vision: https://tulip.co/platform/vision/
- [TU2] Vision docs: https://support.tulip.co/docs/vision
- [TU3] Hardware recommendations for Vision: https://support.tulip.co/docs/hardware-recommendations-for-vision
- [TU4] Plans and pricing: https://tulip.co/plans/
- [TU5] AI Composer, Apr 2025: https://tulip.co/press/ai-composer-announcement/
- [TU6] Operations Calling 2026 release, 6 Oct 2026: https://tulip.co/press/tulip-brings-ai-to-the-factory-floor-at-operations-calling-2026/
- [TU7] Operations Calling 2026 keynote page (status labels): https://keynote-2026.tulip.co/
- [TU8] Tulip and AWS success stories (Laerdal): https://tulip.co/partners/aws/

**Retrocausal**
- [RC1] How it works: https://retrocausal.ai/how-it-works/
- [RC2] Homepage (Assembly Copilot, testimonials): https://retrocausal.ai
- [RC3] Case studies: https://retrocausal.ai/case-studies/
- [RC4] AWS Marketplace listing: https://aws.amazon.com/marketplace/pp/prodview-lqeplvuzdnk7i †

**Augmentir**
- [AU1] Homepage: https://www.augmentir.ai/ †
- [AU2] Gen AI suite (AI Step Verification & Photo Verification): https://www.augmentir.ai/product/augie-generative-ai-suite †
- [AU3] Procedure Studio: https://www.augmentir.ai/product/augie-procedure-studio †
- [AU4] Press release, 11 Mar 2025: https://www.prnewswire.com/news-releases/augmentir-expands-amidst-rapid-growth-announces-new-product-updates-for-industrial-frontline-operations-302398383.html †
- [AU5] Third-party directory (unverified price): https://elearningindustry.com/directory/elearning-software/augmentir/pricing · G2 says no price provided: https://www.g2.com/products/augmentir/pricing †

**Squint**
- [SQ1] Platform: https://www.squint.ai/platform
- [SQ2] Quality and scrap: https://www.squint.ai/solutions/quality-scrap
- [SQ3] Industrial agents: https://www.squint.ai/industrial-ai
- [SQ4] Series B release, Aug 2025 (company claims): https://www.prnewswire.com/news-releases/squint-raises-40m-series-b-to-expand-agentic-manufacturing-and-accelerate-human-potential-with-ai-302527083.html †

**Invisible AI**
- [IN1] Homepage: https://www.invisible.ai/
- [IN2] How it works: https://www.invisible.ai/how-it-works/
- [IN3] Quality: https://www.invisible.ai/quality/
- [IN4] TechCrunch, May 2020: https://techcrunch.com/2020/05/06/invisible-ai-uses-computer-vision-to-help-but-hopefully-not-nag-assembly-line-workers/ †
- [IN5] Studio: https://studio.invisible.ai †

**Instrumental**
- [IM1] Homepage: https://instrumental.com †
- [IM2] Partners: https://instrumental.com/partners/ †

**Others**
- [AR1] Arkite: https://arkite.com/
- [SP1] Spot AI, AI Operations Assistant: https://www.spot.ai/ai-operations-assistant
- [SP2] Spot AI, SOP adherence monitoring: https://www.spot.ai/blog/sop-adherence-monitoring-ensuring-consistency-across-all-production-shifts
- [PT1] PTC Vuforia Step Check: https://support.ptc.com/help/vuforia/editor/en/vuforia_editor/step_check.html
- [ST1] Strivr homepage: https://www.strivr.com
- [ST2] Strivr platform: https://www.strivr.com/platform
- [ST3] Strivr FAQ: https://www.strivr.com/faqs
- [ST4] Strivr blog, Jul 2026: https://www.strivr.com/blog/why-smart-glasses-matter-for-frontline-intelligence
- [ST5] UC Today independent review, 13 Jul 2026: https://www.uctoday.com/strivr-frontline-intelligence-immersive-workplace-review †
- [VI1] Viture Helix release, 16 Jun 2026: https://www.prnewswire.com/news-releases/viture-unveils-helix-the-first-ai-safety-glasses-built-on-nvidias-xr-ai-solution-at-awe-2026-302802005.html
- [MT1] Mentra: https://mentraglass.com/ †
- [DR1] MLex, Apple–Drishti (date as cited in `VISION.md` [D8]; not re-checked): https://www.mlex.com/mlex/articles/2118053/apple-reports-acquisition-of-drishti-assets-staff-to-eu-regulators
- [LB1] LumiBot (aggregator, unverified): https://yespress.io/lumibot-yc-w22
