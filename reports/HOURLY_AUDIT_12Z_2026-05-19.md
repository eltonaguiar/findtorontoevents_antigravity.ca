# Hourly Audit — 2026-05-19T12:13Z

**Dashboard snapshot:** 2026-05-19T10:19:04Z (latest available; 12Z cron produced scanner data at 12:10Z but dashboard_data.json not yet regenerated)  
**Recent_closed picks:** n=3500 (cap)  
**Prior audit:** PR #1251 (11Z) — merged this hour

---

## Per-Asset Metrics (24h / 7d / 30d)

| Class | 24h PF | 24h n | 7d PF | 7d n | 30d PF | 30d n | Delta vs 11Z |
|-------|--------|-------|-------|------|--------|-------|--------------|
| **CRYPTO** | **2.661** | 266 | **1.152** | 1037 | 1.322 | 2896 | 24h +0.120 ✅; 7d FINDING-12 RESOLVED (+0.170 from 0.982) |
| EQUITY | 0.000 | 5 | 0.238 | 15 | 1.939 | 95 | 7d n=15 sub-significance; 30d healthy |
| FOREX | 1.279 | 7 | 1.273 | 19 | 2.514 | 93 | Post-kill dormancy; new picks entering window with positive PF |
| COMMODITY | 0.000 | 3 | 0.193 | 23 | 1.747 | 57 | 7d drag = cftc_cot_commercial_signal (n=18, WR 5.6%) |
| ETF | 1.887 | 9 | 0.989 | 20 | 2.005 | 49 | FINDING-13 RETRACTED — 7d near breakeven |
| FUTURES | — | 0 | — | 0 | inf | 2 | n too small |

### Baselines for comparison

