# Design: AI-Model Hedge-Fund-Style Portfolios

**Author:** Claude Opus 4.7 · **Date:** 2026-05-29 · **Status:** DRAFT for peer review → phased implementation
**Goal alignment:** Goal #1 (phenomenal performance across all asset classes on `/audit`) — this turns the AI-tournament's *pick stream* into *managed, risk-controlled portfolios* whose rules we can measure and combine.

---

## 1. Problem & intent

Today the AI tournament (`/audit/ai-tournament.html`) tracks **individual picks** per model and ranks models by WR/PF over resolved picks. What it does **not** do:

1. Treat each model as a **portfolio manager** with a finite book, position sizing, and risk limits.
2. Apply **defined entry/exit criteria** (TP/SL, 200d-MA EOD filters, time stops) consistently so a "pick" becomes a *position with a lifecycle*.
3. Express **risk appetite** (Conservative / Balanced / Aggressive) the way a fund family does.
4. Record **why** each position was taken and **how it was sized**, so we can later ask *which model's decision rules actually compound capital* — not just which model has a high hit-rate on unsized picks.
5. Surface a path to **combine** the most effective rules/criteria across models into an optimized meta-strategy.

**Thesis:** WR/PF on equal-weight unsized picks is a weak proxy for skill. A model that is right 52% of the time but sizes winners well and cuts losers fast can compound faster than a 60%-WR model that holds losers. Portfolios with explicit risk management expose that difference.

---

## 2. Scope & non-goals

**In scope (v1):**
- Paper portfolios only (no real broker, no real money). NAV is computed from market prices.
- Per-model × risk-appetite portfolios, seeded from the model's tournament picks.
- Daily EOD evaluation via GitHub Actions (entry, exit, rebalance, NAV snapshot).
- DB tables + JSON export + a new dashboard section.
- Meta-analysis report comparing rule effectiveness.

