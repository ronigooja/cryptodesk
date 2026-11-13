import json
from dataclasses import replace

import pytest

from cryptodesk.model import missing


def read_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_first_apply_creates_latest_history_and_run(store, fact):
    run = store.apply([fact], "core", fact.fetched_at)
    assert run == {
        "started": fact.fetched_at, "group": "core", "facts": 1,
        "changed": 1, "unchanged": 0, "missing": 0, "errors": [],
    }
    assert store.load_latest("btc") == {
        fact.id: fact.to_dict() | {"checked_at": fact.fetched_at}
    }
    assert read_lines(store.history_path("2026-11", "btc")) == [fact.to_dict()]
    assert read_lines(store.root / "runs" / "2026-11.jsonl") == [run]
    assert store.coins() == ["btc"]


def test_identical_second_apply_updates_checked_at_without_history(store, fact):
    store.apply([fact], "core", fact.fetched_at)
    later = replace(fact, fetched_at="2026-11-06T11:01:00Z")
    run = store.apply([later], "core", later.fetched_at)
    assert (run["changed"], run["unchanged"]) == (0, 1)
    assert list(store.iter_history("btc")) == [fact.to_dict()]
    assert store.load_latest("btc")[fact.id] == (
        fact.to_dict() | {"checked_at": later.fetched_at}
    )
    runs = read_lines(store.root / "runs" / "2026-11.jsonl")
    assert len(runs) == 2
    assert runs[-1] == run


@pytest.mark.parametrize(
    "changes",
    [
        {"value": 71000},
        {"as_of": "2026-11-06T11:00:00Z"},
        {"status": "missing", "value": None, "reason": "Timeout"},
    ],
)
def test_changed_fact_appends_exactly_one_history_line(store, fact, changes):
    store.apply([fact], "core", fact.fetched_at)
    changed = replace(fact, fetched_at="2026-11-06T11:01:00Z", **changes)
    run = store.apply([changed], "core", changed.fetched_at)
    assert (run["changed"], run["unchanged"]) == (1, 0)
    history = list(store.iter_history("btc"))
    assert history == [fact.to_dict(), changed.to_dict()]
    assert all("checked_at" not in row for row in history)
    assert store.load_latest("btc")[fact.id]["value"] == changed.value


def test_identical_snapshot_always_appends(tmp_path, fact):
    from cryptodesk.registry import parse
    from cryptodesk.store import Store

    registry = parse("## Registry\n\n| Metric | Unit | Meaning | Stale after | Type |\n|---|---|---|---|---|\n"
                     "| `depth_<pct>_<side>` | USD | sample | 1 h | snapshot |\n")
    store = Store(tmp_path, registry)
    snapshot = replace(fact, id="binance.btc.spot.depth_1pct_bid", metric="depth_1pct_bid")
    store.apply([snapshot], "depth", snapshot.fetched_at)
    run = store.apply([snapshot], "depth", snapshot.fetched_at)
    assert (run["changed"], run["unchanged"]) == (1, 0)
    assert list(store.iter_history("btc")) == [snapshot.to_dict()] * 2


def test_missing_facts_count_and_deduplicate_errors(store, fact):
    absent = missing(fact.id, "btc", "spot_price", "USD", "Timeout", fact.fetched_at, "binance")
    other = replace(absent, id="binance.btc.perp_mark_price", metric="perp_mark_price")
    third = replace(absent, id="other.btc.spot_price", source="other", reason="HTTP 403")
    run = store.apply([absent, other, third], "core", fact.fetched_at)
    assert run["facts"] == 3
    assert run["missing"] == 3
    assert run["errors"] == ["binance: Timeout", "other: HTTP 403"]
    changed_reason = replace(absent, reason="HTTP 500")
    run = store.apply([changed_reason], "core", fact.fetched_at)
    assert run["changed"] == 1
    assert len(list(store.iter_history("btc"))) == 4


def test_empty_store_and_empty_run(store, fact):
    assert store.coins() == []
    assert store.load_latest("btc") == {}
    assert list(store.iter_history("btc")) == []
    run = store.apply([], "core", fact.fetched_at)
    assert all(run[key] == 0 for key in ("facts", "changed", "unchanged", "missing"))
    assert read_lines(store.root / "runs" / "2026-11.jsonl") == [run]


@pytest.mark.parametrize("group", ["market", "options", "onchain", "flows", "macro"])
def test_every_apply_prunes_expired_options_across_coins_without_touching_history(store, fact, group):
    expired = replace(fact, id="deribit.btc.opt.2026-11-05.max_pain", source="deribit", metric="max_pain")
    today = replace(expired, id="deribit.btc.opt.2026-11-06.max_pain")
    future = replace(expired, id="deribit.btc.opt.2026-11-27.max_pain")
    unknown = replace(expired, id="deribit.btc.opt.unknown.max_pain")
    total = replace(expired, id="deribit.btc.oi_call_total", metric="oi_call_total")
    store.apply([expired, today, future, unknown, total, fact], "options", "2026-11-05T23:59:59Z")
    history = store.history_path("2026-11", "btc").read_bytes()
    store.apply([], group, "2026-11-06T00:00:00Z")
    assert set(store.load_latest("btc")) == {today.id, future.id, unknown.id, total.id, fact.id}
    assert store.history_path("2026-11", "btc").read_bytes() == history


def test_expired_incoming_option_stays_in_history_not_latest(store, fact):
    expired = replace(fact, id="deribit.btc.opt.2026-11-05.max_pain", source="deribit", metric="max_pain")
    store.apply([expired], "options", fact.fetched_at)
    assert store.load_latest("btc") == {}
    assert list(store.iter_history("btc")) == [expired.to_dict()]
