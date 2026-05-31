# Fresh Strategy Build — Final Launch Plan (peer_claude, 2026-05-31)

**Wave:** build-wave 2026-05-31 (cursor statistical framework)
**Author:** peer_claude
**Goal alignment:** Goal #1 — phenomenal performance across all asset classes on `/audit`.
**Status:** 7 classical-literature strategies built; master paper-pilot harness deployed; **0 closed trades, 0 edge proven**. This is the *starting whistle*, not a result.

---

## 1. What got built

Seven strategies, each implemented from primary academic sources, each shipped with the cursor day-1 statistical framework (Wilson 95 % LB on WR vs realized break-even, bootstrap PF CI lower-bound ≥ 1.20, Bonferroni α = 0.05/7 = 0.00714, walk-forward 70/30 OOS ≥ 0.8 × IS).

Master harness status: `reports/peer_claude-master_paper_pilot_status_2026-05-31.json` (n=0 for all; paper_pilot status).

## 2. TOP-3 LAUNCH TABLE (priority for capital pilot once gates pass)

Ranking weight: literature replication strength × asset-class need on `/audit` × signal density (shots-on-goal per month).

| Rank | Strategy | Class | Citation | Build status | AI refinement | Day-1 ready |
|------|----------|-------|----------|--------------|---------------|-------------|
| 1 | Connors RSI(2) | EQUITY (extensible CRYPTO) | Connors & Alvarez 2008, *Short-Term Trading Strategies That Work* ch.2; Pardo 2010 §7; Quantpedia #46 | ✅ `/tmp/strategy_builds_2026-05-31/connors_rsi2/` + `alpha_engine/strategies/connors_rsi2.py` | Cursor framework wired (Wilson LB, bootstrap PF CI, Bonferroni) | ✅ yes — registered in master harness |
| 2 | Time-Series Momentum (TSMOM) | MULTI (EQUITY/CRYPTO/COMMODITY) | Moskowitz, Ooi & Pedersen 2012, *JFE* 104(2) | ✅ build report + harness slot | Cursor framework wired | ✅ yes |
| 3 | FX Carry Trade | FOREX | Lustig, Roussanov & Verdelhan 2011, *RFS* 24(11); Brunnermeier-Pedersen 2009 | ✅ build report + harness slot | Cursor framework wired | ✅ yes |

### Full 7-strategy roster (all in master harness, paper_pilot status)

| Strategy | Class | Cadence | Citation |
|----------|-------|---------|----------|
| connors_rsi2 | EQUITY/CRYPTO | daily | Connors & Alvarez 2008 |
| faber_tactical | MULTI | monthly | Faber 2007 *JWM* "A Quantitative Approach to Tactical Asset Allocation" |
| tsmom | MULTI | monthly | Moskowitz-Ooi-Pedersen 2012 |
| fx_carry | FOREX | monthly | Lustig-Roussanov-Verdelhan 2011 |
| magic_formula | EQUITY | monthly | Greenblatt 2006 *The Little Book That Beats the Market* |
| post_ipo_drift | EQUITY | daily | Loughran & Ritter 1995 *J. Fin.* 50(1) |
| piotroski | EQUITY | annual | Piotroski 2000 *J. Acc. Res.* 38 |

## 3. Operator action plan

### Day 1 (today, 2026-06-01 EST)
- All 7 strategies enter **paper-pilot shadow mode** via the master harness (`tools/master_paper_pilot.py` invoked nightly).
- Daily cron: emit picks at next-bar open (Connors RSI(2), Post-IPO Drift), monthly cron for tactical/momentum/carry/magic, annual for Piotroski.
- Write per-pick rows with `intent_ts`, `entry_ts`, `entry_px`, `tp`, `sl`, `holding_max_bars`, `strategy_slug`, `bonferroni_family_id="wave_2026-05-31"`.
- **No real capital. Zero exceptions.**

### Day 30 (2026-06-30 EST) — interim Wilson-LB report
- n-check by strategy. Daily strategies (Connors, IPO-drift) should be n=30-100; monthly strategies n=1-3; annual=0.
- Emit `reports/peer_claude-fresh_strategy_day30_wilson_2026-06-30.md` with Wilson 95 % LB on realized WR vs realized break-even WR.
- **Decision:** any strategy with n < 10 stays in pilot; any with Wilson LB already < 0.30 → quarantine + autopsy.

### Day 60 (2026-07-30 EST) — early Bonferroni-adjusted gate evaluation
- Per-test α = 0.05 / 7 = **0.00714**.
- Compute p-value of (realized WR vs realized BE) under binomial null; require p < 0.00714 to clear.
- Bootstrap PF CI lower-bound ≥ 1.20 required.
- Walk-forward 70/30: OOS PF ≥ 0.8 × IS PF.
- **Decision:** strategies failing 2+ of {Wilson LB, PF CI, p-Bonferroni} get *frozen* — no more new picks, only carry existing open positions to settlement.

