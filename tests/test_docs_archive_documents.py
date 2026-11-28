"""Archives use the document reader and OCR queue, with one stable identity per member."""

import contextlib
import io
import re
import tempfile
import zipfile

import httpx
import pytest
from httpx import Client

from catix.docs import frontier, notes
from catix.docs.sources import archive_documents, lighton, tesseract, opendataloader, regulations, sites
from tests.helpers import link_document


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


def pages():
    """The documents the sources make now, by path."""
    return {d.path: d for d in regulations.compile_all()}


def stored(db):
    """Everything the documents' notes, texts and archive manifests hold, to see that a run changed none of it."""
    return [db.execute(f"SELECT * FROM {table} ORDER BY 1, 2").fetchall() for table in ("document_files", "archives")]


def refresh(key):
    """The container asks its site whether it changed (HEAD) and is marked for a new download if so: the first step of recheck."""
    with httpx.Client() as client:
        return archive_documents.refresh(key, regulations.all_docs()[key], client)


def no_originals(bundle):
    """The originals live only in the temporary folder of a run: nothing is left there."""
    return not list(bundle["tmp"].iterdir())


@pytest.fixture
def bundle(tmp_path, monkeypatch, docs_db):
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(tmp))
    monkeypatch.setattr(sites, "SITES", {"unit": sites.Site("https://unit.example/", "ru", "Unit", r"^nothing$", sitemap=False, pause=0)})
    monkeypatch.setattr(regulations, "DOCS", {})
    monkeypatch.setattr(regulations, "PAUSE", 0)
    url = "https://unit.example/docs/rules.zip"
    parent = link_document("unit", url, "Rules and orders")
    state = {"body": zipped({"rules/admission.pdf": b"%PDF TEXT admission", "orders/scan.pdf": b"%PDF SCAN"}), "etag": "v1", "requests": [], "layers": [],
             "tmp": tmp, "db": docs_db}

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
    monkeypatch.setattr(tesseract, "text_of_pdf", lambda *a, **kw: pytest.fail("scheduled archive processing started OCR"))
    state["url"] = url
    state["parent"] = parent
    yield state
    client.close()


def test_archive_named_pdf_is_one_document_with_real_citation(bundle):
    bundle["body"] = standalone_pdf()
    key = bundle["parent"]
    original = regulations.all_docs()[key]
    assert original["ext"] == "zip"  # (the row of the frontier says an archive: the site named it so)
    # Retry an existing unsupported manifest, as produced by the old dispatcher.
    archive_documents.save(key, {"status": "unsupported", "refetch": True, "url": bundle["url"]})
    assert regulations.read_new(ocr=False) == [key]
    docs = regulations.all_docs()
    assert set(docs) == {key}
    assert docs[key]["ext"] == "pdf" and not docs[key].get("member") and docs[key]["archived"]
    assert re.fullmatch(r"[0-9a-f]{64}", docs[key]["revision"])  # (the revision of a PDF an archive URL served: its content's sha)
    assert docs[key]["url"] == bundle["url"]
    assert notes.text(key, docs[key]["revision"]) and no_originals(bundle)
    page = pages()[f"regulations/{key}"]
    assert bundle["url"] in page.body and "archive_member" not in page.meta
    before = stored(bundle["db"])
    assert regulations.read_new(ocr=False) == []
    assert pages()[f"regulations/{key}"] == page
    assert before == stored(bundle["db"])
    assert bundle["requests"] == [("GET", bundle["url"])] and len(bundle["layers"]) == 1


def test_archive_named_scan_queues_once_and_refreshes_at_boundary(bundle, monkeypatch):
    bundle["body"] = standalone_pdf("SCAN")
    key = bundle["parent"]
    assert regulations.read_new(ocr=False) == []
    doc = regulations.all_docs()[key]
    assert regulations.queued() == {key: 1}
    assert no_originals(bundle)  # (the scan waits as a note: a run with OCR downloads it again)
    assert regulations.read_new(ocr=False) == []
    assert bundle["requests"] == [("GET", bundle["url"])] and len(bundle["layers"]) == 1
    bundle.update(body=standalone_pdf("TEXT revised"), etag="v2")
    assert refresh(key)
    assert bundle["requests"][-1] == ("HEAD", bundle["url"])
    assert regulations.queued() == {key: 1}  # (the old scan stays queued until the replacement succeeds)
    assert regulations.read_new(ocr=False) == [key]
    assert regulations.queued() == {}
    assert regulations.all_docs()[key]["revision"] != doc["revision"]
    assert len(bundle["layers"]) == 2 and no_originals(bundle)


