# Roadmap

Current state only; history is in git.

| Item | Status |
|---|---|
| Collectors, fact store, checker, CLI, BTC/ETH profiles, on-demand analysis | done |
| Five workflow groups dispatched by host cron through the GitHub API; GitHub `schedule` triggers removed | done; [cadences](schedule.md#groups), [decision](decisions.md) |
| news and events layer (each record: time, event, source link, registered date; reported numbers are not facts) | todo |
| backfill one to two years of daily prices, MVRV, Treasury yields, stablecoin supply | todo |
| view log: dated conclusions with reasons and what would make them wrong, reviewed against later prices | todo |

Altcoins are out of scope until requested.

Not planned: release/filing/feed collectors, automated calendar checks, query index, staking queues, exchange balances, and treasury-company holdings. Other source blockers and gaps remain in [sources.md](sources.md).
