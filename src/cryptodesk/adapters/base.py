from dataclasses import dataclass
from typing import Callable

import httpx

from ..model import Fact, missing, ok


class FetchError(Exception):
    pass


def _make_fetch(timeout: float, parse: Callable) -> Callable:
    client = httpx.Client(timeout=timeout, headers={"User-Agent": "cryptodesk"})

    def get(url: str, params: dict | None = None):
        try:
            r = client.get(url, params=params)
        except httpx.TimeoutException:
            raise FetchError("Timeout")
        except httpx.HTTPError as e:
            raise FetchError(f"request error {type(e).__name__}")
        if r.status_code != 200:
            raise FetchError(f"HTTP {r.status_code}")
        return parse(r)

    return get


def _json(r):
    try:
        return r.json()
    except ValueError:
        raise FetchError("invalid JSON")


def make_get(timeout: float = 20.0) -> Callable:
    return _make_fetch(timeout, _json)


def make_get_text(timeout: float = 20.0) -> Callable:
    return _make_fetch(timeout, lambda r: r.text)


@dataclass
class Spec:
    """One metric: id suffix, metric name, unit, extractor returning (value, as_of)."""

    metric: str
    unit: str
    extract: Callable
    id_infix: str = ""


@dataclass
class Endpoint:
    url: str
    params: dict
    specs: list[Spec]


def run_endpoint(get, ep: Endpoint, source: str, coin: str, fetched_at: str) -> list[Fact]:
    facts = []
    try:
        data = get(ep.url, ep.params)
        err = None
    except FetchError as e:
        data, err = None, str(e)
    for s in ep.specs:
        fid = f"{source}.{coin}.{s.id_infix}{s.metric}"
        reason = err
        value = as_of = None
        if err is None:
            try:
                value, as_of = s.extract(data)
                if value is None:
                    reason = "field absent in response"
            except (KeyError, IndexError, TypeError, ValueError):
                reason = "field absent in response"
        if reason:
            facts.append(missing(fid, coin, s.metric, s.unit, reason, fetched_at, source))
        else:
            facts.append(ok(fid, coin, s.metric, value, s.unit, as_of, fetched_at, source))
    return facts
