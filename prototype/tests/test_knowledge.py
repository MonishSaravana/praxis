"""Company knowledge backend: parsing, section map, chunking, retrieval, cards, versions, spend cap. No model calls."""
import shutil
import zipfile
from pathlib import Path

import pytest

from praxis.knowledge import parse as P
from praxis.knowledge.budget import LedgerBudget
from praxis.knowledge.cards import extract, safety_suggested, step_cards_numbered
from praxis.knowledge.chunk import chunk_lines
from praxis.knowledge.index import Searcher, tokens
from praxis.knowledge.ingest import ingest, load_sections, searcher
from praxis.knowledge.qa import answer, card_answer
from praxis.knowledge.sections import heading_of, section_map, section_text, step_names, to_lines
from praxis.knowledge.store import Org
from praxis.tasks.schema import Check, Node, TaskGraph
from praxis.verify.common import BudgetExceeded

MANUAL = """ACME P-200 Service Manual
Contents
1 Safety ........ 1
4 Maintenance ........ 2
\f
ACME P-200 Service Manual
1 SAFETY
WARNING: Disconnect power before servicing the pump.
Wear safety glasses.
\f
ACME P-200 Service Manual
4 MAINTENANCE
4.2 Replacing the Inlet Filter
Tools required: 10 mm socket, torque wrench
WARNING: Lock out and tag out the pump motor breaker.
1. Close the inlet valve V1.
2. Remove the four M6 cover bolts.
3. Lift out the old filter (P/N 200-114).
4. Insert the new filter with the arrow pointing up (see Figure 4-3).
5. Refit the cover and tighten the bolts to 9 N·m.
6. Open the inlet valve and check for leaks.
\f
ACME P-200 Service Manual
4.3 Checking the Oil Level
1. Stop the pump and wait 5 minutes.
2. Read the sight glass; the level must be between the marks.
3. Top up with ISO VG 46 oil if needed (0.5 L capacity).
"""


def pages():
    return MANUAL.split("\f")


# ------------------------------------------------------------------ parsing
def test_parse_text_form_feeds_and_parts():
    p = P.parse_text(MANUAL, "text")
    assert len(p.pages) == 4 and not p.paged
    long = P.parse_text("\n\n".join(f"Paragraph {i} " + "word " * 100 for i in range(30)), "text", part_chars=2000)
    assert len(long.pages) > 3 and all(len(x) < 2700 for x in long.pages)


def test_clean_joins_hyphenated_words_and_ligatures():
    assert P.clean("re-\nmove the ﬁlter") == "remove the filter"
    assert P.clean("P/N 200-\n114") == "P/N 200-\n114"            # digits are not joined


def _docx(path: Path):
    W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

    def p(text, style=None, num=None):
        ppr = ""
        if style or num:
            ppr = "<w:pPr>" + (f'<w:pStyle w:val="{style}"/>' if style else "") + \
                  (f'<w:numPr><w:ilvl w:val="0"/><w:numId w:val="{num}"/></w:numPr>' if num else "") + "</w:pPr>"
        return f"<w:p>{ppr}<w:r><w:t>{text}</w:t></w:r></w:p>"
    body = "".join([p("Replacing the Belt", "Heading1"), p("WARNING: Lock out the drive."),
                    p("Loosen the tensioner.", num="1"), p("Remove the old belt.", num="1"),
                    p("Fit the new belt and tension it to 12 mm deflection.", num="1")])
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", f"<w:document {W}><w:body>{body}</w:body></w:document>")


def test_parse_docx_headings_and_numbering(tmp_path):
    f = tmp_path / "belt.docx"
    _docx(f)
    p = P.parse(f)
    text = p.pages[0]
    assert "# Replacing the Belt" in text and "1. Loosen the tensioner." in text and "3. Fit the new belt" in text
    lines, secs, _ = section_map(p.pages)
    proc = max(secs, key=lambda s: s.proc_score)
    assert proc.title == "Replacing the Belt" and len(proc.steps) == 3
    assert proc.steps[0].notes == ["WARNING: Lock out the drive."]


