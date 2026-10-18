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
const TOTAL = 11; // main-deck slides; appendix slides carry the full mark

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
pres.addSlide = (o = {}) => addSlideRaw({ ...o, sectionTitle: SECTION });
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
  if (source) slide.addText(source, { x: x0 + 1.0, y: 6.93, w: 12.83 - x0 - 1.0, h: 0.3, fontFace: "Archivo", fontSize: 9.5, color: C.text2, align: "right", valign: "middle", margin: 0, isTextBox: true, objectName: "footer-source" });
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
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Story" });
  s.addText("THE PROBLEM", { placeholder: "eyebrow" });
  s.addText("A new maintenance technician needs about a year\nof a senior tech's time to work alone", { placeholder: "title" });
  hero(s, G2.x[0], 3.0, G2.w, ">1 year", "of on-the-job training, with a senior tech as the teacher.", { size: 80, capSize: 22, capH: 1.0 });
  hero(s, G2.x[1], 3.0, G2.w, "$11–23k", "of senior-tech time per new hire, by our estimate.", { size: 80, capSize: 22, capH: 1.0 });
  line(s, 0.5, 5.85, 12.83, 5.85, { color: C.accent6, width: 0.75, name: "problem-rule" });
  tb(s, [{ text: "~255,000 openings a year ", options: { fontFace: SEMI } }, { text: "for US maintenance and repair techs, and every new hire pulls a senior tech off the floor." }], { x: 0.5, y: 6.0, w: 12.33, h: 0.5, fontSize: 17 });
  footer(s, 2, "BLS Occupational Outlook Handbook · BLS Employer Costs for Employee Compensation, June 2025 · estimate is ours");
  s.addNotes("The $11-23k is 25-50% of a $44-an-hour senior tech for 3-12 months. BLS says on-the-job training for these jobs typically lasts more than a year. A 2017 survey of 35 aviation repair stations found 9 to 14 months before a new hire was profitable, some 24. $44 an hour is the BLS median wage ($30.82) divided by the 70.2% wage share of employer cost; senior techs cost more. The $11-23k range is our assumption (50% of a senior tech for 3 months, or 25% for 12) and we're asking managers for their real number. Manuals and videos can't see you, so the senior tech is the real teacher, and that time sits in nobody's training budget.");
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
  [["LOAD", "the manuals and checklists a shop already has"], ["COACH", "on a phone or glasses, one short line at a time"], ["VERIFY", "critical steps and keep the record"]].forEach(([k, b], i) => {
    const y = 3.85 + i * 0.95;
    line(s, 0.5, y, 4.45, y, { color: "3A4044", width: 1, name: "product-rule" });
    mono(s, k, { x: 0.5, y: y + 0.17, w: 1.1, h: 0.3, fontSize: 12, color: C.background2 });
    tb(s, b, { x: 1.6, y: y + 0.13, w: 2.85, h: 0.75, fontSize: 16, color: C.accent6 });
  });
  conceptTag(s);
  s.addNotes("What it is: software, not glasses. It runs on a tablet at the bench today and on camera or display glasses through an input adapter. It speaks; cards appear only for mistakes and view requests, and the step graph is never shown. It verifies, logs, and flags mistakes only when confident. Mistake detection is our weakest number today (4 of 17 alerts named a real annotated error), so this slide shows step tracking, which is what we measure best. Buyer: the maintenance manager. User: the new tech.");
}

