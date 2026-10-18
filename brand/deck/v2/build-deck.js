// Praxis deck v2: editable .pptx built with pptxgenjs. v1 lives in ../v1.
// Every text, card, arrow and HUD element is a native shape; photos and the logo/progress marks are the only images.
// Coordinates for photo slides are in the 1920x1080 frame of the HUD mocks (px / 144 = inches on a 13.333" x 7.5" slide).
const path = require("path");
const pptxgen = require("pptxgenjs");
const JSZip = require(require.resolve("jszip", { paths: [require.resolve("pptxgenjs")] }));
const fs = require("fs");

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

const A = (f) => path.join(__dirname, "assets", f);
const P = (px) => px / 144;
const OUT = process.argv[2] || path.join(__dirname, "praxis-deck.pptx");

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
// HUD colors for dark photo backgrounds (brighter than the theme's light-ground state colors)
const HUD = { ink: "16191B", text: "E8EBE9", orange: "FF5B14", green: "3DD68C", blue: "6EA8FF", red: "D92D20", plate: "F6F7F6", body: "3C4347" };
const LOCKUP_RATIO = 452.48 / 91.93;
const MARK_RATIO = 38 / 48;
const TOTAL = 10;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "Praxis";
pres.author = "Monish Saravana";
pres.company = "Praxis";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

// ---------- layouts ----------
const eyebrow = (color, y = 0.5) => ({
  placeholder: { options: { name: "eyebrow", type: "body", x: 0.5, y, w: 9, h: 0.3, fontFace: MONO, fontSize: 11, charSpacing: 2, color, margin: 0, valign: "top" }, text: "Eyebrow" },
});
pres.defineSlideMaster({
  title: "Praxis Light",
  background: { color: C.background2 },
  objects: [
    eyebrow(C.text2),
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.85, w: 12.33, h: 1.05, fontFace: THEME.headFontFace, fontSize: 28, color: C.text1, align: "left", valign: "top", margin: 0, lineSpacingMultiple: 0.95 }, text: "Slide title" } },
  ],
  slideNumber: { x: 0.82, y: 6.93, w: 0.6, h: 0.3, fontFace: MONO, fontSize: 10, color: C.text2, margin: 0, valign: "middle" },
});
pres.defineSlideMaster({
  title: "Praxis Split",
  background: { color: C.background2 },
  objects: [
    { placeholder: { options: { name: "eyebrow", type: "body", x: 7.85, y: 0.6, w: 4.98, h: 0.3, fontFace: MONO, fontSize: 11, charSpacing: 2, color: C.text2, margin: 0, valign: "top" }, text: "Eyebrow" } },
    { placeholder: { options: { name: "title", type: "title", x: 7.85, y: 0.95, w: 4.98, h: 1.9, fontFace: THEME.headFontFace, fontSize: 26, color: C.text1, align: "left", valign: "top", margin: 0, lineSpacingMultiple: 0.95 }, text: "Slide title" } },
  ],
  slideNumber: { x: 8.17, y: 6.93, w: 0.6, h: 0.3, fontFace: MONO, fontSize: 10, color: C.text2, margin: 0, valign: "middle" },
});
pres.defineSlideMaster({
  title: "Praxis Dark Grid",
  background: { path: A("bg-grid-dark.png") },
  objects: [
    eyebrow(C.accent1, 0.83),
    { placeholder: { options: { name: "title", type: "title", x: 0.83, y: 4.2, w: 6.9, h: 1.6, fontFace: THEME.headFontFace, fontSize: 40, color: C.background2, align: "left", valign: "bottom", margin: 0, lineSpacingMultiple: 0.95 }, text: "Section title" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.83, y: 5.95, w: 6.3, h: 0.8, fontFace: THEME.bodyFontFace, fontSize: 16, color: C.accent6, valign: "top", margin: 0 }, text: "Body" } },
  ],
});
pres.defineSlideMaster({ title: "Praxis Photo", background: { color: C.text1 }, objects: [] });

