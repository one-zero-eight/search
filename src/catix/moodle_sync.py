"""A user's Moodle data, sent by the InNoHassle browser extension (api/moodle.py) and read back by the website.

The extension reads Moodle with the user's own Moodle token (which never leaves the browser) and sends: the calendar and
deadlines, grades, assignments with their submission status, quizzes with attempts, activity completion, the user's course
groups, course announcements, and the text of course sections and modules with the names and links of course files (never
the files). The HTML of Moodle is sent raw and turned into Markdown here (the extension's service worker has no DOMParser).

The data is private to the user, except that the students of the user's verified study groups (`moodle_accounts.study_groups`)
read the shareable materials of their courses: files, course texts, announcements, assignment and quiz dates (`scopes`). Grades,
statuses, attempts, completion and events are never shared. Every row carries `innohassle_id`, every sync replaces it, and
`forget` removes it. Course text is content-addressed: stored once per distinct text (`moodle_texts`, sha256 of the
Markdown), and the rows of each user point to it; a text is deleted when no row of any user references it any more.
"""

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal

from html_to_markdown import ConversionOptions, convert
from html_to_markdown.exceptions import ConversionError
from pydantic import BaseModel, Field, field_validator

from catix.db import pg

HTML_MAX = 200_000
DESCRIPTION_MAX = 20_000
MOODLE_URL = "https://moodle.innopolis.university/"


def _moodle_url(value: str | None) -> str | None:
    if value is not None and not value.startswith(MOODLE_URL):
        raise ValueError("not a Moodle link")
    return value


class _UrlChecked(BaseModel):
    @field_validator("url", check_fields=False)
    @classmethod
    def _check_url(cls, value: str | None) -> str | None:
        return _moodle_url(value)


# ---- requests

class MoodleCourseIn(BaseModel):
    course_id: int
    fullname: str = Field(max_length=1000)
    shortname: str = Field(max_length=500)
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class MoodleEventIn(_UrlChecked):
    event_id: int
    course_id: int | None = None
    group_id: int | None = None
    name: str = Field(max_length=1000)
    description_html: str = Field("", max_length=HTML_MAX)
    event_type: str = Field(max_length=50)
    module: str | None = Field(None, max_length=50)
    starts_at: datetime
    duration_seconds: int = Field(0, ge=0)
    url: str | None = Field(None, max_length=2000)
    pending: bool = False


class MoodleGradeItemIn(BaseModel):
    item_id: int
    name: str = Field(max_length=1000)
    item_type: str = Field(max_length=50)
    module: str | None = Field(None, max_length=50)
    grade: float | None = None
    grade_min: float | None = None
    grade_max: float | None = None
    grade_text: str | None = Field(None, max_length=200)
    percentage_text: str | None = Field(None, max_length=200)
    feedback_html: str = Field("", max_length=HTML_MAX)
    graded_at: datetime | None = None


class MoodleCourseGradesIn(BaseModel):
    course_id: int
    items: list[MoodleGradeItemIn] = Field(max_length=1000)


class MoodleAssignmentIn(BaseModel):
    assignment_id: int
    module_id: int
    name: str = Field(max_length=1000)
    description_html: str = Field("", max_length=DESCRIPTION_MAX)
    opens_at: datetime | None = None
    due_at: datetime | None = None
    cutoff_at: datetime | None = None
    grading_due_at: datetime | None = None
    max_grade: float | None = None
    submission_status: str | None = Field(None, max_length=50)
    grading_status: str | None = Field(None, max_length=50)
    grade_html: str = Field("", max_length=2000)


class MoodleCourseAssignmentsIn(BaseModel):
    course_id: int
    items: list[MoodleAssignmentIn] = Field(max_length=500)


class MoodleQuizIn(BaseModel):
    quiz_id: int
    module_id: int
    name: str = Field(max_length=1000)
    description_html: str = Field("", max_length=DESCRIPTION_MAX)
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    time_limit_seconds: int | None = None
    attempts_allowed: int = 0
    attempts_used: int | None = None
    best_grade: float | None = None
    max_grade: float | None = None


class MoodleCourseQuizzesIn(BaseModel):
    course_id: int
    items: list[MoodleQuizIn] = Field(max_length=500)


class MoodleCompletionIn(BaseModel):
    module_id: int
    state: int = Field(ge=0, le=3)
    completed_at: datetime | None = None


class MoodleCourseCompletionIn(BaseModel):
    course_id: int
    items: list[MoodleCompletionIn] = Field(max_length=2000)


class MoodleGroupIn(BaseModel):
    group_id: int
    name: str = Field(max_length=500)


class MoodleCourseGroupsIn(BaseModel):
    course_id: int
    groups: list[MoodleGroupIn] = Field(max_length=200)


