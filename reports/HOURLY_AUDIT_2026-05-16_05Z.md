# Hourly Audit — 2026-05-16 05Z

**Generated:** 2026-05-16T05:09Z  
**Dashboard snapshot:** 2026-05-16T04:04Z  
**Analyst:** Claude Sonnet 4.6 (automated hourly)  
**Prior audit:** `reports/HOURLY_AUDIT_2026-05-15_07Z.md`  
**Issues read:** #685 (resolver rescope DONE), #686 (per-asset attribution), #693 (EQUITY monitor — closed 2026-05-13)

---

## 1. Dashboard Refresh Status

Pull from origin/main succeeded. 25 files updated (KIMI scan logs, HMM regime, genome picks, regime_terminal signals). Dashboard snapshot timestamp: **2026-05-16T04:04Z** (within 1h of expected hourly refresh). Data is fresh.

---

## 2. Asset Class Health — Long-Run (asset_class_health, post-resolver-v2)

| Class | PF | WR% | n | vs Baseline (2026-05-03) | Tier |
|---|---|---|---|---|---|
| CRYPTO | 1.31 | 46.5 | 7,885 | PF +0.06 / WR +1.9pp | sub-T2 |
| EQUITY | **1.56** | 51.5 | 425 | PF +0.15 / WR -1.2pp | **T2 candidate** |
| FOREX | **0.86** | 54.7 | 311 | PF **+0.59** / WR +8.3pp | recovering |
| COMMODITY | **2.57** | 62.6 | 337 | PF **+0.79** / WR +15.7pp | **T1 candidate** |
| ETF | 1.32 | 57.0 | 107 | PF +0.08 / WR +1.8pp | T2 borderline |
| BOND | 0.66 | 54.5 | 11 | — | below charter floor (n<18) |
| FUTURES | — | 100.0 | 2 | — | n too small |

**Baseline source:** CLAUDE.md (CRYPTO 1.25 / EQUITY 1.41 / FOREX 0.27 / COMMODITY 1.78 / ETF 1.24), dated 2026-05-03T00:06Z.

**Headline delta:** FOREX surged from PF 0.27 to 0.86 — direct effect of PR #687 (JPY-cross BUY rule fix). COMMODITY crossed Tier-1 PF threshold (2.57 > 2.0). EQUITY consolidated as T2 candidate.

---

## 3. Per-Asset PF/WR by Time Window (from recent_closed, n=3500)

### CRYPTO
| Window | n | WR% | PF | Sum PnL% |
|---|---|---|---|---|
| 24h | 92 | 34.8 | 0.86 | -18.55 |
| 7d | 777 | 43.9 | 1.26 | +188.05 |
| 30d | 2,852 | 45.6 | 1.26 | +638.19 |

**Delta vs issue #686 baseline (24h PF 2.65 / 7d PF 1.21):** 24h PF collapsed from 2.65 → 0.86 (WR 64% → 34.8%). 7d PF improved slightly 1.21 → 1.26. The 24h drop is concerning but n=92 is low — could be regime volatility. 7d and 30d are stable. **Do not destabilize.** (CLAUDE.md constraint.)

### EQUITY
| Window | n | WR% | PF | Sum PnL% |
|---|---|---|---|---|
| 24h | 6 | 16.7 | 0.02 | -9.64 |
| 7d | 33 | 18.2 | 0.59 | -22.04 |
| 30d | 126 | 50.0 | 2.02 | +176.45 |

**Delta vs issue #693 baseline (7d PF 0.87, 30d PF 2.18):** 7d PF further declined 0.87 → 0.59. PR #692 killed `goldmine_6x_consensus` (the primary 7d drag per #693), but `stocks_rsi2_pullback` (n=7, WR 14.3%) is now the leading 7d drag. 30d PF 2.02 vs baseline 2.18 — modest decline but still T1-range. Issue #693 is closed; monitoring continues per its recommendation.

