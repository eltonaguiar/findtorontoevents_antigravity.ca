---
tags: [index, home]
created: 2026-06-06
---

# FindTorontoEvents — Trading Knowledge Base

Central index for all trading research, strategy analysis, incident logs, and session notes.

---

## Quick Navigation

### 📊 Asset Classes
- [[asset-classes/CRYPTO]]
- [[asset-classes/EQUITY]]
- [[asset-classes/FOREX]]
- [[asset-classes/COMMODITY]]
- [[asset-classes/ETF]]
- [[asset-classes/BOND]]

### 🧠 Strategies
- [[strategies/strategy-catalog-clean-cohort]] — ⭐ live DB clean-cohort per-strategy stats (honest WR/PF)
- [[strategies/mega_mutation]] — ⚠️ T1 REFUTED on clean data (raw n=204 is NULL-timestamp; clean n=13/30.8%)
- [[strategies/fx_smart_carry_trade_momentum]] — T2 candidate (PF 1.85 / n=25 OOS-robust)
- [[strategies/etf_verified_dual_momentum]] — ETF pilot wired (PF 1.60)

### 🔥 Incidents & Decisions
- [[incidents/incidents-live-summary]] — ⭐ live INCIDENT_*/ENHANCEMENT_* counts + /audit/incidents.html
- [[incidents/clean-cohort-6day-snapshot-2026-06-09]] — ⭐ WHY no edge is measurable: clean cohort is 83% one 6-day window
- [[incidents/resolver-keyspace-gap-2026-06-09]] — universal_v2 outcomes orphaned from trading_picks intrabar (but already conservative first-touch)
- [[incidents/resolver-intrabar-blocker]] — upstream T2 blocker
- [[incidents/ai-tournament-wr-artifact]] — 73-91% WR = single-snapshot artifact

### 📅 Sessions
- [[sessions/2026-05-18-autonomous-audit-completion]]
- [[sessions/2026-06-05-session4-deliverables]]
- [[sessions/2026-06-06-money-ready-picks]]
- [[sessions/2026-06-06-edge-audit-and-resolver-fix]] — ⚠️ edge reality check: 0 confirmed edges
- [[sessions/2026-06-09-rescue-fixes-and-benefits]] — ⭐ recent fixes + their benefits (changelog)
- [[sessions/2026-06-09-8h-quant-gaps-and-edge-diagnosis]] — ⭐ 8h loop: 10 commits, HHI P0 closed, daily-breaker restored, 6-day-snapshot finding

### 📋 Reference
- [[reference/reports-map]] — ⭐ MOC: navigable index of the decision-grade `reports/*.md` (of 1,546)
- [[reference/personas-and-research-index]] — ⭐ per-class web-research state + hedge-fund persona catalog
- [[reference/edge-rescue-roadmap]] — ⚠️ how we get from 0 edge to money-ready (SAVE-1..5)
- [[reference/performance-tiers]] — T1/T2/T3 thresholds
- [[reference/banned-sources]] — BANNED_SOURCES gate list
- [[reference/data-quality-checklist]] — admissibility pipeline

---

## Performance Tier Targets

| Tier | PF | WR | MDD |
|------|----|----|-----|
| T1 (Renaissance) | >2.0 | >55% | <10% |
| T2 (Hedge Fund) | >1.5 | >50% | <20% |
| Fail | <1.5 | — | — |

> **Only T2+ classes get sized up. Verify 14d/48h panels before acting on historical numbers.**

---

## Current Status (2026-06-09)

> **0/9 asset classes pass Tier-2 money-ready gates.** Clean-cohort screen: **0 confirmed survivors.**
> Full vault cross-check: `reports/OBS_FINDING_JUNE8.MD` | Roadmap: [/audit/edge_validation_roadmap.html](https://findtorontoevents.ca/audit/edge_validation_roadmap.html)

- **T1 REFUTED (2026-06-09):** `mega_mutation` "PF 2.86/n=204" is raw `trading_picks` (100% NULL created_at). Clean `at_pick_outcomes` = n=13, 30.8% WR, PF 0.57 (honest June resolver: 4/9 LOST). NOT money-ready.
- **T2 candidates:** `fx_smart_carry_trade_momentum` (FOREX, n→100 ~5-6wk)
- **Paper pilots active:** ETF dual-momentum (daily cron 06:15Z)
- **Blockers:** intrabar truth now wired into the verdict (`acc551cd8f`), BUT the **clean cohort is a ~6-day snapshot** (83% resolved 2026-05-31→06-05) → no durable edge is *measurable* yet regardless of strategy. The lever is calendar time, not code. See [[incidents/clean-cohort-6day-snapshot-2026-06-09]]; re-run the edge sweep in 3-6 weeks.
- **Gates hardened 2026-06-09:** HHI fail-closed (P0 closed), daily-loss breaker re-enabled (guarded), DSR/PBO confirmed enabled. See [[sessions/2026-06-09-8h-quant-gaps-and-edge-diagnosis]].

---

*Vault opened in Obsidian: open this folder as a vault. All search is full-text via Ctrl+F (in-note) or Ctrl+Shift+F (global search).*
