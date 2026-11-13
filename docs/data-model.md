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

## Adapter contract

- Input: coin profile (or none for macro) and run start time.
- Output: a list of fact records.
- A single failed endpoint yields `missing` facts for that endpoint's metrics only; adapters do not raise for it.
- Adapters never log or store credentials.

## Citations

Analysis cites a fact as `[F:<id>@<fetched_at>]`. Resolution rules are in [analysis.md](analysis.md#citations).
