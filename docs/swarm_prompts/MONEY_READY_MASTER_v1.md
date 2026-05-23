# Money-Ready Master Consult — architecture + per-class edge

You are a senior quant reviewing **findtorontoevents.ca/audit** — a multi-source pick pipeline (MySQL `ejaguiar1_stocks`, resolver v2, `pf_registry`, ML gates, copy-trader intel, crypto scanners).

## Ground truth (non-negotiable)

- **11/11** pre-registered causal hypotheses **KILLED** by walk-forward sign-stability harness.
- **No asset class** has harness-admissible **daily-bar** causal edge for live capital today.
- `pf_registry.json` policy_clean_net is **ledger accounting** — high PF ≠ admissible edge unless a **new** family clears harness forward.
- CRYPTO class aggregate dragged by `quan_engine` volume; COMMODITY has micro-slices (`multi_asset_cot`, copytrader); FOREX has buried `cta_replicator` slice.

## Deliverables

### A) Per-asset-class table

| Class | Live money-ready? | Best 90d paper path | P(Tier-2, 12mo) | Top blocker |
|-------|-------------------|---------------------|-----------------|-------------|

### B) System architecture fixes (ranked P0–P2)

Each: problem → `wire_target` → acceptance test → ETA days.

### C) Five harvest ideas (repo-grounded)

Format: `id` | `wire_target` | mechanism | acceptance_test | risk.

### D) Backtest / methodology brainstorm

For **one** class only (your choice): propose a **pre-registerable** hypothesis (M-107) that is NOT on the killed list — specify bar frequency (daily vs intraday/tick), data source, causal mechanism, and how `edge_stability_harness.py` would adjudicate it.

### E) Worst-strategy autopsy

Pick the worst `(asset_class, source_system)` pair by clean PF in registry. Propose a **mutated** version (not kill) per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — axis: universe, horizon, or filter.

**Reject** answers that claim EQUITY/ETF/BOND are money-ready from registry PF alone without harness.
