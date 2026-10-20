// Praxis · Harvard Ventures Demo Day deck. Editable .pptx built with pptxgenjs, in the Praxis brand (brand/BRAND.md).
// The story follows the Sequoia outline (purpose, problem, solution, why now, market size, competition, product,
// business model, team, financials) plus the future, and keeps the technical depth in the appendix for Q&A.
// It shares the S@H deck's brand, assets, HUD helpers and numbers (deck/build_deck.js, docs/CLAIMS.md), with new
// layouts and one new device: the progress bar at the top that lights the current section, like the HUD does.
//   cd deck-hv && python3 make_tiles.py && node build_hv.js
const path = require("path");
const fs = require("fs");
const ROOT = path.resolve(__dirname, "..");
const NM = path.join(ROOT, "deck", "node_modules"); // reuse the S@H deck's install
const pptxgen = require(path.join(NM, "pptxgenjs"));
const JSZip = require(path.join(NM, "jszip"));

const OUT = process.argv[2] || path.join(__dirname, "Praxis_HV_DemoDay.pptx");
const TJ = JSON.parse(fs.readFileSync(path.join(__dirname, "assets", "tiles.json"), "utf8"));

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

const A = (f) => path.join(ROOT, "brand", "deck", "v1", "assets", f); // brand photos, logos, grid
const D = (f) => path.join(ROOT, "deck", "assets", f); // S@H deck: cover photo, screenshots, demo videos
const H = (f) => path.join(__dirname, "assets", f); // this deck: cropped tiles
const P = (px) => px / 144; // 1920-px photo coordinates → inches

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
const HEAD = THEME.headFontFace;
const SEMI = "Archivo SemiBold";
const LABEL = SEMI; // spaced labels; no monospace anywhere (as in the S@H deck)
const BODY = "3C4347";
const HUD = { ink: "16191B", text: "E8EBE9", orange: "FF5B14", green: "3DD68C", red: "D92D20", plate: "F6F7F6" };
const LOCKUP_RATIO = 2400 / 499;
const MARK_RATIO = 38 / 48;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "Praxis · Harvard Ventures Demo Day";
pres.author = "Monish Saravana";
pres.company = "Praxis";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

// Slides are functions; the runner at the bottom sets the order, the section number (CUR) and, in the appendix, the
// label (APX). Sources go into the speaker notes, not onto the slides.
const SECTIONS = ["Company purpose", "Problem", "Solution", "Why now", "Market size", "Competition", "Product", "Business model", "Team", "Financials", "Future"];
let SECTION = null, CUR = 0, APX = null;
const addSlideRaw = pres.addSlide.bind(pres);
const ALL_SLIDES = [];
pres.addSlide = (o = {}) => {
  const sl = addSlideRaw({ ...o, sectionTitle: SECTION });
  sl._rawNotes = sl.addNotes.bind(sl);
  sl.addNotes = (t, src) => { sl._notes = t; if (src) sl._src = src; return sl; };
  ALL_SLIDES.push(sl);
  return sl;
};

// ---------- masters ----------
const titlePh = (color, size = 28) => ({
  placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.85, w: 12.33, h: 1.0, fontFace: HEAD, fontSize: size, color, align: "left", valign: "top", margin: 0, lineSpacingMultiple: 0.95 }, text: "Slide title" },
});
pres.defineSlideMaster({ title: "HV Light", background: { color: C.background2 }, objects: [titlePh(C.text1)] });
pres.defineSlideMaster({ title: "HV Dark", background: { color: C.text1 }, objects: [titlePh(C.background2)] });
pres.defineSlideMaster({ title: "HV Grid", background: { path: A("bg-grid-dark.png") }, objects: [titlePh(C.background2, 32)] });
pres.defineSlideMaster({ title: "HV Photo", background: { color: C.text1 }, objects: [] });

// ---------- basics ----------
const tb = (slide, t, o) => slide.addText(t, { margin: 0, valign: "top", isTextBox: true, fontSize: 16, color: C.text1, ...o });
const label = (slide, t, o) => tb(slide, t, { fontFace: LABEL, fontSize: 10.5, charSpacing: 2, color: C.text2, ...o });
function line(slide, x1, y1, x2, y2, opts) {
  const o = { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1), line: { color: opts.color, width: opts.width || 1.5, dashType: opts.dash || "solid", endArrowType: opts.arrow ? "triangle" : undefined }, objectName: opts.name };
  if (x2 < x1) o.flipH = true;
  if (y2 < y1) o.flipV = true;
  slide.addShape(pres.ShapeType.line, o);
}
const rect = (slide, x, y, w, h, color, name, o = {}) => slide.addShape(pres.ShapeType.rect, { x, y, w, h, fill: { color }, line: { type: "none" }, objectName: name, ...o });
const panel = (slide, x, y, w, h, color, name, o = {}) => slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.05, fill: { color }, line: { type: "none" }, objectName: name, ...o });
const dot = (slide, x, y, d, color, name = "dot") => slide.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color }, line: { type: "none" }, objectName: name });
const runs = (pairs, gap = 10) => pairs.flatMap(([a, b], i) => [{ text: a, options: { fontFace: SEMI } }, { text: b, options: { breakLine: i < pairs.length - 1, paraSpaceAfter: gap } }]);
const G2 = { x: [0.5, 6.9], w: 5.93 };
const G3 = { x: [0.5, 4.745, 8.99], w: 3.84 };

// The progress bar: section number and name on the left, one segment per section on the right, the current one lit
// in orange (the HUD's progress pill, as deck chrome). Lockup bottom left, slide count bottom right.
function chrome(s, dark) {
  const ink = dark ? "E8EBE9" : "16191B", rest = dark ? "3A4044" : "C2C8C5", muted = dark ? "9AA3A7" : "5E676C";
  const head = APX ? [{ text: "APPENDIX  ", options: { color: C.accent1 } }, { text: APX }]
    : [{ text: `${String(CUR).padStart(2, "0")}  `, options: { color: C.accent1 } }, { text: SECTIONS[CUR - 1].toUpperCase() }];
  label(s, head, { x: 0.5, y: 0.38, w: 6, h: 0.3, color: muted, valign: "middle", objectName: "section-label" });
  if (!APX) {
    const n = SECTIONS.length, sw = 0.3, gap = 0.06, x0 = 12.83 - (n * sw + (n - 1) * gap);
    for (let i = 0; i < n; i++) rect(s, x0 + i * (sw + gap), 0.495, sw, 0.07, i + 1 === CUR ? "FF5B14" : i + 1 < CUR ? ink : rest, "progress-segment");
  }
  s.addImage({ path: A(dark ? "praxis-lockup-white.png" : "praxis-lockup.png"), x: 0.5, y: 6.98, h: 0.2, w: 0.2 * LOCKUP_RATIO, objectName: "logo" });
  label(s, APX ? "HARVARD VENTURES · DEMO DAY" : `${String(CUR).padStart(2, "0")} / ${SECTIONS.length}`, { x: 8.83, y: 6.95, w: 4, h: 0.26, fontSize: 9.5, charSpacing: 1, color: muted, align: "right", valign: "middle", objectName: "slide-count" });
}
function slide(kind = "light") {
  const s = pres.addSlide({ masterName: { light: "HV Light", dark: "HV Dark", grid: "HV Grid", photo: "HV Photo" }[kind] });
  if (kind !== "photo") chrome(s, kind !== "light");
  return s;
}
// rule, big number or word, caption
function hero(s, x, y, w, big, cap, o = {}) {
  const size = o.size || 54, bh = (size / 72) * 1.2;
  line(s, x, y, x + w, y, { color: o.rule || C.text1, width: 1.5, name: "hero-rule" });
  tb(s, big, { x, y: y + 0.2, w, h: bh, fontFace: HEAD, fontSize: size, color: o.color || C.text1, objectName: "hero" });
  tb(s, cap, { x, y: y + 0.28 + bh, w: w - 0.15, h: o.capH || 1.0, fontSize: o.capSize || 16, color: o.capColor || BODY, objectName: "hero-caption" });
}

