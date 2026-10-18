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

const A = (f) => path.join(ROOT, "brand", "deck", "assets", f);
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
const MONO = "IBM Plex Mono";
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
function footer(slide, n, source, x0 = 0.5) {
  slide.addImage({ path: MK(`prog-light-${n}of${TOTAL}.png`), x: x0, y: 6.93, h: 0.3, w: 0.3 * MARK_RATIO, objectName: "progress-mark" });
  if (source) slide.addText(source, { x: x0 + 1.0, y: 6.93, w: 12.83 - x0 - 1.0, h: 0.3, fontFace: MONO, fontSize: 9.5, color: C.text2, align: "right", valign: "middle", margin: 0, isTextBox: true, objectName: "footer-source" });
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
  const x0 = opts.right ? 1920 - 56 - w : 56, y0 = bottom - h;
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
  slide.addShape(pres.ShapeType.roundRect, { x: P(1920 - 40 - w), y: P(1032), w: P(w), h: P(34), rectRadius: P(6), fill: { color: HUD.ink, transparency: 40 }, line: { type: "none" }, objectName: "concept-tag" });
  slide.addText("CONCEPT MOCK · STOCK PHOTO", { x: P(1920 - 40 - w), y: P(1032), w: P(w), h: P(34), fontFace: MONO, fontSize: 8, charSpacing: 1, color: "C9CFCC", align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "concept-tag-text" });
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

const tableOpts = (colW, w = 12.33) => ({ x: 0.5, y: 2.2, w, colW, fontFace: "Archivo", fontSize: 12, color: "16191B", border: { type: "solid", color: "C9CFCC", pt: 0.75 }, valign: "middle", rowH: 0.52, fill: { color: "F6F7F6" } });
const TH = (t) => ({ text: t, options: { fontFace: MONO, fontSize: 10, color: "E8EBE9", fill: { color: "16191B" } } });

// hero: rule, one big number or word, one caption (the brand "statement slide" pattern, bigger)
function hero(slide, x, y, w, big, cap, o = {}) {
  const size = o.size || 60;
  line(slide, x, y, x + w, y, { color: C.text1, width: 1.5, name: "hero-rule" });
  tb(slide, big, { x, y: y + 0.2, w, h: size / 72 * 1.2, fontFace: HEAD, fontSize: size, color: o.color || C.text1, objectName: "hero" });
  tb(slide, cap, { x, y: y + 0.3 + size / 72 * 1.2, w: w - 0.2, h: o.capH || 1.2, fontSize: o.capSize || 17, objectName: "hero-caption" });
}

// ---------- 1 · Cover ----------
pres.addSection({ title: "Story" });
{
  const s = pres.addSlide({ masterName: "Praxis Photo", sectionTitle: "Story" });
  photo(s, "photo-cover.jpg");
  s.addImage({ path: A("praxis-lockup-white.png"), x: 0.5, y: 0.55, h: 0.4, w: 0.4 * LOCKUP_RATIO, objectName: "logo" });
  s.addText("Instructions that can finally see how you're doing", { x: 0.5, y: 2.05, w: 5.6, h: 2.4, fontFace: HEAD, fontSize: 38, color: C.background2, valign: "middle", margin: 0, lineSpacingMultiple: 0.95, isTextBox: true, objectName: "cover-headline" });
  tb(s, "An AI coach for new maintenance technicians. It watches the work through a first-person camera and says the next step.", { x: 0.5, y: 4.6, w: 5.2, h: 1.0, fontSize: 16, color: C.background2, objectName: "cover-oneliner" });
  s.addText("STARTUPS @ HARVARD · 20 OCT 2026 · MONISH SARAVANA", { x: 0.5, y: 6.75, w: 6.5, h: 0.3, fontFace: MONO, fontSize: 10, charSpacing: 1, color: C.accent6, margin: 0, valign: "middle", isTextBox: true, objectName: "cover-meta" });
  const reg = [860, 640, 1180, 900];
  hudRegion(s, reg, HUD.green);
  hudPulse(s, 1010, 790, HUD.green);
  hudProgress(s, 4, 9, 1920 - 56 - 247);
  const chip = hudChip(s, "Seat the clamp past the hose bead", 624, { right: true });
  hudLeader(s, chip, reg, HUD.green);
  conceptTag(s);
  s.addNotes("Hi, I'm Monish. Praxis is an AI coach for physical work. It watches through a first-person camera, knows where a new technician is in a procedure, checks the work and says the next step. The photo is stock with a mocked-up HUD; the engine behind it is real, and I'll show the numbers.");
}

// ---------- 2 · Problem ----------
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Story" });
  s.addText("THE PROBLEM", { placeholder: "eyebrow" });
  s.addText("A new maintenance technician needs about a year of a senior tech's time to work alone", { placeholder: "title" });
  hero(s, 0.5, 2.55, 6.4, ">1 year", "of on-the-job training, with a senior tech as the teacher.", { color: C.accent2 });
  hero(s, 7.1, 2.55, 5.73, "$11–23k", "of senior-tech time per new hire (our estimate).");
  footer(s, 2, "BLS Occupational Outlook Handbook · BLS Employer Costs for Employee Compensation, June 2025 · estimate labeled as ours");
  s.addNotes("The $11-23k is 25-50% of a $44-an-hour senior tech for 3-12 months. BLS says on-the-job training for these jobs typically lasts more than a year. A 2017 survey of 35 aviation repair stations found 9 to 14 months before a new hire was profitable, some 24. $44 an hour is the BLS median wage ($30.82) divided by the 70.2% wage share of employer cost; senior techs cost more. The $11-23k range is our assumption (50% of a senior tech for 3 months, or 25% for 12) and we're asking managers for their real number. Manuals and videos can't see you, so the senior tech is the real teacher, and that time sits in nobody's training budget.");
}

