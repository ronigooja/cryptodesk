import json
import shutil
from pathlib import Path

import pytest

from cryptodesk import cli

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


def test_market_collect_unchanged_render_check(repo, capsys):
    assert cli.main(["collect", "market"]) == 0
    assert capsys.readouterr().out.strip() == "collect market: facts=36 changed=36 unchanged=0 missing=0"
    histories = {p: p.read_text() for p in (repo / "data" / "facts").rglob("*.jsonl")}
    assert cli.main(["collect", "market"]) == 0
    assert capsys.readouterr().out.strip() == "collect market: facts=36 changed=0 unchanged=36 missing=0"
    assert all(p.read_text() == text for p, text in histories.items())
    assert cli.main(["render"]) == 0
    assert (repo / "coins" / "btc" / "notes.md").is_file()
    assert "binance.btc.spot_price" in (repo / "coins" / "btc" / "notes.md").read_text()
    assert cli.main(["check"]) == 0


def test_options_collect(repo):
    assert cli.main(["collect", "options"]) == 0
    assert cli.main(["check"]) == 0
    latest = json.loads((repo / "data" / "latest" / "btc.json").read_text())
    assert "deribit.btc.opt.2026-11-27.max_pain" in latest


def test_macro_missing_key(repo, monkeypatch, capsys):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
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


def test_macro_secret_not_in_output_or_data(repo, monkeypatch, capsys):
    secret = "fake-secret-do-not-store"
    monkeypatch.setenv("FRED_API_KEY", secret)
    monkeypatch.setattr(cli, "make_get_fn", lambda: lambda *args: {"observations": [{"date": "2026-11-06", "value": "4"}]})
    assert cli.main(["collect", "macro"]) == 0
    assert secret not in capsys.readouterr().out
    for directory in (repo / "data", repo / "runs"):
        assert all(secret not in p.read_text() for p in directory.rglob("*") if p.is_file())