// ---------- HUD helpers (from the S@H deck), for the full-bleed cover photo ----------
function hudProgress(s, step, total, x, y = 56, textW = 137) {
  const markW = 56 * MARK_RATIO, w = 22 + markW + 18 + textW + 26;
  s.addShape(pres.ShapeType.roundRect, { x: P(x), y: P(y), w: P(w), h: P(88), rectRadius: P(14), fill: { color: HUD.ink, transparency: 20 }, line: { type: "none" }, objectName: "hud-progress" });
  s.addImage({ path: A(`prog-hud-${step}of${total}.png`), x: P(x + 22), y: P(y + 16), w: P(markW), h: P(56), objectName: "hud-progress-mark" });
  tb(s, `STEP ${step}/${total}`, { x: P(x + 22 + markW + 18), y: P(y), w: P(textW + 20), h: P(88), fontFace: LABEL, fontSize: 13, charSpacing: 1, color: HUD.text, valign: "middle", objectName: "hud-progress-text" });
}
function hudChip(s, text, textW) {
  const h = 96, w = textW + 88, x0 = 1848 - w, y0 = 1016 - h;
  s.addShape(pres.ShapeType.roundRect, { x: P(x0), y: P(y0), w: P(w), h: P(h), rectRadius: P(10), fill: { color: HUD.ink, transparency: 14 }, line: { type: "none" }, objectName: "hud-chip" });
  rect(s, P(x0), P(y0), P(8), P(h), HUD.orange, "hud-chip-edge");
  tb(s, text, { x: P(x0 + 38), y: P(y0), w: P(w - 50), h: P(h), fontFace: SEMI, fontSize: 20, color: HUD.text, valign: "middle", objectName: "hud-chip-text" });
  return [x0, y0, x0 + w, y0 + h];
}
function hudLeader(s, src, reg, color) {
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const [rx0, ry0, rx1, ry1] = reg, [sx0, sy0, sx1, sy1] = src;
  const cx = (rx0 + rx1) / 2, cy = (ry0 + ry1) / 2;
  let ax = clamp(cx, sx0 + 24, sx1 - 24), ay = clamp(cy, sy0, sy1);
  if (sy0 < cy && cy < sy1) ax = cx < sx0 ? sx0 : sx1;
  let bx = clamp(ax, rx0 + 30, rx1 - 30), by = clamp(ay, ry0, ry1);
  if (ry0 < ay && ay < ry1) bx = ax < rx0 ? rx0 : rx1;
  line(s, P(ax), P(ay), P(bx), P(by), { color, width: 2, name: "hud-leader" });
  dot(s, P(ax - 7), P(ay - 7), P(14), color, "hud-leader-start");
  s.addShape(pres.ShapeType.ellipse, { x: P(bx - 11), y: P(by - 11), w: P(22), h: P(22), fill: { color }, line: { color: HUD.ink, width: 1.5 }, objectName: "hud-leader-dot" });
}
function ring(s, cx, cy, r, color, width, transparency = 0) {
  s.addShape(pres.ShapeType.ellipse, { x: cx - r, y: cy - r, w: 2 * r, h: 2 * r, fill: { type: "none" }, line: { color, width, transparency }, objectName: "hud-verify-pulse" });
}
function conceptTag(s) {
  const w = 446 * 0.69 + 28;
  s.addShape(pres.ShapeType.roundRect, { x: P(1848 - w), y: P(1032), w: P(w), h: P(34), rectRadius: P(6), fill: { color: HUD.ink, transparency: 40 }, line: { type: "none" }, objectName: "concept-tag" });
  tb(s, "CONCEPT MOCK · STOCK PHOTO", { x: P(1848 - w), y: P(1032), w: P(w), h: P(34), fontFace: LABEL, fontSize: 8, charSpacing: 1, color: "C9CFCC", align: "center", valign: "middle", objectName: "concept-tag-text" });
}

// ---------- HUD on a cropped photo tile (Solution slide); tile pixels come from make_tiles.py ----------
const TILE = { w: 3.94, h: 3.2 }; // must match make_tiles.py
function hudTile(s, name, x, y, hud) {
  const t = TJ[name], k = TILE.w / t.crop_w;
  const X = (px) => x + (px - t.x0) * k, Y = (py) => y + (py - t.y0) * k;
  s.addImage({ path: H(`${name}.jpg`), x, y, w: TILE.w, h: TILE.h, objectName: name });
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
      { text: hud.card[0], options: { fontFace: LABEL, fontSize: 8.5, charSpacing: 1, color: C.accent5, breakLine: true, paraSpaceAfter: 3 } },
      { text: hud.card[1], options: { fontFace: SEMI, fontSize: 13, color: HUD.ink, breakLine: true, paraSpaceAfter: 2 } },
      { text: hud.card[2], options: { fontSize: 11, color: BODY } },
    ], { x: bx + 0.17, y: by + 0.14, w: bw - 0.3, h: h - 0.2, objectName: "hud-card-text" });
    box = [bx, by, bx + bw, by + h];
  } else {
    const h = hud.chipLabel ? 0.62 : 0.44, by = hud.top ? y + 0.14 : y + TILE.h - 0.14 - h;
    s.addShape(pres.ShapeType.roundRect, { x: bx, y: by, w: bw, h, rectRadius: 0.05, fill: { color: HUD.ink, transparency: 14 }, line: { type: "none" }, objectName: "hud-chip" });
    rect(s, bx, by, 0.05, h, hud.color, "hud-chip-edge");
    const t2 = [];
    if (hud.chipLabel) t2.push({ text: hud.chipLabel, options: { fontFace: LABEL, fontSize: 8.5, charSpacing: 1, color: HUD.green, breakLine: true, paraSpaceAfter: 3 } });
    t2.push({ text: hud.chip, options: { fontFace: SEMI, fontSize: 12.5, color: HUD.text } });
    tb(s, t2, { x: bx + 0.2, y: by, w: bw - 0.3, h, valign: "middle", objectName: "hud-chip-text" });
    box = [bx, by, bx + bw, by + h];
  }
  // leader: from the chip or card edge straight to the region, ending in the logo's dot
  const lx = Math.max(box[0] + 0.15, Math.min(box[2] - 0.15, (reg[0] + reg[2]) / 2));
  const [ay, by2] = box[1] > reg[3] ? [box[1], reg[3]] : [box[3], reg[1]];
  line(s, lx, ay, lx, by2, { color: hud.color, width: 1.5, name: "hud-leader" });
  dot(s, lx - 0.035, ay - 0.035, 0.07, hud.color, "hud-leader-start");
  s.addShape(pres.ShapeType.ellipse, { x: lx - 0.06, y: by2 - 0.06, w: 0.12, h: 0.12, fill: { color: hud.color }, line: { color: HUD.ink, width: 1 }, objectName: "hud-leader-dot" });
}

// ---------- video (the live repair session, rendered from the session log) ----------
const VID = (f) => D(path.join("video", f));
const poster = (f) => "data:image/png;base64," + fs.readFileSync(VID(f)).toString("base64");
function video(s, name, x, y, w) {
  const h = (w * 9) / 16;
  s.addMedia({ type: "video", path: VID(`${name}.mp4`), cover: poster(`${name}_poster.png`), x, y, w, h, objectName: "demo-video" });
  return y + h;
}

// ================================================================== CORE
// 01 · Company purpose (the cover)
function sCover() {
  const s = slide("photo");
  s.addImage({ path: D("photo-cover-clean.jpg"), x: 0, y: 0, w: 13.333, h: 7.5, objectName: "photo" });
  s.addImage({ path: A("praxis-lockup-white.png"), x: 0.5, y: 0.55, h: 0.4, w: 0.4 * LOCKUP_RATIO, objectName: "logo" });
  tb(s, "Instructions that can finally see how you're doing", { x: 0.5, y: 2.05, w: 5.6, h: 2.4, fontFace: HEAD, fontSize: 40, color: C.background2, valign: "middle", lineSpacingMultiple: 0.95, objectName: "cover-headline" });
  tb(s, "Praxis is an AI coach in smart glasses. It watches new maintenance technicians work and tells them the next step.", { x: 0.5, y: 4.6, w: 5.3, h: 1.0, fontSize: 17, color: C.background2, objectName: "cover-purpose" });
  label(s, "HARVARD VENTURES · DEMO DAY · OCTOBER 2026 · MONISH SARAVANA", { x: 0.5, y: 6.93, w: 7, h: 0.3, fontSize: 10, charSpacing: 1, color: C.accent6, valign: "middle", objectName: "cover-meta" });
  const reg = [860, 640, 1180, 900];
  s.addShape(pres.ShapeType.roundRect, { x: P(reg[0]), y: P(reg[1]), w: P(reg[2] - reg[0]), h: P(reg[3] - reg[1]), rectRadius: P(22), fill: { type: "none" }, line: { color: HUD.text, width: 2.6 }, objectName: "hud-target" });
  ring(s, P(1010), P(790), P(44), HUD.text, 3.5);
  ring(s, P(1010), P(790), P(72), HUD.text, 2, 55);
  hudProgress(s, 4, 9, 1848 - 247);
  hudLeader(s, hudChip(s, "Seat the clamp past the hose bead", 624), reg, HUD.orange);
  conceptTag(s);
  s.addNotes("3-MIN: \"I'm Monish. Praxis is an AI coach that lives in smart glasses. It watches a new maintenance tech work and tells them the next step.\"\n\nThe photo is stock with a mocked-up HUD (it says so in the corner). The engine behind it is real, and the product slide shows it running on real repair footage.");
}

