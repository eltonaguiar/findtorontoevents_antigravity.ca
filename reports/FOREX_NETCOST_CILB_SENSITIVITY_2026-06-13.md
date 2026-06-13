# FOREX consensus — net-cost CI-LB sensitivity (the money-ready gate)

**Author:** claude-fable · 2026-06-13 ~07:05Z · **Method:** cluster-bootstrap PF CI-LB (`tools/pf_ci_lower.py`, symbol-day clusters) on `non_crypto_consensus` FOREX, deduped `trading_picks`, 2026+, with a per-round-trip cost subtracted from each trade's `pnl_pct` (percent units; 1bp = 0.01 subtracted).

## Verdict: NOT money-ready. The edge dies at ~1bp of execution cost.

The gross edge is real (CI-LB 1.35 @ n_eff 304, clears the bar). But it is **entirely consumed by the first ~1bp of round-trip cost** — so it is a sub-1bp-execution edge (institutional/rebate territory), not a deployable directional taker edge at any retail or typical-prop cost.

### Sensitivity curve

| cost/trade | ALL dir (n=304) PF / **CI-LB** | LONG only (n=129) PF / **CI-LB** |
|---|---|---|
| 0bp (gross) | 1.79 / **1.35** ✓PROMOTABLE | 2.49 / **1.64** ✓PROMOTABLE |
| 1bp | 1.32 / **0.996** ✗ | 1.73 / **1.14** (≈bar, just under) |
| 2bp | 0.99 / 0.75 ✗ | 1.23 / **0.82** ✗ |
| 3bp | 0.75 / 0.57 ✗ | 0.90 / 0.60 ✗ |
| 5bp | 0.46 / 0.35 ✗ | 0.53 / 0.34 ✗ |
| blended majors-3bp / JPY-6bp | 0.55 / **0.41** ✗ | 0.64 / **0.41** ✗ |

- **ALL directions:** CI-LB drops below **1.15 at 1bp** and below **1.0 at 1bp**.
- **LONG only** (the "powerhouse" per the forex-consensus memory): CI-LB drops below **1.15 at 1bp** and below **1.0 at 2bp** — marginally more cost-tolerant, still gone by 2bp.

## Why this is tighter than the prior point-PF read
The forex-consensus memory flagged "net-positive only at ≤2bp" using **point** net PF. The **CI-LB** (the promotion-grade statistic) is stricter: it's already <1.0 at 1bp for all-directions, because the gross edge rides on tiny winners (~0.2–0.3%/trade) whose lower confidence bound is fragile to any haircut. **Promotion must be gated on net CI-LB, not net point PF** — same lesson as the MiMo inversions and the freebuff kill-list.

## Implication
- **Do NOT size `non_crypto_consensus` FOREX** on the gross CI-LB 1.35. As a directional taker strategy it is not money-ready at any realistic cost.
- The only path to deployment is **provably sub-1bp execution** — i.e., majors-only, maker/rebate fills, no JPY (JPY-6bp kills it outright). That is an execution-microstructure question, not a signal question. The peer's pilot (PR #592) must gate acceptance on net CI-LB at the *actual achieved* fill cost, not gross.
- **North-star status unchanged: 0 money-ready edges net of realistic cost.** The project's single best *gross* edge is a sub-1bp-execution edge. The bottleneck is now precisely characterized: not signal discovery, but whether sub-1bp FX-majors execution is achievable.

## Reproduce
`tools/pf_ci_lower.py` over deduped `trading_picks` (non_crypto_consensus, FOREX, symbol-day clusters), `net = pnl_pct − cost`, cost ∈ {0,1,2,3,5}bp + blended. DB via `tools/db_env.get_stocks_creds()`.
