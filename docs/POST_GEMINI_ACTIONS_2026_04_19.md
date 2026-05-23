# Post-Gemini Diagnostic Actions — 2026-04-19

Investigations triggered by review of Gemini's advanced analytics walkthrough.
Diagnosis only; no production code or blocklist edits in this pass.

Source data: `audit_dashboard/data/dashboard_data.json` (generated_at 2026-04-19),
3500 rows in `picks.recent_closed`.

---

## Task 1 — Decaying strategies: candidate blocklist additions

Methodology: per-strategy WR over the last 7 days (rows with `closed_at` >= now-7d),
filtered to `n7 >= 10`, compared against `max(strat_fwd_wr)` as all-time baseline
(stored as PERCENT in the dashboard payload). A strategy qualifies if
`wr7 < 35% AND (baseline_pct - wr7) > 20pp`.

Strict-threshold hits:

| strategy                              | wr7%  | n7  | base%  | drop  | fwd_n | blocklist status |
|---------------------------------------|-------|-----|--------|-------|-------|------------------|
| st_fear_greed_contrarian              | 10.5  | 390 | 34.8   | 24.3  | 868   | NOT blocked (`fear_greed_contrarian` IS in `_RETIRED_STRATEGIES` but the `st_`-prefixed variant is NOT — name-mismatch bleed) |
| st_obv_support_divergence             | 17.0  |  53 | 52.9   | 35.9  | 204   | NOT blocked |
| crypto_mtf_ema_slope_alignment_v1     |  9.1  |  11 | 40.7   | 31.6  | 167   | NOT blocked |

