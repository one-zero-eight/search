import logging

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import VerifiedDep
from src.modules.act.music_room.repository import ActRepository
from src.modules.act.music_room.schemas import (
    AvailabilityResponse,
    BookingResponse,
    MusicRoomSlot,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/act/music-room", tags=["act"])
repo = ActRepository()


@router.post("/availability", response_model=AvailabilityResponse)
async def check_availability(
    slot: MusicRoomSlot,
    token: str = Depends(VerifiedDep),
):
    logger.info(f"[Routes] POST /availability slot={slot!r}, token={token[:8]}…")
    result = await repo.check_availability(slot, token)
    logger.info(f"[Routes] availability result: {result}")
    return result


@router.post("/book", response_model=BookingResponse)
async def book_room(
    slot: MusicRoomSlot,
    token: str = Depends(VerifiedDep),
):
    logger.info(f"[Routes] POST /book slot={slot!r}, token={token[:8]}…")
    avail = await repo.check_availability(slot, token)
    if not avail.available:
        logger.warning(f"[Routes] booking denied: {avail.message}")
        raise HTTPException(status_code=400, detail=avail.message or "Room is occupied")

    booking = await repo.create_booking(slot, token)
    logger.info(f"[Routes] booking succeeded: {booking}")
    return booking