// ---------- helpers ----------
function footer(slide, n, source, x0 = 0.5) {
  slide.addImage({ path: A(`prog-light-${n}of${TOTAL}.png`), x: x0, y: 6.93, h: 0.3, w: 0.3 * MARK_RATIO, objectName: "progress-mark" });
  if (source) slide.addText(source, { x: x0 + 1.0, y: 6.93, w: 12.83 - x0 - 1.0, h: 0.3, fontFace: MONO, fontSize: 9.5, color: C.text2, align: "right", valign: "middle", margin: 0, isTextBox: true, objectName: "footer-source" });
}
function line(slide, x1, y1, x2, y2, opts) {
  const o = { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1), line: { color: opts.color, width: opts.width || 1.5, dashType: opts.dash || "solid", endArrowType: opts.arrow ? "triangle" : undefined }, objectName: opts.name };
  // pptx lines run top-left → bottom-right; flip so the arrowhead lands on (x2, y2)
  if (x2 < x1) o.flipH = true;
  if (y2 < y1) o.flipV = true;
  slide.addShape(pres.ShapeType.line, o);
}
function poly(slide, pts, opts) {
  for (let i = 0; i < pts.length - 1; i++) line(slide, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], { ...opts, arrow: opts.arrow && i === pts.length - 2 });
}

// HUD elements, in 1920x1080 px
function hudProgress(slide, step, total, x = 56, y = 56, textW = 137) {
  const markW = 56 * MARK_RATIO, w = 22 + markW + 18 + textW + 26;
  slide.addShape(pres.ShapeType.roundRect, { x: P(x), y: P(y), w: P(w), h: P(88), rectRadius: P(14), fill: { color: HUD.ink, transparency: 20 }, line: { type: "none" }, objectName: "hud-progress" });
  slide.addImage({ path: A(`prog-hud-${step}of${total}.png`), x: P(x + 22), y: P(y + 16), w: P(markW), h: P(56), objectName: "hud-progress-mark" });
  slide.addText(`STEP ${step}/${total}`, { x: P(x + 22 + markW + 18), y: P(y), w: P(textW + 20), h: P(88), fontFace: MONO, fontSize: 13, charSpacing: 1, color: HUD.text, valign: "middle", margin: 0, isTextBox: true, objectName: "hud-progress-text" });
}
function hudChip(slide, text, textW, opts = {}) {
  const h = opts.label ? 136 : 96, w = textW + 64 + 24, bottom = 1016;
  const x0 = opts.right ? 1920 - 56 - w : 56, y0 = bottom - h;
  slide.addShape(pres.ShapeType.roundRect, { x: P(x0), y: P(y0), w: P(w), h: P(h), rectRadius: P(10), fill: { color: HUD.ink, transparency: opts.solid ? 0 : 14 }, line: { type: "none" }, objectName: "hud-chip" });
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
  const w = 446 * 0.69 + 28; // 18px mono vs the 26px measurement
  slide.addShape(pres.ShapeType.roundRect, { x: P(1920 - 40 - w), y: P(1032), w: P(w), h: P(34), rectRadius: P(6), fill: { color: HUD.ink, transparency: 40 }, line: { type: "none" }, objectName: "concept-tag" });
  slide.addText("CONCEPT MOCK · STOCK PHOTO", { x: P(1920 - 40 - w), y: P(1032), w: P(w), h: P(34), fontFace: MONO, fontSize: 8, charSpacing: 1, color: "C9CFCC", align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "concept-tag-text" });
}
function photo(slide, file) {
  slide.addImage({ path: A(file), x: 0, y: 0, w: 13.333, h: 7.5, objectName: "photo" });
}

// ================= v2 =================
// Rules: the deck behaves like the HUD (progress pill + takeaway chip), one thing lit per slide,
// extreme type scale, the tracker's belief bars as the recurring graphic, dark for the story and aluminum for the proof.
// Positions use the mockup's units: cqw = percent of slide width (Q(v) → inches).
const Q = (v) => (v * 13.333) / 100;
const MAIN = 6; // slides in the main story; the appendix is not counted in the progress pill
const pad = (n) => String(n).padStart(2, "0");

pres.defineSlideMaster({ title: "Praxis Dark", background: { color: C.text1 }, objects: [] });
pres.defineSlideMaster({ title: "Praxis Aluminum", background: { color: C.background2 }, objects: [] });

