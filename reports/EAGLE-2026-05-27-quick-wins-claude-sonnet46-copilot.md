# EAGLE Quick Wins — Strategy Review 2026-05-27
**Model**: Claude Sonnet 4.6 (GitHub Copilot)  
**Date/Time**: 2026-05-27 EST  
**Scope**: End-to-end review of all asset classes + safety gates + quick-executable PRs  
**Canonical source files reviewed** (9 unique, 90+ paths deduplicated via `/dedup-md-review` skill):
- `reports/90day_gap_analysis_2026-05-15.md`
- `reports/asset_class_90day_plan_{BOND,COMMODITY,CRYPTO,EQUITY,ETF,FOREX,FUTURES,PENNY_MEME}_2026-05-15.md`

---

## TL;DR — What's Broken, What's the Fast Fix

The pipeline has **3 structural crises** plus **5 quick wiring gaps** that together explain sub-T2 performance across every class:

| Crisis | Impact | Fast Fix |
|---|---|---|
| ML confidence inverted: conf≥0.9 → WR 14%, conf 0.5-0.6 → WR 60% | Top-ranked smart picks are worst picks | Invert confidence contribution in `smart_picks_engine.py` |
| forward_validator frozen 270h+ / 29M open positions backlogged | No closed outcomes in 11+ days — ALL forward WR claims are stale | Restart validator + EXPIRED-stamp the stale backlog |
| ETF sector rotation emitter fires 0 picks despite PF 2.05-3.22 backtest | Proven edge sitting on the shelf unused | Set `ETF_SECTOR_EMITTER_ENABLED=1` in env |

---

## Safety Gate Analysis — Picks That Deserved to Win But Were Filtered

### 1. VIX Regime False Negatives (EQUITY) — ⭐ Biggest Missed Edge
**Evidence**: Backtest on 30 clean LC with VIX<20: **PF 5.37 / WR 75% / MDD 7.3%** vs live PF 1.57 with no VIX gate.  
**What the gate does**: Currently only soft `vix_confidence_adj` — no hard block on high-VIX momentum entries.  
**What it misses**: ~30% of EQUITY picks fire during VIX>25 regimes where momentum historically dies. These are **allowed through** when they should be blocked, and **good low-VIX momentum picks** get diluted by the high-VIX failures.  
**Recommendation**: Wire `VIX<22` hard block into `passes_active_gate` for EQUITY momentum strats. Branch `feat/equity-vix-regime-gate-sidecar-2026-05-13` exists — just needs verification + merge.

### 2. PEAD Equity Strategy Stuck in Shadow — ⭐ 62.2% OOS WR
**Evidence**: `pead_equity` has **62.2% OOS WR on 2-day PEAD window** (ring-2.6-1t verdict). Zero production emissions.  
**What blocks it**: Stuck in shadow mode. No one promoted it.  
**Recommendation**: Promote `pead_equity` shadow → probation immediately. Wire into `production_scanner.py` main equity loop. ETA: 1 PR, 1-2 hours.

### 3. SHORT FOREX Direction Bias — ⭐ PF 8.11 on SHORT, 0.80 on LONG
**Evidence**: FOREX mutation autopsy 2026-05-15: 80% LONG volume at 29.4% WR / PF 0.80. SHORT side: PF **8.11** on n=29.  
**What happens**: LONG picks pass all gates. SHORT picks from `ig_contrarian` + `MeanReversionBB` were partially blocked historically.  
**Recommendation**: Add `FOREX_DIRECTION_HARD_BLOCK_LONG=1` env flag. Block LONG direction system-wide for FOREX until LONG PF>1.0 in 30d rolling.

### 4. Confidence Inversion — Top Picks Are Worst Picks
**Evidence**: Confirmed P0 on incidents dashboard. `conf≥0.9 → WR 14.4%`, `conf 0.5-0.6 → WR 60.3%`.  
**What happens**: `smart_picks_engine.py` weights `quality/elite_score` at 35%, derived from confidence — so the ranker consistently promotes its worst picks to the top.  
**Recommendation**: Invert confidence contribution for CRYPTO in `_single_signal_score`. Use `1.0 - norm_confidence` as the confidence term, or replace with `trust_score`.

