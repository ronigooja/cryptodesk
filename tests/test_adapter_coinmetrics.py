from pathlib import Path

import pytest

from cryptodesk import model, registry
from cryptodesk.adapters import coinmetrics
from cryptodesk.adapters.base import FetchError

FETCHED = "2026-11-11T12:00:00Z"
NEWEST = "2026-11-09T00:00:00.000000000Z"


def validate(facts):
    metrics = registry.parse(Path("docs/metrics.md").read_text())
    for fact in facts:
        assert model.validate(fact.to_dict(), metrics) == []
    return {fact.metric: fact for fact in facts}


@pytest.mark.parametrize("coin", ["btc", "eth"])
def test_newest_row_strings_and_units(coin):
    def get(url, params):
        assert url == coinmetrics.URL
        assert params == {"assets": coin, "metrics": "CapMVRVCur,AdrActCnt,FeeTotNtv",
                          "frequency": "1d", "page_size": 4, "sort": "time", "paging_from": "end"}
        return {"data": [
            {"asset": coin, "time": NEWEST, "CapMVRVCur": "1.25", "AdrActCnt": "123", "FeeTotNtv": "0.5"},
            {"asset": coin, "time": "2026-11-08T00:00:00Z", "CapMVRVCur": "99"},
            {"asset": "other", "time": "2026-11-10T00:00:00Z", "CapMVRVCur": "88"},
        ]}

    facts = validate(coinmetrics.collect(coin, get, FETCHED))
    for metric, expected in {"mvrv": 1.25, "active_addresses": 123.0, "fees_total": 0.5}.items():
        fact = facts[metric]
        assert fact.id == f"coinmetrics.{coin}.{metric}"
        assert fact.value == expected and isinstance(fact.value, float)
        assert fact.as_of == "2026-11-09T00:00:00Z"
        assert fact.unit == {"mvrv": "ratio", "active_addresses": "count", "fees_total": coin.upper()}[metric]


@pytest.mark.parametrize("bad", [None, "N/A", "NaN", "Infinity", {}])
def test_bad_field_does_not_hide_other_fields_or_use_old_row(bad):
    row = {"asset": "btc", "time": NEWEST, "AdrActCnt": "123", "FeeTotNtv": "0"}
    if bad is not None:
        row["CapMVRVCur"] = bad
    data = {"data": [row, {"asset": "btc", "time": "2026-11-08T00:00:00Z", "CapMVRVCur": "2"}]}
    facts = validate(coinmetrics.collect("btc", lambda *_: data, FETCHED))
    assert facts["mvrv"].status == "missing"
    assert facts["mvrv"].reason == "field absent in response"
    assert facts["mvrv"].value is None
    assert facts["active_addresses"].value == 123
    assert facts["fees_total"].status == "ok" and facts["fees_total"].value == 0


@pytest.mark.parametrize("data", [{}, {"data": []}, {"data": None}])
def test_absent_rows(data):
    facts = validate(coinmetrics.collect("btc", lambda *_: data, FETCHED))
    assert all(f.status == "missing" and f.reason == "field absent in response" for f in facts.values())


def test_fetch_error():
    def get(*_):
        raise FetchError("HTTP 429")

    facts = validate(coinmetrics.collect("eth", get, FETCHED))
    assert all(f.status == "missing" and f.reason == "HTTP 429" for f in facts.values())


def test_unsupported_coin():
    assert coinmetrics.collect("sol", None, FETCHED) == []
