import json
from datetime import datetime

import httpx
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
)

from src.api.logging_ import logger
from src.config import settings
from src.ml_service.openai_tools import (
    BOOK_MUSIC_ROOM_FN,
    CANCEL_BOOKING_FN,
    LIST_MY_BOOKINGS_FN,
)
from src.modules.ml.schemas import MLActResponse

from .actions import MusicRoomSlot, music_room_act

client = AsyncOpenAI(
    api_key=settings.ml_service.openrouter_api_key.get_secret_value(),
    base_url=settings.ml_service.llm_api_base,
)


async def act(user_input: str, token: str) -> MLActResponse:
    extra_context = f"\nCurrent time: {datetime.now().strftime('%Y-%m-%d %H:%M %A')}\n"
    messages: list[ChatCompletionMessageParam] = [{"role": "user", "content": user_input + extra_context}]
    logger.info(f"user prompt: {messages[0]['content']}")

    tools = [BOOK_MUSIC_ROOM_FN, LIST_MY_BOOKINGS_FN, CANCEL_BOOKING_FN]
    answer = None
    tool_calls = []
    max_loops = 5
    loop_count = 0

    while True:
        if loop_count >= max_loops:
            logger.warning(f"Max tool call loop count ({max_loops}) reached, breaking to avoid infinite loop.")
            break
        loop_count += 1
        completion = await client.chat.completions.create(
            model=settings.ml_service.llm_model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        msg = completion.choices[0].message
        answer = msg.content
        messages.append(msg)

        if not msg.tool_calls:
            break

        tool_calls.extend(msg.tool_calls)

        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            kwargs = json.loads(tool_call.function.arguments)

            if name == "book_music_room":
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

            elif name == "list_my_bookings":
                try:
                    bookings = await music_room_act.list_my_bookings(token)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": (f"List of bookings: {json.dumps(bookings)}."),
                        }
                    )

                    if not bookings:
                        messages.append(
                            {
                                "role": "system",
                                "content": (
                                    "The user has no bookings in the music room."
                                    "Please politely inform the user about this."
                                ),
                            }
                        )

                    logger.info(f"bookings: {json.dumps(bookings)}")
                except Exception as e:
                    if isinstance(e, httpx.HTTPStatusError):
                        error_text = f"{e} ({e.response.text})"
                    else:
                        error_text = str(e)
                    logger.error(f"Failed to list bookings: {e}")
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": (
                                f"The user tried to see their bookings"
                                f"but the action failed: {error_text}. Please politely inform the user about this."
                            ),
                        }
                    )

            elif name == "cancel_booking":
                start_dt = datetime.fromisoformat(kwargs["time_start"])
                bookings = await music_room_act.list_my_bookings(token)
                target = next((b for b in bookings if b["time_start"] == start_dt.isoformat()), None)
                logger.info(f"target: {target}")
                if not target:
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": (f"Canceled: {False}."),
                        }
                    )
                    messages.append(
                        {
                            "role": "system",
                            "content": (
                                "The user has no bookings in the music room.Please politely inform the user about this."
                            ),
                        }
                    )
                else:
                    booking_id = target["id"]

                    logger.info(f"booking id: {booking_id}")

                    try:
                        success = await music_room_act.cancel_booking(booking_id, token)
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": (f"Canceled: {success}."),
                            }
                        )
                        messages.append(
                            {
                                "role": "system",
                                "content": (
                                    "The user cancels his booking in the music room."
                                    "Please politely inform the user about this."
                                ),
                            }
                        )

                        logger.info(f"canceled: {success}")
                    except Exception as e:
                        if isinstance(e, httpx.HTTPStatusError):
                            error_text = f"{e} ({e.response.text})"
                        else:
                            error_text = str(e)
                        logger.error(f"Failed to cancel booking: {e}")
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": (
                                    f"The user tried to cancel a booking"
                                    f"but the action failed: {error_text}. Please politely inform the user about this."
                                ),
                            }
                        )

    return MLActResponse(
        answer=answer,
        tool_calls=[tool_call.model_dump(mode="json") for tool_call in tool_calls],
        messages=messages,
    )