function deckPill(slide, n, x = 56, y = 56, solid = false) {
  const markW = 56 * MARK_RATIO, textW = 120, w = 22 + markW + 18 + textW + 26;
  slide.addShape(pres.ShapeType.roundRect, { x: P(x), y: P(y), w: P(w), h: P(88), rectRadius: P(14), fill: { color: HUD.ink, transparency: solid ? 0 : 18 }, line: { type: "none" }, objectName: "deck-progress" });
  slide.addImage({ path: A(`prog-hud-${n}of${MAIN}.png`), x: P(x + 22), y: P(y + 16), w: P(markW), h: P(56), objectName: "deck-progress-mark" });
  slide.addText(`${pad(n)} / ${pad(MAIN)}`, { x: P(x + 22 + markW + 18), y: P(y), w: P(textW + 20), h: P(88), fontFace: MONO, fontSize: 13, charSpacing: 1, color: HUD.text, valign: "middle", margin: 0, isTextBox: true, objectName: "deck-progress-text" });
}
function mono(slide, text, x, y, w, opts = {}) {
  slide.addText(text, { x: Q(x), y: Q(y), w: Q(w), h: opts.h || Q(1.6), fontFace: MONO, fontSize: opts.size || 10, charSpacing: opts.spacing ?? 2, color: opts.color || C.accent6, align: opts.align || "left", valign: opts.valign || "top", margin: 0, isTextBox: true, objectName: opts.name || "label" });
}
function sourceLine(slide, text, color) {
  slide.addText(text, { x: Q(40), y: Q(53.4), w: Q(57.1), h: Q(1.4), fontFace: MONO, fontSize: 7.5, charSpacing: 1, color, align: "right", valign: "middle", margin: 0, isTextBox: true, objectName: "footer-source" });
}

// ---------- 1 · Cover ----------
pres.addSection({ title: "Story" });
{
  const s = pres.addSlide({ masterName: "Praxis Photo", sectionTitle: "Story" });
  photo(s, "photo-cover.jpg");
  s.addImage({ path: A("praxis-lockup-white.png"), x: Q(4.5), y: Q(4.6), h: Q(3.4), w: Q(3.4) * LOCKUP_RATIO, objectName: "logo" });
  s.addText([
    { text: "Instructions that can finally " },
    { text: "see", options: { color: C.accent1 } },
    { text: " how you're doing." },
  ], { x: Q(4.5), y: Q(13.8), w: Q(52), h: Q(27), fontFace: THEME.headFontFace, fontSize: 58, color: C.background2, valign: "top", margin: 0, lineSpacingMultiple: 0.92, isTextBox: true, objectName: "cover-headline" });
  mono(s, "STARTUPS @ HARVARD · 20 OCT 2026 · MONISH SARAVANA", 4.5, 49.4, 50, { size: 9.5, name: "cover-meta" });
  const reg = [860, 640, 1180, 900];
  hudRegion(s, reg, HUD.green);
  hudPulse(s, 1010, 790, HUD.green);
  hudProgress(s, 4, 9, 1920 - 56 - 247);
  const chip = hudChip(s, "Seat the clamp past the hose bead", 624, { right: true });
  hudLeader(s, chip, reg, HUD.green);
  conceptTag(s);
  s.addNotes("Hi, I'm Monish. Praxis is AI guidance for the physical world: instructions that can finally see how you're doing. This is what a new maintenance technician sees through the glasses: one short instruction, a small progress mark, and a green check when the step is done. The photo is stock with a mocked-up HUD; the product behind it is real and I'll show the numbers.");
}

