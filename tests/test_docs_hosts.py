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


def test_the_pause_of_a_site_spaces_its_requests_instead_of_the_default(monkeypatch):
    clock = iter([100.0, 100.5])
    sleeps: list[float] = []
    monkeypatch.setattr(hosts, "_NEXT", {})
    monkeypatch.setattr(hosts, "_SHARED", True)
    monkeypatch.setattr(hosts.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(hosts.time, "sleep", sleeps.append)

    hosts.turn("https://slow.example/a", 5.0)
    hosts.turn("https://slow.example/b", 5.0)  # (5 s after the first: 4.5 are left)
    assert sleeps == [4.5]
    assert hosts._NEXT["slow.example"] == 110.0  # (the next one is 5 s after this one, not PAUSE)
