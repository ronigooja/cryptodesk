# Architecture

## Layers

| Layer | Content | Written by | Mutability |
|---|---|---|---|
| Collect | Source adapters call APIs | scheduled workflows | n/a |
| Facts | Normalized fact records | collectors only | append-only history plus regenerated latest |
| Views | `coins/<coin>/notes.md` rendered from latest | renderer | regenerated, never hand-edited |
| Analysis | Dated markdown citing facts | agent in session | write-once per file |

Only the Collect step writes facts. Analysis never writes facts. Manually registered events live in [events/](events/), not in the facts layer.

## Data flow

```
workflow (cron) -> adapters -> facts -> store (history + latest) -> notes.md
                                              ^
analysis/*.md --cites--> fact IDs ------------+   checker validates structure and citations
```

## Directory layout

Created when the phase needs it; do not create empty directories.

```
AGENTS.md  README.md
docs/                        documentation (this layer exists now)
docs/events/<YYYY-MM>.md     event calendar, one file per month
docs/research/<date>-<topic>.md   dated research snapshots, write-once
analysis/                    templates and dated analyses
coins/<coin>/profile.toml    symbol mapping, class, enabled modules
coins/<coin>/notes.md        generated fact table
data/latest/<coin>.json      current record per fact ID
data/facts/<YYYY-MM>/<coin>.jsonl   append-only change history
data/sources.json            source registry: key to base URL and notes
runs/<YYYY-MM>.jsonl         one line per collector run
src/  tests/  .github/workflows/
```

`<coin>` is the lowercase ticker. Macro facts use the pseudo-coin `macro`.

## Separation for later migration

Data lives only under `data/`, `runs/`, and `coins/*/notes.md`. Code in `src/` reads and writes them through the store module only, with no other cross references, so data can move to a separate repo or storage later.

## One repo

BTC, ETH, macro, and altcoins share one repo: they share code, macro facts, and cross-coin citations. Split data from code only when a trigger in [decisions.md](decisions.md) fires.

## Adding a coin

1. Add `coins/<coin>/profile.toml`: `class`, symbol mapping per source, enabled modules ([metrics.md](metrics.md)).
2. No code change if all required modules already have adapters for the coin's sources.
3. Modules the coin does not have are `n/a` and not listed.

## Adding a source

1. Add an adapter that returns facts ([data-model.md](data-model.md#adapter-contract)).
2. Register it in [sources.md](sources.md) with status and blockers, and in a group in [schedule.md](schedule.md).
3. Register any new metric in [metrics.md](metrics.md) first.

## Non-goals

Real-time streaming, order execution, backtesting.
