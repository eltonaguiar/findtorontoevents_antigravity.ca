# Weekly Real-Money Filter — 2026-05-28

**Run:** `/money-maker-readyv2`
**Sources (all fresh, generated 2026-05-28):** `money_ready_verdict.json` (07:41Z),
`pf_registry.json::by_asset_class_policy_clean_net`, `pick_summary_stats_2w.json`
(14d raw, 05:26Z), `db_health.json` (07:58Z).

## VERDICT: 0 of 8 asset classes are real-money ready. No filter is shipped this week.

Per the v2 success criteria (PF≥1.5, WR≥50%, n≥100 **clean** per class, DSR/SPA/PBO
pass), **zero classes qualify**. This is a NO-GO week. Kelly position size for every
class = **0% (DD-halt / insufficient clean evidence)**.

The binding constraint is **not strategy edge — it is data integrity.** We cannot
measure edge cleanly because the outcome lifecycle is broken (see §Blocker).

## Per-class state — the two views diverge, and that divergence IS the finding

| Class | Verdict-grade (policy-clean closed) | 14d RAW (at_raw_picks) | Why raw is untrustworthy |
|-------|-------------------------------------|------------------------|--------------------------|
| EQUITY | n=12, WR 25%, PF 0.03, exp −0.145 → INSUFF | n=8417, WR 65.8%, PF 5.39 | 60% single-source (smart_money); clean n only 12 |
| CRYPTO | n=338, WR 34.3%, PF 0.87, exp −0.012 → NOT_READY | n=482, WR 38.4%, PF 0.67 | 66% incubator_gainer concentration; 67 dup groups |
| FOREX | n=15, WR 20%, PF 0.78 → INSUFF | n=6024, WR 83.5%, **PF 0.10** | WR/PF contradiction = labeling bug; **76% EXPIRED mislabeled WON** |
| FUTURES | n=11, WR 9.1%, PF 0.48 → INSUFF | n=2767, WR 50.6%, **PF 130.6** | 88% single-source (alpha_engine_unified); 204 dup groups |
| ETF | n=3, WR 33%, PF 0.19 → INSUFF | n=140, WR 70%, PF 2.68 | clean n=3; raw 34% single-source |
| COMMODITY | n=4, WR 50%, PF 3.23 → INSUFF | (folded into raw) | clean n=4 — far below floor |
| BOND | n<10 → INSUFF | — | no decisive cohort |
| PENNY_STOCK | n=1 → INSUFF | — | n=1 |

**Read this table as:** the large RAW win-rates are artifacts. FOREX showing 83.5% WR
*and* PF 0.10 simultaneously is mathematically impossible for honest labels — it is the
EXPIRED→WON mislabel drift. FUTURES PF 130 on 88% one-source with 204 duplicate groups
is concentration + ghosting, not edge. The honest, policy-clean cohorts (n=3–338) all
fail PF≥1.5 / WR≥50% and most are below the n≥100 floor.

## Blocker (P0) — fix this before ANY class can be measured, let alone sized

`db_health.json` 2026-05-28 07:58Z:
- **Forward validator frozen — last terminal write 2026-05-12, 368h (15+ days) ago.**
- **29,247,197 OPEN rows** never closing → the clean closed-pick cohort is starved
  (that is why EQUITY clean n=12 while raw 14d n=8417).
- **22,947 ghost rows** across 10 cohorts (MEMECOIN/meta_strategy/DOGEUSDT: 3,569 +
  3,160 near-identical rows) inflating any strategy that touches them.

Until the validator is unfrozen and re-resolves the backlog, every per-class WR/PF on
the dashboard is either (a) starved (clean) or (b) contaminated (raw). Neither is
real-money grade.

## How to apply this week

1. **Do not size up any class.** All Kelly fractions = 0.
2. The only defensible paper-tracking targets are the *clean* cohorts where PF>1 AND
   n is growing — currently **none meet n≥100 clean**. CRYPTO has the largest clean
   cohort (n=338) but PF 0.87 < 1, so it loses money net of slippage.
3. Treat the dashboard's optimistic raw surfaces (EQUITY 65% / FOREX 83%) as
   **DISPUTED** until the validator + labeling P0s close.

## Rescue path (acceptance criteria to revisit next week)

1. **Unfreeze forward_validator** and re-resolve the 29.2M OPEN backlog (P0, incidents).
2. **Re-label EXPIRED→WON drift** (FOREX 76%; affects ~2.5k rows per incidents) and
   re-run the v2 outcome resolver so PF/WR are honest.
3. **Dedup the 22.9k ghost rows** (start with the DOGEUSDT meta_strategy cohort).
4. **Enforce the concentration gate BEFORE DSR/SPA** (open P0 — currently produces
   false Tier-1 passes) so single-source classes (EQUITY smart_money 60%, FUTURES
   alpha_engine 88%) can't masquerade as edge.
5. Re-run `/money-maker-readyv2`. A class is shippable only at PF≥1.5, WR≥50%,
   n≥100 post-dedup clean, with concentration <60% and DSR/SPA pass.

## Risk controls (standing)
- Max per-pick: 0% this week (no class passed the gate).
- DD halt active by default given the frozen-validator P0.