// ---------- 2 · Problem ----------
{
  const s = pres.addSlide({ masterName: "Praxis Dark Grid", sectionTitle: "Story" });
  deckPill(s, 2);
  mono(s, "THE PROBLEM", 4.5, 8.8, 30, { name: "eyebrow" });
  s.addText("1 year", { x: Q(3.9), y: Q(9.7), w: Q(80), h: Q(16.5), fontFace: THEME.headFontFace, fontSize: 158, color: C.background2, valign: "top", margin: 0, isTextBox: true, objectName: "hero-number" });
  mono(s, "TYPICAL ON-THE-JOB TRAINING · BLS", 64, 23.6, 30, { size: 9, name: "hero-number-source" });
  mono(s, "DAY ONE", 4.5, 27.4, 15, { size: 9, color: C.accent1, name: "timeline-start" });
  mono(s, "WORKS ALONE", 80.5, 27.4, 15, { size: 9, color: C.background2, align: "right", name: "timeline-end" });
  const x0 = 4.5, x1 = 95.5, gap = 0.45, segW = (x1 - x0 - gap * 11) / 12;
  for (let i = 0; i < 12; i++) {
    const x = x0 + i * (segW + gap);
    s.addShape(pres.ShapeType.rect, { x: Q(x), y: Q(31.5), w: Q(segW), h: Q(1.05), fill: { color: C.background2, transparency: 86 }, line: { type: "none" }, objectName: `month-${i + 1}` });
    mono(s, pad(i + 1), x, 33.1, 4, { size: 7, color: C.text2, spacing: 1, name: `month-${i + 1}-label` });
  }
  s.addShape(pres.ShapeType.ellipse, { x: Q(4.0), y: Q(30.95), w: Q(2.1), h: Q(2.1), fill: { color: C.accent1 }, line: { color: C.text1, width: 3 }, objectName: "timeline-day-one" });
  s.addShape(pres.ShapeType.rect, { x: Q(95.25), y: Q(30.3), w: Q(0.25), h: Q(3.4), fill: { color: C.background2 }, line: { type: "none" }, objectName: "timeline-works-alone" });
  s.addText("before a new maintenance technician works alone.", { x: Q(4.5), y: Q(37.6), w: Q(60), h: Q(8), fontFace: THEME.headFontFace, fontSize: 30, color: C.background2, valign: "top", margin: 0, lineSpacingMultiple: 0.98, isTextBox: true, objectName: "headline" });
  line(s, Q(73.5), Q(38.6), Q(95.5), Q(38.6), { color: "5E676C", width: 1, name: "side-rule" });
  s.addText([
    { text: "9–14 months", options: { fontFace: THEME.headFontFace, fontSize: 25, color: C.background2, breakLine: true, paraSpaceAfter: 4 } },
    { text: "before a new hire is profitable, in a survey of 35 aviation repair stations. Some took 24.", options: { fontSize: 11.5, color: C.accent6 } },
  ], { x: Q(73.5), y: Q(39.6), w: Q(22), h: Q(9), valign: "top", margin: 0, isTextBox: true, objectName: "side-stat" });
  hudChip(s, "Most of it is shadowing a senior tech", 659);
  sourceLine(s, "BLS OCCUPATIONAL OUTLOOK HANDBOOK · 2017 REPAIR-STATION SURVEY", C.text2);
  s.addNotes("BLS says on-the-job training for these jobs typically lasts more than a year. In a 2017 survey of 35 aviation repair stations, new hires took 9 to 14 months on average to become profitable, and some took 24. Most of that learning is shadowing a senior tech, which nobody budgets for: it shows up as lost senior-tech hours. Sources in docs/POSITIONING.md [P8, P22].");
}

// ---------- 3 · On the job (storyboard) ----------
{
  const s = pres.addSlide({ masterName: "Praxis Dark", sectionTitle: "Story" });
  mono(s, "ON THE JOB", 2.9, 3.1, 30, { color: C.accent1, name: "eyebrow" });
  s.addText("Small and quiet until something goes wrong.", { x: Q(2.9), y: Q(4.9), w: Q(80), h: Q(5), fontFace: THEME.headFontFace, fontSize: 28, color: C.background2, valign: "top", margin: 0, isTextBox: true, objectName: "headline" });
  const heroW = 63.5, heroH = heroW * 9 / 16;
  s.addImage({ path: A("hud-mistake.jpg"), x: Q(2.9), y: Q(11.2), w: Q(heroW), h: Q(heroH), objectName: "frame-mistake" });
  const tag = (text, x, y, color, size = 8) => {
    s.addText(text, { x: Q(x), y: Q(y), w: Q(text.length * 0.62 + 1.6), h: Q(1.9), fontFace: MONO, fontSize: size, charSpacing: 1, color, fill: { color: HUD.ink, transparency: 12 }, align: "center", valign: "middle", margin: 0, objectName: "frame-label" });
  };
  tag("MISTAKE CAUGHT", 4.1, 11.2 + heroH - 3.2, "FF8A73", 9);
  const sx = 67.8, sw = 100 - 2.9 - sx, sh = 10.9, sg = 1.1;
  [["hud-step.jpg", "STEP TRACKING", HUD.text], ["hud-verified.jpg", "VERIFIED", HUD.green], ["hud-view.jpg", "ASKS FOR A BETTER VIEW", HUD.blue]].forEach(([f, label, color], i) => {
    const y = 11.2 + i * (sh + sg);
    s.addImage({ path: A(f), x: Q(sx), y: Q(y), w: Q(sw), h: Q(sh), sizing: { type: "cover", w: Q(sw), h: Q(sh) }, objectName: `frame-${i + 1}` });
    tag(label, sx + 0.8, y + 0.8, color);
  });
  s.addText("It knows where you are in the procedure, so it can tell when a step was skipped.", { x: Q(sx), y: Q(47.4), w: Q(sw), h: Q(5), fontSize: 11.5, color: C.accent6, valign: "top", margin: 0, isTextBox: true, objectName: "caption" });
  s.addNotes("This is the product on the job. Most of the time it's small and quiet: a progress mark and one short instruction. It lights up when it matters: here it caught that lockout was skipped and says exactly how to fix it. It confirms finished steps, and when it can't see well it asks for a better view instead of guessing. Full-screen versions of each are in the appendix. These are concept mocks on stock photos.");
}

