# Hedge-Fund Grade Pick Quality Audit

Date: 2026-04-06

## Scope

- Live audit payload: `audit_trail/data/dashboard_payload.json`
- Dashboard mirror: `audit_dashboard/data/dashboard_data.json`
- Smart-picks engine output: `alpha_engine/data/smart_picks.json`
- Active-book analysis: `tools/data/audit_active_book_analysis.json`
- Score-vs-PnL analysis: `tools/data/score_pnl_analysis.json`
- External exports:
  - `C:\Users\zerou\Downloads\antigravity_all_picks_2026-04-06.csv`
  - `C:\Users\zerou\Downloads\antigravity_closed_picks_2026-04-06.csv`
  - `C:\Users\zerou\Downloads\antigravity_active_picks_2026-04-06.csv`
  - `C:\Users\zerou\Downloads\paper-trading-balance-history-2026-04-06T21_36_13.442Z.csv`
  - `C:\Users\zerou\Downloads\ejaguiar1_stocks_apr62026_extract.sql`

## Current State

### Live `/audit` payload

- Active picks: 58
- Smart picks in payload: 0
- Recent closed picks: 3500
- Verified Alpha active count: 51
- Verified Alpha smart count: 0

Active asset mix from `dashboard_payload.json`:

- Crypto: 55
- Forex: 2
- Equity: 1
- Commodity: 0
- Futures: 0
- ETF: 0

Closed asset mix from `dashboard_payload.json`:

- Crypto: 2855
- Equity: 471
- Forex: 147
- Commodity: 12
- ETF: 12
- Futures: 3

### Exported CSVs

`antigravity_active_picks_2026-04-06.csv` does not match the live payload:

- Active picks in CSV: 110
- Crypto: 58
- Equity: 47
- Forex: 4
- Sports: 1

This means there are at least two materially different “truth layers” for the active book.

### Smart-picks feed mismatch

- `dashboard_payload.json -> picks.smart_picks`: 0
- `alpha_engine/data/smart_picks.json -> picks`: 5 crypto rows

Only 2 of those 5 feed picks also appear on the live active book:

- `LINKUSDT` / `breakout_b_ml`
- `REDUSDT` / `tsmom_volscaled`

The other 3 feed picks are not on the current `/audit` active set. The dashboard is embedding two different smart-pick concepts:

- live smart picks derived from `passes_smart_gate(...)`
- raw smart-picks feed from `alpha_engine/data/smart_picks.json`

## Main Findings

### 1. The active-book score is not working on the current live book

From `tools/data/audit_active_book_analysis.json` and `tools/data/score_pnl_analysis.json`:

- Active score vs unrealized PnL Pearson: `-0.23466`
- Active score vs unrealized PnL Spearman: `-0.12065`
- Aggregate active unrealized PnL: `-21.26%`
- Active mean unrealized PnL: `-0.3666%`

The current active book is not just weakly ranked. It is slightly inversely ranked.

### 2. Closed-book scoring has signal, but the live routing layer is not preserving it

Closed-book evidence is real:

- All closed picks: top score quartile WR `63.04%` vs bottom quartile `34.66%`
- Crypto smart-score Spearman vs PnL: `0.23426`
- Smart-at-signal-time closed picks: `78.78%` WR, `+1.4585%` mean PnL

So the system knows something in hindsight. The problem is that the live active book does not resemble the historical winners.

### 3. The live smart gate is effectively shut

Running `evaluate_smart_gate_funnel(...)` on the 58 live active picks:

- Passes: `0`
- Failures:
  - `score_floor`: 47
  - `anti_overfit`: 7
  - `active_gate`: 4

The gate is not selecting. It is only rejecting.

### 4. Verified Alpha is overrepresented but not delivering clear live edge

Live payload:

- Verified Alpha = `51 / 58` active picks = `87.9%`
- Verified Alpha smart picks = `0`

Closed overlap slice in `tools/data/score_pnl_analysis.json`:

- `recent_closed_verified_alpha_pool_overlap`: `n=322`
- Score quartile WR spread: `-6.66pp`
- Smart-score top minus bottom mean PnL: only `+0.1582pp`

Conclusion: the current Verified Alpha badge is too broad to act as a premium execution cohort.

### 5. Too many active strategies have no closed-book proof

From `tools/data/audit_active_book_analysis.json`:

20 active strategies have zero closed matches, including:

- `breakout_b_ml`
- `contrarian_consensus_flip`
- `regime_terminal`
- multiple `super signal (...)` variants
- `tsmom_volscaled`

That is not hedge-fund routing. That is live capital being allocated to unproven or unjoined strategy identities.

### 6. Non-crypto is still structurally weak

Closed-book asset-class performance from the live audit feed:

