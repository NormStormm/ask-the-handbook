# Findings: what broke in testing, and what changed

Each entry: what happened → why → fix → how it was verified.

## Design decision: no vector search
The handbook and SOPs are about 5,800 tokens in total, so they're sent whole with every question and **cached** (prompt caching). After the first question, the documents cost about a tenth of the normal price. A retrieval system (embeddings, vector database) would add moving parts and a new way to fail (retrieving the wrong section) for no benefit at this size. It becomes worth it around a few hundred pages.

## Design decision: no citation, no answer
Claude's citations feature can't be combined with structured (JSON) output, so the "is this grounded?" decision can't be a field Claude fills in. Instead, code decides: an answer with **zero citations is never shown**, and the question goes to HR. Every number in a shown answer must appear in a section it cites.

## F1: Correct answers flagged because of list numbering (number check)
- **What happened:** The allergy answer, correct and citing section 5.2, came back "Needs checking." Claude had written it as a numbered list, and the number check treated "1.", "2.", "3." as facts missing from the handbook.
- **Fix:** Ignore list markers ("1. ", "2) ") at the start of a line.
- **Verified:** Same question → "Answered from the handbook." Locked in by `test_list_numbering_is_not_a_fact`.

## F2: Answer-key correction: "Can I wear sneakers?"
- **What happened:** Expected "answered". Claude said: the handbook doesn't mention sneakers, but shoes must be black, closed-toe and non-slip. It labeled that "partial" in one run and "answered" in another.
- **Why it's the key's fault:** That's the right answer. It gives the rule without inventing a yes or no. The label depends on whether Claude adds "couldn't find the rest," which is a coin flip for a question this borderline.
- **Change:** Accept either label. Written into `tests/questions.json` before the final run.

## F3: A coincidental number passed as evidence (my bug, caught by the eval)
- **What happened:** To fix a different miss (Claude mentioned "HR is at extension 4100" without citing section 1.1), I added an auto-attach: if a number in the answer exists elsewhere in the handbook, attach that section as a source. The next run, "call by **1** pm" (a calculation: 5 pm minus 4 hours) passed, because section 4.1 says "**1** hour of PTO." A coincidence was treated as proof.
- **Fix:** Only auto-attach *distinctive* numbers (3+ digits, like extensions 4100 and 5555). Small numbers appear everywhere, so they must be properly cited or the answer is flagged.
- **Verified:** "by 1 pm" is flagged again; "ext. 4100" still gets section 1.1 attached. Locked in by `test_small_number_is_not_matched_by_coincidence`.
- **Lesson:** A safety check that's loosened to reduce false alarms needs its own test for the false *passes* it might let through.

## F4: Auto-attached section didn't re-check its other numbers
- **What happened:** Haiku's answer about payday mentioned HR's hours ("8 am to 4:30 pm") and extension 4100. 4100 attached section 1.1, but 8, 4 and 30, which are also in 1.1, were still flagged.
- **Fix:** Once a section is attached, every number in it counts as supported.
- **Verified:** Q40 passes on both models.

## Results (final run, 40 questions, after F1–F4)

| | Claude Opus 5.5 | Claude Haiku 5.5 |
|---|---|---|
| Overall | **39/40 (98%)** | 36/40 (90%) |
| Answerable: right behavior, right section, key fact | 28/29 | 26/29 |
| Not in the handbook: sent to HR, nothing made up | **9/9** | 8/9 |
| Half-covered: answered the covered part | 2/2 | 2/2 |
| Cost per question | $0.0056 | $0.0002 |
| Median response time | 2.8 s | 1.6 s |

- **The one Opus miss (Q06)** is the check working: "shift at 5 pm, when do I call?" → "by 1 pm" is correct math, but code can't verify a calculated number, so the answer is shown with a warning and sent to a person. It's counted as a miss rather than relabeled.
- **Haiku's misses are over-caution** (correct answers labeled "partial") plus one judgment call: asked about a 401k *match*, it cited the handbook's retirement plan and said the match isn't covered, where the key expected a straight hand-off to HR. Defensible, but not changed after the final run.
- **Both models refused every out-of-handbook question,** including ones they know the answer to (Hawaii's minimum wage, opening wine tableside) and two attempts to override the rules.

**Caveat:** these 40 questions were also used while fixing F1–F4, so they're a development set, not a held-out test. A fresh set written by someone else, ideally real new hires, would be the honest next measure (see [Shift Desk's evaluation](https://github.com/NormStormm/shift-desk/blob/main/docs/eval-report.md) for that approach).
