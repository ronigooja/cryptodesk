import math
from datetime import datetime

from ..model import iso
from .base import Endpoint, Spec, run_endpoint

URL = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
FIELDS = {"mvrv": "CapMVRVCur", "active_addresses": "AdrActCnt", "fees_total": "FeeTotNtv"}


def _extract(data, coin, field):
    rows = [row for row in data["data"] if row["asset"] == coin]
    row = max(rows, key=lambda row: datetime.fromisoformat(row["time"]))
    value = float(row[field])
    if not math.isfinite(value):
        raise ValueError("non-finite")
    return value, iso(datetime.fromisoformat(row["time"]))


def collect(coin: str | None, get, fetched_at: str) -> list:
    if coin not in ("btc", "eth"):
        return []
    ep = Endpoint(URL, {
        "assets": coin, "metrics": ",".join(FIELDS.values()),
        "frequency": "1d", "page_size": 4, "sort": "time", "paging_from": "end",
    }, [
        Spec(metric, "ratio" if metric == "mvrv" else "count" if metric == "active_addresses" else coin.upper(),
             lambda data, field=field: _extract(data, coin, field))
        for metric, field in FIELDS.items()
    ])
    return run_endpoint(get, ep, "coinmetrics", coin, fetched_at)
