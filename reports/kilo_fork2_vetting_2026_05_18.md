# Vetting Report — kilo / openrouter-ring 2.61T Fork-2 New-Signal Work

**Date:** 2026-05-18 · **Method:** 6-agent parallel vetting swarm, one agent per
file/concern, each scoring against the 8 non-negotiable rules kilo was given.
**Scope:** the Fork-2 new-signal effort — two signal modules, the harness-gated
research driver, the pre-registration, and the reports.

## Bottom line

| Artifact | Verdict | Merge? |
|----------|---------|--------|
| `reports/` edge conclusions (EDGE_HUNT_CONCLUSION, EDGE_VERDICT, PATH) | **PASS** | trust the conclusion |
| `tools/new_signal_research.py` + tests | **PARTIAL** | fixable |
| `reports/hypothesis_registry.json` H-006/7/8 | **PARTIAL** | fix hashes + waiver |
| `alpha_engine/options_flow.py` | **FAIL** | **do NOT merge** |
| `alpha_engine/onchain_crypto.py` | **FAIL** | **do NOT merge** |
| `reports/mimo_strand_b_reference/` | orphan dump | delete/archive |

**The research conclusion is sound — believe "no edge, 8 kills".** The two signal
*modules* are broken, untested, and ungated — they must not reach any pick path.

## Per-artifact findings

### `alpha_engine/options_flow.py` — FAIL (violates R2, R3, R4, R7, R8)
- **CRITICAL** `:314` dealer-gamma math is wrong — a walrus + a second subtraction
  double-subtracts put gamma; result is `call − 2·put`. The core signal is incorrect.
- **CRITICAL** `:518-528` `compute_skew()` filters on an `option_type` key the dicts
  never contain → `KeyError` every call, swallowed by try/except → the IV-skew signal
  *always returns None*. Dead signal.
- **CRITICAL** never imports/calls `edge_stability_harness` — "edge" is asserted via
  hardcoded confidence constants (R2).
- **CRITICAL** header cites hypotheses H-009/H-011 that do not exist in
  `hypothesis_registry.json` (R4).
- **HIGH** rebuilds a contrarian fear&greed/RSI-style sentiment signal (R3 banned).
- **HIGH** no unit tests exist (R7). **HIGH** "IV skew *momentum*" computes a static
  level; `_get_recent_skew(days=7)` returns 1 snapshot (R8 over-claim).
- Quasi-fabricated stats: hardcoded `EXPECTED_SHARE=0.40`/`VOLATILITY=0.15` called a
  "z-score"; invented VIX term tickers `^VXE/^VXG/...` and DTE map.

### `alpha_engine/onchain_crypto.py` — FAIL (violates R1, R2, R4, R7)
- **CRITICAL** `:156-200` `_compute_deposit_withdrawal_estimate()` derives "exchange
  net-flow" from blockchain.info *network-wide TX volume* — a price/volume proxy
  relabeled as on-chain data. This is the exact R1 / Strand-B automatic-discard
  violation. The correct metric is Glassnode `transfers_volume_exchanges_net` (the
  mimo reference uses it).
- **CRITICAL** never calls the harness / `is_admissible()` (R2).
- **CRITICAL** no network-free unit tests (R7).
- **HIGH** cites unregistered hypothesis H-010; mis-pathed + mis-scoped vs the Strand-B
  plan (which assigns this to `tools/onchain_crypto_research.py`, H-014) (R4).
- **HIGH** `_fetch_large_transactions()` calls any >100 BTC tx a "whale exchange move"
  and stamps it BEARISH without ever resolving an exchange address.
- **MED** aggregate stablecoin supply mislabeled "USDT supply" (R8). Reinvents
  `exchange_flow_strategies.py` / `crypto_onchain_momentum.py` / `defillama_signals.py`.

