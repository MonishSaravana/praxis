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
const ARGS = process.argv.slice(2);
const SHARE = ARGS.includes("--share"); // no appendix, notes keep only the sources
const OUT = ARGS.find((a) => !a.startsWith("--")) || path.join(__dirname, SHARE ? "Praxis_SAH_Oct2026_no_appendix.pptx" : "Praxis_SAH_Oct2026.pptx");
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
  headFontFace: "Archivo SemiBold",
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
const eb = (t) => (APX ? `Appendix ${APX}` : t);

// ---------- layouts (as in brand/deck) ----------
const eyebrow = (color, y = 0.5) => ({
  placeholder: { options: { name: "eyebrow", type: "body", x: 0.5, y, w: 9, h: 0.3, fontFace: MONO, fontSize: 12, charSpacing: 0, color, margin: 0, valign: "top" }, text: "Eyebrow" },
});
pres.defineSlideMaster({
  title: "Praxis Light",
  background: { color: C.background2 },
  objects: [
    eyebrow(C.text2),
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.85, w: 12.33, h: 1.05, fontFace: HEAD, fontSize: 30, color: C.text1, align: "left", valign: "top", margin: 0, lineSpacingMultiple: 1.0 }, text: "Slide title" } },
  ],
  slideNumber: { x: 0.82, y: 6.93, w: 0.6, h: 0.3, fontFace: MONO, fontSize: 10, color: C.text2, margin: 0, valign: "middle" },
});
pres.defineSlideMaster({
  title: "Praxis Split",
  background: { color: C.background2 },
  objects: [
    { placeholder: { options: { name: "eyebrow", type: "body", x: 7.85, y: 0.6, w: 4.98, h: 0.3, fontFace: MONO, fontSize: 12, charSpacing: 0, color: C.text2, margin: 0, valign: "top" }, text: "Eyebrow" } },
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
const mono = (slide, t, o) => tb(slide, t, { fontFace: MONO, fontSize: 10.5, charSpacing: 0.3, color: C.text2, ...o });
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
  s.addText("Instructions that can finally see how you're doing", { x: 0.5, y: 2.05, w: 5.6, h: 2.4, fontFace: HEAD, fontSize: 46, color: C.background2, valign: "middle", margin: 0, lineSpacingMultiple: 0.95, isTextBox: true, objectName: "cover-headline" });
  tb(s, "Software for smart glasses that coaches new maintenance technicians from a company's existing manuals.", { x: 0.5, y: 4.6, w: 5.2, h: 1.1, fontSize: 17, color: C.background2, objectName: "cover-oneliner" });
  s.addText("Startups @ Harvard  ·  October 20, 2026  ·  Monish Saravana", { x: 0.5, y: 6.93, w: 6.5, h: 0.3, fontFace: MONO, fontSize: 12, charSpacing: 0, color: C.accent6, margin: 0, valign: "middle", isTextBox: true, objectName: "cover-meta" });
  const reg = [860, 640, 1180, 900];
  hudRegion(s, reg, HUD_WHITE);
  hudPulse(s, 1010, 790, HUD_WHITE);
  hudProgress(s, 4, 9, 1848 - 247);
  const chip = hudChip(s, "Seat the clamp past the hose bead", 624, { right: true });
  hudLeader(s, chip, reg, HUD.orange);
  s.addNotes("SAY (20 s): Hi, I'm Monish. Praxis is the software layer for smart glasses that trains new maintenance technicians. A company uploads the manuals it already has. Praxis turns each procedure into a task model, watches the work through the glasses' camera, knows which step the tech is on, says the next one, checks the important ones, and asks for a better view instead of guessing. We don't build glasses. The photo is a stock photo with a mocked-up HUD; from slide 4 on, everything is real output.");
}

const VID = (f) => path.join(__dirname, "assets", "video", f);
const poster = (f) => "data:image/png;base64," + fs.readFileSync(VID(f)).toString("base64");
function video(s, name, x, y, w) {
  const h = w * 9 / 16;
  s.addMedia({ type: "video", path: VID(`${name}.mp4`), cover: poster(`${name}_poster.png`), x, y, w, h, objectName: "demo-video" });
  return y + h;
}

// ---------- small drawing helpers for the redesigned core ----------
const rect = (s, x, y, w, h, color, name) => s.addShape(pres.ShapeType.rect, { x, y, w, h, fill: { color }, line: { type: "none" }, objectName: name });
const dot = (s, x, y, d, color, name) => s.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color }, line: { type: "none" }, objectName: name });
const ring = (s, cx, cy, r, color, width, transparency) => s.addShape(pres.ShapeType.ellipse, { x: cx - r, y: cy - r, w: 2 * r, h: 2 * r, fill: { type: "none" }, line: { color, width, transparency }, objectName: "hud-verify-pulse" });
const label = (s, t, o) => tb(s, t, { fontFace: SEMI, fontSize: 12, color: C.text2, ...o });
const SHOT = (f) => path.join(__dirname, "assets", "screens", f);
function shot(s, file, x, y, w, ratio, name = "screenshot") {
  const h = w / ratio;
  s.addShape(pres.ShapeType.rect, { x: x + 0.06, y: y + 0.08, w, h, fill: { color: "16191B", transparency: 85 }, line: { type: "none" }, objectName: "shot-shadow" });
  s.addShape(pres.ShapeType.rect, { x: x - 0.01, y: y - 0.01, w: w + 0.02, h: h + 0.02, fill: { color: "FFFFFF" }, line: { color: "B9C0BC", width: 0.75 }, objectName: "shot-frame" });
  s.addImage({ path: SHOT(file), x, y, w, h, objectName: name });
  return y + h;
}

// ---------- HUD on a cropped photo tile (product slide); tiles + regions from deck-hv/make_tiles.py ----------
const TJ = JSON.parse(fs.readFileSync(path.join(__dirname, "assets", "tiles", "tiles.json"), "utf8"));
const TILE = { w: 3.94, h: 3.2 };
function hudTile(s, name, x, y, hud) {
  const t = TJ[name], k = TILE.w / t.crop_w;
  const X = (px) => x + (px - t.x0) * k, Y = (py) => y + (py - t.y0) * k;
  s.addImage({ path: path.join(__dirname, "assets", "tiles", `${name}.jpg`), x, y, w: TILE.w, h: TILE.h, objectName: name });
  const [a, b, c, d] = t.region, reg = [X(a), Y(b), X(c), Y(d)];
  s.addShape(pres.ShapeType.roundRect, { x: reg[0], y: reg[1], w: reg[2] - reg[0], h: reg[3] - reg[1], rectRadius: 22 * k, fill: { type: "none" }, line: { color: hud.color, width: 2 }, objectName: "hud-target" });
  if (hud.pulse) {
    ring(s, X(hud.pulse[0]), Y(hud.pulse[1]), 44 * k, hud.color, 2.25);
    ring(s, X(hud.pulse[0]), Y(hud.pulse[1]), 72 * k, hud.color, 1.25, 55);
  }
  const bx = x + 0.14, bw = TILE.w - 0.28;
  let box;
  if (hud.card) {
    const h = 0.95, by = y + TILE.h - 0.14 - h;
    s.addShape(pres.ShapeType.roundRect, { x: bx, y: by, w: bw, h, rectRadius: 0.05, fill: { color: HUD.plate }, line: { type: "none" }, objectName: "hud-card" });
    rect(s, bx, by, bw, 0.05, hud.color, "hud-card-state");
    tb(s, [
      { text: hud.card[0], options: { fontFace: SEMI, fontSize: 9.5, color: C.accent5, breakLine: true, paraSpaceAfter: 3 } },
      { text: hud.card[1], options: { fontFace: SEMI, fontSize: 13, color: HUD.ink, breakLine: true, paraSpaceAfter: 2 } },
      { text: hud.card[2], options: { fontSize: 11, color: BODY } },
    ], { x: bx + 0.17, y: by + 0.13, w: bw - 0.3, h: h - 0.2, objectName: "hud-card-text" });
    box = [bx, by, bx + bw, by + h];
  } else {
    const h = hud.chipLabel ? 0.62 : 0.44, by = hud.top ? y + 0.14 : y + TILE.h - 0.14 - h;
    s.addShape(pres.ShapeType.roundRect, { x: bx, y: by, w: bw, h, rectRadius: 0.05, fill: { color: HUD.ink, transparency: 14 }, line: { type: "none" }, objectName: "hud-chip" });
    rect(s, bx, by, 0.05, h, hud.color, "hud-chip-edge");
    const t2 = [];
    if (hud.chipLabel) t2.push({ text: hud.chipLabel, options: { fontFace: SEMI, fontSize: 9.5, color: HUD.green, breakLine: true, paraSpaceAfter: 3 } });
    t2.push({ text: hud.chip, options: { fontFace: SEMI, fontSize: 12.5, color: HUD.text } });
    tb(s, t2, { x: bx + 0.2, y: by, w: bw - 0.3, h, valign: "middle", objectName: "hud-chip-text" });
    box = [bx, by, bx + bw, by + h];
  }
  const lx = Math.max(box[0] + 0.15, Math.min(box[2] - 0.15, (reg[0] + reg[2]) / 2));
  const [ay, by2] = box[1] > reg[3] ? [box[1], reg[3]] : [box[3], reg[1]];
  line(s, lx, ay, lx, by2, { color: hud.color, width: 1.5, name: "hud-leader" });
  dot(s, lx - 0.035, ay - 0.035, 0.07, hud.color, "hud-leader-start");
  s.addShape(pres.ShapeType.ellipse, { x: lx - 0.06, y: by2 - 0.06, w: 0.12, h: 0.12, fill: { color: hud.color }, line: { color: HUD.ink, width: 1 }, objectName: "hud-leader-dot" });
}

// ---------- 2 · Problem: one hero number, the scale, one real quote; a photo on the right ----------
function sProblem() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  const pw = 7.5 * 745 / 1080;
  s.addImage({ path: path.join(__dirname, "assets", "photos", "problem-panel.jpg"), x: 13.333 - pw, y: 0, w: pw, h: 7.5, objectName: "photo" });
  s.addText("Problem", { placeholder: "eyebrow" });
  s.addText("Training new technicians is expensive", { placeholder: "title" });
  tb(s, "Each new hire learns by shadowing an experienced technician, and that time comes off the job.", { x: 0.5, y: 1.42, w: 7.3, h: 0.6, fontSize: 16, color: BODY });
  label(s, "Total cost to hire and ramp up one maintenance technician", { x: 0.5, y: 2.45, w: 7.2, h: 0.3, fontSize: 13 });
  tb(s, "$10–15k", { x: 0.5, y: 2.68, w: 7.3, h: 1.4, fontFace: HEAD, fontSize: 96, color: C.text1, objectName: "hero" });
  tb(s, "including recruiting fees, onboarding time and lost productivity", { x: 0.5, y: 4.28, w: 7.2, h: 0.35, fontSize: 16, color: BODY });
  line(s, 0.5, 4.8, 7.75, 4.8, { color: C.text1, width: 1.25, name: "scale-rule" });
  tb(s, "~255,000", { x: 0.5, y: 4.95, w: 3.1, h: 0.65, fontFace: HEAD, fontSize: 40, objectName: "scale" });
  tb(s, "US maintenance and repair openings a year, each one needing someone to train them", { x: 3.65, y: 4.97, w: 4.1, h: 0.65, fontSize: 14, color: BODY, valign: "middle" });
  tb(s, "In a 2017 survey of 35 aviation repair stations, new hires took 9–14 months to become profitable.", { x: 0.5, y: 5.75, w: 7.3, h: 0.32, fontSize: 14, color: BODY });
  rect(s, 0.5, 6.25, 0.06, 0.5, C.accent1, "quote-edge");
  tb(s, [
    { text: "“The hardest AND most expensive part is training new techs …”", options: { fontFace: SEMI, fontSize: 15, color: C.text1, breakLine: true } },
    { text: "Casey Czarnowski, Healthcare Sterile Processing Association (HSPA), discussed this week", options: { fontSize: 11.5, color: C.text2 } },
  ], { x: 0.72, y: 6.22, w: 7.1, h: 0.58, objectName: "quote" });
  footer(s, 0, "Reliability magazine (A. Gager), hiring + ramp-up estimate · BLS Occupational Outlook Handbook, openings · ARSA member survey of 35 repair stations, 2017 · HSPA email reply, Oct 19 2026 (docs/OUTREACH.md) · photo: Unsplash");
  s.addNotes(`SAY (40 s): Maintenance teams can't hire experienced technicians fast enough, so they hire new ones and train them on the job. The real teacher is a senior tech standing next to them, because a manual or a video can't see what the new person is doing. Hiring and ramping up one maintenance tech costs about 10 to 15 thousand dollars, counting onboarding and lost productivity, and there are about 255,000 of these openings a year in the US. When I asked a hospital sterile processing association about this, they said training new techs is the hardest and most expensive part of the job.

IF ASKED: The $10-15k is a Reliability magazine trade estimate, not a study. ARSA surveyed 35 aviation repair stations: new hires took 9 to 14 months on average to become profitable, some up to 24. BLS says on-the-job training typically lasts more than a year. Openings include people changing jobs, so 255k is an upper bound on brand-new techs. The quote is from Casey Czarnowski at HSPA, the professional association for hospital sterile processing techs, in an email reply on Oct 19. The full line: training new techs on cleaning complex surgical instruments in the decontamination area takes significant one-to-one time, and improper technique can damage expensive instruments. It's the profession's view, not a customer's, and HSPA said it can't refer us to individual members. Our estimate of the senior-tech time alone is $11-23k per hire (appendix ${ref(aUnitEcon)}).`);
}