// ---------- 3 · Product ----------
{
  const s = pres.addSlide({ masterName: "Praxis Photo", sectionTitle: "Story" });
  photo(s, "photo-step.jpg");
  const reg = [800, 300, 1260, 820];
  hudRegion(s, reg, HUD.orange);
  hudProgress(s, 3, 8, 1920 - 56 - 247);
  const chip = hudChip(s, "Loosen the four float-bowl screws a half turn each", 903, { right: true });
  hudLeader(s, chip, reg, HUD.orange);
  s.addShape(pres.ShapeType.rect, { x: 0, y: 0, w: 4.95, h: 7.5, fill: { color: C.text1, transparency: 6 }, line: { type: "none" }, objectName: "product-panel" });
  mono(s, "THE PRODUCT", { x: 0.5, y: 0.6, w: 4.0, h: 0.3, fontSize: 11, color: C.accent6 });
  tb(s, "Praxis watches the work and coaches one step at a time", { x: 0.5, y: 1.0, w: 4.1, h: 2.2, fontFace: HEAD, fontSize: 28, color: C.background2, lineSpacingMultiple: 0.95 });
  [["LOAD", "the manuals, checklists and work orders a shop already has"], ["COACH", "on a phone at the bench or on glasses, one short line at a time"], ["VERIFY", "critical steps and keep a record with keyframes"]].forEach(([k, b], i) => {
    const y = 3.75 + i * 0.95;
    line(s, 0.5, y, 4.45, y, { color: "3A4044", width: 1, name: "product-rule" });
    mono(s, k, { x: 0.5, y: y + 0.15, w: 1.2, h: 0.3, fontSize: 11, color: C.background2 });
    tb(s, b, { x: 1.55, y: y + 0.12, w: 2.95, h: 0.75, fontSize: 14, color: C.accent6 });
  });
  conceptTag(s);
  s.addNotes("What it is: software, not glasses. It runs on a tablet at the bench today and on camera or display glasses through an input adapter. It speaks; cards appear only for mistakes and view requests, and the step graph is never shown. It verifies, logs, and flags mistakes only when confident. Mistake detection is our weakest number today (4 of 17 alerts named a real annotated error), so this slide shows step tracking, which is what we measure best. Buyer: the maintenance manager. User: the new tech.");
}

// ---------- 4 · How it works ----------
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Story" });
  s.addText("HOW IT WORKS", { placeholder: "eyebrow" });
  s.addText("Cheap models watch every frame. The big model is called only when something happens", { placeholder: "title" });
  const bx = (name, x, y, w, h, title, spec, hero) => {
    s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.04, fill: { color: hero ? C.accent1 : C.background1 }, line: hero ? { type: "none" } : { color: C.text1, width: 1.25 }, objectName: `box-${name}` });
    tb(s, title, { x: x + 0.2, y: y + 0.2, w: w - 0.4, h: 0.4, fontFace: SEMI, fontSize: 17 });
    mono(s, spec, { x: x + 0.2, y: y + 0.65, w: w - 0.4, h: 0.5, fontSize: 11, color: hero ? C.text1 : C.text2 });
  };
  const Y = 2.75, H = 1.25, W = 2.75, G = 0.43;
  const xs = [0.5, 0.5 + (W + G), 0.5 + 2 * (W + G), 0.5 + 3 * (W + G)];
  bx("camera", xs[0], Y, W, H, "Camera", "first-person video");
  bx("local", xs[1], Y, W, H, "Local layers", "every frame · ~50 ms");
  bx("tracker", xs[2], Y, W, H, "State tracker", "belief over the steps");
  bx("coach", xs[3], Y, W, H, "Coach", "speaks when confident", true);
  for (let i = 0; i < 3; i++) line(s, xs[i] + W, Y + H / 2, xs[i + 1], Y + H / 2, { color: C.text1, width: 1.25, arrow: true, name: "arrow-fast" });
  bx("fast", xs[2], 4.95, W, H, "Fast verifier", "rented · 151 ms median");
  bx("frontier", xs[3], 4.95, W, H, "Frontier model", "rented · 3.8 s · hard cases");
  line(s, xs[2] + W / 2, Y + H, xs[2] + W / 2, 4.95, { color: C.text1, width: 1.25, arrow: true, dash: "dash", name: "arrow-escalate" });
  mono(s, "14% OF FRAMES", { x: xs[2] + W / 2 + 0.15, y: 4.33, w: 1.9, h: 0.3, fontSize: 10.5, color: C.text1 });
  line(s, xs[2] + W, 4.95 + H / 2, xs[3], 4.95 + H / 2, { color: C.text1, width: 1.25, arrow: true, dash: "dash", name: "arrow-fast-frontier" });
  mono(s, "88% ANSWERED FAST · 12% ESCALATE", { x: xs[2], y: 6.3, w: 6.0, h: 0.3, fontSize: 10.5, color: C.text2 });
  mono(s, "OURS: THE TRACKER, DETECTOR, CALIBRATION AND LOCAL STUDENT. RENTED: ONLY THE VERIFIERS, SWAPPABLE IN ONE LINE", { x: xs[0], y: 4.95, w: W * 2 + G, h: 1.25, fontSize: 10.5, color: C.text2, valign: "middle" });
  footer(s, 4, "Measured on 48 held-out first-person clips · full engine in appendix A1");
  s.addNotes("Two speeds. Open models on the device turn every frame into features in about 50 ms. Our state tracker keeps a running belief about which step you're on, over a task graph compiled from the manual. Only when something happens (a step ends, it's unsure, or you're stuck) does it ask a rented model one typed question: that's 14% of frames, 88% of them answered by the fast tier. The frontier model is a swappable part; swapping it is one config line. The full engine diagram is appendix A1.");
}

// ---------- 5 · Evidence ----------
{
  const s = pres.addSlide({ masterName: "Praxis Split", sectionTitle: "Story" });
  s.addShape(pres.ShapeType.rect, { x: 0, y: 0, w: 7.2, h: 7.5, fill: { color: C.text1 }, line: { type: "none" }, objectName: "results-panel" });
  s.addChart(pres.ChartType.bar, [{ name: "Step accuracy", labels: ["Model every 5 s", "Praxis"], values: [48, 54] }],
    { ...darkChart("Step accuracy · same frontier model"), chartColors: ["4A5156", "FF5B14"], x: 0.5, y: 0.7, w: 6.2, h: 2.7, valAxisMaxVal: 70, valAxisMinVal: 0, dataLabelFormatCode: '0"%"', objectName: "chart-accuracy" });
  s.addChart(pres.ChartType.bar, [{ name: "Cost per video-minute", labels: ["Model every 5 s", "Praxis"], values: [0.085, 0.018] }],
    { ...darkChart("Cost per minute of video"), chartColors: ["4A5156", "FF5B14"], x: 0.5, y: 3.9, w: 6.2, h: 2.7, valAxisMaxVal: 0.11, valAxisMinVal: 0, dataLabelFormatCode: '"$"0.000', objectName: "chart-cost" });
  s.addText("EVIDENCE", { placeholder: "eyebrow" });
  s.addText("Same frontier model, with our tracking: 13% more accurate at a fifth of the cost", { placeholder: "title" });
  [["13%", "more accurate at tracking the current step"], ["1/5", "the cost per minute of video"]].forEach(([b, c], i) => {
    const y = 3.35 + i * 1.55;
    line(s, 7.85, y, 12.83, y, { color: C.text1, width: 1.5, name: "result-rule" });
    tb(s, b, { x: 7.85, y: y + 0.15, w: 4.98, h: 0.8, fontFace: HEAD, fontSize: 44, color: i === 0 ? C.accent2 : C.text1 });
    tb(s, c, { x: 7.85, y: y + 0.95, w: 4.98, h: 0.45, fontSize: 16 });
  });
  footer(s, 5, "48 held-out clips of public cooking video · one run each", 7.85);
  s.addNotes("Like-for-like: the same frontier model on the same frames. Called every 5 seconds with no memory of the task, it names the current step on 48% of frames; with our tracking around it, 54%, at $0.018 vs $0.085 per video-minute. The baseline is a call every 5 seconds, not every frame. With our distilled local model doing routine checks: 52% at $0.008, 11x cheaper. When the view was blurred or blocked it asked for a better view on 77-98% of checks and was never confidently wrong. Caveats to say out loud: one run per system, public cooking video. Procedures are procedures; maintenance footage is the first thing the grant buys.");
}

