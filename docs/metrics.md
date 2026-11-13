# Metrics

When adding a metric, register it here before any adapter writes it.

## Coin profiles

BTC and ETH use `class = "major"` in `profile.toml`.

## Modules

| Module | Collected scope |
|---|---|
| `core` | Spot price, 24h change, high/low |
| `perp` | Perp price, funding, open interest, top-trader long/short ratios; Deribit DVOL in the market group |
| `options` | Total call/put open interest per currency; max pain for the nearest monthly expiry only |
| `etf` | BTC daily ETF flows from Bitbo |
| `onchain` | Coin Metrics MVRV |

Shared `macro` facts include Treasury yields, EFFR, and DefiLlama stablecoin supply; CFTC positioning runs in [flows](schedule.md#groups). MVRV is collected, not planned.

## Removed

Removed from collection: active addresses, total fees, and mempool.space hashrate, difficulty, and recommended fees; prior records remain in history.

## Registry

Fields: name, unit, meaning, staleness limit (time since [last confirmation](data-model.md#time)), type.

| Metric | Unit | Meaning | Stale after | Type |
|---|---|---|---|---|
| `spot_price` | quote currency | Last traded price | 3 h | series |
| `change_24h_pct` | percent | 24h change | 3 h | series |
| `high_24h`, `low_24h` | quote currency | 24h extremes | 3 h | series |
| `perp_mark_price` | quote currency | Perp mark price | 3 h | series |
| `funding_rate_8h` | fraction | Funding rate per 8h interval; other intervals are normalized and the source interval noted in `sources.md` | 3 h | series |
| `open_interest` | base coin | Open interest in coin units | 3 h | series |
| `open_interest_usd` | USD | Open interest in USD | 3 h | series |
| `top_ls_position_ratio` | ratio | Top-trader long/short position ratio | 3 h | series |
| `top_ls_account_ratio` | ratio | Top-trader long/short account ratio | 3 h | series |
| `dvol` | percent | Implied volatility index | 8 h | series |
| `oi_call`, `oi_put` | base coin | Retired: open interest by expiry and side. Kept so stored history validates; no longer collected | 8 h | series |
| `oi_call_total` | base coin | Total call open interest across non-expired option expiries | 8 h | series |
| `oi_put_total` | base coin | Total put open interest across non-expired option expiries | 8 h | series |
| `max_pain` | USD | Strike minimizing holder payout, computed from per-strike open interest; collected only for the nearest monthly expiry | 8 h | series |
| `etf_flow_total`, `etf_flow_<fund>` | USD | Daily net flow for a US trading day | 36 h | series |
| `us10y_yield`, `us2y_yield` | percent | Treasury yields | 48 h | series |
| `fed_funds_effective` | percent | Effective fed funds rate | 48 h | series |
| `mvrv` | ratio | Market value to realized value (Coin Metrics `CapMVRVCur`) | 48 h | series |
| `active_addresses` | count | Retired: daily active addresses (Coin Metrics `AdrActCnt`). Kept so stored history validates; no longer collected | 48 h | series |
| `fees_total` | base coin | Retired: daily total fees (Coin Metrics `FeeTotNtv`). Kept so stored history validates; no longer collected | 48 h | series |
| `hashrate` | H/s | Retired: current Bitcoin network hashrate. Kept so stored history validates; no longer collected | 3 h | series |
| `difficulty` | number | Retired: current Bitcoin mining difficulty. Kept so stored history validates; no longer collected | 48 h | series |
| `fee_fastest` | sat/vB | Retired: recommended fastest-confirmation fee rate. Kept so stored history validates; no longer collected | 3 h | series |
| `stablecoin_supply_usd` | USD | Total pegged-USD stablecoin circulating supply (DefiLlama), pseudo-coin `macro` | 48 h | series |
| `usdt_supply_usd`, `usdc_supply_usd` | USD | Circulating supply of one stablecoin (DefiLlama), pseudo-coin `macro` | 48 h | series |
| `cot_open_interest` | contracts | CFTC futures open interest for the CME contract | 216 h | series |
| `cot_asset_mgr_net`, `cot_lev_money_net` | contracts | Long minus short for that trader group, CME futures | 216 h | series |

## Rules

- When a venue differs in definition (contracts vs coin units, funding interval), use a separate metric name or state the difference in [sources.md](sources.md).
