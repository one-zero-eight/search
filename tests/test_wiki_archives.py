"""Real containers, no OCR, models or live wiki data."""

import hashlib
import importlib
import io
import shutil
import subprocess
import tarfile
import zipfile

import pytest

from catix.wiki.sources import archives


@pytest.mark.parametrize("limit,value,members", [
    ("MAX_ARCHIVE_BYTES", 8, [("a.pdf", b"12345")]),
    ("MAX_FILES", 1, [("a.pdf", b"a"), ("b.pdf", b"b")]),
    ("MAX_MEMBER_BYTES", 4, [("a.pdf", b"12345")]),
    ("MAX_TOTAL_BYTES", 6, [("a.pdf", b"1234"), ("b.txt", b"1234")]),
    ("TIMEOUT", 0.001, [("a.pdf", b"a")]),
    ("MAX_MEMORY_BYTES", 1024 * 1024, [("a.pdf", b"a")]),
])
def test_limits_are_enforced_and_failure_is_retryable(tmp_path, monkeypatch, limit, value, members):
    source = make_zip(tmp_path / "input.zip", members)
    destination = tmp_path / "out"
    with monkeypatch.context() as patch:
        patch.setattr(archives, limit, value, raising=False)
        with pytest.raises(archives.ArchiveError) as error:
            archives.unpack(source, destination)
        assert error.value.status == "limit"
        assert not destination.exists()
    assert archives.unpack(source, destination)


def test_existing_destination_is_untouched(tmp_path):
    source = make_zip(tmp_path / "input.zip", [("a.pdf", b"new")])
    destination = tmp_path / "out"
    destination.mkdir()
    sentinel = destination / "keep.pdf"
    sentinel.write_bytes(b"old")
    with pytest.raises(archives.ArchiveError) as error:
        archives.unpack(source, destination)
    assert error.value.status == "unsafe"
    assert sentinel.read_bytes() == b"old"
    assert list(destination.iterdir()) == [sentinel]


@pytest.mark.parametrize("name", ["../escape.pdf", "/absolute.pdf", "folder/../../escape.pdf", r"folder\..\escape.pdf", r"C:\escape.pdf", "C:escape.pdf", r"\\host\escape.pdf"])
def test_unsafe_paths_are_rejected(tmp_path, name):
    source = make_zip(tmp_path / "input.zip", [(name, b"x")])
    with pytest.raises(archives.ArchiveError) as error:
        archives.unpack(source, tmp_path / "out")
    assert error.value.status == "unsafe"
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("mode", [0o120777, 0o010644, 0o020644, 0o060644, 0o140644])
def test_links_and_special_entries_are_rejected(tmp_path, mode):
    entry = zipfile.ZipInfo("special.pdf")
    entry.create_system = 3
    entry.external_attr = mode << 16
    source = make_zip(tmp_path / "input.zip", [(entry, b"/etc/passwd")])
    with pytest.raises(archives.ArchiveError) as error:
        archives.unpack(source, tmp_path / "out")
    assert error.value.status == "unsafe"


def test_duplicate_normalized_names_are_rejected(tmp_path):
    source = make_zip(tmp_path / "input.zip", [("folder/a.pdf", b"a"), ("./folder//a.pdf", b"b")])
    with pytest.raises(archives.ArchiveError) as error:
        archives.unpack(source, tmp_path / "out")
    assert error.value.status == "unsafe"


def test_directories_are_counted_but_not_documents(tmp_path, monkeypatch):
    source = make_zip(tmp_path / "input.zip", [("folder/", b""), ("folder/a.pdf", b"a")])
    rows = archives.unpack(source, tmp_path / "out")
    assert len(rows) == 1 and rows[0]["member"] == "folder/a.pdf"
    monkeypatch.setattr(archives, "MAX_FILES", 1)
    with pytest.raises(archives.ArchiveError) as error:
        archives.unpack(source, tmp_path / "retry")
    assert error.value.status == "limit"


@pytest.mark.parametrize("prefix", ["word", "xl", "ppt"])
def test_office_zip_is_not_a_container(tmp_path, prefix):
    source = make_zip(tmp_path / "input", [("[Content_Types].xml", b"xml"), (prefix + "/document.xml", b"xml")])
    assert archives.kind(source) is None
    with pytest.raises(archives.ArchiveError) as error:
        archives.unpack(source, tmp_path / "out")
    assert error.value.status == "unsupported"


