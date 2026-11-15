# Harvested Ideas — Mutual Funds

**Asset Class:** `MUTUAL_FUND`  
**Inventory Coverage (`00_inventory.csv`):** Referenced in `tools/recon_uncharted_tables.py` (`mf_`, `mf2_` MySQL tables), `multi_asset` tactical fund rotation, and `final_v4/inspect-wt/03_risk_management/backtest_rotation.py` (`v1_mf_feecost`). Planned `alpha_engine/mutual_fund_ranker.py` and `/audit/mutual-funds.html` do not exist in production code yet (`memory/2026-11-14.md:14`).

---

## 1. What Was Already Tried in the Repo
- **MF Fee-Drag Proxy (`backtest_rotation.py:16,44`):** Modelled mutual fund share-class overhead (`0.15%/yr` low-ER index class drag `(1 - 0.0015)**(1/12)` applied monthly to the 10-asset dual-momentum sleeve), achieving `8.1% CAGR`, `0.51 Sharpe`, `-20.6% MDD` over 166 months.
- **Database Table Exploration (`tools/recon_uncharted_tables.py`):** Tracked `mf_` and `mf2_` historical fund records in `ejaguiar1_stocks`.

## 2. Observed Results & Suspected Failure Modes
- **Structural Mismatch with TP/SL Engine:** Mutual funds price **once daily at 16:00 ET forward NAV** and enforce **30–90 day frequent-trading redemption penalties** (`1%–2%`). Any repo scanner treating mutual funds as intraday or 1–5 day TP/SL picks is **structurally impossible** (`ELIMINATION_RATIONALE.md:36`).
- **Active Selection Failure:** Literature & SubQ prior (`P(active MF beats index net) = 0.03`; SPIVA YE2025 showing `92.89%` of large-cap active funds trail S&P 500 over 20 years) confirms selecting active mutual funds by trailing alpha is a negative-sum game after MER (`1.0%–2.2%` Canadian retail mutual fund MERs).
- **Failure Modes:** #7 Implementation Gap (no dedicated MF emitter/HTML deployed; TP/SL model incompatible with forward NAV), #4 MER & Redemption Friction.

## 3. Research Gap for Phase 3 (`Plan/mutual_funds/PLAN.md`)
- Test **Candidate `M1_MutualFund_Sleeve_CAD_Tax`** — a **monthly tactical index-fund allocation sleeve** respecting **forward-NAV settlement (next-month rebalance)**, **30-day minimum hold compliance (0 short-term redemption fees)**, **low-ER institutional/DIY index class (`0.20%/yr` MER drag)** vs. **Canadian high-MER active comparison (`1.80%/yr` drag sensitivity)** and **Canadian taxable vs. TFSA/RRSP account tax drag**.

