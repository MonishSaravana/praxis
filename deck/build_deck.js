// Praxis S@H grant deck, in the Praxis brand (brand/BRAND.md). Editable .pptx built with pptxgenjs.
// Slides 1–8 and the closing cover come from brand/deck/build-deck.js (same helpers, same assets); the rest are new
// slides drawn in the same system. Every number comes from results/ (docs/CLAIMS.md) or a cited source in
// docs/POSITIONING.md / docs/VISION.md. Photo slides are concept mocks on stock photos and say so.
//   cd deck && node build_deck.js        (progress marks: python3 deck/make_marks.py <TOTAL>)
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const JSZip = require(require.resolve("jszip", { paths: [require.resolve("pptxgenjs")] }));

const ROOT = path.resolve(__dirname, "..");
const OUT = process.argv[2] || path.join(__dirname, "Praxis_SAH_Oct2026.pptx");
const LC = JSON.parse(fs.readFileSync(path.join(ROOT, "results/scaling/learning_curve.json"), "utf8"));

// pptxgenjs can't write theme colors, so write them into ppt/theme/*.xml after saving.
async function applyTheme(file, theme) {
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  const slots = ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "hlink", "folHlink"];
  const scheme = `<a:clrScheme name="${theme.name}">` + slots.map((k) => `<a:${k}><a:srgbClr val="${theme.colors[k]}"/></a:${k}>`).join("") + "</a:clrScheme>";
  for (const name of Object.keys(zip.files).filter((n) => /^ppt\/theme\/theme\d+\.xml$/.test(n))) {
    const xml = await zip.file(name).async("string");
    zip.file(name, xml.replace(/<a:clrScheme[\s\S]*?<\/a:clrScheme>/, scheme).replace(/(<a:theme[^>]*name=")[^"]*"/, `$1${theme.name}"`));
  }
  fs.writeFileSync(file, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}

const A = (f) => path.join(ROOT, "brand", "deck", "v1", "assets", f);
const MK = (f) => path.join(__dirname, "assets", "marks", f);
const P = (px) => px / 144;
const TOTAL = 14; // main-deck slides; appendix slides carry the full mark

const THEME = {
  name: "Praxis",
  headFontFace: "Archivo Expanded SemiBold",
  bodyFontFace: "Archivo",
  colors: {
    dk1: "16191B", // Graphite
    lt1: "F6F7F6", // Plate
    dk2: "5E676C", // Steel
    lt2: "E8EBE9", // Aluminum
    accent1: "FF5B14", // Torque Orange
    accent2: "A3360A", // Torque Ink (orange as text on light)
    accent3: "17784A", // Verified green
    accent4: "1D4ED8", // View-request blue
    accent5: "C21F14", // Mistake red
    accent6: "9AA3A7", // Light steel
    hlink: "A3360A",
    folHlink: "5E676C",
  },
};
const MONO = "Archivo SemiBold"; // labels (was IBM Plex Mono; replaced at the founder's request)
const LABEL = MONO;
const SEMI = "Archivo SemiBold";
const HEAD = THEME.headFontFace;
const HUD = { ink: "16191B", text: "E8EBE9", orange: "FF5B14", green: "3DD68C", blue: "6EA8FF", red: "D92D20", plate: "F6F7F6", body: "3C4347" };
const LOCKUP_RATIO = 452.48 / 91.93;
const MARK_RATIO = 38 / 48;
const BODY = "3C4347";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "Praxis";
pres.author = "Monish Saravana";
pres.company = "Praxis";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

// Slides are functions; the runner at the bottom sets the order. It also sets the section every slide lands in,
// the slide's number (CUR) and, for the appendix, its label (APX), so reordering never means renumbering by hand.
let SECTION = null, CUR = 0, APX = null;
const addSlideRaw = pres.addSlide.bind(pres);
const ALL_SLIDES = [];
pres.addSlide = (o = {}) => {
  const sl = addSlideRaw({ ...o, sectionTitle: SECTION });
  // A pitch deck shows no source lines: footer() keeps each source, and it's written into the speaker notes at the end.
  sl._rawNotes = sl.addNotes.bind(sl);
  sl.addNotes = (t) => { sl._notes = t; return sl; };
  ALL_SLIDES.push(sl);
  return sl;
};
const eb = (t) => (APX ? `APPENDIX · ${APX}` : t);

// ---------- layouts (as in brand/deck) ----------
const eyebrow = (color, y = 0.5) => ({
  placeholder: { options: { name: "eyebrow", type: "body", x: 0.5, y, w: 9, h: 0.3, fontFace: MONO, fontSize: 11, charSpacing: 2, color, margin: 0, valign: "top" }, text: "Eyebrow" },
});
pres.defineSlideMaster({
  title: "Praxis Light",
  background: { color: C.background2 },
  objects: [
    eyebrow(C.text2),
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.85, w: 12.33, h: 1.05, fontFace: HEAD, fontSize: 28, color: C.text1, align: "left", valign: "top", margin: 0, lineSpacingMultiple: 0.95 }, text: "Slide title" } },
  ],
  slideNumber: { x: 0.82, y: 6.93, w: 0.6, h: 0.3, fontFace: MONO, fontSize: 10, color: C.text2, margin: 0, valign: "middle" },
});
pres.defineSlideMaster({
  title: "Praxis Split",
  background: { color: C.background2 },
  objects: [
    { placeholder: { options: { name: "eyebrow", type: "body", x: 7.85, y: 0.6, w: 4.98, h: 0.3, fontFace: MONO, fontSize: 11, charSpacing: 2, color: C.text2, margin: 0, valign: "top" }, text: "Eyebrow" } },
    { placeholder: { options: { name: "title", type: "title", x: 7.85, y: 0.95, w: 4.98, h: 1.9, fontFace: HEAD, fontSize: 26, color: C.text1, align: "left", valign: "top", margin: 0, lineSpacingMultiple: 0.95 }, text: "Slide title" } },
  ],
  slideNumber: { x: 8.17, y: 6.93, w: 0.6, h: 0.3, fontFace: MONO, fontSize: 10, color: C.text2, margin: 0, valign: "middle" },
});
pres.defineSlideMaster({
  title: "Praxis Dark Grid",
  background: { path: A("bg-grid-dark.png") },
  objects: [
    eyebrow(C.accent1, 0.83),
    { placeholder: { options: { name: "title", type: "title", x: 0.83, y: 4.2, w: 6.9, h: 1.6, fontFace: HEAD, fontSize: 40, color: C.background2, align: "left", valign: "bottom", margin: 0, lineSpacingMultiple: 0.95 }, text: "Section title" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.83, y: 5.95, w: 6.3, h: 0.8, fontFace: THEME.bodyFontFace, fontSize: 16, color: C.accent6, valign: "top", margin: 0 }, text: "Body" } },
  ],
});
pres.defineSlideMaster({ title: "Praxis Photo", background: { color: C.text1 }, objects: [] });

// ---------- helpers (as in brand/deck) ----------
function footer(slide, _n, source, x0 = 0.5) {
  const n = APX ? TOTAL : CUR;
  slide.addImage({ path: MK(`prog-light-${n}of${TOTAL}.png`), x: x0, y: 6.93, h: 0.3, w: 0.3 * MARK_RATIO, objectName: "progress-mark" });
  if (source) slide._src = source;
}
function line(slide, x1, y1, x2, y2, opts) {
  const o = { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1), line: { color: opts.color, width: opts.width || 1.5, dashType: opts.dash || "solid", endArrowType: opts.arrow ? "triangle" : undefined }, objectName: opts.name };
  if (x2 < x1) o.flipH = true;
  if (y2 < y1) o.flipV = true;
  slide.addShape(pres.ShapeType.line, o);
}
function poly(slide, pts, opts) {
  for (let i = 0; i < pts.length - 1; i++) line(slide, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], { ...opts, arrow: opts.arrow && i === pts.length - 2 });
}
function hudProgress(slide, step, total, x = 56, y = 56, textW = 137) {
  const markW = 56 * MARK_RATIO, w = 22 + markW + 18 + textW + 26;
  slide.addShape(pres.ShapeType.roundRect, { x: P(x), y: P(y), w: P(w), h: P(88), rectRadius: P(14), fill: { color: HUD.ink, transparency: 20 }, line: { type: "none" }, objectName: "hud-progress" });
  slide.addImage({ path: A(`prog-hud-${step}of${total}.png`), x: P(x + 22), y: P(y + 16), w: P(markW), h: P(56), objectName: "hud-progress-mark" });
  slide.addText(`STEP ${step}/${total}`, { x: P(x + 22 + markW + 18), y: P(y), w: P(textW + 20), h: P(88), fontFace: MONO, fontSize: 13, charSpacing: 1, color: HUD.text, valign: "middle", margin: 0, isTextBox: true, objectName: "hud-progress-text" });
}
function hudChip(slide, text, textW, opts = {}) {
  const h = opts.label ? 136 : 96, w = textW + 64 + 24, bottom = 1016;
  const x0 = opts.right ? 1848 - w : 56, y0 = bottom - h;
  slide.addShape(pres.ShapeType.roundRect, { x: P(x0), y: P(y0), w: P(w), h: P(h), rectRadius: P(10), fill: { color: HUD.ink, transparency: 14 }, line: { type: "none" }, objectName: "hud-chip" });
  slide.addShape(pres.ShapeType.rect, { x: P(x0), y: P(y0), w: P(8), h: P(h), fill: { color: HUD.orange }, line: { type: "none" }, objectName: "hud-chip-edge" });
  const runs = [];
  if (opts.label) runs.push({ text: opts.label, options: { fontFace: MONO, fontSize: 11, charSpacing: 1, color: opts.labelColor, breakLine: true, paraSpaceAfter: 4 } });
  runs.push({ text, options: { fontFace: SEMI, fontSize: 20, color: HUD.text } });
  slide.addText(runs, { x: P(x0 + 38), y: P(y0), w: P(w - 50), h: P(h), valign: "middle", margin: 0, isTextBox: true, objectName: "hud-chip-text" });
  return [x0, y0, x0 + w, y0 + h];
}
function hudCard(slide, kind, color, headColor, title, body, x, y, w = 700) {
  const h = 250;
  slide.addShape(pres.ShapeType.roundRect, { x: P(x), y: P(y), w: P(w), h: P(h), rectRadius: P(10), fill: { color: HUD.plate }, line: { type: "none" }, objectName: "hud-card" });
  slide.addShape(pres.ShapeType.rect, { x: P(x), y: P(y), w: P(w), h: P(10), fill: { color }, line: { type: "none" }, objectName: "hud-card-state" });
  slide.addText([
    { text: kind, options: { fontFace: MONO, fontSize: 11, charSpacing: 1, color: headColor, breakLine: true, paraSpaceAfter: 6 } },
    { text: title, options: { fontFace: SEMI, fontSize: 20, color: HUD.ink, breakLine: true, paraSpaceAfter: 6 } },
    { text: body, options: { fontFace: THEME.bodyFontFace, fontSize: 15.5, color: HUD.body } },
  ], { x: P(x + 34), y: P(y + 30), w: P(w - 68), h: P(h - 50), valign: "top", margin: 0, isTextBox: true, objectName: "hud-card-text" });
  return [x, y, x + w, y + h];
}
function hudRegion(slide, reg, color, dashed) {
  const [x0, y0, x1, y1] = reg;
  slide.addShape(pres.ShapeType.roundRect, { x: P(x0), y: P(y0), w: P(x1 - x0), h: P(y1 - y0), rectRadius: P(22), fill: { type: "none" }, line: { color, width: 2.6, dashType: dashed ? "dash" : "solid" }, objectName: "hud-target" });
}
function hudLeader(slide, src, reg, color) {
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const [rx0, ry0, rx1, ry1] = reg, [sx0, sy0, sx1, sy1] = src;
  const cx = (rx0 + rx1) / 2, cy = (ry0 + ry1) / 2;
  let ax = clamp(cx, sx0 + 24, sx1 - 24), ay = clamp(cy, sy0, sy1);
  if (sy0 < cy && cy < sy1) ax = cx < sx0 ? sx0 : sx1;
  let bx = clamp(ax, rx0 + 30, rx1 - 30), by = clamp(ay, ry0, ry1);
  if (ry0 < ay && ay < ry1) bx = ax < rx0 ? rx0 : rx1;
  line(slide, P(ax), P(ay), P(bx), P(by), { color, width: 2, name: "hud-leader" });
  slide.addShape(pres.ShapeType.ellipse, { x: P(ax - 7), y: P(ay - 7), w: P(14), h: P(14), fill: { color }, line: { type: "none" }, objectName: "hud-leader-start" });
  slide.addShape(pres.ShapeType.ellipse, { x: P(bx - 11), y: P(by - 11), w: P(22), h: P(22), fill: { color }, line: { color: HUD.ink, width: 1.5 }, objectName: "hud-leader-dot" });
}
function hudPulse(slide, cx, cy, color) {
  slide.addShape(pres.ShapeType.ellipse, { x: P(cx - 44), y: P(cy - 44), w: P(88), h: P(88), fill: { type: "none" }, line: { color, width: 3.5 }, objectName: "hud-verify-pulse" });
  slide.addShape(pres.ShapeType.ellipse, { x: P(cx - 72), y: P(cy - 72), w: P(144), h: P(144), fill: { type: "none" }, line: { color, width: 2, transparency: 55 }, objectName: "hud-verify-pulse-outer" });
}
function conceptTag(slide) {
  const w = 446 * 0.69 + 28;
  slide.addShape(pres.ShapeType.roundRect, { x: P(1848 - w), y: P(1032), w: P(w), h: P(34), rectRadius: P(6), fill: { color: HUD.ink, transparency: 40 }, line: { type: "none" }, objectName: "concept-tag" });
  slide.addText("CONCEPT MOCK · STOCK PHOTO", { x: P(1848 - w), y: P(1032), w: P(w), h: P(34), fontFace: MONO, fontSize: 8, charSpacing: 1, color: "C9CFCC", align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "concept-tag-text" });
}
function photo(slide, file) {
  slide.addImage({ path: A(file), x: 0, y: 0, w: 13.333, h: 7.5, objectName: "photo" });
}

// ---------- helpers for the new slides, in the same system ----------
const tb = (slide, t, o) => slide.addText(t, { margin: 0, valign: "top", isTextBox: true, fontSize: 16, color: C.text1, ...o });
const mono = (slide, t, o) => tb(slide, t, { fontFace: MONO, fontSize: 10.5, charSpacing: 1, color: C.text2, ...o });
// a stat column: rule, big number, caption (the brand problem slide's pattern)
function statCol(slide, x, y, w, big, cap, o = {}) {
  line(slide, x, y, x + w, y, { color: C.text1, width: 1.5, name: "stat-rule" });
  tb(slide, big, { x, y: y + 0.18, w, h: 0.75, fontFace: HEAD, fontSize: o.size || 40, color: o.color || C.text1, objectName: "stat" });
  tb(slide, cap, { x, y: y + 0.98, w: w - 0.2, h: o.capH || 0.9, fontSize: 14, objectName: "stat-caption" });
}
const titleWithMark = (before, mark, after = "") => [
  { text: before },
  { text: mark, options: { underline: { style: "heavy", color: "FF5B14" } } },
  ...(after ? [{ text: after }] : []),
];
function darkPanel(slide, x, y, w, h, label, body, size = 17) {
  slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.05, fill: { color: C.text1 }, line: { type: "none" }, objectName: "panel-dark" });
  slide.addText([
    { text: label, options: { fontFace: MONO, fontSize: 10.5, charSpacing: 1, color: C.accent1, breakLine: true, paraSpaceAfter: 6 } },
    { text: body, options: { fontFace: THEME.bodyFontFace, fontSize: size, color: C.background2 } },
  ], { x: x + 0.35, y: y + 0.25, w: w - 0.7, h: h - 0.4, margin: 0, valign: "top", isTextBox: true, objectName: "panel-dark-text" });
}
function plateCard(slide, x, y, w, h, name = "card") {
  slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.05, fill: { color: C.background1 }, line: { type: "none" }, objectName: name });
}
const darkChart = (title) => ({
  barDir: "bar", showTitle: true, title, titleFontFace: "+mn-lt", titleFontSize: 12, titleColor: "E8EBE9",
  showValue: true, dataLabelPosition: "outEnd", dataLabelFontFace: "+mn-lt", dataLabelFontSize: 14, dataLabelColor: "E8EBE9", dataLabelFontBold: true,
  catAxisLabelColor: "9AA3A7", catAxisLabelFontFace: "+mn-lt", catAxisLabelFontSize: 11, catAxisLineShow: false,
  valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false,
  barGapWidthPct: 45, plotArea: { fill: { color: "16191B" } },
});
const mean = (a) => a.reduce((x, y) => x + y, 0) / a.length;
const pct1 = (v) => Math.round(v * 1000) / 10;
const runs = (pairs, gap = 10) => pairs.flatMap(([a, b], i) => [{ text: a, options: { fontFace: SEMI } }, { text: b, options: { breakLine: i < pairs.length - 1, paraSpaceAfter: gap } }]);

const tableOpts = (colW, w = 12.33) => ({ x: 0.5, y: 2.2, w, colW, fontFace: "Archivo", fontSize: 13, color: "16191B", border: [{ type: "none" }, { type: "none" }, { type: "solid", color: "B9C0BC", pt: 0.75 }, { type: "none" }], valign: "middle", rowH: 0.55 });
const TH = (t) => ({ text: t, options: { fontFace: MONO, fontSize: 10, color: "5E676C", border: [{ type: "none" }, { type: "none" }, { type: "solid", color: "16191B", pt: 1.5 }, { type: "none" }] } });

// hero: rule, one big number or word, one caption (the brand "statement slide" pattern, bigger)
function hero(slide, x, y, w, big, cap, o = {}) {
  const size = o.size || 60;
  line(slide, x, y, x + w, y, { color: C.text1, width: 1.5, name: "hero-rule" });
  tb(slide, big, { x, y: y + 0.2, w, h: size / 72 * 1.2, fontFace: HEAD, fontSize: size, color: o.color || C.text1, objectName: "hero" });
  tb(slide, cap, { x, y: y + 0.3 + size / 72 * 1.2, w: w - 0.2, h: o.capH || 1.2, fontSize: o.capSize || 17, objectName: "hero-caption" });
}

// Grid (designer review, v2.5): margins 0.5" and 12.83". Two columns at x 0.5 / 6.9 (5.93" wide);
// three columns at x 0.5 / 4.745 / 8.99 (3.84" wide). Content starts at y 1.95 under one-line titles, 2.3 under two.
const G2 = { x: [0.5, 6.9], w: 5.93 };
const G3 = { x: [0.5, 4.745, 8.99], w: 3.84 };
const HUD_WHITE = "E8EBE9";

// step-model learning curve, held-out, the 3 procedures with 9 training recordings: "31% → 51%"
function progressCurve() {
  const Pr = LC.probes, pk = {};
  Pr.rows.forEach((r) => { if (Pr.n_train_avail[r.task] >= 9) (pk[r.k] = pk[r.k] || []).push(r.acc); });
  const ks = Object.keys(pk).map(Number).sort((a, b) => a - b);
  return `${Math.round(mean(pk[ks[0]]) * 100)}% → ${Math.round(mean(pk[ks[ks.length - 1]]) * 100)}%`;
}
// appendix label of a slide function, for cross-references ("A3")
const ref = (fn) => `A${APPENDIX.findIndex(([f]) => f === fn) + 1}`;

// ---------- Cover ----------
function sCover() {
  const s = pres.addSlide({ masterName: "Praxis Photo", sectionTitle: "Story" });
  s.addImage({ path: path.join(__dirname, "assets", "photo-cover-clean.jpg"), x: 0, y: 0, w: 13.333, h: 7.5, objectName: "photo" }); // brand cover photo, glove logos blurred
  s.addImage({ path: A("praxis-lockup-white.png"), x: 0.5, y: 0.55, h: 0.4, w: 0.4 * LOCKUP_RATIO, objectName: "logo" });
  s.addText("Instructions that can finally see how you're doing", { x: 0.5, y: 2.05, w: 5.6, h: 2.4, fontFace: HEAD, fontSize: 40, color: C.background2, valign: "middle", margin: 0, lineSpacingMultiple: 0.95, isTextBox: true, objectName: "cover-headline" });
  tb(s, "An AI coach for new maintenance technicians. It watches the work through a first-person camera and says the next step.", { x: 0.5, y: 4.6, w: 5.2, h: 1.0, fontSize: 17, color: C.background2, objectName: "cover-oneliner" });
  s.addText("STARTUPS @ HARVARD · 20 OCT 2026 · MONISH SARAVANA", { x: 0.5, y: 6.93, w: 6.5, h: 0.3, fontFace: MONO, fontSize: 10, charSpacing: 1, color: C.accent6, margin: 0, valign: "middle", isTextBox: true, objectName: "cover-meta" });
  const reg = [860, 640, 1180, 900];
  hudRegion(s, reg, HUD_WHITE);
  hudPulse(s, 1010, 790, HUD_WHITE);
  hudProgress(s, 4, 9, 1848 - 247);
  const chip = hudChip(s, "Seat the clamp past the hose bead", 624, { right: true });
  hudLeader(s, chip, reg, HUD.orange);
  conceptTag(s);
  s.addNotes("Hi, I'm Monish. Praxis is an AI coach for physical work. It watches through a first-person camera, knows where a new technician is in a procedure, checks the work and says the next step. The photo is stock with a mocked-up HUD; the engine behind it is real, and I'll show the numbers.");
}

// ---------- Problem ----------
function sProblem() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("THE PROBLEM", { placeholder: "eyebrow" });
  s.addText("A new maintenance technician needs about a year\nof a senior tech's time to work alone", { placeholder: "title" });
  hero(s, G2.x[0], 2.9, G2.w, "9–14", "months before a new technician pays for themselves, in a survey of 35 repair stations.", { size: 60, capSize: 20, capH: 1.0 });
  hero(s, G2.x[1], 2.9, G2.w, "$10–15k", "to hire and ramp up one maintenance technician, counting onboarding and lost productivity.", { size: 60, capSize: 20, capH: 1.0 });
  line(s, 0.5, 5.85, 12.83, 5.85, { color: C.accent6, width: 0.75, name: "problem-rule" });
  tb(s, [{ text: "~255,000 openings a year ", options: { fontFace: SEMI } }, { text: "for US maintenance and repair techs, and every new hire pulls a senior tech off the floor." }], { x: 0.5, y: 6.0, w: 12.33, h: 0.5, fontSize: 17 });
  footer(s, 0, "ARSA member survey of 35 repair stations, 2017 · Reliability magazine (A. Gager) · BLS Occupational Outlook Handbook");
  s.addNotes(`Manuals and videos can't see you, so the senior tech is the real teacher, and that time sits in nobody's training budget. ARSA surveyed 35 aviation repair stations: new hires took 9 to 14 months on average to become profitable, some up to 24. Reliability magazine puts recruiting and hiring one maintenance technician at $10,000 to $15,000 once onboarding time and lost productivity are counted; that's a trade estimate, not a study. BLS says on-the-job training for these jobs typically lasts more than a year. Our own estimate of the senior-tech time alone is $11-23k per hire (appendix ${ref(aUnitEcon)}).`);
}

// ---------- Product ----------
function sProduct() {
  const s = pres.addSlide({ masterName: "Praxis Photo", sectionTitle: "Story" });
  photo(s, "photo-step.jpg");
  const reg = [800, 300, 1260, 820];
  hudRegion(s, reg, HUD_WHITE);
  hudProgress(s, 3, 8, 1848 - 247);
  const chip = hudChip(s, "Loosen the four float-bowl screws a half turn each", 903, { right: true });
  hudLeader(s, chip, reg, HUD.orange);
  s.addShape(pres.ShapeType.rect, { x: 0, y: 0, w: 4.95, h: 7.5, fill: { color: C.text1, transparency: 6 }, line: { type: "none" }, objectName: "product-panel" });
  mono(s, "THE PRODUCT", { x: 0.5, y: 0.6, w: 4.0, h: 0.3, fontSize: 11, color: C.accent6 });
  tb(s, "Praxis watches the work and coaches one step at a time", { x: 0.5, y: 1.0, w: 4.1, h: 2.2, fontFace: HEAD, fontSize: 28, color: C.background2, lineSpacingMultiple: 0.95 });
  [["LOAD", "the manuals and checklists a shop already has"], ["COACH", "through smart glasses, one short line at a time"], ["VERIFY", "critical steps and keep the record"]].forEach(([k, b], i) => {
    const y = 3.85 + i * 0.95;
    line(s, 0.5, y, 4.45, y, { color: "3A4044", width: 1, name: "product-rule" });
    mono(s, k, { x: 0.5, y: y + 0.17, w: 1.1, h: 0.3, fontSize: 12, color: C.background2 });
    tb(s, b, { x: 1.6, y: y + 0.13, w: 2.85, h: 0.75, fontSize: 16, color: C.accent6 });
  });
  conceptTag(s);
  s.addNotes("What it is: software for smart glasses, not the glasses themselves. It runs on camera or display glasses through an input adapter. It speaks; cards appear only for mistakes and view requests, and the step graph is never shown. It verifies, logs, and flags mistakes only when confident. Mistake detection is our weakest number today (4 of 17 alerts named a real annotated error), so this slide shows step tracking, which is what we measure best. Buyer: the maintenance manager. User: the new tech.");
}

const Q = (v) => (v * 13.333) / 100;
// ---------- Engine (dark blueprint, from brand/deck/v2) ----------
function sEngine() {
  const s = pres.addSlide({ masterName: "Praxis Dark Grid", sectionTitle: "Story" });
  tb(s, eb("HOW IT WORKS · ENGINE v0"), { x: Q(2.9), y: Q(3.1), w: Q(40), h: Q(1.6), fontFace: LABEL, fontSize: 10, charSpacing: 2, color: C.accent6, objectName: "eyebrow" });
  s.addText([
    { text: "The frontier model is one swappable part. " },
    { text: "The tracking engine around it is ours.", options: { color: "6B7479" } },
  ], { x: Q(2.9), y: Q(4.9), w: Q(80), h: Q(6.5), fontFace: THEME.headFontFace, fontSize: 24, color: C.background2, valign: "top", margin: 0, lineSpacingMultiple: 0.98, isTextBox: true, objectName: "headline" });

  // 1600x900 blueprint coordinates → inches
  const V = (px) => px / 120;
  const OR = C.accent1;
  const TRAINED = new Set(["event-detector", "task-recognizer", "state-tracker", "flywheel"]); // learn from labeled recordings
  function abox(name, kind, x, y, w, h, title, subs, tsize = 11.5) {
    const st = {
      ours: { fill: "1F2326", line: { color: "E8EBE9", width: 1.1 }, tc: "E8EBE9", sc: "9AA3A7", tag: "OURS" },
      dim: { fill: "1A1D1F", line: { color: "4A5156", width: 1.1 }, tc: "C9CFCC", sc: "7D868B", tag: "OURS" },
      open: { fill: "2A2F32", line: { type: "none" }, tc: "C9CFCC", sc: "8A9397", tag: "OPEN MODEL" },
      rented: { fill: null, line: { color: "5E676C", width: 1.2, dashType: "dash" }, tc: "8A9397", sc: "6B7479", tag: "RENTED · SWAPPABLE" },
      hero: { fill: "23282B", line: { color: "E8EBE9", width: 2.25 }, tc: "FFFFFF", sc: "9AA3A7", tag: "OURS" },
      out: { fill: "FF5B14", line: { type: "none" }, tc: "16191B", sc: "16191B", tag: "" },
    }[kind];
    const runs = [{ text: title, options: { fontFace: SEMI, fontSize: tsize, color: st.tc, breakLine: true, paraSpaceAfter: 2 } }];
    subs.forEach((t, i) => runs.push({ text: t, options: { fontFace: THEME.bodyFontFace, fontSize: 8.5, color: st.sc, breakLine: i < subs.length - 1 } }));
    s.addText(runs, { shape: pres.ShapeType.roundRect, x: V(x), y: V(y), w: V(w), h: V(h), rectRadius: 0.06, fill: st.fill ? { color: st.fill } : { type: "none" }, line: st.line, valign: "top", margin: [kind === "hero" ? 12 : 9, 9, 4, 10], objectName: `box-${name}` });
    const trained = TRAINED.has(name);
    if (st.tag) s.addText(trained ? "OURS · TRAINED" : st.tag, { x: V(x + w - 250), y: V(y + 6), w: V(240), h: V(16), fontFace: LABEL, fontSize: 6.5, charSpacing: 1.5, color: trained ? "FF5B14" : st.sc, align: "right", valign: "middle", margin: 0, isTextBox: true, objectName: `box-${name}-tag` });
  }
  const aline = (pts, name, lit, dash) => poly(s, pts.map(([x, y]) => [V(x), V(y)]), { color: lit ? OR : "6B7479", width: lit ? 1.9 : 1.2, arrow: true, dash, name });
  const alab = (t, x, y, color = "9AA3A7", w = 220, align = "left") => s.addText(t, { x: V(x), y: V(y - 11), w: V(w), h: V(16), fontFace: t === t.toUpperCase() ? LABEL : THEME.bodyFontFace, fontSize: t === t.toUpperCase() ? 7.5 : 8.5, charSpacing: t === t.toUpperCase() ? 1 : 0, color, align, valign: "middle", margin: 0, isTextBox: true, objectName: "arrow-label" });

  abox("compiler", "ours", 560, 196, 480, 70, "Procedure compiler", ["manual → task graph · 8 procedures for $4.16"], 10.5);
  aline([[800, 266], [800, 298]], "arrow-compiler-tracker"); alab("task graph", 810, 288);
  alab("EVERY FRAME · ON THE DEVICE · ~50 MS", 46, 318, "FF5B14", 400);
  abox("camera", "ours", 46, 400, 150, 92, "Camera", ["first-person", "4 frames / s"], 11);
  abox("perception", "open", 236, 386, 170, 120, "Perception", ["SigLIP2", "V-JEPA 2 · hands"], 11);
  abox("event-detector", "ours", 430, 330, 170, 100, "Event detector", ["did a step end?"], 9.5);
  abox("task-recognizer", "ours", 430, 462, 170, 100, "Task recognizer", ["which job is it?"], 9.5);
  abox("state-tracker", "hero", 640, 300, 380, 290, "State tracker", ["where you are in the procedure", "Bayesian semi-Markov model"], 18);
  [0.03, 0.06, 0.14, 0.7, 0.12, 0.05, 0.03].forEach((p, i) => {
    const h = Math.max(4, (p * 150) / 0.7), bx = 668 + i * 46;
    s.addShape(pres.ShapeType.rect, { x: V(bx), y: V(548 - h), w: V(32), h: V(h), fill: { color: i === 3 ? "FF5B14" : "3A4044" }, line: { type: "none" }, objectName: `belief-bar-${i + 1}` });
    s.addText(`S${i + 1}`, { x: V(bx - 6), y: V(556), w: V(44), h: V(16), fontFace: LABEL, fontSize: 6.5, color: i === 3 ? "E8EBE9" : "6B7479", align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: `belief-label-${i + 1}` });
  });
  abox("policy", "ours", 1074, 386, 160, 120, "Policy", ["speak? verify?", "flag? ask?"], 11);
  abox("coach", "out", 1286, 398, 268, 96, "Coach", ["voice + HUD · speaks only", "when confident"], 13);
  aline([[196, 446], [234, 446]], "arrow-camera-perception", true);
  aline([[406, 420], [428, 392]], "arrow-perception-detector", true);
  aline([[406, 472], [428, 500]], "arrow-perception-recognizer", true);
  aline([[600, 380], [638, 380]], "arrow-detector-tracker", true);
  aline([[600, 512], [638, 512]], "arrow-recognizer-tracker", true);
  aline([[1020, 446], [1072, 446]], "arrow-tracker-policy", true);
  aline([[1234, 446], [1284, 446]], "arrow-policy-coach", true);
  s.addShape(pres.ShapeType.roundRect, { x: V(30), y: V(640), w: V(1540), h: V(190), rectRadius: 0.1, fill: { type: "none" }, line: { color: "2A2F32", width: 1.1, dashType: "sysDash" }, objectName: "band-slow" });
  alab("ONLY WHEN SOMETHING HAPPENS", 46, 664, "6B7479", 400);
  abox("flywheel", "dim", 236, 690, 360, 110, "Flywheel + local student", ["0.03 ms per check, free", "34% fewer frontier calls"], 10.5);
  abox("verifier", "rented", 640, 690, 380, 110, "Verifier", ["fast: Jev · 151 ms", "hard cases: Claude Opus · 3.8 s"], 10.5);
  abox("calibration", "dim", 1074, 690, 160, 110, "Calibration", ["error", "0.22 → 0.02"], 10.5);
  aline([[760, 590], [760, 688]], "arrow-tracker-verifier"); alab("14% of frames", 772, 636, "C9CFCC");
  aline([[1020, 745], [1072, 745]], "arrow-verifier-calibration");
  aline([[1154, 690], [1154, 615], [960, 615], [960, 592]], "arrow-calibration-tracker"); alab("evidence", 1166, 640);
  aline([[596, 745], [638, 745]], "arrow-student-verifier");
  aline([[700, 590], [700, 612], [416, 612], [416, 688]], "arrow-tracker-flywheel", false, "dash"); alab("session records", 428, 640);
  // legend
  let lx = 46;
  [["ours", "Ours"], ["open", "Open model, on device"], ["rented", "Rented, swappable"]].forEach(([k, t]) => {
    const o = { x: V(lx), y: V(853), w: V(26), h: V(15), rectRadius: 0.02, objectName: `legend-${k}` };
    if (k === "ours") s.addShape(pres.ShapeType.roundRect, { ...o, fill: { color: "1F2326" }, line: { color: "E8EBE9", width: 1 } });
    if (k === "open") s.addShape(pres.ShapeType.roundRect, { ...o, fill: { color: "2A2F32" }, line: { type: "none" } });
    if (k === "rented") s.addShape(pres.ShapeType.roundRect, { ...o, fill: { type: "none" }, line: { color: "5E676C", width: 1, dashType: "dash" } });
    alab(t, lx + 36, 861, "9AA3A7", 230);
    lx += 36 + { ours: 70, open: 220, rented: 200 }[k];
  });
  alab("OURS · TRAINED: gets better with more labeled recordings", 650, 861, "FF5B14", 470);
  s.addNotes("Walk it left to right along the orange path, which is what happens on every frame, on the device, in about 50 ms: open models turn the frame into features, our detector and recognizer feed our state tracker, and the policy decides whether the coach says anything. Below, in the dark, is the only rented part: on 14% of frames the tracker asks a verifier one typed question (Jev in 151 ms, Claude Opus for hard cases). We calibrate the answer and feed it back. Every session trains our local student, which already handles routine checks. Swapping the rented model is a one-line config change. The four boxes tagged TRAINED learn from labeled recordings; they are what the data and GPU money improves.");
}

// ---------- Evidence ----------
function sEvidence() {
  const s = pres.addSlide({ masterName: "Praxis Split", sectionTitle: "Story" });
  s.addShape(pres.ShapeType.rect, { x: 0, y: 0, w: 7.2, h: 7.5, fill: { color: C.text1 }, line: { type: "none" }, objectName: "results-panel" });
  const chartLabel = (t, y) => mono(s, t, { x: 0.5, y, w: 6.2, h: 0.3, fontSize: 11, color: C.accent6 });
  chartLabel("STEP ACCURACY · SAME FRONTIER MODEL", 0.75);
  s.addChart(pres.ChartType.bar, [{ name: "Step accuracy", labels: ["Model every 5 s", "Praxis"], values: [48, 54] }],
    { ...darkChart(""), showTitle: false, chartColors: ["4A5156", "FF5B14"], x: 0.5, y: 1.05, w: 6.2, h: 2.4, valAxisMaxVal: 70, valAxisMinVal: 0, dataLabelFormatCode: '0"%"', objectName: "chart-accuracy" });
  chartLabel("COST PER MINUTE OF VIDEO", 3.95);
  s.addChart(pres.ChartType.bar, [{ name: "Cost per video-minute", labels: ["Model every 5 s", "Praxis"], values: [0.085, 0.018] }],
    { ...darkChart(""), showTitle: false, chartColors: ["4A5156", "9AA3A7"], x: 0.5, y: 4.25, w: 6.2, h: 2.4, valAxisMaxVal: 0.11, valAxisMinVal: 0, dataLabelFormatCode: '"$"0.000', objectName: "chart-cost" });
  s.addText(eb("EVIDENCE"), { placeholder: "eyebrow" });
  s.addText("Same frontier model, with our tracking: 13% more accurate at a fifth of the cost", { placeholder: "title" });
  line(s, 7.85, 3.6, 12.83, 3.6, { color: C.text1, width: 1.5, name: "result-rule" });
  tb(s, "1/5", { x: 7.85, y: 3.8, w: 4.98, h: 1.3, fontFace: HEAD, fontSize: 80, color: C.text1 });
  tb(s, "the cost per minute of video, and more accurate.", { x: 7.85, y: 5.15, w: 4.98, h: 0.8, fontSize: 18 });
  footer(s, 5, "48 held-out public clips · one run each", 7.85);
  s.addNotes("Like-for-like: the same frontier model on the same frames. Called every 5 seconds with no memory of the task, it names the current step on 48% of frames; with our tracking around it, 54% (6 points more), at $0.018 vs $0.085 per video-minute. The baseline is a call every 5 seconds, not every frame. With our distilled local model doing routine checks: 52% at $0.008, 11x cheaper. When the view was blurred or blocked it asked for a better view on 77-98% of checks and was never confidently wrong. Caveats to say out loud: one run per system, public cooking video. Procedures are procedures; maintenance footage is the first thing the grant buys.");
}

// ---------- Why now ----------
function sWhyNow() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("WHY NOW", { placeholder: "eyebrow" });
  s.addText("Smart glasses took off, and AI keeps getting cheaper", { placeholder: "title" });
  const top = 1.8, base = 5.05;
  const panel = (x, w, label, big, bigCol, cap, bw = 1.6) => {
    line(s, x, top, x + w, top, { color: C.text1, width: 1.5, name: "panel-rule" });
    mono(s, label, { x, y: top + 0.15, w, h: 0.3, fontSize: 10.5, color: C.text1 });
    tb(s, big, { x, y: top + 0.5, w: bw, h: 0.75, fontFace: HEAD, fontSize: 44, color: bigCol });
    tb(s, cap, { x: x + bw + 0.05, y: top + 0.62, w: w - bw - 0.05, h: 0.6, fontSize: 13, color: BODY, valign: "middle" });
  };
  // left: AI glasses shipped a year (to scale)
  const L = { x: 0.5, w: 5.93 };
  panel(L.x, L.w, "AI GLASSES SHIPPED A YEAR", "7×", C.text1, "more glasses in two years. Every pair is a camera we can run on");
  const gl = [["2024", 2.06, "2.1M"], ["2025", 8.7, "8.7M"], ["2026 FORECAST", 15, "15M+"]];
  const bw = 1.1, gap = (L.w - 3 * bw) / 3, maxH = 1.35;
  gl.forEach(([yr, v, lab], i) => {
    const h = maxH * v / 15, x = L.x + gap / 2 + i * (bw + gap), now = i === 2;
    s.addShape(pres.ShapeType.rect, { x, y: base - h, w: bw, h, fill: { color: now ? C.accent1 : i === 1 ? "5E676C" : "9AA3A7" }, line: { type: "none" }, objectName: "glasses-bar" });
    tb(s, lab, { x: x - 0.3, y: base - h - 0.4, w: bw + 0.6, h: 0.36, fontFace: HEAD, fontSize: 17, align: "center", color: now ? C.accent2 : C.text1 });
    mono(s, yr, { x: x - 0.4, y: base + 0.08, w: bw + 0.8, h: 0.26, fontSize: 9.5, align: "center", color: C.text2 });
  });
  line(s, L.x, base, L.x + L.w, base, { color: C.text1, width: 1, name: "glasses-base" });
  // right: cost to watch one hour of work
  const R = { x: 6.9, w: 5.93 };
  panel(R.x, R.w, "PRICE OF THE SAME AI, PER MILLION TOKENS", "1,000×", C.accent2, "cheaper in three years, about 10× every year", 3.3);
  [["2021 · GPT-3 at launch", 60, "$60"], ["2024 · same capability", 0.06, "$0.06"]].forEach(([lab, v, val], i) => {
    const y = 3.65 + i * 0.62, bx = R.x + 2.25, bwid = Math.max(0.05, 2.8 * v / 60), now = i === 1;
    tb(s, lab, { x: R.x, y, w: 2.15, h: 0.4, fontSize: 12.5, color: now ? C.text1 : BODY, valign: "middle", fontFace: now ? SEMI : "Archivo" });
    s.addShape(pres.ShapeType.rect, { x: bx, y: y + 0.07, w: bwid, h: 0.26, fill: { color: now ? C.accent1 : "9AA3A7" }, line: { type: "none" }, objectName: "price-bar" });
    tb(s, val, { x: bx + bwid + 0.12, y, w: 1.2, h: 0.4, fontFace: HEAD, fontSize: 16, valign: "middle", color: now ? C.accent2 : C.text1 });
  });
  tb(s, "So a coach that watches a whole shift is finally affordable.", { x: R.x, y: base + 0.05, w: R.w, h: 0.3, fontSize: 12.5, color: BODY });
  // bottom: the dates
  const ev = [["MAY 2026", "Autodesk buys MaintainX, a maintenance app, for $3.6B"], ["SEPT 2026", "Meta opens its glasses' camera to outside apps", true], ["NOV 2026", "Android XR glasses reported to ship"], ["Q1 2027", "Viture + NVIDIA coaching glasses ship"]];
  const cw = 12.33 / 4, TL = 5.75;
  line(s, 0.5, TL, 12.83, TL, { color: C.accent6, width: 1, name: "timeline" });
  ev.forEach(([d, t, hl], i) => {
    const x = 0.5 + i * cw;
    s.addShape(pres.ShapeType.ellipse, { x, y: TL - 0.08, w: 0.16, h: 0.16, fill: { color: hl ? C.accent1 : C.text1 }, line: { type: "none" }, objectName: "timeline-dot" });
    mono(s, d, { x, y: TL + 0.16, w: cw - 0.2, h: 0.26, fontSize: 9.5, color: C.text1 });
    tb(s, t, { x, y: TL + 0.43, w: cw - 0.3, h: 0.55, fontSize: 12, color: BODY });
  });
  footer(s, 0, "Omdia (2025 shipments, +322%; 2026 forecast) · a16z, LLMflation (Nov 2024) · Autodesk, Meta, 9to5Google, Viture releases");
  s.addNotes("Two curves crossed this year, and both are market-wide, not ours. Cameras moved onto faces: Omdia counts 8.7M AI glasses shipped in 2025, up 322%, and forecasts more than 15M in 2026, about 7x in two years (2024 is backed out from the growth rate). And AI got cheap: a16z measured the price of GPT-3-level capability falling from $60 per million tokens at launch in 2021 to $0.06 in 2024, a 1,000x drop in three years, about 10x a year. That's the market trend. Our own design adds to it (that's on the measured slide): Praxis only asks a model when something happens, so it runs at about $1.08 an hour of video vs $5.10 for calling a frontier model every 5 seconds. Meanwhile the money showed up: Autodesk is paying $3.6B for MaintainX, and Meta opened its glasses' camera to outside apps in September, so a small software company can build on hardware millions of people already wear. Why not 2023: no glasses let apps read the camera, and coaching cost more than the price.");
}

// ---------- Market ----------
function sMarket() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("MARKET + PRICING · US, PER YEAR", { placeholder: "eyebrow" });
  s.addText("A $306M wedge in a $1.8B first market,\nin a $9B one", { placeholder: "title" });
  const rows = [
    ["TAM", 9.2, "$9.2B", "15.4M US workers who follow written procedures", "C2C8C5"],
    ["SAM", 1.8, "$1.8B", "2.47M US maintenance and repair techs", "9AA3A7"],
    ["WEDGE", 0.306, "$306M", "~255k new maintenance techs a year, coached", C.accent1],
    ["YEAR 3", 0.0045, "$4.5M ARR", "~3,750 new techs, about 150 teams", C.text1],
  ];
  const maxW = 4.9;
  rows.forEach(([k, v, big, cap, col], i) => {
    const y = 2.3 + i * 1.1, bw = Math.max(0.05, maxW * v / 9.2);
    mono(s, k, { x: 0.5, y, w: 1.1, h: 0.42, fontSize: 11, color: C.text1, valign: "middle" });
    s.addShape(pres.ShapeType.rect, { x: 1.65, y, w: bw, h: 0.42, fill: { color: col }, line: { type: "none" }, objectName: `bar-${k.toLowerCase()}` });
    tb(s, big, { x: 1.65 + bw + 0.15, y, w: 2.2, h: 0.42, fontFace: HEAD, fontSize: 20, color: k === "WEDGE" ? C.accent2 : C.text1, valign: "middle" });
    tb(s, cap, { x: 1.65, y: y + 0.5, w: 6.2, h: 0.4, fontSize: 14, color: BODY });
  });
  const x = 8.35, w = 4.48, Y = 2.3, ph = 4.4;
  s.addShape(pres.ShapeType.roundRect, { x, y: Y, w, h: ph, rectRadius: 0.05, fill: { color: C.text1 }, line: { type: "none" }, objectName: "panel-pricing" });
  mono(s, "HOW WE CHARGE", { x: x + 0.4, y: Y + 0.3, w: w - 0.8, h: 0.3, fontSize: 11, color: C.accent1 });
  [
    ["A short paid pilot", "with a metric agreed up front. The fee counts toward year one"],
    ["$200 per new-tech seat a month", "billed annually, unlimited sessions. When they work alone, the seat moves to the next hire"],
    ["One-time setup per procedure", "we compile and check the shop's own manuals"],
    ["$50 a month for every tech, next", "skills records for the whole team"],
  ].forEach(([a, b], i) => {
    const y = Y + 0.75 + i * 0.9;
    if (i) line(s, x + 0.4, y - 0.12, x + w - 0.4, y - 0.12, { color: "3A4044", width: 0.75, name: "price-sep" });
    tb(s, [{ text: a, options: { fontFace: SEMI, fontSize: 15, color: i === 1 ? C.accent1 : C.background2, breakLine: true } }, { text: b, options: { fontSize: 12.5, color: C.accent6 } }], { x: x + 0.4, y, w: w - 0.8, h: 0.75 });
  });
  footer(s, 0, `BLS OEWS national tables, May 2025 · prices are our hypotheses, anchored on Tulip's $100–250 per station a month · year 3 is a goal · math in appendix ${ref(aMarketMath)}`);
  s.addNotes("Bars are to scale. TAM: 15.4M US workers who follow written procedures, at $50 a month for verified records, about $9.2B. SAM: 2.47M US maintenance and repair techs, coaching for new hires plus records for everyone, about $1.8B. The wedge we sell first: about 255,000 new maintenance techs a year coached for six months at $200 a month, about $306M. Year 3 target: 1.5% of new techs, about 3,750 new techs across 150 teams, $4.5M ARR. How we charge: a short paid pilot with a metric agreed up front, and the pilot fee is credited to year one; then an annual subscription at $200 per new-tech seat per month, billed annually, with unlimited sessions. A seat belongs to whoever is being coached: when a new tech works alone (about six months), the seat moves to the next new hire. Glasses are the customer's, and several new techs can share one pair across shifts, because we charge per seat, not per device. Plus a one-time setup per procedure; and next, $50 per tech per month for verified records across the whole team. Prices are our hypotheses, anchored on Tulip's published $100-250 per station per month. The records price is not yet validated (it's 82% of the SAM). Not counted: other countries, aviation, field service outside these groups, robotics.");
}