// 02 · Problem
function sProblem() {
  const s = slide("light");
  s.addText("A new maintenance tech needs a year of a senior\ntech's time before they can work alone", { placeholder: "title" });
  [
    ["9–14", "months before a new tech pays for themselves, in a survey of 35 repair stations", C.accent2],
    ["$10–15k", "to hire and ramp up one maintenance tech, counting onboarding and lost work", C.text1],
    ["255k", "openings a year for US maintenance and repair techs. Each one pulls a senior tech off the floor", C.text1],
  ].forEach(([b, c, col], i) => hero(s, G3.x[i], 2.1, G3.w, b, c, { color: col, capH: 0.9 }));
  // an outreach reply, quoted by kind of organization: they answered a student-project email, not a pitch
  rect(s, 0.5, 4.29, 0.06, 0.34, HUD.orange, "quote-edge");
  tb(s, [
    { text: "“The hardest AND most expensive part is training new techs …”", options: { fontFace: SEMI, fontSize: 15, color: C.text1 } },
    { text: "     HOSPITAL STERILE PROCESSING ASSOCIATION · OCT 2026", options: { fontFace: LABEL, fontSize: 9, charSpacing: 1, color: C.text2 } },
  ], { x: 0.72, y: 4.29, w: 12.1, h: 0.34, valign: "middle", objectName: "quote" });
  label(s, "HOW SHOPS HANDLE IT TODAY", { x: 0.5, y: 4.8, w: 6, h: 0.3, color: C.text1 });
  [
    ["Shadowing", "A senior tech stands next to the new hire", "About $44 an hour of senior time, for one new tech at a time"],
    ["Binders, PDFs, YouTube", "They explain what should happen", "They can't see what the tech is actually doing"],
    ["Procedure apps", "Steps on a phone, with a checkbox", "A ticked box isn't proof the step was done right"],
  ].forEach(([h, d, miss], i) => {
    const x = G3.x[i], y = 5.15, w = G3.w;
    panel(s, x, y, w, 1.62, C.background1, `today-${i + 1}`);
    tb(s, [{ text: h, options: { fontFace: SEMI, fontSize: 15, color: C.text1, breakLine: true, paraSpaceAfter: 2 } }, { text: d, options: { fontSize: 12.5, color: BODY } }], { x: x + 0.25, y: y + 0.17, w: w - 0.5, h: 0.65 });
    line(s, x + 0.25, y + 0.88, x + w - 0.25, y + 0.88, { color: "C2C8C5", width: 0.75, name: "today-rule" });
    tb(s, [{ text: "MISSES  ", options: { fontFace: LABEL, fontSize: 9, charSpacing: 1, color: C.accent5 } }, { text: miss }], { x: x + 0.25, y: y + 0.98, w: w - 0.5, h: 0.6, fontSize: 12.5 });
  });
  s.addNotes(
    "3-MIN: \"Every new maintenance tech learns by shadowing a senior tech for most of a year. Shops are hiring about 255,000 of them a year in the US, and each one takes a senior tech off the floor. When I asked a hospital sterile processing association this week, they said training new techs is the hardest and most expensive part.\"\n\n" +
    "ARSA surveyed 35 repair stations: new hires took 9 to 14 months on average to become profitable, some up to 24. Reliability magazine puts hiring and ramping up one maintenance tech at $10,000-15,000 once onboarding and lost productivity are counted (a trade estimate, not a study). BLS says on-the-job training for these jobs typically lasts more than a year. $44 an hour is a senior tech's loaded cost (BLS median wage divided by the 70% wage share of employer cost). Manuals and videos can't see the work, and an app's checkbox isn't proof, so the senior tech stays the real teacher.\n\n" +
    "The quote is a reply to our outreach on Oct 19 from HSPA, the professional association for hospital sterile processing techs, who clean and check surgical instruments. The full line: new techs take significant one-to-one time to train, and bad cleaning technique damages expensive instruments. Don't name them on stage: they answered a student-project email, and it's the profession's view, not a customer's. If asked \"why not just videos?\": a fiber-optic training school replied the same day that it already demos every lab and records a video of each, and students still forget quickly once class ends.",
    "ARSA member survey of 35 repair stations, 2017 · Reliability magazine (A. Gager) · BLS Occupational Outlook Handbook · BLS ECEC (wage share) · outreach replies, Oct 19 2026 (docs/OUTREACH.md)");
}

// 03 · Solution
function sSolution() {
  const s = slide("light");
  s.addText("Praxis watches the work and coaches\none step at a time", { placeholder: "title" });
  tb(s, "The shop uploads the manuals it already has. The new tech wears smart glasses. Praxis follows along.", { x: 0.5, y: 1.92, w: 12.33, h: 0.4, fontSize: 16, color: BODY });
  const gap = (12.33 - 3 * TILE.w) / 2, ty = 2.88;
  [
    ["Says the next step", "FF5B14", "tile-step", { color: HUD.orange, chip: "Loosen the four float-bowl screws" }],
    ["Checks the work", C.accent3, "tile-verified", { color: HUD.green, chipLabel: "STEP 5 VERIFIED · VALVE LASH SET", chip: "Next: rotate the crank to TDC", top: true, pulse: [660, 740] }],
    ["Catches mistakes", C.accent5, "tile-mistake", { color: HUD.red, card: ["MISTAKE CAUGHT", "Lockout was skipped.", "Lock and tag the feeder breaker first."] }],
  ].forEach(([head, col, name, hud], i) => {
    const x = 0.5 + i * (TILE.w + gap);
    dot(s, x, 2.5, 0.28, col, "tile-badge");
    tb(s, String(i + 1), { x, y: 2.5, w: 0.28, h: 0.28, fontFace: SEMI, fontSize: 11, color: "FFFFFF", align: "center", valign: "middle" });
    tb(s, head, { x: x + 0.4, y: 2.47, w: TILE.w - 0.4, h: 0.34, fontFace: SEMI, fontSize: 15, valign: "middle" });
    hudTile(s, name, x, ty, hud);
  });
  const by = 6.3;
  label(s, "BUILT FOR", { x: 0.5, y: by, w: 1.3, h: 0.3, color: C.text1, valign: "middle" });
  tb(s, "HVAC service · facilities teams · plant maintenance · equipment repair", { x: 1.75, y: by, w: 5.6, h: 0.3, fontSize: 13, color: BODY, valign: "middle" });
  label(s, "CONNECTS TO", { x: 7.55, y: by, w: 1.6, h: 0.3, color: C.text1, valign: "middle" });
  tb(s, "Meta and Viture + NVIDIA smart glasses", { x: 9.1, y: by, w: 3.73, h: 0.3, fontSize: 13, color: BODY, valign: "middle" });
  label(s, "CONCEPT MOCKS · STOCK PHOTOS", { x: 6.0, y: 6.95, w: 5.8, h: 0.26, fontSize: 8, charSpacing: 1, color: C.accent6, align: "right", valign: "middle" });
  s.addNotes("3-MIN: \"A shop uploads the manuals it already has. The new tech wears smart glasses, and Praxis follows along: it says the next step, checks the work, and catches mistakes, like a skipped lockout.\"\n\n" +
    "Software, not hardware: it runs on glasses a shop can buy. It speaks one short line at a time, and cards appear only for mistakes and view requests. The buyer is the maintenance manager; the user is the new tech. The photos are stock with a mocked-up HUD. Mistake detection is our weakest number today (in the eval, 4 of 17 alerts named a real annotated error), so if asked, say it plainly. The Meta and Viture connections are built but not yet tested on the devices; say that out loud if asked.");
}

// 04 · Why now
function sWhyNow() {
  const s = slide("light");
  s.addText("Smart glasses took off, and AI got 1,000×\ncheaper. A coach that sees is finally possible", { placeholder: "title" });
  label(s, "HOW A NEW TECH LEARNS A PROCEDURE", { x: 0.5, y: 2.22, w: 8, h: 0.3, color: C.text1 });
  const stages = [["Paper binders", "Read it, then do it"], ["Videos and PDFs", "Watch it, then do it"], ["Procedure apps", "Tick a box when done"], ["A coach that sees", "It watches you do it"]];
  const cw = 2.7, aw = 0.51;
  stages.forEach(([h, c], i) => {
    const x = 0.5 + i * (cw + aw), now = i === 3;
    s.addText(h, { shape: pres.ShapeType.roundRect, x, y: 2.6, w: cw, h: 0.62, rectRadius: 0.06, fill: { color: now ? "FFFFFF" : C.background1 }, line: now ? { color: C.accent1, width: 1.75 } : { color: "C2C8C5", width: 0.75 }, fontFace: SEMI, fontSize: 14.5, color: now ? C.accent2 : C.text1, align: "center", valign: "middle", margin: 0, objectName: "stage" });
    tb(s, c, { x, y: 3.3, w: cw, h: 0.3, fontSize: 12.5, color: BODY, align: "center" });
    if (i < 3) line(s, x + cw + 0.1, 2.91, x + cw + aw - 0.1, 2.91, { color: i === 2 ? C.accent1 : "9AA3A7", width: 1.5, arrow: true, name: "stage-arrow" });
  });
  [
    ["7×", "more AI glasses shipped in two years: about 2.1M in 2024 to 15M+ forecast in 2026. Every pair is a camera we can run on"],
    ["1,000×", "cheaper AI in three years: the same capability fell from $60 to $0.06 per million tokens, so watching a whole shift is affordable"],
    ["$3.6B", "what Autodesk agreed to pay for MaintainX, a maintenance app, in May 2026. In September, Meta opened its glasses' camera to outside apps"],
  ].forEach(([b, c], i) => hero(s, G3.x[i], 4.15, G3.w, b, c, { size: 40, capSize: 13.5, capH: 1.2 }));
  s.addNotes("3-MIN: \"Two things changed this year: cameras moved onto faces, and AI got cheap enough to watch a whole shift. And the money is already here: Autodesk is paying $3.6 billion for a maintenance app.\"\n\n" +
    "Omdia counts 8.7M AI glasses shipped in 2025, up 322%, and forecasts more than 15M in 2026, about 7x in two years (2024 is backed out from the growth rate). a16z measured the price of GPT-3-level capability falling from $60 per million tokens at launch in 2021 to $0.06 in 2024, about 10x a year. Meta's camera toolkit lets a third-party app use the glasses' camera, mic and speakers. Why not 2023: no glasses let apps read the camera, and coaching cost more than its price. Our own design adds to the trend: Praxis only asks a model when something happens, about $1.08 an hour of video vs $5.10 for calling a frontier model every 5 seconds.",
    "Omdia (2025 shipments, +322%; 2026 forecast) · a16z, LLMflation (Nov 2024) · Autodesk–MaintainX release (28 May 2026) · Meta Wearables Device Access Toolkit");
}

