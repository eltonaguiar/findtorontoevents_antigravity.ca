# Crypto Golden Criteria Report

- Generated from: `audit_trail\data\dashboard_payload.json`
- Generated at UTC: `2026-03-27T21:42:30.110379+00:00`
- Closed crypto trades analyzed: `1964`
- Active crypto picks analyzed: `371`

## Metadata Gaps

- Direct HTF bias survives into closed crypto rows only `0.3%` of the time.
- Directional HTF/technical alignment is derivable on `64.9%` of closed rows and `100.0%` of active rows.
- `strong` is populated on `64.7%` of closed rows and `47.7%` of active rows.
- `A-viable` tagging coverage is `0.0%` on closed rows and `0.0%` on active rows.

## Cohort Windows

### Full Sample

- Trades: 1964
- Win rate: 49.8%
- Avg PnL: +0.09%
- Total PnL: +172.01%

### Last 7 Days

- Trades: 1816
- Win rate: 49.7%
- Avg PnL: +0.10%
- Total PnL: +179.70%

### Last 3 Days

- Trades: 1221
- Win rate: 46.8%
- Avg PnL: -0.40%
- Total PnL: -486.36%

### Last 1 Day

- Trades: 283
- Win rate: 34.3%
- Avg PnL: +0.98%
- Total PnL: +278.56%

## Metric Correlations

| Metric | Rows | Corr vs PnL % | Corr vs Win |
| --- | ---: | ---: | ---: |
| rr_ratio | 1221 | -0.110 | -0.042 |
| confidence_pct | 1221 | 0.078 | 0.093 |
| track_wr | 1221 | -0.053 | 0.309 |
| score | 1221 | -0.021 | 0.094 |
| ml_composite_score | 237 | -0.015 | 0.055 |
| agreement_count | 1221 | 0.005 | -0.044 |

### Score Buckets (Last 3 Days)

| Bucket | Trades | Win Rate | Avg PnL | Total PnL |
| --- | ---: | ---: | ---: | ---: |
| <40 | 607 | 42.7% | -0.06% | -38.22% |
| 40-54 | 373 | 47.2% | -1.47% | -548.19% |
| 55-69 | 194 | 58.8% | +0.42% | +80.92% |
| 70+ | 47 | 48.9% | +0.41% | +19.13% |

### Track WR Buckets (Last 3 Days)

| Bucket | Trades | Win Rate | Avg PnL | Total PnL |
| --- | ---: | ---: | ---: | ---: |
| <40 | 510 | 31.8% | +0.66% | +335.75% |
| 40-49 | 111 | 40.5% | -0.47% | -52.27% |
| 50-59 | 327 | 52.6% | -3.16% | -1033.52% |
| 60+ | 273 | 70.7% | +0.97% | +263.68% |

### Agreement Buckets (Last 3 Days)

| Bucket | Trades | Win Rate | Avg PnL | Total PnL |
| --- | ---: | ---: | ---: | ---: |
| 0 | 188 | 38.3% | -0.37% | -68.97% |
| 1 | 177 | 48.0% | +0.60% | +106.18% |
| 2 | 205 | 45.4% | -2.33% | -477.04% |
| 3-4 | 196 | 59.2% | +0.10% | +19.64% |
| 5+ | 455 | 45.3% | -0.15% | -66.18% |

### Trust Tiers (Last 3 Days)

| Bucket | Trades | Win Rate | Avg PnL | Total PnL |
| --- | ---: | ---: | ---: | ---: |
| PROVEN | 345 | 58.8% | +1.57% | +542.39% |
| RELIABLE | 353 | 35.7% | -0.08% | -27.09% |
| WATCH | 469 | 48.0% | -1.97% | -925.55% |
| UNTRUSTED | 10 | 20.0% | -3.12% | -31.23% |
| BANNED | 44 | 36.4% | -1.02% | -44.88% |

## Hypothesis Checks

- `score`: see the score buckets above. The sweet spot is where win rate and avg PnL both stay above baseline without running into overconfidence.
- `track_wr`: compare the track buckets above. This is the cleanest direct proxy for real track record.
- `multi-agree >= 3`: 651 trades, 49.5% WR, -0.07% avg PnL. Control cohort: 570 trades, 43.9% WR, -0.77%.
- `strong=True`: 228 trades, 71.1% WR, -3.65% avg PnL. Other labeled rows: 510 trades, 38.6% WR, -0.09%.
- `HTF/technical match to direction`: 344 trades, 63.4% WR, -2.25% avg PnL. Mismatch cohort: 398 trades, 35.7% WR, -0.28%.
- `A-viable`: no usable sample in the current payload. This is a metadata gap, not a negative result.