class MoodleOverviewIn(BaseModel):
    moodle_user_id: int
    moodle_username: str = Field(max_length=320)
    courses: list[MoodleCourseIn] = Field(max_length=300)
    events: list[MoodleEventIn] | None = Field(
        None, max_length=5000, description="None: Moodle did not answer; the stored events stay"
    )
    grades: list[MoodleCourseGradesIn] = Field(
        default_factory=list, max_length=300,
        description="Only the courses whose grades Moodle returned; the others keep theirs",
    )
    assignments: list[MoodleCourseAssignmentsIn] = Field(
        default_factory=list, max_length=300, description="Only the courses Moodle returned; the others keep theirs"
    )
    quizzes: list[MoodleCourseQuizzesIn] = Field(
        default_factory=list, max_length=300, description="Only the courses Moodle returned; the others keep theirs"
    )
    completion: list[MoodleCourseCompletionIn] = Field(
        default_factory=list, max_length=300, description="Only the courses Moodle returned; the others keep theirs"
    )
    groups: list[MoodleCourseGroupsIn] = Field(
        default_factory=list, max_length=300, description="Only the courses Moodle returned; the others keep theirs"
    )


class MoodleFileIn(_UrlChecked):
    filename: str = Field(max_length=500)
    url: str = Field(max_length=2000)
    size_bytes: int | None = None
    mime_type: str | None = Field(None, max_length=200)
    modified_at: datetime | None = None
    sha256: str | None = Field(None, pattern=r"^[0-9a-f]{64}$", description="sha256 of the file's bytes, when the file is offered")


class MoodleModuleIn(_UrlChecked):
    module_id: int
    name: str = Field(max_length=1000)
    module: str = Field(max_length=50)
    url: str | None = Field(None, max_length=2000)
    external_url: str | None = Field(None, max_length=2000, description="Where a `url` module points; read for chat links only, not stored")
    html: str = Field("", max_length=HTML_MAX)
    files: list[MoodleFileIn] = Field(default_factory=list, max_length=200)
    shareable: bool = Field(False, description="Visible to every student of the course: visible, uservisible, no availability restriction")


class MoodleSectionIn(BaseModel):
    section_id: int
    name: str = Field("", max_length=1000)
    summary_html: str = Field("", max_length=HTML_MAX)
    shareable: bool = Field(False, description="Visible to every student of the course: visible, uservisible, no availability restriction")
    modules: list[MoodleModuleIn] = Field(default_factory=list, max_length=1000)


class MoodleAnnouncementIn(BaseModel):
    discussion_id: int
    title: str = Field(max_length=1000)
    html: str = Field("", max_length=HTML_MAX)
    posted_at: datetime


class MoodleCourseContentIn(BaseModel):
    sections: list[MoodleSectionIn] = Field(max_length=300)
    announcements: list[MoodleAnnouncementIn] = Field(default_factory=list, max_length=50)


# ---- responses

class MoodleSyncResult(BaseModel):
    courses_without_content: list[int]


class MoodleCourseOut(BaseModel):
    course_id: int
    fullname: str
    shortname: str
    starts_at: datetime | None
    ends_at: datetime | None
    content_synced_at: datetime | None


class MoodleEventOut(BaseModel):
    event_id: int
    course_id: int | None
    group_id: int | None
    name: str
    description: str | None
    event_type: str
    module: str | None
    starts_at: datetime
    ends_at: datetime
    url: str | None
    pending: bool


class MoodleGradeOut(BaseModel):
    course_id: int
    item_id: int
    name: str
    item_type: str
    module: str | None
    grade: float | None
    grade_min: float | None
    grade_max: float | None
    grade_text: str | None
    percentage_text: str | None
    feedback: str | None
    graded_at: datetime | None


class MoodleAssignmentOut(BaseModel):
    course_id: int
    assignment_id: int
    module_id: int
    name: str
    description: str | None
    opens_at: datetime | None
    due_at: datetime | None
    cutoff_at: datetime | None
    grading_due_at: datetime | None
    max_grade: float | None
    submission_status: str | None
    grading_status: str | None
    grade: str | None


class MoodleQuizOut(BaseModel):
    course_id: int
    quiz_id: int
    module_id: int
    name: str
    description: str | None
    opens_at: datetime | None
    closes_at: datetime | None
    time_limit_seconds: int | None
    attempts_allowed: int
    attempts_used: int | None
    best_grade: float | None
    max_grade: float | None


class MoodleCompletionOut(BaseModel):
    course_id: int
    module_id: int
    state: Literal["incomplete", "complete", "complete_pass", "complete_fail"]
    completed_at: datetime | None


class MoodleGroupOut(BaseModel):
    course_id: int
    group_id: int
    name: str


class MoodleOverviewOut(BaseModel):
    moodle_user_id: int
    synced_at: datetime
    courses: list[MoodleCourseOut]
    events: list[MoodleEventOut]
    grades: list[MoodleGradeOut]
    assignments: list[MoodleAssignmentOut]
    quizzes: list[MoodleQuizOut]
    completion: list[MoodleCompletionOut]
    groups: list[MoodleGroupOut]


