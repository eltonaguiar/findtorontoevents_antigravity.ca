You are a senior quant risk analyst at a commodity trading hedge fund. Evaluate the following 3-AI consensus request and provide a clear verdict.

## FINDING-19: multi_asset_copytrader × COMMODITY — 7d regime collapse

### Context
The `multi_asset_copytrader` strategy in the COMMODITY asset class has collapsed over the last 7 days while the 30-day attribution remains healthy. The question is whether to block at symbol level, block at class level, or monitor only.

### Evidence

**Performance windows:**
| Window | n | PF | WR | sum PnL% |
|--------|---|----|----|----------|
| 7d | 22 | 0.177 | 9.1% | −62.172% |
| 30d | 56 | 1.633 | 53.6% | +57.518% |

**Worst 7d symbols (metals cluster):**
- PL=F (Platinum): 0% WR in 7d
- GC=F (Gold): 0% WR in 7d
- HG=F (Copper): 0% WR in 7d

**Positive anchor:**
- CT=F (Cotton): WR=56.1% long-run (n=180 per mutation analysis), healthy attribution

**Kill criteria (docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md) check:**
- PF < 0.5: YES (0.177)
- n ≥ 20: YES (22)
- WR < 35% sustained: YES (9.1%)

However: 30d PF=1.633 and WR=53.6% are healthy. The system uses BLOCKED_ASSET_STRATEGY_PAIRS for strategy-level kills and BLOCKED_STRATEGY_SYMBOL_PAIRS for targeted symbol blocks. Both require 3-AI consensus before action.

**Market context (2026-05-19):**
- Gold (GC=F) at ~$4,511 — near all-time highs, metals in strong uptrend
- Platinum and copper also elevated
- Cotton (CT=F) stabilizing

### The 3 options

**Option A — Monitor only (no block)**
- 7d collapse is a known metal-specific regime shift (metals in secular bull)
- 30d attribution is healthy; wait for 30d to deteriorate before acting
- Risk: if 7d is forward-looking, another 3 weeks of losses accumulate

**Option B — Targeted symbol block (recommended in hourly audit)**
- Block: (`multi_asset_copytrader`, `PL=F`), (`multi_asset_copytrader`, `GC=F`), (`multi_asset_copytrader`, `HG=F`)
- Preserves CT=F attribution (the positive anchor)
- Preserves 30d edge by removing the 7d metal-cluster drag
- Risk: if metals recover in 3 weeks, we missed the reversal

**Option C — Class-level block (most conservative)**
- Block `multi_asset_copytrader` from COMMODITY entirely
- Eliminates all 7d drag including CT=F upside
- Risk: destroys the 30d edge (PF=1.633) — CT=F is a proven winner

### Your task

1. State your verdict: Option A, B, or C (or a variation).
2. Explain in 3-5 sentences WHY, citing the specific data points.
3. Name the single most important risk of your recommended option.
4. If Option B, specify the exact BLOCKED_STRATEGY_SYMBOL_PAIRS entries to add.

Output format:
```
VERDICT: <A|B|C|Variation>
REASONING: <3-5 sentences>
KEY_RISK: <one sentence>
PAIRS_TO_BLOCK: <list or N/A>
```
