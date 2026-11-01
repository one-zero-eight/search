"""The cards of entities (wiki/agent.py write_entity), the model's folders beside the documents (paths.py), the register of
relations code writes from them (links.py, compile.write_index), and the move of the documents into wiki/raw/ (layout.py).
No model here: the cards' texts are given."""

import json
from types import SimpleNamespace

import pytest

from catix.wiki import agent, compile as wc, layout, links

ORDER = "/raw/regulations/order-2024.md"
STRUCT = "/raw/sites/structure.md"
OFFICE = "/raw/regulations/office.md"
APPOINTED = "Назначить Вандюкова Кирилла Викторовича директором Университета Иннополис с 1 марта 2024 года"
HEADED = "Директор университета — Вандюков Кирилл Викторович"
REPORTS = "Учебный офис подчиняется проректору по образованию"
FILES = "Учебный офис ведёт личные дела обучающихся"


@pytest.fixture(autouse=True)
def _bundle(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "BUNDLE", tmp_path)
    monkeypatch.setattr(agent.settings, "wiki_agent_quotes", True)
    monkeypatch.setattr(agent.settings, "wiki_agent_two_sources", False)  # (an entity rests on two documents whatever it says)
    return tmp_path


def index() -> SimpleNamespace:
    page = lambda typ, body, title: {"meta": {"type": typ, "title": title, "sources": [{"id": "a1", "last_modified": "2024-03-01"}]}, "body": body}
    return SimpleNamespace(meta={
        ORDER: page("regulation", f"**1.** {APPOINTED}.\n", "Приказ о назначении директора"),
        STRUCT: page("page", f"{HEADED}. {REPORTS}.", "Структура университета"),
        OFFICE: page("regulation", f"**2.1.** {FILES}.\n", "Положение об учебном офисе"),
    })


PERSON = (f'Kirill Vandyukov was appointed director of Innopolis University from March 1, 2024 [п. 1]({ORDER}#1 "{APPOINTED}").\n\n'
          f'The structure of the university names him as its director [source]({STRUCT} "{HEADED}").')
POSITION = (f'The director of Innopolis University is Kirill Vandyukov, appointed in 2024 [п. 1]({ORDER}#1 "{APPOINTED}").\n\n'
            f'The structure of the university names the same director [source]({STRUCT} "{HEADED}").')


def person(**change) -> list[str]:
    args = dict(slug="vandyukov-kirill", title="Kirill Vandyukov", description="Director of Innopolis University.", body=PERSON,
                tags=["people"], audience=["public"], idx=index(), folder="people", folder_about="People in their official roles",
                entity={"kind": "person", "name": "Вандюков Кирилл Викторович", "aliases": ["К.В. Вандюков", "Kirill Vandyukov"]})
    args.update(change)
    return agent.write(**args)


def position(notes: list | None = None, **entity) -> list[str]:
    return agent.write("director", "Director of Innopolis University", "Вандюков Кирилл Викторович, by the order of 2024.", POSITION,
                       [], ["public"], index(), folder="positions", folder_about="Positions of the university and who holds them",
                       entity={"kind": "position", "name": "директор Университета Иннополис",
                               "relations": [{"relation": "held by", "inverse": "holds", "to": "/people/vandyukov-kirill.md"}], **entity},
                       notes=notes)


def test_an_entity_is_written_into_a_folder_the_model_declares(_bundle):
    assert person() == []
    text = (_bundle / "people" / "vandyukov-kirill.md").read_text(encoding="utf-8")
    assert 'kind: "person"' in text and 'name: "Вандюков Кирилл Викторович"' in text
    assert '"Вандюков Кирилл Викторович", "К.В. Вандюков"' in text  # the name is an alias too: links.py links by aliases
    assert json.loads((_bundle / "folders.json").read_text())["people"] == "People in their official roles"
    card = agent.read_file_card("vandyukov-kirill", "people")
    assert card["kind"] == "person" and card["aliases"] == ["К.В. Вандюков"] and card["body"] == PERSON  # (the title is a name already)
    assert agent.all_cards() == ["/people/vandyukov-kirill.md"]


def test_a_folder_is_declared_once_and_the_documents_and_notes_are_not_the_models():
    assert "folder_description" in person(folder="staff", folder_about="")[0]  # a new folder says what it holds (but a kind's own)
    assert "folder:" in person(folder="raw")[0] and "folder:" in person(folder="notes")[0]
    assert "folder:" in person(folder="People")[0]


def test_an_entitys_name_stands_in_what_it_quotes():
    found = person(entity={"kind": "person", "name": "Иванов Пётр Сергеевич"})
    assert any("the name «Иванов Пётр Сергеевич» is not in what the card quotes" in p for p in found)
    assert any("kind:" in p for p in person(entity={"kind": "hero", "name": "Вандюков Кирилл Викторович"}))