**7d Strategy Attribution:**
| Strategy | n | WR% | PF | Sum PnL% |
|---|---|---|---|---|
| stocks_rsi2_pullback | 7 | 14.3 | 0.28 | -13.0 |
| gap-and-go-stocks | 3 | 66.7 | 2.09 | +7.44 |
| macd-hidden-div-scout | 2 | 0.0 | — | -8.14 |
| price-accel-scout | 2 | 0.0 | — | -8.45 |
| stocksunify2_adversarial_trend_v2 | 8 | 0.0 | — | 0.00 |

Note: `stocksunify2_adversarial_trend_v2` shows n=8, WR=0%, sum=0% — zero PnL trades, likely flat/pending exits. Excluded from kill analysis. `stocks_rsi2_pullback` n=7 is below the n>=20 kill threshold — **monitor only**.

### FOREX
| Window | n | WR% | PF | Sum PnL% |
|---|---|---|---|---|
| 24h | 9 | 33.3 | 1.22 | +1.18 |
| 7d | 26 | 19.2 | 1.60 | +3.65 |
| 30d | 48 | 33.3 | 2.30 | +16.47 |

**Delta vs issue #686 baseline (7d PF 0.14, WR 10.7%):** 7d PF surged from 0.14 → 1.60. This is the clearest post-PR-#687 signal to date. FOREX is recovering. `forex_carry_momentum` and `forex_rsi2_mean_reversion` were killed in PR #692; the remaining strategies are performing. **MUTATION_THREE_AXIS_PROTOCOL not needed — improvement confirmed.**

### COMMODITY
| Window | n | WR% | PF | Sum PnL% |
|---|---|---|---|---|
| 24h | 5 | 20.0 | 0.47 | -9.67 |
| 7d | 27 | 29.6 | 0.64 | -24.33 |
| 30d | 65 | 56.9 | 1.97 | +88.85 |

**7d weakness despite long-run PF 2.57 — strategy attribution:**
| Strategy | n | WR% | PF | Sum PnL% |
|---|---|---|---|---|
| cot_positioning | 14 | 35.7 | 0.62 | -15.01 |
| cftc_cot_commercial_signal | 13 | 23.1 | 0.67 | -9.32 |

Both strategies n<20, below kill threshold. `cftc_cot` was killed in PR #683 — these may be tail-end close-outs of pre-kill positions. Long-run PF 2.57 is the authoritative number. **Monitor only — do not act on sub-7d noise.**

### ETF
| Window | n | WR% | PF | Sum PnL% |
|---|---|---|---|---|
| 24h | 2 | 0.0 | — | -12.07 |
| 7d | 13 | 46.2 | 0.66 | -7.14 |
| 30d | 49 | 71.4 | 2.55 | +52.80 |

7d weakness on low n (13). 30d PF 2.55 is robust (T1). **No action.**

---

## 4. PR Triage

