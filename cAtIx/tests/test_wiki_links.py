"""The links between the cards (wiki/links.py): written by code from the cards' names, once, at the first mention,
never inside a heading, a link, a quote or code, and the same text twice gives the same file. No model here."""

import pytest

from catix.wiki import links


@pytest.fixture(autouse=True)
def _cards_dir(tmp_path):
    (tmp_path / links.FOLDER).mkdir()
    return tmp_path


def write_card(bundle, slug, title, body, aliases=(), tags=("tests",), sources=("/regulations/x.md",)):
    front = ["---", "type: card", f'title: "{title}"', "tags: " + str(list(tags)).replace("'", '"'), 'audience: ["student"]']
    if aliases:
        front += ["aliases:", *[f'  - "{a}"' for a in aliases]]
    front += ["sources:", *[f"  - resource: {s}" for s in sources], "status: draft", "---"]
    cites = [f"{n}. [Regulation {n}]({s}), п. 1.1" for n, s in enumerate(sources, 1)]
    text = "\n".join([*front, "", f"# {title}", "", body, "", "# Citations", "", *cites, ""])
    (bundle / links.FOLDER / f"{slug}.md").write_text(text, encoding="utf-8")
    return text


def inline(text):
    """The links written into the body (not the ones the `## See also` section holds)."""
    return [line for line in text.splitlines() if "](/knowledge/" in line and not line.lstrip().startswith("- ")]


def card_of(bundle, slug):
    return (bundle / links.FOLDER / f"{slug}.md").read_text(encoding="utf-8")


def body_of(text):
    """The lines of a card's body: after the title heading, before the citations."""
    lines = text.partition("\n# Citations\n")[0].splitlines()
    at = max(i for i, line in enumerate(lines) if line.startswith("# "))
    return [line for line in lines[at + 1:] if line.strip()]


def test_a_card_links_to_the_card_it_speaks_of_once_at_the_first_mention(_cards_dir):
    write_card(_cards_dir, "academic-leave", "Academic leave", "Leave lasts up to 12 months [1].")
    write_card(_cards_dir, "retakes", "Rules of retakes",
               "An academic leave is granted once [1]. The academic leave ends the course [1]. Academic leave again [1].")
    report = links.apply(_cards_dir)
    text = card_of(_cards_dir, "retakes")
    assert report.links == 1 and report.cards_linked == 1
    assert inline(text) == ["An [academic leave](/knowledge/academic-leave.md) is granted once [1]. "
                            "The academic leave ends the course [1]. Academic leave again [1]."]
    assert "- [Academic leave](/knowledge/academic-leave.md)" in text  # and it is named at the end, for the reader


def test_nothing_is_linked_inside_a_heading_a_link_a_quote_or_code(_cards_dir):
    write_card(_cards_dir, "academic-leave", "Academic leave", "Leave lasts up to 12 months [1].")
    write_card(_cards_dir, "other", "Other subject",
               "## Academic leave\n\nAcademic leave in a heading [1].\n\n"
               "Already a link: [Academic leave](/knowledge/academic-leave.md) [1].\n\n"
               "A quote: «Academic leave» [1].\n\nCode: `Academic leave` [1].")
    links.apply(_cards_dir)
    text = card_of(_cards_dir, "other")
    assert "## Academic leave\n" in text  # the heading itself is never a link
    assert "A quote: «Academic leave»" in text and "Code: `Academic leave`" in text
    assert "Already a link: [Academic leave](/knowledge/academic-leave.md)" in text  # nor is a link written twice
    assert inline(text)[0].startswith("Academic leave") is False  # the first mention outside a heading got the link
    assert text.count("](/knowledge/academic-leave.md)") == 3  # that one, the one before, and the reader's section


def test_a_longer_name_takes_the_words_it_covers(_cards_dir):
    write_card(_cards_dir, "interim-assessment", "Interim assessment", "It is held twice a year [1].")
    write_card(_cards_dir, "remote-assessment", "Remote interim assessment", "It is held online [1].")
    write_card(_cards_dir, "covid", "Assessment in 2020",
               "The remote interim assessment was held online [1].\n\nInterim assessment was held [1].")
    links.apply(_cards_dir)
    text = card_of(_cards_dir, "covid")
    assert "(/knowledge/remote-assessment.md)" in inline(text)[0] and "interim assessment](/knowledge/interim" not in text
    assert "(/knowledge/interim-assessment.md)" in inline(text)[1]  # the plain name is linked where it stands alone


def test_a_name_two_cards_answer_to_is_left_alone_and_reported(_cards_dir):
    write_card(_cards_dir, "exam-a", "Entrance examination in maths", "Held in July [1].", aliases=["entrance examination"])
    write_card(_cards_dir, "exam-b", "Entrance examination in physics", "Held in August [1].", aliases=["entrance examination"])
    write_card(_cards_dir, "goer", "An applicant's page", "The entrance examination is held twice [1].")
    report = links.apply(_cards_dir)
    assert report.ambiguous == ["entrance examination"] and report.cards_linked == 0
    assert "](/knowledge/" not in card_of(_cards_dir, "goer")  # nothing invented, nothing guessed