def test_a_recheck_asks_the_archive_first_and_reads_what_changed(bundle):
    bundle["body"] = standalone_pdf("SCAN")
    key = bundle["parent"]
    assert regulations.read_new(ocr=False) == []
    doc = regulations.all_docs()[key]
    assert regulations.recheck([key]) == []  # (the same ETag: a HEAD, no download)
    assert bundle["requests"] == [("GET", bundle["url"]), ("HEAD", bundle["url"])] and regulations.queued() == {key: 1}
    bundle.update(body=standalone_pdf("TEXT revised"), etag="v2")
    assert regulations.recheck([key]) == [key]
    assert bundle["requests"][-2:] == [("HEAD", bundle["url"]), ("GET", bundle["url"])]
    assert regulations.queued() == {} and regulations.all_docs()[key]["revision"] != doc["revision"] and no_originals(bundle)


def test_standalone_pdf_can_be_replaced_by_a_real_archive(bundle):
    bundle["body"] = standalone_pdf()
    key = bundle["parent"]
    assert regulations.read_new(ocr=False) == [key]
    assert f"regulations/{key}" in pages()
    bundle.update(body=zipped({"scan.pdf": b"%PDF SCAN"}), etag="v2")
    assert regulations.recheck([key]) == [key]  # removal alone must trigger rebuilding
    assert f"regulations/{key}" not in pages()  # the documents are made from the data: the container has none
    assert len(regulations.queued()) == 1


@pytest.mark.parametrize("previous", ["archive", "pdf"])
@pytest.mark.parametrize("replacement,status", [
    (b"<html><body>%PDF-1.4 not a document</body></html>", "unsupported"),
    (b"%PDF-1.4\ntruncated", "invalid"),
    (b"PK\x03\x04truncated", "invalid"),
    (zipped({"[Content_Types].xml": b"types", "word/document.xml": b"word"}), "unsupported"),
])
def test_failed_type_dispatch_retains_previous_revision(bundle, previous, replacement, status):
    if previous == "pdf":
        bundle["body"] = standalone_pdf()
    regulations.read_new(ocr=False)
    docs = regulations.all_docs()
    before = pages()
    bundle.update(body=replacement, etag="v2")
    assert regulations.recheck([bundle["parent"]]) == []
    assert regulations.all_docs() == docs
    assert pages() == before
    manifest = archive_documents.load(bundle["parent"])
    assert manifest["status"] == status and manifest["refetch"]


def test_archive_becomes_a_standalone_pdf_and_removes_old_members(bundle):
    previous = regulations.read_new(ocr=False)
    regulations.compile_all()
    bundle.update(body=standalone_pdf(), etag="v2")
    assert set(previous + [bundle["parent"]]) <= set(regulations.recheck([bundle["parent"]]))
    assert set(regulations.all_docs()) == {bundle["parent"]}
    assert not [d for d in regulations.compile_all() if "-member-" in d.path]


def test_standalone_same_bytes_refresh_does_not_reparse_and_a_read_file_is_not_downloaded_again(bundle):
    bundle["body"] = standalone_pdf()
    key = bundle["parent"]
    assert regulations.read_new(ocr=False) == [key]
    doc = regulations.all_docs()[key]
    bundle["etag"] = "v2"
    assert regulations.recheck([key]) == []  # (the archive boundary downloads it once more: the same bytes, the same text)
    assert regulations.all_docs()[key] == doc
    assert regulations.read_new(ocr=False) == [] and regulations.read_new() == []  # (text is stored: no run needs the file)
    assert bundle["requests"] == [("GET", bundle["url"]), ("HEAD", bundle["url"]), ("GET", bundle["url"])]
    assert len(bundle["layers"]) == 1 and no_originals(bundle)


def test_standalone_scan_is_consumed_by_existing_ocr_queue(bundle, monkeypatch):
    bundle["body"] = standalone_pdf("SCAN")
    assert regulations.read_new(ocr=False) == []
    assert bundle["requests"] == [("GET", bundle["url"])] and no_originals(bundle)
    monkeypatch.setattr(lighton, "available", lambda: False)
    monkeypatch.setattr(tesseract, "available", lambda: True)
    monkeypatch.setattr(tesseract, "text_of_pdf", lambda *a, **kw: "1. Приказ ректора " * 70)
    assert regulations.read_new() == [bundle["parent"]]  # (a run with OCR downloads the file again)
    assert regulations.queued() == {}
    assert bundle["requests"] == [("GET", bundle["url"])] * 2 and len(bundle["layers"]) == 1 and no_originals(bundle)


