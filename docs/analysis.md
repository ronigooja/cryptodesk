# Analysis

Analyses are written on demand by an agent in a session. There is no scheduled model call.

## Files

- Location: `analysis/`. When the count grows, group by month in subdirectories.
- Name: `<YYYY-MM-DD>T<HHMM>Z-<scope>.md`, for example `2026-11-06T1400Z-btc-eth.md`.
- Write-once. A new view is a new file. Fix only broken citations in old files, and note the fix at the end.
- Template: [TEMPLATE-major.md](../analysis/TEMPLATE-major.md).
- Language: English.

## Structure

Header block: generated time in UTC and UTC+8, scope, `Supersedes`, and the line `Not investment advice.`

Required headings, in order:

| Heading | Content |
|---|---|
| `## Facts` | Values from fact records or [daily series](data-model.md#daily-series), each cited |
| `## Inference` | Interpretation; each item ends with `based on:` and citations |
| `## Missing` | Needed data that is absent, stale, or not from a fact record |
| `## What would change this view` | Observable conditions |

## Citations

`[F:<id>@<fetched_at>]`, where `<fetched_at>` is that of the record in `data/latest/<coin>.json` when the analysis was written. The checker verifies the record exists in `data/latest` or `data/facts`.

News citations use `[N:<id>]` without an `@` timestamp, for example `[N:coindesk:3fa1c2b4d5e6]`, resolving to [news metadata](data-model.md#news-items). An optional `## Catalysts and news` section may appear between Facts and Inference; it contains reported claims, not fact records.

When scanning analysis citations, the checker ignores inline code spans, fenced code blocks, and unclosed news citation markers; closed malformed news IDs remain errors.

Daily citations use `[D:<series_id>@<YYYY-MM-DD>]`, resolving to a row in [daily storage](data-model.md#daily-series). Ranges use `[D:<series_id>@<YYYY-MM-DD>..<YYYY-MM-DD>]`; both endpoints must have rows, but intervening missing dates remain absent. The checker ignores daily citations inside code, as for facts and news.

## Rules

- When a number appears, cite a fact or daily series. Numbers from memory, chats, or news articles are not facts and go under Missing.
- When using daily series, cite `[D:...]`, state which source and day definition; never merge two sources.
- When using news, cite it as [N:<id>], describe it as reported, never as a fact, give the time relation (published_at versus the fact times) and never state causation as fact.
- When a fact is `missing`, cite it and say so; do not substitute another source silently.
- When two sources disagree, cite both and state the difference.
- When a fact's last confirmation exceeds its staleness limit in [metrics.md](metrics.md#registry), mark it stale; use [checked_at](data-model.md#time), not the observation time.
- When writing a time, give UTC and UTC+8.
- When quoting a scheduled release, take the time from [events/](events/).
- When a prior analysis is overturned, name it in `Supersedes`.
- When stating a lean (bullish, bearish, neutral), put it under Inference with its conditions, never under Facts.
- When writing analysis, do not give position size, leverage, entry, or stop levels; describe observable conditions only.

## Triggers

On user request, typically after macro releases, FOMC decisions, option expiries, or large price moves. When preparing an analysis, run the relevant group, then the checker, then write the file.

## Validation

The checker fails when a heading or the disclaimer is missing, a citation does not resolve, or a stored fact violates [data-model.md](data-model.md). It does not judge inference.