// ---------- 3 · Product: the flow in one line, then the three things it does ----------
function sProduct() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("Product", { placeholder: "eyebrow" });
  s.addText("Praxis coaches the job through smart glasses", { placeholder: "title" });
  // the flow: five short steps on one baseline, each box sized to its text, arrows sharing the space left over
  const flow = ["Upload the manual", "Praxis compiles it", "Tech wears glasses", "Praxis tracks the job", "Verifies key steps"];
  const fy = 1.55, fh = 0.42, perChar = 0.094, ws = flow.map((t) => (t.length + 3) * perChar + 0.05);
  const aw = (12.33 - ws.reduce((x, y) => x + y, 0)) / 4;
  let fx = 0.5;
  flow.forEach((t, i) => {
    const last = i === 4;
    tb(s, [{ text: `${i + 1}  `, options: { color: last ? C.accent2 : C.text2 } }, { text: t, options: { color: last ? C.accent2 : C.text1 } }], { x: fx, y: fy, w: ws[i] + 0.1, h: fh, fontFace: SEMI, fontSize: 14.5, valign: "middle", objectName: "flow-step" });
    fx += ws[i];
    if (i < 4) line(s, fx + 0.1, fy + fh / 2, fx + aw - 0.12, fy + fh / 2, { color: C.text2, width: 1.25, arrow: true, name: "flow-arrow" });
    fx += aw;
  });
  line(s, 0.5, 2.2, 12.83, 2.2, { color: "C2C8C5", width: 0.75, name: "flow-rule" });
  const gap = (12.33 - 3 * TILE.w) / 2, ty = 2.95;
  [
    ["Says the next step", C.accent1, "tile-step", { color: HUD.orange, chip: "Loosen the four float-bowl screws" }],
    ["Checks the work", C.accent3, "tile-verified", { color: HUD.green, chipLabel: "Step 5 verified · valve lash set", chip: "Next: rotate the crank to TDC", top: true, pulse: [660, 740] }],
    ["Catches a mistake", C.accent5, "tile-mistake", { color: HUD.red, card: ["Mistake caught", "Lockout was skipped.", "Lock and tag the feeder breaker first."] }],
  ].forEach(([head, col, name, hud], i) => {
    const x = 0.5 + i * (TILE.w + gap);
    dot(s, x, 2.52, 0.28, col, "tile-badge");
    tb(s, String(i + 1), { x, y: 2.52, w: 0.28, h: 0.28, fontFace: SEMI, fontSize: 11, color: "FFFFFF", align: "center", valign: "middle" });
    tb(s, head, { x: x + 0.4, y: 2.49, w: TILE.w - 0.4, h: 0.34, fontFace: SEMI, fontSize: 16, valign: "middle" });
    hudTile(s, name, x, ty, hud);
  });
  tb(s, "Built for new technicians in plant maintenance, facilities, HVAC service and equipment repair.", { x: 0.5, y: 6.35, w: 8.6, h: 0.32, fontSize: 13, color: BODY });
  footer(s, 0, "Concept mocks on Unsplash stock photos (brand/mocks/CREDITS.md)");
  s.addNotes(`SAY (40 s): Here's the product. A company uploads the manual it already has. Praxis turns each procedure into something it can follow: the steps, their order, how long they take and what needs checking. The new technician puts on smart glasses, and Praxis watches through the camera. It knows which step they're on and says the next one. It checks the steps that matter. And when something goes wrong, like a skipped lockout, it catches it and says how to fix it.

IF ASKED: These three pictures are mockups on stock photos (labeled). The real system on real footage is two slides ahead. The tech mostly hears short spoken instructions; cards only appear for mistakes and when it needs a better view. Mistake detection is our weakest measured number today (appendix ${ref(aBenchmark)}). Buyer: the maintenance manager. User: the new tech.`);
}

// ---------- 4 · What exists: real screenshots of the backend and the live app ----------
function sExists() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("Built so far", { placeholder: "eyebrow" });
  s.addText("This is already a working software system", { placeholder: "title" });
  // left: the company backend, upload → compile → approve
  label(s, "1  A manager uploads the manuals they already have", { x: 0.5, y: 1.5, w: 6.5, h: 0.3, fontSize: 13, color: C.text1 });
  shot(s, "backend-documents.png", 0.5, 1.88, 5.5, 1660 / 430);
  label(s, "2  Praxis compiles a procedure; the manager reviews and approves it", { x: 0.5, y: 3.5, w: 6.6, h: 0.3, fontSize: 13, color: C.text1 });
  shot(s, "backend-procedure-top.png", 0.5, 3.88, 6.45, 2320 / 1000);
  // right: the live app, engineer view of the real session
  const rx = 7.35, rw = 5.48;
  label(s, "3  The live app tracks the job (engineer view)", { x: rx, y: 1.5, w: rw, h: 0.3, fontSize: 13, color: C.text1 });
  shot(s, "../video/repair_demo_engineer_poster.png", rx, 1.88, rw, 16 / 9, "engineer-view");
  // status of every part, stated exactly
  const st = [
    ["Company backend: upload, index, compile, approve", "built", C.accent3],
    ["Tracking engine and evaluation harness", "built", C.accent3],
    ["Live app with spoken coaching", "built, real time on video", C.accent3],
    ["Meta glasses adapter", "coded, not device-tested", "C99A2E"],
    ["Viture/NVIDIA glasses adapter", "coded, not device-tested", "C99A2E"],
    ["Android XR glasses", "planned", "B9C0BC"],
  ];
  const sy = 5.02;
  st.forEach(([k, v, col], i) => {
    const y = sy + i * 0.3;
    dot(s, rx, y + 0.09, 0.13, col, "status-dot");
    tb(s, [{ text: k, options: { fontFace: SEMI, color: C.text1 } }, { text: `   ${v}`, options: { color: C.text2 } }], { x: rx + 0.25, y, w: rw - 0.25, h: 0.3, fontSize: 12, valign: "middle" });
  });
  footer(s, 0, "Screenshots of the Praxis company backend (Reclamation FIST manuals; ENIGMA-51 procedure) and the live app's engineer view of session 20261018_152645");
  s.addNotes(`SAY (40 s): This isn't a mockup. On the left is the company backend running today: a manager uploads the manuals they already have, here three public maintenance manuals; Praxis indexes them in seconds and finds the procedures. It compiles one into coached steps, with each instruction quoted from the manual, for about 20 cents, and a manager approves it before any technician sees it. On the right is the live app tracking a real repair job: its belief about which step the tech is on, every model call, and the timeline. The backend, the compiler, the tracking engine and the live app with spoken coaching are all built. The Meta and Viture glasses adapters are coded but not yet tested on a device; that's part of what the grant pays for.

IF ASKED: a 97-page safety manual is indexed in 0.34 s on a laptop, for $0; each procedure compiles for about $0.16-0.26. The live app runs on a video stream in real time (local layers about 50 ms a frame). Detail: appendix ${ref(sBuilt)} (backend) and ${ref(aHardwareQA)} (adapters).`);
}

// ---------- 5 · Live proof ----------
function sLive() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("Live test", { placeholder: "eyebrow" });
  s.addText("We already run a real repair procedure live", { placeholder: "title" });
  video(s, "repair_short_engineer", 0.5, 1.75, 8.1);
  const x = 9.0, w = 3.83;
  [
    ["Real repair, start to finish", "16:40", "a high-voltage board repair, filmed first-person in an industrial lab"],
    ["Training on this exact job", "None", "Praxis started from the lab's written procedure"],
    ["Model cost", "≈$1", "of model calls per coached hour, measured across our evaluation"],
  ].forEach(([k, big, cap], i) => {
    const y = 1.75 + i * 1.5;
    line(s, x, y, x + w, y, { color: C.text1, width: i ? 0.75 : 1.5, name: "spec-rule" });
    label(s, k, { x, y: y + 0.12, w, h: 0.28, fontSize: 12.5 });
    tb(s, big, { x, y: y + 0.42, w, h: 0.6, fontFace: HEAD, fontSize: 34, color: i === 2 ? C.accent2 : C.text1, objectName: "spec-value" });
    tb(s, cap, { x, y: y + 1.02, w, h: 0.45, fontSize: 12.5, color: BODY, objectName: "spec-caption" });
  });
  footer(s, 0, "Praxis live session on ENIGMA-51 video 141 · renders/demo/README.md · results/backend/enigma_live_141.json");
  s.addNotes(`SAY (45 s, while it plays; click to play, 15 s): This is real first-person footage from an industrial repair lab, run through the live system in real time. Praxis was never trained on this job; it started from the lab's written procedure. On the left is what the technician sees; on the right is the engine: its belief about which step they're on, and every model call. Three moments. First, the tech moves on and Praxis gives the next step: turn on the soldering iron and set it to 200. Second, they overshoot to 215, and Praxis says "You've gone past 200, press DOWN." Third, the camera swings away and the display is half out of frame: the fast model says it can't see clearly and asks to see the soldering station display, and the frontier model asks for a closer look. Across our evaluation, model cost is about a dollar per coached hour; this 16:40 run itself cost 17 cents.

IF ASKED (be straight): the cut picks three stretches of session time (2:48-2:52, 2:56-3:00, 4:26-4:33), each with its time code on screen; nothing is re-timed and every card and model call comes from the session log. In the third moment the request shows in the model-call panel; the policy didn't put a card on the glasses for it. Across the whole session it confirmed 1 of 19 steps and agreed with proxy step labels 29% of the time; the 215 °C alert came about 6 seconds after the frame it checked. It's a recorded public video replayed in real time, not a camera on a tech yet. Exact cost: $0.165. The full 49-second engineer cut is appendix ${ref(aUnderHood)}.`);
}

// ---------- 6 · Architecture: engineered, every part tagged ----------
function sEngine() {
  const s = pres.addSlide({ masterName: "Praxis Dark Grid" });
  tb(s, "How it works", { x: 0.5, y: 0.4, w: 6, h: 0.28, fontFace: SEMI, fontSize: 12, color: C.accent6, objectName: "eyebrow" });
  tb(s, "The system tracks the job instead of querying a model constantly", { x: 0.5, y: 0.72, w: 12.33, h: 0.55, fontFace: HEAD, fontSize: 26, color: C.background2, objectName: "headline" });
  const ST = {
    ours: { fill: "1F2326", line: { color: "C9CFCC", width: 1 }, tc: "F6F7F6", sc: "9AA3A7", tag: "OURS", tagc: "C9CFCC" },
    trained: { fill: "23282B", line: { color: "FF5B14", width: 1.75 }, tc: "FFFFFF", sc: "AEB6B2", tag: "OURS · TRAINED", tagc: "FF5B14" },
    open: { fill: "343A3D", line: { type: "none" }, tc: "E8EBE9", sc: "AEB6B2", tag: "OPEN MODEL", tagc: "AEB6B2" },
    rented: { fill: null, line: { color: "9AA3A7", width: 1.25, dashType: "dash" }, tc: "D5DAD7", sc: "9AA3A7", tag: "RENTED · SWAPPABLE", tagc: "9AA3A7" },
    coach: { fill: "FF5B14", line: { type: "none" }, tc: "16191B", sc: "16191B", tag: "OURS", tagc: "16191B" },
    input: { fill: null, line: { color: "5E676C", width: 1 }, tc: "C9CFCC", sc: "8A9397", tag: "", tagc: "" },
  };
  const box = (name, kind, x, y, w, h, title, sub, tsize = 13.5) => {
    const st = ST[kind];
    const runs = [{ text: title, options: { fontFace: SEMI, fontSize: tsize, color: st.tc, breakLine: !!sub, paraSpaceAfter: 2 } }];
    if (sub) runs.push({ text: sub, options: { fontFace: THEME.bodyFontFace, fontSize: 10.5, color: st.sc } });
    s.addText(runs, { shape: pres.ShapeType.roundRect, x, y, w, h, rectRadius: 0.05, fill: st.fill ? { color: st.fill } : { type: "none" }, line: st.line, valign: st.tag ? "top" : "middle", margin: [9, 8, 4, st.tag ? 17 : 4], objectName: `box-${name}` });
    if (st.tag) s.addText(st.tag, { x: x + w - 2.0, y: y + 0.07, w: 1.92, h: 0.16, fontFace: LABEL, fontSize: 7, charSpacing: 1, color: st.tagc, align: "right", valign: "middle", margin: 0, isTextBox: true, objectName: `box-${name}-tag` });
  };
  const ln = (pts, lit, name, dash) => poly(s, pts, { color: lit ? "FF5B14" : "8A9397", width: lit ? 1.75 : 1.1, arrow: true, dash, name });
  const lab = (t, x, y, w = 1.3, align = "left", color = "9AA3A7") => tb(s, t, { x, y, w, h: 0.2, fontSize: 9.5, color, align, objectName: "arrow-label" });

  // top: the manual becomes the task graph the tracker follows
  box("manual", "input", 0.5, 1.6, 1.85, 0.6, "Company manual", "", 12);
  ln([[2.35, 1.9], [2.68, 1.9]], false, "a-manual");
  box("compiler", "ours", 2.7, 1.45, 3.55, 0.9, "Procedure compiler", "manual → task graph: steps, order, timing, checks");
  ln([[6.25, 1.9], [8.9, 1.9], [8.9, 2.58]], false, "a-graph"); lab("task graph", 6.45, 1.68);
  // main flow: every frame
  lab("Every frame, on the device", 0.5, 2.62, 3.0, "left", "FF5B14");
  box("video", "input", 0.5, 3.3, 1.85, 0.62, "First-person video", "", 12);
  ln([[2.35, 3.61], [2.68, 3.61]], true, "a-video");
  box("perception", "open", 2.7, 2.95, 2.15, 1.35, "Perception", "SigLIP 2 · V-JEPA 2 · hand features");
  ln([[4.85, 3.12], [5.18, 3.12]], true, "a-p-det");
  ln([[4.85, 4.12], [5.18, 4.12]], true, "a-p-rec");
  box("detector", "trained", 5.2, 2.62, 2.05, 0.95, "Event detector", "did something happen?");
  box("recognizer", "trained", 5.2, 3.67, 2.05, 0.95, "Task recognizer", "which procedure is this?");
  ln([[7.25, 3.12], [7.58, 3.12]], true, "a-det-trk");
  ln([[7.25, 4.12], [7.58, 4.12]], true, "a-rec-trk");
  box("tracker", "trained", 7.6, 2.6, 2.7, 2.05, "Temporal state tracker", "Bayesian semi-Markov model · belief over the current step, time on step and next step", 15);
  [0.03, 0.06, 0.14, 0.7, 0.12, 0.05].forEach((p, i) => {
    const h = Math.max(0.03, (p * 0.5) / 0.7), bx = 7.85 + i * 0.36;
    rect(s, bx, 4.48 - h, 0.24, h, i === 3 ? "FF5B14" : "4A5156", `belief-bar-${i + 1}`);
  });
  ln([[10.3, 3.1], [10.63, 3.1]], true, "a-trk-pol");
  box("policy", "ours", 10.65, 2.62, 2.18, 1.0, "Policy", "speak · verify · stay silent · ask for a better view");
  ln([[11.74, 3.62], [11.74, 3.83]], true, "a-pol-coach");
  box("coach", "coach", 10.65, 3.85, 2.18, 0.8, "Coach", "voice · HUD");
  // bottom: only when something happens
  s.addShape(pres.ShapeType.roundRect, { x: 0.42, y: 5.2, w: 12.49, h: 1.35, rectRadius: 0.06, fill: { type: "none" }, line: { color: "3A4044", width: 1, dashType: "sysDash" }, objectName: "band-events" });
  tb(s, "Only when something happens", { x: 0.6, y: 5.45, w: 1.95, h: 0.8, fontSize: 11, fontFace: SEMI, color: "9AA3A7", objectName: "band-label" });
  ln([[8.0, 4.65], [8.0, 5.05], [3.85, 5.05], [3.85, 5.33]], false, "a-question"); lab("question", 6.6, 4.82, 1.3);
  box("student", "trained", 2.7, 5.35, 2.3, 1.05, "Local student", "routine checks on the device, free");
  ln([[5.0, 5.87], [5.28, 5.87]], false, "a-st-fast");
  box("fast", "rented", 5.3, 5.35, 2.3, 1.05, "Fast verifier", "if the student is unsure: one typed question, ~150 ms");
  ln([[7.6, 5.87], [7.88, 5.87]], false, "a-fast-front");
  box("frontier", "rented", 7.9, 5.35, 2.3, 1.05, "Frontier escalation", "if still unsure: the hard cases only");
  ln([[10.2, 5.87], [10.48, 5.87]], false, "a-front-cal");
  box("calibration", "ours", 10.5, 5.35, 2.33, 1.05, "Calibration", "turns answers into honest confidence");
  ln([[11.66, 5.35], [11.66, 4.95], [9.95, 4.95], [9.95, 4.67]], false, "a-evidence"); lab("evidence", 10.05, 4.73, 1.0);
  // legend
  let lx = 0.5;
  [["ours", "Ours", 0.95], ["trained", "Ours, trained on labeled recordings", 3.05], ["open", "Open model", 1.55], ["rented", "Rented, swappable in one line", 2.75]].forEach(([k, t, w]) => {
    const st = ST[k];
    s.addShape(pres.ShapeType.roundRect, { x: lx, y: 6.85, w: 0.28, h: 0.17, rectRadius: 0.02, fill: st.fill ? { color: st.fill } : { type: "none" }, line: st.line, objectName: `legend-${k}` });
    tb(s, t, { x: lx + 0.37, y: 6.83, w: w - 0.37, h: 0.22, fontSize: 10.5, color: "C9CFCC", objectName: "legend-label" });
    lx += w;
  });
  s.addNotes(`SAY (50 s): Here's what's under the hood, and why it isn't a wrapper around a chatbot. Two inputs. The company's manual goes through our procedure compiler and becomes a structured task graph. The first-person video goes through open vision models, then into two models we train: an event detector that notices when something happened, and a task recognizer that works out which procedure this is. Both feed the core: a temporal state tracker, a Bayesian semi-Markov model that keeps a running belief about which step you're on, how long you've been on it and what comes next. A policy decides whether to speak, verify, stay quiet or ask for a better view, and the coach says it by voice or on the HUD. All of that runs on every frame. The bottom row only runs when something happens: a local student handles routine checks for free, a fast rented model answers in about 150 milliseconds, and only the hard cases go to the expensive frontier model. Calibration turns those answers into honest confidence before they update the tracker. The rented models can be swapped in one line.

IF ASKED: numbers for each part (latencies, 14% of frames, calibration 0.22 → 0.02, the student's 69% agreement and 34% fewer frontier calls) are in appendix ${ref(aArchitecture)}; what we train vs rent is appendix ${ref(aTrain)}.`);
}

