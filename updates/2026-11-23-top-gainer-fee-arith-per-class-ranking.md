# 2026-11-23 — Top-gainer reverse-engineering, fee arithmetic, and a per-class ranking

**Objective:** document the top-ranked picks per asset class plus an overall ranking, look at the ML
layer, and test whether daily/weekly top gainers could have been predicted.

**Outcome:** the ranking question turned out to be answerable only in a narrow way, and the top-gainer
question got a measured **no**. Along the way I found five defects — four in my own new code and one
in the dashboard payload.

---

## 1. What was actually delivered

`reports/TOP_PICKS_BY_ASSET_CLASS_2026-11-23.md` — per-class rankings for 10 classes, an overall
evidence-strength ranking, the mutual-fund fee discussion, and the top-gainer result.

The honest shape of it: **"top pick" means best-evidenced choice, which in this estate is almost
always a cost fact, not a return forecast.** The overall ranking is therefore led by *avoiding the
150 bp FX conversion*, then *refusing active mutual funds*, then *holding a broad index ETF as a
vehicle with no alpha claim*, then *T-bills at the 4.32% hurdle*.

The one crisp statistical claim:

> **Zero classes have both n ≥ 100 and PF > 1.**

CRYPTO (n=22,985, PF 0.258), FOREX (n=468, PF 0.175) and EQUITY (n=218, PF 0.606) are the only
classes at n ≥ 100, and all three are below 1.0. Every class above PF 1.0 has n ≤ 35.

---

## 2. The top-gainer answer: REFUTED, six ways

Pre-registered **H-237** and **H-238** in `reports/hypothesis_registry.json` *before* running
(registry rule: "Commit this file BEFORE running any backtest"). Registry went 120 → 122.

118 liquid US large caps, 1,506 bars, 2020-11-23 → 2026-11-20. Benchmark = **the universe's own
mean**, so beta cannot masquerade as skill. Cost charged every rebalance at the measured 0.98 bp.

| Test | n | Excess/rebal | 95% CI lower | Verdict |
|---|---|---|---|---|
| H-237 daily chase (1d→1d) | 1,504 | +1.61 bp | −4.38 bp | REFUTED |
| H-238 weekly swing (5d→5d) | 1,496 | −2.24 bp | −22.75 bp | REFUTED |
| 5d look → 1d hold | 1,500 | +1.00 bp | −4.81 bp | REFUTED |
| 1m look → 1m hold | 1,464 | −22.13 bp | −93.95 bp | REFUTED |
| 3m look → 1m hold | 1,422 | −30.55 bp | −117.61 bp | REFUTED |
| daily top 2% only | 1,504 | +5.43 bp | −5.28 bp | REFUTED |

Jensen alpha: daily chase **+6.48%/yr, CI [−10.41%, +21.27%]**; weekly swing **−3.11%/yr,
CI [−17.10%, +12.53%]**. Neither interval excludes zero.

The universe is names liquid *today*, which **inflates** long-only results — so a FAIL is strong
evidence and a PASS would have been weak.

---

## 3. The bug that nearly published a fake edge

First run: **+880%/yr alpha.** Not an edge — a defect. Four of them:

1. **Look-ahead.** The strategy ranked on day *d*'s return and then captured day *d*'s return.
   Fixed: enter at *d+1*. This alone accounted for the 880%.
2. **Double shift.** `logret.shift(-hold).rolling(hold).sum().shift(-(hold-1))` — the trailing
   shift re-moved the result by `hold-1` and misaligned every `hold>1` test.
3. **Hurdle test rewarding beta.** Comparing raw net return to 4.32% "passed" a book with
   beta 1.24 in a bull market. This is the *same* trap freebuff identified; the deciding field is
   now the beta-free universe-relative CI. Verified: the reported `raw_net_beats_hurdle` was `true`
   for every variant while all six were simultaneously REFUTED.
4. **Hardcoded `min_names = 20`** (found by the new tests). `daily_series` silently returned an
   **empty** series on any universe under 20 names — the "watchdog that lies" pattern. Now
   proportional, and both `run_one` and `daily_series` **raise** rather than return empty.

Regression tests in `tests/test_top_gainer_and_fees.py` (8 passing) pin the forward-return
alignment, the absence of the double shift, the no-look-ahead entry, and the CI-not-raw-return
verdict rule. Re-running after the fixes reproduced `n=1504` and identical numbers, confirming the
refactor was behaviour-preserving.

---

## 4. A provenance failure I caught in my own document

The first draft of the ranking doc cited fee figures ($50 / $1,050 / $4,520 / $18,520 per $100k over
10 years) and attributed them to "reports/ cost-of-record reconciliation".

**That attribution was false.** `grep -rn "18,520|4_520|1_050" reports/ docs/ tools/cost_of_record.py`
returns nothing. The numbers came from session notes — the same defect already logged for the FOREX
7.533 bp figure ("auditable from the COMS bus, not from the repo").

