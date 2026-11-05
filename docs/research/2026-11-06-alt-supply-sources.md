# Research 2026-11-06: altcoin supply and unlock sources

Write-once snapshot. Current state is in [sources.md](../sources.md). Findings are as reported by a read-only subagent on 2026-11-06; nothing here was independently re-run. "Not found" does not mean absent. Bn = billion, M = million.

## Identity

| Item | Finding |
|---|---|
| JCT | The user states it is Janction. Project docs list a BNB Chain contract `0xeA37A8DE1de2d9D10772EEB569e28Bfa5Cb17707`. CoinPaprika search lists an Ethereum contract `0xC477B6dfd26EC2460b3b92de18837Fd476Ea7549`. The ticker JCT is also used by other projects (for example Japan Content Token). |
| Comparison samples | ARB (CoinPaprika market cap about 1.069 Bn USD) and ORDER (about 7.99 M USD), both updated 2026-11-05 UTC. |

## Vendor free tiers

| Vendor | Free API, key, limits | Supply fields and unlock schedule |
|---|---|---|
| CoinGecko | Demo key, 10,000 calls per month, 100 per minute; a keyless public API also exists | total, circulating, max supply; free unlock API not found |
| CoinMarketCap | Basic key, 15,000 credits per month, 50 per minute; another official page lists 10,000 per month and 30 per minute (conflict) | three supply fields; free unlock API not found |
| CoinPaprika | free, no key, 20,000 per month, 10 per second per IP | free ticker has total and max supply, no circulating supply; unlock API not found |
| DefiLlama | free endpoints need no key; free quota not found | `/api/emissions` and `/api/emission/{protocol}` are paid; web unlock pages are free |
| Tokenomist | application-based free trial, 120 per minute, trial total not found | allocation, unlock events, daily emission; free availability of supply fields not found |
| CryptoRank | sandbox key, 10,000 credits per month, 400 per day, 10 per minute | unlock events API starts at a paid Pro tier |
| Messari | key required; docs list 200 per minute, product page lists 20 per minute (conflict); monthly quota not found | unlock API requires Enterprise |

## JCT supply as shown by vendors

| Source | Total / circulating / max | Update time |
|---|---|---|
| CoinPaprika API | 50 Bn / not returned / 50 Bn | 2026-11-05 17:48 UTC |
| CryptoRank page | 50 Bn / 11.49 Bn / 50 Bn | not found |
| KuCoin page | not found / 10.34 Bn / 50 Bn | page says as of 2026-11-05 |
| Holder.io citing CoinGecko | not found / 11,493,687,500 / 50 Bn | supply snapshot 2026-10-28 06:11 UTC |

Both circulating values (10.34 Bn and 11.49 Bn) were seen. A Phemex article says 10.34 Bn excludes six project multisig wallets as of mid-October 2026; project docs state 22.99% initial circulating share at TGE. These records do not show which basis KuCoin or CryptoRank use. The cause of the difference was not found.

## Unlock records

| Item | Finding |
|---|---|
| JCT 2026-11-10 | CryptoRank page: 1.17 Bn. Gate blog citing Tokenomics.com: about 1.177 Bn. Messari page: 1.2 Bn, four allocation categories. All are web pages; no free API returned this unlock. |
| ARB | CryptoRank page: 2026-11-16, 92.63 M |
| ORDER | DefiLlama page: 2026-11-02, 500,000; page price time 2026-10-30 |

## Holdings

- Janction docs list initial allocation: team 21.34%, foundation 18%, liquidity 4%. This is initial allocation, not current holdings.
- Tokenomist API has category allocations (free trial).
- A free structured source for current team, foundation, or market-maker holdings was not found.

## Terms (recorded as found; not tracked going forward)

CoinGecko site terms prohibit scraping and the free Demo plan has no commercial rights. Tokenomist docs: "personal or non-commercial, non-redistribution use only". CryptoRank sandbox is CC BY-NC-SA. CoinMarketCap pricing page says no data redistribution. Other sources: not found. The user decided not to track terms.
