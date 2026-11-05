import re
from collections import defaultdict
from datetime import UTC, datetime

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
        by_expiry[expiry][float(m.group(2))][m.group(3)] = float(row["open_interest"])
    return by_expiry


def option_facts(coin: str, summary: list[dict], fetched_at: str) -> list[Fact]:
    facts = []
    for expiry, strikes in sorted(group_options(summary).items()):
        base = f"deribit.{coin}.opt.{expiry}."
        calls = sum(v.get("C", 0.0) for v in strikes.values())
        puts = sum(v.get("P", 0.0) for v in strikes.values())
        unit = coin.upper()
        facts.append(ok(base + "oi_call", coin, "oi_call", calls, unit, None, fetched_at, "deribit"))
        facts.append(ok(base + "oi_put", coin, "oi_put", puts, unit, None, fetched_at, "deribit"))
        facts.append(ok(base + "max_pain", coin, "max_pain", max_pain(strikes), "USD", None, fetched_at, "deribit"))
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
    return [missing(f"deribit.{coin}.opt.all.options_summary", coin, "oi_call", coin.upper(), reason, fetched_at, "deribit")]
