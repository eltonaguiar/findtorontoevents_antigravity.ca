# 2026-10-22 — Mutual-Fund Winner Proof: split-half + walk-forward backtest + page

**NOT FINANCIAL ADVICE.** Research and education only. Past performance does not predict
future results. This document, the tool, and the page describe how we tested a theory —
they are not a recommendation.

## What the user asked

1. Dig deeper for profitability per asset class — "there are obviously some traders who
   still win in every market".
2. Set up the mutual-fund tracking page with proper filters and explain which mutual funds
   are most trustworthy based on top-notch stats; research mutual funds specifically and
   "prove" the theory of what makes a mutual fund a winner.
3. Backtest those winner criteria and look for true winners that stand the test of time.
4. Try free ETFs and a comparison — is a lesser-known fund a shocking secret winner vs the
   paid ones?
5. Be extremely clear on methodology (ELI5, but provable — assume a quant SME reviews the
   codebase and chat logs).
6. Every page touched must say "Not financial advice".
7. Note Grok's finding: after ~150 strategies across every asset class, none beats a cheap
   index fund after fees and risk (sector rotation was the closest, 9.5%/yr vs SPY 8.3%,
   still only a CANDIDATE).

## Part 1 — Per-asset-class edge dig (live DB, 108,488 at_raw_picks rows)

### What was broken / why a new method was needed

`pf_registry.json::by_asset_class_strategy_policy_clean_net` flags every n≥15 strategy
cohort as `is_single_source_artifact` — because `single_source_pct == 1.0` for all of them
(a strategy is by definition emitted by one system). That flag therefore separates nothing
at strategy level. The registry-based hunt returned an empty "clean" set.

### Method

Queried `at_raw_picks` directly (pnl_pct not null, closed, non-open) and grouped by
(asset_class, source_system, strategy), computing:

- **`n / distinct_close_days` ratio** — the real artifact detector. QUBT/IONQ/AAPL-style
  frozen-exit stamping shows 100–1800 rows on 1–2 days; genuine independent trades show
  n ≤ 3 × distinct days.
- Day-independent cohorts only (`n <= 3*ddays`, n≥15): 55 of 2,576 survive.
- On the top survivors: half-split PF (first vs second half), PF excluding the best trade,
  2,000-sample bootstrap CI on PF, recency (last 90d), cost stress (0.05/0.10/0.20%
  round-trip), exit-reason mix, symbol concentration.

### Findings

| Cohort | n | PF | Bootstrap CI | H1/H2 PF | Verdict |
|---|---|---|---|---|---|
| CRYPTO `high_trust_momentum` (AlphaEngine) | 211 | 1.80 | [1.31, 2.54] | 1.98 / 1.66 | **only survivor** — CI low > 1, halves stable, 90d PF 1.85, PF 1.52 after 0.20% costs, 12 symbols, exits 84 TIME/69 TP/58 SL (honest mix) |
| FUTURES `seasonal_momentum` | 103 | 2.80 | [1.82, 4.49] | **8.16 / 0.89** | DEAD — edge gone in second half (regime decay) |
| BOND `bond_yield_curve_slope` | 78 | 1.67 | [1.01, 2.67] | 0.97 / 2.51 | borderline; early-half losing |
| CRYPTO `rapid_trend_only_mut` | 112 | 1.96 | [1.12, 3.46] | 2.57 / 1.18 | decaying, watch only |
| FUTURES `commodity_rsi_divergence` | 67 | 1.51 | [0.86, 2.68] | — | CI includes 1 — fail |

Class-level reality check (policy-clean): every class except ETF (n=16) still has PF < 1
at the whole-class level. The honest statement: **edges exist only in specific
strategy×emitter cohorts, not at asset-class level; one crypto momentum cohort survives
every standard fluke test so far (still needs daily mark-to-market equity-curve MDD — the
Grok/Copilot closed-trade-MDD flaw — before any promotion claim).**

## Part 2 — Winner theory: split-half proof (37 rated funds, NAV cache 2016→2026)

Split each fund's history in half; rank features on H1 only; measure H2 outcomes:

