import itertools
import logging
import time
from collections import defaultdict
from contextlib import contextmanager
from multiprocessing import Pool
from pathlib import Path

import httpx
import pymupdf
import pymupdf4llm
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from torch import cuda

from src.compute_service.bm25 import Bm25
from src.compute_service.cache import PDF_TO_TEXT_VERSION
from src.compute_service.chunker import CustomTokenTextSplitter
from src.compute_service.text import clean_text_common, clean_text_for_sparse
from src.config import settings
from src.modules.compute.schemas import Corpora
from src.modules.minio.schemas import MoodleFileObject
from src.modules.moodle.utils import content_to_minio_object
from src.storages.minio import minio_client
from src.storages.mongo.moodle import MoodleEntrySchema

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("compute.prepare")

_timeit = defaultdict(lambda: [0.0, 0])


@contextmanager
def timeit(key: str, times: int = 1, verbose: str | None = None):
    start_time = time.monotonic()
    yield
    end_time = time.monotonic()
    _timeit[key][0] += end_time - start_time
    _timeit[key][1] += times
    if verbose:
        logger.info(f"{verbose} completed in {end_time - start_time:.2f} seconds")


with timeit("init", 1, "BiEncoder, BM25 and ChunkSplitter loading"):
    device = "cuda" if cuda.is_available() else "cpu"
    bi_encoder = SentenceTransformer(settings.compute_settings.bi_encoder_name, trust_remote_code=True, device=device)
    bi_encoder.share_memory()
    chunk_splitter = CustomTokenTextSplitter(
        tokenizer=bi_encoder.tokenizer, chunk_size=bi_encoder.max_seq_length, chunk_overlap=25
    )
    bm25 = Bm25()

with timeit("qdrant", 1, "Qdrant loading"):
    QDRANT_COLLECTION = settings.compute_settings.qdrant_collection_name
    qdrant = QdrantClient(url=settings.compute_settings.qdrant_url.get_secret_value())
    if not qdrant.collection_exists(QDRANT_COLLECTION):
        qdrant.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config={
                "dense": models.VectorParams(
                    size=bi_encoder.get_sentence_embedding_dimension(), distance=models.Distance.DOT
                )
            },
            sparse_vectors_config={
                "bm25": models.SparseVectorParams(modifier=models.Modifier.IDF),
            },
        )
        # create indexes
        qdrant.create_payload_index(
            QDRANT_COLLECTION, "document-ref.course_id", field_schema=models.PayloadSchemaType.INTEGER
        )
        qdrant.create_payload_index(
            QDRANT_COLLECTION, "document-ref.module_id", field_schema=models.PayloadSchemaType.INTEGER
        )
        qdrant.create_payload_index(
            QDRANT_COLLECTION, "document-ref.filename", field_schema=models.PayloadSchemaType.KEYWORD
        )


def fetch_corpora() -> Corpora:
    with httpx.Client(
        base_url=f"{settings.compute_settings.api_url}/compute",
        headers={"Authorization": f"Bearer {settings.compute_settings.auth_token}"},
    ) as session:
        response = session.get("/corpora")
        response.raise_for_status()
        corpora_data = response.json()
        corpora = Corpora.model_validate(corpora_data)

    as_dict = {
        (entry.course_id, entry.module_id, content.filename): entry
        for entry in corpora.moodle_entries
        for content in entry.contents
    }

    # List all objects with the "moodle/" prefix recursively
    objects = minio_client.list_objects(bucket_name=settings.minio.bucket, prefix="moodle/", recursive=True)
    moodle_files = []
    for obj in objects:
        parts = obj.object_name.split("/")
        course_id, module_id, filename = int(parts[1]), int(parts[2]), parts[3]
        moodle_object = MoodleFileObject(course_id=course_id, module_id=module_id, filename=filename)
        entry = as_dict.get((moodle_object.course_id, moodle_object.module_id, moodle_object.filename), None)

        if entry is not None:
            moodle_object.course_fullname = entry.course_fullname
            moodle_object.section_summary = entry.section_summary
            moodle_object.module_name = entry.module_name
            moodle_object.module_modname = entry.module_modname

        moodle_files.append(moodle_object)

    corpora.moodle_files = moodle_files

    return corpora


