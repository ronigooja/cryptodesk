from ..model import ms_to_iso
from .base import Endpoint, Spec, run_endpoint

BASE = "https://www.okx.com/api/v5"


def _row(d):
    if not isinstance(d, dict) or d.get("code") != "0":
        raise KeyError("code")
    return d["data"][0]


def collect(coin: str, profile: dict, get, fetched_at: str) -> list:
    cfg = profile["okx"]
    spot, swap = cfg["spot"], cfg["swap"]

    def num(key, ts="ts"):
        return lambda d: (float(_row(d)[key]), ms_to_iso(_row(d)[ts]))

    endpoints = [
        Endpoint(f"{BASE}/market/ticker", {"instId": spot}, [
            Spec("spot_price", "USDT", num("last")),
            Spec("high_24h", "USDT", num("high24h")),
            Spec("low_24h", "USDT", num("low24h")),
        ]),
        Endpoint(f"{BASE}/public/funding-rate", {"instId": swap}, [
            Spec("funding_rate_8h", "fraction", num("fundingRate", "ts")),
        ]),
        Endpoint(f"{BASE}/public/open-interest", {"instType": "SWAP", "instId": swap}, [
            Spec("open_interest", coin.upper(), num("oiCcy")),
            Spec("open_interest_usd", "USD", num("oiUsd")),
        ]),
    ]
    facts = []
    for ep in endpoints:
        facts += run_endpoint(get, ep, "okx", coin, fetched_at)
    return facts
