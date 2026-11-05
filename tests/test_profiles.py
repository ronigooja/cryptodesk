from pathlib import Path

import pytest

from cryptodesk import profiles

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("coin", ["btc", "eth"])
def test_real_profiles(coin):
    symbol = coin.upper()
    assert profiles.load(ROOT, coin) == {
        "class": "major",
        "modules": ["core", "perp", "options"],
        "binance": {"spot": symbol + "USDT", "perp": symbol + "USDT"},
        "okx": {"spot": symbol + "-USDT", "swap": symbol + "-USDT-SWAP"},
        "deribit": {"currency": symbol, "perp": symbol + "-PERPETUAL"},
    }


def test_list_coins():
    assert profiles.list_coins(ROOT) == ["btc", "eth"]


@pytest.mark.parametrize("coin_class", ["alt", "invalid", None])
def test_class_validation(tmp_path, coin_class):
    path = tmp_path / "coins" / "test" / "profile.toml"
    path.parent.mkdir(parents=True)
    path.write_text(f'class = "{coin_class}"\n' if coin_class else "")
    if coin_class == "alt":
        with pytest.raises(NotImplementedError, match="^alt is built in phase 4$"):
            profiles.load(tmp_path, "test")
    else:
        with pytest.raises(ValueError, match="class must be major or alt"):
            profiles.load(tmp_path, "test")
