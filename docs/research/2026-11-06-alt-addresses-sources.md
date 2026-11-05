# Research 2026-11-06: altcoin holders, address labels, exchange flows

Write-once snapshot. Current state is in [sources.md](../sources.md). Reported by a read-only subagent on 2026-11-06; not independently re-run. No API keys were applied for and no holder snapshot was obtained.

## Quality note

The subagent could not uniquely confirm the project behind JCT (Japan Content Token also exists). It labeled Janction JCT as a "mid-cap comparison" and chose a PEPE variant with about 182,000 USD market cap as the small-cap comparison; neither is a valid comparison design. The top-20 holders, labeled-share, and unlabeled-share requests produced no data. Treat this snapshot as mostly "not found".

## Sources

| Source | Free tier, key, limits | Findings |
|---|---|---|
| Etherscan family and BscScan | free on selected chains, key, 3 per second, 100,000 per day | top holders endpoint is paid; address tag endpoint is Pro Plus |
| Solscan | free network-info endpoints | token holders is a key-required Pro endpoint; free quota, rate, labels, transfers not found |
| TronScan | key required for mainnet auth; anonymous heavily limited | holder, transfer, and tag endpoints exist; free quota not found |
| Blockscout | Pro API free tier needs a key, 100,000 credits per day, 5 per second | holders sorted by balance, address label field, transfers exist; coverage for the sample coins not tested |
| Covalent / GoldRush | key; 14-day trial, 25,000 credits, 4 per second | holders and transfers; vendor states it does not provide address labels |
| Moralis | docs say no self-serve free tier; older pricing page shows one (conflict) | holders, labels, transfers exist; trial quota not found |
| Alchemy / Helius | key; Alchemy free 30 M CU per month; Helius free 1 M credits per month, RPC 10 per second | free top-N, labels, exchange inflow coverage not found |
| Arkham | free API quota, rate, capability not found | not confirmed |
| Nansen | 100 trial credits, 10 per day refill, 15 per second and 300 per minute | holders cost 5 credits, exchange flows 1, labels 100 for a non-empty query |
| Bubblemaps / DeBank | Bubblemaps API starts paid; DeBank needs key and purchased units | free coverage not found |
| Dune / Flipside | Dune: free tier is browse-only; trial up to 14 days, 2,500 credits; Flipside status conflicting | not usable free |

## Labels

Nansen lists exchange, fund, and market-maker labels. Bubblemaps lists CEX, DEX, contract fields, and a community-submitted flag. Evidence per address, confidence, and free coverage of team labels: not found. Label names alone do not satisfy the evidence rule in [metrics.md](../metrics.md#rules).

## Exchange inflow

Nansen provides token flows aggregated by exchange category. Whether other sources can cover all exchanges by linking transfers to exchange address labels: not found.

## Locked versus circulating

Project docs list allocations and unlock plans; Etherscan shows a CMC-sourced circulating supply. A reliable method to classify addresses one by one as locked or circulating: not found.

## Scraping terms

Dune pricing lists internal-use data licensing for relevant plans. Other sources: not found. The user decided not to track terms.
