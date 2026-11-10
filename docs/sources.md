# Sources

Current state only. Dated findings are in [research/](research/); this file is updated when a finding changes a status.

Terms of use and redistribution limits are not reviewed. The user decided not to track them.

Status: `planned`, `draft` (code written, never run), `verified` (run and compared with the source), `blocked` (needs something from the user).

## Registry: major and macro

| Key | Provider | Needs | Coins | Metrics | Phase | Status |
|---|---|---|---|---|---|---|
| `binance` | Binance spot and USD-M futures | none; `CRYPTODESK_PROXY` on GitHub runners | btc, eth | `core`, `perp` | 1 | verified locally 2026-11-05; HTTP 451 from GitHub runners without proxy (run 42094550517); verified on a runner through `CRYPTODESK_PROXY` (run 42095806410) |
| `okx` | OKX v5 public | none | btc, eth | spot, funding, open interest | 1 | verified locally 2026-11-05 |
| `deribit` | Deribit v2 public | none | btc, eth | perp, `dvol`, `options` | 1 | verified locally 2026-11-05 |
| `treasury` | US Treasury daily par yield curve CSV | none | macro | `us2y_yield`, `us10y_yield` (close of day) | 1 | verified locally 2026-11-05 |
| `nyfed` | NY Fed reference rates API | none | macro | `fed_funds_effective` | 1 | verified locally 2026-11-05 |
| `bls` | BLS API v2 | free key `BLS_API_KEY` | macro | payrolls, unemployment, CPI | 2 | blocked: key |
| `fiscaldata` | Treasury FiscalData | none | macro | refunding, auctions | 2 | planned |
| `bitbo` | Bitbo ETF flow table (HTML, US$m) | none | btc | `etf_flow_total`, `etf_flow_<fund>` | 2 | verified locally 2026-11-11; btc only |
| `etf_flows` | Farside and SoSoValue | SoSoValue key | btc, eth | `etf` cross-check, ETH ETF flows | 2 | blocked: Cloudflare returns 403 to scripts, also through the proxy (2026-11-11) |
| `edgar` | SEC EDGAR JSON | User-Agent header | btc, eth | filings | 2 | planned |
| `fed_rss` | Federal Reserve RSS | none | macro | press releases | 2 | planned |
| `coinmetrics` | Coin Metrics Community | none | btc, eth | `mvrv`, `active_addresses`, `fees_total` | 3 | verified locally 2026-11-11 |
| `mempool` | mempool.space | none; rate limited | btc | `hashrate`, `difficulty`, `fee_fastest` | 3 | verified locally 2026-11-11 |
| `defillama` | DefiLlama stablecoins API | none | macro | `stablecoin_supply_usd`, `usdt_supply_usd`, `usdc_supply_usd` | 3 | verified locally 2026-11-11 |
| `beacon` | beaconcha.in | API key | eth | staking queues | 3 | blocked: key (HTTP 401 on 2026-11-11) |
| `cftc` | CFTC Socrata, dataset `gpe5-46if` (futures only) | none | btc, eth | `cot_open_interest`, `cot_asset_mgr_net`, `cot_lev_money_net` | 3 | verified locally 2026-11-11; exact CME contract names |

## Registry: altcoin (phase 4)

Findings from [research/2026-11-06-alt-supply-sources.md](research/2026-11-06-alt-supply-sources.md), [research/2026-11-06-alt-addresses-sources.md](research/2026-11-06-alt-addresses-sources.md), and [research/2026-11-06-alt-depth-dex-derivs.md](research/2026-11-06-alt-depth-dex-derivs.md).

| Module | Source | Needs | Status |
|---|---|---|---|
| `supply` totals | CoinGecko, CoinMarketCap, CoinPaprika (free tiers) | CoinGecko and CoinMarketCap free keys; CoinPaprika none but its free ticker returns no circulating supply | planned |
| `supply` allocation | Project documentation | manual entry | planned |
| unlock schedule | none free by API | CryptoRank Pro, DefiLlama paid, or Tokenomist trial; otherwise manual entry in [events/](events/) | blocked: paid or approval |
| `depth` | Binance, Bitget, MEXC public order book endpoints | none | planned |
| `dex` | DexScreener | none | planned |
| `perp` for small caps | Binance, OKX, Bybit | none; small-cap coverage unverified | planned |
| top holders | Blockscout Pro, Etherscan top holders | key; Etherscan top holders is paid | blocked: key or paid |
| address labels | Etherscan Pro Plus, Nansen, others | paid or limited trial; basis and confidence not found | blocked: paid |
| liquidations | Binance `@forceOrder` | none; one snapshot per symbol per second, not complete | planned, partial |

## Known gaps

| Gap | State |
|---|---|
| Market-wide liquidations (long and short) | No free complete source |
| ETH spot ETF flows | No free source usable by script: Farside returns 403, Bitbo's ETH page is a soft 404 (2026-11-11) |
| Farside ETF flows | No official API; Cloudflare blocks scripts |
| ETF flow disagreement | Bitbo and Farside disagree on 2026-11-09: total -198.6m vs -201.0m, IBIT -210.5m vs -213.2m (US$m). Cause not found. Only Bitbo is collected |
| Stablecoin total | Sum of DefiLlama per-asset USD-pegged supply was 292.894B; DefiLlama's chart total was 292.440B (0.155% apart) on 2026-11-11. Cause not found |
| DefiLlama ETF endpoints | Paid |
| LTH/STH supply, realized price | No stable free source |
| CME FedWatch probabilities | No official free API |
| BLS RSS | Returned HTTP 403 on 2026-11-06 |
| Binance from GitHub-hosted runners | HTTP 451 on all Binance endpoints, observed 2026-11-05 (workflow run 42094550517). Mitigation: `CRYPTODESK_PROXY` routes only `binance.com` requests through a proxy; without it the facts are `missing` with reason `HTTP 451` |
| GDELT | Returned HTTP 429; not planned |
| Circulating supply across vendors | Definitions differ; keep per vendor |

## Cross-source checks

| Metric | Compared | Rule |
|---|---|---|
| spot price | binance, okx | Record both. Analysis notes a gap above 0.5%. |
| funding rate | binance, okx, deribit | Record all; normalize interval. Intervals checked 2026-11-05: Binance and OKX BTC and ETH perps settle every 8 h (`fundingInfo`, OKX `nextFundingTime` minus `fundingTime`). Deribit is read from its `funding_8h` field; its computation was not checked. The adapters do not re-check the interval at run time. |
| circulating supply | all vendors | Record all; analysis states the spread. |
