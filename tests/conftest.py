from pathlib import Path

import pytest

from cryptodesk.model import ok
from cryptodesk.registry import parse
from cryptodesk.store import Store


@pytest.fixture(scope="session")
def registry():
    root = Path(__file__).resolve().parents[1]
    return parse((root / "docs" / "metrics.md").read_text())


@pytest.fixture
def fact():
    return ok(
        "binance.btc.spot_price", "btc", "spot_price", 70000, "USD",
        "2026-11-06T10:00:00Z", "2026-11-06T10:01:00Z", "binance",
    )


@pytest.fixture
def store(tmp_path, registry):
    return Store(tmp_path, registry)
