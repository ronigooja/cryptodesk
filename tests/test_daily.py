import json
from datetime import UTC, date, datetime, timedelta

import pytest

from cryptodesk import check, cli, daily
from cryptodesk.adapters.base import FetchError

SINCE, TODAY = date(2025, 1, 1), date(2025, 1, 3)
MS = 1735689600000


@pytest.mark.parametrize("parser,data,args", [
    (daily.parse_binance, [[MS, 0, 0, 0, "12"], [MS + 86400000 * 2, 0, 0, 0, "13"]], ()),
    (daily.parse_coinbase, [[MS // 1000, 0, 0, 0, "12"], [MS // 1000 + 86400 * 2, 0, 0, 0, "13"]], ()),
    (daily.parse_coinmetrics, {"data": [{"asset": "btc", "time": "2025-01-01T00:00:00Z", "CapMVRVCur": "12"},
                                       {"asset": "btc", "time": "2025-01-03T00:00:00Z", "CapMVRVCur": "13"}]}, ("btc",)),
    (daily.parse_treasury, 'Date,"2 Yr"\n01/01/2025,12\n01/03/2025,13\n', ("2 Yr",)),
    (daily.parse_nyfed, {"refRates": [{"effectiveDate": "2025-01-01", "percentRate": "12"},
                                     {"effectiveDate": "2025-01-03", "percentRate": "13"}]}, ()),
    (daily.parse_defillama, [{"date": str(MS // 1000), "totalCirculatingUSD": {"peggedUSD": "12"}},
                            {"date": str(MS // 1000 + 86400 * 2), "totalCirculatingUSD": {"peggedUSD": "13"}}], ()),
])
def test_parsers_skip_today(parser, data, args):
    assert parser(data, *args, SINCE, TODAY) == ([("2025-01-01", "12")], 1)


@pytest.mark.parametrize("value", [None, ".", "N/A", ""])
def test_missing_is_not_zero(value):
    assert daily.parse_nyfed({"refRates": [{"effectiveDate": "2025-01-01", "percentRate": value}]}, SINCE, TODAY) == ([], 1)


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "invalid"])
def test_invalid_numbers(value):
    with pytest.raises(ValueError):
        daily.number(value)


def test_append_idempotent_conflict_and_late_value(tmp_path):
    db = daily.DailyStore(tmp_path)
    sid = "mvrv.coinmetrics.btc"
    assert db.append(sid, [("2025-01-02", "2")]) == (1, 0, [])
    original = db.path(sid).read_bytes()
    assert db.append(sid, [("2025-01-02", "2.0")]) == (0, 1, [])
    assert db.path(sid).read_bytes() == original
    added, present, conflicts = db.append(sid, [("2025-01-02", "3")])
    assert (added, present) == (0, 1)
    assert "conflict 2025-01-02" in conflicts[0]
    assert db.path(sid).read_bytes() == original
    db.append(sid, [("2025-01-01", "0")])
    assert db.path(sid).read_text() == "date,value\n2025-01-01,0\n2025-01-02,2\n"


@pytest.mark.parametrize("content", ["wrong,header\n", "date,value\n2025-02-30,1\n", "date,value\n2025-01-01,nan\n",
    "date,value\n2025-01-01,1\n2025-01-01,2\n", "date,value\n2025-01-02,1\n2025-01-01,2\n",
    "date,value\n2025-01-01,.\n", "date,value\n2025-01-01,1,2\n"])
def test_checker_invalid_csv(tmp_path, content):
    path = daily.DailyStore(tmp_path).path("test.series")
    path.parent.mkdir(parents=True)
    path.write_text(content)
    assert check.check_daily(tmp_path)


def test_checker_invalid_filename(tmp_path):
    directory = tmp_path / "data" / "daily"
    directory.mkdir(parents=True)
    (directory / "BAD.csv").write_text("date,value\n")
    assert "invalid series id" in check.check_daily(tmp_path)[0]


@pytest.mark.parametrize("citation,ok", [
    ("[D:test.series@2025-01-01]", True),
    ("[D:test.series@2025-01-01..2025-01-03]", True),
    ("[D:test.series@2025-01-01..2025-01-02]", False),
    ("[D:test.series@2025-01-03..2025-01-01]", False),
    ("[D:test.series@2025-02-30]", False), ("[D:../bad@2025-01-01]", False),
    ("[D:bad]", False), ("`[D:bad]`", True), ("```\n[D:bad]\n```", True),
])
def test_daily_citations(tmp_path, store, citation, ok):
    daily.DailyStore(store.root).append("test.series", [("2025-01-01", "1"), ("2025-01-03", "3")])
    path = tmp_path / "analysis.md"
    path.write_text("Not investment advice.\n\n" + "\n\n".join(check.HEADINGS) + "\n" + citation)
    assert (check.check_analysis(path, store) == []) is ok


def setup_cli(tmp_path, monkeypatch, get):
    monkeypatch.setattr(cli.store, "find_root", lambda: tmp_path)
    monkeypatch.setattr(cli.registry, "load", lambda root: None)
    monkeypatch.setattr(cli, "make_get_fn", lambda: get)
    monkeypatch.setattr(cli, "make_get_text_fn", lambda: lambda url, params: 'Date,"2 Yr","10 Yr"\n01/01/2025,4,5\n')


def fake_get(url, params):
    if "binance" in url:
        return [[MS, 0, 0, 0, "12"]]
    if "coinbase" in url:
        return [[MS // 1000, 0, 0, 0, "12"]]
    if "coinmetrics" in url:
        return {"data": [{"asset": params["assets"], "time": "2025-01-01T00:00:00Z", "CapMVRVCur": "2"}]}
    if "newyorkfed" in url:
        return {"refRates": [{"effectiveDate": "2025-01-01", "percentRate": "4"}]}
    return [{"date": str(MS // 1000), "totalCirculatingUSD": {"peggedUSD": "10"}}]


def test_backfill_cli(tmp_path, monkeypatch, capsys):
    setup_cli(tmp_path, monkeypatch, fake_get)
    assert cli.main(["backfill"]) == 0
    assert len(list((tmp_path / "data" / "daily").glob("*.csv"))) == 10
    assert cli.main(["backfill"]) == 0
    runs = [json.loads(line) for p in (tmp_path / "runs").glob("*.jsonl") for line in p.read_text().splitlines()]
    assert runs[0]["changed"] == 10
    assert runs[1]["changed"] == 0
    assert runs[1]["unchanged"] >= 10
    assert check.check_daily(tmp_path) == []
    assert "rows added /" in capsys.readouterr().out


@pytest.mark.parametrize("all_fail", [False, True])
def test_cli_isolates_failures(tmp_path, monkeypatch, all_fail):
    def get(url, params):
        if all_fail or "binance" in url:
            raise FetchError("HTTP 503")
        return fake_get(url, params)
    setup_cli(tmp_path, monkeypatch, get)
    assert cli.main(["backfill", "--series", "price_close.binance.btc", "--series", "mvrv.coinmetrics.btc"]) == int(all_fail)
    run = json.loads(next((tmp_path / "runs").glob("*.jsonl")).read_text())
    assert run["missing"] == (2 if all_fail else 1)
    assert run["errors"][0] == "price_close.binance.btc: HTTP 503"


def test_daily_uses_five_complete_days(tmp_path, monkeypatch):
    setup_cli(tmp_path, monkeypatch, fake_get)
    calls = []
    def fetch(sid, get, get_text, since, today):
        calls.append((since, today))
        return [], 0
    monkeypatch.setattr(daily, "fetch", fetch)
    assert cli.main(["collect", "daily"]) == 0
    assert len(calls) == 10
    assert all(today - since == timedelta(days=5) for since, today in calls)


def test_coinbase_paging_boundaries():
    calls = []
    def get(url, params):
        calls.append(params)
        start = datetime.fromisoformat(params["start"])
        end = datetime.fromisoformat(params["end"])
        return [[int(start.timestamp()), 0, 0, 0, "1"], [int(end.timestamp()), 0, 0, 0, "2"]]
    rows, skipped = daily.fetch("price_close.coinbase.btc", get, None, SINCE, SINCE + timedelta(days=600))
    assert len(calls) == 3
    assert len(rows) == 3
    assert len(set(day for day, _ in rows)) == 3
    assert skipped == 3


@pytest.mark.parametrize("value", [None, ".", "N/A"])
@pytest.mark.parametrize("source", ["binance", "coinbase", "coinmetrics", "treasury", "defillama"])
def test_parser_null_variants(source, value):
    if source == "binance":
        result = daily.parse_binance([[MS, 0, 0, 0, value]], SINCE, TODAY)
    elif source == "coinbase":
        result = daily.parse_coinbase([[MS // 1000, 0, 0, 0, value]], SINCE, TODAY)
    elif source == "coinmetrics":
        result = daily.parse_coinmetrics({"data": [{"asset": "btc", "time": "2025-01-01", "CapMVRVCur": value}]}, "btc", SINCE, TODAY)
    elif source == "treasury":
        result = daily.parse_treasury(f'Date,"2 Yr"\n01/01/2025,{value or ""}\n', "2 Yr", SINCE, TODAY)
    else:
        result = daily.parse_defillama([{"date": MS // 1000, "totalCirculatingUSD": {"peggedUSD": value}}], SINCE, TODAY)
    assert result == ([], 1)


def test_run_records_conflicts(tmp_path):
    db = daily.DailyStore(tmp_path)
    db.append("price_close.binance.btc", [("2025-01-01", "99")])
    run = db.collect(["price_close.binance.btc"], fake_get, None, SINCE, "2025-01-03T00:40:00Z", "daily")
    assert run["conflicts"] == 1
    assert run["changed"] == 0
    assert run["unchanged"] == 1
    assert "stored=99 received=12" in run["errors"][0]
    assert db.load("price_close.binance.btc")["2025-01-01"] == "99"


def test_coinmetrics_pagination():
    calls = []
    def get(url, params):
        calls.append((url, params))
        if len(calls) == 1:
            return {"data": [], "next_page_url": "https://community-api.coinmetrics.io/next"}
        return {"data": [{"asset": "btc", "time": "2025-01-01", "CapMVRVCur": "2"}]}
    assert daily.fetch("mvrv.coinmetrics.btc", get, None, SINCE, TODAY) == ([("2025-01-01", "2")], 0)
    assert calls[1][1] is None


def test_treasury_years_and_binance_pagination():
    calls = []
    def get_text(url, params):
        calls.append(params["field_tdr_date_value"])
        return 'Date,"2 Yr"\n01/02/2025,4\n'
    daily.fetch("us2y_yield.treasury", None, get_text, SINCE, date(2026, 11, 13))
    assert calls == [2025, 2026]
    calls.clear()
    def get(url, params):
        calls.append(params)
        return []
    daily.fetch("price_close.binance.btc", get, None, SINCE, SINCE + timedelta(days=1500))
    assert len(calls) == 2
    assert calls[1]["startTime"] == calls[0]["endTime"] + 1
