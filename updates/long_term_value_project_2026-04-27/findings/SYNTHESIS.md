# UEPS Findings Synthesis — Phase 1 Lock

**Date:** 2026-04-27 (recreated 2026-04-28 after persistence loss)
**Author:** Claude Opus 4.7
**Aligns with:** CLAUDE.md MAJOR GOAL #1, `docs/PERFORMANCE_CHARTER.md`

This document is the AUTHORITY for Phases 2-15. Any deviation requires updating this file first.

---

## 1. Data stack — locked

### Tier A canonical (public domain, no rate cap)
| Need | Source |
|---|---|
| US fundamentals (full universe) | SEC EDGAR `data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json` + nightly `companyfacts.zip` |
| Quarterly cross-check | SEC EDGAR Financial Statement Data Sets ZIPs |
| Insider trades | SEC EDGAR Form 4 Insider Transactions Data Sets |
| ETF holdings (universal monthly) | SEC Form N-PORT |
| Short interest | FINRA Short Interest API |
| Daily short volume | FINRA Daily Short Sale Volume Files |
| Fails-to-deliver | SEC FTD ZIPs |
| Macro context | FRED API |
| US universe roster | Nasdaq Trader FTP |
| EOD prices | Stooq weekly bulk ZIP |
| TSX universe + EOD | EODData TSX download |

### Tier B convenience (ToS-gated, no redistribution)
- Finnhub (60 rpm, 1M/mo) — earnings, news+sentiment, insider transactions
- Tradier sandbox — only realistic free options chains
- Tiingo free (50 syms/hr) — adjusted-close validation
- Twelve Data free (800/day) — 4th failover

### Tier C fallback
- yfinance with `requests-cache` aggressive caching
- FMP free 250/day for splits + dividends calendar

### Excluded
- IEX Cloud (retired 2024), Alpha Vantage news (crippled to 25/day), OpenInsider scrape (fragile), API-Ninjas, sec-api.io free, stockanalysis.com.

---

## 2. Python library stack

```
pip install:
  edgartools           # EDGAR Python wrapper, Form 4 + 8-K + N-PORT parsing
  financetoolkit       # Altman Z + Beneish M + Piotroski F + DCF + ratios pre-built
  yfinance             # already in repo; pin version, add requests_cache
  pandas               # already in repo
  pyarrow              # parquet cache backend
  requests-cache       # mandatory for yfinance rate-limit handling
```

**FinanceToolkit:** highest-impact single dependency — provides Altman Z, Beneish M, Piotroski F, DCF intrinsic value pre-built. MIT license. Replaces ~600 lines of bespoke implementation.

**edgartools:** correct EDGAR Python wrapper. `set_identity(email) → Company(ticker).get_financials()` returns standardized XBRL DataFrames with no API key.

**Backtest framework:** vectorbt (already in repo) for Phase 13 walk-forward; empyrical-reloaded for metrics.

---

## 3. Methodology — locked

### Phase 1 LONG-side composite scoring formula

```
LongTermScore = (0.55 × ValueComposite + 0.45 × QualityComposite) × SafetyGate

ValueComposite = (
  0.40 × MagicFormulaPercentile +     # Greenblatt rank(ROIC) + rank(EarningsYield)
  0.35 × AcquirersMultiplePercentile + # Carlisle EV / OperatingEarnings
  0.25 × FCFYieldPercentile            # FreeCashFlow / EnterpriseValue
)

QualityComposite = (
  0.50 × PiotroskiFScore / 9 +        # 9-pt binary quality screen
  0.30 × ROIC_Stability +              # 5y std dev of ROIC, normalized
  0.20 × DebtToEquityScore             # 1.0 if D/E < 0.5, scales down
)

SafetyGate = 1.0 if (AltmanZ'' >= 1.10 AND BeneishM <= -1.78) else 0.0
```

