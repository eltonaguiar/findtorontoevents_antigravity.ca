# Backtest / simulation of every proposed fix

Each entry: what was simulated, on what data, the result, and what the result does **not** prove.
Where a simulation is in-sample or retroactive, it says so. Nothing here is a forward test.

---

## 1. Per-class cost gate — retroactive simulation

**Method:** apply the shipped rule (`class mean PnL ≥ 3× round-trip cost, n ≥ 30`) to the 3,500 closed
rows, then recompute the ledger as if only allowed classes had been emitted.

| | n | WR | PF | total pp | mean/trade |
|---|---:|---:|---:|---:|---:|
| Actual ledger | 3,500 | 41.71% | 0.895 | **−617.5** | −0.176% |
| With gate (EQUITY only) | 738 | 47.02% | **1.154** | **+238.3** | +0.323% |
| Removed by gate | 2,762 | 40.30% | 0.804 | −855.8 | −0.310% |

**Emissions removed: 78.9%.**

**What it proves:** 79% of current emission volume is responsible for 100%+ of the loss.
**What it does not prove:** that EQUITY has alpha. This is retroactive and in-sample — the gate is
selecting on the same window it is scored on. Its real value is that it stops the bleeding while the
honest test runs.

Gate verdict per class: EQUITY **ALLOW** (3.23×) · CRYPTO 0.58× · ETF 0.40× · FOREX −1.94× ·
BOND −4.41× · COMMODITY thin-sample — **all BLOCK**.

Evidence: `05_evidence/class_cost_gate_report.txt`.

---

## 2. Stop fills — counterfactual over the whole ledger

**Method:** for every stopped row, recompute PnL as if the fill had happened at the declared stop.
This is the **upper bound** (it assumes no gap and no slippage).

| Class | SL rows | planned risk | realized | ratio | overshoot pp | at-stop would save |
|---|---:|---:|---:|---:|---:|---:|
| CRYPTO | 773 | 1.919% | 2.956% | **1.54×** | +801.4 | **+832.4** |
| COMMODITY | 4 | 1.000% | 2.641% | 2.64× | +6.6 | +6.6 |
| EQUITY | 304 | 4.984% | 4.551% | 0.91× | −131.7 | −131.7 |
| ETF | 262 | 2.953% | 2.257% | 0.76× | −182.4 | −182.4 |
| FOREX | 104 | 1.096% | 0.751% | 0.69× | −35.8 | −35.8 |
| BOND | 21 | 1.384% | 0.868% | 0.63× | −10.8 | −10.8 |