const Q = (v) => (v * 13.333) / 100;
// ---------- Engine (dark blueprint, from brand/deck/v2) ----------
function sEngine() {
  const s = pres.addSlide({ masterName: "Praxis Dark Grid", sectionTitle: "Story" });
  tb(s, eb("HOW PRAXIS WORKS · ENGINE v0"), { x: Q(2.9), y: Q(3.1), w: Q(40), h: Q(1.6), fontFace: LABEL, fontSize: 10, charSpacing: 2, color: C.accent6, objectName: "eyebrow" });
  s.addText([
    { text: "The frontier model is one swappable part. " },
    { text: "The tracking engine around it is ours.", options: { color: "6B7479" } },
  ], { x: Q(2.9), y: Q(4.9), w: Q(80), h: Q(6.5), fontFace: THEME.headFontFace, fontSize: 24, color: C.background2, valign: "top", margin: 0, lineSpacingMultiple: 0.98, isTextBox: true, objectName: "headline" });

  // 1600x900 blueprint coordinates → inches
  const V = (px) => px / 120;
  const OR = C.accent1;
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
    if (st.tag) s.addText(st.tag, { x: V(x + w - 250), y: V(y + 6), w: V(240), h: V(16), fontFace: LABEL, fontSize: 6.5, charSpacing: 1.5, color: st.sc, align: "right", valign: "middle", margin: 0, isTextBox: true, objectName: `box-${name}-tag` });
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
  alab("48 held-out clips of public first-person video · one run each", 860, 861, "5E676C", 694, "right");
  s.addNotes("Walk it left to right along the orange path, which is what happens on every frame, on the device, in about 50 ms: open models turn the frame into features, our detector and recognizer feed our state tracker, and the policy decides whether the coach says anything. Below, in the dark, is the only rented part: on 14% of frames the tracker asks a verifier one typed question (Jev in 151 ms, Claude Opus for hard cases). We calibrate the answer and feed it back. Every session trains our local student, which already handles routine checks. Swapping the rented model is a one-line config change.");
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
  s.addText("Same frontier model, with our tracking: 54% vs 48% step accuracy at a fifth of the cost", { placeholder: "title" });
  line(s, 7.85, 3.6, 12.83, 3.6, { color: C.text1, width: 1.5, name: "result-rule" });
  tb(s, "1/5", { x: 7.85, y: 3.8, w: 4.98, h: 1.3, fontFace: HEAD, fontSize: 80, color: C.text1 });
  tb(s, "the cost per minute of video, and more accurate.", { x: 7.85, y: 5.15, w: 4.98, h: 0.8, fontSize: 18 });
  footer(s, 5, "48 held-out public clips · one run each", 7.85);
  s.addNotes("Like-for-like: the same frontier model on the same frames. Called every 5 seconds with no memory of the task, it names the current step on 48% of frames; with our tracking around it, 54% (6 points more), at $0.018 vs $0.085 per video-minute. The baseline is a call every 5 seconds, not every frame. With our distilled local model doing routine checks: 52% at $0.008, 11x cheaper. When the view was blurred or blocked it asked for a better view on 77-98% of checks and was never confidently wrong. Caveats to say out loud: one run per system, public cooking video. Procedures are procedures; maintenance footage is the first thing the grant buys.");
}

// ---------- Why now ----------
function sWhyNow() {
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Market" });
  s.addText("WHY NOW", { placeholder: "eyebrow" });
  s.addText("This year, frontline teams are choosing what\nreplaces their last generation of tools", { placeholder: "title" });
  const ev = [
    ["28 MAY 2026", "Autodesk buys MaintainX for $3.6B"],
    ["16 JUN 2026", "Viture + NVIDIA announce coaching glasses"],
    ["SEPT 2026", "Meta opens its glasses' camera to apps"],
    ["31 DEC 2026", "Microsoft ends Dynamics 365 Guides", true],
    ["Q1 2027", "Helix and Android XR display glasses ship"],
  ];
  const cw = 12.33 / 5, TL = 2.75;
  line(s, 0.5, TL, 12.83, TL, { color: C.text1, width: 1.5, name: "timeline" });
  ev.forEach(([d, t, hl], i) => {
    const x = 0.5 + i * cw;
    s.addShape(pres.ShapeType.ellipse, { x, y: TL - 0.12, w: 0.24, h: 0.24, fill: { color: hl ? C.accent1 : C.text1 }, line: { type: "none" }, objectName: "timeline-dot" });
    mono(s, d, { x, y: TL + 0.35, w: cw - 0.25, h: 0.3, fontSize: 11, color: C.text1 });
    tb(s, t, { x, y: TL + 0.7, w: cw - 0.3, h: 1.3, fontSize: 19 });
  });
  [["$1 an hour", "what it costs us to run Praxis today: $0.018 per minute of video"], ["~10× a year", "how fast the price of the same AI capability keeps falling"]].forEach(([b, c], i) => {
    const x = G2.x[i];
    line(s, x, 5.0, x + G2.w, 5.0, { color: C.accent6, width: 0.75, name: "cost-rule" });
    tb(s, b, { x, y: 5.15, w: G2.w, h: 0.7, fontFace: HEAD, fontSize: 36 });
    tb(s, c, { x, y: 5.9, w: G2.w, h: 0.5, fontSize: 15, color: BODY });
  });
  footer(s, 7, "Autodesk–MaintainX release · Viture/NVIDIA release · Meta Wearables toolkit 1.0 · Microsoft Dynamics 365 retirement notice · a16z on LLM inference prices");
  s.addNotes("Why not 2023: no glasses let apps read the camera, and calling a vision model often enough to coach was too slow and too expensive. Now the hardware and plumbing are being built around us, the incumbent generation (HoloLens-era Guides and Remote Assist) is ending on Dec 31, and the budget is proven by the MaintainX deal. It finally costs out: about $1 an hour of video for us, against $5 for a frontier model called every 5 seconds, and a16z measures the price of a fixed level of AI falling about 10x a year. Nobody publishes accuracy numbers on the coach itself; we do. Apple glasses are reported for 2027, not announced.");
}

