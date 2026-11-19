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


def test_empty_cell_is_missing_not_zero():
    f = facts(page([["18 Nov 2026", "", "2.0", "2.0"]]))
    assert f["etf_flow_etha"].status == "missing" and f["etf_flow_etha"].value is None
    assert f["etf_flow_feth"].value == 2.0e6


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