// ---------- 6 · Learning curve ----------
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Story" });
  s.addText("IT COMPOUNDS", { placeholder: "eyebrow" });
  s.addText("Our models get better with every recording, so every customer session makes Praxis better", { placeholder: "title" });
  const Pr = LC.probes, pk = {};
  Pr.rows.forEach((r) => { if (Pr.n_train_avail[r.task] >= 9) (pk[r.k] = pk[r.k] || []).push(r.acc); });
  const ks = Object.keys(pk).map(Number).sort((a, b) => a - b);
  const pacc = ks.map((k) => pct1(mean(pk[k])));
  s.addChart(pres.ChartType.line, [{ name: "Step model", labels: ks.map(String), values: pacc }], {
    x: 0.5, y: 2.3, w: 8.2, h: 4.3, lineSize: 3.5, lineDataSymbol: "circle", lineDataSymbolSize: 9, showValue: false, showLegend: false,
    valAxisMinVal: 0, valAxisMaxVal: 60, valAxisMajorUnit: 10, valAxisLabelFormatCode: '0"%"', chartColors: ["FF5B14"],
    valAxisLabelColor: "5E676C", catAxisLabelColor: "5E676C", valAxisLabelFontSize: 12, catAxisLabelFontSize: 12,
    valAxisLabelFontFace: "+mn-lt", catAxisLabelFontFace: "+mn-lt", catAxisLineShow: false, valAxisLineShow: false,
    valGridLine: { color: "D0D5D2", size: 0.75 }, catGridLine: { style: "none" },
    showCatAxisTitle: true, catAxisTitle: "Training recordings per procedure", catAxisTitleFontSize: 12, catAxisTitleColor: "5E676C", catAxisTitleFontFace: "+mn-lt",
    objectName: "chart-learning-curve",
  });
  hero(s, 9.1, 2.45, 3.73, `${pacc[0]}% → ${pacc[pacc.length - 1]}%`, "step accuracy on videos it never trained on, from 1 to 9 recordings. Still rising.", { size: 30 });
  tb(s, "Today this is public video. Next, it's our customers' sessions: step-labeled skilled work that nobody else has.", { x: 9.1, y: 4.75, w: 3.73, h: 1.5, fontSize: 16, color: BODY });
  footer(s, 6, "Retrained on random subsets of public train-split recordings, 5 seeds per point");
  s.addNotes("We retrained our step models on growing slices of the training data and scored them only on recordings they never saw, so this isn't memorization. Steady gains per doubling, not 'exponential'. The local student model shows the same pattern: 62.6% to 72.5% on 469 held-out checks from 4 to 30 recordings (appendix A5). The engine we evaluated used only 3 recordings per procedure, so there's headroom we haven't used yet. Contracts include the right to use de-identified procedural data, with a discount for sharing.");
}

// ---------- 7 · Why now ----------
pres.addSection({ title: "Market" });
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Market" });
  s.addText("WHY NOW", { placeholder: "eyebrow" });
  s.addText("This year, frontline teams are choosing what replaces their last generation of tools", { placeholder: "title" });
  const ev = [
    ["28 MAY 2026", "Autodesk agrees to buy MaintainX for $3.6B"],
    ["16 JUN 2026", "Viture + NVIDIA announce coaching glasses"],
    ["SEPT 2026", "Meta opens its glasses' camera to apps"],
    ["31 DEC 2026", "Microsoft ends Dynamics 365 Guides", true],
    ["Q1 2027", "Helix and Android XR display glasses ship"],
  ];
  const cw = 12.33 / 5;
  line(s, 0.5, 2.75, 12.83, 2.75, { color: C.text1, width: 1.5, name: "timeline" });
  ev.forEach(([d, t, hl], i) => {
    const x = 0.5 + i * cw;
    s.addShape(pres.ShapeType.ellipse, { x, y: 2.63, w: 0.24, h: 0.24, fill: { color: hl ? C.accent1 : C.text1 }, line: { type: "none" }, objectName: "timeline-dot" });
    mono(s, d, { x, y: 3.1, w: cw - 0.25, h: 0.3, fontSize: 11, color: hl ? C.accent2 : C.text1 });
    tb(s, t, { x, y: 3.45, w: cw - 0.3, h: 1.3, fontSize: 16 });
  });
  line(s, 0.5, 5.35, 12.83, 5.35, { color: C.accent6, width: 0.75, name: "why-rule" });
  tb(s, [{ text: "And it finally costs out: ", options: { fontFace: SEMI } }, { text: "about $1 an hour of video for us, vs $5 for a model on a timer." }], { x: 0.5, y: 5.55, w: 12.33, h: 0.8, fontSize: 16 });
  footer(s, 7, "Autodesk–MaintainX release · Viture/NVIDIA release · Meta Wearables toolkit 1.0 · Microsoft Dynamics 365 retirement notice");
  s.addNotes("Why not 2023: no glasses let apps read the camera, and calling a vision model often enough to coach was too slow and too expensive. Now the hardware and plumbing are being built around us, the incumbent generation (HoloLens-era Guides and Remote Assist) is ending on Dec 31, and the budget is proven by the MaintainX deal. Nobody publishes accuracy numbers on the coach itself; we do. Apple glasses are reported for 2027, not announced.");
}

