"""The assistant's reads of the asker's Moodle data (moodle_sync.py, moodle_files.py): the text of course files and course pages
(the `moodle` source of the search tool), `get_my_moodle` for deadlines, grades, announcements and courses. For a user signed in on
innohassle.ru with Moodle sync on in the InNoHassle browser extension, and for the members of a verified study group of a user who
syncs: they read the materials and dates the course's owner shares, never grades or statuses."""

from datetime import date, datetime, time, timedelta
from typing import Literal
from urllib.parse import urlsplit

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field, model_validator

from catix import moodle_files, moodle_sync
from catix.agent.sources import Collector
from catix.settings import settings

PIECE_TEXT = 1500
LIMIT = 6
DEADLINE_DAYS = 14
ANNOUNCEMENT_DAYS = 30
MAX_ITEMS = 40
TEXT_MAX = 1000
TIME_FORMAT = "%Y-%m-%d %a %H:%M"

NOT_ALLOWED = (
    "Moodle data is read only for a user signed in on innohassle.ru with Moodle sync on in the InNoHassle browser extension, "
    "or whose verified study group shares it."
)


def asker(runtime: ToolRuntime) -> tuple[str | None, tuple[str, ...]]:
    """(the asker's InNoHassle id, their verified study groups) of this question."""
    context = runtime.context
    return getattr(context, "innohassle_id", None), tuple(getattr(context, "verified_study_groups", ()) or ())


def pdf_ref(url: str, page: int | None) -> str:
    """The link of a piece: a PDF opens on its page."""
    return f"{url}#page={page}" if page and urlsplit(url).path.lower().endswith(".pdf") else url


def fetch(queries: list[str], runtime: ToolRuntime, rerank: bool = True) -> list | None:
    """The pieces of the asker's Moodle courses (and those their verified study group shares) that answer the queries;
    None when the asker has no access to Moodle data."""
    innohassle_id, study_groups = asker(runtime)
    if not innohassle_id and not study_groups:
        return None
    return moodle_files.search(innohassle_id, queries, study_groups=study_groups, limit=LIMIT, rerank=rerank)


def render(hits: list, collector: Collector) -> dict:
    """Pieces with the course path, the page of a PDF and a ref to cite."""
    pieces = []
    for h in hits:
        title = f"{h.title} (p. {h.page})" if h.page else h.title
        piece = {"ref": collector.add_moodle(title, pdf_ref(h.url, h.page)), "kind": h.kind, "course": h.course,
                 "path": h.path, "page": h.page, "shared": h.shared, "section": h.heading, "text": h.text[:PIECE_TEXT]}
        pieces.append({k: v for k, v in piece.items() if k != "page" or v is not None})
    result: dict = {"total": len(hits), "pieces": pieces}
    if not hits:
        result["note"] = ("Nothing found in the asker's Moodle courses or those their study group shares (Moodle sync may be "
                          "off, or the files are not read yet).")
    return result


class GetMyMoodleArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    what: Literal["deadlines", "grades", "announcements", "courses"] = Field(
        description="deadlines: assignments, quizzes and other Moodle events due in the dates; grades; announcements posted in "
        "the dates; courses: names, dates, completion"
    )
    course: str | None = Field(None, max_length=200, description="Words of the course's name, to read only its data")
    date_from: date | None = Field(
        None,
        description="YYYY-MM-DD. deadlines: default today; announcements: default 30 days ago. Not used for grades and courses.",
    )
    date_to: date | None = Field(
        None, description="YYYY-MM-DD inclusive. deadlines: default date_from + 13 days; announcements: default today."
    )

    @model_validator(mode="before")
    @classmethod
    def without_injected_runtime(cls, values):
        if isinstance(values, dict) and isinstance(values.get("runtime"), ToolRuntime):
            return {key: value for key, value in values.items() if key != "runtime"}
        return values


