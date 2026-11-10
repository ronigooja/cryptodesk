from pathlib import Path

import pytest

from cryptodesk import model, registry
from cryptodesk.adapters import cftc
from cryptodesk.adapters.base import FetchError

FETCHED = "2026-11-06T21:00:00Z"
ROW = {
    "report_date_as_yyyy_mm_dd": "2026-11-03T00:00:00.000",
    "open_interest_all": "17527",
    "asset_mgr_positions_long": "4379",
    "asset_mgr_positions_short": "1976",
    "lev_money_positions_long": "5114",
    "lev_money_positions_short": "7705",
}
EXPECTED = {"cot_open_interest": 17527, "cot_asset_mgr_net": 2403, "cot_lev_money_net": -2591}


def assert_valid(facts, coin="btc"):
    real_registry = registry.parse(Path("docs/metrics.md").read_text())
    assert len(facts) == 3
    assert {f.id for f in facts} == {f"cftc.{coin}.{metric}" for metric in EXPECTED}
    for fact in facts:
        assert model.validate(fact.to_dict(), real_registry) == []
        assert (fact.source, fact.coin, fact.fetched_at, fact.unit) == ("cftc", coin, FETCHED, "contracts")


@pytest.mark.parametrize("coin", ["btc", "eth"])
@pytest.mark.parametrize("newest_first", [False, True])
def test_collect_exact_contract_newest_report_and_integer_nets(coin, newest_first):
    older = {**ROW, "report_date_as_yyyy_mm_dd": "2026-10-27T00:00:00.000", "open_interest_all": "999"}
    calls = []

    def get(url, params):
        calls.append(url)
        assert url == "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
        market = {
            "btc": "BITCOIN - CHICAGO MERCANTILE EXCHANGE",
            "eth": "ETHER CASH SETTLED - CHICAGO MERCANTILE EXCHANGE",
        }[coin]
        assert params == {
            "$where": f"market_and_exchange_names = '{market}'",
            "$order": "report_date_as_yyyy_mm_dd DESC",
            "$limit": 1,
        }
        return [ROW, older] if newest_first else [older, ROW]

    facts = cftc.collect(coin, {}, get, FETCHED)
    assert calls == [cftc.BASE]
    assert_valid(facts, coin)
    for fact in facts:
        assert fact.status == "ok"
        assert type(fact.value) is int
        assert fact.value == EXPECTED[fact.metric]
        assert fact.as_of == "2026-11-03T00:00:00Z"
        assert fact.reason is None


@pytest.mark.parametrize("bad,reason", [
    ([], "not published"),
    ("http", "HTTP 503"),
    ({}, "field absent in response"),
    (None, "field absent in response"),
    ([{}], "field absent in response"),
    ([{**ROW, "report_date_as_yyyy_mm_dd": "bad date"}], "field absent in response"),
])
def test_empty_malformed_and_fetch_failures_are_missing(bad, reason):
    def get(url, params):
        if bad == "http":
            raise FetchError("HTTP 503")
        return bad

    facts = cftc.collect("btc", {}, get, FETCHED)
    assert_valid(facts)
    for fact in facts:
        assert fact.status == "missing"
        assert fact.value is fact.as_of is None
        assert fact.reason == reason


@pytest.mark.parametrize("field,metric", [
    ("open_interest_all", "cot_open_interest"),
    ("asset_mgr_positions_long", "cot_asset_mgr_net"),
    ("asset_mgr_positions_short", "cot_asset_mgr_net"),
    ("lev_money_positions_long", "cot_lev_money_net"),
    ("lev_money_positions_short", "cot_lev_money_net"),
])
@pytest.mark.parametrize("bad", ["absent", None, "N/A", "-"])
def test_bad_field_only_affects_its_metric(field, metric, bad):
    row = dict(ROW)
    if bad == "absent":
        del row[field]
    else:
        row[field] = bad
    facts = cftc.collect("btc", {}, lambda url, params: [row], FETCHED)
    assert_valid(facts)
    for fact in facts:
        if fact.metric == metric:
            assert fact.status == "missing"
            assert fact.value is fact.as_of is None
            assert fact.reason == "field absent in response"
        else:
            assert fact.status == "ok"
            assert fact.value == EXPECTED[fact.metric]


def test_report_date_is_required_and_true_zero_is_preserved():
    row = {field: "0" for field in ROW}
    row["report_date_as_yyyy_mm_dd"] = ROW["report_date_as_yyyy_mm_dd"]
    facts = cftc.collect("btc", {}, lambda url, params: [row], FETCHED)
    assert_valid(facts)
    assert all(f.status == "ok" and f.value == 0 for f in facts)
    del row["report_date_as_yyyy_mm_dd"]
    facts = cftc.collect("btc", {}, lambda url, params: [row], FETCHED)
    assert_valid(facts)
    assert all(f.status == "missing" and f.reason == "field absent in response" for f in facts)