def test_missing_standalone_scan_cannot_bypass_a_rejected_refresh(bundle, monkeypatch):
    bundle["body"] = standalone_pdf("SCAN")
    key = bundle["parent"]
    assert regulations.read_new(ocr=False) == []
    doc = regulations.all_docs()[key]
    bundle["etag"] = "v2"
    assert refresh(key)
    requests = []

    def redirect(request):
        requests.append(str(request.url))
        return httpx.Response(302, headers={"location": "https://untrusted.example/replacement.pdf"})

    def forbidden(*args, **kwargs):
        pytest.fail("ordinary GET bypassed the archive boundary after its rejected refresh")

    with Client(transport=httpx.MockTransport(redirect)) as client:
        monkeypatch.setattr(archive_documents.httpx, "stream", client.stream)
        monkeypatch.setattr(regulations.httpx, "get", forbidden)
        assert regulations.read_new() == []  # (a run with OCR wants the scan's file: only the archive boundary may give it)
    assert requests == [bundle["url"]]
    assert regulations.all_docs()[key] == doc
    assert archive_documents.load(key)["status"] == "unsafe" and no_originals(bundle)


def test_archive_members_use_document_text_and_persistent_ocr_queue(bundle, monkeypatch):
    read = regulations.read_new(ocr=False)
    members = {k: d for k, d in regulations.all_docs().items() if d.get("member")}
    assert len(members) == 2 and len(read) == 1
    by_name = {d["member"]: (k, d) for k, d in members.items()}
    key, scan = by_name["orders/scan.pdf"]
    assert re.fullmatch(r"[0-9a-f]{64}", scan["revision"])  # (a member is a revision of its key: the sha of its content)
    assert notes.note(key, scan["revision"])["ocr"] == "queued" and notes.note(key) == {}
    assert no_originals(bundle)  # (the scan is queued as a note; its file is downloaded again by a run with OCR)
    doc = pages()[f"regulations/{read[0]}"]
    assert bundle["url"] in doc.body and doc.meta["archive_member"] == "rules/admission.pdf" and re.fullmatch(r"[0-9a-f]{64}", doc.meta["archive_sha256"])
    assert regulations.read_new(ocr=False) == []
    assert bundle["requests"] == [("GET", bundle["url"])] and len(bundle["layers"]) == 2
    monkeypatch.setattr(lighton, "available", lambda: False)
    monkeypatch.setattr(tesseract, "available", lambda: True)
    monkeypatch.setattr(tesseract, "text_of_pdf", lambda *a, **kw: "1. Приказ ректора " * 70)
    assert regulations.read_new() == [key]
    assert bundle["requests"] == [("GET", bundle["url"])] * 2  # (the archive is downloaded again for the scan)
    assert notes.text(key, scan["revision"]) and no_originals(bundle)


def test_archive_refresh_preserves_previous_members_until_replacement_is_valid(bundle, monkeypatch):
    regulations.read_new(ocr=False)
    before = {d["member"]: (key, d) for key, d in regulations.all_docs().items() if d.get("member")}
    key, doc = before["rules/admission.pdf"]
    page = pages()[f"regulations/{key}"]
    bundle.update(body=b"not an archive", etag="v2")
    assert regulations.recheck([bundle["parent"]]) == []
    assert bundle["requests"][-2:] == [("HEAD", bundle["url"]), ("GET", bundle["url"])]
    assert pages()[f"regulations/{key}"] == page
    assert set(before) == {d["member"] for d in regulations.all_docs().values() if d.get("member")}
    bundle["body"] = zipped({"orders/scan.pdf": b"%PDF SCAN", "new.pdf": b"%PDF TEXT new"})
    asked = len(bundle["requests"])
    assert regulations.read_new(ocr=False) == [] and len(bundle["requests"]) == asked  # (the failed version waits RETRY, not every run)
    from datetime import timedelta
    monkeypatch.setattr(sites, "RETRY", timedelta(0))  # (RETRY has passed)
    changed = regulations.read_new(ocr=False)
    assert key in changed  # deletion-only changes also have to trigger a rebuild
    assert f"regulations/{key}" not in pages()
    after = {d["member"]: (k, d) for k, d in regulations.all_docs().items() if d.get("member")}
    assert set(after) == {"orders/scan.pdf", "new.pdf"}
    assert after["orders/scan.pdf"] == before["orders/scan.pdf"]  # unchanged scan keeps its identity and its queue note
    assert len(bundle["layers"]) == 3  # only the new PDF was extracted


