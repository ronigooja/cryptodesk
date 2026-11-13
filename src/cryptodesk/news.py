"""RSS metadata only; never retain article content."""

import hashlib
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .adapters.base import FetchError
from .model import iso, valid_time
from .store import find_root

FEEDS = {
    "cointelegraph": "https://cointelegraph.com/rss",
    "theblock": "https://www.theblock.co/rss.xml",
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss",
    "decrypt": "https://decrypt.co/feed",
    "fed_press": "https://www.federalreserve.gov/feeds/press_all.xml",
    "fed_monetary": "https://www.federalreserve.gov/feeds/press_monetary.xml",
    "sec": "https://www.sec.gov/news/pressreleases.rss",
}
FIELDS = {"id", "source", "title", "published_at", "url", "fetched_at"}


def canonical_url(raw: str) -> str:
    parts = urlsplit(raw.strip())
    if parts.scheme.lower() != "https" or not parts.hostname or parts.username or parts.password:
        raise ValueError("invalid HTTPS URL")
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith("utm_")]
    return urlunsplit(("https", parts.netloc.lower(), parts.path, urlencode(query), ""))


def item_id(source: str, url: str) -> str:
    return f"{source}:{hashlib.sha1(url.encode('utf-8')).hexdigest()[:12]}"


def clean_title(title: str) -> str:
    title = " ".join(title.split())
    return "".join(c for c in title if not unicodedata.category(c).startswith("C"))[:300].rstrip()


def publication_time(raw: str) -> str:
    try:
        date = parsedate_to_datetime(raw)
    except (ValueError, TypeError, OverflowError):
        date = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if date.tzinfo is None or date.utcoffset() is None:
        raise ValueError("date lacks timezone")
    return iso(date)


def parse_feed(text: str, source: str, fetched_at: str) -> tuple[list[dict], int]:
    root = ET.fromstring(text.lstrip("\ufeff"))
    if root.tag.rsplit("}", 1)[-1] not in ("rss", "RDF"):
        raise ValueError("not RSS")
    records, skipped = [], 0
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "item":
            continue
        fields = {child.tag.rsplit("}", 1)[-1]: child.text or "" for child in element}
        try:
            url = canonical_url(fields.get("link", ""))
            published = publication_time(fields.get("pubDate") or fields.get("date", ""))
        except (ValueError, TypeError, OverflowError):
            skipped += 1
            continue
        records.append({"id": item_id(source, url), "source": source,
                        "title": clean_title(fields.get("title", "")),
                        "published_at": published, "url": url, "fetched_at": fetched_at})
    return records, skipped


def collect(get_text, fetched_at: str) -> tuple[list[dict], list[str], int]:
    records, errors, skipped = [], [], 0
    for source, url in FEEDS.items():
        try:
            items, count = parse_feed(get_text(url, {}), source, fetched_at)
            records.extend(items)
            skipped += count
        except FetchError as exc:
            errors.append(f"{source}: {exc}")
        except (ET.ParseError, ValueError, TypeError):
            errors.append(f"{source}: invalid RSS XML")
    return records, errors, skipped


def validate(record) -> list[str]:
    if not isinstance(record, dict):
        return ["news: record is not an object"]
    label, errors = record.get("id", "<no id>"), []
    if set(record) != FIELDS:
        errors.append(f"{label}: news fields must be metadata only: {', '.join(sorted(FIELDS))}")
    for field in ("published_at", "fetched_at"):
        if not valid_time(record.get(field)):
            errors.append(f"{label}: {field} not UTC ISO")
    title = record.get("title")
    if not isinstance(title, str) or title != clean_title(title) or len(title) > 300:
        errors.append(f"{label}: invalid news title")
    url, source = record.get("url"), record.get("source")
    try:
        if not isinstance(url, str) or canonical_url(url) != url:
            raise ValueError("invalid URL")
        if not isinstance(source, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", source):
            raise ValueError("invalid source")
        if label != item_id(source, url):
            errors.append(f"{label}: news id does not match source and URL")
    except ValueError:
        errors.append(f"{label}: invalid news URL or source")
    return errors


class NewsStore:
    def __init__(self, root: Path | None = None):
        self.root = root if root is not None else find_root()

    def iter_records(self):
        for path in sorted((self.root / "data" / "news").glob("*.jsonl")):
            for line in path.read_text().splitlines():
                if line.strip():
                    yield json.loads(line)

    def apply(self, records: list[dict], started: str, errors: list[str], skipped: int = 0) -> dict:
        known = {record["id"] for record in self.iter_records()}
        changed = unchanged = 0
        for record in records:
            if record["id"] in known:
                unchanged += 1
                continue
            path = self.root / "data" / "news" / f"{record['published_at'][:7]}.jsonl"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            known.add(record["id"])
            changed += 1
        run = {"started": started, "group": "news", "facts": len(records), "changed": changed,
               "unchanged": unchanged, "missing": len(errors), "errors": errors, "skipped": skipped}
        path = self.root / "runs" / f"{started[:7]}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(run, sort_keys=True) + "\n")
        return run
