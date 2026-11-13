from catix.wiki.tables import extract, to_markdown


def test_spans_are_repeated_in_every_covered_cell():
    md = to_markdown('{| class="wikitable"\n! A !! B\n|-\n| rowspan="2" | x || 1\n|-\n| 2\n|}')
    assert md.splitlines()[2:] == ["| x | 1 |", "| x | 2 |"]


def test_colspan_header_and_links():
    md = to_markdown('{|\n! colspan="2" | Group\n|-\n! a !! b\n|-\n| [[Page|Name]] || [https://x.org site]\n|}')
    assert md.splitlines()[0] == "| Group / a | Group / b |"
    assert md.splitlines()[2] == "| [Name](wiki:Page) | [site](https://x.org) |"


def test_empty_rows_and_columns_are_dropped_and_pipes_escaped():
    md = to_markdown("{|\n! A !! !! C\n|-\n| 1 || || a|b\n|-\n| || ||\n|}")
    assert md.splitlines()[0] == "| A | C |"
    assert md.splitlines()[2] == "| 1 | a\\|b |"


def test_extract_replaces_tables_by_tokens():
    text, tables = extract("before\n{|\n! A\n|-\n| 1\n|}\nafter")
    assert text == "before\n@@TABLE_0@@\nafter"
    assert tables[0].splitlines()[-1] == "| 1 |"
