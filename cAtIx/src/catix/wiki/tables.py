"""MediaWiki tables ({| ... |}) -> markdown tables, deterministically.

The model garbles big tables with rowspan/colspan (cells slip to the wrong row) and loops on long ones, so tables never
reach it: `extract` swaps each table for a `@@TABLE_n@@` token and returns the finished markdown separately.
A spanned cell is repeated in every row/column it covers, so each row can be read (and found by search) on its own.
"""

import re

_ATTR_SPAN = re.compile(r'(rowspan|colspan)\s*=\s*"?(\d+)"?', re.I)
TOKEN = "@@TABLE_{}@@"


def inline(text: str, cell: bool = True) -> str:
    """Wiki inline markup -> markdown (links keep the wiki: scheme, resolved later by compile.link). cell=False: running text, not a table cell."""
    t = re.sub(r"\[\[(?:File|Image|Category):[^\]]*\]\]", "", text, flags=re.I)
    t = re.sub(r"\[\[([^\]|]+)\|([^\]]*)\]\]", lambda m: f"[{m.group(2).strip()}](wiki:{m.group(1).strip()})", t)
    t = re.sub(r"\[\[([^\]]+)\]\]", lambda m: f"[{m.group(1).strip()}](wiki:{m.group(1).strip()})", t)
    t = re.sub(r"\[((?:https?|mailto):[^\s\]]+)\s+([^\]]+)\]", r"[\2](\1)", t)
    t = re.sub(r"\[((?:https?|mailto):[^\s\]]+)\]", r"<\1>", t)
    t = re.sub(r"'''(.+?)'''", r"**\1**", t)
    t = re.sub(r"''(.+?)''", r"*\1*", t)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</?(?:span|div|font|small|big|center|u|s|sup|sub|p)\b[^>]*>", "", t, flags=re.I)
    t = re.sub(r"\{\{[^{}]*\}\}", "", t)
    t = t.replace("&nbsp;", " ")
    if not cell:
        return t
    t = t.replace("|", "\\|")
    return " <br> ".join(p.strip() for p in t.split("\n") if p.strip())


def _split_cell(raw: str) -> tuple[dict, str]:
    """'attrs | content' -> (attrs, content); a pipe inside a link or without attributes is content."""
    if "|" in raw and "[[" not in raw.split("|", 1)[0] and not raw.lstrip().startswith("[["):
        head, content = raw.split("|", 1)
        if "=" in head or not head.strip():
            return {k.lower(): int(v) for k, v in _ATTR_SPAN.findall(head)}, content
    return {}, raw


def _rows(body: str) -> tuple[str, list[list[tuple[bool, dict, str]]]]:
    caption, rows, row = "", [], None
    depth = 0
    cell_lines: list[str] = []

    def flush_cell():
        nonlocal cell_lines
        cell_lines = []

    for line in body.splitlines():
        s = line.strip()
        if s.startswith("{|"):
            depth += 1
        if depth > 1:  # a nested table stays inside its cell as plain text
            if row is not None and row:
                row[-1] = (row[-1][0], row[-1][1], row[-1][2] + "\n" + line)
            if s.startswith("|}"):
                depth -= 1
            continue
        if s.startswith("|+"):
            caption = inline(s[2:])
        elif s.startswith("|-"):
            row = []
            rows.append(row)
        elif s.startswith("!") or s.startswith("|"):
            if row is None:
                row = []
                rows.append(row)
            header = s.startswith("!")
            parts = re.split(r"!!|\|\|" if header else r"\|\|", s[1:]) if not header else re.split(r"!!|\|\|", s[1:])
            for p in parts:
                attrs, content = _split_cell(p)
                row.append((header, attrs, content.strip()))
        elif row:  # continuation line of the last cell
            row[-1] = (row[-1][0], row[-1][1], row[-1][2] + "\n" + line)
    return caption, [r for r in rows if r]


def to_markdown(table: str) -> str:
    inner = table.strip()[2:]
    inner = inner[: inner.rfind("|}")] if "|}" in inner else inner
    caption, rows = _rows(inner.partition("\n")[2])  # the first line holds only the table's attributes
    grid: list[list[str | None]] = []
    header_rows = 0
    for r, row in enumerate(rows):
        while len(grid) <= r:
            grid.append([])
        c = 0
        for is_header, attrs, content in row:
            while c < len(grid[r]) and grid[r][c] is not None:
                c += 1
            text = inline(content)
            for dr in range(attrs.get("rowspan", 1)):
                while len(grid) <= r + dr:
                    grid.append([])
                for dc in range(attrs.get("colspan", 1)):
                    line = grid[r + dr]
                    while len(line) <= c + dc:
                        line.append(None)
                    line[c + dc] = text
            c += attrs.get("colspan", 1)
        if all(h for h, _, _ in row) and header_rows == r:
            header_rows += 1
    width = max((len(r) for r in grid), default=0)
    grid = [[(cell or "") for cell in r + [None] * (width - len(r))] for r in grid]
    grid = [r for r in grid if any(r)]  # rows without any text
    keep = [i for i in range(width) if any(r[i] for r in grid)]  # columns without any text
    grid = [[r[i] for i in keep] for r in grid]
    if not grid:
        return ""
    header_rows = max(1, min(header_rows, len(grid) - 1 if len(grid) > 1 else 1))
    header = [" / ".join(dict.fromkeys(x for x in col if x)) for col in zip(*grid[:header_rows])]
    lines = ["| " + " | ".join(header) + " |", "|" + " --- |" * len(header)]
    lines += ["| " + " | ".join(r) + " |" for r in grid[header_rows:]]
    return (f"**{caption}**\n\n" if caption else "") + "\n".join(lines)


def extract(wikitext: str) -> tuple[str, list[str]]:
    """Wikitext without tables (each replaced by a token on its own line) and the markdown of the tables."""
    out, tables, table, depth = [], [], [], 0
    wikitext = re.sub(r"<!--.*?-->", "", wikitext, flags=re.S)  # commented-out tables are not content
    for line in wikitext.splitlines():
        s = line.strip()
        if s.startswith("{|"):
            depth += 1
        if depth:
            table.append(line)
            if s.startswith("|}"):
                depth -= 1
                if depth == 0:
                    md = to_markdown("\n".join(table))
                    if md:
                        out.append(TOKEN.format(len(tables)))
                        tables.append(md)
                    table = []
        else:
            out.append(line)
    if table and (md := to_markdown("\n".join(table))):  # a table the editors never closed
        out.append(TOKEN.format(len(tables)))
        tables.append(md)
    return "\n".join(out), tables
