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


def standalone_pdf(text="TEXT admission rules"):
    """A small, valid PDF; PDF dispatch validates structure, not only magic."""
    stream = f"BT /F1 12 Tf 50 750 Td ({text}) Tj ET".encode()
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>",
               b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
               b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"]
    data, offsets = b"%PDF-1.4\n", [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    start = len(data)
    data += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    data += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    return data + f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode()


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
    class MockClient(Client):
        def __init__(self, **kwargs):
            super().__init__(transport=httpx.MockTransport(response), **kwargs)

    monkeypatch.setattr(regulations.httpx, "Client", MockClient)
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


def test_archive_named_pdf_is_one_document_with_real_citation(bundle):
    from catix.wiki.sources import archive_documents

    bundle["body"] = standalone_pdf()
    key = bundle["parent"]
    original = regulations.all_docs()[key]
    # Retry an existing unsupported manifest, as produced by the old dispatcher.
    archive_documents.save(key, original, {"status": "unsupported", "refetch": True, "url": bundle["url"]})
    assert regulations.read_new(ocr=False) == [key]
    docs = regulations.all_docs()
    assert set(docs) == {key}
    assert docs[key]["ext"] == "pdf" and not docs[key].get("member")
    assert docs[key]["url"] == bundle["url"]
    assert (docs[key]["root"] / f"{key}.pdf").read_bytes() == bundle["body"]
    regulations.compile_all()
    page = (paths.DOCS / "regulations" / f"{key}.md").read_text()
    assert bundle["url"] in page and "archive_member:" not in page
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in original["root"].rglob("*") if p.is_file()}
    assert regulations.read_new(ocr=False) == []
    regulations.compile_all()
    assert before == {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in original["root"].rglob("*") if p.is_file()}
    assert bundle["requests"] == [("GET", bundle["url"])] and len(bundle["layers"]) == 1


def test_archive_named_scan_queues_once_and_refreshes_at_boundary(bundle, monkeypatch):
    bundle["body"] = standalone_pdf("SCAN")
    key = bundle["parent"]
    assert regulations.read_new(ocr=False) == []
    doc = regulations.all_docs()[key]
    assert regulations.queued() == {key: 1}
    assert (doc["root"] / f"{key}.pdf").read_bytes() == bundle["body"]
    assert regulations.read_new(ocr=False) == []
    assert bundle["requests"] == [("GET", bundle["url"])] and len(bundle["layers"]) == 1
    bundle.update(body=standalone_pdf("TEXT revised"), etag="v2")
    assert regulations.refresh() == 1
    assert bundle["requests"][-1] == ("HEAD", bundle["url"])
    assert (doc["root"] / f"{key}.pdf").exists()  # old scan is retained until replacement succeeds
    assert regulations.read_new(ocr=False) == [key]
    assert regulations.queued() == {}
    assert regulations.all_docs()[key]["root"] != doc["root"]
    assert len(bundle["layers"]) == 2


def test_standalone_pdf_can_be_replaced_by_a_real_archive(bundle):
    bundle["body"] = standalone_pdf()
    key = bundle["parent"]
    assert regulations.read_new(ocr=False) == [key]
    regulations.compile_all()
    page = paths.DOCS / "regulations" / f"{key}.md"
    assert page.exists()
    bundle.update(body=zipped({"scan.pdf": b"%PDF SCAN"}), etag="v2")
    assert regulations.refresh() == 1
    assert regulations.read_new(ocr=False) == [key]  # removal alone must trigger rebuilding
    assert page.exists()  # fetch updates raw data; publishing/removing wiki pages belongs to compile
    regulations.compile_all()
    assert not page.exists()
    assert len(regulations.queued()) == 1


