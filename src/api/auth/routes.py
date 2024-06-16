__all__ = ["router"]

from fastapi import APIRouter

from src.api.dependencies import VerifiedDep
from src.exceptions import UserExists, ForbiddenException, UserDidNotConnectTelegram
from src.repositories.innohassle_accounts import innohassle_accounts
from src.repositories.users.repository import user_repository
from src.schemas import CreateUser, UserStatus, ViewUser
from src.schemas.auth import VerificationSource

router = APIRouter(tags=["Auth"])


@router.post("/auth/registration")
async def registration(telegram_id: int, verification: VerifiedDep) -> ViewUser | None:
    if verification.source == VerificationSource.BOT and telegram_id != verification.telegram_id:
        raise ForbiddenException()

    if await user_repository.get_user_id(telegram_id=telegram_id):
        raise UserExists()

    user_from_innohassle = await innohassle_accounts.get_user_by_telegram_id(telegram_id)

    if (
        user_from_innohassle is None
        or user_from_innohassle.telegram is None
        or user_from_innohassle.innopolis_sso is None
    ):
        raise UserDidNotConnectTelegram()

    user = CreateUser(
        email=user_from_innohassle.innopolis_sso.email,
        name=user_from_innohassle.innopolis_sso.name,
        status=UserStatus.FREE,
        telegram_id=telegram_id,
    )
    created = await user_repository.create(user)
    return created


@router.get("/auth/is_user_exists")
async def is_user_exists(verification: VerifiedDep, email: str = None, telegram_id: int = None) -> bool:
    if verification.source == VerificationSource.BOT and telegram_id != verification.telegram_id:
        raise ForbiddenException()
    user_id = await user_repository.get_user_id(email=email, telegram_id=telegram_id)
    if user_id is None:
        return False
    return True
