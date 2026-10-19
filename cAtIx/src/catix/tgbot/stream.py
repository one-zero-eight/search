"""Shows the answer in Telegram while the model is still writing it.

Telegram's `sendMessageDraft` streams a partial message into a private chat: a draft with the same id is updated
in place, it lives 30 seconds, and the final text must still be sent as a normal message (the draft then disappears).
It does not exist for groups, which keep the typing indicator and one message at the end.

Only the text of the last model call is shown. A call that is about to use a tool has no text, or, when the model
writes the tool call as text, text starting with <tool_call>: that is never shown.
"""

import logging
import random
import re
import time
from collections.abc import Callable

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from langchain_core.messages import AIMessageChunk

log = logging.getLogger("catix.stream")

INTERVAL_SECONDS = 0.7  # Between drafts: Telegram limits how fast a bot may send.
MAX_CHARS = 4000  # A message holds 4096; the markup added by the HTML conversion needs room.

# What the user sees while a tool runs, between the model deciding to call it and the answer starting.
STATUS = {
    "search_chats": "🔎 Ищу в чатах…",
    "search_userbot_chats": "🔎 Ищу в больших чатах через Telegram…",
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
        """An empty draft shows Telegram's "Thinking…" placeholder."""
        await self._send("", html=False)

    async def feed(self, chunk) -> None:
        """One streamed piece of a model call (an AIMessageChunk)."""
        # The stream also carries the tools' results (ToolMessage) and the user's message: only the model's text counts.
        if not self.enabled or not isinstance(chunk, AIMessageChunk):
            return
        if chunk.tool_call_chunks:
            status = STATUS.get(chunk.tool_call_chunks[0].get("name") or "")
            if status and status != self._status:
                self._status = status
                await self._send(status, html=False)
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
    async for mode, data in agent.astream(inputs, config, context=context, stream_mode=["messages", "values"]):
        if mode == "messages":
            await streamer.feed(data[0])
        elif mode == "values":
            state = data
    return state
