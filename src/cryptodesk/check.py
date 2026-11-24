import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

from .model import validate
from . import daily, news
from .store import Store

CITE_RE = re.compile(r"\[F:([^\]@\s]+)@([^\]\s]+)\]")
NEWS_CITE_RE = re.compile(r"\[N:([^\]]*)\]")
DAILY_CITE_RE = re.compile(r"\[D:([^\]]*)\]")
HEADINGS = ["## Facts", "## Inference", "## Missing", "## What would change this view"]
DISCLAIMER = "Not investment advice."
SUPERSEDES_RE = re.compile(r"^[ \t]*(?:[-*+]\s+)?Supersedes:[ \t]*(.*)$")
LINK_DESTINATION = r'''(?:<([^<>\n]+)>|((?:\\.|\([^()\s]*\)|[^\s()\\<>])+))'''
INLINE_LINK_RE = re.compile(
    r"(?<!\\)\[(?:\\.|\[[^\[\]]*\]|[^\[\]\\])*\]\(\s*" + LINK_DESTINATION
    + r'''(?:\s+(?:"[^"]*"|'[^']*'|\([^()]*\)))?\s*\)'''
)
REFERENCE_LINK_RE = re.compile(r"(?m)^ {0,3}\[(?!\^)[^\]\n]+\]:[ \t]*" + LINK_DESTINATION)


def _without_code(text: str) -> str:
    """Exclude fenced blocks and matching backtick spans, preserving line numbers."""
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
    return re.sub(r"(?<!`)(`+)(?!`)[\s\S]*?(?<!`)\1(?!`)",
                  lambda match: " " + "\n" * match[0].count("\n"), "".join(lines))


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
    daily_store = daily.DailyStore(store.root)
    daily_cache = {}
    for citation in DAILY_CITE_RE.findall(citation_text):
        match = re.fullmatch(r"([a-z0-9_.]+)@(\d{4}-\d{2}-\d{2})(?:\.\.(\d{4}-\d{2}-\d{2}))?", citation)
        try:
            if not match:
                raise ValueError("malformed daily citation")
            series_id, start, end = match.groups()
            daily.valid_date(start)
            if end:
                daily.valid_date(end)
                if end < start:
                    raise ValueError("reversed daily range")
            if series_id not in daily_cache:
                daily_cache[series_id] = daily_store.load(series_id)
            if start not in daily_cache[series_id] or (end and end not in daily_cache[series_id]):
                errors.append(f"{path.name}: daily citation {citation} not found")
        except ValueError as exc:
            errors.append(f"{path.name}: malformed daily citation {citation}: {exc}")
    return errors


def check_daily(root: Path) -> list[str]:
    errors = []
    db = daily.DailyStore(root)
    for path in sorted((root / "data" / "daily").glob("*.csv")):
        try:
            db.load(path.stem)
        except (ValueError, OSError) as exc:
            errors.append(f"{path.name}: {exc}")
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


def check_analysis_files(store: Store, root: Path) -> list[str]:
    errors = []
    directory = root / "analysis"
    active = set(directory.glob("*.md"))
    archived = set((directory / "archive").glob("*.md"))
    files = {path for path in active | archived if path.is_file()}
    names = {path.name for path in files}
    for path in sorted(files):
        if path.name.startswith("TEMPLATE-"):
            continue
        errors += check_analysis(path, store)
        for number, line in enumerate(_without_code(path.read_text()).splitlines(), 1):
            if line.startswith("## "):
                break
            match = SUPERSEDES_RE.fullmatch(line)
            if not match:
                continue
            target = match[1].strip()
            if target == "none":
                continue
            location = f"{path.relative_to(root)}:{number}"
            if target not in names:
                errors.append(f"{location}: Supersedes target {target!r} not found in analysis/ or analysis/archive/")
            elif target != path.name and not target.startswith("TEMPLATE-") and directory / target in active:
                errors.append(f"{location}: superseded file analysis/{target} must be moved to analysis/archive/")
    return errors


def check_tracked_junk(root: Path) -> list[str]:
    if not (root / ".git").exists():
        return []
    try:
        result = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return []
    return [f"{path}: junk file is tracked by git" for path in result.stdout.decode(errors="surrogateescape").split("\0")
            if Path(path).name == ".DS_Store" or path.endswith((".bak", ".tmp", ".swp"))]


def check_doc_links(root: Path) -> list[str]:
    errors = []
    paths = [root / "README.md", root / "AGENTS.md", *sorted((root / "docs").rglob("*.md")),
             *sorted((root / "analysis").rglob("*.md"))]
    for path in paths:
        if not path.is_file():
            continue
        text = _without_code(path.read_text())
        for pattern in (INLINE_LINK_RE, REFERENCE_LINK_RE):
            for match in pattern.finditer(text):
                destination = match[1] or match[2]
                relative = destination.split("#", 1)[0]
                if not relative or relative.startswith("/") or re.match(r"^[a-z][a-z0-9+.-]*:", relative, re.I):
                    continue
                relative = unquote(re.sub(r"\\([^\w\s])", r"\1", relative))
                if not (path.parent / relative).exists():
                    number = text.count("\n", 0, match.start()) + 1
                    errors.append(f"{path.relative_to(root)}:{number}: broken local link {destination!r}")
    return errors


def check_all(store: Store, root: Path) -> list[str]:
    return (check_facts(store) + check_news(root) + check_daily(root) + check_analysis_files(store, root)
            + check_tracked_junk(root) + check_doc_links(root))
