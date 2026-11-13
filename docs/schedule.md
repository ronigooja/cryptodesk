# Schedule

One workflow per group, using `workflow_dispatch` only. Host cron dispatches through the GitHub API with a token stored only on the scheduler host. GitHub `schedule` triggers were removed ([decision](decisions.md)). Times below are UTC dispatch times, not guaranteed start times.

## Groups

| Group | Contents | Cadence | Cron (UTC) |
|---|---|---|---|
| `market` | Binance, OKX, Deribit ticker and DVOL | hourly | `3 * * * *` |
| `options` | Deribit [option scope](metrics.md#modules) | every 4 h, plus 07:30 daily | `22 */4 * * *`, `30 7 * * *` |
| `macro` | Treasury yields, NY Fed EFFR | weekdays after US close | `45 22 * * 1-5` |
| `onchain` | Coin Metrics MVRV, DefiLlama stablecoin supply | daily | `30 1 * * *` |
| `flows` | Bitbo BTC ETF flows, CFTC positioning | daily | `10 11 * * *` |

CFTC stays for now; a decision on retaining it is pending.

Rules:

- When a group yields zero facts, the run exits non-zero and the workflow fails.
- When some facts are missing, the run still succeeds; inspect `data/latest/` for facts and `runs/` for counts and errors.
- When workflows push data, they share one concurrency group, rebase before pushing, and commit as a bot with message `data: <group> <UTC time>`.

## Actions

Not verified: standard Linux runners are free for public repos. When the repo goes private, re-check minute limits.

- When running collection workflows, use Linux runners; this does not govern development builds/tests.
- When uploading diagnostic artifacts, upload only on failure with short retention.
- When caching dependencies, key on the dependency file.
- When writing workflow logs, omit credentials; logs are public.

## Secrets

| Name | Used by |
|---|---|
| `CRYPTODESK_PROXY` | `market`; optional proxy configuration, behavior in [Known gaps](sources.md#known-gaps) |
