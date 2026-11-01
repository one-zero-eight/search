from catix.wiki.markup import convert


def test_headings_lists_links_and_emphasis():
    out = convert("= Title =\n== Part ==\n* a\n** b\n# one\n''it'' '''bold''' [[Page|label]] [https://x.org site]\n__TOC__")
    assert out.splitlines() == [
        "## Title", "### Part", "- a", "  - b", "1. one",
        "*it* **bold** [label](wiki:Page) [site](https://x.org)",
    ]


def test_stubs_and_templates_are_empty():
    from catix.wiki.compile import empty_reason

    assert empty_reason("## Critical Thinking", [])
    assert empty_reason("@@TABLE_0@@", ["| 1 | 2 |"])
    assert empty_reason("Название: ______\nКем: ______\nКогда: ______\n" + "слово " * 200, []) == "blank template"
    assert empty_reason("Курс про компиляторы и их устройство. " * 10, []) is None