// ---------- Why not consumers ----------
function sConsumers() {
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Market" });
  s.addText(eb("THE OBVIOUS QUESTION"), { placeholder: "eyebrow" });
  s.addText("Why not consumers first? Because the budget\nand the repeat data are in business", { placeholder: "title" });
  hero(s, G2.x[0], 2.75, G2.w, "$3.6B", "what Autodesk agreed to pay for MaintainX, an app that puts maintenance procedures on a phone.", { size: 64, capSize: 18 });
  hero(s, G2.x[1], 2.75, G2.w, "$99 → $25", "what Frontdoor's expert video help for homeowners fell to, per year, from 2023 to 2024.", { size: 64, capSize: 18 });
  line(s, 0.5, 5.45, 12.83, 5.45, { color: C.accent6, width: 0.75, name: "consumer-rule" });
  tb(s, [{ text: "The same checklist runs on every machine, every month. ", options: { fontFace: SEMI } }, { text: "Home tasks don't repeat, and the platforms give consumer help away free. Consumers come last." }], { x: 0.5, y: 5.6, w: 12.33, h: 0.9, fontSize: 17 });
  footer(s, 9, "Autodesk–MaintainX release (28 May 2026) · Frontdoor pricing 2023–2024");
  s.addNotes("Home tasks happen a few times a year, and Meta, Google and Apple will give consumer help away free. Consumers come last, once glasses are everywhere and our models run on the device. This is a choice about order, not size. In maintenance someone signs a budget, the same procedure repeats so the data compounds, ROI shows up in a 30-day pilot. Consumer tasks are a long tail; on open-ended tasks our system is weakest (it named 0 of 7 unseen recipes from video alone). Consumers return in the last phase of the vision.");
}

