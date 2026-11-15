# Company Research — From Struggling to Trustworthy
**Date:** 2026-11-15  
**Purpose:** What financial prediction / risk-management companies (and quantitative funds) have done to go from struggling to find consistent profitability, to becoming trustworthy institutions people can trust with REAL money.  
**Status:** Research synthesis — patterns observed across the industry, applied to this system's situation.

---

## 1. The common pattern: struggling → trustworthy

Firms that successfully made this transition did **not** do it by mining more backtests or chasing higher win rates. They did it by fixing **measurement, governance, and risk controls first**, then proving edge on a tiny, disciplined subset of capital.

| Phase | What struggling firms do | What trustworthy firms do instead |
|-------|-------------------------|-----------------------------------|
| **Measurement** | Trust dashboard headlines; backtest WRs; single-snapshot "best strategy" | Recompute PnL from real entry/exit prices; dedup; exclude backfill labels; count EXPIRED as non-win; intrabar replay |
| **Multiple testing** | Report best-of-thousands as if it were one test | Correct for all strategies tested (`nb_trials`); DSR/SPA/PBO; Bonferroni |
| **Costs** | Ignore slippage/commissions; assume ideal fills | Model realistic round-trip costs per asset class; breakeven-cost analysis |
| **Governance** | No kill gates; promote on vibes; no pre-registration | Pre-register hypotheses; promotion gates (n, PF, DSR, MDD); kill criteria |
| **Risk** | Size by conviction; no drawdown halt | Fractional Kelly; per-trade risk caps (1–2%); daily/weekly/monthly DD halts; concentration caps |
| **Proof** | "Trust me, backtest says 90% WR" | Forward paper-pilot ≥4 weeks–3 months; live OOS; beat transparent benchmark |
| **Capital** | Deploy real money early on unproven signal | Deploy to low-cost index exposure first; paper-pilot the edge; size up only after certification |

---

## 2. Specific patterns observed in successful firms

### 2.1 Renaissance Technologies (Medallion) — signal + execution discipline
- **Pattern:** Massive signal inventory (thousands of signals), but each signal is tiny, short-horizon, and statistically validated. Heavy emphasis on **execution costs** and **market impact** — a signal that looks profitable on paper dies once impact is modeled.
- **Lesson for this system:** The profitable approach already found that crypto sources are "toxic" (failed the training-PF gate). Renaissance would drop them immediately rather than hope they improve. Focus on the few signals that survive cost + impact + multiple-testing (Variant C: equity/ETF walk-forward).
- **Apply:** Before promoting any signal, compute realistic per-class round-trip costs (from `tools/data/transaction_costs.json`) and require PF to clear 3× cost (the existing per-class cost gate).

### 2.2 Two Sigma / DE Shaw — engineering + measurement culture
- **Pattern:** Treat the research pipeline as engineering: versioned data, reproducible queries, feature stores, kill switches, and **measurement-first** culture. No signal goes live without a reproducible pipeline and a documented failure mode.
- **Lesson for this system:** The local `dashboard_data.json` is 26 days stale while the live payload is current. That's a measurement/engineering failure. Trustworthy firms fix the data pipeline before trusting any number from it.
- **Apply:** Fix `dashboard_data.json` freshness; fail-fast if >2h stale (money-maker-ready freshness gate); never audit from a stale local copy.

### 2.3 AQR / quantitative funds — factor transparency + academic rigor
- **Pattern:** Publish the economic rationale for every factor; pre-register tests; require out-of-sample validation; report Sharpe **and** drawdown/Calmar/Sortino, not just WR.
- **Lesson for this system:** This system has plenty of "78% WR / PF 13.1" claims (e.g., `cot_positioning_CT_locked`) that are small-n and likely concentration artifacts. AQR would demand the economic rationale + clean OOS + concentration check before trusting any of it.
- **Apply:** Require `(asset_class \| n \| timeframe)` on every claim; demand economic rationale; reject single-source concentration (>60% from one source = not edge).

### 2.4 Prop firms (FTMO / Hyro-style) — drawdown-first risk management
- **Pattern:** A pick can have 60% WR but still fail the prop challenge if losers are too deep. Risk rules (max daily DD, total DD, profit target) dominate raw WR/PF.
- **Lesson for this system:** HyroTrader has the infrastructure (QuanEngine 18-strategy consensus, validator, ML edge optimizer) but **"No journal trades logged yet"** — infrastructure wired but not producing closed trades. Trustworthy prop firms get the first 30+ resolved trades through the pipeline before evaluating edge.
- **Apply:** Evaluate against prop-firm risk rules (max daily DD, total DD), not raw WR/PF. Get the first 30+ resolved trades into the journal before any edge claim.

### 2.5 Mutual fund / ETF providers (Vanguard, etc.) — low cost + beta capture
- **Pattern:** The most trustworthy "prediction" is often **no prediction** — capture the equity risk premium at minimal cost (ER ≤0.10–0.20%, high AUM, low turnover). Outperformance comes from cost discipline and behavior, not stock-picking.
- **Lesson for this system:** The user's intuition about mutual funds/ETFs is correct for **lower risk**, but as **allocation**, not as ML prediction. The system's proven edge (Variant C) is equity/ETF short-term mean reversion — a different thing from buy-and-hold indexing.
- **Apply:** Deploy core capital to low-cost index ETFs/MFs; run the research system as a small satellite sleeve under strict gates.

---

## 3. What this system should do (adapted from the pattern)

| Struggling behavior (current) | Trustworthy behavior (target) | Concrete action |
|------------------------------|------------------------------|-----------------|
| Trust dashboard headline WR/PF | Recompute from DB with mandatory filters | Run `tools/build_pf_registry.py` + `tools/picks_now_professional.py` |
| Promote on single-snapshot best WR | Pre-register + clean OOS + walk-forward | Run Variant C forward test (equity/ETF) |
| Ignore costs | Model per-class round-trip costs; 3× cost gate | Enforce `tools/per_class_cost_gate.py` |
| No kill gate | Pre-registered kill criteria | PF<0.5 twice consecutively → stop; 3-month rolling PF<1.0 → re-audit |
| Size by conviction | Fractional Kelly + DD-halt | `alpha_engine/kelly_position_sizer.py`; ¼ Kelly ≈2.5%/trade |
| Audit from stale local copy | Fail-fast if dashboard >2h stale | Freshness preflight; use live URL |
| Deploy real money on unproven signal | Core = low-cost index; satellite = paper-pilot edge | Allocate core to index ETFs/MF; research as satellite |

---

## 4. Timeline to trustworthiness (realistic)

| Timeline | Milestone |
|----------|-----------|
| Weeks 1–4 | Fix measurement (P0): fabricate-flat ban, blank-field validation, cost gate enforcement, freshness preflight |
| Weeks 5–12 | Clean cohort screen (P1); EQUITY SPY benchmark pre-registration (P2); crypto OHLCV backfill |
| Months 4–6 | Paper pilot ≥4 weeks (P3); T2 certification attempt (n≥100, PF≥1.5, WR≥50%, MDD<20%) |
| Months 6+ | Live sizing at ¼ Kelly with DD-halt (P4) — only if T2 certified; otherwise remain paper |

**Honest statement:** Most firms never get past the measurement phase. This system is currently at Phase 0 (measurement integrity not yet complete). Claiming profitability now would be premature.

---
