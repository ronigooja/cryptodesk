# Schedule

One workflow per group, each with its own cron. All cron times are UTC. Scheduled runs can be delayed; nothing depends on exact minutes.

## Groups

| Group | Contents | Cadence | Cron (UTC) | Phase |
|---|---|---|---|---|
| `market` | binance, okx, deribit ticker and DVOL | hourly | `7 * * * *` | 1 |
| `options` | deribit option open interest and max pain | every 4 h, plus 07:30 every day (not limited to expiry days) | `22 */4 * * *`, `30 7 * * *` | 1 |
| `macro` | Treasury yields, NY Fed EFFR | weekdays after US close | `45 22 * * 1-5` | 1 |
| `etf` | ETF flows and holdings | three runs per US trading day | `10 22 * * 1-5`, `10 4 * * 2-6`, `10 10 * * 2-6` | 2 |
| `releases` | BLS and Treasury releases | 5 minutes after each time in the event calendar | generated from [events/](events/) | 2 |
| `filings` | EDGAR treasury-company filings | every 4 h | `40 */4 * * *` | 2 |
| `feeds` | Fed RSS | hourly | `12 * * * *` | 2 |
| `onchain` | coinmetrics, mempool, defillama, beacon, cftc_cot | daily | `30 1 * * *` | 3 |
| `calendar` | event calendar check | weekly | `0 3 * * 1` | 3 |
| `alt` | depth, dex, perp, supply for each `alt` coin | hourly; every 15 min within 24 h of an unlock event | see below | 4 |

Rules:

- When an unlock or listing event for an `alt` coin is within 24 hours, the `alt` group runs every 15 minutes for that coin. The trigger reads [events/](events/).
- When a group yields zero facts, the run exits non-zero and the workflow fails.
- When some facts are missing, the run still succeeds; missing facts appear in `runs/` and `notes.md`.
- Workflows for different groups share one concurrency group and rebase before pushing.
- Commit message: `data: <group> <UTC time>`, made by a bot identity.

## Actions

Schedules enabled 2026-11-05 for `market`, `options`, `macro`. Believed (not verified): standard Linux runners are free for public repos, and scheduled workflows in a public repo are disabled after 60 days without repository activity. Verify both before enabling schedules. If the repo goes private, re-check minute limits.

- Use Linux runners only.
- Artifacts: failure-only, short retention.
- Cache dependencies keyed on the dependency file.
- Logs must not contain credentials. The logs are public.
- Binance requests from hosted runners return HTTP 451 (observed); the `market` workflow passes `CRYPTODESK_PROXY`. See [sources.md](sources.md#known-gaps).

## Secrets

| Name | Used by |
|---|---|
| `CRYPTODESK_PROXY` | market; proxy URL for `binance.com` requests only. Unset means direct. |
| `BLS_API_KEY` | releases |
| `SOSOVALUE_API_KEY` | etf |

A missing secret yields `missing` facts with reason `<NAME> not set`, not a failed run.
