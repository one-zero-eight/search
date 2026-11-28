"""The documents of eduwiki pages: made by code from the snapshot, without a model."""

from catix.docs.sources import eduwiki

LONG = "A paragraph of the page that says enough words to be content and not a stub. " * 3


def add(db, pid: int, title: str, wikitext: str, redirect: bool = False) -> None:
    db.execute(
        "INSERT INTO eduwiki_pages (pageid, ns, title, revid, redirect, timestamp, wikitext, fetched_at) VALUES (%s, 0, %s, %s, %s, %s, %s, %s)",
        (pid, title, 100 + pid, redirect, "2024-05-01T10:00:00Z", wikitext, "2024-06-01T00:00:00+00:00"))


def test_a_course_page_is_a_document_of_its_own_folder(docs_db):
    add(docs_db, 1, "MSTE: It Product Development", f"= IT Product Development =\n\n{LONG}")
    [doc] = eduwiki.compile_all()
    assert doc.path == "eduwiki/courses/mste-it-product-development"
    assert doc.meta["title"] == "IT Product Development (MSTE)"
    assert doc.meta["type"] == "course"
    assert doc.meta["generated"]["at"] == "2024-06-01T00:00:00+00:00"
    assert doc.body.startswith("# IT Product Development (MSTE)\n")


def test_citations_name_the_revision_and_the_page(docs_db):
    add(docs_db, 2, "Some Page", f"= Some Page =\n\n{LONG}")
    [doc] = eduwiki.compile_all()
    assert "# Citations" in doc.body and "revision 102" in doc.body
    assert doc.meta["sources"][0]["id"] == "102"


def test_a_wiki_link_points_at_the_page_on_eduwiki(docs_db):
    add(docs_db, 3, "Links", f"= Links =\n\n{LONG} See [[Some Page]].")
    add(docs_db, 4, "Other", f"= Other =\n\n{LONG}")
    docs = {d.path: d for d in eduwiki.compile_all()}
    body = docs["eduwiki/pages/links"].body
    assert "https://eduwiki.innopolis.university/index.php/Some_Page" in body


def test_redirects_and_old_versions_make_no_document(docs_db):
    add(docs_db, 5, "Redirect", "#REDIRECT [[Some Page]]" + " " * 100, redirect=True)
    add(docs_db, 6, "Course previous version", f"= Old =\n\n{LONG}")
    assert eduwiki.compile_all() == []


def test_the_manifest_is_read_from_the_snapshot(docs_db):
    add(docs_db, 7, "Some Page", f"= Some Page =\n\n{LONG}")
    docs_db.execute("INSERT INTO eduwiki_pages (pageid, ns, title, revid, deleted) VALUES (8, 0, 'Gone', 108, true)")
    assert eduwiki.load_manifest() == {
        "7": {"title": "Some Page", "revid": 107, "redirect": False, "ns": 0, "deleted": False},
        "8": {"title": "Gone", "revid": 108, "redirect": False, "ns": 0, "deleted": True}}
    assert [d.path for d in eduwiki.compile_all()] == ["eduwiki/pages/some-page"]  # (a deleted page and a page without text make no document)
