import math
import re
from datetime import UTC, datetime

from ..model import Fact, iso, missing, ok
from .base import FetchError
from .etf import _Tables

URL = "https://farside.co.uk/eth/"
SCALE = 1_000_000
FUND = re.compile(r"[A-Z][A-Z0-9]*")


class _Rows(_Tables):
    """Like the Bitbo parser but tolerates a row or cell left open by the next tag (Farside markup)."""

    def _close_cell(self):
        if self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None

    def _close_row(self):
        self._close_cell()
        if self.row is not None:
            self.table.append(self.row)
            self.row = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._close_row()
            if self.table is not None:
                self.tables.append(self.table)
            self.table = []
        elif self.table is not None and tag == "tr":
            self._close_row()
            self.row = []
        elif self.row is not None and tag in ("th", "td"):
            self._close_cell()
            self.cell = []

    def handle_endtag(self, tag):
        if tag in ("th", "td"):
            self._close_cell()
        elif tag == "tr":
            self._close_row()
        elif tag == "table" and self.table is not None:
            self._close_row()
            self.tables.append(self.table)
            self.table = None


def _number(raw: str) -> float | None:
    raw = raw.strip().replace(",", "")
    if raw in ("", "-"):
        return None
    negative = raw.startswith("(") and raw.endswith(")")
    value = float(raw[1:-1] if negative else raw)
    if not math.isfinite(value):
        raise ValueError("non-finite observation")
    return -value if negative else value


def parse_latest(text: str) -> tuple[list[str], list[str], str]:
    """Newest dated row of the Farside ETH table: (fund tickers + 'total', cells, YYYY-MM-DD).

    Units are US$m; parentheses mean negative. Raises ValueError on an unexpected layout or when the
    funds do not add up to the total within rounding (0.1 per fund).
    """
    if not re.search(r"US\$m", text):
        raise ValueError("unexpected units")
    parser = _Rows()
    parser.feed(text)
    parser.close()
    tables = [t for t in parser.tables if any(len(r) > 3 and r[0] == "Fee" for r in t)]
    if len(tables) != 1:
        raise ValueError("unexpected table")
    funds = None
    best = None
    for row in tables[0]:
        if funds is None:
            if len(row) > 3 and row[0] == "" and row[-1] == "" and all(FUND.fullmatch(c) for c in row[1:-1]):
                funds = row[1:-1]
            continue
        if not row:
            continue
        try:
            date = datetime.strptime(row[0], "%d %b %Y")
        except ValueError:
            continue
        if len(row) != len(funds) + 2:
            raise ValueError("unexpected row width")
        if best is None or date > best[0]:
            best = (date, row[1:])
    if funds is None or len(set(funds)) != len(funds) or best is None:
        raise ValueError("unexpected header")
    cells = best[1]
    parts = [_number(c) for c in cells[:-1]]
    total = _number(cells[-1])
    if total is not None and abs(sum(p or 0.0 for p in parts) - total) > 0.1 * len(funds):
        raise ValueError("funds do not add up to total")
    return [f"etf_flow_{f.lower()}" for f in funds] + ["etf_flow_total"], cells, best[0].strftime("%Y-%m-%d")


def collect(get_text, fetched_at: str) -> list[Fact]:
    reason = None
    metrics, cells, date = [], [], None
    try:
        metrics, cells, date = parse_latest(get_text(URL, {}))
    except FetchError as exc:
        reason = str(exc) or "request error"
    except (ValueError, TypeError):
        reason = "field absent in response"
    if reason:
        return [missing("farside.eth.etf_flow_total", "eth", "etf_flow_total", "USD", reason, fetched_at, "farside")]
    as_of = iso(datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=UTC))
    facts = []
    for metric, raw in zip(metrics, cells):
        fid = f"farside.eth.{metric}"
        value = _number(raw)
        if value is None:
            facts.append(missing(fid, "eth", metric, "USD", "not published", fetched_at, "farside"))
        else:
            facts.append(ok(fid, "eth", metric, value * SCALE, "USD", as_of, fetched_at, "farside"))
    return facts
