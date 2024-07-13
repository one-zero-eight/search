import logging
import re
import time
from multiprocessing import Pool
from pathlib import Path

import httpx
import pymupdf
import pymupdf4llm
from qdrant_client import QdrantClient, models

from sentence_transformers import SentenceTransformer

from src.compute_service.chunker import CustomTokenTextSplitter
from src.config import settings
from src.modules.compute.schemas import Corpora
from src.modules.minio.schemas import MoodleFileObject
from src.modules.moodle.utils import content_to_minio_object
from src.storages.minio import minio_client

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("compute.prepare")

_1 = time.monotonic()
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
chunk_splitter = CustomTokenTextSplitter(tokenizer=model.tokenizer, chunk_size=model.max_seq_length, chunk_overlap=25)

qdrant = QdrantClient(settings.compute_settings.qdrant_url.get_secret_value())
QDRANT_COLLECTION = settings.compute_settings.qdrant_collection_name
if not qdrant.collection_exists(QDRANT_COLLECTION):
    qdrant.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=models.VectorParams(size=model.get_sentence_embedding_dimension(), distance=models.Distance.DOT),
    )
_2 = time.monotonic()

logger.info(f"Initialized in {_2 - _1:.2f} seconds")


def get_client() -> httpx.Client:
    return httpx.Client(
        base_url=f"{settings.compute_settings.api_url}/compute",
        headers={"Authorization": f"Bearer {settings.compute_settings.auth_token}"},
    )


def fetch_corpora() -> Corpora:
    with get_client() as session:
        response = session.get("/corpora")
        response.raise_for_status()
        corpora_data = response.json()
        corpora = Corpora.model_validate(corpora_data)
    return corpora


def object_pipeline(obj: MoodleFileObject):
    s3_object_name = content_to_minio_object(obj.course_id, obj.module_id, obj.filename)
    file_path = Path("s3") / s3_object_name
    if not file_path.exists():
        minio_client.fget_object(settings.minio.bucket, s3_object_name, str(file_path))
    doc = pymupdf.Document(file_path)
    output = pymupdf4llm.process_document(doc, graphics_limit=1000)
    doc.close()
    chunks = []
    for i, page_chunk in enumerate(output["page_chunks"]):
        page_text = re.sub(r"<[^>]*>", "", page_chunk["text"])
        splitted = chunk_splitter.split_text(page_text)
        for j, text in enumerate(splitted):
            chunks.append(
                {
                    "text": text,
                    "document-ref": {
                        "course_id": obj.course_id,
                        "module_id": obj.module_id,
                        "filename": obj.filename,
                    },
                    "chunk-ref": {
                        "page_number": i,
                        "chunk_number": j,
                    },
                }
            )
    return chunks


def save_file_chunks_to_qdrant(chunks: list[dict]):
    if not chunks:
        return
    ref = chunks[0]["document-ref"]
    must = [
        models.FieldCondition(key=f"document-ref.{key}", match=models.MatchValue(value=value))
        for key, value in ref.items()
    ]

    qdrant.delete(
        QDRANT_COLLECTION,
        models.FilterSelector(filter=models.Filter(must=must)),
    )

    vectors = model.encode([chunk["text"] for chunk in chunks], show_progress_bar=False)
    qdrant.upload_collection(QDRANT_COLLECTION, payload=chunks, vectors=vectors)
    logger.info(f"Saved +{len(chunks)} chunks to Qdrant")


def corpora_to_qdrant(corpora: Corpora):
    logger.info(f"Processing {len(corpora.moodle_files)} items")
    collection_len = 0

    _1 = time.monotonic()
    items = [item for item in corpora.moodle_files if item.filename.endswith(".pdf")]

    with Pool(processes=settings.compute_settings.num_workers) as pool:
        file_chunks = pool.imap_unordered(object_pipeline, items)
        for chunks in file_chunks:
            if chunks:
                save_file_chunks_to_qdrant(chunks)
                collection_len += len(chunks)
    _2 = time.monotonic()
    logger.info(f"Processed {collection_len} chunks in {_2 - _1:.2f} seconds")


def no_corpora_changes(prev_corpora: Corpora | None, corpora: Corpora) -> bool:
    if prev_corpora is None:
        return False
    prev_moodle_files = prev_corpora.moodle_files
    corpora_moodle_files = corpora.moodle_files

    _prev = [_.model_dump() for _ in prev_moodle_files]
    _curr = [_.model_dump() for _ in corpora_moodle_files]
    return _prev == _curr


def main():
    logger.info(f"Fetch corpora from API every {settings.compute_settings.corpora_update_period} seconds")
    prev_corpora = None
    while True:
        corpora = fetch_corpora()

        if no_corpora_changes(prev_corpora, corpora):
            logger.info("No corpora changes")
        else:
            logger.info(f"Populated by {len(corpora.moodle_files)} corpora entries")
            corpora_to_qdrant(corpora)
            prev_corpora = corpora

        # Wait for the specified period before fetching tasks again
        time.sleep(settings.compute_settings.corpora_update_period)


if __name__ == "__main__":
    main()