### Day 90+ (≥ 2026-08-29 EST) — graduation decision
- Any strategy passing **all four gates** at **n ≥ 500** is eligible for operator decision on live capital.
- Operator-only decision; no autonomous promotion.
- Even on pass: enter `SHADOW → LIVE_ELIGIBLE` per the real-money state machine; size starts at < 0.5 % NAV.

## 4. Honest disclaimer (read before any capital decision)

Building strategies from academic literature **does not guarantee** they will show edge on this stack's data, execution, or cost structure. Replication crises are widespread:

- **Piotroski 2000's 23.5 % abnormal return** has been heavily challenged in replication. McLean & Pontiff 2016 *JF* documents that ~58 % of US-anomalies decay post-publication, average decay ~32 %. Piotroski survives in some samples and not others.
- **Loughran-Ritter 1995 post-IPO underperformance** is regime- and universe-sensitive; the original effect was concentrated in small-cap, low-book-to-market issues during 1970-1990. Modern IPO universes (SPACs, direct listings, biotech) may not replicate.
- **TSMOM Moskowitz 2012** has weakened substantially in EQUITY after 2010 per Baltas & Kosowski 2020 and AQR's own published commentary; remains stronger in COMMODITY and FX.
- **FX Carry** Lustig-Roussanov 2011 includes the 2008 crash period; carry is *known* to crash during global risk-off. Sharpe after costs/slippage is materially lower than headline.
- **Connors RSI(2)** Connors & Alvarez 2008 backtest is famously vulnerable to selection bias in the test universe; Aronson 2007 *Evidence-Based Technical Analysis* shows most published mean-reversion edges fail OOS without a 200-MA regime filter (which we *do* include).
- **Magic Formula** Greenblatt 2006 has had mixed live results in mutual-fund implementations (Formula Investing fund 2009-2014 underperformed S&P 500 by ~3 %/yr).
- **Faber Tactical 2007** survived 2008 well but has shown decay since 2014 due to QE-suppressed volatility and trend-breakdown frequency increase.

Cost reality: even a true 60 % WR / PF 1.40 strategy can be eliminated by:
- Slippage on illiquid exits
- Funding/carry costs on FX/CRYPTO
- Borrow costs on small-cap shorts (not used here — long-only roster)
- Tax drag (not modeled)

**Paper-pilot is mandatory.** No exceptions. n=500 minimum at all four gates passing before any operator-decision conversation about live capital.

## 5. Artifacts produced this wave

| File | Purpose |
|------|---------|
| `reports/peer_claude-strategy-build-connors_rsi2_2026-05-31.md` | Connors RSI(2) build |
| `reports/peer_claude-strategy-build-tsmom_2026-05-31.md` | TSMOM build |
| `reports/peer_claude-strategy-build-fx_carry_2026-05-31.md` | FX Carry build |
| `reports/peer_claude-strategy-build-magic-formula_2026-05-31.md` | Magic Formula build |
| `reports/peer_claude-strategy-build-piotroski_2026-05-31.md` | Piotroski F-Score build |
| `reports/peer_claude-strategy-build-post-ipo-drift_2026-05-31.md` | Post-IPO Drift build |
| `reports/peer_claude-master_paper_pilot_status_2026-05-31.json` | Master harness state (n=0 day-0) |
| `reports/peer_claude-FRESH_STRATEGY_BUILD_FINAL_LAUNCH_PLAN_2026-05-31.md` | This file |
| `alpha_engine/strategies/connors_rsi2.py` | Connors implementation |

## 6. Where this fits in the bigger plan

Per `CLAUDE.md` Goal #1: 0/6 classes pass Tier 2 today. The 7 fresh strategies are *additional shots on goal* — they do not fix EQUITY's PF 0.90 / WR 33 % on the existing roster, but they add 7 independent, citation-backed signal sources whose decorrelation with existing picks could materially change the per-class verdict if even 2-3 graduate.

Concurrent work (do not block on this wave):
- Resolver intrabar work — upstream T2 blocker per memory `project-session-close-2026-05-31.md`.
- Existing-strategy mutation per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.
- Tournament resolver fixes (now n≥100 across 13 models).

Wave success criterion: ≥ 1 of 7 strategies clears all four day-90 gates at n ≥ 500. Honest expected base-rate per the replication literature: **1-2 of 7** is realistic; **0 of 7** is plausible; **3+ of 7** would be remarkable and should itself trigger a red-team audit.

---

*Generated 2026-05-31 by peer_claude. Sources: `/tmp/strategy_builds_2026-05-31/` build dirs, `reports/peer_claude-strategy-build-*_2026-05-31.md`, master harness JSON. Cursor framework reference: `reports/peer_claude-phase5-strategy-stats-schema-mismatch_plan_2026-05-31.md`.*
