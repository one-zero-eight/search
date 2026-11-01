"""experiments/link_stats.py: what it counts in the pages of a bundle, and the report of one group."""

import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("link_stats", Path(__file__).resolve().parents[1] / "experiments" / "link_stats.py")
stats = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stats)

PAGE = """---
type: page
title: "A [not a link](https://front.example/matter)"
---

# A

[About](/raw/sites/hotel/b.md) and [gone](/raw/sites/hotel/missing.md) and [out](https://example.org/a.pdf?x=1#top)
![ ](https://cdn.example/one.jpg) ![Photo](https://cdn.example/two.png)
[![Linked](https://cdn.example/three.webp)](/raw/sites/hotel/b.md)
[▶ video](https://www.youtube.com/watch?v=abc) [mail](mailto:a@b.ru)

# Citations

1. [A](https://cite.example/a), read 2026-10-30
"""


def bundle(tmp_path):
    for name, text in (("a", PAGE), ("b", "---\ntype: page\n---\n\n[A](/raw/sites/hotel/a.md)\n"), ("_shared", "---\ntype: page\n---\n\n![](https://cdn.example/one.jpg)\n")):
        page = tmp_path / "wiki" / "raw" / "sites" / "hotel" / f"{name}.md"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(text, encoding="utf-8")
    return tmp_path / "wiki", tmp_path / "wiki" / "raw" / "sites"


def test_a_page_is_read_without_its_front_matter_and_its_citations_and_every_link_has_its_line():
    found = stats.occurrences(PAGE)
    kinds = [(o["kind"], o["line"]) for o in found]
    assert ("image", 9) in kinds and ("internal", 8) in kinds and ("external", 8) in kinds and ("video", 11) in kinds and ("other", 11) in kinds
    assert not any("front.example" in o["url"] or "cite.example" in o["url"] for o in found)  # (the page's own address is not a link out)
    linked = next(o for o in found if o["kind"] == "image" and o["text"] == "Linked")
    assert linked["in_link"] == "/raw/sites/hotel/b.md" and linked["line"] == 10
    assert sum(o["kind"] == "internal" for o in found) == 3  # (the link around a picture is a link, with the empty text)


def test_the_report_of_a_group_counts_exactly_what_the_group_is(tmp_path):
    b, folder = bundle(tmp_path)
    pages = stats.collect(b, folder)
    images = stats.group_report(pages, "image", b, top=5, examples=2)
    assert images["occurrences"] == 4 and images["unique_addresses"] == 3 and images["in_shared_pages"] == 1
    assert images["alt"] == {"empty": 2, "with_text": 2, "pictures_that_are_links": 1, "most_common_alt": [("photo", 1), ("linked", 1)]}
    assert images["extensions"] == {"jpg": 2, "png": 1, "webp": 1} and images["repetition"]["addresses_used_more_than_once"] == 1
    internal = stats.group_report(pages, "internal", b, top=5, examples=2)
    assert internal["occurrences"] == 4 and internal["internal"]["links_to_pages_that_do_not_exist"] == 1
    assert internal["internal"]["dead_targets"] == ["/raw/sites/hotel/missing.md"]
    assert internal["internal"]["most_linked_pages"][0] == {"page": "/raw/sites/hotel/b.md", "links": 2, "from_pages": 1}
    files = stats.group_report(pages, "files", b, top=5, examples=2)
    assert files["occurrences"] == 1 and files["addresses"]["with_query"] == 1 and files["addresses"]["with_fragment"] == 1
    assert stats.group_report(pages, "video", b, 5, 2)["platforms"] == {"youtube": 1}
