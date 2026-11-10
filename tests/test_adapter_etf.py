from pathlib import Path

import pytest

from cryptodesk import model, registry
from cryptodesk.adapters import etf
from cryptodesk.adapters.base import FetchError

STARTED = "2026-11-11T12:00:00Z"
REG = registry.parse((Path(__file__).resolve().parents[1] / "docs" / "metrics.md").read_text())
HTML = """<h2>Bitcoin ETF Flow (US$m)</h2><table><tbody>
<tr><th><span>Date</span></th><th>IBIT</th><th>FBTC</th><th>NEWF</th><th>Totals</th></tr>
<tr><td>Nov 06, 2026</td><td>12.3</td><td>9.0</td><td>1.0</td><td>22.3</td></tr>
<tr><td><span>Nov 09, 2026</span></td><td>-210.5</td><td>0.0</td><td>-</td><td>-198.6</td></tr>
</tbody></table>"""


def collect(text=HTML, get=None):
    facts = etf.collect(get or (lambda url, params: text), STARTED)
    for fact in facts:
        assert not model.validate(fact.to_dict(), REG)
        assert fact.unit == "USD"
    return {fact.metric: fact for fact in facts}


def test_newest_row_units_and_unknown_fund():
    facts = collect()
    assert set(facts) == {"etf_flow_ibit", "etf_flow_fbtc", "etf_flow_newf", "etf_flow_total"}
    assert facts["etf_flow_ibit"].value == -210_500_000
    assert facts["etf_flow_total"].value == -198_600_000
    assert facts["etf_flow_total"].id == "bitbo.btc.etf_flow_total"
    assert facts["etf_flow_total"].as_of == "2026-11-09T00:00:00Z"


def test_newest_first_order_also_works():
    before, rest = HTML.split('<tr><td>Nov 06, 2026')
    older, rest = rest.split('</tr>', 1)
    text = before + rest.replace('</tbody>', '<tr><td>Nov 06, 2026' + older + '</tr></tbody>')
    assert collect(text)["etf_flow_total"].as_of == "2026-11-09T00:00:00Z"


@pytest.mark.parametrize("placeholder", ["-", "", "  "])
def test_zero_is_real_but_placeholders_are_missing(placeholder):
    facts = collect(HTML.replace('<td>-</td>', f'<td>{placeholder}</td>'))
    assert facts["etf_flow_fbtc"].status == "ok" and facts["etf_flow_fbtc"].value == 0
    fact = facts["etf_flow_newf"]
    assert fact.status == "missing" and fact.value is None and fact.reason == "not published"


@pytest.mark.parametrize("text", ["", "<html>blocked</html>", HTML.replace('</table>', ''),
                                  HTML.replace('</td>', '', 1),
                                  HTML.replace('Nov 09, 2026', 'bad date'),
                                  HTML.replace('<td>0.0</td>', ''),
                                  HTML.replace('US$m', 'BTC')])
def test_malformed_html_is_missing(text):
    assert all(f.status == "missing" and f.reason == "field absent in response" for f in collect(text).values())


@pytest.mark.parametrize("old,new", [("Date", "Day"), ("Totals", "Sum"), ("FBTC", "IBIT"), ("NEWF", "Not a ticker")])
def test_header_mismatch(old, new):
    assert all(f.reason == "field absent in response" for f in collect(HTML.replace(old, new)).values())


@pytest.mark.parametrize("raw", ["oops", "nan", "inf"])
def test_invalid_value_only_affects_its_metric(raw):
    facts = collect(HTML.replace('-210.5', raw))
    assert facts["etf_flow_ibit"].reason == "field absent in response"
    assert facts["etf_flow_total"].status == "ok"


def test_fetch_error_and_request():
    def get(url, params):
        assert url == etf.BASE and params == {}
        raise FetchError("HTTP 503")

    facts = collect(get=get)
    assert len(facts) == len(etf.FUNDS) + 1
    assert all(f.status == "missing" and f.reason == "HTTP 503" for f in facts.values())


def test_empty_table_is_not_published():
    text = '<h2>Bitcoin ETF Flow (US$m)</h2><table><tr><th>Date</th><th>IBIT</th><th>Total</th></tr></table>'
    assert all(f.reason == "not published" for f in collect(text).values())
