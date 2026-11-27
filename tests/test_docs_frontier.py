"""The crawl as tables (frontier.py), the reading of a page into them (sites.read_page), the catalog's table and the notes of the
documents, in a real Postgres (the docs_db fixture); the loop that reads the rows (runner.py) with fake reads."""

from argparse import Namespace
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
import pytest

from catix.docs import build, frontier, notes, parse_requests, runner, sources
from catix.docs.sources import regulations, sites

NOW = datetime.now(timezone.utc)


def put(db, address: str, site: str, priority: int, next_at: datetime | None, kind: str = "page", state: str = "new") -> None:
    db.execute(
        """INSERT INTO crawl_urls (address, url, site, kind, every, next_at, priority, state, doc_key) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (address, address, site, kind, timedelta(days=7), next_at, priority, state, f"key-{address}" if kind == "document" else None))


def row(db, address: str) -> frontier.Row:
    return frontier.Row(**db.execute("SELECT * FROM crawl_urls WHERE address = %s", (address,)).fetchone())


def test_the_row_due_next_is_a_request_then_a_new_address_then_a_recheck_each_by_its_time(docs_db):
    hour = timedelta(hours=1)
    put(docs_db, "https://hotel.innopolis.university/old", "hotel", frontier.RECHECK, NOW - 5 * hour)
    put(docs_db, "https://hotel.innopolis.university/new-b", "hotel", frontier.NEW, NOW - 2 * hour)
    put(docs_db, "https://hotel.innopolis.university/new-a", "hotel", frontier.NEW, NOW - 3 * hour)
    put(docs_db, "https://apply.innopolis.university/ask", "apply", frontier.REQUEST, NOW - hour)
    put(docs_db, "https://hotel.innopolis.university/later", "hotel", frontier.NEW, NOW + hour)  # (not due)
    order = []
    while due := frontier.next_due():
        order.append(due.address.rsplit("/", 1)[1])
        frontier.save(due, next_at=NOW + 2 * hour)
    assert order == ["ask", "new-a", "new-b", "old"]


def test_a_request_raises_only_the_rows_of_its_site(docs_db):
    put(docs_db, "https://hotel.innopolis.university/a", "hotel", frontier.RECHECK, NOW + timedelta(days=3))
    put(docs_db, "https://hotel.innopolis.university/gone", "hotel", frontier.RECHECK, None, state="gone")
    put(docs_db, "https://apply.innopolis.university/a", "apply", frontier.RECHECK, NOW + timedelta(days=3))
    assert frontier.request(["hotel"]) == 1
    assert frontier.requested(["hotel"]) and not frontier.requested(["apply"])
    assert frontier.next_due().address == "https://hotel.innopolis.university/a"
    assert row(docs_db, "https://apply.innopolis.university/a").priority == frontier.RECHECK


PAGE = """<html><head><title>Rooms of the hotel</title></head><body>
<p>The dormitory rooms of the campus are given to the students of the university for the whole year of study.</p>
<a href="/rooms/">Rooms</a> <a href="https://apply.innopolis.university/en/">Apply</a>
<a href="/upload/docs-hotel/rules.pdf">Rules of living</a> <a href="https://example.org/elsewhere">Elsewhere</a>
</body></html>"""


def served(html: str):
    def get_page(client, site, url, validators=None):
        return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, text=html, request=httpx.Request("GET", url))

    return get_page


def test_the_links_of_a_page_are_rows_by_where_they_lead_and_every_link_is_noted(docs_db, monkeypatch):
    monkeypatch.setattr(sites, "get_page", served(PAGE))
    start = "https://hotel.innopolis.university/"
    frontier.add([frontier.Found(start, "hotel", "page")])
    page = row(docs_db, sites.address(start))
    assert sites.read_page(None, page) is True
    rows = docs_db.execute("SELECT address, site, kind, priority, state, doc_key FROM crawl_urls WHERE address <> %s ORDER BY address", (sites.address(start),)).fetchall()
    pdf = "https://hotel.innopolis.university/upload/docs-hotel/rules.pdf"
    assert [(r["address"], r["site"], r["kind"], r["priority"], r["state"]) for r in rows] == [
        ("https://apply.innopolis.university/en", "apply", "page", frontier.NEW, "new"),
        ("https://hotel.innopolis.university/rooms", "hotel", "page", frontier.NEW, "new"),
        (pdf, "hotel", "document", frontier.NEW, "new")]
    assert rows[2]["doc_key"] == sites.doc_key("hotel", pdf)  # (a new document is keyed by the site that hosts it)
    links = docs_db.execute("SELECT dst, anchor FROM crawl_links WHERE src = %s ORDER BY dst", (sites.address(start),)).fetchall()
    assert sorted((r["dst"].rsplit("/", 1)[-1], r["anchor"]) for r in links) == [
        ("elsewhere", "Elsewhere"), ("en", "Apply"), ("rooms", "Rooms"), ("rules.pdf", "Rules of living")]  # (an unknown host is a link, not a row)
    kept = row(docs_db, sites.address(start))
    assert (kept.state, kept.title, kept.slug, kept.priority) == ("ok", "Rooms of the hotel", "home", frontier.RECHECK) and "dormitory rooms" in kept.text


def test_a_row_added_by_a_request_is_a_request_when_it_is_of_the_site_or_a_document(docs_db):
    put(docs_db, "https://hotel.innopolis.university/", "hotel", frontier.REQUEST, NOW)
    by = row(docs_db, "https://hotel.innopolis.university/")
    frontier.add([frontier.Found("https://hotel.innopolis.university/x", "hotel", "page"),
                  frontier.Found("https://apply.innopolis.university/y", "apply", "page"),
                  frontier.Found("https://apply.innopolis.university/z.pdf", "apply", "document")], by=by)
    got = {r["address"].rsplit("/", 1)[1]: r["priority"] for r in docs_db.execute("SELECT address, priority FROM crawl_urls WHERE address <> %s", (by.address,)).fetchall()}
    assert got == {"x": frontier.REQUEST, "y": frontier.NEW, "z.pdf": frontier.REQUEST}


def test_a_site_takes_no_more_pages_than_its_max_pages(docs_db, site_catalog, monkeypatch):
    raw = sites.load_config()
    raw["sites"]["hotel"]["max_pages"] = 2
    sites.save_catalog(raw)
    sites.reload_catalog()
    assert frontier.add([frontier.Found(f"https://hotel.innopolis.university/p{i}", "hotel", "page") for i in range(5)]) == 2
    assert frontier.add([frontier.Found("https://hotel.innopolis.university/files/a.pdf", "hotel", "document")]) == 1  # (documents are no pages)


def test_a_note_with_a_key_that_is_no_column_is_refused():
    with pytest.raises(ValueError, match="surprise"):
        notes.put_note("key", "", {"title": "x", "surprise": 1})


def test_a_note_is_replaced_whole_and_its_text_stays(docs_db):
    notes.put_text("regulation", "", "text")
    notes.put_note("regulation", "", {"title": "T", "sha256": "ab", "refetch": True, "remote": {"etag": "x"}, "fetched_at": "2026-01-02T03:04:05+00:00"})
    assert notes.note("regulation") == {"title": "T", "sha256": "ab", "refetch": True, "remote": {"etag": "x"}, "fetched_at": "2026-01-02T03:04:05+00:00"}
    notes.put_note("regulation", "", {"title": "U", "failed": False})
    assert notes.note("regulation") == {"title": "U"} and notes.text("regulation") == "text" and notes.has_text("regulation")


def test_the_catalog_round_trips_through_its_tables_and_a_bad_record_changes_nothing(docs_db, site_catalog, monkeypatch):
    monkeypatch.setattr(sites, "load_config", site_catalog.load_config)
    monkeypatch.setattr(sites, "save_catalog", site_catalog.save_catalog)
    base = {"language": "ru", "about": "about", "skip": ""}
    raw = {"sites": {"a": {**base, "base": "https://a.example/", "sitemap": False},
                     "b": {**base, "base": "https://b.example/", "sitemap": True, "max_pages": 7},
                     "c": {**base, "base": "https://c.example/", "sitemap": "wp-sitemap.xml", "feeds": ["news/"], "audience": ["staff"], "pause": 3.5,
                           "end": "Related", "aliases": ["old.c.example"]}},
           "blocked": ["x.example"]}
    sites.save_catalog(raw)
    back = sites.load_config()
    assert {n: sites.make_site(r) for n, r in back["sites"].items()} == {n: sites.make_site(r) for n, r in raw["sites"].items()}
    assert back["blocked"] == ["x.example"]
    with pytest.raises(psycopg.errors.CheckViolation):
        sites.save_catalog({"sites": {"a": {**raw["sites"]["a"], "language": "de"}}, "blocked": []})
    assert sites.load_config() == back
    with pytest.raises(ValueError, match="site a"):
        sites.save_catalog({"sites": {"a": {"language": "ru", "about": "no base"}}, "blocked": []})
    assert sites.load_config() == back


def args(**kw) -> Namespace:
    return Namespace(**{"source": None, "site": None, "build": False, "loop": False, **kw})


def test_a_request_for_a_site_is_finished_when_its_rows_are_read_and_only_its_documents_are_rebuilt(docs_db, parse_queue, monkeypatch):
    asked = parse_requests.submit("sites", "sites", ["hotel"])
    rebuilt = []

    def read_page(client, page):
        frontier.save(page, state="ok")
        return page.site == "hotel"

    def read_listing(client, listing):
        frontier.save(listing, state="ok")
        return False

    monkeypatch.setattr(sites, "read_page", read_page)
    monkeypatch.setattr(sites, "read_listing", read_listing)
    monkeypatch.setattr(sources, "JOBS", [])  # (no job reads the eduwiki here)
    monkeypatch.setattr(regulations, "recheck", lambda keys: [])
    monkeypatch.setattr(build, "rebuild", lambda groups=None: rebuilt.append(groups) or {"pages new": 1})
    runner.run(args())
    done = parse_requests.get(asked.id)
    assert (done.status, done.outcome) == ("done", "changed") and done.result.startswith("documents: 1 new, 0 changed, 0 removed")
    assert rebuilt == [{"sites/hotel"}]
    assert docs_db.execute("SELECT count(*) AS n FROM crawl_urls WHERE site = 'hotel' AND priority = %s", (frontier.REQUEST,)).fetchone()["n"] == 0


# -- the import of the old store (legacy.py)

from catix.docs import legacy  # noqa: E402
from catix.docs.sources import crawl  # noqa: E402

HOTEL, APPLY = "https://hotel.innopolis.university/", "https://apply.innopolis.university/"
RULES, PRICES, PACK, OLD = (f"{HOTEL}upload/docs-hotel/{name}" for name in ("rules.pdf", "prices.pdf", "pack.zip", "old.pdf"))
SHA, MEMBER_SHA = "a" * 64, "b" * 64


def site_record(base: str) -> dict:
    return {"base": base, "language": "ru", "about": "about", "skip": "upload/", "sitemap": False}


def source_files(db) -> None:
    """The old store: what the sources kept as files, as the paths and the JSON they wrote."""
    db.execute("""CREATE TEMP TABLE source_files (path text PRIMARY KEY, data jsonb, text text, updated_at timestamptz NOT NULL DEFAULT now(),
                  CHECK ((data IS NULL) <> (text IS NULL)))""")
    import json

    def json_file(path: str, data) -> None:
        db.execute("INSERT INTO source_files (path, data) VALUES (%s, %s::jsonb)", (path, json.dumps(data)))

    def text_file(path: str, text: str) -> None:
        db.execute("INSERT INTO source_files (path, text) VALUES (%s, %s)", (path, text))

    json_file("catalog/sites.json", {"sites": {"hotel": site_record(HOTEL), "apply": site_record(APPLY)}, "blocked": ["moodle.example"]})
    page = {"title": "T", "sha256": "s", "fetched_at": "2026-11-01T10:00:00+00:00", "last_modified": ""}
    json_file("sites/hotel/index.json", {
        "pages": {"home": {**page, "url": HOTEL, "title": "Hotel"}, "rooms": {**page, "url": f"{HOTEL}rooms/"}, "old": {**page, "url": f"{HOTEL}old/", "gone": True},
                  "flaky": {**page, "url": f"{HOTEL}flaky/", "missing": {"why": "404", "run": "2026-11-20T00:00:00+00:00"}}},
        "docs": {RULES: "Правила проживания в общежитии", PRICES: "Цены", PACK: "Пакет документов"},
        "contexts": {RULES: "Общежитие — правила"},
        "unlisted": {OLD: {"since": "2026-11-04", "anchor": "Старое положение о проживании", "context": "ctx"}},
        "tried": {f"{HOTEL}job": {"run": "2026-11-25T09:58:30+00:00", "why": "404"}}})
    text_file("sites/hotel/home.md", f"## Hotel\n\n[Rooms]({HOTEL}rooms/) [Правила проживания в общежитии]({RULES}) [Цены]({PRICES}) [Пакет документов]({PACK})\n")
    text_file("sites/hotel/rooms.md", "Rooms of the dormitory.\n")
    text_file("sites/hotel/old.md", "A page that is gone.\n")
    text_file("sites/hotel/flaky.md", "A page the site did not answer once.\n")
    json_file("sites/apply/index.json", {"pages": {"home": {**page, "url": APPLY, "audience": ["applicant"]}}, "docs": {RULES: "Rules"}})
    text_file("sites/apply/home.md", f"[Rules]({RULES})\n")
    keys = {name: sites.doc_key(name, RULES) for name in ("hotel", "apply")}
    note = {"title": "Rules", "url": RULES, "sha256": "c" * 64, "method": "text layer", "chars": 5, "tables": 5, "section": "site/apply", "context": "",
            "fetched_at": "2026-10-01T00:00:00+00:00", "remote": {"etag": "e"}}
    # (a file both sites link is one document: the copy already read keeps its key)
    json_file(f"sites/apply/docs/{keys['apply']}.json", note)
    text_file(f"sites/apply/docs/{keys['apply']}.txt", "rules of living")
    json_file(f"sites/hotel/docs/{keys['hotel']}.json", {"title": "Rules", "url": RULES, "failed": "boom", "tried_at": "2026-11-20T00:00:00+00:00"})
    old_key = sites.doc_key("hotel", OLD)
    json_file(f"sites/hotel/docs/{old_key}.json", {**note, "url": OLD, "sha256": "d" * 64})
    text_file(f"sites/hotel/docs/{old_key}.txt", "an old rule")
    pack = sites.doc_key("hotel", PACK)
    member = f"{pack}-member-0123456789abcdef0123"
    json_file(f"sites/hotel/docs/{pack}.archive.json", {
        "url": PACK, "sha256": SHA, "remote": {"etag": "p"}, "status": "ready", "source": f"{pack}.archives/{SHA}.archive",
        "members": [{"key": member, "member": "doc/a.pdf", "ext": "pdf", "sha256": MEMBER_SHA, "status": "ready", "storage": f"{pack}.members/x/{MEMBER_SHA}"}]})
    json_file(f"sites/hotel/docs/{pack}.members/x/{MEMBER_SHA}/{member}.json", {**note, "title": "A", "url": PACK, "sha256": MEMBER_SHA})
    text_file(f"sites/hotel/docs/{pack}.members/x/{MEMBER_SHA}/{member}.txt", "a member text")
    json_file("regulations/attestation-regulation.json", {**note, "title": "Attestation", "url": regulations.BASE + regulations.DOCS["attestation-regulation"][1]})
    text_file("regulations/attestation-regulation.txt", "attestation text")
    json_file("rpd/index.json", {
        "rpd-aaaa-math": {"archive": f"{HOTEL}rpd.7z", "archive_title": "t", "member": "m.pdf", "programme": "p", "level": "бакалавриат", "year": 2025, "semester": 3,
                          "kind": "Рабочая программа", "code": "Б1", "name": "Math", "fetched_at": "2026-01-01T00:00:00+00:00", "sha256": "ab", "method": "m", "chars": 4},
        "archive-zzzz": {"archive": f"{HOTEL}dead.7z", "archive_title": "t", "skipped": "404 on the site"}})
    text_file("rpd/rpd-aaaa-math.txt", "text of the course")
    json_file("rpd/archives.json", {f"{HOTEL}rpd.7z": {"etag": "x"}, f"{HOTEL}bad.7z": {"failed": "boom", "tried_at": "2026-01-01T00:00:00+00:00"}})
    json_file("eduwiki/manifest.json", {"1": {"title": "Main", "revid": 5, "redirect": False, "ns": 0}, "2": {"title": "Lost", "revid": 6, "redirect": False, "ns": 0, "deleted": True}})
    json_file("eduwiki/pages/1.json", {"pageid": 1, "title": "Main", "ns": 0, "revid": 5, "timestamp": "2026-01-01T00:00:00Z", "wikitext": "= Main =\ntext", "fetched_at": "2026-02-01T00:00:00+00:00"})
    text_file("past-papers/x.md", "a past paper nobody reads")
    db.execute("INSERT INTO docs_meta (key, value) VALUES ('runner', %s)", (json.dumps({"asked": {"files": "2026-01-01T00:00:00+00:00", "eduwiki": "2026-01-01T00:00:00+00:00"}}),))


def test_the_old_store_becomes_the_tables_and_is_dropped(docs_db):
    source_files(docs_db)
    counts = legacy.import_all()
    assert docs_db.execute("SELECT to_regclass('source_files') AS t").fetchone()["t"] is None
    assert counts["sites in the catalog"] == 2 and counts["eduwiki pages"] == 2 and counts["course programmes"] == 2
    pages = {(r["site"], r["state"]): r["n"] for r in docs_db.execute("SELECT site, state, count(*) AS n FROM crawl_urls WHERE kind = 'page' GROUP BY 1, 2").fetchall()}
    assert pages == {("hotel", "ok"): 2, ("hotel", "gone"): 1, ("hotel", "missing"): 1, ("hotel", "tried"): 1, ("apply", "ok"): 1}
    home = row(docs_db, sites.address(HOTEL))
    assert (home.slug, home.title, home.pinned, home.every) == ("home", "Hotel", True, frontier.FEED_EVERY) and "Rooms" in home.text
    assert row(docs_db, sites.address(f"{HOTEL}old/")).text is None  # (a page that is gone keeps no text)
    assert row(docs_db, sites.address(APPLY)).audience == ["applicant"]
    tried = row(docs_db, sites.address(f"{HOTEL}job"))
    assert (tried.state, tried.why) == ("tried", "404") and tried.next_at == datetime(2026, 11, 25, 9, 58, 30, tzinfo=timezone.utc) + sites.RETRY
    docs = {r["doc_key"]: r for r in docs_db.execute("SELECT * FROM crawl_urls WHERE kind = 'document' AND site <> 'university'").fetchall()}
    keys = {name: sites.doc_key(name, RULES) for name in ("hotel", "apply")}
    assert keys["hotel"] not in docs and docs[keys["apply"]]["site"] == "hotel" and docs[keys["apply"]]["state"] == "ok"  # (the copy already read keeps its key)
    assert docs[sites.doc_key("hotel", PRICES)]["state"] == "new" and docs[sites.doc_key("hotel", PACK)]["state"] == "ok" and docs[sites.doc_key("hotel", PACK)]["ext"] == "zip"
    assert str(docs[sites.doc_key("hotel", OLD)]["unlinked_since"]) == "2026-11-04" and docs[sites.doc_key("hotel", OLD)]["title"] == "Старое положение о проживании"
    links = {(r["src"], r["dst"]): (r["anchor"], r["context"]) for r in docs_db.execute("SELECT * FROM crawl_links").fetchall()}
    assert links[(sites.address(HOTEL), sites.address(RULES))] == ("Правила проживания в общежитии", "Общежитие — правила")
    assert (sites.address(APPLY), sites.address(RULES)) in links
    assert notes.text(keys["apply"]) == "rules of living" and notes.note(keys["apply"])["remote"] == {"etag": "e"}
    pack = sites.doc_key("hotel", PACK)
    member = f"{pack}-member-0123456789abcdef0123"
    assert notes.text(member, MEMBER_SHA) == "a member text" and notes.text(member, "") is None  # (the revision of a member is its sha)
    assert archive_load(pack)["status"] == "ready" and "source" not in archive_load(pack)
    assert notes.text("attestation-regulation") == "attestation text"
    assert rpd_text("rpd-aaaa-math") == "text of the course" and docs_db.execute("SELECT count(*) AS n FROM course_programmes").fetchone()["n"] == 2
    assert [(r["url"], r["failed"] is not None) for r in docs_db.execute("SELECT * FROM rpd_archives ORDER BY url").fetchall()] == [(f"{HOTEL}bad.7z", True), (f"{HOTEL}rpd.7z", False)]
    assert docs_db.execute("SELECT count(*) AS n FROM eduwiki_pages WHERE wikitext IS NULL").fetchone()["n"] == 1
    assert docs_db.execute("SELECT count(*) AS n FROM document_files WHERE text LIKE '%past paper%'").fetchone()["n"] == 0
    assert docs_db.execute("SELECT count(*) AS n FROM crawl_urls WHERE url LIKE '%past-papers%'").fetchone()["n"] == 0
    assert "files" not in docs_db.execute("SELECT value FROM docs_meta WHERE key = 'runner'").fetchone()["value"] and "eduwiki" in docs_db.execute("SELECT value FROM docs_meta").fetchone()["value"]


def archive_load(key: str) -> dict:
    from catix.docs.sources import archive_documents

    return archive_documents.load(key)


def rpd_text(key: str) -> str | None:
    from catix.docs.sources import rpd

    return rpd.text_of(key)


def test_the_documents_after_the_import_are_what_they_were(docs_db):
    source_files(docs_db)
    legacy.import_all()
    pack = sites.doc_key("hotel", PACK)
    member = f"{pack}-member-0123456789abcdef0123"
    got = {key: (d["title"], d.get("context", ""), d.get("revision", ""), d.get("unlisted"), d.get("member"))
           for key, d in regulations.all_docs().items() if key not in regulations.DOCS}
    assert got == {
        sites.doc_key("apply", RULES): ("Правила проживания в общежитии", "Общежитие — правила", "", None, None),
        sites.doc_key("hotel", PRICES): ("prices", "", "", None, None),
        sites.doc_key("hotel", OLD): ("Старое положение о проживании", "", "", "2026-11-04", None),
        pack: ("Пакет документов", "", "", None, None),
        member: ("Пакет документов — doc/a.pdf", "", MEMBER_SHA, None, "doc/a.pdf")}
    assert crawl.provider(RULES) == "hotel"


# -- the filters of the search by what is known of a document (db/docs.py Filters, docs/store.py site_of, status_of)

from datetime import date  # noqa: E402

from catix.db import docs as doc_search  # noqa: E402
from catix.docs import store  # noqa: E402


def test_the_site_and_status_of_a_document_follow_from_its_meta():
    assert store.site_of("sites/hotel/rooms", {}) == "hotel"
    assert store.site_of("regulations/x", {"section": "site/apply"}) == "apply"
    assert store.site_of("regulations/attestation", {"section": "document"}) == "university"
    assert store.site_of("course-programmes/x", {"section": "sveden/education"}) == "university"
    assert store.site_of("eduwiki/pages/x", {}) == "eduwiki"
    assert store.status_of({"unlisted": "2026-11-04"}) == "unlisted" and store.status_of({}) == "current"


def passing(db, filters: doc_search.Filters) -> set[str]:
    """The documents a search with these filters keeps: the clause a search appends, run over the documents."""
    where, params = filters.clause("path")
    return {r["path"] for r in db.execute(f"SELECT path FROM documents WHERE true{where}", params).fetchall()}


def test_a_search_keeps_the_documents_that_pass_the_status_the_date_and_the_site(docs_db):
    def doc(path, **meta):
        return store.Document(path, {"title": path, "type": "regulation", **meta}, "# T\n\n## P\n\nSome words of the document.\n")

    year = date.today().year
    store.sync("regulations/", [
        doc("regulations/current", section="site/hotel", sources=[{"last_modified": "2025-03-01"}], stale_after=f"{year + 5}-01-01"),
        doc("regulations/old", section="site/hotel", sources=[{"last_modified": "2019-03-01"}], stale_after="2020-01-01"),
        doc("regulations/unlisted", section="site/apply", sources=[{"last_modified": "2024-01-01"}], unlisted="2026-11-04", stale_after="2026-11-04"),
        doc("regulations/undated", section="document")])
    every = {"regulations/current", "regulations/old", "regulations/unlisted", "regulations/undated"}
    assert passing(docs_db, doc_search.Filters()) == every
    assert passing(docs_db, doc_search.Filters(status="current")) == {"regulations/current", "regulations/undated"}
    assert passing(docs_db, doc_search.Filters(status="outdated")) == {"regulations/old"}
    assert passing(docs_db, doc_search.Filters(status="unlisted")) == {"regulations/unlisted"}
    assert passing(docs_db, doc_search.Filters(issued_from=date(2024, 1, 1))) == {"regulations/current", "regulations/unlisted"}  # (undated: left out)
    assert passing(docs_db, doc_search.Filters(issued_to=date(2024, 12, 31))) == {"regulations/old", "regulations/unlisted"}
    assert passing(docs_db, doc_search.Filters(site="hotel", status="current")) == {"regulations/current"}
    assert passing(docs_db, doc_search.Filters(site="university")) == {"regulations/undated"}
    with pytest.raises(ValueError, match="status"):
        doc_search.Filters(status="fresh")


def test_a_search_leaves_out_the_programmes_of_other_cohorts_of_a_course_that_has_the_askers_cohort(docs_db):
    def doc(path, title, **meta):
        return store.Document(path, {"title": title, "type": "regulation", **meta}, "# T\n\n## P\n\nSome words of the document.\n")

    ma = "Рабочая программа «Mathematical Analysis I / Математический анализ I» ({})"
    store.sync("course-programmes/", [
        doc("course-programmes/ma-2023", ma.format(2023), cohort=2023),
        doc("course-programmes/ma-2026", ma.format(2026), cohort=2026),
        doc("course-programmes/mat-2025", "Рабочая программа «Математический анализ (1 семестр)» (2025)", cohort=2025)])
    store.sync("regulations/", [doc("regulations/rules", "Правила")])
    every = {"course-programmes/ma-2023", "course-programmes/ma-2026", "course-programmes/mat-2025", "regulations/rules"}
    assert passing(docs_db, doc_search.Filters()) == every
    assert passing(docs_db, doc_search.Filters(cohorts=frozenset({2026}))) == every - {"course-programmes/ma-2023"}


def test_the_versions_of_a_document_are_told_apart_in_sql(docs_db):
    def doc(path, title):
        return store.Document(path, {"title": title, "type": "regulation"}, "# T\n\n## P\n\nSome words of the document.\n")

    rules = "Правила приема на обучение по программам бакалавриата на {} учебный год"
    store.sync("regulations/", [doc("regulations/r24", rules.format("2024/2025")), doc("regulations/r26", rules.format("2026/2027")),
                                doc("regulations/plain", "Устав")])
    assert store.mark_series(docs_db) == 2
    assert store.mark_series(docs_db) == 0
    every = {"regulations/r24", "regulations/r26", "regulations/plain"}
    assert passing(docs_db, doc_search.Filters(latest_versions=True)) == {"regulations/r26", "regulations/plain"}
    assert passing(docs_db, doc_search.Filters(latest_versions=True, asked_years=frozenset({2024}))) == every
    assert passing(docs_db, doc_search.Filters()) == every
    assert doc_search.page("regulations/r24")[0].newer == rules.format("2026/2027")