// ---------- Market ----------
function sMarket() {
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Market" });
  s.addText("MARKET · US, PER YEAR, BOTTOM-UP", { placeholder: "eyebrow" });
  s.addText("A $306M wedge in a $1.8B first market,\nin a $9B one", { placeholder: "title" });
  const rows = [
    ["TAM", 9.2, "$9.2B", "15.4M US workers who follow written procedures, at $50 a month for verified records", "C2C8C5"],
    ["SAM", 1.8, "$1.8B", "2.47M US maintenance and repair techs: coaching new hires + records for everyone", "9AA3A7"],
    ["WEDGE", 0.306, "$306M", "~255k new maintenance techs a year, coached for 6 months at $200 a month", C.accent1],
    ["YEAR 3", 0.003, "$3M ARR", "1% of new techs: ~2,550 trainees, roughly 100 maintenance teams", C.text1],
  ];
  const maxW = 8.0;
  rows.forEach(([k, v, big, cap, col], i) => {
    const y = 2.4 + i * 1.08, bw = Math.max(0.05, maxW * v / 9.2);
    mono(s, k, { x: 0.5, y, w: 1.1, h: 0.42, fontSize: 11, color: C.text1, valign: "middle" });
    s.addShape(pres.ShapeType.rect, { x: 1.65, y, w: bw, h: 0.42, fill: { color: col }, line: { type: "none" }, objectName: `bar-${k.toLowerCase()}` });
    tb(s, big, { x: 1.65 + bw + 0.15, y, w: 2.5, h: 0.42, fontFace: HEAD, fontSize: 20, color: k === "WEDGE" ? C.accent2 : C.text1, valign: "middle" });
    tb(s, cap, { x: 1.65, y: y + 0.5, w: 10.5, h: 0.4, fontSize: 14, color: BODY });
  });
  footer(s, 8, "BLS OEWS national tables, May 2025 · prices are our hypotheses · year 3 is a goal, not a forecast · math in appendix A4");
  s.addNotes("Bars are to scale. The wedge we sell first is about $306M a year: new maintenance techs coached for six months. The SAM adds verified records for every maintenance tech at $50 a month, which is a product hypothesis we haven't validated (it's 82% of the SAM). The TAM extends that to everyone who follows written procedures: installation, maintenance and repair (6.09M), electricians (0.76M) and production (8.57M). Not counted: other countries, aviation, field service outside these groups, and robotics.");
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
  s.addNotes("Home tasks happen a few times a year, and Meta, Google and Apple will give consumer help away free. Consumers come last, once glasses are everywhere and our models run on the device. This is a choice about order, not size. In maintenance someone signs a budget, the same procedure repeats so the data compounds, ROI shows up in a 30-day pilot, and a tablet at the bench works today without waiting for glasses. Consumer tasks are a long tail; on open-ended tasks our system is weakest (it named 0 of 7 unseen recipes from video alone). Consumers return in the last phase of the vision.");
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

// ---------- How far along: built · works · bottleneck ----------
function sProgress() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("HOW FAR ALONG", { placeholder: "eyebrow" });
  s.addText("It already works on real first-person video.\nThe bottleneck is maintenance data", { placeholder: "title" });
  const Y = 2.3;
  const head = (x, w, label, dot) => {
    line(s, x, Y, x + w, Y, { color: C.text1, width: 1.5, name: "col-rule" });
    s.addShape(pres.ShapeType.ellipse, { x, y: Y + 0.22, w: 0.16, h: 0.16, fill: { color: dot }, line: { type: "none" }, objectName: "state-dot" });
    mono(s, label, { x: x + 0.28, y: Y + 0.15, w: w - 0.3, h: 0.3, fontSize: 11, color: C.text1 });
  };
  const lead = (pairs, gap) => pairs.flatMap(([a, b], i) => [{ text: a, options: { fontFace: SEMI, color: C.text1 } }, { text: b, options: { breakLine: i < pairs.length - 1, paraSpaceAfter: gap } }]);
  head(G3.x[0], G3.w, "BUILT · OCT 2026", C.text1);
  tb(s, lead([
    ["A tracking engine ", "that knows which step of the procedure you're on, and speaks only when it's confident"],
    ["A live app ", "that runs in real time on a laptop, about 50 ms per frame"],
    ["An honest test: ", "48 held-out clips, 235 minutes, with labels we didn't write"],
  ], 16), { x: G3.x[0], y: Y + 0.65, w: G3.w - 0.2, h: 3.6, fontSize: 15, color: BODY });
  head(G3.x[1], G3.w, "WORKS · MEASURED", C.accent3);
  [
    ["54% vs 48%", "step accuracy, against the same frontier model called every 5 s", C.accent2],
    ["1/5 the cost", "$0.018 vs $0.085 per minute of video", C.text1],
    ["73%", "of clips: it named the job by itself, no setup (median 40 s)", C.text1],
    ["0", "times confidently wrong on blurred or blocked views. It asked for a better view instead", C.text1],
  ].forEach(([b, c, col], i) => {
    const y = Y + 0.65 + i * 0.93;
    tb(s, b, { x: G3.x[1], y, w: G3.w, h: 0.42, fontFace: HEAD, fontSize: 22, color: col, objectName: "works-stat" });
    tb(s, c, { x: G3.x[1], y: y + 0.42, w: G3.w - 0.15, h: 0.5, fontSize: 12.5, color: BODY, objectName: "works-caption" });
  });
  const x = G3.x[2], w = G3.w;
  s.addShape(pres.ShapeType.roundRect, { x, y: Y, w, h: 4.45, rectRadius: 0.05, fill: { color: C.text1 }, line: { type: "none" }, objectName: "panel-bottleneck" });
  mono(s, "THE BOTTLENECK", { x: x + 0.35, y: Y + 0.3, w: w - 0.7, h: 0.3, fontSize: 11, color: C.accent1 });
  tb(s, [
    { text: "Every number is from public cooking video. We couldn't get labeled maintenance video.", options: { breakLine: true, paraSpaceAfter: 12 } },
    { text: "Mistake alerts are weak: 4 of 17 named a real error.", options: { breakLine: true, paraSpaceAfter: 12 } },
    { text: "It hasn't run on glasses yet." },
  ], { x: x + 0.35, y: Y + 0.75, w: w - 0.7, h: 2.5, fontSize: 15, color: C.background2, objectName: "bottleneck-items" });
  line(s, x + 0.35, Y + 3.3, x + w - 0.35, Y + 3.3, { color: C.accent1, width: 1.5, name: "bottleneck-rule" });
  tb(s, "Labeled maintenance recordings and a pair of glasses fix all three. That's the $10k.", { x: x + 0.35, y: Y + 3.45, w: w - 0.7, h: 0.85, fontSize: 15, fontFace: SEMI, color: C.background2, objectName: "bottleneck-fix" });
  footer(s, 0, "48 held-out clips of public first-person video (CaptainCook4D) · one run per system · not yet measured on maintenance");
  s.addNotes("Where we are, in one slide. Built in October, solo: the tracking engine, a live app, and an honest test on 48 held-out clips with the dataset's own labels. What works: with the task known, it names the current step 54% of the time vs 48% for the same frontier model called every 5 seconds with no memory, at about a fifth of the cost ($0.018 vs $0.085 per video-minute). With no setup it recognized the job on 73% of clips (median 40 s). When we blurred or blocked the view it asked for a better view on 77-98% of checks and was never confidently wrong. The bottleneck, said plainly: every number is cooking video because the labeled assembly and maintenance data was unreachable; mistake alerts named a real annotated error 4 times out of 17 (the 4 it got were all out-of-order steps, which need task state); and nothing has run on glasses. All three are fixed by the same thing: labeled maintenance recordings and a pair of glasses. That's the ask. The full engine diagram is appendix A1.");
}

