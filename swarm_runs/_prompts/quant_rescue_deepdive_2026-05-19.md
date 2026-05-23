# Quant Rescue Deep-Dive — system architecture + the real question

You are a senior quant brought in to rescue a failing multi-asset prediction
system. Below is the ACTUAL architecture, the current honest verdict, and the
question. Use the architecture detail to dig — do not give generic advice.

## How the system works — data flow

**1. Pick generation (GitHub Actions).** ~36 scheduled GitHub Actions workflows
run scanners/scrapers/ML engines on a cron. Each emits "picks" (symbol +
direction + entry/TP/SL + a confidence/score). Sources are heterogeneous:
technical scanners, ML models (`ml_enhanced`, `quan_engine`), copy-trader
intel, prediction-market signals, mutation/genome engines. Picks are written to
two places: per-system JSON ledgers in the repo, AND MySQL.

**2. MySQL (host `mysql.50webs.com`).** Two databases:
- `ejaguiar1_stocks` — live: `at_raw_picks` (~147k rows, every emitted pick:
  symbol, asset_class, direction, entry/exit, status OPEN/WON/LOST, pnl_pct,
  confidence, source_system, strategy, dedup_hash), `at_consensus_picks`,
  `at_strategy_stats`, `at_filter_log` (gate rejections), `at_pick_outcomes`.
- `ejaguiar1_backtests` — `bt_backtest_trades` (~1.27M rows historical sim).

**3. Resolution.** Workflows resolve OPEN picks to WON/LOST against forward
price (yfinance/Binance). Crypto resolves ~65%; non-crypto partially (EQUITY
45%, FOREX 22%, FUTURES 8.7% — orphan-source gaps).

**4. The dashboard (`audit-dashboard.yml`).** Hourly: runs the dashboard
generator → aggregates picks → writes `audit_dashboard/data/dashboard_data.json`
(~18MB) + `index.html` → FTP-deploys to 50webs `/findtorontoevents.ca/audit/`.
The live `/audit` page renders tiles per asset class from that JSON.

**5. Canonical view.** `audit_dashboard/data/pf_registry.json` is the
POLICY-CLEAN, DEDUPED, net-of-slippage ledger — ~14,705 raw rows collapse to
~2,400 after dropping ~4,830 duplicate re-emissions + policy-excluded picks.
The raw dashboard tiles INFLATE (e.g. EQUITY shows WR 78% / PF 10 raw vs
canonical WR 33% / PF 0.72). `pf_registry` is verdict-grade; the tiles are not.

**6. The admissibility gate.** `tools/edge_stability_harness.py::is_admissible()`
— a signal is "real edge" only if effect size eff>=0.30, SAME SIGN, in >=3 of 5
walk-forward 14-day windows, >=80 picks/window. Pre-registration is enforced
(`reports/hypothesis_registry.json`, rule M-107: register a hypothesis BEFORE
backtesting it).

## The current honest verdict (do not re-discover this — build ON it)

- **11 pre-registered causal hypotheses tested. 11 killed. 0 admissible.**
  Families killed: COT positioning, funding-rate directional, roll-yield,
  yield-curve momentum, PEAD, funding-arb carry, options-flow, on-chain
  address counts, funding-settlement cascade, exchange net-flow, cross-exchange
  premium. Every one died the SAME way: eff sign flips across walk-forward
  windows (regime noise, not edge) AND/OR gross edge (1-9 bps) thinner than the
  ~30 bps round-trip cost.
- Macro root causes (`reports/MACRO_WHY_NO_EDGE_2026-05-18.md`): free-data +
  daily-bar resolution signal space is empirically empty; the system measures
  rather than predicts (8,400-pick ledger is accumulated emitter output, not a
  designed experiment); pervasive data corruption manufactures fake positives;
  non-crypto pick volume too thin (EQUITY n=33, FUTURES n=12 clean).
- Symbol-universe blindness (`reports/DB_PICK_TRACEBACK_2026-05-18.md`): EQUITY
  scanner traded 37 of ~500 S&P symbols in 30 days; crypto ~26-33% of the
  liquid universe. The class with the best apparent WR has the narrowest
  aperture.
- One in-sample-profitable non-artifact cohort exists repo-wide: CRYPTO
  `mega_mutation` (n=72, PF 2.19) — forward-unproven, now paper-tracked.

## The question — answer THIS, specifically

Given the architecture and the 11/11 kill verdict:

1. Is this system salvageable into profitable picks per asset class, or is the
   honest answer "retail-accessible edge space is empty — go paper-only"?
2. If salvageable: what is the ONE highest-leverage change — and is it a data
   change (new input class, finer timescale, paid feed), a methodology change
   (the harness itself, regime-conditioning, meta-labeling), or a scope change
   (abandon FOREX/BOND/FUTURES, concentrate on CRYPTO)?
3. The symbol-universe blindness — is widening the scanner aperture (trade 400
   crypto / 500 equity symbols instead of ~35) a real lever, or does it just
   add noise without adding edge?
4. The system has never tried: genuine intraday/tick resolution; cross-sectional
   ranking done right; meta-labeling (bet-sizing on top of direction);
   causal-inference feature selection. Which of these, if any, is worth a
   3-month bet — and what is the realistic probability it produces an
   admissible edge?
5. What would YOU, as the rescue quant, do in week 1 — concretely, against THIS
   architecture (these workflows, this MySQL schema, this harness)?

Be brutally honest. "There is no edge, go paper-only" is an acceptable answer if
that is what the evidence says. Do NOT propose re-running a killed hypothesis
family. Every new idea must name its causal mechanism and how it clears the
harness.
