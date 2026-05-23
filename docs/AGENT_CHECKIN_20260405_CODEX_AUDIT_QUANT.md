# Agent check-in — Codex audit quant bus (2026-04-05)

**Agent ID:** `codex-audit-quant-bus`  
**Focus:** Review `TESTING_PROTOCOL.MD`, analyze bus traffic, and consolidate the highest-signal improvements for hedge-fund-grade picks on `findtorontoevents.ca/audit`.

## Current scope

- Quant review of crypto and non-crypto performance integrity.
- Stronger backtesting rules before calling any picks "trusted" or "world-class."
- Confluence design that rewards independent agreement instead of duplicate symbol spam.
- Bus coordination with active peers to avoid collisions in `audit_trail/` and `audit_dashboard/`.

## Bus state observed

- `antigrav-dash-integrity` broadcast that the dashboard is **not real-money ready yet**.
  Main blockers: contaminated PROVEN tier history and unresolved "hype phantom" style distortions.
- `claude-noncrypto-drilldown` is focused on leveraged ETF decay shorts with materially better
  backtest quality than the weak generic non-crypto book.
- Existing peer docs confirm several hot files are already in motion:
  - `audit_trail/dashboard_generator.py`
  - `audit_dashboard/template.html`
  - `audit_trail/quality_gates.py`

## Quant conclusions

### 1. The immediate problem is not just strategy logic; it is truthfulness of the book

- Closed-pick corruption, source-less picks, zero-score coverage gaps, and symbol concentration
  make the current headline book too noisy to market as institutional-grade.
- The protocol already has many strong ideas; the missing piece is stricter enforcement at
  publication time.

### 2. Better backtesting should be more realistic, not just broader

- Require **next-bar-open fills**, not same-bar fills.
- Require **asset-specific cost models**: crypto fees/slippage, forex spread/carry, futures roll/tick normalization.
- Add **purged walk-forward with embargo** and **regime-stratified validation** before promotion.
- Add **live-close parity checks** against independent market data so corrupted entries cannot survive into analytics.

### 3. Confluence should mean independent evidence

- Current duplicate symbol-direction exposure creates false confidence.
- Confluence should require either:
  - 2+ independent systems, or
  - trust-weighted agreement from distinct families
- Multiple variants from the same family should be treated as **clones**, not extra conviction.
- Symbols with simultaneous LONG and SHORT exposure should be explicitly penalized or netted.

### 4. Best near-term edge themes from peer work

- **Bear-regime crypto SHORT bias** deserves higher priority than continuing a long-heavy book.
- **Technical confluence** remains promising when built from independent components (trend, momentum, volume, VWAP/market structure).
- **Leveraged ETF decay shorts** appear stronger than broad non-crypto directional exposure right now.
- **Rehabilitation-first inversions / symbol locks** are still valid, but only the repaired variant should be promoted.

## Recommended next actions

1. Fix scoring coverage to `>=95%` before hard-enabling `score < 40` as a gate.
2. Enforce `no source, no publish` and add entry-price sanity checks for both active and closed picks.
3. Add a portfolio-level uniqueness/conflict view to stop counting duplicate symbol-direction bets as diversified alpha.
4. Keep futures on probation until price normalization and contract resolution are provably correct.
5. Use the protocol addendum in `TESTING_PROTOCOL.MD` as the documentation baseline for all new promotion claims.

## Coordination notes

- I requested ideas and ownership checks from:
  - `antigrav-dash-integrity`
  - `claude-noncrypto-drilldown`
- I intentionally did **not** edit hot generator/template files because peers already own those lanes.
- Shared-doc locks were taken on `TESTING_PROTOCOL.MD` and `CHATWITHIT.MD` before editing.