// ---------- Founder ----------
function sFounder() {
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Team" });
  s.addText(eb("WHY ME"), { placeholder: "eyebrow" });
  s.addText("I've built real-time vision on messy video before,\nand I built this in a week", { placeholder: "title" });
  [
    ["LipTrac", "Real-time lip reading from ordinary video. 60,000+ frames, 12 testers, provisional patent filed.", C.text1],
    ["7 years", "of competitive robotics, coaching teammates without seeing what they see.", C.text1],
    ["1 week", "to build the engine, a 48-video eval and a live app, solo. First commit Oct 17.", C.text1],
  ].forEach(([b, c, col], i) => hero(s, G3.x[i], 2.75, G3.w, b, c, { color: col, size: 44, capSize: 18, capH: 1.6 }));
  line(s, 0.5, 5.65, 12.83, 5.65, { color: C.accent6, width: 0.75, name: "bio-rule" });
  tb(s, "Monish Saravana · Harvard College · solo founder. Also: path planning for oil-cleanup boats from aerial imagery.", { x: 0.5, y: 5.8, w: 12.33, h: 0.4, fontSize: 15, color: BODY });
  footer(s, 12, "Startups @ Harvard application");
  s.addNotes("Solo founder is a known risk: the grant tests demand before hiring, and first hires come after the pilot. The provisional patent is LipTrac's, filed before this application. Next step on domain: shadow a maintenance tech and recruit an advisor from the outreach replies.");
}

