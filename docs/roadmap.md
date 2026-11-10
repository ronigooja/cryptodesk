# Roadmap

Status: `todo`, `done`. Current state only; history is in git.

| Phase | Scope | Status |
|---|---|---|
| 0 | Documentation: AGENTS.md, docs, templates | done, awaiting user review |
| 1 | Skeleton (model, store, renderer, checker, CLI), binance, okx, deribit, treasury, nyfed, `btc` and `eth` profiles, workflows `market`, `options`, `macro`. Done: code, 199 local tests, local live runs of all sources, `market` workflow run on GitHub. All three workflows ran on GitHub; schedules enabled 2026-11-05 | done |
| 2 | BTC ETF flows (bitbo, no cross-check: Farside blocked), BLS and Treasury on the event calendar, EDGAR filings, Fed RSS, query index built from files | in progress: ETF flows written; rest todo |
| 3 | coinmetrics, mempool, defillama stablecoins, cftc (written); beacon (blocked: key), calendar check (todo) | in progress |
| 4 | First `alt` coin: `supply`, `depth`, `dex`, `perp`, unlock-aware scheduling; address data when unblocked | todo |

Phase 1 exit: every phase-1 source is `verified` in [sources.md](sources.md), and the checker and tests pass.

Not planned: market-wide liquidations, LTH/STH supply, CME FedWatch scraping. See [sources.md](sources.md#known-gaps).
