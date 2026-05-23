# Google Antigravity — hedge-fund-grade feedback (captured)

**Source:** User-provided summary of Google Antigravity guidance (April 2026).  
**Merged into:** [`HF_MERGED_EXECUTION_PLAN_2026-04-02.md`](./HF_MERGED_EXECUTION_PLAN_2026-04-02.md) §10 + phase IDs **B6–B7**, **C4–C5**, and cross-links to **A1**, **D1**, **B2**, **B5**.

**Video reference:** Feedback mentioned an external video on institutional auditing/compliance; **no URL was included** in the handoff — add the link here when available.

---

## 1. Architectural — quantitative factor model

| Recommendation | Intent | Repo alignment |
|----------------|--------|----------------|
| **Alternative data** | Move beyond isolated price action: sentiment/news aggregators, developer activity (e.g. GitHub) for crypto; macro (yields, CPI) for Forex/Equity. | **C4** — only wire **real** feeds with failover; see project no-placeholder rule. |
| **Multi-timeframe confluence for VA** | “Verified Alpha” only when signal aligns on **4h, Daily, and Weekly** simultaneously. | **B6** — extend `_is_verified_alpha_pick` / enrichment in `audit_trail/dashboard_generator.py` (~4045+); HTF fields already partially flow to audit columns (~5411+). |

---

## 2. Smart Picks / Verified Alpha — risk and regime

| Recommendation | Intent | Repo alignment |
|----------------|--------|----------------|
| **Risk-parity / VaR sizing** | Avoid fixed notionals; scale so each position contributes similar risk (e.g. VaR budget). | **B7** + `HEDGE_FUND_ENHANCEMENT_PLAN.md` §2 (Kelly/CVaR); `tools/hedge_fund_portfolio_risk_snapshot.py` for historical tail views. |
| **Mean reversion vs momentum** | Regime-switching: trending vs ranging; swap logic (e.g. ADX, Hurst). | **B1** (regime-aware routing) — same theme; can add explicit ADX/Hurst features where data exists. |
| **Monte Carlo before VA** | ~10k simulations vs historical vol; cap probability of severe drawdown (e.g. policy at 1% tail). | **C5** — batch/CPU cost and data window must be defined; reuse MC patterns in repo (e.g. `scripts/sports_monte_carlo.py`, alpha_engine MC) without inventing metrics. |

---

## 3. Alpha decay and execution

| Recommendation | Intent | Repo alignment |
|----------------|--------|----------------|
| **Slippage + spread** | Active picks should remain edge-positive under **conservative** bid-ask and slippage. | **A5** (fills truth) + **D1** (TCA); `HEDGE_FUND_ENHANCEMENT_PLAN.md` §3. |
| **Dynamic stops** | ATR-based **trailing** stops — let winners run, cut fast in vol spikes. | **A1** (unified TP/SL + ATR geometry). |
| **Walk-forward backtesting** | Reduce overfit from tuning to old regimes. | **B2** + **B5**; see `docs/WALK_FORWARD_CALIBRATION_REVIEW_2026-04-06.md` for production caveats (purge, side-aware costs). |

---

## 4. Compliance / fund structure

Institutional **audit trail, governance, and compliance** (referenced in feedback) are **out of scope** for this codebase doc unless you add a separate compliance roadmap; the technical backlog above supports **better measurement and controls** that auditors expect (WF, VaR, TCA, promotion stats).

---

## 5. Redis bus

Topic **`GOOGLE_ANTIGRAVITY_HF_FEEDBACK`** — published by `tools/bus_post_google_antigravity_hf_feedback.py` — points peers at this file and the merged plan.
