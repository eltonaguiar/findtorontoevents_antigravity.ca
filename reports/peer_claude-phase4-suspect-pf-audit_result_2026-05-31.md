# Phase-4 SUSPECT-PF AUDIT — Result (2026-05-31)

**Author:** Claude Opus 4.7 (peer-claude phase-4 subagent)
**Scope:** Forensic audit of two Phase-3 MC-flagged "too good to be true" strategies in `ejaguiar1_stocks.trading_picks`.
**Verdict:** Both PFs are **resolver artifacts**, not real edge. **RETIRE both from money-ready until resolver is fixed.**

---

## 1. `cta_golden_cross_200` (COMMODITY)

### Numbers
| Window | n | WR | PF | Notes |
|---|---|---|---|---|
| Phase-3 MC report | 25 | 96% | 44 | mean 4.55%, std 1.98% |
| All-time, all rows | 332 | — | — | 273 = `TIME_EXIT_MAX_HOLD` w/ pnl=0 |
| All-time, pnl_pct ≠ NULL | 303 | 86.7% | 16.76 | 26 wins / 4 losses |
| Excluding TIME_EXIT (= Phase-3 cohort) | 30 | 86.7% | 16.76 | wins concentrated in HG=F |

### Forensic table — top 24 winners (PRICE_RESOLVED family)

| symbol | dir | entry | exit | TP | recomp pnl | TP-target pnl | exit_vs_TP dist | exit_reason |
|---|---|---|---|---|---|---|---|---|
| HG=F | LONG | 5.7245 | 6.1210 | 5.9940 | +6.93% | +4.71% | 2.12% over | PRICE_RESOLVED |
| HG=F | LONG | 5.7030 | 6.0600 | 5.9730 | +6.26% | +4.73% | 1.46% over | PRICE_RESOLVED |
| HG=F | LONG | 5.7235 | 6.0750 | 5.9930 | +6.14% | +4.71% | 1.37% over | PRICE_RESOLVED |
| HG=F | LONG | 5.6985 | 6.0400 | 5.9704 | +5.99% | +4.77% | 1.17% over | PRICE_RESOLVED [PRICE_MISMATCH] |
| ... (20 more rows, all HG=F LONG, all PRICE_RESOLVED variants) | | | | | | | | |

**24/24 of the PRICE_RESOLVED winners are HG=F (copper futures) LONG.**

### Findings
1. **Symbol concentration: 100% HG=F in the winning cohort.** (HHI = 1.00.) The "edge" is one symbol on one direction in one regime.
2. **Exit-reason is not TP_HIT — it is `PRICE_RESOLVED` / `PRICE_RESOLVED [PRICE_MISMATCH]` / `PRICE_RESOLVED [RECONCILED_PNL_PCT]`.** This is the resolver fetching a *later* price (avg 8-10 days after entry) and stamping it as the exit when neither TP nor SL was actually hit intrabar.
3. **`exit_price` consistently *exceeds* `take_profit` by 0.03%–2.86%**. A genuine TP_HIT fills at-or-near TP. An exit *past* TP means the resolver pulled a daily close on a day when the symbol had rallied past TP — but with no intrabar verification, we have no guarantee the trade would have actually filled at that high price (the position may have been stopped out hours earlier on a wick the resolver never sees).
4. **No SL_HIT_REPLAY / SL_HIT for the HG=F cohort** — only 3 SL hits in the entire 332-row table, and they're on GC=F and ZC=F. The resolver only finds wins for HG=F because it never checks intrabar SL.
5. **No exit was exactly `take_profit`** — confirming this is *not* a "resolver writes TP as exit" bug. It is a more subtle **end-of-window mark-to-market** bug masquerading as realized PnL.
6. **`tp_fill_method = OBSERVED` on 25/30 of the non-TIME rows** — the resolver claims it observed the fill, but the exit_price beats TP by up to 286 bps, which is mechanically impossible if TP were honored.

