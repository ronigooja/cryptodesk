"""Append-only, objectively resolvable daily-series forecasts."""

import fcntl
import hashlib
import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from . import daily, model
from .store import _dump

KEYS = {"id", "made_at", "analysis", "series", "op", "threshold", "date", "p"}
HASH_FIELDS = ("made_at", "analysis", "series", "op", "threshold", "date")


def forecast_id(record):
    # JSON array encoding provides unambiguous field boundaries.
    payload = json.dumps([record[k] for k in HASH_FIELDS], ensure_ascii=False, separators=(",", ":"))
    return "fc:" + hashlib.sha1(payload.encode()).hexdigest()[:12]


def validate(record, root):
    if not isinstance(record, dict) or set(record) != KEYS:
        return ["forecast must have exactly the required keys"]
    errors = []
    made = record["made_at"]
    try:
        if not isinstance(made, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", made):
            raise ValueError
        datetime.strptime(made, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        errors.append("invalid made_at")
        made = None
    analysis = record["analysis"]
    if (not isinstance(analysis, str) or not analysis or Path(analysis).name != analysis
            or not any((root / "analysis" / folder / analysis).is_file() for folder in ("", "archive"))):
        errors.append("analysis file missing or invalid")
    if not isinstance(record["series"], str) or record["series"] not in daily.SERIES:
        errors.append("unknown series")
    if record["op"] not in ("gt", "lt"):
        errors.append("invalid op")
    threshold = record["threshold"]
    try:
        if not isinstance(threshold, str) or not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", threshold):
            raise ValueError
        if not Decimal(threshold).is_finite():
            raise ValueError
    except (ValueError, InvalidOperation):
        errors.append("invalid threshold")
    try:
        if not isinstance(record["date"], str):
            raise ValueError
        day = daily.valid_date(record["date"])
        if made and day <= daily.valid_date(made[:10]):
            errors.append("date must be after made_at date")
    except ValueError:
        errors.append("invalid date")
    p = record["p"]
    try:
        if isinstance(p, bool) or not isinstance(p, (int, float, Decimal)):
            raise ValueError
        prob = Decimal(str(p))
        if not prob.is_finite() or not Decimal("0.01") <= prob <= Decimal("0.99") or prob.as_tuple().exponent < -4:
            raise ValueError
    except (ValueError, InvalidOperation):
        errors.append("invalid p")
    if not isinstance(record["id"], str) or record["id"] != forecast_id(record):
        errors.append("id mismatch")
    return errors


class ForecastStore:
    def __init__(self, root):
        self.root = root
        self.directory = root / "data" / "forecasts"

    def records(self):
        for path in sorted(self.directory.glob("*.jsonl")):
            for line in path.read_text().splitlines():
                yield json.loads(line)

    def add(self, analysis, series, op, threshold, date, p):
        # Validate input before creating even the lock directory.
        record = dict(made_at=model.iso(datetime.now(UTC)), analysis=analysis, series=series,
                      op=op, threshold=threshold, date=date, p=p)
        record["id"] = forecast_id(record)
        errors = validate(record, self.root)
        if errors:
            raise ValueError("; ".join(errors))
        self.directory.mkdir(parents=True, exist_ok=True)
        with (self.directory / ".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                # Capture write time under the lock, then revalidate the date.
                record["made_at"] = model.iso(datetime.now(UTC))
                record["id"] = forecast_id(record)
                errors = validate(record, self.root)
                if errors:
                    raise ValueError("; ".join(errors))
                if any(r["id"] == record["id"] for r in self.records()):
                    raise ValueError("duplicate forecast id")
                with (self.directory / (record["made_at"][:7] + ".jsonl")).open("a") as fh:
                    fh.write(_dump(record) + "\n")
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
        return record["id"]

    def score(self, today=None):
        today = today or datetime.now(UTC).date()
        rows, terms, by_analysis, cache = [], [], defaultdict(list), {}
        for record in self.records():
            errors = validate(record, self.root)
            if errors:
                raise ValueError("invalid forecast: " + "; ".join(errors))
            sid = record["series"]
            if sid not in cache:
                cache[sid] = daily.DailyStore(self.root).load(sid)
            value = cache[sid].get(record["date"])
            statement = f"{sid}({record['date']}) {record['op']} {record['threshold']}"
            if value is None:
                status = "open" if daily.valid_date(record["date"]) >= today else "unresolved"
                term = "-"
            else:
                outcome = (Decimal(value) > Decimal(record["threshold"]) if record["op"] == "gt"
                           else Decimal(value) < Decimal(record["threshold"]))
                status = "resolved " + ("yes" if outcome else "no")
                brier = (Decimal(str(record["p"])) - int(outcome)) ** 2
                terms.append(brier)
                by_analysis[record["analysis"]].append(brier)
                term = f"{brier:.8f}"
            rows.append(f"{record['id']} | {record['analysis']} | {statement} | {record['p']} | {status} | {term}")
        output = ["id | analysis | statement | p | status | Brier term", *rows]
        mean = f"{sum(terms) / len(terms):.8f}" if terms else "n/a"
        output.append(f"Resolved: {len(terms)} | mean Brier: {mean} | baseline: 0.25")
        for analysis, values in sorted(by_analysis.items()):
            output.append(f"{analysis}: mean Brier {sum(values) / len(values):.8f} (n={len(values)})")
        if len(terms) < 20:
            output.append("Too few resolved forecasts to judge calibration.")
        return "\n".join(output)


def configure(commands):
    parser = commands.add_parser("forecast")
    actions = parser.add_subparsers(dest="forecast_action", required=True)
    add = actions.add_parser("add")
    for name in ("analysis", "series", "op", "threshold", "date", "p"):
        add.add_argument("--" + name, required=True)
    actions.add_parser("score")


def run(args, root, parser):
    db = ForecastStore(root)
    try:
        if args.forecast_action == "score":
            print(db.score())
        else:
            try:
                probability = Decimal(args.p)
            except InvalidOperation:
                raise ValueError("invalid p") from None
            if not probability.is_finite() or probability.as_tuple().exponent < -4:
                raise ValueError("invalid p")
            print(db.add(args.analysis, args.series, args.op, args.threshold, args.date, float(probability)))
    except (ValueError, OSError, KeyError) as exc:
        parser.error(str(exc))
    return 0