// 05 · Market size
function sMarket() {
  const s = slide("light");
  s.addText("A $306M wedge in a $1.8B first market,\ninside a $9B one", { placeholder: "title" });
  const rows = [
    ["TAM", 9.2, "$9.2B", "15.4M US workers who follow written procedures", "C9CFCC"],
    ["SAM", 1.8, "$1.8B", "2.47M US maintenance and repair techs", "9AA3A7"],
    ["WEDGE", 0.306, "$306M", "~255k new maintenance techs a year, coached", "FF5B14"],
    ["YEAR 3", 0.0045, "$4.5M ARR", "~3,750 new techs, about 150 teams", "16191B"],
  ];
  // nested squares, area to scale, sharing the bottom-left corner
  const side0 = 4.3, k = side0 / Math.sqrt(9.2), bx = 0.5, by = 6.6;
  rows.forEach(([key, v, , , col], i) => {
    const sd = Math.max(0.09, k * Math.sqrt(v));
    rect(s, bx, by - sd, sd, sd, col, `square-${key.toLowerCase()}`);
    if (i < 2) label(s, key, { x: bx + 0.15, y: by - sd + 0.13, w: 1.2, h: 0.26, fontSize: 10, color: C.text1 });
  });
  const lx = 5.3, lw = 3.6;
  rows.forEach(([key, , big, cap, col], i) => {
    const y = 2.3 + i * 1.08;
    rect(s, lx, y + 0.13, 0.22, 0.22, col, "legend-swatch");
    tb(s, [{ text: `${big}  `, options: { fontFace: HEAD, fontSize: 20, color: key === "WEDGE" ? C.accent2 : C.text1 } }, { text: key, options: { fontFace: LABEL, fontSize: 10, charSpacing: 2, color: C.text2 } }], { x: lx + 0.38, y, w: lw - 0.38, h: 0.45, valign: "middle" });
    tb(s, cap, { x: lx + 0.38, y: y + 0.5, w: lw - 0.38, h: 0.5, fontSize: 12.5, color: BODY });
  });
  const px = 9.25, pw = 3.58, py = 2.3, ph = 4.3;
  panel(s, px, py, pw, ph, C.text1, "panel-customer");
  [
    ["WHO BUYS", "Maintenance managers at mid-size plants, facilities teams, and HVAC and equipment-service shops"],
    ["WHO USES IT", "The new tech, for their first six months on the job"],
    ["WHY THEY PAY", "A seat costs less than one hour a week of the senior tech who would otherwise teach them"],
  ].forEach(([k2, b], i) => {
    const y = py + 0.3 + i * 1.33;
    if (i) line(s, px + 0.35, y - 0.17, px + pw - 0.35, y - 0.17, { color: "3A4044", width: 0.75, name: "customer-rule" });
    tb(s, [{ text: k2, options: { fontFace: LABEL, fontSize: 10, charSpacing: 2, color: C.accent1, breakLine: true, paraSpaceAfter: 5 } }, { text: b, options: { fontSize: 13.5, color: C.background2 } }], { x: px + 0.35, y, w: pw - 0.7, h: 1.1 });
  });
  s.addNotes("3-MIN: \"We start with new maintenance techs: a $306 million wedge, inside $1.8 billion for every maintenance tech in the US, inside $9 billion for everyone who works from written procedures.\"\n\n" +
    "Squares are to scale by area. TAM: 15.4M US workers who follow written procedures (installation, maintenance and repair 6.09M; electricians 0.76M; production 8.57M), at $50 a month for verified records, about $9.2B. SAM: 2.47M US maintenance and repair techs, coaching for new hires plus records for everyone, about $1.8B. Wedge: about 255,000 new maintenance techs a year coached for six months at $200 a month, about $306M. Year 3 target (a goal, not a forecast): 1.5% of new techs, about 3,750 across 150 teams, $4.5M ARR. Prices are our hypotheses, anchored on Tulip's $100-250 per station a month. Openings include people changing jobs, so new-tech counts are an upper bound. Not counted: other countries, aviation, field service outside these groups, robotics. Full math in the appendix.",
    "BLS OEWS national tables, May 2025 · BLS Occupational Outlook Handbook · prices are our hypotheses · year 3 is a goal");
}

// 06 · Competition
function sCompetition() {
  const s = slide("light");
  s.addText("Every option today is missing a piece", { placeholder: "title" });
  const crit = [["Sees the work", "a camera on the job"], ["Moves with the tech", "not bolted to one station"], ["Knows the step you're on", "follows the procedure"], ["No filming to set up", "nothing to record or train"]];
  const rows = [
    ["Procedure apps", "MaintainX, Dozuki", [0, 1, 1, 1]],
    ["Fixed cameras", "Retrocausal, Invisible AI", [1, 0, 1, 0]],
    ["First-person AI glasses", "Strivr", [1, 1, 1, 0]],
    ["General AI assistants", "Meta AI, Gemini Live", [1, 1, 0, 1]],
    ["Praxis", "", [1, 1, 1, 1]],
  ];
  const nameW = 3.6, cw = (12.33 - nameW) / 4, hy = 1.75, y0 = 2.72, rh = 0.62, step = 0.72;
  crit.forEach(([h, sub], j) => tb(s, [{ text: h, options: { fontFace: SEMI, fontSize: 13.5, color: C.text1, breakLine: true } }, { text: sub, options: { fontSize: 11, color: BODY } }], { x: 0.5 + nameW + j * cw, y: hy + 0.15, w: cw, h: 0.6, align: "center" }));
  line(s, 0.5, 2.6, 12.83, 2.6, { color: C.text1, width: 1.5, name: "grid-rule" });
  rows.forEach(([name, ex, has], i) => {
    const y = y0 + i * step, ours = name === "Praxis";
    if (ours) {
      rect(s, 0.5, y, 12.33, rh, C.background1, "row-ours");
      rect(s, 0.5, y, 0.06, rh, "FF5B14", "row-ours-edge");
    } else line(s, 0.5, y + rh + 0.04, 12.83, y + rh + 0.04, { color: "C2C8C5", width: 0.75, name: "row-rule" });
    tb(s, ex ? [{ text: name, options: { fontFace: SEMI, fontSize: 14, color: C.text1, breakLine: true } }, { text: ex, options: { fontSize: 11, color: BODY } }]
      : [{ text: name, options: { fontFace: HEAD, fontSize: 16, color: C.accent2 } }], { x: 0.75, y, w: nameW - 0.3, h: rh, valign: "middle" });
    has.forEach((v, j) => {
      const cx = 0.5 + nameW + j * cw + cw / 2, d = 0.24;
      if (v) dot(s, cx - d / 2, y + rh / 2 - d / 2, d, ours ? "FF5B14" : "16191B", "has");
      else s.addShape(pres.ShapeType.ellipse, { x: cx - d / 2, y: y + rh / 2 - d / 2, w: d, h: d, fill: { type: "none" }, line: { color: "9AA3A7", width: 1.25 }, objectName: "lacks" });
    });
  });
  const ly = 6.35;
  dot(s, 0.5, ly + 0.06, 0.16, "16191B", "legend-has");
  tb(s, "has it", { x: 0.74, y: ly, w: 0.8, h: 0.28, fontSize: 11.5, color: BODY, valign: "middle" });
  s.addShape(pres.ShapeType.ellipse, { x: 1.5, y: ly + 0.06, w: 0.16, h: 0.16, fill: { type: "none" }, line: { color: "9AA3A7", width: 1.25 }, objectName: "legend-lacks" });
  tb(s, "doesn't", { x: 1.74, y: ly, w: 0.9, h: 0.28, fontSize: 11.5, color: BODY, valign: "middle" });
  tb(s, "Coming: Viture + NVIDIA coaching glasses ship in Q1 2027. How procedures get into them isn't published.", { x: 3.0, y: ly, w: 9.83, h: 0.28, fontSize: 11.5, color: BODY, valign: "middle", align: "right" });
  s.addNotes("3-MIN: \"Apps can't see the work. Cameras are bolted to one station. The closest, Strivr, has to film and train for every customer. And Meta's and Google's assistants don't know the procedure. Praxis does all four.\"\n\n" +
    "Each mark comes from the vendor's own pages (checked 17 Oct 2026, see docs/COMPETITORS.md). Procedure apps put steps on a phone and collect sign-offs. Fixed cameras (Retrocausal, Invisible AI) track a procedure but at one station, after recording examples (Retrocausal says a couple of hours). Strivr's data team captures images and video of your procedures and trains a per-customer model; it's in early access with no published accuracy. Meta AI and Gemini Live answer questions about a frame, with no plan or state. Honest version if asked: Tulip, Augmentir and Squint also compile instructions, fixed-camera vendors are ahead of us on live mistake alerts, and we haven't compared against any of these products directly. Don't say we're the only first-person system.",
    "Vendor product pages and docs, checked 17 Oct 2026 · Strivr FAQ and platform pages · Viture Helix release (16 Jun 2026)");
}