- Crypto: `49.7%` WR, `+0.3320%` mean PnL
- Equity: `35.46%` WR, `-0.7788%`
- Forex: `31.29%` WR, `-0.2793%`
- Commodity: `8.33%` WR, `-0.6966%`
- ETF: `41.67%` WR, `-0.9511%`
- Futures: `0.0%` WR, `-0.4489%`

The repo already claims crypto-first policy in several places. The realized data still says the non-crypto stack is not ready for equal footing.

### 7. The paper-trading record is close to noise

From `paper-trading-balance-history-2026-04-06T21_36_13.442Z.csv`:

- 34 realized closes
- Win rate: `52.94%`
- Net realized PnL: `-2.1889 USD`
- Approx ending balance: `997.8111 USD`
- Max drawdown: `11.4982 USD`

That is not a robust live edge. It is coin-flip behavior with friction.

### 8. The SQL dump confirms the same pattern: narrative alpha is stronger than realized alpha

The SQL review in `docs/EJAGUIAR1_SQL_EDGE_REVIEW_2026-04-06.md` is directionally correct:

- upstream research tables and live execution tables are being mixed
- impossible TP/SL geometry still exists in live-style rows
- PnL scaling/import normalization issues exist
- consensus quality is overstated

That matches what the current dashboard payload is showing.

## Code-Path Contradictions

### A. Two smart-picks systems disagree

`audit_trail/dashboard_generator.py` does both:

- embeds `smart_picks_feed` from `alpha_engine/data/smart_picks.json`
- separately computes `picks.smart_picks` from `passes_smart_gate(...)`

These are not the same portfolio.

### B. The smart-picks engine demotes `elite_score`, but the audit says elite still matters in non-crypto

`alpha_engine/smart_picks_engine.py` says:

- elite score is “noise” and only a tiebreaker

But `tools/data/score_pnl_analysis.json` shows:

- `elite_score` is the strongest non-crypto Spearman metric at `0.34478`

That means the ranking policy is over-generalizing from crypto evidence and throwing away the best non-crypto separator.

### C. The active book is dominated by low-score rows

Live payload score bins:

- `<40`: 39
- `40-59`: 14
- `60-69`: 5
- `70+`: 0
- zero-score rows: 30

If the historical sweet spot is around score `60-69`, the current live book is mostly outside the good zone before any market move happens.

## Hedge-Fund Grade Fixes

### 1. Unify the truth layer

Pick one canonical portfolio object for production:

- `candidate_book`
- `approved_active_book`
- `approved_smart_book`

Do not mix:

- `alpha_engine/data/smart_picks.json`
- `payload["picks"]["smart_picks"]`
- CSV exports with different active counts

until they reconcile to the same IDs.

### 2. Move from “score everything” to “approve very little”

Hard production rule:

- no promotion to active or smart without joined realized evidence
- route by `strategy x symbol` first
- fall back to `strategy x asset_class`
- only then to global strategy stats

If a strategy has zero closed-book joins, it should go to paper or incubator, not the live active book.

### 3. Split scoring by asset family

Current evidence says one score language is too blunt.

Use separate calibrated rankers:

- crypto ranker: smart score / trust / forward WR
- non-crypto ranker: elite score + symbol-level realized edge + catalyst/liquidity gates

Do not let the crypto-derived policy automatically suppress non-crypto signals if non-crypto has a different predictor structure.

### 4. Tighten Verified Alpha

Verified Alpha should require a stricter cohort definition:

- auditable source family
- minimum sample size
- recent non-decayed edge
- positive symbol- or family-level realized expectancy

The current `87.9%` active-book share is too broad to be informative.

### 5. Replace score-floor-only gating with expected-value gating

Instead of “score >= threshold”, require:

- expected value > 0 after fees/slippage
- forward WR floor
- profit factor floor
- max drawdown sanity
- geometry sanity
- symbol concentration and duplicate-family caps

This will cut volume but improve quality.

### 6. Add a promotion ladder

Suggested route:

1. Idea candidate
2. Paper-tracked candidate
3. Symbol-validated candidate
4. Active eligible
5. Smart eligible
6. Capital weighted

Most of the current pain is caused by jumping from raw signal generation straight to active display.

### 7. Reweight the current active book immediately

Based on the present audit:

- keep crypto as the primary live asset family
- demote broad non-crypto publication until non-crypto routing is proven
- suppress active strategies with zero closed joins
- suppress score `0-39` rows from headline surfaces
- quarantine “Verified Alpha” rows that fail realized symbol/family checks

## Recommended First Implementation Batch

1. Reconcile the smart-picks truth layer so `smart_picks_feed` and `picks.smart_picks` cannot diverge silently.
2. Add a pre-publication rule: no active pick with zero joined closed-book record unless explicitly marked incubator.
3. Split ranking weights by asset family and restore non-crypto use of `elite_score` where it is empirically strongest.
4. Narrow Verified Alpha to a real premium cohort instead of an umbrella label.
5. Add an expected-value approval gate and duplicate-family collapse before picks hit `/audit`.