// ---------- 7 · Measured: same model, better system ----------
function sResults() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("Measured", { placeholder: "eyebrow" });
  s.addText("Same frontier model, better system", { placeholder: "title" });
  tb(s, "We compared Praxis with calling the same model (Claude Opus 5.5) every 5 seconds, on 48 first-person videos neither had seen.", { x: 0.5, y: 1.42, w: 12.33, h: 0.35, fontSize: 15, color: BODY });
  const block = (y, num, rest, bars) => {
    tb(s, [{ text: num, options: { color: C.accent2 } }, { text: rest }], { x: 0.5, y, w: 7.8, h: 0.5, fontFace: HEAD, fontSize: 26, color: C.text1, objectName: "result-head" });
    const max = bars[0][1];
    bars.forEach(([name, v, val], j) => {
      const by = y + 0.62 + j * 0.42, bw = Math.max(0.08, 4.4 * v / max), ours = j === 1;
      tb(s, name, { x: 0.5, y: by, w: 2.2, h: 0.32, fontSize: 13, fontFace: ours ? SEMI : "Archivo", color: ours ? C.text1 : BODY, valign: "middle" });
      rect(s, 2.7, by + 0.04, bw, 0.24, ours ? C.accent1 : "9AA3A7", "result-bar");
      tb(s, val, { x: 2.7 + bw + 0.12, y: by, w: 1.2, h: 0.32, fontFace: SEMI, fontSize: 13.5, color: ours ? C.accent2 : C.text1, valign: "middle" });
    });
  };
  block(2.05, "8× fewer", " calls to the frontier model", [["Every 5 seconds", 2817, "2,817"], ["Praxis", 351, "351"]]);
  block(3.7, "5× cheaper", " per minute of video", [["Every 5 seconds", 0.085, "$0.085"], ["Praxis", 0.018, "$0.018"]]);
  line(s, 0.5, 5.4, 8.2, 5.4, { color: C.text1, width: 1.25, name: "result-rule" });
  [
    ["About $1", "of model calls per coached hour, against $200 a month per trainee"],
    ["Better tracking", "It follows the step more accurately than the baseline while asking the frontier model 8× less"],
  ].forEach(([h, b], i) => {
    const x = 0.5 + i * 3.95;
    tb(s, h, { x, y: 5.55, w: 3.7, h: 0.45, fontFace: HEAD, fontSize: 22, color: C.text1 });
    tb(s, b, { x, y: 6.02, w: 3.65, h: 0.7, fontSize: 12.5, color: BODY });
  });
  // right: a real moment from the live session where it couldn't see, then the benchmark behind it
  const x = 8.75, w = 4.08, iy = 2.5, ih = w * 9 / 16;
  tb(s, "When it can't see, it says so", { x, y: 2.0, w, h: 0.42, fontFace: HEAD, fontSize: 20, color: C.text1 });
  s.addImage({ path: path.join(__dirname, "assets", "photos", "live-4m25s-view.jpg"), x, y: iy, w, h: ih, objectName: "view-frame" });
  const fx = (px) => x + px * w / 960, fy = (py) => iy + py * ih / 540; // the clipped soldering-station display
  s.addShape(pres.ShapeType.roundRect, { x: fx(632), y: fy(3), w: fx(806) - fx(632), h: fy(84) - fy(3), rectRadius: 0.04, fill: { type: "none" }, line: { color: HUD.blue, width: 2, dashType: "dash" }, objectName: "view-target" });
  rect(s, x, iy + ih + 0.2, 0.06, 0.7, C.accent4, "quote-edge");
  tb(s, [
    { text: "“Look closely at the soldering station display, upper right.”", options: { fontFace: SEMI, fontSize: 14, color: C.text1, breakLine: true, paraSpaceAfter: 3 } },
    { text: "Praxis at 4:25 in the live repair, with the display half out of frame", options: { fontSize: 11.5, color: C.text2 } },
  ], { x: x + 0.22, y: iy + ih + 0.17, w: w - 0.22, h: 0.8, objectName: "view-quote" });
  [["77–98%", "of blurred or blocked checks: Praxis asked to see it again", C.accent4], ["Up to 73%", "the every-5-seconds baseline named the wrong step with confidence", C.accent5]].forEach(([b, c, col], i) => {
    const y = 5.95 + i * 0.46;
    tb(s, b, { x, y, w: 1.4, h: 0.42, fontFace: HEAD, fontSize: 18, color: col, valign: "middle" });
    tb(s, c, { x: x + 1.45, y, w: w - 1.45, h: 0.42, fontSize: 11.5, color: BODY, valign: "middle" });
  });
  footer(s, 0, "results/runs/fused_oracle.json vs baseline_stateless.json (48 held-out CaptainCook4D clips, 235 min, one run each) · results/metrics.json call_mix · results/l5/visual_uncertainty.json (60 checks per condition)");
  s.addNotes(`SAY (45 s): Here's what the tracker buys, measured. Same frontier model, same 48 first-person videos neither system had seen. The baseline asks the model about the video every 5 seconds with no memory of the task. Praxis asks the frontier model 8 times less often: 351 calls instead of 2,817. It's 5 times cheaper per minute of video, about a dollar of model calls per coached hour, and it tracks the current step better, not worse. And when the view is blurred or blocked, it asks for another view instead of guessing.

The picture is a real frame from the live repair session at 4:25: the camera swung and the soldering station display is half out of frame. Both verifier tiers logged the view as insufficient, and the quote is the frontier model's actual request from the session log. (In that session the policy did not put a card on screen for it.)

IF ASKED for raw numbers (appendix ${ref(aBenchmark)}): step tracking 54% vs 48% with the task given; $0.018 vs $0.085 per video-minute. Praxis also makes 2,679 calls to a fast, cheap model (~150 ms), so total calls are about the same; what drops is the expensive ones. The eval set is CaptainCook4D, a public first-person procedure dataset (cooking), because labeled maintenance video doesn't exist off the shelf; that's what the grant's data money buys. One run per system. Confident = at least 50% confidence. Mistake detection is our weakest number (4 of 17 alerts named a real annotated error).`);
}

// ---------- 8 · Why now ----------
function sWhyNow() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("Why now", { placeholder: "eyebrow" });
  s.addText("Smart-glasses hardware is finally open to software", { placeholder: "title" });
  const top = 1.75;
  const L = { x: 0.5, w: 5.6 }, base = 5.3, maxH = 2.45;
  line(s, L.x, top, L.x + L.w, top, { color: C.text1, width: 1.25, name: "panel-rule" });
  label(s, "AI glasses shipped per year, worldwide", { x: L.x, y: top + 0.12, w: L.w, h: 0.3, fontSize: 13, color: C.text1 });
  const gl = [["2024", 2.06, "2.1M"], ["2025", 8.7, "8.7M"], ["2026 forecast", 15, "15M+"]];
  const bw = 1.2, gap = (L.w - 3 * bw) / 3;
  gl.forEach(([yr, v, lab], i) => {
    const h = maxH * v / 15, x = L.x + gap / 2 + i * (bw + gap), now = i === 2;
    rect(s, x, base - h, bw, h, now ? C.accent1 : i === 1 ? "5E676C" : "9AA3A7", "glasses-bar");
    tb(s, lab, { x: x - 0.3, y: base - h - 0.46, w: bw + 0.6, h: 0.42, fontFace: HEAD, fontSize: 22, align: "center", color: now ? C.accent2 : C.text1 });
    tb(s, yr, { x: x - 0.4, y: base + 0.08, w: bw + 0.8, h: 0.28, fontSize: 12, align: "center", color: C.text2 });
  });
  line(s, L.x, base, L.x + L.w, base, { color: C.text1, width: 1, name: "glasses-base" });
  const R = { x: 6.75, w: 6.08 };
  line(s, R.x, top, R.x + R.w, top, { color: C.text1, width: 1.25, name: "panel-rule" });
  label(s, "Platforms opening to outside developers", { x: R.x, y: top + 0.12, w: R.w, h: 0.3, fontSize: 13, color: C.text1 });
  const ev = [
    ["2025", "Meta opens a developer preview: outside apps can use its glasses' camera"],
    ["Sept 2026", "Meta's toolkit reaches 1.0: camera, microphones and speakers for outside apps", true],
    ["Fall 2026", "Google's first Android XR glasses arrive: audio, with a camera"],
    ["Q1 2027", "Viture and NVIDIA ship Helix: safety glasses that coach workers on procedures in real time"],
  ];
  const ty0 = top + 0.7, step = 0.82;
  line(s, R.x + 0.08, ty0 + 0.1, R.x + 0.08, ty0 + 3 * step + 0.1, { color: C.accent6, width: 1, name: "timeline" });
  ev.forEach(([d, t, hl], i) => {
    const y = ty0 + i * step;
    dot(s, R.x, y + 0.02, 0.16, hl ? C.accent1 : C.text1, "timeline-dot");
    tb(s, d, { x: R.x + 0.38, y: y - 0.03, w: 1.25, h: 0.28, fontFace: SEMI, fontSize: 13, color: hl ? C.accent2 : C.text1 });
    tb(s, t, { x: R.x + 1.7, y: y - 0.04, w: R.w - 1.7, h: 0.62, fontSize: 14, color: BODY });
  });
  line(s, 0.5, 5.95, 12.83, 5.95, { color: C.accent6, width: 0.75, name: "close-rule" });
  rect(s, 0.5, 6.12, 0.06, 0.62, C.accent1, "close-edge");
  tb(s, "Three years ago we would have had to build the glasses.\nNow we build the software that runs on them.", { x: 0.75, y: 6.08, w: 12.0, h: 0.68, fontFace: SEMI, fontSize: 19, color: C.text1, valign: "middle", objectName: "close-line" });
  footer(s, 0, "Omdia: 8.7M AI glasses shipped in 2025 (+322%), >15M forecast for 2026; 2024 backed out from the growth rate · Meta Wearables Device Access Toolkit docs and changelog · Google I/O 2026 (Android XR audio glasses this fall) · Viture Helix release, 16 Jun 2026");
  s.addNotes(`SAY (40 s): Why now. AI glasses went from about 2 million shipped in 2024 to 8.7 million last year, with more than 15 million forecast this year. And the platforms opened up to outside software: Meta's toolkit, which gives apps the glasses' camera, microphones and speakers, reached 1.0 in September; Google's first Android XR glasses arrive this fall; and Viture and NVIDIA ship Helix early next year, safety glasses that coach workers on procedures, which tells you the category is real. Three years ago we would have had to build the glasses. Now we build the software that runs on them.

IF ASKED: Meta's developer preview came first (announced at Connect 2025); 1.0 is the stable release in September 2026. Public app-store publishing for these apps isn't open yet; test users get builds through Meta's release channels, which is fine for a pilot. Google gave only "fall 2026" for the audio glasses, with display models later.`);
}

