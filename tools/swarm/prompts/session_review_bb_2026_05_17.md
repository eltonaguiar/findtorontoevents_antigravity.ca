# Session BB — Swarm Review Request
# Date: 2026-05-17
# Session: BB (following BA — APPROVE)

## Context

Session BB: COMMODITY strategy autopsy revealing critical non-CT=F drag.
All session reviews through BA have returned deepseek APPROVE.

## Session BB Deliverables

### 1. COMMODITY Non-CT=F Strategy Autopsy (new finding)

Three-axis autopsy on COMMODITY closed_picks.json revealed dramatic per-symbol
performance divergence in `cta_replicator`, `multi_asset_copytrader`, and `multi_asset_cot`:

**CT=F (Cotton Futures) — edge confirmed:**
```
multi_asset_copytrader CT=F:  n=116  WR=84%  avg_pnl=+3.63%
multi_asset_cot CT=F:         n=114  WR=87%  avg_pnl=+3.80%
```

**Non-CT=F — no edge:**
```
cta_replicator CL=F (Oil):    n=47   WR=19%  avg_pnl=-1.47%
cta_replicator NG=F (Gas):    n=24   WR=0%   avg_pnl=-3.00%
cta_replicator ZC=F (Corn):   n=8    WR=0%   avg_pnl=-3.78%
multi_asset_cot non-CT=F:     n=17   WR=29%  avg_pnl=-1.51%
multi_asset_copytrader non-CT=F: n=15 WR=0%  avg_pnl=-2.62%
combined_confidence non-CT=F: n=6    WR=0%   avg_pnl=-3.34%
```

**Aggregate impact of blocking these 3 for non-CT=F:**
```
Current (all COMMODITY):       n=354  WR=60.2%  PF=2.28
If blocked for non-CT=F:       n=239  WR=82.8%  PF=6.67
CT=F only (ground truth):      n=231  WR=85.7%  PF=7.84
Non-CT=F only (the drag):      n=123  WR=12.2%  PF=0.23
```

**Key implication:** The previous COMMODITY recommendation was "raise concentration cap
(COMMODITY 0.60→0.85) to unblock MONEY_READY." But:
- With cap raise only: COMMODITY = WR=60.2%, PF=2.28 (Tier 2, with 35% losing picks)
- With non-CT=F blocks + cap raise: COMMODITY = WR=82.8%, PF=6.67 (Tier 1 Renaissance)

The cap raise alone declares MONEY_READY on a significantly degraded edge.

### 2. Report written

`reports/commodity_nonctf_strategy_autopsy_2026_05_17.md` — full analysis with
per-symbol breakdown, escalation ladder compliance, and action options.

### 3. Complication: cta_replicator can be fully blocked (safe)

`cta_replicator` has ZERO CT=F resolved picks — all its COMMODITY picks are non-CT=F.
A full `('COMMODITY', 'cta_replicator')` block removes 83 losing picks with zero upside loss.

`multi_asset_copytrader` and `multi_asset_cot` have both CT=F winners AND non-CT=F losers.
A full class block would kill CT=F winners too — needs per-symbol logic (which doesn't exist yet).

**Simpler path (minimum user-approved changes):**
1. Block `('COMMODITY', 'cta_replicator')` fully — 83 losing picks removed, 0 CT=F picks lost
2. Add per-symbol block infrastructure for `multi_asset_copytrader`/`multi_asset_cot` on non-CT=F
3. Raise concentration cap (still needed even after non-CT=F blocks because CT=F share → 97%)

### 4. Current verdict remains unchanged (requires user approval)

```
CRYPTO       MONEY_READY   n=443  PF=2.54  WR=66.4%  ✅
COMMODITY    WATCH         n=354  PF=2.28  WR=60.2%  ← CT=F 65.3% > 60% cap + non-CT=F drag
EQUITY       WATCH         n=238  PF=2.04  WR=54.2%  ← accumulation needed
ETF          WATCH         n=74   PF=2.49  WR=67.6%  ← accumulation needed
FOREX        NOT_READY     n=618  PF=0.48  WR=33.3%  ← hard-blocked
```

## Questions for Swarm

1. **cta_replicator COMMODITY block:** Given cta_replicator has 0 CT=F resolved picks and
   83 non-CT=F picks at WR=12% avg_pnl=-2.11%, does this meet the STRATEGY_INVESTIGATION_
   BEFORE_KILL.md threshold for blocking without mutation attempt? The strategy loses on
   every energy/grain commodity (CL=F WR=19%, NG=F WR=0%, ZC=F WR=0%, ZS=F WR=0%).

2. **cap raise vs block sequencing:** Should the user be asked to approve:
   (a) Block `('COMMODITY', 'cta_replicator')` first, then evaluate
   (b) Cap raise 0.60→0.85 first, then block
   (c) Both simultaneously (2 user approvals in one request)
   Which sequencing makes the clearest decision for the user?

3. **Prior recommendation correction:** The previous sessions (AX through BA) framed
   the concentration cap raise as the only path. Now the autopsy shows the cap raise
   alone declares MONEY_READY on WR=60.2%/PF=2.28 (35% losing picks). Should the
   recommendation be updated from "cap raise alone" to "block cta_replicator + cap raise"?

4. **Overall verdict:** Is Session BB APPROVE?

## Verification

- autopsy report: `reports/commodity_nonctf_strategy_autopsy_2026_05_17.md`
- data source: `alpha_engine/data/closed_picks.json` (n=354 COMMODITY resolved)
- CI: clean (0 stale failures)
- Prior verdicts: AR through BA all deepseek APPROVE
