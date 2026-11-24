import json
from datetime import UTC, date, datetime, timedelta

import pytest

from cryptodesk import check, cli, daily, forecast

SID = "price_close.binance.btc"


@pytest.fixture
def root(tmp_path, monkeypatch):
    (tmp_path / "analysis").mkdir()
    (tmp_path / "analysis" / "view.md").touch()
    monkeypatch.setattr(cli.store, "find_root", lambda: tmp_path)
    return tmp_path


def record(**changes):
    rec = dict(made_at="2025-01-01T00:00:00Z", analysis="view.md", series=SID,
               op="gt", threshold="10", date="2025-01-02", p=0.6)
    rec.update(changes)
    rec["id"] = forecast.forecast_id(rec)
    return rec


def write(root, records, month="2025-01"):
    path = root / "data" / "forecasts" / (month + ".jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    return path


def test_add_score_and_no_write(root, capsys):
    tomorrow = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()
    args = ["forecast", "add", "--analysis", "view.md", "--series", SID, "--op", "gt",
            "--threshold", "10", "--date", tomorrow, "--p", "0.6"]
    assert cli.main(args) == 0
    assert capsys.readouterr().out.startswith("fc:")
    path = next((root / "data" / "forecasts").glob("*.jsonl"))
    before = path.read_bytes()
    assert check.check_forecasts(root) == []
    assert cli.main(["forecast", "score"]) == 0
    assert "open" in capsys.readouterr().out
    assert path.read_bytes() == before


@pytest.mark.parametrize("option,value", [("--series", "bad"), ("--date", "2000-01-01"),
                                          ("--p", "0"), ("--p", "1"), ("--analysis", "missing.md")])
def test_cli_invalid(root, option, value):
    args = ["forecast", "add", "--analysis", "view.md", "--series", SID, "--op", "gt",
            "--threshold", "10", "--date", (datetime.now(UTC).date() + timedelta(days=1)).isoformat(), "--p", "0.6"]
    args[args.index(option) + 1] = value
    with pytest.raises(SystemExit):
        cli.main(args)
    assert not (root / "data" / "forecasts").exists()


def test_score_status_and_equality(root):
    records = [record(), record(op="lt"), record(date="2025-01-03"), record(date="2025-01-04")]
    write(root, records)
    daily.DailyStore(root).append(SID, [("2025-01-02", "10")])
    result = forecast.ForecastStore(root).score(date(2025, 1, 4))
    assert result.count("resolved no | 0.36000000") == 2
    assert "unresolved" in result and "| open |" in result
    assert "Resolved: 2 | mean Brier: 0.36000000 | baseline: 0.25" in result
    assert "Too few resolved" in result


def test_twenty_resolved(root):
    records = [record(threshold=str(i)) for i in range(20)]
    write(root, records)
    daily.DailyStore(root).append(SID, [("2025-01-02", "10")])
    result = forecast.ForecastStore(root).score(date(2025, 1, 3))
    assert "Resolved: 20" in result and "Too few" not in result
    assert "view.md: mean Brier" in result


@pytest.mark.parametrize("changes", [
    {"made_at": "bad"}, {"analysis": "missing"}, {"analysis": "../view.md"},
    {"series": "bad"}, {"op": "ge"}, {"threshold": "NaN"}, {"threshold": 2},
    {"date": "2025-02-30"}, {"date": "2025-01-01"}, {"p": 0}, {"p": 1},
    {"p": True}, {"p": 0.12345}, {"p": "0.5"},
])
def test_checker_invalid_fields(root, changes):
    write(root, [record(**changes)])
    assert check.check_forecasts(root)


def test_checker_keys_json_id_duplicate_month(root):
    rec = record()
    path = write(root, [rec, rec, rec | {"id": "fc:wrong"}, rec | {"extra": 1}], "2025-02")
    with path.open("a") as fh:
        fh.write("not json\n")
    errors = check.check_forecasts(root)
    for message in ("duplicate", "id mismatch", "exactly", "invalid forecast JSON", "file month"):
        assert any(message in e and e.startswith("data/forecasts/2025-02.jsonl:") for e in errors)


def test_duplicate_rejected(root, monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2025, 1, 1, tzinfo=UTC)
    monkeypatch.setattr(forecast, "datetime", Clock)
    db = forecast.ForecastStore(root)
    db.add("view.md", SID, "gt", "10", "2025-01-02", 0.5)
    with pytest.raises(ValueError, match="duplicate"):
        db.add("view.md", SID, "gt", "10", "2025-01-02", 0.5)
