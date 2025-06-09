__all__ = ["VerifiedDep", "ComputerServiceDep"]

from typing import Annotated

from fastapi import Depends

from src.modules.auth.dependencies import verify_compute_service, verify_user

VerifiedDep: type = Annotated[str, Depends(verify_user)]

ComputerServiceDep: type = Annotated[bool, Depends(verify_compute_service)]
