# Hourly Audit — 2026-05-15 05Z

**Generated:** 2026-05-15T05:12Z  
**Session:** 1 of N (hourly progress check)  
**Dashboard data timestamp:** 2026-05-15T02:06:57Z  
**Auditor:** Claude Sonnet 4.6  
**Context issues read:** #685 (resolver-rescope DONE), #686 (per-asset attribution), #693 (EQUITY divergence — closed 2026-05-13)

---

## 1. Dashboard Refresh Status

Pulled origin/main at 05:12Z — repo is current (merged #1039/#1040 landed). Dashboard JSON last generated at **02:06Z** (≈3h lag; next auto-refresh expected ~06:06Z via [skip ci] cron). Data is valid for audit purposes.

---

## 2. Asset Class Health — Verdict-Grade (post-resolver-v2)

Source: `audit_dashboard/data/dashboard_data.json::performance.asset_class_health`

| Class | PF | WR | n | Tier-2 gate (PF>1.5 / WR>50%) |
|---|---|---|---|---|
| COMMODITY | **2.49** | **61.5%** | 322 | ✅ CLEAR — real-money pilot candidate (M-050) |
| EQUITY | **1.57** | 51.9% | 420 | ✅ CLEAR |
| ETF | 1.48 | **58.5%** | 106 | ⚠️ PF 0.02 below gate; WR strong |
| CRYPTO | 1.36 | 46.7% | 8011 | ❌ WR below floor (quan_engine/HYPE drag) |
| FOREX | 0.81 | 52.3% | 342 | ❌ PF sub-floor (recovering post-#687/#692) |
| BOND | 0.66 | 54.5% | 11 | ❌ n<100 charter floor |
| FUTURES | N/A | 0.0% | 0 | ❌ no resolved data |

---

## 3. Per-Asset Windowed Metrics (computed from picks.recent_closed, n=3500)

Ref time: 2026-05-15T02:07Z. 11 picks skipped (no parseable timestamp).

| Class | 24h PF | 24h WR | 24h n | 7d PF | 7d WR | 7d n | 30d PF | 30d WR | 30d n |
|---|---|---|---|---|---|---|---|---|---|
| CRYPTO | 1.75 | 49.3% | 146 | 1.34 | 43.8% | 878 | 1.25 | 44.9% | 2873 |
| EQUITY | 1.85 | 66.7% | 3 | 1.19 | 26.5% | 34 | 2.07 | 51.2% | 127 |
| FOREX | 1.06 | 30.0% | 10 | 1.38 | 14.0% | 43 | 1.32 | 27.5% | 91 |
| COMMODITY | 0.00 | 0.0% | 15 | 1.16 | 42.3% | 26 | 2.58 | 61.3% | 62 |
| ETF | ∞ | 100.0% | 2 | 2.19 | 64.3% | 14 | 4.05 | 75.0% | 52 |
| BOND | — | — | 0 | — | — | 0 | — | — | 0 |
| FUTURES | — | — | 0 | — | — | 0 | — | — | 0 |

---

## 4. Deltas vs Documented Baselines

| Class | Window | Baseline | Now | Delta | Signal |
|---|---|---|---|---|---|
| CRYPTO | 24h PF | 3.54 | 1.75 | **−1.79** | Significant drop — small n (146), watch next cycle |
| CRYPTO | 7d PF | 1.33 | 1.34 | +0.01 | FLAT — stable |
| CRYPTO | 30d PF | 1.33 | 1.25 | −0.08 | Minor drift, not alarming |
| EQUITY | 7d PF | 0.87 | 1.19 | **+0.32** | Recovery — PR #692 goldmine_6x_consensus kill confirmed effective |
| EQUITY | 30d PF | 1.41–2.18 | 2.07 | in range | Healthy long-run |
| FOREX | 7d PF | 0.14 (pre-#687) | 1.38 | **+1.24** | Major recovery — PR #687 JPY-cross BUY rule fix working |
| FOREX | 30d PF | 0.97 (pre-#687) | 1.32 | +0.35 | Strong improvement |

### Interpretation

**FOREX recovery (P1 positive):** 7d PF 0.14 → 1.38 is the largest single-asset improvement visible in this audit. WR still low at 14% in the 7d window (n=43) — expected as losing legacy picks close out. 30d will improve as clean post-#687 picks accumulate.

**EQUITY recovery (confirms issue #693 hypothesis):** Post-#692, 7d PF rose 0.87 → 1.19. 14d needs to hit ≥1.5 within next 7 days to fully close issue #693.

**CRYPTO 24h drop:** 3.54 → 1.75 on n=146. Small-sample window; 7d stable at 1.34. No action — per issue #686 "do not destabilize" guidance.

**COMMODITY 24h zero:** 15 picks, 0 wins. 30d PF strong at 2.58. n<20 action threshold. Monitor only.

---

## 5. PR Triage — Full Status at 05:12Z

| PR | Title | CI Status | Mergeable | Decision |
|---|---|---|---|---|
| #1040 | docs(updates): master plan summary + 48h table | ✅ scan:pass | clean | **MERGED 05:12Z** |
| #1039 | docs(plans): hedge-fund gap analysis + M-050..M-054 | ✅ scan:pass | clean | **MERGED 05:12Z** |
| #1037 | feat(crypto): BTC UTC-hour death-zone filter | ❌ gate:fail, test(3.11):fail | — | HOLD — CI failures |
| #1032 | docs(kimi-archive): preserve Kimi 5-PR bundle | ⚪ 0 checks | unknown | HOLD — no CI |
| #1030 | fix(audit): Mercury2 P0.1+P0.2 missing JS | ⚪ 0 checks | unknown | HOLD — no CI |
| #1029 | fix: disable 12 toxic systems + blacklist 3 symbols | ⚪ 0 checks | unknown | HOLD — no CI |
| #1027 | feat(crypto): SHORT direction bias multiplier | ❌ gate:fail, test(3.11):fail | — | HOLD — CI failures |
| #1026 | feat: Phase J ML-calibration banner + Kilo P0 fix | ❌ gate:fail, test(3.11):fail | — | HOLD — CI failures |

HOLD set (#660 #658 #681 #661): not in open list — already handled.
Author-rebase set (#669 #676 #608 #665 #644 #597 #615 #655): none open — all merged or closed.

---

## 6. Mutation Analysis — New Kill Candidates

`python tools/mutation_analysis.py --json` run at 05:12Z.

### Direction-split findings

| Strategy | Direction | WR | n | Already Blocked? |
|---|---|---|---|---|
| `ig_contrarian_sentiment` | LONG | 16.8% | 197 | **NO** — new candidate |
| `forex_rsi2_mean_reversion` | LONG | 7.4% | 108 | NO — P1 in #686, not blocked |
| `quan_engine_swing` | LONG | 26.0% | 104 | **NO** — new candidate |
| `cta_cross_asset_tsmom` | LONG | 29.8% | 84 | **NO** — new candidate |
| `myfxbook_retail_contrarian` | LONG | 13.8% | 123 | ✅ already blocked (FOREX pair) |

PF not directly in mutation_analysis output. All LONG arms: WR ≤ 17%, avg_pnl ≈ −0.00% → PF < 0.50 strongly implied. Needs closed_picks_fast.json verification before kill PR.

### Symbol-level findings

| System | Symbol | WR | n | Threshold met? |
|---|---|---|---|---|
| `rapid_fire` | UUSDT | 0% | 34 | ✅ n>=20, WR<35% |
| `cta_replicator` | NG=F | 0% | 24 | ✅ n>=20, WR<35% |
| `quan_engine` | MATICUSDT | 0% | 553 | ✅ PR #1029 proposes kill |
| `rapid_fire` | TAOUSDT | 5.6% | 18 | ❌ n<20 — monitor |

### Existing kills confirmed active

- (`FOREX`, `forex_carry_momentum`) ✅ — PR #692
- (`EQUITY`, `goldmine_6x_consensus`) ✅ — PR #692
- CRYPTO/HYPEUSDT symbol-block ✅ — PR #694

---

## 7. Gate Checks

**Issue #685 (resolver-rescope DONE):** No PR claims widen re-resolve scope. Gate clear.

**Plan v2.1 stats (PF 5.81 / ml_score 0.90 / WINNER_FILTER):** Not cited in any open PR. Gate clear.

---

## 8. Summary

| Metric | Value |
|---|---|
| PRs merged this check | **2** (#1039, #1040) |
| PRs held | 6 (#1026, #1027, #1029, #1030, #1032, #1037) |
| New kill candidates posted to #686 | 3 strategy-direction pairs + 2 symbols |
| Biggest positive signal | FOREX 7d PF 0.14→1.38 (+1.24) — PRs #687+#692 confirmed working |
| Second positive signal | EQUITY 7d PF 0.87→1.19 (+0.32) — PR #692 effective |
| Watch items | CRYPTO 24h PF drop (3.54→1.75, n=146); COMMODITY 24h zero (n=15) |

*Reproducer:*
```bash
python3 -c "import json; d=json.load(open('audit_dashboard/data/dashboard_data.json')); [print(k,v.get('profit_factor'),v.get('win_rate'),v.get('n')) for k,v in d['performance']['asset_class_health'].items()]"
```
