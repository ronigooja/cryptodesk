import json
import shutil
from pathlib import Path

import pytest

from cryptodesk import cli
from cryptodesk.adapters.base import FetchError

ROOT = Path(__file__).resolve().parents[1]
STAMP = 1793966400000


@pytest.fixture
def repo(tmp_path, monkeypatch):
    (tmp_path / "docs").mkdir()
    shutil.copy(ROOT / "docs" / "metrics.md", tmp_path / "docs" / "metrics.md")
    shutil.copy(ROOT / "AGENTS.md", tmp_path / "AGENTS.md")
    shutil.copytree(ROOT / "coins", tmp_path / "coins")
    monkeypatch.setenv("CRYPTODESK_ROOT", str(tmp_path))
    monkeypatch.setattr(cli, "make_get_fn", lambda: fake_get)
    return tmp_path


def fake_get(url, params):
    if "binance.com" in url:
        if url.endswith("/ticker/24hr"):
            return {"lastPrice": "100", "priceChangePercent": "1", "highPrice": "110", "lowPrice": "90", "closeTime": STAMP}
        if url.endswith("/premiumIndex"):
            return {"markPrice": "101", "lastFundingRate": "0.0001", "time": STAMP}
        if url.endswith("/openInterest"):
            return {"openInterest": "20", "time": STAMP}
        if url.endswith("Ratio"):
            return [{"longShortRatio": "1.2", "timestamp": STAMP}]
    if "okx.com" in url:
        return {"code": "0", "data": [{"last": "100", "high24h": "110", "low24h": "90", "fundingRate": "0.0001", "oiCcy": "20", "oiUsd": "2000", "ts": STAMP}]}
    if "deribit.com" in url:
        if url.endswith("/ticker"):
            return {"result": {"mark_price": 101, "funding_8h": 0.0001, "timestamp": STAMP}}
        if url.endswith("/get_volatility_index_data"):
            return {"result": {"data": [[STAMP, 50, 55, 45, 51]]}}
        if url.endswith("/get_book_summary_by_currency"):
            return {"result": [{"instrument_name": f"{params['currency']}-27NOV26-100-C", "open_interest": 2}]}
    pytest.fail(f"unexpected fake endpoint: {url}")


def test_market_collect_unchanged_check(repo, capsys):
    assert cli.main(["collect", "market"]) == 0
    assert capsys.readouterr().out.strip() == "collect market: facts=36 changed=36 unchanged=0 missing=0"
    histories = {p: p.read_text() for p in (repo / "data" / "facts").rglob("*.jsonl")}
    assert cli.main(["collect", "market"]) == 0
    assert capsys.readouterr().out.strip() == "collect market: facts=36 changed=0 unchanged=36 missing=0"
    assert all(p.read_text() == text for p, text in histories.items())
    assert cli.main(["check"]) == 0


def test_options_collect(repo):
    assert cli.main(["collect", "options"]) == 0
    assert cli.main(["check"]) == 0
    latest = json.loads((repo / "data" / "latest" / "btc.json").read_text())
    assert "deribit.btc.opt.2026-11-27.max_pain" in latest


TREASURY = "Date,\"2 Yr\",\"10 Yr\"\n11/04/2026,4.58,4.90\n11/03/2026,4.61,4.95\n"
NYFED = {"refRates": [{"effectiveDate": "2026-11-04", "type": "EFFR", "percentRate": 3.88}]}


def test_macro_collect(repo, monkeypatch, capsys):
    monkeypatch.setattr(cli, "make_get_text_fn", lambda: lambda url, params: TREASURY)
    monkeypatch.setattr(cli, "make_get_fn", lambda: lambda url, params: NYFED)
    assert cli.main(["collect", "macro"]) == 0
    assert capsys.readouterr().out.strip() == "collect macro: facts=3 changed=3 unchanged=0 missing=0"
    assert cli.main(["check"]) == 0


