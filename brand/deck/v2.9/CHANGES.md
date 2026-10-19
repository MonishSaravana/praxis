# Deck v2.9: changes since v2.8

13 core slides and an 11-slide appendix. Source: `deck/build_deck.js`. Built from Monish's review of v2.8 on 2026-10-18.

| # | Slide | What changed |
|---|---|---|
| 4 | Why now | New title: "2026: cameras moved onto faces, and watching work got cheap". The Microsoft Dynamics 365 date is off the timeline |
| 6 | **How far along · built** | New. Real screenshots of the company backend, restyled in the Praxis brand: uploaded manuals (Hydro Plant demo, 97–222-page Reclamation manuals) and a compiled, approved procedure (ENIGMA-51). Three numbered steps: upload, review, coach |
| 7 | **How far along · measured** | New. Four measured results and the data bottleneck. Says "a handful of videos per procedure" instead of "3 recordings". No admin-portal line |
| 8 | **Competitors** | The matrix is replaced by workflows: what it takes to roll out a new procedure with procedure apps, fixed cameras, first-person AI glasses, and Praxis |
| 9 | Why nobody owns this niche | The Microsoft stat is replaced by "$99 → $25" (consumer help is a race to free), which supports the "not consumer" line |
| 11 | Savings, price + GTM | Go-to-market is spelled out: customers 1–10 (I sell them myself), 10–100 (pilots become proof), 100–1,000 (partners sell it). No Dynamics 365 |

Dynamics 365 Guides now appears only in speaker notes, as a Q&A backup.

## Company backend restyle

`prototype/praxis/studio/static/admin.css` gets a brand layer, scoped to the admin page: Archivo type (served from
`static/brand/`), a Graphite header with the white lockup, an Aluminum ground, Plate surfaces, Torque Orange for
primary buttons and the current section, and the brand state colors. `admin.html` uses the lockup. The Live page is
unchanged.
