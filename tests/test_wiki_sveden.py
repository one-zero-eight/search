"""What a document of innopolis.university/sveden belongs to, from the markup around its link (sveden.context_of)."""

from catix.wiki.sources.sveden import FILE, context_of


def contexts(page: str) -> list[str]:
    return [context_of(page, m.start()) for m in FILE.finditer(page)]


def test_a_cell_of_a_table_of_programmes_gives_the_programme_the_year_and_the_kind_of_document():
    page = """<li>Высшее образование</li><table><caption>Образовательная программа высшего образования - программа магистратуры:
      38.04.05 Бизнес-информатика</caption><thead><tr><th data-name="year">Год</th><th data-name="learn_plan">Учебные планы</th></tr></thead>
      <tbody><tr><td data-name="year">2025</td><td data-name="learn_plan"><a href="/upload/x/УП.pdf"><u>Учебный план</u></a></td></tr></tbody></table>"""
    assert contexts(page) == ["магистратуры: 38.04.05 Бизнес-информатика — 2025 — Учебные планы"]


def test_a_unit_of_the_structure_gives_its_name_not_the_first_unit_of_the_list():
    page = """<ul><li itemprop="structOrgUprav"><div itemprop="name">Администрация</div><div itemprop="fio">Вандюков</div>
      <a href="/upload/a/Положение об Администрации.pdf">Положение</a></li>
      <li itemprop="structOrgUprav"><div itemprop="name">Центр развития проектов </div><div itemprop="fio">-</div>
      <a href="/upload/b/Положение о Центре.pdf">Положение</a></li></ul>"""
    assert contexts(page) == ["Администрация", "Центр развития проектов"]


def test_a_link_in_a_panel_gives_the_panel_header():
    page = """<div class="expand-panel__header collapsed"> Программа бакалавриата 09.03.01 <i class="icon"></i></div>
      <ul><li><a download="" href="/upload/c/Результаты.pdf">Результаты опросов</a></li></ul>"""
    assert contexts(page) == ["Программа бакалавриата 09.03.01"]


def test_supported_archives_are_reconsidered_but_person_decisions_stay(tmp_path, monkeypatch):
    import json
    from catix.wiki.sources import sveden

    monkeypatch.setattr(sveden, "INDEX", tmp_path / "index.json")
    monkeypatch.setattr(sveden, "TRIAGE", tmp_path / "triage.json")
    docs = [{"url": f"https://innopolis.university/{n}.zip", "ext": "zip", "title": n, "sections": ["document"]}
            for n in ("old", "manual", "new")]
    sveden.INDEX.write_text(json.dumps(docs))
    sveden.TRIAGE.write_text(json.dumps({docs[0]["url"]: {"decision": "skip", "by": "code", "reason": "zip archive or spreadsheet: not opened yet"},
                                        docs[1]["url"]: {"decision": "skip", "by": "person", "reason": "not relevant"}}))
    called = []
    monkeypatch.setattr(sveden, "_llm", lambda system, listing: called.append(listing) or ("1: KEEP useful\n2: KEEP useful", {}))
    sveden.triage()
    decisions = json.loads(sveden.TRIAGE.read_text())
    assert len(called) == 1 and "manual" not in called[0]
    assert decisions[docs[0]["url"]]["decision"] == decisions[docs[2]["url"]]["decision"] == "keep"
    assert decisions[docs[1]["url"]]["decision"] == "skip"
