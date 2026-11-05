import pytest

from cryptodesk.registry import parse


@pytest.mark.parametrize(
    "metric", ["spot_price", "funding_rate_8h", "oi_call", "depth_1pct_bid", "etf_flow_ibit"]
)
def test_parse_real_registry_recognizes_metrics(registry, metric):
    assert registry.known(metric)


@pytest.mark.parametrize("metric", ["unknown", "spot_price_extra", "etf_flow_", "prefix_spot_price"])
def test_registry_rejects_unknown_or_partial_metrics(registry, metric):
    assert not registry.known(metric)
    assert registry.stale_hours(metric) is None
    assert not registry.is_snapshot(metric)


def test_registry_snapshot_and_staleness(registry):
    assert registry.is_snapshot("depth_1pct_bid")
    assert registry.is_snapshot("pool_liquidity_usd")
    assert not registry.is_snapshot("spot_price")
    assert registry.stale_hours("depth_1pct_bid") == 1
    assert registry.stale_hours("spot_price") == 3
    assert registry.stale_hours("etf_flow_ibit") == 36


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
