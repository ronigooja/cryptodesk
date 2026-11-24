# Schedule

One workflow per group, using `workflow_dispatch` only. Host cron dispatches through the GitHub API with a token stored only on the scheduler host. GitHub `schedule` triggers were removed ([decision](decisions.md)). Times below are UTC dispatch times, not guaranteed start times.

## Groups

| Group | Contents | Cadence | Cron (UTC) |
|---|---|---|---|
| `market` | Binance, OKX, Deribit ticker and DVOL | hourly | `3 * * * *` |
| `options` | Deribit [option scope](metrics.md#modules) | every 4 h, plus 07:30 daily | `22 */4 * * *`, `30 7 * * *` |
| `macro` | Treasury yields, NY Fed EFFR, FRED CPI, CME FedWatch probabilities (one snapshot per run) | weekdays after US close | `45 22 * * 1-5` |
| `onchain` | Coin Metrics (MVRV, active addresses, fees), mempool.space, DefiLlama stablecoin supply | daily | `30 1 * * *` |
| `flows` | Farside BTC and ETH ETF flows, CFTC positioning | daily | `10 11 * * *` |
| `news` | [News metadata feeds](sources.md#news-feeds) | hourly | `13 * * * *` |
| `daily` | [Daily series](data-model.md#daily-series), last five complete dates | daily after the UTC day closes | `40 0 * * *` |

Rules:

- When a fact group yields zero facts (or news yields zero valid items), the run exits non-zero and the workflow fails. For daily series, only failure of every selected series fails the command; empty successful responses are allowed.
- When some facts are missing, the run still succeeds; see [Failures](#failures).
- When workflows push data, they share one concurrency group, rebase before pushing, and commit as a bot with message `data: <group> <UTC time>`.

## Failures

When a collection fails or is missing:

1. Read the last relevant lines in `runs/<YYYY-MM>.jsonl`; check `group`, `missing`, and `errors`.
2. For fact groups, inspect `status` and `reason` in `data/latest/<coin>.json` (use `macro` for shared facts).
3. Find the GitHub run with `gh run list --workflow <group>.yml`; inspect it with `gh run view <run-id>` and failed steps with `gh run view <run-id> --log-failed`.
4. Read the source adapter in [`src/cryptodesk/adapters/`](../src/cryptodesk/adapters/), or the collector in [`daily.py`](../src/cryptodesk/daily.py) or [`news.py`](../src/cryptodesk/news.py).
5. Expect fact collection failures as `missing` facts, not alerts: [failure handling decision](decisions.md#failure-alerting).

## Actions

Not verified: standard Linux runners are free for public repos. When the repo goes private, re-check minute limits.

- When running collection workflows, use Linux runners; this does not govern development builds/tests.
- When uploading diagnostic artifacts, upload only on failure with short retention.
- When caching dependencies, key on the dependency file.
- When writing workflow logs, omit credentials; logs are public.

## Secrets

| Name | Used by |
|---|---|
| `CRYPTODESK_PROXY` | `market`, `daily`; optional proxy configuration, behavior in [Known gaps](sources.md#known-gaps) |
