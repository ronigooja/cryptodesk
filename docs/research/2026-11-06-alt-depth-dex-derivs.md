# Research 2026-11-06: altcoin order book depth, DEX pools, derivatives

Write-once snapshot. Current state is in [sources.md](../sources.md). Reported by a read-only subagent; the request clock read 2026-11-05 UTC. Measurements are from about 17:48 UTC on 2026-11-05.

## Venues for JCT

- Binance announced Janction (JCT) on Alpha and a JCTUSDT perpetual, and stated a futures listing does not guarantee a spot listing. Whether a regular spot market exists on Binance: not found.
- Bitget and MEXC spot markets were observed. Bitget has a perpetual. A third-party site also lists perpetuals on Binance, Bybit, Gate, MEXC; the full list was not found.

## Order book endpoints

| Venue | Finding |
|---|---|
| Binance spot | up to 5,000 levels; weight 5, 25, 50, or 250 by depth |
| Bitget | up to 1,000 levels; 20 requests per second per IP |
| MEXC | up to 5,000 levels; docs list weight 3, an announcement lists weight 10 and 10 per second (conflict) |
| Bybit, OKX, Gate | public order book endpoints exist; max levels, weights, rate limits not found |

## Measured spot depth (USD, within percent of mid, bid / ask)

Depth is the sum of price times size across levels.

| Coin | Venue | ±1% | ±2% | Time (UTC) |
|---|---|---|---|---|
| JCT | Bitget | 9,746.44 / 7,827.67 | 11,651.58 / 10,359.55 | 2026-11-05 17:48:49 |
| JCT | MEXC | 3,864.01 / 5,278.32 | 9,838.91 / 13,534.72 | 2026-11-05 17:48:49 |
| ARB | Bitget | 153,551.27 / 107,411.01 | 208,294.50 / 122,912.76 | 2026-11-05 17:48:57 |

A small-cap comparison, and market cap or pool measurements for ARB: not found.

## DEX

| Source | Finding |
|---|---|
| DexScreener | pool price, liquidity, volume, creation time; 300 per minute |
| GeckoTerminal | public pool API; docs about 10 per minute; a CoinGecko page says about 5 per minute (conflict); per-field check not found |
| DefiLlama | free pool yield list and token price endpoints; per-pool fields and rate limits not found |
| JCT BSC Uniswap JCT/USDT pool | liquidity 72,330.91 USD; 24h volume 1,868,658.02 USD; price 0.003125 USD; creation time 1762770571000 (Unix ms) |

## Derivatives

- Binance, Bybit, OKX publish funding and open interest. Binance and OKX document top-trader long/short ratios. Bybit's account ratio is not the same as a top-trader position ratio; its top-trader endpoint was not found. A third-party page shows a Binance top-trader ratio for JCT; coverage of all small coins: not found.
- Binance `@forceOrder` and `!forceOrder@arr` are liquidation snapshots, at most one per symbol per second, not complete. JCT actual pushes: not found. REST `allForceOrders` is no longer maintained; `forceOrders` is a user-scoped endpoint.

## Perp versus spot comparison for JCT (Bitget)

Open interest 1,153,292,027 JCT at mark 0.003125 = 3,604,037.58 USD. Spot 24h quote volume 9,624,127.50 USDT. Open interest is a stock and quote volume is a flow, so they are not directly comparable. The claim that perp is much larger than spot was neither confirmed nor rejected. The USDT to USD rate: not found.

## Region

A public GitHub commit reports HTTP 451 from a GitHub-hosted Azure runner calling Binance. Other sources' runner restrictions: not found.