| H1 predictor | → H2 CAGR (Spearman) | → H2 Sharpe | → H2 MDD |
|---|---|---|---|
| **expense ratio** | **−0.378** | −0.257 | −0.276 |
| sharpe (H1) | +0.128 | +0.151 | +0.397 |
| max drawdown (H1) | −0.054 | +0.003 | +0.577 |
| past CAGR (H1) | +0.671 | +0.470 | −0.345 |

- Cheapest ER tercile H2 CAGR **+9.2%/yr** vs dearest tercile **+5.0%/yr** (fees differ by
  only ~0.05pp — the gap is mostly *what kind of fund is cheap*: index vs closet-active).
- Top H2 performers: SWLGX 20.5%, SWLVX 15.1%, SWMCX 13.2%, FXAIX 13.0%, SWPPX 12.9% —
  all index funds at 0.01–0.04% ER.
- Past smoothness does not predict future returns (ρ ≈ −0.05) but does predict future
  drawdowns (ρ = +0.58): low-drawdown yesterday means low-drawdown tomorrow, *not* higher
  returns.

**Winner theory (as tested): cheap fees + index structure → better risk-adjusted forward
returns; past Sharpe/low-drawdown selection does not create forward outperformance.**

## Part 3 — Walk-forward backtest (new tool + tests)

### Files

- **New:** `tools/mf_walkforward_backtest.py` — fetch (71 funds: 37 rated + FZROX/FNILX/
  FZILX zero-fee + SPY/VOO/IVV/SPLG/SCHB/ITOT/SPTM/VV/VXUS/IXUS/BND/AGG/SCHD/AVUV low-fee
  ETFs + FCNTX/DODGX/AGTHX/TRBCX/FLPSX/FOCPX long-history active funds + 12 Canadian ETFs
  incl. XEQT/VBAL/VFV), walk-forward selection, statistics, style-adjusted check.
- **New:** `tests/test_mf_walkforward_backtest.py` — 5 tests, all passing:
  no-lookahead (features identical when future rows are flipped to a crash), forward-CAGR
  refusal on insufficient data, rule-selection expectations, non-overlapping rebalance
  dates, pct-rank/t-test/bootstrap sanity.
- **New:** `audit_dashboard/data/mf_backtest_cache/` (NAV CSVs + `mf_backtest_universe.json`)
  and `audit_dashboard/data/mf_walkforward_results.json` (results, reproducible).

### Methodology (ELI5 + technical)

ELI5: Every December, hide the future. Line up funds using only what you could have known
— how cheap, how smooth the last 3 years, how last year went — pick top 3 per rule, then
see what really happened next 1/3/5 years versus just buying the index fund. Fees are
subtracted. Years never overlap, so one lucky decade can't be counted twice.

Technical: trailing features sliced to rows ≤ t (unit-tested against leakage); rebalance
dates spaced h years apart for horizon h (non-overlapping ⇒ valid paired t); forward CAGR
net of ER; paired t + seeded 10,000-sample bootstrap CI; style-adjusted follow-up vs
same-style index to separate skill from beta.

### Results (US, benchmark SPY, 1994–2024; 31×1y, 10×3y, 6×5y windows, net of fees)

| Rule | 1y excess | 3y excess | 5y excess | Verdict |
|---|---|---|---|---|
| cheapest 3 | −0.9% | −1.0% | −1.0% | ties index (CI includes 0) |
| composite | −0.5% | −2.5% | −2.8% | ties at 1y, drifts behind |
| momentum12m | −1.1% | −4.6% | −4.7% | fails |
| sharpe3y | −5.3% | −5.2% | −6.9% | significantly worse (t≈−2.1, CI excludes 0) |
| lowdd3y | −6.5% | −6.4% | −5.9% | worst rule |

**No rule beats the plain index fund on average.** This independently reproduces Grok's
"~150 strategies, none beats a cheap index fund" conclusion from a different data path.

Canada (benchmark XEQT.TO, 7×1y windows): no rule wins either; cheap rule loses (−3.0%)
because the all-in-one beat its corner pieces in this window.

### Secret-winner hunt (lesser-known vs paid)

