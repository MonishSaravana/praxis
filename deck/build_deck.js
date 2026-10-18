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
const TOTAL = 17; // main-deck slides; appendix slides carry the full mark

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
const tb = (slide, t, o) => slide.addText(t, { margin: 0, valign: "top", isTextBox: true, fontSize: 15, color: C.text1, ...o });
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

// ================================================================== MAIN DECK

// ---------- 1 · Cover ----------
pres.addSection({ title: "Cover" });
{
  const s = pres.addSlide({ masterName: "Praxis Photo", sectionTitle: "Cover" });
  photo(s, "photo-cover.jpg");
  s.addImage({ path: A("praxis-lockup-white.png"), x: 0.5, y: 0.55, h: 0.4, w: 0.4 * LOCKUP_RATIO, objectName: "logo" });
  s.addText("Instructions that can finally see how you're doing", { x: 0.5, y: 2.35, w: 5.6, h: 2.4, fontFace: HEAD, fontSize: 38, color: C.background2, valign: "middle", margin: 0, lineSpacingMultiple: 0.95, isTextBox: true, objectName: "cover-headline" });
  s.addText("STARTUPS @ HARVARD · 20 OCT 2026 · MONISH SARAVANA", { x: 0.5, y: 6.75, w: 6.5, h: 0.3, fontFace: MONO, fontSize: 10, charSpacing: 1, color: C.accent6, margin: 0, valign: "middle", isTextBox: true, objectName: "cover-meta" });
  const reg = [860, 640, 1180, 900];
  hudRegion(s, reg, HUD.green);
  hudPulse(s, 1010, 790, HUD.green);
  hudProgress(s, 4, 9, 1920 - 56 - 247);
  const chip = hudChip(s, "Seat the clamp past the hose bead", 624, { right: true });
  hudLeader(s, chip, reg, HUD.green);
  conceptTag(s);
  s.addNotes("Hi, I'm Monish. Praxis is an AI coach for physical work: it watches through a first-person camera, knows where you are in a procedure, checks your work and talks you through it. This is what a new maintenance technician sees: one short instruction, a small progress mark, and a green check when the step is done. The photo is stock with a mocked-up HUD; the engine behind it is real and I'll show the numbers.");
}

// ---------- 2 · Problem ----------
pres.addSection({ title: "Problem" });
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Problem" });
  s.addText("THE PROBLEM", { placeholder: "eyebrow" });
  s.addText(titleWithMark("A new maintenance technician takes ", "about a year", " to work alone"), { placeholder: "title" });
  const cols = [
    { x: 0.5, big: ">1 yr", cap: "of on-the-job training is typical for industrial machinery mechanics and maintenance workers." },
    { x: 6.92, big: "9–14 mo", cap: "before a new hire is profitable, in a survey of 35 aviation repair stations. Some took 24." },
  ];
  cols.forEach((c, i) => {
    line(s, c.x, 2.75, c.x + 5.91, 2.75, { color: C.text1, width: 1.5, name: `stat-rule-${i + 1}` });
    s.addText(c.big, { x: c.x, y: 2.95, w: 5.91, h: 1.0, fontFace: HEAD, fontSize: 54, color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: `stat-${i + 1}` });
    s.addText(c.cap, { x: c.x, y: 4.05, w: 5.4, h: 0.9, fontSize: 16, color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: `stat-${i + 1}-caption` });
  });
  plateCard(s, 0.5, 5.2, 12.33, 1.2, "problem-why");
  tb(s, [
    { text: "Manuals and videos can't see you. ", options: { fontFace: SEMI } },
    { text: "So the real teacher is a senior tech standing next to the new hire. That time costs about $44 an hour, and it isn't in anyone's training budget." },
  ], { x: 0.85, y: 5.2, w: 11.6, h: 1.2, fontSize: 16, valign: "middle", objectName: "problem-why-text" });
  footer(s, 2, "Sources: BLS Occupational Outlook Handbook · BLS Employer Costs for Employee Compensation · 2017 aviation repair-station survey");
  s.addNotes("BLS says on-the-job training for these jobs typically lasts more than a year. In a 2017 survey of 35 aviation repair stations, new hires took 9 to 14 months on average to become profitable, and some took 24. $44 an hour is the BLS median wage ($30.82) with benefits (wages are 70.2% of employer cost); senior techs cost more. Formal training budgets (about $1,254 per employee a year, ATD) leave out coaching and mentoring, which is most of how a technician learns. Sources: docs/POSITIONING.md [P8, P21, P22, P23].");
}

