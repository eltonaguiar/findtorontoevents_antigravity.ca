# Institutional Alpha Engineering Protocol: Antigravity Edition
**Author:** Antigravity AI  
**Status:** DRAFT / PROPOSED  
**Priority:** CRITICAL - Transition to Live Pilot  

## 1. Executive Summary: The Escape Protocol
The objective is to move the Alpha Engine from a perpetual "Stuck-in-Backtest" (SIB) state to a verified institutional-grade execution environment. This document outlines the roadmap for formalizing our prediction system using GitHub Actions, MySQL (50webs), and the 8-Rung Validation Protocol.

---

## 2. Research Areas & Strategic Enhancements

### A. GitHub Project: "Alpha Deployment Command"
- **Implementation:** Create a GitHub Project (Beta) to track strategy lifecycle stages.
- **Workflow:** Automated status moves (Backtest -> Shadow -> Pilot) triggered by GitHub Actions performance logs.
- **Benefit:** Centralized transparency for multi-system coordination.

### B. MySQL 50webs Optimization (`ejaguiar1_stocks`)
- **Enhancement:** Implementation of `at_institutional_picks` table to separate "noise" from "signal."
- **Infrastructure:** Use `DB_PASS_STOCKS` and `DB_PASS_BACKTESTS` for high-throughput sync from local `.db` to remote MySQL.
- **Benefit:** Faster dashboard rendering and institutional-grade audit trail.

### C. ML Gatekeeper (MLG-1) Scrutiny
- **Enhancement:** A hard-coded logic layer that rejects any signal with `ml_score < 0.85` or `confidence_decay > 0.15`.
- **Benefit:** Eliminates "toxic" crypto and forex noise before it hits the portfolio.

---

## 3. The "Stuck-in-Backtest" Escape Protocol (S-BEP)
*An 8-Rung protocol to ensure zero-regret capital allocation.*

| Rung | Stage | Requirement | Action |
| :--- | :--- | :--- | :--- |
| **1** | Static Backtest | PF > 1.30, Win Rate > 55% | Log to `bt_backtest_trades` |
| **2** | Walk-Forward | Stability over 3x 30-day windows | GitHub Action: `walk-forward.yml` |
| **3** | Shadow Mode | 30 live picks, 0% capital | Log to `at_raw_picks` |
| **4** | Correlation Audit | < 0.30 correlation to existing pilot | Reject if overlapping |
| **5** | Pilot Stage | 0.1% sizing, 10 trades | Execute via `alpha-engine-live.yml` |
| **6** | PCG-5 Enforcement | Pass all 5 Portfolio Construction Gates | Reject if any gate fails |
| **7** | Institutional Pilot | 1.0% sizing | Move to `at_institutional_picks` |
| **8** | Full Scale | Multi-strategy capital allocation | Institutional Certification |

---

## 4. PCG-5 Portfolio Construction Gates
*Mandatory enforcement for every production signal.*

1. **Gate 1: Liquidity/ATR Floor** - Symbol must have > $100M daily volume and ATR > 1.5%.
2. **Gate 2: Sector Correlation** - Max 2 active signals per sector (e.g., AI-Crypto, Tech-Equities).
3. **Gate 3: Regime Match** - Strategy must match current market regime (Trending/Ranging).
4. **Gate 4: Drawdown Watchdog** - If strategy is in > 10% drawdown, disable all new entries.
5. **Gate 5: Alpha Decay Watchdog** - If `KS_D > 0.10`, trigger mandatory DNA mutation.

---

## 5. Institutional Readiness Schedule (Projected EST)

| Asset Class | Readiness Phase | Projected Date/Time | Status |
| :--- | :--- | :--- | :--- |
| **Commodities (Gold/Oil)** | Institutional | 2026-05-18 09:00 EST | **LEADER** |
| **Equities (Large Cap)** | Institutional | 2026-05-25 09:30 EST | **HARDENING** |
| **ETFs (Macro/Bonds)** | Pilot | 2026-06-01 10:00 EST | **STABLE** |
| **Crypto (A-Tier: BTC/ETH)** | Pilot | 2026-06-08 12:00 EST | **PURGING** |
| **Forex (Major Pairs)** | Shadow Mode | 2026-06-15 08:00 EST | **TOXIC** |
| **Memecoins (Pump/Meme)** | Research Only | 2026-07-01 00:00 EST | **HIGH-RISK** |

---

