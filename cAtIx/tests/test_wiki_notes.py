"""The note of a page (wiki/notes.py): the checks of a card, its own page only, and the two numbers that keep a note a
note — the size and the share of the document's clauses it cites. No model here; the note's text is given."""

from types import SimpleNamespace

import pytest

from catix.wiki import notes

PAGE = "/regulations/leave.md"
OTHER = "/regulations/other.md"
CLAUSES = 10
QUOTE = "Academic leave is granted for up to 12 months"


def index() -> SimpleNamespace:
    """A regulation of ten clauses, and a second page for the note that must not cite it."""
    body = "".join(f"**2.{n}.** Academic leave is granted for up to 12 months, clause {n}.\n\n" for n in range(1, CLAUSES + 1))
    page = lambda text: {"meta": {"type": "regulation", "title": "Regulation on academic leave", "sources": [{"id": "abc123", "last_modified": "2026-01-01"}]}, "body": text}
    return SimpleNamespace(meta={PAGE: page(body), OTHER: page(body)})


@pytest.fixture(autouse=True)
def _bundle(tmp_path, monkeypatch):
    monkeypatch.setattr(notes, "BUNDLE", tmp_path)
    monkeypatch.setattr(notes.agent.settings, "wiki_agent_quotes", True)
    (tmp_path / "regulations").mkdir()
    return tmp_path


def note_body(clauses=(1, 2)) -> str:
    return " ".join(f'Leave lasts up to 12 months [п. 2.{n}]({PAGE}#2.{n} "{QUOTE}"), clause {n} [п. 2.{n}]({PAGE}#2.{n} "{QUOTE}").'
                    for n in clauses)


def test_a_note_of_a_page_is_written_with_its_front_matter_and_its_link_to_the_page(_bundle):
    assert notes.write(PAGE, "Academic leave", "What the regulation of leave is about.", note_body(), index()) == []
    text = (_bundle / "notes" / "leave.md").read_text()
    assert "type: note" in text and f"source: {PAGE}" in text and "evidence_sha: abc123" in text
    assert f"- [Regulation on academic leave]({PAGE})" in text  # the note leads back to its page
    assert "1. [Regulation on academic leave](/regulations/leave.md), п. 2.1" in text  # and cites it


def test_a_note_of_one_page_may_not_cite_another(_bundle):
    body = f'Leave [п. 2.1]({OTHER}#2.1 "{QUOTE}").'
    found = notes.note_problems(body, index(), PAGE)
    assert any(f"a note is of one page ({PAGE}): the sentence cites {OTHER}" in p for p in found)
    assert notes.write(PAGE, "t", "d", body, index()) != []


def test_a_note_is_short_and_does_not_restate_the_document(_bundle):
    long = note_body(clauses=(1, 2)) + " " + "Academic leave is granted for up to 12 months [п. 2.3](/regulations/leave.md#2.3 \"" + QUOTE + "\"). " * 6
    assert any("characters: at most" in p for p in notes.note_problems(long, index(), PAGE))
    most = note_body(clauses=(1, 2, 3, 4, 5))  # five of ten clauses: over the share a note may cite
    found = notes.note_problems(most, index(), PAGE)
    assert any("cites 5 of the 10 clauses" in p for p in found)


def test_the_page_leads_to_its_note_and_the_link_is_written_once(_bundle):
    (_bundle / "regulations" / "leave.md").write_text(
        f'---\ntype: regulation\ntitle: "Regulation on academic leave"\n---\n\n# Regulation on academic leave\n\n'
        f"**2.1.** {QUOTE}.\n\n# Citations\n\n1. [It](https://example.org), file abc\n")
    assert notes.write(PAGE, "Academic leave", "d", note_body(clauses=(1,)), index()) == []
    assert notes.link_pages() == 1
    page = (_bundle / "regulations" / "leave.md").read_text()
    assert "## See also" in page and "- [Note: Academic leave](/notes/leave.md)" in page
    assert notes.link_pages() == 0  # the second pass writes nothing: the link is there
    assert (_bundle / "regulations" / "leave.md").read_text() == page


def test_a_note_that_goes_away_takes_its_line_with_it(_bundle):
    (_bundle / "regulations" / "leave.md").write_text(
        f'---\ntype: regulation\ntitle: "Regulation on academic leave"\n---\n\n# Regulation on academic leave\n\n**2.1.** {QUOTE}.\n')
    notes.write(PAGE, "Academic leave", "d", note_body(clauses=(1,)), index())
    notes.link_pages()
    (_bundle / "notes" / "leave.md").unlink()
    assert notes.link_pages() == 1
    assert "## See also" not in (_bundle / "regulations" / "leave.md").read_text()