// ---------- 3–6 · Product on the job ----------
pres.addSection({ title: "Product" });
{
  const s = pres.addSlide({ masterName: "Praxis Photo", sectionTitle: "Product" });
  photo(s, "photo-step.jpg");
  const reg = [800, 300, 1260, 820];
  hudRegion(s, reg, HUD.orange);
  hudProgress(s, 3, 8);
  const chip = hudChip(s, "Loosen the four float-bowl screws a half turn each", 903);
  hudLeader(s, chip, reg, HUD.orange);
  conceptTag(s);
  s.addNotes("Step tracking. Praxis recognizes the job by itself (73% of held-out clips, median 40 seconds) and keeps a running belief about which step you're on. The screen stays quiet: a progress mark, one short instruction, and the part it's talking about.");
}
{
  const s = pres.addSlide({ masterName: "Praxis Photo", sectionTitle: "Product" });
  photo(s, "photo-verified.jpg");
  const reg = [470, 560, 860, 860];
  hudRegion(s, reg, HUD.green);
  hudPulse(s, 660, 740, HUD.green);
  hudProgress(s, 5, 11, 56, 56, 154);
  const chip = hudChip(s, "Rotate the crank to bring cylinder 3 to TDC", 770, { label: "STEP 5 VERIFIED · VALVE LASH SET", labelColor: HUD.green });
  hudLeader(s, chip, reg, HUD.green);
  conceptTag(s);
  s.addNotes("Verified. When the step is done, a green ring confirms it and the instruction moves on. No one has to tick a checklist.");
}
{
  const s = pres.addSlide({ masterName: "Praxis Photo", sectionTitle: "Product" });
  photo(s, "photo-mistake.jpg");
  const reg = [720, 160, 1160, 600];
  hudRegion(s, reg, HUD.red);
  hudProgress(s, 2, 7);
  const card = hudCard(s, "MISTAKE CAUGHT", HUD.red, HUD.red, "Lockout was skipped.", "Open and lock the feeder breaker, tag it, then test for zero voltage.", 1164, 660);
  hudLeader(s, card, reg, HUD.red);
  conceptTag(s);
  s.addNotes("Mistake caught. Praxis knows where you are in the procedure, so it can tell a step was skipped and say how to fix it. Out-of-order mistakes are the most common error type in our eval data, and you can only see them if you track state. Honest caveat if asked: mistake detection is our weakest number today (4 of 17 alerts named a real annotated error).");
}
{
  const s = pres.addSlide({ masterName: "Praxis Photo", sectionTitle: "Product" });
  photo(s, "photo-view.jpg");
  const reg = [330, 620, 780, 1010];
  hudRegion(s, reg, HUD.blue, true);
  hudProgress(s, 6, 12, 56, 56, 154);
  const card = hudCard(s, "NEED A BETTER VIEW", HUD.blue, "1D4ED8", "Can't see the bearing cap.", "Lean in over cylinder 2 and hold still for two seconds.", 1164, 56);
  hudLeader(s, card, reg, HUD.blue);
  conceptTag(s);
  s.addNotes("Needs a better view. When it isn't sure, it asks instead of guessing. On blurred or blocked views it asked for a better look 77-98% of the time and was never confidently wrong.");
}

