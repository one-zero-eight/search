__all__ = ["VerifiedDep", "VerifiedDepWithUserID"]

from typing import TypeAlias, Annotated, cast

from fastapi import Depends

from src.api.auth.dependencies import verify_request
from src.exceptions import ForbiddenException
from src.schemas.auth import SucceedVerificationResult, VerificationResultWithUserId


def verify_request_with_user_id(
    verification: Annotated[SucceedVerificationResult, Depends(verify_request)],
) -> VerificationResultWithUserId:
    if verification.user_id is None or not verification.success:
        raise ForbiddenException()
    return cast(VerificationResultWithUserId, verification)


VerifiedDep: TypeAlias = Annotated[SucceedVerificationResult, Depends(verify_request)]
VerifiedDepWithUserID: TypeAlias = Annotated[VerificationResultWithUserId, Depends(verify_request_with_user_id)]
