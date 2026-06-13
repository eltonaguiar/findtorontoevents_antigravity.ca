# Session Progress — claude-fable — June 13 2026, 02:11 AM EDT

**Scope:** money-ready edge hunt + DAILY_IDEAS action items + peer-review of other agents' work, run as an autonomous ~10-min-cadence loop (deadline 13:47 UTC). This doc = progress, remaining tasks (subtasked), and areas for improvement.

## 1. Executive summary

The session's most valuable output is **honest measurement discipline**, not a finished winner. We found one statistically strong FOREX edge, proved it dies on transaction cost, and discovered the *real* bottleneck: **the system emits low-amplitude picks whose gross edge can't clear spread.** The one net-positive structural candidate (`leveraged_etf_decay`) is marginal. Net: **0 fully money-ready classes still, but we now have a cost-aware methodology + 2 tracked candidates + tooling that stops false winners and false kills.**

## 2. Shipped this session (9 PRs)

| PR | What | Status |
|---|---|---|
| #567 | IDEA-H PM odds-history capture + lead/lag analyzer | merged |
| #575 | Fixed `pm_macro_overlay` silent no-op (API schema drift) | merged |
| #584 | Surface picks-now push masker (unblocks lint-masking on workflow PRs) | open |
| #585 | PM lead/lag = **NO-EDGE** (Bonferroni: 0/20 LEADING survive) + 6mo backfill | open |
| #587 | **FOREX winner** `non_crypto_consensus` LONG (gross PF 3.13) + de-risk + cost caveat | open |
| #589 | `crypto_verified_wf` default OFF + fail-closed (backtest sleeves must not auto-promote) | open |
| #590 | **Kill-validation guard** — caught 4/8 of a peer's kill list as false kills | open |
| #591 | FOREX-LONG pilot plan, peer-reviewed by 8-model panel | open |
| #592 | **Cost-aware** FOREX-LONG forward-paper pilot tracker (Option A sidecar) | open |
| #593 | Net-of-cost edge hunt — `leveraged_etf_decay` is the lead net-positive candidate | open |

## 3. Key findings & durable principles

1. **Net cost is the killer.** FOREX `non_crypto_consensus` LONG: gross PF 3.13 → **net 0.76** at retail FX cost (winners only ~0.2–0.3%). Always screen **net PF + average winner size**, never gross.
2. **Measure edge at the strategy level, not the class level.** FOREX class FAILS (PF 0.55) but one *source* inside is strong-gross — the aggregate buries it.
3. **Per-symbol-day dedup is mandatory.** FOREX raw 15,084 → 1,853 deduped (88% batch duplicates). Un-deduped stats are meaningless.
4. **`at_pick_outcomes` ≠ `trading_picks`.** The kill-switch lane has a broken WR column and disagrees with the live book — it would retire profitable strategies (4/8 false kills caught).
5. **PM prediction-market odds do NOT lead bonds/FX** (0/20 survive Bonferroni) — coincident/reactive only.
6. **Only higher-amplitude edges survive cost.** `leveraged_etf_decay` (~1.6% winners) survives; FOREX (~0.2% winners) doesn't.

## 4. Current best candidates

| Candidate | Gross PF | Net PF | OOS | Status |
|---|---|---|---|---|
| `non_crypto_consensus` FOREX LONG | 3.13 | **0.76** | holds gross | gross-only; viable only at ≤2bp execution (majors) — NOT money-ready as executed |
| `leveraged_etf_decay` SHORT (JDST/SOXS/LABD) | 1.30 | **1.24** | 1.16 net | marginal T3; structural (vol-decay); n=69, 3-symbol concentration |

## 5. Remaining tasks (subtasked)

### T1 — Pre-register both hypotheses (M-107) — *small, mine*
- T1a: add `non_crypto_consensus` FOREX LONG to `reports/hypothesis_registry.json` with a **NET-cost gate** (accept = net PF≥1.5 at ≤2bp).
- T1b: add `leveraged_etf_decay` SHORT with net-cost gate + concentration cap.

### T2 — Expand & re-validate `leveraged_etf_decay` — *medium, mine (needs DB)*
- T2a: pull the full leveraged-ETF universe (TQQQ/SQQQ, SOXL/SOXS, TZA, YANG, FAZ, SDOW, SPXU…) from `trading_picks`.
- T2b: re-measure net PF + IS/OOS on the broader set; check if concentration breaks and net PF holds ≥1.2.
- T2c: if it holds, add as a 2nd pilot sleeve in `forex_long_pilot_tracker` (generalize the tracker to multi-sleeve).

### T3 — Non-crypto intrabar replay (the Stage-4 gap) — *large, delegate-able*
- T3a: scaffold `verified_strategies/intrabar_replay_noncrypto.py` (daily OHLC first-touch, SL-first) for FOREX/ETF.
- T3b: source non-crypto intrabar/daily bars (yfinance/FMP) for the pilot symbols.
- T3c: re-resolve the FOREX LONG + leveraged_etf_decay cohorts intrabar; compare to daily-resolver PF.

### T4 — Pilot auto-accrual — *small, delegate-able*
- T4a: daily cron workflow for `forex_long_pilot_tracker.py` (must carry a `::warning` to pass lint-masking, or wait for #584).
- T4b: publish `forex_long_pilot_status.json` to the audit dashboard.

### T5 — Harden the methodology into gates — *medium*
- T5a: bake the per-class cost model into the audit dashboard so nothing is labeled "winner" on gross PF.
- T5b: wire `cross_validate_kill_candidates.py` as a pre-kill CI gate (so #590's check runs automatically).

### T6 — Get the 9 PRs reviewed/merged — *ongoing*
- multi-model PR review + fix any CI; coordinate luxalgo conflict with peers.

## 6. Areas for further improvement (systemic)

1. **The amplitude problem is the root cause.** The pick generators emit small-target picks (tight TP/SL) that can't clear cost. Fix at the source: either widen TP targets toward ≥0.5–1% moves, or add a **cost-aware emission gate** that rejects picks whose expected move < k×(round-trip cost). This is probably the single highest-leverage change for money-readiness.
2. **Net-PF everywhere.** Every audit surface, registry, and gate should report and gate on **net-of-cost** PF. Gross PF has repeatedly manufactured false winners.
3. **Intrabar coverage for non-crypto.** Only crypto has intrabar replay; FOREX/EQUITY/ETF use daily first-touch. A true intrabar SL-first replay is the gold standard and a hard Stage-4 gate.
4. **Deprecate or fix `at_pick_outcomes`.** It drives the kill switch but disagrees with the live book — either fix its resolver or stop killing on it.
5. **Breadth & regime.** All edges are concentrated (few symbols) and 2026-cohort only. Need universe expansion + regime-stratified / longer-window validation before sizing.
6. **Execution-quality reality check.** The FOREX edge needs ≤2bp round-trip — is that achievable on the intended broker/venue? If not, it's dead. Do an execution-cost study before any FX pilot.

## 7. Autonomous loop status
Running ~10-min increments to 13:47 UTC; hourly `/dropchat-multipc` + peer review (next ~06:47Z). State: `~/.forex_pilot_loop_state.json`. Each tick = one concrete committed/PR'd increment.
