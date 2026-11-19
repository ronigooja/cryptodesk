from pathlib import Path

from cryptodesk import model, registry
from cryptodesk.adapters import fred
from cryptodesk.adapters.base import FetchError

STARTED = "2026-11-19T12:00:00Z"
REG = registry.parse((Path(__file__).resolve().parents[1] / "docs" / "metrics.md").read_text())
CSV = ("observation_date,CPIAUCNS\n2025-09-01,324.800\n2025-10-01,\n2026-09-01,336.940\n2026-10-01,\n")


def by_metric(facts):
    return {f.metric: f for f in facts}


def test_newest_value_and_yoy():
    f = by_metric(fred.collect(lambda url, p: CSV, STARTED))
    assert f["cpi_index"].value == 336.94
    assert f["cpi_index"].as_of == "2026-09-01T00:00:00Z"
    assert f["cpi_yoy_pct"].value == round((336.94 / 324.8 - 1) * 100, 3)
    assert all(not model.validate(x.to_dict(), REG) for x in f.values())


def test_blank_prior_year_month_gives_missing_yoy_not_zero():
    text = "observation_date,CPIAUCNS\n2025-10-01,\n2026-10-01,337.511\n"
    f = by_metric(fred.collect(lambda url, p: text, STARTED))
    assert f["cpi_index"].value == 337.511
    assert f["cpi_yoy_pct"].status == "missing" and f["cpi_yoy_pct"].value is None


def test_bad_header_is_missing():
    f = fred.collect(lambda url, p: "a,b\n1,2\n", STARTED)
    assert all(x.status == "missing" and x.reason == "field absent in response" for x in f)


def test_fetch_error_is_missing():
    def boom(url, p):
        raise FetchError("HTTP 403")

    f = fred.collect(boom, STARTED)
    assert all(x.status == "missing" and x.reason == "HTTP 403" for x in f)