// ---------- 8 · Market ----------
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Market" });
  s.addText("MARKET · US, PER YEAR, BOTTOM-UP", { placeholder: "eyebrow" });
  s.addText("A $300M wedge inside a $1.8B first market, inside a $9B one", { placeholder: "title" });
  const rows = [
    ["TAM", 9.2, "$9.2B", "15.4M US workers who follow written procedures, at $50 a month for verified records", C.accent6],
    ["SAM", 1.8, "$1.8B", "2.47M US maintenance and repair techs: coaching new hires + records for everyone", "5E676C"],
    ["WEDGE", 0.306, "$306M", "~255k new maintenance techs a year, coached for 6 months at $200 a month", C.accent1],
    ["YEAR 3", 0.003, "$3M ARR", "1% of new techs: ~2,550 trainees, roughly 100 maintenance teams", C.text1],
  ];
  const maxW = 8.0;
  rows.forEach(([k, v, big, cap, col], i) => {
    const y = 2.3 + i * 1.08;
    mono(s, k, { x: 0.5, y: y + 0.05, w: 1.1, h: 0.3, fontSize: 11, color: C.text1 });
    s.addShape(pres.ShapeType.rect, { x: 1.65, y, w: Math.max(0.05, maxW * v / 9.2), h: 0.42, fill: { color: col }, line: { type: "none" }, objectName: `bar-${k.toLowerCase()}` });
    tb(s, big, { x: 1.65 + Math.max(0.05, maxW * v / 9.2) + 0.15, y: y - 0.04, w: 2.5, h: 0.5, fontFace: HEAD, fontSize: 20, color: k === "WEDGE" ? C.accent2 : C.text1, valign: "middle" });
    tb(s, cap, { x: 1.65, y: y + 0.48, w: 10.5, h: 0.4, fontSize: 13.5, color: BODY });
  });
  footer(s, 8, "BLS OEWS national tables, May 2025 · prices are our hypotheses · year 3 is a goal, not a forecast · math in appendix A3");
  s.addNotes("Bars are to scale. The wedge we sell first is about $300M a year: new maintenance techs coached for six months. The SAM adds verified records for every maintenance tech at $50 a month, which is a product hypothesis we haven't validated (it's 82% of the SAM). The TAM extends that to everyone who follows written procedures: installation, maintenance and repair (6.09M), electricians (0.76M) and production (8.57M). Not counted: other countries, aviation, field service outside these groups, and robotics.");
}

// ---------- 9 · Why not consumers ----------
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Market" });
  s.addText("THE OBVIOUS QUESTION", { placeholder: "eyebrow" });
  s.addText("Why not consumers first? Because the budget and the repeat data are in business", { placeholder: "title" });
  hero(s, 0.5, 2.55, 6.0, "$3.6B", "what Autodesk agreed to pay for MaintainX, an app that puts maintenance procedures on a phone.", { color: C.accent2 });
  hero(s, 7.1, 2.55, 5.73, "$99 → $25", "what Frontdoor's expert video help for homeowners fell to, per year, from 2023 to 2024.");
  line(s, 0.5, 5.3, 12.83, 5.3, { color: C.accent6, width: 0.75, name: "consumer-rule" });
  tb(s, [{ text: "The same checklist runs on every machine, every month. ", options: { fontFace: SEMI } }, { text: "Home tasks don't repeat, and the platforms give consumer help away free. Consumers come last." }], { x: 0.5, y: 5.45, w: 12.33, h: 1.0, fontSize: 16 });
  footer(s, 9, "Autodesk–MaintainX release (28 May 2026) · Frontdoor pricing 2023–2024");
  s.addNotes("Home tasks happen a few times a year, and Meta, Google and Apple will give consumer help away free. Consumers come last, once glasses are everywhere and our models run on the device. This is a choice about order, not size. In maintenance someone signs a budget, the same procedure repeats so the data compounds, ROI shows up in a 30-day pilot, and a tablet at the bench works today without waiting for glasses. Consumer tasks are a long tail; on open-ended tasks our system is weakest (it named 0 of 7 unseen recipes from video alone). Consumers return in the last phase of the vision.");
}

// ---------- 10 · Why can't big firms copy this ----------
pres.addSection({ title: "Why we win" });
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Why we win" });
  s.addText("THE OTHER OBVIOUS QUESTION", { placeholder: "eyebrow" });
  s.addText("Why can't Meta, Google or Tulip build this? They sell the glasses or the steps. Nobody owns verified work", { placeholder: "title" });
  const layers = [
    ["DEVICES", "Meta · Google · Viture", "Sell the glasses and the camera"],
    ["ASSISTANTS", "Meta AI · Gemini", "Answer about one frame. No plan, no state"],
    ["PRAXIS", "Verified work", "Knows the step, checks it, keeps the record", true],
    ["PROCEDURE APPS", "MaintainX · Tulip · Augmentir", "Hold the steps. Sign-offs, not sight"],
  ];
  layers.forEach(([k, who, what, hl], i) => {
    const y = 2.4 + i * 0.98, w = 7.4;
    s.addShape(pres.ShapeType.rect, { x: 0.5, y, w, h: 0.82, fill: { color: hl ? C.background1 : C.background2 }, line: hl ? { color: C.accent1, width: 2.5 } : { color: C.accent6, width: 0.75 }, objectName: `layer-${i + 1}` });
    mono(s, k, { x: 0.75, y: y + 0.12, w: 2.0, h: 0.3, fontSize: 10.5, color: hl ? C.accent2 : C.text2 });
    tb(s, who, { x: 0.75, y: y + 0.4, w: 2.6, h: 0.35, fontFace: SEMI, fontSize: 14 });
    tb(s, what, { x: 3.4, y: y + 0.12, w: 4.3, h: 0.6, fontSize: 14, color: BODY, valign: "middle" });
  });
  const x = 8.35, w = 4.48;
  mono(s, "IF THEY MOVE", { x, y: 2.4, w, h: 0.3, fontSize: 11, color: C.text1 });
  tb(s, runs([
    ["A platform ships a coach: ", "it's our hardware and channel."],
    ["Tulip or MaintainX adds cameras: ", "we're their verification layer, or acquisition."],
    ["Helix ships: ", "we run on it."],
  ], 10), { x, y: 2.8, w, h: 2.6, fontSize: 14.5 });
  line(s, x, 5.45, x + w, 5.45, { color: C.accent6, width: 0.75, name: "moat-rule" });
  tb(s, "The moat we're building: customer session data, and records nobody wants to rip out.", { x, y: 5.6, w, h: 0.9, fontSize: 13.5, color: BODY });
  footer(s, 10, "Public product pages, checked 17 Oct 2026 · Meta Wearables toolkit 1.0 · Tulip Factory Playback announcement");
  s.addNotes("Honest version. Tulip, Augmentir and Squint already compile instructions. Tulip is testing camera checks of whether a procedure was followed. Retrocausal tracks whole procedures, on fixed cameras at one station. On live mistake detection we're behind fixed-camera vendors today. Viture + NVIDIA and Strivr are first-person; Helix ships Q1 2027 and Strivr films each customer first. The big platforms' play is hardware and consumer assistants. The real defensibility comes once pilots start: step-labeled customer sessions, verified records the customer's quality and audit teams depend on, and integrations into their maintenance systems.");
}

