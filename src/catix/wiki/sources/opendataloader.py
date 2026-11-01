"""The text layer of a PDF as opendataloader-pdf reads it (Java, no model): the reading order of a page (its columns, a frame
around text), its lists, its tables with their merged cells, a page's head where it first stands ('Приложение 2 к Положению
...'; a running head once, page numbers not at all). Its JSON becomes the
text regulations.py reads (to_markdown): a line of the page a line of the text, a blank line between blocks, tables as markdown
(table_markdown: a table of one column is text).

The page's own line breaks are kept (keep_line_breaks): a clause that starts a line of the page starts a line here, and a word
broken at the end of a line ('консор-\\nциума', 'научно-\\nтехнической') is made whole here by the words of the documents
(join_broken). Joining its lines itself, opendataloader glued a clause to the paragraph before it ('…не оплачивается. 10.13.
Обеспечение…') and dropped every hyphen at a break ('научнотехнической').

pdfplumber read a frame around text as a table, the columns of a report line by line across the page ('между- в Москве и ОО
«Совет бол- The International Business народных экспертов'), and a word broken at the end of a line as two ('научно- технической')."""

import json
import re
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

BATCH = 100  # PDFs a run of the converter reads (each run starts a JVM: one a PDF was slow)
WORD = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*")
BROKEN = re.compile(r"(?<![\w-])([^\W_]+(?:-[^\W_]+)*)-$")  # a line that ends in a word broken by a hyphen ('консор-')
LIST_MARK = re.compile(r"^[а-яa-z]\)\s")  # 'а) ...': an item of a list, not a paragraph going on
PAGE_NUMBER = re.compile(r"(?:стр(?:аница)?\.?|с\.|page)?\s*[-–]?\s*\d{1,4}\s*[-–]?(?:\s*(?:из|of|/)\s*\d{1,4})?", re.I)
PAGE_IN_HEAD = re.compile(r"(?<!\w)(?:стр(?:аница)?\.?|page)\s*\d{1,4}(?:\s*(?:из|of|/)\s*\d{1,4})?", re.I)  # 'Страница 23 из 90'
LIGATURES = str.maketrans({"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st"})  # 'Crazyﬂie'


@contextmanager
def converted(pdfs: list[Path]) -> Iterator[dict[Path, Path]]:
    """PDF -> its JSON, in a folder that lasts the block; a PDF the converter could not read has none (Java missing, a broken
    file: the caller reads it the old way)."""
    import opendataloader_pdf

    with tempfile.TemporaryDirectory(prefix="odl-") as out:
        def run(batch: list[Path]) -> bool:
            try:
                opendataloader_pdf.convert(input_path=[str(p) for p in batch], output_dir=out, format="json", image_output="off",
                                           quiet=True, keep_line_breaks=True, include_header_footer=True,
                                           content_safety_off="off-page")  # it took the corner of a landscape page for off it
                return True
            except (subprocess.CalledProcessError, OSError) as e:
                print(f"  opendataloader failed on {len(batch)} PDF(s): {type(e).__name__}", flush=True)
                return False

        for start in range(0, len(pdfs), BATCH):
            batch = pdfs[start:start + BATCH]
            if not run(batch) and len(batch) > 1:  # one bad file fails the run: the others one by one
                for pdf in batch:
                    if not (Path(out) / f"{pdf.stem}.json").exists():
                        run([pdf])
        yield {pdf: Path(out) / f"{pdf.stem}.json" for pdf in pdfs if (Path(out) / f"{pdf.stem}.json").exists()}


def text_of_pdf(pdf: Path, json_path: Path | None = None) -> str | None:
    """The text of a PDF (its JSON when converted already, as reextract does for many); None when it could not be read."""
    if json_path is None:
        with converted([pdf]) as done:
            return text_of(json.loads(done[pdf].read_text(encoding="utf-8"))) if pdf in done else None
    return text_of(json.loads(json_path.read_text(encoding="utf-8")))


def words_in(text: str) -> set[str]:
    """The words of a text inside its lines, a compound with its hyphen and its parts, in lower case; the halves of a word broken
    at a line's end ('консор-\\nциума', or 'консор- циума' as pdfplumber left it) are not words."""
    text = re.sub(r"[^\W\d_]+-(?:\n| )[^\W\d_]+", " ", text.lower())
    words: set[str] = set()
    for w in WORD.findall(text):
        words.add(w)
        words.update(w.split("-"))
    return words


@lru_cache(maxsize=1)
def corpus_words() -> frozenset[str]:
    """The words of all the documents: what decides a word broken at the end of a line, beside the document's own."""
    from catix.wiki.paths import DOCS

    words: set[str] = set()
    for page in (DOCS / "regulations").glob("*.md"):
        words |= words_in(page.read_text(encoding="utf-8"))
    return frozenset(words)


def join_broken(left: str, right: str, words: frozenset[str] | set[str]) -> str:
    """A word broken at the end of a line, whole: 'консор' + 'циума,' -> 'консорциума,', 'научно' + 'технической' ->
    'научно-технической'. The form the documents use inside a line decides; when they have neither or both, the hyphen stays
    if both halves are words ('социально-культурной'), else it was the line's ('органи-зации')."""
    head = re.match(r"[^\W\d_]+", right)
    if not head or right[:1].isupper() or re.search(r"\d", left):  # 'Папуа-\nНовая', '4D-\nплатформы'
        return f"{left}-{right}"
    tail = head.group(0).lower()
    whole_known, compound_known = left.lower() + tail in words, f"{left.lower()}-{tail}" in words
    if whole_known != compound_known:
        return f"{left}-{right}" if compound_known else left + right
    last = left.rsplit("-", 1)[-1].lower()
    return f"{left}-{right}" if len(last) > 1 and last in words and tail in words else left + right