// ---------- Competitors ----------
function sCompetitors() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("COMPETITORS", { placeholder: "eyebrow" });
  s.addText("Others show the steps or watch one station.\nPraxis watches the work, wherever it moves", { placeholder: "title" });
  const x0 = 0.5, x1 = 7.9, y0 = 2.3, y1 = 6.6, mx = (x0 + x1) / 2, my = (y0 + y1) / 2;
  s.addShape(pres.ShapeType.rect, { x: mx, y: y0, w: x1 - mx, h: my - y0, fill: { color: C.background1 }, line: { type: "none" }, objectName: "quadrant-ours" });
  line(s, x0, my, x1, my, { color: C.text1, width: 1.25, name: "axis-x" });
  line(s, mx, y0, mx, y1, { color: C.text1, width: 1.25, name: "axis-y" });
  mono(s, "FOLLOWS THE PERSON", { x: mx + 0.12, y: y0 + 0.08, w: 3.4, h: 0.3, fontSize: 9.5, color: C.text2 });
  mono(s, "FIXED STATION", { x: mx + 0.12, y: y1 - 0.32, w: 3.4, h: 0.3, fontSize: 9.5, color: C.text2 });
  mono(s, "SHOWS THE STEPS", { x: x0, y: my + 0.1, w: 3.0, h: 0.3, fontSize: 9.5, color: C.text2 });
  mono(s, "WATCHES THE WORK", { x: x1 - 3.0, y: my + 0.1, w: 3.0, h: 0.3, fontSize: 9.5, color: C.text2, align: "right" });
  const item = (x, y, name, sub, ours) => {
    const d = ours ? 0.2 : 0.13;
    s.addShape(pres.ShapeType.ellipse, { x: x + (0.2 - d) / 2, y: y + 0.08, w: d, h: d, fill: { color: ours ? C.accent1 : C.text1 }, line: { type: "none" }, objectName: "competitor-dot" });
    tb(s, [{ text: name, options: { fontFace: SEMI, fontSize: ours ? 15 : 13, color: ours ? C.accent2 : C.text1, breakLine: true } }, { text: sub, options: { fontSize: 11, color: BODY } }], { x: x + 0.32, y, w: 3.05, h: 0.6, objectName: "competitor" });
  };
  item(0.65, 2.6, "MaintainX · Augmentir", "steps on a phone; sign-offs, not sight");
  item(0.65, 3.25, "Dynamics 365 Guides", "Microsoft ends it 31 Dec 2026");
  item(0.65, 3.9, "Manuals + videos", "explain the job; can't see you");
  item(0.65, 4.85, "Tulip · Dozuki", "apps at one station on the line");
  item(mx + 0.15, 2.6, "Praxis", "reads the shop's own manuals; on a phone today", true);
  item(mx + 0.15, 3.25, "Strivr", "films and trains per customer; early access");
  item(mx + 0.15, 3.9, "Viture + NVIDIA", "sells the glasses; ships Q1 2027");
  item(mx + 0.15, 4.85, "Retrocausal · Invisible AI", "fixed cameras at one workstation");
  const x = 8.35, w = 4.48;
  line(s, x, y0, x + w, y0, { color: C.text1, width: 1.5, name: "win-rule" });
  mono(s, "WHY WE WIN", { x, y: y0 + 0.15, w, h: 0.3, fontSize: 11, color: C.text1 });
  [
    ["No new hardware. ", "A phone or tablet today, and the camera glasses shops are already starting to buy next."],
    ["No filming each customer. ", "We compile the manuals and checklists a shop already has: 8 procedures for $4.16."],
    ["Proof, not a checkbox. ", "We track the step, verify it and keep the record. We report our accuracy; none of them publish theirs."],
  ].forEach(([a, b], i) => {
    const y = y0 + 0.6 + i * 1.3;
    if (i) line(s, x, y - 0.12, x + w, y - 0.12, { color: C.accent6, width: 0.75, name: "win-sep" });
    tb(s, [{ text: a, options: { fontFace: SEMI } }, { text: b }], { x, y, w, h: 1.15, fontSize: 14.5, objectName: "win-reason" });
  });
  footer(s, 0, "Public product pages, checked 17 Oct 2026 · Viture Helix release, 16 Jun 2026 · UC Today review of Strivr, 13 Jul 2026 · detail in appendix A8");
  s.addNotes("Two questions sort the field: does it watch the work or just show the steps, and does it follow the person or sit at one station. Procedure apps like MaintainX and Augmentir follow the person but only collect sign-offs. Fixed-camera systems like Retrocausal watch the work, but at one workstation, and maintenance moves around the machine. The closest are Strivr and Viture with NVIDIA, who are also first-person. Strivr's data team films each customer's procedures and trains a model per customer, and it's in early access with no published accuracy. Viture sells $600 safety glasses and ships in Q1 2027. Our three edges: no new hardware, no filming each customer because we compile the manuals they already have, and verified records with measured accuracy. Honest version: Tulip, Augmentir and Squint also compile instructions, and fixed-camera vendors are ahead of us on live mistake detection today.");
}

