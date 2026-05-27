# EAGLE Quick Wins — Strategy Review 2026-05-27
**Model**: Claude Sonnet 4.6 (GitHub Copilot)  
**Date/Time**: 2026-05-27 EST (v2 enhanced — post-fix delta as of ~14:50 EST)  
**Scope**: End-to-end review of all asset classes + safety gates + quick-executable PRs  
**Canonical source files reviewed** (9 unique, 90+ paths deduplicated via `/dedup-md-review` skill):
- `reports/90day_gap_analysis_2026-05-15.md`
- `reports/asset_class_90day_plan_{BOND,COMMODITY,CRYPTO,EQUITY,ETF,FOREX,FUTURES,PENNY_MEME}_2026-05-15.md`

---

## ✅ RESOLVED SINCE V1 (commits confirmed)

| Item | Commit | What Was Done |
|---|---|---|
| QW-01 (CRYPTO conf inversion — ranker) | `919b962f9` | Confidence zeroed in `_compute_ml_composite`; `CONFIDENCE_INVERT_CRYPTO=1` added to `smart-picks-tracker.yml` |
| QW-05 (signal_time) | `b8b2cd29b` | `signal_time` populated from pick's actual timestamp |
| QW-06 (VIX<22 EQUITY gate) | `884a1a014` | Hard gate wired and live in `passes_active_gate` |
| QW-08 (EQUITY speculative quarantine) | `884a1a014` | GME/AMC/NIO speculative EQUITY names blocked |
| WON/PnL coherence step | `884a1a014` | Coherence validation added to resolver |
| summary_picks sync | `884a1a014` | `summary_picks` refresh added |
| signal_outcomes + Swarm Picks refresh | `e3ed33ef3` | `signal_outcomes` mirror refreshed; Swarm Picks revived with tournament promotion |

## ⚠️ HALF-DONE — Coded but env flag NOT in `alpha-engine-live.yml`

| Code Path | Where Code Exists | Gap |
|---|---|---|
| `CONFIDENCE_INVERT_CRYPTO=1` | `smart-picks-tracker.yml:32` ONLY | Missing from `alpha-engine-live.yml` → production emission still uses broken confidence |
| `PEAD_EQUITY_ENABLED=1` | `production_scanner.py:3970` | Not set in any GHA → zero PEAD emissions |
| `WIN_RATE_TRAP_GATE_ENABLED=1` | `quality_gates.py:6612-6616` (default-off, `9618bc8d7`) | Not set in any GHA → gate is dead code |
| ETF spike → MySQL | `alpha_engine/data/active_picks_etf.json` (17 picks, `etf_emitter_spike_v1`) | Picks are in JSON only; never INSERTed to `trading_picks` |

---

## TL;DR — What's Still Broken, What's the Fast Fix (v2)

| Issue | Status | Fast Fix |
|---|---|---|
| ML confidence inverted: conf≥0.9 → WR 14% | ⚠️ HALF-FIXED — ranker fixed, but `CONFIDENCE_INVERT_CRYPTO=1` missing from `alpha-engine-live.yml` | Add to GHA env (NEW-QW-01, **5 min**) |
| forward_validator frozen 270h+ / 29M open positions | ❌ STILL OPEN | Restart validator + EXPIRED-stamp stale backlog |
| ETF emitter fires 0 MySQL picks despite PF 2.05-3.22 backtest | ❌ NEW — `etf_emitter_spike_v1` writes JSON only, not MySQL | Wire JSON picks to MySQL INSERT (NEW-QW-03, **30 min**) |
| PEAD equity 62.2% WR stuck in shadow | ⚠️ HALF-DONE — code ready, no GHA env var | Add `PEAD_EQUITY_ENABLED: "1"` to GHA (NEW-QW-02, **5 min**) |
| WIN_RATE_TRAP_BLACKLIST dead code | ⚠️ HALF-DONE — gate wired (`9618bc8d7`), env flag not set | Add `WIN_RATE_TRAP_GATE_ENABLED: "1"` to GHA (NEW-QW-04, **5 min**) |
| FOREX LONG direction: PF 0.80 vs SHORT PF 8.11 | ❌ Soft -15 score penalty only; no hard env block | Add `FOREX_LONG_BLOCK: "1"` to GHA (QW-09, **1 hr**) |

---

## Safety Gate Analysis — v2 Status

