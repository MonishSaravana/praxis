# Deck v2.8: changes since v2.7

12 core slides (about 7 minutes) and an 11-slide appendix. Source: `deck/build_deck.js`. Built from Monish's review of
v2.7 on 2026-10-18.

## Core order

| # | Slide | What changed |
|---|---|---|
| 1 | Cover | Same |
| 2 | Problem | Sourced numbers: **9–14 months** until a new tech pays for themselves (ARSA survey of 35 repair stations) and **$10–15k** to hire and ramp up one maintenance tech (Reliability magazine). Our $11–23k estimate moved to the notes and appendix A4 |
| 3 | Product | Same |
| 4 | **Why now** | Redrawn and moved earlier. To-scale AI-glasses shipments (2.1M → 8.7M → 15M+ forecast), cost to watch an hour of work ($5.10 → $1.08 → $0.48), and a five-date timeline |
| 5 | **How it works** | The engine blueprint, moved up from the appendix. The four boxes that learn from labeled recordings are tagged OURS · TRAINED, which shows what the data and GPU money improves |
| 6 | **How far along** | Adds the company backend (manual upload, compile, cited step cards, admin portal) and glasses + voice as built. Adds "11 of 15 technician questions answered right" on an industrial repair dataset (ENIGMA-51). The bottleneck is framed as data. The slide no longer says "cooking" |
| 7 | **Competitors** | The 2×2 is replaced by a capability matrix: Praxis vs procedure apps, fixed cameras, first-person AI glasses and general assistants on six capabilities. Dynamics 365 Guides is off this slide |
| 8 | **Why nobody owns this niche** | Meta, Google and Apple won't specialize, so we will. Also explains why we don't start with consumers. The old "why not consumers" slide stays as appendix A8 |
| 9 | Market | Same |
| 10 | Savings, price + GTM | Uses the sourced $10–15k. The break-even is one senior-tech hour a week ($44, BLS) |
| 11 | **Long game** | Revenue targets on the staircase ($0.3M → $1.2M → $3M ARR, 2027–29, labeled as targets). The robot step splits into two paths: (A) train our own robot models or (B) sell data and the step checker to labs. A panel shows what labs already pay for data: Mercor $2B+ run-rate, >$100M a year on robotics data, $8.6B market by 2030 |
| 12 | **Ask** | A plain use of funds with no "gap today" column: $3,000 GPU time · $2,500 glasses + capture · $2,000 training data · $1,500 inference · $1,000 formation. Then what's true by April |

## Appendix (A1–A11)

Evidence charts, status quo, market math, unit economics, learning curves, training data, competitor detail, why not
consumers, risks, glasses and voice, why me. A10 now lists the glasses connections and voice control as built, with
device testing as next.

## Notes for the room

- **Glasses and voice** say "built" on the slides. Say out loud that they aren't tested on devices yet. At commit
  `e7e28f7` this repo had only a glasses stub, so make sure the code is somewhere you can show if asked.
- **Step-tracking eval.** If asked, it's 48 held-out clips of a public first-person procedure dataset (CaptainCook4D,
  which is cooking). Say it plainly; the speaker notes on slide 6 have the line.
- **Revenue figures are targets,** from the same math as the market slide (about 25 trainees a team at $1,200).
- **Slide 10 outreach line** still needs the real reply count.