@pytest.mark.parametrize("previous", ["archive", "pdf"])
@pytest.mark.parametrize("replacement,status", [
    (b"<html><body>%PDF-1.4 not a document</body></html>", "unsupported"),
    (b"%PDF-1.4\ntruncated", "invalid"),
    (b"PK\x03\x04truncated", "invalid"),
    (zipped({"[Content_Types].xml": b"types", "word/document.xml": b"word"}), "unsupported"),
])
def test_failed_type_dispatch_retains_previous_revision(bundle, previous, replacement, status):
    from catix.wiki.sources import archive_documents

    if previous == "pdf":
        bundle["body"] = standalone_pdf()
    regulations.read_new(ocr=False)
    regulations.compile_all()
    docs = regulations.all_docs()
    pages = {p: p.read_bytes() for p in (paths.DOCS / "regulations").glob("*.md")}
    bundle.update(body=replacement, etag="v2")
    assert regulations.refresh() == 1
    assert regulations.read_new(ocr=False) == []
    assert regulations.all_docs() == docs
    regulations.compile_all()
    assert pages == {p: p.read_bytes() for p in (paths.DOCS / "regulations").glob("*.md")}
    manifest = archive_documents.load(bundle["parent"], docs[bundle["parent"]])
    assert manifest["status"] == status and manifest["refetch"]


def test_archive_becomes_a_standalone_pdf_and_removes_old_members(bundle):
    previous = regulations.read_new(ocr=False)
    regulations.compile_all()
    bundle.update(body=standalone_pdf(), etag="v2")
    assert regulations.refresh() == 1
    assert set(previous + [bundle["parent"]]) <= set(regulations.read_new(ocr=False))
    regulations.compile_all()
    assert set(regulations.all_docs()) == {bundle["parent"]}
    assert not list((paths.DOCS / "regulations").glob("*-member-*.md"))


def test_standalone_same_bytes_refresh_and_missing_file_do_not_reparse(bundle):
    bundle["body"] = standalone_pdf()
    key = bundle["parent"]
    assert regulations.read_new(ocr=False) == [key]
    doc = regulations.all_docs()[key]
    bundle["etag"] = "v2"
    assert regulations.refresh() == 1
    assert regulations.read_new(ocr=False) == []
    assert regulations.all_docs()[key] == doc
    (doc["root"] / f"{key}.pdf").unlink()
    assert regulations.read_new(ocr=False) == []
    assert (doc["root"] / f"{key}.pdf").read_bytes() == bundle["body"]
    assert bundle["requests"] == [("GET", bundle["url"]), ("HEAD", bundle["url"]), ("GET", bundle["url"])]
    assert len(bundle["layers"]) == 1


def test_standalone_scan_is_consumed_by_existing_ocr_queue(bundle, monkeypatch):
    bundle["body"] = standalone_pdf("SCAN")
    assert regulations.read_new(ocr=False) == []
    monkeypatch.setattr(chandra, "text_of_pdf", lambda *a, **kw: "1. Приказ ректора " * 70)
    assert regulations.read_new() == [bundle["parent"]]
    assert regulations.queued() == {}
    assert bundle["requests"] == [("GET", bundle["url"])] and len(bundle["layers"]) == 1


def test_missing_standalone_scan_cannot_bypass_a_rejected_refresh(bundle, monkeypatch):
    from catix.wiki.sources import archive_documents

    bundle["body"] = standalone_pdf("SCAN")
    key = bundle["parent"]
    assert regulations.read_new(ocr=False) == []
    doc = regulations.all_docs()[key]
    pdf = doc["root"] / f"{key}.pdf"
    bundle["etag"] = "v2"
    assert regulations.refresh() == 1
    pdf.unlink()
    requests = []

    def redirect(request):
        requests.append(str(request.url))
        return httpx.Response(302, headers={"location": "https://untrusted.example/replacement.pdf"})

    def forbidden(*args, **kwargs):
        pytest.fail("ordinary GET bypassed the archive boundary after its rejected refresh")

    with Client(transport=httpx.MockTransport(redirect)) as client:
        monkeypatch.setattr(archive_documents.httpx, "stream", client.stream)
        monkeypatch.setattr(regulations.httpx, "get", forbidden)
        assert regulations.read_new(ocr=False) == []
    assert requests == [bundle["url"]]
    assert not pdf.exists()
    assert regulations.all_docs()[key] == doc
    assert archive_documents.load(key, doc)["status"] == "unsafe"


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
