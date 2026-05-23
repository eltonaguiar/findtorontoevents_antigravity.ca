# 2026-04-30 — Wire equity × POSITION lane (PEAD + bond credit-spread + TF classifier)

## Trigger

User flagged: "EQUITY active picks have no LONG_TERM TF — are we leveraging
the recent integration batch?"

## Empirical baseline (live `audit_dashboard/data/dashboard_data.json`)

```
EQUITY active picks: 3
  AMD  rs-breakout-scout       trade_timeframe=INTRADAY
  LLY  smart_money_accumulation trade_timeframe=SWING
  PEP  stocks_ema_golden_cross  trade_timeframe=SWING
EQUITY × POSITION: 0 active, 0 closed (out of 281 closed equity rows)
PEAD picks: 0 active, 0 closed
Bond credit-spread picks: 0 active, 0 closed
```

User is correct. Recent integration batch (PEAD wire-up, bond credit-spread,
DSR-aware promotion) shipped CODE that imports + invokes correctly, but the
production cron has wiring gaps that keep the strategies dormant.

## 4-AI convergent root-cause analysis

Independent analyses by Claude / FreeBuff GLM-5.1 / Codebuff / Roocode-via-Grok
all converged on the same diagnosis. Verified in this session:

| Gap | Verified at | Effect |
|---|---|---|
| `BOND_ENABLE_CREDIT_SPREAD` env var only in **docstring**, never set | `.github/workflows/bond-agent.yml` | Strategy imported, iterated, returns `[]` every run via gate at [alpha_engine/bond_strategies.py:462](alpha_engine/bond_strategies.py#L462) |
| `cross_aggregation/timeframe_classifier.py` has **zero equity** strategies in `STRATEGY_TIMEFRAME` | `STRATEGY_TIMEFRAME` dict | Every equity pick falls through to `alpha_engine`=SWING default; POSITION lane structurally unreachable |
| Classifier doesn't check `time_horizon_days` field | `classify_timeframe()` line 180 | TradingAgents emitter (PR #544) sets `time_horizon_days=21` but its picks classify as SWING |
| PEAD bootstrap is **silent on failure** + cache **never persisted** across runs | `alpha-engine-live.yml` lines 114-153 | `data/earnings/*/latest.json` is empty every fresh checkout → `vt_earnings_pead` returns `[]` |
| `audit-dashboard.yml` push paths **missing** `cross_aggregation/timeframe_classifier.py` | Codebuff catch | TF classifier changes only propagate via hourly cron, not push trigger |

The original analyses on disk:
- [reports/INTEGRATION_BATCH_VERIFICATION_2026_04_30.md](reports/INTEGRATION_BATCH_VERIFICATION_2026_04_30.md) (Claude)
- [updates/2026-05-01-equity-tf-long-gap-analysis.md](updates/2026-05-01-equity-tf-long-gap-analysis.md) (FreeBuff)
- [updates/2026-04-30-equity-long-timeframe-audit-gap-analysis.md](updates/2026-04-30-equity-long-timeframe-audit-gap-analysis.md) (Codebuff, with `_FORCLAUDEREVIEW_BYCODEBUFF.MD` handoff)
- (Roocode message — not committed; aligned with above)

## What this PR changes

### 1. `cross_aggregation/timeframe_classifier.py`

**Strategy-level mappings** (POSITION):
- `vt_earnings_pead` — PEAD 5-60d drift window
- `magic_formula_x_piotroski_x_acquirers` — UEPS value_screener (3y+ holding)
- `tradingagents_consensus` — TradingAgents emitter (5-90d horizon, PR #544)
- `stocks_ema_golden_cross` — verified live: producing PEP
- `smart_money_accumulation` — verified live: producing LLY

**Strategy-level mapping** (SWING):
- `bond_credit_spread_mean_reversion` — 3-10d reversion window

**System defaults**:
- `tradingagents` → POSITION
- `value_screener` → POSITION
- `bond_agent` → SWING

**Field check** (`classify_timeframe()`):
- Added `time_horizon_days` to the hold-days fallback chain after
  `max_hold_days` / `maxHoldDays` / `hold_days`. Explicit `max_hold_days`
  still wins if both are present.

**Excluded** (per Codebuff review — no speculative placeholders):
- `bond_duration_carry`, `bond_credit_carry`, `equity_htf_trend_follow`,
  `pead_agent`, `stocks_longterm`, `pead_earnings_drift` — these are
  reserved labels with no current emitter. Add them in the same PR that
  ships the corresponding strategy/system, not as dead config.

### 2. `.github/workflows/bond-agent.yml`

```diff
         env:
           PYTHONPATH: ${{ github.workspace }}
           PYTHONUNBUFFERED: '1'
           BOND_ELITE_FLOOR: ${{ vars.BOND_ELITE_FLOOR || '40' }}
+          BOND_ENABLE_CREDIT_SPREAD: '1'
```

One line. The strategy is already imported, iterated, and tested.

### 3. `.github/workflows/alpha-engine-live.yml`

**Fail-loud cache-size check** appended to the bootstrap step — emits
`::warning::` annotation if `data/earnings/` has fewer than 10 ticker
caches after the bootstrap finishes. Was previously silent on
under-population.

**Persistence step** added after the bootstrap that commits
`data/earnings/` via the existing `safe_push.sh` retry-with-rebase script.
Without this, the bootstrap writes to the ephemeral runner FS and the
files vanish at job end — so every fresh checkout starts with an empty
cache. Both steps are `continue-on-error: true` so a transient failure
doesn't break the cycle.

### 4. `.github/workflows/audit-dashboard.yml`

```diff
       - 'audit_trail/dashboard_generator.py'
       - 'audit_trail/universal_pick_resolver.py'
       - 'audit_trail/fetch_stock_prices.py'
+      - 'cross_aggregation/timeframe_classifier.py'
```

Per AGENTS.md path-registry rule: any classifier/scorer change that
affects pick stamping must trigger the dashboard rebuild on push.

### 5. Tests

- `tests/test_timeframe_classifier_long_term.py` — **22 new test cases**:
  6 strategy mappings (5 EQUITY POSITION + 1 BOND SWING), 3 system defaults,
  3 regression guards on existing defaults, 9 `time_horizon_days` boundary
  cases, 1 max_hold_days vs time_horizon_days precedence test.
- `tests/test_bond_agent_workflow.py` — **+1 test case**:
  `test_bond_credit_spread_env_flag_is_set` — pins the workflow YAML so a
  future refactor can't silently drop the env var again.

All 27 tests pass locally + the existing 5 in
`test_noncrypto_floor_override_workflows.py` and
`test_bond_agent_workflow.py` continue to pass (no regressions).

## What this PR explicitly does NOT do

- **No UEPS active-sync fix.** `tools/run_ueps_pickers.py` writes 30
  long_picks to `ueps_picks.json` every 4h but its `sync_to_active_picks()`
  output is discarded because `ueps-pick-runner.yml` only commits the
  dashboard JSON. The workflow's header comment explicitly chose to keep
  UEPS as a "separate dashboard feed" — fixing it introduces concurrent
  writes to `active_picks.json` with race-condition concerns. Out of scope
  for this PR; track as separate follow-up.
- **No dashboard `Asset-Class × Timeframe` panel.** Codebuff proposed it
  as Commit 4. UI change with its own scope; defer to a follow-up PR after
  this lands and the empty-lane signal is observable.
- **No `freshness watchdog` empty_timeframe_lanes extension.** Codebuff
  proposed as Commit 5. Same deferral logic.
- **No new strategy implementations.** The `bond_duration_carry` and
  `equity_htf_trend_follow` placeholder names in earlier drafts were
  dropped per Codebuff review.

## Verification

After merge + one `bond-agent.yml` cron run + one `alpha-engine-live.yml`
cron run, expect:

1. `non_crypto_agent/data/bond_picks.json` to include rows tagged
   `strategy=bond_credit_spread_mean_reversion` (currently 0).
2. `data/earnings/*/latest.json` to start accumulating in git (committed
   by the new persistence step).
3. Within ~1 cron cycle of #2: PEP and LLY (already producing) reclassify
   from SWING → POSITION on the next dashboard rebuild.
4. Within ~24h of #2: `vt_earnings_pead` starts emitting picks once cache
   has ≥10 tickers.
5. Once UEPS sync gap is fixed (separate follow-up), `magic_formula_x_…`
   picks appear with `trade_timeframe=POSITION` and `pick_type=long_term_value`.

## Risk classification: LOW

- Classifier change: pure metadata; existing closed equity picks may
  reclassify SWING → POSITION but the data is unchanged. POSITION × CRYPTO
  has a -5 score penalty in `quality_gates.py:5123`, but **verified
  CRYPTO-gated** by Codebuff — equities are not penalized.
- BOND env flag: rolling back is one-line removal.
- PEAD persistence: `continue-on-error: true` on both new steps; failure
  modes don't block the cycle. Cache commit goes through `safe_push.sh`
  which already handles merge races for other crons.
- Push paths: pure CI metadata.

## Authoritative ordering for review

Per Codebuff's hardened plan: review files in order classifier → BOND env
flag → PEAD persistence. The classifier is the highest-leverage change
because it retroactively reclassifies *existing* closed equity picks the
moment the next dashboard rebuild runs — even if PEAD/bond never emit, the
EQUITY × POSITION lane becomes non-empty for closed-pick aggregation.
