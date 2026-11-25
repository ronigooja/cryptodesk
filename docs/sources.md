# Sources

Sole source registry; current state only. Dated measurements in [research](research/) keep their measured values. Terms of use and redistribution limits are not tracked, by user decision.

Status: `planned`, `draft` (code written, never run), `verified` (run and compared with the source), `blocked` (needs something from the user). Historical `planned`/`blocked` entries below do not imply a current implementation commitment; see [roadmap](roadmap.md).

## Collected sources

| Key | Provider | Needs | Coins | Metrics | Status |
|---|---|---|---|---|---|
| `binance` | Binance spot and USD-M futures | [proxy caveat](#known-gaps) | btc, eth | `core`, `perp` | verified locally 2026-11-05; verified on a runner through proxy (run 42095806410) |
| `okx` | OKX v5 public | none | btc, eth | spot, funding, open interest | verified locally 2026-11-05 |
| `deribit` | Deribit v2 public | none | btc, eth | perp, `dvol`, [options](metrics.md#modules) | verified locally 2026-11-05 |
| `treasury` | US Treasury daily par yield curve CSV | none | macro | `us2y_yield`, `us10y_yield` (close of day) | verified locally 2026-11-05 |
| `nyfed` | NY Fed reference rates API | none | macro | `fed_funds_effective` | verified locally 2026-11-05 |
| `fred` | FRED CSV `fredgraph.csv?id=CPIAUCNS` | httpx default User-Agent; custom User-Agents caused disconnects | macro | `cpi_index`, `cpi_yoy_pct` | verified 2026-11-24 against the FRED CSV: 2026-10 index 337.511; YoY `missing` because 2025-10 is blank |
| `fedwatch` | CME China FedWatch / QuikStrike embedded HTML | none; Chrome TLS fingerprint and transient session | macro | `fedwatch_probability_<outcome>`, `fedwatch_status` | verified 2026-11-23; cross-checked against Cointelegraph and Decrypt reports |
| `farside` | Farside Bitcoin and Ethereum ETF flow tables (HTML, US$m, parentheses = negative) | none; [access caveat](#known-gaps) | btc, eth | `etf_flow_total`, `etf_flow_<fund>` | BTC and ETH verified 2026-11-23; cross-checked against Decrypt and CoinGlass/SoSoValue reports |
| `coinmetrics` | Coin Metrics Community | none | btc, eth | `mvrv`, `active_addresses`, `fees_total` | verified locally 2026-11-11 |
| `mempool` | mempool.space | none; rate limited | btc | `hashrate`, `difficulty`, `fee_fastest` | verified locally 2026-11-11 |
| `defillama` | DefiLlama stablecoins API | none | macro | `stablecoin_supply_usd`, `usdt_supply_usd`, `usdc_supply_usd` | verified locally 2026-11-11 |
| `cftc` | CFTC Socrata, dataset `gpe5-46if` (futures only) | none | btc, eth | `cot_open_interest`, `cot_asset_mgr_net`, `cot_lev_money_net` | verified locally 2026-11-11; exact CME contract names |

Retired collection scope: [metrics.md](metrics.md#retired).

For both BTC and ETH, Farside collects only the newest fully published row. If none exists, the total is `missing` with reason `not published`; if the fund sum differs from the total by more than 0.1 US$m per fund, it is `missing` with reason `field absent in response`. `as_of` is the row date, not a verified session cutoff.

### FedWatch

Each bucket is the NOW probability for the page's selected meeting and an absolute target range in basis points. The outcome ID is `YYYYMMDDb<lower>x<upper>`. The page marks the current range `(Current)`; the adapter discards that marker. When interpreting a bucket, compare it with the target range in force at the snapshot: the same range is a hold, above is a hike, and below is a cut. The [2026-10-28 FOMC statement](https://www.federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm) gives 3.75–4.00% (375–400 bp).

The page's CT timestamp is converted using `America/Chicago` timezone rules, including DST. An unidentifiable meeting, table or timestamp yields a missing `fedwatch_status`; rows with all probability cells blank are skipped, and other absent or invalid NOW values yield missing outcome facts. Old meeting IDs remain in latest until manually removed.

## On-demand reads

| Source | Endpoints / use | Status |
|---|---|---|
| Binance | `api.binance.com/api/v3/klines` and `fapi.binance.com/fapi/v1/klines`; [event study](event-study.md) | verified locally 2026-11-24 |

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

Probed and not registered (2026-11-25): BLS RSS (`bls.gov/feed/empsit.rss`, `bls_latest.rss`) returned HTTP 403 to a plain request with a browser user agent; GDELT DOC API returned HTTP 429 on the first request.

## Inactive sources

| Key | Provider | Needs | Scope | Status |
|---|---|---|---|---|
| `bitbo` | Bitbo ETF flow table | none | btc ETF flows | retired 2026-11-23; see [decision](decisions.md#etf-history-cleanup) |
| `bls` | BLS API v2 | free key `BLS_API_KEY` | payrolls, unemployment, CPI | blocked: key |
| `fiscaldata` | Treasury FiscalData | none | refunding, auctions | planned |
| `etf_flows` | SoSoValue | SoSoValue key | ETF cross-check | blocked: HTTP 403 to scripts, also with a Chrome fingerprint (2026-11-19) |
| `edgar` | SEC EDGAR JSON | User-Agent header | filings | planned |
| `beacon` | beaconcha.in | API key | ETH staking queues | blocked: key (HTTP 401 on 2026-11-11) |

## Known gaps

Past incidents and dated probes: [2026-11-24 incident log](research/2026-11-24-incident-log.md).

| Gap | State and action (last confirmed) |
|---|---|
| Market-wide liquidations (long and short); LTH/STH supply and realized price | No complete free liquidation source or stable free holder source was identified in the original inventory (2026-11-06); none is registered (2026-11-24). Do not present partial or reported figures as collected market-wide facts. |
| Farside access | Plain HTTP returned 403 on 2026-11-11. Use the `curl_cffi` Chrome TLS fingerprint (successful collection 2026-11-23); if access fails, ETF facts are `missing`. |
| Stablecoin total | The live `stablecoin_supply_usd` sums per-asset USD-pegged supply; the [daily series](data-model.md#daily-series) uses the chart total. Do not substitute one for the other (adapters checked 2026-11-24). |
| Coin Metrics MVRV latest day | The `onchain` run at 01:30Z often gets a newest daily row without `CapMVRVCur` while other fields are present; the live fact is then `missing` (`field absent in response`; BTC had 6 `missing` of 12 stored days from 2026-11-10 to 2026-11-24, one of them HTTP 526). Re-querying later the same day returned the value (2026-11-25 15:49Z). The [daily series](data-model.md#daily-series) fills the date on a later run, so cite the daily series, not the live fact, for MVRV (checked 2026-11-25). No collector change decided. |
| Source revisions | Upstream values can change (DefiLlama conflicts recorded 2026-11-24). When reconciling daily values, keep the stored row and follow the [conflict rule](data-model.md#daily-series). |
| DefiLlama ETF endpoints | Listed in the [Pro API](https://api-docs.defillama.com/llms-pro.txt), not the free API (2026-11-24). Use Farside for collection. |
| CME FedWatch probabilities | No free API is configured; the [adapter](#fedwatch) uses the embedded HTML. When debugging collection, check the embedded view rather than assuming a JSON API (adapter checked 2026-11-24). |
| Binance from GitHub-hosted runners | Direct access returned HTTP 451 on all Binance endpoints (2026-11-05, run 42094550517), yielding `missing` facts. Set `CRYPTODESK_PROXY` in the environment or GitHub Secrets for runners; only `binance.com` hosts use it, and unset means a direct connection, not a missing-secret error (routing checked 2026-11-24). |

## Cross-source checks

| Metric | Compared | Rule |
|---|---|---|
| spot price | binance, okx | When comparing, record both and note a gap above 0.5% in analysis. |
| funding rate | binance, okx, deribit | When collecting, record all and normalize interval. Checked 2026-11-05: Binance and OKX BTC/ETH perps settle every 8 h (`fundingInfo`, OKX `nextFundingTime` minus `fundingTime`). Deribit uses `funding_8h`; its computation was not checked. Adapters do not re-check intervals at run time. |
