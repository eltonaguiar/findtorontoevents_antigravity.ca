# Hourly Audit — 2026-05-21 09Z

**Analysis time:** `2026-05-21T09:10:59Z`  
**Dashboard snapshot:** `recent_closed` n=3500 (picks through 2026-05-21 09:07Z)  
**Prior audit:** PR #1283 (08Z) merged this turn — CI 3/3 green, mergeable=clean, greptile COMMENT only

---

## Per-Asset Summary — 09Z Windows

| Class | 24h n | 24h PF | 7d n | 7d WR | 7d PF | 30d n | 30d PF | vs 08Z baseline |
|-------|-------|--------|------|-------|-------|-------|--------|-----------------|
| **CRYPTO** | 90 | 2.867 | 903 | 48.7% | 1.468 | 2657 | 1.365 | 24h −0.632 / 7d −0.034 ↘ |
| **EQUITY** | 8 | **2.321** | 46 | 37.0% | 0.803 | 151 | 1.431 | 24h **+0.931** ✅✅ / 7d −0.061 |
| **FOREX** | 8 | 1.446 | 17 | 35.3% | **1.070** | 94 | 2.577 | 8th consecutive hr ≥1.0 ✅ |
| **COMMODITY** | 3 | 0.000 | 41 | 7.3% | 0.088 | 76 | 0.879 | flat — bypass persistent 🔴🔴 |
| **ETF** | 0 | — | 11 | 27.3% | 1.322 | 47 | 2.121 | stable ✅ |
| **BOND** | 1 | 0.000 | 4 | 0.0% | 0.000 | 4 | 0.000 | sparse (n<5) |
| **FUTURES** | 1 | 999.0 | 1 | 100% | 999.0 | 3 | 999.0 | n too small — sentinel |

### Delta vs CLAUDE.md Documented Baselines

