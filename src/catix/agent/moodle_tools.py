"""The assistant's search of the asker's own Moodle course files (moodle_files.py), for a user signed in on innohassle.ru with
Moodle sync on in the InNoHassle browser extension."""

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langgraph.types import Command
from pydantic import BaseModel, Field, field_validator

from catix import moodle_files
from catix.agent.sources import Collector
from catix.db import pg

PIECE_TEXT = 1500
LIMIT = 6


class SearchMoodleFilesArgs(BaseModel):
    queries: list[str] = Field(
        min_length=1,
        max_length=6,
        description="2 to 4 queries in the language of the course files (usually English; Russian too when the course is Russian): "
        "the words the slides or the assignment would use.",
    )
    course: str | None = Field(None, max_length=200, description="Words of the course's name, to search only its files")

    @field_validator("queries", mode="before")
    @classmethod
    def _one_query(cls, value):
        return [value] if isinstance(value, str) else value


@tool(args_schema=SearchMoodleFilesArgs)
def search_my_moodle_files(queries: list[str], runtime: ToolRuntime, course: str | None = None) -> Command | dict:
    """Search the text of the asker's own Moodle course files (slides, assignments, readings), sent by the InNoHassle browser
    extension when its Moodle sync is on. Returns pieces with the file, the course and a ref to cite."""
    innohassle_id = getattr(runtime.context, "innohassle_id", None)
    if not innohassle_id:
        return {"error": "Course files are searched only for a user signed in on innohassle.ru with Moodle sync on in the "
                         "InNoHassle browser extension."}
    ids: list[int] | None = None
    if course:
        with pg.connection() as conn:
            ids = pg.column(
                conn,
                "SELECT course_id FROM moodle_courses WHERE innohassle_id = %s AND (fullname ILIKE %s OR shortname ILIKE %s)",
                (innohassle_id, f"%{course}%", f"%{course}%"),
            )
        if not ids:
            return {"total": 0, "pieces": [], "note": "No course of the user matches that name: search without `course`."}
    hits = moodle_files.search(innohassle_id, queries, course_ids=ids, limit=LIMIT)
    collector = Collector(runtime)
    result: dict = {
        "total": len(hits),
        "pieces": [
            {"ref": collector.add_web(h.filename, h.url, False), "file": h.filename, "course": h.course,
             "section": h.heading, "text": h.text[:PIECE_TEXT]}
            for h in hits
        ],
    }
    if not hits:
        result["note"] = "Nothing found in the user's course files (Moodle sync may be off, or the files are not read yet)."
    return collector.result(result, "search_my_moodle_files")


MOODLE_TOOLS = [search_my_moodle_files]