class MoodleFileOut(BaseModel):
    filename: str
    url: str
    size_bytes: int | None
    mime_type: str | None
    modified_at: datetime | None
    sha256: str | None
    text_status: Literal["not_offered", "not_uploaded", "queued", "read", "skipped", "failed"]


class MoodleModuleOut(BaseModel):
    module_id: int
    name: str
    module: str
    url: str | None
    text: str | None
    files: list[MoodleFileOut]


class MoodleSectionOut(BaseModel):
    section_id: int
    name: str
    summary: str | None
    modules: list[MoodleModuleOut]


class MoodleAnnouncementOut(BaseModel):
    discussion_id: int
    title: str
    text: str | None
    posted_at: datetime


class MoodleCourseContentOut(BaseModel):
    course_id: int
    content_synced_at: datetime | None
    sections: list[MoodleSectionOut]
    announcements: list[MoodleAnnouncementOut]


class MoodleHitOut(BaseModel):
    kind: Literal["file", "module", "section", "announcement"]
    course_id: int
    course: str
    path: str = Field(description="Course › Section › Module › file, as Moodle shows them")
    title: str
    url: str
    page: int | None = Field(description="The PDF page (slide) of a file's piece; none when not paged")
    heading: str
    text: str
    sha256: str | None = Field(description="The file's sha256; none for course text")
    shared: bool = Field(description="From the course of a member of the user's study group")


class MoodleContentResult(BaseModel):
    files_missing: list[str] = Field(description="sha256 of the listed files the server does not have: upload them")


_TEXT_STATUS = {
    "not_offered": "not_offered",
    None: "not_uploaded",
    "pending": "queued",
    "claimed": "queued",
    "done": "read",
    "skipped": "skipped",
    "failed": "failed",
}


# ---- storage

_COMPLETION_STATES = ("incomplete", "complete", "complete_pass", "complete_fail")


def to_markdown(html: str) -> str | None:
    """Markdown of a fragment of Moodle's HTML; None when it has no text. A fragment that cannot be converted loses its
    text, not the sync."""
    if not html.strip():
        return None
    try:
        text = convert(html, ConversionOptions(extract_images=False, autolinks=False, bullets="-")).content.strip()
    except ConversionError:
        return None
    return text or None


