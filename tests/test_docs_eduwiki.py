"""The documents of eduwiki pages: made by code from the snapshot, without a model."""

from catix.docs import files
from catix.docs.sources import eduwiki

LONG = "A paragraph of the page that says enough words to be content and not a stub. " * 3


def add(pid: int, title: str, wikitext: str, redirect: bool = False) -> None:
    manifest = files.read_json(eduwiki.MANIFEST) or {}
    manifest[str(pid)] = {"title": title, "revid": 100 + pid, "redirect": redirect, "ns": 0}
    files.write_json(eduwiki.MANIFEST, manifest)
    files.write_json(f"{eduwiki.PAGES}/{pid}.json", {
        "pageid": pid, "title": title, "ns": 0, "revid": 100 + pid, "timestamp": "2024-05-01T10:00:00Z",
        "wikitext": wikitext, "fetched_at": "2024-06-01T00:00:00+00:00"})


def test_a_course_page_is_a_document_of_its_own_folder():
    add(1, "MSTE: It Product Development", f"= IT Product Development =\n\n{LONG}")
    [doc] = eduwiki.compile_all()
    assert doc.path == "eduwiki/courses/mste-it-product-development"
    assert doc.meta["title"] == "IT Product Development (MSTE)"
    assert doc.meta["type"] == "course"
    assert doc.meta["generated"]["at"] == "2024-06-01T00:00:00+00:00"
    assert doc.body.startswith("# IT Product Development (MSTE)\n")


def test_citations_name_the_revision_and_the_page():
    add(2, "Some Page", f"= Some Page =\n\n{LONG}")
    [doc] = eduwiki.compile_all()
    assert "# Citations" in doc.body and "revision 102" in doc.body
    assert doc.meta["sources"][0]["id"] == "102"


def test_a_wiki_link_points_at_the_page_on_eduwiki():
    add(3, "Links", f"= Links =\n\n{LONG} See [[Some Page]].")
    add(4, "Other", f"= Other =\n\n{LONG}")
    docs = {d.path: d for d in eduwiki.compile_all()}
    body = docs["eduwiki/pages/links"].body
    assert "https://eduwiki.innopolis.university/index.php/Some_Page" in body


def test_redirects_and_old_versions_make_no_document():
    add(5, "Redirect", "#REDIRECT [[Some Page]]" + " " * 100, redirect=True)
    add(6, "Course previous version", f"= Old =\n\n{LONG}")
    assert eduwiki.compile_all() == []
