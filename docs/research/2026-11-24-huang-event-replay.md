# Nvidia / Huang reinstatement replay — 2026-11-24

Scope: were there public clues before the 2026-11-23 13:55Z press release, and what do they teach the collection and analysis process. Measured values and timestamps below keep their values; the classification and proposals are our own account and may be edited. All times UTC unless marked. News items are attributed claims, not verified facts. Raw responses are not stored in the repo ([out of scope](../../AGENTS.md#out-of-scope)); Yahoo 1-minute data expires after about 7 days, Binance and Polymarket histories can be re-fetched.

## Result

- **T0 is 2026-11-23 13:55:00Z.** Nvidia's own release feed (`nvidianews.nvidia.com/releases.xml`) dates the reinstatement release 13:55:00 GMT. NVDA premarket, BTC and the Polymarket contracts all moved in or just after that minute. The 8-K (13:57:54Z) and every media story read (earliest 13:59:23Z) came later. The `pubDate` is a whole minute like the feed's other releases, so it may be a scheduled time rather than the push time to the second.
- **No clue that predicts the timing was found.** Read sources before T0 pointed away from reinstatement, 1-minute market data shows nothing distinctive in the hour before T0, and prediction markets priced reinstatement at 3% to 12% (near-term contracts) at 13:54Z.
- Public pressure existed (Trump, Musk, petition) but gave direction, not timing. The board vote date is 11-22 per the 8-K; the vote time is unknown.

## Timeline

| Time | Event | Status |
|---|---|---|
| 11-12 13:52:41 | 8-K: resignation accepted 11-11, Kress interim CEO | read (SEC) |
| 11-13 01:17 | WIRED: employees urge the board to bring Huang back | read |
| 11-15 19:25 | Fox Business: Bessent calls for an outside CEO | read |
| 11-15 23:47 | Cointelegraph, citing FT: Huang discusses a return. FT original HTTP 403 | read; FT unread |
| 11-16 19:05 | Decrypt: Trump "would certainly not mind" Huang returning | read |
| 11-16 23:50 | Cointelegraph: board not considering return, per CNBC and ABC sources | read |
| 11-17 21:20 | Nvidia Q3 results released (feed `pubDate`) | read |
| 11-17 22:39 | Decrypt headline: board shuts down comeback | headline only |
| 11-20, time unknown | Trump tells reporters Huang should apologise and go back | secondhand; Reuters HTTP 401 |
| 11-22 15:31 | CBS video uploaded; transcript published 17:16Z. Bessent declines to say whether Huang should return; says the administration contacted interim management, lead directors and lawyers about possible noncompliance | read |
| 11-22 17:20:20 | Trump post blaming Democrats for market losses; does not mention Huang | read |
| 11-22, time unknown | Board vote (8-K: "On November 22") | read; time unknown |
| 11-23 02:54:45 | Trump post: "I hope the Board of Nvidia rehires Jensen Huang" (Truth Social API) | read |
| **11-23 13:55:00** | **Nvidia release** | read |
| 11-23 13:57:54 | 8-K accepted | read |
| 11-23 13:59:23 | CNBC `published_time` | read (meta) |
| 11-23 14:07:17 | Trump post: board made the "correct and proper decision" | read |
| 11-23 14:08 | Bloomberg report on Trump's push | lead only (paywall) |
| 11-23 14:17 / 14:21 / 14:36 | Fortune / TechCrunch (6:21 AM PST) / LA Times | read (meta) |
| 11-23 17:40 | Bloomberg exclusive: decision Sunday afternoon after Trump pressure; senior leaders informed at the last minute; anonymous sources | lead only; unverified |

Trump later told CNBC "I spoke to them and I convinced them" (via a CBS article updated 21:02Z); the contact time and causation are uncorroborated. Nvidia's release cites "input from senior levels of the United States government" without naming anyone; no read source identifies the input with Trump's or Bessent's account. A search result reported WSJ as an early source of the reinstatement; not found or read, unverified.

## Market data before T0

Window 11-22 20:00Z to 11-23 13:54Z. Method: absolute 1-minute log return and USDT turnover from Binance spot, robust z-score (median/MAD) against the same clock minute ±30 minutes over the previous 7 days, flag if z>6. The baseline includes the 11-21 crash day, which inflates control-day counts; the comparison is conservative.

| Window ending | BTC flags (all / last 60 min) | ETH flags (all / last 60 min) |
|---|---|---|
| 11-17 | 76 / 2 | 28 / 0 |
| 11-18 | 30 / 1 | 25 / 0 |
| 11-19 | 18 / 0 | 17 / 0 |
| 11-20 | 40 / 2 | 34 / 4 |
| 11-21 (crash) | 237 / 26 | 206 / 14 |
| 11-22 | 40 / 0 | 22 / 0 |
| **11-23** | **17 / 2** | **5 / 0** |

- 11-23 is not distinctive. The largest pre-T0 turnover spike was 11-23 03:20–03:21Z (BTC spot 8.0M and 20.2M USDT; about 19 times the median minute of that hour). Control days show 3.4 to 17.7 times in the same hour. Its cause is unknown; it came about 25 minutes after the 02:54:45Z Trump post, and the post minute itself shows no change (BTC 0.66M, median 0.73M).
- 13:50–13:54Z: NVDA stayed within 135.85–136.25; BTC spot turnover 0.3–0.8M per minute.
- NVDA premarket: 09:00Z already 135.65 versus about 125.8 at the Friday regular close (about +8%); 13:54Z close 135.98. Yahoo has no bars from 11-21 01:00Z to 11-23 08:59Z, so when the move happened is unknown.
- Yahoo `BTC-USD` and `ETH-USD` volume is zero in about 70% of minutes and its units are unverified; do not use it. Its earlier "first anomaly" readings were discarded.

Reaction (reference only):

| Minute | NVDA close | BTC spot turnover | BTC perp turnover | BTC spot close |
|---|---|---|---|---|
| 13:54 | 135.98 | 0.8M | 15.2M | 61,125.86 |
| 13:55 | 149.56 (+10.0%) | 13.4M | 126.6M | 61,665.16 |
| 13:56 | 153.58 | 54.2M | 574.7M | 62,416.01 |

Turnover is USDT. Earlier figures of 15M, 127M and 575M are the perpetual contract (`fapi`), not spot. BTC reached about 64,603 at 14:25Z and the day closed near 61,271 (earlier live reads).

## Prediction markets

Polymarket event "Jensen Huang rejoins NVIDIA by...?" (id 1374448). Yes price from `clob.polymarket.com/prices-history`, 1-minute. Whether the series is trade price or midpoint, and the volume, were not checked. All four contracts resolved Yes at 16:00–16:01Z. The 2027-03-31 contract returned no history.

| Last point at or before | By 11-30 | By 12-31-2026 | By 12-31-2027 |
|---|---|---|---|
| 11-16 12:00 | 5.9% | 12.0% | 37.5% |
| 11-18 12:00 | 2.5% | 8.2% | 33.5% |
| 11-20 00:00 | 1.3% | 5.1% | 27.5% |
| 11-22 12:00 | 1.6% | 6.0% | 31.5% |
| 11-23 02:50 | 1.8% | 6.8% | 33.5% |
| 11-23 06:00 | 3.4% | 11.0% | 36.5% |
| 11-23 13:54 | 3.1% | 11.7% | 37.5% |
| 13:55 / 13:56 / 13:57 | 3.2 / 18.9 / 89.1% | 10.5 / 23.4 / 87.7% | 36.5 / 40.0 / 89.5% |

- No one-minute move of 2 points or more in the 12-31-2026 contract between 11-18 and T0. The 13:55 minute barely moved; the jump is at 13:56–13:57.
- Prices rose from 03:10Z to 06:00Z (11-30 contract 1.8% to 3.4%); the cause is not established.
- Kalshi: the first page of its events (200, more pages exist) held only "When will Jensen Huang leave as Nvidia CEO?" and "...leave the Nvidia board?" (finalized). No rejoin market was seen; not exhaustive and no price history queried.
- A new Polymarket market on a further removal or resignation (id 1448088) was created at 15:02Z on 11-23. It is after T0 and not part of this replay.

## Classification

| Class | Finding |
|---|---|
| A. No timing clue | Yes for the 13:55Z release. Read news, market data and prediction markets give no timing signal. |
| B. Clue existed, not collected | Not found. NVDA and futures added no clue before T0. |
| C. Collected, not weighted | Yes. 59 related headlines were in the repo before T0, including Trump's 11-23 call (collected 04:13Z). The 11-23T1220Z analysis had no list of pending external events. |
| D. Read, misread | None found in this replay. |

## Not established

- Board vote time; when Trump or White House staff contacted directors; the source of the "senior levels" input.
- Bloomberg bodies (paywall), Reuters (401), FT (403), Axios and Quartz (403), GlobeNewswire (403), Decrypt 11-17 bodies, CoinDesk 11-23 13:53 live post.
- First public report of the reinstatement. The Nvidia feed time is the earliest primary time found.
- The Decrypt 11-23 13:34Z note (read portion) reports emergency market support in Korea, Taiwan and China; a single outlet, not corroborated, and it does not mention the reinstatement in the portion read.

## Proposals (not adopted; owner decision needed)

1. Add a "pending external events" section to the analysis template: unresolved binary events, last evidence read with its time, and which conditions the event would invalidate. No probabilities.
2. An on-demand event-study script that prints per-minute BTC/ETH spot and perp turnover and returns around a given UTC time. No scheduled collection.
3. A forecast register: record each short-term probability when written, score it later. Quantifies the weak short-term calls of 11-20 and 11-23.
4. Not recommended: collecting NVDA or index futures. They gave no clue here and fall outside the BTC and ETH scope.
