"""The wiki's data lives in WIKI_ROOT, a checkout of the `wiki` branch: never in the code, and in the tests never in the real one."""

import os
import subprocess
import sys
from pathlib import Path

from catix.wiki import paths
from catix.wiki.sources import sites


def test_the_wiki_does_not_start_without_wiki_root_nor_with_the_code_as_its_data(tmp_path):
    env = {key: value for key, value in os.environ.items() if key != "WIKI_ROOT"}

    def start(root: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-c", "import catix.wiki.paths"], cwd=tmp_path, capture_output=True, text=True, check=False,
                              env=env | ({"WIKI_ROOT": root} if root else {}))  # (cwd: no .env there)

    assert "WIKI_ROOT is not set" in start().stderr
    assert "is the code's checkout" in start(str(paths.REPO)).stderr
    assert start(str(tmp_path)).returncode == 0


def test_a_test_reads_and_writes_a_wiki_and_a_catalogue_of_sites_of_its_own():
    assert paths.DATA == Path(os.environ["WIKI_ROOT"]).resolve() and paths.DATA.name.startswith("catix-test-wiki-")  # (conftest)
    assert not sites.CONFIG.is_relative_to(paths.DATA) and sites.DISCOVERED.parent == sites.CONFIG.parent  # (wiki_site_catalog)
    assert sites.CONFIG.read_bytes() == (Path(__file__).parent / "fixtures" / "sites.yaml").read_bytes()
    assert not sites.DISCOVERED.exists()
