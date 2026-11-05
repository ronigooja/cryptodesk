from datetime import UTC, datetime
from pathlib import Path

import pytest

from cryptodesk import model, registry
from cryptodesk.adapters import deribit
from cryptodesk.adapters.base import FetchError

FETCHED = "2026-11-06T12:00:00Z"
AS_OF = "2023-11-14T22:13:20Z"
PROFILE = {"deribit": {"currency": "BTC", "perp": "BTC-PERPETUAL"}}
NOW = datetime(2026, 11, 6, 12, tzinfo=UTC)
RESPONSES = {
    "/ticker": {"result": {"mark_price": 90050, "funding_8h": -0.0001, "timestamp": 1700000000000}},
    "/get_volatility_index_data": {"result": {"data": [[1699996400000, 40, 45, 39, 41], [1700000000000, 41, 50, 40, 48.5]]}},
}
EXPECTED = {"perp_mark_price": 90050, "funding_rate_8h": -0.0001, "dvol": 48.5}
SUMMARY = [
    {"instrument_name": "BTC-27NOV26-80000-C", "open_interest": 2},
    {"instrument_name": "BTC-27NOV26-80000-P", "open_interest": 1},
    {"instrument_name": "BTC-27NOV26-90000-C", "open_interest": 3},
    {"instrument_name": "BTC-27NOV26-90000-P", "open_interest": 4},
    {"instrument_name": "BTC-27NOV26-100000-C", "open_interest": 1},
    {"instrument_name": "BTC-27NOV26-100000-P", "open_interest": 2},
    {"instrument_name": "BTC-6NOV26-90000.5-C", "open_interest": "5.5"},
    {"instrument_name": "BTC-PERPETUAL", "open_interest": 999},
]


def assert_valid(facts):
    real_registry = registry.parse(Path("docs/metrics.md").read_text())
    for fact in facts:
        assert model.validate(fact.to_dict(), real_registry) == []
        assert (fact.source, fact.coin, fact.fetched_at) == ("deribit", "btc", FETCHED)


@pytest.mark.parametrize("failure,metrics", [(None, set()), ("/ticker", {"perp_mark_price", "funding_rate_8h"}), ("/get_volatility_index_data", {"dvol"})])
@pytest.mark.parametrize("bad", ["http", {}, {"result": {}}, {"result": {"data": []}}, {"result": None}])
def test_collect_market_values_endpoint_isolation_and_validation(failure, metrics, bad):
    calls = []

    def get(url, params):
        path = next(path for path in RESPONSES if url.endswith(path))
        calls.append(path)
        end = int(NOW.timestamp() * 1000)
        assert params == ({"instrument_name": "BTC-PERPETUAL"} if path == "/ticker" else {"currency": "BTC", "resolution": "3600", "start_timestamp": end - 10800000, "end_timestamp": end})
        if path == failure:
            if bad == "http":
                raise FetchError("HTTP 451")
            return bad
        return RESPONSES[path]

    facts = deribit.collect_market("btc", PROFILE, get, FETCHED, now=NOW)
    assert calls == list(RESPONSES)
    assert len(facts) == len(EXPECTED)
    assert {f.id for f in facts} == {f"deribit.btc.{metric}" for metric in EXPECTED}
    assert_valid(facts)
    for fact in facts:
        if fact.metric in metrics:
            assert fact.status == "missing"
            assert fact.value is fact.as_of is None
            assert fact.reason == ("HTTP 451" if bad == "http" else "field absent in response")
        else:
            assert fact.status == "ok"
            assert fact.value == EXPECTED[fact.metric]
            assert fact.as_of == AS_OF
            assert fact.reason is None
        assert fact.unit == {"perp_mark_price": "USD", "funding_rate_8h": "fraction", "dvol": "percent"}[fact.metric]


def test_max_pain_matches_hand_computed_payouts():
    # Holder payouts at 80k, 90k, 100k are respectively 80k, 40k, 70k USD.
    strikes = {80000: {"C": 2, "P": 1}, 90000: {"C": 3, "P": 4}, 100000: {"C": 1, "P": 2}}
    assert deribit.max_pain(strikes) == 90000


@pytest.mark.parametrize("value", [None, "not a number", {}])
def test_malformed_mark_price_preserves_funding_and_dvol(value):
    def get(url, params):
        if url.endswith("/ticker"):
            return {"result": {**RESPONSES["/ticker"]["result"], "mark_price": value}}
        return RESPONSES["/get_volatility_index_data"]

    facts = deribit.collect_market("btc", PROFILE, get, FETCHED, now=NOW)
    assert_valid(facts)
    for fact in facts:
        if fact.metric == "perp_mark_price":
            assert fact.status == "missing"
            assert fact.reason == "field absent in response"
        else:
            assert fact.status == "ok"
            assert fact.value == EXPECTED[fact.metric]


@pytest.mark.parametrize("strikes,expected", [({}, None), ({90000: {"C": 0}}, 90000), ({100000: {}, 80000: {}}, 80000), ({80000: {"C": 2}, 90000: {"P": 2}}, 80000)])
def test_max_pain_empty_missing_sides_and_lowest_strike_ties(strikes, expected):
    assert deribit.max_pain(strikes) == expected


def test_group_options_parses_expiry_decimal_strike_and_both_sides():
    assert deribit.group_options(SUMMARY) == {
        "2026-11-27": {80000.0: {"C": 2.0, "P": 1.0}, 90000.0: {"C": 3.0, "P": 4.0}, 100000.0: {"C": 1.0, "P": 2.0}},
        "2026-11-06": {90000.5: {"C": 5.5}},
    }


def test_option_facts_totals_ids_units_and_no_invented_source_time():
    facts = deribit.option_facts("btc", SUMMARY, FETCHED)
    expected = {
        "2026-11-06.oi_call": 5.5, "2026-11-06.oi_put": 0, "2026-11-06.max_pain": 90000.5,
        "2026-11-27.oi_call": 6, "2026-11-27.oi_put": 7, "2026-11-27.max_pain": 90000,
    }
    assert {f.id: f.value for f in facts} == {f"deribit.btc.opt.{suffix}": value for suffix, value in expected.items()}
    assert len(facts) == 6
    assert_valid(facts)
    for fact in facts:
        assert fact.status == "ok"
        assert fact.as_of is fact.reason is None
        assert fact.unit == ("USD" if fact.metric == "max_pain" else "BTC")


def test_collect_options_uses_summary_endpoint():
    def get(url, params):
        assert url == deribit.BASE + "/get_book_summary_by_currency"
        assert params == {"currency": "BTC", "kind": "option"}
        return {"result": SUMMARY}

    facts = deribit.collect_options("btc", PROFILE, get, FETCHED)
    assert facts == deribit.option_facts("btc", SUMMARY, FETCHED)
    assert_valid(facts)


@pytest.mark.parametrize("bad", ["http", {}, {"result": None}, {"result": [{}]}, {"result": [{"instrument_name": "BTC-27NOV26-90000-C"}]}, {"result": [{"instrument_name": "BTC-31NOV26-90000-C", "open_interest": 1}]}])
def test_collect_options_failure_returns_one_valid_missing_fact(bad):
    def get(url, params):
        if bad == "http":
            raise FetchError("HTTP 451")
        return bad

    facts = deribit.collect_options("btc", PROFILE, get, FETCHED)
    assert len(facts) == 1
    fact, = facts
    assert fact.id == "deribit.btc.opt.unknown.oi_call"
    assert fact.status == "missing"
    assert fact.value is fact.as_of is None
    assert fact.reason == ("HTTP 451" if bad == "http" else "field absent in response")
    assert_valid(facts)
