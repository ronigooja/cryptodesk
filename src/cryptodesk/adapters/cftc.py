from datetime import datetime

from ..model import Fact
from .base import Endpoint, FetchError, Spec, run_endpoint

BASE = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
MARKETS = {
    "btc": "BITCOIN - CHICAGO MERCANTILE EXCHANGE",
    "eth": "ETHER CASH SETTLED - CHICAGO MERCANTILE EXCHANGE",
}


def _as_of(row):
    date = datetime.fromisoformat(row["report_date_as_yyyy_mm_dd"]).date()
    return date.isoformat() + "T00:00:00Z"


def _open_interest(row):
    return int(row["open_interest_all"]), _as_of(row)


def _net(row, group):
    return int(row[f"{group}_positions_long"]) - int(row[f"{group}_positions_short"]), _as_of(row)


def collect(coin: str, profile: dict, get, fetched_at: str) -> list[Fact]:
    market = MARKETS[coin]

    def latest(url, params):
        rows = get(url, params)
        if not isinstance(rows, list):
            raise FetchError("field absent in response")
        if not rows:
            raise FetchError("not published")
        try:
            return max(rows, key=_as_of)
        except (KeyError, TypeError, ValueError):
            raise FetchError("field absent in response")

    endpoint = Endpoint(BASE, {
        "$where": f"market_and_exchange_names = '{market}'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": 1,
    }, [
        Spec("cot_open_interest", "contracts", _open_interest),
        Spec("cot_asset_mgr_net", "contracts", lambda row: _net(row, "asset_mgr")),
        Spec("cot_lev_money_net", "contracts", lambda row: _net(row, "lev_money")),
    ])
    return run_endpoint(latest, endpoint, "cftc", coin, fetched_at)
