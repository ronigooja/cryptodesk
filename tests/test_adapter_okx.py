from pathlib import Path

import pytest

from cryptodesk import model, registry
from cryptodesk.adapters import okx
from cryptodesk.adapters.base import FetchError

FETCHED = "2026-11-06T12:00:00Z"
AS_OF = "2023-11-14T22:13:20Z"
PROFILE = {"okx": {"spot": "BTC-USDT", "swap": "BTC-USDT-SWAP"}}
RESPONSES = {
    "/market/ticker": {"code": "0", "data": [{"last": "90000", "high24h": "92000", "low24h": "88000", "ts": "1700000000000"}]},
    "/public/funding-rate": {"code": "0", "data": [{"fundingRate": "-0.0002", "ts": "1700000000000"}]},
    "/public/open-interest": {"code": "0", "data": [{"oiCcy": "12.5", "oiUsd": "1125000", "ts": "1700000000000"}]},
}
EXPECTED = {"spot_price": 90000, "high_24h": 92000, "low_24h": 88000, "funding_rate_8h": -0.0002, "open_interest": 12.5, "open_interest_usd": 1125000}
ENDPOINT_METRICS = [
    ("/market/ticker", {"spot_price", "high_24h", "low_24h"}),
    ("/public/funding-rate", {"funding_rate_8h"}),
    ("/public/open-interest", {"open_interest", "open_interest_usd"}),
]


@pytest.mark.parametrize("failure,metrics", [(None, set())] + ENDPOINT_METRICS)
@pytest.mark.parametrize("bad", ["http", {}, {"code": "0", "data": []}, {"code": "0", "data": [{}]}, {"code": "500", "data": []}, {"code": "0", "data": None}])
def test_collect_values_endpoint_isolation_and_validation(failure, metrics, bad):
    calls = []

    def get(url, params):
        path = next(path for path in RESPONSES if url.endswith(path))
        calls.append(path)
        expected_params = {"instId": "BTC-USDT" if path == "/market/ticker" else "BTC-USDT-SWAP"}
        if path == "/public/open-interest":
            expected_params["instType"] = "SWAP"
        assert params == expected_params
        if path == failure:
            if bad == "http":
                raise FetchError("HTTP 451")
            return bad
        return RESPONSES[path]

    facts = okx.collect("btc", PROFILE, get, FETCHED)
    assert calls == list(RESPONSES)
    assert len(facts) == len(EXPECTED)
    assert {f.id for f in facts} == {f"okx.btc.{metric}" for metric in EXPECTED}
    real_registry = registry.parse(Path("docs/metrics.md").read_text())
    for fact in facts:
        assert model.validate(fact.to_dict(), real_registry) == []
        assert (fact.coin, fact.source, fact.fetched_at) == ("btc", "okx", FETCHED)
        if fact.metric in metrics:
            assert fact.status == "missing"
            assert fact.value is fact.as_of is None
            assert fact.reason == ("HTTP 451" if bad == "http" else "field absent in response")
        else:
            assert fact.status == "ok"
            assert fact.value == EXPECTED[fact.metric]
            assert fact.as_of == AS_OF
            assert fact.reason is None
        assert fact.unit == ("fraction" if fact.metric == "funding_rate_8h" else "BTC" if fact.metric == "open_interest" else "USD" if fact.metric == "open_interest_usd" else "USDT")


def test_collect_null_ticker_response_yields_missing_without_aborting_other_endpoints():
    def get(url, params):
        path = next(path for path in RESPONSES if url.endswith(path))
        return None if path == "/market/ticker" else RESPONSES[path]

    facts = okx.collect("btc", PROFILE, get, FETCHED)
    real_registry = registry.parse(Path("docs/metrics.md").read_text())
    assert len(facts) == len(EXPECTED)
    for fact in facts:
        assert model.validate(fact.to_dict(), real_registry) == []
        if fact.metric in {"spot_price", "high_24h", "low_24h"}:
            assert fact.status == "missing"
            assert fact.reason == "field absent in response"
        else:
            assert fact.status == "ok"


@pytest.mark.parametrize("value", [None, "not a number", {}])
def test_malformed_oi_coin_value_preserves_usd_value(value):
    def get(url, params):
        path = next(path for path in RESPONSES if url.endswith(path))
        if path == "/public/open-interest":
            return {"code": "0", "data": [{**RESPONSES[path]["data"][0], "oiCcy": value}]}
        return RESPONSES[path]

    facts = okx.collect("btc", PROFILE, get, FETCHED)
    real_registry = registry.parse(Path("docs/metrics.md").read_text())
    for fact in facts:
        assert model.validate(fact.to_dict(), real_registry) == []
        if fact.metric == "open_interest":
            assert fact.status == "missing"
            assert fact.reason == "field absent in response"
        else:
            assert fact.status == "ok"
            assert fact.value == EXPECTED[fact.metric]
