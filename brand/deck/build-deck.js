// Praxis deck: editable .pptx built with pptxgenjs.
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
  const w = 446 * 0.69 + 28; // 18px mono vs the 26px measurement
  slide.addShape(pres.ShapeType.roundRect, { x: P(1920 - 40 - w), y: P(1032), w: P(w), h: P(34), rectRadius: P(6), fill: { color: HUD.ink, transparency: 40 }, line: { type: "none" }, objectName: "concept-tag" });
  slide.addText("CONCEPT MOCK · STOCK PHOTO", { x: P(1920 - 40 - w), y: P(1032), w: P(w), h: P(34), fontFace: MONO, fontSize: 8, charSpacing: 1, color: "C9CFCC", align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "concept-tag-text" });
}
function photo(slide, file) {
  slide.addImage({ path: A(file), x: 0, y: 0, w: 13.333, h: 7.5, objectName: "photo" });
}

// ---------- 1 · Cover (C: first person) ----------
pres.addSection({ title: "Cover" });
{
  const s = pres.addSlide({ masterName: "Praxis Photo", sectionTitle: "Cover" });
  photo(s, "photo-cover.jpg");
  s.addImage({ path: A("praxis-lockup-white.png"), x: 0.5, y: 0.55, h: 0.4, w: 0.4 * LOCKUP_RATIO, objectName: "logo" });
  s.addText("Instructions that can finally see how you're doing", { x: 0.5, y: 2.35, w: 5.6, h: 2.4, fontFace: THEME.headFontFace, fontSize: 38, color: C.background2, valign: "middle", margin: 0, lineSpacingMultiple: 0.95, isTextBox: true, objectName: "cover-headline" });
  s.addText("STARTUPS @ HARVARD · 20 OCT 2026 · MONISH SARAVANA", { x: 0.5, y: 6.75, w: 6.5, h: 0.3, fontFace: MONO, fontSize: 10, charSpacing: 1, color: C.accent6, margin: 0, valign: "middle", isTextBox: true, objectName: "cover-meta" });
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
pres.addSection({ title: "Problem" });
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "Problem" });
  s.addText("THE PROBLEM", { placeholder: "eyebrow" });
  s.addText([
    { text: "A new maintenance technician takes " },
    { text: "about a year", options: { underline: { style: "heavy", color: "FF5B14" } } },
    { text: " to work alone" },
  ], { placeholder: "title" });
  const cols = [
    { x: 0.5, big: ">1 yr", cap: "of on-the-job training is typical for industrial machinery mechanics and maintenance workers." },
    { x: 6.92, big: "9–14 mo", cap: "before a new hire is profitable, in a survey of 35 aviation repair stations. Some took 24." },
  ];
  cols.forEach((c, i) => {
    line(s, c.x, 2.75, c.x + 5.91, 2.75, { color: C.text1, width: 1.5, name: `stat-rule-${i + 1}` });
    s.addText(c.big, { x: c.x, y: 2.95, w: 5.91, h: 1.0, fontFace: THEME.headFontFace, fontSize: 54, color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: `stat-${i + 1}` });
    s.addText(c.cap, { x: c.x, y: 4.05, w: 5.4, h: 0.9, fontSize: 16, color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: `stat-${i + 1}-caption` });
  });
  footer(s, 2, "Sources: BLS Occupational Outlook Handbook · 2017 aviation repair-station survey");
  s.addNotes("BLS says on-the-job training for these jobs typically lasts more than a year. In a 2017 survey of 35 aviation repair stations, new hires took 9 to 14 months on average to become profitable, and some took 24. Most of that learning is shadowing a senior tech, which nobody budgets for: it shows up as lost senior-tech hours. Sources in docs/POSITIONING.md [P8, P22].");
}

// ---------- 3–6 · Product: what it looks like on the job ----------
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
  s.addNotes("Step tracking. Praxis recognizes the job by itself and keeps a running belief about which step you're on. The screen stays quiet: a progress mark, one short instruction, and the part it's talking about.");
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
  s.addNotes("Mistake caught. This is the moment that matters: Praxis knows where you are in the procedure, so it can tell that lockout was skipped and say exactly how to fix it. Out-of-order mistakes are the most common error type in our eval data, and you can only see them if you track state.");
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
  s.addImage({ path: A("prog-divider-7of10.png"), x: 13.333 - 1.2 - 5 * MARK_RATIO, y: 1.25, h: 5, w: 5 * MARK_RATIO, objectName: "progress-mark-large" });
  s.addNotes("Our conviction: coaching someone through physical work is a tracking problem, not a seeing problem. Most competitors either stream video to a big model and hope, or bolt a camera to one workstation. We keep a belief about where the person is, and only ask a big model when something happens.");
}