def _all(conn, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        return cur.execute(sql, params).fetchall()


def _put_text(conn, text: str | None) -> str | None:
    """Store a text once; its sha256 is what the rows point to. DO UPDATE (not DO NOTHING) row-locks an existing text until
    commit, so a concurrent `_gc` (SKIP LOCKED) cannot delete a text this transaction is about to reference."""
    if text is None:
        return None
    sha = hashlib.sha256(text.encode()).hexdigest()
    conn.execute(
        "INSERT INTO moodle_texts (sha256, text) VALUES (%s, %s) ON CONFLICT (sha256) DO UPDATE SET text = EXCLUDED.text",
        (sha, text),
    )
    return sha


def _held(conn, innohassle_id: str, course_id: int | None = None) -> list[str]:
    """The hashes of the texts the user's rows (of one course, when given) point to."""
    where = "innohassle_id = %s" + ("" if course_id is None else " AND course_id = %s")
    params = (innohassle_id,) if course_id is None else (innohassle_id, course_id)
    hashes: set[str] = set()
    for table, col in (
        ("moodle_sections", "summary_sha256"),
        ("moodle_modules", "text_sha256"),
        ("moodle_announcements", "text_sha256"),
    ):
        hashes.update(pg.column(conn, f"SELECT DISTINCT {col} FROM {table} WHERE {where} AND {col} IS NOT NULL", params))
    return sorted(hashes)


def _gc(conn, hashes: list[str]) -> None:
    """Delete the texts of `hashes` that no row of any user references. Locked rows (a concurrent upload about to reference
    them) are skipped."""
    if not hashes:
        return
    conn.execute(
        """DELETE FROM moodle_texts WHERE sha256 IN (
               SELECT t.sha256 FROM moodle_texts t WHERE t.sha256 = ANY(%s)
                 AND NOT EXISTS (SELECT 1 FROM moodle_modules m WHERE m.text_sha256 = t.sha256)
                 AND NOT EXISTS (SELECT 1 FROM moodle_sections s WHERE s.summary_sha256 = t.sha256)
                 AND NOT EXISTS (SELECT 1 FROM moodle_announcements a WHERE a.text_sha256 = t.sha256)
               FOR UPDATE SKIP LOCKED)""",
        (hashes,),
    )


def _held_files(conn, innohassle_id: str, course_id: int | None = None) -> list[str]:
    """The sha256 of the files the user's rows (of one course, when given) list."""
    where = "innohassle_id = %s" + ("" if course_id is None else " AND course_id = %s")
    params = (innohassle_id,) if course_id is None else (innohassle_id, course_id)
    return pg.column(conn, f"SELECT DISTINCT sha256 FROM moodle_files WHERE {where} AND sha256 IS NOT NULL", params)


def _gc_files(conn, hashes: list[str]) -> None:
    """Delete the uploaded files of `hashes` that no row of any user lists (their pieces and vectors go with them)."""
    if not hashes:
        return
    conn.execute(
        """DELETE FROM moodle_blobs WHERE sha256 IN (
               SELECT b.sha256 FROM moodle_blobs b WHERE b.sha256 = ANY(%s)
                 AND NOT EXISTS (SELECT 1 FROM moodle_files f WHERE f.sha256 = b.sha256)
               FOR UPDATE SKIP LOCKED)""",
        (hashes,),
    )


def _replace_course_rows(
    conn, table: str, innohassle_id: str, course_id: int, columns: tuple[str, ...], rows: list[tuple]
) -> None:
    """Replace the rows of one course of one user. `table` and `columns` are literals of this module."""
    conn.execute(f"DELETE FROM {table} WHERE innohassle_id = %s AND course_id = %s", (innohassle_id, course_id))
    if not rows:
        return
    marks = ", ".join(["%s"] * (len(columns) + 2))
    with conn.cursor() as cur:
        cur.executemany(
            f"INSERT INTO {table} (innohassle_id, course_id, {', '.join(columns)}) VALUES ({marks}) ON CONFLICT DO NOTHING",
            [(innohassle_id, course_id, *row) for row in rows],
        )


def replace_overview(innohassle_id: str, snapshot: MoodleOverviewIn, study_groups: list[str]) -> list[int]:
    """Replace the user's courses, events and per-course data with the snapshot; what Moodle did not answer stays. Returns
    the ids of the courses whose text was never sent."""
    with pg.connection() as conn:
        known = pg.scalar(conn, "SELECT moodle_user_id FROM moodle_accounts WHERE innohassle_id = %s FOR UPDATE", (innohassle_id,))
        if known is not None and known != snapshot.moodle_user_id:
            old = _held(conn, innohassle_id)
            old_files = _held_files(conn, innohassle_id)
            conn.execute("DELETE FROM moodle_courses WHERE innohassle_id = %s", (innohassle_id,))
            conn.execute("DELETE FROM moodle_events WHERE innohassle_id = %s", (innohassle_id,))
            _gc(conn, old)
            _gc_files(conn, old_files)
        conn.execute(
            "INSERT INTO moodle_accounts (innohassle_id, moodle_user_id, study_groups) VALUES (%s, %s, %s) "
            "ON CONFLICT (innohassle_id) DO UPDATE SET moodle_user_id = EXCLUDED.moodle_user_id, synced_at = now(), "
            "study_groups = EXCLUDED.study_groups",
            (innohassle_id, snapshot.moodle_user_id, study_groups),
        )
        ids = [c.course_id for c in snapshot.courses]
        old = _held(conn, innohassle_id)
        old_files = _held_files(conn, innohassle_id)
        conn.execute(
            "DELETE FROM moodle_courses WHERE innohassle_id = %s AND NOT (course_id = ANY(%s))", (innohassle_id, ids)
        )
        _gc(conn, old)
        _gc_files(conn, old_files)
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO moodle_courses (innohassle_id, course_id, fullname, shortname, starts_at, ends_at) "
                "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (innohassle_id, course_id) DO UPDATE SET "
                "fullname = EXCLUDED.fullname, shortname = EXCLUDED.shortname, starts_at = EXCLUDED.starts_at, "
                "ends_at = EXCLUDED.ends_at",
                [(innohassle_id, c.course_id, c.fullname, c.shortname, c.starts_at, c.ends_at) for c in snapshot.courses],
            )
        if snapshot.events is not None:
            conn.execute("DELETE FROM moodle_events WHERE innohassle_id = %s", (innohassle_id,))
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO moodle_events (innohassle_id, event_id, course_id, group_id, name, description, event_type, "
                    "module, starts_at, duration_seconds, url, pending) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (innohassle_id, event_id) DO NOTHING",
                    [
                        (innohassle_id, e.event_id, e.course_id, e.group_id, e.name, to_markdown(e.description_html),
                         e.event_type, e.module, e.starts_at, e.duration_seconds, e.url, e.pending)
                        for e in snapshot.events
                    ],
                )
        for g in snapshot.grades:
            if g.course_id in ids:
                _replace_course_rows(
                    conn, "moodle_grades", innohassle_id, g.course_id,
                    ("item_id", "position", "name", "item_type", "module", "grade", "grade_min", "grade_max",
                     "grade_text", "percentage_text", "feedback", "graded_at"),
                    [
                        (i.item_id, n, i.name, i.item_type, i.module, i.grade, i.grade_min, i.grade_max, i.grade_text,
                         i.percentage_text, to_markdown(i.feedback_html), i.graded_at)
                        for n, i in enumerate(g.items)
                    ],
                )
        for a in snapshot.assignments:
            if a.course_id in ids:
                _replace_course_rows(
                    conn, "moodle_assignments", innohassle_id, a.course_id,
                    ("assignment_id", "module_id", "name", "description", "opens_at", "due_at", "cutoff_at",
                     "grading_due_at", "max_grade", "submission_status", "grading_status", "grade"),
                    [
                        (i.assignment_id, i.module_id, i.name, to_markdown(i.description_html), i.opens_at, i.due_at,
                         i.cutoff_at, i.grading_due_at, i.max_grade, i.submission_status, i.grading_status,
                         to_markdown(i.grade_html))
                        for i in a.items
                    ],
                )
        for q in snapshot.quizzes:
            if q.course_id in ids:
                _replace_course_rows(
                    conn, "moodle_quizzes", innohassle_id, q.course_id,
                    ("quiz_id", "module_id", "name", "description", "opens_at", "closes_at", "time_limit_seconds",
                     "attempts_allowed", "attempts_used", "best_grade", "max_grade"),
                    [
                        (i.quiz_id, i.module_id, i.name, to_markdown(i.description_html), i.opens_at, i.closes_at,
                         i.time_limit_seconds, i.attempts_allowed, i.attempts_used, i.best_grade, i.max_grade)
                        for i in q.items
                    ],
                )
        for c in snapshot.completion:
            if c.course_id in ids:
                _replace_course_rows(
                    conn, "moodle_completion", innohassle_id, c.course_id, ("module_id", "state", "completed_at"),
                    [(i.module_id, i.state, i.completed_at) for i in c.items],
                )
        for gr in snapshot.groups:
            if gr.course_id in ids:
                _replace_course_rows(
                    conn, "moodle_groups", innohassle_id, gr.course_id, ("group_id", "name"),
                    [(i.group_id, i.name) for i in gr.groups],
                )
        return pg.column(
            conn,
            "SELECT course_id FROM moodle_courses WHERE innohassle_id = %s AND content_synced_at IS NULL ORDER BY course_id",
            (innohassle_id,),
        )


