"""A concept of the bundle cut into the pieces the agent's search returns.

Cut by meaning, in code: a heading starts a new piece, a regulation is cut at its numbered clauses (`**5.3.**`) and short
clauses are packed together up to MAX characters, a big table is cut by rows with its header repeated, a very long
paragraph by sentences. Every piece knows the headings above it and the clauses it holds, so that a search hit can be cited
as "п. 5.3" of its document. A guide's `[n]` references are resolved to the pages its `# Citations` section names, so that
the agent can cite the original and not the guide.

The text a piece is searched by (`search_text`) starts with the page title and the headings: "5.3. The term is ..." alone
says nothing about which regulation it belongs to.
"""

import hashlib
import re
from dataclasses import dataclass, field

from catix.wiki.compile import front_of
from catix.wiki.graph import split_front

SCHEME = "chunks-1"  # change it when the cutting rules change: every page is then cut again
MAX = 1200  # characters of a piece (about 300-400 tokens)
MIN = 300  # a smaller piece is packed with the next one of the same section

HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
CLAUSE = re.compile(r"^\*\*(\d{1,2}(?:\.\d{1,2}){0,4})\.?\*\*")  # the same form as synth.clauses
CITE = re.compile(r"\[(\d{1,3})\]")
LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
SENTENCE = re.compile(r"(?<=[.!?;])\s+")


@dataclass
class Chunk:
    seq: int
    heading: str  # the headings above it, "Chapter > Section"
    clauses: list[str]  # numbers of the clauses it holds, in order
    text: str
    cites: list[dict] = field(default_factory=list)  # for a guide: [{"n": 5, "title": ..., "href": ...}] of the [n] it uses

    @property
    def clause(self) -> str:
        """'5.3' or '5.3–5.5' or ''."""
        if not self.clauses:
            return ""
        return self.clauses[0] if len(self.clauses) == 1 else f"{self.clauses[0]}–{self.clauses[-1]}"

    def search_text(self, title: str) -> str:
        return "\n".join(p for p in (title, self.heading, self.text) if p)

    @property
    def sha(self) -> str:
        return hashlib.sha256(f"{self.heading}\n{self.text}".encode()).hexdigest()[:16]


def citations(body: str) -> tuple[str, dict[int, list[tuple[str, str]]]]:
    """The body without its `# Citations` section, and that section as number -> [(title, href)]."""
    m = re.search(r"^# Citations\s*$", body, re.M)
    if not m:
        return body, {}
    found: dict[int, list[tuple[str, str]]] = {}
    for line in body[m.end():].splitlines():
        if n := re.match(r"\s*(\d+)\.\s+(.*)", line):
            found[int(n.group(1))] = LINK.findall(n.group(2))
    return body[: m.start()], found


def blocks(body: str) -> list[tuple[str, str]]:
    """(kind, text) in order: 'heading' (text = '## Title'), 'table' (all its rows), 'para' (a paragraph or list)."""
    out: list[tuple[str, str]] = []
    para: list[str] = []
    table: list[str] = []

    def flush() -> None:
        if para:
            out.append(("para", "\n".join(para).strip()))
            para.clear()
        if table:
            out.append(("table", "\n".join(table)))
            table.clear()

    for line in body.splitlines():
        if HEADING.match(line):
            flush()
            out.append(("heading", line.strip()))
        elif line.lstrip().startswith("|"):
            if para:
                out.append(("para", "\n".join(para).strip()))
                para.clear()
            table.append(line.rstrip())
        elif not line.strip():
            flush()
        elif CLAUSE.match(line.strip()):  # a clause starts a new paragraph even without a blank line before it
            flush()
            para.append(line.rstrip())
        else:
            if table:
                out.append(("table", "\n".join(table)))
                table.clear()
            para.append(line.rstrip())
    flush()
    return [(k, t) for k, t in out if t]


def split_long(text: str) -> list[str]:
    """A paragraph longer than MAX in pieces at sentence ends (a sentence longer than MAX is cut hard)."""
    if len(text) <= MAX:
        return [text]
    parts, cur = [], ""
    for s in SENTENCE.split(text):
        while len(s) > MAX:
            if cur:
                parts.append(cur)
                cur = ""
            parts.append(s[:MAX])
            s = s[MAX:]
        if cur and len(cur) + 1 + len(s) > MAX:
            parts.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        parts.append(cur)
    return parts


def split_table(rows: str) -> list[str]:
    """A table longer than MAX in pieces of whole rows, each with the header (first two rows) repeated; a row longer than
    MAX on its own is cut by sentences, every part again under the header."""
    lines = rows.splitlines()
    if len(rows) <= MAX:
        return [rows]
    if len(lines) < 3 or not re.fullmatch(r"\|[\s:|-]+\|?", lines[1].strip()):
        return split_long(rows)
    head, out, cur = lines[:2], [], []
    room = MAX - len("\n".join(head)) - 1
    if room < MAX // 2:  # a header as long as a page (a table glued into one row): repeating it would not fit
        return split_long(rows)
    for line in lines[2:]:
        parts = split_long(line) if len(line) > room else [line]
        for part in parts:
            if cur and len("\n".join(head + cur + [part])) > MAX:
                out.append("\n".join(head + cur))
                cur = []
            cur.append(part)
    if cur:
        out.append("\n".join(head + cur))
    return out


def cut(text: str) -> tuple[dict, list[Chunk]]:
    """Front matter and the pieces of one concept file."""
    _, body = split_front(text)
    meta = front_of(text)
    body = re.sub(r"<!-- /?catix:relations -->", "", body)  # the relations block is plain text for the search: keep it, drop the markers
    body, refs = citations(body)
    path: list[tuple[int, str]] = []  # (level, title) of the headings above
    units: list[tuple[str, str, str, bool]] = []  # (heading, clause, text, continues a clause started before)
    clause = ""  # the clause the text belongs to: its list items and paragraphs follow it without a number
    for kind, block in blocks(body):
        if kind == "heading":
            m = HEADING.match(block)
            level, title = len(m.group(1)), m.group(2).strip()
            if level > 1:  # (the page title is already in every piece's search text)
                path = [(lv, t) for lv, t in path if lv < level] + [(level, title)]
            clause = ""
            continue
        heading = " > ".join(t for _, t in path)
        if num := CLAUSE.match(block):
            clause = num.group(1)
        pieces = split_table(block) if kind == "table" else split_long(block)
        for i, piece in enumerate(pieces):
            units.append((heading, clause, piece, bool(clause) and (i > 0 or not num)))
    chunks: list[Chunk] = []
    for heading, num, piece, continues in units:
        last = chunks[-1] if chunks else None
        tail = heading.rsplit(" > ", 1)[-1]
        joined = piece if not last or last.heading == heading or not tail else f"### {tail}\n\n{piece}"
        if last and len(last.text) + len(joined) + 2 <= MAX and (last.heading == heading or len(last.text) < MIN):
            # Pieces of one section are packed together; a small piece also takes the start of the next section, with its heading.
            last.text += "\n\n" + joined
            if num and num not in last.clauses:
                last.clauses.append(num)
            continue
        chunks.append(Chunk(len(chunks), heading, [num] if num else [], f"({num}) {piece}" if continues else piece))
    for c in chunks:
        used = sorted({int(n) for n in CITE.findall(c.text)})
        c.cites = [{"n": n, "title": t, "href": h} for n in used for t, h in refs.get(n, [])]
    return meta, chunks
