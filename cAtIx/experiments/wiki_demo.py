"""The wiki's own run on a stand-in site (wiki/mock.py), start to end, without touching the real `wiki` branch.

    uv run python experiments/wiki_demo.py

1. A local site with one new document: a made-up "Положение о студенческом научном обществе", marked as a test.
2. `catix-wiki autopilot --source mock` on a local branch `wiki-demo` of the data checkout (WIKI_ROOT), no push: the
   document is downloaded and read, the model describes it, it gets a page; the model proposes a guide, writes it; the
   checks run; a commit.
3. The site gets a new version of the document (30 days become 14, 50 000 roubles become 70 000). The next run finds it
   by HEAD (Last-Modified, size), reads it again, rewrites the page and the guide whose evidence changed; checks; a commit.
4. The data checkout goes back to `wiki`, and the search index with it. `wiki-demo` stays, to look at (git log wiki-demo).
"""

import os
import subprocess
import sys
import time
from pathlib import Path

from catix.settings import settings
from catix.wiki import mock

DATA = settings.wiki_root
SITE = Path(__file__).resolve().parent / ".wiki-demo-site"  # (ignored by git)
NAME = "Положение_о_студенческом_научном_обществе_(тестовый_документ_cAtIx)"
TEXT = """АНО ВО «Университет Иннополис»
ПОЛОЖЕНИЕ О СТУДЕНЧЕСКОМ НАУЧНОМ ОБЩЕСТВЕ
(тестовый документ cAtIx, не является документом университета)
от 20 октября 2026 г.

1. Общие положения
1.1. Студенческое научное общество (далее — Общество) объединяет обучающихся, которые ведут научную работу.
1.2. Членом Общества может стать обучающийся по программам бакалавриата, магистратуры и аспирантуры.
1.3. Обществом руководит совет из 5 человек, избираемый на 1 год.

2. Порядок вступления
2.1. Для вступления обучающийся подает заявление в совет Общества.
2.2. Совет рассматривает заявление в течение {days} календарных дней.
2.3. К заявлению прилагается описание научной работы объемом не более 2 страниц.
2.4. Решение о приеме сообщается заявителю по корпоративной почте.

3. Права и обязанности членов Общества
3.1. Член Общества вправе участвовать в ежегодной конференции Общества.
3.2. Член Общества вправе подать заявку на грант на научную работу в размере до {grant} рублей.
3.3. Член Общества обязан не реже 1 раза в семестр отчитываться о ходе научной работы.
3.4. Член Общества, не отчитавшийся 2 семестра подряд, исключается из Общества.

4. Заключительные положения
4.1. Положение вступает в силу с момента утверждения.
"""


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(DATA), *args], capture_output=True, text=True, check=True).stdout.strip()


def publish(days: int, grant: str) -> None:
    """The document on the mock site, as a PDF with a text layer (LibreOffice), as the university publishes them."""
    SITE.mkdir(exist_ok=True)
    source = SITE / f"{NAME}.txt"
    source.write_text(TEXT.format(days=days, grant=grant), encoding="utf-8")
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(SITE), str(source)], capture_output=True, check=True, timeout=180)
    source.unlink()


def autopilot(url: str) -> None:
    env = {**os.environ, "WIKI_BRANCH": "wiki-demo", "WIKI_MOCK_SITE": url}
    run = subprocess.run(["uv", "run", "catix-wiki", "autopilot", "--source", "mock", "--no-push"], capture_output=True, text=True, env=env)
    for line in (run.stdout + run.stderr).splitlines():
        if line.startswith(("== ", "[", "  -> ", "  accepted", "  rejected")) or "mock-" in line or "Traceback" in line or "Error" in line:
            print("   ", line)


def show_commit() -> None:
    print(git("log", "-1", "--format=%n    commit %h by %an%n%n%B"))
    for path in git("diff", "--name-only", "HEAD~1", "HEAD", "--", "wiki/guides", "wiki/regulations/mock-*").splitlines():
        print(f"    --- {path}")
        diff = git("diff", "--unified=0", "HEAD~1", "HEAD", "--", path).splitlines()
        lines = [line for line in diff if line[:1] in "+-" and not line.startswith(("+++", "---"))]
        for line in lines[:14]:
            print("      " + line[:160])
        if len(lines) > 14:
            print(f"      ... {len(lines) - 14} more lines")


def main() -> None:
    if DATA is None:
        sys.exit("WIKI_ROOT is not set: the demo runs on a branch of the wiki's data checkout")
    stashed = bool(git("status", "--porcelain"))
    if stashed:
        git("stash", "push", "-q", "-u", "-m", "wiki-demo: what the checkout had before")
    git("switch", "-q", "-C", "wiki-demo")
    server = mock.serve(SITE)
    url = f"http://127.0.0.1:{server.server_port}/"
    try:
        print("1. The mock site publishes a new document")
        publish(days=30, grant="50 000")
        print("2. The wiki's run: source mock -> page -> guide -> checks -> commit")
        autopilot(url)
        show_commit()
        print("3. The site publishes a new version: 30 days -> 14, 50 000 -> 70 000 roubles")
        time.sleep(1.5)  # (Last-Modified has a precision of a second)
        publish(days=14, grant="70 000")
        autopilot(url)
        show_commit()
    finally:
        server.shutdown()
        print("4. Back to `wiki`; the search index follows it")
        git("switch", "-q", "wiki")
        if stashed:
            git("stash", "pop", "-q")
        subprocess.run(["uv", "run", "catix-wiki", "index", "--no-embed"], capture_output=True)
        print("   the demo commits stay on the local branch wiki-demo: git -C", DATA, "log wiki-demo")


if __name__ == "__main__":
    main()