Fixed by making them computable: `tools/fee_arithmetic.py` → `reports/fee_arithmetic_2026-11-23.json`,
with the MER assumptions stated as **ASSUMED illustrative levels, not scraped from fund documents**,
and the method declared as simple `MER × balance × years` (not compounded — deliberately
conservative against my own conclusion).

**And a units bug inside that fix:** I stored `0.105` meaning *0.105%* but consumed it as a decimal,
inflating every dollar figure **100×**. Caught because the printed output (105,000) contradicted
hand arithmetic. Now `mer_rate` in true decimal, with a test pinning the scale
(`test_fee_arithmetic_units_are_decimals_not_percent`).

Verified: 1,050 / 4,520 / 18,520 match hand calculation exactly; ratios **4.3×** and **17.64×**.
The direct-index figure also changed from "≈ $50" to **$0 management fee** (transaction costs are a
separate, excluded bucket).

---

## 5. The dashboard contradicts itself on FOREX

`audit_dashboard/data/dashboard_data.json` (generated `2026-11-22T04:00:19Z`) carries **two** per-class
panels that disagree — and for FOREX they disagree on the **sign**:

| Class | `asset_class_health` | `by_asset_class` (raw) |
|---|---|---|
| FOREX | n=468, WR 33.1%, **PF 0.175** | closed=95, WR 23.2%, **PF 1.64** |
| CRYPTO | n=22,985, WR 41.0%, PF 0.258 | closed=5,044, WR 39.7%, PF 0.86 |

Both FOREX rows are internally consistent (raw: 22×0.96 = 21.1; 73×0.18 = 13.1; PF = 1.61 ✓). They
differ because they measure different things over different denominators — health n (468) is ~5×
raw closed (95).

**Consequence:** I did **not** rank classes on profit factor. The n≥100-and-PF>1 statement survives
both panels. Adopting FOREX's raw 1.64 would have been picking the panel that gives the preferred
answer. Open P1: resolve which panel is authoritative before any capital decision.

---

## 6. Asset classes with no measurement infrastructure at all

Searched the entire 25.8 MB payload:

- **MUTUAL_FUND**: n = 0. No performance measurement exists.
- **OPTIONS**: **zero** occurrences of "OPTION" anywhere. No pipeline, no cost model, no greeks.
  Naming "top 5 options" would be pure invention, so the document declines.
- **MEMECOIN** (`MEME`): n=10, WR 10.0%, PF **0.023**. The only class where the document says
  plainly: no position.

Also corrected again: the **BOND 42.64 bp** figure is claim C-013, a **CRYPTO** delta-neutral
funding-carry round trip. `cost_measurement_20261122.json` has no bond entry. BOND has no measured cost.

---

## 7. Could not load the system vault

The referenced operating docs — `vault/00_System/00_Constitution.md`, `01_Data_Contract.md`,
`03_Measurement_SOP.md`, `04_Operating_Protocol.md`, `05_Banned_Patterns.md`, the three
`MEMORY/*.md`, `LIVE_DASHBOARD.md`, `07_Methodology/08_AI_Coding_Agent_Protocol.md`,
`03_Data/01_DATA_SOURCES.md`, and the two `raw/` reports — **do not exist on this filesystem.**
No `vault/` directory exists in this repo; a filesystem-wide search for each basename returned
nothing.

I did not substitute my own constitution for theirs. The document was written against the rules I
could verify (`CLAUDE.md`, `AGENTS.md`, the registry rule, the tier table). **If those vault files
exist on another host, this work should be re-checked against them.**

---

## 8. Files

| File | Status |
|---|---|
| `reports/TOP_PICKS_BY_ASSET_CLASS_2026-11-23.md` | NEW — the deliverable |
| `tools/top_gainer_test.py` | NEW — backtest, 4 bugs fixed, comments carry the reasons |
| `tools/fee_arithmetic.py` | NEW — makes the fee numbers computable |
| `tests/test_top_gainer_and_fees.py` | NEW — 8 passing |
| `reports/top_gainer_test.json` | NEW artifact |
| `reports/fee_arithmetic_2026-11-23.json` | NEW artifact |
| `reports/hypothesis_registry.json` | H-237, H-238 added and marked REFUTED (n=122) |
| `reports/equity_cost_hml.json` | existing — EQUITY 0.98 bp |
| `reports/hml_result.json` | existing — verdict KILL |

## 9. Verification

```
python3 -m pytest tests/test_top_gainer_and_fees.py -q     -> 8 passed
python3 tools/top_gainer_test.py                           -> 6/6 REFUTED, n=1504
python3 tools/fee_arithmetic.py                            -> 1,050 / 4,520 / 18,520 match hand calc
```

Zero capital sanctioned. Paper only. Not investment advice.