// 07 · Product
function sProduct() {
  const s = slide("dark");
  s.addText("It already works, live, on a real repair job", { placeholder: "title" });
  video(s, "repair_demo_user", 0.5, 1.75, 7.75);
  tb(s, "Real footage from an industrial repair lab. Every card on screen is the model's own output, from the live session. 49 s, click to play.", { x: 0.5, y: 6.25, w: 7.75, h: 0.5, fontSize: 11.5, color: C.accent6 });
  const x = 8.65, w = 4.18;
  [
    ["13% more", "accurate at tracking the step than the same frontier model on its own, at 1/5 the cost", "FF5B14"],
    ["11 of 15", "technician questions on a repair job answered right from the company's own manuals", "E8EBE9"],
    ["0 times", "confidently wrong when the view was blurred or blocked. It asks for a better view instead", "E8EBE9"],
  ].forEach(([b, c, col], i) => hero(s, x, 1.75 + i * 1.6, w, b, c, { size: 30, color: col, rule: "E8EBE9", capColor: C.accent6, capSize: 13.5, capH: 0.8 }));
  s.addNotes("3-MIN: \"This is real repair footage streamed through Praxis live. It started from the lab's written procedure and was never trained on this task. Here it catches the soldering iron at 215 degrees and tells the tech to go back to 200. On our tests it's 13% more accurate than the same frontier model on its own, at a fifth of the cost.\"\n\n" +
    "Click to play; it's 49 seconds, from the ENIGMA-51 dataset (first-person industrial repair). The fast tier is Jev; Claude Opus double-checks when the fast model is unsure. 13% is relative: with the task known, Praxis names the current step 54% of the time vs 48% for the same frontier model called every 5 seconds with no memory, at $0.018 vs $0.085 per video-minute, on 48 held-out public clips (one run each). 11 of 15: technician questions on ENIGMA-51 answered from the uploaded procedures, 2 partly, 2 wrong, blind-judged. When we blurred or blocked the view, it asked for a better view on 77-98% of checks and was never confidently wrong. If asked: these are selected moments. Across the 16-minute session it confirmed 1 of 19 steps, and the overshoot alert landed about 6 seconds late. The engineer view is appendix A1.",
    "Praxis Studio live session on ENIGMA-51 video 141 · 48 held-out clips of public first-person procedure video, one run per system · ENIGMA-51 questions, blind-judged");
}

// 08 · Business model
function sBusiness() {
  const s = slide("light");
  s.addText("$200 a month per new tech. Saving a senior\ntech one hour a week pays for it", { placeholder: "title" });
  label(s, "HOW WE MAKE MONEY", { x: 0.5, y: 2.2, w: 5, h: 0.3, color: C.text1 });
  const steps = [
    ["A short paid pilot", "with a metric agreed up front. The fee counts toward year one"],
    ["$200 per new-tech seat a month", "billed annually, unlimited sessions. When the tech works alone, the seat moves to the next hire"],
    ["One-time setup per procedure", "we compile and check the shop's own manuals"],
    ["$50 a month for every tech, next", "skills records for the whole team"],
  ];
  line(s, 0.64, 2.75, 0.64, 2.75 + 3 * 0.98, { color: "9AA3A7", width: 1, name: "steps-spine" });
  steps.forEach(([h, b], i) => {
    const y = 2.62 + i * 0.98;
    dot(s, 0.5, y, 0.28, i === 1 ? "FF5B14" : "16191B", "step-badge");
    tb(s, String(i + 1), { x: 0.5, y, w: 0.28, h: 0.28, fontFace: SEMI, fontSize: 10.5, color: "FFFFFF", align: "center", valign: "middle" });
    tb(s, [{ text: h, options: { fontFace: SEMI, fontSize: 15.5, color: i === 1 ? C.accent2 : C.text1, breakLine: true, paraSpaceAfter: 2 } }, { text: b, options: { fontSize: 12.5, color: BODY } }], { x: 0.95, y: y - 0.04, w: 5.4, h: 0.9 });
  });
  const x = 6.9, w = 5.93;
  panel(s, x, 2.2, w, 1.85, C.background1, "card-payback");
  label(s, "WHY IT PAYS FOR ITSELF", { x: x + 0.35, y: 2.4, w: w - 0.7, h: 0.3, color: C.accent2 });
  let tx = x + 0.35;
  [["$200", "a month for a seat", 1.5], ["≈ $46", "a week", 1.6], ["≈ 1 hour", "of a senior tech's time ($44)", 2.13]].forEach(([b, c, tw]) => {
    tb(s, b, { x: tx, y: 2.8, w: tw, h: 0.55, fontFace: HEAD, fontSize: 26, color: C.text1 });
    tb(s, c, { x: tx, y: 3.38, w: tw - 0.1, h: 0.55, fontSize: 12.5, color: BODY });
    tx += tw;
  });
  panel(s, x, 4.3, w, 2.4, C.text1, "panel-gtm");
  label(s, "HOW WE GET CUSTOMERS", { x: x + 0.35, y: 4.52, w: w - 0.7, h: 0.3, color: C.accent1 });
  tb(s, "Outreach → demo → paid pilot → annual seats", { x: x + 0.35, y: 4.87, w: w - 0.7, h: 0.35, fontFace: SEMI, fontSize: 14, color: C.background2 });
  tb(s, [
    { text: "Direct outreach: 70 maintenance teams and programs this week", options: { bullet: { indent: 14 }, breakLine: true, paraSpaceAfter: 6 } },
    { text: "Trade schools: students bring Praxis to their first job. A fiber-optic school is open to a one-lab trial", options: { bullet: { indent: 14 }, breakLine: true, paraSpaceAfter: 6 } },
    { text: "Partners: maintenance apps, distributors, glasses makers", options: { bullet: { indent: 14 } } },
  ], { x: x + 0.35, y: 5.35, w: w - 0.7, h: 1.2, fontSize: 12.5, color: C.accent6 });
  s.addNotes("3-MIN: \"We sell a seat for each new tech: $200 a month. That's about one hour a week of the senior tech who'd otherwise teach them, so it pays for itself if it saves one hour.\"\n\n" +
    "An annual subscription after a short paid pilot whose fee counts toward year one. A new tech holds a seat for about six months; then it moves to the next new hire. Plus a one-time setup per procedure, and next, $50 per tech per month for verified skills records across the whole team. $200 a month is about $46 a week; a senior tech costs about $44 an hour loaded (BLS median wage over the 70% wage share). It costs us about $1.08 an hour of coaching to run today. Prices are hypotheses anchored on Tulip's $100-250 per station a month. Outreach: 14 emails went out Oct 17 and 56 on Oct 19 (54 delivered, 2 bounced). By the evening of Oct 19, two had replied: the sterile processing association quoted on slide 2, and a fiber-optic training school that said it's open to trying this on one lab exercise. That's a trial they're open to, not a pilot or a customer. Update the reply count before presenting. Founder-led sales first; trade schools double as how we collect training footage.",
    "Reliability magazine (hiring + ramp-up) · senior-tech hour: BLS wage ÷ wage share · pricing is our hypothesis · send log in docs/OUTREACH.md");
}

// 09 · Team
function sTeam() {
  const s = slide("light");
  s.addText("I've built real-time vision on messy video\nbefore, and I built this in a week", { placeholder: "title" });
  const px = 0.5, py = 2.2, pw = 3.9, ph = 4.5;
  s.addImage({ path: A("bg-grid-dark.png"), x: px, y: py, w: pw, h: ph, sizing: { type: "cover", w: pw, h: ph }, objectName: "founder-panel" });
  tb(s, "Monish\nSaravana", { x: px + 0.35, y: py + 1.95, w: pw - 0.7, h: 1.1, fontFace: HEAD, fontSize: 26, color: C.background2, valign: "bottom", lineSpacingMultiple: 0.95, objectName: "founder-name" });
  label(s, "FOUNDER · HARVARD COLLEGE", { x: px + 0.35, y: py + 3.2, w: pw - 0.7, h: 0.3, color: C.accent1, objectName: "founder-role" });
  tb(s, "Solo today. Next: an advisor from the maintenance trade, then first hires after the pilot.", { x: px + 0.35, y: py + 3.55, w: pw - 0.7, h: 0.75, fontSize: 11.5, color: C.accent6 });
  const x = 4.85, w = 7.98;
  [
    ["Praxis, in one week", "The engine, a 48-video evaluation and a live app, built solo. First commit Oct 17.", C.accent2],
    ["LipTrac", "Real-time lip reading from ordinary video: 60,000+ frames, 12 testers, provisional patent filed.", C.text1],
    ["7 years of robotics", "Competitive robotics, coaching teammates without seeing what they see.", C.text1],
    ["Oil-cleanup boats", "Path planning for cleanup boats from aerial imagery.", C.text1],
  ].forEach(([h, b, col], i) => {
    const y = 2.2 + i * 1.13;
    line(s, x, y, x + w, y, { color: i ? "9AA3A7" : C.text1, width: i ? 0.75 : 1.5, name: "bio-rule" });
    tb(s, h, { x, y: y + 0.17, w: 3.4, h: 0.8, fontFace: HEAD, fontSize: 17, color: col, lineSpacingMultiple: 0.95 });
    tb(s, b, { x: x + 3.55, y: y + 0.19, w: w - 3.55, h: 0.8, fontSize: 14, color: BODY });
  });
  s.addNotes("3-MIN: \"I've done seven years of competitive robotics and built real-time lip reading from ordinary video. I built this engine, its evaluation and a live app myself, in a week.\"\n\n" +
    "Solo founder is a known risk: demand comes first, then hires. Next step on the domain is to shadow a maintenance tech and recruit an advisor from the outreach replies. The provisional patent is LipTrac's. To add a photo: drop it over the dark panel on the left and send it to the back, behind the name.",
    "Startups @ Harvard application · git log");
}