// ---------- How far along (1/2): built, with real screenshots ----------
function sBuilt() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("HOW FAR ALONG · BUILT", { placeholder: "eyebrow" });
  s.addText("A shop uploads the manuals it already has.\nPraxis turns each procedure into a coach", { placeholder: "title" });
  const SC = (f) => path.join(__dirname, "assets", "screens", f);
  const shot = (file, x, y, w, ratio) => {
    const h = w / ratio;
    s.addShape(pres.ShapeType.rect, { x: x - 0.01, y: y - 0.01, w: w + 0.02, h: h + 0.02, fill: { color: "FFFFFF" }, line: { color: "B9C0BC", width: 0.75 }, objectName: "shot-frame" });
    s.addImage({ path: SC(file), x, y, w, h, objectName: "screenshot" });
    return y + h;
  };
  const badge = (n, x, y) => {
    s.addShape(pres.ShapeType.ellipse, { x, y, w: 0.3, h: 0.3, fill: { color: C.text1 }, line: { type: "none" }, objectName: "step-badge" });
    tb(s, String(n), { x, y, w: 0.3, h: 0.3, fontFace: SEMI, fontSize: 11, color: "FFFFFF", align: "center", valign: "middle" });
  };
  const cap = (n, x, y, w, head, body) => {
    badge(n, x, y + 0.02);
    tb(s, [{ text: head, options: { fontFace: SEMI, color: C.text1, breakLine: true } }, { text: body, options: { color: BODY } }], { x: x + 0.45, y, w: w - 0.45, h: 0.95, fontSize: 13 });
  };
  const L = 0.5, LW = 4.4, R = 5.3, RW = 7.53;
  const ly = shot("backend-documents.png", L, 2.2, LW, 1660 / 430);
  cap(1, L, ly + 0.22, LW, "Upload the manuals", "A 97-page safety manual is indexed in 0.34 s on a laptop, for $0. Its procedures are found automatically.");
  cap(2, L, ly + 1.27, LW, "Review the coached steps", "Each procedure compiles for about $0.19, with cards quoted from the manual. A manager approves it first.");
  cap(3, L, ly + 2.32, LW, "Coach through smart glasses", "Live tracking and voice control, with Meta and Viture glasses connections and screen or voice-only modes.");
  shot("backend-procedure.png", R, 2.2, RW, 2320 / 1310);
  footer(s, 0, "Screenshots of the Praxis company backend · Hydro Plant demo: public Reclamation FIST manuals · ENIGMA-51 repair procedures");
  s.addNotes("This is the product a company actually touches, running today. One: a manager uploads the manuals they already have. Here it's three public Bureau of Reclamation maintenance manuals, 97 to 222 pages; each is parsed and indexed on the laptop in under 2 seconds, nothing is sent to a model, and it finds the likely procedures. Two: they pick a procedure and Praxis compiles it into coached steps for about 16 to 19 cents, with knowledge cards quoted from the manual and the page cited; the manager reviews, edits and approves before any technician sees it. Three: the technician is coached live through smart glasses, by voice or on the glasses' screen depending on the model. Say out loud: the Meta and Viture glasses connections are built but not yet tested on the devices; that's part of what the grant buys.");
}