## Golden Criteria Candidates

### Candidate 1

- Rule: `40 <= score < 70, trust tier proven, agreement 1-2`
- Last 3 days: 91 trades, 68.1% WR, +6.62% avg PnL
- Full sample: 151 trades, 68.2% WR, +4.67% avg PnL

| Active Match | Dir | Score | Track WR | Agree | Trust | Source |
| --- | --- | ---: | ---: | ---: | --- | --- |
| WLDUSDT | LONG | 69 | 4.0% | 1 | PROVEN | super_signals |

### Candidate 2

- Rule: `trust tier proven, agreement 1-2`
- Last 3 days: 100 trades, 69.0% WR, +6.03% avg PnL
- Full sample: 182 trades, 68.7% WR, +4.02% avg PnL

| Active Match | Dir | Score | Track WR | Agree | Trust | Source |
| --- | --- | ---: | ---: | ---: | --- | --- |
| ALGOUSDT | LONG | 94 | 4.0% | 2 | PROVEN | super_signals |
| HBARUSDT | LONG | 94 | 4.0% | 1 | PROVEN | super_signals |
| OPUSDT | LONG | 86 | 4.0% | 1 | PROVEN | super_signals |
| TRXUSDT | LONG | 74 | 4.0% | 1 | PROVEN | super_signals |
| ONDOUSDT | LONG | 73 | 4.0% | 1 | PROVEN | super_signals |
| WLDUSDT | LONG | 69 | 4.0% | 1 | PROVEN | super_signals |
| DOTUSDT | LONG | 26 | 4.0% | 2 | PROVEN | super_signals |
| HBARUSDT | LONG | 24 | 100.0% | 1 | PROVEN | super_signals |

### Candidate 3

- Rule: `score >= 40, trust tier proven, agreement 1-2`
- Last 3 days: 100 trades, 69.0% WR, +6.03% avg PnL
- Full sample: 181 trades, 68.5% WR, +3.99% avg PnL

| Active Match | Dir | Score | Track WR | Agree | Trust | Source |
| --- | --- | ---: | ---: | ---: | --- | --- |
| ALGOUSDT | LONG | 94 | 4.0% | 2 | PROVEN | super_signals |
| HBARUSDT | LONG | 94 | 4.0% | 1 | PROVEN | super_signals |
| OPUSDT | LONG | 86 | 4.0% | 1 | PROVEN | super_signals |
| TRXUSDT | LONG | 74 | 4.0% | 1 | PROVEN | super_signals |
| ONDOUSDT | LONG | 73 | 4.0% | 1 | PROVEN | super_signals |
| WLDUSDT | LONG | 69 | 4.0% | 1 | PROVEN | super_signals |

### Candidate 4

- Rule: `40 <= score < 70, trust tier proven, agreement <= 2`
- Last 3 days: 117 trades, 68.4% WR, +5.28% avg PnL
- Full sample: 188 trades, 69.1% WR, +3.97% avg PnL

| Active Match | Dir | Score | Track WR | Agree | Trust | Source |
| --- | --- | ---: | ---: | ---: | --- | --- |
| WLDUSDT | LONG | 69 | 4.0% | 1 | PROVEN | super_signals |

### Candidate 5

- Rule: `trust tier proven, agreement <= 2`
- Last 3 days: 126 trades, 69.0% WR, +4.91% avg PnL
- Full sample: 219 trades, 69.4% WR, +3.53% avg PnL

| Active Match | Dir | Score | Track WR | Agree | Trust | Source |
| --- | --- | ---: | ---: | ---: | --- | --- |
| ARBUSDT | LONG | 96 | 4.0% | 0 | PROVEN | super_signals |
| ALGOUSDT | LONG | 94 | 4.0% | 2 | PROVEN | super_signals |
| HBARUSDT | LONG | 94 | 4.0% | 1 | PROVEN | super_signals |
| OPUSDT | LONG | 86 | 4.0% | 1 | PROVEN | super_signals |
| TRXUSDT | LONG | 74 | 4.0% | 1 | PROVEN | super_signals |
| ONDOUSDT | LONG | 73 | 4.0% | 1 | PROVEN | super_signals |
| WLDUSDT | LONG | 69 | 4.0% | 1 | PROVEN | super_signals |
| DOTUSDT | LONG | 26 | 4.0% | 2 | PROVEN | super_signals |