def test_a_post_is_named_by_the_title_of_its_page():
    # the page of the director is titled by the post, its text names only the person: the model shortened the name to "Директор"
    idx = index()
    idx.meta[STRUCT]["meta"]["title"] = "Директор Университета Иннополис"
    body = f'The page of the director names Kirill Vandyukov [source]({STRUCT} "{HEADED}").'
    entity = {"kind": "position", "name": "Директор Университета Иннополис"}
    assert agent.write("director", "Director", "The post.", body, [], ["public"], idx, folder="positions", entity=entity) == []


def test_a_line_written_twice_is_one_line_with_both_links(_bundle):
    # a local model wrote the director's deputies twice, once from each page that names them
    again = f'Kirill Vandyukov was appointed director of Innopolis University from March 1, 2024 [source]({STRUCT} "{HEADED}").'
    assert person(body=f"{PERSON}\n\n{again}") == []  # (its numbers are in the other link's quote)
    text = (_bundle / "people" / "vandyukov-kirill.md").read_text(encoding="utf-8")
    assert text.count("was appointed director") == 1 and "2024 [1] [2]." in text


def test_a_subject_card_is_not_written_beside_an_entitys_card():
    assert person() == []
    one = f'Kirill Vandyukov was appointed director from March 1, 2024 [п. 1]({ORDER}#1 "{APPOINTED}").'
    found = agent.write("vandyukov-kirill", "Вандюков Кирилл", "The director.", one, [], ["public"], index())
    assert found and found[0].startswith("/people/vandyukov-kirill.md is the card of «Вандюков Кирилл»")
    assert agent.write("director-appointment", "The appointment of the director", "d", one, [], ["public"], index()) == []


def test_an_entity_may_rest_on_one_document():
    one = f'Kirill Vandyukov was appointed director from March 1, 2024 [п. 1]({ORDER}#1 "{APPOINTED}").'
    assert person(body=one) == []


def test_one_entity_is_one_card():
    assert person() == []
    found = person(slug="kirill-vandyukov")
    assert any("/people/vandyukov-kirill.md already answers to" in p for p in found)
    assert person() == []  # its own card it may write again


def test_a_persons_official_contacts_stay(_bundle):
    # the table of the leaders gives a phone and an e-mail beside the name: official data, shown as the page has it
    row = "Вандюков Кирилл Викторович | Директор | (843) 203-92-53 | director@innopolis.ru"
    idx = index()
    idx.meta[STRUCT]["body"] += f"\n\n| {row} |\n"
    body = PERSON.replace(f'"{HEADED}"', f'"{row}"') + f'\n\nHis office phone is (843) 203-92-53 [source]({STRUCT} "{row}").'
    assert person(idx=idx, body=body) == []
    text = (_bundle / "people" / "vandyukov-kirill.md").read_text(encoding="utf-8")
    assert "director@innopolis.ru" in text and "(843) 203-92-53" in text


def test_a_relation_to_a_card_not_written_yet_waits_for_it(_bundle):
    # the post "held by" the person and the person "holds" the post: each was refused until the other was written
    notes: list = []
    assert position(notes=notes) == [] and "without the relation 'held by' to /people/vandyukov-kirill.md" in notes[0]
    write_entity = {t.name: t for t in agent._tools([index()], [])}["write_entity"]
    said = write_entity.invoke({"folder": "positions", "slug": "director", "kind": "position", "name": "директор Университета Иннополис",
                                "title": "Director of Innopolis University", "description": "Вандюков Кирилл Викторович, by the order of 2024.",
                                "body": POSITION, "relations": [{"relation": "held by", "inverse": "holds", "to": "/people/vandyukov-kirill.md"}]})
    assert said.startswith("written: /positions/director.md") and "without the relation 'held by' to /people/vandyukov-kirill.md" in said
    assert "('holds' to /positions/director.md)" in said
    assert "relations:" not in (_bundle / "positions" / "director.md").read_text(encoding="utf-8")
    holds = [{"relation": "holds", "inverse": "held by", "to": "/positions/director.md"}]
    assert person(entity={"kind": "person", "name": "Вандюков Кирилл Викторович", "aliases": ["Kirill Vandyukov"], "relations": holds}) == []
    links.apply(_bundle)
    assert "- held by: [Kirill Vandyukov](/people/vandyukov-kirill.md)" in (_bundle / "positions" / "director.md").read_text(encoding="utf-8")
    wc.write_index(wc.concepts(_bundle), _bundle)  # (the register says who holds the post from the person's card too)
    assert "— held by [Kirill Vandyukov](/people/vandyukov-kirill.md)" in (_bundle / "positions" / "index.md").read_text(encoding="utf-8")