// ---------- Live demo: real repair footage, the model's own output (renders/demo, praxis.render.reel) ----------
const VID = (f) => path.join(__dirname, "assets", "video", f);
const poster = (f) => "data:image/png;base64," + fs.readFileSync(VID(f)).toString("base64");
function video(s, name, x, y, w) {
  const h = w * 9 / 16;
  s.addMedia({ type: "video", path: VID(`${name}.mp4`), cover: poster(`${name}_poster.png`), x, y, w, h, objectName: "demo-video" });
  return y + h;
}
function sLive() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("HOW FAR ALONG · LIVE", { placeholder: "eyebrow" });
  s.addText("A live session on a real repair job.\nEvery card on screen is the model's own output", { placeholder: "title" });
  video(s, "repair_demo_user", 0.5, 2.3, 7.82);
  const x = 8.7, w = 4.13;
  [["0:00", "Starts from the lab's written procedure. It was never trained on this task."],
   ["0:26", "The fast model suspects a missed button. Opus checks and clears it, so no false alarm."],
   ["2:52", "Safety-critical step: it reads the iron at 215 °C and tells the tech to go back to 200."],
   ["3:37", "Follows the resolder, step by step."]].forEach(([t, b], i) => {
    const y = 2.3 + i * 0.98;
    line(s, x, y, x + w, y, { color: C.text1, width: i ? 0.75 : 1.5, name: "beat-rule" });
    tb(s, t, { x, y: y + 0.14, w: 0.8, h: 0.3, fontFace: SEMI, fontSize: 14, color: C.accent2, objectName: "beat-time" });
    tb(s, b, { x: x + 0.8, y: y + 0.12, w: w - 0.8, h: 0.8, fontSize: 13.5, color: BODY, objectName: "beat-text" });
  });
  mono(s, "ENIGMA-51 · REAL REPAIR LAB · 16-MINUTE LIVE SESSION · $0.17", { x, y: 6.35, w, h: 0.3, fontSize: 9.5 });
  footer(s, 0, "Praxis Studio live session on ENIGMA-51 video 141 (first-person high-voltage board repair) · renders/demo/README.md");
  s.addNotes("Click to play; it's 49 seconds. This is real footage from an industrial repair lab (the ENIGMA-51 dataset), streamed through Praxis live: the fast tier is Jev, and Claude Opus double-checks when the fast model is unsure. Every card is drawn from the session's log at the time it happened. The cut only picks moments, and each frame shows its session time. The procedure was compiled from the lab's written instructions, and the models were never trained on this task. Say plainly if asked: these are selected moments. Across the whole 16-minute session it confirmed 1 of 19 steps and agreed with proxy step labels 29% of the time. The overshoot alert came about 6 seconds after the frame it checked, while it waited on Opus, and by then the tech had already pressed DOWN back to 200. A second alert later in the session was a false alarm and is left out. The engineer view of the same session is in the appendix.");
}

// ---------- How far along (2/2): what works, measured, and the bottleneck ----------
function sWorks() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("HOW FAR ALONG · MEASURED", { placeholder: "eyebrow" });
  s.addText("It already beats a frontier model on its own.\nThe bottleneck is maintenance data", { placeholder: "title" });
  const stats = [
    ["13% more", "accurate at tracking the step than the same frontier model called every 5 seconds", C.accent2],
    ["1/5 the cost", "$0.018 vs $0.085 per minute of video, because it only asks a model when something happens", C.text1],
    ["11 of 15", "technician questions on an industrial repair job answered correctly from the company's own manuals", C.text1],
    ["0", "times confidently wrong when the view was blurred or blocked. It asks for a better view instead", C.text1],
  ];
  const cw = 3.6, gx = 0.35;
  stats.forEach(([b, c, col], i) => {
    const x = 0.5 + (i % 2) * (cw + gx), y = 2.3 + Math.floor(i / 2) * 2.2;
    line(s, x, y, x + cw, y, { color: C.text1, width: 1.5, name: "stat-rule" });
    tb(s, b, { x, y: y + 0.2, w: cw, h: 0.7, fontFace: HEAD, fontSize: 34, color: col, objectName: "works-stat" });
    tb(s, c, { x, y: y + 0.95, w: cw - 0.1, h: 1.0, fontSize: 14, color: BODY, objectName: "works-caption" });
  });
  const x = 8.35, w = 4.48, Y = 2.3, ph = 4.4;
  s.addShape(pres.ShapeType.roundRect, { x, y: Y, w, h: ph, rectRadius: 0.05, fill: { color: C.text1 }, line: { type: "none" }, objectName: "panel-bottleneck" });
  mono(s, "THE BOTTLENECK: DATA", { x: x + 0.4, y: Y + 0.32, w: w - 0.8, h: 0.3, fontSize: 11, color: C.accent1 });
  tb(s, "First-person video of real maintenance work isn't sold off the shelf. So we collect it:", { x: x + 0.4, y: Y + 0.78, w: w - 0.8, h: 0.85, fontSize: 15, color: C.background2, objectName: "bottleneck-lead" });
  tb(s, [
    { text: "Pay students at trade schools to wear glasses on real jobs", options: { bullet: { indent: 14 }, breakLine: true, paraSpaceAfter: 8 } },
    { text: "Label it with our own step-marking tool", options: { bullet: { indent: 14 }, breakLine: true, paraSpaceAfter: 8 } },
    { text: "Every pilot adds more, with the customer's consent", options: { bullet: { indent: 14 } } },
  ], { x: x + 0.4, y: Y + 1.72, w: w - 0.8, h: 1.6, fontSize: 13.5, color: C.accent6, objectName: "bottleneck-items" });
  line(s, x + 0.4, Y + 3.4, x + w - 0.4, Y + 3.4, { color: C.accent1, width: 1.5, name: "bottleneck-rule" });
  tb(s, "About 80 hours of footage for $2,000, then GPU time to retrain.", { x: x + 0.4, y: Y + 3.52, w: w - 0.8, h: 0.75, fontSize: 15, fontFace: SEMI, color: C.background2, objectName: "bottleneck-fix" });
  footer(s, 0, "48 held-out clips of public first-person procedure video · one run per system · questions: ENIGMA-51 industrial repair, blind-judged");
  s.addNotes("Measured, not claimed. 13% more accurate is relative: if asked, with the task known Praxis names the current step 54% of the time vs 48% for the same frontier model called every 5 seconds with no memory, at about a fifth of the cost ($0.018 vs $0.085 per video-minute). On an industrial repair dataset (ENIGMA-51) it answered 11 of 15 technician questions correctly from the uploaded procedures, 2 partly, 2 wrong, blind-judged; on spec questions like 'what voltage do I set?', the same model without the manual got 0 of 4, with it 4 of 4. When we blurred or blocked the view, it asked for a better view on 77-98% of checks and was never confidently wrong. If asked what the step-tracking eval is: 48 held-out clips of a public first-person procedure dataset (CaptainCook4D, which is cooking), with the dataset's own labels. Say it plainly. The bottleneck is data. Labeled first-person maintenance video isn't sold off the shelf, and most academic first-person datasets are non-commercial. So we collect it: students at trade schools are paid to wear glasses on real jobs (contributor rates for first-person recording run about $15-30 an hour in the US, so $2,000 is roughly 80 hours at ~$25), we label it with the step-marking tool already in the backend, and every pilot adds more with consent. More video keeps helping: the step models went from 31% to 51% held-out accuracy from 1 to 9 recordings, still rising. Mistake alerts named a real error 4 of 17 times; that needs real maintenance examples.");
}

// ---------- Competitors, as workflows ----------
function sWorkflow() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("COMPETITORS", { placeholder: "eyebrow" });
  s.addText("Rolling out a new procedure: what it takes\ntoday, and what it takes with Praxis", { placeholder: "title" });
  const rows = [
    ["Procedure apps", "MaintainX, Augmentir", ["Type the steps into the app", "The tech reads them on a phone", "Ticks a box when done"], "Nobody sees whether the step was done right", false],
    ["Fixed cameras", "Retrocausal, Invisible AI", ["Mount a camera at one workstation", "Record and label runs to train it", "It watches that one station"], "Can't follow a tech around a machine", false],
    ["First-person AI glasses", "Strivr, Viture + NVIDIA", ["Their team films your procedures", "They train a model for your site", "Coach through their glasses"], "Filming and training for every customer", false],
    ["Praxis", "", ["Upload the manual you already have", "Approve the coached steps, about $0.19 each", "Coach through smart glasses"], "Verified and recorded, with no filming", true],
  ];
  const nameW = 2.45, chipW = 2.2, arrW = 0.32, outW = 12.33 - nameW - 3 * chipW - 3 * arrW, rh = 0.86, gap = 0.2;
  rows.forEach(([name, ex, chips, out, ours], i) => {
    const y = 2.3 + i * (rh + gap) + (ours ? 0.12 : 0);
    if (ours) {
      s.addShape(pres.ShapeType.rect, { x: 0.5, y: y - 0.1, w: 12.33, h: rh + 0.2, fill: { color: C.background1 }, line: { type: "none" }, objectName: "row-ours" });
      s.addShape(pres.ShapeType.rect, { x: 0.5, y: y - 0.1, w: 0.06, h: rh + 0.2, fill: { color: C.accent1 }, line: { type: "none" }, objectName: "row-ours-edge" });
    }
    tb(s, ex ? [{ text: name, options: { fontFace: SEMI, fontSize: 14, color: C.text1, breakLine: true } }, { text: ex, options: { fontSize: 11, color: BODY } }]
      : [{ text: name, options: { fontFace: SEMI, fontSize: 16, color: C.accent2 } }], { x: 0.7, y, w: nameW - 0.25, h: rh, valign: "middle" });
    chips.forEach((t, j) => {
      const cx = 0.5 + nameW + j * (chipW + arrW);
      s.addText(t, { shape: pres.ShapeType.roundRect, x: cx, y, w: chipW, h: rh, rectRadius: 0.06, fill: { color: ours ? "FFFFFF" : C.background1 }, line: ours ? { color: C.accent1, width: 1.5 } : { color: "C2C8C5", width: 0.75 }, fontFace: "Archivo", fontSize: 12.5, color: C.text1, align: "center", valign: "middle", margin: [4, 8, 4, 8], objectName: "workflow-step" });
      const ax = cx + chipW + 0.06;
      line(s, ax, y + rh / 2, ax + arrW - 0.12, y + rh / 2, { color: ours ? C.accent1 : "9AA3A7", width: 1.5, arrow: true, name: "workflow-arrow" });
    });
    const ox = 0.5 + nameW + 3 * (chipW + arrW);
    s.addShape(pres.ShapeType.ellipse, { x: ox + 0.05, y: y + rh / 2 - 0.08, w: 0.16, h: 0.16, fill: { color: ours ? C.accent3 : C.accent5 }, line: { type: "none" }, objectName: "outcome-dot" });
    tb(s, out, { x: ox + 0.32, y, w: outW - 0.32, h: rh, fontSize: 13, fontFace: ours ? SEMI : "Archivo", color: ours ? C.text1 : BODY, valign: "middle", objectName: "workflow-outcome" });
  });
  footer(s, 0, `Vendor product pages and docs, checked 17 Oct 2026 · Retrocausal: record, label, train · Strivr: per-customer capture and model · detail in appendix ${ref(aCompetitors)}`);
  s.addNotes("Same job, four ways: a shop wants new technicians coached through a procedure. With a procedure app like MaintainX, someone types the steps in, the tech reads them and ticks boxes; a checkbox isn't proof. Fixed cameras like Retrocausal watch the work, but you mount a camera at one workstation, record and label runs and train it, and it can't follow a tech around a machine. The closest are first-person AI glasses: Strivr's data team films your procedures and trains a model per customer, it's in early access with no published accuracy, and Viture with NVIDIA sells $600 safety glasses shipping in Q1 2027. With Praxis you upload the manual you already have, approve the coached steps for about 19 cents each, and coach through smart glasses the shop buys off the shelf, with every critical step verified and recorded. Honest version: Tulip, Augmentir and Squint also compile instructions, and fixed-camera vendors are ahead of us on live mistake detection today.");
}

// ---------- Big Tech glasses ----------
function sBigTech() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("WHY NOBODY OWNS THIS NICHE", { placeholder: "eyebrow" });
  s.addText("Meta, Google and Apple won't specialize, so we will.\nTheir glasses become our hardware", { placeholder: "title" });
  [
    ["15M+", "AI glasses forecast to ship this year. Every pair is a camera we can run on, and we pay $0 to build it."],
    ["Sept 2026", "Meta opened its glasses' camera to outside apps. The platforms want specialists building on top."],
    ["$0", "What Meta AI and Gemini Live charge consumers to look through the camera and help. We don't sell against free."],
  ].forEach(([b, c], i) => statCol(s, G3.x[i], 2.3, G3.w, b, c, { size: 32, capH: 1.0 }));
  const y = 4.3, h = 1.5, half = 12.33 / 2;
  s.addShape(pres.ShapeType.roundRect, { x: 0.5, y, w: 12.33, h, rectRadius: 0.05, fill: { color: C.text1 }, line: { type: "none" }, objectName: "panel-platforms" });
  line(s, 0.5 + half, y + 0.25, 0.5 + half, y + h - 0.25, { color: "3A4044", width: 1, name: "panel-divider" });
  [["THEY BUILD FOR EVERYONE", C.accent6, "Glasses, cameras and one free general assistant that answers questions about a single frame."],
   ["WE BUILD FOR ONE TRADE", C.accent1, "A coach for maintenance teams: their own procedures, step-by-step state, verified records, a pilot on site."]].forEach(([k, col, b], i) => {
    const px = 0.5 + i * half + 0.4;
    tb(s, [{ text: k, options: { fontFace: MONO, fontSize: 10.5, charSpacing: 1, color: col, breakLine: true, paraSpaceAfter: 6 } }, { text: b, options: { fontSize: 16, color: C.background2 } }], { x: px, y: y + 0.25, w: half - 0.8, h: h - 0.35, objectName: "panel-platforms-text" });
  });
  line(s, 0.5, 6.05, 12.83, 6.05, { color: C.accent6, width: 0.75, name: "consumer-rule" });
  tb(s, [{ text: "That's also why we don't start with consumers. ", options: { fontFace: SEMI } }, { text: "Consumer help is their turf and they give it away free. In a maintenance shop someone pays, and the same checklist runs every month." }], { x: 0.5, y: 6.15, w: 12.33, h: 0.6, fontSize: 14.5 });
  footer(s, 0, "Omdia AI-glasses forecast · Meta Wearables Device Access Toolkit 1.0 · Meta AI and Gemini Live product pages · Apple glasses reported for 2027");
  s.addNotes("We're not competing with Meta, Google or Apple; we're riding them. They're paying to put cameras on faces: EssilorLuxottica sold over 7M AI glasses in 2025, and Omdia forecasts more than 15M in 2026. Meta's toolkit gives a third-party app the glasses' camera, mic and speakers. Android XR glasses are reported for November; Apple's for 2027, not announced. They build one general assistant for everyone. They don't do one trade's procedures, records and on-site pilots. If asked for evidence that big companies don't stay in this niche: Microsoft is retiring Dynamics 365 Guides, its HoloLens app for step-by-step work instructions, on Dec 31, and PTC retired Vuforia Chalk in 2025. That's also why we're not consumer first: consumer help is their turf and they give it away. Meta AI on the glasses and Gemini Live's camera mode are free. Even paid expert help collapsed: Frontdoor's expert video help for homeowners fell from $99 to $25 a year. Home tasks don't repeat, and there's no budget owner. In maintenance someone signs, the procedure repeats so the data compounds. If Meta ships a general coach anyway, it answers about one frame, and we still run on their glasses.");
}