// ---------- 7 · Divider ----------
pres.addSection({ title: "How it works" });
{
  const s = pres.addSlide({ masterName: "Praxis Dark Grid", sectionTitle: "How it works" });
  s.addText("02 · HOW IT WORKS", { placeholder: "eyebrow" });
  s.addText("A tracking problem, not a seeing problem", { placeholder: "title" });
  s.addText("Praxis keeps a running belief about where you are in the procedure, and speaks only when it's sure.", { placeholder: "body" });
  s.addImage({ path: MK(`prog-dark-7of${TOTAL}.png`), x: 13.333 - 1.2 - 5 * MARK_RATIO, y: 1.25, h: 5, w: 5 * MARK_RATIO, objectName: "progress-mark-large" });
  s.addNotes("Our conviction: coaching someone through physical work is a tracking problem, not a seeing problem. Most competitors either stream video to a big model and hope, or bolt a camera to one workstation. We keep a belief about where the person is, and only ask a big model when something happens.");
}

// ---------- 8 · Architecture (native diagram, from brand/deck) ----------
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "How it works" });
  s.addText("HOW PRAXIS WORKS · ENGINE v0", { placeholder: "eyebrow" });
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
  footer(s, 8, "Measured on 48 held-out first-person clips from a public dataset (CaptainCook4D) · results/RESULTS.md · docs/CLAIMS.md");
  s.addNotes("Walk it left to right. Open models on the device turn every frame into features. Our state tracker keeps a running belief about which step you're on, using a task graph we compiled from the manual. Only when something happens (a step ends, it's unsure, or you're stuck) does it ask a rented model one typed question: that's 14% of frames. We calibrate the answer and feed it back, and the policy decides whether to say anything. Every session becomes training data, and our local student already handles routine checks. If asked 'isn't this a wrapper?': with the same frontier model, our layers make it about 13% more accurate at a fifth of the cost, and swapping the rented model is a one-line config change.");
}

// ---------- 9 · Results (relative framing) ----------
{
  const s = pres.addSlide({ masterName: "Praxis Split", sectionTitle: "How it works" });
  s.addShape(pres.ShapeType.rect, { x: 0, y: 0, w: 7.2, h: 7.5, fill: { color: C.text1 }, line: { type: "none" }, objectName: "results-panel" });
  const labels = ["Model every 5 s", "Praxis", "Praxis + our local model"];
  s.addChart(pres.ChartType.bar, [{ name: "Relative step accuracy", labels, values: [100, 113, 109] }],
    { ...darkChart("Step accuracy · same frontier model on a timer = 100"), chartColors: ["4A5156", "FF5B14", "FF5B14"], x: 0.5, y: 0.7, w: 6.2, h: 2.7, valAxisMaxVal: 135, valAxisMinVal: 0, dataLabelFormatCode: "0", objectName: "chart-accuracy" });
  s.addChart(pres.ChartType.bar, [{ name: "Cost per video-minute", labels, values: [0.085, 0.018, 0.008] }],
    { ...darkChart("Cost per minute of video"), chartColors: ["4A5156", "FF5B14", "FF5B14"], x: 0.5, y: 3.9, w: 6.2, h: 2.7, valAxisMaxVal: 0.11, valAxisMinVal: 0, dataLabelFormatCode: '"$"0.000', objectName: "chart-cost" });
  s.addText("RESULTS", { placeholder: "eyebrow" });
  s.addText("Same frontier model. 13% more accurate at a fifth of the cost", { placeholder: "title" });
  const rows = [
    { y: 2.9, big: "+13%", vs: "accuracy", cap: "tracking the current step, versus the same model called every 5 seconds" },
    { y: 4.2, big: "4.6×", vs: "cheaper", cap: "$0.018 vs $0.085 per minute of video" },
    { y: 5.5, big: "11×", vs: "cheaper", cap: "with our distilled local model, and still 9% more accurate" },
  ];
  rows.forEach((r, i) => {
    line(s, 7.85, r.y, 12.83, r.y, { color: C.text1, width: 1.5, name: `result-rule-${i + 1}` });
    s.addText([
      { text: r.big, options: { fontFace: HEAD, fontSize: 30, color: i === 0 ? C.accent2 : C.text1 } },
      { text: "  " + r.vs, options: { fontFace: HEAD, fontSize: 16, color: C.text2 } },
    ], { x: 7.85, y: r.y + 0.08, w: 4.98, h: 0.55, margin: 0, valign: "middle", isTextBox: true, objectName: `result-${i + 1}` });
    s.addText(r.cap, { x: 7.85, y: r.y + 0.62, w: 4.98, h: 0.55, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: `result-${i + 1}-caption` });
  });
  footer(s, 9, "48 held-out clips · results/runs", 7.85);
  s.addNotes("Like-for-like: the same frontier model, the same frames. With our layers around it, it tracks the current step about 13% more accurately (54% vs 48% of frames) at about a fifth of the cost, because most checks never leave the device. With our distilled local model doing routine checks, it's 11x cheaper and still about 9% more accurate (52% vs 48%). The baseline calls the model every 5 seconds, not every frame. All measured on 48 held-out first-person clips from a public cooking dataset (CaptainCook4D), task given, one run per system. Say so if asked: procedures are procedures; maintenance footage is the first thing the grant funds.");
}

