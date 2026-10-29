"""Links between the cards of the bundle, written by code — the model cannot write them.

    catix-wiki agent links [--dry-run]      # the links of every card, and the names it left alone
    catix-wiki agent candidates [--folders a,b]   # what the corpus repeats that no artifact answers (see below)

The report reads the whole bundle — the documents and the cards — and ranks. What it tells apart by itself: a phrase the
bundle already answers to under another name (an alias to add to that card or page), and a phrase two and more documents
repeat while no artifact answers (the evidence a card would have). What it cannot tell apart is a subject of the
university from an outside body or a law ("Трудовой кодекс", "Ministry of Science") and from a turn of a sentence the model
wrote twice ("university ensures"): a person, or a model told to, reads the head of the list and says which is which.

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
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from catix.wiki.compile import BUNDLE, front_of, worth_reading
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


# ---- what the corpus names that no artifact answers: the criterion for a card ----
#
# The report reads the whole bundle, not the cards alone: the cards name a few hundred subjects, the documents name the
# university's whole life. A phrase the documents repeat while no card, page or alias answers to it is a subject the wiki
# still owes a card; a phrase the bundle answers to under another name is an alias to add to that artifact. What the report
# cannot do is tell a subject of the university from an outside body or a law ("Трудовой кодекс", "Ministry of Science") and
# from a turn of a sentence the model wrote twice ("university ensures"): a person (or a model) reads the head of the list
# and says which is which. Nothing here writes into the bundle.

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
STEM = 5  # letters of a word that count as the same word ("пересдач" is "пересдачи"): the rule db/wiki.py follows
RARE = 0.05  # a word named in more than this share of the documents is not the head of a subject
SIZES = (3, 2)  # a phrase of two or three words ("пересдача промежуточной аттестации")
RUN = re.compile(r"[^\W_]+(?: [^\W_]+)*")  # words joined by single spaces: a name holds no comma or bracket inside
HYPHEN = "-"  # "-" at either end of a run: the extraction broke a word in two ("мо-", "гут"), not a name
SKIP: tuple[str, ...] = ()  # folders to leave out on top of worth_reading (the course programmes are out by default)
MIN_PAGES = 2  # documents a phrase must stand in to be a subject (a card rests on more than one page: SOURCES)
BAND = 0.2  # documents a word may head a subject in: a word of more headings than this one heads the genre
TEMPLATE = 0.3  # share of one folder's documents a phrase may stand in: what most of a folder repeats is its template
TEMPLATE_MIN = 8  # ... and a folder is read this way only when it holds this many documents (a small folder says nothing)
MIN_FOLDERS = 2  # folders those documents must come from: what one genre repeats is its template, not a subject
LIMIT = 2000  # phrases written to the report (the head of the list is what is read)


@dataclass
class Candidate:
    """A phrase the corpus repeats, and what the bundle has for it."""

    phrase: str
    cards: list[str]  # the cards that name it
    pages: list[str]  # a few of the documents it stands in (documents says how many)
    verdict: str  # 'alias': an artifact answers to another name | 'card': no artifact, two documents and more
    artifact: str = ""  # the path of the artifact an alias would be added to
    example: str = ""  # the sentence it was met in
    documents: int = 0  # documents it stands in
    folders: int = 0  # folders those documents come from

    @property
    def card_count(self) -> int:
        return len(self.cards)


@dataclass
class Candidates:
    """The report: what the corpus repeats while the bundle answers nothing, by the evidence a card would have."""

    phrases: int = 0  # phrases standing in two documents and more
    articles: int = 0  # artifacts the bundle has (a name a reader may follow)
    items: list[Candidate] = field(default_factory=list)
    by_verdict: dict[str, int] = field(default_factory=dict)
    output: str = ""


def stem(word: str) -> str:
    """A word as it is compared across the corpus: lower case, ё as е, its first STEM letters (no lemmatiser here)."""
    return norm(word)[:STEM]


def readable(text: str) -> str:
    """What of a concept may name a subject: its prose alone — no front matter, no citations, no machine sections, and
    nothing already marked as not ours (a link, code, a quote of a document, a heading)."""
    rest = text
    if text.startswith("---\n") and "\n---\n" in text:
        _, rest = split_front(text)
    body = rest.partition(CITATIONS)[0]
    body, _ = see_also_of(body)
    for pattern in TAKEN:
        body = pattern.sub(" ", body)
    return body


def concepts(bundle: Path = BUNDLE, skip: tuple[str, ...] = SKIP) -> list[tuple[str, str, dict]]:
    """Every concept of the bundle as (its path, its prose, its front matter): the documents, the wiki, the cards.

    Every concept is returned, with its front matter (a name answers wherever it stands, and the report needs the names of
    the folders it does not read); the text is kept only for the pages the wiki reads for its cards (worth_reading): the
    surveys, the curricula and the course programmes (68% of the bundle's bytes, 1877 pages of one template of hours and
    reading lists) hold no subject of the university, and reading them costs minutes and returns table soup.
    """
    out = []
    for path in sorted(bundle.rglob("*.md")):
        parts = path.relative_to(bundle).parts
        if any(part.startswith(".") for part in parts) or path.name in {"index.md", "log.md", "README.md"}:
            continue
        if parts[0] in skip:
            continue
        raw = path.read_text(encoding="utf-8")
        meta = front_of(raw)
        out.append(("/" + path.relative_to(bundle).as_posix(), raw if worth_reading(meta) else "", meta))
    return out


HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", re.M)  # a section of a document names its subject
LEAD = re.compile(r"^\s{0,3}\*\*([^*\n]{4,90})\*\*", re.M)  # a clause of a regulation names its own ("**5.3.** …")


def body_of(text: str) -> str:
    """The body of a concept: no front matter, no citations — the headings and the clauses stay."""
    rest = text
    if text.startswith("---\n") and "\n---\n" in text:
        _, rest = split_front(text)
    return rest.partition(CITATIONS)[0]


def names_of_document(text: str) -> list[str]:
    """What a document names as its own subjects: the headings of its sections, the leads of its clauses, its tables' first
    line. Their prose is not read here: what a page repeats in prose is its template ("Каждая сторона должна оппонировать"),
    what it names in a heading is a subject ("Пересдача промежуточной аттестации")."""
    body = body_of(text)
    return [m.group(1).strip() for m in HEADING.finditer(body)] + [m.group(1).strip() for m in LEAD.finditer(body)]


def phrase_keys(text: str, allowed: set[str], sizes: tuple[int, ...] = SIZES):
    """The (as the text writes it, its key) of every phrase of a text that may name a subject, one a word at a time.

    A subject is named by a rare word and two to four words around it ("пересдача промежуточной аттестации"): the head is
    a word of COMMON and less, so the phrases of the genre ("высшее образование") are never built — that is what keeps a
    corpus of two million characters readable. A phrase holding a number or a one-letter token is a piece of a table or of
    a possessive, a word in capitals is the head of a document as the extraction printed it.
    """
    for match in RUN.finditer(text):
        if match.start() and text[match.start() - 1] == HYPHEN or match.end() < len(text) and text[match.end()] == HYPHEN:
            continue  # a word the extraction broke in two: "мо-гут" is not a name
        words = match.group(0).split()
        for i, word in enumerate(words):
            if stem(word) not in allowed:
                continue
            for size in sizes:  # the longest first: the report shows the fullest name of a subject
                tokens = words[i:i + size]
                if len(tokens) < size:
                    continue
                if any(len(t) < 2 or LABEL.search(t) or (t.isupper() and len(t) > 1) for t in tokens):
                    continue
                if tokens[-1].lower() in NOISE or sum(1 for t in tokens if t.lower() in NOISE) > 1:
                    continue
                if len([t for t in tokens if t.lower() not in NOISE]) < 2:
                    continue
                yield " ".join(tokens), tuple(stem(t) for t in tokens)


def stems_of(name: str) -> tuple[str, ...]:
    """The key of a name, as the corpus is read."""
    return tuple(stem(word) for word in norm(name).split())


def names_of(documents: list[tuple[str, str, dict]]) -> list[tuple[str, str]]:
    """Every name the bundle answers to: the title and the aliases of every concept, with the path it belongs to."""
    return [(str(meta.get("title", "")), path) for path, _, meta in documents] + \
           [(str(alias), path) for path, _, meta in documents for alias in meta.get("aliases") or []]


def artifacts_of(pairs: list[tuple[str, str]]) -> dict[tuple[str, ...], str]:
    """Name (as its key) -> the path of the artifact that answers to it: a title and its head, its aliases."""
    names: dict[tuple[str, ...], str] = {}
    for name, path in pairs:
        for part in [name, HEAD.split(name)[0]]:
            key = stems_of(part)
            if len(key) >= 2 or len("".join(key)) >= MIN_KEY:
                names.setdefault(key, path)
    return names


def holds(name: tuple[str, ...], key: tuple[str, ...]) -> bool:
    """Whether a name stands inside a longer phrase, word for word: "пересдача" answers "пересдача экзамена"."""
    return any(key[i:i + len(name)] == name for i in range(len(key) - len(name) + 1))


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


def head_words(names: list[list[str]], documents: int) -> set[str]:
    """The words that may head a subject: named in two of these documents and less than BAND of them (the rest is genre)."""
    seen: Counter = Counter()
    for spans in names:
        seen.update({stem(word) for span in spans for word in span.split()})
    return {word for word, n in seen.items() if MIN_PAGES <= n <= max(MIN_PAGES, int(BAND * documents))}


def candidates(bundle: Path = BUNDLE, output: Path | None = None, limit: int = LIMIT, skip: tuple[str, ...] = SKIP) -> Candidates:
    """What the corpus repeats that the bundle answers nothing for, with the evidence a card of each would have.

    The criterion this report is: a subject the documents speak of (two and more of them, so a card of it can rest on more
    than one page) that no artifact answers — no card, and no page whose title or alias names it. A phrase the bundle
    answers to under another name is an alias to add to that artifact. What it ranks by is how many documents speak of the
    subject and how many cards already name it: a subject of fifty documents no card mentions is what the wiki owes most.
    """
    documents = concepts(bundle, skip)
    pages = [(path, text) for path, text, _ in documents if text and not path.startswith(f"/{FOLDER}/")]
    cards = read_cards(bundle)
    allowed = head_words([names_of_document(text) for _, text in pages], len(pages) or 1)
    artifacts = artifacts_of(names_of(documents))  # a name answers wherever it stands, the skipped folders too
    docs: dict[tuple[str, ...], set[str]] = defaultdict(set)
    folders: dict[tuple[str, ...], set[str]] = defaultdict(set)
    in_folder: dict[tuple[str, ...], Counter] = defaultdict(Counter)  # phrase -> folder -> documents
    surface: dict[tuple[str, ...], Counter] = defaultdict(Counter)
    example: dict[tuple[str, ...], str] = {}
    for path, text in pages:
        folder = path.split("/")[1]
        for span in names_of_document(text):
            for form, key in phrase_keys(span, allowed):
                docs[key].add(path)
                folders[key].add(folder)
                surface[key][form] += 1
                example.setdefault(key, span)
    card_spans = [names_of_document(card.text) + [readable(card.text)] for card in cards]
    card_allowed = head_words(card_spans, len(cards) or 1)
    in_cards: dict[tuple[str, ...], set[str]] = defaultdict(set)
    for card, spans in zip(cards, card_spans):
        for span in spans:
            for _, key in phrase_keys(span, card_allowed):
                in_cards[key].add(card.slug)
    totals = Counter(path.split("/")[1] for path, _ in pages)
    template = {key for key, counts in in_folder.items()
                if any(n >= TEMPLATE * total and total >= TEMPLATE_MIN for folder, n in counts.items() if (total := totals[folder]))}
    report = Candidates(phrases=sum(1 for key, paths in docs.items() if len(paths) >= MIN_PAGES
                                    and len(folders[key]) >= MIN_FOLDERS and key not in template), articles=len(artifacts))
    for key, paths in docs.items():
        if len(paths) < MIN_PAGES or len(folders[key]) < MIN_FOLDERS or key in template:
            continue
        artifact = artifacts.get(key) or next((path for name, path in artifacts.items() if holds(name, key)), "")
        verdict = "alias" if artifact else "card"
        form = surface[key].most_common(1)[0][0]
        report.items.append(Candidate(form, sorted(in_cards.get(key, [])), sorted(paths)[:6], verdict, artifact,
                                      example.get(key, ""), len(paths), len(folders[key])))
        report.by_verdict[verdict] = report.by_verdict.get(verdict, 0) + 1
    # what the wiki owes most first: many documents, and no card names it yet
    report.items.sort(key=lambda c: (0 if c.verdict == "alias" else 1, -c.documents, c.card_count, c.phrase))
    report.items = report.items[:limit]
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
        folders = tuple(args[args.index("--folders") + 1].split(",")) if "--folders" in args else SKIP
        found = candidates(output=output, skip=folders)
        print(f"{found.phrases} phrases stand in two documents and more, of {found.articles} artifacts the bundle has")
        print("an alias settles these (the artifact already answers to another name):")
        for item in [i for i in found.items if i.verdict == "alias"][:12]:
            print(f"  {item.phrase} -> {item.artifact}")
        print("what the wiki owes most (documents it stands in, then cards that name it):")
        for item in [i for i in found.items if i.verdict == "card"][:20]:
            print(f"  {item.documents:3} documents in {item.folders} folders, {item.card_count:2} cards: {item.phrase} — {item.example[:80]}")
        print(f"the whole report: {found.output}")
        return
    report = apply(dry_run="--dry-run" in args)
    print(f"{report.links} links between cards: {report.cards_linked} of {report.cards} cards link to another one "
          f"({report.names} names in the registry; {len(report.changed)} files rewritten)")
    if report.ambiguous:
        print(f"{len(report.ambiguous)} names two cards answer to (an alias settles them): " + ", ".join(report.ambiguous[:12]))


if __name__ == "__main__":
    main()
