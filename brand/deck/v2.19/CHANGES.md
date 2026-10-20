# Deck v2.19: changes since v2.18

A redesign from Monish's review on 2026-10-20. It keeps v2.18's story, brings back the richer visuals from earlier
versions, and rewrites every title the way a founder would say it. The core is now 14 slides (about 10 minutes),
followed by the same 17-slide Q&A appendix.

## Type

There's one family now: Archivo Regular + SemiBold, used for headlines and big numbers too. The wide Archivo
Expanded headline face is gone. Section labels are small, sentence-case and have no letter-spacing ("Problem",
"Built so far"). The appendix eyebrows read "Appendix A1". Source lines stay in the speaker notes.

## Core

| # | Title | Visual |
|---|---|---|
| 1 | Instructions that can finally see how you're doing | cover photo + HUD; subhead: software for smart glasses, from a company's existing manuals |
| 2 | Training new technicians is expensive | half-bleed graphite photo with the orange test lead in color; $10–15k hero, ~255k, 9–14 months as one line, HSPA quote |
| 3 | Praxis coaches the job through smart glasses | the HV deck's three HUD tiles (next step / checks the work / catches a mistake) under a one-line flow |
| 4 | This is already a working software system | **new**: backend screenshots (documents, compiled + approved procedure) and the live app's engineer view; exact build status of each part |
| 5 | We already run a real repair procedure live | live video; 16:40 / None / $0.17 |
| 6 | The system tracks the job instead of querying a model constantly | rich diagram again: compiler, perception, event detector, task recognizer, semi-Markov tracker, policy, coach; local student → fast verifier → frontier escalation → calibration; ours / trained / open / rented |
| 7 | Same frontier model, better system | 2,817 → 351 and $0.085 → $0.018 bars; ~$1 per coached hour; better tracking; "asks for another view" card |
| 8 | Smart-glasses hardware is finally open to software | shipments bars + platform timeline; "Now we build the software that runs on them" |
| 9 | We don't need to win the glasses hardware race | devices → thin adapters → Praxis layer (six parts); other approaches, Viture named as closest, "we want Praxis to run on Helix too" |
| 10 | Maintenance is our first market | wedge equation, ROI panel, horizontal expansion path with equal-size stations (no TAM/SAM/SOM, no nested squares) |
| 11 | We sell to maintenance managers, one paid pilot at a time | 5-stage customer path, pricing rules, trade schools as a second path with the fiber-optic school's quote. No email counts |
| 12 | I've built real-time vision systems for the physical world, and I've helped grow startups | from the resume: LipTrac, OCTOPAS, robotics / Qurios, Claisen, Acely; Harvard; a dashed **[SCOPE — INSERT VERIFIED FACTS FROM MONISH]** placeholder |
| 13 | Coaching comes first. Our own models and skill records come next | the rising stepped path again, no ARR labels, "Later: physical AI" dashed |
| 14 | $10k gets us to the first paid pilot | fund bar + dark "By April" panel |

Removed from the core: "first signal", "second loop", "why it compounds", "the long game", "4 days / 130+ commits",
"70 emails / 2 replies", TAM/SAM/SOM labels and ARR labels on the roadmap.

## Appendix

The titles are now plain ("Benchmark results and method", "Glasses hardware and adapters", "Safety", "Risks", and so on).
The founder appendix uses the resume: IRO, FTC Coach / FTC Elo, awards, and both provisional patent numbers. Adapter
status is worded exactly: camera/upload path tested; Meta and Viture/NVIDIA adapters built, not device-tested;
Android XR planned.

## Assets

- `deck/assets/tiles/`: the three HUD tiles and their regions, copied from `deck-hv/assets` (`deck-hv/make_tiles.py`).
- `deck/assets/photos/problem-panel.jpg`: the Unsplash electrical-panel photo, graphite-toned, with only the
  orange probe left in color.
- `deck/assets/screens/backend-procedure-top.png`: the top 1000 px of the procedure screenshot.

## Open items from Monish

- SCOPE facts (placeholder on slide 12).
- The voice layer: this repo has spoken coaching (TTS); voice input isn't built per `docs/VOICE.md`.
- The Meta/Viture adapters: this repo only has a Meta stub.
- "7 years" of robotics vs. FTC 2022–26 on the resume.

## Follow-up the same day

- **Slide 4.** The Meta and Viture/NVIDIA adapters are on separate rows, both "coded, not device-tested".
- **Slide 13.** "Later" splits into two paths into physical AI: (A) build our own robot models on step-verified
  recordings customers opted in, (B) sell to physical-AI labs by licensing consented data and our step checker.