// ---------- Savings, price + go-to-market ----------
function sBusiness() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("SAVINGS + MARKETING PLAN", { placeholder: "eyebrow" });
  s.addText("A new tech costs $10–15k to hire and ramp up.\nA seat is $200 a month. One saved hour covers it", { placeholder: "title" });
  statCol(s, G3.x[0], 2.3, G3.w, "$10–15k", "to hire and ramp up one maintenance tech today", { size: 40 });
  statCol(s, G3.x[1], 2.3, G3.w, "$200", "a month per seat for each new tech, billed annually. Unlimited sessions; the seat moves to the next new hire", { size: 40, color: C.accent2, capH: 1.1 });
  statCol(s, G3.x[2], 2.3, G3.w, "1 hour", "a week of a senior tech's time ($44) is what a seat costs, so saving one hour a week pays for it", { size: 40, capH: 1.1 });
  // How we get customers: its own card, so it reads apart from the savings math above
  const gy = 4.5, gh = 2.2;
  s.addShape(pres.ShapeType.roundRect, { x: 0.5, y: gy, w: 12.33, h: gh, rectRadius: 0.05, fill: { color: C.background1 }, line: { color: "C2C8C5", width: 0.75 }, objectName: "gtm-card" });
  mono(s, "MARKETING + SALES PLAN", { x: 0.85, y: gy + 0.25, w: 5, h: 0.3, fontSize: 11, color: C.accent2 });
  mono(s, "OUTREACH → DEMO → PAID PILOT → ANNUAL SEATS → EVERY SITE", { x: 5.6, y: gy + 0.25, w: 6.9, h: 0.3, fontSize: 9.5, color: C.text2, align: "right" });
  const n = 4, cg = 0.3, gw = (12.33 - 0.7 - (n - 1) * cg) / n;
  [
    ["Direct outreach", "I email and call maintenance managers at plants, facilities teams and repair shops. 70 this week."],
    ["Trade schools", "HVAC and maintenance programs coach students with Praxis. Graduates bring it to their first job."],
    ["Trade shows + forums", "Maintenance and reliability conferences, and the online forums where techs and managers trade advice."],
    ["Partners", "Built into the maintenance apps shops already use, and resold by distributors and glasses makers."],
  ].forEach(([h, b], i) => {
    const x = 0.85 + i * (gw + cg), y = gy + 0.72;
    s.addShape(pres.ShapeType.ellipse, { x, y: y + 0.02, w: 0.28, h: 0.28, fill: { color: C.text1 }, line: { type: "none" }, objectName: "channel-badge" });
    tb(s, String(i + 1), { x, y: y + 0.02, w: 0.28, h: 0.28, fontFace: SEMI, fontSize: 10.5, color: "FFFFFF", align: "center", valign: "middle" });
    tb(s, h, { x: x + 0.4, y, w: gw - 0.4, h: 0.32, fontFace: SEMI, fontSize: 15, color: C.text1, valign: "middle" });
    tb(s, b, { x, y: y + 0.42, w: gw - 0.05, h: 0.95, fontSize: 12.5, color: BODY });
  });
  footer(s, 0, `Reliability magazine (hiring + ramp-up) · senior-tech hour: BLS wage ÷ wage share · pricing is our hypothesis (appendix ${ref(aUnitEcon)})`);
  s.addNotes("The money, from the customer's side. Reliability magazine puts hiring and ramping up one maintenance tech at $10-15k, counting onboarding time and lost productivity; that's a trade estimate. We sell an annual subscription: $200 per new-tech seat per month, billed annually, unlimited sessions, plus a one-time setup per procedure, after a short paid pilot whose fee counts toward year one. A new tech holds a seat for about six months (about $1,200 of seat time); then the seat moves to the next new hire. $200 a month is about $46 a week, which is about one hour of a senior tech's time ($44 an hour: BLS median wage divided by the 70% wage share of employer cost). So it pays for itself if it saves a senior tech one hour a week. It costs us about $1.08 an hour to run today ($0.48 with our local model). Pricing anchors on Tulip's $100-250 per station per month. Pricing risk: all-shift use squeezes a flat seat, so we'd price by coached hours or tiers. Marketing and sales plan, in the order each channel kicks in. One: direct outreach. I email and call maintenance managers myself (founder-led sales: they pay us for a pilot; we don't pay them). Two: trade schools. HVAC and industrial-maintenance programs coach students with Praxis, which is also how we collect training footage, and graduates carry it to their first employer. Three: maintenance and reliability trade shows and the online communities where techs and managers talk. Four: partners. An integration into the maintenance apps shops already use (MaintainX-style), and resale through equipment distributors and glasses makers. The funnel: outreach, then a demo, then a short paid pilot with a metric, then annual seats, then every site. Say the outreach numbers out loud: 14 emails sent Oct 17, 56 more Oct 19, plus any replies.");
}

// ---------- The long game ----------
function sVision() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("THE LONG GAME", { placeholder: "eyebrow" });
  s.addText("Every coaching session builds data nobody else has.\nThat data is how we climb from technicians to robots", { placeholder: "title" });
  const gap = 0.15, w = (12.33 - 3 * gap) / 4, ys = [2.95, 2.68, 2.41, 2.14];
  // each step: the move, why customers stay (or what it adds), then the revenue target
  const steps = [
    ["NOW · 2027", "Coach new techs", "Paid pilots with maintenance teams. Every session becomes labeled training data.", "$0.3M · 10 teams"],
    ["NEXT · 2028", "Our own models", "Trained on our pilot footage, on the glasses. Cheaper to run and better at maintenance than rented models.", "$1.5M · 50 teams · 5×"],
    ["THEN · 2029", "A skills record for every tech", "Verified work and certifications live in Praxis, so leaving means losing them. Then new trades.", "$4.5M ARR · 150 teams · 3×"],
    ["LATER · 2030+", "Robots: two paths", null, "$13M → $30M ARR, 2030–31"],
  ];
  steps.forEach(([k, h, body, rev], i) => {
    const x = 0.5 + i * (w + gap), y = ys[i], xe = i < 3 ? x + w + gap : x + w;
    line(s, x, y, xe, y, { color: i === 0 ? C.accent1 : C.text1, width: i === 0 ? 2.5 : 1.5, name: "stair-tread" });
    if (i < 3) line(s, xe, y, xe, ys[i + 1], { color: C.text1, width: 1.5, name: "stair-riser" });
    s.addShape(pres.ShapeType.ellipse, { x: x - 0.02, y: y - 0.1, w: 0.2, h: 0.2, fill: { color: i === 0 ? C.accent1 : C.text1 }, line: { type: "none" }, objectName: "stair-dot" });
    const tx = x + 0.2, tw = w - 0.3;
    mono(s, k, { x: tx, y: y + 0.17, w: tw, h: 0.28, fontSize: 10, color: C.text1 });
    tb(s, h, { x: tx, y: y + 0.45, w: tw, h: 0.55, fontFace: HEAD, fontSize: 14.5, lineSpacingMultiple: 0.95, valign: "top" });
    if (body) {
      const by = y + (h.length > 18 ? 1.02 : 0.82); // one-line headings pull the body up
      tb(s, body, { x: tx, y: by, w: tw, h: 0.85, fontSize: 12, color: BODY });
      tb(s, rev, { x: tx, y: by + 0.88, w: tw, h: 0.32, fontFace: SEMI, fontSize: 13, color: i === 0 ? C.accent2 : C.text1, objectName: "stair-revenue" });
    } else {
      [["A", "Train our own robot models on the data we've collected"], ["B", "Sell the data and our step checker to robot labs"]].forEach(([t, b], j) => {
        const by = y + 0.85 + j * 0.66;
        s.addShape(pres.ShapeType.roundRect, { x: tx, y: by, w: tw, h: 0.58, rectRadius: 0.04, fill: { color: C.background1 }, line: { color: C.text1, width: 1 }, objectName: "robot-path" });
        tb(s, [{ text: `${t}  `, options: { fontFace: HEAD, color: C.accent2 } }, { text: b }], { x: tx + 0.12, y: by, w: tw - 0.2, h: 0.58, fontSize: 11.5, valign: "middle" });
      });
      tb(s, rev, { x: tx, y: y + 2.17, w: tw, h: 0.32, fontFace: SEMI, fontSize: 13, color: C.text1, objectName: "stair-revenue" });
    }
  });
  // what labs already pay for data
  const py = 5.45, ph = 1.3;
  s.addShape(pres.ShapeType.roundRect, { x: 0.5, y: py, w: 12.33, h: ph, rectRadius: 0.05, fill: { color: C.text1 }, line: { type: "none" }, objectName: "panel-data-market" });
  mono(s, "AI LABS ALREADY PAY FOR DATA, AND IT'S GROWING", { x: 0.85, y: py + 0.18, w: 8, h: 0.28, fontSize: 10, color: C.accent1 });
  [
    ["$2B+ a year", "Mercor's run-rate selling expert data to AI labs, doubled in four months"],
    [">$100M a year", "what robotics companies already spend buying real-world data"],
    ["$8.6B by 2030", "the AI training-data market, growing about 22% a year"],
  ].forEach(([b, c], i) => {
    const x = 0.85 + i * 4.0;
    tb(s, b, { x, y: py + 0.45, w: 3.7, h: 0.38, fontFace: HEAD, fontSize: 19, color: C.background2 });
    tb(s, c, { x, y: py + 0.83, w: 3.6, h: 0.42, fontSize: 11.5, color: C.accent6 });
  });
  footer(s, 0, "Revenue: targets, not forecasts; triple-triple-double pace after year 2 · Mercor: The Information, Dealroom (Jun 2026) · Micro1 CEO estimate · Grand View Research");
  s.addNotes("Each step has paying demand today and builds the asset the next step needs. Revenue targets, not forecasts, on the pace investors expect: the median Series A in 2025 had about $3.3M ARR growing 2-3x a year, and the top-decile path is triple, triple, double, double, double. Same math as the market slide, about 25 new techs a team at $1,200 of seat time each, plus records. 2027: 10 teams from paid pilots, about $0.3M. 2028: our own models. Within a year of the first pilots we train our own step and checking models on the pilot footage, running on the glasses, so most rented model calls go away: cheaper to run, and better at maintenance than a general model. 50 teams, about $1.5M (5x). 2029: a skills record for every tech. The seat follows the new tech being coached, but the record follows the employee: every procedure they've done, verified step by step, building toward certifications and audits. By 2029 there are enough verified records for certifications to matter, so once a company's training and compliance history lives in Praxis, leaving means losing it (a switching cost, and a network effect if techs carry Praxis-verified records to new employers). Then the same engine goes into new trades: field service, assembly lines, aviation maintenance. 150 teams, about $4.5M ARR (3x), the year-3 goal on the market slide. 2030-31: about $13M then $30M ARR, still under 2% of the $1.8B first market, before any robotics revenue. Every session is first-person video of skilled work, lined up to the procedure, with verified steps, real mistakes and the fixes that worked. Customers pay us to collect it. Then two paths to robots: A, train our own robot models on that data; or B, sell the data and our 'did this step succeed?' checker to robot labs. Labs already pay: Mercor's run-rate selling expert data to AI labs passed $2B in June 2026, double what it was four months earlier (gross, reported by The Information); Micro1's CEO estimates robotics companies spend over $100M a year on real-world data; Figure says it has paid $15M for human video; Grand View Research sizes the AI training-data market at $8.6B by 2030, growing about 22% a year. Raw footage is becoming a commodity; skilled, verified, procedure-aligned footage isn't. Gates, not dates: each step needs the last one's metric hit first.");
}

