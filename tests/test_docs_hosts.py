from catix.docs.sources import hosts


def test_one_host_is_asked_pause_seconds_apart_across_threads(monkeypatch):
    clock = iter([100.0, 100.0, 100.5, 100.5])
    sleeps: list[float] = []
    monkeypatch.setattr(hosts, "_NEXT", {})
    monkeypatch.setattr(hosts, "_SHARED", True)
    monkeypatch.setattr(hosts.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(hosts.time, "sleep", sleeps.append)

    hosts.turn("https://innopolis.university/a")
    hosts.turn("https://www.innopolis.university/b")
    hosts.turn("https://apply.innopolis.university/c")

    assert sleeps == [2.0]

    monkeypatch.setattr(hosts, "_SHARED", False)
    hosts.turn("https://innopolis.university/d")
    assert sleeps == [2.0]
