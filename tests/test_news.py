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


@pytest.mark.parametrize("text,reason", [
    ('<!ENTITY title "expanded">' + rss(), "unsafe XML"),
    ('<!entity title "expanded">' + rss(), "unsafe XML"),
    ('<!doctype rss>' + rss(), "unsafe XML"),
    ('<!DOCTYPE lolz [<!ENTITY lol "lol">' + ''.join(
        f'<!ENTITY lol{i} "' + (f'&lol{i - 1};' if i > 1 else '&lol;') * 10 + '">'
        for i in range(1, 10)) + ']><rss>&lol9;</rss>', "unsafe XML"),
    (" " * 2_000_001, "feed too large"),
])
def test_unsafe_or_large_feed_never_parsed_or_stored(tmp_path, monkeypatch, text, reason):
    monkeypatch.setattr(news, "FEEDS", {"sec": "https://example.org/rss"})

    def forbidden_parse(*args, **kwargs):
        pytest.fail("rejected feed reached XML parser")

    monkeypatch.setattr(news.ET, "fromstring", forbidden_parse)
    items, errors, skipped = news.collect(lambda *_: text, NOW)
    assert (items, errors, skipped) == ([], [f"sec: {reason}"], 0)
    news.NewsStore(tmp_path).apply(items, NOW, errors, skipped)
    assert not (tmp_path / "data/news").exists()


def test_feed_size_limit_inclusive():
    text = rss()
    assert len(news.parse_feed(text + " " * (2_000_000 - len(text)), "sec", NOW)[0]) == 1


def test_million_character_title_capped_before_sanitizing(monkeypatch):
    category = news.unicodedata.category
    inspected = []

    def tracked_category(char):
        inspected.append(char)
        return category(char)

    monkeypatch.setattr(news.unicodedata, "category", tracked_category)
    title = " " * 2000 + "x" * 998_000
    item = news.parse_feed(rss(title=title), "sec", NOW)[0][0]
    assert item["title"] == ""
    assert len(inspected) <= 2000


@pytest.mark.parametrize("tracking", ["fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src", "cmpid", "taid"])
def test_tracking_url_ids(tracking):
    canonical = news.canonical_url(f"https://example.org/a/?{tracking}=x")
    assert news.item_id("sec", canonical) == news.item_id("sec", "https://example.org/a")


def test_canonical_path_and_query_id_policy():
    def identity(suffix):
        return news.item_id("sec", news.canonical_url("https://example.org" + suffix))

    assert identity("/a") == identity("/a/") == identity("/a?fbclid=x")
    assert identity("/a?utm_source=x&id=7") == identity("/a?id=7")
    assert identity("/a?id=7") != identity("/a")
    assert identity("/a//") != identity("/a/")
    assert news.canonical_url("https://example.org/") == "https://example.org/"
    with pytest.raises(ValueError):
        news.canonical_url("http://example.org/a")


@pytest.mark.parametrize("stored", [False, True])
def test_id_collision_reported_once_and_not_written(tmp_path, monkeypatch, stored):
    class ConstantHash:
        def hexdigest(self):
            return "0" * 40

    monkeypatch.setattr(news.hashlib, "sha1", lambda _: ConstantHash())
    first = record()
    second = news.parse_feed(rss(url="https://example.org/b"), "coindesk", NOW)[0][0]
    db = news.NewsStore(tmp_path)
    if stored:
        db.apply([first], NOW, [])
    run = db.apply(([first] if not stored else []) + [second, second], NOW, [])
    assert run["skipped"] == 2
    assert run["unchanged"] == 0
    assert run["errors"] == ["coindesk: id collision"]
    assert list(db.iter_records()) == [first]