def test_macro_failure_is_missing_not_crash(repo, monkeypatch, capsys):
    def get(url, params):
        raise FetchError("HTTP 503")

    monkeypatch.setattr(cli, "make_get_text_fn", lambda: get)
    monkeypatch.setattr(cli, "make_get_fn", lambda: get)
    assert cli.main(["collect", "macro"]) == 0
    assert "missing=3" in capsys.readouterr().out
    assert cli.main(["check"]) == 0


def test_zero_facts_fails(repo, monkeypatch, capsys):
    monkeypatch.setattr(cli.profiles, "list_coins", lambda root: [])
    assert cli.main(["collect", "market"]) == 1
    assert "facts=0" in capsys.readouterr().out


def test_check_errors_fail(repo, monkeypatch, capsys):
    monkeypatch.setattr(cli.check, "check_all", lambda *args: ["invalid fact"])
    assert cli.main(["check"]) == 1
    assert capsys.readouterr().out.strip() == "check: errors=1"


COINMETRICS = {"data": [{"asset": "btc", "time": "2026-11-09T00:00:00.000000000Z",
                         "CapMVRVCur": "1.39", "AdrActCnt": "676220", "FeeTotNtv": "2.68"},
                        {"asset": "eth", "time": "2026-11-09T00:00:00.000000000Z",
                         "CapMVRVCur": "0.97", "AdrActCnt": "807775", "FeeTotNtv": "156.85"}]}
LLAMA = {"peggedAssets": [{"symbol": "USDT", "pegType": "peggedUSD", "circulating": {"peggedUSD": 100.0}},
                          {"symbol": "USDC", "pegType": "peggedUSD", "circulating": {"peggedUSD": 50.0}}]}
CFTC_ROW = {"report_date_as_yyyy_mm_dd": "2026-11-03T00:00:00.000", "open_interest_all": "100",
            "asset_mgr_positions_long": "10", "asset_mgr_positions_short": "4",
            "lev_money_positions_long": "3", "lev_money_positions_short": "9"}
BITBO = ("<h1>Bitcoin ETF Flow (US$m)</h1><table><tr><th>Date</th><th>IBIT</th><th>Total</th></tr>"
         "<tr><td>Nov 09, 2026</td><td>-210.5</td><td>-198.6</td></tr></table>")


def fake_get_more(url, params):
    if "coinmetrics" in url:
        return {"data": [r for r in COINMETRICS["data"] if r["asset"] == params["assets"]]}
    if "stablecoins.llama.fi" in url:
        return LLAMA
    if "cftc.gov" in url:
        return [CFTC_ROW]
    pytest.fail(f"unexpected fake endpoint: {url}")


def test_onchain_collect_and_check(repo, monkeypatch, capsys):
    monkeypatch.setattr(cli, "make_get_fn", lambda: fake_get_more)
    assert cli.main(["collect", "onchain"]) == 0
    assert capsys.readouterr().out.strip() == "collect onchain: facts=5 changed=5 unchanged=0 missing=0"
    assert cli.main(["check"]) == 0
    latest = json.loads((repo / "data" / "latest" / "macro.json").read_text())
    assert latest["defillama.macro.stablecoin_supply_usd"]["value"] == 150.0


def test_flows_collect_and_check(repo, monkeypatch, capsys):
    monkeypatch.setattr(cli, "make_get_fn", lambda: fake_get_more)
    monkeypatch.setattr(cli, "make_get_text_fn", lambda: lambda url, params: BITBO)
    assert cli.main(["collect", "flows"]) == 0
    assert "missing=" in capsys.readouterr().out
    assert cli.main(["check"]) == 0
    btc = json.loads((repo / "data" / "latest" / "btc.json").read_text())
    assert btc["bitbo.btc.etf_flow_total"]["value"] == -198.6 * 1_000_000
    assert btc["cftc.btc.cot_lev_money_net"]["value"] == -6
    assert json.loads((repo / "data" / "latest" / "eth.json").read_text())["cftc.eth.cot_asset_mgr_net"]["value"] == 6
