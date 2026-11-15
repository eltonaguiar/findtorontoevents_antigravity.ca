# Algorithm Specification — COMMODITY / FUTURES

**Asset Class:** COMMODITY / FUTURES
**Status:** RESEARCH SLOT 1 — NOT MONEY-READY (COMMODITY copy-trader/COT is strongest proven edge)
**sizing_allowed:** false

---

## 1. Algorithm Specification

### Strategies Tested / Identified

| Strategy | Class | n | WR | Status | Source |
|----------|-------|---|-----|--------|--------|
| multi_asset_copytrader | COMMODITY | 96 | 93.8% | **REAL EDGE** | closed_picks.json per-class audit |
| multi_asset_cot | COMMODITY | 102 | 94.1% | **REAL EDGE** | DB-verify pending |
| multi_asset_copytrader | FOREX | 662 | 14.8% | Massive drain — BLOCK | closed_picks.json per-class audit |
| multi_asset_copytrader | FUTURES | 157 | 2.5% | Critical drain — BLOCK | closed_picks.json per-class audit |
| CTA trend following | COMMODITY | n/a | n/a | Historical PF 1.78 | Legacy data |

### Cost Model
- Commodity copy-trader/COT: costs not fully modeled in per-class audit — needs verification
- Futures: roll yield, contango/backwardation, commission, slippage, contract identity

### Benchmark
- COMMODITY: matched-exposure commodity benchmark needed
- Must beat on risk-adjusted basis, not just raw return

### Walk-Forward Design
- Not yet implemented for COMMODITY copy-trader/COT — needs pre-registered walk-forward

---

## 2. Backtest Results (Per-Class CopyTrader Audit)

**Source:** `reports/multi_asset_copytrader_per_class_audit_20260513T014000Z.md`

| Class | n | WR % | Volume Share | Status | Action |
|-------|---|------|-------------|--------|--------|
| **COMMODITY** | 96 | **93.8%** | 6.4% | ✅ Real edge — pristine WR | **PRESERVE + SCALE** |
| EQUITY | 28 | 42.9% | 1.9% | ⚠️ Thin (n<100) | Monitor |
| **FOREX** | 662 | **14.8%** | 44.0% | ❌ Massive drag | **MUTATE-BEFORE-KILL** |
| **FUTURES** | 157 | **2.5%** | 10.4% | ❌ Critical drain | **SURGICAL BLOCK** |

### Aggregate Masking Problem

Dashboard reports `multi_asset_copytrader` PF=4.28 / WR=47.3% / n=1505 / MDD=16.67%.

This aggregate is **misleading**. The COMMODITY 93.8% WR tail wins mask the FOREX/FUTURES drain. The system's true edge is COMMODITY-only.

### Peer Claim FALSIFIED

Peer Big Pickle claimed: "multi_asset_copytrader is your most robust system — PF 4.09, n=812, MDD 16.67%, spans 5 classes. Best candidate for go-live TODAY."

**Falsified on multiple counts:**
1. Spans 3-4 classes, not 5
2. NOT go-live ready — 44% of resolved volume is FOREX at 14.8% WR
3. True edge is COMMODITY-only, same as `multi_asset_cot` finding

### Recommended Actions

| ID | Action | Priority |
|----|--------|----------|
| Block `(FUTURES, multi_asset_copytrader)` | P0 — n=157, WR=2.5% is empirically dead |
| Mutate-before-kill `(FOREX, multi_asset_copytrader)` | P1 — 662 picks at 14.8% WR needs axis analysis |
| Preserve `(COMMODITY, multi_asset_copytrader)` | P0 — 96 picks at 93.8% WR is the legitimate edge |

---

## 3. Pick Justification

**COMMODITY copy-trader/COT pick is justified for further research (not yet deployment).**

**Reasoning:**
1. **WR=93.8% (n=96)** — pristine win rate, statistically meaningful sample
2. **WR=94.1% (n=102)** — multi_asset_cot confirms the edge independently
3. **Cross-system confirmation** — two independent systems (copy-trader + COT) agree on COMMODITY edge
4. **Class-specific** — edge does NOT extend to FOREX (14.8%) or FUTURES (2.5%)

**NOT yet deployable because:**
- DB verification pending (next session action)
- No pre-registered walk-forward with DSR/PBO gates
- No cost model verification (commission, slippage, roll costs)
- No forward testing (n=0 forward closes)

**Best (least bad) non-commodity alternative:** None — all other copy-trader classes fail badly.

---

## 4. Elimination Reason

- **FUTURES copy-trader:** Eliminated — WR=2.5%, n=157, critical drain. Surgical block.
- **FOREX copy-trader:** Mutate-before-kill — WR=14.8%, n=662, massive drag. Needs axis analysis before kill decision.
- **All other commodity strategies:** Not yet tested — acquire real feed + contract identity first.

---

## 5. Money-Ready Gate Result

**Not yet evaluated** — COMMODITY copy-trader/COT has not been run through the full 7-gate money-ready framework (PF≥1.15, WR≥50%, Sharpe≥1.0, DSR≥0.95, PBO≤0.10, MaxDD<15%, Trades≥50).

**Next step:** Run full gate evaluation on COMMODITY copy-trader/COT with proper cost model and walk-forward.
