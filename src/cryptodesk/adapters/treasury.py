import csv
import io
import math
from datetime import UTC, datetime

from ..model import Fact, iso, missing, ok
from .base import FetchError

BASE = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv"
COLUMNS = {"2 Yr": "us2y_yield", "10 Yr": "us10y_yield"}


def _params(year: int) -> dict:
    return {"type": "daily_treasury_yield_curve", "field_tdr_date_value": year, "_format": "csv"}


def parse_latest(text: str, column: str) -> tuple[float, str] | None:
    """Newest row (the file lists newest first) with a numeric value in column.

    Returns (value, date as YYYY-MM-DD) or None if no row has a value.
    Raises ValueError when the header lacks Date or the column.
    """
    reader = csv.DictReader(io.StringIO(text.strip()))
    if not reader.fieldnames or "Date" not in reader.fieldnames or column not in reader.fieldnames:
        raise ValueError("unexpected header")
    best = None
    for row in reader:
        raw = (row[column] or "").strip()
        if raw in ("", "N/A"):
            continue
        date = datetime.strptime(row["Date"], "%m/%d/%Y")
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError("non-finite observation")
        if best is None or date > best[0]:
            best = (date, value)
    return None if best is None else (best[1], best[0].strftime("%Y-%m-%d"))


def collect(get_text, fetched_at: str) -> list[Fact]:
    year = int(fetched_at[:4])
    err = None
    texts = []
    for y in (year, year - 1):
        try:
            texts.append(get_text(f"{BASE}/{y}/all", _params(y)))
        except FetchError as exc:
            err = str(exc) or "request error"
            break
        try:
            if any(parse_latest(texts[-1], c) for c in COLUMNS):
                break
        except (ValueError, TypeError):
            break
    facts = []
    for column, metric in COLUMNS.items():
        fid = f"treasury.macro.{metric}"
        reason = err
        value = as_of = None
        if reason is None:
            try:
                latest = None
                for text in texts:
                    latest = parse_latest(text, column)
                    if latest:
                        break
                if latest is None:
                    reason = "not published"
                else:
                    value = latest[0]
                    as_of = iso(datetime.strptime(latest[1], "%Y-%m-%d").replace(tzinfo=UTC))
            except (ValueError, TypeError):
                reason = "field absent in response"
        if reason:
            facts.append(missing(fid, "macro", metric, "percent", reason, fetched_at, "treasury"))
        else:
            facts.append(ok(fid, "macro", metric, value, "percent", as_of, fetched_at, "treasury"))
    return facts