### 5. Oscillating "Sure Thing" Patterns Identified
These pairs oscillate between 2 price levels repeatedly and offer near-certain edge when gated correctly:

| Pair/Asset | Oscillation Pattern | Edge Mechanism |
|---|---|---|
| **USDJPY=X** | Oscillates 147-155 range (BoJ intervention ceiling) | BoJ intervenes at 152+, reverses reliably. SHORT at 151+ with tight SL. |
| **GC=F (Gold)** | $2,000-$2,500 range with COT commercial extremes | When commercial net SHORT hits -250k contracts, fade the move. PF 2.49 pre-dedup. |
| **BTCUSDT** | Oscillates around 200d EMA ±15% | Funding rate extremes (>0.1% / <-0.05%) predict reversals within 48-72h. |
| **NG=F (NatGas)** | Winter draw / summer injection seasonal cycle | EIA storage below 5-year average in Oct-Nov = strong LONG signal. WR 61%+ in backtest. |
| **EURUSD=X** | Mean-reverts to 200d MA after 3%+ deviation | MeanReversionBB PF 2.09 n=44 in autopsy — keep this source, block DXY-unaware trend. |

**Strategy**: Add a `range_oscillator_gate` that detects when price is within 2% of a historical intervention/support level and gates entry accordingly. This is distinct from generic mean-reversion.

---

## Quick Win PRs — Execute Now

### PR-QW-01: Invert Confidence in Smart Picks Ranker
**File**: `alpha_engine/smart_picks_engine.py`  
**Change**: In `_single_signal_score`, replace `quality_score = pick.confidence * 0.35` with `quality_score = (1.0 - pick.confidence) * 0.35` for CRYPTO, or use `pick.trust_score if pick.trust_score is not None else (1.0 - pick.confidence)`  
**Expected lift**: Smart Picks CRYPTO WR improves toward 60%+ (conf 0.5-0.6 bucket).  
**Risk**: Low — change is in ranking/display, not in gate logic. Reversible.  
**Effort**: 30 min  

### PR-QW-02: Promote `pead_equity` Shadow → Probation
**Files**: `alpha_engine/production_scanner.py`, `audit_trail/shadow_probation.json`  
**Change**: Add `pead_equity` to equity scanner main loop; set probation_start_date in shadow_probation.json.  
**Expected lift**: First 30 equity picks from a WF-verified strategy (62.2% OOS WR).  
**Risk**: Low — probation means small sizing, monitored.  
**Effort**: 1 hour  

### PR-QW-03: Enable ETF Sector Rotation Emitter
**File**: `tools/etf_sector_emitter.py`, `alpha_engine/config.py` or env  
**Change**: Set `ETF_SECTOR_EMITTER_ENABLED=1` in `.github/workflows/alpha-engine-etf.yml` env block.  
**Expected lift**: ETF picks from proven rotation system (backtest PF 2.05-3.22).  
**Risk**: Low — emitter already coded, just needs env switch.  
**Effort**: 15 min  

### PR-QW-04: Fix `summary_picks.json` Fixture Bug
**File**: `audit_trail/dashboard_generator.py` (summary_picks writer)  
**Change**: Replace static timestamp with `SELECT MAX(created_at) as last_pick_at FROM trading_picks WHERE category=%s GROUP BY category`.  
**Expected lift**: Removes P1 incident from dashboard; correct timestamps visible.  
**Risk**: None — pure data fix.  
**Effort**: 30 min  

### PR-QW-05: Add `signal_time` to Smart Picks Feed
**File**: `audit_trail/dashboard_generator.py` (smart_picks_feed builder)  
**Change**: One-line add: `"signal_time": pick.get("created_at", "")` in the smart_picks_feed dict construction.  
**Expected lift**: Resolves P1 "all picks show 1.4h ago" display bug.  
**Risk**: None.  
**Effort**: 15 min  

