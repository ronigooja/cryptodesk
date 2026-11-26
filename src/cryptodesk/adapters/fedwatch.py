import math
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

from ..model import iso, missing, ok
from .base import FetchError
from .etf import _Tables

URL = "https://www.cmegroup.cn/fed-watch/"


class _Iframes(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        if tag == "iframe":
            self.urls.append(dict(attrs).get("src", ""))


def fetch_page():
    try:
        from curl_cffi import requests
    except ImportError:
        raise FetchError("curl_cffi not installed")
    try:
        with requests.Session(impersonate="chrome", timeout=30) as session:
            page = session.get(URL)
            if page.status_code != 200:
                raise FetchError(f"HTTP {page.status_code}")
            parser = _Iframes()
            parser.feed(page.text)
            urls = [urljoin(URL, u) for u in parser.urls if urlsplit(urljoin(URL, u)).hostname == "cmegroup-tools.quikstrike.net"]
            if len(urls) != 1:
                raise FetchError("field absent in response")
            wrapper = session.get(urls[0], headers={"Referer": URL})
            if wrapper.status_code != 200:
                raise FetchError(f"HTTP {wrapper.status_code}")
            if (urlsplit(wrapper.url).hostname != "cmegroup-tools.quikstrike.net"
                    or urlsplit(wrapper.url).path != "/User/QuikStrikeTools.aspx"):
                raise FetchError("field absent in response")
            view = wrapper.url.replace("/User/QuikStrikeTools.aspx", "/User/QuikStrikeView.aspx", 1)
            response = session.get(view, headers={"Referer": wrapper.url})
            if response.status_code != 200:
                raise FetchError(f"HTTP {response.status_code}")
            return response.text
    except FetchError:
        raise
    except Exception as exc:
        raise FetchError(f"request error {type(exc).__name__}")


CT = ZoneInfo("America/Chicago")


def resolve_time(wall, reference):
    """The page prints a 12-hour clock without AM or PM (00:23 CT shows as 12:23, 16:31 CT as 04:31).
    Take the latest reading not after `reference` (UTC datetime); data 12 hours or older is ambiguous."""
    hours = [wall.hour] if wall.hour == 0 or wall.hour > 12 else [wall.hour % 12, wall.hour % 12 + 12]
    candidates = [wall.replace(hour=h, tzinfo=CT).astimezone(timezone.utc) for h in hours]
    allowed = [c for c in candidates if c <= reference + timedelta(minutes=5)]
    if not allowed or (len(candidates) == 2 and reference - max(allowed) >= timedelta(hours=12)):
        raise ValueError("time ambiguous")
    return max(allowed)


def parse_page(text, reference):
    meeting = re.findall(r"Target Rate Probabilities for (\d{1,2} [A-Za-z]{3} \d{4}) Fed Meeting", text)
    if len(set(meeting)) != 1:
        raise ValueError("meeting absent")
    date = datetime.strptime(meeting[0], "%d %b %Y").strftime("%Y%m%d")
    tables = []
    for match in re.finditer(r"<table\b[^>]*>.*?</table\s*>", text, re.I | re.S):
        html = match.group()
        if "Probability(%)" in html and "Target Rate (bps)" in html:
            parser = _Tables()
            parser.feed(html)
            tables.extend(parser.tables)
    if len(tables) != 1:
        raise ValueError("table absent")
    rows = tables[0]
    if len(rows) < 3 or len(rows[1]) != 4 or not re.fullmatch(r"Now\s*\*?", rows[1][0], re.I):
        raise ValueError("header absent")
    times = [re.search(r"Data as of (\d{1,2} [A-Za-z]{3} \d{4} \d\d:\d\d:\d\d) CT", cell)
             for row in rows for cell in row if "Data as of" in cell]
    if len(times) != 1 or times[0] is None:
        raise ValueError("time absent")
    as_of = iso(resolve_time(datetime.strptime(times[0].group(1), "%d %b %Y %H:%M:%S"), reference))
    result = []
    for row in rows[2:]:
        if not row:
            continue
        match = re.fullmatch(r"(\d+)-(\d+)(?:\s*\(Current\))?", row[0])
        if not match:
            continue
        lower, upper = map(int, match.groups())
        if lower >= upper:
            raise ValueError("invalid range")
        metric = f"fedwatch_probability_{date}b{lower}x{upper}"
        raw = row[1] if len(row) > 1 else ""
        if not any(row[1:4]):
            continue
        value = None
        if re.fullmatch(r"\d+(?:\.\d+)?%", raw):
            value = float(raw[:-1])
            if not math.isfinite(value) or not 0 <= value <= 100:
                value = None
        result.append((metric, value))
    if not result or len({m for m, _ in result}) != len(result):
        raise ValueError("rows absent or duplicated")
    return result, as_of


def collect(fetch, fetched_at):
    try:
        values, as_of = parse_page(fetch(), datetime.fromisoformat(fetched_at.replace("Z", "+00:00")))
    except FetchError as exc:
        return [missing("fedwatch.macro.fedwatch_status", "macro", "fedwatch_status", "number", str(exc), fetched_at, "fedwatch")]
    except (ValueError, TypeError, IndexError):
        return [missing("fedwatch.macro.fedwatch_status", "macro", "fedwatch_status", "number", "field absent in response", fetched_at, "fedwatch")]
    facts = []
    for metric, value in values:
        fid = f"fedwatch.macro.{metric}"
        facts.append(missing(fid, "macro", metric, "percent", "field absent in response", fetched_at, "fedwatch")
                     if value is None else ok(fid, "macro", metric, value, "percent", as_of, fetched_at, "fedwatch"))
    return facts
