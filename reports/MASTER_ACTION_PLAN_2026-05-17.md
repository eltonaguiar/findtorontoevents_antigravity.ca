# MASTER ACTION PLAN — 2026-05-17
**Generated:** 2026-05-17 ~20:00 UTC | **Corrected:** 2026-05-18 ~00:15 UTC (peer validation invalidated CRYPTO/COMMODITY verdicts)
**Predecessor:** `reports/MASTER_ACTION_PLAN_2026-05-15.md`  
**Sources:** live `money_ready_verdict()`, `pf_registry.json` (canonical), `dashboard_data.json`, peer swarm cross-validation (claude-opus-4-7 SESSION_SUMMARY), Kimi ACTION_PLAN, FOOLPROOF_ACTION_PLAN, GOLDEN_STANDARD_ACTION_PLAN, SUPREME_PLAN_90days, 5-agent synthesis (2026-05-12)

> ⚠️ **CORRECTION (00:15 UTC):** Cross-PC peer validation (claude-desktop-081g9oh) invalidated both CRYPTO MONEY_READY and COMMODITY WATCH verdicts. See Section 1a for details. **No asset class is currently real-money ready.**

---

## 1. MONEY-READY VERDICT DASHBOARD (Corrected — 2026-05-18 00:15 UTC)

**Canonical source: `audit_dashboard/data/pf_registry.json::by_asset_class_policy_clean_net`**

| Class | Verdict | PF (canonical) | PF (raw, inflated) | n (deduped) | Blocker |
|---|---|---|---|---|---|
| **CRYPTO** | 🔴 NOT_READY | **1.28** | ~~2.54~~ | 2021 | ml_enhanced sprawl: 147/149 variants unquarantined; family PF=0.64 |
| **COMMODITY** | 🔴 NOT_READY | **1.17** | ~~2.15~~ | 160 | 47% duplicate re-emissions; CT=F 84.9% concentration; COT 3d lag |
| **ETF** | 🟡 WATCH | est. 2.25 | — | 75 | n<100; OOS WR=75% (5 folds) — closest to ready |
| **EQUITY** | 🔴 INSUFF_DATA | 0.72 | — | 31† | MySQL sync 2026-05-24; local data only |
| **FOREX** | 🔴 NOT_READY | 0.33 | — | 392 | DSR=0.0, E=-0.002, hard-disabled |
| **BOND** | 🔴 INSUFF_DATA | — | — | 1‡ | Scanner wired today; data accumulating |
| **FUTURES** | 🔴 INSUFF_DATA | 0.96 | — | 12 | multi_asset_copytrader blocked |

†Local only — MySQL has n=240, WR=53.3%  
‡USDJPY=X misclassification fixed; real data starts 2026-05-17

### 1a. Why CRYPTO and COMMODITY verdicts were wrong (peer validation)

**CRYPTO — ml_enhanced mining sprawl (3-agent swarm confirmed):**
- Our `money_ready_verdict()` 3-layer filter only excludes 2 of 149 `ml_enhanced` variants
- 97.7% of the "clean" 443-pick set is ml_enhanced; family PF = 0.64 (net loser)
- Non-ml_enhanced CRYPTO: n=14 picks, PF=0.40
- DSR/SPA passed because they test return series shape, not source validity
- **M-105 required:** quarantine entire ml_enhanced family pending per-variant SPA validation