### PR-QW-06: Wire `VIX<22` Hard Gate for EQUITY Momentum
**Files**: `audit_trail/quality_gates.py` (`passes_active_gate`), `audit_trail/vix_regime_gate.py`  
**Change**: In `passes_active_gate`, for EQUITY momentum strategies: `if vix_regime_gate.get_vix() > 22: return False, "vix_block"`.  
**Expected lift**: Removes ~30% of failing EQUITY picks; lifts WR toward backtest 75%.  
**Risk**: Medium — may reduce emission volume short-term. Monitor for 14d.  
**Effort**: 2 hours  

### PR-QW-07: Clamp 5 Extreme FOREX pnl_pct Rows
**File**: SQL migration (run once)  
```sql
UPDATE trading_picks 
SET pnl_pct = -100 
WHERE pnl_pct < -100 AND category = 'FOREX';
```
**Expected lift**: Removes P0 distortion (one -106,700% row makes FOREX avg look catastrophic). FOREX avg_loss reverts to realistic ~-0.8%.  
**Risk**: Data fix, recoverable (keep audit trail).  
**Effort**: 5 min  

### PR-QW-08: Block ALL PENNY/MEME from Production EQUITY Path
**File**: `alpha_engine/config.py` (EQUITY_SYMBOLS), `alpha_engine/scanner.py`  
**Change**: Move 8 speculative names (NIO/LCID/RIVN/SNDL/GME/AMC/PLTR spec tier/SOFI) to `EQUITY_RESEARCH_ONLY` dict. Production `scanner.py` EQUITY routing only reads `EQUITY_SYMBOLS_PRODUCTION` (20-30 LC names).  
**Expected lift**: EQUITY PF likely improves 0.1-0.3 as penny/meme drag removed (PENNY_STOCK WR 6.76% PF 0.19).  
**Risk**: Reduces EQUITY pick volume 30-40%. Monitor 14d.  
**Effort**: 1 hour  

### PR-QW-09: Add FOREX LONG Direction Hard Block
**File**: `audit_trail/quality_gates.py` (BLOCKED_DIRECTION_TRIPLES or new `FOREX_DIRECTION_GATE`)  
**Change**: Add env-gated block: `if category == "FOREX" and direction == "LONG" and os.getenv("FOREX_LONG_BLOCK", "0") == "1": return False`. Set `FOREX_LONG_BLOCK=1` in GH Actions env.  
**Expected lift**: FOREX volume drops to SHORT-only. FOREX SHORT PF 8.11 vs LONG 0.80.  
**Risk**: Low — LONG block, not class kill. Reversible.  
**Effort**: 1 hour  

### PR-QW-10: Label IPO Tab Honestly OR Build MVP Scanner
**File**: `audit_dashboard/template.html`  
**Change (Option A — fast)**: Add `(n=0 — scanner in development)` caveat to IPO tab heading and disable the class from asset_class_health display.  
**Change (Option B — build)**: `alpha_engine/ipo_scanner.py` — query EDGAR 8-K for recent IPO registrations (S-1 + 424B4 filings), filter for revenue>0 + lockup expiry within 30d, emit PEAD-adapted picks.  
**Effort**: 15 min (Option A) / 3 hours (Option B)  

---

## Top-Notch Strategy Per Asset Class (Recommended Architecture)

### CRYPTO — Liquid-25 On-Chain + Funding Carry
```
Universe:  BTC/ETH/SOL + top 22 by ADV>$10M (binance top-30 vol tier)
           Remove all 9 meme symbols + illiquid alts (<$5M ADV)
Strategy:  1. On-chain MVRV-Z (Glassnode, enable CRYPTO_ONCHAIN_MOMENTUM_ENABLED=1)
           2. Funding rate carry (Binance free API, positive funding = trend confirms)
           3. BTC UTC 08-09Z death-zone reject (M-001)
Sources:   ONLY: mega_mutation + dna_winner_picks + kimi_riseoftheclaw + baby_strats_forward
Gate:      confidence INVERTED (target 0.5-0.65), ADV>$10M, trust_score>=0.6
Target:    PF>1.5 / WR>50% (T2)
```

