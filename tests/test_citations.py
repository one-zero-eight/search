"""Backend-owned numbering, resolution and provenance, independent of UI wording."""

from datetime import datetime, timezone
from types import SimpleNamespace

from catix.agent import sources
from catix.common.citations import MAX_SOURCE_IMAGES, CitedAnswer, images_in, render_cited_answer


def document(title="Rules", **fields):
    return {"wiki": True, "title": title, "link": "https://example.org/rules", "trust": "official", **fields}


def test_only_used_sources_are_numbered_in_first_appearance_order():
    registry = {"m0": document("Unused"), "m1": document("First"), "m2": document("Second")}
    result = sources.cite("Second [m2], first [m1], second again [m2], unknown [m99].", registry)
    assert result.answer == "Second [1], first [2], second again [1], unknown."
    assert [(source.number, source.title) for source in result.sources] == [(1, "Second"), (2, "First")]


def test_missing_database_rows_do_not_leave_dangling_numbers_or_consume_run_slots(monkeypatch):
    calls = []

    def lookup(ids):
        calls.append(ids)
        return {}

    monkeypatch.setattr(sources.store, "message_sources", lookup)
    registry = {"m0": {"message_id": 41}, **{f"m{i}": document(f"Rules {i}") for i in range(1, 7)}}
    result = sources.cite("Fact [m0][m1][m2][m3][m4][m5][m6].", registry)
    assert calls == [[41]]
    assert result.answer == "Fact [1][2][3][4][5]."
    assert [source.title for source in result.sources] == [f"Rules {i}" for i in range(1, 6)]
    assert sources.cite("Missing [m0].", {"m0": registry["m0"]}) == CitedAnswer(answer="Missing.")


def test_uncited_database_rows_are_not_read(monkeypatch):
    def unexpected(ids):
        raise AssertionError("An unused source was resolved")

    monkeypatch.setattr(sources.store, "message_sources", unexpected)
    assert sources.cite("Answer", {"m0": {"message_id": 41}}) == CitedAnswer(answer="Answer")


def test_chat_metadata_survives_database_resolution_and_live_messages(monkeypatch):
    date = datetime(2026, 11, 9, tzinfo=timezone.utc)
    row = SimpleNamespace(chat_title="Official chat", link=None, chat_link="https://t.me/official", date=date,
                          sender_name="Author (forwarded by Other)", sender_link="https://t.me/author", chat_official=True,
                          text="Экзамен перенесён")
    monkeypatch.setattr(sources.store, "message_sources", lambda ids: {41: row})
    registry = {"m0": {"message_id": 41}, "m1": {"chat_title": "Live chat", "link": "https://t.me/live/1",
                "date": date.isoformat(), "author": "Live author", "sender_link": "https://t.me/live_author", "text": "Live text"}}
    result = sources.cite("First [m0], live [m1].", registry)
    first, live = result.sources
    assert (first.kind, first.url, first.date, first.author, first.author_url, first.official) == (
        "chat", row.chat_link, date, "Author", row.sender_link, True)
    assert (live.title, live.date, live.author, live.author_url, live.official) == (
        "Live chat", date, "Live author", "https://t.me/live_author", False)
    assert first.text == "Экзамен перенесён" and live.text == "Live text"


def test_a_chat_source_carries_the_message_for_a_preview_and_a_document_does_not():
    live = {"chat_title": "Chat", "link": "https://t.me/c/1/2", "date": datetime(2026, 11, 9, tzinfo=timezone.utc).isoformat(), "author": "A"}
    registry = {"m0": {**live, "text": "x" * (sources.MESSAGE_CHARS + 10)}, "m1": {**live, "link": "https://t.me/c/1/3"}, "m2": document()}
    long, saved_before, rules = sources.cite("Long [m0], old [m1], rules [m2].", registry).sources
    assert long.text == "x" * sources.MESSAGE_CHARS
    assert saved_before.text is None and rules.text is None


