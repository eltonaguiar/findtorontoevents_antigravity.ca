# FINDING-19: 3-AI Consensus Report — multi_asset_copytrader × metals block

**Date:** 2026-05-19  
**Finding:** FINDING-19 from `reports/HOURLY_AUDIT_15Z.md`  
**Consensus:** 3/3 OPTION B (targeted symbol block)

---

## Evidence

| Window | n | PF | WR | sum PnL% |
|--------|---|----|----|----------|
| 7d | 22 | 0.177 | 9.1% | −62.172% |
| 30d | 56 | 1.633 | 53.6% | +57.518% |

Kill criteria met (7d): PF<0.5 ✅ | n≥20 ✅ | WR<35% ✅  
30d attribution: healthy. CT=F long-run WR=56.1% (n=180) — positive anchor.  
Metals cluster: PL=F, GC=F, HG=F all at 0% WR in 7d.

---

## AI Verdicts

### Engine 1: DeepSeek (deepseek-v4-flash)
```
VERDICT: B
REASONING: The 7d collapse is concentrated in a metals cluster (PL=F, GC=F, HG=F) with 0% win rates,
while the 30d attribution remains healthy (PF=1.633, WR=53.6%) and CT=F shows sustained positive
performance. A targeted symbol block removes the three failing symbols, preserving the strategy's
overall edge while mitigating the acute regime-specific drag.
KEY_RISK: Metals may reverse sharply in the next 3 weeks, causing us to miss profitable trades.
PAIRS_TO_BLOCK: multi_asset_copytrader:PL=F, multi_asset_copytrader:GC=F, multi_asset_copytrader:HG=F
```

### Engine 2: Kilo
```
VERDICT: B
REASONING: The 7-day collapse in the metals cluster is severe, with 0% win rate and PF=0.177,
meeting kill criteria. The 30-day performance remains healthy (PF=1.633, WR=53.6%), and CT=F
continues to show strong long-run attribution. A targeted block preserves the strategy's edge in
non-metals while eliminating the current regime-specific drag.
KEY_RISK: If the blocked metals reverse and enter a new winning regime within 30 days, the strategy
will miss the recovery.
PAIRS_TO_BLOCK: ("multi_asset_copytrader", "PL=F"), ("multi_asset_copytrader", "GC=F"),
("multi_asset_copytrader", "HG=F")
```

### Engine 3: Claude (claude-sonnet-4-6)
```
VERDICT: B — Targeted symbol block (metals cluster only)
REASONING: The 7d data meets all three formal kill criteria simultaneously (PF=0.177 < 0.5,
n=22 ≥ 20, WR=9.1% < 35%), which is not a statistical artifact — it is 22 resolved trades with
zero edge. The collapse is cleanly attributable to the metals cluster (PL=F/GC=F/HG=F all at 0% WR)
rather than strategy-wide failure. Metals at or near all-time highs (GC=F ~$4,511) represent a
structural mismatch between the strategy's signal space and the current market microstructure.
Option C destroys a proven 30d edge (CT=F n=180, WR=56.1%) to solve a problem that is
demonstrably localized to three symbols; that is an asymmetric sacrifice. Option A violates the
kill protocol: all three criteria are met.
KEY_RISK: If the metals bull run stalls and reverts sharply within 3-4 weeks, we miss the reversal.
Accepted cost given PF=0.177 burn rate (~2.8% PnL lost per trade).
PAIRS_TO_BLOCK: ("multi_asset_copytrader", "PL=F"), ("multi_asset_copytrader", "GC=F"),
("multi_asset_copytrader", "HG=F")
REVIEW_DATE: 2026-06-09 (3 weeks)
```

---

## Consensus: 3/3 Option B

**Action taken:** Added to `BLOCKED_STRATEGY_SYMBOL_PAIRS` in `audit_trail/quality_gates.py`:
- (`multi_asset_copytrader`, `PL=F`)
- (`multi_asset_copytrader`, `GC=F`)
- (`multi_asset_copytrader`, `HG=F`)

**Review date:** 2026-06-09 — unblock if metals regime softens AND 14d WR returns to ≥35%.

**CT=F preserved:** strategy remains active for Cotton and all non-metals symbols.

---

## Swarm run directories
- DeepSeek: `swarm_runs/run_20260519T204229Z/`
- Kilo: `swarm_runs/run_20260519T204255Z/`
- Claude: `swarm_runs/run_20260519T204334Z/`
