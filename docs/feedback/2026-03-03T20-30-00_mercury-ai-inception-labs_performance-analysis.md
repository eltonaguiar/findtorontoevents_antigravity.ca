# Mercury AI / Inception Labs — Performance Analysis & Tactical Recommendations
> **Received:** 2026-03-03 ~20:30 UTC
> **Source:** Mercury AI, Inception Labs
> **Context:** Analyzed from closed-trade data used by Discord feeders (mercury2, alpha_engine, baby_battleground, claws_of_doom) and current Discord routing code.
> **Saved by:** Claude Code session, auto-archived for reference

---

## Performance Snapshot

| System | Trades | WR | Expectancy/trade |
|--------|-------:|---:|-----------------:|
| Mercury2 | 46 | 39.1% | +0.25% |
| Alpha Engine | 162 | 34.6% | -2.45% |
| Baby Battleground | 128 | 64.8% | +0.53% |
| Claws of Doom | 25 | 56.0% | +0.78% |
| FC-PRO qualified mix (claws+baby) | 153 | 63.4% | +0.57% |

---

## Big Findings

### Mercury has clear pattern edge
- `risk_reward >= 1.4` subset: 68.2% WR, +1.87% expectancy.
- `above_200 == False` subset: 60.0% WR, +1.39% expectancy.

### Alpha is direction-asymmetric
- **LONG:** 26.4% WR, -3.95% expectancy.
- **SHORT:** 66.7% WR, +3.41% expectancy.

### Discord consensus issues
- In current consensus snapshot, 12/15 symbols are single-system; 3/4 "master" scores are single-system.
- Manual sender script flattens all signals and sends by confidence only (can bypass consensus robustness).

### Data quality inconsistency
- Status/exit-reason conflicts and mixed PnL units exist in closed logs, which can distort tracking if not normalized.

---

## TP/SL + Pattern Tweaks (highest impact first)

1. **Alpha:** Gate to SHORT-only for selected strategies until LONG recovers.
2. **Mercury:** Enforce stricter RR >= 1.4 (or 1.5) and prefer below 200-SMA contrarian setups in extreme fear.
3. **Discord master routing:** Require >=2 unique agreeing systems for master-picks.
4. **Remove raw manual sender path** (or force it through vetted deployment).
5. **Keep Baby** but prioritize top 5 strategies (small uplift with lower noise).

---

## Estimated Uplift Scenarios

| Scenario | Expectancy/trade |
|----------|----------------:|
| Alpha SHORT whitelist only (historical, 16 trades) | +11.29% |
| Mercury RR >= 1.4 | +1.87% (vs +0.25% baseline) |
| FC-PRO + Alpha short whitelist | +1.59% (vs +0.57% current) |

---

## Where To Change

| File | Purpose |
|------|---------|
| `mercury2/config.py`, `mercury2/risk_engine.py` | Mercury thresholds |
| `cross_aggregation/fc_crypto_pro.py` | FC-PRO scoring/filter gates |
| `alpha_engine/auto_tuner.py`, `alpha_engine/scanner.py` | Alpha direction restriction + disabled strategy handling |
| `signal_aggregator/picks_router.py`, `signal_aggregator/aggregator_fixed.py`, `scripts/send_top_picks_now.py` | Discord routing/consensus robustness |

---

## Verification Notes (Claude Code, Mar 3 2026)

### Confirmed accurate:
- Mercury2: 46 trades, 39.1% WR -- matches data
- Alpha direction asymmetry: LONG ~26% WR, SHORT ~65% WR -- confirmed
- All referenced file paths exist
- Baby Battleground is strongest by WR

### Corrections:
- Baby Battleground actual: **117 trades** (not 128), **65.8% WR** (not 64.8%)
- Alpha Engine actual: **165 trades** (not 162), data grew by 3 since snapshot
- Alpha LONG expectancy: **-1.01%** (not -3.95% as claimed)
- Alpha SHORT expectancy: **+2.12%** (not +3.41% as claimed)
- "Manual sender bypasses consensus" -- **FALSE**: code sorts by consensus_score first, routes through PicksRouter gates
- "12/15 single-system" -- **UNVERIFIED**: code has anti-single-system dedup logic
- Mercury RR >= 1.4 "subset" -- ALL 46 trades have RR=1.5 (this IS the full dataset)

---

*End of feedback archive.*
