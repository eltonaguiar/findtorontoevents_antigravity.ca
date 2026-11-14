# 2026-11-14 — stop-fill model, per-class cost gate, COT contrarian test

Three fixes from `final_2026_11_14` idea list #1, #2 and #6. Each states what was broken, what
changed, and how it was verified — including the test that failed.

---

## 1. Stop fills — `audit_trail/stop_fill.py` (new) + resolver wiring

### What was broken

Of 1,468 `SL_HIT` rows in the live payload, **1,360 exited at a price that is not the declared stop**.
Crypto planned risk 1.919% vs realized 2.956% (1.54×); overshoot +832.4pp against a class total of
−837.8pp. The rows carried `resolver_version = NULL`, i.e. they never passed through
`universal_pick_resolver` — they came from self-tracked writers that close at a polled price and then
label the row `SL_HIT`.

Also found while measuring: **non-crypto classes exit *inside* the stop** (EQUITY 66%, ETF 79%,
BOND 86% of their SL rows). That is a different defect — likely a trailing stop whose initial level is
what `stop_loss` records — and is left OPEN (see `final_v3/00_common_themes/BUGS.md` B4).

### What changed

- **`audit_trail/stop_fill.py`** (new, pure): classifies each stopped row `stop | gap_through |
  late_polled | unmeasured` and annotates `planned_risk_pct`, `realized_risk_pct`, `stop_slippage_pct`,
  `pnl_pct_at_stop`, `stop_fill_cost_pp`. **It never rewrites `pnl_pct`** — the realized exit is a fact;
  inventing a better fill would be the mirror of the bug.
- **`find_stop_fill()`**: resting-stop model. Fill at the stop when the bar spans it; at the bar **open**
  when the bar gapped through. Gap fills are worse by construction.
- **`universal_pick_resolver._gap_fill_price()`** wired into `_check_tp_sl_intrabar` for both SL and TP,
  symmetric. Env flag `RESOLVER_GAP_AWARE_FILL` (default `1`; `0` restores legacy byte-identical
  behaviour).
- **`tools/stop_fill_replay.py`** (new): replays stopped picks against real 1h candles and scores three
  fill models (recorded / at_stop / gap_aware).

### How it was verified

- `tests/test_stop_fill.py` — 20 tests: risk measures, direction handling, classification tolerance,
  annotation immutability, gap-through on both sides, summary arithmetic. Passing.
- Replay, crypto/`kimi_riseoftheclaw`, n=30 deterministic sample, 48 × 1h candles: **28 stops touched,
  2 never touched, 14.3% gapped through**. Recorded −177.90pp (mean −6.354%) → at_stop −42.00pp
  (−1.500%) → **gap_aware −46.19pp (−1.650%)**. The gap-aware model costs 4.6% more than the optimistic
  at-stop ceiling, which is the expected direction and confirms the model choice.
- Evidence: `final_v3/05_evidence/stop_fill_replay_kimi_crypto.json`.

**Expectation, stated before the fix and unchanged:** PF 0.768 → **≈1.00**. Breakeven, not profit.

---

## 2. Per-class cost gate — `tools/per_class_cost_gate.py` (new) + wiring

### What was broken

`readiness.by_class` reported `sizing_allowed: false` for **all nine classes** while the scanner emitted
~390 picks/month. The system's own slippage validator scored ETF at 267% and COMMODITY at 422% of
average PnL. Separately, `after_cost_net_per_trade` — the field the existing HC after-cost gate reads —
was **null on 3,500/3,500 rows**, so that gate could never block anything either.

### What changed

- **`tools/per_class_cost_gate.py`**: builds `config/per_class_cost_gate.json` under the pre-registered
  rule *class mean PnL ≥ 3× round-trip cost, n ≥ 30*. Costs come from the existing
  `tools/data/transaction_costs.json` — no new cost model. Fail-open on unknown class / thin sample /
  missing or stale (>25h) index. Cached on mtime.
- **`dashboard_generator.stamp_after_cost_fields`**: falls back to the class index when the
  strategy-level B16 index misses, so `after_cost_net_per_trade` / `is_ac_survivor` are populated.
- **`tools/hc_gates_python.passes_high_conviction_pick`**: runs the gate before quality gates. Default
  ON; `PER_CLASS_COST_GATE_ENABLED=0` disables.

### How it was verified

- `tests/test_per_class_cost_gate.py` — 18 tests: 3× boundary, thin sample, unmeasured rows excluded,
  unknown class default cost, fail-open paths, stamping, on-disk round trip, stale-index rejection.
- Built against the live payload:
  **EQUITY ALLOW (3.23×) · CRYPTO 0.58× BLOCK · ETF 0.40× BLOCK · FOREX −1.94× BLOCK · BOND −4.41× BLOCK
  · COMMODITY thin-sample BLOCK.**
- Retroactive simulation over the 3,500 closed rows: keeping only allowed classes turns **−617.5pp into
  +238.3pp**, removing **78.9%** of emissions.

**Caveat, stated plainly:** this is an in-sample, retroactive simulation. It shows the gate removes
losing classes; it does not show the remaining class has alpha.

---

## 3. COT contrarian — `tools/cot_contrarian_backtest.py` (new). GATE FAILED.

### What was tested

Pre-registered in `final_v2/quant-audit-2026-11-14/03_ideas_ranked/RANKED_IDEAS.md` §6 before this file
existed: *weekly rebalance on COT extremes, hold 1–4 weeks, 10bp; gate OOS PF ≥ 1.15 on n ≥ 100,
slippage < 25% of average PnL, and beat an equal-weight commodity benchmark (not zero).*

Data: `ejaguiar1_stocks.cftc_cot_weekly` (2,849 weekly rows, 11 markets, 2021-06-22 → 2026-11-03) +
yfinance daily continuous futures. Signal: trailing z-score of commercial net as % of open interest over
the prior 156 reports (no look-ahead); z ≥ +2.5 LONG, z ≤ −2.5 SHORT. Entry = first bar ≥ report_date + 6
days (Tuesday as-of → Friday publish → Monday entry). Parameters selected on the first 60% of report
dates only, then applied once to the last 40%.

### Result

| Item | Value |
|---|---|
| Selected on IS | z ≥ 2.5, hold 2w (IS n=51, IS PF 1.309) |
| OOS | **n=30, PF 0.861**, mean net **−0.45%/trade** |
| Equal-weight benchmark, same window | **+0.66%/trade** |
| Gate checks | n≥100 **FAIL** · PF≥1.15 **FAIL** · slippage<25% **FAIL** · beats benchmark **FAIL** |
| Diagnostic — inverse (momentum) direction | OOS n=30, PF 1.087, mean +0.25% |

**Verdict: does not survive.** The contrarian sign was also the wrong way round — momentum scored better
OOS. At the 15bp cost in `transaction_costs.json` the result is worse still.

I am **not** re-fitting to the `z ≥ 2.0 / 2w` cell, which had OOS n=109 and would have been the only
combination with enough trades. Choosing it after seeing OOS would be selecting on the test — the exact
error this repo's 4-of-170 result punishes. It is recorded as a candidate for a **new pre-registered
trial** if commodity work resumes.

Evidence: `reports/cot_contrarian_2026-11-14.json`.

---

## Scope note

No production behaviour changed except: gap-aware fill inside the resolver (flagged, default on) and the
HC filter now consulting the class cost gate (flagged, default on, fail-open). Both are one-env-var
reversible. `check_active_picks.py` and `smart_picks_engine.py` were not run (per AGENTS.md).