def replace_course_content(innohassle_id: str, course_id: int, content: MoodleCourseContentIn) -> list[str] | None:
    """Replace the text, file names and announcements of one course of the user; None when the user has no such course.
    Returns the sha256 of the course's files whose bytes the server does not have yet (to be uploaded)."""
    with pg.connection() as conn:
        if pg.scalar(
            conn,
            "SELECT 1 FROM moodle_courses WHERE innohassle_id = %s AND course_id = %s FOR UPDATE",
            (innohassle_id, course_id),
        ) is None:
            return None
        old = _held(conn, innohassle_id, course_id)
        old_files = _held_files(conn, innohassle_id, course_id)
        conn.execute("DELETE FROM moodle_sections WHERE innohassle_id = %s AND course_id = %s", (innohassle_id, course_id))
        conn.execute("DELETE FROM moodle_announcements WHERE innohassle_id = %s AND course_id = %s", (innohassle_id, course_id))
        for i, section in enumerate(content.sections):
            conn.execute(
                "INSERT INTO moodle_sections (innohassle_id, course_id, section_id, position, name, summary_sha256, shareable) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (innohassle_id, course_id, section.section_id, i, section.name,
                 _put_text(conn, to_markdown(section.summary_html)), section.shareable),
            )
            for j, module in enumerate(section.modules):
                conn.execute(
                    "INSERT INTO moodle_modules (innohassle_id, course_id, module_id, section_id, position, name, module, "
                    "url, text_sha256, shareable) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    (innohassle_id, course_id, module.module_id, section.section_id, j, module.name, module.module,
                     module.url, _put_text(conn, to_markdown(module.html)), section.shareable and module.shareable),
                )
                if module.files:
                    with conn.cursor() as cur:
                        cur.executemany(
                            "INSERT INTO moodle_files (innohassle_id, course_id, module_id, position, filename, url, "
                            "size_bytes, mime_type, modified_at, sha256) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                            "ON CONFLICT DO NOTHING",
                            [
                                (innohassle_id, course_id, module.module_id, k, f.filename, f.url, f.size_bytes,
                                 f.mime_type, f.modified_at, f.sha256)
                                for k, f in enumerate(module.files)
                            ],
                        )
        for i, a in enumerate(content.announcements):
            conn.execute(
                "INSERT INTO moodle_announcements (innohassle_id, course_id, discussion_id, position, title, text_sha256, "
                "posted_at) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (innohassle_id, course_id, a.discussion_id, i, a.title, _put_text(conn, to_markdown(a.html)), a.posted_at),
            )
        conn.execute(
            "UPDATE moodle_courses SET content_synced_at = now() WHERE innohassle_id = %s AND course_id = %s",
            (innohassle_id, course_id),
        )
        _gc(conn, old)
        _gc_files(conn, old_files)
        return pg.column(
            conn,
            "SELECT DISTINCT f.sha256 FROM moodle_files f WHERE f.innohassle_id = %s AND f.course_id = %s "
            "AND f.sha256 IS NOT NULL AND NOT EXISTS (SELECT 1 FROM moodle_blobs b WHERE b.sha256 = f.sha256) ORDER BY 1",
            (innohassle_id, course_id),
        )


