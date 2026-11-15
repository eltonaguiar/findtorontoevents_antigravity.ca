# Asset-class triage and the "10 lottery tickets" question — 2026-11-15

Every number here was computed in this session from
`audit_dashboard/data/dashboard_data.json` (`generated_at 2026-10-19T19:40:11Z`,
3,500 closed picks). Reproduce with the script at the bottom. No number is from a report,
and nothing here is benchmark-adjusted yet — that is stated where it matters.

## 1. What the closed ledger actually says, per class

Per-trade `pnl_pct`, equal weight, **gross** of fees and slippage:

| Class | n | mean % | median % | WR | PF | Power |
|---|---:|---:|---:|---:|---:|---|
| CRYPTO | 2,070 | +0.54 | −0.88 | 46.1% | 1.31 | adequate |
| EQUITY | 690 | +0.46 | −0.18 | 47.5% | 1.23 | adequate |
| ETF | 503 | +0.08 | −0.68 | 44.3% | 1.07 | adequate |
| FOREX | 199 | −0.13 | 0.00 | 32.2% | 0.66 | adequate |
| BOND | 28 | −0.23 | −0.76 | 35.7% | 0.56 | **underpowered** |
| COMMODITY | 9 | +0.03 | 0.00 | 44.4% | 1.03 | **underpowered** |
| FUTURES | 1 | −0.47 | −0.47 | 0.0% | 0.00 | **underpowered** |

Read this table with two corrections before drawing any conclusion:

1. **A mean above zero with a median below zero is a fat-tail profile, not an edge.** CRYPTO
   (+0.54 mean, −0.88 median) and EQUITY (+0.46, −0.18) both win less than half their trades
   and are carried by a minority of large winners. PF 1.31 therefore measures the size of the
   tail, and it is the first thing that disappears when you require a positive median or a
   cost haircut.
2. **PF ignores the benchmark.** A +0.46% equity trade in a month SPY returned +1% is a losing
   trade. None of the rows above are excess-adjusted. The repo now has the machinery to do it
   (`tools/pick_excess.py`, and the ledger's own `excess_pp` leg); it has not been applied to
   this table.

## 2. Ranking, by what is actually measurable

**Only CRYPTO and EQUITY are candidates at all**, and only because both have n ≥ 690. ETF is
the null result (PF 1.07 on n=503 is what "no edge" looks like at that sample size). FOREX is
not a candidate: PF 0.66, WR 32.2%, n=199 is enough evidence to stop, not to tune.

BOND — the class most likely to work in theory (carry, duration, low correlation) — has 28
closed picks, PF 0.56. That is not evidence against bonds; it is evidence that **this system
has not traded bonds**. Any bond programme has to start from zero with real duration data
(yield-curve history, TLT/IEF/SHY, rate expectations), not from these 28 rows.

COMMODITY (9) and FUTURES (1) are unmeasurable. Any claim about them, positive or negative, is
currently unsupported by this ledger.

## 3. The "10 penny stocks, one skyrockets" test — measured, and it fails

Every closed pick with an entry price below $5 (n = 1,360):

| Threshold | Count | Share | Expected winners in a 10-pick basket |
|---|---:|---:|---:|
| ≥ +50% | 4 | 0.3% | 0.03 |
| ≥ +100% | 2 | 0.1% | 0.01 |
| ≥ +200% | 0 | 0.0% | 0.00 |
| ≥ +500% | 0 | 0.0% | 0.00 |

Best +100.0%, worst −24.6%, mean +0.80%, **median −1.00%**.

The $2–5 band is worse: n=93, mean +0.88%, median −1.40%, P(≥+100%) = 0%, best +23%.

### Why the thesis fails here specifically

- **The upside is capped and the downside is not.** Zero of 1,360 sub-$5 picks reached +200%;
  the best possible outcome observed is +100% (a take-profit at a double). Losers are cut
  around −25%. A lottery needs a fat right tail; this pipeline's exit rules truncate exactly
  the tail the thesis depends on.
- **The positive mean is entirely the top decile.** Top 10% of sub-$5 picks average +13.1%
  and contribute ~1,780 percentage points against a total of +1,084 — i.e. the other 90% net
  negative. That is the same fat-tail arithmetic as the class table, not a lottery.
- **Basket arithmetic.** To make "1 in 10 doubles" pay, that single double must cover nine
  losers at −25% (−225%): a +100% winner covers only 400% of a 25% loss... before costs, and
  with P(double) = 0.1% the expected number of doubles in a 10-pick basket is 0.01, so the
  strategy is nine-to-one against even reaching its own premise.

**Verdict: REJECT as stated.** A lottery strategy needs a right tail that is (a) empirically
present at a usable rate and (b) not truncated by the exit rule. Neither holds. If a
high-variance sleeve is wanted, it must be re-specified as: universe of liquid sub-$5 names
with a hard rule to let winners run (no TP below +300%), position size where a total loss is
survivable, and ≥ 300 trades before judging — then measured on excess, not gross.

## 4. What to do next, in order

1. **Apply the benchmark leg to this table** before any allocation decision. Recompute the
   class table on `excess_pp` (SPY for EQUITY/ETF, BTC-USD for CRYPTO). If CRYPTO's +0.54%
   gross is +0.1% excess, the class is dead regardless of PF.
2. **Kill FOREX allocation.** PF 0.66 at n=199 with 32% WR is a decision, not a research
   question. The one thing that would reopen it is a strategy that has never traded.
3. **Stop reporting BOND/COMMODITY/FUTURES numbers.** With n<30 the honest label is
   INSTRUMENTED — NOT MEASURED. Bond research starts fresh with duration data.
4. **Test the only untested structural hypothesis cheaply:** EQUITY and ETF both look like
   fat-tail profiles; if the winners are concentrated in a few dates, the "edge" is one
   market episode and clustered-t on `(entry_day, exit_day)` will say so immediately.
5. Use `reports/quant_audit/STRATEGY_SHORTLIST_TEMPLATE.md` for whatever survives step 4 —
   it will not let a fat-tail PF through as PROVEN.

## 5. Reproduce

```bash
python3 - <<'PY'
import json, statistics as st
d = json.load(open("audit_dashboard/data/dashboard_data.json"))
closed = (d.get("picks") or {}).get("recent_closed") or []
by = {}
for p in closed:
    try: v = float(p.get("pnl_pct"))
    except (TypeError, ValueError): continue
    by.setdefault((p.get("asset_class") or "?").upper(), []).append(v)
for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    g = sum(x for x in v if x > 0); l = -sum(x for x in v if x < 0)
    print(k, len(v), round(st.mean(v), 2), round(st.median(v), 2),
          round(sum(1 for x in v if x > 0)/len(v)*100, 1),
          round(g/l, 2) if l else "inf")
PY
```

## 6. Limits of this note

- Gross of costs. Costs of 6 bps/side are small per trade but the median trade is −1%, so a
  cost haircut moves the median, not just the mean.
- No benchmark adjustment (stated above, not hidden).
- Payload snapshot is 2026-10-19; the ledger has moved since. Re-run before acting.
- No regime split and no cluster count yet — step 4 is exactly that work.
