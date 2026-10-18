# Praxis decks

| Folder | Deck | Notes |
|---|---|---|
| [`v1/`](v1/) | `praxis-deck.pptx`, 10 slides | The first editable deck: light content slides and full-screen HUD slides |
| [`v2/`](v2/) | `praxis-deck-v2.pptx`, 6 story slides + 5 appendix | The redesign that makes the deck behave like the HUD. Use this one |
| [`v2.5/`](v2.5/) | `Praxis_SAH_v2.5.pptx`, 14 core slides + 9 appendix | The full investor storyline (problem, why now, market, why not consumers, why big firms can't copy it, business model, founder, vision, ask) after an investor review and a designer review; see `FEEDBACK.md`. Rendered output only: its source is `deck/build_deck.js` |
| [`v2.6/`](v2.6/) | `Praxis_SAH_v2.6.pptx`, 14 core slides + 8 appendix | v2.5 plus the dark engine blueprint from `v2/` as slide 4, and no monospace type anywhere (labels in spaced Archivo SemiBold). See `CHANGES.md`. Source: `deck/build_deck.js` |

Each folder is self-contained: the deck, the `build-deck.js` that generates it, the assets, the fonts and a README
on how to edit it (by hand or with Claude).
