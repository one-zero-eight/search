import asyncio
import html

import lancedb
from chonkie import TokenChunker
from lancedb.pydantic import LanceModel, Vector

from src.api.logging_ import logger
from src.config import settings
from src.ml_service.db_utils import get_all_documents
from src.ml_service.text import clean_text
from src.modules.sources_enum import ALL_SOURCES, InfoSources


class Schema(LanceModel):
    resource: str
    mongo_id: str | None
    chunk_number: int
    content: str
    embedding: Vector(settings.ml_service.bi_encoder_dim)


chunker = TokenChunker(
    tokenizer=settings.ml_service.bi_encoder,
    chunk_size=512,
    chunk_overlap=128,
)


async def prepare_maps(doc: list[dict]):
    if "location_url" in doc and "scene_id" in doc and "area_id" in doc:
        url_escaped = html.escape(doc["location_url"], quote=True)
        prefix = f'<chunk chunk_number=0 location_url="{url_escaped}" hint="This is a entry pointing to some room in Innopolis University">'
        chunk = clean_text(doc.get("content", ""))
        prefixed_chunk = prefix + chunk
    return [prefixed_chunk]


async def prepare_large(doc: dict):
    raw = doc.get("content", "")
    text = clean_text(raw)
    chunks = chunker.chunk(text)
    prefixed_chunks = []
    for idx, chunk in enumerate(chunks):
        if "source_url" in doc and "source_page_title" in doc:
            source_url_escaped = html.escape(doc["source_url"], quote=True)
            source_page_title_escaped = html.escape(doc["source_page_title"], quote=True)
            prefix = f'<chunk chunk_number={idx} source_url="{source_url_escaped}" source_page_title="{source_page_title_escaped}">'
            prefixed_chunks.append(f"{prefix}\n{chunk.text}")
        else:
            prefixed_chunks.append(chunk.text)
    return prefixed_chunks


async def prepare_resource(resource: InfoSources, docs: list[dict]):
    lance_db = await lancedb.connect_async(settings.ml_service.lancedb_uri)
    table_name = f"chunks_{resource}"
    arrow_schema = Schema.to_arrow_schema()

    logger.info(f"Resource `{resource}`: found {len(docs)} documents in MongoDB")

    idxs = []
    mongo_ids = []
    prefixed_chunks = []
    for doc in docs:
        if resource == InfoSources.maps:
            res = await prepare_maps(doc)
        elif resource in [
            InfoSources.campuslife,
            InfoSources.eduwiki,
            InfoSources.hotel,
            InfoSources.residents,
            InfoSources.resources,
        ]:
            res = await prepare_large(doc)
        else:
            raise Exception("Unknown resource")
        prefixed_chunks.extend(res)
        idxs.extend(list(range(len(res))))
        mongo_ids.extend([str(doc.get("_id", doc.get("id", None)))] * len(res))

    if settings.ml_service.infinity_url:
        import src.ml_service.infinity

        embeddings = await src.ml_service.infinity.embed(prefixed_chunks, task="passage")
    else:
        import src.ml_service.non_infinity

        embeddings = await src.ml_service.non_infinity.embed(prefixed_chunks, task="passage")

    records = []
    for idx, mongo_id, chunk, emb in zip(idxs, mongo_ids, prefixed_chunks, embeddings):
        records.append(
            {
                "resource": resource,
                "mongo_id": mongo_id,
                "chunk_number": idx,
                "content": chunk,
                "embedding": emb,
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
    logger.info(f"Resource `{resource}`: {arrow_tbl.num_rows} rows (Arrow)")
    return arrow_tbl.drop("embedding").to_pylist()


if __name__ == "__main__":
    print("📥 Starting prepare pipeline...")
    for r in ALL_SOURCES:
        docs = get_all_documents(r.value)
        asyncio.run(prepare_resource(r, docs))