def overview(innohassle_id: str) -> MoodleOverviewOut | None:
    with pg.connection() as conn:
        account = _all(conn, "SELECT moodle_user_id, synced_at FROM moodle_accounts WHERE innohassle_id = %s", (innohassle_id,))
        if not account:
            return None

        def select(table: str, order: str) -> list[dict[str, Any]]:
            return _all(conn, f"SELECT * FROM {table} WHERE innohassle_id = %s ORDER BY {order}", (innohassle_id,))

        events = []
        for r in select("moodle_events", "starts_at, event_id"):
            r["ends_at"] = r["starts_at"] + timedelta(seconds=r["duration_seconds"])
            events.append(MoodleEventOut(**r))
        return MoodleOverviewOut(
            moodle_user_id=account[0]["moodle_user_id"],
            synced_at=account[0]["synced_at"],
            courses=[MoodleCourseOut(**r) for r in select("moodle_courses", "fullname, course_id")],
            events=events,
            grades=[MoodleGradeOut(**r) for r in select("moodle_grades", "course_id, position")],
            assignments=[MoodleAssignmentOut(**r) for r in select("moodle_assignments", "due_at NULLS LAST, assignment_id")],
            quizzes=[MoodleQuizOut(**r) for r in select("moodle_quizzes", "closes_at NULLS LAST, quiz_id")],
            completion=[
                MoodleCompletionOut(**{**r, "state": _COMPLETION_STATES[r["state"]]})
                for r in select("moodle_completion", "course_id, module_id")
            ],
            groups=[MoodleGroupOut(**r) for r in select("moodle_groups", "course_id, name")],
        )


def course_content(innohassle_id: str, course_id: int) -> MoodleCourseContentOut | None:
    with pg.connection() as conn:
        course = _all(
            conn,
            "SELECT content_synced_at FROM moodle_courses WHERE innohassle_id = %s AND course_id = %s",
            (innohassle_id, course_id),
        )
        if not course:
            return None
        key = (innohassle_id, course_id)
        files: dict[int, list[MoodleFileOut]] = {}
        for r in _all(
            conn,
            "SELECT f.*, b.status AS blob_status FROM moodle_files f LEFT JOIN moodle_blobs b ON b.sha256 = f.sha256 "
            "WHERE f.innohassle_id = %s AND f.course_id = %s ORDER BY f.module_id, f.position",
            key,
        ):
            status = _TEXT_STATUS["not_offered" if r["sha256"] is None else r["blob_status"]]
            files.setdefault(r["module_id"], []).append(MoodleFileOut(**r, text_status=status))
        modules: dict[int, list[MoodleModuleOut]] = {}
        for r in _all(
            conn,
            "SELECT m.module_id, m.section_id, m.name, m.module, m.url, t.text FROM moodle_modules m "
            "LEFT JOIN moodle_texts t ON t.sha256 = m.text_sha256 "
            "WHERE m.innohassle_id = %s AND m.course_id = %s ORDER BY m.position",
            key,
        ):
            modules.setdefault(r["section_id"], []).append(MoodleModuleOut(**r, files=files.get(r["module_id"], [])))
        sections = [
            MoodleSectionOut(
                section_id=r["section_id"], name=r["name"], summary=r["text"], modules=modules.get(r["section_id"], [])
            )
            for r in _all(
                conn,
                "SELECT s.section_id, s.name, t.text FROM moodle_sections s "
                "LEFT JOIN moodle_texts t ON t.sha256 = s.summary_sha256 "
                "WHERE s.innohassle_id = %s AND s.course_id = %s ORDER BY s.position",
                key,
            )
        ]
        announcements = [
            MoodleAnnouncementOut(**r)
            for r in _all(
                conn,
                "SELECT a.discussion_id, a.title, t.text, a.posted_at FROM moodle_announcements a "
                "LEFT JOIN moodle_texts t ON t.sha256 = a.text_sha256 "
                "WHERE a.innohassle_id = %s AND a.course_id = %s ORDER BY a.position",
                key,
            )
        ]
        return MoodleCourseContentOut(
            course_id=course_id,
            content_synced_at=course[0]["content_synced_at"],
            sections=sections,
            announcements=announcements,
        )


