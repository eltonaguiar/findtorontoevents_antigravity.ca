# Equities Repos — 2026-11-18 Scout Report

## What we already have internally (do not duplicate)

- `STRATEGY_DISCOVERY_REPORT_V3_2026-11-18.md` — Stocks section: `*Backtest evidence pending.*`
- `equities_db_profile.md` — only bonds-proxy profile (TLT/IEF/etc.), no equity factor/edge findings.
- `CROSS_DB_DATA_QUALITY_MATRIX.md` — stocks DB has HIGH-severity ghost rows (22,986 `pnl_pct=0` in `at_raw_picks`) and won/lost contradictions. Data quality is the gating issue, not OSS code.

## Ranked equities repos (verified via api.github.com, not web search)

| Rank | Repo | Stars | Last push | License | Verdict |
|---|---|---|---|---|---|
| 1 | [microsoft/qlib](https://github.com/microsoft/qlib) | 50,391 | 2026-11-04 | MIT | VIABLE |
| 2 | [polakowo/vectorbt](https://github.com/polakowo/vectorbt) | 9,885 | 2026-11-11 | None (NOASSERTION) | PARTIAL |
| 3 | [mementum/backtrader](https://github.com/mementum/backtrader) | 23,759 | 2024-08-19 | GPL-3.0 | PARTIAL |
| 4 | [dcajasn/Riskfolio-Lib](https://github.com/dcajasn/Riskfolio-Lib) | 4,613 | 2026-11-04 | BSD-3-Clause | PARTIAL |
| 5 | [quantopian/alphalens](https://github.com/quantopian/alphalens) | 4,518 | 2024-02-12 | Apache-2.0 | DECORATIVE |
| 6 | [ranaroussi/quantstats](https://github.com/ranaroussi/quantstats) | 7,891 | 2026-11-02 | Apache-2.0 | DECORATIVE |
| 7 | [anthonymakarewicz/volatility-trading](https://github.com/anthonymakarewicz/volatility-trading) | 46 | 2026-04-01 | MIT | PARTIAL |
| 8 | [tibkiss/huba-v1](https://github.com/tibkiss/huba-v1) | 201 | 2022-07-09 | AGPL-3.0 | DECORATIVE |

## What each actually does

1. **qlib** — Full ML quant platform: alpha research, risk model, portfolio optimization, execution. You supply OHLCV/fundamentals. Falsifiable via its own backtest engine. Biggest blocker: you must bring clean data + compute.
2. **vectorbt** — Vectorized backtesting for factor/signal research. Ships no data. Excellent speed; license ambiguity (no SPDX) blocks commercial reuse.
3. **backtrader** — General event-driven backtester. Flexible but slow; GPL-3.0 restricts reuse.
4. **Riskfolio-Lib** — Portfolio optimization (HRP, risk-parity, CVaR). Strong for factor portfolio construction once signals exist; not an edge source.
5. **alphalens** — Factor tear-sheet analytics. Assumes you already have alpha factors.
6. **quantstats** — Performance analytics (Sharpe, drawdown, etc.). Post-backtest only, zero alpha.
7. **volatility-trading** — Equity options volatility backtesting (closest VRP/options logic found). Tiny stars, narrow scope.
8. **huba-v1** — Pairs/stat-arb engine. AGPL copyleft; stale (2022).

## Copy-trading / signal-following

No repo ships a practical, license-clean way to follow a known-good account's trades or aggregate signals. All "copy-trading" results are closed-source bots or decorative dashboards. Verdict: **DECORATIVE**.

## Hallucination / stale flags

- `search_web` previously returned fabricated repos (`factor-investing-backtest`, `quant-trading/factor-backtesting`, `pyfolio-factors`, etc.) with implausible star counts. **Do not trust those.** Only repos above were verified via api.github.com.
- GitHub search for `topic:quant equity factor backtest` returned only 3 low-star repos (2★ each) — the niche is thin.
- Equity options is essentially barren OSS (11 results, mostly 0–2★).

## Verdict

No consistent proven edge for equities as of 2026-11-18. OSS is thin outside qlib/vectorbt (platforms, not edges).

**Next concrete experiment:** Run the existing Arkane filter (`n≥30`, `win_rate≥0.55`) on the `stocks` DB once ghost-row data-quality issues are fixed, then compare surviving configs against qlib factor baselines.
