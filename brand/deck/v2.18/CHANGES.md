# Deck v2.18: changes since v2.17

A restructure for the 15-minute S@H interview: a 13-slide core (about 9 minutes) with one takeaway per slide, and a
17-slide Q&A appendix. The visual identity is unchanged (Aluminum, graphite, Torque Orange, Archivo, HUD photo slides).

## Core order

| # | Title | Was |
|---|---|---|
| 1 | Instructions that can finally see how you're doing | cover; new one-liner (software for smart glasses, from a company's own manuals) |
| 2 | Every new maintenance hire consumes scarce senior-technician time | Problem. $10–15k is the only hero; 255k is the scale; 9–14 months is a source note. The quote moved to slide 10 |
| 3 | Upload the manual. Praxis coaches the job through smart glasses | Product. LOAD / COACH / VERIFY now includes "ask for a better view instead of guessing" |
| 4 | Real repair footage, run through the live engine | Live slide, moved before the architecture. Spec plate: 16:40, never trained on this job, $0.17 |
| 5 | The frontier model is one swappable part. The tracking engine around it is ours. | Engine v0, cut to five blocks at readable sizes. The full diagram is appendix A4 |
| 6 | Same frontier model. Better system. | New. 8× fewer frontier calls (351 vs 2,817 Opus), 5× cheaper, step tracking better; abstains on degraded views |
| 7 | The hardware layer just became a platform | Why now. The "$60 → $0.06, 1,000×" panel is gone; platform timeline instead |
| 8 | We don't need to win the glasses war | Replaces "Meta, Google and Apple won't specialize" and the workflow comparison. Viture is described from its release, not straw-manned |
| 9 | A $306M first wedge, at a price a maintenance manager can approve | Market + Savings merged. Wedge equation, $200/mo ≈ 1 senior-tech hour/week, how we charge. $1.8B / $9.2B demoted to one line |
| 10 | We sell to one maintenance manager at a time, starting with a paid pilot | New. One motion, outreach numbers (70 sent, 68 delivered, 2 replies), both quotes, trade-school loop |
| 11 | I've built real-time vision on messy real-world video before, and I build fast | Founder moved into the core. "1 week" is now "4 days" (first commit Oct 17) |
| 12 | Coaching is the wedge. What compounds is maintenance data, models and skill records | Long game simplified; robotics is a dashed "long-term option". "Every session becomes training data" is now "with customer permission, sessions can become labeled training data" |
| 13 | $10k turns a working prototype into a first paid pilot on real glasses | Ask; each bucket now names its output. TRUE BY APRIL kept |

## Appendix

New: A1 benchmark table and method (raw 54/48, call counts, mistakes, degraded views, repair Q&A), A8 competitor
table with Strivr and Viture as separate rows, A11 hardware Q&A (why not build glasses, what if Meta closes access,
glasses as shared site equipment) with adapter status, A12 data rights and privacy, A13 safety model, A16 founder
detail. Moved in from the core: A4 full architecture, A6 backend screenshots, A17 long game in detail (revenue
targets, certifications, robotics). Removed: the stand-alone evidence bars slide (its numbers are in A1) and the
status-quo slide (merged into A8). The divider lists all 17 in two columns.

## Wording fixed for accuracy

- Glasses adapters: "built, not yet tested on a device" everywhere; "plug and play" is gone.
- Meta's toolkit: "1.0 in Sept 2026", without a day (the repo's docs say Sept 24; the brief said Sept 30).
- Google: "says its first Android XR glasses arrive this fall", no month.
- Viture Helix: no claim that it needs per-customer filming; that stays with Strivr, where the vendor docs say so.
- Customer data: the customer owns it; shared-model training needs a separate opt-in.
