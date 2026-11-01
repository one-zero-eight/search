"""A note on a page: what a document is and whom it concerns, written by the model, kept beside the document.

    catix-wiki agent notes /raw/regulations/x.md ...    # the model writes the note of each page it is given

A page of the sources is evidence: its text is the document's, cards quote it, and the search marks it `official`. A note
is not evidence and never becomes one. It is the orientation a reader needs before 800 KB of a regulation: three to five
sentences in the wiki's own words, every sentence citing a clause of that same page (so it points into the document instead
of restating it), and held to two numbers that keep it a note — NOTE_CHARS characters and NOTE_COVERAGE of the document's
clauses. A card of one page was removed for good reason (2026-10-29: 209 of them, median 0.64 of the document's size, 79%
of its clauses: a second copy of the document the search had to choose between). The two numbers are what tells a note from
that copy, and `trust_of` (search_index.py) marks a note `guide`, so it can be an entry point and never a fact.

The file lives in wiki/notes/<the page's name>.md, beside the document and not inside it: the pages stay written by code,
every writer of a page stays as it is, and the model gets one file it owns whole. Code writes the link between the two
(`link_pages`), and the note itself names its page under `## See also`.
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from catix.settings import settings
from catix.wiki import agent
from catix.wiki.compile import BUNDLE, front_of, yaml_value
from catix.wiki.graph import split_front
from catix.wiki.paths import DOCS_FOLDER, is_document

FOLDER = "notes"
NOTE_CHARS = 1200  # characters of a note: an orientation, not a summary — the document is one click away
NOTE_COVERAGE = 0.3  # clauses of the document a note may cite: above this it is a rewrite of the document
SEE_ALSO = "## See also"
CITATIONS = "\n# Citations\n"
MARK = "<!-- catix:notes -->"
BLOCK = re.compile(r"\n*<!-- catix:notes -->.*?<!-- /catix:notes -->\n?", re.S)  # code's block in a document: its notes


def rel(page: str) -> str:
    """A page path as the bundle writes it: a document is under /raw/ ('/regulations/x' is '/raw/regulations/x.md')."""
    page = "/" + page.strip().lstrip("/")
    page = page if page.endswith(".md") else f"{page}.md"
    return page if is_document(page) else f"/{DOCS_FOLDER}{page}"


def path_of(page: str) -> Path:
    """Where the note of a page lives: the same name, the folder of the notes."""
    return BUNDLE / FOLDER / f"{Path(rel(page)).stem}.md"


def note_problems(body: str, idx, page: str) -> list[str]:
    """What is wrong with a note of a page; [] when it may be written.

    The checks of a card come first (every sentence cites a clause, with a verbatim quote of it, and the numbers of the
    sentence are in that quote: agent.problems), and then the two that make a note a note and not a card of one page: it is
    of this page alone, it is short, and it points into the document instead of restating it.
    """
    out = agent.problems(body, idx, quotes=settings.wiki_agent_quotes)
    places = {(page_of, clause) for _, page_of, clause, _ in agent.LINK.findall(body)}
    other = sorted({page_of for page_of, _ in places if page_of != page})
    if other:
        out.append(f"a note is of one page ({page}): the sentence cites {other[0]}")
    if len(body) > NOTE_CHARS:
        out.append(f"the note is {len(body)} characters: at most {NOTE_CHARS} — a note is read before the document, not instead of it")
    clauses = agent.clauses_of(idx, page)
    cited = {clause for page_of, clause in places if page_of == page and clause}
    if clauses and len(cited) > NOTE_COVERAGE * len(clauses):
        out.append(f"the note cites {len(cited)} of the {len(clauses)} clauses of {page}: at most {NOTE_COVERAGE:.0%} — "
                   f"a note points into the document, it does not restate it")
    return out


def write(page: str, title: str, description: str, body: str, idx) -> list[str]:
    """Check the note of a page and write it; the problems when it is not written."""
    page = rel(page)
    if page not in idx.meta:
        return [f"no such page {page}"]
    if not title.strip() or not description.strip():
        return ["a title and a one-sentence description are needed"]
    body, placed = agent.place_quotes(body.strip(), idx, settings.wiki_agent_quotes)  # (the lines the model pointed at, as quotes)
    if placed:
        return placed
    body = agent.fit_quotes(body, idx)
    if found := note_problems(body, idx, page):
        return found
    text, refs = agent.to_file_body(body)  # inline links -> [n], a Citations section written by code
    meta = idx.meta[page]["meta"]
    source = (meta.get("sources") or [{}])[0]
    page_title = str(meta.get("title", page))
    front = ["---", "type: note", f"title: {yaml_value(title.strip()[:200])}", f"description: {yaml_value(description.strip()[:300])}",
             f"source: {yaml_value(page)}", f"evidence_sha: {yaml_value(str(source.get('id', '')))}",
             "sources:", f"  - resource: {yaml_value(page)}", f"    id: {yaml_value(str(source.get('id', '')))}",
             f"    title: {yaml_value(page_title)}", f"    last_modified: {yaml_value(source.get('last_modified', ''))}",
             "generated:", f"  by: {yaml_value(f'{agent.PRODUCER} note ({agent.model_name()})')}",
             f"  at: {yaml_value(datetime.now(timezone.utc).isoformat(timespec='seconds'))}", "status: draft", "---"]

    def citation(n: int, file: str, clause: str, quote: str) -> str:
        path = BUNDLE / file.lstrip("/")
        at = agent.lines_of(quote, path.read_text(encoding="utf-8")) if quote and path.exists() else ""
        return (f"{n}. [{page_title}]({file})" + (f", п. {clause}" if clause else "") + (f", {at}" if at else "")
                + (f": «{quote}»" if quote else ""))

    citations = [citation(n, file, clause, quote) for n, (file, clause, quote) in enumerate(refs, 1)]
    page_file = path_of(page)
    page_file.parent.mkdir(parents=True, exist_ok=True)
    page_file.write_text("\n".join(front) + f"\n\n# {title.strip()}\n\n{text}\n\n{SEE_ALSO}\n\n- [{page_title}]({page})\n\n"
                                   f"# Citations\n\n" + "\n".join(citations) + "\n", encoding="utf-8")
    return []


def notes(bundle: Path | None = None) -> dict[str, str]:
    """Note file -> the page it is of."""
    bundle, out = bundle or BUNDLE, {}
    for path in sorted((bundle / FOLDER).glob("*.md")):
        if path.name == "index.md":
            continue
        source = str(front_of(path.read_text(encoding="utf-8")).get("source", ""))
        if source:
            out["/" + path.relative_to(bundle).as_posix()] = source
    return out


def link_pages(bundle: Path | None = None, dry_run: bool = False) -> int:
    """Every page that has a note leads to it, under `## See also` (code writes the page, the note is the model's).

    Idempotent: the section is rebuilt from the notes that exist, so a note that goes away takes its line with it.
    """
    bundle = bundle or BUNDLE
    by_page: dict[str, list[tuple[str, str]]] = {}
    for note, page in notes(bundle).items():
        title = str(front_of((bundle / note.lstrip("/")).read_text(encoding="utf-8")).get("title", note))
        by_page.setdefault(page, []).append((title, note))
    for file in (bundle / DOCS_FOLDER).rglob("*.md") if (bundle / DOCS_FOLDER).exists() else []:  # a page whose note went away
        if MARK in file.read_text(encoding="utf-8"):
            by_page.setdefault("/" + file.relative_to(bundle).as_posix(), [])
    written = 0
    for page, links in by_page.items():
        file = bundle / page.lstrip("/")
        if not file.exists():
            continue
        text = file.read_text(encoding="utf-8")
        front, rest = split_front(text)
        body, _, tail = rest.partition(CITATIONS)
        body = BLOCK.sub("\n", body).rstrip("\n")  # the block is code's: written again from the notes there are
        lines = "\n".join(f"- [Note: {title}]({note})" for title, note in sorted(links))
        block = f"\n\n{MARK}\n{SEE_ALSO}\n\n{lines}\n<!-- /catix:notes -->\n" if links else "\n"
        new = f"{front}{body}{block}" + (f"{CITATIONS}{tail}" if tail or CITATIONS in rest else "")
        if new != text:
            written += 1
            if not dry_run:
                file.write_text(new, encoding="utf-8")
    return written


NOTES_INSTRUCTIONS = """A note on one page of the wiki of Innopolis University: what the document is, whom it concerns, what a
reader finds in it. You are given the path of the page; read it (read_page: its lines numbered, or one clause of it) and write its
note with write_note. The page is a document of the university: its text is evidence, your note is not.

- Three to five sentences, at most {chars} characters. English, plain markdown, no headings, no front matter, no Citations
  section (the program writes those).
- Every sentence cites THIS page and nothing else. Point at the place, do not copy it: read_page numbers the lines of the
  document, and [source](/raw/regulations/x.md#L118-L120) points at lines 118 to 120 — the few lines the sentence rests on.
  A short clause may be pointed at whole: [п. 5.3](/raw/regulations/x.md#5.3). The program copies the words of that place
  into the citation and checks your numbers against them, so do not state a number those lines do not.
- Say what a reader needs before reading the document: what it governs, whom it binds, what it establishes, what has to be
  done and by when. Do not walk through the clauses: at most {share:.0%} of them may be cited, and the document is one click
  away.
- Write no list of the document's contents and no conclusion about it: the reader has the document itself.
- A note is of one page: never cite another page, and never link another card.
- If write_note returns problems, fix exactly those and write again. Answer with one line that starts with DONE:.
"""


def instructions(page: str) -> str:
    return NOTES_INSTRUCTIONS.format(chars=NOTE_CHARS, share=NOTE_COVERAGE) + f"\nThe page to write the note of: {rel(page)}\n"


# ---- the model that writes a note: the card agent's tools, one page a task -----------------------------------------


def _tools(idx_box: list, written: list, refused: dict):
    from langchain_core.tools import tool

    @tool
    def read_page(page: str, clause: str = "", offset: int = 0) -> str:
        """A page (/raw/regulations/x.md) with the numbers of its lines, or one clause of it ("5.3"). A long page is cut: read
        on with offset=the line to start at. Cite a sentence by the lines it rests on: [source](/raw/x.md#L118-L120)."""
        return agent.read_document(idx_box[0], rel(page), clause, offset)

    @tool
    def write_note(page: str, title: str, description: str, body: str) -> str:
        """The note of a page: three to five sentences, every sentence citing a clause of that page. Returns 'written' or the problems to fix."""
        page = rel(page)
        if refused.get(page, 0) >= agent.MAX_REFUSED:
            return f"STOP: {agent.MAX_REFUSED} attempts of this note were refused. Do not call write_note again: answer with DONE: gave up."
        found = write(page, title, description, body, idx_box[0])
        if found:
            refused[page] = refused.get(page, 0) + 1
            return "NOT written, fix these:\n" + "\n".join(f"- {p}" for p in found[:12])
        written.append(page)
        return f"written: /{FOLDER}/{Path(page).stem}.md"

    return [read_page, write_note]


def _build(idx_box: list, written: list, refused: dict):
    from deepagents import create_deep_agent
    from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend
    from deepagents.middleware.filesystem import FilesystemPermission
    from langchain_openai import ChatOpenAI

    local = settings.wiki_llm_route is None
    model = ChatOpenAI(
        base_url=str(settings.wiki_llm_route or settings.llm_route),
        api_key=settings.wiki_llm_api_key.get_secret_value() if settings.wiki_llm_api_key else "not-needed",
        model=agent.model_name(),
        temperature=0,
        max_tokens=settings.wiki_agent_max_tokens,
        **({"extra_body": {"chat_template_kwargs": {"enable_thinking": False}}} if local else {}),
        **agent.server_context(),
    )
    return create_deep_agent(
        model=model,
        tools=_tools(idx_box, written, refused),
        system_prompt=NOTES_INSTRUCTIONS.format(chars=NOTE_CHARS, share=NOTE_COVERAGE),
        backend=CompositeBackend(default=FilesystemBackend(root_dir=BUNDLE, virtual_mode=True),
                                 routes={"/conversation_history/": StateBackend(), "/large_tool_results/": StateBackend()}),
        permissions=[FilesystemPermission(operations=["write"], paths=["/**"], mode="deny")],  # a note goes through write_note only
        middleware=[agent._guard(lambda page, line: agent.read_document(idx_box[0], page, offset=line))],
        name="wiki-notes",
    )


def run(pages: list[str]) -> dict:
    """A note for each of these pages, written by the model, then the link from every page to its note."""
    idx_box, written, refused = [agent.Index()], [], {}
    builder = _build(idx_box, written, refused)
    for page in pages:
        page = rel(page)
        print(f"== note of {page}", flush=True)
        print("  " + agent._invoke(builder, instructions(page), name=f"wiki note: {page}"), flush=True)
        idx_box[0] = agent.Index()  # the note just written is part of the bundle
    linked = link_pages()
    print(f"== {len(written)} notes written of {len(pages)} pages; {linked} pages link to a note")
    return {"pages": len(pages), "notes written": len(written), "pages linked": linked}


def check_all(bundle: Path | None = None) -> dict[str, list[str]]:
    """Every note against its page as the bundle is now: a page that changed shows up here (the note no longer holds)."""
    idx = agent.Index()
    out: dict[str, list[str]] = {}
    for note, page in notes(bundle).items():
        read = agent.read_file_card(Path(note).stem, FOLDER)
        if read and (found := note_problems(read["body"], idx, page)):
            out[Path(note).stem] = found
    return out


def main() -> None:
    from catix.wiki import quality

    console = sys.argv[3:]  # `catix-wiki agent notes ...`: the first two words are the tool and the command
    args = [a for a in console if not a.startswith("--")]
    if "--check" in console:
        broken = check_all()
        for slug, found in broken.items():
            print(f"{slug}:\n  " + "\n  ".join(found[:6]))
        print(f"{len(notes())} notes, {len(broken)} do not hold")
        return
    if "--link" in console or not args:
        print(f"{link_pages()} pages link to a note")
        return
    before = quality.score() if "--measure" in console else None
    stats = run(args)
    if before is not None:
        after = quality.score()
        print(f"search: hit@5 {before.hit5:.0%} -> {after.hit5:.0%}, hit@10 {before.hit10:.0%} -> {after.hit10:.0%}")
        if after.missed:
            print("no answer among the first ten:", "; ".join(after.missed[:5]))
    print(stats)
