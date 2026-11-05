from pathlib import Path

import httpx
import pytest

from cryptodesk import model, registry
from cryptodesk.adapters import base

FETCHED = "2026-11-06T12:00:00Z"
AS_OF = "2023-11-14T22:13:20Z"


def test_run_endpoint_values_ids_and_real_registry():
    calls = []

    def get(url, params):
        calls.append((url, params))
        return {"price": "0", "time": 1700000000000}

    ep = base.Endpoint("https://example.invalid/ticker", {"symbol": "BTC"}, [
        base.Spec("spot_price", "USD", lambda d: (float(d["price"]), model.ms_to_iso(d["time"]))),
    ])
    facts = base.run_endpoint(get, ep, "binance", "btc", FETCHED)
    assert calls == [(ep.url, ep.params)]
    assert facts == [model.ok("binance.btc.spot_price", "btc", "spot_price", 0.0, "USD", AS_OF, FETCHED, "binance")]
    real_registry = registry.parse(Path("docs/metrics.md").read_text())
    for fact in facts:
        assert model.validate(fact.to_dict(), real_registry) == []


@pytest.mark.parametrize("bad", [{}, {"price": "bad"}, {"price": None}, [], None])
def test_run_endpoint_malformed_field_does_not_poison_other_specs(bad):
    ep = base.Endpoint("unused", {}, [
        base.Spec("spot_price", "USD", lambda d: (float(d["price"]), AS_OF)),
        base.Spec("high_24h", "USD", lambda d: (10.0, AS_OF)),
    ])
    facts = base.run_endpoint(lambda url, params: bad, ep, "binance", "btc", FETCHED)
    assert facts[0].status == "missing"
    assert facts[0].reason == "field absent in response"
    assert facts[0].value is facts[0].as_of is None
    assert facts[1].status == "ok"
    real_registry = registry.parse(Path("docs/metrics.md").read_text())
    for fact in facts:
        assert model.validate(fact.to_dict(), real_registry) == []


def test_run_endpoint_none_value_and_id_infix():
    ep = base.Endpoint("unused", {}, [base.Spec("oi_call", "BTC", lambda d: (None, AS_OF), "opt.2026-11-27.")])
    fact, = base.run_endpoint(lambda url, params: {}, ep, "deribit", "btc", FETCHED)
    assert fact.id == "deribit.btc.opt.2026-11-27.oi_call"
    assert fact.reason == "field absent in response"
    assert fact.value is fact.as_of is None
    assert model.validate(fact.to_dict(), registry.parse(Path("docs/metrics.md").read_text())) == []


def test_run_endpoint_fetch_error_marks_all_specs_without_extracting():
    def get(url, params):
        raise base.FetchError("HTTP 451")

    def extract(data):
        pytest.fail("extract must not run after a fetch failure")

    ep = base.Endpoint("unused", {}, [base.Spec("spot_price", "USD", extract), base.Spec("high_24h", "USD", extract)])
    facts = base.run_endpoint(get, ep, "binance", "btc", FETCHED)
    assert len(facts) == 2
    real_registry = registry.parse(Path("docs/metrics.md").read_text())
    for fact in facts:
        assert fact.status == "missing"
        assert fact.reason == "HTTP 451"
        assert fact.value is fact.as_of is None
        assert model.validate(fact.to_dict(), real_registry) == []


@pytest.mark.parametrize("outcome,reason", [
    (httpx.Response(451), "HTTP 451"),
    (httpx.Response(200, content=b"not json"), "invalid JSON"),
    (httpx.ReadTimeout("slow"), "Timeout"),
    (httpx.ConnectError("offline"), "request error ConnectError"),
])
def test_make_get_translates_transport_failures(monkeypatch, outcome, reason):
    class Client:
        def __init__(self, **kwargs):
            assert kwargs == {"timeout": 3, "headers": {"User-Agent": "cryptodesk"}}

        def get(self, url, params):
            assert (url, params) == ("https://example.invalid", {"a": 1})
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    monkeypatch.setattr(base.httpx, "Client", Client)
    with pytest.raises(base.FetchError, match=f"^{reason}$"):
        base.make_get(timeout=3)("https://example.invalid", {"a": 1})


def test_make_get_decodes_json_without_network(monkeypatch):
    class Client:
        def __init__(self, **kwargs):
            pass

        def get(self, url, params):
            assert params is None
            return httpx.Response(200, json={"lastPrice": "90000"})

    monkeypatch.setattr(base.httpx, "Client", Client)
    assert base.make_get()("unused") == {"lastPrice": "90000"}
