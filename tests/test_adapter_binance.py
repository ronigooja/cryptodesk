from pathlib import Path

import pytest

from cryptodesk import model, registry
from cryptodesk.adapters import binance
from cryptodesk.adapters.base import FetchError

FETCHED = "2026-11-06T12:00:00Z"
AS_OF = "2023-11-14T22:13:20Z"
PROFILE = {"binance": {"spot": "BTCUSDT", "perp": "BTCUSDT"}}
RESPONSES = {
    "/api/v3/ticker/24hr": {"lastPrice": "90000", "priceChangePercent": "-2.5", "highPrice": "92000", "lowPrice": "88000", "closeTime": 1700000000000},
    "/fapi/v1/premiumIndex": {"markPrice": "90010", "lastFundingRate": "0.0001", "time": 1700000000000},
    "/fapi/v1/openInterest": {"openInterest": "123.5", "time": 1700000000000},
    "/futures/data/topLongShortPositionRatio": [{"longShortRatio": "1.25", "timestamp": 1700000000000}],
    "/futures/data/topLongShortAccountRatio": [{"longShortRatio": "0.75", "timestamp": 1700000000000}],
}
EXPECTED = {
    "spot_price": 90000, "change_24h_pct": -2.5, "high_24h": 92000,
    "low_24h": 88000, "perp_mark_price": 90010, "funding_rate_8h": 0.0001,
    "open_interest": 123.5, "top_ls_position_ratio": 1.25, "top_ls_account_ratio": 0.75,
}
ENDPOINT_METRICS = [
    ("/api/v3/ticker/24hr", {"spot_price", "change_24h_pct", "high_24h", "low_24h"}),
    ("/fapi/v1/premiumIndex", {"perp_mark_price", "funding_rate_8h"}),
    ("/fapi/v1/openInterest", {"open_interest"}),
    ("/futures/data/topLongShortPositionRatio", {"top_ls_position_ratio"}),
    ("/futures/data/topLongShortAccountRatio", {"top_ls_account_ratio"}),
]


@pytest.mark.parametrize("failure,metrics", [(None, set())] + ENDPOINT_METRICS)
@pytest.mark.parametrize("bad", ["http", {}, None, []])
def test_collect_values_endpoint_isolation_and_validation(failure, metrics, bad):
    calls = []

    def get(url, params):
        path = next(path for path in RESPONSES if url.endswith(path))
        calls.append(path)
        expected_params = {"symbol": "BTCUSDT"}
        if "Ratio" in path:
            expected_params.update(period="1h", limit=1)
        assert params == expected_params
        if path == failure:
            if bad == "http":
                raise FetchError("HTTP 451")
            return bad
        return RESPONSES[path]

    facts = binance.collect("btc", PROFILE, get, FETCHED)
    assert calls == list(RESPONSES)
    assert {f.id for f in facts} == {f"binance.btc.{metric}" for metric in EXPECTED}
    assert len(facts) == len(EXPECTED)
    real_registry = registry.parse(Path("docs/metrics.md").read_text())
    for fact in facts:
        assert model.validate(fact.to_dict(), real_registry) == []
        assert (fact.coin, fact.source, fact.fetched_at) == ("btc", "binance", FETCHED)
        if fact.metric in metrics:
            assert fact.status == "missing"
            assert fact.value is fact.as_of is None
            assert fact.reason == ("HTTP 451" if bad == "http" else "field absent in response")
        else:
            assert fact.status == "ok"
            assert fact.value == EXPECTED[fact.metric]
            assert fact.as_of == AS_OF
            assert fact.reason is None
        assert fact.unit == ("percent" if fact.metric == "change_24h_pct" else "fraction" if fact.metric == "funding_rate_8h" else "BTC" if fact.metric == "open_interest" else "ratio" if "ratio" in fact.metric else "USDT")


@pytest.mark.parametrize("value", [None, "not a number", {}])
def test_malformed_price_preserves_other_ticker_fields(value):
    def get(url, params):
        path = next(path for path in RESPONSES if url.endswith(path))
        if path == "/api/v3/ticker/24hr":
            return {**RESPONSES[path], "lastPrice": value}
        return RESPONSES[path]

    facts = binance.collect("btc", PROFILE, get, FETCHED)
    real_registry = registry.parse(Path("docs/metrics.md").read_text())
    for fact in facts:
        assert model.validate(fact.to_dict(), real_registry) == []
        if fact.metric == "spot_price":
            assert fact.status == "missing"
            assert fact.reason == "field absent in response"
        else:
            assert fact.status == "ok"
            assert fact.value == EXPECTED[fact.metric]