// ---------- 4 · Divider ----------
pres.addSection({ title: "How it works" });
{
  const s = pres.addSlide({ masterName: "Praxis Dark", sectionTitle: "How it works" });
  mono(s, "02 · HOW IT WORKS", 4.5, 4.6, 30, { color: C.accent1, name: "eyebrow" });
  s.addText([
    { text: "A tracking problem,", options: { breakLine: true } },
    { text: "not a seeing problem.", options: { color: "4A5156" } },
  ], { x: Q(4.5), y: Q(6.9), w: Q(80), h: Q(13), fontFace: THEME.headFontFace, fontSize: 52, color: C.background2, valign: "top", margin: 0, lineSpacingMultiple: 0.95, isTextBox: true, objectName: "headline" });
  const hs = [7, 11, 18, 31, 100, 26, 13, 8, 5], bx0 = 4.5, bx1 = 95.5, g = 1.5, bw = (bx1 - bx0 - g * 8) / 9, base = 49.85, hmax = 30;
  hs.forEach((h, i) => {
    const x = bx0 + i * (bw + g), bh = (hmax * h) / 100, on = i === 4;
    s.addShape(pres.ShapeType.rect, { x: Q(x), y: Q(base - bh), w: Q(bw), h: Q(bh), fill: on ? { color: C.accent1 } : { color: C.background2, transparency: 89 }, line: { type: "none" }, objectName: `belief-bar-S${i + 1}` });
    mono(s, `S${i + 1}`, x, base + 0.9, 5, { size: 8, color: on ? C.background2 : C.text2, spacing: 1, name: `belief-label-S${i + 1}` });
  });
  const barRight = bx0 + 4 * (bw + g) + bw;
  line(s, Q(barRight), Q(23.4), Q(61.3), Q(23.4), { color: C.accent1, width: 2, name: "belief-leader" });
  s.addShape(pres.ShapeType.ellipse, { x: Q(61.3 - 0.4), y: Q(23.4 - 0.4), w: Q(0.8), h: Q(0.8), fill: { color: C.accent1 }, line: { type: "none" }, objectName: "belief-leader-dot" });
  s.addText([
    { text: "WHERE YOU ARE: STEP 5", options: { color: C.background2, breakLine: true, paraSpaceAfter: 2 } },
    { text: "0:41 ON STEP · TYPICAL 0:25", options: { color: C.accent6 } },
  ], { x: Q(62.4), y: Q(22.2), w: Q(30), h: Q(4), fontFace: MONO, fontSize: 9, charSpacing: 1, valign: "top", margin: 0, isTextBox: true, objectName: "belief-note" });
  s.addNotes("Our conviction: coaching someone through physical work is a tracking problem, not a seeing problem. Praxis keeps a running belief about which step you're on (these bars), how long you've been on it versus how long it usually takes, and how sure it is. It only asks a big model when something happens. The bars are illustrative.");
}