// ---------- 9 · Competition: devices below, Praxis above ----------
function sGlassesWar() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("Competition", { placeholder: "eyebrow" });
  s.addText("We don't need to win the glasses hardware race", { placeholder: "title" });
  // left: the stack. Praxis on top, one thin adapter per device, the hardware underneath
  const L = 0.5, LW = 7.75, py = 1.7, ph = 2.45;
  rect(s, L, py, LW, ph, C.text1, "praxis-plate");
  rect(s, L, py, LW, 0.07, C.accent1, "praxis-plate-top");
  tb(s, [{ text: "Praxis", options: { fontFace: HEAD, fontSize: 24, color: C.background2 } }, { text: "    the maintenance software", options: { fontSize: 15, color: C.accent6 } }], { x: L + 0.3, y: py + 0.25, w: LW - 0.6, h: 0.5, valign: "middle", objectName: "praxis-name" });
  const mods = ["Procedure compiler", "Task state", "Verification", "When to speak", "Records", "Maintenance models"];
  const mg = 0.12, mw = (LW - 0.6 - 2 * mg) / 3, mh = 0.62;
  mods.forEach((t, i) => {
    const mx = L + 0.3 + (i % 3) * (mw + mg), my = py + 0.95 + Math.floor(i / 3) * (mh + mg);
    s.addText(t, { shape: pres.ShapeType.rect, x: mx, y: my, w: mw, h: mh, fill: { color: "2A2F32" }, line: { type: "none" }, fontFace: SEMI, fontSize: 14, color: "E8EBE9", valign: "middle", margin: [12, 8, 4, 4], objectName: "praxis-module" });
  });
  // adapter layer
  const dw = (LW - 3 * 0.15) / 4, ay = 4.3, ah = 0.34, dy = 4.8, dh = 1.05;
  rect(s, L, ay, LW, ah, C.accent1, "adapter-band");
  tb(s, "A thin adapter for each device", { x: L + 0.3, y: ay, w: LW - 0.6, h: ah, fontFace: SEMI, fontSize: 12, color: C.text1, valign: "middle", objectName: "adapter-label" });
  const devs = [["Meta", "Ray-Ban, Oakley, Display"], ["Google", "Android XR, with Samsung"], ["Viture", "Helix, with NVIDIA"], ["Future devices", "the next platform", true]];
  devs.forEach(([h, b, future], i) => {
    const x = L + i * (dw + 0.15), cx = x + dw / 2;
    line(s, cx, py + ph, cx, ay, { color: C.accent1, width: 2, name: "adapter-up" });
    line(s, cx, ay + ah, cx, dy, { color: C.accent1, width: 2, name: "adapter-down" });
    s.addText([{ text: h, options: { fontFace: HEAD, fontSize: 16, color: future ? C.text2 : C.text1, breakLine: true } }, { text: b, options: { fontSize: 11.5, color: future ? C.text2 : BODY } }], { shape: pres.ShapeType.rect, x, y: dy, w: dw, h: dh, fill: future ? { type: "none" } : { color: "C9CFCC" }, line: future ? { color: "9AA3A7", width: 1.25, dashType: "dash" } : { type: "none" }, valign: "middle", margin: [12, 8, 4, 4], objectName: "device-plate" });
  });
  tb(s, "They build the glasses. Every new device is one more adapter for Praxis.", { x: L, y: 6.1, w: LW, h: 0.4, fontFace: SEMI, fontSize: 15.5, color: C.text1 });
  // right: other approaches, the closest one marked
  const x = 8.65, w = 4.18;
  tb(s, "Other approaches", { x, y: 1.7, w, h: 0.35, fontFace: SEMI, fontSize: 15, color: C.text2 });
  [
    ["Procedure software", "MaintainX, Tulip, Augmentir", "Steps on a screen. It can't see the work."],
    ["Fixed cameras", "Retrocausal, Invisible AI", "Watch one station. They can't follow a tech around a machine."],
    ["General assistants", "Meta AI, Gemini Live", "Answer about what's in view, with no procedure or step state."],
    ["Viture Helix + NVIDIA", "Our closest competitor", "Real-time coaching sold with its own glasses. We want Praxis to run on Helix too."],
  ].forEach(([h, ex, b], i) => {
    const y = 2.15 + i * 1.1, close = i === 3;
    line(s, x, y, x + w, y, { color: close ? C.accent1 : C.text1, width: close ? 2.5 : 1, name: "other-rule" });
    tb(s, [
      { text: h, options: { fontFace: SEMI, fontSize: 15, color: C.text1 } },
      { text: `   ${ex}`, options: { fontSize: 11.5, color: close ? C.accent2 : C.text2, breakLine: true } },
      { text: b, options: { fontSize: 13, color: BODY } },
    ], { x, y: y + 0.12, w, h: 0.92, objectName: "other-text" });
  });
  footer(s, 0, `Vendor product pages and docs, checked 17 Oct 2026 · Viture Helix release, 16 Jun 2026 · detail in appendix ${ref(aCompetitors)}`);
  s.addNotes(`SAY (45 s): We don't need to win the glasses race. Meta, Google and Samsung, Viture and NVIDIA are spending billions on cameras, batteries, optics and distribution, and they ship one general assistant for everyone. Praxis sits on top: the procedure compiler, the task state, verification, deciding when to speak, the records, and over time our own maintenance models. Each new device is one thin adapter for us. As for other software: procedure apps put steps on a screen but can't see the work; fixed cameras watch one station; general assistants answer about what's in view with no procedure. The closest competitor is Viture's Helix with NVIDIA: real-time procedure coaching, sold with their own glasses, shipping early next year. We want Praxis to run on Helix too.

IF ASKED: our Meta and Viture adapters are coded but not yet tested on a device (appendix ${ref(aHardwareQA)}). Whether Helix accepts outside apps isn't documented; NVIDIA's XR AI library is open source, which is the likely path. Viture hasn't published how procedures get into Helix or any accuracy numbers, so don't say they need filming. Fixed-camera vendors are ahead of us on live mistake detection at a single station.`);
}

// ---------- 10 · Market + buyer economics: where we start, and why the buyer's math works ----------
function sMarket() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("Market", { placeholder: "eyebrow" });
  s.addText("Maintenance is where we start, and Praxis pays for itself", { placeholder: "title" });
  // the wedge, as an equation
  label(s, "Maintenance new-hire onboarding in the US, per year", { x: 0.5, y: 1.45, w: 7.8, h: 0.3, fontSize: 13, color: C.text1 });
  [
    [0.5, 1.5, "~255k", "new maintenance techs"],
    [2.0, 0.35, "×"],
    [2.35, 1.35, "$200", "a month per trainee"],
    [3.7, 0.35, "×"],
    [4.05, 1.15, "~6", "months of onboarding"],
    [5.2, 0.35, "≈"],
    [5.55, 3.0, "$306M", "a year, at our pricing hypothesis"],
  ].forEach(([x, w, big, cap], i) => {
    const res = i === 6;
    tb(s, big, { x, y: 1.72, w, h: 0.65, fontFace: HEAD, fontSize: cap ? (res ? 38 : 30) : 24, color: res ? C.accent2 : cap ? C.text1 : C.text2, align: cap ? "left" : "center", valign: "bottom", objectName: cap ? "wedge-term" : "wedge-op" });
    if (cap) tb(s, cap, { x, y: 2.42, w: w - 0.05, h: 0.5, fontSize: 12, color: BODY });
  });
  // where the same software goes next, as a short vertical path
  const vx = 8.9, vw = 3.93;
  line(s, vx + 0.08, 1.62, vx + 0.08, 2.52, { color: C.accent6, width: 1, name: "next-track" });
  [
    ["Start", "maintenance new-hire onboarding", true],
    ["Next", "all maintenance and field service"],
    ["Then", "technical onboarding in manufacturing, utilities, aviation, telecom, labs"],
  ].forEach(([k, t, now], i) => {
    const y = 1.47 + i * 0.45;
    dot(s, vx, y + 0.07, 0.16, now ? C.accent1 : C.text1, "next-dot");
    tb(s, [{ text: `${k}  `, options: { fontFace: SEMI, color: now ? C.accent2 : C.text1 } }, { text: t, options: { color: BODY } }], { x: vx + 0.3, y, w: vw - 0.3, h: 0.5, fontSize: 12.5 });
  });
  line(s, 0.5, 3.12, 12.83, 3.12, { color: C.text1, width: 1.25, name: "econ-rule" });
  // left: one new technician, to scale
  label(s, "One new technician", { x: 0.5, y: 3.25, w: 7, h: 0.3, fontSize: 13, color: C.text1 });
  const bx = 2.95, k = 3.9 / 15000;
  [
    ["Hire + ramp burden today", 10000, 15000, "$10–15k", C.text1],
    ["Praxis, six months", 1200, null, "$1,200", C.accent1],
    ["Our cost to serve", 270, null, "~$270", "5E676C"],
  ].forEach(([name, v, v2, val, col], i) => {
    const y = 3.62 + i * 0.47, w = Math.max(0.06, v * k);
    tb(s, name, { x: 0.5, y, w: 2.4, h: 0.38, fontSize: 13.5, fontFace: i === 1 ? SEMI : "Archivo", color: C.text1, valign: "middle" });
    rect(s, bx, y + 0.06, w, 0.26, col, "econ-bar");
    let end = bx + w;
    if (v2) { rect(s, end, y + 0.06, (v2 - v) * k, 0.26, "9AA3A7", "econ-bar-range"); end = bx + v2 * k; }
    tb(s, val, { x: end + 0.12, y, w: 1.2, h: 0.38, fontFace: HEAD, fontSize: 18, color: i === 1 ? C.accent2 : C.text1, valign: "middle" });
  });
  tb(s, "~77% gross margin today, ~90% with our local model", { x: bx, y: 5.02, w: 5, h: 0.3, fontSize: 12, color: BODY });
  tb(s, [{ text: "Pays for itself if it removes roughly " }, { text: "8–12%", options: { color: C.accent2 } }, { text: " of that burden." }], { x: 0.5, y: 5.35, w: 8.1, h: 0.45, fontFace: HEAD, fontSize: 19, color: C.text1 });
  // right: a 50-technician team (about 1 in 10 maintenance jobs opens each year)
  const x = 8.9, base = 5.45, kk = 1.15 / 75000;
  label(s, "A 50-technician maintenance team", { x, y: 3.25, w: 3.93, h: 0.3, fontSize: 13, color: C.text1 });
  tb(s, "about 5 new hires a year", { x, y: 3.52, w: 3.93, h: 0.28, fontSize: 12, color: BODY });
  [
    [x + 0.15, 50000, 75000, "$50–75k", "hire + ramp burden", C.text1],
    [x + 2.2, 6000, null, "$6k", "Praxis a year", C.accent1],
  ].forEach(([cx, v, v2, val, cap, col], i) => {
    const h = v * kk, top = base - (v2 ? v2 * kk : h);
    if (v2) rect(s, cx, base - v2 * kk, 1.3, (v2 - v) * kk, "9AA3A7", "org-bar-range");
    rect(s, cx, base - h, 1.3, h, col, "org-bar");
    tb(s, val, { x: cx - 0.2, y: top - 0.38, w: 1.7, h: 0.34, fontFace: HEAD, fontSize: 17, color: i ? C.accent2 : C.text1, align: "center" });
    tb(s, cap, { x: cx - 0.25, y: base + 0.05, w: 1.8, h: 0.28, fontSize: 11.5, color: BODY, align: "center" });
  });
  line(s, x, base, 12.83, base, { color: C.text1, width: 1, name: "org-base" });
  // who we sell to first
  line(s, 0.5, 5.95, 12.83, 5.95, { color: C.accent6, width: 0.75, name: "who-rule" });
  rect(s, 0.5, 6.13, 0.1, 0.1, C.accent1, "who-mark");
  tb(s, [
    { text: "We start with small and mid-size maintenance teams. ", options: { fontFace: SEMI, color: C.text1 } },
    { text: "98% of US manufacturers have fewer than 500 employees, and there one maintenance manager can approve a paid pilot. The pilot measures senior-tech hours, days until a new tech works alone, and rework.", options: { color: BODY } },
  ], { x: 0.72, y: 6.03, w: 12.1, h: 0.75, fontSize: 13 });
  footer(s, 0, `BLS OEWS + Occupational Outlook Handbook: ~255k openings a year on ~2.47M maintenance and repair jobs (about 1 in 10) · Reliability magazine (A. Gager): $10–15k to recruit, hire and ramp a maintenance tech, including recruiting fees · Eptura: hidden onboarding cost is experienced staff supervising and double-checking new hires · NAM: 98% of US manufacturers have fewer than 500 employees · cost to serve: $0.018/video-min measured × ~250 coached hours · $200/month is our hypothesis; Tulip lists ~$100 (Essentials) and ~$250 (Professional) per interface a month · later-market sizing in appendix ${ref(aMarketMath)}`);
  s.addNotes(`SAY (50 s): We start with maintenance, specifically new technicians. About 255,000 maintenance and repair openings a year in the US, at $200 a month for about six months of onboarding, is about $306 million a year at our pricing hypothesis. From there the same software extends to every maintenance and field-service tech, and then to technical onboarding in manufacturing, utilities, aviation, telecom and labs. And the buyer's math works. A new tech carries a $10 to 15 thousand hire-and-ramp burden, mostly experienced staff supervising and double-checking them. Praxis costs $1,200 for six months, and about $270 for us to run, so it pays for itself if it removes roughly 8 to 12% of that burden. For a 50-technician team that hires about 5 people a year, that's $50 to 75 thousand of burden against $6 thousand of Praxis. We start with small and mid-size teams, where one maintenance manager can approve a paid pilot, and the pilot measures what we actually change.

IF ASKED: about 1 in 10 maintenance jobs opens each year (BLS: ~255k openings on ~2.47M jobs), so a 50-tech team hires about 5. A team hiring 25 a year is a ~250-tech org, like a hospital system or a multi-plant manufacturer. The $10-15k includes recruiting fees, which Praxis doesn't touch, so the gap is not savings; Praxis pays back if it removes about a tenth of it. Eptura cites ~25% productivity in month one and up to ~26 weeks to full performance. Who the buyer is: the maintenance manager at a plant (food, packaging, plastics), a facilities director (property managers, hotels, school districts, towns, universities, hospitals), or a service manager at an HVAC, elevator or equipment-service contractor. Small firms decide fast but are price-sensitive, which is why the pitch is in their own senior techs' hours. Later-market sizing (~$1.8B, ~$9.2B) is in appendix ${ref(aMarketMath)}.`);
}