### `tools/new_signal_research.py` + `test_new_signal_research.py` — PARTIAL
- py_compile clean; tests **run green** (11 checks / 5 pytest functions), network-free.
- Tests are **real, not theatre** — the harness negative-control (600 noise records →
  rejected) genuinely proves the wiring discriminates. **But thin:** no test ever
  constructs separating records and asserts `admissible=True` — the harness *accept*
  path is unexercised; a "reject-everything" bug would pass all 11 checks.
- **HIGH R3** H-006 is perpetual-funding-rate directional; H-008 is 2s10s yield-curve
  slope — both banned families. The contrarian/momentum framing does not exempt them
  without a documented waiver.
- **MED** `_purge_embargo()` advertises an embargo purge it never performs (`EMBARGO_DAYS`
  unused). **R1 PASS** — no simulated price data; the "synthetic resolved-pick record"
  is just a harness wrapper around real API prices.

### `hypothesis_registry.json` H-006/H-007/H-008 — PARTIAL
- Mechanically correct: pre-registration commit `46873896e24` landed 6 min *before* the
  logic commit `8b04aa0ed0c`; one test statistic each; the logic commit only filled in
  results (no after-the-fact insertion).
- **CRITICAL** every `registered_commit` field points to `892d5163d019` (an unrelated
  M-105 gates fix), not the actual pre-registration commit `46873896e24`. The anchor is
  meaningless — fix all three.
- **CRITICAL** H-006/H-007/H-008 re-test M-107 banned families (funding-rate, 2s10s,
  term-structure carry). M-107 is supposed to *forbid* this; the pre-registration ritual
  was used to launder banned-family backtests. All rejected by the harness, none wired —
  so no production damage — but the discipline did not fire.
- **MED** pre-registered with `status: LIVE_TESTING` (should be `REGISTERED`/`PENDING_TEST`).

### Harness wiring + duplication — PARTIAL
- The two `alpha_engine/` modules are genuine **opt-in sidecars** — `grep` confirms zero
  production callers; the Strand-B plan labels them opt-in. Wire-Up Rule satisfied.
- **CRITICAL** the harness is called *only* by `new_signal_research.py`. `options_flow.py`
  and `onchain_crypto.py` — the files that actually emit picks — never touch it. They are
  ungated pick emitters, safe today only because nothing calls them.
- **MED** `reports/mimo_strand_b_reference/{options_flow,onchain_crypto}.py` are untracked
  divergent twins (different API, will drift). **HIGH** `reports/mimo_strand_b_reference/
  __pycache__/` is build litter — gitignored, but delete it.

### Reports / edge conclusions — PASS (minor cleanups)
- No edge claimed anywhere; every verdict is REJECTED, gated on the harness, with real
  eff-per-window arrays. Kills reported plainly. Every claimed file/module/branch
  (`feat/h006-funding-redesign`, `h008-bond-redesign`, `h010-equity-pead` + their
  research modules/reports) **verified on disk**. No fabrication.
- **MED** kill-ledger table is internally muddled — "242 names" vs report's 247; two
  `#5`s and two "kill #6"s. **LOW** `EDGE_HUNT_CONCLUSION` + `strand_b_baseline.json` are
  uncommitted while their evidence lives on three unmerged branches — a reader on
  `feat/fork2-new-signals` cannot reproduce the claims.

## Recommended actions

1. **Do NOT merge `options_flow.py` / `onchain_crypto.py`.** Send back: fix the gamma
   bug + skew dead code, replace the TX-volume proxy with a real exchange-flow metric,
   pre-register real hypotheses, add network-free tests (incl. the harness *accept*
   path), and route signals through `is_admissible()` before any pick emission.
2. **Fix `registered_commit`** in all three H-00x entries → `46873896e242...`.
3. **Get operator sign-off or drop** H-006/H-008 — they re-test M-107-banned families.
4. **Delete `reports/mimo_strand_b_reference/`** (orphan twins + `__pycache__`).
5. **Trust the edge conclusion** — 8 harness kills, no edge. This is the honest,
   verified result. The path forward is the genuine-new-input route in
   `reports/roadmap_no_edge_to_money_ready_2026_05_18.md` Phase 3 — done with the
   discipline this vetting found missing.
