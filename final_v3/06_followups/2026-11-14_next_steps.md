# Follow-ups from the 2026-11-14 review — results

Three experiments run after the `final_v3` package was delivered. Two changed a
conclusion; one refuted a number I had published the hour before.

| # | Follow-up | Result |
|---|---|---|
| 1 | Route `kimi_riseoftheclaw` exits through the intrabar fill model | **Shipped.** Real defect confirmed. My earlier "+727.3pp crypto leak" was **overstated ~10×** — the true correction is **+67.5pp** |
| 2 | Settle B4 (non-crypto `SL_HIT` rows that never touched their stop) | **Settled.** 11/14 EQUITY and 12/13 ETF never-touched rows exited at a *different level*. Exit taxonomy, not fill |
| 3 | EQUITY vs SPY, pre-registered gate | **FAIL — `NO_ALPHA_BETA`.** t=1.05, mean excess +0.21%, median excess **−0.57%** |

---

## 1. kimi exits — the defect is real, my headline was not

### What was wrong

`KIMI_RISEOFTHECLAW/live_scanner.py` fires its ATR stop when the **polled** price
has already crossed it, then booked P&L at that polled price:

```python
elif curr <= _pick_stop:
    exit_reason = f"STOP_LOSS {ret*100:.1f}% (ATR stop={_pick_stop:.4f})"
...
gross_pnl = alloc * ret          # ret is measured from `curr`, not the stop
```

A resting stop order cannot fill at "wherever the market had drifted to by the
time the cron ran". Measured over the 815 kimi `SL_HIT` rows in the live payload:

- **0 of 815** were booked at the stop they exited against
- 778 carry `STOP_LOSS -X% (ATR stop=P)`; **P never equals `exit_price`** (0/778)
- P differs from the row's own `stop_loss` field by a **median 1.69%** (p90 3.79%)

That last line is the important one. Three different prices describe one exit
(stop field, ATR stop in the reason text, booked exit). Any metric computed from
`stop_loss` is measuring a number the trade never used.

### What shipped

`audit_trail/stop_fill.py::exit_fill_for_stop()` — pure, tested fill model:
fill at the stop; at the bar open when the bar gapped through it. The scanner now
books at that fill and records provenance:

```python
"exitPrice":      fill,          # what we booked
"polledPrice":    curr,          # what we declined to book at
"stopUsed":       _pick_stop,    # the stop the exit actually used
"targetUsed":     _pick_target,
"exitPriceBasis": "stop" | "gap_through" | "target" | "polled",
```

`TAKE_PROFIT` was fixed in the same pass: it booked at the polled price too, so a
poll that ran past the target credited a gain **beyond** the limit order. It now
fills at the target. Fixing only the stop side would have made the comparison
lopsided against the fix.

### Re-measure: what it is actually worth

Full population, using the **executed** ATR stop from the reason string (no
network — this is arithmetic on the ledger), implied risk ≤ 25%:

| class | rows fixed | recorded | at-stop | delta |
|---|---:|---:|---:|---:|
| CRYPTO | 152 | −858.4 | −790.9 | **+67.5** |
| EQUITY | 302 | −1380.2 | −1131.8 | +248.4 |
| ETF | 256 | −584.9 | −499.9 | +85.0 |
| FOREX | 49 | −21.5 | −16.2 | +5.2 |
| BOND | 18 | −16.0 | −12.3 | +3.7 |

Class totals after correction:

| class | recorded | corrected |
|---|---:|---:|
| CRYPTO | −837.8 | −770.3 |
| EQUITY | +238.3 | +486.7 |
| ETF | +22.9 | +107.9 |
| FOREX | −29.0 | −23.8 |
| BOND | −7.7 | −4.0 |

**Crypto is still −770pp.** The fix moves it from catastrophic to very bad; PF
0.768 → roughly 0.80, not the ~1.00 the earlier estimate implied. My
`+727.3pp` figure came from differencing against the drifted `stop_loss` field,
i.e. it measured the field mismatch, not the fill. Recording that here rather
than letting the bigger number stand.

### One row had to be thrown away — and it is a finding

`ADA-USD`: entry `0.201105`, `exit_reason_raw = "STOP_LOSS -5.1% (ATR stop=92.2514)"`.
An ATR stop of 92 on a $0.20 asset is another symbol's stop written into ADA's
exit reason — implied risk 45,772%. Left in, this **single row** would have
injected +45,772pp of fake "correction" into the crypto total.

Logged as **B14: cross-symbol stop contamination** in `live_scanner.py`'s exit
path. Rate is low (1 of 153 crypto ATR rows, 0.65%) but the blast radius on any
aggregate is unbounded, which is the argument for the implied-risk sanity bound
being part of the measurement, not an afterthought.

---

## 2. B4 — settled: the exit *label* is wrong, not the exit *price*