def lines_of(text: str) -> list[str]:
    """The lines of a block, their spaces collapsed (a run of spaces is a table's gap to to_markdown)."""
    return [line for line in (re.sub(r"\s+", " ", raw).strip() for raw in text.translate(LIGATURES).split("\n")) if line]


def joined(lines: list[str], words: frozenset[str] | set[str]) -> list[str]:
    """The lines with the words broken at their ends made whole: the broken line takes the rest of the word from the next."""
    out: list[str] = []
    for line in lines:
        if out and (m := BROKEN.search(out[-1])) and line[:1].isalpha():
            rest, _, after = line.partition(" ")
            out[-1] = out[-1][:m.start()] + join_broken(m.group(1), rest, words) + (f" {after}" if after else "")
        else:
            out.append(line)
    return out


def texts(nodes: list[dict]) -> Iterator[str]:
    """The text of nodes in their order (the cell of a table: its paragraphs, lists, a table inside it)."""
    for node in nodes:
        if isinstance(node.get("content"), str):
            yield node["content"]
        for key in ("kids", "list items"):
            yield from texts(node.get(key) or [])
        for row in node.get("rows") or []:
            yield from texts(row.get("cells") or [])


def table_grid(table: dict, words: frozenset[str] | set[str]) -> tuple[list[list[str | None]], list[list[bool]]]:
    """The cells of a table on a grid, as table_markdown takes them: a cell another one covers is None, and `wide` when the
    one covering it is to its left (it stays empty) rather than above (it takes the value above)."""
    rows, cols = int(table.get("number of rows") or 0), int(table.get("number of columns") or 0)
    grid: list[list[str | None]] = [[None] * cols for _ in range(rows)]
    wide = [[False] * cols for _ in range(rows)]
    for row in table.get("rows") or []:
        for cell in row.get("cells") or []:
            r, c = int(cell["row number"]) - 1, int(cell["column number"]) - 1
            if not (0 <= r < rows and 0 <= c < cols):
                continue
            grid[r][c] = " ".join(" ".join(joined(lines_of(t), words)) for t in texts(cell.get("kids") or []))
            for i in range(r, min(r + int(cell.get("row span") or 1), rows)):
                for j in range(c + 1, min(c + int(cell.get("column span") or 1), cols)):
                    wide[i][j] = True
    return grid, wide


def heading_mark(title: str) -> str:
    """A heading the OCR found, as markdown: its depth from its number ('4' ##, '4.1' ###, deeper ####), not from the OCR's
    h2/h3/h4, which differ for headings of one level (chandra: '2.2' h2, '2.3' h3, '2.4' h4); one with no number ##."""
    m = re.match(r"(\d{1,2}(?:\.\d{1,2})*)\.?\s", title)
    return "#" * (min(m.group(1).count(".") + 2, 4) if m else 2) + " " + title


def text_of(doc: dict, known: frozenset[str] | set[str] | None = None, headings: bool = False) -> str:
    """The text of a document's JSON: a block of lines per heading, paragraph, item of a list, caption; a table as markdown.
    `known`: the words that decide a broken word (the documents' by default), beside the document's own. `headings`: its
    headings marked as markdown ('## 4 Процесс …'), to be taken as they are (chandra's: opendataloader's own take a page
    number, a line of a formula, half of a title for one), not guessed again from the numbers of the lines."""
    from catix.wiki.sources.regulations import table_markdown

    nodes = doc.get("kids") or []
    words = (corpus_words() if known is None else frozenset(known)) | words_in("\n".join(texts(nodes)))
    blocks: list[tuple[str, list[str]]] = []  # (kind, lines): "text", "table", or "head" (a page's head or foot)
    heads: set[str] = set()

    def add(content: str, kind: str = "text") -> None:
        lines = lines_of(content)
        if not lines:
            return
        last = next((b for b in reversed(blocks) if b[0] != "head"), None)  # past a page's foot and the next one's head
        if kind == "text" and last and last[0] == "text" and lines[0][:1].islower() and not LIST_MARK.match(lines[0]):
            last[1].extend(lines)  # a paragraph going on (on the next page, after a frame): the same block
        else:
            blocks.append((kind, lines))

    def walk(nodes: list[dict]) -> None:
        for node in nodes:
            kind = node.get("type")
            if kind == "table":
                blocks.append(("table", [table_markdown(*table_grid(node, words))]))
            elif kind == "list":
                for item in node.get("list items") or []:
                    lines = [item.get("content") or ""]  # the item with its paragraphs, a list or table in it where it stands
                    for kid in item.get("kids") or []:
                        if kid.get("type") in ("list", "table", "text block"):
                            add("\n".join(lines))
                            lines = []
                            walk([kid])
                        elif isinstance(kid.get("content"), str):
                            lines.append(kid["content"])
                    add("\n".join(lines))
            elif kind == "heading" and headings and isinstance(node.get("content"), str):
                if title := " ".join(lines_of(node["content"])):
                    blocks.append(("heading", [heading_mark(title)]))
            elif kind in ("heading", "paragraph", "caption") and isinstance(node.get("content"), str):
                add(node["content"])
            elif kind == "text block":
                walk(node.get("kids") or [])
            elif kind in ("header", "footer"):  # a page number, a running head again: not text; 'Приложение 2 к ...' is
                head = PAGE_IN_HEAD.sub("", "\n".join(texts(node.get("kids") or [])))
                key = " ".join(lines_of(head))
                if key and not PAGE_NUMBER.fullmatch(key) and key not in heads:
                    heads.add(key)
                    add(head, "head")

    walk(nodes)
    return "\n\n".join("\n".join(lines if kind == "table" else joined(lines, words)) for kind, lines in blocks if any(lines))
