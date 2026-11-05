import re
from pathlib import Path


class Registry:
    def __init__(self, entries: list[tuple[re.Pattern, str, float, str]]):
        self._entries = entries

    def _find(self, metric: str):
        for pat, unit, stale, typ in self._entries:
            if pat.fullmatch(metric):
                return unit, stale, typ
        return None

    def known(self, metric: str) -> bool:
        return self._find(metric) is not None

    def is_snapshot(self, metric: str) -> bool:
        e = self._find(metric)
        return bool(e and e[2] == "snapshot")

    def stale_hours(self, metric: str) -> float | None:
        e = self._find(metric)
        return e[1] if e else None


def _pattern(name: str) -> re.Pattern:
    parts = re.split(r"<[a-z]+>", name)
    return re.compile("[a-z0-9]+".join(re.escape(p) for p in parts))


def parse(text: str) -> Registry:
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.strip() == "## Registry")
    entries = []
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 5 or cells[0] in ("Metric",) or set(cells[0]) <= {"-"}:
            continue
        m = re.fullmatch(r"(\d+(?:\.\d+)?) h", cells[3])
        if not m:
            raise ValueError(f"bad staleness {cells[3]!r} in row {cells[0]!r}")
        for name in re.findall(r"`([^`]+)`", cells[0]):
            entries.append((_pattern(name), cells[1], float(m.group(1)), cells[4]))
    if not entries:
        raise ValueError("no metrics parsed from registry")
    return Registry(entries)


def load(root: Path) -> Registry:
    return parse((root / "docs" / "metrics.md").read_text())
