import json

import pytest

from cryptodesk.adapters import fred
from cryptodesk.adapters.base import FetchError

STARTED = "2026-11-06T12:00:00Z"
KEY = "fake-secret-never-persist"


def test_observations_skip_dot():
    calls = []

    def get(url, params):
        calls.append((url, params))
        return {"observations": [
            {"date": "2026-11-06", "value": "."},
            {"date": "2026-11-05", "value": "4.25"},
            {"date": "2026-11-04", "value": "4.5"},
        ]}

    facts = fred.collect(KEY, get, STARTED)
    assert len(facts) == 3
    for fact, (url, params), (series, metric) in zip(facts, calls, fred.SERIES.items()):
        assert url == fred.BASE
        assert params == {"series_id": series, "api_key": KEY, "file_type": "json", "sort_order": "desc", "limit": 5}
        assert fact.id == f"fred.macro.{metric}"
        assert fact.value == 4.25
        assert fact.status == "ok"
        assert fact.as_of == "2026-11-05T00:00:00Z"
        assert fact.unit == "percent"
        assert fact.fetched_at == STARTED
    assert KEY not in json.dumps([f.to_dict() for f in facts])


@pytest.mark.parametrize("key", [None, ""])
def test_missing_key_never_fetches(key):
    def get(*args):
        pytest.fail("missing key must not fetch")

    facts = fred.collect(key, get, STARTED)
    assert len(facts) == 3
    assert all(f.status == "missing" and f.value is None and f.as_of is None for f in facts)
    assert {f.reason for f in facts} == {"FRED_API_KEY not set"}


@pytest.mark.parametrize("observations", [[], [{"date": "2026-11-06", "value": "."}]])
def test_unpublished_is_not_zero(observations):
    facts = fred.collect(KEY, lambda *args: {"observations": observations}, STARTED)
    assert all(f.status == "missing" and f.value is None and f.reason == "not published" for f in facts)


@pytest.mark.parametrize("payload", [{}, {"observations": None}, {"observations": [{"value": "oops"}]},
                                     {"observations": [{"value": "NaN", "date": "2026-11-06"}]},
                                     {"observations": [{"value": "1", "date": KEY}]}])
def test_malformed_payload_is_missing_without_secrets(payload):
    facts = fred.collect(KEY, lambda *args: payload, STARTED)
    assert all(f.reason == "field absent in response" for f in facts)
    assert KEY not in repr(facts)


@pytest.mark.parametrize("reason", ["HTTP 403", "Timeout", f"request error {KEY}"])
def test_fetch_error_is_sanitized(reason):
    def get(*args):
        raise FetchError(reason)

    facts = fred.collect(KEY, get, STARTED)
    assert all(f.status == "missing" for f in facts)
    assert KEY not in repr(facts)


def test_true_zero_is_ok():
    facts = fred.collect(KEY, lambda *args: {"observations": [{"date": "2026-11-06", "value": "0"}]}, STARTED)
    assert all(f.status == "ok" and f.value == 0 for f in facts)
