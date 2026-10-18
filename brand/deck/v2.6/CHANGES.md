# Deck v2.6: changes since v2.5

v2.6 has 14 core slides and an 8-slide appendix. Its source is `deck/build_deck.js`. The review notes behind v2.5 are
in [`../v2.5/FEEDBACK.md`](../v2.5/FEEDBACK.md).

| File | What it is |
|---|---|
| `Praxis_SAH_v2.6.pptx` | Editable deck. Install the fonts in `brand/deck/v1/fonts/` first |
| `Praxis_SAH_v2.6.pdf` | Rendered with the brand fonts |
| `slides/` | One PNG per slide |

## What changed

- **Slide 4 is now the dark engine blueprint from `v2/`.** It shows the full engine: the orange live path, our parts, the
  open models, and the rented verifier in dashed outline, with measured numbers on the boxes. It replaces the simple
  four-box diagram. The light engine slide that used to be appendix A1 is removed, since it duplicated this one.
  The appendix is renumbered A1–A8.
- **No monospace type anywhere.** Monish felt IBM Plex Mono labels give the deck away as AI-made. The new type roles:
  - eyebrows, labels and tags: Archivo SemiBold in capitals, letter-spaced
  - lowercase labels and small specs: plain Archivo, no letter-spacing
  - footers: Archivo 9.5pt

  Rebuilding the PDF confirms only the Archivo family is embedded.
- **The engine slide's source line** now reads "48 held-out clips of public first-person video · one run each". The
  repository path is gone.
