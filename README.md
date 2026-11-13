# cryptodesk

Per-coin information collection for BTC and ETH, with shared macro facts.

- Facts layer: scheduled collectors write timestamped, sourced facts. Missing data is recorded as missing.
- Analysis layer: dated markdown files that cite facts and separate inference from fact.

Personal-use project. No license is granted. Entry point for agents: [AGENTS.md](AGENTS.md).

Not investment advice.

## Architecture

Host cron dispatches [workflow groups](docs/schedule.md) through the GitHub API. Source adapters write normalized facts through the store: append-only change history plus refreshed latest records. On-demand analyses cite facts; they never write them. Manually registered [events](docs/events/) are separate from facts.

| Path | Purpose |
|---|---|
| `src/`, `tests/`, `.github/workflows/` | Collectors, store, checker, CLI, tests, workflows |
| `coins/<coin>/profile.toml` | Source symbols, `major` class, enabled [modules](docs/metrics.md#modules) |
| `data/`, `runs/` | [Fact storage and run logs](docs/data-model.md#storage); kept separate from code |
| `analysis/` | [Template and write-once analyses](docs/analysis.md) |
| `docs/events/<YYYY-MM>.md` | Monthly event calendar |
| `docs/research/<date>-<topic>.md` | Write-once research snapshots |

`<coin>` is a lowercase ticker; `macro` is the shared pseudo-coin. Data and code share one repository; migration triggers are in [decisions](docs/decisions.md#triggers-to-revisit).

When adding a source, register its metrics in [metrics.md](docs/metrics.md), implement the [adapter contract](docs/data-model.md#adapter-contract), and update [sources.md](docs/sources.md) and [schedule.md](docs/schedule.md).

Non-goals: real-time streaming, order execution, backtesting.