// ---------- Big Tech glasses ----------
function sBigTech() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("THE PLATFORMS", { placeholder: "eyebrow" });
  s.addText("Meta, Google and Apple are building our hardware.\nA maintenance coach isn't their business", { placeholder: "title" });
  [
    ["15M+", "AI glasses forecast to ship in 2026. Each one is a camera we can run on, and we spend $0 building it."],
    ["Sept 2026", "Meta opened its glasses' camera to outside apps. The platforms want apps like ours on top."],
    ["31 Dec 2026", "Microsoft shuts down Dynamics 365 Guides. Big Tech tried frontline maintenance and is walking away."],
  ].forEach(([b, c], i) => statCol(s, G3.x[i], 2.3, G3.w, b, c, { size: 34, capH: 1.2 }));
  const y = 4.6, h = 1.95, half = 12.33 / 2;
  s.addShape(pres.ShapeType.roundRect, { x: 0.5, y, w: 12.33, h, rectRadius: 0.05, fill: { color: C.text1 }, line: { type: "none" }, objectName: "panel-platforms" });
  line(s, 0.5 + half, y + 0.3, 0.5 + half, y + h - 0.3, { color: "3A4044", width: 1, name: "panel-divider" });
  [["THEY BUILD", C.accent6, "Glasses, cameras and one general assistant for everyone. It answers questions about a single frame."],
   ["WE BUILD", C.accent1, "The coach for one maintenance team at a time: its own procedures, step-by-step state, verified records and a pilot on site."]].forEach(([k, col, b], i) => {
    const px = 0.5 + i * half + 0.4;
    tb(s, [{ text: k, options: { fontFace: MONO, fontSize: 11, charSpacing: 1, color: col, breakLine: true, paraSpaceAfter: 8 } }, { text: b, options: { fontSize: 18, color: C.background2 } }], { x: px, y: y + 0.32, w: half - 0.8, h: h - 0.5, objectName: "panel-platforms-text" });
  });
  footer(s, 0, "Omdia AI-glasses forecast · Meta Wearables Device Access Toolkit 1.0 · Microsoft Dynamics 365 retirement notice · Apple glasses reported for 2027");
  s.addNotes("We are not competing with Meta, Google or Apple. They're paying to put cameras on people's faces: EssilorLuxottica sold over 7M AI glasses in 2025, and Omdia forecasts more than 15M shipments in 2026. Meta's Wearables toolkit 1.0 gives a third-party app the glasses' camera, mic and speakers (open App Store publishing isn't confirmed yet). Android XR glasses are reported for November; Apple's for 2027, not announced. Meanwhile the big companies are leaving frontline maintenance: Microsoft ends Dynamics 365 Guides and Remote Assist on Dec 31, and PTC retired Vuforia Chalk in October 2025. A maintenance coach needs each shop's procedures, state, records and someone on site for the pilot: a niche a platform won't staff. If Meta ships a general coach anyway, it answers about one frame, and we still run on their glasses. We also work on a phone or tablet today, so we don't depend on glasses distribution opening.");
}