// ---------- 10 · Learning curves ----------
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "How it works" });
  s.addText("OUR OWN MODELS · LEARNING CURVES", { placeholder: "eyebrow" });
  s.addText(titleWithMark("Our own models already get better with ", "every recording"), { placeholder: "title" });
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
  mono(s, "TRAINED IN SECONDS ON A LAPTOP · TESTED ONLY ON RECORDINGS IT NEVER SAW · NEITHER CURVE HAS LEVELED OFF", { x: 0.5, y: 6.42, w: 12.33, h: 0.3, color: C.text1 });
  footer(s, 10, "Random subsets of public train-split recordings, 5 seeds per point · results/scaling/learning_curve.json");
  s.addNotes("We retrained our learned layers on growing slices of the training data and scored them only on recordings they never saw, so this isn't memorization. Left: the 3 procedures with 9 training recordings, held-out step accuracy. Right: the local student model on the same 469 held-out checks as the headline result. Steady gains per doubling of data, not 'exponential'. If asked for counts: up to 9 recordings per procedure, 30 recordings for the student. Every customer session is new training data. The engine we evaluated used only 3 recordings per procedure, so there's headroom we haven't used yet (not re-measured end to end).");
}

// ---------- 11 · Why now ----------
pres.addSection({ title: "Market" });
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Market" });
  s.addText("WHY NOW", { placeholder: "eyebrow" });
  s.addText(titleWithMark("Everyone is building the glasses. Nobody has proven ", "the coach"), { placeholder: "title" });
  const ev = [
    ["JUN 2026", "Viture + NVIDIA announce Helix, safety glasses that coach workers", true],
    ["AUG 2026", "NVIDIA open-sources its toolkit for AI agents on glasses", true],
    ["SEPT 2026", "Meta opens its glasses' camera to third-party apps", true],
    ["NOV 2026", "Google + Samsung Android XR glasses (reported)", false],
    ["2027", "Apple glasses (reported)", false],
  ];
  const cw = 12.33 / 5;
  line(s, 0.5, 2.55, 12.83, 2.55, { color: C.text1, width: 1.5, name: "timeline" });
  ev.forEach(([d, t, done], i) => {
    const x = 0.5 + i * cw;
    s.addShape(pres.ShapeType.ellipse, { x, y: 2.44, w: 0.22, h: 0.22, fill: { color: done ? C.text1 : C.background2 }, line: { color: C.text1, width: 1.5 }, objectName: "timeline-dot" });
    mono(s, d, { x, y: 2.85, w: cw - 0.25, h: 0.3, fontSize: 11, color: C.text1 });
    tb(s, t, { x, y: 3.2, w: cw - 0.3, h: 1.1, fontSize: 15 });
  });
  darkPanel(s, 0.5, 4.65, 12.33, 1.75, "SO WE DON'T FIGHT FOR CONSUMERS", "We sell to businesses, on whatever glasses they pick, or a phone. The hardware and plumbing are being built around us. The part nobody publishes numbers on is the coach, and that's the part we've measured.");
  footer(s, 11, "Viture/NVIDIA release · NVIDIA XR AI beta · Meta Wearables toolkit 1.0 · 9to5Google · Apple: reported, not announced");
  s.addNotes("Filled dots happened; open dots are reported. Say 'designed to run on' glasses until an adapter has run on that device: today it runs live on a video stream on a laptop, and glasses are one more input adapter. Apple is reported only. Sources in docs/POSITIONING.md 'Why now'.");
}

