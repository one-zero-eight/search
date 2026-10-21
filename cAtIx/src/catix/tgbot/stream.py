"""Shows the answer in Telegram while the model is still writing it.

Telegram's `sendMessageDraft` streams a partial message into a private chat: a draft with the same id is updated
in place, it lives 30 seconds, and the final text must still be sent as a normal message (the draft then disappears).
It does not exist for groups, which keep the typing indicator and one message at the end.

Only the text of the supervisor's last model call is shown (`lc_agent_name` and `langgraph_node` in the metadata of a
streamed piece say whose it is): the screen's JSON verdict and the helpers' reports are never shown. A call that is about
to use a tool has no text, or, when the model writes the tool call as text, text starting with <tool_call>: that is never
shown either. Between the question and the answer the user sees what is going on: the check, which helper was asked, which
tool it runs (the tool reports that as a "custom" event), then the writing of the answer.
"""

import logging
import random
import re
import time
from collections.abc import Callable

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from langchain_core.messages import AIMessageChunk, ToolMessage

from catix.agent.core import SUPERVISOR_NAME

log = logging.getLogger("catix.stream")

INTERVAL_SECONDS = 0.7  # Between drafts: Telegram limits how fast a bot may send.
MAX_CHARS = 4000  # A message holds 4096; the markup added by the HTML conversion needs room.

# What the user sees while a tool runs, between the model deciding to call it and the answer starting.
CHECKING = "🛡 Проверяю запрос…"
WRITING = "✍️ Формулирую ответ…"
STATUS = {
    "ask_chats": "💬 Спрашиваю помощника по чатам…",
    "ask_campus": "🧭 Спрашиваю помощника по кампусу…",
    "search_chats": "🔎 Ищу в базе знаний…",
    "search_userbot_chats": "🔎 Ищу в чатах…",
    "get_schedule": "🗓 Смотрю расписание…",
    "get_clubs": "🎯 Смотрю клубы…",
    "get_university_events": "📅 Смотрю события…",
    "find_room": "🗺 Ищу на карте…",
    "query_db": "🧮 Считаю по базе сообщений…",
}

REF_GROUP = re.compile(r"\[\s*m\d+(?:\s*[,;]\s*m\d+)*\s*\]")
PARTIAL_REF = re.compile(r"\[[m\d,;\s]*$")  # "[m12" at the end: the ref is still being written


def partial_text(text: str) -> str:
    """What may be shown of an unfinished answer: source refs (not numbered yet) and a half-written one are hidden."""
    return PARTIAL_REF.sub("", REF_GROUP.sub("", text)).strip()


class DraftStreamer:
    def __init__(self, bot: Bot, chat_id: int, thread_id: int | None, render: Callable[[str], str]) -> None:
        self.bot, self.chat_id, self.thread_id, self.render = bot, chat_id, thread_id, render
        self.draft_id = random.randint(1, 2**31 - 1)  # Non-zero; the same id makes the updates animated.
        self.enabled = True
        self._call_id: str | None = None
        self._text = ""
        self._shown = ""
        self._status = ""
        self._last = 0.0

    async def _send(self, text: str, *, html: bool) -> None:
        try:
            await self.bot.send_message_draft(
                chat_id=self.chat_id,
                draft_id=self.draft_id,
                message_thread_id=self.thread_id,
                text=text,
                parse_mode=ParseMode.HTML if html else None,
            )
        except TelegramAPIError as e:
            log.warning("message drafts are not available here, streaming is off for this answer: %s", e)
            self.enabled = False
            return
        self._last = time.monotonic()

    async def start(self) -> None:
        """The first thing the user sees: the screen is checking the question."""
        self._status = CHECKING
        await self._send(CHECKING, html=False)

    async def _show_status(self, status: str | None) -> None:
        if self.enabled and status and status != self._status:
            self._status = status
            await self._send(status, html=False)

    async def feed_custom(self, event) -> None:
        """A "custom" event of the stream: a helper agent reports the tool it is about to run (`{"tool": name}`)."""
        if isinstance(event, dict):
            await self._show_status(STATUS.get(event.get("tool") or ""))

    async def feed(self, chunk, metadata: dict | None = None) -> None:
        """One streamed piece: a part of a model call (AIMessageChunk) or a tool result, with its metadata."""
        if isinstance(chunk, ToolMessage):  # A helper came back: the supervisor now writes the answer.
            if chunk.name in (n for n in STATUS if n.startswith("ask_")):
                await self._show_status(WRITING)
            return
        # The user's message and other things in the stream do not count: only the model's text does.
        if not self.enabled or not isinstance(chunk, AIMessageChunk):
            return
        if metadata is not None and (
            metadata.get("langgraph_node") != "model" or metadata.get("lc_agent_name") != SUPERVISOR_NAME
        ):
            return  # The screen's verdict, the summary, a helper's own calls: not the answer.
        if chunk.tool_call_chunks:
            await self._show_status(STATUS.get(chunk.tool_call_chunks[0].get("name") or ""))
            return
        if chunk.id != self._call_id:  # A new model call begins: its text starts from zero.
            self._call_id, self._text = chunk.id, ""
        self._text += chunk.text
        text = partial_text(self._text)
        if not text or "<tool_call>" in self._text or text == self._shown:
            return
        if time.monotonic() - self._last >= INTERVAL_SECONDS:
            await self._send(self.render(text[:MAX_CHARS]), html=True)
            self._shown = text


async def run(agent, inputs: dict, config: dict, context, streamer: DraftStreamer | None) -> dict:
    """Run the agent and return its final state (`messages`, `sources`); with a streamer, show the answer as it is written."""
    if streamer is None:
        return await agent.ainvoke(inputs, config, context=context)
    await streamer.start()
    state: dict = {"messages": []}
    async for mode, data in agent.astream(inputs, config, context=context, stream_mode=["messages", "values", "custom"]):
        if mode == "messages":
            await streamer.feed(*data)
        elif mode == "custom":
            await streamer.feed_custom(data)
        elif mode == "values":
            state = data
    return state
