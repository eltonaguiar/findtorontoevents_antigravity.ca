# FOREX Pipeline — Proposed Quick Wins

**Audit date:** 2026-11-14  
**Auditor:** Quantitative Engineer  
**Asset class:** FOREX  
**Current state:** HARD_DISABLED since 2026-05-18, yet consensus bypass continues to emit toxic picks.

---

## Executive Summary

FOREX is not money-ready. The aggregate closed-book is **WR 36.6%, PF 0.48, PnL -27.78%**. The hard-disable flag (`FOREX_HARD_DISABLE=1`) exists in `quality_gates.py`, but `non_crypto_consensus.py` routes around it by emitting picks with `asset_class=FOREX` and `source_system=non_crypto_consensus`, which downstream consumers (`combined_confidence_strategy.py`, `smart_picks_engine.py`) ingest without checking the hard-disable log. Additionally, `forex_rsi2_mean_reversion` — already on `BLACKLISTED_STRATEGIES` in `alpha_engine/config.py` — is still present in `forex_copytrader_picks.json` and `multi_asset_picks.json`, and because `non_crypto_consensus.py` loads these files directly, blacklisted strategies re-enter the pipeline. 96.6% of stored picks have null PnL, indicating the resolver/price-fetch path is broken for FX. Duplication (4x USDCAD=X, 4x AUDUSD=X) means the consensus vote is not actually independent.

The fixes below are ordered by ROI: plug the leaks first, then fix the data, then decide whether to rebuild or retire.

---

## 1. TOP 3 QUICK WINS (< 1 day each)

### QW-1. Honor `BLACKLISTED_STRATEGIES` inside `non_crypto_consensus.py`

**What to do:**  
Add a hard filter in `non_crypto_consensus.py` that drops any pick whose `strategy` field appears in `alpha_engine/config.py::BLACKLISTED_STRATEGIES`. Do not rely on `_load_quality_blocks()` alone — that gate is statistical and needs n≥20 trades; a strategy already blacklisted at the engine level should never reach consensus.

**File/location:**  
- `copy_trader_intel/non_crypto_consensus.py`, after `_apply_quality_gate()` (~line 303) or inside `consensus_vote()` before counting votes.
- Also check `alpha_engine/config.py` line ~264 for the canonical list.

**Expected impact:**  
Stops `forex_rsi2_mean_reversion`, `myfxbook_retail_contrarian`, `ig_contrarian_sentiment`, and other known losers from being counted as "independent sources" in the consensus vote. This alone removes the majority of toxic FOREX consensus picks.

**Effort:** 2–4 hours (import config, add filter, run unit test).

---

### QW-2. Respect `FOREX_HARD_DISABLE` in consensus and downstream consumers

**What to do:**  
1. In `non_crypto_consensus.py`, skip any pick where `asset_class.upper() == "FOREX"` when the hard-disable is active (read `audit_trail/data/forex_hard_disable_log.json` or check env var `FOREX_HARD_DISABLE`).  
2. In `combined_confidence_strategy.py` and `smart_picks_engine.py`, add the same guard before ingesting `non_crypto_consensus_picks.json`.

**File/location:**  
- `copy_trader_intel/non_crypto_consensus.py` — add early-return guard in `run_consensus()`.
- `alpha_engine/combined_confidence_strategy.py` — skip FOREX picks when hard-disable is on.
- `alpha_engine/smart_picks_engine.py` — line ~518, remove or gate `non_crypto_consensus` from the active strategy list while `FOREX_HARD_DISABLE=1`.

**Expected impact:**  
Eliminates the bypass that makes PR #6's claim false. No new FOREX picks will be emitted, traded, or tracked until the disable is explicitly lifted by an operator.

**Effort:** 3–6 hours (3 files, plus integration smoke-test).

---

### QW-3. Deduplicate consensus votes by (symbol, direction) source uniqueness

**What to do:**  
In `non_crypto_consensus.py::consensus_vote()`, deduplicate inputs so that the same strategy cannot vote twice for the same symbol/direction. Currently `forex_copytrader_picks.json` and `multi_asset_picks.json` both contain identical `forex_rsi2_mean_reversion` rows, so one bad strategy counts as two "independent" votes. Change the vote counter to use `len(set(votes["buy_strategies"]))` (already tracked) but also ensure the input set is deduped by `(symbol, direction, strategy)` before voting.

**File/location:**  
- `copy_trader_intel/non_crypto_consensus.py`, inside `consensus_vote()` (~line 163).

**Expected impact:**  
Prevents a single bad strategy from manufacturing fake consensus by appearing in multiple JSON files. Restores the intended meaning of "≥2 independent sources agree."

