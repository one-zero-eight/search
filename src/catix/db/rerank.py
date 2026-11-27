"""One rerank over the candidates of several sources together.

Each source (chats, documents, Moodle) gives its pool of hybrid-ranked candidates unscored (`search(..., rerank=False)`); the
reranker scores them all against the queries in one pass, so that their scores are on one scale and the best of all sources
come first, instead of each source being ranked among its own. Scoring is as in db/store.py `_rerank`: the best score over
the queries orders the candidates, the second best is their `relevance` (how well two angles agree that it is about the
question), and `rerank_min_score` is the cutoff.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from catix.agent import tracing
from catix.db import pg
from catix.db.docs import demote_course_programmes, freshness
from catix.settings import settings

log = logging.getLogger("catix.rerank")


def mixed(queries: list[str], pools: dict[str, list[tuple[object, str]]], limit: int, reserve: int = 2) -> dict[str, list]:
    """The best `limit` candidates of all `pools` (source -> [(hit, the text the reranker reads)]) together, regrouped by
    source, each source's best first, each hit with its `relevance`. A source keeps at least its `reserve` best candidates
    that pass the cutoff, so that a source with many near-duplicates (the chats) cannot push the others out entirely.
    If the reranker server is down the sources' own order stays and they take turns up to `limit`."""
    flat = [(source, hit, document) for source, items in pools.items() for hit, document in items]
    out: dict[str, list] = {source: [] for source in pools}
    if not flat or limit <= 0:
        return out
    queries = queries[: settings.rerank_queries]
    documents = [document for *_, document in flat]
    try:
        with tracing.span("rerank", "RERANKER", input=queries, documents=len(documents)), ThreadPoolExecutor(max_workers=len(queries)) as executor:
            scores = list(executor.map(tracing.carry(lambda q: pg.rerank(q, documents)), queries))
    except Exception:  # noqa: BLE001 - search must keep working without the reranker
        log.warning("reranker server unavailable, keeping the hybrid ranking", exc_info=True)
        rows = {source: iter(items) for source, items in pools.items()}
        taken = 0
        while taken < limit and rows:
            for source in list(rows):
                item = next(rows[source], None)
                if item is None:
                    del rows[source]
                elif taken < limit:
                    out[source].append(item[0])
                    taken += 1
        return out
    best = [max(column) for column in zip(*scores)]
    agreed = [sorted(column, reverse=True)[1 if len(column) > 1 else 0] for column in zip(*scores)]
    ranked = [best[i] * freshness(flat[i][1]) for i in range(len(flat))]
    order = sorted(range(len(flat)), key=lambda i: ranked[i], reverse=True)
    if settings.rerank_min_score is not None:
        order = [i for i in order if best[i] >= settings.rerank_min_score]
    order = demote_course_programmes(order, [hit for _, hit, _ in flat])
    chosen = []
    for source in pools:  # the reserved ones first, then the best of all
        chosen += [i for i in order if flat[i][0] == source][:reserve]
    chosen += [i for i in order if i not in chosen][: max(limit - len(chosen), 0)]
    for i in sorted(chosen, key=lambda i: ranked[i], reverse=True):
        source, hit, _ = flat[i]
        out[source].append(replace(hit, relevance=agreed[i]))
    return out
