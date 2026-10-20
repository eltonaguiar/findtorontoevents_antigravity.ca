# Six-Method Review — Which of the Pasted Methods Actually Works Here — 2026-10-19

**Question:** document the six pasted methods (TSMOM, QMJ/value, pairs trading, volatility
risk premium, crypto funding carry, conditional PEAD) and find which one actually works
**in this repo's own evidence**.

**Evidence base:** existing backtest result JSONs in `audit_dashboard/data/`, forward
(recently-closed) trade stats from `dashboard_data.json` (`generated_at=2026-10-19T19:40:11.683221+00:00`,
3,500 closed picks), wiring status in the implementing modules, and the live data files
those methods write. No new backtests were run (multiple-testing discipline: per the
pasted text's own toolkit, anything that *looks* good here must be pre-registered under
M-107 and confirmed forward before belief).

## Verdict table (read this first)

| # | Method | Backtest evidence (in repo) | Forward evidence (closed picks) | VERDICT HERE |
|---|---|---|---|---|
| 1 | **TSMOM / trend** | futures TSMOM **TIER_2** (PF 1.71, Sharpe 0.66 L/S; 0.86 L-only); equity top-momentum Sharpe **1.34** PF 2.82 vs SPY 0.94 ("T2 confirmed"); ETF rotation PF 2.05 Sharpe 0.97 | ETF `adx-trend-scout` **n=35 WR 54.3% PF 1.76** ✅; EQUITY `adx-trend-scout` PF 0.93 ❌; ETF `sector-rotation` PF 0.28 ❌ | **WORKS (best of the six)** — only method with Tier-2 backtests *and* a forward cohort above the bar; but class verdict still INSUFFICIENT/NOT_READY |
| 2 | QMJ / quality+value | lowvol PF 1.93 Sharpe 0.879 ≈ SPY 0.8596; Piotroski basket Sharpe 0.792 **< SPY 0.806** | `quality-minus-junk` EQUITY n=49 WR 49.0% **PF 0.69**; ETF n=41 PF 0.88; `quality-momentum-scout` 1.03 / 0.88 | **FAILS HERE** — published QMJ is long/short + sector-neutral; our long-only screens don't reproduce it |
| 3 | Pairs trading | `cointegration_pairs.py` + `crypto_pairs_arb.py` exist (gated n≥30/WR≥50/PF≥1.3 in dashboard) | `pairs-trading` **n=8 WR 12.5% PF 0.04** | **FAILS HERE** — worst record of the six |
| 4 | Volatility risk premium | `strategies/unique_vol_risk_premium_harvest.py` exists, **not wired** to pick path, no results JSON | **0 closed trades ever** | **CANNOT TEST** — no options data/feed in this repo; needs a new data dependency before any claim |
| 5 | Funding-rate carry | `funding_rate_arb.py` wired as scanner; data file `funding_rate_picks.json` | snapshot: 17 picks, all `entry_date=2026-06-05`, all still `OPEN` (4.5-month-old frozen tracker); funding annualized **mean −189.7%, only 3/17 positive**; nearest forward strategy `funding-rate-reversal` n=15 WR 53.3% PF 1.59 | **DEAD TRACKER + NEGATIVE REGIME** — carry not collectible in this snapshot; nothing collectible until funding flips positive and the tracker is revived |
| 6 | Conditional PEAD | `strategies/pead_equity.py`, `earnings_drift.py`; shadow record says **`wf_verdict: T2_WF_VERIFIED`** but `shadow_only: true`, `count: 1` (dry-run pick `LEN`, 2026-06-12), `_wired_to_production: false`, files frozen since 2026-06-21 | no `pead`-named closed trades; nearest is `post-earnings-rev-scout` (**reversal**, opposite signal) **n=14 WR 64.3% PF 1.70** | **MOST PROMISING UNFINISHED** — WF-verified backtest, zero production trades; wire it before judging |

## 1. TSMOM / trend following — the one that actually works here

Backtests (all in `audit_dashboard/data/`):