**Effort:** 2–3 hours (add dedup logic, verify with existing test fixtures).

---

## 2. MEDIUM FIXES (1–3 days)

### MF-1. Fix the FOREX price resolver / PnL hydration path

**What to do:**  
96.6% of stored FOREX picks have `null` PnL. This means the resolver (`audit_trail/universal_pick_resolver.py` or `tools/forex_resolver_ab_replay.py`) is either not receiving live prices for FX symbols, or the price-fetch client does not handle Yahoo Finance FOREX tickers (`EURUSD=X`, `USDCAD=X`) correctly.  
- Verify that `yfinance` or the price backend returns data for `EURUSD=X`.  
- If the backend is crypto-centric (e.g., Binance), add a FOREX branch that hits Yahoo, Alpha Vantage, or OANDA.  
- Ensure `current_price` is written back to the pick record so PnL is computed as `(current - entry) / entry` (or inverse for JPY crosses/USD-quoting nuances).

**File/location:**  
- `audit_trail/universal_pick_resolver.py` — check FX price fetch path.
- `tools/forex_resolver_ab_replay.py` — test and fix replay logic.
- `tools/fix_forex_pnl_clamping.py` — verify clamping does not hide resolver failures.

**Expected impact:**  
Transforms 96.6% null-PnL rows into measurable data. Without this, the quality gate and blocklist are flying blind.

**Effort:** 1–2 days (debug fetch, add FX provider, test with 10 live symbols).

---

### MF-2. Replace contrarian-sentiment consensus sources with regime-filtered momentum

**What to do:**  
The two largest consensus sources are `ig_contrarian_sentiment` (WR 36.9%) and `myfxbook_retail_contrarian` (39.9%). Contrarian retail sentiment is not an edge in this dataset — it is a drag. Remove them from the default source set in `non_crypto_consensus.py`. Replace with a single regime-aware source: `regime_filtered_momentum.py` (already exists in `alpha_engine/`) or `forex_session_carry_momentum.py` (already exists in `mimo_strategies/`). Only add them back after they demonstrate WR ≥ 50% on n ≥ 30 out-of-sample trades.

**File/location:**  
- `copy_trader_intel/non_crypto_consensus.py` — comment out or remove the IG / Myfxbook loader paths (lines 267–270 and any scraper wiring).
- `alpha_engine/regime_filtered_momentum.py` — ensure it emits FOREX picks in the expected JSON shape.

**Expected impact:**  
Removes the two worst-performing signal streams. Raising the source floor from ~37% to ≥50% WR is the single biggest expected lift for consensus quality.

**Effort:** 1–2 days (source swap + backfill test).

---

### MF-3. Implement symbol-level duplication guard in storage

**What to do:**  
Prevent the same symbol from entering the active panel more than once per direction. The dashboard currently shows 4x USDCAD=X and 4x AUDUSD=X. Add a uniqueness constraint (or application-level check) in the pick ingestion pipeline: before appending a new pick, reject if `(symbol, direction)` already exists in `active_picks.json` or the DB with status `OPEN`.

**File/location:**  
- `alpha_engine/mysql_trading_sync.py` or `alpha_engine/scanner.py` — add pre-insert dedup.
- `audit_trail/dashboard_generator.py` — verify the guard surfaces in the audit payload.

**Expected impact:**  
Eliminates capital fragmentation and reduces noise in the active panel. Makes the consensus vote cleaner because downstream dedup is no longer needed.

**Effort:** 1 day (DB unique index or in-memory guard + test).

---

## 3. LONG-TERM FIXES (1–2 weeks)

### LF-1. Build a FOREX-specific forward-test lane with swap-cost accounting

**What to do:**  
The hard-disable lift criteria (see `forex_hard_disable_log.json`) require:  
- WR ≥ 55% on n ≥ 150 resolved picks  
- PF ≥ 1.5  
- PBO < 0.10  
- Post-cost expectancy positive after swap costs  

Create a dedicated forward-test environment (paper lane) that runs only candidate FOREX strategies, accounts for realistic spread + swap, and resolves picks daily. Use the existing `paper_trading/strategies/` framework but add an FX cost model (typical retail spread 1–2 pips, overnight swap ±0.5–2 pips depending on direction/broker).

**File/location:**  
- New: `paper_trading/strategies/forex_forward_lane.py`
- Update: `alpha_engine/benchmark_closed_ledger.py` to include swap-adjusted PF.

**Expected impact:**  
Provides the statistically valid sample (n=150) needed to lift the hard disable. Without this, any "fix" is guesswork.

