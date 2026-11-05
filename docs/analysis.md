# Analysis

Analyses are written on demand by an agent in a session. There is no scheduled model call.

## Files

- Location: `analysis/`. When the count grows, group by month in subdirectories.
- Name: `<YYYY-MM-DD>T<HHMM>Z-<scope>.md`, for example `2026-11-06T1400Z-btc-eth.md`.
- Write-once. A new view is a new file. Fix only broken citations in old files, and note the fix at the end.
- Templates: [TEMPLATE-major.md](../analysis/TEMPLATE-major.md), [TEMPLATE-alt.md](../analysis/TEMPLATE-alt.md).
- Language: English.

## Structure

Header block: generated time in UTC and UTC+8, scope, `Supersedes`, and the line `Not investment advice.`

Required headings, in order:

| Heading | Content |
|---|---|
| `## Facts` | Values from fact records only, each cited |
| `## Inference` | Interpretation; each item ends with `based on:` and citations |
| `## Missing` | Needed data that is absent, stale, or not from a fact record |
| `## What would change this view` | Observable conditions |

## Citations

`[F:<id>@<fetched_at>]`, where `<fetched_at>` is that of the record in `data/latest/<coin>.json` when the analysis was written. The checker verifies the record exists in `data/latest` or `data/facts`.

## Rules

- When a number appears, cite a fact. A number without a fact goes under Missing.
- When a fact is `missing`, cite it and say so; do not substitute another source silently.
- When two sources disagree, cite both and state the difference.
- When a fact is older than its staleness limit in [metrics.md](metrics.md#registry), mark it stale in the text.
- When writing a time, give UTC and UTC+8.
- When quoting a scheduled release, take the time from [events/](events/).
- When a prior analysis is overturned, name it in `Supersedes`.
- When stating a lean (bullish, bearish, neutral), put it under Inference with its conditions, never under Facts.
- Do not give position size, leverage, entry, or stop levels.

### Rules for `alt`

- When a statement is about control, accumulation, or distribution by specific holders, put it under Inference and list the facts it rests on. It is never a fact.
- When the sample is small (single event, short history), state the sample count and do not present the result as statistical.
- When address labels are used, each needs evidence recorded in a fact; otherwise list the gap under Missing.
- When vendors disagree on supply, show all vendor values and the spread before any ratio is computed.
- When a coin has no spot market, state which venue sets price and use perp facts for price, marked as such.
- When describing fragility, report depth, slippage, and leverage facts; do not recommend sizing.

## Triggers

On user request, and typically after jobs or CPI releases, FOMC decisions, option expiry days, large 24h moves, and `alt` unlock events. The agent first runs the relevant group, then the checker, then writes the file.

## Validation

The checker fails when a heading or the disclaimer is missing, a citation does not resolve, or a stored fact violates [data-model.md](data-model.md). It does not judge inference.
