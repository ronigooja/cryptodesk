from pathlib import Path

import pytest

from cryptodesk import model, registry
from cryptodesk.adapters import nyfed, treasury
from cryptodesk.adapters.base import FetchError

STARTED = "2026-11-06T12:00:00Z"
REG = registry.parse((Path(__file__).resolve().parents[1] / "docs" / "metrics.md").read_text())
CSV = ('Date,"1 Mo","2 Yr","10 Yr"\n'
       "11/04/2026,4.01,4.58,4.90\n11/03/2026,4.03,4.61,4.95\n11/02/2026,4.05,N/A,\n")
EFFR = {"refRates": [{"effectiveDate": "2026-11-04", "type": "EFFR", "percentRate": 3.88}]}


def valid(facts):
    return all(not model.validate(f.to_dict(), REG) for f in facts)


def test_treasury_takes_newest_dated_row():
    facts = {f.metric: f for f in treasury.collect(lambda url, p: CSV, STARTED)}
    assert (facts["us2y_yield"].value, facts["us10y_yield"].value) == (4.58, 4.90)
    assert facts["us10y_yield"].as_of == "2026-11-04T00:00:00Z"
    assert facts["us10y_yield"].id == "treasury.macro.us10y_yield"
    assert valid(facts.values())


def test_treasury_oldest_first_order_still_picks_newest():
    text = 'Date,"2 Yr","10 Yr"\n11/03/2026,4.61,4.95\n11/04/2026,4.58,4.90\n'
    assert treasury.parse_latest(text, "10 Yr") == (4.90, "2026-11-04")


def test_treasury_na_is_not_zero():
    text = 'Date,"2 Yr","10 Yr"\n11/04/2026,N/A,\n'
    facts = treasury.collect(lambda url, p: text, STARTED)
    assert all(f.status == "missing" and f.reason == "not published" and f.value is None for f in facts)


def test_treasury_url_has_year_and_all():
    urls = []
    treasury.collect(lambda url, p: urls.append(url) or CSV, STARTED)
    assert urls == [treasury.BASE + "/2026/all"]


def test_treasury_new_year_falls_back_to_previous_year():
    calls = []

    def get(url, params):
        assert url.endswith(f"/{params['field_tdr_date_value']}/all")
        calls.append(params["field_tdr_date_value"])
        return 'Date,"2 Yr","10 Yr"\n' if params["field_tdr_date_value"] == 2027 else CSV

    facts = treasury.collect(get, "2027-01-02T12:00:00Z")
    assert calls == [2027, 2026]
    assert all(f.status == "ok" for f in facts)


@pytest.mark.parametrize("text", ["", "<html>blocked</html>", 'Date,"1 Mo"\n11/04/2026,4\n',
                                  'Date,"2 Yr","10 Yr"\n13/45/2026,4,4\n', 'Date,"2 Yr","10 Yr"\n11/04/2026,oops,oops\n'])
def test_treasury_malformed_is_missing(text):
    facts = treasury.collect(lambda url, p: text, STARTED)
    assert all(f.status == "missing" and f.reason == "field absent in response" for f in facts)


def test_treasury_fetch_error():
    def get(url, params):
        raise FetchError("HTTP 503")

    facts = treasury.collect(get, STARTED)
    assert {f.reason for f in facts} == {"HTTP 503"} and len(facts) == 2 and valid(facts)


def test_nyfed_ok():
    (fact,) = nyfed.collect(lambda url, p: EFFR, STARTED)
    assert (fact.id, fact.value, fact.as_of) == ("nyfed.macro.fed_funds_effective", 3.88, "2026-11-04T00:00:00Z")
    assert valid([fact])


@pytest.mark.parametrize("payload", [{}, {"refRates": []}, {"refRates": [{"effectiveDate": "2026-11-04"}]}, None,
                                     {"refRates": [{"effectiveDate": "x", "percentRate": 1}]}])
def test_nyfed_malformed_is_missing(payload):
    (fact,) = nyfed.collect(lambda url, p: payload, STARTED)
    assert fact.status == "missing" and fact.reason == "field absent in response" and valid([fact])


def test_nyfed_fetch_error():
    def get(url, params):
        raise FetchError("Timeout")

    (fact,) = nyfed.collect(get, STARTED)
    assert fact.reason == "Timeout"
