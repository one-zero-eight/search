from fastapi import APIRouter

from src.ml_service.llm import act
from src.modules.ml.schemas import MLActRequest, MLActResponse

router = APIRouter(prefix="/act", tags=["Act"])


@router.post("", response_model=MLActResponse)
async def act_llm(request: MLActRequest) -> MLActResponse:
    result = await act(request.query, request.user_token)
    return result