// ---------- The ask ----------
function sAsk() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("THE ASK", { placeholder: "eyebrow" });
  s.addText([{ text: "$10k", options: { color: C.accent2 } }, { text: " buys the data and GPU time to make the models\nbetter, and puts Praxis on glasses at a first pilot" }], { placeholder: "title" });
  const funds = [
    [3000, "GPU time", "Train our models (step tracker, event detector, local checker) on more data"],
    [2500, "Glasses + capture", "Run Praxis on camera glasses at a pilot site"],
    [2000, "Training data", "Buy labeled first-person recordings of real maintenance work"],
    [1500, "Inference", "About 1,400 hours of live pilot coaching, at ~$1.08 an hour"],
    [1000, "Company formation", "So a customer can sign a paid pilot"],
  ];
  const fills = [C.accent1, "16191B", "3C4347", "5E676C", "9AA3A7"];
  let fx = 0.5;
  funds.forEach(([amt], i) => {
    const w = 12.33 * amt / 10000;
    s.addShape(pres.ShapeType.rect, { x: fx, y: 2.3, w: w - 0.04, h: 0.32, fill: { color: fills[i] }, line: { type: "none" }, objectName: "funds-bar" });
    fx += w;
  });
  const cw = 12.33 / 5;
  funds.forEach(([amt, name, why], i) => {
    const x = 0.5 + i * cw;
    s.addShape(pres.ShapeType.rect, { x, y: 2.95, w: 0.16, h: 0.16, fill: { color: fills[i] }, line: { type: "none" }, objectName: "funds-swatch" });
    tb(s, `$${amt.toLocaleString("en-US")}`, { x, y: 3.2, w: cw - 0.2, h: 0.5, fontFace: HEAD, fontSize: 26, color: i === 0 ? C.accent2 : C.text1 });
    tb(s, name, { x, y: 3.75, w: cw - 0.2, h: 0.35, fontFace: SEMI, fontSize: 15 });
    tb(s, why, { x, y: 4.12, w: cw - 0.25, h: 0.9, fontSize: 12.5, color: BODY });
  });
  line(s, 0.5, 5.2, 12.83, 5.2, { color: C.text1, width: 1.5, name: "april-rule" });
  mono(s, "TRUE BY APRIL", { x: 0.5, y: 5.35, w: 3, h: 0.3, fontSize: 11, color: C.text1 });
  ["Models retrained on real maintenance recordings", "Running on glasses at a real site", "A first paid pilot, with a metric agreed up front"].forEach((t, i) => {
    tb(s, t, { x: G3.x[i], y: 5.72, w: G3.w - 0.15, h: 0.6, fontSize: 16, fontFace: SEMI });
  });
  footer(s, 0, "$10,000 over six months · same amounts as the application");
  s.addNotes("Where the money goes, and what it unlocks. $3,000 of GPU time to retrain the models we own (the step tracker, event detector and local checker) on more data: the learning curves say more recordings keep helping. $2,000 to buy labeled first-person recordings of real maintenance work, so they learn the domain. $2,500 for camera glasses and capture gear, to run at a real site. $1,500 of inference for pilots: at about $1.08 an hour, roughly 1,400 coached hours, about 30 seat-months at 2 hours a day. $1,000 for company formation, so a customer can sign and pay. Same amounts as the application. By April: models retrained on maintenance recordings, running on glasses at a real site, and a first paid pilot whose metric (time until a new tech works alone) is agreed before we start.");
}

function aTrain() {
  const s = appx("", "What we train in-house, and why a big AI lab won't build this");
  const R = (a, ours) => a.map((t, i) => ({ text: t, options: i === 0 ? { fontFace: SEMI } : i === 1 ? { color: ours ? C.accent2 : C.text2, fontFace: SEMI, fontSize: 11 } : {} }));
  s.addTable([
    [TH("PART"), TH("WHO"), TH("WHAT IT DOES")],
    R(["Event detector", "OURS · TRAINED", "A small temporal network that spots the moment a step ends"], true),
    R(["Task recognizer", "OURS · TRAINED", "Works out which procedure the tech is doing"], true),
    R(["State tracker", "OURS · TRAINED", "A Bayesian model of where the tech is in the procedure, with step models per procedure"], true),
    R(["Local checker", "OURS · TRAINED", "Learned from the frontier model; answers routine \"is this step done?\" checks for free"], true),
    R(["Perception", "OPEN MODELS", "SigLIP2, V-JEPA 2 and hand tracking turn each frame into features. Not trained by us"], false),
    R(["Verifier", "RENTED", "A frontier model answers hard questions on 14% of frames. Swappable in one line"], false),
  ], { ...tableOpts([2.0, 1.6, 4.1], 7.7), rowH: 0.56, fontSize: 12.5, objectName: "table-train" });
  const x = 8.6, w = 4.23, Y = 2.2, ph = 4.3;
  s.addShape(pres.ShapeType.roundRect, { x, y: Y, w, h: ph, rectRadius: 0.05, fill: { color: C.text1 }, line: { type: "none" }, objectName: "panel-labs" });
  mono(s, "WHY A BIG LAB WON'T", { x: x + 0.35, y: Y + 0.28, w: w - 0.7, h: 0.3, fontSize: 11, color: C.accent1 });
  tb(s, [
    { text: "They sell one general model. ", options: { fontFace: SEMI, color: C.background2 } },
    { text: "Ours wraps any model, so their best one becomes our swappable verifier.", options: { breakLine: true, paraSpaceAfter: 12 } },
    { text: "The hard part is data they don't have: ", options: { fontFace: SEMI, color: C.background2 } },
    { text: "first-person video of skilled work, lined up to the procedure, with verified steps.", options: { breakLine: true, paraSpaceAfter: 12 } },
    { text: "And a business they don't run: ", options: { fontFace: SEMI, color: C.background2 } },
    { text: "each shop's manuals and records, and a pilot on site." },
  ], { x: x + 0.35, y: Y + 0.72, w: w - 0.7, h: ph - 0.9, fontSize: 14, color: C.accent6, objectName: "labs-text" });
  footer(s, TOTAL, "docs/ARCHITECTURE.md · docs/MODEL_ROADMAP.md");
  s.addNotes("If asked what we train: the event detector is a small causal temporal convolutional network on frozen video features that predicts step boundaries. The task recognizer is a linear probe over frozen features plus zero-shot text matching. The state tracker is a hidden semi-Markov model over the procedure's task graph, with duration priors and per-procedure step probes learned from training recordings. The local checker is a student distilled from the frontier verifier; it agrees with it on 69% of held-out checks, runs in 0.03 ms on a laptop CPU, and removes 34% of frontier calls. Perception is frozen open models (SigLIP2, V-JEPA 2, MediaPipe hands). The verifier is rented: Jev as the fast tier, Claude Opus for hard cases. Next in-house steps: fine-tune a small open vision-language model on our logged verifier calls so mistakes and fine checks run in-house, and distill a smaller video backbone for on-device use. Why a big lab won't: they could build the parts, but their business is one general model for everyone. Coaching is a tracking problem, not a seeing problem: the value is the state around the model and the procedure-aligned data, plus the enterprise work of each shop's manuals, records and pilots.");
}

// ---------- Appendix divider: where the backup starts ----------
function sAppendixDivider() {
  const s = pres.addSlide({ masterName: "Praxis Dark Grid" });
  s.addText("INFO SLIDES", { placeholder: "eyebrow" });
  s.addText("Appendix", { placeholder: "title" });
  const items = APPENDIX.map(([, label]) => label);
  const x = 8.3, y0 = 1.25, rh = 0.42;
  items.forEach((t, i) => {
    const y = y0 + i * rh;
    tb(s, `A${i + 1}`, { x, y, w: 0.6, h: rh, fontFace: SEMI, fontSize: 12, color: C.accent1, valign: "middle" });
    tb(s, t, { x: x + 0.65, y, w: 3.9, h: rh, fontSize: 14, color: C.background2, valign: "middle" });
    if (i < items.length - 1) line(s, x, y + rh, x + 4.5, y + rh, { color: "3A4044", width: 0.75, name: "appx-rule" });
  });
}

// ================================================================== APPENDIX
const appx = (_label, title) => {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText(eb(""), { placeholder: "eyebrow" });
  s.addText(title, { placeholder: "title" });
  return s;
};

// ---------- Under the hood: the engineer cut of the live session ----------
function aUnderHood() {
  const s = appx("", "Under the hood: the same live session, layer by layer");
  video(s, "repair_demo_engineer", 0.5, 1.95, 8.6);
  const x = 9.4, w = 3.43;
  tb(s, runs([
    ["State tracker. ", "Its belief over the 19 steps, the time on the current step, and whether the tech looks like a novice."],
    ["Model calls. ", "Jev answers in 150 ms (median, 130 calls). Opus double-checks 14 moments, about 4 s each."],
    ["Timeline. ", "The event detector, both model tiers, the tracked step and every decision to speak or stay quiet."],
    ["Cost. ", "$0.165 for the whole 16:40 session, with 0 errors."],
  ], 12), { x, y: 1.95, w, h: 4.8, fontSize: 13.5, color: BODY, objectName: "hood-legend" });
  footer(s, TOTAL, "Praxis Studio live session on ENIGMA-51 video 141 · latencies from the session log");
  s.addNotes("The same 49 seconds as the live slide, with the engine underneath. Right: the state tracker's belief over the 19 steps, and below it each model call with its real latency. Bottom: a scrolling timeline of the event detector, the fast tier (Jev), the Opus escalations, the step it thinks you're on, and the policy's decisions. Two moments to point at. At 0:26 the fast model flags a missed button with 0.84 confidence; Opus says the step is still in progress, so no alert goes out (both buttons are lit in the footage). At 2:52 the fast model guesses the wrong cause and Opus reads the display at 215 °C. That alert lands 6 seconds after the checked frame, and cutting that escalation latency is next.");
}

// ---------- Status quo ----------
function aStatusQuo() {
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Appendix" });
  s.addText(eb(""), { placeholder: "eyebrow" });
  s.addText("The status quo: what each tool does today, and what it misses", { placeholder: "title" });
  const cols = [
    ["SHADOWING", "A senior tech, side by side", "The real teacher today", "About $44 an hour of senior time, one new tech at a time"],
    ["MANUALS + VIDEOS", "PDFs, binders, YouTube", "Explain what should happen", "Can't see what you're actually doing"],
    ["PROCEDURE APPS", "MaintainX, Tulip, Augmentir", "Put the steps on a phone; collect sign-offs and photos", "A checkbox isn't proof the step was done right"],
    ["FIXED CAMERAS", "Retrocausal, Invisible AI", "Watch one workstation on a line", "Maintenance moves around the machine"],
  ];
  const gap = 0.15, w = (12.33 - 3 * gap) / 4;
  cols.forEach(([k, who, does, miss], i) => {
    const x = 0.5 + i * (w + gap);
    plateCard(s, x, 2.2, w, 2.75, `status-${i + 1}`);
    mono(s, k, { x: x + 0.25, y: 2.4, w: w - 0.5, h: 0.3, fontSize: 10.5, color: C.text1 });
    tb(s, who, { x: x + 0.25, y: 2.75, w: w - 0.5, h: 0.6, fontFace: SEMI, fontSize: 15 });
    tb(s, does, { x: x + 0.25, y: 3.35, w: w - 0.5, h: 0.65, fontSize: 13, color: BODY });
    line(s, x + 0.25, 4.05, x + w - 0.25, 4.05, { color: C.accent6, width: 0.75, name: "status-rule" });
    tb(s, [{ text: "MISSES  ", options: { fontFace: MONO, fontSize: 9.5, color: C.accent5 } }, { text: miss }], { x: x + 0.25, y: 4.15, w: w - 0.5, h: 0.75, fontSize: 13 });
  });
  darkPanel(s, 0.5, 5.25, 12.33, 1.15, "PRAXIS", "Watches the work, follows the person around the machine, and runs on hardware a shop already owns.", 18);
  footer(s, TOTAL, "Competitor pages checked 2026-10-17");
  s.addNotes("Don't claim nobody else is here. Procedure apps already compile instructions (Tulip, Augmentir, Squint). Tulip is testing camera checks of whether a procedure was followed. Retrocausal tracks whole procedures, but on fixed cameras at a station. First-person entrants (Viture + NVIDIA, Strivr) are the closest: see the competition slide.");
}

// Market math
function aMarketMath() {
  const s = appx("APPENDIX · A2", "Market math, and the assumptions behind it");
  const R = (a) => a.map((t, i) => ({ text: t, options: i === 0 ? { fontFace: SEMI } : {} }));
  s.addTable([
    [TH(""), TH("WHO (BLS)"), TH("MATH"), TH("PER YEAR")],
    R(["TAM", "Installation, maintenance + repair 6,086,190 · electricians 757,220 · production 8,565,760 = 15.4M", "15.4M × $50 a month × 12", "≈ $9.2B"]),
    R(["SAM", "General maintenance + repair, machinery mechanics + millwrights, HVAC = 2.47M jobs, ~255k openings a year", "255k × $200 × 6 months = $306M; 2.47M × $50 × 12 = $1.48B", "≈ $1.8B"]),
    R(["SOM (year 3)", "1.5% of new maintenance techs ≈ 3,750 new techs a year, ~150 mid-size teams", "3,750 × $200 × 6 months", "≈ $4.5M ARR"]),
  ], { ...tableOpts([1.1, 5.3, 4.33, 1.6]), rowH: 0.7, objectName: "table-market" });
  tb(s, runs([
    ["Prices are hypotheses. ", "$200 a month for coaching anchors on Tulip's $100–250 per station; $50 a month for every-worker records is a guess"],
    ["Openings ", "include people changing jobs, so new-tech counts are an upper bound"],
    ["Not counted: ", "other countries, field service outside these groups, aviation maintenance, and the robotics upside"],
  ], 6), { x: 0.5, y: 5.3, w: 12.33, h: 1.3, fontSize: 13 });
  footer(s, TOTAL, "BLS OEWS national tables, May 2025 · BLS Occupational Outlook Handbook");
}

