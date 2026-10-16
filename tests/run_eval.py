"""Scores the assistant on 40 questions with known right answers.

    .venv/bin/python tests/run_eval.py                         # Claude Opus 5.5
    .venv/bin/python tests/run_eval.py --model claude-haiku-5-5

For each question:
  - Right behavior: answered when the handbook covers it, escalated to HR when it doesn't, partial when half-covered.
  - Right source: an answer must cite the expected section.
  - Key facts: the answer must contain the important detail (e.g. "4 hours", "5555").
  - No unsupported numbers: every number in an answer must appear in the section it cites.
Writes tests/results/<model>-<time>.json
"""
import argparse
import json
import pathlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import anthropic
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from ask_handbook.engine import MODEL, ask  # noqa: E402

load_dotenv(ROOT / ".env")
ap = argparse.ArgumentParser()
ap.add_argument("--model", default=MODEL)
ap.add_argument("ids", nargs="*")
args = ap.parse_args()

cases = json.loads((ROOT / "tests" / "questions.json").read_text())
if args.ids:
    cases = [c for c in cases if c["id"] in args.ids]
client = anthropic.Anthropic()
EXPECTED_STATUS = {"answer": {"ANSWERED"}, "escalate": {"ESCALATED"}, "partial": {"PARTIAL"}, "answer_or_partial": {"ANSWERED", "PARTIAL"}}


def run(c):
    a = ask(c["q"], client, model=args.model, log=False)
    cited = {s["label"].split()[1] for s in a.sources}
    behavior_ok = a.status in EXPECTED_STATUS[c["expect"]]
    source_ok = not c.get("sections") or bool(cited & set(c["sections"]))
    facts_ok = all(f.lower() in a.text.lower() for f in c.get("facts", []))
    ok = behavior_ok and (c["expect"] == "escalate" or (source_ok and facts_ok))
    return {"id": c["id"], "q": c["q"], "expect": c["expect"], "status": a.status, "ok": ok, "behavior_ok": behavior_ok,
            "source_ok": source_ok, "facts_ok": facts_ok, "cited": sorted(cited), "unsupported": a.unsupported_numbers,
            "answer": a.text, "cost": a.cost, "seconds": a.seconds}


ask("warm-up: what time is the first day?", client, model=args.model, log=False)   # writes the cache once, so the run reads it
with ThreadPoolExecutor(max_workers=3) as pool:
    results = list(pool.map(run, cases))

for r in results:
    mark = "✓" if r["ok"] else "✗"
    why = "" if r["ok"] else f"  <- behavior {'ok' if r['behavior_ok'] else 'WRONG'}, source {'ok' if r['source_ok'] else 'MISSING'}, facts {'ok' if r['facts_ok'] else 'MISSING'}" + (f", unsupported {r['unsupported']}" if r["unsupported"] else "")
    print(f"{mark} {r['id']} {r['expect']:<8} -> {r['status']:<9} cites {','.join(r['cited']) or '-':<8} {r['q'][:55]}{why}")

n = len(results)
by = lambda e: [r for r in results if r["expect"] == e]
pct = lambda xs: f"{sum(r['ok'] for r in xs)}/{len(xs)}"
print(f"\nModel: {args.model}")
print(f"Overall correct:           {pct(results)} ({sum(r['ok'] for r in results) / n:.0%})")
print(f"  Answerable, answered right (behavior + source + key fact): {pct(by('answer'))}")
print(f"  Not in handbook, sent to HR (no made-up answer):          {pct(by('escalate'))}")
print(f"  Half-covered, answered the covered part:                  {pct(by('partial') + by('answer_or_partial'))}")
print(f"Answers with a number not in the cited section: {sum(1 for r in results if r['unsupported'])}")
print(f"Cost: ${sum(r['cost'] for r in results):.3f} total, ${sum(r['cost'] for r in results) / n:.4f} per question; "
      f"median {sorted(r['seconds'] for r in results)[n // 2]}s")
out = ROOT / "tests" / "results"
out.mkdir(exist_ok=True)
(out / f"{args.model.replace('claude-', '')}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(results, indent=1))
