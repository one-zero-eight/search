import lancedb
from lancedb.pydantic import LanceModel, Vector
from sentence_transformers import SentenceTransformer

from src.ml_service.chunker import sentence_chunker
from src.ml_service.config import settings
from src.ml_service.db_utils import get_all_documents
from src.ml_service.text import clean_text


class Schema(LanceModel):
    text: str
    embedding: Vector(settings.LANCEDB_EMBEDDING_DIM)
    resource: str
    mongo_id: str
    title: str
    page_name: str
    filename: str
    chunk_number: int


def prepare_resource(resource):
    lance_db = lancedb.connect(settings.LANCEDB_URI)
    table_name = f"chunks_{resource}"
    arrow_schema = Schema.to_arrow_schema()
    if table_name not in lance_db.table_names():
        lance_db.create_table(
            table_name,
            schema=arrow_schema,
        )
    tbl = lance_db.open_table(table_name)

    encoder = SentenceTransformer(settings.BI_ENCODER_MODEL, device=settings.DEVICE)

    docs = get_all_documents(resource)
    print(f">>> Resource `{resource}`: found {len(docs)} documents in MongoDB")

    for doc in get_all_documents(resource):
        raw = doc.get("text", "")
        text = clean_text(raw)
        chunks = sentence_chunker(text)
        for idx, chunk in enumerate(chunks):
            emb = encoder.encode(chunk)
            tbl.add(
                Schema(
                    text=chunk,
                    embedding=emb,
                    resource=resource,
                    mongo_id=str(doc.get("_id", "")),
                    title=doc.get("title", ""),
                    page_name=doc.get("page_name", ""),
                    filename=doc.get("filename", ""),
                    chunk_number=idx,
                )
            )

    arrow_tbl = tbl.to_arrow()
    print("checking table size:", arrow_tbl.num_rows, "strings (Arrow)")


if __name__ == "__main__":
    print("📥 Starting prepare pipeline...")
    for resource in settings.RESOURCES:
        prepare_resource(resource)