**Non-goals (v1):**
- Intraday execution / live brokerage.
- Re-deriving each model's "edge strategy" with ML (v2 — see §10).
- Replacing the existing tournament pick stream (this consumes it, doesn't replace it).
- Any change to live-money sizing on the main `/audit` surfaces.

---

## 3. Portfolio matrix (what gets created)

Creating 39 models × 3 appetites = 117 portfolios is too many to be legible and too sparse per book. **v1 roster:**

- **Top-N eligible models only**: models that are `rank_eligible` (n≥30 resolved) on the leaderboard. Currently ~29. Re-evaluated weekly; a model dropping below n=30 freezes (no new entries) but keeps marking-to-market.
- **3 risk appetites each** → ~ up to 87 portfolios, but we **gate by edge**: a model gets portfolios only if its leaderboard `pf_ci_lo > 1.0` for at least one asset class OR overall (the §"statistically valid edge" bar). That trims to the models that have *something* to manage. Today that's ~4 strong + a tier of marginal — call it **~10–15 models × 3 = 30–45 portfolios**.
- **3 "fund-of-funds" blended portfolios** (one per appetite) that allocate across the *best* per-class model rather than one model — the "what if we combined the best rules" baseline (feeds §10).

Each portfolio has a **starting NAV of $100,000** (notional, paper) so cross-portfolio comparison is apples-to-apples.

---

## 4. Risk appetites (the fund-family knobs)

| Knob | Conservative | Balanced | Aggressive |
|---|---|---|---|
| Annualized vol target | 8% | 15% | 28% |
| Kelly fraction (of edge-implied) | 0.25× | 0.50× | 1.00× (capped) |
| Max single position | 4% NAV | 8% NAV | 15% NAV |
| Max single asset-class exposure | 25% NAV | 40% NAV | 65% NAV |
| Gross exposure cap | 80% NAV | 110% NAV | 160% NAV (paper "leverage") |
| Cash floor | 20% | 10% | 0% |
| Per-position stop-loss | 1.0× ATR / −5% | 1.5× ATR / −8% | 2.5× ATR / −15% |
| Take-profit | +8% or 2R | +15% or 3R | trail-only (let winners run) |
| Trend filter (gate entries) | must be **above 200d MA** (longs) | 50d MA | none (signal-only) |
| Max open positions | 12 | 20 | 30 |
| Drawdown circuit-breaker | halt new entries at −8% MTD | −15% | −25% |
| Asset-class allowlist | BOND, ETF, EQUITY, FOREX | + COMMODITY | + CRYPTO, FUTURES, PENNY |

These live in `config/portfolio_risk_profiles.json` (single source of truth, hot-loadable). Numbers are **starting** values for review — the design intent is the *structure*, not the exact constants.

---

## 5. Entry / exit / sizing rules (the position lifecycle)

A tournament pick becomes a position through a deterministic, auditable pipeline:

```
tournament pick (model, symbol, dir, thesis, confidence, class)
   │  ① ELIGIBILITY GATE  (appetite allowlist for class? model edge in class? not already held?)
   ▼
   │  ② TREND FILTER      (EOD: longs require price ≥ Xd-MA; shorts ≤ Xd-MA; else reject)
   ▼
   │  ③ SIZING            (target_weight = clamp(kelly_fraction × edge_signal × vol_scalar, 0, max_pos))
   │                       vol_scalar = appetite_vol_target / trailing_realized_vol(symbol)
   ▼
   │  ④ RISK CHECK        (would it breach class cap / gross cap / max-positions / drawdown breaker?)
   ▼
   │  ⑤ OPEN POSITION     (entry=EOD close, set TP/SL from appetite, record reason+sizing rationale)
   ▼
   │  ⑥ DAILY MARK + EXIT (each EOD: mark price; exit if TP hit / SL hit / trend flips / time-stop / thesis-invalid)
```

- **EOD discipline:** all evaluation uses end-of-day closes (matches "above at end of day" style). No intraday whipsaw.
- **`edge_signal`** = the model's per-class `pf_ci_lo`-derived score (so sizing is proportional to *proven* edge, not raw confidence). Falls back to confidence × class-WR when CI is thin.
- **Price source:** the mandated failover chain (Binance mirrors → CoinGecko → KuCoin → CryptoCompare for crypto; yfinance → stooq → AlphaVantage for equities/ETF/FX). Never a single endpoint (CLAUDE.md API Failover Rule).
- **Reason capture:** every OPEN stores `entry_reason` (model thesis + which gate/filter passed), `sizing_reason` (the clamp inputs), `exit_reason` on close. This is the data §10 mines.

---

## 6. Data model (DB: `ejaguiar1_stocks`)

New tables (prefix `PF_` to namespace this subsystem):

```sql
PF_PORTFOLIO        -- one row per (model_id, risk_appetite) or fund-of-funds
  id, portfolio_key, model_id, risk_appetite, kind('model'|'fof'),
  starting_nav, created_at, status('active'|'frozen'), config_snapshot JSON

PF_POSITION         -- one row per open/closed position
  id, portfolio_id, symbol, asset_class, direction, status('open'|'closed'),
  entry_date, entry_price, qty, weight_at_entry,
  tp_price, sl_price, exit_date, exit_price, exit_reason,
  realized_pnl_pct, realized_pnl_usd,
  source_pick_id, entry_reason TEXT, sizing_reason TEXT

PF_NAV_SNAPSHOT     -- daily mark per portfolio (the equity curve)
  id, portfolio_id, asof_date, nav_usd, cash_usd, gross_exposure_pct,
  n_open, daily_return_pct, drawdown_pct

PF_RULE_EVENT       -- audit log of every gate decision (entry rejected, stop hit, breaker tripped)
  id, portfolio_id, asof_date, event_type, symbol, detail JSON

PF_DAILY_METRICS    -- rolling per-portfolio risk/return metrics (for the dashboard + meta-analysis)
  portfolio_id, asof_date, sharpe_30d, sortino_30d, max_dd, cagr, vol_realized,
  pf_to_date, wr_to_date, turnover, exposure_by_class JSON
```

JSON export for the dashboard: `audit_dashboard/data/pf_portfolios.json` (roster + latest NAV + metrics) and `pf_portfolio_<key>.json` (per-portfolio detail: positions + equity curve). `generated_at` stays ISO-UTC (machine field); dashboard renders EST.

---

## 7. Daily GitHub Actions job

New workflow `.github/workflows/ai-model-portfolios-daily.yml`:

- **Schedule:** `0 22 * * 1-5` (after US equity close; 22:00 UTC ≈ 17:00–18:00 ET). Crypto marks 7d but we keep one cadence.
- **Steps:** checkout → setup-python → install (pymysql, yfinance, requests) → `python tools/portfolios/run_daily.py` → ingest to DB → export JSON → FTP deploy (`tools/deploy_audit_files.py --only audit`) → commit JSON snapshots.
- **Failover + soft-fail:** price-fetch failures `continue-on-error` per symbol (logged to `PF_RULE_EVENT`), never abort the whole book. Honors the masking-policy linter (no *silent* maskers — every skip logs a `::warning`).
- **Idempotent:** keyed on `asof_date`; re-runs the same day overwrite that day's snapshot, never double-count.

`run_daily.py` orchestration: load profiles → for each active portfolio → ingest new eligible picks → run lifecycle (§5) → mark NAV → write metrics.

---

## 8. Dashboard section (`/audit/ai-tournament.html`)

New section **"Model Portfolios — Risk-Managed Books"** below the Model Summary:

- **Fund-family table:** rows = portfolio_key, cols = Model · Appetite · NAV · Total Return · CAGR · Sharpe · Sortino · MaxDD · PF · Gross Exp · #Open · Last Rebalance (EST).
- **Filters:** by appetite (Conservative/Balanced/Aggressive), by model, by asset class.
- **Drill-down** (`pf.html?key=...`): equity curve (NAV snapshots), open positions with TP/SL + entry/sizing reason, closed-trade blotter, exposure-by-class donut, rule-event log.
- All timestamps **EST** via the existing `toEST()` helper. "Last updated … EST" header stamp.

---

## 9. Meta-analysis: which rules compound best (the payoff)

Weekly `tools/portfolios/meta_effectiveness.py` → `reports/portfolio_meta_<date>.md` + `pf_meta.json`:

- **Rank portfolios by risk-adjusted return** (Sharpe, Sortino, CAGR/MaxDD) — *not* raw WR. Answers "whose decision rules actually compound."
- **Attribution:** decompose each portfolio's return into selection (pick quality), sizing (did weighting help vs equal-weight?), and timing (did the EOD/MA filter help vs naive entry?). The equal-weight tournament pick is the counterfactual baseline.
- **Per-class skill matrix:** model × asset-class CAGR/Sharpe → which model "manages" each class best.
- **Combination search (v1 = heuristic):** build the fund-of-funds by taking each class's best-Sharpe model's rules; report whether the blend beats every single-model book. This is the seed for v2 parameter optimization.

---

## 10. v2 (explicitly deferred)
- Walk-forward parameter optimization of the appetite knobs (vol target, Kelly fraction, MA window) per class with proper OOS/MC validation (reuse `reports/CYCLE_*` harness + M-107 pre-registration).
- ML meta-model that learns the optimal rule-combination weights (must pass the Wire-Up Rule + no-lookahead test).
- Correlation-aware portfolio construction (risk parity / HRP across the model books).

---

## 11. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Look-ahead / survivorship in backfilled seeding | Seed only from picks with real `submitted_at`; entry price = the *next* EOD close after submit, never the submit-day close. No backfill of historical NAV before a portfolio's `created_at`. |
| Stale/de-rostered models produce no new picks | Frozen portfolios mark-to-market but open no new positions; flagged in UI. (Ties into the model-revival work.) |
| Price-source disagreement skews NAV | Median-of-sources mark; log dispersion to `PF_RULE_EVENT`. |
| Overfitting the appetite constants | v1 constants are fixed & documented; optimization is a *separate, pre-registered* v2 effort. |
| DB/live-publish risk | Paper only; new `PF_*` tables don't touch existing pick/money-ready tables; JSON deploy is additive. |
| Scope/complexity | Phased delivery (§12) — each phase is independently shippable + reviewable. |

---

## 12. Phased delivery (maps to parallel implementation tasks)

| Phase | Deliverable | Files | Wire-up |
|---|---|---|---|
| **P1** | Risk profiles + DB schema | `config/portfolio_risk_profiles.json`, `tools/portfolios/schema.sql`, `tools/portfolios/init_db.py` | migration applied to `ejaguiar1_stocks` |
| **P2** | Portfolio engine (lifecycle §5) + sizing/risk | `tools/portfolios/engine.py`, `sizing.py`, `risk.py` | unit-tested, pure functions |
| **P3** | Price layer (failover) + daily runner | `tools/portfolios/prices.py`, `run_daily.py` | called by GHA |
| **P4** | GHA workflow + JSON export | `.github/workflows/ai-model-portfolios-daily.yml`, `tools/portfolios/export_json.py` | scheduled |
| **P5** | Dashboard section + drill-down | `audit_dashboard/ai-tournament.html` (section), `audit_dashboard/pf.html` | reads P4 JSON |
| **P6** | Meta-effectiveness | `tools/portfolios/meta_effectiveness.py` | weekly report |

**Acceptance criteria:** P1–P4 produce ≥1 daily NAV snapshot per active portfolio with auditable entry/exit reasons; P5 renders them with EST stamps; P6 ranks books by Sharpe with a selection/sizing/timing attribution.

---

## 13. Open questions for review
1. Portfolio roster size — gate by `pf_ci_lo>1.0` (lean, ~30–45 books) vs all rank-eligible (~87)? *Proposed: edge-gated.*
2. Appetite constants in §4 — sane starting points? Any class allowlist objections (e.g. PENNY in Aggressive)?
3. Rebalance cadence — pure EOD daily, or weekly rebalance with daily marks? *Proposed: daily evaluate, but cap turnover.*
4. Fund-of-funds construction — best-per-class (proposed) vs equal-weight-of-top-N?
