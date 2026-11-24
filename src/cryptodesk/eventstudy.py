"""Read-only, on-demand Binance minute-bar event study."""
from datetime import UTC, datetime, timedelta, timezone
from math import isfinite
import re
from statistics import median

from .adapters.base import FetchError

MINUTE = timedelta(minutes=1)
DAY = timedelta(days=1)
ENDPOINTS = {
    "spot": "https://api.binance.com/api/v3/klines",
    "perpetual": "https://fapi.binance.com/fapi/v1/klines",
}


def parse_at(value):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?Z", value):
        raise ValueError("--at must be a UTC ISO time ending in Z")
    try:
        at = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise ValueError("--at must be a UTC ISO time ending in Z") from None
    if at.second or at.microsecond:
        raise ValueError("--at must be aligned to a UTC minute")
    if at > datetime.now(UTC):
        raise ValueError("--at must not be in the future")
    return at


def fetch_window(get, endpoint, symbol, start, end):
    """Fetch [start, end), retaining gaps and rejecting malformed rows."""
    result = {}
    cursor = start
    while cursor < end:
        stop = min(end, cursor + 1000 * MINUTE)
        rows = get(endpoint, {"symbol": symbol, "interval": "1m", "startTime": int(cursor.timestamp() * 1000),
                              "endTime": int(stop.timestamp() * 1000) - 1, "limit": 1000})
        if not isinstance(rows, list):
            raise ValueError("invalid response")
        for row in rows:
            try:
                if not isinstance(row, list) or len(row) != 12:
                    raise ValueError
                values = [float(x) for x in row]
                if not all(isfinite(x) for x in values):
                    raise ValueError
                ms = values[0]
                if ms != int(ms) or int(ms) % 60000:
                    raise ValueError
                when = datetime.fromtimestamp(ms / 1000, UTC)
                if not cursor <= when < stop or when in result or values[4] <= 0 or values[7] < 0:
                    raise ValueError
                result[when] = (values[4], values[7])
            except (ValueError, TypeError, OverflowError, OSError):
                raise ValueError("invalid kline row") from None
        cursor = stop
    return result


def minute_return(data, when):
    current, previous = data.get(when), data.get(when - MINUTE)
    return 100 * (current[0] / previous[0] - 1) if current and previous else None


def observations(days, when, metric, exclude=None):
    values = []
    for day, data in days.items():
        if day == exclude:
            continue
        center = datetime.combine(day, when.timetz())
        for offset in range(-30, 31):
            t = center + offset * MINUTE
            value = data.get(t, (None, None))[1] if metric == "turnover" else minute_return(data, t)
            if value is not None:
                values.append(abs(value) if metric == "return" else value)
    return values


def baseline(days, when, metric, exclude=None):
    values = observations(days, when, metric, exclude)
    if len(values) < 5:
        return None, None
    mid = median(values)
    return mid, median(abs(x - mid) for x in values)


def multiple(data, days, when):
    mid, _ = baseline(days, when, "turnover")
    row = data.get(when)
    return row[1] / mid if row and mid else None


def count_flags(data, days, at, exclude=None):
    count = 0
    for offset in range(-60, 0):
        when = at + offset * MINUTE
        row = data.get(when)
        for metric, value in (("turnover", row[1] if row else None), ("return", minute_return(data, when))):
            mid, mad = baseline(days, when, metric, exclude)
            if value is not None and mad and 0.67448975 * (abs(value) - mid) / mad > 6:
                count += 1
                break
    return count


def fmt(value, places=3):
    return "-" if value is None else f"{value:.{places}f}"


def run(get, at, before=60, after=30, baseline_days=7):
    print("Research read, not fact records; nothing is stored.")
    print(f"T: {at.isoformat().replace('+00:00', 'Z')} / {at.astimezone(timezone(timedelta(hours=8))).isoformat()} (UTC+8)")
    print(f"before={before} min after={after} min baseline-days={baseline_days}; window [T-before, T+after)")
    print(f"Endpoints: spot {ENDPOINTS['spot']}; perpetual {ENDPOINTS['perpetual']}")
    print("Baseline: prior UTC days, same clock minute +/-30 min; median and MAD, >=5 observations; robust z=0.67449*(value-median)/MAD, zero MAD undefined; control days exclude themselves.")
    succeeded = 0
    for symbol in ("BTCUSDT", "ETHUSDT"):
        for market, endpoint in ENDPOINTS.items():
            name = f"{symbol} {market}"
            try:
                # Extra prior minute supports the first return; baseline margin supports +/-30 and controls.
                data = fetch_window(get, endpoint, symbol, at - max(before, 60) * MINUTE - MINUTE, at + max(after, 31) * MINUTE)
                days = {}
                for n in range(1, baseline_days + 1):
                    center = at - n * DAY
                    days[center.date()] = fetch_window(get, endpoint, symbol,
                        center - (max(before, 60) + 31) * MINUTE,
                        center + (after + 30) * MINUTE)
                if not data or not any(at - before * MINUTE <= t < at + after * MINUTE for t in data):
                    raise ValueError("no event-window data")
                if not any(days.values()):
                    raise ValueError("no baseline data")
            except (FetchError, ValueError) as exc:
                print(f"missing: {name} {exc}")
                continue
            succeeded += 1
            print(f"\n{name}")
            print("UTC minute | close | return % | turnover USDT M | baseline multiple | after T")
            for offset in range(-before, after):
                t = at + offset * MINUTE
                row = data.get(t)
                print(f"{t:%Y-%m-%dT%H:%MZ} | {fmt(row[0] if row else None)} | {fmt(minute_return(data, t))} | "
                      f"{fmt(row[1] / 1e6 if row else None)} | {fmt(multiple(data, days, t))} | {'*' if offset >= 0 else ''}")
            previous = data.get(at - MINUTE)
            def event_return(offset):
                row = data.get(at + offset * MINUTE)
                return 100 * (row[0] / previous[0] - 1) if row and previous else None
            post = [(v[1], t) for t, v in data.items() if at <= t < at + after * MINUTE]
            peak = max(post) if post else None
            peak_text = f"{peak[1]:%Y-%m-%dT%H:%MZ} {fmt(peak[0] / 1e6)}M multiple={fmt(multiple(data, days, peak[1]))}" if peak else "-"
            controls = ", ".join(f"{day}={count_flags(rows, days, at - (at.date() - day), day)}" for day, rows in days.items())
            print(f"summary {name}: return T+5={fmt(event_return(5))}% T+30={fmt(event_return(30))}%; peak turnover {peak_text}; pre-T flags={count_flags(data, days, at)}; controls {controls}")
    return 0 if succeeded else 1
