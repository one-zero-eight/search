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


def test_a_document_names_its_subjects_in_its_headings_and_the_leads_of_its_clauses():
    text = ("---\ntype: regulation\ntitle: \"X\"\n---\n\n# X\n\n## Пересдача промежуточной аттестации\n\n"
            "**5.3.** Академический отпуск предоставляется на срок не более 12 месяцев.\n\n# Citations\n\n"
            "1. [X](/regulations/x.md)\n")
    spans = links.names_of_document(text)
    assert "Пересдача промежуточной аттестации" in spans  # a section names a subject
    assert any(span.startswith("5.3.") for span in spans)  # a clause names its own
    assert "12 месяцев" not in spans  # the prose of the clause is not read: it repeats the template of the document


def test_a_phrase_two_documents_name_in_a_heading_and_no_artifact_answers_is_a_card(_cards_dir):
    for folder, name in (("regulations", "a"), ("procedures", "b")):
        ( _cards_dir / folder).mkdir(exist_ok=True)
        ( _cards_dir / folder / f"{name}.md").write_text(
            f'---\ntype: regulation\ntitle: "Документ {name}"\n---\n\n# Документ {name}\n\n## Академический отпуск порядок оформления\n',
            encoding="utf-8")
    write_card(_cards_dir, "leave", "Leave", "The order of it [1].")
    report = links.candidates(_cards_dir)
    found = [c for c in report.items if "Академический отпуск" in c.phrase]
    assert found and found[0].verdict == "card"
    assert found[0].documents == 2 and found[0].folders == 2
    assert found[0].cards == []  # the card names it in its title, not in its headings or its prose


def test_a_phrase_the_bundle_answers_to_is_an_alias_not_a_card(_cards_dir):
    for folder, name in (("regulations", "a"), ("procedures", "b")):
        ( _cards_dir / folder).mkdir(exist_ok=True)
        ( _cards_dir / folder / f"{name}.md").write_text(
            f'---\ntype: regulation\ntitle: "Документ {name}"\n---\n\n# Документ {name}\n\n## Академический отпуск порядок оформления\n',
            encoding="utf-8")
    ( _cards_dir / "pages").mkdir(exist_ok=True)
    ( _cards_dir / "pages" / "leave.md").write_text(
        '---\ntype: page\ntitle: "Академический отпуск порядок оформления"\n---\n\n# Академический отпуск порядок оформления\n',
        encoding="utf-8")
    report = links.candidates(_cards_dir)
    found = [c for c in report.items if "Академический отпуск" in c.phrase]
    assert found and found[0].verdict == "alias" and found[0].artifact == "/pages/leave.md"


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
