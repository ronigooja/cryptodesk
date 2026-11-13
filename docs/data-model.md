# Data model

## Fact record

One JSON object per observed value.

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Unique fact ID, see [IDs](#ids) |
| `coin` | string | Ticker or `macro` |
| `metric` | string | Metric name registered in [metrics.md](metrics.md) |
| `status` | string | `ok` or `missing`, see [States](#states) |
| `value` | number, string, or null | Observed value; null only when `missing` |
| `unit` | string | From the metric registry |
| `as_of` | string or null | UTC time the value describes, from the source payload when given |
| `fetched_at` | string | UTC time the run started |
| `checked_at` | string | Latest records only: UTC time the value was last re-confirmed; absent from history lines |
| `source` | string | Source key from [sources.md](sources.md) |
| `reason` | string or null | Why missing; null when `ok` |

The request URL is not stored per fact, to limit repository growth. [sources.md](sources.md) is the sole source registry.

## IDs

| Kind | Pattern | Example |
|---|---|---|
| Market | `<source>.<coin>.<metric>` | `binance.btc.funding_rate_8h` |
| Option expiry | `<source>.<coin>.opt.<YYYY-MM-DD>.<metric>` | `deribit.btc.opt.2026-11-27.max_pain` |
| Macro | `<source>.macro.<metric>` | `treasury.macro.us10y_yield` |

When multiple sources report a metric, keep separate facts; never merge or average them. Analysis comparison rules are in [analysis.md](analysis.md#rules).

## States

| State | Meaning | Stored |
|---|---|---|
| `ok` | Value obtained | yes |
| `missing` | Should exist but could not be obtained | yes, with `reason` |
| `n/a` | The coin has no such market or module | no record; declared by absence from `profile.toml` |

When a value is unavailable, use `missing` with a short reason: `HTTP <code>`, `Timeout`, `field absent in response`, `not published`, `<ENV_NAME> not set`, `requires paid plan`, or `requires approval`. Never substitute an estimate or another source's value. Source placeholders (a dash or `N/A`) are `missing`, not zero; a true zero is `ok` with value 0. Proxy behavior is defined in [Known gaps](sources.md#known-gaps).

## Time

- Store UTC `YYYY-MM-DDTHH:MM:SSZ`.
- `as_of` null means the source gave no time; analysis states that caveat.
- Staleness uses `checked_at` in latest records (falling back to `fetched_at` for records without it). Observation time remains `as_of`, or `fetched_at` when unavailable; confirmation does not move the observation time.
- Daily macro series (Treasury, NY Fed) use the observation date at `00:00:00Z`.
- A source's local-time claims (for example "ET") are converted at ingest; DST must not be hand-computed. Convert with a timezone library.

## Storage

| Path | Behavior |
|---|---|
| `data/latest/<coin>.json` | Map of fact ID to latest record; refresh `checked_at` even when unchanged. Expired option series are removed on every run. |
| `data/facts/<YYYY-MM>/<coin>.jsonl` | Append when `status`, `value`, `as_of`, or `reason` differs from latest; no `checked_at`. Never edited, including expired options. |
| `runs/<YYYY-MM>.jsonl` | One line per run: start time, group, counts (facts, changed, unchanged, missing), error strings. |

Raw HTTP responses are not committed. For diagnosis, upload as a failure-only workflow artifact with short retention ([schedule.md](schedule.md#actions)).

When evaluating storage growth, measure actual size and record the result in [decisions.md](decisions.md); no size estimate is validated.

## Daily series

Latest facts retain one value per ID, not a multi-year observation history. Daily observations therefore live separately in `data/daily/<series_id>.csv`: header `date,value`, finite numeric values, one unique `YYYY-MM-DD` date per row, ascending. IDs match `[a-z0-9_.]+`.

Daily JSON decimals are decoded exactly and stored in fixed-point form with trailing zeros preserved; writers hold an exclusive `data/daily/.lock` across load/merge/replace.

When collecting daily series, add only previously absent dates; never change an existing row. Late values may be inserted in date order. When a source changes an existing value, retain the stored value and record a conflict (series, date, stored and received values) in the run. Missing dates stay absent; null, empty, `.`, and `N/A` values are skipped, never zero or interpolated.

| Series ID | Definition | Unit / day definition |
|---|---|---|
| `price_close.binance.btc`, `price_close.binance.eth` | BTCUSDT / ETHUSDT spot daily kline close (index 4) | USDT; UTC 00:00 through next UTC 00:00 |
| `price_close.coinbase.btc`, `price_close.coinbase.eth` | BTC-USD / ETH-USD daily candle close (index 4) | USD; UTC 00:00 through next UTC 00:00 |
| `mvrv.coinmetrics.btc`, `mvrv.coinmetrics.eth` | Community `CapMVRVCur`, frequency `1d` | ratio; source UTC observation date |
| `us2y_yield.treasury`, `us10y_yield.treasury` | Daily par yield curve, `2 Yr` / `10 Yr` columns | percent; source business date, not a UTC candle close |
| `fed_funds_effective.nyfed` | EFFR `refRates[].percentRate` | percent; source `effectiveDate`, not publication date |
| `stablecoin_supply_usd.defillama` | Chart `totalCirculatingUSD.peggedUSD` | USD; Unix timestamp converted to UTC date; snapshot cutoff unverified |

When collecting, exclude today UTC and future dates for every series; price candles are incomplete until the next UTC midnight. Binance quotes USDT and Coinbase quotes USD: keep both separate, never average or merge them. The live fact `stablecoin_supply_usd` is a per-asset sum; the daily series is the chart total. They are not interchangeable ([observed difference](sources.md#known-gaps)).

`cryptodesk backfill` starts at 2025-01-01 by default; `--since YYYY-MM-DD` changes the lower bound and repeatable `--series <id>` selects series. Binance pages in 1,000-day windows; Coinbase uses 299-day windows within its 300-candle limit, excluding the inclusive end boundary to avoid duplicates. Coin Metrics follows `next_page_url`; Treasury fetches each required calendar year. `cryptodesk collect daily` rechecks the last five complete UTC dates for late values. Older gaps require another backfill.

Daily run records use group `backfill` or `daily`: `facts` counts accepted rows seen, `changed` added dates, `unchanged` existing dates (including conflicts), `missing` failed series, plus `skipped`, `conflicts`, and series-prefixed `errors`. A failed series does not stop other series; the command fails only when every selected series fails.

## News items

News is separate from facts. Each record has exactly `id`, `source`, `title`, `published_at`, `url`, and `fetched_at`. Both timestamps use [UTC format](#time); `published_at` comes from the feed, never the fetch time. When a date or HTTPS URL is missing or invalid, skip the item and count it in the run's `skipped` field. A failed feed increments `missing` and contributes a source-prefixed error.

The ID is `<source>:<first 12 hex characters of SHA-1(canonical URL)>`; for news URLs, accept HTTPS only, lowercase scheme/host, remove fragments and one trailing path slash except `/`, drop `utm_*`, `fbclid`, `gclid`, `mc_cid`, `mc_eid`, `ref`, `ref_src`, `cmpid`, and `taid` query keys (case-insensitive), and preserve other parameters.

When processing news feeds, reject text over 2,000,000 characters or containing `<!DOCTYPE` or `<!ENTITY` (case-insensitive) before XML parsing. Titles take only the first 2,000 raw characters, collapse whitespace, remove control/format characters, and are capped at 300 characters.

When first seen, append a record once to `data/news/<YYYY-MM>.jsonl`, using the publication month; deduplicate IDs across all months and never edit a stored item. When an ID matches a different URL, skip the item and report `<source>: id collision` once per run. Store metadata only: no body, summary, or description, to avoid redistributing copyrighted article content in this public repository. News numbers are not facts; [analysis rules](analysis.md#rules) apply.

## Adapter contract

- Input: coin profile (or none for macro) and run start time.
- Output: a list of fact records.
- A single failed endpoint yields `missing` facts for that endpoint's metrics only; adapters do not raise for it.
- Adapters never log or store credentials.

## Citations

Analysis cites a fact as `[F:<id>@<fetched_at>]`. Resolution rules are in [analysis.md](analysis.md#citations).
