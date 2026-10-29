"""Links between the cards of the bundle, written by code — the model cannot write them.

    catix-wiki agent links [--dry-run]      # the links of every card, and the names it left alone

The bundle is read by people: wiki/ is an Obsidian vault, and the readers of a card are helped most by the cards it should
lead to. The model cannot write these links: its task shows it the titles of the cards, not their aliases, and what it
invented were dangling links to cards that do not exist (136 of them, removed 2026-10-29). So the links are written here,
from a registry of the titles and aliases of the cards, deterministically: the same text gives the same links, and a
second run changes nothing.

Only cards are linked. A card is prose, not evidence, so a link inside it changes nothing that agent.problems() checks.
The source pages are evidence and nothing here touches them: a link inside a clause puts the words of its own address into
the word stream (agent.words_of), and the quotes of the cards that rest on that clause stop being found. A page that
should lead somewhere gets a block of its own, the way graph.py writes `## Relations`.

Rules, so that the reading stays quiet: one link to a card, at its first mention; the longest name wins, so "academic
leave" is linked and "leave" inside it is not; at most one link in a paragraph; nothing inside a heading, a link already
written, a quote of a document or its code; a name that two cards answer to is left alone and reported, because an alias
has to say which card is meant.
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from catix.wiki.compile import BUNDLE, front_of
from catix.wiki.graph import split_front

FOLDER = "knowledge"
WORD = re.compile(r"[^\W_]+", re.UNICODE)  # a word, however the text spells it
TAKEN = [re.compile(r"\[[^\]]*\]\([^)]*\)"),  # a link already written
         re.compile(r"`[^`]*`"),  # code
         re.compile(r"«[^»]*»"),  # a quote of a document: its words are not ours to link
         re.compile(r"^\s{0,3}#{1,6} .*$", re.M)]  # a heading, the title and the citations heading too
CITATIONS = "\n# Citations\n"
SEE_ALSO = "## See also"
MIN_WORDS = 2  # words of a name: a single word is taken only when it is distinctive by itself
MIN_KEY = 12  # characters of a single-word name ("administration" is a name, "leave" is not)
MAX_WORDS = 16  # words of a name: a longer one is a sentence, not a name
HEAD = re.compile(r"\s+[—–]\s+|\s*[(«:]")  # a title is a name and, after this, its explanation


@dataclass
class Card:
    """A card as a reader meets it: its slug, the names a link may rest on, and the whole file."""

    slug: str
    title: str
    keys: list[str]
    text: str


@dataclass
class Written:
    """What one card got: the links written into it, and the names that were left alone."""

    slug: str
    links: list[tuple[str, str]] = field(default_factory=list)  # (the words as the card has them, the slug they lead to)
    ambiguous: list[str] = field(default_factory=list)


def norm(text: str) -> str:
    """A name or a phrase, as they are compared: lower case, ё as е, words only."""
    return " ".join(WORD.findall(text.lower().replace("ё", "е")))


def keys_of(meta: dict) -> list[str]:
    """The names of a card that may be linked: its title and its aliases, and the name at the head of a long title.

    A title like "Documents on additional education (ДПО and ДОП) — types, blank forms" is a name followed by its
    explanation; a card of another subject mentions the name ("documents on additional education"), never the whole
    sentence, so the part before the dash or the bracket is a name here too. What follows explains the card and is not
    linked to: it is prose, and pieces of it ("for bachelor programmes") name other cards by accident.
    """
    keys = [str(meta.get("title", "")), *[str(a) for a in meta.get("aliases") or []]]
    out: list[str] = []
    for key in keys:
        for part in [key, HEAD.split(key)[0]]:
            name = norm(part)
            if not name or len(name.split()) > MAX_WORDS:
                continue
            if (len(name.split()) >= MIN_WORDS or len(name) >= MIN_KEY) and name not in out:
                out.append(name)
    return out


def read_cards(bundle: Path = BUNDLE) -> list[Card]:
    """Every card of the bundle, with the names a link may rest on."""
    cards = []
    for path in sorted((bundle / FOLDER).glob("*.md")):
        if path.name == "index.md":
            continue
        text = path.read_text(encoding="utf-8")
        cards.append(Card(path.stem, str(front_of(text).get("title", "")), keys_of(front_of(text)), text))
    return cards


def registry(cards: list[Card]) -> tuple[dict[str, str], set[str]]:
    """Name -> the slug it leads to, and the names two cards answer to (they are not linked until an alias says which)."""
    names: dict[str, str] = {}
    ambiguous: set[str] = set()
    for card in cards:
        for name in card.keys:
            if (there := names.get(name)) and there != card.slug:
                ambiguous.add(name)
            else:
                names[name] = card.slug
    return {n: s for n, s in names.items() if n not in ambiguous}, ambiguous


def frozen_spans(text: str) -> list[tuple[int, int]]:
    """What is not a place for a link at all (a heading, a quote, code) — a link already written is not among them.

    It has to be told apart from a link already written, or the pass is not the same twice: a mention inside a link is
    "this card already leads there" (nothing to write), while the same mention under a heading is "not here", and the plan
    of where the links go must not depend on the links of the run before (that is what made a second run move them).
    """
    return [m.span() for pattern in TAKEN[1:] for m in pattern.finditer(text)]


def linked_spans(text: str) -> list[tuple[int, int]]:
    """The links already written in the text (the model's, or an earlier pass of this one)."""
    return [m.span() for m in TAKEN[0].finditer(text)]


def inside(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    return any(span[0] < end and start < span[1] for start, end in spans)


def words_of(text: str) -> list[tuple[int, int]]:
    return [m.span() for m in WORD.finditer(text)]


def paragraphs(text: str) -> list[int]:
    """For every character, the number of its paragraph (a blank line apart)."""
    where, out, at = 0, [0] * len(text), 0
    for m in re.finditer(r"\n\s*\n", text):
        out[where:m.end()] = [at] * (m.end() - where)
        where, at = m.end(), at + 1
    out[where:] = [at] * (len(text) - where)
    return out


def see_also_of(text: str) -> tuple[str, list[str]]:
    """A card without its `## See also` section, and the cards that section led to (they are written again below)."""
    if SEE_ALSO not in text:
        return text, []
    head, rest = text.split(SEE_ALSO, 1)
    section, _, tail = rest.partition("\n# ")
    return head.rstrip("\n") + "\n" + (f"\n# {tail}" if tail else ""), [m.group(2) for m in re.finditer(r"\[([^\]]*)\]\(/knowledge/([^)\s]+)\.md\)", rest)]


def write_see_also(text: str, cards: dict[str, str], also: list[str]) -> str:
    """The links this card leads to, as the `## See also` section: the cards its text names, and the ones it named before."""
    body, _, cites = text.partition(CITATIONS)
    leading = [m.group(2) for m in re.finditer(r"\[([^\]]*)\]\(/knowledge/([^)\s]+)\.md\)", body)]
    targets = [s for s in dict.fromkeys([*leading, *also]) if s in cards]
    if not targets:
        return text
    lines = "\n".join(f"- [{cards[s]}](/knowledge/{s}.md)" for s in sorted(targets, key=lambda s: cards[s].lower()))
    return f"{body.rstrip(chr(10))}\n\n{SEE_ALSO}\n\n{lines}\n\n{CITATIONS}{cites}"


def link_card(card: Card, names: dict[str, str], ambiguous: set[str], cards: dict[str, str]) -> tuple[str, Written]:
    """One card with its links written: the first mention of every name, the longest name first, one to a paragraph.

    The front matter is never touched — a tag or a title is not a sentence a reader follows — and neither are the
    citations (code writes them, and they name pages, not cards). A name two cards answer to is not linked: the report
    says which names those are, and an alias settles it.
    """
    written = Written(card.slug)
    front, rest = split_front(card.text)
    body, _, cites = rest.partition(CITATIONS)
    body, also = see_also_of(body)
    frozen, there, words, paras = frozen_spans(body), linked_spans(body), words_of(body), paragraphs(body)
    planned = set()  # the paragraph of every link this pass plans: the plan must not depend on what was written before
    linked: set[str] = set()
    places: list[tuple[int, int, str, str, bool]] = []  # (start, end, the words as the card has them, slug, already there)
    for name in sorted(names, key=lambda n: (-len(n.split()), n)):  # the longest name first, then by name: the same twice
        slug = names[name]
        if slug == card.slug or slug in linked:
            continue
        if name in ambiguous:
            written.ambiguous.append(name)
            continue
        want = name.split()
        for i in range(len(words) - len(want) + 1):
            span = (words[i][0], words[i + len(want) - 1][1])
            if [norm(body[start:end]) for start, end in words[i:i + len(want)]] != want:
                continue
            if inside(span, frozen) or inside(span, [(p[0], p[1]) for p in places]):
                continue
            if paras[span[0]] in planned:  # one link a paragraph: the reading stays quiet
                continue
            linked.add(slug)
            planned.add(paras[span[0]])
            places.append((span[0], span[1], body[span[0]:span[1]], slug, inside(span, there)))
            break
    for start, end, said, slug, done in sorted(places, reverse=True):  # from the last to the first: the places stay valid
        if done:  # a link written before (the model's, or the run before): nothing to write here
            continue
        body = f"{body[:start]}[{said}](/knowledge/{slug}.md){body[end:]}"
        written.links.append((said, slug))
    text = front + write_see_also(body + CITATIONS + cites, cards, also)
    return text, written


def cards_by_slug(cards: list[Card]) -> dict[str, str]:
    """Slug -> the title a reader sees in a link."""
    return {c.slug: c.title for c in cards}


@dataclass
class Report:
    """What a pass over the cards did: the links written, and the names it left alone."""

    cards: int = 0
    names: int = 0  # names in the registry
    links: int = 0
    cards_linked: int = 0
    ambiguous: list[str] = field(default_factory=list)  # names two cards answer to
    cards_with_an_ambiguity: int = 0
    changed: list[str] = field(default_factory=list)  # cards whose file the pass rewrites


def apply(bundle: Path = BUNDLE, dry_run: bool = False) -> Report:
    """Every card with the links between it and the cards it speaks of; with `dry_run` nothing is written."""
    cards = read_cards(bundle)
    names, ambiguous = registry(cards)
    titles = cards_by_slug(cards)
    report = Report(cards=len(cards), names=len(names), ambiguous=sorted(ambiguous))
    for card in cards:
        text, written = link_card(card, names, ambiguous, titles)
        if written.links:
            report.cards_linked += 1
            report.links += len(written.links)
        if written.ambiguous:
            report.cards_with_an_ambiguity += 1
        if text != card.text:
            report.changed.append(card.slug)
            if not dry_run:
                (bundle / FOLDER / f"{card.slug}.md").write_text(text, encoding="utf-8")
    return report


def main() -> None:
    report = apply(dry_run="--dry-run" in sys.argv[2:])
    print(f"{report.links} links between cards: {report.cards_linked} of {report.cards} cards link to another one "
          f"({report.names} names in the registry; {len(report.changed)} files rewritten)")
    if report.ambiguous:
        print(f"{len(report.ambiguous)} names two cards answer to (an alias settles them): " + ", ".join(report.ambiguous[:12]))


if __name__ == "__main__":
    main()
