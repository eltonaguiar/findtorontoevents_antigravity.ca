# Overall / dashboard-level quick wins + proposed fixes (deepAI, 2026-11-14)

Scope: cross-asset, dashboard and pipeline level. Per-asset detail lives in sibling folders.
Evidence base: `2026-11-14/inspect-wt_20261114_1058/` (findings + evidence_live_audit.json)
and `fixspecs/` in this folder.

## Quick win A — PASS (patch attached): add hyro_pick_performance.json to the freshness tripwire
- File was 157h stale on the live site while "Hyro daily" kept reporting success.
- `patches/0001-hyro-pick-perf-freshness-tripwire.patch` (anchor-verified against f54efb3b4a,
  audit-dashboard.yml tripwire list ~line 582). One-day ship, zero risk.

## Quick win B — PASS (display-only): surface-disagreement warning on class cards
- The data needed is already in the payload: pf_registry rows carry `profit_factor` and n;
  money_ready carries pf per class. Render both on the class card when they differ >25% with a
  "SURFACES DISAGREE" badge. Currently the disagreement is invisible unless the user reads
  two different panels. Zero backend change. Spec: `fixspecs/fixspec_surface_disagreement_banner.md`
  (being finalized) — the pattern is already used by the existing honesty banners.

## Quick win C — PASS (data verified): kill the "best strategy: prediction_market_consensus (score 92)" highlight
- That highlight comes from hyro_pick_performance.json — which is 157h stale — and the same source
  emitted XRPUSDT entry=0.0 live 90 minutes before my fetch. Until the file refreshes and the
  garbage-price guard (fixspec_garbage_price_ingest_guard.md) ships, suppress "best strategy"
  badges sourced from that file. Frontend-only, low risk.

## Quick win D — PASS (verified vaporware): remove mutual-fund claims from the live page until real
- No live mutual-fund picks exist; `alpha_engine/mutual_fund_ranker.py` does not exist. Options
  spec: `fixspecs/fixspec_mutual_fund_vaporware.md`. One-day decision, removes a false promise.

## Quick win E — FAIL (needs admin): attach failure artifacts for the 4 broken workflows
- Alpha Engine Live / yfinance refresh / CI Tests / audit-dashboard queue-cancels: root causes
  UNVERIFIED because logs are admin-only. Add `actions/upload-artifact` of failing-step logs —
  then every future audit (and the actions-failure-guardian) can diagnose without admin.
  Spec: `fixspecs/fixspec_actions_remediation.md` §3–5.

## Quick win F — PASS (config-verified): FOREX kill-switch default flip
- See `per_asset_class/forex_futures_commodity/quick_wins_and_proposed_fix.md` Quick win 1
  (one-character change, anchor verified).

## Overall proposed fix — one canonical ledger + one class-policy layer
- The two deepest cross-asset fixes combine in `fixspecs/fixspec_single_canonical_ledger.md`
  (all stat surfaces compute from one dedup'd ledger; filter diff published; CI gate on
  inter-surface divergence) and the class-policy layer (emission and display gated by one
  verdict). Together they eliminate: contradictory stats, emitting-while-blocked, and
  zombie/garbage leakage into aggregates.
