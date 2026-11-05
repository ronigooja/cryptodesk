from ..model import ms_to_iso
from .base import Endpoint, Spec, run_endpoint

SPOT = "https://api.binance.com"
FAPI = "https://fapi.binance.com"


def collect(coin: str, profile: dict, get, fetched_at: str) -> list:
    cfg = profile["binance"]
    spot, perp = cfg["spot"], cfg["perp"]
    ratio_params = {"symbol": perp, "period": "1h", "limit": 1}

    def f(key):
        return lambda d: (float(d[key]), ms_to_iso(d["closeTime"]))

    endpoints = [
        Endpoint(f"{SPOT}/api/v3/ticker/24hr", {"symbol": spot}, [
            Spec("spot_price", "USDT", f("lastPrice")),
            Spec("change_24h_pct", "percent", f("priceChangePercent")),
            Spec("high_24h", "USDT", f("highPrice")),
            Spec("low_24h", "USDT", f("lowPrice")),
        ]),
        Endpoint(f"{FAPI}/fapi/v1/premiumIndex", {"symbol": perp}, [
            Spec("perp_mark_price", "USDT", lambda d: (float(d["markPrice"]), ms_to_iso(d["time"]))),
            Spec("funding_rate_8h", "fraction", lambda d: (float(d["lastFundingRate"]), ms_to_iso(d["time"]))),
        ]),
        Endpoint(f"{FAPI}/fapi/v1/openInterest", {"symbol": perp}, [
            Spec("open_interest", coin.upper(), lambda d: (float(d["openInterest"]), ms_to_iso(d["time"]))),
        ]),
        Endpoint(f"{FAPI}/futures/data/topLongShortPositionRatio", ratio_params, [
            Spec("top_ls_position_ratio", "ratio", lambda d: (float(d[0]["longShortRatio"]), ms_to_iso(d[0]["timestamp"]))),
        ]),
        Endpoint(f"{FAPI}/futures/data/topLongShortAccountRatio", ratio_params, [
            Spec("top_ls_account_ratio", "ratio", lambda d: (float(d[0]["longShortRatio"]), ms_to_iso(d[0]["timestamp"]))),
        ]),
    ]
    facts = []
    for ep in endpoints:
        facts += run_endpoint(get, ep, "binance", coin, fetched_at)
    return facts
