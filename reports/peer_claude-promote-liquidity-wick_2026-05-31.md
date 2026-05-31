# Peer report — Conditional promotion of `crypto_liquidity_wick_reversal_v1`

- **Author:** claude (peer subagent)
- **Date:** 2026-05-31
- **Recommendation:** **PROMOTE-WHEN-RESOLVER-FIXED** (do NOT promote yet)
- **Type:** docs-only proposal — no code change, no registry mutation
- **Goal alignment:** CLAUDE.md Goal #1 (phenomenal performance across asset classes — CRYPTO)

## TL;DR

`crypto_liquidity_wick_reversal_v1` is the only CRYPTO strategy that currently
passes Bonferroni-walk-forward + R:R analysis (full-table WR ~59% / PF ~2.1 /
realized payoff ~1.46 per the upstream R:R optimization analysis cited by the
operator request). It is the lead T2 candidate for CRYPTO. **However**, a
known resolver pathology (FINDING_OVERALL #12 — one-sided resolution: WIN side
closes promptly while the LOSS side hangs OPEN/never resolves) would mean any
promotion is sized against a numerator that has not yet been adversarially
debited by its losses. Promotion is therefore **gated** on the FINDING #12 fix
landing + a re-resolve sweep that confirms the loss side actually closes.

## 1. Current gates and state (sources of truth)

### 1a. Production registry / promotion path

`tools/build_pf_registry.py:50-58` already names this strategy explicitly in
the `SOURCE_CONCENTRATION` guard. Threshold:

- `SOURCE_CONCENTRATION_THRESHOLD_DEFAULT = 0.60`
- `SOURCE_CONCENTRATION_MIN_N = 5`
- env override: `PF_REGISTRY_SOURCE_CONCENTRATION_THRESHOLD`

Per `feedback-concentration-strategy-not-engine.md` (HHI > 0.30 at strategy
level), the strategy is **flagged** in pf_registry single_source_pct logic but
**not blocked**; it remains in `by_asset_class_strategy_symbol`.

### 1b. Probation / killer gates

`alpha_engine/strategy_killer.py`:

- `PROBATION_PENALTY = -25` (line 80)
- WR 25-40% with n>=triggers => PROBATION (lines 405-409)
- PF 0.50-0.80 => PROBATION

Current strategy stats (post-policy-clean, n=30 BTCUSDT-only):
WR 60.0% / PF 1.56 → does **NOT** trigger probation, does **NOT** trigger kill.
Status per killer = `ACTIVE` (default branch, line 415). No PROBATION_PENALTY
is applied today.

### 1c. Forward / walk-forward gate

`alpha_engine/data/walk_forward_validation.json:3895`:

```
strategy: crypto_liquidity_wick_reversal_v1
trades_in_data: 1
trades_in_leaderboard: 13
verdict: INSUFFICIENT
reason: "Only 1 trades in data (need 20+)"
```

→ The walk-forward harness sees only 1 closed trade in its data window. This
is the **emission-coverage** problem documented in
`reports/mutation_crypto_wick_reversal_2026-05-31.md` — emits BTCUSDT-only.

### 1d. Whitelist / promotion membership

`alpha_engine/data/core_whitelist.json:145`:

```
"baby_strats_forward::crypto_liquidity_wick_reversal_v1"
```

→ Already whitelisted on the `baby_strats_forward` source path. Not on
production scanner / smart_picks_engine path.

### 1e. No explicit `min_confidence`, `min_rr`, `min_forward_trades`,
`allow_without_forward` keys are configured for this strategy. It inherits the
global walk-forward `INSUFFICIENT` verdict + the `baby_strats_forward`
whitelist. There is no per-strategy probation downweight today.

## 2. Numeric basis for promotion

Operator-cited R:R optimization analysis (`reports/rr_optimization_analysis_2026-05-31.md`
referenced but not yet committed in this worktree — TREAT AS UPSTREAM CLAIM):

- WR 59.03%
- PF 2.106
- Realized payoff 1.46
- Bonferroni-walk-forward: PASS
- R:R analysis: PASS

Local corroboration (`reports/mutation_crypto_wick_reversal_2026-05-31.md`,
2026-05-31):

- Closed picks (raw, n=43, BTCUSDT-only): WR 58.1% / PF 1.50
- Policy-clean cohort (pf_registry, n=30): WR 60.0% / PF 1.56
- 25 WIN / 18 LOSS in the raw cohort — losses ARE present

→ Magnitudes agree with the upstream R:R analysis; signs agree. **CAVEAT:** the
operator's brief states "n=59 WON / 0 LOST" for this strategy. Local
`battleground/data/closed_picks.json` shows 25 WIN / 18 LOSS at n=43 — i.e.
LOSSES DO RESOLVE on this strategy in at least one ledger. This is the exact
discrepancy FINDING #12 is meant to explain: the **resolver**'s view (n=59 / 0
LOST) differs from the **raw-ledger** view (n=43 / 18 LOST). Both must be
reconciled before promotion.

## 3. Proposed promotion (conditional)

When (and only when) the FINDING #12 fix has landed AND a re-resolve sweep has
confirmed losses now close, the following changes are proposed:

