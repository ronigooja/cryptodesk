import math
from datetime import UTC, datetime

from ..model import Fact, iso, missing, ok
from .base import FetchError

BASE = "https://api.stlouisfed.org/fred/series/observations"
SERIES = {
    "DGS10": "us10y_yield",
    "DGS2": "us2y_yield",
    "DFF": "fed_funds_effective",
}


def collect(api_key: str | None, get, fetched_at: str) -> list[Fact]:
    facts = []
    for series, metric in SERIES.items():
        fid = f"fred.macro.{metric}"
        reason = None
        value = as_of = None
        if not api_key:
            reason = "FRED_API_KEY not set"
        else:
            try:
                data = get(BASE, {
                    "series_id": series,
                    "api_key": api_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 5,
                })
                observation = next((o for o in data["observations"] if o["value"] != "."), None)
                if observation is None:
                    reason = "not published"
                else:
                    value = float(observation["value"])
                    if not math.isfinite(value):
                        raise ValueError("non-finite observation")
                    as_of = iso(datetime.strptime(observation["date"], "%Y-%m-%d").replace(tzinfo=UTC))
            except FetchError as exc:
                reason = str(exc).replace(api_key, "[redacted]")
                if not reason:
                    reason = "request error"
            except (KeyError, IndexError, TypeError, ValueError):
                reason = "field absent in response"
        if reason:
            facts.append(missing(fid, "macro", metric, "percent", reason, fetched_at, "fred"))
        else:
            facts.append(ok(fid, "macro", metric, value, "percent", as_of, fetched_at, "fred"))
    return facts
