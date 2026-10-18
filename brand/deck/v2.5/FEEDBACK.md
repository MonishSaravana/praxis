# Deck v2.5: feedback and what we did with it

v2.5 is the Startups @ Harvard grant deck after two outside reviews:
- an investor review (a skeptical seed investor reading the story)
- a designer review (a senior presentation designer judging the visuals)

Both reviews were run by subagents on rendered slides. The editable source is `deck/build_deck.js`; this folder
holds the outputs.

| File | What it is |
|---|---|
| `Praxis_SAH_v2.5.pptx` | Editable deck. Install the fonts in `brand/deck/v1/fonts/` first |
| `Praxis_SAH_v2.5.pdf` | Rendered with the brand fonts |
| `slides/` | One PNG per slide |

## Investor review

**Verdict:** "Honest and visually coherent, but it reads as a technical-diligence document, not an investor story."
It found three gaps:
- no demand evidence
- no answer to "why can't Tulip, MaintainX or Meta copy this"
- no believable vision

Items 1–10 are the review's top 10 issues, in its order. Items 11–12 are its design notes. "v2" is commit `14f9a91`.

| # | Issue | Status | What changed |
|---|---|---|---|
| 1 | No copy-defense answer. Competition appeared three times and never answered the question | Fixed in v2 | Slide 10 asks "Why can't Meta, Google or Tulip build this?". It answers with a layer diagram (devices, assistants, procedure apps, and Praxis as verified work), says what we do if each of them moves, and names the moat honestly |
| 2 | No demand evidence: "70 contacted" is effort, not traction | Partly fixed | Slide 11 states exactly "14 sent 17 Oct, 56 scheduled 19 Oct". There are still no replies on the deck. **To do before Tuesday:** add real reply counts and one quote |
| 3 | Proof thinner than it looks: relative %, one run, cooking video | Fixed with one exception | Bars show the absolute numbers (54% vs 48%), and the footer says "public cooking video · one run each". The product slide shows step tracking, not mistake catching. **Declined:** the headline stays relative ("13% more accurate"), at the founder's request |
| 4 | The "moat" slide isn't a moat | Fixed in v2 | Retitled "It compounds". It shows one curve, labeled "Today this is public video. Next, it's our customers' sessions". The moat is named on slide 10 |
| 5 | Vision came late and overreached | Fixed in v2 | "We're building the record of how physical work gets done right": three gated steps, with robots last |
| 6 | The $1.8B SAM is mostly an unvalidated product | Fixed in v2 | Headline: "A $300M wedge inside a $1.8B first market". Bars are drawn to scale, and the notes say the records product is a hypothesis |
| 7 | Engine diagram too hard for slide 5 | Fixed in v2 | Core slide 4 is now a four-box diagram. The full engine is appendix A1 |
| 8 | Why-now leaned on glasses | Fixed in v2 | A dated timeline led by the MaintainX deal and the Dynamics 365 Guides retirement, plus the cost line |
| 9 | Team slide: "built in a week" invites copying; no domain exposure; no named robotics result | **Open** | Kept "built this in a week" at the founder's request (no longer in orange). The provisional patent is LipTrac's, filed earlier. **No named robotics result or maintenance-domain exposure is on file, so neither was invented. To do:** add a robotics result, shadow a technician or name an advisor |
| 10 | Problem slide: four equal stats, no hero | Fixed in v2 | Two heroes: ">1 year" and "$11–23k" (labeled as our estimate) |
| 11 | Cover: third-party glove branding visible | **Fixed in v2.5** | The glove logos are blurred in a copy of the cover photo (`deck/assets/photo-cover-clean.jpg`). The brand files are untouched |
| 12 | Ask needs a concrete success metric | **Fixed in v2.5** | Slide 14 adds the pilot metric: time until a new tech works alone, agreed with the customer before the pilot starts |

## Designer review

**Score: 6.5/10 before these fixes.** "The deck has the right bones and no longer reads as vibe slop. What stops it
reading as studio work is grid discipline and vertical rhythm."

