# Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-11-06 | Repo name `cryptodesk`; GitHub account is the local `gh` login; local path `~/Terminal/cryptodesk` | User choice |
| 2026-11-06 | Public repo to start; may become private or move later | User wants a larger Actions allowance. Content committed while public must be treated as already public. |
| 2026-11-06 | Terms of use and redistribution limits are not tracked | User decision |
| 2026-11-06 | Sources that need keys, payment, or approval are registered as `blocked`, not removed | User will resolve them one by one |
| 2026-11-06 | One repo for BTC, ETH, macro, and altcoins | Shared code, macro facts, and cross-coin citations. Data kept separable for later migration. |
| 2026-11-06 | BTC and ETH first; `class` (`major`, `alt`) required; altcoin design reserved, built in phase 4 | Altcoin investigation differs: supply, holders, depth, derivatives. See [metrics.md](metrics.md). |
| 2026-11-06 | JCT (Janction) is an example for `alt` only, not a special case | User statement |
| 2026-11-06 | Files plus git; no database service | Hosted runners are not persistent; files are auditable. A local query index may be built from files and not committed. |
| 2026-11-06 | Source URL not stored per fact | Repository growth |
| 2026-11-06 | Update cadence differs by data category | See [schedule.md](schedule.md) |
| 2026-11-06 | Analysis on demand in session, in English, four-section structure | No model keys or scheduled cost |
| 2026-11-06 | Times stored in UTC; analysis shows UTC and UTC+8; no hand DST math | An earlier timezone conversion error |
| 2026-11-06 | `missing` is distinct from `0` and from `n/a` | An unpublished dash was once read as 0; a missing spot market is not an outage |
| 2026-11-06 | Citations pin `fetched_at` | Latest values change; pinned citations stay verifiable |
| 2026-11-06 | No raw HTTP responses in git | Repository growth |
| 2026-11-06 | Docs split by nature: rules in single files; events by month; research by date and write-once | Growth and staleness differ by content type |
| 2026-11-06 | No position, leverage, entry, or stop guidance in analysis | Default assumed; the user has not confirmed or rejected it |
| 2026-11-06 | Documentation first, then implementation; the assistant states its plan and waits for "go" before changes | User instruction after an unrequested early implementation, which was deleted |
| 2026-11-06 | Binance requests may go through a proxy configured by `CRYPTODESK_PROXY`; only `binance.com` hosts use it | Binance returns HTTP 451 to GitHub runners. The proxy URL holds credentials, so it lives only in Secrets or the local environment. |
| 2026-11-06 | Schedules enabled for `market`, `options`, `macro`; the Actions free-tier and 60-day inactivity assumptions were not verified | User instruction to enable without checking |
| 2026-11-06 | Dispatch workflows from a host cron through the GitHub API; removed the `schedule` trigger | `schedule` ran about 7 times in 24 h against about 30 expected, with multi-hour delays. GitHub documents delay and dropping under load. |

## Triggers to revisit

| Trigger | Action |
|---|---|
| Repo size or commit volume becomes a problem (measure after the first month of phase 1) | Split data from code, or move data out |
| Concurrent pushes conflict repeatedly | Merge groups or serialize |
| Repo goes private | Re-check Actions minutes in [schedule.md](schedule.md#actions) |