## 6. Implementation Checklist (Next 48 Hours)
- [ ] **DB Sync:** Finalize migration of backtest data to `ejaguiar1_backtests`.
- [ ] **Hard-Kill:** Purge 26 toxic crypto strategies from `scanner.py`.
- [ ] **PCG-5 Setup:** Modify `portfolio_gates.py` to return `REJECT` instead of `WARNING`.
- [ ] **GitHub Action:** Create `institutional-readiness-audit.yml` to track Rung progress.

> [!IMPORTANT]
> The transition from "Backtest Hero" to "Institutional Trader" requires the courage to kill 90% of strategies. We prioritize **Quality over Quantity**.

---

## Claude Code Analysis — 2026-05-16T22:10Z

### Current State vs. Antigravity Projections

The Antigravity roadmap was directionally correct but timeline-optimistic. Here is the verified state against each projection:

| Asset Class | Antigravity Status (projected) | Verified State (2026-05-16) | Gap |
|---|---|---|---|
| Commodities | Institutional by 2026-05-18 | PAPER-TRADE ONLY — CT=F on PROBATION, multi_asset_cot pending ab_analysis.yml DB verification | ~6 weeks |
| Equities | Hardening | T2 CONFIRMED (PF=1.56/WR=51.5%/n=425) — real-money eligible at $100/pick (swing cap) | On track |
| ETFs | Pilot | RESEARCH_ONLY — PF=1.32 below T2 floor, n=107 building | Lagging |
| Crypto | Purging | Sub-T2 class-wide — UTC-hour filter + quarantine shipped; M-034 confidence inversion gate in shadow | Progressing |
| Forex | Toxic/Shadow | FOREX_HARD_DISABLE=1 active (hard-blocked) | Aligns |
| Memecoins | Research Only | Not yet split from CRYPTO | On track |

### High-Value Action Items — Pros/Cons

**8-Rung S-BEP Protocol — ADOPT with caveats**
- Pro: The staged Backtest→Shadow→Pilot→Institutional ladder is the correct framework. Rungs 1-5 are now partially enforced via quality_gates + hedge_fund_quality_gate.
- Con: Rung timing estimates (e.g., "Commodities Institutional 2026-05-18") were based on cumulative-since-inception numbers (same failure mode as claude_gainer_st blacklist incident). Any promotion must clear `ab_analysis.yml` MATCH + DSR≥0.85 + 30d rolling clean.
- **Action:** Add `ab_analysis.yml` cron result as a hard gate on Rung 5→6 transition. Do not size up on headline PF alone.

**PCG-5 Portfolio Construction Gates — HIGH VALUE, OPEN**
- Pro: Gates 1 (liquidity), 2 (sector correlation), 3 (regime), 4 (drawdown watchdog) are all missing from current runtime. Gate 5 (KS_D > 0.10 triggers mutation) duplicates existing drift detection but with actionable trigger.
- Con: None of these 5 gates have a production caller yet — pure disclosure.
- **Action (P1):** Ship `audit_trail/portfolio_gates.py` with all 5 gate functions wired in shadow-log mode to `audit_dashboard/data/pcg5_log.json`. Zero sizing change until 7-day shadow passes clean.

**ML Gatekeeper (MLG-1) — ALREADY PARTIALLY SHIPPED**
- Pro: The `ml_score < 0.85` reject is now enforced via M-034 (confidence inversion gate, shadow mode). The `confidence_decay > 0.15` logic is not yet wired.
- **Action:** Enable M-034 gate out of shadow (`CRYPTO_CONF_INVERSION_GATE=1`) once 30-day shadow paper confirms no false-reject on elite strategies.

**DB Sync / `at_institutional_picks` table — BLOCKED**
- `DB_PASS_BACKTESTS` GitHub secret not confirmed. User must add to GH secrets before any DB split or new table creation.
- **Action (USER):** `gh secret set DB_PASS_BACKTESTS -R eltonaguiar/findtorontoevents_antigravity.ca`

### Remaining Checklist Status (§6)

- [x] PCG-5 Setup: `portfolio_gates.py` — NOT YET shipped as exec-time REJECT; still disclosure-only
- [x] Hard-Kill: FOREX blocked (FOREX_HARD_DISABLE=1); toxic CRYPTO sources quarantined
- [ ] DB Sync: `ejaguiar1_backtests` not provisioned (blocked by missing GH secret)
- [ ] GitHub Action `institutional-readiness-audit.yml` — not shipped
