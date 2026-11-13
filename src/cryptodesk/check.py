import json
import re
from pathlib import Path

from .model import validate
from . import news
from .registry import Registry
from .store import Store

CITE_RE = re.compile(r"\[F:([^\]@\s]+)@([^\]\s]+)\]")
NEWS_CITE_RE = re.compile(r"\[N:([^\]]*)\]")
HEADINGS = ["## Facts", "## Inference", "## Missing", "## What would change this view"]
DISCLAIMER = "Not investment advice."


def _without_code(text: str) -> str:
    """When scanning citations, exclude fenced blocks and matching backtick spans."""
    lines = []
    fence = ""
    for line in text.splitlines(keepends=True):
        if fence:
            if re.fullmatch(r" {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}[ \t]*\n?", line):
                fence = ""
            lines.append("\n")
            continue
        opener = re.match(r" {0,3}(`{3,}|~{3,})(.*)$", line)
        if opener and (opener[1][0] != "`" or "`" not in opener[2]):
            fence = opener[1]
            lines.append("\n")
        else:
            lines.append(line)
    return re.sub(r"(?<!`)(`+)(?!`)[\s\S]*?(?<!`)\1(?!`)", " ", "".join(lines))


def check_facts(store: Store) -> list[str]:
    errors = []
    for coin in store.coins():
        for rec in store.load_latest(coin).values():
            errors += validate({k: v for k, v in rec.items() if k != "checked_at"}, store.registry)
        for rec in store.iter_history(coin):
            errors += validate(rec, store.registry)
    return errors


def _known_citations(store: Store, coin: str) -> set[tuple[str, str]]:
    keys = set()
    for rec in store.load_latest(coin).values():
        keys.add((rec["id"], rec["fetched_at"]))
    for rec in store.iter_history(coin):
        keys.add((rec["id"], rec["fetched_at"]))
    return keys


def check_analysis(path: Path, store: Store) -> list[str]:
    text = path.read_text()
    errors = []
    if DISCLAIMER not in text:
        errors.append(f"{path.name}: disclaimer missing")
    pos = -1
    for h in HEADINGS:
        i = text.find("\n" + h + "\n")
        if i < 0:
            errors.append(f"{path.name}: heading {h!r} missing")
        elif i < pos:
            errors.append(f"{path.name}: heading {h!r} out of order")
        else:
            pos = i
    cache: dict[str, set] = {}
    citation_text = _without_code(text)
    for fid, fetched in CITE_RE.findall(citation_text):
        parts = fid.split(".")
        if len(parts) < 3:
            errors.append(f"{path.name}: malformed citation {fid}")
            continue
        coin = parts[1]
        if coin not in cache:
            cache[coin] = _known_citations(store, coin)
        if (fid, fetched) not in cache[coin]:
            errors.append(f"{path.name}: citation {fid}@{fetched} not found")
    known_news = set()
    try:
        known_news = {rec.get("id") for rec in news.NewsStore(store.root).iter_records()
                      if isinstance(rec, dict) and isinstance(rec.get("id"), str)}
    except ValueError:
        pass  # Invalid JSON is reported by check_news.
    for nid in NEWS_CITE_RE.findall(citation_text):
        if not re.fullmatch(r"[a-z][a-z0-9_]*:[0-9a-f]{12}", nid):
            errors.append(f"{path.name}: malformed news citation {nid}")
        elif nid not in known_news:
            errors.append(f"{path.name}: news citation {nid} not found")
    return errors


def check_news(root: Path) -> list[str]:
    errors, known = [], set()
    for path in sorted((root / "data" / "news").glob("*.jsonl")):
        for number, line in enumerate(path.read_text().splitlines(), 1):
            try:
                record = json.loads(line)
            except ValueError:
                errors.append(f"{path.name}:{number}: invalid news JSON")
                continue
            errors += news.validate(record)
            nid = record.get("id") if isinstance(record, dict) else None
            if isinstance(nid, str):
                if nid in known:
                    errors.append(f"{nid}: duplicate news id")
                known.add(nid)
    return errors


def check_all(store: Store, root: Path) -> list[str]:
    errors = check_facts(store) + check_news(root)
    adir = root / "analysis"
    if adir.exists():
        for p in sorted(adir.rglob("*.md")):
            if p.name.startswith("TEMPLATE-"):
                continue
            errors += check_analysis(p, store)
    return errors
