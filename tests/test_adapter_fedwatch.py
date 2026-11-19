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
    facts = fedwatch.collect(lambda: page, STARTED)
    assert facts[0].as_of == "2026-06-19T10:35:27Z"
    assert facts[1].status == "missing"


def test_missing_metadata_and_fetch_error():
    for page in (PAGE.replace("Fed Meeting", ""), PAGE.replace(" CT", ""), PAGE.replace("Now", "Later")):
        facts = fedwatch.collect(lambda: page, STARTED)
        assert len(facts) == 1 and facts[0].status == "missing"
    def fail():
        raise FetchError("HTTP 403")
    assert fedwatch.collect(fail, STARTED)[0].reason == "HTTP 403"
