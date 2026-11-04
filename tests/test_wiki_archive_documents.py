"""Archives use the document reader and OCR queue, with one stable identity per member."""

import contextlib
import io
import json
import zipfile

import httpx
import pytest
from httpx import Client

from catix.wiki import paths
from catix.wiki.sources import chandra, opendataloader, regulations, sites


def zipped(files):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return out.getvalue()


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    monkeypatch.setattr(sites, "ROOT", tmp_path / "raw" / "sites")
    monkeypatch.setattr(sites, "DOCS", tmp_path / "wiki" / "raw")
    monkeypatch.setattr(paths, "DOCS", tmp_path / "wiki" / "raw")
    monkeypatch.setattr(sites, "DISCOVERED", tmp_path / "raw" / "sites-discovered.json")
    monkeypatch.setattr(sites, "SITES", {"unit": sites.Site("https://unit.example/", "ru", "Unit", r"^nothing$", sitemap=False, pause=0)})
    monkeypatch.setattr(regulations, "DOCS", {})
    monkeypatch.setattr(regulations, "ROOT", tmp_path / "raw" / "regulations")
    monkeypatch.setattr(regulations, "SVEDEN_ROOT", tmp_path / "raw" / "sveden")
    monkeypatch.setattr(regulations, "LINKED", tmp_path / "raw" / "linked.json")
    monkeypatch.setattr(regulations, "PAUSE", 0)
    url = "https://unit.example/docs/rules.zip"
    sites.save("unit", {"pages": {}, "docs": {url: "Rules and orders"}})
    state = {"body": zipped({"rules/admission.pdf": b"%PDF TEXT admission", "orders/scan.pdf": b"%PDF SCAN"}), "etag": "v1", "requests": [], "layers": []}

    def response(request):
        state["requests"].append((request.method, str(request.url)))
        assert str(request.url) == url
        return httpx.Response(200, content=state["body"] if request.method == "GET" else b"", headers={"etag": state["etag"], "content-type": "application/zip"})

    client = httpx.Client(transport=httpx.MockTransport(response))
    monkeypatch.setattr(regulations.httpx, "get", client.get)
    monkeypatch.setattr(regulations.httpx, "stream", client.stream)
    monkeypatch.setattr(regulations.httpx, "Client", lambda **kw: contextlib.nullcontext(client))
    monkeypatch.setattr(regulations, "pages_of", lambda pdf: 1)

    def to_pdf(src):
        assert src.suffix == ".pdf", "archive was sent to the document converter"
        return src

    def layer(pdf, converted=None):
        state["layers"].append(pdf)
        return ("1. Общие положения " * 70, "text layer") if b"TEXT" in pdf.read_bytes() else None

    monkeypatch.setattr(regulations, "to_pdf", to_pdf)
    monkeypatch.setattr(regulations, "layer_text", layer)
    monkeypatch.setattr(opendataloader, "converted", lambda pdfs: contextlib.nullcontext({}))
    monkeypatch.setattr(chandra, "text_of_pdf", lambda *a, **kw: pytest.fail("scheduled archive processing started OCR"))
    state["url"] = url
    state["parent"] = next(iter(sites.docs()))
    yield state
    client.close()


def test_archive_members_use_document_text_and_persistent_ocr_queue(bundle, monkeypatch):
    read = regulations.read_new(ocr=False)
    members = {k: d for k, d in regulations.all_docs().items() if d.get("member")}
    assert len(members) == 2 and len(read) == 1
    by_name = {d["member"]: (k, d) for k, d in members.items()}
    key, scan = by_name["orders/scan.pdf"]
    assert json.loads((scan["root"] / f"{key}.json").read_text())["ocr"] == "queued"
    assert (scan["root"] / f"{key}.pdf").exists()
    regulations.compile_all()
    page = (paths.DOCS / "regulations" / f"{read[0]}.md").read_text()
    assert bundle["url"] in page and "rules/admission.pdf" in page
    assert regulations.read_new(ocr=False) == []
    assert bundle["requests"] == [("GET", bundle["url"])] and len(bundle["layers"]) == 2
    monkeypatch.setattr(chandra, "text_of_pdf", lambda *a, **kw: "1. Приказ ректора " * 70)
    assert regulations.read_new() == [key]
    assert bundle["requests"] == [("GET", bundle["url"])]


def test_archive_refresh_preserves_previous_members_until_replacement_is_valid(bundle):
    regulations.read_new(ocr=False)
    regulations.compile_all()
    before = {d["member"]: (key, d) for key, d in regulations.all_docs().items() if d.get("member")}
    key, doc = before["rules/admission.pdf"]
    page = paths.DOCS / "regulations" / f"{key}.md"
    original = page.read_bytes()
    bundle.update(body=b"not an archive", etag="v2")
    assert regulations.refresh() == 1
    assert bundle["requests"][-1] == ("HEAD", bundle["url"])
    assert regulations.read_new(ocr=False) == []
    regulations.compile_all()
    assert page.read_bytes() == original
    assert set(before) == {d["member"] for d in regulations.all_docs().values() if d.get("member")}
    bundle["body"] = zipped({"orders/scan.pdf": b"%PDF SCAN", "new.pdf": b"%PDF TEXT new"})
    changed = regulations.read_new(ocr=False)
    assert key in changed  # deletion-only changes also have to trigger a rebuild
    regulations.compile_all()
    assert not page.exists()
    after = {d["member"]: (k, d) for k, d in regulations.all_docs().items() if d.get("member")}
    assert set(after) == {"orders/scan.pdf", "new.pdf"}
    assert after["orders/scan.pdf"] == before["orders/scan.pdf"]  # unchanged scan keeps its queue and local file
    assert len(bundle["layers"]) == 3  # only the new PDF was extracted