### EQUITY — VIX-Regime Momentum on Large-Cap Core  
```
Universe:  30 liquid LC: AAPL/MSFT/NVDA/TSLA/AMZN/GOOGL/META/AMD/AVGO/ORCL/
           JPM/GS/UNH/LLY/WMT/COST/XOM/PG/PEP + 11 more by ADV>$5M
           QUARANTINE: GME/AMC/NIO/LCID/RIVN/SNDL to RESEARCH_ONLY
Strategy:  1. 12-1 momentum top-5 (Jegadeesh-Titman)
           2. PEAD on earnings beats (promote pead_equity NOW)
           3. ConnorsRSI2 on SPY/QQQ
Gate:      VIX<22 hard block + SPY>200SMA + factor score (PE/ROE/momentum)
Target:    PF>2.5 / WR>60% (T2+ based on backtest evidence)
```

### ETF — SPDR Sector Rotation + VIX Regime  
```
Universe:  11 SPDR sectors (XLK/XLE/XLF/XLV/XLI/XLY/XLP/XLU/XLB/XLRE/XLC) + IWM
Strategy:  Faber TAA 10mo SMA + Antonacci 12-1 momentum top-3 long-only
           Monthly rebalance; skip month when VIX>25
Gate:      VIX<25 regime gate (skip, don't invert), friction model 2.5bp
Enable:    ETF_SECTOR_EMITTER_ENABLED=1 (QUICK WIN PR-QW-03)
Target:    PF 2.05-3.22 (proven backtest; Tier-1 with VIX gate)
```

### COMMODITY — Diversified COT on 10-Symbol Core  
```
Universe:  CT=F + GC=F + KC=F + SB=F + ZC=F + ZS=F + HG=F + NG=F + SI=F + CC=F
           Cap: max 25% PnL concentration on any single symbol
Strategy:  CFTC COT commercial net extreme (weekly release, 3d lag enforced)
           ONE SIGNAL PER WEEKLY CYCLE (dedup ledger cot_emitted_releases.json)
           Seasonal overlay: grain harvest / energy winter draw
Gate:      DSR>=0.85 + COT MATCH + dedup ledger (no re-fire same week)
Target:    PF>1.5 / WR>50% on n>=20 clean post-dedup cycles (realistic)
```

### FOREX — SHORT-Only Majors (Paper Phase Only)
```
Universe:  EURUSD + GBPUSD + AUDUSD + USDJPY (4 majors only; block all 16 others)
Strategy:  SHORT direction only (PF 8.11) via ig_contrarian + MeanReversionBB + cta_fx
           Carry: positive carry SHORT confirmation (USDJPY +4.5 carry → SHORT aligns)
Gate:      FOREX_LONG_BLOCK=1 env; DXY regime awareness (add)
Timeline:  30d paper on SHORT-only → if PF>1.3 / WR>50 / n>30, remove HARD_DISABLE
Target:    PF>1.3 (paper phase); abandon class if not met by day 60
```

### BOND — Research/OPT-IN Only  
```
Universe:  TLT + IEF + LQD + HYG + TIP (5 names)
Strategy:  TIPS vs nominal MR (Fleckenstein-Longstaff) + HYG-LQD credit spread MR
           MOVE index vol gate (skip when MOVE>130)
Gate:      sizing_allowed=False; n<50 insufficient; no production emissions
Timeline:  Revisit in 90 days when n>=50 clean picks from new strategies
Target:    Track only — no T2 claim until n>=100
```