// ---------- 11 · How we sell: one customer path, pricing on it, trade schools as a second path ----------
function sGTM() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("Go-to-market", { placeholder: "eyebrow" });
  s.addText("We sell to maintenance managers, one paid pilot at a time", { placeholder: "title" });
  const stages = [
    ["Maintenance manager", "at a plant, facilities team, HVAC company or repair shop"],
    ["Demo on their own manual", "a procedure their new techs already struggle with"],
    ["Short paid pilot", "the success metric is agreed first, like days until a new tech works alone"],
    ["Annual agreement", "$200 a month per active-trainee license"],
    ["Expand", "every new hire, then other sites"],
  ];
  const ty = 2.0, n = stages.length, sp = 12.33 / n;
  line(s, 0.6, ty, 12.7, ty, { color: C.text1, width: 1.5, arrow: true, name: "path-track" });
  stages.forEach(([h, b], i) => {
    const x = 0.5 + i * sp, pilot = i === 2;
    dot(s, x, ty - 0.14, 0.28, pilot ? C.accent1 : C.text1, "path-dot");
    tb(s, String(i + 1), { x, y: ty - 0.14, w: 0.28, h: 0.28, fontFace: SEMI, fontSize: 11, color: "FFFFFF", align: "center", valign: "middle" });
    tb(s, h, { x, y: ty + 0.3, w: sp - 0.25, h: 0.6, fontFace: SEMI, fontSize: 15, color: pilot ? C.accent2 : C.text1 });
    tb(s, b, { x, y: ty + 0.9, w: sp - 0.3, h: 0.9, fontSize: 12.5, color: BODY });
  });
  // pricing, stated plainly
  const py = 4.15;
  line(s, 0.5, py, 7.9, py, { color: C.text1, width: 1.25, name: "pricing-rule" });
  label(s, "How pricing works", { x: 0.5, y: py + 0.12, w: 7, h: 0.3, fontSize: 13, color: C.text1 });
  [
    ["One active-trainee license", " = one employee being onboarded: $200 a month, unlimited coaching sessions"],
    ["Five techs onboarding at once = five licenses.", " When one finishes, the license moves to the next hire"],
    ["Glasses are shared site equipment.", " 10 licenses with 3 people coached at the same time needs about 3 pairs"],
    ["We don't resell hardware.", " Sites buy supported glasses directly"],
  ].forEach(([a, b], i) => {
    tb(s, [{ text: a, options: { fontFace: SEMI, color: C.text1 } }, { text: b, options: { color: BODY } }], { x: 0.5, y: py + 0.45 + i * 0.56, w: 7.4, h: 0.52, fontSize: 13, valign: "middle" });
  });
  // second path: trade schools
  const x = 8.5, w = 4.33, Y = py, ph = 2.6;
  line(s, x, Y, x + w, Y, { color: C.text1, width: 1.25, name: "schools-rule" });
  tb(s, "Second path: trade schools", { x, y: Y + 0.12, w, h: 0.32, fontFace: SEMI, fontSize: 15, color: C.text1 });
  tb(s, "Students learn hands-on skills with Praxis and bring it to their first employer.", { x, y: Y + 0.5, w, h: 0.65, fontSize: 13.5, color: BODY });
  rect(s, x, Y + 1.35, 0.05, 0.85, C.accent1, "quote-edge");
  tb(s, [
    { text: "“We would be open to an experiment like this.”", options: { fontFace: SEMI, fontSize: 14, color: C.text1, breakLine: true, paraSpaceAfter: 3 } },
    { text: "Sonny Hunt, COO, The Fiber School (FiberOptic.com), discussed this week", options: { fontSize: 11.5, color: C.text2 } },
  ], { x: x + 0.22, y: Y + 1.32, w: w - 0.22, h: 0.95, objectName: "quote" });
  footer(s, 0, `Pricing is our hypothesis (appendix ${ref(aUnitEcon)}) · fiber-optic school email reply, Oct 19 2026 (docs/OUTREACH.md)`);
  s.addNotes(`SAY (35 s): How we sell. One customer path. I go to a maintenance manager at a plant, a facilities team or a repair shop, and show Praxis on one of their own manuals, a procedure their new techs already struggle with. Then a short paid pilot, with the success metric agreed before we start, like how many days until a new tech can do the job alone. If it works, an annual agreement at $200 a month per active-trainee license, and the license moves to the next hire. Glasses are shared site equipment, so a site needs enough pairs for the techs being coached at once, and we don't resell hardware. Trade schools are a second path: students learn with Praxis and bring it to their first job. A fiber-optic training school has already said they'd be open to trying it on one lab.

IF ASKED: no pilots or customers yet; outreach to maintenance employers, training programs and associations started Oct 17. Sonny Hunt, COO of The Fiber School, replied by email on Oct 19: instructors demo each lab, students follow a lab manual, there are recorded videos, and students still forget quickly once class ends. "We would be open to an experiment like this" is an offer to try one lab, not a pilot. Heavy all-shift use squeezes a flat license, so we'd price by coached hours or tiers if needed (appendix ${ref(aUnitEcon)}).`);
}

// ---------- 12 · Founder: technical depth + company building (from the resume) ----------
function sFounder() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("Founder", { placeholder: "eyebrow" });
  s.addText("I've built real-time vision systems for the physical world,\nand I've helped grow startups", { placeholder: "title" });
  const col = (x, w, head, rows) => {
    line(s, x, 2.2, x + w, 2.2, { color: C.text1, width: 1.5, name: "col-rule" });
    tb(s, head, { x, y: 2.3, w, h: 0.32, fontFace: SEMI, fontSize: 14, color: C.text2 });
    rows.forEach(([name, big, cap, body], i) => {
      const y = 2.75 + i * 1.18;
      if (i) line(s, x, y - 0.08, x + w, y - 0.08, { color: "C2C8C5", width: 0.75, name: "row-rule" });
      tb(s, big, { x, y, w: 1.85, h: 0.48, fontFace: HEAD, fontSize: 24, color: C.accent2, objectName: "founder-metric" });
      tb(s, cap, { x, y: y + 0.48, w: 1.8, h: 0.55, fontSize: 10.5, color: C.text2 });
      tb(s, [{ text: name, options: { fontFace: SEMI, color: C.text1, breakLine: true } }, { text: body, options: { color: BODY } }], { x: x + 1.95, y, w: w - 1.95, h: 1.08, fontSize: 12.5 });
    });
  };
  col(0.5, 6.0, "Engineering and research", [
    ["LipTrac", "60,000+", "video frames", "Real-time visual speech recognition. Conv3D + bidirectional GRU, tested with 12 participants. Provisional patent filed."],
    ["OCTOPAS", "217.9%", "better collection than conventional methods", "Autonomous oil-spill cleanup: aerial computer vision, path planning and marine robotics. Published; provisional patent filed."],
    ["Competitive robotics", "7 years", "FTC team captain", "World Championship qualifier. Autonomous control, sensor fusion, OpenCV and path planning. My open-source FTC Coach has 25,000+ users."],
  ]);
  col(6.83, 6.0, "Startups and growth", [
    ["Qurios Ventures · co-founder, CMO", "$50k", "MRR, from under $1k", "Built a 14,000+ member community in about four months. Acquired by Crimson Education for $1.3M."],
    ["Claisen Health · co-founder, CMO", "13", "person growth team", "Ran acquisition across UGC, influencers and Reddit as the company raised $200k from angels."],
    ["Acely AI (YC W18)", "$300k", "attributable revenue", "One of 6 marketing interns picked from 1,500 applicants."],
  ]);
  line(s, 0.5, 6.32, 12.83, 6.32, { color: C.accent6, width: 0.75, name: "founder-rule" });
  tb(s, [{ text: "Harvard College", options: { fontFace: SEMI, color: C.text1 } }, { text: "   Applied Mathematics + Computer Science", options: { color: BODY } }], { x: 0.5, y: 6.42, w: 6.2, h: 0.36, fontSize: 14, valign: "middle" });
  footer(s, 0, "Monish Saravana resume (Oct 2026) · Startups @ Harvard application · LipTrac provisional US 63/812,158 · OCTOPAS provisional US 63/813,616, Florida Water Resources Journal");
  s.addNotes(`SAY (30 s): On the left, the technical side: I've built real-time vision for the physical world before. LipTrac reads lips in real time from video, with a provisional patent. OCTOPAS used aerial computer vision and path planning to guide oil-spill cleanup robots, and beat conventional collection by 218%. And seven years of competitive robotics: autonomous control, sensor fusion, path planning. On the right, the company side: I co-founded Qurios, grew it from under a thousand to fifty thousand a month in recurring revenue, and it was acquired; at Claisen I ran a 13-person growth team; at Acely I drove $300k in revenue. So I can build the system, and I know how to get it to customers.

IF ASKED: solo founder is a known risk; the grant tests demand before hiring, and first hires come after the first pilot. FTC Coach (25,000+ users in 50+ countries) and FTC Elo (3,000+ recurring users) are open-source tools I built. More in appendix ${ref(aFounder)}.`);
}

// ---------- 13 · Roadmap: the rising stepped path ----------
function sVision() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("Roadmap", { placeholder: "eyebrow" });
  s.addText("Coaching comes first. Our own models and\nskill records come next", { placeholder: "title" });
  const gap = 0.15, w = (12.33 - 3 * gap) / 4, ys = [2.95, 2.65, 2.35, 2.05];
  const steps = [
    ["Now", "Maintenance coaching and verification", "Paid pilots. New techs coached from their own company's manuals."],
    ["Next", "Maintenance-specific models", "With customer permission, real maintenance recordings make our state and checking models better and cheaper."],
    ["Then", "Verified skills and certification partners", "Techs and employers build verified skill histories in Praxis. Certified techs bring Praxis to their next job."],
    ["Later", "Physical AI, two ways in", null],
  ];
  steps.forEach(([k, h, body], i) => {
    const x = 0.5 + i * (w + gap), y = ys[i], xe = i < 3 ? x + w + gap : x + w, later = i === 3;
    line(s, x, y, xe, y, { color: i === 0 ? C.accent1 : later ? "9AA3A7" : C.text1, width: i === 0 ? 3 : 1.5, dash: later ? "dash" : undefined, name: "stair-tread" });
    if (i < 3) line(s, xe, y, xe, ys[i + 1], { color: i === 2 ? "9AA3A7" : C.text1, width: 1.5, dash: i === 2 ? "dash" : undefined, name: "stair-riser" });
    s.addShape(pres.ShapeType.ellipse, { x: x - 0.02, y: y - 0.11, w: 0.22, h: 0.22, fill: later ? { color: C.background2 } : { color: i === 0 ? C.accent1 : C.text1 }, line: later ? { color: "9AA3A7", width: 1.5 } : { type: "none" }, objectName: "stair-dot" });
    const tx = x + 0.2, tw = w - 0.3;
    tb(s, k, { x: tx, y: y + 0.18, w: tw, h: 0.28, fontFace: SEMI, fontSize: 13, color: i === 0 ? C.accent2 : later ? C.text2 : C.text1 });
    tb(s, h, { x: tx, y: y + 0.47, w: tw, h: 0.62, fontFace: HEAD, fontSize: 16.5, color: C.text1 });
    if (body) {
      tb(s, body, { x: tx, y: y + 1.1, w: tw - 0.05, h: 1.3, fontSize: 13, color: BODY });
    } else {
      // the two paths into physical AI, drawn as a fork off the dashed tread
      const fx = tx + 0.02;
      line(s, fx, y + 0.98, fx, y + 2.05, { color: "9AA3A7", width: 1.5, dash: "dash", name: "fork-trunk" });
      [["A", "Build our own robot models", "trained on step-verified recordings customers opted in"],
       ["B", "Sell to physical-AI labs", "license consented data and our step checker"]].forEach(([tt, hh, bb], j) => {
        const by = y + 1.0 + j * 0.88, my = by + 0.17;
        line(s, fx, my, fx + 0.2, my, { color: "9AA3A7", width: 1.5, name: "fork-branch" });
        dot(s, fx + 0.17, my - 0.06, 0.12, C.accent1, "fork-dot");
        tb(s, [
          { text: `${tt}  `, options: { fontFace: HEAD, color: C.accent2 } },
          { text: hh, options: { fontFace: SEMI, color: C.text1, breakLine: true } },
          { text: bb, options: { fontSize: 11.5, color: BODY } },
        ], { x: fx + 0.38, y: by, w: tw - 0.38, h: 0.82, fontSize: 13 });
      });
    }
  });
  // what labs already pay for human training data, and the robot companies coming next
  const py = 4.95, ph = 1.85;
  s.addShape(pres.ShapeType.roundRect, { x: 0.5, y: py, w: 12.33, h: ph, rectRadius: 0.05, fill: { color: C.text1 }, line: { type: "none" }, objectName: "panel-data-market" });
  tb(s, "What AI labs pay for human training data keeps climbing", { x: 0.85, y: py + 0.18, w: 7, h: 0.32, fontFace: SEMI, fontSize: 14, color: C.accent1 });
  // mini bar chart: one data vendor's gross run-rate
  const bars = [["Dec 2025", 0.76, "$0.76B"], ["Feb 2026", 1.0, "$1B"], ["Jun 2026", 2.0, "$2B"]];
  const cbase = py + 1.42, cmax = 0.72, cbw = 0.62, cx0 = 0.85;
  bars.forEach(([d, v, lab], i) => {
    const h = cmax * v / 2.0, x = cx0 + i * 0.95, now = i === 2;
    rect(s, x, cbase - h, cbw, h, now ? C.accent1 : i === 1 ? "8A9397" : "5E676C", "data-bar");
    tb(s, lab, { x: x - 0.2, y: cbase - h - 0.27, w: cbw + 0.4, h: 0.25, fontFace: SEMI, fontSize: 12, color: now ? C.accent1 : C.background2, align: "center" });
    tb(s, d, { x: x - 0.2, y: cbase + 0.04, w: cbw + 0.4, h: 0.22, fontSize: 9.5, color: C.accent6, align: "center" });
  });
  line(s, cx0 - 0.05, cbase, cx0 + 2.6, cbase, { color: "5E676C", width: 0.75, name: "data-base" });
  tb(s, "Mercor's run-rate from selling expert human data to AI labs", { x: 3.6, y: py + 0.62, w: 2.3, h: 0.9, fontSize: 11.5, color: C.accent6 });
  line(s, 6.15, py + 0.62, 6.15, py + 1.6, { color: "3A4044", width: 1, name: "panel-sep" });
  [
    [">$100M", "a year that robotics companies already spend buying real-world data"],
    [">$1B", "that Figure has committed to data and compute over the next 12 months"],
    ["$3.2B → $16.3B", "the AI training-data market, 2025 to the 2033 forecast"],
  ].forEach(([b, c], i) => {
    const x = 6.45 + i * 2.1;
    tb(s, b, { x, y: py + 0.6, w: 2.0, h: 0.42, fontFace: HEAD, fontSize: i === 2 ? 17 : 20, color: C.background2 });
    tb(s, c, { x, y: py + 1.02, w: 1.92, h: 0.75, fontSize: 11, color: C.accent6 });
  });
  footer(s, 0, `Mercor: CEO via Dealroom (Jul 2026), gross run-rate; Dec 2025 is a Sacra estimate · robotics data spend: Micro1 CEO estimate, MIT Technology Review (Apr 2026) · Figure, Introducing Index (Aug 2026) · Grand View Research, AI training dataset market (2026–2033 edition) · revenue targets: appendix ${ref(aLongGame)}`);
  s.addNotes(`SAY (40 s): Here's where it goes. Now: maintenance coaching and verification, in paid pilots. Next: with customer permission, real maintenance recordings make our own state and checking models better and cheaper. Then: verified skill histories with certification partners, which gives us switching friction and distribution, because certified techs carry Praxis to their next job. Later, physical AI, and there are two ways in: build our own robot models on step-verified recordings customers opted in, or sell that data and our step checker to physical-AI labs. That second market is already real. One company selling expert human data to AI labs, Mercor, went from about a billion to two billion dollars a year in run-rate in four months this year. Robotics companies already spend over $100 million a year buying real-world data, and Figure alone has committed more than a billion to data and compute. Each stage only starts once the one before it works with paying customers.

IF ASKED: Mercor's figures are gross (it pays 60-70% to its contractors) and come from the CEO and press reports, not audited numbers; the Dec 2025 bar is a Sacra estimate. The $100M+ is Micro1's CEO's estimate (MIT Technology Review). Figure's $1B covers data and compute together, by Figure's own statement. Grand View's forecast covers all AI training datasets, not just robotics. We haven't talked to any robot company yet, and we never assume we own customer footage: shared or licensed use needs a separate opt-in (appendix ${ref(aDataRights)}). Revenue targets per stage: appendix ${ref(aLongGame)}.`);
}

