# Harvard Ventures Demo Day deck

`Praxis_HV_DemoDay.pptx` is the pitch for the Harvard Ventures Demo Day: 11 core slides in the Sequoia order, then an
appendix divider and 3 appendix slides for Q&A. `Praxis_HV_DemoDay.pdf` is the same deck rendered with the brand
fonts. The videos show as poster frames in the PDF.

It's a separate deck from the S@H grant deck (`deck/`). It uses the same brand, photos, demo videos and checked numbers
(`docs/CLAIMS.md`), with new layouts. Following the HV coaching notes, the core slides go problem → solution → future,
and the technical depth sits in the appendix. The coach suggested "a few" appendix slides (demos, modeling, deeper
tech), so there are three. Each one also answers the questions a board asks most often.

| # | Section | Headline |
|---|---|---|
| 1 | Company purpose | Instructions that can finally see how you're doing |
| 2 | Problem | A new maintenance tech needs a year of a senior tech's time before they can work alone |
| 3 | Solution | Praxis watches the work and coaches one step at a time |
| 4 | Why now | Smart glasses took off, and AI got 1,000× cheaper |
| 5 | Market size | A $306M wedge in a $1.8B first market, inside a $9B one |
| 6 | Competition | Every option today is missing a piece |
| 7 | Product | It already works, live, on a real repair job (the 49 s demo video) |
| 8 | Business model | $200 a month per new tech. Saving a senior tech one hour a week pays for it |
| 9 | Team | I've built real-time vision on messy video before, and I built this in a week |
| 10 | Financials | A path to $4.5M ARR by 2029, at 77–90% gross margin |
| 11 | Future | Today we coach the people. Next, the robots |
| A1 | Under the hood | The engineer view of the live demo. Is it real? Was it trained on this job? Does it run on glasses? |
| A2 | How it works | The engine part by part, plus six Q&A cards: wrapper, moat, Big Tech, accuracy, safety, privacy |
| A3 | Market math | TAM/SAM/SOM with the math, plus four Q&A cards: why not consumers, why a shop pays, margins, customers |

## Presenting

- **3-minute version.** Each core slide's speaker notes start with a `3-MIN:` line. If you say only those lines,
  the whole deck takes about 3 minutes. The rest of each note has the exact numbers and the honest caveats for Q&A.
- **The video on slide 7 runs 49 seconds.** In a short slot, talk over it while it plays, or stop it after the 2:52
  moment (the soldering iron at 215 °C).
- **Before you present, check:**
  - Slide 8 and appendix A3 say "70 … this week" (14 sent Oct 17, 56 sent Oct 19, 68 delivered).
  - Slide 2 quotes the first outreach reply (a hospital sterile processing association), and slide 8 and A3
    mention the fiber-optic school that's open to a one-lab trial. Both are named by kind of organization only, since
    they answered a student-project email. Update the reply count in the notes from `docs/OUTREACH.md`.
  - Slide 9 has no photo. To add one, drop it over the dark panel and send it to the back.

## Editing

The script builds the deck, so edit `build_hv.js`, not the .pptx. A rebuild overwrites any edits made in PowerPoint.

```bash
cd deck-hv && python3 make_tiles.py && node build_hv.js
```

- **Dependencies.** It reuses `deck/node_modules`, so run `npm install` in `deck/` first if that folder is
  missing.
- **Fonts.** Install the fonts in `brand/deck/v1/fonts/` before opening the deck (see `brand/deck/v1/README.md`).
- **Order.** `CORE` and `APPENDIX` at the bottom of the script set the order. The progress bar, section labels and
  appendix numbers update on their own. The core deck must have one slide per entry in `SECTIONS`.
- **Tiles.** `make_tiles.py` crops the three photo tiles on slide 3 out of the brand's concept-mock photos. The
  HUD on top is drawn natively in the script, so its text stays editable.
- **Preview.** Render the preview the way `deck/README.md` describes: LibreOffice with a fontconfig file that points at
  the brand fonts. `pdffonts` should list only Archivo, plus OpenSymbol for the bullets.
- **Claims.** Every number comes from `docs/CLAIMS.md`, `docs/POSITIONING.md` or `docs/VISION.md`, with its source
  in the speaker notes. The photos are concept mocks on stock photos and are labeled that way. The appendix stays at
  the "ours, open, rented" level and leaves out how the tracker works, until the provisional patent is filed.