**Effort:** 1–2 weeks.

---

### LF-2. Retire or refactor `multi_asset_copytrader_scraper.py` FOREX branch

**What to do:**  
`multi_asset_copytrader_scraper.py` (line 2472) still calls `scan_forex_rsi2_mean_reversion()`, which populates `multi_asset_picks.json` with blacklisted picks. Either:  
- (a) Remove the FOREX scan functions entirely, or  
- (b) Refactor them to use a vetted strategy list that is checked against `BLACKLISTED_STRATEGIES` at scrape time.

**File/location:**  
- `copy_trader_intel/multi_asset_copytrader_scraper.py`, lines 480–524 and 2472.

**Expected impact:**  
Stops the root cause of blacklisted strategy resurrection. Cleaner data in → cleaner consensus out.

**Effort:** 3–5 days (refactor + regression tests for remaining asset classes).

---

### LF-3. Per-symbol, per-direction edge tracking with automatic kill-switch

**What to do:**  
Currently the quality gate blocks strategies and symbols based on historical closed-pick stats, but the thresholds are static (`MIN_STRATEGY_WR = 0.35`). Build a dynamic kill-switch: if a `(symbol, direction)` pair falls below 40% WR over the last 20 trades, automatically hard-disable that specific pair and surface it in the audit dashboard. This prevents the JPY-cross BUY disaster ( Phase 2-C, -45.43% ) from repeating.

**File/location:**  
- `audit_trail/quality_gates.py` — new dynamic gate module.
- `audit_dashboard/dashboard_enhancements.js` — UI for blocked pairs.

**Expected impact:**  
Reduces the blast radius of a failing edge from asset-class-wide to symbol-specific. Protects capital while preserving any real edges that may exist in other pairs.

**Effort:** 1 week.

---

## 4. VERDICT: Is FOREX Salvageable?

**Short answer:** Not with the current pipeline. The combination of a bypassed hard-disable, blacklisted strategies voting in consensus, broken price resolution, and sub-40% source WR means the system is structurally unprofitable.

**What would it take to make it salvageable?**

1. **Plug the leaks first** (Quick Wins 1–3). If the hard-disable is real, enforce it everywhere. If it is not real, delete it and stop lying to the dashboard.
2. **Fix the data**. 96.6% null PnL means you have no feedback loop. A strategy pipeline without resolved PnL is a random-number generator.
3. **Raise the source floor**. Do not allow any source with WR < 45% into consensus. Currently the floor is 35% — that guarantees net-negative aggregate performance.
4. **Run a clean forward test** (LF-1). 150 resolved trades, swap-adjusted, on a single regime-aware strategy (e.g., session momentum + carry filter). If that lane hits WR ≥ 55% and PF ≥ 1.5, expand. If not, hard-disable FOREX permanently and reallocate compute.

**Cost/benefit estimate:**  
- Quick Wins: ~1 day, stops the bleeding.
- Medium Fixes: ~1 week, restores measurement and source quality.
- Long-term: ~2 weeks, delivers the evidence needed for a go/no-go decision.

If the forward lane fails, the rational choice is to **permanently retire FOREX** and redirect the scraper/consensus compute toward EQUITY or CRYPTO, where the edge is documented (EQUITY z=1.39, closer to significance; CRYPTO has volume and resolver infrastructure that works).

---

## Appendix: File Map for Implementers

| File | Relevance |
|------|-----------|
| `copy_trader_intel/non_crypto_consensus.py` | Consensus engine — add blacklist guard, dedup, hard-disable check |
| `alpha_engine/config.py` | `BLACKLISTED_STRATEGIES` canonical list |
| `alpha_engine/combined_confidence_strategy.py` | Downstream consumer of consensus — add FOREX disable gate |
| `alpha_engine/smart_picks_engine.py` | Active strategy list — gate `non_crypto_consensus` |
| `audit_trail/quality_gates.py` | Existing FOREX gates (SHORT-only, session, JPY-cross BUY kill) |
| `audit_trail/data/forex_hard_disable_log.json` | Disable rationale and lift criteria |
| `audit_trail/universal_pick_resolver.py` | Price resolution — likely broken for FX |
| `tools/forex_resolver_ab_replay.py` | FX-specific resolver replay test |
| `copy_trader_intel/multi_asset_copytrader_scraper.py` | Root source of blacklisted FOREX picks |
| `copy_trader_intel/data/forex_copytrader_picks.json` | Contains `forex_rsi2_mean_reversion` rows |
| `copy_trader_intel/data/non_crypto_consensus_picks.json` | Output — shows 4x duplication and 1v0 consensus |
