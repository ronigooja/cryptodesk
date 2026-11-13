# Sources

Sole source registry; current state only. Dated [research](research/) remains write-once history. Terms of use and redistribution limits are not tracked, by user decision.

Status: `planned`, `draft` (code written, never run), `verified` (run and compared with the source), `blocked` (needs something from the user). Historical `planned`/`blocked` entries below do not imply a current implementation commitment; see [roadmap](roadmap.md).

## Collected sources

| Key | Provider | Needs | Coins | Metrics | Status |
|---|---|---|---|---|---|
| `binance` | Binance spot and USD-M futures | [proxy caveat](#known-gaps) | btc, eth | `core`, `perp` | verified locally 2026-11-05; verified on a runner through proxy (run 42095806410) |
| `okx` | OKX v5 public | none | btc, eth | spot, funding, open interest | verified locally 2026-11-05 |
| `deribit` | Deribit v2 public | none | btc, eth | perp, `dvol`, [options](metrics.md#modules) | verified locally 2026-11-05 |
| `treasury` | US Treasury daily par yield curve CSV | none | macro | `us2y_yield`, `us10y_yield` (close of day) | verified locally 2026-11-05 |
| `nyfed` | NY Fed reference rates API | none | macro | `fed_funds_effective` | verified locally 2026-11-05 |
| `bitbo` | Bitbo ETF flow table (HTML, US$m) | none | btc | `etf_flow_total`, `etf_flow_<fund>` | verified locally 2026-11-11; btc only |
| `coinmetrics` | Coin Metrics Community | none | btc, eth | `mvrv`, `active_addresses`, `fees_total` | verified locally 2026-11-11 |
| `mempool` | mempool.space | none; rate limited | btc | `hashrate`, `difficulty`, `fee_fastest` | verified locally 2026-11-11 |
| `defillama` | DefiLlama stablecoins API | none | macro | `stablecoin_supply_usd`, `usdt_supply_usd`, `usdc_supply_usd` | verified locally 2026-11-11 |
| `cftc` | CFTC Socrata, dataset `gpe5-46if` (futures only) | none | btc, eth | `cot_open_interest`, `cot_asset_mgr_net`, `cot_lev_money_net` | verified locally 2026-11-11; exact CME contract names |

Retired collection scope: [metrics.md](metrics.md#retired).

## Daily backfill endpoints

Definitions, units, and day boundaries are in [Daily series](data-model.md#daily-series). These direct read-only shape checks did not perform a backfill.

| Source | Endpoint / backfill use | Status |
|---|---|---|
| Binance | `api.binance.com/api/v3/klines`, `interval=1d`; BTCUSDT and ETHUSDT close | verified locally 2026-11-13; UTC midnight opens; `limit=1000` accepted with a one-day interval; hard maximum not probed |
| Coinbase Exchange | `api.exchange.coinbase.com/products/<BTC-USD or ETH-USD>/candles`, `granularity=86400`; close | verified locally 2026-11-13; newest first, inclusive end, today's candle partial; oversized request rejected with explicit 300-aggregation limit |
| Coin Metrics | Community `/v4/timeseries/asset-metrics`, `CapMVRVCur`, `frequency=1d` | BTC and ETH verified locally 2026-11-13; string values; `page_size=10000` accepted for a small interval; hard maximum not probed |
| Treasury | Daily par yield curve CSV `/<year>/all`, existing date/column format | 2025 and 2026 verified locally 2026-11-13 |
| NY Fed | `/api/rates/unsecured/effr/search.json`, `startDate` / `endDate` | verified locally 2026-11-13; 6,624 `refRates` returned back to 2000-07-03 in one request; hard maximum unverified |
| DefiLlama | `stablecoins.llama.fi/stablecoincharts/all`; chart total, not per-asset sum | verified locally 2026-11-13; string Unix seconds, UTC midnight dates including today; exact snapshot cutoff unverified |

## News feeds

[Metadata only](data-model.md#news-items); terms of use not reviewed. Verified locally means RSS endpoint shape checked, not article claims verified.

| Key | Feed | Status | Note |
|---|---|---|---|
| `cointelegraph` | https://cointelegraph.com/rss | verified locally 2026-11-13 | terms of use not reviewed, metadata only |
| `theblock` | https://www.theblock.co/rss.xml | verified locally 2026-11-13 | terms of use not reviewed, metadata only |
| `coindesk` | https://www.coindesk.com/arc/outboundfeeds/rss | verified locally 2026-11-13 | terms of use not reviewed, metadata only |
| `decrypt` | https://decrypt.co/feed | verified locally 2026-11-13 | terms of use not reviewed, metadata only |
| `fed_press` | https://www.federalreserve.gov/feeds/press_all.xml | verified locally 2026-11-13 | terms of use not reviewed, metadata only |
| `fed_monetary` | https://www.federalreserve.gov/feeds/press_monetary.xml | verified locally 2026-11-13 | terms of use not reviewed, metadata only |
| `sec` | https://www.sec.gov/news/pressreleases.rss | verified locally 2026-11-13 | terms of use not reviewed, metadata only |

## Inactive sources

| Key | Provider | Needs | Scope | Status |
|---|---|---|---|---|
| `bls` | BLS API v2 | free key `BLS_API_KEY` | payrolls, unemployment, CPI | blocked: key |
| `fiscaldata` | Treasury FiscalData | none | refunding, auctions | planned |
| `etf_flows` | Farside and SoSoValue | SoSoValue key | ETF cross-check, ETH ETF flows | blocked: Cloudflare returns 403 to scripts, also through the proxy (2026-11-11) |
| `edgar` | SEC EDGAR JSON | User-Agent header | filings | planned |
| `beacon` | beaconcha.in | API key | ETH staking queues | blocked: key (HTTP 401 on 2026-11-11) |

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
| Binance from GitHub-hosted runners | HTTP 451 on all Binance endpoints, observed 2026-11-05 (run 42094550517). When `CRYPTODESK_PROXY` is set, only `binance.com` hosts use it; keep the credential-bearing URL only in environment variables or GitHub Secrets. Unset means direct connection, not `<NAME> not set`; on hosted runners the resulting facts are `missing` with reason `HTTP 451` |
| GDELT | Returned HTTP 429; not planned |

## Cross-source checks

| Metric | Compared | Rule |
|---|---|---|
| spot price | binance, okx | When comparing, record both and note a gap above 0.5% in analysis. |
| funding rate | binance, okx, deribit | When collecting, record all and normalize interval. Checked 2026-11-05: Binance and OKX BTC/ETH perps settle every 8 h (`fundingInfo`, OKX `nextFundingTime` minus `fundingTime`). Deribit uses `funding_8h`; its computation was not checked. Adapters do not re-check intervals at run time. |