// 10 · Financials
function sFinancials() {
  const s = slide("light");
  s.addText("A path to $4.5M ARR by 2029,\nat 77–90% gross margin", { placeholder: "title" });
  label(s, "ARR TARGETS", { x: 0.5, y: 2.2, w: 3, h: 0.3, color: C.text1 });
  const bars = [["2027", 0.3, "$0.3M", "10 teams"], ["2028", 1.5, "$1.5M", "50 teams"], ["2029", 4.5, "$4.5M", "150 teams"], ["2030", 13, "$13M", ""], ["2031", 30, "$30M", ""]];
  const base = 4.95, maxH = 2.1, bw = 0.78, cw = 5.6 / bars.length;
  bars.forEach(([yr, v, lab, teams], i) => {
    const h = Math.max(0.04, (maxH * v) / 30), bx = 0.5 + i * cw + (cw - bw) / 2;
    rect(s, bx, base - h, bw, h, i === 0 ? "FF5B14" : i < 3 ? "16191B" : "9AA3A7", "arr-bar");
    tb(s, lab, { x: bx - 0.3, y: base - h - 0.4, w: bw + 0.6, h: 0.34, fontFace: HEAD, fontSize: 14, color: i === 0 ? C.accent2 : C.text1, align: "center" });
    label(s, yr, { x: bx - 0.3, y: base + 0.1, w: bw + 0.6, h: 0.26, fontSize: 10, charSpacing: 1, color: C.text1, align: "center" });
    if (teams) tb(s, teams, { x: bx - 0.3, y: base + 0.36, w: bw + 0.6, h: 0.26, fontSize: 11, color: BODY, align: "center" });
  });
  line(s, 0.5, base, 6.1, base, { color: C.text1, width: 1, name: "arr-base" });
  const x = 6.9, w = 5.93;
  label(s, "PER SEAT, PER MONTH", { x, y: 2.2, w, h: 0.3, color: C.text1 });
  const maxW = 2.9, bx0 = x + 1.95;
  [["Price", 200, "$200", "9AA3A7", ""], ["Our cost today", 45, "$45", "16191B", "about 77% margin"], ["With our own model", 20, "$20", "FF5B14", "about 90% margin"]].forEach(([n, v, lab, col, m], i) => {
    const y = 2.68 + i * 0.66, bwid = (maxW * v) / 200;
    tb(s, n, { x, y, w: 1.85, h: 0.36, fontSize: 13, fontFace: SEMI, valign: "middle" });
    rect(s, bx0, y + 0.05, bwid, 0.26, col, "seat-bar");
    tb(s, [{ text: lab, options: { fontFace: HEAD, fontSize: 14, color: i === 2 ? C.accent2 : C.text1 } }, ...(m ? [{ text: `  ${m}`, options: { fontSize: 11.5, color: BODY } }] : [])], { x: bx0 + bwid + 0.12, y, w: 3.0, h: 0.36, valign: "middle" });
  });
  tb(s, "At 2 hours of coaching a day. Our own model takes the routine checks off the rented one. Heavy all-shift use squeezes a flat seat, so we'd price by coached hours.", { x, y: 4.7, w, h: 0.75, fontSize: 12, color: BODY });
  line(s, 0.5, 5.75, 12.83, 5.75, { color: C.text1, width: 1.5, name: "funds-rule" });
  label(s, "WHAT THE FIRST $10K BUYS", { x: 0.5, y: 5.88, w: 4, h: 0.3, color: C.accent2 });
  const funds = [["$3k", " GPU time"], ["$2.5k", " glasses + capture"], ["$2k", " maintenance training video"], ["$1.5k", " pilot inference"], ["$1k", " company formation"]];
  tb(s, funds.flatMap(([a, b], i) => [{ text: a, options: { fontFace: SEMI } }, { text: b + (i < funds.length - 1 ? "  ·  " : "") }]), { x: 0.5, y: 6.2, w: 12.33, h: 0.3, fontSize: 12.5, color: C.text1, valign: "middle" });
  tb(s, [{ text: "True by April: ", options: { fontFace: SEMI } }, { text: "models retrained on real maintenance video, running on glasses at a real site, and a first paid pilot." }], { x: 0.5, y: 6.52, w: 12.33, h: 0.3, fontSize: 12.5, color: BODY, valign: "middle" });
  s.addNotes("3-MIN: skip, or one line: \"Targets: $4.5 million ARR by 2029 at 77 to 90% gross margin. The first $10k gets us to a paid pilot on glasses by April.\"\n\n" +
    "These are targets, not forecasts, on the pace investors expect after year 2 (triple, triple, double). About 25 new techs a team at about $1,200 of seat time each, plus records. 2027: 10 teams from paid pilots, $0.3M. 2028: our own models, 50 teams, $1.5M. 2029: skills records, 150 teams, $4.5M (the year-3 goal on the market slide). 2030-31: about $13M then $30M, still under 2% of the $1.8B first market. Per seat at 2 hours a day: about $45 of model cost today ($0.018 per video-minute), about $20 with our local model doing routine checks ($0.008). Pricing risk: at 8 hours a day a flat $200 seat is about $1.19 an hour against our $1.08 cost, so we'd price by coached hours or tiers. No P&L or cap table yet: there's no revenue and no company yet (company formation is in the $10k). The $10k is the Startups @ Harvard grant budget, the same amounts as that application.",
    "Revenue: targets, not forecasts · unit costs from the evaluation runs (docs/CLAIMS.md) · $10k budget as in the S@H application");
}

// 11 · Future
function sFuture() {
  const s = slide("grid");
  s.addText("Today we coach the people.\nNext, the robots", { placeholder: "title" });
  const gap = 0.15, w = (12.33 - 3 * gap) / 4, ys = [3.75, 3.4, 3.05, 2.7];
  const steps = [
    ["NOW · 2027", "Coach new techs", "Paid pilots with maintenance teams. Every session becomes labeled training data.", "$0.3M · 10 teams"],
    ["NEXT · 2028", "Our own models", "Trained on our pilot footage, running on the glasses. Cheaper and better at maintenance than rented models.", "$1.5M · 50 teams"],
    ["THEN · 2029", "Certifications through Praxis", "Partner with NCCER, NIMS and equipment makers so their hands-on tests run on Praxis. Certified techs bring us their next shop.", "$4.5M · 150 teams"],
    ["LATER · 2030+", "Robots", "Train robot models on the data we've collected, or sell the data and our step checker to robot labs.", "$13M → $30M ARR"],
  ];
  steps.forEach(([k, h, body, rev], i) => {
    const x = 0.5 + i * (w + gap), y = ys[i], xe = i < 3 ? x + w + gap : x + w, now = i === 0;
    line(s, x, y, xe, y, { color: now ? "FF5B14" : "E8EBE9", width: now ? 2.5 : 1.5, name: "stair-tread" });
    if (i < 3) line(s, xe, y, xe, ys[i + 1], { color: "E8EBE9", width: 1.5, name: "stair-riser" });
    dot(s, x - 0.02, y - 0.1, 0.2, now ? "FF5B14" : "E8EBE9", "stair-dot");
    const tx = x + 0.2, tw = w - 0.3;
    label(s, k, { x: tx, y: y + 0.17, w: tw, h: 0.28, fontSize: 10, color: now ? C.accent1 : C.accent6 });
    tb(s, h, { x: tx, y: y + 0.47, w: tw, h: 0.55, fontFace: HEAD, fontSize: 15, color: C.background2, lineSpacingMultiple: 0.95 });
    const by = y + (h.length > 18 ? 1.05 : 0.85);
    tb(s, body, { x: tx, y: by, w: tw, h: 0.9, fontSize: 12, color: C.accent6 });
    tb(s, rev, { x: tx, y: by + 0.95, w: tw, h: 0.3, fontFace: SEMI, fontSize: 13, color: now ? C.accent1 : C.background2, objectName: "stair-revenue" });
  });
  line(s, 0.5, 6.12, 12.83, 6.12, { color: "3A4044", width: 0.75, name: "future-rule" });
  tb(s, [{ text: "Every session records skilled work, step by step. ", options: { fontFace: SEMI, color: C.background2 } }, { text: "Nobody else has that data, and AI labs pay billions a year for data like it." }], { x: 0.5, y: 6.27, w: 12.33, h: 0.35, fontSize: 13, color: C.accent6 });
  s.addNotes("3-MIN: \"Every coaching session is first-person video of skilled work that nobody else has. That's how we climb: coach new techs, train our own models, run the industry's skill certifications through Praxis, and then train the robots that work next to them. Thank you.\"\n\n" +
    "Gates, not dates: each step needs the last one's metric hit first. Revenue numbers are targets, not forecasts. Labs already pay for data: Mercor's run-rate selling expert data to AI labs passed $2B in June 2026 (The Information); Micro1's CEO estimates robotics companies spend over $100M a year on real-world data; Grand View Research sizes the AI training-data market at $8.6B by 2030. Robots: two options, train our own robot models, or sell the data and our 'did this step succeed?' checker to robot labs. With customers and workers, the line stays \"robots work next to you\", not \"robots replace you\".\n\n" +
    "Certifications (2029): these are the trades' version of a Microsoft Office certificate. We don't issue licenses; we partner with the bodies that already certify techs and run the hands-on part of their tests. Today a person has to watch that part: NCCER performance verifications need an NCCER-certified evaluator; NIMS maintenance credentials need a supervised hands-on record; HSPA's sterile processing certification (CRCST) needs 400 hands-on hours signed off by a manager; the Fiber Optic Association's CFOT has instructors verify lab skills; OSHA makes employers evaluate every forklift operator's performance at least every three years. Praxis already watches the work step by step, so it can record that evidence at scale. Why it's a moat: certified techs carry the credential to their next job, the way Cisco and AWS certifications spread Cisco and AWS, and partners' tests run on us. Be straight if asked: no partner conversations yet, and it comes after our own models, because a certificate is only worth the checking behind it. Then new trades.",
    "Revenue: targets, not forecasts · Mercor: The Information, Dealroom (Jun 2026) · Micro1 CEO estimate · Grand View Research · NCCER, NIMS, HSPA, FOA and OSHA (29 CFR 1910.178(l)) requirements, checked Oct 2026");
}