| File | Headline |
|---|---|
| `futures_ts_momentum_backtest.json` | long-short: n=160 periods, WR 58.13%, PF 1.7083, Sharpe 0.6564, MDD 13.61% — `tier_comparison_long_short: TIER_2`; long-only Sharpe 0.8551, MDD 6.57%. Caveat in-file: `benchmark_audit_futures.verdict = "silent-dead per memory project_futures_kill_without_replacement"` (wr 5.9 — the *benchmark* leg; quoted verbatim, backstory not found in memory files) |
| `equity_top_momentum_backtest.json` | WR 64.75%, PF 2.8177, Sharpe 1.3382, MDD 24.19%, +1515.9% vs buy-hold SPY +346.9% (Sharpe 0.9395); `benchmark_audit_equity: "T2 confirmed"` (wr 53.2, pf 1.55) |
| `etf_sector_rotation_backtest.json` | WR 70.49%, PF 2.0472, Sharpe 0.9732, MDD 16.1% — but `benchmark_audit_etf: "sub-T2 (PF<1.5)"` (wr 56.1, pf 1.34): the audit view disagrees with the raw backtest |
| `trend_strength_200ma_adx_backtest.json` | PF 2.06 but Sharpe 0.4576, **MDD 55.3%** → fails the 20% MDD gate outright |
| `ust_tsmom.json`, `sector_dual_momentum.json` | `wiring_status: OPT_IN_SIDECAR — not yet consumed by production pick path` |
| ETF TAA (Antonacci) | Sharpe 0.88 / MaxDD −19% (verified in `reports/QUICKWIN_STRATEGY_TEMPLATES_2026-10-19.md`) — but verdict n=15 |

Forward (recent_closed): **ETF `adx-trend-scout` n=35, WR 54.3%, PF 1.76** — passes the
n≥30/WR≥50/PF≥1.5 proxy. Counter-evidence: EQUITY `adx-trend-scout` n=49 PF 0.93, ETF
`sector-rotation` n=8 PF 0.28. So trend works **per-cohort, per-asset-class**, not
wholesale — the exact "concentration on passing cohorts" lever from the sprint plan.

**Why it's #1:** it is the only method of the six with (a) in-repo Tier-2-grade
backtests, (b) a forward cohort already above the bar, and (c) live infrastructure
(wired ETF emitters emitting today: 7 of 9 active ETF picks are momentum/rotation).

## 2. QMJ / quality+value — fails here despite the citations

The pasted text's citations are about the *published* factor (long/short, sector-neutral,
55–68 bp/month, t=7–11). Our implementations are long-only screens, and they don't
reproduce it: `lowvol_compounders_backtest.json` Sharpe 0.879 vs benchmark SPY Sharpe
0.8596 (≈zero alpha), `piotroski_fscore_backtest.json` basket Sharpe 0.7917 **below** SPY
0.8064. Forward is worse: `quality-minus-junk` (EQUITY n=49, WR 49.0%, **PF 0.69**;
ETF n=41, PF 0.88) — our own quality book is a money-loser. The UEPS
(`magic_formula_x_piotroski_x_acquirers`) book has 22 open positions and **0 closed
trades** — no record at all yet, which is consistent with the earlier case-study finding.

Conclusion: "we already have the inputs" (true — ROIC/F-score/Acquirer's Multiple are on
every card) does **not** mean "we already have the edge." Reproducing published QMJ needs
the short leg or sector-neutralization — a design decision, not a data gap.

## 3. Pairs trading — worst record of the six

`alpha_engine/cointegration_pairs.py` and `crypto_pairs_arb.py` exist;
`crypto_pairs_arb` is even registered with promotion gates in
`dashboard_generator.py` (`gate_n: 30, gate_wr: 50.0, gate_pf: 1.3`). But the forward
record is `pairs-trading`: **n=8, WR 12.5%, PF 0.04** — one win in eight. The paste's own
caveat (decay after the 1990s, costs are the whole game) is borne out by our sample.
Verdict: research-only, and honestly probably not worth the research budget versus
trend.

## 4. Volatility risk premium — no record, no data

`alpha_engine/strategies/unique_vol_risk_premium_harvest.py` exists (with per-asset
friction handling) but is referenced nowhere in the pick pipeline (no
`JSON_PICK_SOURCES` entry, no results JSON in `audit_dashboard/data/`), and there are
**0 closed trades** for any vol/harvest strategy. Deeper blocker: this repo has no
options price/chain feed at all — the method is untestable here without adding one.
Honest status: **untested, not failing.** If pursued, it needs (a) an options data
source and (b) pre-registration before the first backtest, per M-107.

## 5. Funding-rate carry — tracker dead, regime negative

- `funding_rate_picks.json`: 17 picks, **every one `entry_date=2026-06-05`, every one
  still `status=OPEN`** — the file has not progressed in ~4.5 months (same dead-emitter
  pattern as the static investments-hub cards).
