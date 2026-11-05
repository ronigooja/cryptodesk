import json
import os
from pathlib import Path

from .model import COMPARED, Fact, iso
from .registry import Registry


def find_root(start: Path | None = None) -> Path:
    env = os.environ.get("CRYPTODESK_ROOT")
    if env:
        return Path(env)
    p = (start or Path.cwd()).resolve()
    for d in [p, *p.parents]:
        if (d / "AGENTS.md").exists() and (d / "docs" / "metrics.md").exists():
            return d
    raise FileNotFoundError("repo root not found; set CRYPTODESK_ROOT")


def _dump(obj, indent=None) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=indent)


class Store:
    def __init__(self, root: Path, registry: Registry):
        self.root = root
        self.registry = registry

    def latest_path(self, coin: str) -> Path:
        return self.root / "data" / "latest" / f"{coin}.json"

    def history_path(self, month: str, coin: str) -> Path:
        return self.root / "data" / "facts" / month / f"{coin}.jsonl"

    def load_latest(self, coin: str) -> dict:
        p = self.latest_path(coin)
        return json.loads(p.read_text()) if p.exists() else {}

    def iter_history(self, coin: str):
        base = self.root / "data" / "facts"
        if not base.exists():
            return
        for p in sorted(base.glob(f"*/{coin}.jsonl")):
            for line in p.read_text().splitlines():
                if line.strip():
                    yield json.loads(line)

    def coins(self) -> list[str]:
        d = self.root / "data" / "latest"
        return sorted(p.stem for p in d.glob("*.json")) if d.exists() else []

    def apply(self, facts: list[Fact], group: str, started: str) -> dict:
        month = started[:7]
        by_coin: dict[str, list[Fact]] = {}
        for f in facts:
            by_coin.setdefault(f.coin, []).append(f)
        changed = unchanged = 0
        for coin, items in by_coin.items():
            latest = self.load_latest(coin)
            appended = []
            for f in items:
                rec = f.to_dict()
                prev = latest.get(f.id)
                same = prev is not None and all(prev[k] == rec[k] for k in COMPARED)
                if same and not self.registry.is_snapshot(f.metric):
                    prev["checked_at"] = f.fetched_at
                    unchanged += 1
                    continue
                rec["checked_at"] = f.fetched_at
                latest[f.id] = rec
                appended.append(rec)
                changed += 1
            if appended:
                hp = self.history_path(month, coin)
                hp.parent.mkdir(parents=True, exist_ok=True)
                with hp.open("a") as fh:
                    for rec in appended:
                        h = {k: v for k, v in rec.items() if k != "checked_at"}
                        fh.write(_dump(h) + "\n")
            lp = self.latest_path(coin)
            lp.parent.mkdir(parents=True, exist_ok=True)
            lp.write_text(_dump(latest, indent=1) + "\n")
        missing = [f for f in facts if f.status == "missing"]
        errors = sorted({f"{f.source}: {f.reason}" for f in missing})
        run = {
            "started": started,
            "group": group,
            "facts": len(facts),
            "changed": changed,
            "unchanged": unchanged,
            "missing": len(missing),
            "errors": errors,
        }
        rp = self.root / "runs" / f"{month}.jsonl"
        rp.parent.mkdir(parents=True, exist_ok=True)
        with rp.open("a") as fh:
            fh.write(_dump(run) + "\n")
        return run
