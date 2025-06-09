from fastapi import APIRouter, status

from src.api.dependencies import VerifiedDep
from src.modules.telegram.schemas import DBMessageSchema, MessageSchema
from src.storages.mongo import Message

router = APIRouter(prefix="/telegram", tags=["Telegram"])


@router.post("/messages", response_model=DBMessageSchema, status_code=status.HTTP_201_CREATED)
async def save_or_update_message(_: VerifiedDep, message: MessageSchema):
    """Determining whether to save the message or overwrite it"""
    as_dict = message.model_dump()
    db_message = DBMessageSchema(
        message_id=as_dict["id"],
        date=as_dict["date"],
        chat_id=as_dict["chat"]["id"],
        chat_title=as_dict["chat"]["title"],
        chat_username=as_dict["chat"]["username"],
        text=as_dict.get("text"),
        caption=as_dict.get("caption"),
        link=f"https://t.me/{as_dict['chat']['username']}/{as_dict['id']}",
    )

    existing_message = await Message.find_one(Message.message_id == db_message.message_id)
    if existing_message:
        await existing_message.update({"$set": db_message.model_dump()})
    else:
        new_message = Message(**db_message.model_dump())
        await new_message.insert()

    response_message = DBMessageSchema.model_validate(db_message)

    return response_message