### 1. VIX Regime Gate (EQUITY) — ✅ LIVE as of `884a1a014`
**Status**: Hard block wired. `VIX>22` picks blocked in `passes_active_gate`.  
**Remaining**: Monitor for 14d to confirm volume drop + WR lift. No action needed now.

### 2. PEAD Equity — ⚠️ CODE READY, ENV FLAG MISSING
**Evidence**: `pead_equity` has **62.2% OOS WR**. Code guard at `production_scanner.py:3970`.  
**What blocks it**: `PEAD_EQUITY_ENABLED` not set in `alpha-engine-live.yml`. Picks are silently skipped.  
**Fix**: `NEW-QW-02` — add `PEAD_EQUITY_ENABLED: "1"` to `alpha-engine-live.yml` env block. **5 minutes.**

### 3. SHORT FOREX Direction Bias — ⚠️ SOFT PENALTY ONLY
**Evidence**: FOREX mutation autopsy: 80% LONG volume at 29.4% WR / PF 0.80. SHORT side: PF **8.11** on n=29.  
**Current state**: Soft `-15` score penalty in `quality_gates.py:4153-4156` but no hard block env flag.  
**Fix**: `QW-09` — add `FOREX_LONG_BLOCK: "1"` env gate. **1 hour.**

### 4. Confidence Inversion — ⚠️ PARTIALLY FIXED
**Status**: `919b962f9` fixed confidence in `_compute_ml_composite` and `smart-picks-tracker.yml`.  
**Remaining gap**: `CONFIDENCE_INVERT_CRYPTO=1` is NOT in `alpha-engine-live.yml` — production emission still uses broken confidence during pick scoring.  
**Fix**: `NEW-QW-01` — add to `alpha-engine-live.yml`. **5 minutes.**

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

## Quick Win PRs — v2 Status

### ✅ RESOLVED PRs

| PR | Commit | Status |
|---|---|---|
| QW-01 (confidence inversion — ranker/tracker) | `919b962f9` | Done in smart-picks-tracker. See NEW-QW-01 for production GHA gap. |
| QW-05 (signal_time) | `b8b2cd29b` | Done |
| QW-06 (VIX<22 EQUITY gate) | `884a1a014` | Live |
| QW-08 (EQUITY speculative quarantine) | `884a1a014` | GME/AMC/NIO blocked |

---

### 🔴 NEW-QW-01: Add `CONFIDENCE_INVERT_CRYPTO: "1"` to `alpha-engine-live.yml`
**File**: `.github/workflows/alpha-engine-live.yml` — add to `env:` block  
**Why**: `919b962f9` fixed the smart-picks-tracker only. The production alpha engine workflow (`alpha-engine-live.yml`) runs WITHOUT this env var — CRYPTO live pick emission still uses inverted confidence.  
**Expected lift**: CRYPTO Smart Picks WR improves toward 60%+ (conf 0.5-0.6 is the winning bucket).  
**Effort**: **5 min**

### 🔴 NEW-QW-02: Add `PEAD_EQUITY_ENABLED: "1"` to `alpha-engine-live.yml`
**File**: `.github/workflows/alpha-engine-live.yml` — add to `env:` block  
**Code ready at**: `production_scanner.py:3970` — `if os.getenv("PEAD_EQUITY_ENABLED") == "1":`  
**Expected lift**: First 30+ EQUITY picks from a WF-verified strategy (62.2% OOS WR).  
**Effort**: **5 min**

### 🔴 NEW-QW-03: Wire ETF Spike Picks to MySQL
**Files**: `alpha_engine/etf_sector_emitter.py`, `alpha_engine/data/active_picks_etf.json`  
**Change**: After JSON write, INSERT each pick to `trading_picks` with `category='ETF'`. Dedup on `(symbol, source_system, signal_timestamp)`.  
**Evidence**: 17 picks exist in `active_picks_etf.json` (version `etf_emitter_spike_v1`) but audit dashboard shows zero ETF picks.  
**Expected lift**: ETF picks appear on dashboard; proven backtest edge (PF 2.05-3.22) becomes trackable.  
**Effort**: **30 min**

