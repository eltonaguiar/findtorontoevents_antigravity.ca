# Mutation Evidence: Direction-Flip Candidates — 2026-05-18

**Analyst:** Claude Code (Session CQ)  
**Protocol:** `docs/MUTATION_THREE_AXIS_PROTOCOL.md`  
**Data Source:** pf_registry.json (32 source files, all policy-excluded strategies removed)  
**Purpose:** Required pre-block evidence document per CLAUDE.md "Strategy demotion" rule.

---

## Executive Summary

Four strategies show severe LONG-direction underperformance with viable SHORT-side or
symbol-restricted alternatives. Recommendations per three-axis mutation protocol:

| Strategy | Verdict | Recommended Action |
|----------|---------|-------------------|
| `ig_contrarian_sentiment LONG` | **Axis 1+2: Block LONG JPY-crosses; let SHORT+non-JPY run** | USER APPROVAL NEEDED |
| `myfxbook_retail_contrarian LONG` | **Axis 1: Block LONG** | USER APPROVAL NEEDED |
| `cta_cross_asset_tsmom COMMODITY` | **Axis 1: Block COMMODITY direction only** | USER APPROVAL NEEDED |
| `forex_carry_momentum LONG` | **Axis 2: Block LONG JPY-crosses (symbol-lock kill)** | USER APPROVAL NEEDED |

---

## 1. ig_contrarian_sentiment

### Performance by Direction
| Direction | n | WON | LOST | WR | PF |
|-----------|---|-----|------|----|----|
| LONG | 197 | 33 | 164 | 16.8% | 0.252 |
| SHORT | 57 | 35 | 22 | **61.4%** | **2.238** |

SHORT is T1-grade (PF 2.238 / WR 61.4%). LONG is catastrophically below floor.

### LONG Symbol Breakdown (Axis 2 evidence)
| Symbol | n | WR | Verdict |
|--------|---|----|---------|
| USDJPY=X | 61 | **0%** | KILL — zero wins |
| EURJPY=X | 60 | **0%** | KILL — zero wins |
| EURGBP=X | 27 | 56% | KEEP — viable |
| USDCAD=X | 20 | 35% | MARGINAL |
| CADJPY=X | 10 | **0%** | KILL — zero wins |
| USDCHF=X | 8 | 100% | SMALL SAMPLE |
| GBPJPY=X | 10 | 20% | MARGINAL |

**Root cause:** IG retail contrarian LONG signal is structurally broken on JPY-crosses.
USDJPY+EURJPY+CADJPY+GBPJPY = 142 picks, ~2 wins. Non-JPY pairs show 35-100% WR.

### Three-Axis Mutation Options
- **Axis 1 (Direction flip):** Block LONG entirely; let SHORT run (WR=61.4%, PF=2.238). This is the cleanest option.
- **Axis 2 (Symbol lock):** If keeping LONG, block JPY-cross symbols. EURGBP/USDCHF non-JPY LONG performance is viable.
- **Axis 3 (TP/SL):** Not applicable — the issue is structural directional bias, not stop calibration.

**Recommended:** Axis 1 + Axis 2 combined. Add to `BLOCKED_ASSET_STRATEGY_PAIRS`:
```python
("FOREX", "ig_contrarian_sentiment", "USDJPY=X"),   # 0/61 = 0% WR
("FOREX", "ig_contrarian_sentiment", "EURJPY=X"),   # 0/60 = 0% WR
("FOREX", "ig_contrarian_sentiment", "CADJPY=X"),   # 0/10 = 0% WR
```
AND add direction-level block in `WINNER_FILTER_CONFIG` for LONG.

---

## 2. myfxbook_retail_contrarian

### Performance by Direction
| Direction | n | WON | LOST | WR | PF |
|-----------|---|-----|------|----|----|
| LONG | 123 | 17 | 106 | 13.8% | 0.138 |
| SHORT | 14 | 7 | 7 | 50.0% | 0.941 |

**SHORT n=14 is too small for confident promotion** but directional bias is clear.
LONG PF=0.138 is a structural loser: for every $1 won, $7.25 is lost.

### Root Cause
`myfxbook_retail_contrarian` bets against retail positioning. Retail is mostly LONG in
FOREX (home bias). A contrarian that bets against retail LONG picks is effectively going
SHORT — but this strategy labels those picks as LONG. The label-direction mismatch is
the likely cause: the signal is telling you retail is LONG (bearish signal for the pair),
but the pick direction is also labelled LONG (picking with retail, not against them).

### Three-Axis Mutation Options
- **Axis 1 (Direction flip):** Block LONG, wait for SHORT to accumulate n≥30.
- **Axis 2 (Symbol lock):** Insufficient per-symbol data to evaluate.
- **Axis 3 (TP/SL):** Not applicable.