def local(moment: datetime | None) -> str | None:
    return moment.astimezone(settings.tz).strftime(TIME_FORMAT) if moment else None


def local_day(moment: datetime | None) -> str | None:
    return moment.astimezone(settings.tz).strftime("%Y-%m-%d") if moment else None


@tool(args_schema=GetMyMoodleArgs)
def get_my_moodle(
    runtime: ToolRuntime,
    what: Literal["deadlines", "grades", "announcements", "courses"],
    course: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    """The asker's Moodle data as the InNoHassle browser extension last synced it: deadlines, grades, announcements, courses.
    Also the courses a member of the asker's verified study group shares (`shared: true`): their dates and announcements, never
    anyone else's grades or status. For questions about course material use search with sources=["moodle"]."""
    innohassle_id, study_groups = asker(runtime)
    if not innohassle_id and not study_groups:
        return {"error": NOT_ALLOWED}
    everything = moodle_sync.scopes(innohassle_id, study_groups)
    if not everything:
        return {"error": "No Moodle data: the asker turns on Moodle sync in the InNoHassle browser extension, or a member of "
                         "their verified study group shares course materials."}
    found = everything
    if course:
        ids = moodle_sync.matching_course_ids(everything, course)
        if not ids:
            return {"error": "No course of the user matches that name: read without `course`, or with what=\"courses\" for the names."}
        found = [s for s in everything if s.course_id in ids]
    today = datetime.now(settings.tz).date()
    result: dict = {"what": what}
    if what in ("deadlines", "announcements"):
        if what == "deadlines":
            start = date_from or today
            end = date_to or start + timedelta(days=DEADLINE_DAYS - 1)
        else:
            end = date_to or today
            start = date_from or end - timedelta(days=ANNOUNCEMENT_DAYS - 1)
        if end < start:
            return {"error": "date_to must not be before date_from."}
        since = datetime.combine(start, time.min, settings.tz)
        until = datetime.combine(end + timedelta(days=1), time.min, settings.tz)
        result["range"] = [start.isoformat(), end.isoformat()]
        if what == "deadlines":
            raw = sorted(moodle_sync.deadlines(innohassle_id, found, since, until, filtered=bool(course)), key=lambda i: i["due"])
            items = [{**i, **{k: local(i[k]) for k in ("due", "cutoff", "opens") if k in i}} for i in raw]
        else:
            items = [{**i, "posted": local(i["posted"]), "text": i["text"][:TEXT_MAX]} for i in moodle_sync.announcements(found, since, until)]
    elif what == "grades":
        items = grades(innohassle_id, found)
    else:
        items = [{**i, "starts": local_day(i["starts"]), "ends": local_day(i["ends"])} for i in moodle_sync.courses(found)]
    result |= {"items": items[:MAX_ITEMS], "total": len(items), "truncated": len(items) > MAX_ITEMS}
    if not items:
        result["note"] = "Nothing of that kind in the asker's Moodle data or what their study group shares, as of the last sync."
    elif result["truncated"]:
        result["note"] = f"Only the first {MAX_ITEMS} are shown: narrow by course or dates."
    return result


def grades(innohassle_id: str | None, found: list[moodle_sync.Scope]) -> list[dict]:
    """The asker's own grades (never a shared owner's) in the courses in scope."""
    own = {s.course_id for s in found if s.own}
    data = moodle_sync.overview(innohassle_id) if innohassle_id and own else None
    if data is None:
        return []
    names = {c.course_id: c.fullname for c in data.courses}
    return [
        {"course": names.get(g.course_id, ""), "shared": False, "name": g.name, "grade": g.grade_text,
         "percentage": g.percentage_text, "max": g.grade_max, "feedback": (g.feedback or "")[:TEXT_MAX] or None,
         "graded_at": local(g.graded_at)}
        for g in data.grades
        if g.item_type != "category" and g.course_id in own
    ]


MOODLE_TOOLS = [get_my_moodle]