// ---------- Savings, price + go-to-market ----------
function sBusiness() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("SAVINGS, PRICE + GO-TO-MARKET", { placeholder: "eyebrow" });
  s.addText("Each new tech costs a shop $11–23k of senior time.\nWe charge $1,200. One saved hour a week pays for it", { placeholder: "title" });
  statCol(s, G3.x[0], 2.3, G3.w, "$11–23k", "of senior-tech time per new hire today, by our estimate", { size: 40 });
  statCol(s, G3.x[1], 2.3, G3.w, "$1,200", "per trainee: $200 a month for six months, after a short paid pilot", { size: 40, color: C.accent2 });
  statCol(s, G3.x[2], 2.3, G3.w, "1 hour", "a week of saved senior time pays for it, out of the 10–20 hours a week a senior tech spends on each new hire", { size: 40, capH: 1.1 });
  [
    ["FIRST 10", "Founder-led paid pilots: facilities teams, service shops, and Dynamics 365 Guides customers who need a replacement"],
    ["NEXT 100", "Case studies, plus reading procedures straight from the maintenance apps shops already use"],
    ["THEN 1,000", "Distributors and glasses partners. Land one site, then every site, then records for the whole team"],
  ].forEach(([k, b], i) => {
    const x = G3.x[i];
    line(s, x, 4.6, x + G3.w, 4.6, { color: C.text1, width: 1.5, name: "gtm-rule" });
    mono(s, k, { x, y: 4.75, w: G3.w, h: 0.3, fontSize: 11, color: C.text1 });
    tb(s, b, { x, y: 5.12, w: G3.w - 0.1, h: 1.1, fontSize: 15, color: BODY });
  });
  mono(s, "OUTREACH SO FAR: 14 EMAILS SENT 17 OCT · 56 MORE SCHEDULED FOR 19 OCT", { x: 0.5, y: 6.4, w: 12.33, h: 0.3, fontSize: 10.5, color: C.text2 });
  footer(s, 0, "Pricing is our hypothesis, anchored on Tulip's $100–250 per station per month · senior-time split is our assumption (appendix A5)");
  s.addNotes("The money, from the customer's side. A new tech takes a senior tech's time: if that's 50% of a $44-an-hour senior tech for 3 months, about $11,400; at 25% for 12 months, about $22,800. That's 10 to 20 hours a week. Our assumption, and we're asking managers for their real split. We charge $200 a month per trainee for six months, $1,200, plus a one-time setup per procedure, after a short paid pilot. $200 a month is about $46 a week, about one hour of a senior tech's time, so it pays for itself if it saves one of those 10 to 20 hours. It costs us about $1.08 an hour to run today ($0.48 with our local model). Pricing risk: all-shift use squeezes a flat seat, so we'd price by coached hours or tiers (appendix A5). Go-to-market: founder-led pilots first, including Dynamics 365 Guides customers who must replace it by Dec 31. Update the outreach line with real replies before Tuesday.");
}

