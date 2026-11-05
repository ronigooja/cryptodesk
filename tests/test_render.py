from dataclasses import replace
from datetime import UTC, datetime

import pytest

from cryptodesk.model import missing
from cryptodesk.render import render_all, render_coin


@pytest.mark.parametrize(("hour", "second", "stale"), [(13, 0, False), (13, 1, True)])
def test_render_marks_rows_after_staleness_limit(store, fact, hour, second, stale):
    fact = replace(fact, fetched_at="2026-11-06T10:00:00Z")
    store.apply([fact], "core", fact.fetched_at)
    rendered = render_coin(store, "btc", datetime(2026, 11, 6, hour, 0, second, tzinfo=UTC))
    assert ("stale" in rendered) is stale
    assert f"`{fact.id}` | ok | 70000 | USD" in rendered


def test_render_uses_checked_at_for_unchanged_fact(store, fact):
    store.apply([fact], "core", fact.fetched_at)
    later = replace(fact, fetched_at="2026-11-06T14:00:00Z")
    store.apply([later], "core", later.fetched_at)
    rendered = render_coin(store, "btc", datetime(2026, 11, 6, 15, tzinfo=UTC))
    assert "stale" not in rendered
    assert fact.fetched_at in rendered


def test_render_missing_reason_and_blank_value(store, fact):
    absent = missing(fact.id, "btc", "spot_price", "USD", "Timeout", fact.fetched_at, "binance")
    store.apply([absent], "core", absent.fetched_at)
    rendered = render_coin(store, "btc", datetime(2026, 11, 6, 14, tzinfo=UTC))
    assert "| missing |  | USD |  |" in rendered
    assert "| Timeout stale |" in rendered
    assert "None" not in rendered


def test_render_all_writes_only_temporary_notes(store, fact):
    store.apply([fact], "core", fact.fetched_at)
    now = datetime(2026, 11, 6, 11, tzinfo=UTC)
    paths = render_all(store, now)
    assert paths == [store.root / "coins" / "btc" / "notes.md"]
    assert paths[0].read_text() == render_coin(store, "btc", now)
