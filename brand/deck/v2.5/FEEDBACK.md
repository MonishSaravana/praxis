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

Filled in below after the designer pass.
