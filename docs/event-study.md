# Event study

Use `cryptodesk event-study --at 2026-11-23T13:55:00Z` for a post-event research read, not a scheduled collection or a fact record. It writes nothing. Options `--before`, `--after`, and `--baseline-days` set the minute windows and prior UTC days. T must be a past, minute-aligned UTC ISO timestamp ending in `Z`.

The output shows minute closes, returns, quote turnover and same-clock baseline multiples, followed by post-event returns, peak turnover and pre-event anomaly counts. The baseline uses the median and MAD of observations within 30 minutes of the same clock time on prior days; control-day counts exclude the day being scored. Compare the event count with those controls before calling it distinctive. A zero MAD is undefined, not an anomaly. Missing minutes and insufficient baselines are `-`.

Spot and perpetuals are different markets, not interchangeable measures. This read cannot establish causation, market-wide activity, or other venues' trading; an incomplete window can undercount anomalies. Binance access may require `CRYPTODESK_PROXY` in some regions; HTTP 451 or 403 means blocked, not zero activity. See [sources](sources.md#on-demand-reads).
