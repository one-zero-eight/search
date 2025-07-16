import asyncio
import json
from datetime import datetime

import httpx
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from src.api.logging_ import logger
from src.config import settings
from src.ml_service.openai_tools import BOOK_MUSIC_ROOM_FN
from src.modules.ml.schemas import MLActResponse

from .actions import MusicRoomSlot, music_room_act
from .prompt import build_prompt

client = AsyncOpenAI(
    api_key=settings.ml_service.openrouter_api_key.get_secret_value(),
    base_url=settings.ml_service.llm_api_base,
)


async def generate_answer(
    question: str,
    contexts: list[str],
    lang_name: str | None = None,
) -> str:
    prompt = build_prompt(
        question,
        contexts,
        lang_name,
    )
    messages = [
        ChatCompletionSystemMessageParam(role="system", content=settings.ml_service.system_prompt),
        ChatCompletionUserMessageParam(role="user", content=prompt),
    ]

    logger.info(f"system prompt: {messages[0]['content']}")
    logger.info(f"user prompt: {messages[1]['content']}")

    resp = await client.chat.completions.create(
        model=settings.ml_service.llm_model,
        messages=messages,
        max_tokens=2048,
        temperature=0.2,
        top_p=1.0,
    )
    return resp.choices[0].message.content


async def act(user_input: str, token: str) -> MLActResponse:
    extra_context = f"\nCurrent time: {datetime.now().strftime('%Y-%m-%d %H:%M %A')}\n"
    messages: list[ChatCompletionMessageParam] = [{"role": "user", "content": user_input + extra_context}]
    logger.info(f"user prompt: {messages[0]['content']}")

    completion = await client.chat.completions.create(
        model=settings.ml_service.llm_model,
        messages=messages,
        tools=[BOOK_MUSIC_ROOM_FN],
        tool_choice="auto",
    )
    msg = completion.choices[0].message
    answer = msg.content

    logger.info(type(msg))

    if msg.tool_calls:
        for tool_call in msg.tool_calls:
            if tool_call.function.name == "book_music_room":
                messages.append(msg)

                kwargs = json.loads(tool_call.function.arguments)
                start_dt = datetime.fromisoformat(kwargs["start_datetime"])
                end_dt = datetime.fromisoformat(kwargs["end_datetime"])

                slot = MusicRoomSlot(time_start=start_dt, time_end=end_dt)

                try:
                    booking = await music_room_act.create_booking(slot, token)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": (f"The music room is booked: {booking}."),
                        }
                    )
                    logger.info(f"booking: {booking}")
                except Exception as e:
                    if isinstance(e, httpx.HTTPStatusError):
                        error_text = f"{e} ({e.response.text})"
                    else:
                        error_text = str(e)
                    logger.error(f"Failed to book music room: {e}")
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": (
                                f"The user tried to book a music room with"
                                f"{slot.time_start.strftime('%Y-%m-%d%H:%M')} to "
                                f"{slot.time_end.strftime('%Y-%m-%d%H:%M')}, "
                                f"but the booking failed: {error_text}. Please politely inform the user about this."
                            ),
                        }
                    )

                completion2 = await client.chat.completions.create(
                    model=settings.ml_service.llm_model,
                    messages=messages,
                    tools=[BOOK_MUSIC_ROOM_FN],
                    tool_choice="auto",
                )
                answer = completion2.choices[0].message.content
    return MLActResponse(
        answer=answer,
        tool_calls=[tool_call.model_dump(mode="json") for tool_call in msg.tool_calls or []],
        messages=messages,
    )


if __name__ == "__main__":
    system = """
    You are a helpful multilingual assistant.
    Your ONLY rule is: ALWAYS answer in the SAME language as the input question.
    If the user writes in Russian — answer in Russian.
    If the user writes in English — answer in English. Etc.

    Do not explain your behavior.
    Do not translate the question.
    Do not ask what language it is.

    Just answer in the same language as the input. """

    contexts = [
        "3 600 rubles, One room suite, 21 м², • 2 single beds, • Working area , • Mini kitchen, Designed to accommodate two guests",
        "4 400 rubles, Two-room Suite, 45 м², • 2 single beds, • Working area, • Lounge with Mini kitchen, • A TV, • An armchair and a sofa, Designed to accommodate two guests",
    ]
    question = "How much does a room for 2 people cost?"
    # r = asyncio.run(generate_answer("question", ["context 1", "context 2"]))
    # print(r)

    answer = asyncio.run(generate_answer(question, contexts))
    print(answer)
