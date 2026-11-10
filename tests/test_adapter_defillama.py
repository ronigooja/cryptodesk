from pathlib import Path

import pytest

from cryptodesk import model, registry
from cryptodesk.adapters import defillama
from cryptodesk.adapters.base import FetchError

FETCHED = "2026-11-11T12:00:00Z"


def asset(symbol, value, peg="peggedUSD"):
    return {"symbol": symbol, "pegType": peg, "circulating": {peg: value}}


def validate(facts):
    metrics = registry.parse(Path("docs/metrics.md").read_text())
    for fact in facts:
        assert model.validate(fact.to_dict(), metrics) == []
        assert fact.id == f"defillama.macro.{fact.metric}"
        assert fact.unit == "USD" and fact.as_of is None
    return {fact.metric: fact for fact in facts}


def test_supply_strings_filter_and_duplicate_symbols():
    def get(url, params):
        assert url == defillama.URL and params == {"includePrices": "false"}
        return {"peggedAssets": [asset("USDT", "100"), asset("USDT", "10"), asset("USDC", "50"),
                                 asset("OTHER", "5"), asset("EUR", "999", "peggedEUR")]}

    facts = validate(defillama.collect(None, get, FETCHED))
    assert facts["usdt_supply_usd"].value == 100
    assert facts["usdc_supply_usd"].value == 50
    assert facts["stablecoin_supply_usd"].value == 165
    assert all(f.status == "ok" for f in facts.values())


@pytest.mark.parametrize("bad", [None, "N/A", "NaN", "Infinity", {}])
def test_bad_supply_never_becomes_zero_or_partial_total(bad):
    usdt = asset("USDT", bad)
    if bad is None:
        usdt["circulating"] = {}
    data = {"peggedAssets": [usdt, asset("USDC", 0)]}
    facts = validate(defillama.collect("macro", lambda *_: data, FETCHED))
    for metric in ("usdt_supply_usd", "stablecoin_supply_usd"):
        assert facts[metric].status == "missing" and facts[metric].value is None
        assert facts[metric].reason == "field absent in response"
    assert facts["usdc_supply_usd"].status == "ok" and facts["usdc_supply_usd"].value == 0


@pytest.mark.parametrize("data", [{}, {"peggedAssets": []}, {"peggedAssets": None}])
def test_absent_assets(data):
    facts = validate(defillama.collect(None, lambda *_: data, FETCHED))
    assert all(f.status == "missing" and f.reason == "field absent in response" for f in facts.values())


def test_absent_symbol_only_affects_that_fact():
    facts = validate(defillama.collect(None, lambda *_: {"peggedAssets": [asset("USDT", 100)]}, FETCHED))
    assert facts["usdt_supply_usd"].value == facts["stablecoin_supply_usd"].value == 100
    assert facts["usdc_supply_usd"].status == "missing"


def test_fetch_error():
    def get(*_):
        raise FetchError("HTTP 503")

    facts = validate(defillama.collect(None, get, FETCHED))
    assert all(f.status == "missing" and f.reason == "HTTP 503" for f in facts.values())


def test_unsupported_coin():
    assert defillama.collect("btc", None, FETCHED) == []