**Recommended:** Block LONG direction. Monitor SHORT for 4 weeks (needs n≥30).
Add to `BLOCKED_ASSET_STRATEGY_PAIRS` (direction-level):
```python
("FOREX", "myfxbook_retail_contrarian"),  # block globally, SHORT n=14 too small
```

---

## 3. cta_cross_asset_tsmom

### Performance by Asset Class
| Asset Class | n | WR | PF | Verdict |
|-------------|---|----|----|---------|
| FOREX | 179 | **58%** | ~0.82* | Keep |
| COMMODITY | 71 | **13%** | ~0.10* | KILL |

*PF estimated from WR and avg pnl pattern; exact PF calculation pending.

FOREX subset shows strong WR=58% (n=179). COMMODITY is destroying the all-class average.

### Three-Axis Mutation Options
- **Axis 1 (Class filter):** Block COMMODITY direction only; let FOREX run.
- **Axis 2 (Symbol lock):** Check specific FOREX symbols driving 58% WR.
- **Axis 3 (TP/SL):** Secondary refinement after class filter.

**Recommended:** Axis 1 class filter — block `("COMMODITY", "cta_cross_asset_tsmom")`.
FOREX cohort at WR=58% is worth keeping but needs PF calculation (SHORT-dominant).

---

## 4. forex_carry_momentum

### Performance by Direction
| Direction | n | WON | LOST | WR | PF |
|-----------|---|-----|------|----|----|
| LONG | 181 | 9 | 169 | 5.1% | 0.082 |
| SHORT | 1 | — | — | n/a | n/a |

### LONG Symbol Breakdown (Axis 2 evidence)
| Symbol | n | WR | Verdict |
|--------|---|----|---------|
| AUDJPY=X | 78 | **0%** | KILL — carry unwind trap |
| NZDUSD=X | 45 | 18% | VERY LOW |
| GBPJPY=X | 36 | **3%** | KILL |
| CADJPY=X | 17 | **0%** | KILL |
| USDJPY=X | 3 | **0%** | KILL |

**Root cause:** Carry momentum LONG is betting on JPY-depreciation (carry trade). Post-2024
JPY has been volatile with sharp carry unwind events (AUDJPY -8% in 1 week multple times).
In a high-volatility JPY environment, carry trades LONG systematically lose.

### Three-Axis Mutation Options
- **Axis 1 (Direction flip):** SHORT side is n=1, impossible to evaluate.
- **Axis 2 (Symbol lock — KILL):** Block JPY crosses entirely. AUDJPY+GBPJPY+CADJPY+USDJPY = 134 picks, ~1 win.
- **Axis 3 (TP/SL):** Not applicable — WR=5% means the signal is wrong, not the exit.

**Recommended:** Block `forex_carry_momentum` entirely (LONG-only strategy, no viable SHORT data,
JPY-cross dominates with 0% WR). Mutation cannot save this without SHORT-direction data.
```python
("FOREX", "forex_carry_momentum"),  # LONG-only, 5.1% WR, JPY-carry structural loser
```

---

## Summary of Required User Approvals

| # | Addition to BLOCKED_ASSET_STRATEGY_PAIRS | Evidence |
|---|------------------------------------------|----------|
| A | `("FOREX", "ig_contrarian_sentiment", "USDJPY=X")` — 0/61 LONG | n=61, 0 wins |
| B | `("FOREX", "ig_contrarian_sentiment", "EURJPY=X")` — 0/60 LONG | n=60, 0 wins |
| C | `("FOREX", "ig_contrarian_sentiment", "CADJPY=X")` — 0/10 LONG | n=10, 0 wins |
| D | `("FOREX", "myfxbook_retail_contrarian")` — 13.8% WR | n=123, PF=0.138 |
| E | `("COMMODITY", "cta_cross_asset_tsmom")` — 13% WR | n=71, WR=13% |
| F | `("FOREX", "forex_carry_momentum")` — 5.1% WR LONG-only | n=181, PF=0.082 |

**Each requires explicit user go/no-go per CLAUDE.md before adding to quality_gates.py.**

---

## Validation Commands

```bash
# Reproduce evidence
python3 -c "
import json
from pathlib import Path
from collections import Counter
reg = json.loads(Path('audit_dashboard/data/pf_registry.json').read_text())
# ... (full script in tools/mutation_analysis.py)
"

# Run mutation analysis tool
python tools/mutation_analysis.py --strategy ig_contrarian_sentiment
python tools/mutation_analysis.py --strategy myfxbook_retail_contrarian
python tools/mutation_analysis.py --strategy cta_cross_asset_tsmom
python tools/mutation_analysis.py --strategy forex_carry_momentum
```

---

*Next step: User approves items A-F individually. Claude Code adds to `BLOCKED_ASSET_STRATEGY_PAIRS`*
*in `audit_trail/quality_gates.py` and creates 1 test per addition.*