def test_a_relation_leads_to_an_entity_the_documents_of_the_card_name():
    assert person() == []
    assert position() == []
    office = (f'The study office reports to the vice-rector for education [source]({STRUCT} "{REPORTS}").\n\n'
              f'It keeps the personal files of students [п. 2.1]({OFFICE}#2.1 "{FILES}").')
    found = agent.write("study-office", "Study office", "The unit that keeps students' files.", office, [], [], index(),
                        folder="units", folder_about="Units of the university",
                        entity={"kind": "unit", "name": "Учебный офис", "relations": [{"relation": "head", "to": "/people/vandyukov-kirill.md"}]})
    assert any("its name «Вандюков Кирилл Викторович» (or an alias) is not in what this card quotes" in p for p in found)


def test_a_relation_agrees_with_the_one_leading_back(_bundle):
    # the person's card said "held by" the post whose card said "held by" the person: the person's is made "holds"
    assert person() == [] and position() == []
    wrong = [{"relation": "held by", "inverse": "holds", "to": "/positions/director.md"}]
    assert person(entity={"kind": "person", "name": "Вандюков Кирилл Викторович", "relations": wrong}) == []
    text = (_bundle / "people" / "vandyukov-kirill.md").read_text(encoding="utf-8")
    assert '{"relation": "holds", "inverse": "held by", "to": "/positions/director.md"}' in text


def test_the_relations_are_written_into_both_cards_and_the_register(_bundle):
    assert person() == [] and position() == []
    report = links.apply(_bundle)
    assert report.relations == 2
    holder = (_bundle / "people" / "vandyukov-kirill.md").read_text(encoding="utf-8")
    post = (_bundle / "positions" / "director.md").read_text(encoding="utf-8")
    assert "## Relations\n\n- held by: [Kirill Vandyukov](/people/vandyukov-kirill.md)" in post
    assert "## Relations\n\n- holds: [Director of Innopolis University](/positions/director.md)" in holder
    assert "## See also" not in post and "## See also" not in holder  # (each named the other: the relation says it already)
    assert links.apply(_bundle).changed == []  # the same twice
    body = agent.read_file_card("director", "positions")["body"]
    assert "## Relations" not in body and "held by" not in body  # the agent gets back what it wrote, not the program's section
    assert "[Kirill Vandyukov](/people/vandyukov-kirill.md)" in body  # and the link code wrote from the name of the holder's card
    assert agent.check_all(index()) == {}
    wc.write_index(wc.concepts(_bundle), _bundle)
    register = (_bundle / "positions" / "index.md").read_text(encoding="utf-8")
    assert ("- [Director of Innopolis University](/positions/director.md): Вандюков Кирилл Викторович, by the order of 2024. "
            "— held by [Kirill Vandyukov](/people/vandyukov-kirill.md)") in register
    root = (_bundle / "index.md").read_text(encoding="utf-8")
    assert "(/positions/index.md): Positions of the university and who holds them, 1 pages" in root


def test_a_relation_whose_card_went_away_no_longer_holds(_bundle):
    assert person() == [] and position() == []
    (_bundle / "people" / "vandyukov-kirill.md").unlink()
    broken = agent.check_all(index())
    assert list(broken) == ["/positions/director.md"] and "there is no entity card" in broken["/positions/director.md"][0]


def test_only_documents_are_evidence_and_an_old_path_is_named():
    found = agent.problems(f'Appointed in 2024 [п. 1](/regulations/order-2024.md#1 "{APPOINTED}").', index())
    assert any("the documents are under /raw/, cite /raw/regulations/order-2024.md" in p for p in found)
    assert agent.resolve("/regulations/order-2024.md", index()) == ORDER


def test_the_documents_move_into_raw_and_every_path_to_them_follows(tmp_path):
    bundle = tmp_path / "wiki"
    (bundle / "regulations").mkdir(parents=True)
    (bundle / "courses").mkdir()
    (bundle / "knowledge").mkdir()
    (bundle / "regulations" / "x.md").write_text("---\ntype: regulation\n---\n\n**1.** Text.\n")
    (bundle / "courses" / "c.md").write_text("---\ntype: course\n---\n\nTaught by [Y](/people/y.md), see https://site/regulations/x.md\n")
    (bundle / "knowledge" / "k.md").write_text('---\ntype: card\nsources:\n  - resource: "/regulations/x.md"\n---\n\nText [1].\n\n'
                                               "# Citations\n\n1. [X](/regulations/x.md), п. 1\n")
    assert layout.to_move(bundle) == ["courses", "regulations"]
    assert layout.move_files(["courses", "regulations"], bundle) == 2
    assert layout.rewrite_files(["courses", "regulations", "people"], bundle) == 2
    assert (bundle / "raw" / "regulations" / "x.md").exists() and not (bundle / "regulations").exists()
    card = (bundle / "knowledge" / "k.md").read_text()
    assert 'resource: "/raw/regulations/x.md"' in card and "1. [X](/raw/regulations/x.md), п. 1" in card
    course = (bundle / "raw" / "courses" / "c.md").read_text()
    assert "[Y](/raw/people/y.md)" in course and "https://site/regulations/x.md" in course  # a URL is not a path of the bundle
    assert layout.to_move(bundle) == []  # a second run finds nothing


