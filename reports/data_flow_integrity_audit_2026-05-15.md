# Data Flow Integrity Audit — May 2026

**Date:** 2026-05-15  
**Scope:** Cross-asset-class review of outcome resolution, stat updates (trust_score, forward_wr, symbol/strategy win rates), GitHub Actions coverage, and classification correctness.  
**Goal:** Identify zero/blank fields, misrouting, and broken feedback loops that prevent accurate per-asset-class and per-strategy performance measurement.

---

## 1. Outcome Resolution & Stat Update Flow

### Core Path
1. Pick emitted → stored in `at_raw_picks`
2. `universal_pick_resolver.py` (or equivalent) detects close → writes to `at_signal_outcomes`
3. `dashboard_generator.py` + `strategy_health` logic updates:
   - `strategy_health` table / JSON (per-strategy WR, PF, forward_wr, etc.)
   - Symbol-level tracking (symbol_track_wr, FWD WR%)
   - `asset_class_health` aggregate
   - `trust_score` / `at_issue_trust_score` enrichment

### Known Issues (Evidence-Based)
- **Low `at_signal_outcomes` coverage**: Historically ~0.08% (121 resolved out of 145k+). Even after resolver-v2 improvements, many asset classes still have thin resolved samples (BOND n=11 total, FUTURES effectively 0 in its own tile).
- **Forward_wr and trust_score enrichment is fragile**: `dashboard_generator.py` has multiple fallback paths (`at_issue_trust_score`, `forward_wr` from pick metadata). When the resolver does not write these fields, downstream calculations fall back to defaults or stale values.
- **Strategy_health and symbol win-rate updates are not uniformly populated** across all classes. Some strategies (especially older or low-volume ones in BOND/FUTURES/PENNY) have blank or zeroed `forward_wr` / `trust_score` fields in the live payload.
- **Penny/Meme and low-quality symbols** frequently appear with missing or zero `symbol_track_wr` because they are emitted by many different scanners without consistent tracking.

**Verdict**: The feedback loop (close → update strategy/symbol stats → influence future scoring) is **partially broken** for thin or noisy asset classes. This directly contributes to the "why aren't win rates higher?" problem when good signals (Polymarket, Kalshi, CopyTrader) exist but the system cannot reliably measure or promote them.

---

## 2. Asset Class Classification Correctness

### Current Logic (`dashboard_generator.py:_derive_asset_class`)
- Strong crypto lock-in first (good).
- Explicit =F handling with `_COMMODITY_ROOTS` vs `_INDEX_FUTURES_ROOTS` (improved after historical ZN=F → BOND bugs).
- Hard overrides for known BOND symbols.

### Remaining / Historical Flaws
- **FUTURES tile is starved**: Commodity futures (CT=F, GC=F, HG=F, NG=F, etc.) are correctly routed to COMMODITY. This leaves the FUTURES tile with almost only financial futures (ES, NQ, ZN, 6E, etc.), which have near-zero activity and no strong edge. The classification is *correct* but the **business split** creates a misleading "FUTURES" asset class with n≈0.
- **Penny/Meme leakage**: Low-quality equities are still emitted into both EQUITY and CRYPTO tiles by multiple scanners (community_penny_volume_surge, goldmine_meme, etc.). This pollutes parent-class stats.
- **No runtime liquidity/ADV gate** at emission time for many low-quality symbols → bad data enters the system and only gets partially filtered later.

**Verdict**: Classification has improved, but the **downstream effect** (FUTURES appearing dead, Penny/Meme dragging EQUITY/CRYPTO) is still present because the routing + emitter logic was never fully cleaned up after the big triage.

---

## 3. GitHub Actions Coverage per Asset Class

- **COMMODITY**: Dedicated `bond-agent.yml` style jobs + COT-specific workflows. Relatively good coverage.
- **EQUITY**: `non_crypto_agent` + equity-specific scanners. Decent.
- **ETF**: Relies on generic non-crypto + `etf_sector_emitter.py`. Coverage is lighter.
- **CRYPTO**: Heavy (many scanners), but noisy.
- **FOREX / BOND / FUTURES**: Very thin dedicated GHA jobs. Most rely on generic non-crypto paths that have lower priority and fewer validation steps.
- **Penny/Meme**: Almost no dedicated validation jobs — they ride along with whatever scanner emits them.

**Missing**: Systematic per-asset-class "health check" jobs that verify `at_signal_outcomes` population, forward_wr freshness, and trust_score distribution for that class.

---

## 4. Zero / Blank Data Points by Asset Class

From `dashboard_data.json` (2026-05-15) and subagent reports:
- **BOND**: n=11 resolved (extremely low). Many strategy-level forward_wr / trust fields blank or defaulted.
- **FUTURES**: n=0 in its own tile (misleading).
- **PENNY/MEME**: High volume of emissions but very low resolved outcomes with usable forward_wr / symbol_track_wr. Many "0/0" or blank win-rate entries.
- **FOREX**: Thin resolved sample; several strategies show blank or near-zero forward metrics.
- **COMMODITY**: Surface numbers look good, but after COT deduplication the effective independent n for the flagship strategy collapses dramatically.

---

## 5. Recommendations (Actionable)

1. **Strengthen the resolver → stats update path** so that every resolved outcome reliably writes `forward_wr`, `trust_score`, and per-symbol/per-strategy win rates (even for low-volume classes).
2. **Add per-asset-class data quality GHA jobs** that alert on blank forward_wr % or trust_score distribution anomalies.
3. **Fix emitter leakage for Penny/Meme** (hard upstream filter + CATEGORY_RISK enforcement) so they stop polluting EQUITY and CRYPTO stats.
4. **Reconsider the FUTURES vs COMMODITY split** — either merge financial futures into a unified "Futures CTA" tile or clearly label the current FUTURES tile as "Financial Futures (low activity)".
5. **Make HyroTrader, Polymarket, and Kalshi** first-class citizens in the outcome tracking and trust scoring pipeline (currently they are scoring add-ons, not primary measured strategies).

---

## 6. Impact on Win-Rate Visibility

Because of the above gaps, even when good external signals (top Polymarket/Kalshi traders, quality CopyTraders) are present, the system often cannot:
- Accurately measure their forward performance (low resolved n + blank forward_wr).
- Promote them with proper trust_score.
- Show clean per-asset-class statistics in `/audit`.

This is one of the structural reasons win rates per asset class appear lower than the "smart money" data would suggest.

---

**This report should be read alongside the 8 asset-class 90-day plans and the 4 strategy-type assessments.** It explains *why* some of the recommended fixes (especially for BOND, FUTURES, PENNY_MEME, and the prediction-market layers) are necessary before those classes can contribute real, measurable edge.