def test_tar_is_not_accepted_even_with_zip_suffix(tmp_path):
    source = tmp_path / "input.zip"
    with tarfile.open(source, "w") as archive:
        entry = tarfile.TarInfo("a.pdf")
        entry.size = 1
        archive.addfile(entry, io.BytesIO(b"a"))
    assert archives.kind(source) is None
    with pytest.raises(archives.ArchiveError) as error:
        archives.unpack(source, tmp_path / "out")
    assert error.value.status == "unsupported"


@pytest.mark.parametrize("content", [b"PK\x03\x04broken", b"7z\xbc\xaf\x27\x1cbroken", b"PK\x05\x06"])
def test_malformed_archive_is_explicit(tmp_path, content):
    source = tmp_path / "input"
    source.write_bytes(content)
    with pytest.raises(archives.ArchiveError) as error:
        archives.unpack(source, tmp_path / "out")
    assert error.value.status == "invalid"
    assert not (tmp_path / "out").exists()


def test_empty_archive_is_invalid(tmp_path):
    source = make_zip(tmp_path / "input", [])
    with pytest.raises(archives.ArchiveError) as error:
        archives.unpack(source, tmp_path / "out")
    assert error.value.status == "invalid"


def make_7z(tmp_path, *, encrypted=False, header_encrypted=False, format="7z"):
    executable = shutil.which("7z") or shutil.which("7zz")
    if not executable:
        pytest.skip("7z fixture builder is unavailable")
    source = tmp_path / "input-container"
    document = tmp_path / "Rules.DOC"
    document.write_bytes(b"document body")
    args = [executable, "a", "-t" + format, str(source), document.name]
    if encrypted:
        args.append("-pfixture-password")
    if header_encrypted:
        args.append("-mhe=on")
    subprocess.run(args, cwd=tmp_path, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True, timeout=20)
    source.with_suffix("." + format).rename(source)
    return source


def test_real_7z_document(tmp_path):
    source = make_7z(tmp_path)
    assert archives.kind(source) == "7z"
    rows = archives.unpack(source, tmp_path / "out")
    assert len(rows) == 1 and rows[0]["member"] == "Rules.DOC"
    assert rows[0]["ext"] == ".doc"
    assert rows[0]["sha256"] == hashlib.sha256(b"document body").hexdigest()
    assert (tmp_path / "out" / rows[0]["file"]).read_bytes() == b"document body"


@pytest.mark.parametrize("format,header", [("zip", False), ("7z", False), ("7z", True)])
def test_encrypted_archives_are_explicit(tmp_path, format, header):
    source = make_7z(tmp_path, encrypted=True, header_encrypted=header, format=format)
    with pytest.raises(archives.ArchiveError) as error:
        archives.unpack(source, tmp_path / "out")
    assert error.value.status == "encrypted"


def test_directory_payload_cannot_bypass_byte_budgets(tmp_path):
    source = make_zip(tmp_path / "input", [("folder/", b"hidden payload"), ("a.pdf", b"a")])
    with pytest.raises(archives.ArchiveError) as error:
        archives.unpack(source, tmp_path / "out")
    assert error.value.status == "unsafe"


def test_non_regular_input_is_rejected_without_opening_it(tmp_path, monkeypatch):
    import os

    monkeypatch.setattr(archives, "TIMEOUT", 0.2)
    source = tmp_path / "fifo"
    os.mkfifo(source)
    with pytest.raises(archives.ArchiveError) as error:
        archives.unpack(source, tmp_path / "out")
    assert error.value.status == "unsafe"


def test_7z_symlink_is_rejected(tmp_path):
    executable = shutil.which("7z") or shutil.which("7zz")
    if not executable:
        pytest.skip("7z fixture builder is unavailable")
    (tmp_path / "link.pdf").symlink_to("missing-target")
    source = tmp_path / "links.7z"
    subprocess.run([executable, "a", "-t7z", "-snl", str(source), "link.pdf"], cwd=tmp_path, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True, timeout=20)
    with pytest.raises(archives.ArchiveError) as error:
        archives.unpack(source, tmp_path / "out")
    assert error.value.status == "unsafe"


def test_decoder_hardlinks_are_rejected(tmp_path, monkeypatch):
    # ZIP and 7z writers cannot portably encode hardlinks; exercise libarchive's
    # exposed hardlink flag before content can be read or a local file opened.
    from contextlib import contextmanager
    from types import SimpleNamespace
    import libarchive

    source = make_7z(tmp_path)

    @contextmanager
    def reader(*args, **kwargs):
        yield [SimpleNamespace(pathname="link.pdf", issym=False, islnk=True)]

    monkeypatch.setattr(libarchive, "file_reader", reader)
    destination = tmp_path / "out"
    destination.mkdir()
    with pytest.raises(archives.ArchiveError) as error:
        archives._extract(source, destination)
    assert error.value.status == "unsafe"
    assert not list(destination.iterdir())