| Layer | From | To | File |
|---|---|---|---|
| Whitelist | `baby_strats_forward::*` only | Add `alpha_engine::crypto_liquidity_wick_reversal_v1` | `alpha_engine/data/core_whitelist.json` |
| Position weight | 0.5x (implicit; sandbox sleeve) | 1.0x (full T2 sleeve, per deep_dive_CRYPTO recommendation §105 step "2x current") | `alpha_engine/conviction_stack.py` / `risk_policy_loader.py` |
| Walk-forward gate | INSUFFICIENT blocks production emission | Allow production emission once `trades_in_data >= 20` | `alpha_engine/validation/promotion_gate.py` |
| Emission universe | BTCUSDT-only (de-facto) | Keep BTCUSDT in PROD; lift {ETH, SOL, BNB, AVAX} into SANDBOX per mutation autopsy §Next-step | `incubator/agents/*/crypto_liquidity_wick_reversal_v1.py` |
| Source-concentration override | flag-only (single_source_pct=1.0) | Annotate as "by construction — BTC-only universe" in pf_registry meta | `tools/build_pf_registry.py` |

Headline: **lift probation/sandbox treatment to T2 sleeve sizing on BTC; keep
non-BTC symbols in SANDBOX until ≥20 closes each.**

## 4. THE GATING DEPENDENCY — FINDING_OVERALL #12 (RESOLVER ONE-SIDED CLOSE)

Per the operator brief: "n=59 WON / 0 LOST means the resolver only closes the
WIN side for this strategy." This matches a class of pathology where:

- Winning picks hit TP fast → resolver writes `WIN` row immediately.
- Losing picks hit SL slow / SL is wide / mark-price source disagrees with
  trigger source → resolver leaves the row OPEN indefinitely.
- Net result: PF and WR are inflated because the loss-side numerator never
  enters the denominator.

**Promotion is BLOCKED until the following are all true:**

1. FINDING_OVERALL #12 root cause identified and fixed in
   `alpha_engine/outcome_resolver.py` (the canonical fix site — `PNL_WIN_THRESHOLD_BY_CLASS`
   already lives at lines 115-126; the one-sided issue is downstream of that).
2. A re-resolve sweep is run over all OPEN `crypto_liquidity_wick_reversal_v1`
   picks older than the strategy's typical hold window (3h per mutation report
   §Axis 3). Expected effect: a non-zero count of OPEN → LOSS transitions.
3. Post-fix cohort still meets the T2 bar: WR >= 50%, PF >= 1.5, n >= 30,
   on the policy-clean cohort.

If post-fix WR drops below 50% OR PF drops below 1.5, **DO NOT PROMOTE** —
the apparent edge was a resolver artifact.

## 5. Conditional acceptance criteria

| # | Criterion | Source / test |
|---|---|---|
| AC-1 | FINDING #12 fix merged + re-resolve sweep complete | `reports/` post-fix audit, pf_registry rebuilt |
| AC-2 | Post-fix cohort WR >= 50% on BTCUSDT, n >= 30 | `pf_registry.by_asset_class_strategy_symbol` |
| AC-3 | Post-fix cohort PF >= 1.5 on BTCUSDT, n >= 30 | same |
| AC-4 | Realized payoff >= 1.3 (down from 1.46 to allow margin) | upstream R:R analysis re-run |
| AC-5 | `walk_forward_validation.json.trades_in_data >= 20` | `alpha_engine/data/walk_forward_validation.json` |
| AC-6 | No source-concentration > 0.60 across SOURCES (the strategy can be 100% one-symbol but should not be 100% one source_system) | `pf_registry` single_source_pct |
| AC-7 | Operator sign-off | manual |

All 7 must be GREEN before merging the promotion PR.

## 6. Rollback plan

If post-promotion WR drops below 45% over a 7-day rolling window OR PF below
1.3 on n >= 20 of new picks:

1. Revert `core_whitelist.json` entry → return to sandbox.
2. Set conviction weight back to 0.5x in `conviction_stack.py`.
3. Re-enable `walk_forward_validation` INSUFFICIENT block.
4. Open `reports/rollback_liquidity_wick_<DATE>.md` with the WR / PF / n that
   triggered the rollback + the per-pick autopsy.
5. Re-enter mutation protocol (`docs/MUTATION_THREE_AXIS_PROTOCOL.md`) before
   any second promotion attempt.

Mean-time-to-rollback budget: 24h from criterion breach to whitelist revert.

## 7. What this PR does NOT do

- No edit to `alpha_engine/conviction_stack.py`.
- No edit to `alpha_engine/data/core_whitelist.json`.
- No edit to `tools/build_pf_registry.py` thresholds.
- No edit to `outcome_resolver.py` (FINDING #12 fix belongs in its own PR).
- No edit to dashboards, no FTP deploy, no `updates/index.html` entry.

This is a docs-only artifact recording the conditional plan so a future PR can
reference these acceptance criteria once FINDING #12 lands.

## 8. Cross-references

- `reports/mutation_crypto_wick_reversal_2026-05-31.md` — three-axis autopsy.
- `reports/deep_dive_CRYPTO_2026-05-31.md` §60, §105 — same strategy named as
  T2-grade contributor + paper-money sleeve at 2x recommendation.
- `reports/crypto_resolver_lag_root_cause_2026-05-31.md` — adjacent resolver
  pathology (CRYPTO 48h 0-closes), context for FINDING #12.
- `tools/build_pf_registry.py:50-58` — strategy explicitly named in
  concentration guard comment block.
- `alpha_engine/data/core_whitelist.json:145` — current whitelist entry.
- `alpha_engine/data/walk_forward_validation.json:3895` — current INSUFFICIENT
  verdict.
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — mutate-before-kill, also
  mutate-before-promote.
- CLAUDE.md goal #1 — n >= 100 "proven" bar (current n=30 does NOT meet this
  for full real-money sizing; T2 sleeve at the AC bar is the compromise).