**COMMODITY — three stacked inflation artifacts:**
1. 47% duplicate re-emissions in raw `closed_picks.json` → PF 2.28 collapses to **1.17** deduped
2. CT=F concentration 84.9% → ex-CT=F PF = **0.28** (single-symbol bet disguised as diversification)
3. COT 3-day CFTC publication lag (PR #941) → WR 87% → **45-55%** post-correction

**DSR nb_trials=1 — peer claim REJECTED (3-engine swarm confirmed correct):**
- `_dsr_gate()` tests pooled class aggregate, not a selected-best from 149 variants
- Selection bias is upstream; nb_trials=1 is mathematically sound — do NOT revert M-076

**elite_score — peer claim CONFIRMED:**
- WR by quartile: Q1=30.9%, Q2=25.4%, Q3=26.4%, Q4=38.0% — non-monotonic, eff=0.06
- Do not gate on elite_score; it has zero stable discriminating power
| **ETF** | 🟡 WATCH | 66.7% | 2.25 | 75 | N/A | N/A | N/A | ✅ est. | ❌ n<100 |
| **EQUITY** | 🔴 INSUFFICIENT_DATA | 35.5%† | 0.72† | 31† | None | None | None | ❌ -0.033† | ❌ |
| **FOREX** | 🔴 NOT_READY | 33.3% | 0.48 | 618 | ❌ 0.0 | N/A | ✅ | ❌ -0.002 | ❌ Hard-disabled |
| **BOND** | 🔴 INSUFFICIENT_DATA | 0% | 0.0 | 1‡ | None | None | None | None | ❌ |
| **FUTURES** | 🔴 INSUFFICIENT_DATA | 16.7% | 0.96 | 12 | None | None | None | None | ❌ |

*PBO N/A: needs ≥5 strategies, currently 3  
†EQUITY local data only (n=31); MySQL has n=240, WR=53.3%, PF=1.41 — sync pending 2026-05-24  
‡BOND scanner just fixed today (was running proof-of-concept spike, not production); real data accumulation begins 2026-05-17

---

## 2. PER-CLASS ACTION PLANS

---

### 🟢 CRYPTO — MONEY_READY (maintain + optimize)

**Current state:** WR=66.4%, PF=2.54, DSR=1.0, PBO=0.007, E=+0.029  
**Sized at:** 25% fractional Kelly (BLOCKED_SYMBOLS filter in place)

**Blockers resolved this session:**
- BLOCKED_SYMBOLS PF filter now applies 3-layer filter (global + per-class + symbol) — PF was 0.98, now correctly 2.54
- CRYPTO stop-loss direction bug fixed
- ml_enhanced_BTCUSDT/ADAUSDT_15m_D SHORT direction blocked (WR=17%)

**Remaining drag (requires STRATEGY_INVESTIGATION_BEFORE_KILL.md):**
- `quan_engine`: 18% of CRYPTO volume, WR=30.4%, PF=0.41 — massive aggregate drag
- `rapid_fire`: WR=29%, PF=0.16 — losing strategy

**Elite sources to protect:**
- `mega_mutation`: WR=60.6%, PF=2.61, n=94
- `kimi_riseoftheclaw`: WR=58.4%, PF=1.65, n=89
- `claude_gainer_st`: WR=56.4%, PF=1.48, n=110
- `baby_strats_forward`: WR=51.9%, PF=1.65, n=539

**Action items:**
| ID | Action | Priority | ETA | Status |
|---|---|---|---|---|
| **M-105** | **Quarantine entire ml_enhanced family** — add source-prefix block in money_ready_verdict for CRYPTO until each of 147 variants passes per-variant SPA (n≥20 each). Downgrade CRYPTO to NOT_READY immediately. | **P0** | **2026-05-18** | **PENDING** |
| C-1 | Write STRATEGY_INVESTIGATION for quan_engine + block CRYPTO | P0 | 2026-05-24 | PENDING |
| C-2 | Write STRATEGY_INVESTIGATION for rapid_fire + block CRYPTO | P0 | 2026-05-24 | PENDING |
| C-3 | M-034 CRYPTO_CONF_INVERSION_GATE enable | P1 | 2026-06-15 | SHADOW (logger wired today) |
| C-4 | BTC UTC-hour filter (reject 08-09Z, boost 22Z) | P1 | 2026-05-24 | In quality_gates, verify active |
| C-5 | Funding rate arb on ETH/DOGE/AVAX | P2 | 2026-06-01 | Research |
| C-6 | Pairs cointegration strategy | P2 | 2026-06-15 | Research |

**Unlock condition:** After C-1/C-2, expect PF to rise from 2.54 → 3.5+ on filtered universe

---

### 🟡 COMMODITY — WATCH (1-2 weeks to MONEY_READY)

> ## ⛔ CORRECTION 2026-05-18 — COMMODITY section is STALE. Do NOT action O-5.
>
> The claim **"CT=F Cotton edge is real"** and **O-5 (first real-money pilot
> $500-2000 on `cot_positioning` CT=F SHORT, ETA 2026-05-23)** are FALSIFIED.
>
> Evidence (`reports/EDGE_VERDICT_2026-05-18.md`, PR #1195/#1200):
> - 13-year real-CFTC-COT walk-forward backtest (`tools/cot_edge_research.py`):
>   COT-z pooled hit-rate **53.8%**, year-unstable — not an edge.
> - `cot_positioning` excluding CT=F: **n=20, WR 30%, PF 0.51** — a loser.
>   The whole "edge" IS the CT=F COT-row-duplication leakage artifact.
> - DSR 1.0 / SPA-pass on cot_positioning are **artifacts** — they test the
>   return series, not the 85%-one-symbol concentration or the data corruption.
>
> **O-5 must NOT proceed** — sizing real money on `cot_positioning CT=F SHORT`
> stakes capital on a leakage artifact (repeat of the cotton stale-pre-kill-data
> trap, `project_cotton_blacklisted`). O-1 (COT lag patch) is moot — COT-z is
> dead regardless of the 3-day lag. The COMMODITY "WR 60.2% PF 2.15 DSR 1.0"
> numbers below are CT=F-leakage-inflated, not verdict-grade.
>
> COMMODITY is NOT 1-2 weeks from MONEY_READY. It has no concentration-clean,
> leakage-free edge today. Authoritative: `reports/EDGE_VERDICT_2026-05-18.md`.
>
> ---
>

**Current state:** WR=60.2%, PF=2.15, DSR=1.0, SPA=✅, E=+0.014  
**Blocker:** CT=F concentration 65.25% (above 30% cap) → PBO N/A (only 3 strategies)

**CT=F Cotton edge is real:** multi_asset_cot n=114 WR=87% PF=3.80; multi_asset_copytrader CT=F n=116 WR=84% PF=3.63

**Non-CT=F drag eliminated today:**
- cta_cross_asset_tsmom COMMODITY LONG+SHORT blocked (CL=F WR=19%, NG=F WR=0%)
- cta_commodity_momentum_term blocked (ZC=F WR=0%, ZS=F WR=0%)  
- cta_replicator umbrella block added

**Remaining blockers:**
1. **Concentration cap** (CT=F = 65.25% of picks → triggers concentration_capped=True → limits verdict)
2. **COT lag correction (M-021)** — 3-day publication lag on CFTC COT data may inflate WR; need re-run
3. **PBO needs 5+ strategies** — only 3 COMMODITY strategies qualify

**Action items:**
| ID | Action | Priority | ETA | Status |
|---|---|---|---|---|
| O-1 | COT lag-corrected re-run (M-021) — patch 3d lag in cot_positioning | P0 | 2026-05-24 | PENDING |
| O-2 | Add 2+ non-CT=F COMMODITY strategies to reach PBO threshold | P1 | 2026-05-31 | PENDING |
| O-3 | Commodity carry-momentum strategy wire-up (Miffre 2008, commodity_carry_momo.py exists) | P1 | 2026-05-31 | PENDING |
| O-4 | Diversify CT=F allocation cap to 40% max; add HE=F (Live Cattle), ZW=F (Wheat), KC=F (Coffee) | P1 | 2026-05-24 | PENDING |
| O-5 | First real-money pilot at $500-$2,000 on cot_positioning CT=F SHORT | P0 | 2026-05-23 | FOOLPROOF_PLAN target |

**Unlock condition:** O-1 + concentration below 30% → PBO computable → MONEY_READY

---

### 🟡 ETF — WATCH (1-2 weeks to MONEY_READY)

**Current state:** WR=66.7%, PF=2.25, n=75, OOS WR=75% (5 folds)  
**Blocker:** n<100 (gate is 100); 0 closed picks until today

**Fixed today:**
- `etf_rsi2_pullback` strategy added (RSI2<10 BUY, 2-5 day hold vs 10-week momentum)
- 80+ ETF symbols already defined; scanner was generating active picks, none closing

**Action items:**
| ID | Action | Priority | ETA | Status |
|---|---|---|---|---|
| E-1 | Accumulate n≥100 (natural, ~1-2 weeks with RSI2 cycling) | P0 | 2026-05-31 | IN PROGRESS |
| E-2 | Promote to live sizing at 3.9% once n≥100 | P0 | 2026-05-31 | DATA-GATED |
| E-3 | VIX<25 gate wire to ETF sector emitter (PF lift 2.05→3.22 per gap analysis) | P1 | 2026-05-24 | PENDING |
| E-4 | Sector dual-momentum (Antonacci GEM, 9 SPDR sectors) | P2 | 2026-06-15 | PENDING |

**Unlock condition:** E-1 done — MONEY_READY within 2 weeks

---

### 🔴 EQUITY — INSUFFICIENT_DATA (MySQL sync unlocks 2026-05-24)

**Current state (local):** WR=35.5%, PF=0.72, n=31 (misleading — only local resolver picks)  
**True state (MySQL/dashboard):** WR=53.3%, PF=1.41, n=240, OOS WR=66.1% (7 folds)  
**Root cause:** Local closed_picks.json has n=44 (37 from stocks_rsi2_pullback). DSR/PBO/SPA need ≥2 strategies with n≥20 locally. Only 1 qualifies.

**Fixed today:**
- EQUITY_SYMBOLS expanded: 20 → 35 symbols (added JPM, BAC, V, MA, WMT, HD, PG, KO, PEP, JNJ, PFE, CVX, AVGO, COST, LLY)
- stocks_rsi2_pullback now scans 47 symbols (up from 37, added UNH, GS, WFC, MS, ADBE, INTC, QCOM, TXN, C, AXP)
- ml_enhanced 15m ADAUSDT/BTCUSDT SHORT direction blocked (WR=17%)

**Action items:**
| ID | Action | Priority | ETA | Status |
|---|---|---|---|---|
| Q-1 | MySQL ghost-row purge → data sync | P0 | 2026-05-24 | PA CONSOLE ACTION |
| Q-2 | Block AMD EQUITY once n≥20 (currently n=12 WR=8%) | P1 | Data-gated | MONITOR |
| Q-3 | Block NIO EQUITY once n≥20 (currently n=4 WR=0%) | P1 | Data-gated | MONITOR |
| Q-4 | PEAD (post-earnings drift) strategy — pead_equity.py exists, needs PF≥1.5/WR≥50% backtest | P1 | 2026-06-01 | PENDING |
| Q-5 | DOW tilt (Tue/Wed long bias) — EQUITY_DOW_TILT env flag exists, disabled | P2 | 2026-05-24 | SHADOW |
| Q-6 | Overnight-intraday reversal — tools/research/overnight_intraday_reversal.py | P2 | 2026-06-15 | RESEARCH |

**Unlock condition:** Q-1 (2026-05-24) → local n≥100 → DSR/PBO/SPA computable → target MONEY_READY

---

### 🔴 FOREX — NOT_READY (mutate-before-kill protocol active)

**Current state:** WR=33.3%, PF=0.48, DSR=0.0, E=-0.002  
**Status:** FOREX_HARD_DISABLE active (M-007). Negative expectancy confirmed.

**What's blocked:**
- Aggregate FOREX losing money: avg_win=0.0038, avg_loss=0.0049 post-slippage
- DSR=0.0 (hardest statistical fail — strategy is purely noise)
- ig_contrarian_sentiment LONG already blocked (FOREX WR=16.3% n=196)

**Only salvageable signal:**
- ig_contrarian_sentiment SHORT: WR=60.7%, n=56 — T1-quality but tiny
- cta_cross_asset_tsmom SHORT: WR=71.4%, PF=3.61 — explicitly preserved

**Action items:**
| ID | Action | Priority | ETA | Status |
|---|---|---|---|---|
| F-1 | Maintain FOREX_HARD_DISABLE until carry backtest clears | P0 | Ongoing | ACTIVE |
| F-2 | Forex carry factor backtest (tools/research/forex_carry.py) — need PF>1.0, WR>45% | P1 | 2026-06-01 | PENDING |
| F-3 | Non-JPY SHORT re-enable when n_short≥30 | P1 | Data-gated | MONITOR |
| F-4 | FOREX_COPYTRADER_ENABLE override for cta_cross_asset_tsmom SHORT if confirmed | P2 | 2026-06-01 | PENDING |

**Unlock condition:** Carry backtest PF>1.0 + 30d paper non-JPY SHORT WR≥50% — 6+ months

---

### 🔴 BOND — INSUFFICIENT_DATA (scanner just wired)

**Current state:** WR=0%, PF=0.0, n=1 (USDJPY=X was misclassified as BOND — fixed today)  
**Real data accumulation begins:** 2026-05-17 (bond_scanner now running on 14 real bond ETFs)

**Fixed today:**
- bond_scanner was running proof-of-concept spike (`bond_emitter_spike.py`) — fixed to `bond_scanner.py --merge`
- USDJPY=X misclassification in outcome_resolver fixed (=X suffix now wins over asset_class field)

**Bond strategies wired:** yield_momentum, duration_rotation, mean_reversion, yield_curve_slope, connors_rsi2, credit_spread_mean_reversion

**Action items:**
| ID | Action | Priority | ETA | Status |
|---|---|---|---|---|
| B-1 | Accumulate n≥20 on ≥2 bond strategies (natural) | P0 | ~2026-06-14 | IN PROGRESS |
| B-2 | UST TSMOM (time-series momentum on TLT/IEF/SHY) — ust_tsmom.py exists | P1 | 2026-06-01 | PENDING |
| B-3 | FRED_API_KEY GitHub secret (Issue #1095) — enables macro-driven bond signals | P1 | Admin | BLOCKED |
| B-4 | Live sizing gate: n≥100 AND PF>1.3 AND WR>50% (no exceptions) | P0 | Data-gated | ENFORCED |

**Unlock condition:** 3-4 weeks natural accumulation; formal review 2026-06-14

---

### 🔴 FUTURES — INSUFFICIENT_DATA (abandon current strategies)

**Current state:** WR=16.7%, PF=0.96, n=12  
**Root cause:** 100% of picks from multi_asset_copytrader — both LONG (WR=2%, n=147) and SHORT (WR=5.4%, n=56) blocked today. Same CT=F/SI=F symbols show WR=85.7% under COMMODITY COT strategies → strategy failure, not symbol failure.

**Action items:**
| ID | Action | Priority | ETA | Status |
|---|---|---|---|---|
| FU-1 | Both multi_asset_copytrader LONG+SHORT FUTURES blocked (done) | P0 | DONE | ✅ |
| FU-2 | Research term-structure momentum as replacement FUTURES strategy | P2 | 2026-07-01 | DEPRIORITIZED |

**Unlock condition:** New strategy with n≥100 + PF>1.5 (6+ months minimum)

---

## 3. CROSS-CLASS INFRASTRUCTURE (applies to all classes)

| ID | Item | Priority | ETA | Status |
|---|---|---|---|---|
| I-1 | Post-cost expectancy gate (E>0) — warning-only, hard gate 2026-06-17 | P0 | 2026-06-17 | WIRED today (warning) |
| I-2 | Regime conditioning — require edge on ≥2 regimes (bull/bear/sideways) | P1 | 2026-06-01 | PENDING |
| I-3 | MDD ≤ 20% + CVaR tail-risk gate (tbot.augustwheel lesson: 1 bad trade = 69% losses) | P0 | 2026-05-31 | PENDING |
| I-4 | Per-symbol autopsy workflow — auto-flag symbol+strategy with n≥20 and WR divergence | P1 | 2026-05-31 | PENDING |
| I-5 | Slippage model wire-up (PR #1026 scaffold) → post-cost PF/Sharpe | P0 | 2026-05-24 | PENDING |
| I-6 | Concentration gate: top-symbol <30% + top-strategy <30% + top-regime <30% | P1 | 2026-05-31 | PARTIAL (symbol only) |
| I-7 | M-034 CRYPTO_CONF_INVERSION_GATE enable | P1 | 2026-06-15 | SHADOW (logger wired) |
| I-8 | META_LABEL_GATE_ENFORCE=1 review | P1 | 2026-05-24 | SHADOW |
| I-9 | FRED_API_KEY GitHub secret | P1 | Admin | BLOCKED |

---

## 4. CONVERGENCE MAP (multi-plan consensus)

Items appearing in ≥3 prior plans (Kimi, FOOLPROOF, GOLDEN_STANDARD, SUPREME, 5-agent):

| Item | Plans | Consensus verdict |
|---|---|---|
| CT=F COT edge real | All 5 | Ship COMMODITY paper pilot 2026-05-23 |
| FOREX kill / hard-disable | All 5 | Maintain M-007; carry backtest prerequisite |
| Trust-tier inversion fix | Kimi, Golden, 5-agent | HC gate lowered 6→5 today ✅ |
| Confidence inversion (CRYPTO) | All 5 | M-034 shadow pending; M-035 already live |
| Data trust > alpha hunt | Supreme, 5-agent, Review | MySQL sync 2026-05-24 is single highest unlock |
| DSR as primary discriminator | Supreme, 5-agent | Wired; DSR=1.0 on CRYPTO/COMMODITY |
| Post-cost slippage model | FOOLPROOF, Supreme, Review | Expectancy gate wired today (warning) ✅ |
| 15m timeframe = overfit-bait | 5-agent, Checkpoint | ml_enhanced 15m SHORT blocked ✅ |
| Position sizer rebuild | FOOLPROOF, Supreme | vol-target + max-per-name, still pending |

---

## 5. 30/60/90 DAY ROADMAP

### 30 Days (by 2026-06-17)

| Class | Target | Key action |
|---|---|---|
| COMMODITY | MONEY_READY | COT lag fix + paper pilot + concentration <30% |
| ETF | MONEY_READY | n≥100 natural accumulation + VIX gate |
| CRYPTO | Improve PF → 3.5+ | quan_engine + rapid_fire investigation + block |
| EQUITY | WATCH → closer | MySQL sync 2026-05-24; symbol expansion accruing |
| BOND | n≥20 on 2 strategies | Natural accumulation |
| FOREX | Maintain disabled | Carry backtest underway |
| FUTURES | Maintain disabled | Deprioritized |

**Infrastructure milestones:**
- 2026-05-23: COMMODITY first real-money pilot ($500-$2,000, cot_positioning CT=F SHORT)
- 2026-05-24: MySQL purge → EQUITY data sync; META_LABEL_GATE review
- 2026-06-01: MDD/CVaR gate live
- 2026-06-15: M-034 shadow review; BOND 30-day check
- 2026-06-17: Expectancy gate promoted to hard gate

### 60 Days (by 2026-07-17)

- **COMMODITY T1 target:** PF>2.0, WR>55%, MDD<15%, position sizer live
- **EQUITY WATCH → MONEY_READY:** post-MySQL data + AMD/NIO symbol blocks + PEAD strategy
- **ETF live sizing:** 3.9% fractional Kelly
- **CRYPTO enhanced:** quan_engine/rapid_fire fully blocked; PF target 3.5+

### 90 Days (by 2026-08-17)

- **2+ classes generating real P&L** (COMMODITY + ETF confirmed, EQUITY probable)
- **FOREX carry backtest verdict** (promote or kill permanently)
- **BOND first live sizing** (if n≥100 + PF>1.3)
- **Regime conditioning live** across all classes
- **Target portfolio:** PF>1.6, Sortino>1.8, MDD<12-15% (SUPREME_PLAN_90days target)

---

## 6. TODAY'S SESSION COMMITS (2026-05-17)

| Commit | Description |
|---|---|
| `9981f110a0` | feat(etf): etf_rsi2_pullback short-term strategy |
| `d6c31c0fb7` | fix(bond): bond_scanner production wiring + =X classification |
| `4cd293d04e` | feat(equity): EQUITY_SYMBOLS +15 + STOCK_SYMBOLS +10 |
| `aeb4c06f1e` | test: ig_contrarian_sentiment LONG already blocked (FOREX), test coverage |
| `825b3ede01` | perf(hc-gate): trust_score HC 6→5 (ts=5 WR=75.9% > ts=6 WR=67%) |
| `ac4ef55287` | gate(commodity): cta_replicator COMMODITY LONG+SHORT umbrella block |
| `f528f6c680` | feat(money-ready): post-cost expectancy gate warning-only |
| `c135d04e09` | feat(m034): M-034 shadow logger wired |
| `3384f3e120` | test: cta_cross_asset_tsmom COMMODITY+FOREX direction coverage |

**Total quality gate blocks added this session:** 8 direction triples  
**Tests:** 120/120 passing

---

## 7. OPEN DECISIONS (requires human/PA action)

| Decision | Owner | Deadline |
|---|---|---|
| MySQL ghost-row purge (PA console) | PA | 2026-05-24 |
| COMMODITY real-money pilot approval ($500-$2,000) | User | 2026-05-23 |
| FRED_API_KEY GitHub secret | Admin | ASAP |
| DB password rotation | 50webs operator | Ongoing |
| quan_engine/rapid_fire kill approval (after investigation doc) | User | 2026-05-24 |
| FOREX carry backtest green light | User | 2026-06-01 |

---

*Living document — successor: `reports/MASTER_ACTION_PLAN_2026-05-24.md` after MySQL sync*