**Key insights:**
- Magic Formula has decayed post-2010 (~1pp alpha vs 18pp pre-2010). Piotroski as quality filter is non-negotiable.
- SafetyGate is multiplicative — single bankruptcy or fraud flag zeros the score.
- All 12 evaluated methodologies (Magic Formula, Piotroski, Acquirer's, Graham, Buffett, Damodaran DCF, EV/EBITDA+ROIC, Beneish M, Sloan, Altman Z, Mohanram G, K-Ratio) are computable from `data.sec.gov/api/xbrl/companyfacts/CIK*.json` plus free EOD prices.

### Phase 4 SHORT-side trigger

```
ShortTrigger = (Beneish M-Score top decile)
            OR (Altman Z'' < 1.10)
            OR (Sloan Accruals top decile)

≥ 2-of-3 → SHORT candidate
1-of-3 → BLOCK from LONG-side picks (value-trap exclusion)
```

### Universe gates (hard exclusions before scoring)

```
EXCLUDE:
  market_cap < 300_000_000
  OR operating_history_years < 5
  OR asset_class IN {"Financial", "Utilities"}
  OR going_concern_flag IS True
  OR pink_sheets IS True
  OR last_10K_filing_age_days > 540
  OR fiscal_year_change_within_3y IS True
```

### n≥100 floor (mandatory, per CLAUDE.md MAJOR GOAL #1)

- **No source/strategy claims "proven edge" without n≥100 closed picks.**
- Walk-forward backtest target window: 2012-2025 (EDGAR XBRL coverage), 4 overlapping sleeves quarterly rebalance.

---

## 4. Pick contract additions

See `alpha_engine/long_term_pick_contract.py` for the implementation. New fields (all additive, all nullable):

```python
{
  # Existing fields preserved...
  "pick_type": "scalp" | "intraday" | "swing" | "position" | "long_term_value",
  "holding_horizon": "1d" | "1w" | "1m" | "3m" | "1y" | "3y+",
  "exit_mode": "tp_sl" | "thesis" | "calendar" | "trail",
  "thesis": str,                          # markdown bullet list
  "thesis_break_rules": list[ThesisBreakRule],
  "intrinsic_value": float | None,
  "fundamental_snapshot": FundamentalSnapshot,  # P/E, P/B, ROIC, F-Score, etc.
  "earnings_history": list[EarningsRow],   # last 8 quarters
  "next_earnings_date": str | None,
  "dividend_record": DividendRecord,
  "catalyst_dates": list[str],
  "universe_gate_passed": bool,
  "safety_gate_passed": bool
}
```

---

## 5. Dashboard surface

New tab "US Equity Picks" with sub-tabs Long-Term Value / Swing / Closed.

Each pick card shows: header (ticker + days_held) / thesis block / fundamental snapshot card with green-yellow-red colorization / earnings history table (8 quarters) / next earnings countdown + LTCG warning / dividend record + 5y sparkline / technical state / thesis-break status per rule / IV progress bar / position sizing breadcrumb.

All numerical claims include n=value where applicable.

---

## 6. Resolver split

| Pick type | Resolver | Behavior |
|---|---|---|
| `long_term_value` | `thesis_resolver.py` (Phase 8) | Quarterly thesis-break check. Hard time-stop at horizon expiry. IV-attainment exit. **Never closes on price drawdown alone.** |
| `swing` | `swing_resolver.py` (Phase 9) | TP/SL with bar HIGH/LOW touch detection. Time-stop at 30 days max. |
| `scalp`/`intraday` | existing `forward_validator.py` (crypto path) | unchanged |

**Critical:** `outcome_resolver.py:384-405` (the current broken non-crypto path) is NOT used for any new pick type.

---

## 7. Tier gates

Aligned with CLAUDE.md MAJOR GOAL #1 + `docs/PERFORMANCE_CHARTER.md`:

| Tier | PF | WR | MaxDD | n |
|---|---|---|---|---|
| **Tier 2 (size up)** | ≥ 1.5 | ≥ 50% | ≤ 20% | ≥ 100 |
| **Tier 1 (Renaissance)** | ≥ 2.0 | ≥ 55% | ≤ 10% | ≥ 200 |

Long-term extras: 3y CAGR ≥ 10% (T2) / ≥ 15% (T1); Sharpe ≥ 0.8 (T2) / ≥ 1.2 (T1).

---

## 8. Lift targets (from Agent D research)

### Primary lift (Phase 6 value_screener.py)
- `stocks_apr252025_440pmEST/scoring.py` (850 lines) — 13 technical sub-scorers + sector-relative fundamentals scoring + regime-aware weights + real unit tests.

### Secondary lift (Phase 7 swing_screener.py)
- STOCKSUNIFY2 `scripts/lib/strategies.ts` — 5 well-isolated scoring functions. Translate momentum-side ones to Python.

### Avoid
- `stock_quickpicks/risk_calculator.py:46-67` — uses `random.uniform()` for fake metrics.
- STOCKSUNIFY2 `stock-api-keys.ts` — security incident; user is rotating keys (deferred to private-repo move).
- 35-symbol fixed `V2_UNIVERSE` — too narrow.

---

## Decision log

- 2026-04-27: Project initiated for long-term value only.
- 2026-04-27 ~22:00 UTC: User expanded scope to long-term + swing + dashboard transparency + hedge-fund bar. Phases expanded from 8 to 15.
- 2026-04-27 ~22:30 UTC: CLAUDE.md added MAJOR GOALS section; UEPS aligned to Goal #1, n≥100 floor + Tier 2 thresholds locked.
- 2026-04-28 ~02:00 UTC: All 5 research agents complete; this synthesis written.
- 2026-04-28 ~02:30 UTC: Phases 12, 13, 14, 10-11 landed. Phases 4-9 reported PASS but did not persist. Recovery initiated.
- 2026-04-28 ~02:35 UTC: Phases 2 + 3 recreated and verified on disk.