| Class | CRYPTO 24h | CRYPTO 7d | CRYPTO 30d | EQUITY 7d | EQUITY 30d | FOREX 7d | FOREX 30d |
|---|---|---|---|---|---|---|---|
| **Documented baseline (issue #686)** | PF 3.54 | PF 1.33 | PF 1.33 | PF 0.87 | PF 1.41–2.18 | PF 0.14 (pre-#687) | PF 0.97 |
| **11Z (PR #1251)** | 2.541 | 1.161 | — | 0.238 | — | 1.273 | 2.514 |
| **12Z (this audit)** | 2.661 | 1.152 | 1.322 | 0.238 | 1.939 | 1.273 | 2.514 |

---

## Findings

### FINDING-12: RESOLVED ✅
CRYPTO 7d PF recovered 0.982→1.161→**1.152** (stable above 1.0 for 2 consecutive hourly checks). First sub-1.0 regression from 10Z confirmed transient — regime-driven noise, not structural degradation. No action required.

### FINDING-14: STRENGTHENING — monitor to 24h
CRYPTO 24h PF spike: 0.853 (10Z) → 2.541 (11Z) → **2.661** (12Z, n=266). Three consecutive hours positive. `st_fear_greed_contrarian` is the dominant driver (n=193, WR 69.4%, PF 3.399 in 7d). Likely a regime tailwind. Still monitoring — will confirm structural vs transient at 24h mark.

### FINDING-13: RETRACTED ✅
ETF 7d PF recovered 0.302→0.989. Confirmed in 11Z audit; stable at 0.989 this hour.

### FINDING-15 (NEW): `ensemble` CRYPTO 7d — kill candidate
| Metric | Value | Kill threshold |
|---|---|---|
| n | 25 | ≥20 ✅ |
| WR | 20.0% | <35% sustained ✅ |
| PF | 0.290 | <0.5 ✅ |
| sum PnL% | −31.49 | — |

Pattern: same CRYPTO-engine kill family as `quan_engine` volume reduction (PR #694). **Requires 3-AI consensus before adding to `BLOCKED_ASSET_STRATEGY_PAIRS` or `BLOCKED_STRATEGY_SYMBOL_PAIRS`.**

### FINDING-16 (NEW): `crypto_mtf_ema_slope_alignment_v1` CRYPTO 7d — kill candidate
| Metric | Value | Kill threshold |
|---|---|---|
| n | 24 | ≥20 ✅ |
| WR | 16.7% | <35% sustained ✅ |
| PF | 0.294 | <0.5 ✅ |

Same criteria met. Requires 3-AI consensus.

### COMMODITY drag: `cftc_cot_commercial_signal` approaching kill threshold
n=18, WR 5.6%, PF 0.133. **n=18 is below the n≥20 floor — do NOT kill yet.** Note: `cftc_cot_commercial_signal` may be distinct from the strategy killed in PR #683 (`cftc_cot`). Verify naming before acting. Next hourly: if n reaches 20+, escalate to 3-AI consensus.

### Kill verification: all target strategies absent ✅
- `forex_carry_momentum` — 0 picks in 7d ✅
- `goldmine_6x_consensus` — 0 picks in 7d ✅
- `quan_engine×HYPEUSDT` — 0 picks in 7d ✅

---

## CRYPTO 7d Strategy Attribution (top 10 by n)

| Strategy | n | WR% | PF | sum PnL% |
|---|---|---|---|---|
| `st_fear_greed_contrarian` | 193 | 69.4% | 3.399 | +142.47 |
| `luxalgo_confluence` | 181 | 43.6% | 1.059 | +13.25 |
| `unknown` | 169 | 29.0% | 0.991 | −1.51 |
| `strong consensus (alpha_engine, ml_crypto_pred)` | 106 | 45.3% | 1.013 | +1.81 |
| `claude_ml_moderate_mut` | 46 | 50.0% | 1.675 | +25.37 |
| `ensemble` | 25 | 20.0% | 0.290 | −31.49 ← FINDING-15 |
| `crypto_mtf_ema_slope_alignment_v1` | 24 | 16.7% | 0.294 | −6.37 ← FINDING-16 |
| `signal_engine_momentum_mut` | 18 | 33.3% | 0.828 | −3.26 |
| `multi_period_rsi_confluence_eth` | 18 | 50.0% | 0.544 | −3.61 |
| `keltner_compression_expansion_eth_v1` | 17 | 29.4% | 0.858 | −0.54 |

---

## PR Triage

| PR | Title | CI | Mergeable | REQUEST_CHANGES | Action |
|---|---|---|---|---|---|
| **#1251** | 11Z audit — FINDING-12 resolving | ✅ All green | CLEAN | None | **MERGED ✅** |
| **#1247** | model grill sequential + API roster | ❌ test(3.11) FAILED | — | greptile COMMENTED only | **HOLD — CI red** |

**HOLD set confirmed closed/merged:** #660, #658, #681, #661 — all resolved in prior sessions.  
**Rebase set confirmed closed/merged:** #669, #676, #608, #665, #644, #597, #615, #655 — all resolved in prior sessions.

---

## Mutation Analysis

No new full-pool strategies emerging beyond FINDING-15/16 above (computed from `recent_closed` 7d window).

**Awaiting 3-AI consensus (unchanged from prior audits):**
1. `ig_contrarian_sentiment` LONG: WR 16.5%, n=200
2. `myfxbook_retail_contrarian` LONG: WR 13.7%, n=124
3. `quan_engine_swing` LONG: WR 26.0%, n=104
4. `forex_rsi2_mean_reversion` LONG: WR 6.8%, n=117
5. `rapid_fire`×UUSDT: WR 0%, n=34
6. `cta_replicator`×NG=F: WR 0%, n=24
7. **NEW — `ensemble` CRYPTO: WR 20%, n=25, PF 0.29** (FINDING-15)
8. **NEW — `crypto_mtf_ema_slope_alignment_v1` CRYPTO: WR 16.7%, n=24, PF 0.294** (FINDING-16)

---

## References

- Issue #685 (resolver DONE — no action)
- Issue #686 (live quality — FINDING-14/15/16 updates posted)
- Issue #693 (EQUITY monitor — closed 2026-05-13; protocol active, EQUITY 7d still sub-floor but n=15)
- PR #1251 merged (11Z audit)
- HOLD: PR #1247 (CI red)

---
_Generated by [Claude Code](https://claude.ai/code/session_01Rq35QSd9TvYKTKJtz4AkTu) — 2026-05-19T12:13Z_
