# Deck v2.7: changes since v2.6

v2.7 has 11 core slides (about 7 minutes of talk) and a 12-slide appendix for Q&A. Its source is `deck/build_deck.js`.
It's cut for a 15-minute call: the pitch runs about 7 minutes and the rest is questions.

| File | What it is |
|---|---|
| `Praxis_SAH_v2.7.pptx` | Editable deck. Install the fonts in `brand/deck/v1/fonts/` first |
| `Praxis_SAH_v2.7.pdf` | Rendered with the brand fonts |
| `slides/` | One PNG per slide |

## Core order

| # | Slide | Status |
|---|---|---|
| 1 | Cover | Kept |
| 2 | Problem | Kept, plus ~255k openings a year along the bottom. The big number is no longer orange |
| 3 | Product | Kept |
| 4 | **How far along: built · works · bottleneck** | New. Replaces the engine and evidence slides in the talk. The bottleneck panel leads into the ask |
| 5 | Why now | Kept. The confusing "$5/hour … more than the price" row is now "$1 an hour" vs "~10× a year cheaper" |
| 6 | **Competitors** | New 2×2: does it watch the work or show the steps, and does it follow the person or sit at a station. Plus three reasons we win |
| 7 | **The platforms** | New. Meta, Google and Apple build our hardware; a maintenance coach isn't their business. Proof: 15M+ glasses forecast, Meta's camera toolkit, Microsoft leaving Guides |
| 8 | Market | Kept |
| 9 | **Savings, price + go-to-market** | Rebuilt: $11–23k of senior time per hire vs $1,200 per trainee; one saved hour a week pays for it |
| 10 | **The long game** | Rebuilt as a four-step staircase (coach → record → own models → robots), with who pays and the gate for each, and the data asset underneath |
| 11 | **The ask** | Rebuilt: each line of the $10k is tied to one gap and one milestone. Amounts unchanged from the application |

## Appendix (A1–A12)

The engine blueprint (A1), evidence charts (A2), status quo (A3), market math (A4), unit economics (A5), learning curves
(A6), training data (A7), competitor detail (A8), why not consumers (A9), risks (A10), glasses and voice (A11), why me
(A12). The old core learning-curve slide and the "why can't Meta, Google or Tulip build this" slide were removed, because
A6, slide 6 and slide 7 cover them.

## Fixes

- "13% more accurate" (relative) is now "54% vs 48%" everywhere, including speaker notes.
- Orange is only for "ours" and "now": the problem stat, Frontdoor's price and LipTrac went back to graphite.
- The build script runs slides in the order set by a runner at the bottom, which also numbers the progress marks and
  appendix labels. Reordering no longer means renumbering by hand. It throws if `TOTAL` doesn't match the core count.

## Still to decide before Tuesday

- Slide 9 outreach line: replace "14 sent · 56 scheduled" with real replies.
- A12 still says "I built this in a week" (first commit Oct 17). It's in the appendix now, so it's only said if asked.
