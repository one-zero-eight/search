"""Structured, backend-numbered citations and their terminal Markdown presentation.

The answer carries numeric references; sources carry provenance separately. API consumers
must not parse a rendered bibliography to recover these fields.
"""

import re
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field

from catix.settings import settings


class ArchiveDocument(BaseModel):
    page: str
    revision: str
    member: str


class CitationLink(BaseModel):
    title: str
    url: str | None = None


class SourceImage(BaseModel):
    url: str
    alt: str | None = None


# A picture of a crawled site page as its markdown keeps it (docs/sources/sites.py _Page._picture: absolute, no spaces or brackets).
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\((https?://[^)\s]+)\)")
MAX_CHUNK_IMAGES = 4  # pictures one cited piece adds to its source
MAX_SOURCE_IMAGES = 6  # pictures one line of the source list shows


def images_in(text: str, limit: int = MAX_CHUNK_IMAGES) -> list[dict]:
    """The pictures of a piece's markdown, first `limit`, each URL once: [{"url", "alt"}], alt None when empty."""
    found: list[dict] = []
    for match in IMAGE_RE.finditer(text):
        if len(found) >= limit:
            break
        if all(item["url"] != match.group(2) for item in found):
            found.append({"url": match.group(2), "alt": match.group(1).strip() or None})
    return found


class AnswerSource(BaseModel):
    number: int
    title: str
    url: str | None = None
    kind: Literal["official_document", "guide", "eduwiki", "website", "web", "moodle", "chat"]
    clauses: list[str] = Field(default_factory=list)
    sections: list[str] = Field(default_factory=list)
    based_on: list[CitationLink] = Field(default_factory=list)
    archive_document: ArchiveDocument | None = None
    date: datetime | None = None
    author: str | None = None
    author_url: str | None = None
    text: str | None = None  # the cited chat message (kind `chat`), for its preview on the site
    images: list[SourceImage] = Field(default_factory=list)  # pictures of the cited pieces of a site page, for the site's source list
    official: bool = False


class CitedAnswer(BaseModel):
    answer: str
    sources: list[AnswerSource] = Field(default_factory=list)


def _link(title: str, url: str | None) -> str:
    title = f"«{title.replace('[', '(').replace(']', ')')}»"
    return f"[{title}]({url})" if url else title


def _place(source: AnswerSource) -> str:
    if source.clauses:
        return f", п. {', '.join(source.clauses)}"
    if source.kind == "guide":
        return ""
    shown = []
    for section in source.sections:
        section = re.sub(r"\s+", " ", section).strip(" :.#").replace("[", "(").replace("]", ")")
        if section and section != source.title and section not in shown:
            shown.append(section if len(section) <= 90 else section[:90].rstrip() + "…")
    if not shown:
        return ""
    return (", разделы " if len(shown) > 1 else ", раздел ") + ", ".join(f"«{section}»" for section in shown[:3])


def render_cited_answer(result: CitedAnswer) -> str:
    """Render the structured answer for terminal clients, preserving source provenance."""
    if not result.sources:
        return result.answer
    lines = []
    for source in result.sources:
        line = f"[{source.number}] {_link(source.title, source.url)}"
        if source.kind == "chat":
            if source.official:
                line += " (официальный чат)"
            if source.date:
                line += f", {source.date.astimezone(settings.tz):%d.%m.%Y}"
            if source.author:
                author = source.author.replace("[", "(").replace("]", ")")
                line += f", [{author}]({source.author_url})" if source.author_url else f", {author}"
        else:
            line += _place(source)
            if source.kind == "official_document":
                line += " (документ университета)"
            elif source.kind == "guide":
                based = ", ".join(_link(item.title, item.url) for item in source.based_on)
                line += " (сводка cAtIx" + (f" по документам: {based})" if based else ")")
            elif source.kind == "moodle":
                line += " (Moodle)"
            elif source.kind in {"website", "web"}:
                host = (urlsplit(source.url or "").hostname or "").removeprefix("www.")
                if source.kind == "website" or source.official:
                    where = host or "сайт"
                else:
                    where = f"{host}, из интернета" if host else "из интернета"
                line += f" ({where})"
            else:
                line += " (eduwiki)"
        lines.append(line)
    heading = "Источники" if re.search(r"[а-яё]", result.answer.lower()) else "Sources"
    return f"{result.answer.strip()}\n\n{heading}:\n" + "\n".join(lines)
