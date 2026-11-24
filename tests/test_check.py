import json
import shutil
import subprocess
from dataclasses import replace

import pytest

from cryptodesk.check import check_all, check_analysis, check_facts


def test_check_all_includes_forecast_errors(tmp_path, store):
    directory = tmp_path / "data" / "forecasts"
    directory.mkdir(parents=True)
    (directory / "2025-01.jsonl").write_text("not json\n")
    assert check_all(store, tmp_path) == ["data/forecasts/2025-01.jsonl:1: invalid forecast JSON"]


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


def test_check_all_ignores_templates_but_checks_archived_analysis(tmp_path, store):
    directory = tmp_path / "analysis" / "archive"
    directory.mkdir(parents=True)
    (directory / "TEMPLATE-major.md").write_text("placeholder")
    assert check_all(store, tmp_path) == []
    (directory / "broken.md").write_text("incomplete")
    assert any("broken.md: disclaimer missing" in error for error in check_all(store, tmp_path))


@pytest.mark.parametrize("from_archive", [False, True])
def test_superseded_analysis_must_be_archived(analysis_file, store, from_archive):
    directory = analysis_file.parent
    archive = directory / "archive"
    archive.mkdir()
    successor = (archive if from_archive else directory) / "successor.md"
    successor.write_text(analysis_file.read_text().replace("Supersedes: none", f"- Supersedes: {analysis_file.name}"))
    assert check_all(store, store.root) == [
        f"{successor.relative_to(store.root)}:5: superseded file analysis/{analysis_file.name} "
        "must be moved to analysis/archive/"
    ]

    archived = analysis_file.rename(archive / analysis_file.name)
    assert check_all(store, store.root) == []
    archived.write_text(archived.read_text().replace("@2026-11-06T10:01:00Z]", "@2026-11-06T09:01:00Z]"))
    assert any(archived.name in error and "citation" in error for error in check_all(store, store.root))


@pytest.mark.parametrize("from_archive", [False, True])
def test_supersedes_target_must_exist(analysis_file, store, from_archive):
    if from_archive:
        archive = analysis_file.parent / "archive"
        archive.mkdir()
        analysis_file = analysis_file.rename(archive / analysis_file.name)
    analysis_file.write_text(analysis_file.read_text().replace("Supersedes: none", "Supersedes: missing.md"))
    assert check_all(store, store.root) == [
        f"{analysis_file.relative_to(store.root)}:5: Supersedes target 'missing.md' not found in "
        "analysis/ or analysis/archive/"
    ]


def test_check_only_rejects_tracked_junk(tmp_path, store, monkeypatch):
    if not shutil.which("git"):
        pytest.skip("git unavailable")
    tracked = [".DS_Store", "data/has space.bak", "data/file.swp", "data/temp.tmp"]
    (tmp_path / "data").mkdir()
    for relative in [*tracked, "data/untracked.tmp", "data/kept.md"]:
        (tmp_path / relative).touch()
    assert check_all(store, tmp_path) == []

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-f", "--", *tracked, "data/kept.md"],
                   cwd=tmp_path, check=True, capture_output=True)
    assert set(check_all(store, tmp_path)) == {f"{path}: junk file is tracked by git" for path in tracked}

    monkeypatch.setenv("PATH", str(tmp_path / "no-bin"))
    assert check_all(store, tmp_path) == []


def test_check_doc_links_resolve_relative_paths_and_ignore_code(tmp_path, store):
    nested = tmp_path / "docs" / "nested"
    nested.mkdir(parents=True)
    (nested / "with space.md").touch()
    (nested / "with(parens).md").touch()
    (tmp_path / "README.md").write_text(
        '[dir](docs/nested/) [path](docs/nested/with%20space.md#section "Title")\n'
        '[anchor](#local) [external](https://example.org/missing) [mail](mailto:user@example.org)\n'
        '`[example](missing.md)`\n'
        '```markdown\n[example](missing.md)\n```\n'
        '``multiline\n[example](missing.md)``\n'
        '[missing](missing.md#section)\n'
    )
    (tmp_path / "AGENTS.md").write_text('[`code label`](README.md) [missing](not-found.md)\n')
    (nested / "guide.md").write_text(
        '[root](../../README.md) [literal spaces](<with space.md>) [parens](with(parens).md)\n'
        '[missing][ref]\n'
        '[ref]: missing-target.md\n'
    )
    (tmp_path / "outside.md").write_text('[not in scope](missing.md)\n')
    assert check_all(store, tmp_path) == [
        "README.md:9: broken local link 'missing.md#section'",
        "AGENTS.md:1: broken local link 'not-found.md'",
        "docs/nested/guide.md:3: broken local link 'missing-target.md'",
    ]


@pytest.mark.parametrize("code", [
    "`[N:bad] [F:invalid@now]`",
    "``[N:bad] `[F:invalid@now]``",
    "```markdown\n[N:bad] [F:invalid@now]\n```",
    "~~~markdown\n[N:bad] [F:invalid@now]\n~~~",
    "````\n```\n[N:bad] [F:invalid@now]\n````",
    "```\n[N:bad] [F:invalid@now]\n",
])
def test_citations_ignore_markdown_code(analysis_file, store, code):
    analysis_file.write_text(analysis_file.read_text() + "\n" + code + "\n")
    assert check_analysis(analysis_file, store) == []


def test_unclosed_news_citation_ignored(analysis_file, store):
    analysis_file.write_text(analysis_file.read_text() + "\n[N:unfinished")
    assert check_analysis(analysis_file, store) == []


@pytest.mark.parametrize("citation", ["[N:bad]", "[N:]", "[F:invalid@now]"])
def test_closed_malformed_citation_fails(analysis_file, store, citation):
    analysis_file.write_text(analysis_file.read_text() + "\n" + citation)
    assert any("malformed" in error for error in check_analysis(analysis_file, store))


def test_citations_after_code_still_checked(analysis_file, store):
    analysis_file.write_text(analysis_file.read_text() + "\n```\n[N:ignored]\n```\n[N:bad]")
    errors = check_analysis(analysis_file, store)
    assert len(errors) == 1
    assert "malformed news citation bad" in errors[0]