// ---------- 14 · Ask ----------
function sAsk() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText("Ask", { placeholder: "eyebrow" });
  s.addText([{ text: "$10k", options: { color: C.accent2 } }, { text: " gets us to the first paid pilot" }], { placeholder: "title" });
  const funds = [
    [3000, "Model training", "GPU time to retrain the step tracker, event detector and local checker on real maintenance footage"],
    [2500, "Devices + capture", "Supported glasses and capture gear to run Praxis end to end at a real site"],
    [2000, "Maintenance data", "Pay techs and trade-school students to record and label ~80 hours of real work, with consent"],
    [1500, "Pilot inference", "About 1,400 coached hours at today's measured cost"],
    [1000, "Company + legal", "Formation and the contracts a paid pilot needs"],
  ];
  const fills = [C.accent1, "16191B", "3C4347", "5E676C", "9AA3A7"];
  let fx = 0.5;
  funds.forEach(([amt], i) => {
    const w = 12.33 * amt / 10000;
    rect(s, fx, 1.75, w - 0.04, 0.36, fills[i], "funds-bar");
    fx += w;
  });
  const cw = 12.33 / 5;
  funds.forEach(([amt, name, why], i) => {
    const x = 0.5 + i * cw;
    tb(s, `$${amt.toLocaleString("en-US")}`, { x, y: 2.4, w: cw - 0.2, h: 0.55, fontFace: HEAD, fontSize: 30, color: i === 0 ? C.accent2 : C.text1 });
    tb(s, name, { x, y: 3.0, w: cw - 0.2, h: 0.35, fontFace: SEMI, fontSize: 15 });
    tb(s, why, { x, y: 3.38, w: cw - 0.3, h: 1.1, fontSize: 12.5, color: BODY });
  });
  const by = 4.75;
  s.addShape(pres.ShapeType.roundRect, { x: 0.5, y: by, w: 12.33, h: 1.85, rectRadius: 0.05, fill: { color: C.text1 }, line: { type: "none" }, objectName: "panel-april" });
  tb(s, "By April", { x: 0.85, y: by + 0.25, w: 3, h: 0.35, fontFace: SEMI, fontSize: 15, color: C.accent1 });
  ["Models retrained on real maintenance footage", "Praxis running end to end on real glasses at a real site", "A first paid pilot, with the success metric agreed before launch"].forEach((t, i) => {
    const x = 0.85 + i * 4.0;
    tb(s, t, { x, y: by + 0.75, w: 3.6, h: 0.85, fontFace: SEMI, fontSize: 17, color: C.background2 });
  });
  footer(s, 0, "$10,000 over six months · same amounts as the application · data: ~$25/h contributor rate (estimate) · inference: $1.08 per coached hour, measured");
  s.addNotes("SAY (35 s): The ask is $10,000. $3,000 of GPU time retrains the three models we own on real maintenance footage. $2,500 buys supported glasses and capture gear so Praxis runs end to end at a real site. $2,000 pays technicians and trade-school students, with consent, to record and label about 80 hours of real maintenance work. $1,500 covers pilot inference, about 1,400 coached hours at today's cost. And $1,000 is formation and the contracts a paid pilot needs. By April: models retrained on real maintenance footage, Praxis running on real glasses at a real site, and a first paid pilot with the success metric agreed before launch. Thank you.\n\nIF ASKED: 80 hours at about $25 an hour is a contributor-rate estimate, not a quote. 1,400 hours at $1.08 per coached hour is measured on public video, not yet on glasses; about 30 trainee-months at 2 hours a day. The pilot metric we'd propose: days until a new tech does a procedure alone.");
}

// ================================================================== APPENDIX

const appx = (_label, title) => {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText(eb(""), { placeholder: "eyebrow" });
  s.addText(title, { placeholder: "title" });
  return s;
};

const Q = (v) => (v * 13.333) / 100;