def test_a_moodle_file_is_a_moodle_source_not_the_web():
    url = "https://moodle.example.org/pluginfile.php/1/syllabus.pdf#page=2"
    registry = {"m1": {"moodle": True, "title": "Syllabus.pdf (p. 2)", "link": url}}
    result = sources.cite("The course has six credits [m1].", registry)
    assert [(source.kind, source.url) for source in result.sources] == [("moodle", url)]
    assert "(Moodle)" in render_cited_answer(result)


def test_archive_identity_includes_page_revision_and_member():
    archive = {"page": "/raw/archive.md", "revision": "a" * 64, "member": "first.pdf"}
    variants = [archive, {**archive, "member": "second.pdf"}, {**archive, "revision": "b" * 64},
                {**archive, "page": "/raw/other.md"}]
    registry = {f"m{i}": document(archive_document=value, clause=str(i)) for i, value in enumerate(variants)}
    registry["m4"] = document(archive_document=archive, clause="4")
    result = sources.cite("Fact [m0][m1][m2][m3][m4].", registry)
    assert result.answer == "Fact [1][2][3][4][1]."
    assert [source.archive_document.model_dump() for source in result.sources] == variants
    assert result.sources[0].clauses == ["0", "4"]


def test_shared_documents_merge_only_cited_clauses_sections_and_provenance():
    registry = {
        "m0": document(clause="1"), "m1": document(clause="2"), "m2": document(section="Contacts"),
        "m3": document(clause="Unused"), "m4": document(section="Contacts"),
        "m5": document("Guide", trust="guide", based_on=[{"title": "Rules", "link": "https://example.org/rules"}]),
        "m6": document("Guide", trust="guide", based_on=[{"title": "Policy", "link": "https://example.org/policy"}]),
    }
    result = sources.cite("Fact [m0][m1][m2][m4], guide [m5][m6].", registry)
    assert result.answer == "Fact [1], guide [2]."
    first, guide = result.sources
    assert first.clauses == ["1", "2"] and first.sections == ["Contacts"]
    assert [(item.title, item.url) for item in guide.based_on] == [
        ("Rules", "https://example.org/rules"), ("Policy", "https://example.org/policy")]


def test_terminal_renderer_preserves_provenance_without_mutating_answer():
    result = sources.cite("Fact [m0], guide [m1].", {
        "m0": document(clause="4.2"),
        "m1": document("Guide", trust="guide", based_on=[{"title": "Rules", "link": "https://example.org/rules"}]),
    })
    rendered = render_cited_answer(result)
    assert rendered.startswith(result.answer + "\n\nSources:\n")
    assert "https://example.org/rules" in rendered and "4.2" in rendered
    assert "Rules" in rendered and "Guide" in rendered
    assert result.answer == "Fact [1], guide [2]." and "Sources" not in result.answer
    assert render_cited_answer(CitedAnswer(answer="No sources")) == "No sources"


def test_a_site_source_carries_the_pictures_of_its_cited_pieces_except_those_in_the_answer():
    registry = {
        "m0": document(section="A", images=[{"url": "https://e.org/1.png", "alt": "Map"}, {"url": "https://e.org/2.png", "alt": None}]),
        "m1": document(section="B", images=[{"url": "https://e.org/2.png", "alt": None}, {"url": "https://e.org/3.png", "alt": None}]),
        "m2": document("Other"),
    }
    result = sources.cite("Fact [m0][m1].\n![Map](https://e.org/1.png)", registry)
    assert [i.url for i in result.sources[0].images] == ["https://e.org/2.png", "https://e.org/3.png"]
    many = {"m0": document(images=[{"url": f"https://e.org/{i}.png", "alt": None} for i in range(10)])}
    assert len(sources.cite("Fact [m0].", many).sources[0].images) == MAX_SOURCE_IMAGES


def test_images_in_takes_absolute_pictures_once_and_caps_them():
    text = "![a](https://e.org/1.png) ![](https://e.org/1.png) ![](rel.png) [![b](https://e.org/2.png)](https://e.org/doc.pdf)"
    assert images_in(text) == [{"url": "https://e.org/1.png", "alt": "a"}, {"url": "https://e.org/2.png", "alt": "b"}]
    assert len(images_in(" ".join(f"![](https://e.org/{i}.png)" for i in range(9)))) == 4
