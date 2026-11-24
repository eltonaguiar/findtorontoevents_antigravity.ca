# Edge screen result — what is worth forward-testing, and what is not

Run 2026-11-22 with `tools/edge_screen.py --min-n 100` over the live `trading_picks` table
(22,219 rows under the scrutiny filter, pnl clipped to [-100, 100]).
**25 cells tested.** Output: `reports/edge_screen_20261122.{json,md}`.

This screen promotes nothing. It ranks cells for the confirmatory stage and names why each fails.

---

## 1 The one genuinely promising cell: `mega_mutation` / CRYPTO

| Test | Result |
|---|---|
| n | 339 |
| WR | 66.96% |
| Gross PF | 3.4958 |
| Net PF at the class cost (9.96bp) | 3.33 |
| Net mean per trade | +2.65% |
| Bootstrap CI lower bound of the mean | 2.1291 |
| Split halves (net mean) | h1 2.2396, h2 2.8656 — stable, and the second half is BETTER |
| Top symbol share | 19.53% (JUPUSDT) — under the 30% cap |
| Micro-hold rows | **0** (but see the caveat: `created_at` is NULL for all 339, so hold time is UNMEASURED) |
| Window | 2026-04-02 to 2026-06-11, 8 symbols, all altcoins |

**Why it looks real rather than beta:** on the same 8 symbols in the same window, every other
strategy pooled averages +0.345%/trade, and the whole CRYPTO class averages +0.084%. `mega_mutation`
averages +2.653%, roughly 8x the pooled figure, with a 67% win rate against roughly 44%.
It is not the market rising.

**Why it is still not investable:**

1. **Stale.** Its window ends 2026-06-11 and only 4 rows exist after that date. Five months of silence.
2. **Batch-resolved.** 339 rows share only 268 distinct `closed_at` timestamps; up to 7 different symbols
   close at the identical second, and 7 symbols share the very first timestamp 2026-04-02 08:12:14.
   That is consistent with a sweeping resolver, not with 339 independent discretionary exits.
3. **No hold time.** `created_at` is NULL on every row, so the micro-hold artifact guard cannot even evaluate it.
4. **Direction missing.** `direction` is empty on all rows, so the "LONG" assumption is inferred from positive prices, not recorded.
5. **8 symbols, 82% of profit in 3 of them.** JUPUSDT +281.86, ENAUSDT +206.00, WIFUSDT +200.54 of +899.40 total.
6. **In-sample only.** It was found *and* "validated" on the same window by the mid-date split.

Verdict: **the strongest signal in the system, and it is a lead, not a result.** It is already
pre-registered as `POD-MEGA-MUTATION-CANDIDATE` (H-2026-11-22-01) in observe mode.

---

## 2 The other two ADVANCE cells, and why they do not survive a second look

| Cell | n | Net PF | CI-LB | Micro-hold | Re-check |
|---|---|---|---|---|---|
| `battleground_luxalgo` / CRYPTO | 150 | 2.6091 | 0.5143 | 18 rows | Net PF on real rows only 2.5498, WR 52.3% — survives, but weaker |
| `alpha_engine` / COMMODITY | 150 | 2.515 | 0.4096 | **61 rows (41%)** | **Fails**: on real rows net PnL is -49.72 (PF 0.5487, WR 23.0%), while the 61 micro-hold rows contributed +268.75 |

So of 3 ADVANCE cells, one is real-but-stale, one is real-but-weaker, and one is an artifact whose entire
positive result comes from sub-minute rows. That is the expected hit rate for a first screen, and it is
exactly why the screen must precede any money.

---

## 3 The honest answer to "is there something worthy of money yet"

**Not yet.** Nothing clears the bar today. The ranking for what to put forward first:

1. `mega_mutation` / CRYPTO-candidate (needs fresh rows and a real resolver, not more analysis)
2. `battleground_luxalgo` / CRYPTO (needs n to grow and micro-hold purged)
3. Nothing in ETF, BOND or MUTUAL_FUND: ETF's `/audit` PF 1.8752 is a 100.28x daily-vs-intrabar artifact,
   BOND is 2 trades, MUTUAL_FUND has 0 rows.

A mutual fund or ETF is the natural *instrument* for a real edge because it has the cheapest execution and no
borrow cost, but the evidence does not presently show an ETF edge to put in one. Choosing the instrument
before the edge exists is how people lose money politely.

---

## 4 What would make `mega_mutation` investable

- Fresh forward rows after 2026-11-22 with recorded `created_at`, `direction`, and per-trade entry/exit.
- Resolution by the intrabar resolver, not a batch sweep.
- n >= 100 forward rows, net PF CI-LB > 1.0, 2x-cost still positive.
- Benchmarked against buy-and-hold of the same 8 symbols over the same forward window.

Until then it stays a CANDIDATE at most, exactly as the tribunal caps it.

---

## Provenance

- model: none (curator-written from the screen output and live read-only SQL)
- screen: `tools/edge_screen.py --min-n 100`, 2,000 seeded bootstrap resamples, seed 42
- DB: `ejaguiar1_stocks` on `mysql.50webs.com`, read-only, 52,608 closed rows, measured 2026-11-22
- delegated review D1: `UNMEASURED` — the `diverse5` preset's model names are stale (HTTP 410/404/401);
  of explicit providers only cloudflare answered, and its reply was generic and did not engage the evidence
