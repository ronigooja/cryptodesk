from pathlib import Path

import pytest

from cryptodesk import model, registry
from cryptodesk.adapters import mempool
from cryptodesk.adapters.base import FetchError

FETCHED = "2026-11-11T12:00:00Z"


@pytest.mark.parametrize("failure", [None, "hashrate", "fees"])
@pytest.mark.parametrize("bad", ["http", {}, {"currentHashrate": "N/A", "currentDifficulty": "NaN", "fastestFee": "Infinity"}])
def test_values_validation_and_endpoint_isolation(failure, bad):
    calls = []

    def get(url, params):
        assert params == {}
        endpoint = "hashrate" if url.endswith("/mining/hashrate/3d") else "fees"
        assert url in (f"{mempool.BASE}/mining/hashrate/3d", f"{mempool.BASE}/fees/recommended")
        calls.append(endpoint)
        if endpoint == failure:
            if bad == "http":
                raise FetchError("Timeout")
            return bad
        return {"currentHashrate": "9.6e20", "currentDifficulty": "1.48e14", "fastestFee": "3"}

    facts = mempool.collect("btc", get, FETCHED)
    assert calls == ["hashrate", "fees"]
    metrics = registry.parse(Path("docs/metrics.md").read_text())
    for fact in facts:
        assert model.validate(fact.to_dict(), metrics) == []
        assert fact.id == f"mempool.btc.{fact.metric}"
        assert fact.as_of is None
        assert fact.unit == {"hashrate": "H/s", "difficulty": "number", "fee_fastest": "sat/vB"}[fact.metric]
        failed = failure == ("fees" if fact.metric == "fee_fastest" else "hashrate")
        if failed:
            assert fact.status == "missing" and fact.value is None
            assert fact.reason == ("Timeout" if bad == "http" else "field absent in response")
        else:
            assert fact.status == "ok"
            assert fact.value == {"hashrate": 9.6e20, "difficulty": 1.48e14, "fee_fastest": 3}[fact.metric]


def test_one_bad_field_preserves_other_metric():
    facts = mempool.collect("btc", lambda *_: {"currentHashrate": None, "currentDifficulty": 123, "fastestFee": 0}, FETCHED)
    metrics = registry.parse(Path("docs/metrics.md").read_text())
    for fact in facts:
        assert model.validate(fact.to_dict(), metrics) == []
    assert [f.status for f in facts] == ["missing", "ok", "ok"]
    assert facts[-1].value == 0


def test_unsupported_coin():
    assert mempool.collect("eth", None, FETCHED) == []
