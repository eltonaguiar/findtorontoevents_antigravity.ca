# STRAND B — New-Input Signal Build: Plan, Testing, Validation (2026-05-18)

Strand B of the post-edge-hunt strategic fork (`reports/STRATEGIC_FORK_SYNTHESIS_2026-05-18.md`).
Built in-house — NOT routed through the Kimi swarm, which produced
synthetic-data backtests twice. Two independent research modules.

## 1. Scope

| Module | Signal | Hypothesis | Branch |
|--------|--------|-----------|--------|
| `tools/options_flow_research.py` | put/call ratio, IV skew (25Δ), unusual options volume, dealer-gamma proxy | H-013 | `feat/strand-b-options-flow` |
| `tools/onchain_crypto_research.py` | exchange net-flows, stablecoin supply Δ, active-address momentum | H-014 | `feat/strand-b-onchain` |

These are genuinely-new input classes — the system has never ingested options
or on-chain data. They are NOT the killed families (funding-rate, yield-curve,
fear&greed, COT).

## 2. The ruleset — 8 base + 6 patched

Base: no simulated data; only `edge_stability_harness.is_admissible()` counts;
no banned/killed signals; pre-register before backtest; opt-in sidecar (no
production wiring); py_compile + network-free tests; honest reporting.

Patched (closing the 6 holes a generic prompt leaves open):
- **H1 data-floor** — harness needs ≥5 windows at n≥80. If free data can't
  supply it, the verdict is "UNTESTED — data-insufficient", explicitly NOT a
  pass. No threshold-lowering to manufacture windows.
- **H2 no proxies** — real options / on-chain data only. A price/volume series
  dressed as options or on-chain data is an automatic discard.
- **H3 honest harness construction** — harness runs on the FULL signal pick
  series with purged+embargoed walk-forward OOS, not a self-selected
  always-positive subset (which passes by construction — the funding-arb
  agent flagged exactly this).
- **H4 post-cost gate** — net edge must leave ≥60% of gross after realistic
  round-trip cost. BOTH harness AND cost gate required. Funding-arb passed
  the harness and still died on cost (5.71%).
- **H5 unmodified harness + reproducible** — import `is_admissible()`
  unmodified; commit the data cache + exact run command + output so the
  verdict is independently re-runnable.
- **H6 real data sources** — CBOE / yfinance option chains / Polygon free
  for options; blockchain.com / CoinGecko / Glassnode / CoinMetrics for
  on-chain. Check env vars for keys first.

## 3. Testing plan

**Per module, before PR:**
1. `py_compile` — clean.
2. Network-free unit tests (`tools/test_<module>.py`): signal math, the
   cost model, the harness wiring, no-look-ahead entry, the
   data-insufficient → UNTESTED path. All must pass.
3. Real-data backtest run: pull real history, run through the unmodified
   `edge_stability_harness`, capture eff-per-window. Commit the data cache
   (or fetch script + cached sample) + the exact run command + its output.
4. The report states the explicit harness construction so a reviewer can
   re-run and reproduce the verdict.

**Acceptance — a signal is an "edge" only if BOTH:**
- `is_admissible()` == True (eff≥0.30, same sign, ≥3/5 windows), AND
- post-cost survival ≥60% of gross.
Anything else → honest KILL or UNTESTED. Expected: after 8 kills the base
rate is low; a kill is the likely and acceptable outcome.

## 4. Post-implementation validation of findtorontoevents.ca/audit

These modules are **opt-in research sidecars with zero production wiring** —
so the correct post-implementation check is a REGRESSION check: confirm /audit
is UNCHANGED by the two PRs.

After the PRs merge and the next hourly pipeline job runs:
1. **No production callers** — `grep -rln "options_flow_research\|onchain_crypto_research" audit_trail/ alpha_engine/` returns nothing in the pick/score path. (Wire-Up Rule: sidecar.)
2. **dashboard_data.json unchanged** — `audit_dashboard/data/dashboard_data.json::performance.asset_class_health` PF/WR/n per class identical before vs after (pull origin/main copy, diff). The modules must not move a single tile.
3. **pf_registry unchanged** — `by_asset_class_policy_clean_net` verdict view identical.
4. **Pipeline green** — `gh run list --branch main` shows the audit-dashboard workflow passing post-merge; no new import errors from the two modules.
5. **harness verdict recorded** — `reports/hypothesis_registry.json` carries H-013 + H-014 with their final verdicts; no silent promotion.

If any of 1–4 changed, a sidecar leaked into production — revert and fix the
Wire-Up violation. If a signal genuinely clears both gates (harness + cost),
that is a SEPARATE future decision: a wiring PR with its own plan, ≥4-week
paper-trade, and the standing money-posture gate — never an auto-promote.

## 5. Status

Both build agents dispatched in-house 2026-05-18. Verdicts pending.
Kimi runs the same scope in parallel; its files will be cross-checked on
delivery for anything this build overlooked.
