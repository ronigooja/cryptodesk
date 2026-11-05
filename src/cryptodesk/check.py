import re
from pathlib import Path

from .model import validate
from .registry import Registry
from .store import Store

CITE_RE = re.compile(r"\[F:([^\]@\s]+)@([^\]\s]+)\]")
HEADINGS = ["## Facts", "## Inference", "## Missing", "## What would change this view"]
DISCLAIMER = "Not investment advice."


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
    for fid, fetched in CITE_RE.findall(text):
        parts = fid.split(".")
        if len(parts) < 3:
            errors.append(f"{path.name}: malformed citation {fid}")
            continue
        coin = parts[1]
        if coin not in cache:
            cache[coin] = _known_citations(store, coin)
        if (fid, fetched) not in cache[coin]:
            errors.append(f"{path.name}: citation {fid}@{fetched} not found")
    return errors


def check_all(store: Store, root: Path) -> list[str]:
    errors = check_facts(store)
    adir = root / "analysis"
    if adir.exists():
        for p in sorted(adir.rglob("*.md")):
            if p.name.startswith("TEMPLATE-"):
                continue
            errors += check_analysis(p, store)
    return errors