// ---------- 11 · Business model + GTM ----------
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Why we win" });
  s.addText("BUSINESS MODEL + GO-TO-MARKET", { placeholder: "eyebrow" });
  s.addText("One saved senior-tech hour a week pays for a seat", { placeholder: "title" });
  tb(s, [
    { text: "$2,400 ÷ 52 ÷ $44 ≈ ", options: { color: C.text1 } },
    { text: "1 hour", options: { color: C.accent2 } },
  ], { x: 0.5, y: 2.2, w: 12.33, h: 1.0, fontFace: HEAD, fontSize: 40 });
  mono(s, "A $200-A-MONTH SEAT · A YEAR · WEEKS · A SENIOR TECH'S HOURLY COST", { x: 0.5, y: 3.2, w: 12.33, h: 0.3, fontSize: 10.5, color: C.text2 });
  const steps = [
    ["FIRST 10", "Founder-led paid pilots with facilities teams and service shops"],
    ["NEXT 100", "Case studies, plus integrations with the apps shops already use"],
    ["THEN 1,000", "Distributors and glasses partners; land one site, then every site"],
  ];
  const cw = 12.33 / 3;
  steps.forEach(([k, b], i) => {
    const x = 0.5 + i * cw, w = cw - 0.35;
    line(s, x, 4.05, x + w, 4.05, { color: C.text1, width: 1.5, name: "gtm-rule" });
    mono(s, k, { x, y: 4.2, w, h: 0.3, fontSize: 11, color: C.text1 });
    tb(s, b, { x, y: 4.6, w, h: 1.4, fontSize: 15, color: BODY });
  });
  mono(s, "OUTREACH: 14 EMAILS SENT 17 OCT · 56 SCHEDULED FOR 19 OCT", { x: 0.5, y: 6.25, w: 12.33, h: 0.3, fontSize: 10.5, color: C.text1 });
  footer(s, 11, "Pricing is our hypothesis, anchored on Tulip's $100–250 per station per month · run cost about $1.08 an hour");
  s.addNotes("First 10: facilities teams, HVAC and equipment-service shops, technical training programs, and Dynamics 365 Guides customers who need a replacement, each with a metric agreed up front. Next 100: case studies, and reading procedures straight from the maintenance apps shops already use. Then 1,000: distributors and glasses partners; new techs first, then records for the whole team. Who pays: the maintenance or service manager. How: a short paid pilot, then a subscription per trainee per month ($150-250 to test) plus a one-time setup per procedure. It costs us about $1.08 an hour to run today ($0.48 with the local model), against $4.76 an hour to the customer at 2 hours a day. Pricing risk: all-shift use squeezes a flat seat, so price by coached hours or tiers (appendix A4). Update the outreach line with real replies before Tuesday.");
}

// ---------- 12 · Founder ----------
pres.addSection({ title: "Team" });
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Team" });
  s.addText("WHY ME", { placeholder: "eyebrow" });
  s.addText("I've built real-time vision on messy video before, and I built this in a week", { placeholder: "title" });
  const cw = 12.33 / 3;
  [
    ["LipTrac", "Real-time lip reading from ordinary video. 60,000+ frames, 12 testers, provisional patent filed.", C.accent2],
    ["7 years", "of competitive robotics, coaching teammates without seeing what they see.", C.text1],
    ["1 week", "to build the engine, a 48-video eval and a live app, solo. First commit Oct 17.", C.text1],
  ].forEach(([b, c, col], i) => hero(s, 0.5 + i * cw, 2.55, cw - 0.35, b, c, { color: col, size: 40, capH: 1.6 }));
  tb(s, "Monish Saravana · Harvard College · solo founder. Also: path planning for oil-cleanup boats from aerial imagery.", { x: 0.5, y: 5.9, w: 12.33, h: 0.4, fontSize: 14, color: BODY });
  footer(s, 12, "Startups @ Harvard application");
  s.addNotes("Solo founder is a known risk: the grant tests demand before hiring, and first hires come after the pilot. The provisional patent is LipTrac's, filed before this application. Next step on domain: shadow a maintenance tech and recruit an advisor from the outreach replies.");
}

// ---------- 13 · Vision ----------
pres.addSection({ title: "Vision" });
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Vision" });
  s.addText("THE LONG GAME", { placeholder: "eyebrow" });
  s.addText("We're building the record of how physical work gets done right", { placeholder: "title" });
  const steps = [
    ["NOW", "Coach new technicians", "Paid per trainee. Every session is labeled data.", "Gate: paid pilots hit their metric"],
    ["NEXT", "Verify and record critical work", "The record quality and audit teams pay for.", "Gate: customers expand without us"],
    ["LATER", "Check any worker or robot", "Our data and models train and check robots.", "Gate: a paying robot partner"],
  ];
  const cw = 12.33 / 3;
  line(s, 0.5, 2.62, 12.83, 2.62, { color: C.text1, width: 1.5, name: "vision-line" });
  steps.forEach(([k, h, b, g], i) => {
    const x = 0.5 + i * cw, w = cw - 0.4;
    s.addShape(pres.ShapeType.ellipse, { x, y: 2.5, w: 0.24, h: 0.24, fill: { color: i === 0 ? C.accent1 : C.text1 }, line: { type: "none" }, objectName: "vision-dot" });
    mono(s, k, { x, y: 2.95, w, h: 0.3, fontSize: 11, color: i === 0 ? C.accent2 : C.text1 });
    tb(s, h, { x, y: 3.3, w, h: 0.85, fontFace: HEAD, fontSize: 20, lineSpacingMultiple: 0.95 });
    tb(s, b, { x, y: 4.2, w, h: 1.3, fontSize: 15, color: BODY });
    mono(s, g.toUpperCase(), { x, y: 5.65, w, h: 0.5, fontSize: 10, color: C.text2 });
  });
  footer(s, 13, "Valuations: Figure $39B (Sept 2025) · Physical Intelligence $5.6B (Nov 2025) · Skild AI >$14B (Jan 2026)");
  s.addNotes("Next: the system of record that quality, audit and warranty teams pay for, then field service, assembly and aviation. Later: consumers too, once glasses are everywhere. Two horizons. Near term: coach new maintenance techs. Long term: the model of how physical work gets done correctly, which every worker and every robot needs. Robot companies already pay for first-person human video; our customers pay us to collect ours, and the plants we coach in are the ones buying robots. Honest risks: human video doesn't transfer straight to robots, and robot work is capital-heavy, so it's gated on a paying partner and we never build hardware. With customers and workers, the story is 'robots work next to you'.");
}

