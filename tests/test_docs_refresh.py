"""A document downloaded again is not read again when it is the same file; a document the site says nothing about is
compared by its bytes once a month."""

import contextlib
import hashlib
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from catix.docs import files
from catix.docs.sources import regulations, sites

KEY, URL, BODY = "site-hotel-1-rules", "https://hotel.innopolis.university/r.pdf", b"%PDF-1.4 same"
TEXT = "1. Общие положения " * 50


def _document(monkeypatch, **note):
    monkeypatch.setattr(regulations, "all_docs", lambda: {KEY: {"title": "Правила", "url": URL, "root": "r", "section": "site/hotel", "ext": "pdf"}})
    monkeypatch.setattr(sites, "collect_linked_docs", lambda: 0)
    monkeypatch.setattr(regulations, "discover_linked_documents", dict)
    monkeypatch.setattr(regulations, "PAUSE", 0)
    monkeypatch.setattr(regulations, "layer_text", lambda *a, **k: pytest.fail("the unchanged file was extracted again"))
    monkeypatch.setattr(regulations, "ocr_text", lambda *a, **k: pytest.fail("the unchanged file was OCR'd again"))
    files.write_text(f"r/{KEY}.txt", TEXT)
    files.write_json(f"r/{KEY}.json", {"title": "Правила", "sha256": hashlib.sha256(BODY).hexdigest(), "method": "text layer", "refetch": True, **note})


def test_a_refetched_document_with_the_same_bytes_is_not_read_again(monkeypatch):
    _document(monkeypatch)
    monkeypatch.setattr(regulations.httpx, "get", lambda u, **k: httpx.Response(200, content=BODY, request=httpx.Request("GET", u)))
    assert regulations.read_new() == []
    note = files.read_json(f"r/{KEY}.json")
    assert "refetch" not in note and note["sha256"] == hashlib.sha256(BODY).hexdigest() and files.read_text(f"r/{KEY}.txt") == TEXT


def test_a_refetch_answered_304_keeps_the_text(monkeypatch):
    _document(monkeypatch, remote={"etag": '"v1"'})

    def get(u, headers=None, **k):
        assert headers["If-None-Match"] == '"v1"'
        return httpx.Response(304, request=httpx.Request("GET", u))

    monkeypatch.setattr(regulations.httpx, "get", get)
    assert regulations.read_new() == []
    note = files.read_json(f"r/{KEY}.json")
    assert "refetch" not in note and note["remote"] == {"etag": '"v1"'} and files.read_text(f"r/{KEY}.txt") == TEXT


def test_a_document_the_site_says_nothing_about_is_compared_by_its_bytes_once_a_month(monkeypatch):
    _document(monkeypatch, remote={})
    files.write_json(f"r/{KEY}.json", {k: v for k, v in files.read_json(f"r/{KEY}.json").items() if k != "refetch"})
    gets = []

    class Client:
        def head(self, u):
            return httpx.Response(200, request=httpx.Request("HEAD", u))

        def get(self, u, **k):
            gets.append(u)
            return httpx.Response(200, content=b"%PDF-1.4 other", request=httpx.Request("GET", u))

    monkeypatch.setattr(regulations.httpx, "Client", lambda **k: contextlib.nullcontext(Client()))
    assert regulations.refresh() == 1
    note = files.read_json(f"r/{KEY}.json")
    assert note["refetch"] is True and note["checked_at"] and len(gets) == 1
    files.write_json(f"r/{KEY}.json", {k: v for k, v in note.items() if k != "refetch"})
    assert regulations.refresh() == 0 and len(gets) == 1  # (checked within the month: no download)
    old = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat(timespec="seconds")
    files.write_json(f"r/{KEY}.json", {**note, "refetch": False, "checked_at": old})
    assert regulations.refresh() == 1 and len(gets) == 2
