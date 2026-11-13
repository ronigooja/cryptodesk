import json

import pytest

from cryptodesk import cli, news
from cryptodesk.adapters.base import FetchError
from cryptodesk.adapters import base
from cryptodesk.check import check_all, check_analysis, check_news

NOW = "2026-11-13T08:00:00Z"


def rss(date="Fri, 13 Nov 2026 06:00:00 +0000", title="News", url="https://example.org/a", tag="pubDate"):
    return (f'<rss xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><item>'
            f'<title>{title}</title><link>{url}</link><{tag}>{date}</{tag}>'
            '<description>DO NOT STORE</description></item></channel></rss>')


def record():
    return news.parse_feed(rss(), "coindesk", NOW)[0][0]


@pytest.mark.parametrize("date,tag,expected", [
    ("Fri, 13 Nov 2026 06:00:00 +0000", "pubDate", "2026-11-13T06:00:00Z"),
    ("2026-11-13T06:00:00Z", "dc:date", "2026-11-13T06:00:00Z"),
    ("2026-11-13T06:00:00-05:00", "dc:date", "2026-11-13T11:00:00Z"),
    ("Tue, 10 Nov 2026 11:15:35 -0500", "pubDate", "2026-11-10T16:15:35Z"),
    ("2026-07-13T06:00:00-04:00", "dc:date", "2026-07-13T10:00:00Z"),
])
def test_dates_bom(date, tag, expected):
    items, skipped = news.parse_feed("\ufeff" + rss(date, tag=tag), "sec", NOW)
    assert skipped == 0
    assert items[0]["published_at"] == expected
    assert set(items[0]) == news.FIELDS


@pytest.mark.parametrize("date,url", [("", "https://example.org/a"), ("invalid", "https://example.org/a"),
                                           ("2026-11-13T06:00:00", "https://example.org/a"),
                                           (NOW, ""), (NOW, "http://example.org/a")])
def test_invalid_item_skipped(date, url):
    assert news.parse_feed(rss(date, url=url), "sec", NOW) == ([], 1)


def test_title_sanitizing_and_cap():
    assert news.clean_title(" \nTitle\t words\x00\u200b ") == "Title words"
    item = news.parse_feed(rss(title=" \n" + "x" * 400), "sec", NOW)[0][0]
    assert item["title"] == "x" * 300
    assert news.validate(news.parse_feed(rss(title="x" * 299 + " more"), "sec", NOW)[0][0]) == []


def test_namespace_and_id_stability():
    first = record()
    text = rss(url="https://EXAMPLE.org/a?utm_source=rss#top").replace("<rss ", '<rss xmlns="urn:rss" ')
    second = news.parse_feed(text, "coindesk", NOW)[0][0]
    assert first == second
    assert first["id"] == news.item_id("coindesk", "https://example.org/a")


def test_dedupe_write_once_across_months(tmp_path):
    db = news.NewsStore(tmp_path)
    item = record()
    assert db.apply([item, item], NOW, [])["unchanged"] == 1
    old = tmp_path / "data/news/2026-11.jsonl"
    original = old.read_bytes()
    other = news.parse_feed(rss("2026-10-31T23:00:00Z", url="https://example.org/b"), "sec", NOW)[0][0]
    run = db.apply([item | {"title": "Edited"}, other], "2026-12-01T00:00:00Z", [])
    assert (run["changed"], run["unchanged"]) == (1, 1)
    assert old.read_bytes() == original
    assert (tmp_path / "data/news/2026-10.jsonl").exists()
    assert len(list(db.iter_records())) == 2


def test_feed_failure_isolation():
    def get(url, params):
        if url == news.FEEDS["sec"]:
            raise FetchError("HTTP 403")
        if url == news.FEEDS["fed_press"]:
            return "bad XML"
        return rss()
    items, errors, skipped = news.collect(get, NOW)
    assert len(items) == 5
    assert errors == ["fed_press: invalid RSS XML", "sec: HTTP 403"]
    assert skipped == 0


