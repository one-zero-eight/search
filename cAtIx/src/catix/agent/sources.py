"""Source citations built in code, because small models do not reliably name their sources.

Tools tag results that come from chat messages with a ref such as "m123" (the message's database rowid).
The model copies refs next to the facts it uses; `cite` then replaces them by [1], [2], ... and appends a
source list taken from the database. Only refs that tools returned in this conversation are honoured,
so a made-up or injected ref can neither leak a message nor produce a fake source.
"""

import json
import logging
import re

from langchain_core.messages import BaseMessage, ToolMessage

from catix.db import store
from catix.settings import settings

log = logging.getLogger("catix.sources")

REF_RE = re.compile(r"^m\d+$")
# [m12], [m12, m13], [ m12 ; m13 ]
GROUP_RE = re.compile(r"\[\s*(m\d+(?:\s*[,;]\s*m\d+)*)\s*\]")
FORWARDER_RE = re.compile(r"\s*\(forwarded by .*\)$")
# Keys under which tools put refs; message texts cannot forge a key.
REF_KEYS = {"ref", "source_ref"}


def ref(rowid: int | None) -> str | None:
    return f"m{rowid}" if rowid else None


def _collect(value: object, found: set[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in REF_KEYS and isinstance(item, str) and REF_RE.match(item):
                found.add(item)
            else:
                _collect(item, found)
    elif isinstance(value, list):
        for item in value:
            _collect(item, found)


def known_refs(messages: list[BaseMessage]) -> set[str]:
    """Refs that tools returned anywhere in the conversation (follow-ups may cite earlier results)."""
    found: set[str] = set()
    for message in messages:
        if isinstance(message, ToolMessage):
            try:
                _collect(json.loads(message.content), found)
            except (TypeError, json.JSONDecodeError):
                continue
    return found


def cite(answer: str, messages: list[BaseMessage]) -> str:
    """Replace refs in the answer by numbers and append the numbered source list."""
    known = known_refs(messages)
    numbers: dict[str, int] = {}

    def renumber(match: re.Match) -> str:
        used: set[int] = set()
        for item in re.findall(r"m\d+", match.group(1)):
            if item in known:
                used.add(numbers.setdefault(item, len(numbers) + 1))
            else:
                log.warning("dropping unknown source ref %s", item)
        return f"[{', '.join(map(str, sorted(used)))}]" if used else ""

    answer = GROUP_RE.sub(renumber, answer)
    answer = re.sub(r"[ \t]+([.,;:!?])", r"\1", answer)  # Where a dropped ref left a gap.
    if not numbers:
        return answer.strip()

    rows = store.message_sources([int(item[1:]) for item in numbers])

    lines = []
    for item, number in numbers.items():
        row = rows.get(int(item[1:]))
        if not row:
            continue
        when = row.date.astimezone(settings.tz)
        author = FORWARDER_RE.sub("", row.sender_name or "")
        title = f"«{row.chat_title}»"
        if link := row.link or row.chat_link:  # The chat's own link when the message has none.
            title = f"[{title.replace('[', '(').replace(']', ')')}]({link})"
        line = f"[{number}] {title}, {when:%d.%m.%Y}"
        if author and row.sender_link:
            line += f", [{author.replace('[', '(').replace(']', ')')}]({row.sender_link})"
        elif author:
            line += f", {author}"
        lines.append(line)
    if not lines:
        return answer.strip()
    title = "Источники" if re.search(r"[а-яё]", answer.lower()) else "Sources"
    return f"{answer.strip()}\n\n{title}:\n" + "\n".join(lines)
