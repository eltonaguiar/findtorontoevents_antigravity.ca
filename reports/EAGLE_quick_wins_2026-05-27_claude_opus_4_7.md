# EAGLE: Quick Wins — 9 PRs to Execute Immediately
**Date:** 2026-05-27 02:26 EST | **Model:** Claude Opus 4.7 (via CommandCode)
**Branch:** `feat/EAGLE-2026-05-27-end-to-end-review`

---

## PR-1: Wire VIX<25 Gate into ETF Sector Emitter Production Path
**Impact:** HIGH | **Effort:** S | **Class:** ETF

**Why:** Backtest shows sector rotation + VIX<25 yields PF 3.22/Sharpe 1.63 vs live PF 1.48. VIX gate already coded in `vix_regime_gate.py` and `quality_gates.py` (env: ETF_VIX_GATE, default ON). Gap: NOT enforced in the `etf_sector_emitter.py` production path.

**Files:** `tools/etf_sector_emitter.py`, `audit_trail/vix_regime_gate.py`
**Acceptance:** ETF emitter checks VIX before generating picks. VIX≥25: skip or stamp vix_block=True.

---

## PR-2: EQUITY Universe Split — LARGE_CAP vs SPECULATIVE
**Impact:** HIGH | **Effort:** M | **Class:** EQUITY

**Why:** 8/18 EQUITY_SYMBOLS are speculative penny/meme. Research backtests use 30 clean LC (PF 2.82); live runs on narrow 18.

**Files:** `alpha_engine/config.py` (add LARGE_CAP_EQUITY_SYMBOLS 20-25), `alpha_engine/equity_strategies.py` (is_liquid_equity gate), `alpha_engine/scanner.py`
**Acceptance:** 0 emissions from NIO/LCID/RIVN/SNDL/GME/AMC as EQUITY.

---

## PR-3: CRYPTO Source Whitelist
**Impact:** HIGH | **Effort:** M | **Class:** CRYPTO

**Why:** 5+ sources (luxalgo 23% vol PF1.07, alpha_engine 12% PF0.99, quan_engine 10.5% WR35%) dilute 5 elite sources (mega_mutation PF2.29, dna_winner PF1.88).

**Files:** `alpha_engine/config.py` (CRYPTO_SOURCE_WHITELIST), `audit_trail/quality_gates.py` (whitelist gate)
**Acceptance:** Only dna_winner/mega_mutation/kimi/baby_strats_forward/aggregated_picks/claude_gainer_st emit.

---

## PR-4: Enable CRYPTO_ONCHAIN_MOMENTUM_ENABLED=1
**Impact:** MEDIUM | **Effort:** S | **Class:** CRYPTO

**Why:** Glassnode MVRV-Z for BTC/ETH. Backtest n=167, WR 47.3%, PF 1.28. Free data, unused.

**Files:** GHA env vars, verify `alpha_engine/crypto_onchain_momentum.py` in production path

---

## PR-5: Re-Derive COMMODITY PF/WR Post-COT Dedup
**Impact:** CRITICAL | **Effort:** M | **Class:** COMMODITY

**Why:** COT over-emission inflated headline PF 2.49. Real post-dedup: n≈5, WR 40%, PF 0.17. Dashboard STILL shows pre-dedup numbers.

**Files:** `audit_trail/dashboard_generator.py` (enforce 1-per-cycle), MySQL re-aggregation script

---

## PR-6: Add ADV Minimum Gate to Production Scanner
**Impact:** HIGH | **Effort:** S-M | **Class:** CRYPTO + EQUITY

**Why:** 179 CRYPTO symbols include illiquid memes. No runtime ADV gate anywhere.

**Files:** `alpha_engine/production_scanner.py`, `alpha_engine/scanner.py`
**Acceptance:** Symbols with 24h volume <$1M rejected at scanner level.

---

## PR-7: MD Dedup Skill
**Impact:** LOW (utility) | **Effort:** S | **Class:** INFRA

**Files:** `.claude/skills/md-dedup/SKILL.md`
**Acceptance:** `/md-dedup` identifies unique vs duplicate .md files, keeps shortest path.

---

## PR-8: Set FRED_API_KEY in GitHub Secrets
**Impact:** MEDIUM | **Effort:** S | **Class:** BOND + EQUITY + COMMODITY

**Why:** Unblocks economic data for yield curve, breakevens, macro context.

**Files:** GHA secrets, `alpha_engine/bond_data_fred.py`

---

## PR-9: Fix 4 Stale Resolved Incidents Showing OPEN
**Impact:** MEDIUM | **Effort:** S | **Class:** OVERALL

**Why:** INC #3, #11, #13, #18 resolved weeks ago but still show OPEN in MySQL tables.

**Files:** `tools/audit_pick_funnel/cli_track.py` (dedup logic)

---

## Implementation Order
1. PR-5 (COMMODITY dedup — critical data integrity)
2. PR-1 (ETF VIX gate — smallest, highest impact +0.5-1.0 PF)
3. PR-2 (EQUITY universe split +0.15-0.25 PF)
4. PR-6 (ADV gate)
5. PR-3 (CRYPTO source whitelist +0.1-0.2 PF)
6. PR-4 (On-chain enable)
7. PR-8 (FRED key)
8. PR-9 (Stale incidents)
9. PR-7 (MD dedup skill)
