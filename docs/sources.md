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
| `fred` | FRED CSV `fredgraph.csv?id=CPIAUCNS` | none | macro | `cpi_index`, `cpi_yoy_pct` | draft: probed 2026-11-19; api.bls.gov returned Access Denied from this host; blank months (2025-10) are skipped, so `cpi_yoy_pct` for 2026-10 is `missing`; FRED drops connections from custom User-Agents, so the collector uses the httpx default |
| `fedwatch` | CME China FedWatch / QuikStrike embedded HTML | none; Chrome TLS fingerprint and transient session | macro | `fedwatch_probability_<outcome>`, `fedwatch_status` | draft: embedded view retrieved 5/5 fresh sessions from Japan on 2026-11-19; US runner untested; source may change |
| `farside` | Farside Bitcoin and Ethereum ETF flow tables (HTML, US$m, parentheses = negative) | none; Chrome TLS fingerprint | btc, eth | `etf_flow_total`, `etf_flow_<fund>` | draft: ETH parsed locally 2026-11-19, BTC 2026-11-23; fund columns must sum to the total within 0.1 per fund, else `missing`; `as_of` is the row date, not a verified session cutoff |
| `coinmetrics` | Coin Metrics Community | none | btc, eth | `mvrv`, `active_addresses`, `fees_total` | verified locally 2026-11-11 |
| `mempool` | mempool.space | none; rate limited | btc | `hashrate`, `difficulty`, `fee_fastest` | verified locally 2026-11-11 |
| `defillama` | DefiLlama stablecoins API | none | macro | `stablecoin_supply_usd`, `usdt_supply_usd`, `usdc_supply_usd` | verified locally 2026-11-11 |
| `cftc` | CFTC Socrata, dataset `gpe5-46if` (futures only) | none | btc, eth | `cot_open_interest`, `cot_asset_mgr_net`, `cot_lev_money_net` | verified locally 2026-11-11; exact CME contract names |

Retired collection scope: [metrics.md](metrics.md#retired).

For both BTC and ETH, Farside collection skips rows with an unpublished fund or total and collects only the newest fully published row, using that row's date; if none exists, the total is `missing` with reason `not published`. Previously, ETH could collect a total when a fund such as ETHA was unpublished.

FedWatch reads the NOW column for the page's selected meeting, with date and target bounds encoded in each metric. The page's CT timestamp is converted using `America/Chicago` timezone rules, including DST. Unidentifiable meeting, table or timestamp yields a missing `fedwatch_status`; absent or invalid probability cells yield missing outcome facts. Old meeting IDs remain in latest until manually removed.

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
| `bitbo` | Bitbo ETF flow table | none | btc ETF flows | retired 2026-11-23; see [Known gaps](#known-gaps) |
| `bls` | BLS API v2 | free key `BLS_API_KEY` | payrolls, unemployment, CPI | blocked: key |
| `fiscaldata` | Treasury FiscalData | none | refunding, auctions | planned |
| `etf_flows` | SoSoValue | SoSoValue key | ETF cross-check | blocked: HTTP 403 to scripts, also with a Chrome fingerprint (2026-11-19) |
| `edgar` | SEC EDGAR JSON | User-Agent header | filings | planned |
| `beacon` | beaconcha.in | API key | ETH staking queues | blocked: key (HTTP 401 on 2026-11-11) |

## Known gaps

| Gap | State |
|---|---|
| Market-wide liquidations (long and short) | No free complete source |
| Farside access | Plain HTTP clients get 403 (2026-11-11); a Chrome TLS fingerprint (`curl_cffi`) returns the page (2026-11-19). It may be blocked again at any time, then ETF facts are `missing`. Bitbo's ETH page is a 404 |
| ETF flow disagreement | Wrong Bitbo BTC records were deleted and Farside rows backfilled; an incomplete Farside ETH total was also deleted. See the [2026-11-23 decision for IDs and `as_of` dates](decisions.md#etf-history-cleanup). The smaller 2026-11-09 Bitbo–Farside disagreement was retained: total -198.6m vs -201.0m and IBIT -210.5m vs -213.2m (US$m). |
| Stablecoin total | The live fact `stablecoin_supply_usd` sums per-asset USD-pegged supply and was 292.894B on 2026-11-11; the daily series `stablecoin_supply_usd.defillama` uses the chart total, 289.469B for 2026-11-11 (about 1.2% lower), and an earlier comparison on 2026-11-11 found a 0.155% gap (292.894B versus 292.440B). Cause not found; the two are not interchangeable |
| Coin Metrics MVRV latest day | The newest daily row often has `CapMVRVCur: null` while other fields are set (ETH 2026-11-15, 2026-11-15 probe). The live fact is then `missing`; the daily series holds the last dated value |
| History rollback 2026-11-16 | `main` was reset to the 2026-11-15T15:13Z commit, dropping data commits up to 2026-11-16T15:03Z. On 2026-11-17 the dropped lines of `data/facts` and `runs/` were restored from the backup branch with original values and times. Not restored: `data/latest` (newer values exist) and news lines (already re-collected with later `fetched_at`). `daily` re-adds the last 5 complete days, so daily series have no gap |
| Binance gaps | No `market` run recorded 2026-11-01 to 2026-11-05T18:00Z, plus scattered hours on 11-05 and 11-06; collection history starts 2026-11-05T19:30Z. All Binance facts `missing` at 11-05 19:30Z (HTTP 451), 11-06 15:53Z to 11-08 12:03Z (ConnectError), 11-08 13:03Z to 11-10 08:03Z (ProxyError), 11-15 04:03Z to 07:03Z (ConnectError). Repeated unchanged `missing` facts are not appended |
| Source revisions | Past daily values are revised upstream: DefiLlama stablecoin total (2026-11-12 to 11-14, about 5e-5) and Coin Metrics MVRV (about 1e-8; ETH 2026-11-14 about 3e-6). Stored daily values are kept and the difference appears as a conflict in `runs/`. Bitbo's 2026-11-13 total changed from -369.9m to -373.5m between fetches |
| `fed_press` feed | Returned HTTP 404 on 2026-11-15 and 2026-11-17; HTTP 200 when probed 2026-11-18. Intermittent, cause unknown |
| DefiLlama ETF endpoints | Paid |
| LTH/STH supply, realized price | No stable free source |
| CME FedWatch probabilities | No official free API; the draft collector parses the embedded HTML rather than an API |
| BLS RSS | Returned HTTP 403 on 2026-11-06 |
| Binance from GitHub-hosted runners | HTTP 451 on all Binance endpoints, observed 2026-11-05 (run 42094550517). When `CRYPTODESK_PROXY` is set, only `binance.com` hosts use it; keep the credential-bearing URL only in environment variables or GitHub Secrets. Unset means direct connection, not `<NAME> not set`; on hosted runners the resulting facts are `missing` with reason `HTTP 451` |
| GDELT | Returned HTTP 429; not planned |

## Cross-source checks

| Metric | Compared | Rule |
|---|---|---|
| spot price | binance, okx | When comparing, record both and note a gap above 0.5% in analysis. |
| funding rate | binance, okx, deribit | When collecting, record all and normalize interval. Checked 2026-11-05: Binance and OKX BTC/ETH perps settle every 8 h (`fundingInfo`, OKX `nextFundingTime` minus `fundingTime`). Deribit uses `funding_8h`; its computation was not checked. Adapters do not re-check intervals at run time. |