// ================================================================== APPENDIX (for Q&A)
// Three backup slides, as the HV coach suggested: the demo, how it works, and the market math. Each one also answers
// the questions a board asks most often, with short answers.
function sAppendixDivider() {
  const s = pres.addSlide({ masterName: "HV Photo" });
  s.addImage({ path: A("bg-grid-dark.png"), x: 0, y: 0, w: 13.333, h: 7.5, objectName: "grid" });
  label(s, "FOR Q&A", { x: 0.83, y: 0.83, w: 4, h: 0.3, color: C.accent1 });
  tb(s, "Appendix", { x: 0.83, y: 4.2, w: 6.4, h: 1.6, fontFace: HEAD, fontSize: 44, color: C.background2, valign: "bottom" });
  tb(s, "The demo up close, how it works, and the market math, each with the hard questions answered.", { x: 0.83, y: 5.95, w: 6.2, h: 0.8, fontSize: 16, color: C.accent6 });
  const x = 7.9, w = 4.93, y0 = 2.0, rh = 1.3;
  APPENDIX.forEach(([, t, qs], i) => {
    const y = y0 + i * rh;
    line(s, x, y, x + w, y, { color: i ? "3A4044" : "E8EBE9", width: i ? 0.75 : 1.5, name: "appx-rule" });
    tb(s, `A${i + 1}`, { x, y: y + 0.18, w: 0.6, h: 0.35, fontFace: SEMI, fontSize: 14, color: C.accent1 });
    tb(s, [{ text: t, options: { fontFace: SEMI, fontSize: 16, color: C.background2, breakLine: true, paraSpaceAfter: 4 } }, { text: qs, options: { fontSize: 12, color: C.accent6 } }], { x: x + 0.65, y: y + 0.16, w: w - 0.65, h: rh - 0.25 });
  });
}
const appx = (title) => { const s = slide("light"); s.addText(title, { placeholder: "title" }); return s; };
const tableOpts = (colW, w = 12.33, y = 2.0) => ({ x: 0.5, y, w, colW, fontFace: "Archivo", fontSize: 13, color: "16191B", border: [{ type: "none" }, { type: "none" }, { type: "solid", color: "B9C0BC", pt: 0.75 }, { type: "none" }], valign: "middle", rowH: 0.55 });
const TH = (t) => ({ text: t, options: { fontFace: LABEL, fontSize: 10, charSpacing: 1, color: "5E676C", border: [{ type: "none" }, { type: "none" }, { type: "solid", color: "16191B", pt: 1.5 }, { type: "none" }] } });
// a question in SemiBold with its short answer under it, on a plate card
function qaCard(s, x, y, w, h, q, a) {
  panel(s, x, y, w, h, C.background1, "qa-card");
  tb(s, [{ text: q, options: { fontFace: SEMI, fontSize: 13, color: C.text1, breakLine: true, paraSpaceAfter: 5 } }, { text: a, options: { fontSize: 11.5, color: BODY } }], { x: x + 0.22, y: y + 0.18, w: w - 0.4, h: h - 0.3, objectName: "qa-text" });
}
// question-and-answer pairs as one text block
const qaRuns = (pairs) => pairs.flatMap(([q, a], i) => [
  { text: q, options: { fontFace: SEMI, color: C.text1, breakLine: true, paraSpaceAfter: 2 } },
  { text: a, options: { color: BODY, breakLine: i < pairs.length - 1, paraSpaceAfter: 10 } },
]);

// A1 · the live demo, with the engine underneath
function aUnderHood() {
  const s = appx("Under the hood: the same live session, layer by layer");
  const vw = 6.8, vEnd = video(s, "repair_demo_engineer", 0.5, 1.95, vw);
  [["50 ms", "per frame for our layers, on a laptop"], ["0.15 s · 4 s", "fast model, and Opus when it's unsure"], ["$0.165", "for the whole 16:40 session"]].forEach(([b, c], i) => {
    const x = 0.5 + i * (vw / 3), w = vw / 3 - 0.2;
    line(s, x, vEnd + 0.17, x + w, vEnd + 0.17, { color: C.text1, width: 1.5, name: "hood-stat-rule" });
    tb(s, b, { x, y: vEnd + 0.26, w, h: 0.36, fontFace: HEAD, fontSize: 17, color: i === 0 ? C.accent2 : C.text1, objectName: "hood-stat" });
    tb(s, c, { x, y: vEnd + 0.62, w, h: 0.4, fontSize: 11, color: BODY, objectName: "hood-stat-caption" });
  });
  const x = 7.75, w = 5.08;
  label(s, "WHAT EACH PART OF THE SCREEN SHOWS", { x, y: 1.95, w, h: 0.3, color: C.text1 });
  tb(s, runs([
    ["Top right: ", "where it thinks the tech is in the 19 steps, how long they've been on this one, and whether they look new to it."],
    ["Middle right: ", "every model call, with its real wait time."],
    ["Bottom: ", "the timeline of step detections, model calls and each choice to speak or stay quiet."],
  ], 6), { x, y: 2.3, w, h: 1.7, fontSize: 11.5, color: BODY, objectName: "hood-legend" });
  line(s, x, 4.12, x + w, 4.12, { color: C.text1, width: 1.5, name: "ask-rule" });
  label(s, "IF THEY ASK", { x, y: 4.22, w, h: 0.3, color: C.accent2 });
  tb(s, qaRuns([
    ["Is this real?", "Yes. Real footage from an industrial repair lab (ENIGMA-51), streamed through Praxis live. Every card comes from the session log."],
    ["Was it trained on this job?", "No. It turned the lab's written procedure into steps and coached from those."],
    ["Does it run on glasses?", "The Meta and Viture + NVIDIA connections are built, with voice control and screen or voice-only modes."],
  ]), { x, y: 4.58, w, h: 2.25, fontSize: 11.5, objectName: "hood-qa" });
  s.addNotes("The same 49 seconds as the product slide, with the engine underneath. Two moments to point at. At 0:26 the fast model flags a missed button with 0.84 confidence; Opus says the step is still in progress, so no alert goes out (both buttons are lit in the footage). At 2:52 the fast model guesses the wrong cause and Opus reads the display at 215 °C.\n\n" +
    "If pushed on what isn't good yet, say it plainly: these are selected moments. Across the whole 16-minute session it confirmed 1 of 19 steps and agreed with proxy step labels 29% of the time. The overshoot alert landed about 6 seconds after the frame it checked, while it waited on Opus, and cutting that delay is next. A second alert later in the session was a false alarm and is left out of the cut. The 50 ms is from a recorded clip replayed in real time on a laptop, not a webcam. Say out loud: the glasses connections are built but not yet tested on the devices, because I don't have them yet; the first $10k pays for that.",
    "Praxis Studio live session on ENIGMA-51 video 141 · latencies from the session log · results/live/live_replay_async.json");
}

