# QA PLAN — PnL=0 & blank-field validation against real market data (deepAI/inspect-wt)

**Scope:** every pick on the live surfaces (`picks.active_raw`, `picks.recent_closed`,
`hyrotrader` picks, `money_ready`) — with priority on **OPEN** and **recently-closed** rows.
**Principle:** stored P/L is a *claim*; market data is the *evidence*. A claim with no evidence
fails closed. All gates ship as a CI job + `/audit` banner counts; spec'd file:line against
`f54efb3b4a` — **caveat: that is a 2026-06-06 commit, ~5 months behind `origin/main`; the
fixspecs themselves warn "re-grep before merge" — QA must not inherit stale anchors silently.**

**Relationship to shipped gates (read first).** Gates 1/2 are *row-level measurement*,
complementary to `tools/per_class_cost_gate.py` (class-level **emission** gate, deliberately
fail-open on missing evidence — **do not modify it; QA fail-closed applies to
money-ready/promotion only**, per `final_v3/07_peer_review` G5: emission fail-open, promotion
fail-closed with `INSUFFICIENT`). Gate 3.1 reuses `tools/stop_fill_replay.py`; Gate 1 should
import its `fetch_bars()`/`fetch_bars_yfinance()` rather than build a second candle pipeline
(B2-class divergence defect). **One implementation, not two:** reconcile this plan with
flaxen-hair's proposed `alpha_engine/risk_qa_validator.py` (`final_v4/flaxen-hair_2026-11-14T2304/
01_proposed_edits/PROPOSED_EDITS.md` Edit 5/6 — same validator, wired into
`production_scanner.py`) — single module, this plan's thresholds.

---

## Gate 1 — PnL = 0% validator (the core ask)

For every row where `pnl_pct == 0` (or is blank — Gate 2), independently recompute expected P/L:

| Step | Rule |
|---|---|
| 1. Anchor window | `t0 = entry/open timestamp`, `t1 = closed_at if present else now`. Reject rows with missing/zero timestamps → Gate 2. |
| 2. Price source (by class, redundancy first) | CRYPTO: Binance klines (fallback KuCoin, then CryptoCompare). EQUITY/ETF/BOND/FUTURES: Yahoo chart (fallback Stooq). FX: open.er-api + Yahoo `XXX=X` (cross-check both). MUTUAL FUND: Yahoo NAV. Source + fetch time recorded per row. |
| 3. Implied P/L | LONG: `(px(t1) − px(t0)) / px(t0)`; SHORT: reversed. Use the *same* fill convention the resolver claims (entry price on the row; exit = TP/SL if hit inside window per replay, else `px(t1)` for still-open). |
| 4. Reasonability band | `stored` must lie within `implied ± max(0.25%, 3 × σ_class)` where `σ_class` = robust σ (MAD-based) of `(stored − implied)` residuals for that class over the full ledger (recomputed nightly; typical crypto σ ≈ 1–2%). |
| 5. Zero-specific test | If stored==0 but `|implied| > max(1.0%, 3σ_class)` → **`ZERO_PNL_MISMATCH`** (the pick is flat by assertion, not by market). If stored==0 and `|implied| ≤ band` → **`ZERO_PNL_OK`** (genuinely flat: no movement in window — counted separately so "81% fake zeros" becomes a measured, shrinking number). |
| 6. Time-period sanity | Hold duration must be plausible for the timeframe (e.g. 15m strategy ⇒ hours–days, not 267 days); closed rows with `t1 > now + 5min` or `t1 < t0` → **`TIME_ANOMALY`**. Open rows older than strategy horizon → **`STALE_OPEN`** (feeds the zombie purge). |

**Outputs:** per-row `qa_status` ∈ {OK, ZERO_PNL_OK, ZERO_PNL_MISMATCH, STALE_OPEN, TIME_ANOMALY,
BLANK_*}; nightly JSON `qa_report.json`; dashboard counts; **any nonzero MISMATCH rate >2% on
recently-closed blocks money-ready scoring** (fail-closed).

**Sampling budget:** full reprice for OPEN + closed within 7d (≈700–900 rows/day ≈ 4 API calls
per 100 symbols); older closed rows re-priced weekly on a 10% sample (drift monitor). Reuse
`alpha_engine/universal_price_enricher.py` for symbol→feed mapping before any new fetch layer.

## Gate 2 — Blank-field flagger (open + recently-closed priority)

Fields checked per row: `entry_price, exit_price, current_price, stop_loss, take_profit,
closed_at, direction, strategy, asset_class, timestamp, entry_time, exit_date`
(`entry_time`/`exit_date` from flaxen-hair Edit 5 `required_open`/`required_closed` — one
canonical blank-field contract, not two).

- Blank/null/0/""/NaN on an **OPEN** row → `BLANK_<field>_OPEN` (severity HIGH — cannot compute
  PnL, cannot size, cannot resolve).
- Blank on a **recently-closed** row (≤7d) → `BLANK_<field>_RECENT` (HIGH for entry/exit/direction;
  MEDIUM for TP/SL after the fact).
- Blank on older rows → `BLANK_<field>_HIST` (LOW, weekly sweep).
- **Never coerce blanks to 0** (that is the current failure mode: `pnl_pct` blank→0 manufactures
  the fake-flat rows). Blanks propagate as `UNQUOTED`/`BLANK` into `dashboard_data.json`.
- Correlation rule: `BLANK_entry_price` ∧ `pnl_pct==0` → auto-merge into Gate 1 MISMATCH
  (blank-priced rows are the #1 source of fake zeros — EURGBP/JPY-class garbage).

## Gate 3 — Exit-reasonableness (supports open bugs B4/B5)

1. **Stop-touch replay:** for each `SL_HIT`, did price actually trade through `stop_loss` in
   `(entry_ts, exit_ts]`? If not → `STOP_NEVER_TOUCHED` (B4). Reuse
   `tools/stop_fill_replay.py --truncate-at-exit` (untruncated replay *manufactures* touches —
   `final_v3/07_peer_review` §2.1) — extend to all classes. Peers' **settled** never-touched
   rates are **52–56%** truncated (EQUITY 14/25, ETF 13/25); the 40–56% figure was the
   untruncated first pass.
2. **TP-claim replay:** `TP_HIT` where high/low never reached TP → `TP_NEVER_REACHED` —
   **re-measure from scratch: no source exists for the "flaxen-hair 13/24" attribution**
   (searched their bundles; peer anchor = B4 replay, n=25/class, 4 rows never traded at their
   recorded exit price). **Split pre-/post-#773:** the PR fixed `TAKE_PROFIT` booking in
   `KIMI_RISEOFTHECLAW/live_scanner.py` (fills at the target, not the polled price) — mixing
   windows muddies the measurement.
3. **Fill-vs-plan:** `|exit_price − stop_loss| / entry` beyond class fill-error budget (from
   `stop_fill.py` telemetry) → `FILL_OVERSHOOT` (inspect-wt independent re-run:
   1.932%→2.970%, `final_v2/inspect-wt/01_peer_review/peer_adjudication_final.md`; peers
   publish 1.919%→2.956% — B3/`stop_fill.py` docstring; **pin which budget the gate uses**).
4. `resolution_method` (how filled) still unset → rows get `RESOLUTION_UNKNOWN` until B5 closes;
   `exit_reason` (which trigger) is already populated — use it, don't re-add it.

## Gate 4 — Cross-surface consistency (supports B1/B2/B8)
Same pick id on 2+ surfaces must agree on status/PnL within 0.05pp; EXPIRED ∧ pnl≠0 or
WON ∧ price-never-moved → `STATUS_PNL_CONFLICT`. Counts feed the existing disagreement banner
fixspec (`2026-11-14/deepAI_proposed_fixes_20261114_1612/fixspecs/fixspec_surface_disagreement_banner.md`).

## Rollout
1. Week 1: Gates 1–2 as a nightly script + `qa_report.json` (read-only, no pipeline changes).
2. Week 2: wire into `dashboard_generator.py` as `qa_status` fields + banner counts.
3. Week 3: money-ready score consumes gates (fail-closed); CI job fails on MISMATCH>2%.
4. Gate definitions are pre-registered: thresholds above change only with a recorded justification
   (multiple-testing discipline — B8 lesson).

## Verification plan for the QA system itself
- Unit tests with synthetic rows: genuine-flat, fake-zero, blank, time-anomaly, overshoot.
- Shadow run 7 days: human-review 50 flagged rows against exchange data.
- Peer cross-check: run Gate 1 logic against finpredict-v3's `pi_data_hygiene.py` outputs and
  quant-audit's `per_class_stats.py` — disagreement rate must be <1% (two independent implementations).