// ---------- 5 · Architecture (dark blueprint, native) ----------
{
  const s = pres.addSlide({ masterName: "Praxis Dark Grid", sectionTitle: "How it works" });
  mono(s, "HOW PRAXIS WORKS · ENGINE v0", 2.9, 3.1, 40, { name: "eyebrow" });
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
    subs.forEach((t, i) => runs.push({ text: t, options: { fontFace: MONO, fontSize: 7.5, color: st.sc, breakLine: i < subs.length - 1 } }));
    s.addText(runs, { shape: pres.ShapeType.roundRect, x: V(x), y: V(y), w: V(w), h: V(h), rectRadius: 0.06, fill: st.fill ? { color: st.fill } : { type: "none" }, line: st.line, valign: "top", margin: [kind === "hero" ? 12 : 9, 9, 4, 10], objectName: `box-${name}` });
    if (st.tag) s.addText(st.tag, { x: V(x + w - 170), y: V(y + 6), w: V(160), h: V(16), fontFace: MONO, fontSize: 6.5, charSpacing: 1, color: st.sc, align: "right", valign: "middle", margin: 0, isTextBox: true, objectName: `box-${name}-tag` });
  }
  const aline = (pts, name, lit, dash) => poly(s, pts.map(([x, y]) => [V(x), V(y)]), { color: lit ? OR : "6B7479", width: lit ? 1.9 : 1.2, arrow: true, dash, name });
  const alab = (t, x, y, color = "9AA3A7", w = 220, align = "left") => s.addText(t, { x: V(x), y: V(y - 11), w: V(w), h: V(16), fontFace: MONO, fontSize: 7.5, charSpacing: 1, color, align, valign: "middle", margin: 0, isTextBox: true, objectName: "arrow-label" });

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
    s.addText(`S${i + 1}`, { x: V(bx - 6), y: V(556), w: V(44), h: V(16), fontFace: MONO, fontSize: 6.5, color: i === 3 ? "E8EBE9" : "6B7479", align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: `belief-label-${i + 1}` });
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
  alab("48 held-out clips (public CaptainCook4D) · results/RESULTS.md", 860, 861, "5E676C", 694, "right");
  s.addNotes("Walk it left to right along the orange path, which is what happens on every frame, on the device, in about 50 ms: open models turn the frame into features, our detector and recognizer feed our state tracker, and the policy decides whether the coach says anything. Below, in the dark, is the only rented part: on 14% of frames the tracker asks a verifier one typed question (Jev in 151 ms, Claude Opus for hard cases). We calibrate the answer and feed it back. Every session trains our local student, which already handles routine checks. Swapping the rented model is a one-line config change.");
}

// ---------- 6 · Results (light) ----------
{
  const s = pres.addSlide({ masterName: "Praxis Aluminum", sectionTitle: "How it works" });
  deckPill(s, 6, 56, 56, true);
  mono(s, "RESULTS · SAME FRONTIER MODEL, SAME FRAMES", 4.5, 10.2, 60, { color: C.text2, name: "eyebrow" });
  const cols = [
    { x: 4.5, big: [{ text: "54%" }], cap: "step accuracy with our state tracker around the model", bars: [90, 80] },
    { x: 53.5, big: [{ text: "5×" }], cap: "per minute of video: $0.018 versus $0.085", bars: [19, 90] },
  ];
  cols.forEach((c, i) => {
    s.addText(c.big, { x: Q(c.x - 0.4), y: Q(12.4), w: Q(44), h: Q(15), fontFace: THEME.headFontFace, fontSize: 148, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: `result-${i + 1}` });
    s.addText(c.cap, { x: Q(c.x), y: Q(28.6), w: Q(40), h: Q(3), fontSize: 14, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: `result-${i + 1}-caption` });
    [["PRAXIS", c.bars[0], true], ["MODEL EVERY 5 S", c.bars[1], false]].forEach(([label, pct, on], j) => {
      const y = 33.3 + j * 2.0;
      mono(s, label, c.x, y - 0.15, 11, { size: 8, color: on ? C.text1 : C.text2, spacing: 1, name: `result-${i + 1}-bar-${j + 1}-label` });
      s.addShape(pres.ShapeType.rect, { x: Q(c.x + 12), y: Q(y), w: Q((30 * pct) / 100), h: Q(1.3), fill: { color: on ? C.accent1 : "BFC6C2" }, line: { type: "none" }, objectName: `result-${i + 1}-bar-${j + 1}` });
    });
  });
  s.addText("cheaper", { x: Q(74.6), y: Q(20.6), w: Q(24), h: Q(6.2), fontFace: THEME.headFontFace, fontSize: 40, color: C.text2, valign: "bottom", margin: 0, isTextBox: true, objectName: "result-2-unit" });
  line(s, Q(50), Q(13), Q(50), Q(43), { color: "CBD1CE", width: 0.75, name: "divider" });
  hudChip(s, "Same model. Our layers make it better and cheaper.", 941, { solid: true });
  sourceLine(s, "48 HELD-OUT CLIPS · RESULTS/RUNS/FUSED_ORACLE.JSON", C.text2);
  s.addNotes("Like-for-like: the same frontier model, the same frames. Called every 5 seconds without state it tracks the step 48% of the time. With our layers around it, 54%, and about 5x cheaper ($0.018 vs $0.085 per minute) because most checks never leave the device. Bars are drawn to scale. Measured on 48 held-out first-person clips from a public cooking dataset (CaptainCook4D): say so if asked.");
}

