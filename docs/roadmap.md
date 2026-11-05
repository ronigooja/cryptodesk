# Roadmap

Status: `todo`, `done`. Current state only; history is in git.

| Phase | Scope | Status |
|---|---|---|
| 0 | Documentation: AGENTS.md, docs, templates | done, awaiting user review |
| 1 | Skeleton (model, store, renderer, checker, CLI), binance, okx, deribit, treasury, nyfed, `btc` and `eth` profiles, workflows `market`, `options`, `macro`. Done: code, 199 local tests, local live runs of all sources, `market` workflow run on GitHub. Remaining: run `options` and `macro` workflows on GitHub, then decide on enabling schedules | in progress |
| 2 | ETF flows with cross-check, BLS and Treasury on the event calendar, EDGAR filings, Fed RSS, query index built from files | todo |
| 3 | coinmetrics, mempool, defillama, beacon, cftc_cot, calendar check | todo |
| 4 | First `alt` coin: `supply`, `depth`, `dex`, `perp`, unlock-aware scheduling; address data when unblocked | todo |

Phase 1 exit: every phase-1 source is `verified` in [sources.md](sources.md), and the checker and tests pass.

Not planned: market-wide liquidations, LTH/STH supply, CME FedWatch scraping. See [sources.md](sources.md#known-gaps).
