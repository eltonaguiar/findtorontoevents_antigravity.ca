# Focus decision — where to spend the next 90 days

**The question:** which 1–2 asset classes can get to profitability, if any.

**The answer, in one line:** **EQUITY** is the only class with a measured positive margin and should get
the first real test; **CRYPTO** is the only class where a known, fixable defect hides a possible edge,
so it gets the second slot — but only after the fill fix has forward evidence. Everything else is blocked
by arithmetic, not by effort.

---

## The screen I applied

A class can only be a profitability candidate if all three hold:

1. **It clears its own cost structure** (mean PnL ≥ 3× round-trip cost) — otherwise no signal can save it.
2. **Its loss mechanism is understood** — you cannot fix what you have not diagnosed.
3. **Its sample supports a decision** (n ≥ 100 decisive trades).

| Class | 3× cost | Loss mechanism known? | n | Candidate? |
|---|---|---|---|---|
| **EQUITY** | ✅ 3.23× | ✅ no defect found; 0.91× means stops are respected | 738 | **YES — slot 1** |
| **CRYPTO** | ❌ 0.58× | ✅ late fills, 94% from one system | 1,966 | **YES — slot 2, conditional** |
| ETF | ❌ 0.40× | ✅ cost ≥ edge (267% of PnL) | 567 | no |
| FOREX | ❌ −1.94× | ✅ contaminated + 16pp gap | 187 | no |
| BOND | ❌ −4.41× | ⚠️ exit labels broken | 35 | no |
| COMMODITY | ❌ thin | ✅ 422% cost ratio; COT gate failed today | 7 | no |
| MUTUAL FUND | n/a — not in ledger | n/a | 0 | no (see below) |

Only two classes pass. That is the honest count, and it happens to match the requested "1–2".

---

## Slot 1 — EQUITY: the one class where the money is already positive

**Why first:** mean +0.323% per trade against a 0.30% requirement, losses inside the plan (0.91×), and
the single best-behaved exit bucket in the ledger (TIME_EXIT n=220, WR 61.4%, PF 1.988). It is the only
class where a positive number does not require a fix first.

**Why it might be nothing:** t=1.52, p=0.12; second-half PF fell 1.342 → 0.977. An equity strategy in a
rising market is beta until proven otherwise, and the peer program already falsified three RSI(2)
variants against buy-and-hold (Sharpe 1.50, 1.83, DSR 0.603).

**The test, pre-registered (unchanged from `final_2026_11_14`):**

| Element | Specification |
|---|---|
| Sample | 24 months, n ≥ 500 closed equity trades |
| Benchmark | **SPY total return**, same window — not zero |
| Gate | OOS Sharpe ≥ SPY Sharpe **and** PF ≥ 1.15 |
| Stability | first-half PF ≥ 1.05 **and** second-half PF ≥ 1.05 |
| Kill condition | fails any line → EQUITY is beta, stop emitting it, hold the index |

**Effort:** ~1 week (extend history, wire benchmark, run once). **Cost of being wrong:** low — it is
already allowed to emit, so a negative result only removes emissions that were near break-even.

---

## Slot 2 — CRYPTO: conditional, and only because the defect is known

**Why not first:** the class loses −837.8pp and 98.8% of that is fill slippage. Measuring signal quality
on it today is measuring the executor.

**Why it is still worth the second slot:** it is the only class with (a) a large, diagnosed, fixable
defect and (b) a positive sub-bucket already visible (POSITION horizon: n=33, WR 69.7%, PF 3.180,
+74.4pp). If fills are the whole problem, a real signal may be underneath.

**Order of operations — do not skip step 1:**

1. **Route `kimi_riseoftheclaw` through the intrabar resolver.** Its rows carry `resolver_version = NULL`
   and account for +727.3pp of the +832.4pp leak. This is one system, and it is the largest single PnL
   item in the repo.
2. **Kill CRYPTO SWING emission** (n=243, PF 0.457, −328.6pp — 39% of the class loss).
3. **Forward-test POSITION horizon only**, frozen rules, n ≥ 100, gate PF ≥ 1.3 and WR ≥ 55%.
4. **Re-measure before touching any signal.** The fill fix is expected to reach PF ≈ 1.00 — breakeven,
   not profit. If forward PF after the fix is still < 1.0, crypto is a signal problem too and the class
   should be wound down rather than tuned.

**Effort:** ~1 week for step 1–2, then it is a waiting game (100 forward trades ≈ 6–10 weeks).
**Cost of being wrong:** the fix is worth doing regardless — it turns an unmeasurable class into a
measurable one.

---

## Mutual funds: excluded from the count, and why that is not a dodge

The premise "mutual funds have a high chance of being profitable" is correct and describes the **equity
risk premium**, not a prediction edge. It cannot count as a class the system makes profitable, because
the system contributes nothing to it. It is also structurally untradeable as a pick class: daily NAV, next-NAV
execution, no intraday TP/SL, frequent-trading limits.

Where MF *is* useful is a different job — cheap, passive, low-maintenance exposure. On the subset you
asked about (less money in, lower fees, less maintenance) the ranking is unambiguous and needs no
model: **broad-market index fund → target-date index fund → money market**, screening on expense ratio
≤ 0.20%, no load, no 12b-1, minimum ≤ $1,000, AUM ≥ $1B, turnover ≤ 20%, tracking error ≤ 0.25%. That
is a *procurement* decision, not a research programme.

Full detail, including the trap in "high chance to be profitable" (fee is certain, return is not):
`MUTUAL_FUNDS_SUBSET.md`.

**If you want MF counted anyway**, the honest framing is: "the portfolio holds a low-cost index fund;
the system's job is to not lose money around it." That is a valid goal and a much cheaper one than
finding an edge.

---

## What I would explicitly NOT do in the next 90 days

| Tempting | Why not |
|---|---|
| Tune commodity COT until it passes | it failed all four pre-registered checks today; re-fitting until it passes is exactly the 4-of-170 problem |
| Add mutual funds as a class | 3–6 months, expected Sharpe 0.2–0.5, no intraday measurement possible |
| Mine more strategies | 170 ledgers already sampled the space; 4 pass at 95% vs 8.5 by chance. More trials = more false positives at the current threshold |
| Fix FOREX's 16pp gap with better entries | a 16pp breakeven gap is a structural problem; no entry-timing improvement closes it |
| Turn on more emitting systems | sizing is disabled everywhere for a reason; emission is the loss source |

---

## 90-day sequence

| Weeks | Work | Decision point |
|---|---|---|
| 1 | EQUITY 24-month benchmark test; route kimi to resolver; kill crypto SWING | EQUITY alpha or beta |
| 2–3 | Exit-semantics fix (B4); per-class cost gate in CI; freshness gates (B9) | can we trust the numbers? |
| 4–8 | CRYPTO POSITION forward test begins; commodity momentum-vs-contrarian as a **new pre-registered trial** | does crypto have signal after the fix? |
| 9–13 | Review forward data against gates; publish trial count | scale, or wind down |

**Success at day 90 is not "profitable".** It is: *one class with a pre-registered, benchmark-relative
result and a known trial count.* That is the first point at which "is this profitable?" becomes a
question this repo can answer.
