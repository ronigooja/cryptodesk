# cryptodesk agent guide

Public repo (may later become private or move). Collects BTC, ETH, and macro facts separately from analysis.

## Read order

| Need | Read |
|---|---|
| Layers, directory layout, adding a source | [README.md](README.md#architecture) |
| Fact schema, IDs, states, time, storage | [docs/data-model.md](docs/data-model.md) |
| Modules, metric registry | [docs/metrics.md](docs/metrics.md) |
| Source registry, status, blockers | [docs/sources.md](docs/sources.md) |
| Update cadence, workflow groups | [docs/schedule.md](docs/schedule.md) |
| Analysis format, citations, rules | [docs/analysis.md](docs/analysis.md) |
| Event calendar (unlocks, expiries, releases) | [docs/events/](docs/events/) |
| Dated research snapshots | [docs/research/](docs/research/) |
| Status and next items | [docs/roadmap.md](docs/roadmap.md) |
| Why things are as they are | [docs/decisions.md](docs/decisions.md) |

## Rules

- When writing any repo document, write in English, keep it concise, and define each fact once; link to the defining file instead of repeating it.
- When writing a rule in this repo, state when it applies.
- When adding or changing a metric, source, or schedule, update its defining doc in the same change.
- When collecting facts, follow [states](docs/data-model.md#states) and [time rules](docs/data-model.md#time).
- When writing a scheduled release time, take it from an event record or official calendar, never from memory.
- When writing analysis, follow [docs/analysis.md](docs/analysis.md), including its citation and guidance limits.
- When handling credentials, read them from environment variables or GitHub Secrets only; never write them to files, logs, commits, or error text. The repo is public.
- When writing any file, do not include positions, balances, cost basis, or personal plans. The repo is public.
- When a research result is recorded, put it in `docs/research/` with its date and keep it unchanged afterward; update [sources.md](docs/sources.md) for current state.
- Before committing code, run the checker and tests once they exist.
- When the work is complete, commit only the files you changed to the default branch.
- When the user has not said to proceed, state understanding and plan first; do not create or change files.

## Out of scope

Trading, order placement, investment advice, raw HTTP response storage in git.