@pytest.mark.parametrize("ext", [".doc", ".docx", ".rtf"])
def test_supported_document_extensions(tmp_path, ext):
    content = b"document body"
    source = make_zip(tmp_path / "input", [("folder/document" + ext, content)])
    row, = archives.unpack(source, tmp_path / "out")
    assert row["status"] == "ready" and row["ext"] == ext
    assert (tmp_path / "out" / row["file"]).read_bytes() == content


def test_7z_actual_byte_limit(tmp_path, monkeypatch):
    source = make_7z(tmp_path)
    monkeypatch.setattr(archives, "MAX_MEMBER_BYTES", 2)
    with pytest.raises(archives.ArchiveError) as error:
        archives.unpack(source, tmp_path / "out")
    assert error.value.status == "limit"


def test_unsupported_member_is_still_byte_limited(tmp_path, monkeypatch):
    source = make_zip(tmp_path / "input", [("nested.zip", b"x" * 1000)])
    monkeypatch.setattr(archives, "MAX_MEMBER_BYTES", 100)
    with pytest.raises(archives.ArchiveError) as error:
        archives.unpack(source, tmp_path / "out")
    assert error.value.status == "limit"


def test_truncated_zip_central_directory_is_invalid(tmp_path):
    source = make_zip(tmp_path / "input", [("a.pdf", b"a")])
    source.write_bytes(source.read_bytes()[:-22])
    with pytest.raises(archives.ArchiveError) as error:
        archives.unpack(source, tmp_path / "out")
    assert error.value.status == "invalid"


def test_null_byte_name_is_unsafe(tmp_path):
    source = make_zip(tmp_path / "input", [("aX.pdf", b"a")])
    source.write_bytes(source.read_bytes().replace(b"aX.pdf", b"a\x00.pdf"))
    with pytest.raises(archives.ArchiveError) as error:
        archives.unpack(source, tmp_path / "out")
    assert error.value.status == "unsafe"


@pytest.mark.parametrize("ext", [".pdf", ".docx"])
def test_nested_archive_cannot_hide_behind_document_extension(tmp_path, ext):
    nested = make_zip(tmp_path / "nested", [("a.pdf", b"a")])
    source = make_zip(tmp_path / "input", [("nested" + ext, nested.read_bytes())])
    row, = archives.unpack(source, tmp_path / "out")
    assert row["status"] == "unsupported" and row["file"] is None and row["sha256"] is None
    assert not list((tmp_path / "out").iterdir())


def test_real_docx_package_inside_container_remains_a_document(tmp_path):
    docx = make_zip(tmp_path / "document", [("[Content_Types].xml", b"xml"), ("word/document.xml", b"xml")])
    source = make_zip(tmp_path / "input", [("rules.docx", docx.read_bytes())])
    row, = archives.unpack(source, tmp_path / "out")
    assert row["status"] == "ready" and row["ext"] == ".docx"
    assert (tmp_path / "out" / row["file"]).read_bytes() == docx.read_bytes()


def make_zip(path, members):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in members:
            archive.writestr(name, content)
    return path


def test_zip_documents_use_generated_names(tmp_path):
    archives = importlib.import_module("catix.wiki.sources.archives")
    source = make_zip(tmp_path / "input.bin", [("./folder/Rules.PDF", b"%PDF-content"), ("notes.txt", b"text"), ("nested.zip", b"PK\x03\x04")])
    destination = tmp_path / "output"
    assert archives.kind(source) == "zip"
    rows = archives.unpack(source, destination)
    assert [r["member"] for r in rows] == ["folder/Rules.PDF", "notes.txt", "nested.zip"]
    ready = rows[0]
    assert ready["status"] == "ready"
    assert ready["sha256"] == hashlib.sha256(b"%PDF-content").hexdigest()
    assert ready["size"] == len(b"%PDF-content")
    assert ready["ext"] == ".pdf"
    assert "/" not in ready["file"] and "Rules" not in ready["file"]
    assert (destination / ready["file"]).read_bytes() == b"%PDF-content"
    for row in rows[1:]:
        assert row["status"] == "unsupported" and row["file"] is None and row["sha256"] is None
    assert len(list(destination.iterdir())) == 1
