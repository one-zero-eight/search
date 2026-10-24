"""index.md: the root one lists the folders, each folder lists its pages, grouped where a folder is large (compile.py)."""

from catix.wiki import compile as wc


def _page(path, **front):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = "".join(f"{k}: {v!r}\n".replace("'", '"') for k, v in front.items())
    path.write_text(f"---\n{lines}---\n\nbody\n", encoding="utf-8")


def test_every_folder_has_its_index_and_the_root_lists_the_folders(tmp_path, monkeypatch):
    monkeypatch.setattr(wc, "BUNDLE", tmp_path)
    _page(tmp_path / "regulations/a.md", type="regulation", title="A", description="a", section="sveden/grants")
    _page(tmp_path / "regulations/b.md", type="regulation", title="B", description="b")
    for n, (cohort, semester) in enumerate([(2025, 2), (2026, 1), (2025, 1)]):
        _page(tmp_path / f"course-programmes/p{n}.md", type="course-programme", title=f"P{n}", description="p",
              programme="MSc 09.04.01", cohort=cohort, semester=semester)
    wc.link()
    root = (tmp_path / "index.md").read_text()
    assert root.startswith('---\nokf_version: "0.2"\n---') and "(/regulations/index.md)" in root and "2 pages" in root
    assert "/regulations/a.md" not in root and "guides" not in root  # pages are in the folders' indexes; empty folders are not listed
    regulations = (tmp_path / "regulations/index.md").read_text()
    assert not regulations.startswith("---") and "## eduwiki" in regulations and "## sveden/grants" in regulations
    programmes = (tmp_path / "course-programmes/index.md").read_text()
    order = [programmes.index(f"набор {c}, {s} семестр") for c, s in [(2026, 1), (2025, 1), (2025, 2)]]
    assert order == sorted(order)  # the newest cohort first, then by semester
    assert "index.md" not in {p for p, _ in wc.concepts()}
