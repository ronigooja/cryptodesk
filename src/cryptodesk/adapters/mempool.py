import math

from .base import Endpoint, Spec, run_endpoint

BASE = "https://mempool.space/api/v1"


def _extract(data, field):
    value = float(data[field])
    if not math.isfinite(value):
        raise ValueError("non-finite")
    return value, None


def collect(coin: str | None, get, fetched_at: str) -> list:
    if coin != "btc":
        return []
    endpoints = [
        Endpoint(f"{BASE}/mining/hashrate/3d", {}, [
            Spec("hashrate", "H/s", lambda data: _extract(data, "currentHashrate")),
            Spec("difficulty", "number", lambda data: _extract(data, "currentDifficulty")),
        ]),
        Endpoint(f"{BASE}/fees/recommended", {}, [
            Spec("fee_fastest", "sat/vB", lambda data: _extract(data, "fastestFee")),
        ]),
    ]
    facts = []
    for ep in endpoints:
        facts += run_endpoint(get, ep, "mempool", coin, fetched_at)
    return facts