// ---------- 14 · Ask ----------
pres.addSection({ title: "Ask" });
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Ask" });
  s.addText("THE ASK", { placeholder: "eyebrow" });
  s.addText("$10k makes a first paid maintenance pilot true by April", { placeholder: "title" });
  mono(s, "TODAY", { x: 0.5, y: 2.2, w: 5.4, h: 0.3, fontSize: 11, color: C.text2 });
  mono(s, "BY APRIL", { x: 6.92, y: 2.2, w: 5.9, h: 0.3, fontSize: 11, color: C.accent2 });
  [
    ["Measured on public cooking video", "Measured on real maintenance footage"],
    ["Runs live on a laptop", "Running on glasses at a real site"],
    ["Mistake alerts: 4 of 17 named a real error", "Mistake detection re-measured on maintenance"],
    ["No customers yet", "A first paid pilot, judged on time to work alone"],
  ].forEach(([a, b], i) => {
    const y = 2.6 + i * 0.66;
    line(s, 0.5, y, 12.83, y, { color: C.accent6, width: 0.75, name: "ask-rule" });
    tb(s, a, { x: 0.5, y: y + 0.14, w: 5.6, h: 0.45, fontSize: 16, color: BODY });
    tb(s, "→", { x: 6.25, y: y + 0.1, w: 0.5, h: 0.45, fontSize: 18, color: C.text2 });
    tb(s, b, { x: 6.92, y: y + 0.14, w: 5.9, h: 0.45, fontSize: 16, fontFace: SEMI });
  });
  line(s, 0.5, 5.25, 12.83, 5.25, { color: C.text1, width: 1.5, name: "funds-rule" });
  mono(s, "$3,000 MODELS + GPUS · $2,500 GLASSES + CAPTURE · $2,000 RECORDING MAINTENANCE TASKS · $1,500 INFERENCE · $1,000 FORMATION", { x: 0.5, y: 5.45, w: 12.33, h: 0.3, fontSize: 10.5, color: C.text1 });
  tb(s, "monishsaravana@college.harvard.edu", { x: 0.5, y: 6.0, w: 6, h: 0.4, fontSize: 16, fontFace: SEMI });
  footer(s, 14, "Budget as submitted in the application");
  s.addNotes("The point isn't the budget split. It's what becomes true by April that isn't true today. The pilot metric: time until a new tech works alone, agreed with the customer before we start. The mistake number: the errors it does catch all need task state (steps done out of order), so better tracking and locked procedures should mean more catches.");
}

// ================================================================== APPENDIX
pres.addSection({ title: "Appendix" });
const appx = (eb, title) => {
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Appendix" });
  s.addText(eb, { placeholder: "eyebrow" });
  s.addText(title, { placeholder: "title" });
  return s;
};

