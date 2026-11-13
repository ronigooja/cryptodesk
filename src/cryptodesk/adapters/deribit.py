import math
import re
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from ..model import Fact, missing, ms_to_iso, ok
from .base import Endpoint, FetchError, Spec, run_endpoint

BASE = "https://www.deribit.com/api/v2/public"
INSTR_RE = re.compile(r"^[A-Z]+-(\d{1,2}[A-Z]{3}\d{2})-(\d+(?:\.\d+)?)-([CP])$")


def _result(d):
    return d["result"]


def max_pain(strikes: dict[float, dict[str, float]]) -> float | None:
    """strikes: strike -> {"C": oi, "P": oi}. Returns the strike minimizing total holder payout."""
    if not strikes:
        return None
    best = None
    for k in sorted(strikes):
        payout = sum(
            v.get("C", 0.0) * max(0.0, k - s) + v.get("P", 0.0) * max(0.0, s - k)
            for s, v in strikes.items()
        )
        if best is None or payout < best[1]:
            best = (k, payout)
    return best[0]


def group_options(summary: list[dict]) -> dict[str, dict[float, dict[str, float]]]:
    by_expiry: dict[str, dict[float, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    for row in summary:
        m = INSTR_RE.match(row["instrument_name"])
        if not m:
            continue
        expiry = datetime.strptime(m.group(1), "%d%b%y").strftime("%Y-%m-%d")
        strike, interest = float(m.group(2)), float(row["open_interest"])
        if not math.isfinite(strike) or not math.isfinite(interest) or interest < 0:
            raise ValueError("invalid option value")
        by_expiry[expiry][strike][m.group(3)] = interest
    return by_expiry


def option_facts(coin: str, summary: list[dict], fetched_at: str) -> list[Fact]:
    grouped = group_options([row for row in summary if row["instrument_name"].startswith(coin.upper() + "-")])
    if not grouped:
        raise ValueError("no option series")
    now = datetime.fromisoformat(fetched_at)
    active = {
        expiry: strikes for expiry, strikes in sorted(grouped.items())
        if datetime.fromisoformat(expiry).replace(hour=8, tzinfo=UTC) > now
    }
    facts = []
    for side, metric in (("C", "oi_call_total"), ("P", "oi_put_total")):
        total = sum(v.get(side, 0.0) for strikes in active.values() for v in strikes.values())
        facts.append(ok(f"deribit.{coin}.{metric}", coin, metric, total, coin.upper(), None, fetched_at, "deribit"))
    for expiry, strikes in active.items():
        date = datetime.fromisoformat(expiry)
        if date.weekday() == 4 and (date + timedelta(days=7)).month != date.month:
            facts.append(ok(f"deribit.{coin}.opt.{expiry}.max_pain", coin, "max_pain", max_pain(strikes), "USD", None, fetched_at, "deribit"))
            break
    return facts


def _dvol(d):
    rows = _result(d)["data"]
    ts, _o, _h, _l, close = rows[-1]
    return float(close), ms_to_iso(ts)


def collect_market(coin: str, profile: dict, get, fetched_at: str, now: datetime | None = None) -> list[Fact]:
    cfg = profile["deribit"]
    now = now or datetime.now(UTC)
    end = int(now.timestamp() * 1000)
    endpoints = [
        Endpoint(f"{BASE}/ticker", {"instrument_name": cfg["perp"]}, [
            Spec("perp_mark_price", "USD", lambda d: (float(_result(d)["mark_price"]), ms_to_iso(_result(d)["timestamp"]))),
            Spec("funding_rate_8h", "fraction", lambda d: (float(_result(d)["funding_8h"]), ms_to_iso(_result(d)["timestamp"]))),
        ]),
        Endpoint(f"{BASE}/get_volatility_index_data",
                 {"currency": cfg["currency"], "resolution": "3600", "start_timestamp": end - 3 * 3600 * 1000, "end_timestamp": end},
                 [Spec("dvol", "percent", _dvol)]),
    ]
    facts = []
    for ep in endpoints:
        facts += run_endpoint(get, ep, "deribit", coin, fetched_at)
    return facts


def collect_options(coin: str, profile: dict, get, fetched_at: str) -> list[Fact]:
    cfg = profile["deribit"]
    try:
        data = get(f"{BASE}/get_book_summary_by_currency", {"currency": cfg["currency"], "kind": "option"})
        return option_facts(coin, _result(data), fetched_at)
    except FetchError as e:
        reason = str(e)
    except (KeyError, TypeError, ValueError):
        reason = "field absent in response"
    return [missing(f"deribit.{coin}.{metric}", coin, metric, coin.upper(), reason, fetched_at, "deribit")
            for metric in ("oi_call_total", "oi_put_total")]
