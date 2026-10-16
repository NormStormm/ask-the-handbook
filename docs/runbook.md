# Ask the Handbook runbook

## Set up
Python 3.10+.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
read -s "k?Paste your Claude API key: " && printf 'ANTHROPIC_API_KEY=%s\n' "$k" > .env && chmod 600 .env && unset k
```

## Run the web page
```bash
.venv/bin/python -m ask_handbook.app
```
Open **http://localhost:8000**. The **HR view** tab lists every question that was escalated, half-answered or flagged (stored in `logs/unanswered.csv`, which is not committed).

## Update the handbook
Edit `handbook/handbook.md` or `handbook/sops.md`. Rules:
- Each section starts with `## <id> <title>`, e.g. `## 2.3 Calling out sick or late`. Each section is one citable unit, so keep sections focused (one topic, under about 200 words).
- Write numbers as staff should see them (`4 hours`, `extension 4100`, `$15`). The number check compares the answer's numbers against the cited section.
- Restart the app after editing. Then run the tests:
```bash
.venv/bin/python -m pytest -q          # free; update the section counts in test_engine.py if you added sections
.venv/bin/python tests/run_eval.py     # about 23¢: re-checks all 40 questions against the new text
```

## What the statuses mean

| Status shown | Meaning | What happens |
|---|---|---|
| Answered from the handbook | Cited, every number verified | Shown with sources |
| Partly answered: rest sent to HR | Part of the question isn't covered | The covered part is shown; the question is logged |
| Not in the handbook: sent to HR | No section supports an answer | No answer shown; logged |
| Needs checking: sent to HR | A number in the answer isn't in its cited section (often a calculation) | Shown with a warning; logged |
| Unavailable | The Claude API call failed | Staff are told to ask their manager or HR |

## Cost
About **$0.006 per question** with Claude Opus 5.5 (the handbook is cached after the first question), or about **$0.0002** with Haiku 5.5 (`ask(..., model="claude-haiku-5-5")`). Haiku scored 90% vs Opus's 98% on the test questions, mostly by being over-cautious.

## Before using with real staff
- Replace the fictitious handbook with the real one, and have HR review the 40 test questions and add their own.
- Put it behind the company's sign-in, and decide whether the gaps log should record who asked.
- The assistant explains policy; it isn't legal advice, and the handbook should say who to contact for anything personal.
