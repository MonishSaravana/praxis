# Praxis brand v0.1 (2026-10-17)

Brand board: https://claude.ai/artifact/XC1WCDRykDEgL6MprKAsq7

## Idea

It should look like it belongs on the shop floor. The look borrows from three things technicians already know:
equipment data plates (aluminum, graphite, wide capitals), torque stripes (the orange line painted on a checked
bolt), and ANSI Z535 safety colors (for product states).

## Mark

A P drawn like a progress ring. The stem is the procedure. The bowl is progress, left open where the work
isn't done. The orange dot is the step you're on. The same shape is used as the HUD progress indicator.

Geometry on a 64-unit grid: stroke 9u, bowl radius 14.5u, dot radius 6u, mitered top corner.

## Wordmark

Lowercase `praxis`, set in Archivo at 125% width and weight 600, tracked −10, then outlined. The i's dot is a
Torque Orange circle. In the lockup, the mark spans from the top of the i-dot to the bottom of the p's descender.
Keep clear space equal to the dot's diameter. Don't set the lockup narrower than 96px.

## Color tokens

| Token | Hex | Use |
|---|---|---|
| Graphite | `#16191B` | Ink, dark surfaces, HUD backing |
| Aluminum | `#E8EBE9` | Page ground |
| Plate | `#F6F7F6` | Cards, raised surfaces |
| Steel | `#5E676C` | Secondary text, labels (4.8:1 on Aluminum) |
| Torque Orange | `#FF5B14` | The dot, primary buttons, current step. Fills only on light grounds |
| Torque Ink | `#A3360A` | Orange as text on light grounds (5.7:1). Dark mode: `#FF7A3D` |

Product states (ANSI meanings):

| State | Light | Dark |
|---|---|---|
| Step verified (green, OK) | `#17784A` | `#3DD68C` |
| Needs a better view (blue, information) | `#1D4ED8` | `#6EA8FF` |
| Mistake caught (red, stop) | `#C21F14` | `#FF6B5E` |
| Current step (brand) | `#FF5B14` | `#FF5B14` |

## Type

- Display: Archivo, width 125, weight 600
- Body and UI: Archivo, width 100, weights 400 and 600
- Specs and data: IBM Plex Mono 500

All are on Google Fonts under the SIL Open Font License:
`https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@100..125,400..700&family=IBM+Plex+Mono:wght@400;500&display=swap`

## Files

- `svg/`: mark, wordmark and lockup in color, `-white` (for dark grounds) and `-black` (one color), plus the app icon and favicon
- `png/`: 2400px lockups and wordmark, 1024px mark and app icon, 180px apple-touch-icon, 32px favicon
- `src/`: the generator. It needs `fonttools` and `Archivo[wdth,wght].ttf` (from github.com/google/fonts, `ofl/archivo`)
  in `brand/fonts/`. Run `python brand/src/build.py <outdir>`

## Before shipping

"Praxis" is a crowded name (ETS's Praxis exams, among others). Run a USPTO search in classes 9 and 42 before
printing anything expensive.