def test_changed_member_keeps_identity_but_is_read_again(bundle):
    regulations.read_new(ocr=False)
    before = {d["member"]: (key, d) for key, d in regulations.all_docs().items() if d.get("member")}
    bundle.update(body=zipped({"rules/admission.pdf": b"%PDF TEXT revised", "orders/scan.pdf": b"%PDF SCAN"}), etag="v2")
    assert regulations.refresh() == 1
    assert regulations.read_new(ocr=False) == [before["rules/admission.pdf"][0]]
    after = {d["member"]: (key, d) for key, d in regulations.all_docs().items() if d.get("member")}
    assert before["rules/admission.pdf"][1]["root"] != after["rules/admission.pdf"][1]["root"]
    assert before["orders/scan.pdf"] == after["orders/scan.pdf"]
    assert regulations.read_new(ocr=False) == []


def test_archive_with_only_unsupported_files_removes_old_documents(bundle):
    read = regulations.read_new(ocr=False)
    regulations.compile_all()
    bundle.update(body=zipped({"readme.txt": b"documents withdrawn"}), etag="v2")
    assert regulations.refresh() == 1
    changed = regulations.read_new(ocr=False)
    assert set(read) <= set(changed)
    regulations.compile_all()
    assert not any(d.get("member") for d in regulations.all_docs().values())
    assert not list((paths.DOCS / "regulations").glob("*-member-*.md"))


def test_nested_archives_are_visible_but_not_recursively_opened(bundle):
    from catix.wiki.sources import archive_documents

    bundle["body"] = zipped({"nested.zip": zipped({"deep.pdf": b"%PDF TEXT"}), "plain.pdf": b"%PDF TEXT"})
    assert len(regulations.read_new(ocr=False)) == 1
    doc = regulations.all_docs()[bundle["parent"]]
    listing = archive_documents.load(bundle["parent"], doc)
    assert next(m for m in listing["members"] if m["member"] == "nested.zip")["status"] == "unsupported"
    assert {d["member"] for d in regulations.all_docs().values() if d.get("member")} == {"plain.pdf"}


def test_cached_archive_restores_a_missing_member_without_network(bundle):
    from catix.wiki.sources import archive_documents

    regulations.read_new(ocr=False)
    docs = regulations.all_docs()
    meta = archive_documents.load(bundle["parent"], docs[bundle["parent"]])
    assert (docs[bundle["parent"]]["root"] / meta["source"]).read_bytes() == bundle["body"]
    key, doc = next((k, d) for k, d in docs.items() if d.get("member") == "orders/scan.pdf")
    (doc["root"] / f"{key}.pdf").unlink()
    assert regulations.read_new(ocr=False) == []
    assert (doc["root"] / f"{key}.pdf").exists()
    assert bundle["requests"] == [("GET", bundle["url"])]


@pytest.mark.parametrize("only_new", [False, True])
def test_site_discovers_archive_download_without_filename(bundle, only_new):
    url = "https://unit.example/download?id=rules"
    html = "<html><title>Unit</title><p>" + "Student rules and documents. " * 30 + f'</p><a href="{url}">Rules</a></html>'
    requests = []

    def answer(request):
        requests.append(str(request.url))
        if str(request.url) == "https://unit.example/":
            return httpx.Response(200, text=html, headers={"content-type": "text/html"})
        assert str(request.url) == url
        return httpx.Response(200, content=bundle["body"], headers={"content-type": "application/zip"})

    with Client(transport=httpx.MockTransport(answer)) as client:
        if only_new:
            sites.fetch_new(["unit"], client=client)
        else:
            sites.fetch_site("unit", sites.SITES["unit"], client)
    assert url in sites.load("unit")["docs"]
    assert next(d for d in sites.docs().values() if d["url"] == url)["ext"] == "zip"
    assert url in requests


def test_course_archives_keep_their_specialized_reader(bundle, monkeypatch):
    from catix.wiki.sources import rpd

    monkeypatch.setattr(rpd, "archives", lambda: [{"url": bundle["url"]}])
    assert bundle["url"] not in {d["url"] for d in regulations.all_docs().values()}


def test_oversized_download_is_reported_without_publishing_members(bundle, monkeypatch):
    from catix.wiki.sources import archive_documents, archives

    monkeypatch.setattr(archives, "MAX_ARCHIVE_BYTES", 1)
    assert regulations.read_new(ocr=False) == []
    docs = regulations.all_docs()
    assert not any(d.get("member") for d in docs.values())
    assert archive_documents.load(bundle["parent"], docs[bundle["parent"]])["status"] == "limit"


def test_archive_redirect_cannot_leave_trusted_providers(bundle, monkeypatch, tmp_path):
    from catix.wiki.sources import archive_documents, archives

    requests = []
    def answer(request):
        requests.append(str(request.url))
        return httpx.Response(302, headers={"location": "https://untrusted.example/private.zip"})

    with Client(transport=httpx.MockTransport(answer)) as client:
        monkeypatch.setattr(archive_documents.httpx, "stream", client.stream)
        with pytest.raises(archives.ArchiveError) as error:
            archive_documents.download(bundle["url"], tmp_path / "download")
    assert error.value.status == "unsafe" and requests == [bundle["url"]]


def test_cp866_member_names_are_read_as_cyrillic(tmp_path):
    from catix.wiki.sources import archives

    name = "Программа.pdf"
    encoded = name.encode("cp866")
    placeholder = "x" * len(encoded)
    source = tmp_path / "old.zip"
    source.write_bytes(zipped({placeholder: b"%PDF course"}).replace(placeholder.encode(), encoded))
    listing = archives.unpack(source, tmp_path / "members")
    assert listing[0]["member"] == name
