import html

import lancedb
from chonkie import TokenChunker
from lancedb.pydantic import LanceModel, Vector

from src.api.logging_ import logger
from src.config import settings
from src.ml_service.db_utils import get_all_documents
from src.ml_service.infinity import embed
from src.ml_service.text import clean_text
from src.modules.sources_enum import InfoSources, InfoSourcesToMongoEntryName


class Schema(LanceModel):
    content: str
    embedding: Vector(settings.ml_service.bi_encoder_dim)
    resource: str
    mongo_id: str
    title: str
    page_name: str
    filename: str
    chunk_number: int


chunker = TokenChunker(
    tokenizer="jinaai/jina-embeddings-v3",
    chunk_size=512,
    chunk_overlap=128,
    return_type="texts",
)


async def prepare_resource(resource: InfoSources):
    lance_db = await lancedb.connect_async(settings.LANCEDB_URI)
    table_name = f"chunks_{resource}"
    arrow_schema = Schema.to_arrow_schema()
    mongo_table_name = InfoSourcesToMongoEntryName[resource]
    docs = get_all_documents(mongo_table_name)
    logger.info(f">>> Resource `{resource}`: found {len(docs)} documents in MongoDB")

    records = []
    for doc in docs:
        raw = doc.get("content", "")
        text = clean_text(raw)
        chunks = chunker.chunk(text)
        for idx, (chunk, emb) in enumerate(zip(chunks, await embed(chunks))):
            prefixed = chunk
            if "source_url" in doc and "source_page_title" in doc:
                source_url_escaped = html.escape(doc["source_url"], quote=True)
                source_page_title_escaped = html.escape(doc["source_page_title"], quote=True)
                prefix = f'<chunk chunk_number={idx} source_url="{source_url_escaped}" source_page_title="{source_page_title_escaped}">'
                prefixed = f"{prefix}\n{chunk}"

            records.append(
                {
                    "content": prefixed,
                    "embedding": emb,
                    "resource": resource,
                    "mongo_id": str(doc.get("_id", "")),
                    "title": doc.get("title", ""),
                    "page_name": doc.get("page_name", ""),
                    "filename": doc.get("filename", ""),
                    "chunk_number": idx,
                }
            )

    if table_name in await lance_db.table_names():
        await lance_db.drop_table(table_name)

    if records:
        await lance_db.create_table(
            table_name,
            data=records,
            schema=arrow_schema,
        )
    else:
        await lance_db.create_table(
            table_name,
            schema=arrow_schema,
        )

    tbl = await lance_db.open_table(table_name)
    # tbl.create_fts_index("content", replace=True, use_tantivy=False)
    arrow_tbl = await tbl.to_arrow()
    print("checking table size:", arrow_tbl.num_rows, "strings (Arrow)")


if __name__ == "__main__":
    print("📥 Starting prepare pipeline...")
    for r in settings.RESOURCES:
        prepare_resource(r)
