# Rescue Plan — Per Asset Class (2026-05-12)

**Author:** Grok (external AI audit), red-teamed by 2 in-repo agents.
**Basis:** Production DB (55,510 resolved trades), `metrics_by_asset_class.csv`,
rolling charts, algorithm_performance.csv, edge stability, research
orchestrator, multi-agent audits. Red-team verdict: numbers verified
exact-match in-repo (see `reports/grok_audit_red_team_synthesis_2026-05-12.md`).

## Executive summary

System has no statistically significant positive edge across asset
classes (t-tests p > 0.05; overall Sharpe -2.34). Clear rescue paths
exist for most classes. Highest-leverage fixes:

1. Data pipeline + dragger quarantine (immediate)
2. Gate enforcement + staleness hard-fail (next 48h)
3. Class-specific feature injection + walk-forward validation
4. Shadow / paper trading before real capital

---

## COMMODITY — highest priority, closest to ready

**Current:** PF ~2.08-3.92, WR 48-67%, DSR 1.0 on CT=F. Thin but high-quality.

**Rescue:**
- Promote CT=F to paper-pilot with 4-week monitored run + regime gate (VIX, COT)
- Expand to GC=F via COT + term-structure mutations
- Add seasonality + roll-yield features

**Edge basis:** multi_asset_cot (PF 19.19, n=130), CT=F DSR 1.0.

**Gate:** 4-week paper-pilot + rolling Sharpe > 0.8 + PBO < 0.05.

**Status (this session):** SHIPPED — `audit_dashboard/paper_pilot.html`
tracker live; cot_paper_pilot cron hourly; 7-step testing plan executed
(4 PASS + 1 CONDITIONAL); ROR Monte Carlo wired (Step 7).

---

## EQUITY — strong secondary candidate

**Current:** +0.02% avg, Sharpe +0.67, PF 2.18 on n=814. Low WR (1.84%)
but positive expectancy and PF.

**Rescue:**
- Leverage `ml_gatekeeper` lift (+16pp WR observed in holdout)
- Add earnings drift (PEAD), sector rotation, short-interest features
- Prune bottom symbols; focus high-conviction names
- Expand with survivorship-bias-free universe (CRSP-style)

**Edge basis:** Consistent positive (not significant) mean + strong PF.

**Gate:** Walk-forward consistency ≥ 60% + DSR > 0.95 on top-N portfolio.

**Status (this session):** `tools/top_n_rank_backtest.py` shipped +
dashboard card live; answers "if I bought top-10 today/yday/1mo ago, would
I have profited?" Per `audit_dashboard/data/top_n_rank_backtest.json`.

---

## ETF — quick win with volume

**Current:** n≈40-100, WR 53-60%, PF 1.20-1.58. Near T2; sample-limited.

**Rescue:**
- Universe expansion to n≥150-200
- Sector-momentum + risk-parity rotation
- Block leveraged ETFs; focus on broad + thematic
- NAV vs market price arb monitoring

**Edge basis:** High walk-forward consistency (up to 100% in some folds).

**Gate:** n≥100 + sustained T2 metrics for 30 days.

**Status (this session):** Open. ETF n=87 sub-floor; emission audit
recommended (which of 4 core ETF strategies fires?).

---

## BOND — thin but fixable

**Current:** n=18, WR 55.6%, PF 1.72 (meets quality, fails volume charter).

**Rescue:**
- **Fix FRED API timeout (primary blocker)**
- Add duration, curve steepener, carry strategies
- Expand with treasury + IG credit
- Use Black-Litterman + pyportfolioopt for allocation

**Edge basis:** Literature-rich (Cochrane-Piazzesi, Fleckenstein et al.)

**Gate:** n≥100 + FRED live + 30d paper-pilot.

**Status (this session):** SHIPPED — FRED `SKIP_FRED` env + empty-values
detection unblocks yfinance fallback (commit `293017a5cc9`). BOND scanner
registry wired (`5c7a8c43a27`). Expected n: 18 → 50+ within 2 weeks.

---

## FOREX — major rehab required

**Current:** PF 0.27-0.28, negative expectancy.

**Rescue:**
- Hard-cap sizing to near-zero until rehab complete
- SHORT-only gate + session (13-21 UTC) + news-blackout
- Add carry, COT, DXY beta, macro regime features
- Test deep RL from stefan-jansen Ch.12-18

**Edge basis:** No positive edge in raw data. Mutation-before-kill protocol.

**Gate:** PF ≥ 0.8 on SHORT-only subset + regime gate for 60 days.