// ---------- 12 · Wedge + how we charge ----------
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Market" });
  s.addText("WHERE WE START", { placeholder: "eyebrow" });
  s.addText(titleWithMark("We start with new ", "maintenance and repair", " technicians"), { placeholder: "title" });
  const why = [
    ["01", "The work moves around the machine", "A camera bolted to a workbench can't follow it. A first-person camera can."],
    ["02", "The procedures already live on their phones", "Autodesk is buying MaintainX, a maintenance-procedures app, for $3.6B. We give those procedures eyes."],
    ["03", "New hires keep coming", "About 51,900 US openings a year for machinery maintenance mechanics and millwrights."],
  ];
  why.forEach(([n, h, b], i) => {
    const y = 2.2 + i * 1.4;
    line(s, 0.5, y, 6.9, y, { color: C.text1, width: 1.5, name: "row-rule" });
    mono(s, n, { x: 0.5, y: y + 0.18, w: 0.6, h: 0.3, fontSize: 11, color: C.accent2 });
    tb(s, h, { x: 1.1, y: y + 0.15, w: 5.8, h: 0.4, fontFace: SEMI, fontSize: 17 });
    tb(s, b, { x: 1.1, y: y + 0.55, w: 5.8, h: 0.75, fontSize: 14, color: BODY });
  });
  plateCard(s, 7.35, 2.2, 5.48, 4.2, "card-pricing");
  mono(s, "HOW WE CHARGE", { x: 7.7, y: 2.45, w: 4.8, h: 0.3, fontSize: 11, color: C.text1 });
  tb(s, runs([
    ["A subscription ", "per trainee, per month. We'll test $150 to $250"],
    ["A one-time setup ", "per procedure, compiled from their existing manuals"],
    ["Reusable ", "for every new hire. Edit the procedure and every trainee gets the update"],
    ["No repeat walkthroughs: ", "a manager doesn't have to stop work to show it again"],
  ]), { x: 7.7, y: 2.9, w: 4.8, h: 2.6, fontSize: 14 });
  mono(s, "TULIP LISTS $100–250 PER STATION PER MONTH. ONE RETROCAUSAL LISTING WORKS OUT TO ABOUT $500.", { x: 7.7, y: 5.6, w: 4.8, h: 0.6, fontSize: 9, color: C.text2 });
  footer(s, 12, "Autodesk–MaintainX (28 May 2026) · BLS Occupational Outlook 2025–35 · pricing is our hypothesis, to be tested in pilots");
  s.addNotes("Expansion after maintenance: field service (HVAC, equipment), then assembly lines, then regulated maintenance (aviation, medical devices). They share the same physical building blocks: fasteners, connectors, orientation, torque.");
}

