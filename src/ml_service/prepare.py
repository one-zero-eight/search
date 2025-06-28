import asyncio
import html

import lancedb
from chonkie import TokenChunker
from lancedb.pydantic import LanceModel, Vector

from src.api.logging_ import logger
from src.config import settings
from src.ml_service.db_utils import get_all_documents
from src.ml_service.text import clean_text
from src.modules.sources_enum import InfoSources


class Schema(LanceModel):
    resource: str
    mongo_id: str | None
    chunk_number: int
    content: str
    embedding: Vector(settings.ml_service.bi_encoder_dim)


chunker = TokenChunker(
    tokenizer="jinaai/jina-embeddings-v3",
    chunk_size=512,
    chunk_overlap=128,
    return_type="texts",
)


async def prepare_maps(response: list[dict]):
    idx = 0
    prefixed_chunks = []
    for scene in response:
        scene_str = f"# {scene['title']}\n"
        for area in scene["areas"]:
            area_str = f"### {area['title']}\n"
            description_str = ""
            if area["description"]:
                joined_lines = "  \n".join(area["description"].split("\n"))
                description_str = f"**Description:** {joined_lines}  \n"
            link_str = f"https://innohassle.ru/maps?scene={scene['scene_id']}&area={area['svg_polygon_id']}"
            people_str = ""
            if area["people"]:
                people_str = "**People:** "
                people_str += f"{', '.join(area['people'][::2])}  \n"

            source_url_escaped = html.escape(link_str, quote=True)
            prefix = f'<chunk chunk_number={idx} source_url="{source_url_escaped}">'
            chunk = scene_str + area_str + description_str + link_str + people_str
            prefixed_chunk = prefix + chunk
            prefixed_chunks.append(prefixed_chunk)
            idx += 1

    return await embed(InfoSources.maps, prefixed_chunks, None)


async def prepare_mongo(resource: InfoSources, docs: list[dict]):
    logger.info(f"Resource `{resource}`: found {len(docs)} documents in MongoDB")

    records = []
    for doc in docs:
        raw = doc.get("content", "")
        text = clean_text(raw)
        chunks = chunker.chunk(text)
        prefixed_chunks = []
        for idx, chunk in enumerate(chunks):
            if "source_url" in doc and "source_page_title" in doc:
                source_url_escaped = html.escape(doc["source_url"], quote=True)
                source_page_title_escaped = html.escape(doc["source_page_title"], quote=True)
                prefix = f'<chunk chunk_number={idx} source_url="{source_url_escaped}" source_page_title="{source_page_title_escaped}">'
                prefixed_chunks.append(f"{prefix}\n{chunk}")
            else:
                prefixed_chunks.append(chunk)

        records.extend(await embed(resource, prefixed_chunks, str(doc.get("_id", doc.get("id", None)))))
    return records


async def embed(resource, prefixed_chunks, mongo_id=None):
    if settings.ml_service.infinity_url:
        import src.ml_service.infinity

        embeddings = await src.ml_service.infinity.embed(prefixed_chunks, task="passage")
    else:
        import src.ml_service.non_infinity

        embeddings = await src.ml_service.non_infinity.embed(prefixed_chunks, task="passage")

    records = []
    for idx, (chunk, emb) in enumerate(zip(prefixed_chunks, embeddings)):
        records.append(
            {
                "resource": resource,
                "mongo_id": mongo_id,
                "chunk_number": idx,
                "content": chunk,
                "embedding": emb,
            }
        )
    return records


async def prepare_resource(resource: InfoSources, docs: list[dict]):
    lance_db = await lancedb.connect_async(settings.ml_service.lancedb_uri)
    table_name = f"chunks_{resource}"
    arrow_schema = Schema.to_arrow_schema()

    records = []
    if resource == InfoSources.maps:
        records = await prepare_maps(docs)
    elif resource in [InfoSources.campuslife, InfoSources.eduwiki, InfoSources.hotel]:
        records = await prepare_mongo(resource, docs)
    else:
        raise Exception("Unknown resource")

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
    for r in [
        InfoSources.campuslife,
        InfoSources.eduwiki,
        InfoSources.hotel,
        InfoSources.moodle,
    ]:
        docs = get_all_documents(r.value)
        asyncio.run(prepare_resource(r, docs))
