# Picks NOW — Quality Audit (2026-06-09)

**Auditor:** read-only quality auditor (no DB access; verdicts from JSON + code + yfinance spot-checks)
**Backing data:** `audit_dashboard/data/picks_now.json` (generated_at `2026-06-08T18:48:05Z`, 20 picks, all EQUITY)
**Generator:** `tools/picks_now_professional.py`
**Page:** `audit_dashboard/picks-now.html`

---

## OVERALL VERDICT: **NOT-TRUSTWORTHY** (display-blocking)

The Picks NOW surface is currently **not safe to show users as-is**. There is no
fabricated *price/return* data (yfinance spot-checks match), and the "loser-after-loser
coin-flip" risk is partly mitigated by the negative-expectancy guard in code — but two
**display-blocking** bugs are live on the page right now:

1. A **dividend-yield double-multiply** that prints physically impossible yields
   (GOOGL **24%**, SBUX **260%**, PLD **296%**) to users. The page tooltip literally
   tells the user "Above 5% may signal risk" next to a "296.00%" chip. This is the
   single most embarrassing thing on the page.
2. The **same div bug corrupts the ranking**: 14 of 20 picks received a wrongful +5
   composite-score bonus; with correct yields **all 14 lose it**, so the displayed
   rank order is contaminated.

Plus a visible **duplicate AMZN** at rank #1/#2, three **STRONG_BUY picks whose own
analyst target is BELOW current price** (AMD, DDOG, MU — MU target is -22%), and a
**"safest" bucket** containing a negative-Sharpe no-data crypto (ARB-USD WATCH).

A peer agent is already mid-fix in the working tree (`git diff tools/picks_now_professional.py`),
but their patch only covers the FMP fallback path and **does not fix the primary
yfinance div bug or the AMZN dup that produced the live JSON.**

---

## RANKED ISSUES

