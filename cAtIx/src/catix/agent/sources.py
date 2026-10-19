"""Source citations built in code, because small models do not reliably name their sources.

Every question has its own registry of sources (`Registry`, kept in the AgentContext). A tool that finds a chat message
registers it and puts the ref it gets (m0, m1, ... in the order the messages reach the model) next to the message.
The model copies refs next to the facts it uses; `cite` then replaces them by [1], [2], ... and appends a source list.
Only refs of this question's registry are honoured, so a made-up or injected ref can neither leak a message nor
produce a fake source, and a source is described by its fields, not by a database row (a message found live in
Telegram has none).
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime

from catix.db import store
from catix.settings import settings

log = logging.getLogger("catix.sources")

# [m0], [m0, m1], [ m0 ; m1 ]
GROUP_RE = re.compile(r"\[\s*(m\d+(?:\s*[,;]\s*m\d+)*)\s*\]")
FORWARDER_RE = re.compile(r"\s*\(forwarded by .*\)$")
DB_REF_RE = re.compile(r"^m\d+$")
# Keys under which tools put refs; message texts cannot forge a key.
REF_KEYS = {"ref", "source_ref"}


@dataclass(frozen=True, slots=True)
class Source:
    """What a ref stands for: a stored message (`message_id`, the rest is read from the database) or a message found
    live (the rest is given here)."""

    message_id: int | None = None
    chat_title: str | None = None
    link: str | None = None
    date: datetime | None = None
    author: str | None = None
    sender_link: str | None = None


class Registry:
    """The sources of one question, numbered in the order they were registered."""

    def __init__(self) -> None:
        self.items: dict[str, Source] = {}
        self._by_key: dict[tuple, str] = {}

    def _add(self, key: tuple, source: Source) -> str:
        if key not in self._by_key:  # The same message found twice keeps its ref.
            self._by_key[key] = f"m{len(self.items)}"
            self.items[self._by_key[key]] = source
        return self._by_key[key]

    def add_db(self, message_id: int | None) -> str | None:
        return self._add(("db", message_id), Source(message_id=message_id)) if message_id else None

    def add_live(self, chat_id: int, msg_id: int, source: Source) -> str:
        return self._add(("live", chat_id, msg_id), source)

    def rewrite(self, value: object) -> object:
        """Tool output that carries database refs ('m5127', from the SQL views) with this question's refs."""
        if isinstance(value, dict):
            return {
                key: (self.add_db(int(item[1:])) if key in REF_KEYS and isinstance(item, str) and DB_REF_RE.match(item) else self.rewrite(item))
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self.rewrite(item) for item in value]
        return value


def cite(answer: str, registry: Registry) -> str:
    """Replace refs in the answer by numbers and append the numbered source list."""
    numbers: dict[str, int] = {}

    def renumber(match: re.Match) -> str:
        used: set[int] = set()
        for item in re.findall(r"m\d+", match.group(1)):
            if item in registry.items:
                used.add(numbers.setdefault(item, len(numbers) + 1))
            else:
                log.warning("dropping unknown source ref %s", item)
        return f"[{', '.join(map(str, sorted(used)))}]" if used else ""

    answer = GROUP_RE.sub(renumber, answer)
    answer = re.sub(r"[ \t]+([.,;:!?])", r"\1", answer)  # Where a dropped ref left a gap.
    if not numbers:
        return answer.strip()

    stored = store.message_sources([s.message_id for ref in numbers if (s := registry.items[ref]).message_id])
    lines = []
    for ref, number in numbers.items():
        source = registry.items[ref]
        if source.message_id:
            row = stored.get(source.message_id)
            if not row:
                continue
            source = Source(
                chat_title=row.chat_title, link=row.link or row.chat_link,  # The chat's own link when the message has none.
                date=row.date, author=row.sender_name, sender_link=row.sender_link,
            )
        lines.append(_line(number, source))
    if not lines:
        return answer.strip()
    title = "Источники" if re.search(r"[а-яё]", answer.lower()) else "Sources"
    return f"{answer.strip()}\n\n{title}:\n" + "\n".join(lines)


def _line(number: int, source: Source) -> str:
    when = source.date.astimezone(settings.tz) if source.date else None
    author = FORWARDER_RE.sub("", source.author or "")
    title = f"«{source.chat_title}»"
    if source.link:
        title = f"[{title.replace('[', '(').replace(']', ')')}]({source.link})"
    line = f"[{number}] {title}" + (f", {when:%d.%m.%Y}" if when else "")
    if author and source.sender_link:
        line += f", [{author.replace('[', '(').replace(']', ')')}]({source.sender_link})"
    elif author:
        line += f", {author}"
    return line
