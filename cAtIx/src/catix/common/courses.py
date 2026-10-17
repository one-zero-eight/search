"""Course glossary from courses.toml: canonical short names and the slang students use."""

import difflib
import re
import tomllib
from dataclasses import dataclass
from functools import cache

from catix.settings import settings


@dataclass(frozen=True)
class Course:
    short: str
    name: str
    aliases: tuple[str, ...]


@cache
def courses() -> tuple[Course, ...]:
    if not settings.courses_file.exists():
        return ()
    data = tomllib.loads(settings.courses_file.read_text(encoding="utf-8"))
    return tuple(
        Course(short=c["short"], name=c["name"], aliases=tuple(a.lower() for a in c.get("aliases", [])))
        for c in data.get("course", [])
    )


def normalize(value: str | None) -> str | None:
    """Map any known spelling to the canonical short name; unknown names are kept as is."""
    if not value:
        return None
    key = value.strip().lower()
    for course in courses():
        if key in (course.short.lower(), course.name.lower(), *course.aliases):
            return course.short
    return value.strip()


def _pattern(alias: str) -> str:
    # Two letters ("dm", "ma") must be a whole word; three ("итп") may take an ending ("итпшка"); longer ones match
    # inflected forms by their stem ("дискретка" -> "дискретке", "матан" -> "матану").
    if len(alias) <= 2:
        return rf"(?<!\w){re.escape(alias)}(?!\w)"
    if len(alias) == 3:
        return rf"(?<!\w){re.escape(alias)}"
    return rf"(?<!\w){re.escape(alias[:-1])}"


def mentioned(short: str, text: str) -> bool:
    """Whether the text names the course by any of its names (hashtags included)."""
    course = next((c for c in courses() if c.short == short), None)
    names = (course.short.lower(), course.name.lower(), *course.aliases) if course else (short.lower(),)
    lowered = text.lower()
    return any(re.search(_pattern(name), lowered) for name in names)


MIN_TYPO_LEN = 5  # Shorter words are never matched by closeness: "диск" is not "дискра".
TYPO_SIMILARITY = 0.85
MAX_HINTS = 3


def hints(text: str) -> list[Course]:
    """Courses the text names, by any known spelling, inflected form (stem) or a close misspelling of a name."""
    words = [w for w in re.findall(r"\w+", text.lower()) if len(w) >= MIN_TYPO_LEN]
    found: list[Course] = []
    for course in courses():
        names = (course.short.lower(), course.name.lower(), *course.aliases)
        close = any(
            difflib.SequenceMatcher(None, word, name).ratio() >= TYPO_SIMILARITY for word in words for name in names if " " not in name
        )
        if close or mentioned(course.short, text):
            found.append(course)
    return found[:MAX_HINTS]


def hint_line(text: str) -> str:
    """One line for the prompt about the subjects the text names, or an empty string."""
    found = hints(text)
    if not found:
        return ""
    parts = [f"{c.short} = {c.name} (also called: {', '.join(c.aliases)})" for c in found]
    return "Subjects the question may refer to, decoded from abbreviations: " + "; ".join(parts) + ".\n"


MIN_EXPANSION_LEN = 3  # "ca", "ma", "dm" as search words would match half of the chat history.


def expand_query(query: str) -> str:
    """Add the one-word aliases of every course the query names to the query.

    Students write "компарч", the model searches "компарх"; both are aliases of the same course.
    """
    extra: list[str] = []
    for course in courses():
        if mentioned(course.short, query):
            extra += [a for a in (course.short.lower(), *course.aliases) if " " not in a and len(a) >= MIN_EXPANSION_LEN]
    return f"{query} {' '.join(dict.fromkeys(extra))}" if extra else query