### Deck-wide fixes

| # | Fix | Status | What changed |
|---|---|---|---|
| 1 | Lock one grid | Fixed | Margins are 0.5" and 12.83". Two columns at x 0.5 / 6.9 (5.93" wide); three columns at x 0.5 / 4.745 / 8.99 (3.84" wide). Applied to slides 2, 9, 11, 12, 13 and appendix A2 |
| 2 | Title system with no orphans | Fixed | Manual two-line breaks on 2, 4, 6, 7, 8, 9, 10, 12 and 13. Content starts at 1.95" under one-line titles |
| 3 | Fill the dead bands | Fixed | Slide 2 heroes are 80pt with 22pt captions. Slide 7 gets a two-number cost strip. Slides 9 and 12 are rebalanced |
| 4 | Footer system | Partly fixed | Footers are one line and never wrap. **Declined:** moving the page number to x 0.5 on split slides, because the layout puts it beside the dark panel |
| 5 | One orange per slide | Fixed | Cover and product HUD outlines are white, with orange only on the leader and caption. Slide 5: only the Praxis accuracy bar is orange. Slide 14: only "$10k". Slide 9: orange moved to the argument ("$99 → $25") |
| 6 | One diagram language | Fixed | Slides 4 and 10 use 1pt graphite borders. Appendix tables use horizontal rules only, with no cell fills |
| 7 | Chart parity | Fixed | 2.5pt lines, 7px markers, a lighter grid, mono chart titles on slide 5. The appendix A5 axes start at 0% |
| 8 | Break the template | Partly fixed | Slide sizes now vary (80pt heroes on 2, the equation on 11). **Declined:** a full-bleed 140pt number. The numerals in this deck are too wide in Archivo Expanded |

### Core-slide notes

| Slide | Fix | Status |
|---|---|---|
| 1 | Single accent, keep inside the margin | Fixed. HUD is white, the caption and tag end at 12.83", the meta line is on the footer baseline |
| 2 | Empty bottom; tight gutter | Fixed. Two-column grid, 80pt numerals |
| 3 | Four oranges; crowded rows | Fixed. White target box; 12pt mono labels with 16pt body |
| 4 | Dead quadrant; floating note | Fixed. The "ours vs rented" note is one full-width line at the bottom |
| 5 | Stats repeat the headline; four oranges | Fixed. One "1/5" hero; only the Praxis accuracy bar is orange; left-aligned mono chart titles |
| 6 | Line too heavy | Fixed. 2.5pt line, 7px markers, lighter grid |
| 7 | Floating cost line | Fixed. Turned into a $1 vs $5 strip at 36pt |
| 8 | "$9B one" orphan; four bar colors; $300M vs $306M | Fixed. Title broken across two lines with "$306M", TAM and SAM in two steel tints, labels centered on the bars |
| 9 | Unequal columns; arbitrary orange | Fixed |
| 10 | Cramped cards; mismatched borders | Fixed. Descriptions start at x 4.0", graphite borders, rules between right-column items |
| 11 | Equation labels don't map to the terms | Fixed. One label under each term; three-column grid; outreach line in steel |
| 12 | "I" orphan; columns stop short | Fixed |
| 13 | "done right" orphan; dot mismatch | Fixed. Balanced break; same dot size and y as slide 7 |
| 14 | Dense; ask buried; two oranges | Fixed. Table moved up; metric line in graphite; proportional budget strip; email moved to the footer |

### Appendix

- **A2:** card row now ends at 12.83". Fixed.
- **A3, A4, A7, A8:** horizontal-rule tables. Fixed.
- **A5:** axes from 0%. Fixed.
- **A1:** in-box text is still about 8.5pt. Declined; it's the brand team's diagram, and it's for Q&A, not projection.
- **A6, A9:** left as text slides.

## Still open (needs Monish)

- Outreach replies for slide 11, plus one quote (the Gmail check was skipped at your request).
- A named robotics result for slide 12, and a maintenance advisor or a shadowing day.
