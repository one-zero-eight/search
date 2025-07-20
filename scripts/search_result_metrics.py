import asyncio

import httpx
import numpy as np
import pandas as pd
from irmetrics.topk import rr


async def pred(i, question, expected_urls, token):
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            "http://127.0.0.1:8001/search/search",
            params={
                "query": question,
                "response_types": ["link_to_source"],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    response_data = response.json()
    if not response_data["responses"]:
        return []

    used = [0 for _ in range(len(expected_urls))]
    result = []
    for item in response_data["responses"]:
        try:
            index = expected_urls.index(item.get("source", "-").get("url", "-"))
            used[index] = 1
            result.append(1)
        except ValueError:
            result.append(0)

    if sum(used) > 0 and sum(used) < len(used):
        result = [0 for _ in range(len(result))]
    return result


def count_ndcg(relevance_scores, k=None):
    if not relevance_scores:
        return 0
    scores = np.asarray(relevance_scores)[:k]
    discounts = np.log2(np.arange(2, len(scores) + 2))
    dcg = np.sum(scores / discounts)
    idcg = np.sum(discounts)
    return dcg / idcg


def count_average_precision(relevance_scores, k=None):
    if not relevance_scores:
        return 0
    scores = np.asarray(relevance_scores)[:k]
    rel_cumsum = np.cumsum(scores)

    precision_at_k = rel_cumsum / (np.arange(len(scores)))

    ap = np.sum(precision_at_k * scores) / np.sum(scores)

    return ap


async def get_preds(df, token):
    result = []
    problematic_queries = []
    for i, question in enumerate(df["Вопрос"]):
        pred_list = await pred(i, question, df["Ссылка"][i].split("\n"), token)
        result.append(pred_list)
        if sum(pred_list) == 0:
            problematic_queries.append(question)
    return result, problematic_queries


def count_metrics(pred_lists):
    response_rates = []
    aps = []
    ndcgs = []

    for pred_list in pred_lists:
        response_rate = rr(1, pred_list) if pred_list else 0
        ap = sum(pred_list) / len(pred_list) if pred_list else 0
        ndcg = count_ndcg(pred_list) if pred_list else 0

        response_rates.append(response_rate)
        aps.append(ap)
        ndcgs.append(ndcg)

    print(f"Mean Response Rate: {np.array(response_rates).mean()}")
    print(f"Mean Average Precision: {np.array(aps).mean()}")
    print(f"Mean NDCG: {np.array(ndcgs).mean()}")


async def process():
    SHEET_ID = "1kpxqZB_gEwnivJHe5jJCVE0o_zqLAYw_Q_xQO3SwplI"

    en_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
    ru_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=53855511"
    en_df = pd.read_csv(en_url)
    ru_df = pd.read_csv(ru_url)

    token = input("Enter your token from https://innohassle.ru/account/token: ")
    en_preds, en_problematic_queries = await get_preds(en_df, token)
    ru_preds, ru_problematic_queries = await get_preds(ru_df, token)

    print("Metrics for English queries")
    count_metrics(en_preds)
    print("---")
    print("Metrics for Russian queries")
    count_metrics(ru_preds)
    print("---")
    print("Metrics for both")
    count_metrics(en_preds + ru_preds)
    print("---")
    print("Problematic queries: ")
    print("\n".join(en_problematic_queries))
    print("\n".join(ru_problematic_queries))


if __name__ == "__main__":
    asyncio.run(process())
