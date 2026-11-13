# Roadmap

Current state only; history is in git.

| Item | Status |
|---|---|
| Collectors, fact store, checker, CLI, BTC/ETH profiles, on-demand analysis | done |
| Five workflow groups dispatched by host cron through the GitHub API; GitHub `schedule` triggers removed | done; [cadences](schedule.md#groups), [decision](decisions.md) |
| [News metadata](data-model.md#news-items) and events layer; reported numbers are not facts | done: news hourly on the host cron; event calendar manual in [events/](events/) |
| backfill one to two years of [daily series](data-model.md#daily-series) | in progress: collector implemented; initial backfill and host scheduling pending |
| view log: dated conclusions with reasons and what would make them wrong, reviewed against later prices | todo |

Altcoins are out of scope until requested.

Not planned: release/filing collectors beyond registered [news feeds](sources.md#news-feeds), automated calendar checks, query index, staking queues, exchange balances, and treasury-company holdings. Other source blockers and gaps remain in [sources.md](sources.md).