Replayed with a new `--truncate-at-exit` flag, which drops candles printed after
the pick's recorded exit. Without it, "stop was touched" can be manufactured by
price action that happened while we were already flat.

| class | sampled | stop touched | never touched | of the never-touched: different level | never reached at all |
|---|---:|---:|---:|---:|---:|
| EQUITY | 25 | 11 | 14 | **11** | 3 |
| ETF | 25 | 12 | 13 | **12** | 1 |

So the never-touched rows overwhelmingly **did** hit a level — just not the one
recorded. `exit_reason = SL_HIT` in these classes names the wrong mechanism:
these are trailing-stop / target / max-hold exits mislabelled as stop-outs. A
small remainder (3 + 1) never traded at their recorded exit price at all, which
is a data-integrity problem rather than a labelling one.

PnL over the touched subset only:

| class | recorded | at_stop | gap_aware |
|---|---:|---:|---:|
| EQUITY | −63.41 | −50.07 | **−83.62** |
| ETF | −30.45 | −31.55 | −32.11 |

**Gap-aware filling makes EQUITY worse than the recorded number** (−83.62 vs
−63.41), on a 45.5% gap-through rate. Two consequences:

1. The resolve-the-stop-fill fix must **not** be extended to non-crypto exits.
   44–52% of those rows never touched their stop, so a stop-fill model is being
   applied to trades that did not stop out. That is fitting a model to a label
   that is wrong.
2. EQUITY's work item is the exit taxonomy (B4), not the fill model. Until
   `exit_reason` means what it says, every R-multiple, breakeven-WR and PF number
   for EQUITY/ETF is computed against the wrong denominator.

Caveat: n=25 per class, evenly spaced, 1h bars. Directionally clear (11/14 and
12/13 is not a coin flip) but not a census.

---

## 3. EQUITY vs SPY — the gate failed, and it decides the focus question

Pre-registered before the file was run (`tools/equity_vs_spy.py`, gate in the
module docstring): PASS requires n ≥ 100, mean excess > 0, t ≥ 2.0, and mean
excess > class round-trip cost. Each pick is paired with SPY's return over **that
pick's own holding window**, adjusted closes (dividends included), shorts
benchmarked against −SPY.

| metric | value |
|---|---:|
| usable pairs | 738 |
| mean hold | 4.37 days |
| strategy mean PnL | +0.3230% |
| SPY same window | +0.1138% |
| **mean excess** | **+0.2092%** |
| **median excess** | **−0.5726%** |
| t-statistic | **1.05** |
| beat-SPY rate | 45.53% |

| gate | result |
|---|---|
| G1 n ≥ 100 | PASS (738) |
| G2 mean excess > 0 | PASS (+0.21%) |
| G3 t ≥ 2.0 | **FAIL (1.05)** |
| G4 excess > cost | PASS (+0.21 > 0.10) |
| **VERDICT** | **NO_ALPHA_BETA** |

The median pick **loses** 0.57% to SPY while the mean gains 0.21%: a right tail
carrying a negative-median distribution. 54% of picks underperform simply holding
the index.

EQUITY passed the per-class cost gate at 3.23× and still cannot beat the
benchmark. That inverts the focus decision in `03_focus/DECISION.md` — the one
class clearing its costs is not an edge, it is beta with extra steps. See the
dated revision appended to that file.

---

## What this means for the plan

- **Stop-fill work is done and correctly sized.** It repairs measurement; it does
  not create profit. Crypto goes from −838pp to −770pp, still the worst class.
- **The binding constraint is exit taxonomy (B4) + B14 contamination**, not fills.
- **No asset class has demonstrated benchmark-relative alpha.** EQUITY is the
  closest and it is beta. The honest status of the system after today is:
  *measurement improved, edge unproven*.
- The mutual-fund subset in `03_focus/MUTUAL_FUNDS_SUBSET.md` looks stronger, not
  weaker, after this test: if the equity picks are beta, a low-cost index fund
  delivers the same exposure without the −0.57% median shortfall or the fees.

## Reproduce

```bash
python3 tools/equity_vs_spy.py --payload /tmp/peercheck/dashboard_payload.json \
    --json final_v3/05_evidence/equity_vs_spy.json

python3 tools/stop_fill_replay.py --payload /tmp/peercheck/dashboard_payload.json \
    --class EQUITY --limit 25 --truncate-at-exit \
    --json final_v3/05_evidence/replay_equity_truncated.json

python3 -m pytest tests/test_kimi_exit_fill.py tests/test_stop_fill.py \
    tests/test_per_class_cost_gate.py tests/test_cot_contrarian_backtest.py -q   # 66 passed
```

Evidence: `05_evidence/{equity_vs_spy,kimi_atr_stop_correction,replay_equity_truncated,replay_etf_truncated}.json`