def _pdf(path: Path):
    import matplotlib
    matplotlib.use("pdf")
    matplotlib.rcParams["pdf.fonttype"] = 42
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    with PdfPages(path) as pdf:
        for page in pages():
            fig = plt.figure(figsize=(8.5, 11))
            for i, line in enumerate(x for x in page.split("\n") if x):
                fig.text(0.08, 0.92 - i * 0.04, line, fontsize=11)
            pdf.savefig(fig)
            plt.close(fig)


@pytest.mark.skipif(shutil.which("swiftc") is None and not P.PDFKIT_BIN.exists(), reason="needs macOS PDFKit")
def test_parse_pdf_pages_and_render(tmp_path):
    f = tmp_path / "manual.pdf"
    _pdf(f)
    p = P.parse(f)
    assert p.paged and len(p.pages) == 4 and p.parser == "pdfkit"
    assert "9 N·m" in p.pages[2] and "P/N 200-114" in p.pages[2]
    out = P.render_page(f, 3, tmp_path / "p3.png", 400)
    assert out.stat().st_size > 1000


# ------------------------------------------------------------------ section map
def test_heading_rules():
    assert heading_of("4.2 Replacing the Inlet Filter")[:2] == (2, "4.2")
    assert heading_of("3 Maintenance")[:2] == (1, "3")
    assert heading_of("3 Remove the cover") is None              # a step, not a heading
    assert heading_of("1. Close the inlet valve V1.") is None
    assert heading_of("## Torque table")[0] == 2
    assert heading_of("Chapter 5 Hydraulics")[0] == 1
    assert heading_of("WARNING: hot surface") is None
    assert heading_of("Replacing the filter ........ 45") is None  # table of contents line


def test_boilerplate_removed_on_many_pages():
    body = ["Inspect the seal.", "Drain the tank.", "Check the belt.", "Clean the screen.", "Fit the guard.", "Test run."]
    ps = [f"Header Line\nPage {i}\n{b}" for i, b in enumerate(body, 1)]
    lines, removed = to_lines(ps)
    assert all(ln.text != "Header Line" for ln in lines) and "header line" in removed
    assert [ln.text for ln in lines][:2] == ["Inspect the seal.", "Drain the tank."]


def test_section_map_finds_procedures_with_pages_and_warnings():
    lines, secs, stats = section_map(pages())
    by = {s.title: s for s in secs}
    f = by["4.2 Replacing the Inlet Filter"]
    assert (f.page_start, f.page_end) == (3, 3) and len(f.steps) == 6 and f.proc_score >= 0.5
    assert f.steps[0].notes == ["WARNING: Lock out and tag out the pump motor breaker."]
    assert f.parent == by["4 Maintenance"].id
    oil = by["4.3 Checking the Oil Level"]
    assert oil.page_start == 4 and len(oil.steps) == 3
    assert by["4 Maintenance"].line_end >= oil.line_end           # the chapter spans its sub-sections
    assert stats["n_procedures"] == 2
    src = section_text(lines, f)
    assert src.startswith("[page 3]\n4.2 Replacing") and "Checking the Oil" not in src
    assert step_names(f.steps)[2] == {"id": "s3", "name": "Lift out the old filter (P/N 200-114)"}


# ------------------------------------------------------------------ chunking
def test_chunks_respect_sections_and_pages():
    lines, secs, _ = section_map(pages())
    chunks = chunk_lines(lines, secs, "ab" * 32, target=120, hard=200)
    assert len(chunks) > 4
    for c in chunks:
        owners = {next(s.id for s in sorted(secs, key=lambda s: -s.level) if s.line_start <= i < s.line_end)
                  for i in range(c.line_start, c.line_end)}
        assert len(owners) == 1 and c.section in owners            # never across a section boundary
        assert c.page_start == lines[c.line_start].page and c.page_end == lines[c.line_end - 1].page
    torque = next(c for c in chunks if "9 N·m" in c.text)
    assert torque.page_start == 3 and "Replacing the Inlet Filter" in torque.section_path


# ------------------------------------------------------------------ retrieval
def test_tokens_normalize_units_and_part_numbers():
    assert "nm" in tokens("tighten to 9 N·m") and "nm" in tokens("9 Nm") and "ftlb" in tokens("25 ft-lbs")
    assert "partnumber" in tokens("P/N 200-114") and "200-114" in tokens("P/N 200-114")
    assert tokens("tightening")[0] == tokens("tighten")[0] and tokens("removed")[0] == tokens("remove")[0]


