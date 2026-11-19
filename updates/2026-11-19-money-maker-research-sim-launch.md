# 2026-11-19 — Money-maker research: sleeve-claim cross-mark, forward-clock unstick, live crypto paper sim

## What was broken

1. **Uncorroborated headline sleeves on /audit.** The MAJOR GOAL banner's per-class "Top:" sleeves (`Multi-Timeframe Trend Alignment` 87% WR / PF 11.8, `AuditEnsemble_LONG` PF 10.1, FOREX `non_crypto_consensus` PF 9.68) came from `_top_sleeves_from_outcomes()` in [alpha_engine/money_ready_verdict.py](../alpha_engine/money_ready_verdict.py) — a post-hoc MySQL selection (WR≥50 & PF≥1.5 over ~277 strategies, no multiplicity correction). None of those names exist among the audit3 tribunal's 277 scored cells, nor in the 3,500-row payload it ingests. Headline numbers with zero independent scoring.
2. **ETF forward clock stuck at n=0.** `etf_dual_momentum_pilot.py` only closed on rotation/cash (winner-stays), so months could pass with zero closed trades; and no pilot's closes ever reached `reports/forward_observations.jsonl`, so POD-FABER-TAA & co. could never accrue forward evidence.
3. **No live short-term simulation.** The operator asked for a live, constantly-monitored short-term/day-trading paper experiment with trial/error and parallel strategies; nothing existed for crypto intraday.

## What changed

- `alpha_engine/money_ready_verdict.py`: new `_audit3_cross_mark()` stamps every sleeve with the tribunal's verdict (`audit3_verdict`, `tribunal_corroborated`); `audit_dashboard/template.html` renders a green `AUDIT3 <verdict>` badge when corroborated, amber **UNVERIFIED (not in audit3)** when the tribunal never scored it, red when the tribunal rates it WEAK/KILL.
- `verified_strategies/paper_pilot/etf_dual_momentum_pilot.py`: calendar-month segment closes (close + re-open at month boundary) so the forward book accrues one row per held month; CLOSE rows now carry `entry_date`/`asset_class`/`exit_reason`.
- **New** `tools/pilot_forward_bridge.py` (+ `tools/crypto_bars.py`): re-resolves every pilot CLOSE from real bars through `intrabar_resolver.stamp_pick` (yfinance daily for ETF, Binance mirrors→KuCoin→CryptoCompare for crypto), computes the matched benchmark leg, and appends contract-validated rows to `reports/forward_observations.jsonl` idempotently. Rows closed before pod registration (2026-11-19) are dropped.
- **New** `verified_strategies/paper_pilot/crypto_intraday_sim.py` + `.github/workflows/crypto-intraday-sim.yml` (cron :07/:37): three pre-registered paper slots — `vwap_reversion` (H-2026-11-19-01), `bollinger_mr` (H-2026-11-19-02), `btc_4h_rsi_macd` (H-2026-11-19-07, newly registered) — with prop-firm guardrails: trailing-DD >10% → HALT, daily loss >3% → PAUSE until next UTC day, single-day >40% of profit → consistency flag, n<20 → "no_judgment". Paper-only; promotion only via the audit3 forward gate.
- `reports/hypothesis_registry.json` + `reports/audit3_confirmatory.json`: pre-registered H-2026-11-19-06 (ETF dual momentum, POD-ETF-DUAL-MOMENTUM) and H-2026-11-19-07 (BTC 4h RSI/MACD, POD-CRYPTO-BTC4H-RSIMACD) before any forward data (M-107); added `faber_taa_paper_pilot` to POD-FABER-TAA's claimed strategies.
- Research + $2k allocation verdict: [reports/money_maker_per_asset_class_2026-11-19.md](../reports/money_maker_per_asset_class_2026-11-19.md); external evidence with citations in `ACTIONPLAN_AUDITPAGE/2026-11-19T1906Z_copilot-moneyresearch/RESEARCH_EXTERNAL_EDGES.md`.

## How it was verified

- `python3 -m pytest tests/test_money_ready_verdict.py -k "Audit3CrossMark or Sleeve or merge"` → 12 passed (4 new cross-mark tests: NOT_SCORED on absent sleeve, corroboration on CANDIDATE, strongest-verdict-across-directions, fail-open on missing ledger).
- `python3 -m pytest tests/test_crypto_intraday_sim.py` → 15 passed (entry signals per slot, intrabar TP/SL ordering, time exit, DD-halt, daily-loss pause, halted-slot-takes-no-entries, full open→close lifecycle, bridge contract validation incl. `FO.validate`, foreign-strategy rejection, pre-registration date cutoff).
- Live smoke: `crypto_intraday_sim.py --one-shot` ran against the real failover chain and opened `vwap_reversion` LONG BTCUSDT @ 62,757 (z=−1.96), paper-only; `pilot_forward_bridge.py --json` correctly emitted 0 rows (all existing pilot closes predate pod registration).
- `py_compile` on every touched Python file; workflow YAML parsed with `yaml.safe_load`.