def test_a_task_lists_the_cards_of_its_documents_once_there_are_many(_bundle, monkeypatch):
    (_bundle / "knowledge").mkdir()
    for n in range(agent.CARDS_IN_TASK + 5):
        source = ORDER if n == 3 else OFFICE
        (_bundle / "knowledge" / f"card-{n}.md").write_text(
            f'---\ntype: card\ntitle: "Card {n}"\ndescription: "d"\nsources:\n  - resource: "{source}"\n---\n\nText [1].\n')
    monkeypatch.setattr(agent, "near_cards", lambda pages, idx: ["/knowledge/card-7.md"])
    listed = agent.cards_now([ORDER], index())
    assert listed.splitlines()[:2] == ["- /knowledge/card-3.md: Card 3", "- /knowledge/card-7.md: Card 7"]
    assert f"({agent.CARDS_IN_TASK + 3} more cards in knowledge" in listed
    tools = {t.name: t for t in agent._tools([index()], [])}
    assert tools["list_cards"].invoke({"words": "card 3"}).splitlines()[0].startswith("/knowledge/card-3.md")
    assert "more: give folder or words" in tools["list_cards"].invoke({}).splitlines()[-1]


def test_an_entity_is_found_by_its_name_wherever_it_is():
    tools = {t.name: t for t in agent._tools([index()], [])}
    assert "there is none yet" in tools["list_cards"].invoke({"folder": "knowledge", "words": "Вандюков"})
    assert "there is none yet" in tools["read_card"].invoke({"card": "Вандюков Кирилл Викторович"})
    assert person() == []
    found = tools["list_cards"].invoke({"folder": "knowledge", "words": "Вандюков"})  # (not in knowledge/: looked for everywhere)
    assert found.startswith("/people/vandyukov-kirill.md [person: Вандюков Кирилл Викторович]")
    assert tools["list_cards"].invoke({"words": "К.В. Вандюков"}).startswith("/people/vandyukov-kirill.md")  # an alias
    assert tools["read_card"].invoke({"card": "Вандюков Кирилл Викторович"})["folder"] == "people"
    folders = tools["list_folders"].invoke({})
    assert folders.startswith("knowledge — ") and "\npeople — People in their official roles (1 cards)" in folders
    assert "not made yet, write_entity into one makes it: positions (position), units (unit)" in folders


def test_the_folder_of_a_kind_is_made_by_itself_and_sources_may_be_listed_at_the_end(_bundle):
    listed = f'Kirill Vandyukov is the director.\n\nHe was appointed in 2024.\n\n[Order]({ORDER}#1)\n[Structure]({STRUCT} "{HEADED}")'
    assert person(folder_about="", body=listed, entity={"kind": "person", "name": "Вандюков Кирилл Викторович", "aliases": ["director@x.ru"]}) == []
    assert "People of the university" in json.loads((_bundle / "folders.json").read_text())["people"]
    text = (_bundle / "people" / "vandyukov-kirill.md").read_text(encoding="utf-8")
    assert "director@x.ru" not in text and "He was appointed in 2024." in text  # (an alias is a name; the lines above the sources stay)


def test_a_persons_card_is_titled_by_the_name(_bundle):
    assert person(title="Director of Innopolis University", description="Director of Innopolis University") == []
    card = agent.read_file_card("vandyukov-kirill", "people")
    assert card["title"] == "Вандюков Кирилл Викторович" and card["description"] == "Director of Innopolis University"


def test_a_person_named_in_short_is_the_same_person():
    assert agent.same_person("Екатерина Галиханова", "Галиханова Екатерина Борисовна")
    assert agent.same_person("Вандюкова Кирилла", "Вандюков Кирилл Викторович")  # (a case form)
    assert not agent.same_person("Кирилл", "Вандюков Кирилл Викторович")  # (one word is not a name)
    assert not agent.same_person("Екатерина Иванова", "Галиханова Екатерина Борисовна")
    assert person() == []
    found = person(slug="kirill-vandyukov", entity={"kind": "person", "name": "Кирилл Вандюков"})
    assert any("/people/vandyukov-kirill.md already answers to «Вандюков Кирилл Викторович», the same person" in p for p in found)