def forget(innohassle_id: str) -> None:
    """Delete everything of the user; a text stays only while a row of another user references it."""
    with pg.connection() as conn:
        old = _held(conn, innohassle_id)
        old_files = _held_files(conn, innohassle_id)
        conn.execute("DELETE FROM moodle_accounts WHERE innohassle_id = %s", (innohassle_id,))
        _gc(conn, old)
        _gc_files(conn, old_files)


# ---- who reads what: the user's own rows, and what their study group shares

@dataclass(frozen=True)
class Scope:
    """One course read for an asker: `owner` is the `innohassle_id` whose rows are read (never put in any output), `own` that it
    is the asker. A non-own scope shows only shareable modules, announcements and dates (see the rule in the module docstring)."""

    owner: str
    course_id: int
    own: bool


def scopes(innohassle_id: str | None, study_groups: Sequence[str], course_ids: list[int] | None = None) -> list[Scope]:
    """The courses the asker reads: their own, and those of other users who share with one of `study_groups` (the freshest
    synced owner of a course; the asker's own rows win). `course_ids`: only these."""
    found: list[Scope] = []
    with pg.connection() as conn:
        if innohassle_id is not None:
            found = [
                Scope(innohassle_id, r["course_id"], True)
                for r in _all(conn, "SELECT course_id FROM moodle_courses WHERE innohassle_id = %s ORDER BY course_id", (innohassle_id,))
            ]
        if study_groups:
            found += [
                Scope(r["innohassle_id"], r["course_id"], False)
                for r in _all(
                    conn,
                    """SELECT DISTINCT ON (c.course_id) c.innohassle_id, c.course_id
                       FROM moodle_courses c JOIN moodle_accounts a USING (innohassle_id)
                       WHERE a.study_groups && %(g)s::text[] AND c.innohassle_id IS DISTINCT FROM %(u)s
                         AND c.content_synced_at IS NOT NULL AND NOT (c.course_id = ANY(%(own)s))
                       ORDER BY c.course_id, c.content_synced_at DESC""",
                    {"g": list(study_groups), "u": innohassle_id, "own": [s.course_id for s in found]},
                )
            ]
    if course_ids is not None:
        found = [s for s in found if s.course_id in course_ids]
    return found


SCOPE_CTE = "WITH s(innohassle_id, course_id, own) AS (SELECT * FROM unnest(%(o)s::text[], %(c)s::bigint[], %(w)s::bool[]))"


def scope_arrays(found: list[Scope]) -> dict[str, list]:
    """The parameters of SCOPE_CTE."""
    return {"o": [s.owner for s in found], "c": [s.course_id for s in found], "w": [s.own for s in found]}


def matching_course_ids(found: list[Scope], words: str) -> list[int]:
    """The courses in scope whose full or short name contains `words`."""
    if not found:
        return []
    escaped = words.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    with pg.connection() as conn:
        return pg.column(
            conn,
            SCOPE_CTE + """ SELECT DISTINCT c.course_id FROM s JOIN moodle_courses c USING (innohassle_id, course_id)
                            WHERE c.fullname ILIKE %(p)s OR c.shortname ILIKE %(p)s ORDER BY 1""",
            {**scope_arrays(found), "p": f"%{escaped}%"},
        )


_SHAREABLE_MODULE = (
    "(s.own OR EXISTS (SELECT 1 FROM moodle_modules m WHERE m.innohassle_id = s.innohassle_id AND m.course_id = s.course_id "
    "AND m.module_id = {module_id} AND m.shareable))"
)


