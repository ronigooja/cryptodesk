import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
STATUSES = ("ok", "missing")
FIELDS = ("id", "coin", "metric", "status", "value", "unit", "as_of", "fetched_at", "source", "reason")
COMPARED = ("status", "value", "as_of", "reason")


@dataclass(frozen=True)
class Fact:
    id: str
    coin: str
    metric: str
    status: str
    value: float | int | str | None
    unit: str
    as_of: str | None
    fetched_at: str
    source: str
    reason: str | None

    def to_dict(self) -> dict:
        return asdict(self)


def valid_time(s) -> bool:
    if not isinstance(s, str) or not TIME_RE.match(s):
        return False
    try:
        datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return True


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def ms_to_iso(ms: int | float | str) -> str:
    return iso(datetime.fromtimestamp(int(ms) / 1000, UTC))


def ok(id: str, coin: str, metric: str, value, unit: str, as_of: str | None, fetched_at: str, source: str) -> Fact:
    return Fact(id, coin, metric, "ok", value, unit, as_of, fetched_at, source, None)


def missing(id: str, coin: str, metric: str, unit: str, reason: str, fetched_at: str, source: str) -> Fact:
    return Fact(id, coin, metric, "missing", None, unit, None, fetched_at, source, reason)


def validate(d: dict, registry) -> list[str]:
    errors = []
    fid = d.get("id", "<no id>")
    for f in FIELDS:
        if f not in d:
            errors.append(f"{fid}: field {f} absent")
    if errors:
        return errors
    if d["status"] not in STATUSES:
        errors.append(f"{fid}: status {d['status']!r} invalid")
    if not registry.known(d["metric"]):
        errors.append(f"{fid}: metric {d['metric']!r} not registered")
    if not d["id"].startswith(f"{d['source']}.{d['coin']}.") or not d["id"].endswith("." + d["metric"]):
        errors.append(f"{fid}: id does not match source, coin, metric")
    if d["status"] == "ok":
        if d["value"] is None:
            errors.append(f"{fid}: ok with null value")
        if d["reason"] is not None:
            errors.append(f"{fid}: ok with reason")
    elif d["status"] == "missing":
        if d["value"] is not None:
            errors.append(f"{fid}: missing with value")
        if not d["reason"]:
            errors.append(f"{fid}: missing without reason")
    if not valid_time(d["fetched_at"]):
        errors.append(f"{fid}: fetched_at not UTC ISO")
    if d["as_of"] is not None and not valid_time(d["as_of"]):
        errors.append(f"{fid}: as_of not UTC ISO")
    if not d["unit"]:
        errors.append(f"{fid}: unit empty")
    return errors
