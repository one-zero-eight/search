"""Fresher documents first: the factor of a hit's reranker score for its age (db/docs.py freshness)."""

from datetime import date, timedelta

import pytest

from catix.db import docs
from catix.db.docs import DocHit, freshness


def hit(issued: date | None, path: str = "regulations/x", id: int = 1) -> DocHit:
    return DocHit(id=id, path=path, seq=0, heading="", clause=None, sha=f"s{id}", text="t", cites=[], title="T", type="regulation",
                  trust="official", audience=[], resource=None, status=None, review=None, source_warning=None, stale_after=None, issued=issued)


def ago(years: float) -> date:
    return date.today() - timedelta(days=round(years * 365.25))


def test_a_document_loses_score_with_each_year_after_the_first_down_to_a_floor():
    assert freshness(hit(date.today())) == 1.0
    assert freshness(hit(ago(3))) == pytest.approx(0.94, abs=0.01)
    assert freshness(hit(ago(20))) == 0.85
    assert freshness(hit(None)) == 1.0
    assert freshness(hit(ago(10), path="sites/u/p")) == 1.0


def test_an_older_document_comes_after_a_newer_one_the_reranker_scored_the_same(monkeypatch):
    monkeypatch.setattr(docs.pg, "rerank", lambda query, documents: [0.8, 0.8])
    old, new = hit(date(2015, 1, 1), id=1), hit(ago(0), id=2)
    assert docs._rerank(["q"], [old, new], 2) == [new, old]