def test_the_phrases_of_a_text_leave_out_the_prose_the_labels_and_the_document_heads():
    text = ("Interim assessment evaluates the work of a student. The Ministry of Science and Higher Education approved "
            "the rules. Правила_приема_ВО_новая_редакция ПРОГРАММАМ. The Director for Development and HR signed it.")
    found = links.phrases_of(text)
    assert "Ministry of Science and Higher" in found  # a name of two capitals and more
    assert "Director for Development" in found  # a name met inside a sentence
    assert not any(p.startswith("Interim assessment evaluates") for p in found)  # a sentence, not a name
    assert not any("Правила" in p or "ПРОГРАММАМ" in p for p in found)  # a label of a document, a head in capitals
    assert links.phrases_of("The higher education programme is approved.", common={"higher", "education", "programme"}) == set()


def test_a_name_the_cards_repeat_without_an_artifact_is_the_candidate_for_a_card(_cards_dir):
    write_card(_cards_dir, "student", "A student's duties", "The Student Council is consulted before the rules change [1].")
    write_card(_cards_dir, "rules", "Rules of the university", "The Student Council approves the plan of events [1].")
    report = links.candidates(_cards_dir)
    found = [c for c in report.items if c.phrase == "Student Council"]
    assert found and found[0].cards == ["rules", "student"]
    assert found[0].verdict == "mention"  # one document cannot carry a card: it would be that document again
    assert "candidate of a card" in found[0].example or found[0].example  # the sentence, for the reader of the report


def test_a_candidate_two_documents_speak_of_is_a_card_and_one_the_bundle_answers_to_is_an_alias(_cards_dir):
    write_card(_cards_dir, "student", "A student's duties", "The Student Council is consulted before the rules change [1].",
               sources=("/regulations/a.md", "/regulations/b.md"))
    write_card(_cards_dir, "rules", "Rules of the university", "The Student Council approves the plan of events [1]. "
               "The Methodological department keeps the programmes [1].", sources=("/regulations/a.md", "/courses/c.md"))
    ( _cards_dir / "regulations").mkdir(exist_ok=True)
    ( _cards_dir / "regulations" / "methodological.md").write_text(
        '---\ntype: regulation\ntitle: "Methodological department — place and tasks"\n---\n\n# Methodological department\n', encoding="utf-8")
    write_card(_cards_dir, "other", "Other subject", "The Methodological department keeps the programmes [1].")
    report = links.candidates(_cards_dir)
    by_phrase = {c.phrase: c for c in report.items}
    assert by_phrase["Student Council"].verdict == "card"
    assert by_phrase["Student Council"].pages == ["/courses/c.md", "/regulations/a.md", "/regulations/b.md"]
    assert by_phrase["Methodological department"].verdict == "alias"
    assert by_phrase["Methodological department"].artifact == "/regulations/methodological.md"
    assert report.by_verdict["card"] == 1 and report.by_verdict["alias"] == 1


def test_the_front_matter_is_never_touched(_cards_dir):
    """A tag or a title is not a sentence a reader follows: the link goes into the text, never into the front matter."""
    write_card(_cards_dir, "academic-leave", "Academic leave", "Leave lasts up to 12 months [1].")
    write_card(_cards_dir, "student", "A student's duties", "Academic leave is granted once [1].", tags=["academic-leave", "student"])
    report = links.apply(_cards_dir)
    text = card_of(_cards_dir, "student")
    assert 'tags: ["academic-leave", "student"]' in text
    assert report.links == 1 and "](/knowledge/academic-leave.md)" in text


def test_an_alias_is_a_name_and_a_second_pass_changes_nothing(_cards_dir):
    write_card(_cards_dir, "dop", "Documents on additional education", "Blank forms are issued by the centre [1].", aliases=["дополнительное образование"])
    write_card(_cards_dir, "listener", "A listener's page", "The дополнительное образование programmes are open to all [1].")
    first = links.apply(_cards_dir)
    text = card_of(_cards_dir, "listener")
    assert first.links == 1 and "(/knowledge/dop.md)" in text
    second = links.apply(_cards_dir)
    assert second.links == 0 and second.changed == [] and card_of(_cards_dir, "listener") == text


def test_one_link_a_paragraph_and_one_link_a_card(_cards_dir):
    write_card(_cards_dir, "academic-leave", "Academic leave", "Leave lasts up to 12 months [1].")
    write_card(_cards_dir, "retakes", "Rules of retakes", "It is granted once [1].")
    write_card(_cards_dir, "student", "A student's duties",
               "Academic leave is granted and rules of retakes apply [1].\n\n"
               "Academic leave is granted again [1].\n\nRules of retakes apply once more [1].")
    links.apply(_cards_dir)
    body = body_of(card_of(_cards_dir, "student"))
    assert body[0].count("](/knowledge/") == 1  # one link a paragraph: the reading stays quiet
    assert body[1].count("](/knowledge/") == 1
    assert body[2].count("](/knowledge/") == 0  # and one card is linked once
