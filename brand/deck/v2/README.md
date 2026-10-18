# Praxis deck v2 (editable)

`praxis-deck-v2.pptx` is the redesigned deck: the same content as v1, but the deck behaves like the Praxis HUD.
Design direction: https://claude.ai/artifact/KMsv2Z8Hpw4iWoBFsWnFAP

**The five rules:**
1. **The deck coaches the room.** Slides carry the HUD: a progress pill (`02 / 06`) and a chip with the one line to
   remember.
2. **One thing lit.** One word, number or box is at full brightness and the rest is dimmed.
3. **Extreme scale.** Hero numbers at about 150 pt against 7–9 pt mono labels.
4. **The belief bars.** The tracker's step-probability bars are the recurring graphic.
5. **Dark for the story, aluminum for the proof.**

| # | Slide | Layout |
|---|---|---|
| 1 | Cover: first-person photo, headline with "see" lit | Praxis Photo |
| 2 | Problem: "1 year", drawn as a 12-month timeline | Praxis Dark Grid |
| 3 | On the job: storyboard (mistake caught as the hero, plus 3 states) | Praxis Dark |
| 4 | Divider: "A tracking problem, not a seeing problem", with the belief bars | Praxis Dark |
| 5 | Architecture: dark blueprint, orange live path, rented part dimmed | Praxis Dark Grid |
| 6 | Results: 54% and 5× cheaper, bars drawn to scale | Praxis Aluminum |
| 7–10 | Appendix: full-screen HUD states (step, verified, mistake, better view), all native | Praxis Photo |
| 11 | Appendix: backup cover B | Praxis Dark Grid |

The progress pill counts the 6 main slides only.

## Before opening it

Install the five fonts in `fonts/` (double-click each `.ttf` → Install). The headings use `Archivo Expanded SemiBold`.

## Editing

Everything is native and editable except the photos, the logo, the progress marks and the four storyboard frames on
slide 3 (images of the HUD mocks; the editable versions are slides 7–10). Shapes are named in the Selection Pane,
for example `hero-number`, `month-1`…`month-12`, `belief-bar-S5`, `deck-progress`, `box-state-tracker`,
`arrow-tracker-verifier` and `result-1-bar-1`. The results bars are shapes drawn to scale: if a number changes, change
the bar's width too, or rebuild.

To rebuild after changing `build-deck.js`:

```bash
cd brand/deck/v2 && npm install && node build-deck.js praxis-deck-v2.pptx
```

In `build-deck.js`, positions on the new slides use the mockup's units: `Q(v)` is v percent of the slide width.
The architecture slide uses a 1600×900 grid (`V(px)`), and the photo HUD slides use the 1920×1080 frame (`P(px)`).

## Claims

The photo and storyboard slides are concept mocks on stock photos and are tagged that way. The numbers come from
`results/RESULTS.md` and `docs/CLAIMS.md`, measured on a public first-person cooking dataset. The belief bars on the
divider and architecture slides are illustrative.
