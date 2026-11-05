from dataclasses import replace

import pytest

from cryptodesk.model import FIELDS, missing, validate


def test_validate_accepts_ok_fact(fact, registry):
    assert validate(fact.to_dict(), registry) == []


def test_validate_accepts_true_zero_and_unknown_source_time(fact, registry):
    assert validate(replace(fact, value=0, as_of=None).to_dict(), registry) == []


def test_validate_accepts_missing_fact(registry):
    fact = missing(
        "binance.btc.spot_price", "btc", "spot_price", "USD",
        "Timeout", "2026-11-06T10:01:00Z", "binance",
    )
    assert validate(fact.to_dict(), registry) == []


@pytest.mark.parametrize("field", FIELDS)
def test_validate_rejects_absent_required_field(field, fact, registry):
    record = fact.to_dict()
    del record[field]
    fid = record.get("id", "<no id>")
    assert validate(record, registry) == [f"{fid}: field {field} absent"]


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"value": None}, "ok with null value"),
        ({"reason": "Timeout"}, "ok with reason"),
        ({"status": "missing", "value": None}, "missing without reason"),
        ({"status": "missing", "reason": "Timeout"}, "missing with value"),
        ({"status": "n/a"}, "status 'n/a' invalid"),
        ({"fetched_at": "2026-11-06T10:01:00+00:00"}, "fetched_at not UTC ISO"),
        ({"fetched_at": None}, "fetched_at not UTC ISO"),
        ({"as_of": "2026-11-06"}, "as_of not UTC ISO"),
        ({"unit": ""}, "unit empty"),
        ({"metric": "not_registered"}, "metric 'not_registered' not registered"),
        ({"id": "other.btc.spot_price"}, "id does not match source, coin, metric"),
        ({"id": "binance.eth.spot_price"}, "id does not match source, coin, metric"),
        ({"id": "binance.btc.open_interest"}, "id does not match source, coin, metric"),
    ],
)
def test_validate_rejects_invalid_record(changes, message, fact, registry):
    errors = validate(fact.to_dict() | changes, registry)
    assert f"{changes.get('id', fact.id)}: {message}" in errors


@pytest.mark.parametrize("field", ["as_of", "fetched_at"])
def test_bug_validate_rejects_impossible_calendar_time(field, fact, registry):
    record = fact.to_dict() | {field: "2026-99-99T99:99:99Z"}
    assert validate(record, registry)