// ---------- 5 · Architecture (native diagram, from brand/deck) ----------
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Appendix" });
  s.addText("APPENDIX · A1", { placeholder: "eyebrow" });
  s.addText("The frontier model is one swappable part. The tracking engine around it is ours", { placeholder: "title" });
  const OPEN = "D6DBD8";
  const legend = [["ours", "Ours: code and trained weights"], ["open", "Open model, frozen, runs on the device"], ["rented", "Rented API behind a typed interface"]];
  let lx = 0.5;
  legend.forEach(([k, label]) => {
    const sw = { x: lx, y: 2.03, w: 0.3, h: 0.17, rectRadius: 0.03, objectName: `legend-${k}` };
    if (k === "ours") s.addShape(pres.ShapeType.roundRect, { ...sw, fill: { color: C.background1 }, line: { color: C.text1, width: 1.25 } });
    if (k === "open") s.addShape(pres.ShapeType.roundRect, { ...sw, fill: { color: OPEN }, line: { type: "none" } });
    if (k === "rented") s.addShape(pres.ShapeType.roundRect, { ...sw, fill: { type: "none" }, line: { color: C.text1, width: 1.25, dashType: "dash" } });
    s.addText(label, { x: lx + 0.4, y: 1.98, w: 3.4, h: 0.27, fontSize: 11, color: C.text1, margin: 0, valign: "middle", isTextBox: true, objectName: `legend-${k}-label` });
    lx += 0.4 + { ours: 2.35, open: 2.75, rented: 2.6 }[k] + 0.3;
  });
  function box(name, kind, x, y, w, h, title, plain, specs = [], opts = {}) {
    const base = { x, y, w, h, rectRadius: 0.05, objectName: `box-${name}` };
    let shape;
    if (kind === "ours") shape = { fill: { color: C.background1 }, line: { color: C.text1, width: opts.hero ? 2.5 : 1.25 } };
    if (kind === "open") shape = { fill: { color: OPEN }, line: { type: "none" } };
    if (kind === "rented") shape = { fill: { type: "none" }, line: { color: C.text1, width: 1.4, dashType: "dash" } };
    if (kind === "out") shape = { fill: { color: C.accent1 }, line: { type: "none" } };
    const r = [
      { text: title, options: { fontFace: SEMI, fontSize: 13, color: C.text1, breakLine: true } },
      { text: plain, options: { fontSize: 10.5, color: kind === "out" ? C.text1 : BODY, breakLine: specs.length > 0, paraSpaceAfter: opts.compact ? 0 : 3 } },
    ];
    specs.forEach((t, i) => r.push({ text: t, options: { fontFace: MONO, fontSize: 8.5, color: kind === "out" ? C.text1 : C.text2, breakLine: i < specs.length - 1 } }));
    s.addText(r, { shape: pres.ShapeType.roundRect, ...base, ...shape, valign: "top", margin: opts.compact ? [4, 9, 2, 9] : [7, 9, 6, 9], isTextBox: false });
    const tag = { ours: "OURS", open: "OPEN MODEL", rented: "RENTED · SWAPPABLE", out: "" }[kind];
    if (tag) s.addText(tag, { x: x + w - 1.6, y: y + 0.06, w: 1.52, h: 0.16, fontFace: MONO, fontSize: 7.5, charSpacing: 1, color: kind === "ours" ? C.text1 : C.text2, align: "right", margin: 0, valign: "top", isTextBox: true, objectName: `box-${name}-tag` });
  }
  const label = (t, x, y, w = 2.2, align = "left", name = "arrow-label") =>
    s.addText(t, { x, y, w, h: 0.2, fontFace: MONO, fontSize: 8.5, color: C.text1, margin: 0, valign: "middle", align, isTextBox: true, objectName: name });
  const arrow = (pts, name, dash) => poly(s, pts, { color: C.text1, width: 1.25, arrow: true, dash, name });
  const bandLabel = (t, x, y) => s.addText(t, { x, y, w: 9, h: 0.2, fontFace: MONO, fontSize: 8.5, charSpacing: 1, color: C.text2, margin: 0, valign: "middle", isTextBox: true, objectName: "band-label" });
  bandLabel("OFFLINE, ONCE PER PROCEDURE", 0.5, 2.5);
  box("compiler", "ours", 4.05, 2.4, 4.9, 0.8, "Procedure compiler", "Turns a manual into a task graph the engine can track", ["steps · checks · common mistakes · typical durations"]);
  s.addText([
    { text: "8 procedures compiled", options: { breakLine: true } },
    { text: "96 steps · 207 checks", options: { breakLine: true } },
    { text: "267 known mistakes", options: { breakLine: true } },
    { text: "$4.16 total, one-time" },
  ], { x: 9.15, y: 2.4, w: 3.0, h: 0.8, fontFace: MONO, fontSize: 9, color: C.text2, margin: 0, valign: "middle", isTextBox: true, objectName: "compiler-stats" });
  s.addShape(pres.ShapeType.roundRect, { x: 0.35, y: 3.32, w: 12.63, h: 1.92, rectRadius: 0.08, fill: { color: C.background1, transparency: 45 }, line: { type: "none" }, objectName: "band-fast" });
  bandLabel("FAST PATH · EVERY FRAME · ON THE DEVICE", 0.5, 3.38);
  s.addText("3.1× FASTER THAN REAL TIME", { x: 8.83, y: 3.38, w: 4.0, h: 0.2, fontFace: MONO, fontSize: 8.5, charSpacing: 1, color: C.text2, align: "right", margin: 0, valign: "middle", isTextBox: true, objectName: "band-label-speed" });
  const Y = 3.62, H = 1.5;
  box("camera", "ours", 0.5, Y, 1.45, H, "Camera", "Live video", ["first-person", "4 frames / s", "webcam or file", "glasses adapter:", "not yet tested"]);
  box("perception", "open", 2.12, Y, 1.75, H, "Perception", "What's in view", ["SigLIP2 · 20 ms/frame", "hands · 6 ms/frame", "V-JEPA 2 · 221ms @1Hz"]);
  box("event-detector", "ours", 4.04, Y, 1.8, 0.73, "Event detector", "Did a step just end?", ["F1 0.38 vs rule 0.24"], { compact: true });
  box("task-recognizer", "ours", 4.04, Y + 0.77, 1.8, 0.73, "Task recognizer", "Which job is this?", ["73% top-1, 40 s"], { compact: true });
  box("state-tracker", "ours", 6.01, Y, 2.9, H, "State tracker", "Where you are in the procedure", ["Bayesian semi-Markov model", "over the task graph"], { hero: true });
  const ps = [0.02, 0.04, 0.09, 0.7, 0.1, 0.03, 0.02];
  ps.forEach((p, i) => {
    const bh = Math.max(0.02, (p * 0.3) / 0.7), bx = 6.18 + i * 0.22;
    s.addShape(pres.ShapeType.rect, { x: bx, y: 4.9 - bh, w: 0.15, h: bh, fill: { color: i === 3 ? C.accent1 : C.accent6 }, line: { type: "none" }, objectName: `belief-bar-${i + 1}` });
    s.addText(`S${i + 1}`, { x: bx - 0.05, y: 4.93, w: 0.25, h: 0.15, fontFace: MONO, fontSize: 7, color: i === 3 ? C.text1 : C.text2, align: "center", margin: 0, valign: "middle", isTextBox: true, objectName: `belief-label-${i + 1}` });
  });
  s.addText([
    { text: "→ P(step)", options: { breakLine: true } },
    { text: "→ time on step", options: { breakLine: true } },
    { text: "→ uncertainty" },
  ], { x: 7.78, y: 4.52, w: 1.1, h: 0.56, fontFace: MONO, fontSize: 8.5, color: C.text1, margin: 0, valign: "middle", isTextBox: true, objectName: "tracker-outputs" });
  box("policy", "ours", 9.08, Y, 1.8, H, "Policy", "Should it say anything?", ["speak", "verify", "flag a mistake", "ask for a better view", "expand the detail"]);
  box("coach", "out", 11.05, Y + 0.18, 1.78, 1.14, "Coach", "Voice + HUD", ["speaks only", "when confident"]);
  const mid = Y + H / 2;
  arrow([[1.95, mid], [2.12, mid]], "arrow-camera-perception");
  arrow([[3.87, Y + 0.355], [4.04, Y + 0.355]], "arrow-perception-detector");
  arrow([[3.87, Y + 1.145], [4.04, Y + 1.145]], "arrow-perception-recognizer");
  arrow([[5.84, Y + 0.355], [6.01, Y + 0.355]], "arrow-detector-tracker");
  arrow([[5.84, Y + 1.145], [6.01, Y + 1.145]], "arrow-recognizer-tracker");
  arrow([[8.91, mid], [9.08, mid]], "arrow-tracker-policy");
  arrow([[10.88, mid], [11.05, mid]], "arrow-policy-coach");
  arrow([[7.5, 3.2], [7.5, Y]], "arrow-compiler-tracker");
  label("task graph", 7.58, 3.4, 1.2);
  arrow([[5.93, 3.2], [5.93, Y + 1.4], [5.84, Y + 1.4]], "arrow-compiler-recognizer");
  label("library", 5.15, 3.4, 0.7, "right");
  s.addShape(pres.ShapeType.roundRect, { x: 0.35, y: 5.5, w: 12.63, h: 1.3, rectRadius: 0.08, fill: { type: "none" }, line: { color: "B9C0BC", width: 1, dashType: "sysDash" }, objectName: "band-slow" });
  bandLabel("SLOW PATH · ONLY WHEN SOMETHING HAPPENS", 0.5, 5.56);
  const SY = 5.82, SH = 0.9;
  box("flywheel", "ours", 2.0, SY, 3.85, SH, "Flywheel + local student", "Every session becomes training data", ["student: 0.03 ms per check, free", "takes routine checks: 34% fewer frontier calls"]);
  box("verifier", "rented", 6.01, SY, 2.9, SH, "Verifier", "Answers one typed question", ["fast: Jev · 151 ms · 88% of calls", "hard cases: Claude Opus · 3.8 s"]);
  box("calibration", "ours", 9.08, SY, 1.8, SH, "Calibration", "Trusts each answer", ["the right amount", "error 0.22 → 0.02"]);
  arrow([[6.6, Y + H], [6.6, SY]], "arrow-tracker-verifier");
  label("step ends · unsure · stuck", 6.68, 5.26, 1.88);
  label("14% of frames", 6.68, 5.56, 1.4);
  arrow([[8.91, SY + 0.45], [9.08, SY + 0.45]], "arrow-verifier-calibration");
  arrow([[9.98, SY], [9.98, 5.42], [8.6, 5.42], [8.6, Y + H]], "arrow-calibration-tracker");
  label("evidence", 9.08, 5.56, 0.85);
  arrow([[5.85, SY + 0.45], [6.01, SY + 0.45]], "arrow-student-verifier");
  arrow([[6.3, Y + H], [6.3, 5.38], [5.55, 5.38], [5.55, SY]], "arrow-tracker-flywheel", "dash");
  label("session records", 3.9, 5.58, 1.55, "right");
  footer(s, TOTAL, "Measured on 48 held-out first-person clips from a public dataset (CaptainCook4D)");
  s.addNotes("Walk it left to right. Open models on the device turn every frame into features. Our state tracker keeps a running belief about which step you're on, using a task graph we compiled from the manual. Only when something happens (a step ends, it's unsure, or you're stuck) does it ask a rented model one typed question: that's 14% of frames. We calibrate the answer and feed it back, and the policy decides whether to say anything. Every session becomes training data, and our local student already handles routine checks. If asked 'isn't this a wrapper?': with the same frontier model, our layers make it about 13% more accurate at a fifth of the cost, and swapping the rented model is a one-line config change.");
}


