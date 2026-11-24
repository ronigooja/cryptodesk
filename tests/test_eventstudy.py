from datetime import UTC, datetime, timedelta

import pytest

from cryptodesk import cli, eventstudy
from cryptodesk.adapters.base import FetchError

T = datetime(2020, 1, 10, 12, tzinfo=UTC)


def row(ms, volume=100):
    return [ms, '100', '101', '99', '100', '1', ms + 59999, str(volume), 1, '1', '1', '0']


def get(url, params):
    return [row(t, 100 + (t // 60000) % 7) for t in range(params['startTime'], params['endTime'] + 1, 60000)]


def test_alignment_and_paging():
    calls = []
    def fetch(url, params):
        calls.append(params)
        return get(url, params)
    rows = eventstudy.fetch_window(fetch, 'url', 'BTCUSDT', T, T + timedelta(minutes=1001))
    assert len(rows) == 1001 and len(calls) == 2
    assert all(c['limit'] == 1000 for c in calls)
    with pytest.raises(ValueError, match='invalid kline'):
        eventstudy.fetch_window(lambda u, p: [row(p['startTime'] + 1)], 'url', 'BTCUSDT', T, T + timedelta(minutes=1))


def test_baseline_and_flag():
    days = {}
    for n in range(1, 8):
        center = T - timedelta(days=n)
        days[center.date()] = {center + timedelta(minutes=i): (100, 100 + i % 7) for i in range(-100, 31)}
    mid, mad = eventstudy.baseline(days, T, 'turnover')
    assert mid == 103 and mad == 2
    data = {T + timedelta(minutes=i): (100, 100) for i in range(-61, 0)}
    data[T - timedelta(minutes=5)] = (100, 10000)
    assert eventstudy.count_flags(data, days, T) == 1


def test_missing_bad_row_gap_and_no_files(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv('CRYPTODESK_ROOT', str(tmp_path))
    def fake(url, params):
        if params['symbol'] == 'ETHUSDT':
            raise FetchError('HTTP 451')
        if 'fapi' in url:
            return [['bad']]
        rows = get(url, params)
        return [r for r in rows if r[0] != int(T.timestamp() * 1000)]
    monkeypatch.setattr(cli, 'make_get_fn', lambda: fake)
    assert cli.main(['event-study', '--at', '2020-01-10T12:00:00Z', '--before', '1', '--after', '2', '--baseline-days', '1']) == 0
    output = capsys.readouterr().out
    assert 'missing: ETHUSDT spot HTTP 451' in output
    assert 'missing: BTCUSDT perpetual invalid kline row' in output
    assert '2020-01-10T12:00Z | - | - | - | -' in output
    assert list(tmp_path.iterdir()) == []


def test_future_and_non_utc_rejected(capsys):
    for value in ('2999-01-01T00:00:00Z', '2020-01-01T00:00:00+00:00'):
        with pytest.raises(SystemExit) as error:
            cli.main(['event-study', '--at', value])
        assert error.value.code == 2