Ledger-wide: stopped trades realized **−4,366.4pp**; filled at the stop they would have realized
**−3,886.8pp** (delta **+479.5pp**, dominated by crypto's +832.4 offset by the others).

**Interpretation:** the "fix" helps crypto by ~832pp and *hurts* every other class, because those
classes' stops were rarely the actual exit. That asymmetry is the whole story of B3 vs B4.

By source system, the crypto leak is concentrated: `kimi_riseoftheclaw` n=174 → **+727.3pp** (94% of
the class leak); `luxalgo_filters` n=371 → +82.8pp; `battleground` n=36 → −22.6pp.

Evidence: `05_evidence/stop_fill_audit.txt`.

---

## 3. Stop fills — real intrabar replay (the fix, measured)

**Method:** `tools/stop_fill_replay.py`, 1h candles from each pick's entry timestamp, deterministic
even-spaced sample. Three models per trade: *recorded* (ledger), *at_stop* (optimistic ceiling),
*gap_aware* (shipped model — fill at stop, or at bar open when the bar gapped through).

### CRYPTO — `kimi_riseoftheclaw`, n=30

| model | n | sum pp | mean pp |
|---|---:|---:|---:|
| recorded | 28 | **−177.90** | −6.354% |
| at_stop (ceiling) | 28 | −42.00 | −1.500% |
| **gap_aware (shipped)** | 28 | **−46.19** | **−1.650%** |

- **28 of 30 stops were genuinely touched**; 2 were not.
- **Gap-through rate: 14.3%** (4 of 28) — roughly 1 in 7 stop fills would have been worse than the stop.
- Gap-aware costs **4.6%** more than the at-stop ceiling. That is the measured price of realism, and it
  confirms at-stop is optimistic rather than conservative.

**Result:** the fix recovers ~74% of these losses (−177.9 → −46.2) and lands just below planned risk
(−1.65% vs −1.50%). Consistent with the earlier estimate: **PF 0.768 → ≈1.00. Breakeven.**

Evidence: `05_evidence/stop_fill_replay_kimi_crypto.json`.

### EQUITY / ETF — the same replay, and a different bug

Numbers below are from the shipped tool (`05_evidence/replay_equity.txt`, `replay_etf.txt`), which is
canonical: an earlier ad-hoc script gave 9 and 12 touched respectively, so treat these as the
reproducible figures.

| Class | sampled | stop touched | **never touched** | recorded pp (touched) | at_stop pp | gap_aware pp | gap-through |
|---|---:|---:|---:|---:|---:|---:|---:|
| EQUITY | 25 | 11 | **14 (56%)** | −63.41 | −50.07 | **−83.62** | 45.5% |
| ETF | 25 | 15 | **10 (40%)** | −35.61 | −40.55 | −41.92 | 20.0% |

**This is the finding of the session.** More than half of sampled non-crypto `SL_HIT` rows are not
stop-outs: the declared level was never reached inside the hold window, yet the row is stamped `SL_HIT`
and carries a real loss.

**A caveat that changes how to read EQUITY:** its `gap_aware` total is *worse* than what was recorded
(−83.6 vs −63.4pp). That is not the model failing — it is the replay detecting a stop touch **after the
position had already closed** (the window is a fixed 5 days and does not know the exit time). For a class
where exits are not stop-driven, replaying fills over a fixed window is the wrong counterfactual. It
strengthens the case that EQUITY's exit semantics are broken; it does not imply the fill fix would hurt
EQUITY, because EQUITY's stops are not what closed those trades.

Three candidate explanations, none yet confirmed:
1. the exit writer closes on its own logic and stamps `SL_HIT` regardless of level;
2. a trailing stop moved the effective level above the recorded `stop_loss`;
3. the ledger's `stop_loss` is a *later* edit (recalculated stop) not the one in force.

**Caveats, stated:** n=25 per class; fixed 5-day 1h-bar window that is not truncated at the actual exit
time (this is what inflates `gap_aware` for EQUITY); yfinance 1h coverage can be sparse for some
tickers. Strong enough to justify an investigation, not strong enough to rewrite the ledger.

Evidence: `05_evidence/stop_fill_replay_equity.json`, `..._etf.json`.

---

## 4. COT contrarian, COMMODITY — pre-registered, **GATE FAILED**

**Method:** `tools/cot_contrarian_backtest.py`. 2,849 weekly CFTC rows / 11 markets (2021-06 → 2026-11)
+ yfinance daily futures. Trailing z of commercial net as % of OI over the prior 156 reports (no
look-ahead); z ≥ +2.5 LONG, ≤ −2.5 SHORT; entry first bar ≥ report_date + 6d (Tue as-of → Fri publish →
Mon entry); costs 10bp. Params chosen on the first 60% of report dates, applied once to the last 40%.

| | value |
|---|---|
| Selected on IS only | z ≥ 2.5, hold 2w (IS n=51, PF 1.309) |
| OOS | **n=30, PF 0.861, mean net −0.45%/trade** |
| Benchmark (equal-weight, same window) | **+0.66%/trade** |
| n ≥ 100 | ❌ FAIL |
| PF ≥ 1.15 | ❌ FAIL |
| slippage < 25% of gross PnL | ❌ FAIL (mean gross ≤ 0) |
| beat benchmark | ❌ FAIL |
| Diagnostic: inverse/momentum direction | OOS n=30, PF 1.087, mean +0.25% |

**Verdict:** no COT edge demonstrated, and the sign points the other way — momentum-following scored
better than contrarian OOS, though still below the gate.

**Not re-fitting:** the `z ≥ 2.0 / 2w` cell had OOS n=109 (the only cell with enough trades). Selecting
it now would be choosing on the test set. It is recorded for a **new pre-registered trial**, not as a
pass.

Evidence: `reports/cot_contrarian_2026-11-14.json`.

---

## 5. What was proposed and deliberately NOT simulated

| Fix | Why no simulation |
|---|---|
| EQUITY vs SPY, 24 months | requires 15 more months of history than the ledger holds — not simulatable from this data |
| Exits-inside-stop (B4) | the mechanism is unknown, so there is nothing to simulate yet; D1 in `../00_common_themes/DEEP_INVESTIGATION.md` is the test |
| Trial registry / FDR | a process control, not a returns model |
| Freshness gates | cannot be simulated; they prevent fabricated inputs |
| Mutual fund allocation | monthly NAV data is not in the repo at all — any simulation would use data I do not have |

---

## Summary table

| Fix | Simulated on | Headline | Confidence | Status |
|---|---|---|---|---|
| Cost gate | 3,500 closed rows | −617.5 → +238.3pp, −78.9% emissions | high (arithmetic) | **shipped** |
| Stop fill (crypto) | 30 real 1h replays + 773 counterfactual | −177.9 → −46.2pp; PF ≈ 1.00 | high | **shipped** |
| Stop semantics (non-crypto) | 50 real 1h replays | 52–64% never touched their stop | medium (n=25/class) | **investigate** |
| COT contrarian | 2,849 COT weeks, 11 markets | OOS PF 0.861, gate failed 4/4 | high | **rejected** |

The two shipped fixes are **loss-avoidance**, not alpha. Nothing in this file demonstrates a profitable
strategy, and no number here should be quoted as if it did.
