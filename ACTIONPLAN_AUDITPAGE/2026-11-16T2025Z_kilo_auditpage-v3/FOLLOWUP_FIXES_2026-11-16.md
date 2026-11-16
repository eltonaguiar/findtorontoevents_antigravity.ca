# Follow-up Fixes — PM Shadow Pin + Unit Contract

- **Author:** kilo (worktree `auditpage-v3`), COMS seat `kilo-general`
- **Date:** 2026-11-16T20:25Z
- **Base:** `origin/main` @ `5f902fd0ee5` (after PR #852)
- **Predecessor:** `ACTIONPLAN_AUDITPAGE/2026-11-16T2003Z_kilo_auditpage-v3/AUDIT_FINDINGS_2026-11-16.md`

---

## 1. What peers had already fixed (verified on `main`, no action taken)

Before writing code I re-checked the open items from the audit and found these already handled — I did **not** duplicate them:

| Item | State on `main` |
|---|---|
| `strategy_ic_analysis.json` 404 | **Fixed** — live at `/audit/data/strategy_ic_analysis.json` (200, 42 KB, generated 04:49Z), generator `tools/audit_pick_funnel/build_ic_analysis.py` wired into `pick-funnel-nightly.yml` |
| Missing dashboard JSONs (edge_stability / ai_leaderboard / swarm_picks) | **Fixed** — PR #831 merged 17:31Z |
| `forward_clock.js` / `excess_column.js` 404 | **Fixed** — both live 200; `forward_clock.json` present on `main` |
| Ghost-row truth-layer contradiction | **Fixed** — live page now reads "Ghost rows are not cleared … 22,947" |
| PF 999 / ∞ zero-loss sentinel | **Fixed** — `dashboard_enhancements.js:37` renders `n/a` for PF ≥ 999 |
| Walk-forward Sharpe −65.6 on n=3 | **Fixed** — peer clamp renders `n/a` for \|Sharpe\| > 5 |
| "5/5 checks pass" static footer | **Fixed** — string no longer present in `template.html` |

## 2. Fix A (HIGH): prediction markets had no enforced shadow pin

**Problem.** The documented decision is "prediction markets stay shadow (PBO 0.603)", and PM copy-trading is structurally rejected. In code, nothing enforced it: `SIZING_SCHEDULE["shadow"] = 0.0` only applies *if a row lands in the shadow tier*. A PM strategy that cleared the generic 10-step pipeline would have been assigned `recommended_sizing = "tiny"` (0.2% of allocated capital) in `admissibility_pipeline.evaluate()`.

Compounding the risk, PM PnL is currently derived from **spot-proxy TP/SL** on top of binary contract odds (`alpha_engine/polymarket_signals.py`, `kalshi_signals.py`, `dashboard_generator.py:5467`), so a binary contract's true 0/1 payoff is not represented — the gate is being "passed" on a number that cannot exist in the real instrument.

**Fix.** New, additive, env-overridable pin in `alpha_engine/admissibility_pipeline.py`:

- `PREDICTION_MARKETS_SHADOW_ONLY_DEFAULT = True`
- `prediction_markets_shadow_only()` — reads `PREDICTION_MARKETS_SHADOW_ONLY` **at call time** (not import; per the PR #845 lesson about frozen env reads). `0/false/no/off` disables.
- `is_prediction_market_strategy(name)` — matches `polymarket`, `kalshi`, `prediction_market`, `copy_pm`, `pm_momentum`, `pm_whale`, `pm_kalshi`.
- `apply_prediction_market_shadow_pin(verdict, name)` — forces `recommended_sizing = "shadow"`, sets new additive field `shadow_pin = True`, appends one warning naming the forced transition. Idempotent; non-PM verdicts untouched.
- Called once in `evaluate()` after tier determination, so no PM verdict can leave shadow regardless of tier.

**Blast radius.** `evaluate()` gains one post-tier call; the dataclass gains one trailing field (`shadow_pin: bool = False`) — safe for positional construction. No PM row can become *more* sized; non-PM behaviour is byte-identical (verified by the 26 neighbouring tests).

## 3. Fix B (LOW): `money_ready_verdict.json` had mixed units and no contract

`classes.CRYPTO` carries `wr: 0.3576` (fraction) next to `policy_clean_wr_pct: 41.63` (percent), `mdd: 1.0009` (fraction = **100.09% drawdown**, i.e. total wipeout) next to `cvar_95: -95.34` (percent), with `units` declaring only `wr`/`wr_pct`. Any new renderer would display MDD 1.0009 as "1.0%".

**Fix.** Extended the top-level `units` block to declare `mdd`, `cvar_95`, `expectancy`, `bootstrap_ci_lower/upper`, `policy_clean_wr_pct`, `pf`. Additive metadata only — **no value changed**, existing consumers unaffected.

## 4. File paths

**Edited**
- `alpha_engine/admissibility_pipeline.py` — PM pin constants/helpers, `shadow_pin` field, one call in `evaluate()`
- `alpha_engine/money_ready_verdict.py` — extended `units` contract in the `--json` output

**Added**
- `tests/test_pm_shadow_pin.py` — 18 tests (name detection ×13, pin flip, idempotency, kill-switch, non-PM no-op)
- `ACTIONPLAN_AUDITPAGE/2026-11-16T2025Z_kilo_auditpage-v3/FOLLOWUP_FIXES_2026-11-16.md` (this file)

**Not touched:** generated data (`audit_dashboard/data/*.json`), workflows, dashboard JS/template. No data files committed — the hourly `audit-dashboard.yml` owns those.

## 5. Validation

- `python3 -m pytest tests/test_pm_shadow_pin.py -q` → **18 passed**
- Neighbour suites: `tests/test_pf_count_ratio_fix.py tests/test_shadow_size_policy.py tests/test_pm_shadow_pin.py` → **26 passed**
- `py_compile` clean on both edited modules
- `python3 -m alpha_engine.money_ready_verdict --class COMMODITY --ci --json` → exit 0, `units` now lists 9 keys, JSON strict-parses
- No conflict markers

## 6. Still open (not in this PR)

1. **One ledger per class.** CRYPTO is still quoted at PF 0.92 (intrabar n=3,716), 0.26 (money_ready policy-clean n=21,548) and 0.26 (pf_registry n=22,189); EQUITY 59.2% vs 38.8% WR. Pick `pf_registry.by_asset_class_policy_clean_net` as the sizing cohort and badge every other tile `DISCOVERY (n=…)`.
2. **Upstream 91-0 assertion.** Downstream flagging (PR #852) is a backstop; a WR=100%/zero-loss cohort at n≥50 should fail the resolver, not merely be labelled.
3. **Reconcile IC vs calibration.** Confidence is inverted by calibration (conf≥0.90 → 14.4% WR) yet the IC panel calls it ρ=+0.27 "STRONG".
4. **Rebuild PM PnL on contract prices** before the pin is ever lifted; then consolidate the four overlapping PM workflows (`alpha-engine-live`, `prediction-market-agents`, `polymarket-signals`, `audit-dashboard`) and drop the `|| echo` masks.
5. **FOREX geometry.** Wins 0.62% vs losses 1.00% at 57.8% WR — net negative by construction. Raise the TP floor before any FOREX emitter is re-enabled.
6. **Effective-n reporting.** MEMECOIN 74.5% / EQUITY 41.6% / COMMODITY 35.4% single-day concentration means the Wilson CIs in the audit are optimistic; report day-clustered n_eff beside every WR.