// ---------- 13 · Economics ----------
{
  const s = pres.addSlide({ masterName: "Praxis Split", sectionTitle: "Market" });
  s.addShape(pres.ShapeType.rect, { x: 0, y: 0, w: 7.2, h: 7.5, fill: { color: C.text1 }, line: { type: "none" }, objectName: "economics-panel" });
  s.addChart(pres.ChartType.bar, [{ name: "Customer cost per hour", labels: ["Senior tech's time", "Praxis"], values: [43.9, 4.76] }],
    { ...darkChart("What the customer pays, per hour"), chartColors: ["4A5156", "FF5B14"], x: 0.5, y: 0.7, w: 6.2, h: 2.7, valAxisMaxVal: 56, valAxisMinVal: 0, dataLabelFormatCode: '"$"0.00', objectName: "chart-customer-hour" });
  s.addChart(pres.ChartType.bar, [{ name: "Our cost per hour", labels: ["Model every 5 s", "Praxis today", "Praxis + our local model"], values: [5.1, 1.08, 0.48] }],
    { ...darkChart("What it costs us to run, per hour"), chartColors: ["4A5156", "FF5B14", "FF5B14"], x: 0.5, y: 3.9, w: 6.2, h: 2.7, valAxisMaxVal: 6.6, valAxisMinVal: 0, dataLabelFormatCode: '"$"0.00', objectName: "chart-our-hour" });
  s.addText("UNIT ECONOMICS", { placeholder: "eyebrow" });
  s.addText("An hour of Praxis costs what 6 minutes of a senior tech does", { placeholder: "title" });
  const rows = [
    { y: 3.25, big: "1 h / week", cap: "of senior-tech time saved pays for a $200-a-month seat" },
    { y: 4.85, big: "$1.08", vs: "vs $5.10", cap: "per hour to run. A frontier model on a timer costs more than the price, so the architecture is the business model" },
  ];
  rows.forEach((r, i) => {
    line(s, 7.85, r.y, 12.83, r.y, { color: C.text1, width: 1.5, name: `economics-rule-${i + 1}` });
    s.addText([
      { text: r.big, options: { fontFace: HEAD, fontSize: 30, color: i === 0 ? C.accent2 : C.text1 } },
      ...(r.vs ? [{ text: "  " + r.vs, options: { fontFace: HEAD, fontSize: 16, color: C.text2 } }] : []),
    ], { x: 7.85, y: r.y + 0.1, w: 4.98, h: 0.6, margin: 0, valign: "middle", isTextBox: true, objectName: `economics-${i + 1}` });
    s.addText(r.cap, { x: 7.85, y: r.y + 0.75, w: 4.98, h: 0.75, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: `economics-${i + 1}-caption` });
  });
  footer(s, 13, "BLS · $200/month at 2 h/day · $/video-min × 60", 7.85);
  s.addNotes("Senior tech: BLS median $30.82 an hour divided by the 70.2% wage share is about $44 fully loaded, which is low for a senior tech. Praxis at $200 per trainee-month and 2 hours a day is about $4.76 an hour. Break-even: $2,400 a year / 52 / $44 is about 1 hour a week. Run cost is measured cost per video-minute times 60. Pricing risk: if trainees wear it all shift, a flat $200 seat leaves about a 9% margin today and about 60% with the local model, so price by coached hours or tiers (appendix).");
}

// ---------- 14 · Divider: the long game ----------
pres.addSection({ title: "Long game" });
{
  const s = pres.addSlide({ masterName: "Praxis Dark Grid", sectionTitle: "Long game" });
  s.addText("03 · THE LONG GAME", { placeholder: "eyebrow" });
  s.addText("Today we coach the people. Next, the robots", { placeholder: "title" });
  s.addText("Every session is step-labeled video of real skilled work: exactly what robots need to learn the same jobs, and to be checked while they do them.", { placeholder: "body" });
  s.addImage({ path: MK(`prog-dark-14of${TOTAL}.png`), x: 13.333 - 1.2 - 5 * MARK_RATIO, y: 1.25, h: 5, w: 5 * MARK_RATIO, objectName: "progress-mark-large" });
  s.addNotes("The full line: today we coach the people; next we train and check the robots that work next to them. Customers pay us to collect the data that robot labs pay crowds to stage.");
}

