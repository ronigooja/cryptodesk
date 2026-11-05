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
| `source` | string | Source key from [sources.md](sources.md) |
| `reason` | string or null | Why missing; null when `ok` |

The request URL is not stored per fact. It is derived from `source` plus the metric via `data/sources.json`. Reason: repository growth.

## IDs

| Kind | Pattern | Example |
|---|---|---|
| Market | `<source>.<coin>.<metric>` | `binance.btc.funding_rate_8h` |
| Option expiry | `<source>.<coin>.opt.<YYYY-MM-DD>.<metric>` | `deribit.btc.opt.2026-11-27.max_pain` |
| Depth snapshot | `<source>.<coin>.<market>.depth_<pct>_<side>` | `bitget.jct.spot.depth_1pct_bid` |
| Macro | `<source>.macro.<metric>` | `fred.macro.us10y_yield` |

The same metric from two sources is two facts. Never merge or average. Analysis cites both and states the difference. Fields that vary between vendors (for example circulating supply) must be kept as separate facts per vendor.

## States

| State | Meaning | Stored |
|---|---|---|
| `ok` | Value obtained | yes |
| `missing` | Should exist but could not be obtained | yes, with `reason` |
| `n/a` | The coin has no such market or module | no record; declared by absence from `profile.toml` |

`missing` reasons use short fixed text: `HTTP <code>`, `Timeout`, `field absent in response`, `not published`, `<ENV_NAME> not set`, `requires paid plan`, `requires approval`. Never write `0`, an estimate, or another source's value in place of a missing value. A true zero is `ok` with value 0.

## Time

- Store UTC `YYYY-MM-DDTHH:MM:SSZ`.
- `as_of` null means the source gave no time; analysis states that caveat.
- FRED daily series use the observation date at `00:00:00Z`.
- A source's local-time claims (for example "ET") are converted at ingest; DST must not be hand-computed. Convert with a timezone library.

## Storage

| Path | Behavior |
|---|---|
| `data/latest/<coin>.json` | Map of fact ID to latest record. |
| `data/facts/<YYYY-MM>/<coin>.jsonl` | One line appended when `status`, `value`, `as_of`, or `reason` differs from latest. Never edited. |
| `runs/<YYYY-MM>.jsonl` | One line per run: start time, group, counts (facts, changed, unchanged, missing), error strings. |
| `data/sources.json` | Source key to base URL and notes. |

Raw HTTP responses are not committed. For diagnosis, upload as a failure-only workflow artifact with short retention ([schedule.md](schedule.md#actions)).

Depth and pool snapshots are point-in-time: every snapshot is stored even if the value is unchanged, because the time is the information. These metrics are marked `snapshot` in the registry and skip the unchanged filter.

Size is a concern, not a measured one. An unmeasured estimate for 80 facts hourly was tens of MB per year. Measure after the first month and record the result in [decisions.md](decisions.md).

## Adapter contract

- Input: coin profile (or none for macro) and run start time.
- Output: a list of fact records.
- A single failed endpoint yields `missing` facts for that endpoint's metrics only; adapters do not raise for it.
- Adapters never log or store credentials.

## Citations

Analysis cites a fact as `[F:<id>@<fetched_at>]`. Resolution rules are in [analysis.md](analysis.md#citations).