### Diagnosis
This is a **path-dependence / resolver-window bug.** The resolver appears to:
1. Wait N days, fetch daily OHLC,
2. If at any later daily-close `(close-entry)/entry > 0` for LONG, mark as WIN with that close as the exit,
3. Never check whether SL was breached intrabar between entry and that "winning" close.

Combined with HG=F's strong 2026 trend (copper up significantly), one-directional LONG signals on a trending symbol *always* look like wins under this resolver. This explains PF=44 in MC and PF=16.76 in the broader cohort.

### Recommendation: **RETIRE** from money-ready cohort.
- Strip from `money_ready_verdict.json` immediately.
- Do NOT re-promote until the resolver is rebuilt with intrabar OHLC replay (per `memory/MEMORY.md` SL-optimization-needs-pricepath rule, proven 2026-05-31).
- COMMODITY class verdict remains **FAIL+INSUFF-N** — this strategy was not the savior.

---

## 2. `prediction_market_consensus` (CRYPTO)

### Numbers
| Window | n | WR | PF | Notes |
|---|---|---|---|---|
| Phase-3 MC report | 89 | 90% | 24.5 | |
| All-time, all rows | 2942 | — | — | 2249 = `TIME_EXIT_MAX_HOLD` (76.4%), 294 still ACTIVE |
| All-time, pnl_pct ≠ NULL | 2471 | 63.1% | 3.25 | 135W / 79L (plus 2257 zero-pnl TIME rows) |
| Excluding TIME_EXIT | 212 | 63.7% | 3.25 | |

### Forensic table — top winners (non-TIME)

| symbol | dir | pnl% | exit_vs_TP | exit_reason | tp_fill_method |
|---|---|---|---|---|---|
| XRPUSDT | LONG | **+80.37%** | 29.8% over TP | `SL_HIT (REPAIRED_PNL_CONTRADIC)` | NOMINAL_TP_LEGACY |
| DOGEUSDT | SHORT | +6.63% | 4.24% past TP | `SL_HIT_RESOLVED [PRICE_MISMATCH]` | OBSERVED |
| DOGEUSDT | SHORT | +6.50% | 4.10% past TP | `SL_HIT_RESOLVED [PRICE_MISMATCH]` | OBSERVED |
| DOGEUSDT | SHORT | +6.34% | 3.94% past TP | `SL_HIT_RESOLVED [PRICE_MISMATCH]` | OBSERVED |
| ... 15 more DOGEUSDT SHORT rows, all `SL_HIT_RESOLVED [PRICE_MISMATCH]`, all positive PnL | | | | | |
| SOL/ETH/BNB | LONG | +2.449% (24× exactly) | 0.05% | `TP_HIT` | OBSERVED |

### Findings
1. **`SL_HIT_RESOLVED` rows with POSITIVE PnL — the smoking gun.** 23 rows tagged "SL_HIT_RESOLVED [PRICE_MISMATCH]" all show POSITIVE pnl, all on DOGEUSDT SHORT, all with exit_price 0.26%–4.24% *past* the TP target. An "SL_HIT" tag with a winning exit_price is a contradiction — the resolver re-stamped the exit but kept the SL_HIT label. This is **data corruption** in the resolver write path.
2. **1 row tagged `SL_HIT (REPAIRED_PNL_CONTRADIC)` with +80.37% PnL on XRPUSDT** — the literal exit_reason admits "REPAIRED_PNL_CONTRADICTION", and it's the largest single contributor to the strategy's gross profit. **This single row inflates PF by ~30%.** It dominates the sum_pnl of the SL_HIT bucket (+80.37 out of +80.37 total in that bucket).
3. **24 rows with exit_price exactly at TP (+2.449% identical to 3 decimals across SOL/ETH/BNB/DOGE)** — looks like a fabricated batch where the resolver assigned the TP price as exit for picks that were never actually verified.
4. **55 wins with `exit_reason = NULL`** (no provenance) summing to +130 of profit. These have no audit trail.
5. **Symbol concentration in the winning cohort: DOGEUSDT 19/30 (63%)** — same single-asset risk pattern.
6. **`tp_fill_method = NOMINAL_TP_LEGACY` on the largest outlier** — legacy nominal-fill is exactly the synthetic-fill mode that should NEVER be in a money-ready cohort.