// ---------- 15 · Staircase ----------
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Long game" });
  s.addText("THE LONG GAME", { placeholder: "eyebrow" });
  s.addText("Each step pays for itself and builds what the next one needs", { placeholder: "title" });
  const steps = [
    ["NOW", "Coach new technicians", "Paid per trainee. Produces step-labeled video of real skilled work"],
    ["YEARS 1.5–3", "The record of physical work", "Capture your best tech once. Proof that each critical step was done"],
    ["YEARS 2–4", "Our own models", "Trained on our sessions: cheaper, on the device, better at fine checks"],
    ["YEARS 3–6", "Data + checker for robots", "Robot labs buy the step-labeled data and the step checker they lack"],
    ["OPTION", "Robot intelligence", "Robot skills for the jobs we know best, on partners' robots. No hardware"],
  ];
  const cw = 12.33 / 5, gap = 0.15, base = 6.4;
  steps.forEach(([when, h, b], i) => {
    const x = 0.5 + i * cw, w = cw - gap, hh = 2.4 + i * 0.45, y = base - hh;
    const cur = i === 0;
    s.addShape(pres.ShapeType.roundRect, { x, y, w, h: hh, rectRadius: 0.05, fill: { color: cur ? C.accent1 : C.background1 }, line: { type: "none" }, objectName: `step-${i + 1}` });
    mono(s, when, { x: x + 0.2, y: y + 0.2, w: w - 0.4, h: 0.3, fontSize: 10, color: cur ? C.text1 : C.text2 });
    tb(s, h, { x: x + 0.2, y: y + 0.55, w: w - 0.4, h: 0.65, fontFace: SEMI, fontSize: 16 });
    tb(s, b, { x: x + 0.2, y: y + 1.2, w: w - 0.4, h: 0.95, fontSize: 13, color: cur ? C.text1 : BODY });
  });
  footer(s, 15, "Each step has a gate: a condition, not a date · robot-brain valuations: Figure, Physical Intelligence, Skild · docs/VISION.md");
  s.addNotes("Why it compounds: robot companies already pay for first-person human video, and investors are paying for the robot brain (Figure, Physical Intelligence, Skild). The plants where we coach technicians are the ones buying robots, and those robots need maintaining too. Honest risks: human video doesn't transfer straight to robots, and robot policy work is capital-heavy, so the last step is an option, gated on a paying robot partner. With customers and workers the story is 'robots work next to you', not automation.");
}

// ---------- 16 · Gaps + ask ----------
pres.addSection({ title: "Ask" });
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Ask" });
  s.addText("WHAT THE GRANT BUYS", { placeholder: "eyebrow" });
  s.addText(titleWithMark("What isn't proven yet, and what ", "$10k", " over six months buys"), { placeholder: "title" });
  line(s, 0.5, 2.2, 6.4, 2.2, { color: C.text1, width: 1.5, name: "gaps-rule" });
  mono(s, "NOT PROVEN YET", { x: 0.5, y: 2.4, w: 5.9, h: 0.3, fontSize: 11, color: C.text1 });
  tb(s, runs([
    ["Catching mistakes. ", "4 of 17 alerts named a real annotated error. Our weakest number"],
    ["Maintenance footage. ", "Every metric so far is on public cooking video"],
    ["Glasses. ", "It runs live on a video stream on a laptop; no glasses yet"],
    ["Customers. ", "None yet. Outreach to maintenance managers has started"],
  ], 12), { x: 0.5, y: 2.85, w: 5.9, h: 3.4, fontSize: 15 });
  line(s, 6.92, 2.2, 12.83, 2.2, { color: C.text1, width: 1.5, name: "budget-rule" });
  mono(s, "$10K · SIX MONTHS", { x: 6.92, y: 2.4, w: 5.9, h: 0.3, fontSize: 11, color: C.text1 });
  const rows = [["$3,000", "Model, API and GPU experiments"], ["$2,500", "Smart glasses and capture gear"], ["$2,000", "Recording and labeling real maintenance tasks"], ["$1,500", "Inference and storage"], ["$1,000", "Company formation"]];
  rows.forEach(([a, b], i) => {
    const y = 2.85 + i * 0.42;
    mono(s, a, { x: 6.92, y, w: 1.2, h: 0.35, fontSize: 12, color: C.accent2 });
    tb(s, b, { x: 8.2, y: y - 0.02, w: 4.6, h: 0.35, fontSize: 15 });
  });
  darkPanel(s, 6.92, 5.0, 5.91, 1.5, "GOAL BY APRIL", "Measured on real maintenance footage, running on glasses, and a first paid pilot with a metric agreed up front.", 15);
  footer(s, 16, "docs/CLAIMS.md · context/APPLICATION.md");
  s.addNotes("The mistake number: the errors it does catch all need task state (steps done out of order), so better tracking should mean more catches. The grant funds exactly the experiments that close these gaps.");
}

