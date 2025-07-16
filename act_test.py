import asyncio
from datetime import date, time
from types import SimpleNamespace

import src.config
from src.modules.act.music_room.repository import ActRepository
from src.modules.act.music_room.schemas import BookingRequest, BookingResponse, MusicRoomSlot

src.config.settings = SimpleNamespace(music_booking=SimpleNamespace(api_url="https://stub-api"))


class StubActRepository(ActRepository):
    def __init__(self):
        super().__init__()

        self.booked_slots = set()

    async def check_availability(self, slot: MusicRoomSlot, token: str):
        key = (slot.date, slot.start, slot.end)
        print(f"[STUB] check_availability for {key}")
        if key in self.booked_slots:
            return SimpleNamespace(available=False, message="Stub: occupied")
        return SimpleNamespace(available=True, message="Stub: available")

    async def create_booking(self, slot: MusicRoomSlot, token: str):
        key = (slot.date, slot.start, slot.end)
        print(f"[STUB] create_booking for {key}")

        self.booked_slots.add(key)
        return BookingResponse(
            booking_id="stub-1234",
            status="confirmed",
            date=slot.date,
            start=slot.start,
            end=slot.end,
        )


async def main():
    token = "dummy-token"
    repo = StubActRepository()

    slot = MusicRoomSlot(date=date(2025, 7, 15), start=time(16, 0), end=time(18, 0))

    req = BookingRequest(date=slot.date, start=slot.start, end=slot.end, confirm=False)
    print("→ handle_booking(confirm=False)")
    r1 = await repo.handle_booking(req, token)
    print("Result:", r1, "\n")

    req.confirm = True
    print("→ handle_booking(confirm=True)")
    r2 = await repo.handle_booking(req, token)
    print("Result:", r2, "\n")

    print("→ handle_booking(confirm=True) again for the same slot")
    r3 = await repo.handle_booking(req, token)
    print("Result:", r3, "\n")


if __name__ == "__main__":
    asyncio.run(main())