- **Slide 13, new dark panel: "What AI labs pay for human training data keeps climbing."**
  - Mercor's gross run-rate as bars: $0.76B in Dec 2025 (Sacra estimate), $1B around Feb 2026, $2B in Jun 2026
    (CEO, via Dealroom).
  - More than $100M a year spent by robotics companies on real-world data (Micro1's CEO, via MIT Technology Review).
  - More than $1B committed by Figure to data and compute.
  - The AI training-data market at $3.2B in 2025, forecast to reach $16.3B by 2033 (Grand View Research).
  - The "each stage starts only once…" line moved to the speaker notes.

## Second follow-up: design pass and a short demo cut

- **Disclaimers off the core slides.**
  - The "concept mock · stock photo" tag on the cover and the "Concept mocks on stock photos" line on slide 3 are
    gone.
  - So are the caption under the live video, the appendix pointer on the architecture slide, and "Example card
    (mockup)". The notes still say which visuals are mockups.
- **Slide 5.** The video is a new 15-second engineer-view cut of the same session
  (`renders/demo/praxis_repair_short_engineer.mp4`). It shows a step change, the 200 °C overshoot caught, and a moment
  it can't see the display and asks for a closer look. The 49-second cut stays in appendix A5.
- **Slide 7.** The mock view-request card is replaced by a real frame from the session at 4:25, with the clipped
  display highlighted. Next to it are the frontier model's logged request ("Look closely at the soldering station
  display, upper right."), then 77–98% vs. up to 73% as the benchmark.
- **Slide 9.** A stack diagram replaces the white, outlined boxes:
  - Praxis on top as a dark plate with six modules.
  - An orange adapter band in the middle, with one connector per device.
  - Device nameplates below (Meta, Google, Viture, future devices).
  - The other approaches as ruled rows on the right, with Viture marked as the closest competitor.
- **Slide 10.** The ROI panel is now a 40-hour unit chart: one orange hour out of a senior tech's week ≈ one seat.
- **Slide 11.** The trade-school card's box is gone; it's now a rule-topped column like the pricing one.
- **Slide 13.** The two physical-AI paths are drawn as a fork off the dashed "Later" tread instead of boxes.

## Third follow-up: economics, pricing and market framing

- **Core is 15 slides.** The market slide split into two: "Maintenance is where we start" (the wedge, why
  maintenance first, and an expansion path ending at broader technical onboarding) and a new "Praxis only has to
  shorten the ramp by a fraction to pay for itself".
- **The new economics slide.**
  - One new tech: $10–15k hire-and-ramp burden vs $1,200 Praxis vs ~$270 to serve (~77% margin, ~90% with the local
    model). Praxis pays for itself if it removes roughly 8–12% of the burden.
  - One org hiring 25 a year: $250–375k vs $30k.
  - The pilot measures the actual effect.
- **Deleted:** the 40-hour unit chart and $44/$46 line. $1.8B/$9.2B are now only in the appendix.
- **Pricing.** "Seat" is now "active-trainee license" in every slide and note. The glasses example is 10 licenses,
  3 concurrent people, about 3 pairs. Tulip is now described as ~$100/month Essentials and ~$250/month Professional
  per interface, an anchor and not proof.
- **Problem slide.** The $10–15k is now described as "including recruiting fees, onboarding time and lost
  productivity". 9–14 months is now attributed to a 2017 survey of 35 aviation repair stations.
- **Live slide.** The model cost now reads "≈$1 of model calls per coached hour, across our evaluation". This run's
  $0.17 (~$0.60/h) moved to appendix A5 and the notes.
- **Product slide.** The flow strip now has five one-line steps, sized to their text, on one baseline.
- **Other wording.**
  - The fiber-optic caption lost "about a one-lab test".
  - Every "Opus" now reads "Claude Opus 5.5" or "Opus 5.5".

## Fourth follow-up: market and economics merged, shareable copy

- **Core is 14 slides again.** Market and economics are now one slide, "Maintenance is where we start, and Praxis
  pays for itself". Top: the $306M equation and a short Start/Next/Then path. Middle: the per-tech bars. Bottom: one
  line on starting with small and mid-size teams (NAM: 98% of US manufacturers have fewer than 500 employees).
- **Team example.** The 25-hires-a-year example is gone; that's a ~250-tech org. It's now a 50-technician team with
  about 5 new hires a year (about 1 in 10 maintenance jobs opens yearly, per BLS): $50–75k burden vs $6k of Praxis.
- **Founder slide.** The SCOPE placeholder is removed.
- **Shareable copy.** `node build_deck.js --share` builds `deck/Praxis_SAH_Oct2026_no_appendix.pptx` and its PDF: core
  only, notes stripped to sources.

## Fifth follow-up: the view request is visible in the demo

- Slide 5's cut is now 17 s. In the third moment the HUD shows the verifiers' logged view requests as a card at
  their logged times: "Show me the soldering station display." (fast model, 4:25.2), then "Look closely at the
  soldering station display, upper right." (Claude Opus 5.5, 4:30.75). In the live session the policy logged these
  without showing a card, so the card is tagged "verifier request · text from the session log".
- Only that beat was re-rendered (`reel.py --cut short --view-cards --beat 2`) and spliced after the first 8.5 s.