- Raw: FSPGX +5.6%/yr, SWLGX +5.1%/yr vs SPY — **style-adjusted vs VIGAX: +0.2% / −0.1% ⇒
  growth beta, not skill** (the trap the test exists to catch).
- **FOCPX (Fidelity OTC, active, 0.78% ER): +4.0%/yr raw vs SPY over 31 windows, stable
  H1 +3.6 / H2 +4.5, and +2.2%/yr vs style-matched VIGAX over 25 windows (win 56%).
  The only fund whose edge survives style adjustment.** Caveats on the page: worst relative
  years −23.5% (1999), −22.2% (1996); concentrated growth; one fund, one era → CANDIDATE,
  not proven.
- Zero-fee clones (FZROX/FNILX) beat SPY 71–100% of 1y windows — but they track the same
  index; the "win" is the fee difference, which is exactly the cheap-index thesis.

## Part 4 — Page updates

- `audit_dashboard/mutual-funds.html`:
  - Header disclaimer: "⚠ NOT FINANCIAL ADVICE — research and education only…".
  - New section "What makes a mutual fund a WINNER? — walk-forward backtest": ELI5
    methodology, technical reproducibility (`python3 tools/mf_walkforward_backtest.py`),
    results table, split-half proof, style-adjusted secret-winner findings, bottom line.
  - Existing tier/category/index filters unchanged; verified intact.
- **Disclaimer sweep of every page touched in this conversation** — added where missing:
  - `ghcopilot_paper.html` (1), `poolside_paper.html` (1),
    `inception_paper_trading.html` (1), `mutual-funds.html` (2 — header + section end).
  - Already had it: `freebuff_buffy_proven_picks.html` (3), `opencode_paper_trading.html`
    (1), `index.html`/`template.html` (6 each).

## Part 5 — Grok's note recorded (user request)

Grok's cross-agent conclusion, on record: after testing ~150 strategies across every asset
class, **none beats a cheap index fund after fees and risk** — the real winner is the
boring low-fee all-in-one fund (XEQT from $1 at Wealthsimple TFSA; VBAL if a 30% drop
would make you panic-sell; TD e-Series $100-min mutual funds for the up-to-$1,000 tier;
no true 0% fund in Canada — Fidelity ZERO is US-only). Sector rotation was the closest
strategy (9.5%/yr vs SPY 8.3%, less than half the worst drop) and remains a CANDIDATE for
paper only. Our independent walk-forward backtest (Part 3) reaches the same conclusion by
a different method. Also relevant from the same note: the repo's 15-ETF dataset is clean
(no missing days/gaps/stale prices; the >15% daily moves are real 2008/2020 events), no
repo ETF strategy passed the gates (best: adx-trend-scout, 36 trades, lower confidence
bound 0.61), and USO lost 98% / DBC, SLV fell 76% over the period.

## Verification

- `python3 tests/test_mf_walkforward_backtest.py` → **PASS (5/5)**.
- `py_compile` clean on `tools/mf_walkforward_backtest.py`.
- Full run `--universe all` writes `mf_walkforward_results.json`; US 31×1y windows
  1994–2024; CA 7×1y windows; style-adjusted block present for both regions.
- Local server (`tools/serve_local.py`): page HTTP 200, both JSONs HTTP 200, DOM sanity
  (divs balanced 19/19, 2 tables balanced, filter element IDs present, ends `</html>`,
  disclaimer present ×2), "walk-forward backtest" and FOCPX finding present in served HTML.
- ER unit trap regression: fetch normalizes Yahoo's mixed units
  (`netExpenseRatio`=percent, `expenseRatio`=fraction) to decimal fractions with a >5%
  sanity clamp — first run charged funds 100× real fees and produced fake −24%/yr rule
  results; fixed and re-fetched (71 funds) before all reported numbers.

## What NOT to claim

- Do not call FOCPX (or anything) a "winner" — one fund, one style, needs out-of-sample /
  forward confirmation; the page labels it CANDIDATE explicitly.
- Do not claim any selection rule beats the index — the data says the opposite.
- Do not drop the disclaimers when editing these pages.
