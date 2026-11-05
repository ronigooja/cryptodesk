import math
from datetime import UTC, datetime

from ..model import Fact, iso, missing, ok
from .base import FetchError

URL = "https://markets.newyorkfed.org/api/rates/unsecured/effr/last/1.json"
ID = "nyfed.macro.fed_funds_effective"


def collect(get, fetched_at: str) -> list[Fact]:
    reason = None
    value = as_of = None
    try:
        row = get(URL, None)["refRates"][0]
        value = float(row["percentRate"])
        if not math.isfinite(value):
            raise ValueError("non-finite")
        as_of = iso(datetime.strptime(row["effectiveDate"], "%Y-%m-%d").replace(tzinfo=UTC))
    except FetchError as exc:
        reason = str(exc) or "request error"
    except (KeyError, IndexError, TypeError, ValueError):
        reason = "field absent in response"
    if reason:
        return [missing(ID, "macro", "fed_funds_effective", "percent", reason, fetched_at, "nyfed")]
    return [ok(ID, "macro", "fed_funds_effective", value, "percent", as_of, fetched_at, "nyfed")]
