"""Daily observations, kept separate from latest-value facts."""

import csv
import fcntl
import io
import json
import re
import stat
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4

from .adapters import coinmetrics, treasury
from .store import find_root

START = date(2025, 1, 1)
SERIES = {
    **{f"price_close.{source}.{coin}": (source, coin, unit)
       for source, unit in (("binance", "USDT"), ("coinbase", "USD"))
       for coin in ("btc", "eth")},
    **{f"mvrv.coinmetrics.{coin}": ("coinmetrics", coin, "ratio") for coin in ("btc", "eth")},
    "us2y_yield.treasury": ("treasury", "2 Yr", "percent"),
    "us10y_yield.treasury": ("treasury", "10 Yr", "percent"),
    "fed_funds_effective.nyfed": ("nyfed", "", "percent"),
    "stablecoin_supply_usd.defillama": ("defillama", "", "USD"),
}


def valid_date(value: str) -> date:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("invalid date")
    return date.fromisoformat(value)


def number(value) -> str | None:
    if value is None or str(value).strip() in ("", ".", "N/A"):
        return None
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except InvalidOperation:
        raise ValueError("invalid number") from None
    if not result.is_finite():
        raise ValueError("non-finite number")
    return format(result, "f")


def _rows(observations, since: date, today: date):
    rows, skipped = [], 0
    for day, raw in observations:
        value = number(raw)
        if value is None or not since <= valid_date(day) < today:
            skipped += 1
        else:
            rows.append((day, value))
    return sorted(rows), skipped


def parse_binance(data, since, today):
    return _rows(((datetime.fromtimestamp(int(r[0]) / 1000, UTC).date().isoformat(), r[4])
                  for r in data), since, today)


def parse_coinbase(data, since, today):
    return _rows(((datetime.fromtimestamp(int(r[0]), UTC).date().isoformat(), r[4])
                  for r in data), since, today)


def parse_coinmetrics(data, coin, since, today):
    return _rows(((r["time"][:10], r.get("CapMVRVCur")) for r in data["data"]
                  if r["asset"] == coin), since, today)


def parse_treasury(text, column, since, today):
    reader = csv.DictReader(io.StringIO(text.strip()))
    if not reader.fieldnames or "Date" not in reader.fieldnames or column not in reader.fieldnames:
        raise ValueError("unexpected header")
    return _rows(((datetime.strptime(r["Date"], "%m/%d/%Y").date().isoformat(), r[column])
                  for r in reader), since, today)


def parse_nyfed(data, since, today):
    return _rows(((r["effectiveDate"], r.get("percentRate")) for r in data["refRates"]), since, today)


def parse_defillama(data, since, today):
    return _rows(((datetime.fromtimestamp(int(r["date"]), UTC).date().isoformat(),
                   r["totalCirculatingUSD"].get("peggedUSD")) for r in data), since, today)


def fetch(series_id, get, get_text, since, today):
    source, key, _ = SERIES[series_id]
    rows, skipped = [], 0

    def add(result):
        nonlocal skipped
        items, count = result
        rows.extend(items)
        skipped += count

    if source == "binance":
        cursor = since
        while cursor < today:
            end = min(cursor + timedelta(days=1000), today)
            data = get("https://api.binance.com/api/v3/klines", {
                "symbol": key.upper() + "USDT", "interval": "1d", "limit": 1000,
                "startTime": int(datetime.combine(cursor, datetime.min.time(), UTC).timestamp() * 1000),
                "endTime": int(datetime.combine(end, datetime.min.time(), UTC).timestamp() * 1000) - 1})
            add(parse_binance(data, since, today))
            cursor = end
    elif source == "coinbase":
        cursor = since
        while cursor < today:
            end = min(cursor + timedelta(days=299), today)
            data = get(f"https://api.exchange.coinbase.com/products/{key.upper()}-USD/candles", {
                "granularity": 86400, "start": cursor.isoformat() + "T00:00:00Z",
                "end": end.isoformat() + "T00:00:00Z"})
            # The API includes the end boundary; exclude it to avoid overlap.
            add(parse_coinbase(data, cursor, end))
            cursor = end
    elif source == "coinmetrics":
        url, params = coinmetrics.URL, {"assets": key, "metrics": "CapMVRVCur", "frequency": "1d",
                                      "start_time": since.isoformat(), "page_size": 10000}
        visited = set()
        while url:
            if url in visited or len(visited) >= 50:
                raise ValueError("pagination loop")
            visited.add(url)
            data = get(url, params)
            add(parse_coinmetrics(data, key, since, today))
            url, params = data.get("next_page_url"), None
    elif source == "treasury":
        for year in range(since.year, today.year + 1):
            add(parse_treasury(get_text(f"{treasury.BASE}/{year}/all", treasury._params(year)),
                               key, since, today))
    elif source == "nyfed":
        add(parse_nyfed(get("https://markets.newyorkfed.org/api/rates/unsecured/effr/search.json", {
            "startDate": since.isoformat(), "endDate": today.isoformat()}), since, today))
    else:
        add(parse_defillama(get("https://stablecoins.llama.fi/stablecoincharts/all", {}), since, today))
    return sorted(rows), skipped


