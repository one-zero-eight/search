"""Preview identity comes from the metadata the store keeps for a document, with no disk and no network."""

import hashlib
import socket
from dataclasses import replace

import httpx
import pytest

from catix.db.docs import DocHit
from catix.docs import preview_cache, previews

URL = "https://innopolis.university/programmes.zip"
MEMBER = "first/Б1.О.01_Algebra.pdf"
SHA = hashlib.sha256(b"original PDF bytes").hexdigest()


def hit(**fields) -> DocHit:
    base = dict(id=1, path="course-programmes/rpd-1-same-title", seq=0, heading="", clause="", sha="c1", text="Original evidence.", cites=[],
                title="Same title", type="course-programme", trust="official", audience=[], resource=URL, status=None, review=None,
                source_warning=None, stale_after=None, issued=None, page_sha="a1b2c3d4e5f60718", archive_member=MEMBER, archive_sha256=SHA)
    return DocHit(**{**base, **fields})


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("describing metadata must not download or unpack anything")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(httpx.Client, "send", forbidden)


@pytest.mark.parametrize("path", ["course-programmes/rpd-1-same-title", "regulations/site-university-programmes-member-0123"])
def test_a_page_with_a_member_and_a_digest_is_described(path):
    page = hit(path=path)
    assert previews.describe(page) == {"page": path, "revision": "a1b2c3d4e5f60718", "member": MEMBER}


@pytest.mark.parametrize("member", ["../original.pdf", "/original.pdf", "a/../original.pdf", "a\\original.pdf",
                                    "C:/original.pdf", "a//original.pdf", "a/./original.pdf", "a/\x00original.pdf",
                                    "a/\noriginal.pdf", "original.doc", "original.pdf.zip", "", None])
def test_unsafe_or_non_pdf_member_is_refused(member):
    assert previews.describe(hit(archive_member=member)) is None
    assert previews.read(hit(archive_member=member)) is None


def test_a_pdf_member_in_any_case_is_accepted():
    assert previews.describe(hit(archive_member="first/Algebra.PDF"))["member"] == "first/Algebra.PDF"


@pytest.mark.parametrize("digest", [None, "", SHA[:12], SHA[:-1], SHA.upper(), "g" * 64, SHA + "0"])
def test_a_digest_that_is_not_a_full_sha256_is_refused(digest):
    assert previews.describe(hit(archive_sha256=digest)) is None
    assert previews.read(hit(archive_sha256=digest)) is None


@pytest.mark.parametrize("path", ["sites/hotel/rooms", "eduwiki/courses/a", "/raw/course-programmes/a.md",
                                  "course-programme/a", "other/regulations/a"])
def test_only_regulations_and_course_programmes_have_previews(path):
    assert previews.describe(hit(path=path)) is None
    assert previews.read(hit(path=path)) is None


@pytest.mark.parametrize("resource", [None, ""])
def test_a_page_without_an_original_has_no_preview(resource):
    assert previews.describe(hit(resource=resource)) is None
    assert previews.read(hit(resource=resource)) is None


def test_read_opens_the_member_the_page_names(monkeypatch):
    calls = []
    monkeypatch.setattr(preview_cache, "read", lambda *args: calls.append(args) or (b"%PDF", "Algebra.pdf"))
    assert previews.read(hit()) == (b"%PDF", "Algebra.pdf")
    assert calls == [(URL, MEMBER, SHA)]


def test_a_page_of_another_revision_describes_that_revision():
    other = replace(hit(), page_sha="0" * 16)
    assert previews.describe(other)["revision"] == "0" * 16