**Status (this session):** Deep-dive report shipped
(`reports/asset_class_deep_dive_FOREX_2026-05-12.md`); SHORT-axis edge
documented (57% vs LONG 21% on ig_contrarian_sentiment). 5-step plan
queued for next session.

---

## CRYPTO — high volume, high risk, heavy filtering

**Current:** n=51k, WR 11.3%, -3.73% avg, Sharpe -2.89 (raw). Filtered
view: WR 47.1%, PF 1.36 (per `dashboard_data.json::performance.asset_class_health`).

**Rescue:**
- Aggressive dragger quarantine (kimi_signal_tracking ✓ blacklisted,
  crypto_soc_* ✓ blocked, stale models)
- ml_gatekeeper CRYPTO class gate to fix confidence inversion
- Add on-chain (funding skew, OI delta), perp basis, Hyperliquid carry
- Focus on proven subsystems (aggregated_picks, claude_gainer_st)

**Edge basis:** A few subsystems show ~80% WR / PF ~6.8, dragged by toxic emitters.

**Gate:** Post-quarantine rolling Sharpe > 0.5 + confidence calibration fix.

**Status (this session):** SHIPPED — kimi_signal_tracking blacklisted
(prior commit), crypto_soc 3 named draggers blocked, meta_strategy CRYPTO
blanket block (`5c7a8c43a27`), ghost-row 5-cohort triple block
(`597819d79c7`), ml_gatekeeper CRYPTO inversion gate (`c778f8f1696`)
defaults to threshold=70 with env override, ML staleness watchdog
hard-fail mtime gate (`db5bcfa0f04` rebased from `2b9692d4f3e`).

---

## FUTURES — silent and dead, rebuild required

**Current:** n=172, WR 17.44%, Sharpe -3.73. Almost no emission.

**Rescue:**
- Build dedicated COT + roll-yield scanner focused on CT=F + GC=F
- FinRL-style deep RL for futures rollovers
- Start paper-trading only

**Gate:** CT=F/GC=F backtest + 30d paper-pilot.

**Status (this session):** Deep-dive report shipped
(`reports/asset_class_deep_dive_FUTURES_2026-05-12.md`); CT=F anchor +
GC=F mutation plan queued.

---

## Cross-cutting enablers (this session status)

| Enabler | Status | Commit |
|---|---|---|
| 1. Data pipeline integrity (zero-PnL filter) | ✓ SHIPPED | `dd8e8282537` |
| 2. Anti-overfit gates (PBO/DSR/CPCV) | PARTIAL — DSR cron-wired; PBO/CPCV orphan | `tools/anti_overfit_audit_sidecar.py` cron |
| 3. ML staleness hard-fail | ✓ SHIPPED | `db5bcfa0f04` (rebased from `2b9692d4f3e`) |
| 4. Dragger quarantine | ✓ SHIPPED (multi-commit) | `597819d79c7`, `5c7a8c43a27`, `c778f8f1696` |
| 5. Research orchestrator + v3b signal translator | OPEN — v3b queued per DAILY_IDEAS 2026-05-12 | n/a |
| 6. Shadow/paper-trading layer | ✓ LIVE | paper_pilot.html + cot_paper_pilot.py |

## Implementation priority order

- **Week 1 (this session shipped 80%):** Data fix ✓, dragger quarantine ✓, ML staleness hard-fail ✓, updates entry ✓, truth-layer banner ✓
- **Week 2:** FOREX/FUTURES gates → COMMODITY/EQUITY paper pilots (CT=F running)
- **Week 3-4:** BOND/ETF ramp + full research orchestrator on cleaned data
- **Ongoing:** Weekly edge-stability + research loop

## Real-money rule

No capital until **at least two classes** sustain T2 metrics (PF>1.5,
WR>50%, MDD<20%, n>100, PBO<0.05, WFE>60%) for 30 consecutive days on
live/shadow data.

## NFA

Research surface only. Real-money sizing remains gated on the 10-step
Lopez de Prado AFML readiness pipeline.

## Refs

- Grok 2026-05-12 audit (verbatim above)
- Red-team verification: `reports/grok_audit_red_team_synthesis_2026-05-12.md`
- All session commits today on origin/main (~24 commits, latest `db5bcfa0f04`)
- `audit_dashboard/real_money.html` (readiness hub)
- `audit_dashboard/paper_pilot.html` (SHADOW tracker)
- `updates/2026-05-11-money-maker-master-plan.html#db-health-remediation`