// A2 · how it works, and the questions about the tech and the moat
function aEngine() {
  const s = appx("How it works, and the hard questions");
  label(s, "THE ENGINE, PART BY PART", { x: 0.5, y: 1.58, w: 8, h: 0.3, color: C.text1 });
  const parts = [
    ["Perception", "OPEN MODEL", "Turns each frame into features", "open"],
    ["Step detector", "OURS · TRAINED", "Spots when a step ends", "ours"],
    ["Task recognizer", "OURS · TRAINED", "Works out which job it is", "ours"],
    ["Step tracker", "OURS · TRAINED", "Knows where the tech is", "ours"],
    ["Local checker", "OURS · TRAINED", "Answers routine checks, free", "ours"],
    ["Verifier", "RENTED", "Hard questions, on 14% of frames", "rented"],
  ];
  const gap = 0.15, bw = (12.33 - 5 * gap) / 6;
  parts.forEach(([n, tag, d, kind], i) => {
    const x = 0.5 + i * (bw + gap), y = 1.95, h = 1.05;
    const box = { ours: { fill: { color: C.background1 }, line: { color: "16191B", width: 1 } }, open: { fill: { color: "D5DAD7" }, line: { type: "none" } }, rented: { fill: { type: "none" }, line: { color: "5E676C", width: 1.25, dashType: "dash" } } }[kind];
    s.addShape(pres.ShapeType.roundRect, { x, y, w: bw, h, rectRadius: 0.05, ...box, objectName: `part-${kind}` });
    tb(s, [
      { text: tag, options: { fontFace: LABEL, fontSize: 8, charSpacing: 1, color: kind === "ours" ? C.accent2 : C.text2, breakLine: true, paraSpaceAfter: 3 } },
      { text: n, options: { fontFace: SEMI, fontSize: 13, color: C.text1, breakLine: true, paraSpaceAfter: 2 } },
      { text: d, options: { fontSize: 11, color: BODY } },
    ], { x: x + 0.15, y: y + 0.13, w: bw - 0.25, h: h - 0.2, objectName: "part-text" });
  });
  tb(s, "Our parts run on every frame, on the device, in about 50 ms. The rented model is asked only when something happens.", { x: 0.5, y: 3.15, w: 12.33, h: 0.3, fontSize: 12, color: BODY });
  [
    ["Isn't this just a ChatGPT wrapper?", "No. The frontier model is one rented part, asked on 14% of frames and swappable in one line. The tracking, the checks and the data are ours."],
    ["What's the moat?", "Data nobody sells: first-person video of skilled work, lined up to each step. Customers pay us to collect it, and our step models already improve with it (31% → 51%)."],
    ["Why won't Big Tech build it?", "Meta, Google and OpenAI sell one general model to everyone and give consumer help away free. This takes one trade's manuals, records and on-site pilots. Their glasses become our hardware."],
    ["How accurate is it today?", "13% more accurate at tracking the step than the same frontier model alone, at 1/5 the cost. Mistake alerts are the weak spot: 4 of 17 named a real error."],
    ["What if it's wrong on a safety step?", "Lockout and similar steps stay the tech's job: Praxis prompts and records them, and never approves them. When it can't see, it asks for a better view."],
    ["Isn't this surveillance?", "Our layers run on the device, and only key moments leave it (14% of frames). The tech gets coaching; the employer sees totals, not a live feed."],
  ].forEach(([q, a], i) => qaCard(s, G3.x[i % 3], 3.68 + Math.floor(i / 3) * 1.6, G3.w, 1.47, q, a));
  s.addNotes("Coaching is a tracking problem, not a seeing problem. Walk the parts left to right if asked: open models turn the frame into features; our detector and recognizer feed our step tracker; our local checker handles routine 'is this step done?' checks; and only on hard questions, on 14% of frames, the tracker asks the rented verifier (Jev in about 150 ms, Claude Opus for hard cases, about 4 s).\n\n" +
    "Numbers behind the answers, if pushed. Accuracy: with the task known, Praxis names the current step 54% of the time vs 48% for the same frontier model called every 5 seconds with no memory, at $0.018 vs $0.085 per video-minute, on 48 held-out clips of public first-person procedure video, one run each. With our local checker doing routine checks: 52% at $0.008. Learning curve: on the 3 procedures with 9 training recordings, held-out step accuracy went from 31% with 1 recording to 51% with 9, still rising; say 'steady gains', not 'exponential'. The local checker agrees with the frontier model on 69% of held-out checks and removes 34% of frontier calls. Bad views: when we blurred or blocked the view, it asked for a better view on 77-98% of checks and was never confidently wrong. Mistakes: 4 of 17 alerts named a real annotated error; real maintenance data is what fixes that. Don't say we're the only first-person system: Strivr and Viture + NVIDIA are there too. Keep the tracker's internals and trigger rules out of the answer until the provisional patent is filed.",
    "docs/CLAIMS.md · docs/ARCHITECTURE.md · docs/COMPETITORS.md · results/scaling/learning_curve.json");
}

// A3 · the market math, and the questions about the business
function aMarketMath() {
  const s = appx("Market math, and the questions behind it");
  const R = (a) => a.map((t, i) => ({ text: t, options: i === 0 ? { fontFace: SEMI } : {} }));
  s.addTable([
    [TH(""), TH("WHO (BLS)"), TH("MATH"), TH("PER YEAR")],
    R(["TAM", "Installation, maintenance + repair 6,086,190 · electricians 757,220 · production 8,565,760 = 15.4M", "15.4M × $50 a month × 12", "≈ $9.2B"]),
    R(["SAM", "General maintenance + repair, machinery mechanics + millwrights, HVAC = 2.47M jobs, ~255k openings a year", "255k × $200 × 6 months = $306M; 2.47M × $50 × 12 = $1.48B", "≈ $1.8B"]),
    R(["SOM (year 3)", "1.5% of new maintenance techs ≈ 3,750 new techs a year, ~150 mid-size teams", "3,750 × $200 × 6 months", "≈ $4.5M ARR"]),
  ], { ...tableOpts([1.3, 5.3, 4.13, 1.6], 12.33, 1.62), fontSize: 11.5, rowH: 0.5, objectName: "table-market" });
  tb(s, [
    { text: "Assumptions: ", options: { fontFace: SEMI, color: C.text1 } },
    { text: "prices are our hypotheses, anchored on Tulip's $100–250 per station a month. Openings include people changing jobs, so new-tech counts are an upper bound. Not counted: other countries, aviation, and robotics." },
  ], { x: 0.5, y: 3.98, w: 12.33, h: 0.45, fontSize: 11.5, color: BODY });
  const gap = 0.15, cw = (12.33 - 3 * gap) / 4;
  [
    ["Why maintenance, not consumers?", "A manager signs a budget, and the same procedure runs every month, so the data compounds. Meta and Google give consumer help away free."],
    ["Why would a shop pay $200 a month?", "It's about one hour a week of the senior tech who'd otherwise teach ($44 an hour). Hiring and ramping up one tech costs $10–15k."],
    ["What are the margins?", "About $45 of model cost per seat-month today, so 77%. With our own model, $20, so 90%. All-shift use squeezes that, so we'd price by coached hours."],
    ["Any customers yet?", "Not yet. Outreach started this week: 70 maintenance teams and training programs, and a fiber-optic school is open to a one-lab trial. The first $10k funds a paid pilot, with a metric agreed up front."],
  ].forEach(([q, a], i) => qaCard(s, 0.5 + i * (cw + gap), 4.6, cw, 2.2, q, a));
  s.addNotes("Bottom-up, US only. The SOM is a goal, not a forecast. If asked about consumers: it's about order, not size. Home tasks don't repeat, there's no budget owner, and even paid expert help collapsed (Frontdoor's expert video help for homeowners fell from $99 to $25 a year from 2023 to 2024). Consumers come last, once glasses are everywhere and our models run on the device.\n\n" +
    "Senior-tech time, labeled as our assumption: if a senior tech spends 50% of their time on a new hire for 3 months, that's about $11,400; at 25% for 12 months, about $22,800. We're asking maintenance managers for their real split. Margins: at 2 hours of coaching a day, a seat-month is 2,520 video-minutes; $0.018 a minute is about $45, $0.008 is about $20. At 8 hours a day a flat $200 seat is $1.19 an hour against our $1.08 cost, about 9%; with the local model, about 60%. Customers: be straight that there are no customers or pilots yet. 70 emails went out Oct 17-19 (68 delivered). The fiber-optic school said \"we would be open to an experiment like this\" about one lab exercise; nothing has run yet, so call it a trial they're open to.",
    "BLS OEWS national tables, May 2025 · BLS Occupational Outlook Handbook · Reliability magazine · Frontdoor pricing 2023–2024 · send log in docs/OUTREACH.md");
}

// ================================================================== ORDER
const CORE = [sCover, sProblem, sSolution, sWhyNow, sMarket, sCompetition, sProduct, sBusiness, sTeam, sFinancials, sFuture];
const APPENDIX = [
  [aUnderHood, "Under the hood: the live demo", "Is it real? Was it trained on this job? Does it run on glasses?"],
  [aEngine, "How it works", "Is it a wrapper? What's the moat? Why won't big labs build it? How accurate? Safety? Privacy?"],
  [aMarketMath, "Market math", "How was it sized? Why not consumers? Why would a shop pay? Margins? Customers?"],
];
if (CORE.length !== SECTIONS.length) throw new Error(`${SECTIONS.length} sections but ${CORE.length} core slides`);
pres.addSection({ title: "Pitch" });
SECTION = "Pitch";
CORE.forEach((f) => { CUR++; f(); });
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