- Funding regime in that snapshot: `funding_rate_annualized` mean **−189.7%**
  (min −541.4%, max +243.8%), only **3 of 17 positive** — those are wild alts, and the
  sign distribution says the *short-perp collect* side of carry was not payable there.
  (The paste's "yields compressed to ~3.6% by mid-2026" warning is directionally
  consistent.)
- `funding-rate-reversal` (directional, not delta-neutral carry) forward: n=15, WR 53.3%,
  PF 1.59 — small, and a different strategy than the carry the paste recommends.

Verdict: **cannot claim carry works here — we have neither a live carry ledger nor a
positive funding snapshot.** To test it properly: revive the tracker (8h snapshots into
a history file, not one frozen day), pre-register the carry rule (7d mean funding ≥
cost floor, exit on 3 negative intervals), and let the paper record accumulate. That is
a genuinely cheap, convergence-based, provable-edge candidate — but only after the
tracker runs.

## 6. Conditional PEAD — the unfinished winner

- Backtest side: `pead_shadow_picks.json` carries **`wf_verdict: T2_WF_VERIFIED`** —
  walk-forward verified — but also `shadow_only: true`, `count: 1`, `generated_at:
  2026-06-12`, and the history row has `_wired_to_production: false, _dry_run: true`.
  `pead_shadow_history.jsonl` has exactly **1 row**, files untouched since 2026-06-21.
- Forward side: zero `pead`-named closed trades. The closest live thing,
  `post-earnings-rev-scout` (an *earnings reversal* — the opposite tilt), has
  **n=14, WR 64.3%, PF 1.70**, also small-n.

Verdict: the paste rates conditional PEAD as "real but conditional," and our repo
*agrees structurally*: the WF-verified implementation exists and was never wired, while
an adjacent earnings strategy quietly posts the best small-n forward numbers in the
book. **This is the highest-leverage unfinished item of the six** — wiring costs little
and the evidence base already claims T2_WF_VERIFIED.

## What to actually do (ranked by evidence-per-effort)

1. **Double down on trend cohorts (method 1)** — it's the only proven-here edge; feed
   its passing cohorts into the sprint plan's cohort-concentration lever (Task 3).
   Pre-register before promoting (M-107).
2. **Wire PEAD (method 6)** — `T2_WF_VERIFIED` sitting on `_wired_to_production=false`
   is the cheapest unfinished win; also watch `post-earnings-rev-scout` (n=14 → 30).
3. **Revive the funding tracker (method 5)** before claiming anything about carry — the
   method is provable *only* with a history file that updates.
4. **Park pairs (method 3)** — PF 0.04 forward; don't spend research budget.
5. **Park QMJ-as-implemented (method 2)** — long-only quality underperforms SPY in our
   own numbers; a sector-neutral/long-short redesign would be a *new* hypothesis (M-107).
6. **Vol premium (method 4)** needs options data we don't have — decide on the data
   dependency first, never on the marketing Sharpe.

## Honesty notes

- **Multiple testing:** six methods × many cohorts — the pasted text's own DSR/
  pre-registration rule applies to *our* "winner" list too. The forward numbers above
  are observations, not proof; the bar remains n≥100 + pre-registered rules + walk-forward.
- Forward WR/PF are computed from `recent_closed.pnl_pct` (flats excluded from WR,
  wins/losses only in PF), same convention as the sprint-plan case study.
- The `benchmark_audit_*` fields disagree with their parent backtests in 2 of 3 trend
  files (ETF sub-T2, futures benchmark "silent-dead") — both disagreements are quoted
  verbatim rather than resolved here; they need a separate reconciliation (they look
  like backtest-vs-forward audits, the same ledger split flagged in the case study).

## Verification map

Every figure traces to: `audit_dashboard/data/{futures_ts_momentum,equity_top_momentum,
etf_sector_rotation,trend_strength_200ma_adx,lowvol_compounders,piotroski_fscore,
ust_tsmom,sector_dual_momentum}.json`, `dashboard_data.json::picks.recent_closed`
(strategy-grouped aggregates), `alpha_engine/data/{funding_rate_picks,pead_shadow_picks,
pead_shadow_history.jsonl}` (file mtimes = local, content dates cited), and
`audit_trail/dashboard_generator.py:12007,12018` (crypto_pairs_arb gates).
