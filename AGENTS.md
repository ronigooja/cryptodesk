# cryptodesk agent guide

Public repo (may later become private or move). Collects per-coin facts for BTC and ETH on per-category schedules, keeps a separate analysis layer, and reserves a design for altcoins.

## Read order

| Need | Read |
|---|---|
| Layers, directory layout, how to add a coin or source | [docs/architecture.md](docs/architecture.md) |
| Fact schema, IDs, states, time, storage | [docs/data-model.md](docs/data-model.md) |
| Coin classes, modules, metric registry | [docs/metrics.md](docs/metrics.md) |
| Source registry, status, blockers | [docs/sources.md](docs/sources.md) |
| Update cadence, workflow groups | [docs/schedule.md](docs/schedule.md) |
| Analysis format, citations, rules | [docs/analysis.md](docs/analysis.md) |
| Event calendar (unlocks, expiries, releases) | [docs/events/](docs/events/) |
| Dated research snapshots | [docs/research/](docs/research/) |
| Phases and status | [docs/roadmap.md](docs/roadmap.md) |
| Why things are as they are | [docs/decisions.md](docs/decisions.md) |

## Rules

- When writing any repo document, write in English, keep it concise, and define each fact once; link to the defining file instead of repeating it.
- When writing a rule in this repo, state when it applies.
- When adding or changing a metric, source, or schedule, update its defining doc in the same change.
- When a value cannot be obtained, record a `missing` fact with a reason; never estimate, never substitute another source silently. See [data-model.md](docs/data-model.md#states).
- When a source shows a placeholder (a dash, "N/A") instead of a number, record `missing`, never `0`.
- When a coin has no such market (for example no spot market), the metric is `n/a`, not `missing`.
- When writing any time, store UTC ISO-8601 with `Z`. Analysis files also show UTC+8.
- When writing a scheduled release time, take it from an event record or official calendar, never from memory.
- When writing analysis, follow [docs/analysis.md](docs/analysis.md); every number cites a fact record.
- When a number comes from memory, a chat, or a news article, it is not a fact; list it under Missing.
- When handling credentials, read them from environment variables or GitHub Secrets only; never write them to files, logs, commits, or error text. The repo is public.
- When writing any file, do not include positions, balances, cost basis, or personal plans. The repo is public.
- When writing analysis, do not give position size, leverage, entry, or stop levels. Describe observable conditions only.
- When a research result is recorded, put it in `docs/research/` with its date and keep it unchanged afterward; update [sources.md](docs/sources.md) for current state.
- Before committing code, run the checker and tests once they exist.
- When the work is complete, commit only the files you changed to the default branch.
- When the user has not said to proceed, state understanding and plan first; do not create or change files.

## Out of scope

Trading, order placement, investment advice, raw HTTP response storage in git.
