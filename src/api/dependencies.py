__all__ = ["VerifiedDep", "ComputerServiceDep"]

from typing import TypeAlias, Annotated

from fastapi import Depends

from src.modules.auth.dependencies import verify_user, verify_compute_service

VerifiedDep: TypeAlias = Annotated[str, Depends(verify_user)]

ComputerServiceDep: TypeAlias = Annotated[bool, Depends(verify_compute_service)]