def test_bm25_retrieves_the_right_chunk():
    lines, secs, _ = section_map(pages())
    chunks = [c.as_dict() for c in chunk_lines(lines, secs, "cd" * 32, target=120, hard=200)]
    s = Searcher(chunks)
    top = s.search("what torque for the cover bolts?", k=1)[0]
    assert "9 N·m" in top["text"]
    top = s.search("part number of the inlet filter", k=1)[0]
    assert "200-114" in top["text"]
    top = s.search("how much oil does it take", k=1)[0]
    assert "0.5 L" in top["text"] and top["page_start"] == 4
    assert s.search("zebra unicorn", k=3) == []
    assert s.search("torque", k=3, docs={"nope"}) == []


# ------------------------------------------------------------------ cards
def test_cards_are_verbatim_with_pages():
    cs = extract("Refit the cover and tighten the bolts to 9 N·m (see Figure 4-3). Use P/N 200-114.", 3)
    kinds = {(c["kind"], c["label"]) for c in cs}
    assert ("spec", "torque: 9 N·m") in kinds and ("part", "part 200-114") in kinds and ("figure", "Figure 4-3") in kinds
    assert all(c["page"] == 3 for c in cs)
    w = extract("WARNING: Lock out and tag out the pump motor breaker.", 3)
    assert w[0]["kind"] == "warning" and w[0]["label"] == "WARNING"


def test_step_cards_and_safety_suggestions():
    lines, secs, _ = section_map(pages())
    f = next(s for s in secs if s.title.startswith("4.2"))
    cards = step_cards_numbered(lines, f.steps)
    assert any(c["kind"] == "warning" for c in cards["s1"])
    assert any(c["label"] == "torque: 9 N·m" for c in cards["s5"])
    nodes = [Node(id=s["id"], name=s["name"], instruction_novice="", instruction_expert="", end_state="")
             for s in step_names(f.steps)]
    assert safety_suggested(cards, nodes) == ["s1"]


# ------------------------------------------------------------------ store, versions, ingest, questions
def _graph(task_id="t", names=("Close the valve", "Remove the bolts", "Tighten the bolts")):
    nodes = [Node(id=f"s{i + 1}", name=n, instruction_novice=n + ".", instruction_expert=n, end_state=n,
                  checks=[Check(id=f"s{i + 1}c1", question=f"Is it done: {n}?")],
                  successors=[f"s{i + 2}"] if i + 1 < len(names) else []) for i, n in enumerate(names)]
    return TaskGraph(task_id=task_id, title="Replace filter", domain="maintenance", source="unit", nodes=nodes, start=["s1"])


def test_documents_keep_versions_and_ingest_once(tmp_path):
    o = Org.create("Acme Pumps", root=tmp_path)
    f1 = tmp_path / "P-200 manual.md"
    f1.write_text(MANUAL.replace("\f", "\n\n"))
    h1 = P.file_sha256(f1)
    r1 = o.add_document(f1, f1.name, h1, "markdown")
    assert r1["new"] and r1["version"] == 1
    assert not o.add_document(f1, f1.name, h1, "markdown")["new"]            # same bytes: nothing new
    m = ingest(o, h1)
    assert m["status"] == "ready" and m["n_procedures"] == 2 and not m["paged"]
    t = m["ingest_s"]
    assert ingest(o, h1)["ingest_s"] == t                                     # second call reuses the index
    f1.write_text(MANUAL.replace("9 N·m", "11 N·m").replace("\f", "\n\n"))
    h2 = P.file_sha256(f1)
    r2 = o.add_document(f1, f1.name, h2, "markdown")
    assert r2["version"] == 2 and r2["new"]
    ingest(o, h2)
    docs = o.documents()
    assert len(docs) == 1 and [v["version"] for v in docs[0]["versions"]] == [1, 2] and docs[0]["current"] == h2
    assert (o.doc_dir(h1) / "index.json").exists()                            # old version kept
    hit = searcher(o).search("cover bolt torque", k=1)[0]
    assert "11 N·m" in hit["text"]                                            # questions use the current version
    lines, secs, _ = load_sections(o, h2)
    assert any(s.title.startswith("4.2") for s in secs)