def deadlines(
    innohassle_id: str | None, found: list[Scope], since: datetime, until: datetime, *, filtered: bool = False
) -> list[dict]:
    """Assignments, quizzes and other events due in [since, until): `kind`, `course`, `shared` and the kind's fields, with
    datetimes as stored. Assignments and quizzes of a shared course need a shareable module and carry no status of the owner;
    events are the asker's own, and those Moodle mirrors from assignments and quizzes are left out. `filtered`: the scopes
    are a course filter, so events with no course are left out."""
    items: list[dict] = []
    with pg.connection() as conn:
        if found:
            args = {**scope_arrays(found), "since": since, "until": until}
            for r in _all(
                conn,
                SCOPE_CTE + f""" SELECT s.own, c.fullname AS course, a.name, a.due_at, a.cutoff_at, a.module_id,
                       CASE WHEN s.own THEN a.submission_status END AS submission_status,
                       CASE WHEN s.own THEN a.grading_status END AS grading_status
                    FROM s JOIN moodle_assignments a USING (innohassle_id, course_id)
                    JOIN moodle_courses c USING (innohassle_id, course_id)
                    WHERE a.due_at >= %(since)s AND a.due_at < %(until)s AND {_SHAREABLE_MODULE.format(module_id="a.module_id")}""",
                args,
            ):
                items.append({
                    "kind": "assignment", "course": r["course"], "shared": not r["own"], "name": r["name"], "due": r["due_at"],
                    "cutoff": r["cutoff_at"], "submission_status": r["submission_status"], "grading_status": r["grading_status"],
                    "url": f"{MOODLE_URL}mod/assign/view.php?id={r['module_id']}",
                })
            for r in _all(
                conn,
                SCOPE_CTE + f""" SELECT s.own, c.fullname AS course, q.name, q.closes_at, q.opens_at, q.module_id,
                       q.attempts_allowed, q.max_grade,
                       CASE WHEN s.own THEN q.attempts_used END AS attempts_used,
                       CASE WHEN s.own THEN q.best_grade END AS best_grade
                    FROM s JOIN moodle_quizzes q USING (innohassle_id, course_id)
                    JOIN moodle_courses c USING (innohassle_id, course_id)
                    WHERE q.closes_at >= %(since)s AND q.closes_at < %(until)s AND {_SHAREABLE_MODULE.format(module_id="q.module_id")}""",
                args,
            ):
                items.append({
                    "kind": "quiz", "course": r["course"], "shared": not r["own"], "name": r["name"], "due": r["closes_at"],
                    "opens": r["opens_at"], "attempts_allowed": r["attempts_allowed"], "max_grade": r["max_grade"],
                    "attempts_used": r["attempts_used"], "best_grade": r["best_grade"],
                    "url": f"{MOODLE_URL}mod/quiz/view.php?id={r['module_id']}",
                })
        if innohassle_id is not None:
            for r in _all(
                conn,
                """SELECT e.name, e.event_type, e.starts_at, e.pending, e.url, COALESCE(c.fullname, '') AS course
                   FROM moodle_events e
                   LEFT JOIN moodle_courses c ON c.innohassle_id = e.innohassle_id AND c.course_id = e.course_id
                   WHERE e.innohassle_id = %(u)s AND e.starts_at >= %(since)s AND e.starts_at < %(until)s
                     AND COALESCE(e.module, '') NOT IN ('assign', 'quiz')
                     AND (e.course_id = ANY(%(own)s) OR (e.course_id IS NULL AND NOT %(filtered)s))""",
                {"u": innohassle_id, "since": since, "until": until, "own": [s.course_id for s in found if s.own], "filtered": filtered},
            ):
                items.append({
                    "kind": "event", "course": r["course"], "shared": False, "name": r["name"], "event_type": r["event_type"],
                    "due": r["starts_at"], "pending": r["pending"], "url": r["url"],
                })
    return items


def announcements(found: list[Scope], since: datetime, until: datetime) -> list[dict]:
    """Announcements posted in [since, until) in the courses in scope (shared ones too), newest first."""
    if not found:
        return []
    with pg.connection() as conn:
        rows = _all(
            conn,
            SCOPE_CTE + """ SELECT s.own, a.course_id, c.fullname, a.discussion_id, a.title, a.posted_at, t.text
                            FROM s JOIN moodle_announcements a USING (innohassle_id, course_id)
                            JOIN moodle_courses c USING (innohassle_id, course_id)
                            LEFT JOIN moodle_texts t ON t.sha256 = a.text_sha256
                            WHERE a.posted_at >= %(since)s AND a.posted_at < %(until)s ORDER BY a.posted_at DESC""",
            {**scope_arrays(found), "since": since, "until": until},
        )
    return [
        {"course": r["fullname"], "shared": not r["own"], "title": r["title"], "posted": r["posted_at"], "text": r["text"] or "",
         "url": f"{MOODLE_URL}mod/forum/discuss.php?d={r['discussion_id']}"}
        for r in rows
    ]


def courses(found: list[Scope]) -> list[dict]:
    """The courses in scope by name; completion counts only for the asker's own."""
    if not found:
        return []
    count = (
        "CASE WHEN s.own THEN (SELECT count(*) FROM moodle_completion k WHERE k.innohassle_id = s.innohassle_id "
        "AND k.course_id = s.course_id{states}) END"
    )
    with pg.connection() as conn:
        rows = _all(
            conn,
            SCOPE_CTE + f""" SELECT s.own, c.fullname, c.shortname, c.starts_at, c.ends_at, c.content_synced_at,
                               {count.format(states=" AND k.state IN (1, 2)")} AS completed, {count.format(states="")} AS tracked
                            FROM s JOIN moodle_courses c USING (innohassle_id, course_id) ORDER BY c.fullname, s.course_id""",
            scope_arrays(found),
        )
    return [
        {"course": r["fullname"], "shared": not r["own"], "shortname": r["shortname"], "starts": r["starts_at"], "ends": r["ends_at"],
         "content_synced": r["content_synced_at"] is not None, "completed": r["completed"], "tracked": r["tracked"]}
        for r in rows
    ]
