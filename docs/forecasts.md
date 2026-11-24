# Forecast register

The register records objectively resolvable yes/no judgments for later scoring, not trading advice. Only registered [daily series](data-model.md#daily-series) are eligible: their stored dated values provide reproducible outcomes without subjective interpretation. Past calls are not backfilled.

Each append-only `data/forecasts/<YYYY-MM>.jsonl` line is a JSON object with exactly:

- `id`: `fc:` and the first 12 SHA-1 hex characters of the UTF-8 JSON array `[made_at, analysis, series, op, threshold, date]`, encoded without spaces and with non-ASCII characters unescaped.
- `made_at`: UTC write time in `YYYY-MM-DDTHH:MM:SSZ`; the file month matches this timestamp.
- `analysis`: filename of an existing file in `analysis/` or `analysis/archive/`.
- `series`: registered daily series ID; `op`: `gt` or `lt`; `threshold`: finite decimal string.
- `date`: UTC `YYYY-MM-DD`, strictly after the `made_at` date; `p`: numeric probability from 0.01 to 0.99 inclusive, with at most four decimal places.

`cryptodesk forecast add --analysis FILE --series ID --op gt|lt --threshold DECIMAL --date YYYY-MM-DD --p PROBABILITY` appends one record; duplicate IDs are rejected. The statement is true only when the stored daily value for `date` is strictly greater (`gt`) or strictly less (`lt`) than the threshold; equality is false. When the row is absent, the forecast is open on or before its date and unresolved afterwards; missing values are never guessed.

`cryptodesk forecast score` derives output without storing scores. Resolved records receive Brier term `(p - outcome)^2`, where outcome is 1 for true and 0 for false; the report includes overall and per-analysis means and the always-50% baseline of 0.25. At least 20 resolved forecasts are required before drawing any conclusion about calibration.
