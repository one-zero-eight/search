"""Wikitext prose -> markdown, deterministically: headings, lists, bold/italic, links.

Done before the model sees the page, so it only cleans up and describes; left alone it sometimes copies the wiki markup as it is.
Tables are handled by tables.py and arrive here as tokens.
"""

import re

from catix.wiki.tables import inline

HEADING = re.compile(r"^(={1,6})\s*(.*?)\s*\1\s*$")
DROP = re.compile(r"^\s*(__[A-Z]+__|\[\[Category:[^\]]*\]\]|<references\s*/>|----+)\s*$", re.I)


def convert(text: str) -> str:
    text = re.sub(r"</?nowiki>", "", text)
    lines = text.splitlines()
    levels = [len(m.group(1)) for line in lines if (m := HEADING.match(line))]
    shift = 2 - min(levels) if levels else 0  # the program writes the H1 title, the page's top heading becomes H2
    out = []
    for line in lines:
        if DROP.match(line):
            continue
        if m := HEADING.match(line):
            out.append("#" * min(6, max(2, len(m.group(1)) + shift)) + " " + inline(m.group(2), cell=False))
            continue
        if m := re.match(r"^([*#]+)\s*(.*)$", line):
            marker = "-" if m.group(1)[-1] == "*" else "1."
            out.append("  " * (len(m.group(1)) - 1) + f"{marker} " + inline(m.group(2), cell=False))
            continue
        line = re.sub(r"^:+\s*", "", line)  # indentation of a paragraph
        out.append(inline(line, cell=False))
    return "\n".join(out)
