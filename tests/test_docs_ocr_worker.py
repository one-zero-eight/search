import pytest

from catix.docs import ocr_worker
from catix.docs.sources import lighton, ocr_queue, pastpapers, regulations
from catix.docs.sources.ocr_queue import Scan


def test_the_worker_reads_only_what_waits_and_only_when_the_server_answers(monkeypatch):
    queues = iter([[], [Scan(source="regs", key="k1", title="t", url="u", pages=3, too_long=False),
                        Scan(source="regs", key="long", title="t", url="u", pages=90, too_long=True)]] * 2)
    monkeypatch.setattr(ocr_queue, "scans", lambda: next(queues))
    answers = iter([False, True])
    monkeypatch.setattr(lighton, "available", lambda: next(answers))
    calls: list[dict] = []
    monkeypatch.setattr(regulations, "read_new", lambda **kw: calls.append(kw) or ["k1"])
    monkeypatch.setattr(pastpapers, "fetch", lambda **kw: pytest.fail("no paper waits"))

    assert ocr_worker.read_once() == (0, True)  # nothing queued
    assert ocr_worker.read_once() == (0, False)  # a scan waits, the server is away
    assert calls == []
    next(queues)  # (skip the empty list of the second pair)
    assert ocr_worker.read_once() == (1, True)
    assert calls == [{"prefixes": ("k1",), "ocr": True, "collect": False}]
