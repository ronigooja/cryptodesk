# Metrics

New metrics must be registered here before any adapter writes them.

## Coin classes

`class` is required in `profile.toml`.

| Class | Meaning | Investigation focus |
|---|---|---|
| `major` | BTC, ETH: deep multi-venue markets | Macro, flows, derivatives, on-chain statistics |
| `alt` | Other coins: thin, concentrated, possibly derivatives-led | Supply structure, unlock events, holders and addresses, depth, derivatives |

Implemented in phase 1: `major` only. `alt` is designed here and built in phase 4 ([roadmap.md](roadmap.md)).

## Modules

| Module | Contents | major | alt |
|---|---|---|---|
| `core` | spot price, 24h change, 24h high/low | required | required if a spot market exists, else `n/a` |
| `perp` | perp price, funding, open interest, top-trader long/short ratios | required | required if a perp exists |
| `options` | option open interest by expiry, max pain, implied vol index | required | `n/a` unless options exist |
| `etf` | daily ETF flows, issuer holdings | BTC, ETH | `n/a` |
| `onchain` | exchange balance, supply, fees, valuation ratios | recommended | recommended |
| `staking` | staked amount, entry and exit queues | ETH | per chain |
| `treasury` | treasury-company holdings from filings | recommended | optional |
| `supply` | total, circulating, max supply per vendor; documented allocation | optional | required |
| `depth` | near-price order book depth on each venue | optional | required |
| `dex` | pool liquidity, 24h volume, price, creation time | `n/a` | required if a DEX pool exists |
| `addresses` | top holders and labeled addresses, each with evidence | `n/a` | required, mostly `blocked` |

Macro (`macro` pseudo-coin) has its own metrics below and is shared by all classes.

## Registry

Fields: name, unit, meaning, staleness limit (value older than this at analysis time is marked stale), type.

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

Metrics planned for later phases (payrolls, CPI, exchange balances, MVRV, staking queues, treasury holdings) are added when their phase starts.

## Rules

- A metric from a venue that differs in definition (contracts vs coin units, funding interval) is a separate metric name, or the difference is stated in [sources.md](sources.md).
- Documented allocation (team, foundation, liquidity shares from project docs) is an initial plan, not current holdings. Do not label it current.
- An address label requires evidence (source and basis). A label without evidence is not stored; list the gap under Missing.