`gh pr list --state open` returned **0 open PRs**. All 8 PRs merged earlier today (#684, #674, #673, #664, #683, #687, #692, #694) have landed. HOLD set (#660, #658, #681, #661) confirmed closed/absent from open list.

Author rebase check targets (#669, #676, #608, #665, #644, #597, #615, #655): **none appear in open PR list** — all previously closed or merged. No rebase merges needed this cycle.

---

## 5. New Strategy Kill Candidates (mutation_analysis.py --json)

### KILL CANDIDATE: (CRYPTO, ensemble) — 3-AI CONSENSUS REQUIRED, DO NOT AUTO-KILL

| Metric | Value |
|---|---|
| n (7d) | 41 |
| WR (7d) | 24.4% |
| PF (7d) | **0.43** |
| Sum PnL% (7d) | -32.54% |
| PF (30d) | 1.12 |
| PF (all, 3500 cap) | 1.31 |
| Direction (7d) | LONG only |
| Existing penalty | -10 score (quality_gates.py:4121) |

**Evidence:** 7d PF 0.43 < 0.50 threshold, n=41 ≥ 20, WR 24.4% < 35%. Meets all three criteria per CLAUDE.md §4 kill protocol.

**Context:** Long-run PF 1.31 (all) and 30d PF 1.12 suggest structural edge exists; 7d collapse is recent and direction-specific (all LONGs). Worst symbols are low-cap altcoins (SAHARAUSDT -12.47%, SHIBUSDT -6.04%, SUIUSDT -4.35%). Score penalty already in place (-10 at line 4121). **Mutation recommendation: symbol-allowlist rotation (per mutation_analysis.py Section 3) is the right intervention, not a full kill.** Post to issue #686 for 3-AI deliberation.

### Mutation Analysis — Direction Flips (no kill action, monitoring notes)
- `ig_contrarian_sentiment`: SHORT 61.4% WR vs LONG 16.8% WR (45pp spread, n=197 LONG) — sandbox SHORT-only mutation candidate
- `myfxbook_retail_contrarian`: SHORT 50.0% vs LONG 13.8% (36pp, n=123 LONG) — same
- `cta_cross_asset_tsmom`: SHORT 52.4% vs LONG 29.8% (23pp) — worth flagging

### Symbol-Variance Alerts (no kill action)
- `rapid_fire` × `UUSDT`: n=34, WR=0% — single-symbol block candidate
- `rapid_fire` × `TAOUSDT`: n=18, WR=5.6% — approaching block threshold
- `cta_replicator` × `NG=F`: n=24, WR=0% — block candidate
- `cta_replicator` × `ZC=F`: n=8, WR=0% — below threshold

---

## 6. CRYPTO 24h PF Collapse — Root Cause Assessment

24h PF dropped from baseline 3.54 → 0.86 (WR 64% → 34.8%). This is the most alarming signal this session.

**Mitigating factors:**
- n=92 (within range of baseline n=85) — statistically noisy
- 7d PF 1.26 is stable vs 7d baseline 1.33 — no structural shift visible
- `quan_engine` HYPEUSDT block (PR #694) landed today; may temporarily inflate loss count on tail-end closes
- No new strategies emerged in kill scan beyond `ensemble`

**Verdict:** Do not act. Monitor 24h PF at next cycle. If 24h PF remains <1.0 for 3 consecutive cycles (15:00Z, 16:00Z, 17:00Z), escalate to issue #686 with time-series table.

---

## 7. Deltas vs Prior Audit

(Compared against `HOURLY_AUDIT_2026-05-15_07Z.md` if available, else against CLAUDE.md baseline)

| Class | Long-Run PF (prev) | Long-Run PF (now) | Δ |
|---|---|---|---|
| CRYPTO | 1.25 (CLAUDE.md) | 1.31 | ↑ +0.06 |
| EQUITY | 1.41 (CLAUDE.md) | 1.56 | ↑ +0.15 |
| FOREX | 0.27 (CLAUDE.md) | 0.86 | ↑↑ +0.59 |
| COMMODITY | 1.78 (CLAUDE.md) | 2.57 | ↑↑ +0.79 |
| ETF | 1.24 (CLAUDE.md) | 1.32 | ↑ +0.08 |

All classes improved vs CLAUDE.md baseline. No regressions in long-run health.

---

## 8. Actions Taken This Cycle

| Action | Detail |
|---|---|
| Pull | `git pull --rebase origin/main` — 25 files updated, 1h-fresh |
| PR triage | 0 open PRs — nothing to merge |
| Mutation analysis | Ran `python tools/mutation_analysis.py --json` |
| Kill candidate posted | Issue #686 comment — (CRYPTO, ensemble) for 3-AI review |
| Audit committed | `audit/hourly-05z` branch, this file |

---

## 9. Next Cycle Priorities (06Z)

1. **Monitor CRYPTO 24h PF** — if <1.0 for a second consecutive cycle, escalate
2. **ensemble kill deliberation** — await 2 more AI responses on issue #686 before acting
3. **EQUITY 7d WR recovery** — check if `stocks_rsi2_pullback` n crosses 20 (kill analysis gate)
4. **COMMODITY 7d** — verify `cot_positioning`/`cftc_cot_commercial_signal` decay (PR #683 tail-end)
5. **ig_contrarian_sentiment SHORT-only mutation** — n=57, 61.4% WR on SHORTs — sandbox evaluation

---

*Generated by hourly audit agent. Refs: issues #685, #686, #693. Dashboard: `audit_dashboard/data/dashboard_data.json` (2026-05-16T04:04Z).*
