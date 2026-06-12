# BUFFY PROGRESS TRACKER — June 12, 2026

**Session:** Buffy (deepseek-v4-pro) via Codebuff
**Started:** 2026-06-12
**Source:** `BUFFY_MASTER_HANDOFF_JUNE122026.MD` sections C-E

---

## ✅ COMPLETED (5 PRs merged to main)

| # | PR | Commit | What | Files |
|---|---|---|---|---|
| **P0C** | [#568](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/568) | `63eb53e` | Block CRYPTO LONG (stops Σ−503% PnL bleed) | `config.py`, `quality_gates.py` |
| **Picks-now #1** | [#568](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/568) | same | One-position-per-ticker hard limit | `quality_gates.py` |
| **Picks-now #2** | [#568](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/568) | same | Universal TP/SL fallback per asset class | `quality_gates.py` |
| **P0B** | [#569](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/569) | `9670338` | Unified kill list (7 strategies) + `is_emission_allowed()` | `emitter_discipline.py`, `config.py`, `backfill_local_sources.py` |
| **Council #6** | [#569](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/569) | same | DB Edge Overlay weight 10→25, rebalanced | `picks_now_professional.py` |
| **P0A** | [#573](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/573) | `f46a230` | Hourly intrabar reresolve + bootstrap batch dispatch | `audit-dashboard.yml` |
| **Council #5** | [#576](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/576) | `eff3485` | Factor 4 → hard circuit breaker (SKIP_VOL veto) | `picks_now_professional.py` |

**P0A bootstrap triggered:** [Run #27439641941](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/27439641941) (seeds 177K backlog, then 500/hr hourly)

---

## 🔴 P0 — ALL COMPLETE

| # | Task | Status |
|---|---|---|
| P0C | Block CRYPTO LONG | ✅ Merged |
| P0B | Unified kill list + `is_emission_allowed()` | ✅ Merged |
| P0A | Intrabar hourly reresolve + bootstrap batch | ✅ Merged + triggered |

---

## 🟡 P1 — NEXT PRIORITIES

| # | Task | Impact | Effort | Status |
|---|---|---|---|---|
| **Picks-now #3** | Bridge AI panel → quant score (-20pts per reject) | META 7/7 reject shouldn't show as top pick | Medium | ❌ |
| **Picks-now #4** | Factor correlation penalty (diminishing returns) | Reduces echo-chamber from correlated factors | Medium | ❌ |
| **Picks-now #7** | Expose trimmed-mean PnL on dashboard | Shows real story: −0.04% vs raw −35.86% | Low | ❌ |
| **P1A** | Intrabar-only verdict UI | Shows honest WR/PF when n≥30 | Medium | ❌ |
| **P1B** | Auto-kill tribunal (weekly automated demotion) | Systematizes strategy lifecycle | Medium | ❌ |
| **E.1** | CRYPTO LONG full post-mortem | Understand conditions producing LONG losses | Medium | ❌ |
| **E.6** | equity_gap_fade deep-dive | 66.7% WR, n=36 — closest to P95 | Medium | ❌ |
| **E.4** | CRYPTO SHORT-only forward experiment | Prove 55.8% WR holds forward | Medium | ❌ |

---

## 🟢 P2 — NICE TO HAVE

| # | Task |
|---|---|
| 5 | Tune 3 zero-trade strategies |
| 6 | Add SHORT variants (PF=7.40 futures, PF=6.13 forex_rsi2) |
| 7 | Pre-register 4 strategies in M-107 hypothesis registry |
| 8 | Apply stress matrix before promoting any MONITORED strategy |
| 9 | Verify FOREX OHLCV data completeness |
| 11 | Double down on equity_gap_fade optimization |
| 12 | CRYPTO SHORT-only forward experiment |

---

## 📊 CURRENT HONEST STATE (intrabar)

| Class | n | WR% | PF | Money-Ready? |
|---|---|---|---|---|
| CRYPTO | 1,283 | 29.2 | 0.728 | ❌ |
| EQUITY | 130 | 28.5 | 0.509 | ❌ |
| FOREX | 124 | 29.8 | 1.107 | ❌ (thin) |
| COMMODITY | 110 | 33.6 | 1.426 | ❌ (below P95) |
| ETF | 22 | 0.0 | 0.148 | ❌ |
| MEMECOIN | 77 | 26.0 | 0.580 | ❌ |
| BOND | 7 | 28.6 | 1.699 | ❌ (n too low) |

**0/9 classes money-ready.** The deficit is entry selection, not exit geometry.

---

## 📋 picks-now Council Enhancements Status

| # | Enhancement | Status |
|---|---|---|
| 1 | One-position-per-ticker hard limit | ✅ Merged (P0C) |
| 2 | Universal ATR-trailing stop-loss | ✅ Merged (P0C) |
| 3 | Bridge AI panel → quant score | ❌ |
| 4 | Factor correlation penalty | ❌ |
| 5 | Factor 4 → veto gate | ✅ Merged (Council #5) |
| 6 | DB Edge Overlay 10%→25% | ✅ Merged (Council #6) |
| 7 | Expose trimmed-mean PnL | ❌ |

**4/7 council enhancements shipped.**

---

## 🔧 CI PIPELINE FIXES (pre-session, already on main)

| Workflow | Fix |
|---|---|
| `ci-tests.yml` | fail-fast disabled, known-drift quarantine, timeout guards, FRED_MACRO_DISABLED |
| `audit-dashboard.yml` | DB_PASS_STOCKS + DB_PASS_BACKUPS env, P0A hourly reresolve |
| `alpha-engine-live.yml` | CoinGecko ADV cache warm before scan |
| `2hour_challenge.yml` | File paths fixed, `|| true` guards |
| `genome-daily-pipeline.yml` | `promotion_gate_report.json` staged |
| `mirror-site.yml` | Timeout 15→30 min, lftp retry |
| `ml-gatekeeper-train-ab.yml` | `dashboard_data.json` fetch, `git add -f` bundles |
| `daily-scrutiny-engine.yml` | FINDING_OVERALL#12 one-sided resolution check |

---

## 🎯 NEXT RECOMMENDED ACTIONS

1. **Picks-now #3** — Bridge AI panel → quant score (highest remaining council priority)
2. **CRYPTO LONG post-mortem (E.1)** — Understand the worst sub-strategies for targeted optimization
3. **equity_gap_fade optimization (E.6)** — Closest to P95, deserves focused iteration

---

*Generated 2026-06-12 by Buffy (deepseek-v4-pro)*
