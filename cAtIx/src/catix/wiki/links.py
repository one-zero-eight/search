"""Links between the cards of the bundle, written by code — the model cannot write them.

    catix-wiki agent links [--dry-run]      # the links of every card, and the names it left alone
    catix-wiki agent candidates [--phrases] # what the cards name that no artifact answers: the cards still to write

The report ranks, it does not decide. What it tells apart by itself: a phrase the bundle already answers to under another
name (an alias to add to that card or page), a phrase the cards of two and more cards name while two and more documents
speak of it (the evidence a card would have), and the rest. What it cannot tell apart is a subject of the university from
an outside body or a law ("Labour Code", "Ministry of Science") and from a turn of a sentence the model wrote twice
("university ensures"): a model or a person reads the list and says which is which. Measured on the 66 cards of 2026-10-29,
the strict pass gives 181 phrases of 3139 before the filters, of which the useful reading is the head of the list.

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

import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from catix.wiki.compile import BUNDLE, front_of
from catix.wiki.graph import split_front
from catix.wiki.paths import DATA

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


# ---- what the cards name that no artifact answers: the criterion for a card ----

NOISE = {  # a word a name does not begin with, and a word that carries no subject (a phrase of them names nothing)
    "the", "a", "an", "this", "these", "those", "their", "its", "his", "her", "our", "your", "such", "some", "any",
    "what", "when", "where", "which", "who", "whom", "whose", "how", "why", "if", "and", "or", "but", "for", "from",
    "with", "without", "within", "in", "into", "on", "at", "to", "of", "by", "as", "is", "are", "was", "were", "be",
    "been", "not", "may", "must", "shall", "can", "does", "do", "has", "have", "had", "under", "over", "after",
    "before", "during", "until", "also", "then", "than", "that", "it", "they", "we", "you", "he", "she", "one", "two",
    "three", "more", "most", "other", "others", "each", "both", "same", "only", "about", "according", "и", "или", "в",
    "во", "на", "по", "от", "до", "из", "за", "для", "при", "о", "об", "со", "к", "ко", "с", "не", "что", "как", "кто",
    "где", "когда", "если", "это", "эти", "тот", "та", "те", "их", "его", "ее", "её", "свой", "также", "либо", "лишь",
    "только", "таких", "такой", "такая", "данного", "данной", "данные", "указанных", "быть", "может", "должен", "все",
}
LABEL = re.compile(r"\d|_|[/|]")  # a number, an underscore or a table bar: a label the extraction printed, not a name
CAPITAL = re.compile(r"^[A-ZА-ЯЁ]")
CANDIDATE_WORDS = (3, 2)  # a subject is named by two or three words in a row ("Director for Development and HR")
MIN_CARDS = 2  # cards a phrase must be named in to be looked at: what one card says once is that card's own phrasing
MIN_PAGES = 2  # documents those cards rest on (a card rests on more than one page: SOURCES)
COMMON = 0.35  # a word of the genre, named in this share of the cards ("education", "programme"): a phrase of them
# names the corpus itself, not a subject ("higher education", "federal law", "educational activity")
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")  # a phrase does not run across two sentences
RUN = re.compile(r"[^\W_]+(?: [^\W_]+)*")  # words joined by single spaces: a name holds no comma or bracket inside


@dataclass
class Candidate:
    """A phrase the cards name, and what the bundle has for it."""

    phrase: str
    cards: list[str]  # the cards that name it
    pages: list[str]  # the documents those cards rest on (the evidence a card of it would have)
    verdict: str  # 'alias': an artifact answers to another name | 'card': two documents and more | 'mention': one
    artifact: str = ""  # the path of the artifact an alias would be added to
    example: str = ""  # the sentence it was met in


@dataclass
class Candidates:
    """The report: what the cards name that no card answers, by how much evidence there would be for it."""

    phrases: int = 0  # phrases the cards name in two cards and more
    items: list[Candidate] = field(default_factory=list)
    by_verdict: dict[str, int] = field(default_factory=dict)
    output: str = ""


def readable(text: str) -> str:
    """What of a card may name a subject: its prose alone — no front matter, no citations, no machine sections, and
    nothing already marked as not ours (a link, code, a quote of a document, a heading)."""
    rest = text
    if text.startswith("---\n") and "\n---\n" in text:
        _, rest = split_front(text)
    body = rest.partition(CITATIONS)[0]
    body, _ = see_also_of(body)
    for pattern in TAKEN:
        body = pattern.sub(" ", body)
    return body


def phrases_of(text: str, common: set[str] | None = None, named_only: bool = True) -> set[str]:
    """The phrases of a text that a card could be about (see Candidate): two and three words, still readable.

    A phrase that begins or ends in a word carrying no subject is a piece of a sentence, not a name; one holding a
    number, an underscore or a one-letter token ("University's" is "University" and "s") is not a name either; a word in
    capitals is the head of a document as the extraction printed it ("ПРОГРАММАМ"). `common` is the words of the genre
    (named in COMMON of the cards): a phrase of them alone names the corpus, not a subject. With `named_only` only a
    phrase that begins with a capital is taken — a name — else every repeated phrase of content words is (Russian names
    a subject without capitals, but that pass reads a lot of prose to find a few).
    """
    words_by_sentence = [[word for word in run.split()] for sentence in SENTENCE.split(text) for run in RUN.findall(sentence)]
    common = common or set()
    out = set()
    for words in words_by_sentence:  # a name runs without punctuation: "Federation the Labour" is two names and a comma
        for size in CANDIDATE_WORDS:
            for i in range(len(words) - size + 1):
                tokens = words[i:i + size]
                if any(len(t) < 2 or LABEL.search(t) or (t.isupper() and len(t) > 1) for t in tokens):
                    continue
                if tokens[0].lower() in NOISE or tokens[-1].lower() in NOISE:
                    continue
                if sum(1 for t in tokens if t.lower() in NOISE) > 1:  # "Director for Development", not "as for the"
                    continue
                substantive = [t.lower() for t in tokens if t.lower() not in NOISE]
                if len(substantive) < 2 or all(t in common for t in substantive):
                    continue
                caps = sum(1 for t in tokens if CAPITAL.match(t))
                if named_only and not (caps >= 2 or (caps == 1 and i > 0)):
                    # a name, not the first word of a sentence: "Interim assessment evaluates the work" is prose
                    continue
                out.add(" ".join(tokens))
    return out


def common_words(cards: list[Card], share: float = COMMON) -> set[str]:
    """The words of the genre: a word named in this share of the cards belongs to how the corpus speaks, not to a subject."""
    seen: dict[str, int] = defaultdict(int)
    for card in cards:
        for word in {w.lower() for w in WORD.findall(readable(card.text))}:
            seen[word] += 1
    return {word for word, n in seen.items() if n >= share * len(cards)}


def rests_on(text: str) -> list[str]:
    """The pages a card rests on: the sources of its citations."""
    cites = text.partition(CITATIONS)[2]
    return list(dict.fromkeys(re.findall(r"^\s*\d+\.\s+\[[^\]]*\]\((/[^)\s#]+\.md)\)", cites, re.M)))


def sentence_of(text: str, phrase: str) -> str:
    """The sentence a phrase was met in, for the report: a person reading it decides in a second what it means."""
    at = text.lower().find(phrase.lower())
    if at < 0:
        return ""
    before = [text.rfind(end, 0, at) for end in ".!?\n"]
    end = [found for found in (text.find(stop, at) for stop in ".!?\n") if found >= 0]
    start = max(before) + 1 if max(before) >= 0 else 0
    return " ".join(text[start:end[0] + 1 if end else len(text)].split())[:200]


def page_names(bundle: Path = BUNDLE) -> dict[str, str]:
    """Every concept of the bundle by a name a reader may follow to it (its title and its aliases) -> its path.

    A phrase the bundle already answers to, under another name, is an alias to add, not a card to write: the cards are in
    here too, so the report tells the two apart.
    """
    names: dict[str, str] = {}
    for path in sorted(bundle.rglob("*.md")):
        if any(part.startswith(".") for part in path.relative_to(bundle).parts):
            continue
        meta = front_of(path.read_text(encoding="utf-8"))
        for key in [str(meta.get("title", "")), *[str(a) for a in meta.get("aliases") or []]]:
            for part in [key, HEAD.split(key)[0]]:  # a title that explains itself names the artifact by its head
                name = norm(part)
                if len(name.split()) >= MIN_WORDS or len(name) >= MIN_KEY:
                    names.setdefault(name, "/" + path.relative_to(bundle).as_posix())
    return names


def candidates(bundle: Path = BUNDLE, output: Path | None = None, named_only: bool = True) -> Candidates:
    """The phrases the cards name that no card answers, with the evidence a card of each would have.

    The criterion this report is: a subject deserves a card when the cards themselves name it (two and more cards, so a
    reader arrives at it from both sides) and two and more documents speak of it (SOURCES: a card rests on more than one
    page). A phrase the bundle answers to already — the title or an alias of some page or card — is an alias to add to
    that artifact instead, and is reported as one. Nothing here writes anything: a person (or the agent, told to) decides.
    """
    cards = read_cards(bundle)
    names, _ = registry(cards)
    artifacts = {**page_names(bundle), **names}
    common = common_words(cards)
    met: dict[str, set[str]] = defaultdict(set)
    rests: dict[str, set[str]] = defaultdict(set)
    example: dict[str, str] = {}
    for card in cards:
        text = readable(card.text)
        pages = set(rests_on(card.text))
        for phrase in phrases_of(text, common, named_only):
            key = norm(phrase)
            met[key].add(card.slug)
            rests[key] |= pages
            example.setdefault(key, sentence_of(text, phrase))
    report = Candidates(phrases=sum(1 for slugs in met.values() if len(slugs) >= MIN_CARDS))
    order = {"alias": 0, "card": 1, "mention": 2}
    for key, slugs in met.items():
        if len(slugs) < MIN_CARDS:
            continue
        artifact = artifacts.get(key) or next((path for name, path in artifacts.items() if name in key), "")
        verdict = "alias" if artifact else ("card" if len(rests[key]) >= MIN_PAGES else "mention")
        report.items.append(Candidate(key, sorted(slugs), sorted(rests[key]), verdict, artifact, example.get(key, "")))
        report.by_verdict[verdict] = report.by_verdict.get(verdict, 0) + 1
    # the order a reader works in: what an alias settles today, then what a card would have the evidence for, then the rest
    report.items.sort(key=lambda c: (order[c.verdict], -len(c.pages), -len(c.cards), c.phrase))
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps([c.__dict__ for c in report.items], ensure_ascii=False, indent=1), encoding="utf-8")
        report.output = str(output)
    return report


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
    args = sys.argv[2:]
    if "candidates" in args:
        output = Path(args[args.index("--output") + 1]) if "--output" in args else DATA / ".knowledge-candidates.json"
        found = candidates(output=output, named_only="--phrases" not in args)
        counts = ", ".join(f"{n} {v}" for v, n in sorted(found.by_verdict.items(), key=lambda kv: -kv[1]))
        print(f"{found.phrases} phrases the cards name in two cards and more: {counts or 'nothing'}")
        print("an alias settles these (the artifact already answers to another name):")
        for item in [i for i in found.items if i.verdict == "alias"][:12]:
            print(f"  {item.phrase} -> {item.artifact}")
        print("a card would have the evidence of these:")
        for item in [i for i in found.items if i.verdict == "card"][:15]:
            print(f"  {len(item.cards)} cards, {len(item.pages)} documents: {item.phrase} — {item.example[:100]}")
        print(f"the whole report: {found.output}")
        return
    report = apply(dry_run="--dry-run" in args)
    print(f"{report.links} links between cards: {report.cards_linked} of {report.cards} cards link to another one "
          f"({report.names} names in the registry; {len(report.changed)} files rewritten)")
    if report.ambiguous:
        print(f"{len(report.ambiguous)} names two cards answer to (an alias settles them): " + ", ".join(report.ambiguous[:12]))


if __name__ == "__main__":
    main()