// ---------- 8 · Architecture (native diagram) ----------
{
  const s = pres.addSlide({ masterName: "Praxis Light", sectionTitle: "How it works" });
  s.addText("HOW PRAXIS WORKS · ENGINE v0", { placeholder: "eyebrow" });
  s.addText("The frontier model is one swappable part. The tracking engine around it is ours", { placeholder: "title" });

  const OPEN = "D6DBD8", BODY = "3C4347";
  // legend
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
    const runs = [
      { text: title, options: { fontFace: SEMI, fontSize: 13, color: C.text1, breakLine: true } },
      { text: plain, options: { fontSize: 10.5, color: kind === "out" ? C.text1 : BODY, breakLine: specs.length > 0, paraSpaceAfter: opts.compact ? 0 : 3 } },
    ];
    specs.forEach((t, i) => runs.push({ text: t, options: { fontFace: MONO, fontSize: 8.5, color: kind === "out" ? C.text1 : C.text2, breakLine: i < specs.length - 1 } }));
    s.addText(runs, { shape: pres.ShapeType.roundRect, ...base, ...shape, valign: "top", margin: opts.compact ? [4, 9, 2, 9] : [7, 9, 6, 9], isTextBox: false });
    const tag = { ours: "OURS", open: "OPEN MODEL", rented: "RENTED · SWAPPABLE", out: "" }[kind];
    if (tag) s.addText(tag, { x: x + w - 1.6, y: y + 0.06, w: 1.52, h: 0.16, fontFace: MONO, fontSize: 7.5, charSpacing: 1, color: kind === "ours" ? C.text1 : C.text2, align: "right", margin: 0, valign: "top", isTextBox: true, objectName: `box-${name}-tag` });
  }
  const label = (t, x, y, w = 2.2, align = "left", name = "arrow-label") =>
    s.addText(t, { x, y, w, h: 0.2, fontFace: MONO, fontSize: 8.5, color: C.text1, margin: 0, valign: "middle", align, isTextBox: true, objectName: name });
  const arrow = (pts, name, dash) => poly(s, pts, { color: C.text1, width: 1.25, arrow: true, dash, name });
  const bandLabel = (t, x, y) => s.addText(t, { x, y, w: 9, h: 0.2, fontFace: MONO, fontSize: 8.5, charSpacing: 1, color: C.text2, margin: 0, valign: "middle", isTextBox: true, objectName: "band-label" });

  // offline row
  bandLabel("OFFLINE, ONCE PER PROCEDURE", 0.5, 2.5);
  box("compiler", "ours", 4.05, 2.4, 4.9, 0.8, "Procedure compiler", "Turns a manual into a task graph the engine can track", ["steps · checks · common mistakes · typical durations"]);
  s.addText([
    { text: "8 procedures compiled", options: { breakLine: true } },
    { text: "96 steps · 207 checks", options: { breakLine: true } },
    { text: "267 known mistakes", options: { breakLine: true } },
    { text: "$4.16 total, one-time" },
  ], { x: 9.15, y: 2.4, w: 3.0, h: 0.8, fontFace: MONO, fontSize: 9, color: C.text2, margin: 0, valign: "middle", isTextBox: true, objectName: "compiler-stats" });

  // fast path
  s.addShape(pres.ShapeType.roundRect, { x: 0.35, y: 3.32, w: 12.63, h: 1.92, rectRadius: 0.08, fill: { color: C.background1, transparency: 45 }, line: { type: "none" }, objectName: "band-fast" });
  bandLabel("FAST PATH · EVERY FRAME · ON THE DEVICE", 0.5, 3.38);
  s.addText("3.1× FASTER THAN REAL TIME", { x: 8.83, y: 3.38, w: 4.0, h: 0.2, fontFace: MONO, fontSize: 8.5, charSpacing: 1, color: C.text2, align: "right", margin: 0, valign: "middle", isTextBox: true, objectName: "band-label-speed" });
  const Y = 3.62, H = 1.5;
  box("camera", "ours", 0.5, Y, 1.45, H, "Camera", "Live video", ["first-person", "4 frames / s", "webcam or file", "glasses adapter:", "not yet tested"]);
  box("perception", "open", 2.12, Y, 1.75, H, "Perception", "What's in view", ["SigLIP2 · 20 ms/frame", "hands · 6 ms/frame", "V-JEPA 2 · 221ms @1Hz"]);
  box("event-detector", "ours", 4.04, Y, 1.8, 0.73, "Event detector", "Did a step just end?", ["F1 0.38 vs rule 0.24"], { compact: true });
  box("task-recognizer", "ours", 4.04, Y + 0.77, 1.8, 0.73, "Task recognizer", "Which job is this?", ["73% top-1, 40 s"], { compact: true });
  box("state-tracker", "ours", 6.01, Y, 2.9, H, "State tracker", "Where you are in the procedure", ["Bayesian semi-Markov model", "over the task graph"], { hero: true });
  // tracker belief: bars over steps, current step in orange
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

  // slow path
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
  s.addNotes("Walk it left to right. Open models on the device turn every frame into features. Our state tracker keeps a running belief about which step you're on, using a task graph we compiled from the manual. Only when something happens (a step ends, it's unsure, or you're stuck) does it ask a rented model one typed question: that's 14% of frames. We calibrate the answer and feed it back, and the policy decides whether to say anything. Every session becomes training data, and our local student already handles routine checks. If asked 'isn't this a wrapper?': same model with and without our layers is 48% vs 54% step accuracy at a fifth of the cost, and swapping the rented model is a one-line config change.");
}

