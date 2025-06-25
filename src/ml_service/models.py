from sentence_transformers import SentenceTransformer
from sentence_transformers.cross_encoder import CrossEncoder

from src.config import settings

bi_encoder = SentenceTransformer(settings.ml_service.bi_encoder, trust_remote_code=True)
cross_encoder = CrossEncoder(
    settings.ml_service.cross_encoder,
    model_kwargs={"torch_dtype": "auto"},
    trust_remote_code=True,
)