### FUTURES — Merge into COMMODITY or Deprecate  
```
Action:    Remove standalone FUTURES tile from /audit (shows n=0, misleading)
           Reclassify ES=F/NQ=F as "EQUITY_FUTURES" under EQUITY tile
           Reclassify ZN=F/ZB=F under BOND tile
           Keep GC=F/SI=F/HG=F under COMMODITY
New tile:  Optional: "Financial Futures" tile once ES overnight drift strategy (n>=30) validates
Target:    Avoid zombie tile — either build real edge or remove from UI
```

### PENNY/MEME — Full Quarantine  
```
Universe:  MOVE TO RESEARCH_ONLY config (no production emissions)
Strategy:  None for production. Research-only: extreme vol mean-reversion hypothesis
           (0.5% micro-size, 1d hold, ADV>$5M, paper only, 6m test)
Gate:      BLOCKED_SOURCE_SYSTEMS entries for all penny/meme emitters
           ADV gate: ADV>$5M required for any equity production pick
Target:    Remove from live metrics entirely; stop polluting EQUITY/CRYPTO aggregates
```

### IPO — Build or Remove Advertising  
```
Quick (15 min): Add "scanner in development" caveat to /audit IPO tab
Build (3h): alpha_engine/ipo_scanner.py — EDGAR S-1 + lockup expiry + PEAD
Strategy:  IPO day-5 through day-30 momentum (post-stabilization)
           Lock-up expiry fade (insider selling = bearish signal 6m post-IPO)
           Revenue trajectory + gross margin filter
Gate:      Only emit if revenue growing >20% YoY + gross margin >30%
Target:    n>=30 clean picks before any sizing claim
```

---

## PR Priority Stack (Execute in Order)

| # | PR | Files | Effort | Impact |
|---|---|---|---|---|
| 1 | QW-07: Clamp FOREX extreme pnl | SQL | 5 min | Fixes P0 metric distortion |
| 2 | QW-05: signal_time one-liner | dashboard_generator.py | 15 min | Fixes P1 display |
| 3 | QW-03: ETF emitter enabled | alpha-engine-etf.yml | 15 min | Unlocks PF 2+ ETF edge |
| 4 | QW-09: FOREX LONG block | quality_gates.py | 1 hr | Removes -EV direction |
| 5 | QW-01: Invert confidence | smart_picks_engine.py | 30 min | Fixes inverted ranker |
| 6 | QW-08: Quarantine penny/meme | config.py + scanner.py | 1 hr | Cleans EQUITY/CRYPTO |
| 7 | QW-02: Promote pead_equity | production_scanner.py | 1 hr | Deploys 62% WR strategy |
| 8 | QW-04: Fix summary_picks.json | dashboard_generator.py | 30 min | Fixes P1 fixture bug |
| 9 | QW-06: VIX<22 EQUITY gate | quality_gates.py | 2 hrs | Lifts EQUITY WR toward 75% |
| 10 | QW-10: IPO tab caveat | template.html | 15 min | Removes false advertising |

**Total estimated effort: ~7 hours for all 10 PRs**

---

## Dedup-MD-Review Skill Created

The `/dedup-md-review` skill has been created at `.claude/skills/dedup-md-review/SKILL.md`.

**Usage**: When given 90+ file paths with worktree duplicates, the skill:
1. Normalizes all paths (Windows `E:\` → Linux `/`)
2. Groups by **basename** 
3. Picks **shortest path** (root copy over worktree copy)
4. Returns 9 unique canonical paths instead of 90

**Result for this session**:
- 90 input paths → **9 unique canonical files** (all under `reports/`)
- 81 worktree copies skipped (`.claude/worktrees/agent-*/`)
- Reading: `reports/90day_gap_analysis_2026-05-15.md` + 8 per-class plans

---

*Generated by Claude Sonnet 4.6 via GitHub Copilot — 2026-05-27 EST*  
*Source review: 9 canonical 90day plan reports + live incidents dashboard + DAILY_IDEAS.MD*
