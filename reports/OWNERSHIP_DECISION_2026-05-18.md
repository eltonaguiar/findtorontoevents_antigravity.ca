# Ownership Decision — edge-work collision — 2026-05-18

`claude-opus-4-7-desktop` taking ownership per operator directive. Three agents
were independently building the same two signal modules. This resolves it.

## The collision

| work | who was doing it | state |
|------|------------------|-------|
| `alpha_engine/onchain_crypto.py` | external ring-AI (OpenRouter) | local-only, never committed |
| `tools/onchain_crypto_research.py` | peer STRAND B (`feat/strand-b-onchain`) | live peer, in progress |
| `feat/onchain-crypto-signal` | kilo-code | worktree branch, in progress |
| `alpha_engine/options_flow.py` | external ring-AI | local-only, never committed |
| `feat/options-flow-signal` | kilo-code | worktree branch, in progress |

## Decision

### 1. on-chain crypto → peer STRAND B owns it. SOLE owner.

STRAND B (`tools/onchain_crypto_research.py`, branch `feat/strand-b-onchain`)
is the live, coordinated peer and the furthest along. It is also the asset
class the swarm-reviewed roadmap (`ROADMAP_TO_EDGE_2026-05-18.md`) named as the
one real bet.

- ring-AI's local `alpha_engine/onchain_crypto.py` → **discard, do not commit.**
- kilo's `feat/onchain-crypto-signal` → **abandon the branch.**
- STRAND B proceeds, harness + cost gated, as the only on-chain effort.

### 2. options-flow → PARKED. Not built now.

Both reviewers (Grok + DeepSeek) were explicit: feeding a new-data module into
the **current** harness — which tests only sign-stability and **kills
regime-dependent edges** — produces a 9th kill. options-flow is an EQUITY-class
signal; the roadmap puts EQUITY at paper-only-later.

- kilo's `feat/options-flow-signal` → **stop. Abandon the branch.**
- ring-AI's local `alpha_engine/options_flow.py` → **discard.**
- `H-009` (options) stays **pre-registered** in `hypothesis_registry.json` —
  pre-registration before backtest is correct process — implementation deferred
  to after the harness upgrade below.

### 3. Regime-conditional harness → claude-opus-4-7-desktop owns it.

This is roadmap Phase 1 and the real unlock. Unowned, not peer-hot. I take it.

## Phase-1 spec — regime-conditional admissibility

**The gap.** `tools/edge_stability_harness.py::evaluate()` sets
`admissible = len(same_sign) >= 3 AND len(same_sign) == len(strong)` — i.e.
**every** strong window must share one sign. A genuinely regime-dependent edge
(positive in risk-on windows, negative in risk-off) has both `pos` and `neg`
non-empty → `same_sign != strong` → REJECTED. Most real edge is
regime-conditional. The harness is structurally blind to it.

**The fix.** Add `evaluate_by_regime(field, window_days)`:
1. Stratify closed picks by a `regime` label.
2. Run the existing per-window `eff` logic *within each regime cohort*.
3. Verdict: a field is **regime-admissible** if, within at least one regime,
   it is same-sign stable across ≥3 of that regime's windows (≥15 WON / ≥15
   LOST per window, unchanged thresholds).
4. `is_admissible()` gains an optional `regime=` arg; the all-windows verdict
   stays the default (no regression).

**Hard dependency — must come first.** The closed-pick ledger has a `regime`
field populated on only ~3 of ~6,000 rows. `evaluate_by_regime()` is untestable
until `regime` is backfilled onto `closed_picks.json` at each pick's
resolve-date — using the existing `regime_terminal` HMM 7-state detector.

**Sequencing:**
1. Backfill `regime` onto the closed-pick ledger (regime_terminal HMM, keyed on
   resolve-date). Separate PR.
2. Add `evaluate_by_regime()` + `is_admissible(regime=)` to the harness.
   Backward-compatible. Separate PR.
3. Only then: re-test parked signals (options-flow, on-chain) under the
   regime-conditional gate.

## Net

One owner per workstream. on-chain = STRAND B. harness upgrade = me.
options-flow parked until the harness can fairly judge it. No agent builds a
new-data module into a harness that will structurally reject it.
