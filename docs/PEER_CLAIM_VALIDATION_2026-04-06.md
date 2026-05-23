# Peer Claim Validation

Date: 2026-04-06

## Scope

This note validates recent peer claims against:

- `audit_dashboard/data/dashboard_data.json`
- array: `picks.recent_closed`

The key issue was not simple arithmetic. It was methodology drift.

## Agents Used

Sub-agents deployed:

- `Harvey` — independent stat recomputation and claim verification
- `Halley` — failure-mode / mismatch investigation

`Harvey` completed and confirmed the core mismatch cause: different row filters and timestamp parsing.

## Methodology

### Raw source

- raw `recent_closed` row count: `3500`

### Strict parser methodology

Filters:

- require timestamp from `closed_at` or `exit_time` or `closedAt` or `entry_time`
- require timestamp to parse via Python `datetime.fromisoformat(ts.replace('Z', '+00:00'))`
- require numeric `pnl_pct`

Result:

- usable rows: `3198`
- dropped rows: `302`

Why rows were dropped:

- many timestamps are not ISO-8601
- examples:
  - `2026-04-06 16:15:19 EST`
  - `2026-04-05T19:32:53 EST`
  - `2026-04-06T05:09:13 EST`

The dropped rows are concentrated in:

- `stocks_competition`
- `ml_bg_system_f`

### Timezone-normalized methodology

Second pass:

- same source array
- same numeric `pnl_pct` requirement
- normalize ` EST -> -05:00`, ` EDT -> -04:00`
- then parse with `datetime.fromisoformat`

Result:

- usable rows: `3500`

This is the broadest defensible methodology currently available without inventing timestamps.

## Findings That Survive Both Methods

### 1. Thursday is bad, not best

Strict sample (`n=3198`):

- Thursday: `27.7%` WR, avg PnL `-1.0916%`

Timezone-normalized sample (`n=3500`):

- Thursday: `26.96%` WR, avg PnL `-1.2465%`

Crypto-only in normalized sample:

- Thursday: `27.03%` WR, avg PnL `-1.1417%`

Verdict:

- any claim that Thursday is the best day from this source is not consistent with either reproducible method above

### 2. LONG outperforms SHORT

Strict sample:

- LONG: `48.4%` WR
- SHORT: `31.4%` WR

Normalized sample:

- LONG: `47.2%` WR
- SHORT: `31.4%` WR

Verdict:

- claims that SHORT is massively outperforming LONG in this source are inverted

### 3. `trust_score >= 5` is genuinely strong

Strict sample:

- `trust_score >= 5`: `69.5%` WR

Crypto-only strict sample:

- `trust_score >= 5`: `72.0%` WR

Normalized sample:

- `trust_score >= 5`: `68.4%` WR overall

Verdict:

- this is a robust finding

### 4. Score `60-69` is strong

Strict sample:

- score `60-69`: `58.8%` WR

Normalized sample:

- score `60-69`: `57.96%` WR

Crypto-only earlier pass:

- score `60-69`: roughly `59%`

Verdict:

- this band is clearly good
- whether it is the absolute best depends on whether you compare against a tiny higher-score bucket

### 5. Very high score buckets are too small to overinterpret

Strict sample:

- score `70-84`: `54` rows, `70.4%` WR
- score `80+`: `4` rows, `75.0%` WR

Verdict:

- these buckets are promising but too small to use as the only basis for global scoring changes

### 6. `has_conflict=true` is slightly positive, not a huge edge

Strict sample:

- conflict true: `49.3%` WR
- conflict false: `45.3%` WR

Verdict:

- enough to reject a harsh blanket conflict penalty
- not strong enough to justify a major positive bonus

## Why Peers Got Opposite Answers

Likely root causes:

1. **Different timestamp parsers**
   - strict ISO parsing drops 302 rows
   - permissive parsing keeps all 3500

2. **Different timestamp fields**
   - `closed_at` vs `exit_time` vs fallback to `entry_time`

3. **Different arrays**
   - `picks.recent_closed` vs other arrays in the same JSON

4. **Different metrics**
   - win rate vs average PnL vs cumulative PnL can tell different stories

5. **Different cohort definitions**
   - crypto-only vs all-asset
   - `70+` vs `70-84` vs `80+`

## Claim Matrix

### Confirmed or mostly confirmed

- `trust_score >= 5` is strong
- score `60-69` is a strong band
- `has_conflict=true` is not clearly harmful

### Refuted

- Thursday is the best day
- SHORT massively outperforms LONG
- Monday is the uniquely dominant day in this source
- score `80+` is clearly negative in any robust sense

## Practical Recommendation

When publishing analytics from `dashboard_data.json`, every message should include:

1. source file
2. exact array used
3. row count before filters
4. timestamp fields used
5. timestamp normalization rule
6. final usable row count

Without that, two agents can both be “using the same file” and still produce opposite conclusions.
