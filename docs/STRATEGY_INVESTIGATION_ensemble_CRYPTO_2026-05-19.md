# STRATEGY_INVESTIGATION — `ensemble` CRYPTO — 2026-05-19

Pre-kill investigation per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`.
Mutation 3-axis test per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

## Trigger

`audit_dashboard/data/pf_registry.json` `by_asset_class_strategy_policy_clean_net`
(canonical post-dedup post-policy-clean net-of-cost):

```
asset_class=CRYPTO strategy=ensemble
n=79  wins=4  losses=75  WR=5.06%  PF=0.013  total_pnl_pct=-56.346
```

Single largest pnl drag in the entire canonical CRYPTO ledger
(class total pnl = −43.36; ensemble alone = −56.35; removing ensemble flips
class to PF 1.21 / +12.98pp per arithmetic on canonical).

## Mutation axis 1 — Direction

Raw scan of `audit_dashboard/data/dashboard_data.json` + `pf_registry.json` +
`alpha_engine/data/*.json` for `strategy=ensemble`:

- **136 LONG, 0 SHORT, 82 NULL/unset.** Strategy is direction-mono.
- Sign-flip (SHORT instead of LONG) on the canonical n=79 would yield
  WR ≈ 95% — but this is **post-selection bias on a same-sample bear-period
  cohort**. Per 3-AI swarm review (`reports/PF_IMPROVEMENT_PER_CLASS_2026-05-19T2137Z.md`):
  inverting because it lost = ex-post pruning, not edge.
- Verdict: **direction inversion NOT a rescue.** A separately pre-registered
  hypothesis "SHORT ensemble during contango/risk-off regimes" (e.g. H-039)
  would be a legitimate path; that needs M-107 pre-reg first.

## Mutation axis 2 — Symbol rotation

`by_asset_class_strategy_symbol` CRYPTO ensemble — 25 distinct symbols:

| Top losers | n | pnl |
|---|---|---|
| LTCUSDT  | 14 | −10.49 |
| SHIBUSDT | 13 | −10.09 |
| BCHUSDT  | 5  | −3.38  |
| HBARUSDT | 5  | −3.69  |
| POLUSDT  | 5  | −3.93  |
| ETCUSDT  | 4  | −2.81  |

**24 of 25 symbols WR=0%.** Only winner: SOLUSDT n=1 (single pick, +0.13).
No symbol subset preserves edge — symbol rotation does not rescue.

## Mutation axis 3 — Timeframe / regime

Raw entry timestamps from `dashboard_data.json` sample: 2026-05-14 → 2026-05-17
— strategy is **actively emitting today**. Bleed is current, not historical.
Insufficient regime tagging in canonical view to test regime-conditional rescue
without further data pulls; doing so risks the same convergence trap that
killed H-001..H-037.

## Verdict

**KILL.** Add `("CRYPTO", "ensemble")` to
`audit_trail/quality_gates.py::BLOCKED_ASSET_STRATEGY_PAIRS`.

Rationale:
1. PF 0.013 net, n=79 ≥ kill threshold (n≥30 + PF<1.0 per existing
   `copy_trader_clones` precedent).
2. Symbol breadth (25 symbols, 24/25 WR=0%) rules out symbol-ghost.
3. Direction mono-LONG with all losses — inversion = post-selection bias,
   rejected by today's 3-AI swarm verdict.
4. Currently bleeding −56pp net on canonical ledger; halting emission is
   highest-leverage single drag-removal available.

## Do NOT

- Do not invert direction without M-107 pre-registration of SHORT-ensemble
  as a new family (H-039 candidate).
- Do not promote sign-flipped same-sample number as evidence of edge.
- Do not re-aggregate canonical post-block as same-sample "lift" — proof
  comes from forward 200-close window, per acceptance gate revision in
  `reports/PF_IMPROVEMENT_PER_CLASS_2026-05-19T2137Z.md`.

## Unblock condition

Re-emerge only if BOTH:
1. Pre-registered as H-039 (or later) with M-107 commit before any backtest.
2. New variant clears unmodified `tools/edge_stability_harness.py`
   `is_admissible()` on ≥3 same-sign windows of n≥80 each.

## References

- Canonical ledger: `audit_dashboard/data/pf_registry.json` (snapshot 2026-05-19T19:46:55Z)
- Authoritative no-edge frame: `reports/EDGE_VERDICT_2026-05-18.md`
- PF improvement plan: `reports/PF_IMPROVEMENT_PER_CLASS_2026-05-19T2137Z.md`
- Companion blocks landed same session: `rapid_fire`, `copy_trader_intel`,
  `copy_trader_clones` (CRYPTO).
