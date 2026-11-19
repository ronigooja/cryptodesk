import csv
import io
import math
from datetime import UTC, datetime

from ..model import Fact, iso, missing, ok
from .base import FetchError

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
SERIES = "CPIAUCNS"
IDS = {"cpi_index": "fred.macro.cpi_index", "cpi_yoy_pct": "fred.macro.cpi_yoy_pct"}
UNITS = {"cpi_index": "index", "cpi_yoy_pct": "percent"}


def parse(text: str) -> tuple[str, float, float | None]:
    """Newest row with a value: (YYYY-MM-DD, index, year-over-year percent or None).

    Blank rows are skipped. Year-over-year is None when the same month a year earlier has no value.
    Raises ValueError on an unexpected header or a non-finite value.
    """
    reader = csv.DictReader(io.StringIO(text.strip()))
    if not reader.fieldnames or "observation_date" not in reader.fieldnames or SERIES not in reader.fieldnames:
        raise ValueError("unexpected header")
    rows = {}
    for row in reader:
        raw = (row[SERIES] or "").strip()
        if raw in ("", "."):
            continue
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError("non-finite observation")
        rows[row["observation_date"]] = value
    if not rows:
        raise ValueError("no observation")
    date = max(rows)
    prior = rows.get(f"{int(date[:4]) - 1}{date[4:]}")
    yoy = None if prior is None or prior == 0 else (rows[date] / prior - 1) * 100
    return date, rows[date], yoy


def collect(get_text, fetched_at: str) -> list[Fact]:
    reason = None
    date = index = yoy = None
    try:
        date, index, yoy = parse(get_text(URL, {"id": SERIES}))
    except FetchError as exc:
        reason = str(exc) or "request error"
    except (ValueError, TypeError):
        reason = "field absent in response"
    facts = []
    for metric, fid in IDS.items():
        r = reason
        value = index if metric == "cpi_index" else yoy
        if r is None and value is None:
            r = "not published"
        if r:
            facts.append(missing(fid, "macro", metric, UNITS[metric], r, fetched_at, "fred"))
        else:
            as_of = iso(datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=UTC))
            facts.append(ok(fid, "macro", metric, round(value, 3) if metric == "cpi_yoy_pct" else value,
                            UNITS[metric], as_of, fetched_at, "fred"))
    return facts