def moodle_file_to_chunks(obj: MoodleFileObject):
    s3_object_name = content_to_minio_object(obj.course_id, obj.module_id, obj.filename)

    file_path = Path("s3") / s3_object_name
    if not file_path.exists():
        minio_client.fget_object(settings.minio.bucket, s3_object_name, str(file_path))

    text_path = Path("cache") / f"text-{PDF_TO_TEXT_VERSION}" / s3_object_name
    if not text_path.exists():
        with timeit("to_text", 1, f"Converting {obj.filename} to text"):
            text_path.parent.mkdir(parents=True, exist_ok=True)
            with open(text_path, "w") as f:
                doc = pymupdf.Document(file_path)
                out = pymupdf4llm.process_document(doc, graphics_limit=1000)
                output = "\n\n".join([chunk["text"] for chunk in out["page_chunks"]])
                doc.close()
                f.write(output)
    else:
        with open(text_path) as f:
            output = f.read()
    chunks = []

    page_text = clean_text_common(obj.meta_prefix + output)
    splitted = chunk_splitter.split_text(page_text)
    for j, text in enumerate(splitted):
        chunks.append(
            {
                "text": text,
                "type": "moodle-file",
                "document-ref": {
                    "course_id": obj.course_id,
                    "module_id": obj.module_id,
                    "filename": obj.filename,
                },
                "chunk-ref": {
                    "chunk_number": j,
                },
            }
        )
    return chunks


def moodle_entry_to_chunks(entry: MoodleEntrySchema):
    chunks = []
    meta_prefix = entry.meta_prefix
    for content in entry.contents:
        text = clean_text_common(meta_prefix + f"{content.filename}")
        splitted = chunk_splitter.split_text(text)
        for j, text in enumerate(splitted):
            chunks.append(
                {
                    "text": text,
                    "type": "moodle-entry",
                    "document-ref": {
                        "course_id": entry.course_id,
                        "module_id": entry.module_id,
                        "filename": content.filename,
                    },
                    "chunk-ref": {
                        "chunk_number": j,
                    },
                }
            )
    return chunks


def save_chunks_to_qdrant(chunks: list[dict]):
    if not chunks:
        return

    ref = chunks[0]["document-ref"]
    must = [
        models.FieldCondition(key=f"document-ref.{key}", match=models.MatchValue(value=value))
        for key, value in ref.items()
    ]
    duplicates_filter = models.Filter(must=must)

    exact_match = qdrant.count(QDRANT_COLLECTION, count_filter=duplicates_filter).count
    if exact_match == len(chunks):
        logger.info(f"Skipping {len(chunks)} chunks as they are already in Qdrant")
        return

    qdrant.delete(QDRANT_COLLECTION, models.FilterSelector(filter=duplicates_filter), wait=True)
    texts = [chunk["text"] for chunk in chunks]
    with timeit("dense", len(texts), None):
        dense_vectors = bi_encoder.encode(
            texts,
            show_progress_bar=False,
            batch_size=settings.compute_settings.bi_encoder_batch_size,
        )

    with timeit("sparse", len(texts), None):
        sparse_vectors = list(bm25.embed(map(clean_text_for_sparse, texts)))

    vectors = []
    for dense_vector, sparse_vector in zip(dense_vectors, sparse_vectors):
        vectors.append({"dense": dense_vector, "bm25": sparse_vector})

    qdrant.upload_collection(QDRANT_COLLECTION, payload=chunks, vectors=vectors)
    logger.info(f"Saved +{len(chunks)} chunks to Qdrant")


def corpora_to_qdrant(corpora: Corpora):
    logger.info(f"Processing {len(corpora.moodle_files)} items")
    collection_len = 0
    pdf_files = [item for item in corpora.moodle_files if item.filename.endswith(".pdf")]
    _pdf_files = {(item.course_id, item.module_id, item.filename) for item in pdf_files}
    moodle_entries_but_not_pdf = []
    for moodle_entry in corpora.moodle_entries:
        for content in moodle_entry.contents:
            if (moodle_entry.course_id, moodle_entry.module_id, content.filename) not in _pdf_files:
                moodle_entries_but_not_pdf.append(moodle_entry)
                break

    with timeit("corpora", len(pdf_files) + len(moodle_entries_but_not_pdf), "Processing corpora"):
        with Pool(processes=settings.compute_settings.num_workers) as pool:
            file_chunks = pool.imap_unordered(moodle_file_to_chunks, pdf_files)
            entry_chunks = pool.imap_unordered(moodle_entry_to_chunks, moodle_entries_but_not_pdf)

            for chunks in itertools.chain(entry_chunks, file_chunks):
                if chunks:
                    save_chunks_to_qdrant(chunks)
                    collection_len += len(chunks)
        logger.info(f"Processed {collection_len} chunks")
        _ = "\n"
        for key, (spent, count) in _timeit.items():
            _ += f"{key}: {spent:.2f} seconds ({count} times)\n"
            _timeit[key] = [0.0, 0]
        logger.info(_)


def no_corpora_changes(prev_corpora: Corpora | None, corpora: Corpora) -> bool:
    if prev_corpora is None:
        return False
    prev_moodle_files = prev_corpora.moodle_files
    corpora_moodle_files = corpora.moodle_files

    _prev = [_.model_dump() for _ in prev_moodle_files]
    _curr = [_.model_dump() for _ in corpora_moodle_files]
    return _prev == _curr


def main():
    logger.info(f"Fetch corpora every {settings.compute_settings.corpora_update_period} seconds")
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
