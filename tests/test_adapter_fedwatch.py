from pathlib import Path

from cryptodesk import model, registry
from cryptodesk.adapters import fedwatch
from cryptodesk.adapters.base import FetchError

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "tests/fixtures/fedwatch.html").read_text()
REG = registry.parse((ROOT / "docs/metrics.md").read_text())
STARTED = "2026-11-19T12:00:00Z"


def test_outcomes_and_missing_cell():
    facts = fedwatch.collect(lambda: PAGE, STARTED)
    assert [f.value for f in facts] == [0.0, 92.7, None]
    assert facts[0].as_of == "2026-11-19T11:35:27Z"
    assert facts[1].metric == "fedwatch_probability_20261209b400x425"
    assert facts[2].status == "missing"
    assert all(not model.validate(f.to_dict(), REG) for f in facts)


def test_hidden_row_without_now_to_1week_values_is_skipped():
    page = PAGE.replace("<tr><td colspan=\"5\">",
                        "<tr><td>125-150</td><td></td><td></td><td></td><td>0.0%</td></tr><tr><td colspan=\"5\">")
    assert [f.metric for f in fedwatch.collect(lambda: page, STARTED)] == [
        f.metric for f in fedwatch.collect(lambda: PAGE, STARTED)]


def test_dst_and_invalid_cell():
    page = PAGE.replace("19 Nov 2026", "19 Jun 2026").replace("92.7%", "invalid")
    facts = fedwatch.collect(lambda: page, "2026-06-19T12:00:00Z")
    assert facts[0].as_of == "2026-06-19T10:35:27Z"
    assert facts[1].status == "missing"


def _as_of(wall, started):
    page = PAGE.replace("19 Nov 2026 05:35:27", wall)
    return fedwatch.collect(lambda: page, started)[0].as_of


def test_twelve_hour_clock_without_am_pm():
    assert _as_of("19 Nov 2026 04:31:34", "2026-11-19T22:45:19Z") == "2026-11-19T22:31:34Z"
    assert _as_of("26 Nov 2026 12:23:56", "2026-11-26T06:36:00Z") == "2026-11-26T06:23:56Z"
    assert _as_of("19 Nov 2026 05:45:29", "2026-11-19T11:55:42Z") == "2026-11-19T11:45:29Z"
    assert _as_of("19 Nov 2026 16:31:34", "2026-11-19T22:45:19Z") == "2026-11-19T22:31:34Z"
    assert _as_of("19 Nov 2026 00:23:56", "2026-11-19T06:36:00Z") == "2026-11-19T06:23:56Z"


def test_ambiguous_or_future_time_is_missing():
    for wall, started in (("19 Nov 2026 05:35:27", "2026-11-20T12:00:00Z"),
                          ("19 Nov 2026 11:35:27", "2026-11-19T10:00:00Z"),
                          ("19 Nov 2026 16:35:27", "2026-11-19T10:00:00Z")):
        page = PAGE.replace("19 Nov 2026 05:35:27", wall)
        facts = fedwatch.collect(lambda: page, started)
        assert len(facts) == 1 and facts[0].status == "missing"


def test_missing_metadata_and_fetch_error():
    for page in (PAGE.replace("Fed Meeting", ""), PAGE.replace(" CT", ""), PAGE.replace("Now", "Later")):
        facts = fedwatch.collect(lambda: page, STARTED)
        assert len(facts) == 1 and facts[0].status == "missing"
    def fail():
        raise FetchError("HTTP 403")
    assert fedwatch.collect(fail, STARTED)[0].reason == "HTTP 403"
