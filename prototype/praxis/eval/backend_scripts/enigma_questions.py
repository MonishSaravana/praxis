"""Approved: does the general model know these task details without the company's procedure? Same model both ways
(Claude Opus 5.5, effort low). General: no document. Praxis: the company question box (step's cards first, else the
top-5 passages from the uploaded procedure) with the step the technician would be on. Scored by a fixed fact check."""
import json, re, sys, time
import anthropic
from praxis.knowledge.budget import backend_budget
from praxis.knowledge.qa import answer
from praxis.knowledge.store import Org
from praxis.paths import load_env
from praxis.verify.common import cost_usd
load_env()
org = Org("enigma-repair-lab")
x = org.load_version(org.procedures()[0]["id"], org.procedures()[0]["approved_version"])
g, cards = x["graph"], x["cards"]
ver = x["proc"]["versions"][-1]
def step(nid):
    n = g.node(nid)
    return {"task": g.title, "name": n.name, "instruction": n.instruction_novice, "cards": cards.get(nid, []),
            "procedure_cards": cards.get("_procedure", []), "doc": ver["doc_hash"], "node": nid}
QS = [  # question, step the technician is on, facts the procedure states (all must appear)
    ("What voltage should I set on the power supply before I connect it to the board?", "s3", [r"\b5\s*(v|volts?)\b"]),
    ("What temperature do I set the soldering iron to, and which button do I use?", "s6", [r"\b200\b", r"\bup\b"]),
    ("When I get to the lab, which buttons do I press on panel A?", "s1", [r"\bgreen\b", r"\b(two|2|both)\b"]),
    ("Which oscilloscope channel and button do I use for the probe?", "s11", [r"ch\s*2|channel\s*(2|two)", r"menu"]),
]
CTX = "A technician is repairing a high-voltage electrical board at a lab workbench with a bench power supply, a soldering iron, pliers and an oscilloscope."
client = anthropic.Anthropic(timeout=60, max_retries=1)
b = backend_budget()
rows = []
for q, nid, facts in QS:
    b.ensure(0.02, "a comparison question"); b.check()
    t0 = time.perf_counter()
    r = client.messages.create(model="claude-opus-5-5", max_tokens=1000,
        system="You are the assistant in a maintenance technician's smart glasses. Answer in one or two short sentences.",
        messages=[{"role": "user", "content": f"{CTX}\n\nQuestion: {q}"}], output_config={"effort": "low"})
    gen = next((c.text for c in r.content if c.type == "text"), "").strip()
    gcost = b.record("question (no document, comparison)", "claude-opus-5-5", r.usage, org=org.id, detail={"question": q[:100]})
    glat = round(1000 * (time.perf_counter() - t0))
    p = answer(org, q, step=step(nid), allow_model=True)
    ok = lambda s: all(re.search(f, s, re.I) for f in facts)
    row = {"question": q, "step": g.node(nid).name,
           "general": {"answer": gen, "correct": ok(gen), "cost_usd": round(gcost, 5), "latency_ms": glat},
           "praxis": {"answer": p["answer"], "correct": ok(p["answer"]), "source": p["source"], "citations": [c.get("where") or c.get("label") for c in p.get("citations", [])],
                      "cost_usd": round(p.get("cost_usd", 0.0), 5), "latency_ms": round(p.get("latency_ms", 0))}}
    rows.append(row)
    print("ROW", json.dumps(row), flush=True)
out = {"label": "ENIGMA-51 high-voltage repair procedure; same model both ways (Claude Opus 5.5, effort low); fixed fact check against the written procedure",
       "rows": rows, "general_correct": sum(r["general"]["correct"] for r in rows), "praxis_correct": sum(r["praxis"]["correct"] for r in rows),
       "n": len(rows), "spend_usd": round(sum(r["general"]["cost_usd"] + r["praxis"]["cost_usd"] for r in rows), 4)}
json.dump(out, open(sys.argv[1], "w"), indent=2)
print("SUMMARY", json.dumps({k: out[k] for k in ("general_correct", "praxis_correct", "n", "spend_usd")}))
