# Deep Dive — COMMODITY (FAIL class #2) — v2

**Date:** 2026-05-31
**Author:** Claude deep-dive subagent (PR #267 follow-on, DD2)
**Scope:** 90d window, `ejaguiar1_stocks.trading_picks WHERE category='commodity'`
**Verdict source:** `audit_dashboard/data/money_ready_verdict.json` (2026-05-31)
**Note:** Companion to existing `deep_dive_COMMODITY_2026-05-31.md`. This v2 focuses on the **raw 90d 0-WR collapse** (the v1 used the policy-clean cohort) and the **Phase 10b #200 non-COT pivot plan**.

---

## 0. Executive summary

The money-ready verdict for COMMODITY reports `n_resolved=7 / WR 57.1% / PF 3.87` → INSUFFICIENT_DATA. That 7-row post-policy-clean slice masks the **raw truth**: 90d COMMODITY emitted **6,820 picks** and resolved **0 wins out of 546 LOST + 84 EXPIRED**. Every strategy with n ≥ 2 is at WR=0.000. This is a systematic regime collapse, not a sample-size problem. Silver alone is 49% of dollar-PnL damage.

Recommendation: **kill all live commodity emitters**, drop COT entirely per Phase 10b plan #200, rebuild via term-structure / EIA inventory / NOAA weather signals in a 30/60/90 paper sleeve that never touches `trading_picks` until n≥100 PF≥1.5 WR≥50% MDD<20% DSR≥0.7.

---

## 1. Per-source autopsy (raw 90d)

### 1.1 By `source_system`

| source_system | n | wins | losses | exp | WR | PF | avg_pnl% |
|---|---:|---:|---:|---:|---:|---:|---:|
| multi_asset_copytrader | 486 | 0 | 410 | 76 | 0.0000 | 0.000 | -1.169 |
| cta_replicator | 121 | 0 | 116 | 5 | 0.0000 | 0.000 | -1.864 |
| combined_confidence_strategy | 6 | 0 | 5 | 1 | 0.0000 | 0.000 | -2.735 |
| multi_asset_cot | 6 | 0 | 5 | 1 | 0.0000 | 0.000 | -2.055 |
| alpha_engine | 4 | 0 | 4 | 0 | 0.0000 | 0.000 | -0.451 |
| forex_copy_trader | 2 | 0 | 2 | 0 | 0.0000 | 0.000 | -0.767 |
| non_crypto_consensus | 1 | 0 | 1 | 0 | 0.0000 | 0.000 | **-96.07** |
| alpha_engine_fast | 1 | 0 | 1 | 0 | 0.0000 | 0.000 | -2.400 |
| cftc_socrata | 1 | 0 | 1 | 0 | 0.0000 | — | NULL |
| coinglass_sentiment | 1 | 0 | 1 | 0 | 0.0000 | 0.000 | **-98.40** |
| prediction_market_agents | 1 | 0 | 0 | 1 | NULL | NULL | 0.0000 |

**Total 90d:** n=6,820 emitted · 546 LOST · 84 EXPIRED · 3 ACTIVE · **0 WON**.

### 1.2 By `strategy`

| strategy | n_closed | WR | PF |
|---|---:|---:|---:|
| futures_momentum | 413 | 0.0000 | 0.000 |
| cta_cross_asset_tsmom | 78 | 0.0000 | 0.000 |
| cta_commodity_momentum_term | 31 | 0.0000 | 0.000 |
| cta_golden_cross_200 | 6 | 0.0000 | 0.000 |
| combined_confidence | 5 | 0.0000 | 0.000 |
| cot_positioning (TRIAGED-falsified) | 5 | 0.0000 | 0.000 |
| cftc_cot_commercial_signal (BLOCKED) | 3 | 0.0000 | 0.000 |
| commodity_tsmom_12m | 2 | 0.0000 | NULL |
| gold_safe_haven | 0 | — | — (no emissions) |
| ema_stack_momentum | 0 | — | — (no emissions) |

### 1.3 Loss concentration — worst symbols

| symbol | n_closed | WR | sum(pnl%) |
|---|---:|---:|---:|
| SI=F (silver) | 149 | 0.000 | **-320.39** |
| HG=F (copper) | 116 | 0.000 | -205.85 |
| CL=F (WTI crude) | 43 | 0.000 | -122.00 |
| PL=F (platinum) | 95 | 0.000 | -110.49 |
| NG=F (nat gas) | 23 | 0.000 | -69.17 |
| CT=F (cotton) | 19 | 0.000 | -50.19 |
| GC=F (gold) | 68 | 0.000 | -45.68 |

Top-3 (SI/HG/CL) = 74% of losses. Silver = 49% of dollar damage. The CT=F 57% concentration noted in the CLAUDE.md banner reflects an earlier 28-row cohort — **current bleed is silver-led, not cotton-led**.

### 1.4 Worst exit reasons

| exit_reason | n | avg pnl% |
|---|---:|---:|
| SL_HIT_REPLAY | 240 | -3.350 |
| PRICE_RESOLVED [RECONCILED_PNL | 179 | -0.307 |
| PRICE_RESOLVED | 99 | -0.750 |
| SL_HIT | 11 | -3.081 |
| TP_HIT_RESOLVED [PRICE_MISMATCH] | 1 | **-96.07** |

SL_HIT family = ~46% of resolutions. Signals are **directionally wrong** in a regime where commodity-trend funds (DBMF, KMLM) printed positive.

Two PnL outliers (-96.07% on a `TP_HIT_RESOLVED` row; -98.40% on a `coinglass_sentiment` row) are **pipeline bugs**, not strategy bugs — exit-reason / pnl_pct decoupling. Filed as follow-up incidents.

---

## 2. External replication options

| Benchmark | Style | Live Sharpe (3y) | MaxDD | Why useful |
|---|---|---:|---:|---|
| **DBMF** (iMGP DBi Managed Futures) | SocGen CTA replicator | ~1.10 (2022–25) | -12% | Daily tradeable proxy for our `cta_cross_asset_tsmom`. Disclosed holdings = free signal. |
| **KMLM** (KFA Mt Lucas Managed Futures) | Equal-vol momentum basket | ~0.85 | -15% | Pure trend; cleanest "is commodity-trend on?" gauge. |
| **QMOM** (Alpha Architect Quant Momentum) | Equity x-sectional momentum | ~0.55 | -25% | Cross-asset momentum regime confirmer. |
| **Moskowitz–Ooi–Pedersen (JF 2012) — TS Momentum** | 12m TS momentum across 58 instruments | 1.58 | -13% | Peer-reviewed analog to `commodity_tsmom_12m`. Underperforming the paper by >50bp/m on same basket = our impl is broken. |
| **Erb & Harvey (FAJ 2006)** | Roll-yield + momentum on GSCI | IR ~0.70 | -18% | **Term-structure** signal Phase 10b #200 wants. Reproducible from free CFTC/CME data. |
| **PCRIX** (PIMCO CommodityRealReturn) | Active long + roll | ~0.45 long-only | -42% (2008/20) | Long-only baseline. Underperforming PCRIX = no edge to size. |

**Recommendation:** treat **KMLM 60d return sign + DBMF 20d momentum** as the **regime gate** — no commodity pick publishes unless both confirm direction.

---

## 3. Non-COT pivot — 30/60/90 plan (Phase 10b #200)

COT dropped. Stack = **term-structure + EIA inventory + NOAA weather**. All work runs in a **paper sleeve** (`source_system='commodity_rebuild_paper'`, status='PAPER'), never gated into live until day-90 acceptance.

### Days 0–30 — Term-structure baseline

- **Signal:** front / 6th-month log-ratio (contango / backwardation) on CL, NG, GC, SI, HG, ZC, ZW, ZS, KC.
- **Data:** CME Datamine EOD curves; yfinance continuous contracts cross-check.
- **Rule:** long when backwardation slope > +2σ vs 252d rolling; short when contango slope < -2σ. 5d hold, no pyramiding.
- **Targets to advance:** n≥40 paper, PF≥1.2, WR≥45%, MDD≤8%. Fail any → kill.
- **Concentration guard:** ≤30% single-symbol, ≤50% single-sector (energy/metals/ags).

### Days 30–60 — EIA inventory + roll-yield overlay

- **Add:** EIA Weekly Petroleum Status (CL/NG); USDA WASDE (ZC/ZW/ZS); LME warehouse (HG); COMEX inventory (GC/SI).
- **Rule:** term-structure signal × inventory-surprise (actual vs Bloomberg consensus). Long only if surprise agrees; mute if disagrees.
- **Targets to advance:** n≥80 cumulative, PF≥1.3, WR≥48%, MDD≤10%, no single strategy share >50%, DSR≥0.5.

### Days 60–90 — Weather overlay + live shadow

- **Add:** NOAA CPC 6–10d outlook + drought monitor (ags); HDD/CDD anomaly (NG).
- **Add:** **live-shadow mode** — identical logic running against `trading_picks` with `status='SHADOW'` for A/B vs real-money emitters.
- **Graduation to T2 live:** see §5.

---

## 4. Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Overfit to spring-2026 commodity tape | High | Hold out Jan–Feb 2026 + 2024 backtest; paper PF must hold ±20% on held-out window. |
| Regime shift mid-sleeve (energy spring→summer contango flip) | Med | Refit thresholds every 30d on trailing 252d. |
| Correlation creep: KMLM/DBMF gate locks long during ag divergence | Med | Per-sector gates — energy=CL+EIA, metals=KMLM, ags=weather+WASDE. |
| Data-feed lag (EIA Wed release vs Tue timestamps) | High | Pin pick ts ≥30min post release; reject feature windows crossing release boundary. |
| PnL-decoupling bugs (the -96/-98% rows) reappear in paper sleeve | Med | Resolver-validator: reject if `sign(pnl_pct) != sign((exit-entry)*dir)`. |
| Term-structure data licensing (CME Datamine limits) | Low | Quandl `OWF` + yfinance cross-check; never single-source. |
| Same-symbol cluster bleed (silver 24% of n today) | High | Hard cap 1 active per symbol per 24h; per-symbol -5R 14d kill switch. |
| SHADOW status leaks into gates | High | CI guard: `passes_smart_gate` / `passes_active_gate` assert `status != 'SHADOW'`; unit test. |

---

## 5. Acceptance criteria

### 5.1 Standard T2 (CLAUDE.md)

- n ≥ 100 closed paper, PF ≥ 1.5 net of 12 bps, WR ≥ 50%, MDD < 20%, expectancy > 0.

### 5.2 Class-specific guardrails (all must pass)

1. Single-symbol concentration ≤ 30%.
2. Single-strategy concentration ≤ 50%.
3. Sector concentration ≤ 60% (energy / metals / ags / softs).
4. DSR ≥ 0.7 on 90d slice.
5. Live-shadow vs paper PnL correlation ≥ 0.85.
6. PnL-direction validator: 100% of paper picks satisfy `sign(pnl_pct) == sign((exit-entry)*direction)`.
7. Regime-gate compliance: KMLM 60d + DBMF 20d agree with pick direction ≥ 80%.
8. Kill-on-bleed: cumulative paper DD > -7% before day 60 → freeze, require re-approval.

### 5.3 Immediate demotion for current live emitters

Per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md`:

- **`futures_momentum`** (n=413, 0% WR): KILL — add to `BLOCKED_SOURCE_SYSTEMS` post mutation analysis.
- **`cta_cross_asset_tsmom`** (n=78, 0% WR): MUTATE THEN KILL — `python tools/mutation_analysis.py`; if no axis shows WR≥40% n≥20, block.
- **`cta_commodity_momentum_term`** (n=31, 0% WR): same mutation-then-kill.
- **`cot_positioning`** + **`cftc_cot_commercial_signal`**: already TRIAGED / BLOCKED — confirm in block list.
- **`multi_asset_copytrader`** (n=486 commodity-only, 0% WR): block `category='commodity'` only; preserve other-class signal.
- **`cta_replicator`** (n=121, 0% WR): KILL entirely — commodity-CTA only, nothing to preserve.

---

## Appendix A — Live verdict JSON

```json
{
  "n_resolved": 7, "wr": 0.5714, "pf": 3.8701,
  "n_ok": false, "wr_ok": true, "pf_ok": true,
  "dsr_ok": null, "pbo_ok": null, "spa_ok": null,
  "expectancy": 0.020055, "expectancy_ok": true,
  "verdict": "INSUFFICIENT_DATA",
  "top_symbol": "GC=F", "top_symbol_share": 0.5714,
  "top_source": "UNKNOWN", "top_source_share": 0.5714
}
```

The 7-row policy-clean cohort is not representative. **Raw 90d is the operative truth: 0/546 WR.**

## Appendix B — Reproducer

```bash
python3 -c "
import mysql.connector
c=mysql.connector.connect(host='mysql.50webs.com',user='ejaguiar1_stocks',
  password='stocks1234560',database='ejaguiar1_stocks')
cur=c.cursor(dictionary=True)
cur.execute(\"\"\"SELECT source_system,strategy,COUNT(*) n,
  SUM(status='WON') w, SUM(status='LOST') l
  FROM trading_picks WHERE category='commodity'
  AND status IN ('WON','LOST','EXPIRED')
  AND created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
  GROUP BY source_system,strategy ORDER BY n DESC\"\"\")
for r in cur.fetchall(): print(r)
"
```