// ---------- 3 · Status quo ----------
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Appendix" });
  s.addText("APPENDIX · A2", { placeholder: "eyebrow" });
  s.addText("The status quo: what each tool does today, and what it misses", { placeholder: "title" });
  const cols = [
    ["SHADOWING", "A senior tech, side by side", "The real teacher today", "About $44 an hour of senior time, one trainee at a time"],
    ["MANUALS + VIDEOS", "PDFs, binders, YouTube", "Explain what should happen", "Can't see what you're actually doing"],
    ["PROCEDURE APPS", "MaintainX, Tulip, Augmentir", "Put the steps on a phone; collect sign-offs and photos", "A checkbox isn't proof the step was done right"],
    ["FIXED CAMERAS", "Retrocausal, Invisible AI", "Watch one workstation on a line", "Maintenance moves around the machine"],
  ];
  const cw = 12.33 / 4, gap = 0.15;
  cols.forEach(([k, who, does, miss], i) => {
    const x = 0.5 + i * cw, w = cw - gap;
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

// A2 · market math
{
  const s = appx("APPENDIX · A3", "Market math, and the assumptions behind it");
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

// A3 · unit economics
{
  const s = appx("APPENDIX · A4", "Unit economics, and the pricing risk");
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

// ---------- 12 · Moat: learning curves ----------
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Appendix" });
  s.addText("APPENDIX · A5", { placeholder: "eyebrow" });
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
    valAxisMinVal: ymin, valAxisMaxVal: ymax, valAxisMajorUnit: 10, valAxisLabelFormatCode: '0"%"',
    valAxisLabelColor: "5E676C", catAxisLabelColor: "5E676C", valAxisLabelFontSize: 10, catAxisLabelFontSize: 10,
    valAxisLabelFontFace: "+mn-lt", catAxisLabelFontFace: "+mn-lt", catAxisLineShow: false, valAxisLineShow: false,
    valGridLine: { color: "D0D5D2", size: 0.75 }, catGridLine: { style: "none" },
    showCatAxisTitle: true, catAxisTitle: title, catAxisTitleFontSize: 10, catAxisTitleColor: "5E676C", catAxisTitleFontFace: "+mn-lt",
  });
  statCol(s, 0.5, 2.15, 5.91, `${pacc[0]}% → ${pacc[pacc.length - 1]}%`, "recognizing the current step, on videos it never trained on", { color: C.accent2, size: 34, capH: 0.4 });
  s.addChart(pres.ChartType.line, [{ name: "Step model", labels: ks.map(String), values: pacc }],
    { ...chart(0.5, "Training recordings per procedure", 20, 60), chartColors: ["FF5B14"], objectName: "chart-step-model" });
  statCol(s, 6.92, 2.15, 5.91, `${sacc[0]}% → ${sacc[sacc.length - 1]}%`, `checking a step is done · grey: the frontier model, ${teacher}%`, { color: C.accent2, size: 34, capH: 0.4 });
  s.addChart(pres.ChartType.line, [
    { name: "Our local model", labels: ns.map(String), values: sacc },
    { name: "Frontier model it learns from", labels: ns.map(String), values: ns.map(() => teacher) },
  ], { ...chart(6.92, "Training recordings", 50, 90), chartColors: ["FF5B14", "9AA3A7"], objectName: "chart-student" });
  mono(s, "TESTED ONLY ON RECORDINGS IT NEVER SAW · BOTH STILL RISING AT THE LARGEST SIZE WE HAVE", { x: 0.5, y: 6.42, w: 12.33, h: 0.3, color: C.text1 });
  footer(s, TOTAL, "Random subsets of public train-split recordings, 5 seeds per point");
  s.addNotes("We retrained our learned layers on growing slices of the training data and scored them only on recordings they never saw, so this isn't memorization. Left: the 3 procedures with 9 training recordings, held-out step accuracy. Right: the local student model on the same 469 held-out checks as the headline result. Steady gains per doubling of data, not 'exponential'. If asked for counts: up to 9 recordings per procedure, 30 recordings for the student. Every customer session is new training data. The engine we evaluated used only 3 recordings per procedure, so there's headroom we haven't used yet (not re-measured end to end).");
}



// A1 · training data
{
  const s = appx("APPENDIX · A6", "Training data, stated plainly");
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

// A6 · competitors
{
  const s = appx("APPENDIX · A7", "Who else is here, and how we differ");
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

// A4 · risks
{
  const s = appx("APPENDIX · A8", "The risks we see, and what we do about each");
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
// A5 · glasses + voice
{
  const s = appx("APPENDIX · A9", "Glasses and voice: what's built, and what's designed");
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

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