// Unit economics
function aUnitEcon() {
  const s = appx("APPENDIX · A3", "Unit economics, and the pricing risk");
  const R = (a) => a.map((t) => ({ text: t }));
  s.addTable([
    [TH("DESIGN"), TH("$ / VIDEO-MIN"), TH("$ / SEAT-MONTH, 2 H/DAY"), TH("MARGIN AT $200")],
    R(["Frontier model every 5 s", "$0.085", "about $214", "negative"]),
    R(["Praxis engine today", "$0.018", "about $45", "about 77%"]),
    R(["Praxis + our local model", "$0.008", "about $20", "about 90%"]),
  ], { ...tableOpts([2.9, 1.6, 2.4, 1.5], 8.4), objectName: "table-unit-economics" });
  tb(s, "Labeled assumptions, not sourced: if a senior tech spends 50% of their time on a new hire for 3 months, that's about $11,400 of their time; at 25% for 12 months, about $22,800. We're asking maintenance managers for their real split.", { x: 0.5, y: 4.55, w: 8.4, h: 1.2, fontSize: 14, color: BODY });
  darkPanel(s, 9.25, 2.2, 3.58, 2.75, "THE RISK", "All-shift use (8 h/day) makes a flat $200 seat $1.19 an hour against our $1.08 cost: about a 9% margin. With the local model, about 60%. So price by coached hours or tiers, and move routine checks to the local model first.", 14);
  footer(s, TOTAL, "2,520 coached minutes a month = 2 h/day × 21 days · senior-tech cost: BLS");
}

// ---------- Learning curves ----------
function aCurves() {
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Appendix" });
  s.addText(eb(""), { placeholder: "eyebrow" });
  s.addText("Both learning curves: step models and the local student", { placeholder: "title" });
  const Pr = LC.probes, pk = {};
  Pr.rows.forEach((r) => { if (Pr.n_train_avail[r.task] >= 9) (pk[r.k] = pk[r.k] || []).push(r.acc); });
  const ks = Object.keys(pk).map(Number).sort((a, b) => a - b);
  const pacc = ks.map((k) => pct1(mean(pk[k])));
  const st = LC.student, sk = {};
  st.rows.forEach((r) => { (sk[r.n_recordings] = sk[r.n_recordings] || []).push(r.acc_vs_gt); });
  const ns = Object.keys(sk).map(Number).sort((a, b) => a - b);
  const sacc = ns.map((n) => pct1(mean(sk[n])));
  const teacher = pct1(st.teacher_acc_vs_gt);
  const chart = (x, title, ymin, ymax) => ({
    x, y: 3.7, w: 5.91, h: 2.6, lineSize: 3, lineDataSymbol: "circle", lineDataSymbolSize: 7, showValue: false, showLegend: false,
    valAxisMinVal: ymin, valAxisMaxVal: ymax, valAxisMajorUnit: 20, valAxisLabelFormatCode: '0"%"',
    valAxisLabelColor: "5E676C", catAxisLabelColor: "5E676C", valAxisLabelFontSize: 10, catAxisLabelFontSize: 10,
    valAxisLabelFontFace: "+mn-lt", catAxisLabelFontFace: "+mn-lt", catAxisLineShow: false, valAxisLineShow: false,
    valGridLine: { color: "D0D5D2", size: 0.75 }, catGridLine: { style: "none" },
    showCatAxisTitle: true, catAxisTitle: title, catAxisTitleFontSize: 10, catAxisTitleColor: "5E676C", catAxisTitleFontFace: "+mn-lt",
  });
  statCol(s, 0.5, 2.15, 5.91, `${pacc[0]}% → ${pacc[pacc.length - 1]}%`, "recognizing the current step, on videos it never trained on", { color: C.accent2, size: 34, capH: 0.4 });
  s.addChart(pres.ChartType.line, [{ name: "Step model", labels: ks.map(String), values: pacc }],
    { ...chart(0.5, "Training recordings per procedure", 0, 60), chartColors: ["FF5B14"], objectName: "chart-step-model" });
  statCol(s, 6.92, 2.15, 5.91, `${sacc[0]}% → ${sacc[sacc.length - 1]}%`, `checking a step is done · grey: the frontier model, ${teacher}%`, { color: C.accent2, size: 34, capH: 0.4 });
  s.addChart(pres.ChartType.line, [
    { name: "Our local model", labels: ns.map(String), values: sacc },
    { name: "Frontier model it learns from", labels: ns.map(String), values: ns.map(() => teacher) },
  ], { ...chart(6.92, "Training recordings", 0, 100), chartColors: ["FF5B14", "9AA3A7"], objectName: "chart-student" });
  mono(s, "TESTED ONLY ON RECORDINGS IT NEVER SAW · BOTH STILL RISING AT THE LARGEST SIZE WE HAVE", { x: 0.5, y: 6.42, w: 12.33, h: 0.3, color: C.text1 });
  footer(s, TOTAL, "Random subsets of public train-split recordings, 5 seeds per point");
  s.addNotes("We retrained our learned layers on growing slices of the training data and scored them only on recordings they never saw, so this isn't memorization. Left: the 3 procedures with 9 training recordings, held-out step accuracy. Right: the local student model on the same 469 held-out checks as the headline result. Steady gains per doubling of data, not 'exponential'. If asked for counts: up to 9 recordings per procedure, 30 recordings for the student. Every customer session is new training data. The engine we evaluated used only 3 recordings per procedure, so there's headroom we haven't used yet (not re-measured end to end).");
}



// Training data
function aTraining() {
  const s = appx("APPENDIX · A5", "Training data, stated plainly");
  tb(s, runs([
    ["Train and test never overlap. ", "Everything learned uses only the dataset's official train-split recordings"],
    ["Small on purpose. ", "A weekend-scale proof: the step-change detector trained on 24 recordings, the step models on 3 per procedure, the student on checks from 30"],
    ["Tested on 48 held-out clips: ", "235 min, 302 annotated steps, 170 annotated mistakes, plus procedure types never seen in training"],
    ["Design choices ", "were made on train-split recordings only, never on the test clips"],
    ["Labels are the dataset's, ", "not ours. One run per system, no confidence intervals yet"],
  ]), { x: 0.5, y: 2.2, w: 7.0, h: 4.3, fontSize: 14 });
  plateCard(s, 7.95, 2.2, 4.88, 2.6, "card-curves");
  const st = LC.student, sk = {};
  st.rows.forEach((r) => { (sk[r.n_recordings] = sk[r.n_recordings] || []).push(r.acc_vs_gt); });
  const ns = Object.keys(sk).map(Number).sort((a, b) => a - b);
  const Pr = LC.probes, pk = {};
  Pr.rows.forEach((r) => { if (Pr.n_train_avail[r.task] >= 9) (pk[r.k] = pk[r.k] || []).push(r.acc); });
  mono(s, "LEARNING CURVES", { x: 8.25, y: 2.45, w: 4.3, h: 0.3, fontSize: 11, color: C.text1 });
  tb(s, runs([
    ["Step models: ", `${pct1(mean(pk[1]))}% with 1 recording → ${pct1(mean(pk[3]))}% with 3 → ${pct1(mean(pk[9]))}% with 9 (the 3 procedures with 9)`],
    ["Student: ", `${pct1(mean(sk[ns[0]]))}% with ${ns[0]} recordings → ${pct1(mean(sk[ns[ns.length - 1]]))}% with ${ns[ns.length - 1]}; the frontier teacher is ${pct1(st.teacher_acc_vs_gt)}%`],
    ["Detector: ", "noisy, no clear trend yet. Not claimed"],
  ]), { x: 8.25, y: 2.85, w: 4.3, h: 2.25, fontSize: 13 });
  footer(s, TOTAL, "Praxis evaluation results");
}

// Competitors
function aCompetitors() {
  const s = appx("APPENDIX · A6", "Who else is here, and how we differ");
  const R = (a) => a.map((t) => ({ text: t }));
  s.addTable([
    [TH("CATEGORY"), TH("EXAMPLES"), TH("US VS THEM")],
    R(["Instruction platforms", "Tulip, Augmentir, Dozuki", "They show the steps; we watch the work. Natural integration partners"]),
    R(["Line cameras", "Retrocausal, Invisible AI, Tulip Vision", "Fixed at a station on a production line. Can't follow a person around a machine"]),
    R(["First-person coaching", "Viture Helix + NVIDIA, Strivr", "Closest. Hardware-led or high-touch; no published accuracy"]),
    R(["Toolkits", "NVIDIA XR AI, Meta's camera toolkit, Android XR", "Complements: the plumbing we build on"]),
    R(["General assistants", "Meta AI, Gemini Live", "Answer questions about a frame. No plan, no state, no calibration"]),
  ], { ...tableOpts([2.6, 3.9, 5.83]), objectName: "table-competitors" });
  tb(s, "If a big platform ships a coach: they're building our hardware and plumbing. We go deep in one vertical, with its procedures, records and data.", { x: 0.5, y: 5.65, w: 12.33, h: 0.7, fontSize: 15, color: C.accent2 });
  footer(s, TOTAL, "Public product pages, checked 17 Oct 2026");
}

// Risks
function aRisks() {
  const s = appx("APPENDIX · A7", "The risks we see, and what we do about each");
  const R = (a) => a.map((t, i) => ({ text: t, options: i === 0 ? { fontFace: SEMI } : {} }));
  s.addTable([
    [TH("RISK"), TH("WHAT WE DO")],
    R(["Meta or Google ships a coach", "They're building our hardware and plumbing. We go deep in maintenance with its procedures, records and data, and run on their glasses"]),
    R(["Glasses aren't ready", "We run on glasses that ship today (Meta, Viture + NVIDIA). Each new device is one more adapter"]),
    R(["Mistake detection is weak (4 of 17)", "Locked procedures, maintenance data and the tech saying \"done\" all add evidence. Measured in every pilot"]),
    R(["Privacy, unions, monitoring laws", "Fast layers run locally; only event keyframes leave (14% of frames). Coaching for the worker, aggregates for the employer. Blur next"]),
    R(["A wrong prompt on a safety-critical step", "Lockout and similar steps stay the tech's job. Praxis prompts and records them, and never approves them"]),
    R(["Depending on model vendors", "The verifier is swappable in one config line, and our local student already handles routine checks"]),
    R(["Solo founder", "The grant tests demand before hiring. First hires come after the pilot"]),
  ], { ...tableOpts([3.6, 8.73]), rowH: 0.52, fontSize: 12, objectName: "table-risks" });
  footer(s, TOTAL, "Praxis evaluation results and planning notes");
}
// Glasses + voice
function aGlasses() {
  const s = appx("APPENDIX · A8", "Glasses and voice: what's built, and what's next");
  const cols = [
    ["BUILT", C.accent3, ["Runs live in real time, with the local layers at about 50 ms per frame; model calls never block the loop", "Glasses connections for Meta and Viture + NVIDIA, plug and play", "Voice control, plus screen or voice-only modes depending on the glasses", "Praxis Studio: the engine in a browser, on a camera, an upload or a test clip"]],
    ["NEXT, WITH DEVICES IN HAND", C.text2, ["Test end to end on Meta and Viture glasses at a pilot site", "Measure glass-to-coach latency, the biggest unknown", "A hearing-protection headset for loud plants", "Face and badge blur; a local-model tier for sensitive sites"]],
  ];
  cols.forEach(([h, col, items], i) => {
    const x = 0.5 + i * 6.42;
    line(s, x, 2.2, x + 5.91, 2.2, { color: C.text1, width: 1.5, name: "col-rule" });
    s.addShape(pres.ShapeType.ellipse, { x, y: 2.45, w: 0.18, h: 0.18, fill: { color: col }, line: { type: "none" }, objectName: "state-dot" });
    mono(s, h, { x: x + 0.32, y: 2.4, w: 5.5, h: 0.3, fontSize: 11, color: C.text1 });
    tb(s, items.map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < items.length - 1, paraSpaceAfter: 8 } })), { x, y: 2.9, w: 5.91, h: 3.4, fontSize: 14 });
  });
  footer(s, TOTAL, "Built; not yet tested on the devices");
}

// ================================================================== ORDER
const CORE = [
  ["Story", [sCover, sProblem, sProduct]],
  ["Progress", [sEngine, sBuilt, sLive, sWorks]],
  ["Why now", [sWhyNow]],
  ["Why we win", [sWorkflow, sBigTech]],
  ["Market", [sMarket, sBusiness]],
  ["Vision", [sVision]],
  ["Ask", [sAsk]],
];
const APPENDIX = [
  [sEvidence, "Evidence: accuracy and cost"], [aUnderHood, "Under the hood: the live session"], [aTrain, "What we train, and why big labs won't"], [aStatusQuo, "The status quo, tool by tool"],
  [aMarketMath, "Market math and assumptions"], [aUnitEcon, "Unit economics and pricing risk"], [aCurves, "Learning curves"],
  [aTraining, "Training data, stated plainly"], [aCompetitors, "Competitor detail"], [sConsumers, "Why not consumers first"],
  [aRisks, "Risks and what we do"], [aGlasses, "Glasses and voice"], [sFounder, "Why me"],
];
for (const [title, fns] of CORE) {
  pres.addSection({ title });
  SECTION = title;
  for (const f of fns) { CUR++; f(); }
}
if (CUR !== TOTAL) throw new Error(`TOTAL is ${TOTAL} but the core deck has ${CUR} slides`);
pres.addSection({ title: "Appendix" });
SECTION = "Appendix";
sAppendixDivider();
APPENDIX.forEach(([f], i) => { APX = `A${i + 1}`; f(); });

ALL_SLIDES.forEach((sl) => {
  const t = [sl._notes, sl._src && `Sources: ${sl._src}`].filter(Boolean).join("\n\n");
  if (t) sl._rawNotes(t);
});

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
