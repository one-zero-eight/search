from catix.wiki.regulations import to_markdown


def test_numbered_clauses_and_chapters():
    md = to_markdown("1. Общие положения\n\n1.1. Первый пункт\nпродолжение строки.\n\n1.2. Второй пункт.")
    assert md.split("\n\n") == ["## 1. Общие положения", "**1.1.** Первый пункт продолжение строки.", "**1.2.** Второй пункт."]


def test_flat_numbering_has_clauses_not_chapters():
    md = to_markdown("1. Настоящее Положение определяет порядок\nперехода обучающихся.\n\n2. Положение обязательно для всех.")
    assert md.split("\n\n") == ["**1.** Настоящее Положение определяет порядок перехода обучающихся.", "**2.** Положение обязательно для всех."]


def test_table_rows_from_layout_gaps_and_page_numbers():
    md = to_markdown("Буква        Оценка\nA            отлично\n\n12\n")
    assert md == "| Буква | Оценка |\n| --- | --- |\n| A | отлично |"


def test_audience_is_kept_to_the_closed_set():
    from catix.wiki.compile import AUDIENCES, clean_audience
    from catix.wiki.topics import parse

    assert clean_audience("Students, teachers and the rector") == ["student", "teacher"]
    assert clean_audience("everyone") == list(AUDIENCES)  # nothing usable: the page is for all readers
    t = parse("TOPIC: phd-attestation | PhD attestation | How is a PhD student attested? | d1 | phd, attestation | postgraduate, teacher")[0]
    assert t["audience"] == ["postgraduate", "teacher"]