### 🔴 NEW-QW-04: Add `WIN_RATE_TRAP_GATE_ENABLED: "1"` to `alpha-engine-live.yml`
**File**: `.github/workflows/alpha-engine-live.yml` — add to `env:` block  
**Code ready at**: `quality_gates.py:6612-6616` — gate wired but defaults OFF (commit `9618bc8d7`).  
**Expected lift**: Eliminates "win rate trap" symbol/source pairs. Estimated +2-5 PF on affected pairs.  
**Effort**: **5 min**

---

### PR-QW-07: Clamp 5 Extreme FOREX pnl_pct Rows — ❌ STILL OPEN — ❌ STILL OPEN
**File**: SQL migration (run once)  
```sql
UPDATE trading_picks 
SET pnl_pct = -100 
WHERE pnl_pct < -100 AND category = 'FOREX';
```
**Expected lift**: Removes P0 distortion (one -106,700% row makes FOREX avg look catastrophic). FOREX avg_loss reverts to realistic ~-0.8%.  
**Effort**: **5 min**

### PR-QW-08: Block ALL PENNY/MEME from Production EQUITY Path — ✅ DONE (`884a1a014`)
GME/AMC/NIO speculative names blocked. Monitor for additional names (LCID/RIVN/SNDL) if they appear.

### PR-QW-09: Add FOREX LONG Direction Hard Block — ❌ STILL OPEN (soft penalty only)
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
           QUARANTINE: GME/AMC/NIO/LCID/RIVN/SNDL — ✅ DONE (884a1a014)
Strategy:  1. 12-1 momentum top-5 (Jegadeesh-Titman)
           2. PEAD on earnings beats — ⚠️ enable PEAD_EQUITY_ENABLED=1 (NEW-QW-02, 5 min)
           3. ConnorsRSI2 on SPY/QQQ
Gate:      VIX<22 hard block ✅ LIVE (884a1a014) + SPY>200SMA + factor score
Target:    PF>2.5 / WR>60% (T2+ based on backtest evidence)
```

### ETF — SPDR Sector Rotation + VIX Regime  
```
Universe:  11 SPDR sectors (XLK/XLE/XLF/XLV/XLI/XLY/XLP/XLU/XLB/XLRE/XLC) + IWM
Strategy:  Faber TAA 10mo SMA + Antonacci 12-1 momentum top-3 long-only
           Monthly rebalance; skip month when VIX>25
Gate:      VIX<25 regime gate (skip, don't invert), friction model 2.5bp
Status:    etf_emitter_spike_v1 running — 17 picks in JSON but NOT in MySQL (NEW-QW-03)
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
Gate:      FOREX_LONG_BLOCK soft -15 penalty active (❌ hard block still needed — QW-09)
           DXY regime awareness (❌ not yet built — REMAINING-P2-05)
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

## PR Priority Stack (v2 — Execute in Order)

| # | PR | Files | Effort | Status |
|---|---|---|---|---|
| 1 | NEW-QW-01: `CONFIDENCE_INVERT_CRYPTO: "1"` in `alpha-engine-live.yml` | GHA workflow | **5 min** | ❌ OPEN |
| 2 | NEW-QW-02: `PEAD_EQUITY_ENABLED: "1"` in `alpha-engine-live.yml` | GHA workflow | **5 min** | ❌ OPEN |
| 3 | NEW-QW-04: `WIN_RATE_TRAP_GATE_ENABLED: "1"` in `alpha-engine-live.yml` | GHA workflow | **5 min** | ❌ OPEN |
| 4 | QW-07: Clamp FOREX extreme `pnl_pct < -100` | SQL one-shot | **5 min** | ❌ OPEN |
| 5 | NEW-QW-03: Wire ETF spike picks to MySQL | `etf_sector_emitter.py` | **30 min** | ❌ OPEN |
| 6 | QW-09: FOREX LONG hard block env gate | `quality_gates.py` + GHA | **1 hr** | ⚠️ Soft only |
| 7 | QW-10: Label IPO tab honestly | `template.html` | **15 min** | ❌ OPEN |
| 8 | QW-04: Fix `summary_picks.json` timestamp | `dashboard_generator.py` | **30 min** | ⚠️ Verify |

**Items 1-4 are all 5-min env-var additions or a SQL one-liner. Total ~20 min for the highest-impact fixes.**

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
*v1: 2026-05-27 ~07:00 EST | v2 enhanced: 2026-05-27 ~14:50 EST*  
*Source review: 9 canonical 90day plan reports + live incidents dashboard + DAILY_IDEAS.MD + git log since v1*
