# Strategy discovery & validation protocol (multi-asset)

**Scope:** equities, ETFs, forex, crypto, commodities.  
**Goal:** propose **novel** rules, reject look‑alikes of the existing library, and promote only robust, cost‑aware strategies.

Related: [TESTING_PROTOCOL.MD](../TESTING_PROTOCOL.MD), [QUANT_SIGNAL_ENGINE_FRAMEWORK_V2.md](QUANT_SIGNAL_ENGINE_FRAMEWORK_V2.md) (if present), `baby_strategies/compare_to_audit_baselines.py`, `baby_strategies/correlation_prune_strategies.py`.

**Snapshot docs (2026-04-19):** [STRATEGY_SUMMARY_BY_ASSET_CLASS_2026_04_19.md](STRATEGY_SUMMARY_BY_ASSET_CLASS_2026_04_19.md), [OUTPERFORMER_ANALYSIS_2026_04_19.md](OUTPERFORMER_ANALYSIS_2026_04_19.md) — use the same definitions of “baseline” and “outperform” across research and audit writing.

---

## Review feedback — Cursor agent (2026-04-19)

1. **Single index:** This protocol is the **discovery** complement to Strategy Factory **promotion** — keep “S0 hypothesis” language aligned with [STRATEGY_FACTORY_V1_1_AMENDMENTS.md](STRATEGY_FACTORY_V1_1_AMENDMENTS.md).
2. **Correlation tooling:** `correlation_prune_strategies.py` is intentionally minimal — document expected CSV shape in the script header (done); add a `tools/export_strategy_daily_returns.py` when someone builds the plumbing.
3. **Cost table:** Reconcile bps assumptions quarterly vs live slippage telemetry from `/audit` — add a revision date row when numbers change.
4. **Novel commodity example:** Treat as **illustrative** until backtested; still subject to ρ checks vs existing commodity templates.
5. **Audit dirs:** See table in [CROSS_ASSET_STRATEGY_MATRIX.md](CROSS_ASSET_STRATEGY_MATRIX.md) for `docs/strategy_audits/` and siblings.

---

## 1. Research objective & constraints

| Item | Action |
|------|--------|
| Universe | Fixed ticker lists per class (e.g. liquid US names, G10 FX, top crypto by ADV, commodity ETFs). Document vendor + as‑of date. |
| Bar size + history | Default **daily** for cross‑asset comparability; ≥10y equities, ≥5y crypto where data exists. |
| Costs | Apply **round‑trip** assumptions before any promotion (see §5). |
| Novelty | New template must have **|ρ| < 0.2** vs every existing strategy on **aligned daily returns** (see §6). |
| Performance | Minimum gates are **research‑phase** (e.g. PF > 1, enough trades); **stricter OOS** gates before production. |

---

## 2. Data & preprocessing

- UTC timestamps; OHLCV mandatory; adjust equities/ETFs for splits/dividends when using price levels.  
- Data quality report: missingness, outliers, calendar alignment (see framework v2 Appendix C pattern).  
- Build a **feature matrix** only after clean bars (indicators, cross‑asset factors if needed).

---

## 3. Candidate generation (novelty‑aware)

| Approach | Note |
|----------|------|
| Rule grammar | Combine small building blocks (trend filter + pullback + trigger); grid modestly. |
| Factor / ML | LASSO or shallow trees on **purged** samples; explain top features. |
| Cross‑asset | e.g. “risk‑off” filter from VIX/DXY — document lag and leakage controls. |

**Novel commodity example (illustrative):**  
*Roll‑adjusted backwardation filter + seasonal window* — long a **commodity ETF** only when: (i) front–next futures spread proxy (or ETF vs index momentum) indicates **backwardation** over a 5d smoothed window, **and** (ii) calendar month in a **harvest / inventory** window documented for that market, **and** (iii) 20d realized vol below its 252d **median** (vol filter). This is **not** a generic EMA+RSI pullback; correlation vs “trend + RSI pullback” templates should stay low if implemented distinctly.

---

## 4. Screening (in‑sample, fast)

- Vectorized or baby‑runner backtests with **explicit fees/slippage** (§5).  
- Drop candidates with trivial turnover, absurd drawdowns, or **near‑duplicate** equity curves.  
- Run **correlation pruning** vs the library (§6).

---

## 5. Transaction costs (backtest defaults)

Use **asset‑specific** round‑trip friction; increase slippage in stressed regimes if you model it.

| Asset class | Typical round‑trip (indicative) | Notes |
|-------------|----------------------------------|--------|
| US equities / ETFs | 5–20 bps + half‑spread | Add borrow for shorts; use ADV‑scaled slippage for size. |
| Forex (retail spot) | 0.5–2 pips major pairs + slippage | Model **spread** as % of price for daily bars. |
| Crypto (exchange) | 5–25 bps + depth‑based impact | Taker vs maker; perps include funding separately if applicable. |
| Commodity ETFs | 10–30 bps | Contango/decay not in spot OHLC — document ETF tracking risk. |

**Practice:** build a **single cost table** in code (bps per side or round‑trip), apply **next‑bar** execution after signal, and run **sensitivity** ±50% on friction before trusting Sharpe.

---

## 6. Correlation pruning (automated)

1. For each strategy, export **daily simple returns** on a **common calendar** (fill non‑trading with 0 or align per asset class — be consistent).  
2. Build CSV: `date`, `strat_a`, `strat_b`, …  
3. Run:

```bash
python baby_strategies/correlation_prune_strategies.py --csv strategy_daily_returns.csv --threshold 0.2
```

Exit code **0** = no pair ≥ 0.2; **1** = at least one violation. Wire this into CI or a pre‑merge checklist.

**Library baseline:** concatenate returns from existing promoted strategies (or representative basket) in the same CSV.

---

## 7. Robustness & OOS

- **Walk‑forward** or **purged K‑fold**; embargo between train/test.  
- **Parameter sensitivity** (±20% on key thresholds).  
- **Hold‑out** last 12 months (or 6 for very fast crypto) untouched until final gate.  
- Optional: bootstrap on trade returns; deflated Sharpe / multiple‑testing awareness.

---

## 8. Documentation & handoff

- One **spec sheet** per strategy: logic, parameters, data, costs, known failure modes.  
- Versioned code + pinned env; JSON backtest artifact in repo for the approved run.  
- Compare to audit baselines where applicable (`compare_to_audit_baselines.py`).

---

## 9. Quick submission checklist

- [ ] Signal definition distinct from existing templates  
- [ ] Costs in the backtest  
- [ ] IS + WF + final OOS summarized  
- [ ] Correlation CSV passes `correlation_prune_strategies.py`  
- [ ] Drawdown / exposure / liquidity addressed  
- [ ] Module + runner test in `baby_strategies/`