def test_changed_member_keeps_identity_but_is_read_again(bundle):
    regulations.read_new(ocr=False)
    before = {d["member"]: (key, d) for key, d in regulations.all_docs().items() if d.get("member")}
    bundle.update(body=zipped({"rules/admission.pdf": b"%PDF TEXT revised", "orders/scan.pdf": b"%PDF SCAN"}), etag="v2")
    assert regulations.recheck([bundle["parent"]]) == [before["rules/admission.pdf"][0]]
    after = {d["member"]: (key, d) for key, d in regulations.all_docs().items() if d.get("member")}
    assert before["rules/admission.pdf"][0] == after["rules/admission.pdf"][0]
    assert before["rules/admission.pdf"][1]["revision"] != after["rules/admission.pdf"][1]["revision"]
    assert before["orders/scan.pdf"] == after["orders/scan.pdf"]
    assert regulations.read_new(ocr=False) == []


def test_archive_with_only_unsupported_files_removes_old_documents(bundle):
    read = regulations.read_new(ocr=False)
    regulations.compile_all()
    bundle.update(body=zipped({"readme.txt": b"documents withdrawn"}), etag="v2")
    changed = regulations.recheck([bundle["parent"]])
    assert set(read) <= set(changed)
    assert not any(d.get("member") for d in regulations.all_docs().values())
    assert not [d for d in regulations.compile_all() if "-member-" in d.path]


def test_nested_archives_are_visible_but_not_recursively_opened(bundle):
    bundle["body"] = zipped({"nested.zip": zipped({"deep.pdf": b"%PDF TEXT"}), "plain.pdf": b"%PDF TEXT"})
    assert len(regulations.read_new(ocr=False)) == 1
    listing = archive_documents.load(bundle["parent"])
    assert next(m for m in listing["members"] if m["member"] == "nested.zip")["status"] == "unsupported"
    assert {d["member"] for d in regulations.all_docs().values() if d.get("member")} == {"plain.pdf"}


def test_site_discovers_archive_download_without_filename(bundle):
    url = "https://unit.example/download?id=rules"
    html = "<html><title>Unit</title><p>" + "Student rules and documents. " * 30 + f'</p><a href="{url}">Rules</a></html>'
    requests = []

    def answer(request):
        requests.append((request.method, str(request.url)))
        if str(request.url) == "https://unit.example/":
            return httpx.Response(200, text=html, headers={"content-type": "text/html"})
        assert str(request.url) == url
        return httpx.Response(200, content=bundle["body"], headers={"content-type": "application/zip"})

    bundle["db"].execute("UPDATE crawl_urls SET state = 'new', next_at = now() WHERE kind = 'page'")  # (the start page, left by the helper as read, is due)
    with Client(transport=httpx.MockTransport(answer)) as client:
        while row := frontier.next_due(documents=False):  # (the start page, which links the download; then the download: a HEAD says an archive)
            sites.read_page(client, row)
    assert ("HEAD", url) in requests and ("GET", url) not in requests  # (an archive is not fetched as a page)
    assert next(d for d in sites.docs().values() if d["url"] == url)["ext"] == "zip"


def test_course_archives_keep_their_specialized_reader(bundle, monkeypatch):
    from catix.docs.sources import rpd

    monkeypatch.setattr(rpd, "archives", lambda: [{"url": bundle["url"]}])
    assert bundle["url"] not in {d["url"] for d in regulations.all_docs().values()}


def test_oversized_download_is_reported_without_publishing_members(bundle, monkeypatch):
    from catix.docs.sources import archives

    monkeypatch.setattr(archives, "MAX_ARCHIVE_BYTES", 1)
    assert regulations.read_new(ocr=False) == []
    docs = regulations.all_docs()
    assert not any(d.get("member") for d in docs.values())
    assert archive_documents.load(bundle["parent"])["status"] == "limit"


def test_archive_redirect_cannot_leave_trusted_providers(bundle, monkeypatch, tmp_path):
    from catix.docs.sources import archives

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
    from catix.docs.sources import archives

    name = "Программа.pdf"
    encoded = name.encode("cp866")
    placeholder = "x" * len(encoded)
    source = tmp_path / "old.zip"
    source.write_bytes(zipped({placeholder: b"%PDF course"}).replace(placeholder.encode(), encoded))
    listing = archives.unpack(source, tmp_path / "members")
    assert listing[0]["member"] == name
