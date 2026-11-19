"""Real ZIP/7z -> Word conversion -> PDF extraction -> documents, with only HTTP replaced."""

import copy
import re
import shutil
import subprocess
import tempfile
import zipfile

import httpx
import pytest

from catix.docs.sources import tesseract, regulations, sites


@pytest.mark.parametrize("extension", ["zip", "7z", "pdf"])
def test_real_archive_documents_reach_the_store_without_ocr(tmp_path, monkeypatch, memory_files, extension):
    if not all(shutil.which(cmd) for cmd in ("soffice", "pdfinfo", "7z")):
        pytest.skip("real archive conversion requires LibreOffice, Poppler and 7z")
    source = tmp_path / "source"
    source.mkdir()
    text = "Students must follow the university admission rules and submit their application before the deadline. " * 25
    (source / "rules.rtf").write_text("{\\rtf1\\ansi " + text + "}")
    archive = tmp_path / f"documents.{extension}"
    if extension == "zip":
        with zipfile.ZipFile(archive, "w") as output:
            output.write(source / "rules.rtf", "regulations/rules.rtf")
    elif extension == "7z":
        subprocess.run(["7z", "a", "-t7z", str(archive), "rules.rtf"], cwd=source, check=True, capture_output=True, timeout=20)
    else:
        archive = regulations.to_pdf(source / "rules.rtf")
        assert archive.exists()
    monkeypatch.setattr(sites, "SITES", {"unit": sites.Site("https://unit.example/", "en", "Unit", "^nothing$", sitemap=False)})
    monkeypatch.setattr(regulations, "DOCS", {})
    monkeypatch.setattr(regulations, "PAUSE", 0)
    monkeypatch.setattr(tesseract, "text_of_pdf", lambda *a, **kw: pytest.fail("a text document called OCR"))
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(work))
    url = f"https://unit.example/documents.{extension if extension != 'pdf' else 'zip'}"
    sites.save("unit", {"pages": {}, "docs": {url: "University admission rules"}})
    requests = []
    with httpx.Client(transport=httpx.MockTransport(lambda req: requests.append(str(req.url)) or httpx.Response(200, content=archive.read_bytes()))) as client:
        monkeypatch.setattr(regulations.httpx, "stream", client.stream)
        read = regulations.read_new(ocr=False)
        assert len(read) == 1
        [doc] = regulations.compile_all()
        assert doc.path == f"regulations/{read[0]}"
        assert "submit their application" in doc.body and url in doc.body and doc.meta["resource"] == url
        if extension == "pdf":
            assert "archive_member" not in doc.meta
            assert read == list(sites.docs())
        else:
            assert doc.meta["archive_member"].endswith("rules.rtf") and re.fullmatch(r"[0-9a-f]{64}", doc.meta["archive_sha256"])
        assert not list(work.iterdir())  # (the original lived only in the run's temporary folder)
        before = copy.deepcopy(memory_files.items)
        assert regulations.read_new(ocr=False) == []
        assert regulations.compile_all() == [doc]
        assert before == memory_files.items
        assert requests == [url]
