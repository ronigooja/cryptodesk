import json
from dataclasses import replace

import pytest

from cryptodesk.check import check_all, check_analysis, check_facts


@pytest.fixture
def analysis_file(tmp_path, store, fact):
    store.apply([fact], "core", fact.fetched_at)
    path = tmp_path / "analysis" / "2026-11-06T1001Z-btc.md"
    path.parent.mkdir()
    path.write_text(
        "# BTC analysis\n\n"
        "Generated: 2026-11-06T10:01:00Z / 2026-11-06 18:01 UTC+8\n"
        "Scope: BTC\nSupersedes: none\nNot investment advice.\n\n"
        f"## Facts\nSpot price is 70000 USD [F:{fact.id}@{fact.fetched_at}]\n\n"
        f"## Inference\nNo directional view; based on: [F:{fact.id}@{fact.fetched_at}]\n\n"
        "## Missing\nNo source comparison.\n\n"
        "## What would change this view\nAdditional independently sourced observations.\n"
    )
    return path


def test_check_facts_accepts_temporary_store(store, fact):
    store.apply([fact], "core", fact.fetched_at)
    assert check_facts(store) == []


@pytest.mark.parametrize("location", ["latest", "history"])
def test_check_facts_rejects_invalid_latest_or_history(store, fact, location):
    store.apply([fact], "core", fact.fetched_at)
    invalid = fact.to_dict() | {"value": None}
    if location == "latest":
        store.latest_path("btc").write_text(json.dumps({fact.id: invalid}))
    else:
        store.history_path("2026-11", "btc").write_text(json.dumps(invalid) + "\n")
    assert check_facts(store) == [f"{fact.id}: ok with null value"]


def test_check_analysis_accepts_correct_file(analysis_file, store):
    assert check_analysis(analysis_file, store) == []
    assert check_all(store, store.root) == []


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("## Missing\n", "## Unavailable\n", "heading '## Missing' missing"),
        ("Not investment advice.", "", "disclaimer missing"),
        ("@2026-11-06T10:01:00Z]", "@2026-11-06T09:01:00Z]", "not found"),
        ("## Inference\n", "## Missing\n", "out of order"),
    ],
)
def test_check_analysis_rejects_invalid_file(analysis_file, store, old, new, message):
    text = analysis_file.read_text()
    if message == "out of order":
        text = text.replace("## Missing\n", "## Inference\n").replace(old, new, 1)
    else:
        text = text.replace(old, new)
    analysis_file.write_text(text)
    assert any(message in error for error in check_analysis(analysis_file, store))


def test_check_analysis_resolves_citation_from_history(analysis_file, store, fact):
    later = replace(fact, value=71000, fetched_at="2026-11-06T11:01:00Z")
    store.apply([later], "core", later.fetched_at)
    assert check_analysis(analysis_file, store) == []


def test_check_analysis_resolves_pruned_option_citation(analysis_file, store, fact):
    option = replace(fact, id="deribit.btc.opt.2026-11-06.max_pain", source="deribit", metric="max_pain")
    store.apply([option], "options", fact.fetched_at)
    analysis_file.write_text(analysis_file.read_text().replace(fact.id, option.id))
    store.apply([], "macro", "2026-11-07T00:00:00Z")
    assert option.id not in store.load_latest("btc")
    assert check_analysis(analysis_file, store) == []


def test_check_analysis_rejects_malformed_citation(analysis_file, store, fact):
    analysis_file.write_text(analysis_file.read_text().replace(fact.id, "invalid"))
    assert any("malformed citation invalid" in error for error in check_analysis(analysis_file, store))


def test_check_all_ignores_templates_but_checks_nested_analysis(tmp_path, store):
    directory = tmp_path / "analysis" / "2026-11"
    directory.mkdir(parents=True)
    (directory / "TEMPLATE-major.md").write_text("placeholder")
    assert check_all(store, tmp_path) == []
    (directory / "broken.md").write_text("incomplete")
    assert any("broken.md: disclaimer missing" in error for error in check_all(store, tmp_path))
