import math
import re
from datetime import UTC, datetime
from html.parser import HTMLParser

from ..model import Fact, iso, missing, ok
from .base import FetchError

BASE = "https://bitbo.io/treasuries/etf-flows/"
FUNDS = ("IBIT", "FBTC", "GBTC", "BTC", "BITB", "ARKB", "HODL", "MSBT",
         "BRRR", "EZBC", "BTCO", "BTCW", "BITA", "DEFI")
# The source explicitly labels this table "Bitcoin ETF Flow (US$m)".
# Farside's /btc/ table independently confirms the USD-million scale; values differ.
SCALE = 1_000_000


class _Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.table = self.row = self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            if self.table is not None:
                raise ValueError("nested table")
            self.table = []
        elif self.table is not None and tag == "tr":
            if self.row is not None:
                raise ValueError("unclosed row")
            self.row = []
        elif self.row is not None and tag in ("th", "td"):
            if self.cell is not None:
                raise ValueError("unclosed cell")
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("th", "td") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.cell is not None:
                raise ValueError("unclosed cell")
            self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            if self.row is not None:
                raise ValueError("unclosed row")
            self.tables.append(self.table)
            self.table = None


def parse_latest(text: str) -> tuple[list[str], list[str] | None, str | None]:
    parser = _Tables()
    parser.feed(text)
    parser.close()
    if parser.table is not None or not re.search(r"Bitcoin\s+ETF\s+Flow\s*\(US\$m\)", text):
        raise ValueError("unexpected table or units")
    tables = [table for table in parser.tables if table and table[0] and table[0][0] == "Date"]
    if len(tables) != 1:
        raise ValueError("unexpected header")
    header, *rows = tables[0]
    if (len(header) < 3 or header[-1] not in ("Total", "Totals")
            or len(set(header)) != len(header)
            or any(not re.fullmatch(r"[A-Z][A-Z0-9]*", fund) for fund in header[1:-1])):
        raise ValueError("unexpected header")
    best = None
    for row in rows:
        if row and row[0] in ("Total", "Totals", "Average", "Maximum", "Minimum"):
            continue
        if len(row) != len(header):
            raise ValueError("unexpected row width")
        date = datetime.strptime(row[0], "%b %d, %Y").replace(tzinfo=UTC)
        if best is None or date > best[0]:
            best = (date, row[1:])
    metrics = [f"etf_flow_{fund.lower()}" for fund in header[1:-1]] + ["etf_flow_total"]
    return metrics, None if best is None else best[1], None if best is None else iso(best[0])


def collect(get_text, fetched_at: str) -> list[Fact]:
    metrics = [f"etf_flow_{fund.lower()}" for fund in FUNDS] + ["etf_flow_total"]
    reason = None
    values = as_of = None
    try:
        metrics, values, as_of = parse_latest(get_text(BASE, {}))
    except FetchError as exc:
        reason = str(exc) or "request error"
    except (ValueError, TypeError):
        reason = "field absent in response"
    facts = []
    for index, metric in enumerate(metrics):
        why = reason
        value = None
        if why is None:
            raw = "" if values is None else values[index]
            if raw in ("", "-"):
                why = "not published"
            else:
                try:
                    value = float(raw.replace(",", "")) * SCALE
                    if not math.isfinite(value):
                        raise ValueError("non-finite observation")
                except ValueError:
                    why = "field absent in response"
        fid = f"bitbo.btc.{metric}"
        if why:
            facts.append(missing(fid, "btc", metric, "USD", why, fetched_at, "bitbo"))
        else:
            facts.append(ok(fid, "btc", metric, value, "USD", as_of, fetched_at, "bitbo"))
    return facts
