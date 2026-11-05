from datetime import UTC, datetime
from pathlib import Path

from .store import Store


def _stale(rec: dict, store: Store, now: datetime) -> bool:
    limit = store.registry.stale_hours(rec["metric"])
    if limit is None:
        return False
    checked = datetime.strptime(rec.get("checked_at", rec["fetched_at"]), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    return (now - checked).total_seconds() > limit * 3600


def render_coin(store: Store, coin: str, now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    latest = store.load_latest(coin)
    lines = [
        f"# {coin} facts",
        "",
        "Generated from `data/latest`. Do not edit.",
        "",
        "| Fact | Status | Value | Unit | as_of | fetched_at | Note |",
        "|---|---|---|---|---|---|---|",
    ]
    for fid in sorted(latest):
        r = latest[fid]
        note = r["reason"] or ""
        if _stale(r, store, now):
            note = (note + " stale").strip()
        value = "" if r["value"] is None else r["value"]
        lines.append(f"| `{fid}` | {r['status']} | {value} | {r['unit']} | {r['as_of'] or ''} | {r['fetched_at']} | {note} |")
    return "\n".join(lines) + "\n"


def render_all(store: Store, now: datetime | None = None) -> list[Path]:
    out = []
    for coin in store.coins():
        p = store.root / "coins" / coin / "notes.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(render_coin(store, coin, now))
        out.append(p)
    return out
