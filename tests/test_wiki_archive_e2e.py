"""Real ZIP/7z -> Word conversion -> PDF extraction -> wiki pages, with only HTTP replaced."""

import hashlib
import shutil
import subprocess
import zipfile

import httpx
import pytest

from catix.wiki import paths
from catix.wiki.sources import chandra, regulations, sites


@pytest.mark.parametrize("extension", ["zip", "7z"])
def test_real_archive_documents_reach_wiki_without_ocr(tmp_path, monkeypatch, extension):
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
    else:
        subprocess.run(["7z", "a", "-t7z", str(archive), "rules.rtf"], cwd=source, check=True, capture_output=True, timeout=20)
    monkeypatch.setattr(sites, "ROOT", tmp_path / "raw" / "sites")
    monkeypatch.setattr(sites, "DOCS", tmp_path / "wiki" / "raw")
    monkeypatch.setattr(paths, "DOCS", tmp_path / "wiki" / "raw")
    monkeypatch.setattr(sites, "DISCOVERED", tmp_path / "raw" / "discovered.json")
    monkeypatch.setattr(sites, "SITES", {"unit": sites.Site("https://unit.example/", "en", "Unit", "^nothing$", sitemap=False)})
    monkeypatch.setattr(regulations, "DOCS", {})
    monkeypatch.setattr(regulations, "SVEDEN_ROOT", tmp_path / "raw" / "sveden")
    monkeypatch.setattr(regulations, "LINKED", tmp_path / "raw" / "linked.json")
    monkeypatch.setattr(regulations, "PAUSE", 0)
    monkeypatch.setattr(chandra, "text_of_pdf", lambda *a, **kw: pytest.fail("a text document called OCR"))
    url = f"https://unit.example/documents.{extension}"
    sites.save("unit", {"pages": {}, "docs": {url: "University admission rules"}})
    requests = []
    with httpx.Client(transport=httpx.MockTransport(lambda req: requests.append(str(req.url)) or httpx.Response(200, content=archive.read_bytes()))) as client:
        monkeypatch.setattr(regulations.httpx, "stream", client.stream)
        read = regulations.read_new(ocr=False)
        assert len(read) == 1
        regulations.compile_all()
        page = paths.DOCS / "regulations" / f"{read[0]}.md"
        assert "submit their application" in page.read_text() and url in page.read_text() and "rules.rtf" in page.read_text()
        before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (tmp_path / "raw").rglob("*") if p.is_file()}
        assert regulations.read_new(ocr=False) == []
        regulations.compile_all()
        assert before == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (tmp_path / "raw").rglob("*") if p.is_file()}
        assert requests == [url]
