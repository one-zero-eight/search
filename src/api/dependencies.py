__all__ = ["VerifiedDep"]

from typing import TypeAlias, Annotated

from fastapi import Depends

from src.api.auth.dependencies import verify_user

VerifiedDep: TypeAlias = Annotated[str, Depends(verify_user)]