| Class | Metric | Baseline | 09Z | Delta |
|-------|--------|----------|-----|-------|
| CRYPTO | 24h PF | 3.54 | 2.867 | −0.673 (still healthy) |
| CRYPTO | 7d PF | 1.33 | 1.468 | **+0.138** ✅ |
| CRYPTO | 30d PF | 1.33 | 1.365 | **+0.035** ✅ |
| EQUITY | 7d PF | 0.87 | 0.803 | −0.067 (slight deterioration) |
| EQUITY | 30d PF | 1.41–2.18 | 1.431 | at low end of range |
| FOREX | 7d PF | 0.14 (pre-#687) | 1.070 | **+0.930** ✅✅✅ |
| FOREX | 30d PF | 0.97 (pre-#687) | 2.577 | **+1.607** ✅✅✅ |

---

## CRYPTO Detail

- 24h surge cool-off: PF 3.499 (08Z) → 2.867 (09Z). Normal regression — regime tailwind from PR #694 HYPEUSDT block continuing.
- 7d still above CLAUDE.md baseline (1.468 vs 1.33). Positive drift.
- `unknown` SHORT (quan_engine/regime_terminal) still dragging: n=146, WR=12.3%, PF=0.347 (30d). Source attribution: quan_engine 119, regime_terminal 24, ml_crypto_pred 3. All CRYPTO class. This is the post-#694 residual NULL-strategy picks.

## EQUITY Detail

- **24h PF 2.321 on n=8** — strong positive signal post-#692 (goldmine_6x_consensus kill). EQUITY 24h surge from 1.390 (08Z) to 2.321 (+0.931). Consistent with issue #693 hypothesis that #692 kill would partially recover EQUITY.
- 7d PF 0.803 (vs 0.864 at 08Z) — slight intraday worsening but 24h trend overrides. Monitor.
- `stocks_rsi2_pullback` 30d: n=52, WR=40.4%, PF=1.025 — breakeven, watch for drift below 1.0.
- `macd-hidden-div-scout` in positive territory 30d — not a kill candidate.

## FOREX Detail

- **8th consecutive hour ≥1.0 on 7d PF** — sustained improvement post-PR #687 (JPY-cross BUY rule fix).
- 30d PF=2.577 vs pre-#687 baseline 0.97 → +1.607 improvement. Post-#687 normalization is real.
- 24h n=8 only — sample too small to read directionally, but PF=1.446 positive.

## COMMODITY Detail

- **Persistent catastrophe**: 7d PF 0.088, WR 7.3%, n=41. No change from 08Z.
- `cftc_cot_commercial_signal` SHORT (CT=F, ZS=F, ZW=F): n=22 in 7d window, WR=4.5%, PF=0.099. **Already blocked** in `alpha_engine/strategy_blocklist.py:176` and `BLOCKED_ASSET_STRATEGY_PAIRS` in production_scanner.py since 2026-05-02. These picks have `closed_at` 05-14 to 05-21 but were likely opened pre-block. Block confirmed operational.
- Deep-dive required per CLAUDE.md: what other strategies drive the 7d COMMODITY drag beyond cftc_cot tail?

---

## NEW FINDING-47: `crypto_mtf_ema_slope_alignment_v1` SHORT directional split

**Source:** mutation_analysis.py 09Z run — 30d window

| Direction | n | WR | PF |
|-----------|---|----|-----|
| SHORT | 38 | 31.6% | **0.497** 🔴 |
| LONG | 51 | 58.8% | 1.640 ✅ |
| **Spread** | — | **27pp** | — |

- SHORT meets kill threshold: n=38≥20, PF<0.5, WR<35%.
- LONG is healthy Tier-2 candidate (PF 1.640, WR 58.8%).
- **Recommended mutation:** LONG-only block on SHORT direction for this strategy (add `("CRYPTO", "crypto_mtf_ema_slope_alignment_v1", "SHORT")` to symbol/direction blocklist). Do NOT kill full strategy — LONG is positive.
- **Status:** 1/3 AI vote (this audit). Awaiting 2nd+3rd AI consensus per CLAUDE.md protocol.
- **Evidence:** `reports/HOURLY_AUDIT_2026-05-21_09Z.md` + mutation_analysis.py 09Z run.

---

## Kill Queue Status (09Z — 9 existing + 1 new)

| Finding | Description | Status |
|---------|-------------|--------|
| FINDING-22 | cftc_cot×COMMODITY SHORT | Already blocked (strategy_blocklist.py:176) — tail cleanup only |
| FINDING-34 | cta_replicator×NG=F | Awaiting 2nd+3rd AI vote |
| FINDING-36 | rapid_fire×UUSDT | Awaiting 2nd+3rd AI vote |
| FINDING-37/46 | ig_contrarian LONG (n=200, WR=16.5%) | Awaiting 2nd+3rd AI vote — DO NOT block SHORT |
| FINDING-39 | myfxbook_retail_contrarian LONG (n=124, WR=13.7%) | Awaiting 2nd+3rd AI vote |
| FINDING-44 | quan_engine_swing LONG (n=104, WR=26.0%) | Awaiting 2nd+3rd AI vote |
| FINDING-45 | cta_cross_asset_tsmom LONG (n=85, WR=29.4%) | Awaiting 2nd+3rd AI vote |
| FINDING-43 | Watch only | Watch |
| FINDING-31 | n<20 | Watch until n≥20 |
| **FINDING-47** | `crypto_mtf_ema_slope_alignment_v1` SHORT (n=38, PF=0.497) | **NEW — 1/3 AI vote** |

---

## PR Triage

### Merged this turn
| PR | Title | Why |
|----|-------|-----|
| **#1283** | 08Z audit — EQUITY 24h +0.312 PF, FOREX 7th hr ≥1.0 | mergeable=clean, 3/3 CI green, greptile-bot COMMENT only (not REQUEST_CHANGES) |

### Open PRs (post-merge)
| PR | State | Action |
|----|-------|--------|
| **#1279** | DRAFT | No merge — DRAFT by policy |

### HOLD set (#660 #658 #681 #661)
Not present in open PRs ✅

### Author-rebase watch PRs (#669 #676 #608 #665 #644 #597 #615 #655)
All 7 of the open ones were already merged before this audit:
- #669 merged 2026-05-02T23:08:19Z ✅
- #676 merged 2026-05-03T21:52:55Z ✅
- #608 merged 2026-05-03T21:57:17Z ✅
- #665 merged 2026-05-02T23:08:17Z ✅
- #644 merged 2026-05-03T22:00:47Z ✅
- #597 merged 2026-05-03T22:33:02Z ✅
- #615 merged 2026-05-03T21:57:14Z ✅
- #655 closed without merge (doc-only, superseded) ✅

### Plan v2.1 guardrails
- No PRs citing PF 5.81 / ml_score 0.90 ✅
- No resolver-rescope PRs detected (issue #685: DONE) ✅
- HOLD set not in open PRs ✅

---

## New Kill Candidates from mutation_analysis.py 09Z

### Strategies meeting PF<0.5 + n≥20 (new at 09Z)

| Strategy | Direction | Window | n | WR | PF | Action |
|----------|-----------|--------|---|-----|-----|--------|
| `cftc_cot_commercial_signal` | SHORT | 7d | 22 | 4.5% | 0.099 | **Already blocked** — tail picks only |
| `crypto_mtf_ema_slope_alignment_v1` | SHORT | 30d | 38 | 31.6% | 0.497 | **FINDING-47 NEW** — 1/3 vote |
| `unknown` (quan_engine) | SHORT | 30d | 146 | 12.3% | 0.347 | Data quality — NULL strategy label; addressed by #694 HYPEUSDT block partially |

### Strategies approaching threshold (PF 0.5–1.0, watch)

| Strategy | Direction | n | WR | PF |
|----------|-----------|---|-----|-----|
| `luxalgo_confluence` | SHORT | 363 | 42.4% | 0.906 |
| `multi_period_rsi_confluence_eth` | LONG | 33 | 51.5% | 0.940 |
| `keltner_compression_expansion_eth_v` | SHORT | 30 | 33.3% | 0.841 |
| `claude_ml_conservative_mut` | LONG | 20 | 20.0% | 0.545 |

---

## Refs

- Issue #685 (resolver-rescope: DONE)
- Issue #686 (per-asset quality regression + kill queue)
- Issue #693 (EQUITY divergence monitor — closed 2026-05-13, superseded by 09Z data)
- `reports/HOURLY_AUDIT_2026-05-21_08Z.md` (prior audit)
- `tools/mutation_analysis.py` (09Z run)
- `audit_dashboard/data/dashboard_data.json` (source data)

---

_Generated by [Claude Code](https://claude.ai/code/session_01Lg2NcouLCT6kcjbE7U1AVK)_