// ---------- Full architecture (the v2.17 engine slide, now in the appendix) ----------
function aArchitecture() {
  const s = pres.addSlide({ masterName: "Praxis Dark Grid", sectionTitle: "Story" });
  tb(s, eb("HOW IT WORKS · ENGINE v0"), { x: Q(2.9), y: Q(3.1), w: Q(40), h: Q(1.6), fontFace: LABEL, fontSize: 10, charSpacing: 2, color: C.accent6, objectName: "eyebrow" });
  s.addText([
    { text: "Full architecture. " },
    { text: "Orange runs on every frame; the bottom row only when something happens.", options: { color: "9AA3A7" } },
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
  abox("verifier", "rented", 640, 690, 380, 110, "Verifier", ["fast: Jev · 151 ms", "hard cases: Claude Opus 5.5 · 3.8 s"], 10.5);
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
  s.addNotes("Walk it left to right along the orange path, which is what happens on every frame, on the device, in about 50 ms: open models turn the frame into features, our detector and recognizer feed our state tracker, and the policy decides whether the coach says anything. Below, in the dark, is the only rented part: on 14% of frames the tracker asks a verifier one typed question (Jev in 151 ms, Claude Opus 5.5 for hard cases). We calibrate the answer and feed it back. With customer permission, session records train our local student, which already handles routine checks. Swapping the rented model is a one-line config change. The four boxes tagged TRAINED learn from labeled recordings; they are what the data and GPU money improves.");
}

// ---------- How far along (1/2): built, with real screenshots ----------
function sBuilt() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText(eb(""), { placeholder: "eyebrow" });
  s.addText("Company backend: upload, compile, approve", { placeholder: "title" });
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
  cap(3, L, ly + 2.32, LW, "Coach through smart glasses", "Live tracking and voice control. Meta and Viture adapters are built, not yet tested on a device.");
  shot("backend-procedure.png", R, 2.2, RW, 2320 / 1310);
  footer(s, 0, "Screenshots of the Praxis company backend · Hydro Plant demo: public Reclamation FIST manuals · ENIGMA-51 repair procedures");
  s.addNotes("This is the product a company actually touches, running today. One: a manager uploads the manuals they already have. Here it's three public Bureau of Reclamation maintenance manuals, 97 to 222 pages; each is parsed and indexed on the laptop in under 2 seconds, nothing is sent to a model, and it finds the likely procedures. Two: they pick a procedure and Praxis compiles it into coached steps for about 16 to 19 cents, with knowledge cards quoted from the manual and the page cited; the manager reviews, edits and approves before any technician sees it. Three: the technician is coached live through smart glasses, by voice or on the glasses' screen depending on the model. Say out loud: the Meta and Viture glasses connections are built but not yet tested on the devices; that's part of what the grant buys.");
}

// ---------- The long game in detail (the v2.17 core slide, now in the appendix) ----------
function aLongGame() {
  const s = pres.addSlide({ masterName: "Praxis Light" });
  s.addText(eb(""), { placeholder: "eyebrow" });
  s.addText("Revenue targets, certifications and robotics", { placeholder: "title" });
  const gap = 0.15, w = (12.33 - 3 * gap) / 4, ys = [2.95, 2.68, 2.41, 2.14];
  // each step: the move, why customers stay (or what it adds), then the revenue target
  const steps = [
    ["NOW · 2027", "Coach new techs", "Paid pilots with maintenance teams. With permission, sessions can become labeled training data.", "Target: $0.3M · 10 teams"],
    ["NEXT · 2028", "Our own models", "Trained on our pilot footage, on the glasses. Cheaper to run and better at maintenance than rented models.", "$1.5M · 50 teams · 5×"],
    ["THEN · 2029", "Certifications through Praxis", "Partner with NCCER, NIMS and equipment makers so their hands-on tests run on Praxis. Certified techs bring us their next shop.", "$4.5M ARR · 150 teams · 3×"],
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
      [["A", "Train our own robot models on data customers opted in"], ["B", "Sell the data and our step checker to robot labs"]].forEach(([t, b], j) => {
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
  footer(s, 0, "Revenue: targets, not forecasts; triple-triple-double pace after year 2 · Mercor: The Information, Dealroom (Jun 2026) · Micro1 CEO estimate · Grand View Research · NCCER, NIMS, HSPA, FOA and OSHA (29 CFR 1910.178(l)) requirements, checked Oct 2026");
  s.addNotes("Each step has paying demand today and builds the asset the next step needs. Revenue targets, not forecasts, on the pace investors expect: the median Series A in 2025 had about $3.3M ARR growing 2-3x a year, and the top-decile path is triple, triple, double, double, double. Same math as the market slide, about 25 new techs a team at $1,200 of license time each, plus records. 2027: 10 teams from paid pilots, about $0.3M. 2028: our own models. Within a year of the first pilots we train our own step and checking models on the pilot footage, running on the glasses, so most rented model calls go away: cheaper to run, and better at maintenance than a general model. 50 teams, about $1.5M (5x). 2029: certifications through Praxis. The license follows the new tech being coached, but the record follows the employee: every procedure they've done, verified step by step. These are the trades' version of a Microsoft Office certificate. We don't issue licenses; we partner with the bodies that already certify techs and run the hands-on part of their tests, which today needs a person watching: NCCER performance verifications need an NCCER-certified evaluator; NIMS maintenance credentials need a supervised hands-on record; HSPA's sterile processing certification (CRCST) needs 400 hands-on hours signed off by a manager; the Fiber Optic Association's CFOT has instructors verify lab skills; OSHA makes employers evaluate every forklift operator's performance at least every three years. Why it's a moat: certified techs carry the credential to their next job, the way Cisco and AWS certifications spread Cisco and AWS, and once a company's training and compliance history lives in Praxis, leaving means losing it. Be straight if asked: no partner conversations yet, and it comes after our own models, because a certificate is only worth the checking behind it. Then the same engine goes into new trades: field service, assembly lines, aviation maintenance. 150 teams, about $4.5M ARR (3x), the year-3 goal on the market slide. 2030-31: about $13M then $30M ARR, still under 2% of the $1.8B first market, before any robotics revenue. With customer permission, sessions are first-person video of skilled work, lined up to the procedure, with verified steps, real mistakes and the fixes that worked. We never assume we own customer video. Then two paths to robots: A, train our own robot models on that data; or B, sell the data and our 'did this step succeed?' checker to robot labs. Labs already pay: Mercor's run-rate selling expert data to AI labs passed $2B in June 2026, double what it was four months earlier (gross, reported by The Information); Micro1's CEO estimates robotics companies spend over $100M a year on real-world data; Figure says it has paid $15M for human video; Grand View Research sizes the AI training-data market at $8.6B by 2030, growing about 22% a year. Raw footage is becoming a commodity; skilled, verified, procedure-aligned footage isn't. Gates, not dates: each step needs the last one's metric hit first.");
}

// ---------- Learning curves ----------
function aCurves() {
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Appendix" });
  s.addText(eb(""), { placeholder: "eyebrow" });
  s.addText("Learning curves: step models and the local student", { placeholder: "title" });
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
  s.addNotes("We retrained our learned layers on growing slices of the training data and scored them only on recordings they never saw, so this isn't memorization. Left: the 3 procedures with 9 training recordings, held-out step accuracy. Right: the local student model on the same 469 held-out checks as the headline result. Steady gains per doubling of data, not 'exponential'. If asked for counts: up to 9 recordings per procedure, 30 recordings for the student. With customer permission, pilot sessions can add training data. The engine we evaluated used only 3 recordings per procedure, so there's headroom we haven't used yet (not re-measured end to end).");
}

// ---------- Why not consumers ----------
function sConsumers() {
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Market" });
  s.addText(eb("THE OBVIOUS QUESTION"), { placeholder: "eyebrow" });
  s.addText("Why we don't start with consumers", { placeholder: "title" });
  hero(s, G2.x[0], 2.75, G2.w, "$3.6B", "what Autodesk agreed to pay for MaintainX, an app that puts maintenance procedures on a phone.", { size: 64, capSize: 18 });
  hero(s, G2.x[1], 2.75, G2.w, "$99 → $25", "what Frontdoor's expert video help for homeowners fell to, per year, from 2023 to 2024.", { size: 64, capSize: 18 });
  line(s, 0.5, 5.45, 12.83, 5.45, { color: C.accent6, width: 0.75, name: "consumer-rule" });
  tb(s, [{ text: "The same checklist runs on every machine, every month. ", options: { fontFace: SEMI } }, { text: "Home tasks don't repeat, and the platforms give consumer help away free. Consumers come last." }], { x: 0.5, y: 5.6, w: 12.33, h: 0.9, fontSize: 17 });
  footer(s, 9, "Autodesk–MaintainX release (28 May 2026) · Frontdoor pricing 2023–2024");
  s.addNotes("Home tasks happen a few times a year, and Meta, Google and Apple will give consumer help away free. Consumers come last, once glasses are everywhere and our models run on the device. This is a choice about order, not size. In maintenance someone signs a budget, the same procedure repeats so the data compounds, ROI shows up in a 30-day pilot. Consumer tasks are a long tail; on open-ended tasks our system is weakest (it named 0 of 7 unseen recipes from video alone). Consumers return in the last phase of the vision.");
}

function aTrain() {
  const s = appx("", "What we train and what we rent");
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
  s.addNotes("If asked what we train: the event detector is a small causal temporal convolutional network on frozen video features that predicts step boundaries. The task recognizer is a linear probe over frozen features plus zero-shot text matching. The state tracker is a hidden semi-Markov model over the procedure's task graph, with duration priors and per-procedure step probes learned from training recordings. The local checker is a student distilled from the frontier verifier; it agrees with it on 69% of held-out checks, runs in 0.03 ms on a laptop CPU, and removes 34% of frontier calls. Perception is frozen open models (SigLIP2, V-JEPA 2, MediaPipe hands). The verifier is rented: Jev as the fast tier, Claude Opus 5.5 for hard cases. Next in-house steps: fine-tune a small open vision-language model on our logged verifier calls so mistakes and fine checks run in-house, and distill a smaller video backbone for on-device use. Why a big lab won't: they could build the parts, but their business is one general model for everyone. Coaching is a tracking problem, not a seeing problem: the value is the state around the model and the procedure-aligned data, plus the enterprise work of each shop's manuals, records and pilots.");
}

// ---------- Under the hood: the engineer cut of the live session ----------
function aUnderHood() {
  const s = appx("", "Live session, engineer view");
  video(s, "repair_demo_engineer", 0.5, 1.95, 8.6);
  const x = 9.4, w = 3.43;
  tb(s, runs([
    ["State tracker. ", "Its belief over the 19 steps, the time on the current step, and whether the tech looks like a novice."],
    ["Model calls. ", "Jev answers in 150 ms (median, 130 calls). Opus 5.5 double-checks 14 moments, about 4 s each."],
    ["Timeline. ", "The event detector, both model tiers, the tracked step and every decision to speak or stay quiet."],
    ["Cost. ", "$0.17 for this whole 16:40 run (about $0.60 an hour), with 0 errors. Across the evaluation, about $1 per coached hour."],
  ], 12), { x, y: 1.95, w, h: 4.8, fontSize: 13.5, color: BODY, objectName: "hood-legend" });
  footer(s, TOTAL, "Praxis Studio live session on ENIGMA-51 video 141 · latencies from the session log");
  s.addNotes("The same 49 seconds as the live slide, with the engine underneath. Right: the state tracker's belief over the 19 steps, and below it each model call with its real latency. Bottom: a scrolling timeline of the event detector, the fast tier (Jev), the Opus 5.5 escalations, the step it thinks you're on, and the policy's decisions. Two moments to point at. At 0:26 the fast model flags a missed button with 0.84 confidence; Opus 5.5 says the step is still in progress, so no alert goes out (both buttons are lit in the footage). At 2:52 the fast model guesses the wrong cause and Opus 5.5 reads the display at 215 °C. That alert lands 6 seconds after the checked frame, and cutting that escalation latency is next.");
}

function aMarketMath() {
  const s = appx("", "Market sizing math");
  const R = (a) => a.map((t, i) => ({ text: t, options: i === 0 ? { fontFace: SEMI } : {} }));
  s.addTable([
    [TH(""), TH("WHO (BLS)"), TH("MATH"), TH("PER YEAR")],
    R(["TAM", "Installation, maintenance + repair 6,086,190 · electricians 757,220 · production 8,565,760 = 15.4M", "15.4M × $50 a month × 12", "≈ $9.2B"]),
    R(["SAM", "General maintenance + repair, machinery mechanics + millwrights, HVAC = 2.47M jobs, ~255k openings a year", "255k × $200 × 6 months = $306M; 2.47M × $50 × 12 = $1.48B", "≈ $1.8B"]),
    R(["SOM (year 3)", "1.5% of new maintenance techs ≈ 3,750 new techs a year, ~150 mid-size teams", "3,750 × $200 × 6 months", "≈ $4.5M ARR"]),
  ], { ...tableOpts([1.1, 5.3, 4.33, 1.6]), rowH: 0.7, objectName: "table-market" });
  tb(s, runs([
    ["Prices are hypotheses. ", "$200 a month for coaching is a hypothesis; Tulip lists ~$100/month (Essentials) and ~$250/month (Professional) per interface, which anchors it but doesn't prove willingness to pay. $50 a month for every-worker records is a guess"],
    ["Openings ", "include people changing jobs, so new-tech counts are an upper bound"],
    ["Not counted: ", "other countries, field service outside these groups, aviation maintenance, and the robotics upside"],
  ], 6), { x: 0.5, y: 5.3, w: 12.33, h: 1.3, fontSize: 13 });
  footer(s, TOTAL, "BLS OEWS national tables, May 2025 · BLS Occupational Outlook Handbook");
}

function aUnitEcon() {
  const s = appx("", "Unit economics and pricing risk");
  const R = (a) => a.map((t) => ({ text: t }));
  s.addTable([
    [TH("DESIGN"), TH("$ / VIDEO-MIN"), TH("$ / TRAINEE-MONTH, 2 H/DAY"), TH("MARGIN AT $200")],
    R(["Frontier model every 5 s", "$0.085", "about $214", "negative"]),
    R(["Praxis engine today", "$0.018", "about $45", "about 77%"]),
    R(["Praxis + our local model", "$0.008", "about $20", "about 90%"]),
  ], { ...tableOpts([2.9, 1.6, 2.4, 1.5], 8.4), objectName: "table-unit-economics" });
  tb(s, "Labeled assumptions, not sourced: if a senior tech spends 50% of their time on a new hire for 3 months, that's about $11,400 of their time; at 25% for 12 months, about $22,800. We're asking maintenance managers for their real split. Per new tech over six months (~250 coached hours): ~$270 to serve today, ~$120 with our local model, against $1,200 of revenue.", { x: 0.5, y: 4.55, w: 8.4, h: 1.2, fontSize: 14, color: BODY });
  darkPanel(s, 9.25, 2.2, 3.58, 2.75, "THE RISK", "All-shift use (8 h/day) makes a flat $200 license $1.19 an hour against our $1.08 cost: about a 9% margin. With the local model, about 60%. So price by coached hours or tiers, and move routine checks to the local model first.", 14);
  footer(s, TOTAL, "2,520 coached minutes a month = 2 h/day × 21 days · senior-tech cost: BLS");
}

function aTraining() {
  const s = appx("", "Dataset, splits and denominators");
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

// ---------- Benchmark: the raw numbers and how they were measured ----------
function aBenchmark() {
  const s = appx("", "Benchmark results and method");
  const R = (a, ours) => a.map((t, i) => ({ text: t, options: i === 0 ? { fontFace: SEMI, color: ours ? C.accent2 : C.text1 } : {} }));
  s.addTable([
    [TH("SYSTEM (SAME 48 HELD-OUT CLIPS, TASK GIVEN)"), TH("STEP TRACKING"), TH("FRONTIER (OPUS 5.5) CALLS"), TH("COST / VIDEO-MIN")],
    R(["Baseline: Claude Opus 5.5 every 5 s, no task state", "48%", "2,817", "$0.085"]),
    R(["Praxis: fast tier (Jev) + Opus 5.5 escalation", "54%", "351  (+2,679 fast-tier)", "$0.018"], true),
    R(["Praxis, fast tier only (no escalation)", "53%", "0", "$0.001"]),
    R(["Praxis + our local student on routine checks", "52%", "not broken out", "$0.008"]),
    R(["Our local layers only, no model calls", "41%  (49% retrained)", "0", "$0"]),
  ], { ...tableOpts([5.1, 2.9, 2.5, 1.83]), rowH: 0.42, fontSize: 12.5, objectName: "table-benchmark" });
  tb(s, runs([
    ["Data. ", "48 held-out first-person clips (235 min) from CaptainCook4D, a public procedure dataset (cooking): 8 procedure types, 302 annotated steps, 170 annotated mistakes. Labels are the dataset's. Train and test never overlap."],
    ["Metric. ", "Step tracking = share of frames where the tracked step matches the label. One run per system; no confidence intervals yet."],
    ["Mistakes (strict, judge-verified). ", "Praxis alerts named a real annotated error 4 of 17 times; the baseline 2 of 3. Both catch a small share of the 170."],
    ["Degraded views (60 checks per condition). ", "Praxis asked for a better view on 77–98% and was never confidently wrong; the baseline was wrong at ≥50% confidence on 12–73%."],
    ["Repair Q&A (ENIGMA-51). ", "11 of 15 technician questions answered correctly from the uploaded procedures, 2 partly, 2 wrong, blind-judged."],
  ], 4), { x: 0.5, y: 5.0, w: 12.33, h: 1.8, fontSize: 11, color: BODY });
  footer(s, TOTAL, "results/runs/*.json · results/metrics.json · results/l5/visual_uncertainty.json · results/l6/mistake_semantic_*.json · docs/CLAIMS.md");
  s.addNotes("The raw numbers behind the 'same model, better system' slide. Like-for-like: the same frontier model on the same frames. Lead with relative gains (+13% relative accuracy, 1/5 the cost, 8x fewer frontier calls); give these absolutes only if asked. Every test is on held-out recordings, and some procedure types were never seen in training. The dataset is cooking because labeled first-person maintenance video doesn't exist off the shelf; procedures are procedures, but say plainly it's not maintenance yet. On ENIGMA-51 repair footage with uploaded written procedures, the instruction named the right step 45% of the time and the right or an adjacent step 74%, vs 36% and 45% for a general vision assistant given the same procedure.");
}

// ---------- Competitors, in full ----------
function aCompetitors() {
  const s = appx("", "Competitors in detail");
  const R = (a, close) => a.map((t, i) => ({ text: t, options: i === 0 ? { fontFace: SEMI, color: close ? C.accent2 : C.text1 } : {} }));
  s.addTable([
    [TH("APPROACH"), TH("EXAMPLES"), TH("WHAT IT DOES"), TH("HOW WE DIFFER")],
    R(["Shadowing", "A senior tech", "The real teacher today", "About $44 an hour of senior time, one new tech at a time"]),
    R(["Manuals + videos", "PDFs, binders, YouTube", "Explain what should happen", "Can't see what the tech is doing"]),
    R(["Procedure software", "MaintainX, Tulip, Augmentir, Dozuki", "Steps on a screen, sign-offs, photos; some compile instructions", "A checkbox isn't proof. Natural integration partners"]),
    R(["Fixed cameras", "Retrocausal, Invisible AI, Tulip Vision", "Watch one station; record, label and train per station", "Ahead of us on live mistake detection at a station; can't follow a tech around a machine"]),
    R(["General assistants", "Meta AI, Gemini Live", "Free help about what's in view", "No procedure, step state, calibration or records"]),
    R(["First-person, high-touch", "Strivr", "Per-customer capture and model (vendor docs); early access", "No published accuracy; we start from the manuals a shop has"]),
    R(["First-person, hardware-led", "Viture Helix + NVIDIA XR AI", "Real-time SOP coaching on its own safety glasses; ships Q1 2027, from $600", "Closest. How SOPs get in and accuracy aren't published. We'd rather run on it"], true),
    R(["Toolkits", "NVIDIA XR AI, Meta's toolkit, Android XR", "Plumbing for apps", "Complements: what we build on"]),
  ], { ...tableOpts([2.25, 2.85, 3.6, 3.63]), rowH: 0.5, fontSize: 11.5, objectName: "table-competitors" });
  footer(s, TOTAL, "Public product pages and docs, checked 17 Oct 2026 · Viture Helix release, 16 Jun 2026 · docs/COMPETITORS.md, docs/POSITIONING.md");
  s.addNotes("Don't claim nobody else is here. Tulip, Augmentir and Squint already compile instructions; Tulip is testing camera checks of whether a procedure was followed; Retrocausal tracks whole procedures on fixed cameras. Viture Helix is the closest direct competitor: first-person, real-time coaching on SOPs, built on NVIDIA's XR AI, from $600, ships Q1 2027, enterprise pilots invite-only, safety certification pending. It has voice input and a safety form factor; we don't have published accuracy from them, and they haven't said how SOPs get in, so don't say they need filming. If Helix becomes the standard safety glasses, we want Praxis running on it; whether it accepts outside apps isn't documented. Big-company exits from this niche, if asked: Microsoft is retiring Dynamics 365 Guides (Dec 31) and PTC retired Vuforia Chalk in 2025.");
}

// ---------- Hardware questions ----------
function aHardwareQA() {
  const s = appx("", "Glasses hardware and adapters");
  const R = (a) => a.map((t, i) => ({ text: t, options: i === 0 ? { fontFace: SEMI } : {} }));
  s.addTable([
    [TH("QUESTION"), TH("ANSWER")],
    R(["Why not build our own glasses?", "Meta, Google, Samsung and Viture + NVIDIA are solving optics, batteries, cameras, radios, distribution and SDKs at a scale we can't match. Our value starts after the camera: procedures, step state, verification, when to speak, records."]),
    R(["What if Meta closes access?", "The engine doesn't care where frames come from: each device is a thin adapter over one camera-and-audio interface. Meta is one of several families (Android XR, NVIDIA XR AI glasses, Android headsets)."]),
    R(["How do glasses and licenses work?", "Glasses are shared site equipment: a site needs enough pairs for the techs coached at the same time, not one per employee. Software is one license per active trainee, and it moves to the next hire. We don't resell hardware."]),
  ], { ...tableOpts([3.0, 9.33]), rowH: 0.78, fontSize: 12.5, objectName: "table-hardware" });
  const y = 5.45;
  line(s, 0.5, y, 12.83, y, { color: C.text1, width: 1.5, name: "status-rule" });
  mono(s, "Adapter status, Oct 20", { x: 0.5, y: y + 0.13, w: 5, h: 0.26, fontSize: 10.5, color: C.text1 });
  [
    ["Camera / upload path", "tested: runs live in real time on recorded video (local layers ~50 ms a frame)", C.accent3],
    ["Meta adapter (toolkit 1.0)", "built, not device-tested", C.accent6],
    ["Viture / NVIDIA XR AI adapter", "built, not device-tested", C.accent6],
    ["Android XR", "planned", "C2C8C5"],
  ].forEach(([k, b, col], i) => {
    const x = 0.5 + i * 3.1, yy = y + 0.5;
    s.addShape(pres.ShapeType.ellipse, { x, y: yy + 0.05, w: 0.16, h: 0.16, fill: { color: col }, line: { type: "none" }, objectName: "status-dot" });
    tb(s, [{ text: k, options: { fontFace: SEMI, breakLine: true } }, { text: b, options: { color: BODY } }], { x: x + 0.28, y: yy, w: 2.75, h: 0.9, fontSize: 12 });
  });
  footer(s, TOTAL, "docs/GLASSES.md (Meta toolkit docs, read 2026-10-17) · docs/PITCH_QA.md platform readiness · Built; not yet tested on the devices");
  s.addNotes("Say plainly: the glasses adapters are built but have not been tested on a real device; that's what the $2,500 devices line buys. Meta's toolkit: our phone app registers with the Meta AI app, the wearer grants camera permission, no code runs on the glasses, and public app-store publishing isn't open yet (test users get builds through Meta's release channels, fine for a pilot). Glass-to-coach latency is the biggest unknown. For loud plants, a hearing-protection headset. If Meta tightens access, we still have Android XR, NVIDIA XR AI glasses and Android headsets such as RealWear.");
}

// ---------- Data rights and privacy ----------
function aDataRights() {
  const s = appx("", "Data rights and privacy");
  const R = (a) => a.map((t, i) => ({ text: t, options: i === 0 ? { fontFace: SEMI } : {} }));
  s.addTable([
    [TH("QUESTION"), TH("DEFAULT ANSWER")],
    R(["Who owns the manuals and footage?", "The customer. Praxis gets a limited license to process them to provide the service."]),
    R(["Can Praxis train on proprietary company video?", "Only with contractual permission. Improving our shared models needs a separate, explicit opt-in. Without it, a customer's data stays isolated to that customer."]),
    R(["What leaves the site?", "The fast layers can run locally; only event keyframes go to a model (about 14% of frames in our evaluation). Keep as little as possible, for as short as possible."]),
    R(["Workers, unions, monitoring rules", "Coaching is for the worker; the employer gets records and aggregates. Face and badge blur is next. Each site's workplace, privacy and union rules come first."]),
  ], { ...tableOpts([3.6, 8.73]), rowH: 0.68, fontSize: 12.5, objectName: "table-data" });
  darkPanel(s, 0.5, 5.85, 12.33, 0.95, "IN SHORT", "We never assume we own customer video. Shared-model training happens only on data a customer has opted in.", 16);
  footer(s, TOTAL, "Proposed default contract terms; not yet reviewed by counsel");
  s.addNotes("If asked whether every session becomes training data: no. With customer permission, sessions can become labeled training data. The default: the customer owns raw footage and manuals; we get a limited license to process them to deliver the service; a separate opt-in covers improving shared models; non-opt-in data stays tenant-specific. The paid trade-school capture in the ask is consented from the start. These are proposed terms; counsel reviews them with the first pilot contract (the $1,000 company + legal line). Blur is not built yet.");
}

// ---------- Safety model ----------
function aSafety() {
  const s = appx("", "Safety");
  const R = (a) => a.map((t, i) => ({ text: t, options: i === 0 ? { fontFace: SEMI } : {} }));
  s.addTable([
    [TH("SITUATION"), TH("WHAT PRAXIS DOES")],
    R(["Safety-critical steps (lockout/tagout)", "They stay the tech's job. Praxis prompts and records them, and never approves them."]),
    R(["A procedure before anyone uses it", "A manager reviews and approves every compiled procedure before a tech sees it, with each card quoted from the manual."]),
    R(["It can't see well enough", "It asks for a better view instead of guessing: 77–98% of blurred or blocked checks, never confidently wrong on them."]),
    R(["It isn't sure", "Calibrated confidence decides whether to speak; below the bar it stays quiet or asks. Calibration error fell from 0.22 to 0.02 on held-out checks."]),
    R(["Mistake alerts", "Our weakest number today: 4 of 17 alerts named a real annotated error. Every pilot measures it before we claim more."]),
  ], { ...tableOpts([3.6, 8.73]), rowH: 0.66, fontSize: 13, objectName: "table-safety" });
  footer(s, TOTAL, "results/l5/visual_uncertainty.json · results/l5/calibration.json · results/l6/mistake_semantic_fused_oracle.json · company backend approval flow");
  s.addNotes("In the live demo the overshoot alert came about 6 seconds late because it waited on the frontier model; cutting escalation latency is on the list. Praxis is a coach, not a safety system of record: it never replaces lockout/tagout sign-off. Strictly scored, Praxis raised about one alert every 18 minutes of video that didn't name an annotated error (some may be real but unannotated).");
}

// ---------- Risks ----------
function aRisks() {
  const s = appx("", "Risks");
  const R = (a) => a.map((t, i) => ({ text: t, options: i === 0 ? { fontFace: SEMI } : {} }));
  s.addTable([
    [TH("RISK"), TH("WHAT WE DO")],
    R(["Meta or Google ships a general coach", "It answers about what's in view. We go deep in maintenance: procedures, step state, records, pilots on site, and we run on their glasses"]),
    R(["Viture + NVIDIA win the safety-glasses slot", "Run on Helix via NVIDIA's open XR AI library or its app path, rather than fight it"]),
    R(["Glasses don't work end to end yet", `Adapters are built but untested on a device; testing at a real site is the $2,500 line (appendix ${ref(aHardwareQA)})`]),
    R(["Mistake detection is weak (4 of 17)", "Locked procedures, maintenance data and the tech saying \"done\" all add evidence. Measured in every pilot"]),
    R(["Evaluated on cooking, not maintenance", "That's why the grant buys ~80 hours of consented maintenance footage first"]),
    R(["Depending on model vendors", "The verifier is swappable in one config line, and our local student already handles routine checks"]),
    R(["Solo founder", "The grant tests demand before hiring. First hires come after the first pilot"]),
  ], { ...tableOpts([3.8, 8.53]), rowH: 0.52, fontSize: 12, objectName: "table-risks" });
  footer(s, TOTAL, "Praxis evaluation results and planning notes");
}

// ---------- Founder details ----------
function aFounder() {
  const s = appx("", "Founder background");
  tb(s, runs([
    ["LipTrac (2024–26). ", "Wearable real-time visual speech recognition for assistive transcription. Conv3D + bidirectional GRU on 60,000+ video frames, spatiotemporal feature extraction and sequence decoding, evaluated with 12 participants. Provisional patent US 63/812,158."],
    ["OCTOPAS (2023–25). ", "End-to-end autonomous oil-spill remediation: drone and marine robotics, computer vision and engineered sorbents. 217.9% better collection performance than conventional methods. Published in Florida Water Resources Journal. Provisional patent US 63/813,616."],
    ["Competitive robotics. ", "FTC team captain (2022–26), World Championship qualifier, Control Awards for autonomous software. PID control, Kalman filtering, sensor fusion, OpenCV detection, custom path planning. Built FTC Coach (25,000+ users in 50+ countries) and FTC Elo (3,000+ recurring users)."],
    ["Startups and growth. ", "Qurios Ventures co-founder and CMO: MRR from under $1k to $50k, a 14,000+ member community, acquired by Crimson Education for $1.3M. Claisen Health co-founder and CMO: 13-person growth team, $200k angel raise. Acely AI (YC W18): $300k attributable revenue. International Research Olympiad: 43 to 89 countries, $50k+ in sponsorships."],
    ["Praxis (Oct 2026). ", "Built solo: a tracking engine with trained event and step models, a 48-clip evaluation harness with a stateless baseline, a company backend that indexes manuals and compiles procedures, and a live app with spoken coaching."],
    ["Education and awards. ", "Harvard College, Applied Mathematics + Computer Science (expected 2030). Harvard SPARK Fellow; Actuarial Foundation STEM Stars Scholar."],
  ], 9), { x: 0.5, y: 1.95, w: 12.33, h: 4.85, fontSize: 13.5, color: BODY });
  footer(s, TOTAL, "Monish Saravana resume (Oct 2026) · Startups @ Harvard application");
  s.addNotes("SCOPE is not in the resume or the application; add it here once Monish supplies verified facts. The application says seven years of competitive robotics; the resume lists FTC from Sep 2022 to May 2026.");
}

// ---------- Appendix divider: two columns, so the whole Q&A index fits ----------
function sAppendixDivider() {
  const s = pres.addSlide({ masterName: "Praxis Dark Grid" });
  s.addText("For questions", { placeholder: "eyebrow" });
  s.addText("Appendix", { placeholder: "title" });
  const items = APPENDIX.map(([, label]) => label);
  const half = Math.ceil(items.length / 2), rh = 0.5, y0 = 0.85;
  items.forEach((t, i) => {
    const col = i < half ? 0 : 1, row = i % half;
    const x = 5.0 + col * 4.1, y = y0 + row * rh;
    tb(s, `A${i + 1}`, { x, y, w: 0.55, h: rh, fontFace: SEMI, fontSize: 12, color: C.accent1, valign: "middle" });
    tb(s, t, { x: x + 0.55, y, w: 3.4, h: rh, fontSize: 13, color: C.background2, valign: "middle" });
    if (row < half - 1 && i < items.length - 1) line(s, x, y + rh, x + 3.85, y + rh, { color: "3A4044", width: 0.75, name: "appx-rule" });
  });
}

// ================================================================== ORDER
const CORE = [
  ["Story", [sCover, sProblem, sProduct]],
  ["Built", [sExists, sLive, sEngine, sResults]],
  ["Market", [sWhyNow, sGlassesWar, sMarket, sGTM]],
  ["Team", [sFounder]],
  ["Plan", [sVision, sAsk]],
];
const APPENDIX = [
  [aBenchmark, "Benchmark results and method"], [aTraining, "Dataset, splits and denominators"], [aCurves, "Learning curves"],
  [aArchitecture, "Architecture with numbers"], [aUnderHood, "Live session, engineer view"], [sBuilt, "Company backend"],
  [aTrain, "What we train and what we rent"], [aCompetitors, "Competitors in detail"], [aMarketMath, "Market sizing math"],
  [aUnitEcon, "Unit economics and pricing risk"], [aHardwareQA, "Glasses hardware and adapters"], [aDataRights, "Data rights and privacy"],
  [aSafety, "Safety"], [aRisks, "Risks"], [sConsumers, "Why we don't start with consumers"],
  [aFounder, "Founder background"], [aLongGame, "Revenue targets, certifications, robotics"],
];
for (const [title, fns] of CORE) {
  pres.addSection({ title });
  SECTION = title;
  for (const f of fns) { CUR++; f(); }
}
if (CUR !== TOTAL) throw new Error(`TOTAL is ${TOTAL} but the core deck has ${CUR} slides`);
if (!SHARE) {
  pres.addSection({ title: "Appendix" });
  SECTION = "Appendix";
  sAppendixDivider();
  APPENDIX.forEach(([f], i) => { APX = `A${i + 1}`; f(); });
}

// the shared copy keeps sources but drops the speaker scripts and any pointer to the appendix it doesn't have
const shareSrc = (src) => src.replace(/\s*\(appendix A\d+[^)]*\)/g, "").split(" · ").filter((x) => !/appendix/i.test(x)).join(" · ");
ALL_SLIDES.forEach((sl) => {
  const t = SHARE ? (sl._src ? `Sources: ${shareSrc(sl._src)}` : "") : [sl._notes, sl._src && `Sources: ${sl._src}`].filter(Boolean).join("\n\n");
  if (t) sl._rawNotes(t);
});

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();

