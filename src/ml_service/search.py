import lancedb
from sentence_transformers import SentenceTransformer

from src.ml_service.config import settings
from src.ml_service.text import clean_text

bi_encoder = SentenceTransformer(settings.BI_ENCODER_MODEL, device=settings.DEVICE)


def search_pipeline(query, resources=None, return_chunks=False, top_k=5):
    if resources is None or not resources:
        resources = settings.RESOURCES
    query_emb = bi_encoder.encode(clean_text(query), convert_to_numpy=True)
    print(query_emb)
    all_results = []
    lance_db = lancedb.connect(settings.LANCEDB_URI)
    for resource in resources:
        table_name = f"chunks_{resource}"
        if table_name not in lance_db.table_names():
            continue
        tbl = lance_db.open_table(table_name)
        results = tbl.search(query_emb).limit(top_k).to_pandas()
        print(results)
        for _, row in results.iterrows():
            all_results.append(
                {
                    "resource": resource,
                    "mongo_id": row["mongo_id"],
                    "score": row["_distance"],
                    "meta": row["meta"],
                    "snippet": row["text"],
                }
            )
    all_results.sort(key=lambda x: x["score"])
    if return_chunks:
        return all_results[:top_k]
    return all_results[:top_k]


if __name__ == "__main__":
    print("📥 Starting search pipeline...")
    query = "How much does room rent cost?"
    results = search_pipeline(query)
    for i, r in enumerate(results, 1):
        print(f"{i}. ({r['resource']}) [{r['score']:.3f}]: {r['text']}")
