from pathlib import Path

import pytest

from cryptodesk import model, registry
from cryptodesk.adapters import farside
from cryptodesk.adapters.base import FetchError

STARTED = "2026-11-19T12:00:00Z"
REG = registry.parse((Path(__file__).resolve().parents[1] / "docs" / "metrics.md").read_text())


def page(rows):
    return ("<html>Daily Flow (US$m)<table class='etf'>"
            "<tr><th></th><th>Total</th></tr>"
            "<tr><td></td><td>ETHA</td><td>FETH</td><td></td></tr>"
            "<tr><td>Fee</td><td>0.25%</td><td>0.25%</td><td></td></tr>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
            + "<tr><td>Total</td><td>1</td><td>2</td><td>3</td></tr></table></html>")


def facts(text):
    return {f.metric: f for f in farside.collect(lambda url, p: text, STARTED)}


def test_newest_row_parentheses_are_negative_and_scaled():
    f = facts(page([["17 Nov 2026", "1.0", "0.0", "1.0"], ["18 Nov 2026", "(17.4)", "(5.0)", "(22.4)"]]))
    assert f["etf_flow_etha"].value == -17.4e6
    assert f["etf_flow_total"].value == -22.4e6
    assert f["etf_flow_total"].as_of == "2026-11-18T00:00:00Z"
    assert f["etf_flow_total"].id == "farside.eth.etf_flow_total"
    assert all(not model.validate(x.to_dict(), REG) for x in f.values())


@pytest.mark.parametrize("placeholder", ["", "-"])
def test_incomplete_eth_row_skipped(placeholder):
    f = facts(page([["17 Nov 2026", "1.0", "2.0", "3.0"],
                    ["18 Nov 2026", placeholder, "2.0", "2.0"]]))
    assert f["etf_flow_etha"].value == 1e6
    assert f["etf_flow_total"].value == 3e6
    assert all(x.as_of == "2026-11-17T00:00:00Z" for x in f.values())


def test_no_complete_row_is_missing_total():
    result = farside.collect(lambda url, p: page([["18 Nov 2026", "1.0", "-", "1.0"]]), STARTED)
    assert len(result) == 1 and result[0].id == "farside.eth.etf_flow_total"
    assert result[0].status == "missing" and result[0].reason == "not published"


def test_funds_not_adding_to_total_is_missing():
    f = farside.collect(lambda url, p: page([["18 Nov 2026", "1.0", "1.0", "9.0"]]), STARTED)
    assert len(f) == 1 and f[0].status == "missing" and f[0].reason == "field absent in response"


def test_wrong_units_or_layout_is_missing():
    for text in ("<html>no tables</html>", page([["18 Nov 2026", "1", "1", "2"]]).replace("US$m", "US$bn")):
        f = farside.collect(lambda url, p: text, STARTED)
        assert f[0].status == "missing" and f[0].reason == "field absent in response"


def test_fetch_error_is_missing():
    def boom(url, p):
        raise FetchError("HTTP 403")

    f = farside.collect(boom, STARTED)
    assert f[0].status == "missing" and f[0].reason == "HTTP 403"


def test_btc_incomplete_newest_selects_previous_complete_row():
    text = (Path(__file__).parent / "fixtures" / "farside_btc.html").read_text()
    seen = []
    def get(url, params):
        seen.append(url)
        return text
    result = farside.collect(get, STARTED, "btc")
    assert seen == ["https://farside.co.uk/btc/"]
    assert len(result) == 13
    previous = {f.metric: f for f in result}
    assert previous["etf_flow_total"].value == -582.3e6
    assert previous["etf_flow_total"].as_of == "2026-11-19T00:00:00Z"
    assert previous["etf_flow_ibit"].value == -541.1e6
    assert all(f.status == "ok" and f.as_of == "2026-11-19T00:00:00Z" for f in result)
    assert all(not model.validate(f.to_dict(), REG) for f in result)
