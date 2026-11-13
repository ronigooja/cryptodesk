# Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-11-06 | Repo name `cryptodesk`; GitHub account is the local `gh` login; local path `~/Terminal/cryptodesk` | User choice |
| 2026-11-06 | Public repo to start; may become private or move later | User wants a larger Actions allowance. Content committed while public must be treated as already public. |
| 2026-11-06 | Terms of use and redistribution limits are not tracked | User decision |
| 2026-11-06 | Sources that need keys, payment, or approval are registered as `blocked`, not removed | User will resolve them one by one |
| 2026-11-06 | One repo for BTC, ETH, and macro | Shared code, macro facts, and cross-coin citations. Data kept separable for later migration. |
| 2026-11-06 | Files plus git; no database service | Hosted runners are not persistent; files are auditable. |
| 2026-11-06 | Source URL not stored per fact | Repository growth |
| 2026-11-06 | Update cadence differs by data category | See [schedule.md](schedule.md) |
| 2026-11-06 | Analysis on demand in session, in English, four-section structure | No model keys or scheduled cost |
| 2026-11-06 | Times stored in UTC; analysis shows UTC and UTC+8; no hand DST math | An earlier timezone conversion error |
| 2026-11-06 | `missing` is distinct from `0` and from `n/a` | An unpublished dash was once read as 0; a missing spot market is not an outage |
| 2026-11-06 | Citations pin `fetched_at` | Latest values change; pinned citations stay verifiable |
| 2026-11-06 | No raw HTTP responses in git | Repository growth |
| 2026-11-06 | Docs split by nature: rules in single files; events by month; research by date and write-once | Growth and staleness differ by content type |
| 2026-11-06 | Analysis guidance limits adopted | Defined in [analysis.md](analysis.md#rules) |
| 2026-11-06 | Documentation first, then implementation; the assistant states its plan and waits for "go" before changes | User instruction after an unrequested early implementation, which was deleted |
| 2026-11-06 | Binance proxy support added | Behavior and verified limitation: [sources.md](sources.md#known-gaps) |
| 2026-11-06 | Dispatch workflows from a host cron through the GitHub API; removed the `schedule` trigger | `schedule` ran about 7 times in 24 h against about 30 expected, with multi-hour delays. GitHub documents delay and dropping under load. |
| 2026-11-13 | Remove altcoin design, mempool/active-address/fee metrics, generated `notes.md`, and `sources.json` | Unused by the analyses; history remains in git. |
| 2026-11-13 | Restore active-address, fee, and mempool collection removed earlier the same day; keep CFTC | The removal criterion was weak: one earlier analysis did not use them, while no analysis had enough history to judge them. |
| 2026-11-13 | Add a news metadata layer (seven RSS feeds, six metadata fields, no article text) and rebuild the event calendar from official pages; no denser collection around events | Short-term analysis needs reported events with times; copyright and a public repo rule out storing text; the user declined event-window collection. |

## Triggers to revisit

| Trigger | Action |
|---|---|
| Repo size or commit volume becomes a problem (measure actual growth) | Split data from code, or move data out |
| Concurrent pushes conflict repeatedly | Merge groups or serialize |
| Repo goes private | Re-check Actions minutes in [schedule.md](schedule.md#actions) |