// ---------- The long game ----------
function sVision() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("THE LONG GAME", { placeholder: "eyebrow" });
  s.addText("Every coaching session builds data nobody else has.\nThat data is how we climb from technicians to robots", { placeholder: "title" });
  const gap = 0.15, w = (12.33 - 3 * gap) / 4, ys = [3.2, 2.9, 2.6, 2.3];
  const steps = [
    ["NOW", "Coach new maintenance techs", "Paid by maintenance managers, per trainee", "Gate: paid pilots hit their metric"],
    ["NEXT", "The record of verified work", "Paid by quality and audit teams; then field service and assembly", "Gate: customers expand without us"],
    ["THEN", "Our own models", "On the device, replacing the rented model: better margins", "Gate: match it at 1/10 the cost"],
    ["LATER", "Train and check robots", "Paid by robot labs, which already spend >$100M a year on real-world data", "Gate: a paying robot partner"],
  ];
  steps.forEach(([k, h, b, g], i) => {
    const x = 0.5 + i * (w + gap), y = ys[i], xe = i < 3 ? x + w + gap : x + w;
    line(s, x, y, xe, y, { color: i === 0 ? C.accent1 : C.text1, width: i === 0 ? 2.5 : 1.5, name: "stair-tread" });
    if (i < 3) line(s, xe, y, xe, ys[i + 1], { color: C.text1, width: 1.5, name: "stair-riser" });
    s.addShape(pres.ShapeType.ellipse, { x: x - 0.02, y: y - 0.1, w: 0.2, h: 0.2, fill: { color: i === 0 ? C.accent1 : C.text1 }, line: { type: "none" }, objectName: "stair-dot" });
    const tx = x + 0.2, tw = w - 0.3; // clear of the riser on the left
    mono(s, k, { x: tx, y: y + 0.2, w: tw, h: 0.3, fontSize: 11, color: C.text1 });
    tb(s, h, { x: tx, y: y + 0.5, w: tw, h: 0.62, fontFace: HEAD, fontSize: 16, lineSpacingMultiple: 0.95 });
    tb(s, b, { x: tx, y: y + 1.15, w: tw, h: 0.75, fontSize: 13, color: BODY });
    mono(s, g.toUpperCase(), { x: tx, y: 5.05, w: tw, h: 0.45, fontSize: 9.5, color: C.text2 });
  });
  const Pr = LC.probes, pk = {};
  Pr.rows.forEach((r) => { if (Pr.n_train_avail[r.task] >= 9) (pk[r.k] = pk[r.k] || []).push(r.acc); });
  const ks = Object.keys(pk).map(Number).sort((a, b) => a - b);
  const a0 = Math.round(mean(pk[ks[0]]) * 100), a1 = Math.round(mean(pk[ks[ks.length - 1]]) * 100);
  darkPanel(s, 0.5, 5.6, 12.33, 1.15, "THE ASSET UNDER EVERY STEP", `First-person video of skilled work, lined up to the procedure, with verified steps, real mistakes and the fixes that worked. Customers pay us to collect it, and our step models already improve with every recording (${a0}% → ${a1}%).`, 15);
  footer(s, 0, "Robot-data spend: Micro1 CEO estimate · gates are conditions, not dates · learning curve on held-out public recordings (appendix A6)");
  s.addNotes("Each step has paying demand today and produces the asset the next step needs. Now: coach new maintenance techs, paid per trainee. Next: the record of verified work that quality, audit and warranty teams pay for, then field service and assembly. Then: our own on-device models replace the rented one, which widens margins. Later: robots. Robot companies already pay for first-person human video: Figure says its Index app has paid creators $15M, and Micro1's CEO estimates robotics companies spend over $100M a year on real-world data. Raw footage is becoming a commodity. What stays scarce is skilled work in real workplaces, aligned to a plan, with verified steps, real mistakes and the fixes, plus a 'did this step succeed?' checker. We produce all of that as a by-product of coaching, and the customer pays for the coaching. Evidence that data compounds: our step models went from 31% to 51% held-out accuracy from 1 to 9 recordings, still rising. Don't say 'exponential'. Risks: human video doesn't transfer straight to robots, so the robot step is gated on a paying partner, and we never build hardware.");
}

// ---------- The ask ----------
function sAsk() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("THE ASK", { placeholder: "eyebrow" });
  s.addText([{ text: "$10k", options: { color: C.accent2 } }, { text: " clears the bottleneck and gets a first\npaid maintenance pilot by April" }], { placeholder: "title" });
  const R = (a) => a.map((t, i) => ({ text: t, options: [{ color: BODY }, {}, { fontFace: HEAD, fontSize: 15 }, { fontFace: SEMI }][i] }));
  s.addTable([
    [TH("THE GAP TODAY"), TH("WHAT THE MONEY BUYS"), TH("AMOUNT"), TH("TRUE BY APRIL")],
    R(["Every number is from cooking video", "Step-labeled recordings of real maintenance jobs", "$2,000", "Measured on real maintenance footage"]),
    R(["Mistake alerts: 4 of 17 named a real error", "Retraining the step and mistake models on that footage", "$3,000", "Mistake detection re-measured on maintenance"]),
    R(["Runs on a laptop", "Camera glasses and a capture kit", "$2,500", "Running on glasses at a real site"]),
    R(["Live coaching costs money every hour", "About 1,400 hours of pilot coaching, at ~$1.08 an hour", "$1,500", "About 30 trainee-months of coaching covered"]),
    R(["No company a customer can sign with", "Company formation and a pilot contract", "$1,000", "A first paid pilot, with a metric agreed up front"]),
  ], { ...tableOpts([3.35, 4.25, 1.2, 3.53]), y: 2.3, fontSize: 13.5, rowH: 0.6, objectName: "table-ask" });
  mono(s, "PILOT METRIC: TIME UNTIL A NEW TECH WORKS ALONE, AGREED WITH THE CUSTOMER BEFORE WE START", { x: 0.5, y: 6.25, w: 12.33, h: 0.3, fontSize: 11, color: C.text1 });
  footer(s, 0, "monishsaravana@college.harvard.edu · $10,000 over six months · same line items and amounts as the application");
  s.addNotes("Each line of the budget closes one gap from the 'how far along' slide. $2,000 buys step-labeled recordings of real maintenance jobs, so we stop measuring on cooking video. $3,000 retrains the step and mistake models on that footage; the errors we catch today all need task state, so better tracking on real procedures should mean more catches, and we re-measure it. $2,500 is camera glasses and capture gear, to run at a real site. $1,500 is pilot inference: at about $1.08 an hour that's roughly 1,400 coached hours, about 30 trainee-months at 2 hours a day. $1,000 is company formation and a pilot contract, so a customer can actually pay us. These are the same amounts as the application. The pilot metric is time until a new tech works alone, agreed with the customer before we start.");
}