// ---------- 9 · Results ----------
{
  const s = pres.addSlide({ masterName: "Praxis Split", sectionTitle: "How it works" });
  s.addShape(pres.ShapeType.rect, { x: 0, y: 0, w: 7.2, h: 7.5, fill: { color: C.text1 }, line: { type: "none" }, objectName: "results-panel" });
  const chartBase = (title) => ({
    barDir: "bar", showTitle: true, title, titleFontFace: "+mn-lt", titleFontSize: 12, titleColor: "E8EBE9",
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontFace: "+mn-lt", dataLabelFontSize: 14, dataLabelColor: "E8EBE9", dataLabelFontBold: true,
    catAxisLabelColor: "9AA3A7", catAxisLabelFontFace: "+mn-lt", catAxisLabelFontSize: 11, catAxisLineShow: false,
    valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false,
    chartColors: ["4A5156", "FF5B14"], barGapWidthPct: 45, plotArea: { fill: { color: "16191B" } },
  });
  s.addChart(pres.ChartType.bar, [{ name: "Step accuracy", labels: ["Model every 5 s", "Praxis"], values: [48, 54] }],
    { ...chartBase("Step accuracy · same frontier model"), x: 0.5, y: 0.7, w: 6.2, h: 2.7, valAxisMaxVal: 70, valAxisMinVal: 0, dataLabelFormatCode: '0"%"', objectName: "chart-accuracy" });
  s.addChart(pres.ChartType.bar, [{ name: "Cost per video-minute", labels: ["Model every 5 s", "Praxis"], values: [0.085, 0.018] }],
    { ...chartBase("Cost per minute of video"), x: 0.5, y: 3.9, w: 6.2, h: 2.7, valAxisMaxVal: 0.11, valAxisMinVal: 0, dataLabelFormatCode: '"$"0.000', objectName: "chart-cost" });
  s.addText("RESULTS", { placeholder: "eyebrow" });
  s.addText("Same frontier model. Better tracking at a fifth of the cost", { placeholder: "title" });
  const rows = [
    { y: 3.25, big: "54%", vs: "vs 48%", cap: "step accuracy with our state tracker, versus calling the model every 5 seconds" },
    { y: 4.85, big: "$0.018", vs: "vs $0.085", cap: "per minute of video" },
  ];
  rows.forEach((r, i) => {
    line(s, 7.85, r.y, 12.83, r.y, { color: C.text1, width: 1.5, name: `result-rule-${i + 1}` });
    s.addText([
      { text: r.big, options: { fontFace: THEME.headFontFace, fontSize: 36, color: i === 0 ? C.accent2 : C.text1 } },
      { text: "  " + r.vs, options: { fontFace: THEME.headFontFace, fontSize: 18, color: C.text2 } },
    ], { x: 7.85, y: r.y + 0.12, w: 4.98, h: 0.65, margin: 0, valign: "middle", isTextBox: true, objectName: `result-${i + 1}` });
    s.addText(r.cap, { x: 7.85, y: r.y + 0.8, w: 4.98, h: 0.6, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: `result-${i + 1}-caption` });
  });
  footer(s, 9, "48 held-out clips · results/runs/fused_oracle.json", 7.85);
  s.addNotes("Like-for-like: the same frontier model, the same frames. Called every 5 seconds without state it tracks the step 48% of the time. With our layers around it, 54%, and about 5x cheaper because most checks never leave the device. These were measured on 48 held-out first-person clips from a public cooking dataset (CaptainCook4D). Say so if asked: procedures are procedures; the maintenance pilot is what we want to fund.");
}

// ---------- 10 · Backup cover (B: construction grid) ----------
pres.addSection({ title: "Backup" });
{
  const s = pres.addSlide({ masterName: "Praxis Dark Grid", sectionTitle: "Backup" });
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
