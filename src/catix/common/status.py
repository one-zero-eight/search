"""What the site is told while the agent works on a question: the API sends `status` events with a phase code, and the site
writes the words (and picks the mascot's face) in the user's language. The code says what the agent does, not which tool it
uses: the user's data sources stay out of it."""

from typing import Literal

Phase = Literal["checking", "thinking", "searching", "reading", "working", "preparing_action", "writing"]

CHECKING: Phase = "checking"  # the guardrail screens the message
THINKING: Phase = "thinking"  # the model reasons before it calls a tool or starts the answer
WRITING: Phase = "writing"  # the answer text is being written

# The phase of a tool while it runs, between the model deciding to call it and its result.
TOOL_PHASE: dict[str, Phase] = {
    "search": "searching",
    "search_api_tools": "searching",
    "search_web": "searching",
    "read_wiki": "reading",
    "read_chats": "reading",
    "read_attachment": "reading",
    "read_web_page": "reading",
    "call_api_tool": "working",
    "get_my_ai_calendar": "working",
    "get_my_schedule": "working",
    "get_my_moodle": "working",
    "add_to_ai_calendar": "preparing_action",
    "update_ai_calendar": "preparing_action",
    "remove_from_ai_calendar": "preparing_action",
}
