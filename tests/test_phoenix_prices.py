"""The wiki model's prices in Phoenix (agent/tracing.py): made once, then updated, never twice; nothing without tracing."""

from types import SimpleNamespace

from catix.agent import tracing


def test_the_model_is_made_once_then_updated(monkeypatch):
    sent, models = [], []

    def post(url, json, timeout):
        sent.append(json)
        q = json["query"]
        if "createModel" in q:
            models.append({"id": "M1", "name": json["variables"]["input"]["name"], "kind": "CUSTOM"})
        data = {"generativeModels": {"edges": [{"node": m} for m in models]}} if "generativeModels" in q else {"x": {}}
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"data": data})

    import httpx

    monkeypatch.setattr(httpx, "post", post)
    monkeypatch.setattr(tracing, "enabled", lambda: True)
    monkeypatch.setattr(tracing.settings, "phoenix_endpoint", "http://phoenix:6006")
    prices = {"input": 0.15, "cache_read": 0.003, "output": 0.6}
    tracing.price_model("deepseek-flash", prices)
    tracing.price_model("deepseek-flash", prices)
    mutations = [j for j in sent if j["query"].startswith("mutation")]
    assert ["createModel" in m["query"] for m in mutations] == [True, False] and len(models) == 1
    costs = {c["tokenType"]: (c["kind"], c["costPerMillionTokens"]) for c in mutations[1]["variables"]["input"]["costs"]}
    assert costs == {"input": ("PROMPT", 0.15), "cache_read": ("PROMPT", 0.003), "output": ("COMPLETION", 0.6)}


def test_without_tracing_nothing_is_sent(monkeypatch):
    import httpx

    monkeypatch.setattr(httpx, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("sent")))
    monkeypatch.setattr(tracing, "enabled", lambda: False)
    tracing.price_model("deepseek-flash", {"input": 1.0})
