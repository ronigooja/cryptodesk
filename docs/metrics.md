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
| `oi_call`, `oi_put` | base coin | Open interest by expiry and side | 8 h | series |
| `oi_call_total` | base coin | Total call open interest across non-expired option expiries | 8 h | series |
| `oi_put_total` | base coin | Total put open interest across non-expired option expiries | 8 h | series |
| `max_pain` | USD | Strike minimizing holder payout, computed from per-strike open interest | 8 h | series |
| `etf_flow_total`, `etf_flow_<fund>` | USD | Daily net flow for a US trading day | 36 h | series |
| `total_supply`, `circulating_supply`, `max_supply` | base coin | Per vendor; vendors differ in definition | 48 h | series |
| `depth_<pct>_<side>` | USD | Sum of price times size within pct of mid, bid or ask, for one venue | 1 h | snapshot |
| `pool_liquidity_usd` | USD | DEX pool liquidity | 3 h | snapshot |
| `pool_volume_24h_usd` | USD | DEX pool 24h volume | 3 h | snapshot |
| `us10y_yield`, `us2y_yield` | percent | Treasury yields | 48 h | series |
| `fed_funds_effective` | percent | Effective fed funds rate | 48 h | series |
| `mvrv` | ratio | Market value to realized value (Coin Metrics `CapMVRVCur`) | 48 h | series |
| `active_addresses` | count | Daily active addresses (Coin Metrics `AdrActCnt`) | 48 h | series |
| `fees_total` | base coin | Daily total fees (Coin Metrics `FeeTotNtv`) | 48 h | series |
| `hashrate` | H/s | Current Bitcoin network hashrate | 3 h | series |
| `difficulty` | number | Current Bitcoin mining difficulty | 48 h | series |
| `fee_fastest` | sat/vB | Recommended fastest-confirmation fee rate | 3 h | series |
| `stablecoin_supply_usd` | USD | Total pegged-USD stablecoin circulating supply (DefiLlama), pseudo-coin `macro` | 48 h | series |
| `usdt_supply_usd`, `usdc_supply_usd` | USD | Circulating supply of one stablecoin (DefiLlama), pseudo-coin `macro` | 48 h | series |
| `cot_open_interest` | contracts | CFTC futures open interest for the CME contract | 216 h | series |
| `cot_asset_mgr_net`, `cot_lev_money_net` | contracts | Long minus short for that trader group, CME futures | 216 h | series |

## Rules

- When a venue differs in definition (contracts vs coin units, funding interval), use a separate metric name or state the difference in [sources.md](sources.md).