// ---------- 17 · Close ----------
{
  const s = pres.addSlide({ masterName: "Praxis Dark Grid", sectionTitle: "Ask" });
  s.addImage({ path: A("mark-dark-full.png"), x: 0.83, y: 0.83, h: 5.83, w: 5.83 * MARK_RATIO, objectName: "mark-large" });
  s.addImage({ path: A("praxis-lockup-white.png"), x: 6.67, y: 1.67, h: 0.45, w: 0.45 * LOCKUP_RATIO, objectName: "logo" });
  s.addText("Instructions that can finally see how you're doing", { x: 6.67, y: 2.5, w: 5.8, h: 2.2, fontFace: HEAD, fontSize: 34, color: C.background2, valign: "top", margin: 0, lineSpacingMultiple: 0.95, isTextBox: true, objectName: "cover-headline" });
  s.addText([
    { text: "STARTUPS @ HARVARD · 20 OCT 2026", options: { breakLine: true } },
    { text: "MONISH SARAVANA · FOUNDER", options: { breakLine: true } },
    { text: "MONISHSARAVANA@COLLEGE.HARVARD.EDU" },
  ], { x: 6.67, y: 5.75, w: 5.8, h: 0.8, fontFace: MONO, fontSize: 10, charSpacing: 1, color: C.accent6, margin: 0, valign: "top", isTextBox: true, objectName: "cover-meta" });
  s.addNotes("Thank you. Happy to go deeper on the engine, the data or the plan; the appendix has the details.");
}

// ================================================================== APPENDIX
pres.addSection({ title: "Appendix" });
const appx = (eb, title) => {
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Appendix" });
  s.addText(eb, { placeholder: "eyebrow" });
  s.addText(title, { placeholder: "title" });
  return s;
};
const tableOpts = (colW, w = 12.33) => ({ x: 0.5, y: 2.2, w, colW, fontFace: "Archivo", fontSize: 12, color: "16191B", border: { type: "solid", color: "C9CFCC", pt: 0.75 }, valign: "middle", rowH: 0.52, fill: { color: "F6F7F6" } });
const TH = (t) => ({ text: t, options: { fontFace: MONO, fontSize: 10, color: "E8EBE9", fill: { color: "16191B" } } });

// A1 · training data
{
  const s = appx("APPENDIX · A1", "Training data, stated plainly");
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
  footer(s, TOTAL, "results/RESULTS.md · results/scaling/learning_curve.json · docs/DATA.md");
}

// A2 · competitors
{
  const s = appx("APPENDIX · A2", "Who else is here, and how we differ");
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
  footer(s, TOTAL, "docs/COMPETITORS.md · docs/POSITIONING.md · docs/PITCH_QA.md");
}

// A3 · unit economics
{
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
  footer(s, TOTAL, "Cost per video-minute: docs/CLAIMS.md · 2,520 coached minutes a month = 2 h/day × 21 days · senior-tech cost: BLS");
}

// A4 · glasses + voice
{
  const s = appx("APPENDIX · A4", "Glasses and voice: what's built, and what's designed");
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
  footer(s, TOTAL, "docs/GLASSES.md · docs/VOICE.md · docs/NEXT.md · we say \"designed to run on\" glasses until an adapter has run on that device");
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
