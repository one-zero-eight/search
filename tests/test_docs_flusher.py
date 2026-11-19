from datetime import datetime, timezone

from catix.docs import build, flusher


def test_a_flush_rebuilds_only_what_the_sources_wrote_since_the_last_rebuild(monkeypatch):
    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 2, tzinfo=timezone.utc)
    marks = iter([None, t1, t1, t2])
    current: list = []
    calls: list[int] = []

    def mark():
        current[:] = [next(marks)]
        return current[0]

    def rebuild():
        calls.append(1)
        monkeypatch.setattr(build, "BUILT_UP_TO", current[0])
        return {"pages new": 1}

    monkeypatch.setattr(build, "BUILT_UP_TO", None)
    monkeypatch.setattr(build, "source_mark", mark)
    monkeypatch.setattr(build, "rebuild", rebuild)

    assert [flusher.flush_once() for _ in range(4)] == [False, True, False, True]
    assert len(calls) == 2