// ---------- Appendix: full-screen HUD states (native, editable) ----------
pres.addSection({ title: "Appendix" });
{
  const s = pres.addSlide({ masterName: "Praxis Photo", sectionTitle: "Appendix" });
  photo(s, "photo-step.jpg");
  const reg = [800, 300, 1260, 820];
  hudRegion(s, reg, HUD.orange);
  hudProgress(s, 3, 8);
  const chip = hudChip(s, "Loosen the four float-bowl screws a half turn each", 903);
  hudLeader(s, chip, reg, HUD.orange);
  conceptTag(s);
  s.addNotes("Step tracking. Praxis recognizes the job by itself and keeps a running belief about which step you're on. The screen stays quiet: a progress mark, one short instruction, and the part it's talking about.");
}
{
  const s = pres.addSlide({ masterName: "Praxis Photo", sectionTitle: "Appendix" });
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
  const s = pres.addSlide({ masterName: "Praxis Photo", sectionTitle: "Appendix" });
  photo(s, "photo-mistake.jpg");
  const reg = [720, 160, 1160, 600];
  hudRegion(s, reg, HUD.red);
  hudProgress(s, 2, 7);
  const card = hudCard(s, "MISTAKE CAUGHT", HUD.red, HUD.red, "Lockout was skipped.", "Open and lock the feeder breaker, tag it, then test for zero voltage.", 1164, 660);
  hudLeader(s, card, reg, HUD.red);
  conceptTag(s);
  s.addNotes("Mistake caught. This is the moment that matters: Praxis knows where you are in the procedure, so it can tell that lockout was skipped and say exactly how to fix it. Out-of-order mistakes are the most common error type in our eval data, and you can only see them if you track state.");
}
{
  const s = pres.addSlide({ masterName: "Praxis Photo", sectionTitle: "Appendix" });
  photo(s, "photo-view.jpg");
  const reg = [330, 620, 780, 1010];
  hudRegion(s, reg, HUD.blue, true);
  hudProgress(s, 6, 12, 56, 56, 154);
  const card = hudCard(s, "NEED A BETTER VIEW", HUD.blue, "1D4ED8", "Can't see the bearing cap.", "Lean in over cylinder 2 and hold still for two seconds.", 1164, 56);
  hudLeader(s, card, reg, HUD.blue);
  conceptTag(s);
  s.addNotes("Needs a better view. When it isn't sure, it asks instead of guessing. On blurred or blocked views it asked for a better look 77-98% of the time and was never confidently wrong.");
}

// ---------- Appendix: backup cover B ----------
{
  const s = pres.addSlide({ masterName: "Praxis Dark Grid", sectionTitle: "Appendix" });
  s.addImage({ path: A("mark-dark-full.png"), x: 0.83, y: 0.83, h: 5.83, w: 5.83 * MARK_RATIO, objectName: "mark-large" });
  s.addImage({ path: A("praxis-lockup-white.png"), x: 6.67, y: 1.67, h: 0.45, w: 0.45 * LOCKUP_RATIO, objectName: "logo" });
  s.addText("Instructions that can finally see how you're doing", { x: 6.67, y: 2.5, w: 5.8, h: 2.2, fontFace: THEME.headFontFace, fontSize: 34, color: C.background2, valign: "top", margin: 0, lineSpacingMultiple: 0.95, isTextBox: true, objectName: "cover-headline" });
  s.addText([
    { text: "STARTUPS @ HARVARD · 20 OCT 2026", options: { breakLine: true } },
    { text: "MONISH SARAVANA · FOUNDER" },
  ], { x: 6.67, y: 5.9, w: 5.8, h: 0.55, fontFace: MONO, fontSize: 10, charSpacing: 1, color: C.accent6, margin: 0, valign: "top", isTextBox: true, objectName: "cover-meta" });
  s.addNotes("Backup cover (B). Use it if the photo cover feels too busy on the venue projector.");
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
