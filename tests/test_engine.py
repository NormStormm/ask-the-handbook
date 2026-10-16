"""Offline tests for the answer checks (no API calls, no cost):  .venv/bin/python -m pytest -q

A fake Claude response is fed to engine.ask(), so these test the rules in code, not Claude.
"""
from types import SimpleNamespace as NS

from ask_handbook import engine
from ask_handbook.engine import DOCS, _numbers, ask


def section_index(sid):
    for d, doc in enumerate(DOCS):
        for i, s in enumerate(doc):
            if s.sid == sid:
                return d, i
    raise KeyError(sid)


def cite(sid):
    d, i = section_index(sid)
    return NS(type="content_block_location", document_index=d, start_block_index=i, end_block_index=i + 1,
              cited_text=DOCS[d][i].text[:80])


class FakeClient:
    def __init__(self, *blocks):
        self.messages = NS(create=lambda **kw: NS(
            content=[NS(type="text", text=t, citations=c) for t, c in blocks],
            usage=NS(input_tokens=10, output_tokens=10, cache_read_input_tokens=0, cache_creation_input_tokens=0)))


def test_handbook_loads_every_section():
    assert [len(d) for d in DOCS] == [28, 7]
    assert all(s.text for d in DOCS for s in d)


def test_no_citation_means_no_answer():
    a = ask("Can I bring my dog?", FakeClient(("Sure, dogs are welcome on Fridays.", [])), log=False)
    assert a.status == "ESCALATED" and "dogs are welcome" not in a.text


def test_cited_answer_is_shown():
    a = ask("When do schedules come out?", FakeClient(("Schedules are posted every Wednesday by 5 pm.", [cite("2.1")])), log=False)
    assert a.status == "ANSWERED" and a.sources[0]["label"].startswith("Handbook 2.1")


def test_number_not_in_cited_section_is_flagged():
    a = ask("When do schedules come out?", FakeClient(("Schedules are posted every Wednesday by 6 pm.", [cite("2.1")])), log=False)
    assert a.status == "FLAGGED" and a.unsupported_numbers == ["6"]


def test_list_numbering_is_not_a_fact():
    text = "Steps:\n1. Write it on the ticket.\n2. Tell the chef.\n3. Call security at extension 5555."
    a = ask("allergy?", FakeClient((text, [cite("5.2")])), log=False)
    assert a.status == "ANSWERED"


def test_numbers_the_employee_typed_are_allowed():
    a = ask("My shift is at 5pm, when do I call?", FakeClient(("For a 5 pm shift, call at least 4 hours before.", [cite("2.3")])), log=False)
    assert a.status == "ANSWERED"


def test_distinctive_uncited_number_gets_its_section_attached():
    a = ask("How do I report harassment?", FakeClient(("Use the Ethics Line. HR is at extension 4100.", [cite("6.3")])), log=False)
    assert a.status == "ANSWERED"
    assert any(s["label"].startswith("Handbook 1.1") and "added by number check" in s["label"] for s in a.sources)


def test_small_number_is_not_matched_by_coincidence():
    """F3: '1 pm' once matched the '1 hour of PTO' in section 4.1 and passed. Small numbers must be properly cited."""
    a = ask("Shift at 5pm, when do I call?", FakeClient(("Call by 1 pm, at least 4 hours before.", [cite("2.3")])), log=False)
    assert a.status == "FLAGGED" and a.unsupported_numbers == ["1"]
    assert not any("4.1" in s["label"] for s in a.sources)


def test_partial_answer_detected():
    a = ask("Payday, and can I pick up my check?",
            FakeClient(("Pay is every other Friday by direct deposit. ", [cite("3.1")]),
                       (engine.NOT_FOUND[:-1] + " for the rest.", [])), log=False)
    assert a.status == "PARTIAL"


def test_number_parsing():
    assert _numbers("Call 1-800-555-0199 or ext. 4100; $1,234.50 by 4:30 pm.") >= {"1", "800", "555", "0199", "4100", "1234.50", "4", "30"}