class DailyStore:
    def __init__(self, root: Path | None = None):
        self.root = root if root is not None else find_root()

    def path(self, series_id):
        if not re.fullmatch(r"[a-z0-9_.]+", series_id) or series_id in (".", ".."):
            raise ValueError("invalid series id")
        return self.root / "data" / "daily" / f"{series_id}.csv"

    def load(self, series_id):
        path = self.path(series_id)
        if not path.exists():
            return {}
        reader = csv.reader(io.StringIO(path.read_text()))
        if next(reader, None) != ["date", "value"]:
            raise ValueError("invalid daily header")
        rows, previous = {}, ""
        for row in reader:
            if len(row) != 2:
                raise ValueError("invalid daily row")
            day, value = row
            valid_date(day)
            if day <= previous:
                raise ValueError("daily dates must be ascending and unique")
            if number(value) is None:
                raise ValueError("missing daily value")
            rows[day], previous = value, day
        return rows

    def append(self, series_id, rows):
        path = self.path(series_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with (path.parent / ".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                return self._append(series_id, rows)
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _append(self, series_id, rows):
        known = self.load(series_id)
        added = present = 0
        conflicts = []
        for day, value in sorted(rows):
            valid_date(day)
            value = number(value)
            if value is None:
                raise ValueError("missing daily value")
            if day in known:
                present += 1
                if Decimal(known[day]) != Decimal(value):
                    conflicts.append(f"{series_id}: conflict {day}: stored={known[day]} received={value}")
            else:
                known[day] = value
                added += 1
        if added:
            path = self.path(series_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            # Late observations require sorted insertion; existing rows remain unchanged.
            temporary = path.parent / f".{path.name}.{uuid4().hex}.tmp"
            try:
                with temporary.open("x", newline="") as fh:
                    writer = csv.writer(fh, lineterminator="\n")
                    writer.writerow(["date", "value"])
                    writer.writerows(sorted(known.items()))
                if path.exists():
                    temporary.chmod(stat.S_IMODE(path.stat().st_mode))
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
        return added, present, conflicts

    def collect(self, series_ids, get, get_text, since, started, group):
        today = datetime.fromisoformat(started).astimezone(UTC).date()
        run = {"started": started, "group": group, "facts": 0, "changed": 0,
               "unchanged": 0, "missing": 0, "errors": [], "skipped": 0, "conflicts": 0}
        for series_id in series_ids:
            try:
                rows, skipped = fetch(series_id, get, get_text, since, today)
                added, present, conflicts = self.append(series_id, rows)
                run["facts"] += len(rows)
                run["changed"] += added
                run["unchanged"] += present
                run["skipped"] += skipped
                run["conflicts"] += len(conflicts)
                run["errors"].extend(conflicts)
                print(f"{series_id}: {added} rows added / {present} already present / "
                      f"{skipped} skipped / {len(conflicts)} conflicts")
            except Exception as exc:
                # Do not expose request URLs or credentials in public run records.
                from .adapters.base import FetchError
                reason = str(exc) if isinstance(exc, (FetchError, ValueError)) else type(exc).__name__
                run["missing"] += 1
                run["errors"].append(f"{series_id}: {reason}")
                print(f"{series_id}: failed: {reason}")
        path = self.root / "runs" / f"{started[:7]}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as fh:
            fh.write(json.dumps(run, sort_keys=True) + "\n")
        return run
