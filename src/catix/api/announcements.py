"""Schedule changes found in the user's chats (worker/changes.py): `GET /announcements` lists them (oldest first),
`POST /announcements/{change_id}/calendar` applies one to the user's AI Calendar. Scope is the user's verified study groups,
as for /sources."""

from fastapi import APIRouter, HTTPException, Response

from catix import groups, personal_calendar
from catix.api.auth import VerifiedDep
from catix.api.schemas import AddedAnnouncement, Announcement, AnnouncementSource
from catix.worker import changes

router = APIRouter(prefix="/announcements", tags=["Announcements"])


def _chat_ids(user) -> set[int]:
    verified = groups.website_groups(user.token.get_secret_value() if user.token else None)
    return groups.website_chat_ids(verified)


@router.get("", response_model=list[Announcement])
def list_announcements(user: VerifiedDep, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    return [
        Announcement(
            id=view.id,
            kind=view.kind,
            subject=view.subject,
            summary=view.summary,
            starts_at=view.starts_at,
            ends_at=end,
            end_suggested=suggested,
            all_day=view.all_day,
            room=view.room,
            found_at=view.created_at,
            source=AnnouncementSource(
                chat_title=view.chat_title,
                link=view.link or view.chat_link,
                sent_at=view.date,
                sender_name=view.sender_name,
                text=view.text[:600],
            ),
        )
        for view, end, suggested in changes.feed(_chat_ids(user))
    ]


@router.post("/{change_id}/calendar", responses={404: {"description": "No such announcement, or not in the user's chats"}})
def apply_announcement(user: VerifiedDep, change_id: int) -> AddedAnnouncement:
    """Put the change in the user's calendar: a new event, or a move, room change or removal of the one they have. Twice is once."""
    key = personal_calendar.account_key(user.innohassle_id, user.telegram_id)
    result = changes.add_to_calendar(key, change_id, chat_ids=_chat_ids(user))
    if result is None:
        raise HTTPException(404, "No such announcement")
    action, title = result
    return AddedAnnouncement(change_id=change_id, action=action, title=title)
