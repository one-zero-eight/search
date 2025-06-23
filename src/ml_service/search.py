import re

import lancedb
from sentence_transformers import SentenceTransformer

from src.ml_service.config import settings
from src.ml_service.text import clean_text

bi_encoder = SentenceTransformer(settings.BI_ENCODER_MODEL, device=settings.DEVICE)

def search_pipeline(query, resources=None, return_chunks=False, top_k=5):
    if not resources:
        resources = settings.RESOURCES
    query_emb = bi_encoder.encode(clean_text(query), convert_to_numpy=True)
    print("Query embedding (first 5 dims):", query_emb[:5], "…")
    all_results = []
    lance_db = lancedb.connect(settings.LANCEDB_URI)
    for resource in resources:
        tbl_name = f"chunks_{resource}"
        if tbl_name not in lance_db.table_names():
            continue
        tbl = lance_db.open_table(tbl_name)
        results = tbl.search(query_emb).limit(top_k).to_pandas()
        print(f"\nRaw results for {resource}:")
        print(results[["mongo_id", "_distance", "content"]].head())
        for _, row in results.iterrows():
            snippet = row["content"]
            snippet = re.sub(r'#{2,}\s*', '', snippet)
            all_results.append({
                "resource": resource,
                "mongo_id": row["mongo_id"],
                "score":    row["_distance"],
                "snippet":  snippet,
                
            })
    all_results.sort(key=lambda x: x["score"])
    return all_results[:top_k] if not return_chunks else all_results[:top_k]

if __name__ == "__main__":
    print("📥 Starting search pipeline…")
    query = "How much does room for 2 people rent cost?"
    results = search_pipeline(query)
    for i, r in enumerate(results, 1):
        print(f"{i}. ({r['resource']}) [{r['score']:.3f}]: {r['snippet']}")
