# COMMODITY — COT Post-PR-#994 PF Re-Derivation (2026-05-16)

Closes the open item from `reports/asset_class_verification_2026-05-15.md`:
"re-derive COMMODITY PF/WR on post-PR-#994 (COT-dedup) picks — headline
PF 2.37 / n=326 may be over-emission inflated."

**Verdict: confirmed inflated. Severely.**

## Method

Sliced `audit_dashboard/data/dashboard_data.json::picks.recent_closed` for
`asset_class==COMMODITY` (79-pick window), split by emit date around the
PR-#994 COT-dedup merge (2026-05-14). PF = gross-profit / gross-loss on
`pnl_pct`. Reproduce: the slice logic is trivial — group by `timestamp[:10]`
vs `2026-05-14`, and by `symbol=='CT=F'`.

## Results

| Slice | n | WR | PF | net PnL |
|---|---|---|---|---|
| ALL (window) | 79 | 51.9% | 1.95 | +99.9% |
| pre-PR#994 (dedup OFF) | 59 | 67.8% | 5.17 | +158.8% |
| **post-PR#994 (dedup ON)** | 20 | **5.0%** | **0.12** | **−58.9%** |
| COT-strategy only | 64 | 57.8% | 1.98 | +89.3% |
| CT=F (cotton) only | 43 | 81.4% | 6.33 | +151.4% |
| **ex-cotton** | 36 | **16.7%** | **0.33** | −51.5% |

## Finding

The COMMODITY headline (`asset_class_health` PF 2.37 / WR 60.7% / n=326) is a
**mirage built on two artifacts**:

1. **Cotton (CT=F).** 43 of 79 window picks are CT=F at WR 81.4% / PF 6.33.
   CT=F is **blacklisted** (`COMMODITY_BLACKLIST`, Phase 2-D kill) — that
   "edge" is not tradeable. Strip it and COMMODITY is WR 16.7% / PF 0.33.
2. **Pre-dedup COT over-emission.** Before PR-#994 the `cot_positioning`
   strategy fired the same weekly CFTC signal ~20×/cycle. Pre-PR#994 picks
   show PF 5.17; post-PR#994 (dedup active) picks show **PF 0.12 / WR 5.0% /
   −58.9%**. Once each COT release counts once, the edge vanishes.

Tradeable COMMODITY = post-dedup, ex-cotton ≈ **PF 0.12-0.33** — sub-floor.

## Caveats

- `recent_closed` is a 79-pick window, not the full n=326 ledger. Post-PR#994
  n=20 and ex-cotton n=36 are small — the *magnitude* is not verdict-grade.
- The *direction* is unambiguous and severe across every cut: remove the two
  artifacts and COMMODITY collapses below the charter floor.
- A full-ledger re-derivation needs the universal closed-pick export or a
  dashboard regen (not runnable locally per CLAUDE.md).

## Implication

- **COMMODITY is NOT a Tier-1 / real-money candidate.** The
  `asset_class_action_items_2026-05-15.md` and `FOOLPROOF_ACTION_PLAN.md`
  framing of COMMODITY as "best edge, pushing Tier-1" is **falsified** — it
  was reading the cotton + over-emission mirage.
- COMMODITY belongs in the sub-floor / mutate-before-kill bucket alongside
  FOREX, not the Tier-1 push.
- Action: re-run this on the FULL closed-pick ledger to get verdict-grade
  numbers; until then, no COMMODITY sizing-up, no Tier-1 claim.

_Generated 2026-05-16. Source: dashboard_data.json::picks.recent_closed._