### Diagnosis
PMC is corrupted on **two independent axes**:
- (a) **Direction-resolver mismatch on DOGEUSDT SHORT** — `SL_HIT_RESOLVED [PRICE_MISMATCH]` consistently flips a stop-loss event into a win when the resolver pulls a later price (post-mortem mark instead of intrabar). PMC keeps the SL label but rewrites the PnL positive. PF gets a free 23-row tailwind.
- (b) **One catastrophic repair-tag row (XRPUSDT +80.37%)** that the resolver itself flagged as "REPAIRED_PNL_CONTRADICTION" — i.e. the resolver KNOWS this row is broken — yet it remains in the cohort with full weight in PF.

Excluding (a) + (b), the residual PF on real TP_HIT/OBSERVED rows is closer to ~1.5–2.0, consistent with the broader CRYPTO sub-T2 verdict (PF 1.14 across the class), not the Phase-3 MC's PF 24.5.

### Recommendation: **RETIRE** from money-ready cohort.
- Strip from `money_ready_verdict.json`.
- Source `prediction_market_agents` and `combined_confidence_strategy` should be flagged in `BLOCKED_SOURCE_SYSTEMS` per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`.

---

## 3. Cross-strategy resolver bug pattern (operator action)

Both audits converge on a single class of bug. **Proposed fix (plain text, NOT shipped as code — operator must review):**

1. **Add an `EXCLUDE_FROM_PERF` flag to any exit_reason containing the substrings**: `REPAIRED`, `PRICE_MISMATCH`, `RECONCILED_PNL_PCT`, `STATUS_STANDARDIZED`, `NOMINAL_TP_LEGACY`. These tags are the resolver's own admission that the row is synthetic.
2. **Hard rule in PF / WR aggregators**: rows where `(direction='LONG' AND exit_price > take_profit AND exit_reason LIKE 'SL_HIT%')` OR `(direction='SHORT' AND exit_price < take_profit AND exit_reason LIKE 'SL_HIT%')` must be **DROPPED**, not counted as wins. The exit_reason and the exit_price contradict each other.
3. **Resolver must use intrabar OHLC replay** (yfinance/Binance 1h or 15m) — per `memory/MEMORY.md` "SL optimization needs price-path" rule, the daily-close walk-forward shortcut is what creates these phantom wins.
4. **`tp_fill_method = NOMINAL_TP_LEGACY` rows must be excluded** from any money-ready cohort. They are by definition synthetic fills.
5. **`exit_reason IS NULL` rows must be excluded** from PF/WR. No provenance = not auditable.

**Estimated impact when fix lands:**
- `cta_golden_cross_200`: PF 16.76 → likely <1.5 (drops all HG=F PRICE_RESOLVED rows; cohort shrinks to ~5 real exits).
- `prediction_market_consensus`: PF 3.25 → likely ~1.3 (drops XRPUSDT outlier and 23 DOGEUSDT SHORT contradictory rows).
- Both fall **below T2 threshold** and would be auto-demoted.

This is a **money-ready blocker** consistent with the 2026-05-31 memory note: "money-ready bottleneck is PLUMBING (wire dormant backtest edges + fix resolvers/mislabels), not strategies/MC."

---

## Artefacts
- Plan: `reports/peer_claude-phase4-suspect-pf-audit_plan_2026-05-31.md`
- Result (this file): `reports/peer_claude-phase4-suspect-pf-audit_result_2026-05-31.md`
- Source DB: `ejaguiar1_stocks.trading_picks` (live, read-only).
