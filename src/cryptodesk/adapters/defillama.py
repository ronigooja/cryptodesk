import math

from .base import Endpoint, Spec, run_endpoint

URL = "https://stablecoins.llama.fi/stablecoins"


def _supply(asset):
    value = float(asset["circulating"]["peggedUSD"])
    if not math.isfinite(value):
        raise ValueError("non-finite")
    return value


def _symbol(data, symbol):
    matches = [asset for asset in data["peggedAssets"] if asset.get("symbol") == symbol]
    # When symbols collide, keep the largest circulating supply, never sum them.
    if len(matches) == 1:
        return _supply(matches[0]), None
    return max(_supply(asset) for asset in matches), None


def _total(data):
    assets = [asset for asset in data["peggedAssets"] if asset["pegType"] == "peggedUSD"]
    if not assets:
        raise ValueError("no USD-pegged assets")
    value = math.fsum(_supply(asset) for asset in assets)
    if not math.isfinite(value):
        raise ValueError("non-finite")
    return value, None


def collect(coin: str | None, get, fetched_at: str) -> list:
    if coin not in (None, "macro"):
        return []
    ep = Endpoint(URL, {"includePrices": "false"}, [
        Spec("stablecoin_supply_usd", "USD", _total),
        Spec("usdt_supply_usd", "USD", lambda data: _symbol(data, "USDT")),
        Spec("usdc_supply_usd", "USD", lambda data: _symbol(data, "USDC")),
    ])
    return run_endpoint(get, ep, "defillama", "macro", fetched_at)
