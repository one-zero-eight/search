"""leave_feedback: the asker's feedback (a bug, a wish, an idea, a chat to add to the search) sent to the InNoHassle team
through the one-zero-eight Google Form, the form of the site's "Leave feedback" button. Only the site's signed-in user can
send it, after approving the exact text (native approval, FEEDBACK_APPROVAL); the form's contact field gets their Innopolis
email and Telegram id."""

import logging

import httpx
from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from catix.agent.approval import WAITING_FOR_USER
from catix.agent.calendar_approval import _calendar_business_args
from catix.settings import settings

log = logging.getLogger("catix.feedback")

FORM_LINK = "https://forms.gle/2vMmu4vSoVShvbMw6"  # the same form, as the site's button opens it
TIMEOUT = httpx.Timeout(15, connect=5)


class LeaveFeedbackArgs(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    subject: str = Field(min_length=1, max_length=100, description="What it is about, in a few words: the service or the idea "
                         "('catix', 'room booking', 'music room bot', 'a chat to add', 'new idea').")
    feedback: str = Field(min_length=1, max_length=4000, description="The user's feedback in their own words and language: what "
                          "happened or what they want; with the chat's link or name when they propose a chat.")


def _sender(runtime) -> tuple[str | None, str | None]:
    """The form's contact field for the site's signed-in asker (their email, and Telegram id when linked); else None and why."""
    context = getattr(runtime, "context", None)
    email = getattr(context, "innohassle_email", None)
    token = getattr(context, "innohassle_token", None)
    if not isinstance(email, str) or not email.strip() or not token or not token.get_secret_value().strip():
        return None, "Feedback can be left only by a user signed in on innohassle.ru; nothing was sent."
    telegram_id = getattr(context, "user_telegram_id", None)
    return (f"{email}, Telegram id {telegram_id}" if isinstance(telegram_id, int) else email), None


def _submit(data: dict) -> httpx.Response:
    return httpx.post(settings.feedback_form_url, data=data, timeout=TIMEOUT, follow_redirects=False)


@tool(args_schema=LeaveFeedbackArgs)
def leave_feedback(subject: str, feedback: str, runtime: ToolRuntime) -> dict:
    """Send the user's feedback to the InNoHassle team (one-zero-eight): a bug, a wish, an idea, or a chat they want added to
    the search. Only when the user asks to leave feedback or to pass something on to the developers; write it in their
    words. The user approves the exact text before it is sent; send it once."""
    try:
        args = LeaveFeedbackArgs(subject=subject, feedback=feedback)
    except ValidationError as e:
        return {"done": False, "error": str(e)}
    contact, why = _sender(runtime)
    if contact is None:
        return {"done": False, "error": why, "form": FORM_LINK}
    try:
        response = _submit({settings.feedback_subject_field: args.subject, settings.feedback_text_field: args.feedback,
                            settings.feedback_contact_field: contact})
    except (httpx.ConnectError, httpx.ConnectTimeout):
        log.warning("feedback form unreachable")
        return {"done": False, "error": "The feedback form could not be reached; nothing was sent.", "form": FORM_LINK}
    except httpx.HTTPError:
        log.warning("feedback form outcome unknown")
        return _unknown()
    if response.status_code == 200:
        return {"done": True, "note": "Recorded in the InNoHassle feedback form."}
    if response.status_code >= 500:
        return _unknown()
    log.warning("feedback form refused: HTTP %s", response.status_code)
    return {"done": False, "error": f"The feedback form refused it (HTTP {response.status_code}); nothing was sent.",
            "form": FORM_LINK}


def _unknown() -> dict:
    return {"done": None, "outcome": "unknown",
            "error": "Sending could not be confirmed; the feedback may have been recorded. Do not send it again."}


def _valid(request) -> bool:
    try:
        LeaveFeedbackArgs.model_validate(_calendar_business_args(request.tool_call["args"]))
    except ValidationError:
        return False
    return _sender(request.runtime)[0] is not None


FEEDBACK_APPROVAL = {"leave_feedback": {"allowed_decisions": ["approve", "edit", "reject"], "description": WAITING_FOR_USER, "when": _valid}}
FEEDBACK_TOOLS = [leave_feedback]