// ================================================================== APPENDIX
const appx = (_label, title) => {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText(eb(""), { placeholder: "eyebrow" });
  s.addText(title, { placeholder: "title" });
  return s;
};

// ---------- Status quo ----------
function aStatusQuo() {
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Appendix" });
  s.addText(eb(""), { placeholder: "eyebrow" });
  s.addText("The status quo: what each tool does today, and what it misses", { placeholder: "title" });
  const cols = [
    ["SHADOWING", "A senior tech, side by side", "The real teacher today", "About $44 an hour of senior time, one trainee at a time"],
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
    R(["SOM", "1% of new maintenance techs ≈ 2,550 trainees a year, ~100 mid-size teams", "2,550 × $200 × 6 months", "≈ $3M ARR"]),
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
    [TH("DESIGN"), TH("$ / VIDEO-MIN"), TH("$ / TRAINEE-MONTH, 2 H/DAY"), TH("MARGIN AT $200")],
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
    R(["Glasses aren't ready", "It works on a tablet or phone today. Glasses are one more input adapter"]),
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
  const s = appx("APPENDIX · A8", "Glasses and voice: what's built, and what's designed");
  const cols = [
    ["BUILT", C.accent3, ["Runs live in real time on a recorded stream, with the local layers at about 50 ms per frame", "Model calls run in the background, so the live loop never waits (worst lag 0.8 s)", "Speaks its instructions; an urgent line cuts the queue", "Praxis Studio: the engine in a browser, on a camera, an upload or a test clip"]],
    ["DESIGNED, NOT BUILT", C.text2, ["Glasses input adapters (Meta camera toolkit, Android XR), one adapter pattern per device", "Voice input in natural language: \"skip that\", \"why?\", \"no, I'm still on the belt\"", "Push-to-talk by default; a protection headset in loud plants", "Face and badge blur; a local-model tier for sensitive sites"]],
  ];
  cols.forEach(([h, col, items], i) => {
    const x = 0.5 + i * 6.42;
    line(s, x, 2.2, x + 5.91, 2.2, { color: C.text1, width: 1.5, name: "col-rule" });
    s.addShape(pres.ShapeType.ellipse, { x, y: 2.45, w: 0.18, h: 0.18, fill: { color: col }, line: { type: "none" }, objectName: "state-dot" });
    mono(s, h, { x: x + 0.32, y: 2.4, w: 5.5, h: 0.3, fontSize: 11, color: C.text1 });
    tb(s, items.map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < items.length - 1, paraSpaceAfter: 8 } })), { x, y: 2.9, w: 5.91, h: 3.4, fontSize: 14 });
  });
  footer(s, TOTAL, "We say \"designed to run on\" glasses until an adapter has run on that device");
}

// ================================================================== ORDER
const CORE = [
  ["Story", [sCover, sProblem, sProduct, sProgress]],
  ["Why now", [sWhyNow]],
  ["Why we win", [sCompetitors, sBigTech]],
  ["Market", [sMarket, sBusiness]],
  ["Vision", [sVision]],
  ["Ask", [sAsk]],
];
const APPENDIX = [sEngine, sEvidence, aStatusQuo, aMarketMath, aUnitEcon, aCurves, aTraining, aCompetitors, sConsumers, aRisks, aGlasses, sFounder];
for (const [title, fns] of CORE) {
  pres.addSection({ title });
  SECTION = title;
  for (const f of fns) { CUR++; f(); }
}
if (CUR !== TOTAL) throw new Error(`TOTAL is ${TOTAL} but the core deck has ${CUR} slides`);
pres.addSection({ title: "Appendix" });
SECTION = "Appendix";
APPENDIX.forEach((f, i) => { APX = `A${i + 1}`; f(); });

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