| # | Severity | Pick(s) / Field | Evidence | Suggested fix |
|---|----------|-----------------|----------|---------------|
| 1 | **CRITICAL** | All dividend payers / `div_yield_pct` | `tools/picks_now_professional.py:492-494` does `div_yield = info.get("dividendYield"); if div_yield: div_yield *= 100`. yfinance now returns the yield **already as a percent** (spot-check: GOOGL raw `0.24`, SBUX `2.62`, PLD `3.0`). The `*100` produces GOOGL **24.0%**, SBUX **260.0%**, PLD **296.0%**, BAC **208%**, BLK **230%** in the JSON. HTML renders `divVal.toFixed(2)` → user sees "296.00%". 12 of 14 yields are >15% (impossible). | Remove the `*100` for the yfinance path (it's already a percent), or detect units: `if div_yield and div_yield < 1: div_yield *= 100`. The in-flight working-tree diff only fixes the FMP `lastDiv` path — the primary yfinance path is still wrong. |
| 2 | **CRITICAL** | 14 picks / `score` + `rank_in_class` | Same bug as #1. Scorer line 584-586: `if div_yield and div_yield > 3: score += 5; signals.append("DIV=...")`. With the bug, 14/20 picks (GOOGL, NVDA, AVGO, EQIX, DIS, PLD, AAPL, BAC, FDX, ORCL, SBUX, BLK, MU, V) cleared 3% and got +5. With **correct** yields (real GOOGL 0.24%, NVDA 0.49%, AAPL 0.35%, MU 0.07%) **none** of the 14 exceed 3% → all 14 lose the bonus. The displayed cross-sectional rank ordering is therefore contaminated. | Fix #1 first; the score/rank fall out correctly once div is in real units. |
| 3 | **HIGH** | AMZN (x2) / whole row | `picks[0]` and `picks[1]` are both AMZN, both `rank_in_class=1.5`, near-identical (price 244.69 vs 244.70, market_cap differs in last 6 digits). Root cause: `HEAD:tools/picks_now_professional.py` lists `"AMZN"` **twice** in the EQUITY universe (line ~95 and line ~111) → scored twice → no `drop_duplicates(subset="symbol")` before `head(20)`. The live cron uses HEAD, so this is reproducible. (A working-tree edit removes one AMZN but the live JSON predates it.) | De-dupe the universe list AND add `df_res.drop_duplicates(subset=["symbol","class"])` before ranking/`head()`. |
| 4 | **HIGH** | AMD, DDOG, MU / `direction` vs `upside_pct` + `eli5_reason` | All three are `STRONG_BUY` while the mean analyst target is **below** current price: AMD `-1.9%`, DDOG `-2.4%`, **MU `-22.1%`** (target $739 vs price $949). The ELI5 text literally reads "...average target of $739 (that's **-22% higher** than today's price)" — a self-contradicting sentence shown to users. The score crosses 75 purely on momentum (MU 3m=+135%) + the bogus DIV bonus, overriding negative analyst upside. | Add a guard: if `upside_pct < 0`, demote out of STRONG_BUY (or to WATCH) and fix the ELI5 template to say "lower than" when upside is negative. |
| 5 | **MEDIUM** | All 20 picks / `db_n`, `db_wr`, `db_avg_pnl` | Every pick has `db_n=0, db_wr=0, db_avg_pnl=0`. These are **not fabricated** — `load_db_edge()` returns `{}` when DB creds are absent (lines 298-301), and the scorer defaults to 0 (lines 507-509). So they are honest placeholders, **but** the page advertises a "Database Win Rate … actual closed-trade performance" chip (picks-now.html:822) and a DB-edge scoring component that is entirely inert here. No pick gets the DB overlay (+10 max). Users may read "0% WR" as a real loss signal rather than "no data". | Render `db_n=0` as "no trade history yet / n=0" instead of "0% WR", and gate the DB-edge chip on `db_n >= 5` (HTML already does this at line 867/961 — verify it's not showing a misleading 0%). |
| 6 | **MEDIUM** | `safest` bucket (5 entries) | Selected purely by `nsmallest(5, "rvol")` (line 1053) with **no direction/data-validity filter**. Result: `ARB-USD` is in "safest" with `direction=WATCH`, `atr_pct=0.0`, `rvol=0.0` (i.e. **no/insufficient data**), `max_dd=36.1%`, `sharpe=-1.74` — a negative-Sharpe, high-drawdown, data-missing crypto labeled among the "safest". The three bond ETFs (SHV/SGOV/BIL) carry `sharpe -8.83/-7.31/-7.30` (artifact of comparing cash-like yields to a 5% RFR) which will read as alarming. | Filter `safest` to `direction in (BUY, STRONG_BUY)` AND `rvol > 0 and atr_pct > 0` (drop no-data rows). Consider suppressing/explaining the negative Sharpe for cash-equivalent bonds. |
| 7 | **MEDIUM** | NVDA, DDOG, MU / `eps_growth_pct` (HTML labels "YoY") | `eps_growth_pct` is sourced from yfinance `earningsQuarterlyGrowth` (generator line 489) — a **quarterly** YoY figure — but picks-now.html:960 prints it as "+211% YoY" and the tooltip (816) calls it the long-term EPS driver. Values: NVDA 210.6, MU 770.8, DDOG 113.4. Possibly real quarterly numbers but mislabeled as the headline growth driver. | Relabel as "EPS Growth (latest qtr YoY)" or switch the source to an annual figure. |
| 8 | **LOW** | PLD / `peg` | PLD `peg=112.44` — passed straight through from yfinance with no sanity clamp; will display as a meaningless "112.44" PEG chip. | Clamp/flag PEG to a sane range (e.g. hide if `<=0` or `>10`). |
| 9 | **LOW** | SNOW / `direction` vs `rsi_signal` | SNOW is `STRONG_BUY` with `rsi=66.7 / OVERBOUGHT_65`. Not wrong by the scoring rules (momentum + analyst carry it), but buying a name flagged overbought, with `max_dd=48.4%` and `atr_pct=7.24%`, is the kind of high-variance pick the "no coin-flips" directive wants flagged. Position size is correctly throttled to 1%. | Optional: surface an "overbought — chase risk" caveat in the ELI5 when RSI signal is OVERBOUGHT. |
| 10 | **LOW** | All picks / `ret_6m`, `piotroski`, `altman_z` | `ret_6m` is null for all 20 (6-month history fetch yields ~126 bars, just under the `>=126` cutoff at line 458). `piotroski` and `altman_z` are null for all 20 (FMP fetch capped/rate-limited at 30 symbols, lines 384-417; or 429'd). These are schema fields the page may try to render as blanks. **Fundamental-sanity check N/A** — no impossible values because the fields are simply absent. | Bump 6m history fetch to `period="1y"`; widen/space the FMP fetch or accept these as best-effort nulls and hide empty chips. |
| 11 | **INFO** | `honest_bridge_note` / `money_ready_status` | Generator tries to inject these context fields (lines 1236-1251) but references an **undefined name `ROOT`** (the module defines `REPO`, not `ROOT`) → the whole block silently `except`s → neither field is present in the JSON. The honesty/NFA bridge note never reaches the JSON consumers. | Change `ROOT` → `REPO` so the honest-bridge note is actually emitted. |

---

## What is OK (not fabricated)

- **Prices & returns are real.** yfinance spot-checks match: GOOGL price 363–364, target $431.19; SBUX target $106.25; PLD target $152.30 — all match the JSON exactly. `upside_pct` is internally consistent with `(target-price)/price` for all 20 picks (max diff <0.1pt).
- **`rank_in_class` correctly tracks `score` descending** (ties get .5 averaged ranks).
- **Position sizing is sane** — vol-scaled 1–8%, none >25%; high-vol names (SNOW, MU 1%) throttled correctly.
- **Risk/reward** is ≥1.43 on every pick (6 picks at exactly 1.43 due to the 10%/7% equity TP/SL caps — acceptable but on the low side).
- **Negative-expectancy guard exists** (lines 615-617): a symbol with `db_n>=20` and negative own avg PnL is demoted to WATCH — good design, just dormant here because DB is unreachable.
- **db_n/db_wr/db_avg_pnl are honest placeholders, not fabricated** (return `{}` on no-creds, default 0).
- **Banned-source leakage: NONE.** Picks NOW does not consume strategy `source_system` — it is a fresh yfinance/FMP screener. The only strategy interaction is a defensive ban-filter inside `load_db_edge()`'s SQL (lines 309-314) which excludes `BANNED_SOURCES` + myfxbook/ig-contrarian from the WR overlay. No `PERMANENTLY_KILLED`/`LOW_CONFIDENCE` strategy can leak into these picks.
- **Staleness OK.** `generated_at` is ~5h before the audit date — fresh.

---

## Bottom line

The picks themselves (mega-cap quality names on a pullback in a risk-off tape) are
*reasonable*, and there's no evidence of fabricated performance numbers or
banned-strategy contamination. But the page cannot be shown to users until the
**div-yield double-multiply (issues #1/#2)** and the **duplicate-AMZN + negative-upside
STRONG_BUYs (issues #3/#4)** are fixed — those are exactly the kind of obviously-wrong,
embarrassing artifacts the directive is trying to prevent.
