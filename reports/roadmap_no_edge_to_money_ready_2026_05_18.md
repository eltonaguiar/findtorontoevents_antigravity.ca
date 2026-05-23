# Roadmap — No Statistical Edge → Money-Ready System (per Asset Class)

**Date:** 2026-05-18 · **Author:** Claude Opus 4.7 · **Goal #1** (audit dashboard).
Companion to `reports/audit_pick_flow_case_study_2026_05_18.md` and the
`audit-pick-flow` skill.

## Honest starting position

- **No asset class is money-ready.** CRYPTO is the only class with a meaningful
  resolved sample and it is sub-floor (WR ~33%, PF 0.17-0.41). Non-crypto classes
  are unresolved (`pnl_pct=0.0` placeholders) or artifact-inflated (COMMODITY/COT).
- **The edge hunt is exhausted** — 8 leakage-controlled candidates rejected by
  `tools/edge_stability_harness.py`. Re-testing killed families is M-107-banned.
- The only forward route is **genuinely new input data, harness-gated** — and the
  first attempt at that (Fork-2 `options_flow.py` / `onchain_crypto.py`) failed
  vetting (see `reports/kilo_fork2_vetting_2026_05_18.md`).

This roadmap is therefore **measurement-first**: you cannot build edge you cannot
see, and right now 5 of 6 asset classes are statistically invisible.

## The 6 phases

### Phase 0 — Make the system measurable (2-3 weeks) — BLOCKER FOR EVERYTHING

Nothing downstream is trustworthy until these land.

| Task | Why | Done when |
|------|-----|-----------|
| Fix the non-crypto outcome resolver | EQUITY/FOREX/FUTURES/ETF/BOND close at `pnl_pct=0.0` — see `feedback_noncrypto_resolver_live_close_bug` | a sampled non-crypto closed pick has a real entry/exit/pnl |
| Populate `at_raw_picks.closed_at` on every terminal-status row | rollups keyed on `closed_at` undercount; status enum is inconsistent | `closed_at` non-null wherever `status` is terminal |
| Normalize the `status` enum | `CLOSED` vs `WON`/`LOST`/`EXPIRED` both terminal | single documented enum |
| Wire the `at_pick_audit_trail` writer | full per-gate trace; opt-in per Wire-Up Rule | `trace_pick.py` shows PASS rows, not just rejects |
| Adopt `at_pick_flow_daily` on `/audit` | nightly per-class funnel already live | dashboard reads the rollup |

**Exit criterion:** `pick_flow_funnel.py --days 30` returns a real WR/PF for every
class, not placeholders.

### Phase 1 — Fix the plumbing (2 weeks)

The funnel loses most picks to *freshness*, not *quality*: staleness rejected 5,396
CRYPTO picks/week, `no_consensus` 1,600+. Edge filters barely get to act.

- Diagnose the emit→corroborate latency: why do picks go stale before a second
  source confirms them? Faster aggregation cycle, or longer freshness window.
- Audit `no_consensus`: are single-source picks genuinely weak, or is the
  consensus-window too tight? Per-class consensus thresholds.
- **Exit criterion:** <20% of emitted picks die to staleness/no_consensus.

### Phase 2 — Per-class triage (parallel with Phase 1)

| Class | Action | Target |
|-------|--------|--------|
| CRYPTO | Cut volume from sub-PF-1 source systems; keep only forward-validated strategies. The drag is unfiltered volume + the `LOST`-status −78% tail. | lift resolved PF toward 1.0 |
| EQUITY | After Phase 0, re-measure. Charter says T2-candidate (PF 1.4). Gather n≥100 clean. | verdict-grade sample |
| FOREX | Keep SHORT-only throttle. Mutate-before-kill per `MUTATION_THREE_AXIS_PROTOCOL`. | stop the bleed, don't kill |
| COMMODITY | Stop citing the COT-inflated tile. Re-measure ex-COT. | honest non-artifact number |
| BOND/ETF/FUTURES | Below n≥50 floor — gather data, no verdict. | n≥50 per class |

### Phase 3 — Genuine new-input edge hunt (4-8 weeks, ongoing)

The directional-signal space is exhausted. The only admissible route:

1. **One hypothesis at a time**, pre-registered in `reports/hypothesis_registry.json`
   in a *separate commit before any backtest logic* (family, ONE test statistic,
   correct `registered_commit` hash).
2. **Real data only** — live-API historical data; no `np.random`, no proxy
   relabeled as a new input (the Fork-2 `onchain_crypto.py` failure mode).
3. **The harness is the only verdict** — `edge_stability_harness.is_admissible()`
   (eff≥0.30, same sign, ≥3/5 windows). Win-rate/PF/Sharpe alone never promote.
4. **Not a banned family** — no funding-rate-directional, 2s10s, COT, RSI/F&G
   contrarian, per-symbol curve-fit ML.
5. **Network-free unit tests** that exercise the signal math *and the harness
   accept path* (Fork-2 tests only exercised the reject path).
6. Opt-in sidecar with a `## Wiring Plan` until the harness clears it.

Candidate new-input families not yet genuinely tried: L2 order-book imbalance /
trade-tape microstructure; real dealer-gamma from properly-sourced options data;
genuine on-chain exchange net-flow (Glassnode `transfers_volume_exchanges_net`,
not a TX-volume proxy); cross-exchange basis dispersion.

### Phase 4 — Money-ready promotion gate (per class)

A class is promoted only when, on Phase-0-clean resolved data:
`n≥100` · `WR ≥ 0.52` · `PF ≥ 1.5` · `DSR ≥ 0.95` · `PBO ≤ 0.55` · `MDD < 20%` ·
≥4-week forward track record · at least one harness-admissible signal driving it.
This is Tier-2 (`docs/PERFORMANCE_CHARTER.md`). Document each promotion as an
`updates/` card citing the `reports/` source + reproducer command.

### Phase 5 — User experience

- **Fix the orphaned "💰 Money Ready" button** — `applyMoneyReady()` calls
  undefined `window.renderActive` and no render path applies `filterMoneyReady()`.
  Either wire it to the render path or remove the button and keep only the
  working Money Ready *tab*.
- Surface the **pick funnel** on `/audit` from `at_pick_flow_daily` so users see
  emitted → gated → published → resolved per class.
- Make Smart Picks / High Conviction / Money Ready visibly nested (one filter
  refining the previous), so a user understands why a pick is or isn't in each.

## Timeline

```
Weeks 1-3   Phase 0  (measurement) ──────────────┐ blocks all
Weeks 2-4   Phase 1  (plumbing)        ──────────┤
Weeks 2-6   Phase 2  (per-class triage)──────────┤
Weeks 5-13  Phase 3  (new-input edge hunt) ──────┤
Ongoing     Phase 4  (promotion gate, per class)─┤
Weeks 3-6   Phase 5  (UX) ───────────────────────┘
```

## Definition of success

The roadmap succeeds when at least one asset class clears the Phase-4 gate on
clean data with a harness-admissible signal — and `/audit` honestly shows the
others as WATCH/NOT_READY rather than inflated. A truthful "not ready yet"
dashboard is a valid milestone; a falsely-green one is a regression.
