import json
import re

import pytest

from catix.docs import runner, store
from catix.docs.sources import guide


def test_the_real_guide_has_six_documents_with_stable_meta():
    docs = guide.compile_all()
    assert [d.path for d in docs] == sorted(f"guide/{t}.{l}" for t in guide.LINKS for l in ("ru", "en"))
    for d in docs:
        assert d.meta["title"]
        assert d.meta["resource"] == guide.LINKS[d.path.split("/")[1].rsplit(".", 1)[0]]
        assert not re.search(r"\d{4}-\d{2}-\d{2}", json.dumps(d.meta))
    assert [store.fingerprint(d) for d in docs] == [store.fingerprint(d) for d in guide.compile_all()]


@pytest.mark.parametrize("name, text, message", [
    ("x.md", "# T\n", "guide file name"),
    ("catix.ru.md", "no title\n", "without a # title"),
    ("other.ru.md", "# T\n", "without a link"),
])
def test_a_broken_guide_file_is_refused(tmp_path, monkeypatch, name, text, message):
    (tmp_path / name).write_text(text, encoding="utf-8")
    monkeypatch.setattr(guide, "FOLDER", tmp_path)
    with pytest.raises(ValueError, match=message):
        guide.compile_all()


def test_a_failing_guide_sync_does_not_stop_the_loop(monkeypatch, capsys):
    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(runner.build, "sync_guide", boom)
    runner.sync_guide()
    assert "RuntimeError: db down" in capsys.readouterr().err