def test_questions_without_a_model(tmp_path):
    o = Org.create("Acme", root=tmp_path)
    f = tmp_path / "m.txt"
    f.write_text(MANUAL)
    h = P.file_sha256(f)
    o.add_document(f, f.name, h, "text")
    ingest(o, h)
    r = answer(o, "what is the torque for the cover bolts", allow_model=False)
    assert r["source"] == "excerpt" and "9 N·m" in r["answer"] and r["citations"][0]["section"]
    r = answer(o, "what is the torque for the cover bolts", step={"name": "Close the inlet valve V1"}, allow_model=False)
    assert "9 N·m" in r["answer"]                    # the quoted line answers the question, not the step name
    step = {"name": "Refit the cover", "cards": [{"kind": "spec", "label": "torque: 9 N·m", "text": "tighten to 9 N·m.", "page": 3}]}
    c = card_answer("how tight should the bolts be?", step)
    assert c["source"] == "card" and c["answer"].startswith("9 N·m") and c["citations"][0]["page"] == 3
    assert card_answer("why do I close the valve first?", step) is None


def test_procedure_versions_approve_and_edit(tmp_path):
    from praxis.knowledge.compile import edit_version
    from praxis.knowledge.store import write_json
    o = Org.create("Acme", root=tmp_path)
    v1 = o.new_version("replace-filter", "Replace filter", {"doc_hash": "x", "doc_version": 1})
    d = o.version_dir("replace-filter", v1)
    d.mkdir(parents=True)
    _graph(task_id="org-acme-replace-filter").save(d / "graph.json")
    write_json(d / "cards.json", {"s1": [], "s2": [], "s3": [], "_procedure": []})
    write_json(d / "review.json", {"safety": []})
    assert o.library() == {}                                                  # nothing approved yet
    o.approve("replace-filter", v1)
    assert list(o.library()) == ["org-acme-replace-filter"]
    v2 = edit_version(o, "replace-filter", v1, {"nodes": {"s3": {"name": "Torque the bolts to 9 N·m"}}, "safety": ["s1"]})
    assert v2 == 2                                                            # approved v1 is never changed
    assert o.load_version("replace-filter", 1)["graph"].node("s3").name == "Tighten the bolts"
    x = o.load_version("replace-filter", 2)
    assert x["graph"].node("s3").name == "Torque the bolts to 9 N·m" and x["review"]["safety"] == ["s1"]
    assert o.proc("replace-filter")["approved_version"] == 1                  # live keeps v1 until v2 is approved
    assert edit_version(o, "replace-filter", 2, {"notes": "checked"}) == 2    # a draft is edited in place


def test_ledger_budget_caps_spend_across_restarts(tmp_path):
    class U:
        input_tokens, output_tokens = 10_000, 2_000
    b = LedgerBudget(tmp_path / "spend.json", max_calls=10, max_usd=0.10)
    b.check()
    usd = b.record("question", "claude-opus-5-5", U, org="acme")
    assert abs(usd - (10_000 * 4 + 2_000 * 20) / 1e6) < 1e-9
    b2 = LedgerBudget(tmp_path / "spend.json", max_calls=10, max_usd=0.10)   # a restart reads the ledger
    assert abs(b2.usd - usd) < 1e-9 and b2.calls == 1
    with pytest.raises(BudgetExceeded):
        b2.ensure(0.05, "a compile")
    b2.record_usd("compile", "claude-opus-5-5", 0.03)
    with pytest.raises(BudgetExceeded):
        b2.check()


def test_reference_video_alignment_is_ordered():
    import numpy as np
    from praxis.knowledge.video import align
    sim = np.full((3, 9), 0.1)
    sim[0, 1], sim[1, 4], sim[2, 7] = 0.9, 0.9, 0.9            # each step best matches one frame, in order
    spans = align(sim)
    assert [a <= b for (a, _), (b, _) in zip(spans, spans[1:])] == [True, True]
    assert all(a <= k < b for (a, b), k in zip(spans, (1, 4, 7)))
    assert spans[0][0] == 0 and spans[-1][1] == 9               # the spans cover the whole video