Borderline (fails one criterion but matches Gemini's flagging):

| strategy              | wr7%  | n7 | base% | drop  | note |
|-----------------------|-------|----|-------|-------|------|
| macd_rsi_confluence   | 27.3  | 44 | 44.1  | 16.8  | drop<20pp; still sub-30% WR on 44 trades |
| MeanReversionBB       | 46.2  | 13 | 56.3  | 10.1  | fails wr7<35% filter; watchlist only |
| forex_rsi2_mean_reversion | 52.7 | 186 | 100.0 | 47.3 | baseline=100% is suspect (low-n registry artifact), keep watching |

### Recommended `_PAPER_ONLY_STRATEGIES` additions (reversible tier)

1. **`st_fear_greed_contrarian`** — same mechanic as the already-retired
   `fear_greed_contrarian`; the `st_` prefix variant slipped through the name match.
   Root-cause the prefix first (maybe canonicalize before `is_blocked_strategy`),
   OR add both names. High confidence, n=390.
2. **`st_obv_support_divergence`** — n=53, WR 17%, drop 35.9pp; clean
   paper-only candidate.
3. **`crypto_mtf_ema_slope_alignment_v1`** — n=11 is the minimum bar; paper-only
   (not retired) is the right tier given small sample.

Hold off: `macd_rsi_confluence` and `MeanReversionBB` — symptoms match but numbers
do not clear the stated thresholds. Watchlist; re-check in 7 days.

---

## Task 2 — `forward_win_rate` reference map

The canonical post-Oct-2025 field name is **`strat_fwd_wr`** (see
`audit_trail/stamp_pick_quality.py:297`). `forward_win_rate` is legacy.

### Live hot-path readers (priority fixes)

| File:line | Op | Fallback? | Status | Fix |
|-----------|-----|-----------|--------|-----|
| `battleground_quality_filter.py:429` | read `strat.get('forward_win_rate', 0)` | none | LIVE filter layer (see header docstring) | Add fallback chain: `strat.get('forward_win_rate') or strat.get('strat_fwd_wr') or 0`. Silently zero today → filter currently drops everything except records that still carry the legacy field. |
| `bundle_baby_system.py:537` | `stats.get("forward_win_rate", 0)` | none | LIVE bundle scorer | Same dual-key read; unit check (fraction vs percent) required since `strat_fwd_wr` is percent. |
| `discord_bundle_baby.py:152` | `bundle.get('forward_win_rate', 0)` | none | LIVE discord notifier | Same dual-key fallback. |

### Dashboard / schema (not a silent-zero bug, but stale naming)

| File:line | Notes |
|-----------|-------|
| `audit_dashboard/template.html:12361`, `index.html:12358` | Dashboard renders `p.forward_win_rate` — probably already NaN/blank in the UI. Swap to `p.strat_fwd_wr` (edit template, not index). |
| `cross_aggregation/aggregator.py:238,248` | Constructor kwarg + dict-write of a legacy name. Either pass through both keys or rename; confirm downstream reader. |

### Dead / write-only sites (no fix needed)

- `BABY_BUNDLE_REGISTRY.md:399`, `bundle_baby_system.py:93,216,366,489,507`,
  `deploy_high_performance_bundles.py:{83,113,143,173}`, `updates/*`, the ~200
  entries in `genome/data/unified_strategy_catalog.json` — all schema/writers
  feeding the baby-bundle pipeline, an isolated subsystem. Leave as-is.
- `CRYPTO_SYSTEM_COMPREHENSIVE_IMPROVEMENT_PLAN.md:215` — doc.

### Priority order

1. `battleground_quality_filter.py:429`  (drives filter acceptance)
2. `bundle_baby_system.py:537`
3. `discord_bundle_baby.py:152`
4. `audit_dashboard/template.html:12361`  (UI cosmetic, but misleading)
5. `cross_aggregation/aggregator.py:238,248`  (verify consumer first)

---

## Task 3 — PROVEN tier tagging diagnosis

### Tagging paths (two independent systems)

1. **System-level** — `cross_aggregation/system_trust_registry.py:_compute_tier_from_stats`
   (lines 688–720). Requires `wr >= 0.65 AND closed >= 30`. Called from
   `get_dynamic_system_tier()` which reads live `closed_picks.json` each run and
   recomputes. Static registry can only promote a BANNED system to UNTRUSTED,
   **never downgrade a dynamic PROVEN** (line 819 comment explicitly forbids it).

2. **Pick-level** — `audit_trail/stamp_pick_quality.py:_assign_trust_tier`
   (lines 161–172). Thresholds are much looser: `n >= 10 AND wr >= 0.55`.
   Stamps `trust_tier` onto live active picks via `stamp_picks()` (line 251).

### Retroactive update on closed picks — THE REGRESSION

`stamp_pick_quality.py:303–309`:

```python
existing_trust = str(p.get("trust_tier") or "").upper()
if existing_trust not in ("PROVEN", "BANNED", "UNTRUSTED"):
    p["trust_tier"] = trust
```

- The stamper is invoked on a `picks` list loaded from a file (`run()` at
  line 332). Nothing in the function restricts it to OPEN picks — if the caller
  passes closed picks, they get re-tagged.
- PROVEN is a one-way ratchet: once stamped, it is preserved forever even if
  the strategy's current WR collapses. A strategy that hit 56% WR on 10 trades
  briefly became PROVEN and stays PROVEN on every subsequent pick, including
  the ones now losing. This matches Verified Alpha's WR 14.5% / PF 0.17 on last 7d.
- The 3× trade-count discrepancy (498 vs 2145) is consistent with the dashboard
  scoping Verified Alpha to pick-level `trust_tier == "PROVEN"` while Gemini
  counted system-level PROVEN systems' entire output.

### Demotion path

- System-level: automatic on every aggregator run (recomputes from fresh
  `closed_picks.json`). Working.
- Pick-level: **no demotion exists**. The only way `trust_tier` changes off
  PROVEN is a manual file edit. `alpha_engine/auto_tuner.py:907+` has a
  drawdown-gated demotion but it edits `LOW_CONFIDENCE_STRATEGIES`, not
  `trust_tier`. These are different systems with no shared state.

### Verdict

Regression is real and root cause is clear:

1. `stamp_pick_quality._assign_trust_tier` PROVEN bar (WR>=55%, n>=10) is too
   loose and lacks a rolling window — it uses all-time stats.
2. The `existing_trust not in ("PROVEN", ...)` guard turns PROVEN into a
   sticky label that survives catastrophic recent decay.
3. There is no pick-level demotion job.

Obvious fixes (do NOT apply without peer review per CLAUDE.md):
- Drop `"PROVEN"` from the preserved-tier set so tier gets recomputed each run.
- Require n >= 30 AND WR >= 0.60 for PROVEN at the pick level, matching the
  system-level bar.
- Add a rolling-7d filter to the stats used by `_assign_trust_tier`, or stamp
  a separate `trust_tier_recent` and have the dashboard read that.
