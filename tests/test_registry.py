import pytest

from cryptodesk.registry import parse


@pytest.mark.parametrize(
    "metric", ["spot_price", "funding_rate_8h", "oi_call_total", "max_pain", "etf_flow_ibit"]
)
def test_parse_real_registry_recognizes_metrics(registry, metric):
    assert registry.known(metric)


@pytest.mark.parametrize("metric", ["unknown", "spot_price_extra", "etf_flow_", "prefix_spot_price"])
def test_registry_rejects_unknown_or_partial_metrics(registry, metric):
    assert not registry.known(metric)
    assert registry.stale_hours(metric) is None
    assert not registry.is_snapshot(metric)


SNAPSHOT_TABLE = """## Registry

| Metric | Unit | Meaning | Stale after | Type |
|---|---|---|---|---|
| `depth_<pct>_<side>` | USD | point-in-time sample | 1 h | snapshot |
| `spot_price` | USD | last price | 3 h | series |
"""


def test_registry_snapshot_and_staleness(registry):
    assert not registry.is_snapshot("spot_price")
    assert registry.stale_hours("spot_price") == 3
    assert registry.stale_hours("etf_flow_ibit") == 36
    assert not registry.known("depth_1pct_bid")


def test_snapshot_type_is_parsed_from_a_registry_table():
    snap = parse(SNAPSHOT_TABLE)
    assert snap.is_snapshot("depth_1pct_bid")
    assert not snap.is_snapshot("spot_price")
    assert snap.stale_hours("depth_1pct_bid") == 1


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("## Registry\n", "no metrics parsed"),
        ("## Registry\n| `spot_price` | USD | Price | daily | series |\n", "bad staleness"),
    ],
)
def test_parse_rejects_invalid_registry(text, message):
    with pytest.raises(ValueError, match=message):
        parse(text)