def test_text_fetch_user_agent_and_timeout(monkeypatch):
    class Client:
        headers = {}

        def __init__(self, **kwargs):
            assert kwargs["timeout"] == 20.0

        def get(self, url, params):
            assert self.headers["User-Agent"] == "Mozilla/5.0 (cryptodesk)"
            return base.httpx.Response(200, text=rss())

    monkeypatch.setattr(base.httpx, "Client", Client)
    assert base.make_get_text()(news.FEEDS["sec"], {}) == rss()


def test_checker_valid_and_duplicate(tmp_path):
    news.NewsStore(tmp_path).apply([record()], NOW, [])
    assert check_news(tmp_path) == []
    path = tmp_path / "data/news/2026-11.jsonl"
    with path.open("a") as fh:
        fh.write(path.read_text())
    assert any("duplicate" in error for error in check_news(tmp_path))


@pytest.mark.parametrize("change", [
    {"published_at": "2026-11-13T00:00:00-05:00"}, {"fetched_at": "2026-99-01T00:00:00Z"},
    {"url": "http://example.org"}, {"title": "bad\nline"}, {"id": "bad"},
    {"summary": "forbidden"}, {"source": None},
])
def test_checker_rejects_invalid_metadata(tmp_path, change):
    path = tmp_path / "data/news/2026-11.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(record() | change) + "\n")
    assert check_news(tmp_path)


def test_checker_missing_fields_bad_json(tmp_path):
    path = tmp_path / "data/news/2026-11.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text('{}\nnot json\n[]\n')
    assert len(check_news(tmp_path)) >= 3


def test_news_citations(store, tmp_path):
    item = record()
    news.NewsStore(tmp_path).apply([item], NOW, [])
    path = tmp_path / "analysis.md"
    base = ("Not investment advice.\n\n## Facts\n\n## Catalysts and news\n"
            f"Reported [N:{item['id']}]\n\n## Inference\n\n## Missing\n\n"
            "## What would change this view\n")
    path.write_text(base)
    assert check_analysis(path, store) == []
    path.write_text(base.replace(item["id"], "sec:000000000000"))
    assert any("not found" in error for error in check_analysis(path, store))
    path.write_text(base.replace(item["id"], item["id"] + "@" + NOW))
    assert any("malformed news" in error for error in check_analysis(path, store))
    assert check_all(store, tmp_path) == []


def test_cli_news_end_to_end(store, monkeypatch, capsys):
    monkeypatch.setenv("CRYPTODESK_ROOT", str(store.root))
    monkeypatch.setattr(cli.registry, "load", lambda root: store.registry)
    monkeypatch.setattr(cli, "make_get_text_fn", lambda: lambda url, params: rss())
    assert cli.main(["collect", "news"]) == 0
    assert "facts=7 changed=7 unchanged=0 missing=0" in capsys.readouterr().out
    assert cli.main(["collect", "news"]) == 0
    assert "facts=7 changed=0 unchanged=7 missing=0" in capsys.readouterr().out
    assert cli.main(["check"]) == 0
    assert not (store.root / "data/latest").exists()


@pytest.mark.parametrize("text", ["<rss><channel/></rss>", rss(date=""), "bad XML"])
def test_cli_zero_valid_items_exits_one(store, monkeypatch, text):
    monkeypatch.setenv("CRYPTODESK_ROOT", str(store.root))
    monkeypatch.setattr(cli.registry, "load", lambda root: store.registry)
    monkeypatch.setattr(cli, "make_get_text_fn", lambda: lambda url, params: text)
    assert cli.main(["collect", "news"]) == 1
    run = json.loads(next((store.root / "runs").glob("*.jsonl")).read_text())
    assert run["facts"] == 0
    assert run["skipped"] == (7 if text == rss(date="") else 0)
    assert run["missing"] == (7 if text == "bad XML" else 0)
