# EAGLE Full Strategy Audit — All Asset Classes
**Model/Provider**: Cursor Composer  
**Date/Time**: 2026-05-27T02:25:00 EST  
**Scope**: End-to-end pipeline review — symbol universe → emission → safety gates → Smart Picks → money-ready verdict  
**Sources**: 9 canonical 90-day plans (deduped via `/dedup-md-review`), `money_ready_verdict.json` (2026-05-26), `incidents_enhancements_feed.json`, `DAILY_IDEAS.MD`, [findtorontoevents.ca/audit/incidents.html](https://findtorontoevents.ca/audit/incidents.html), [updates/index.html](https://findtorontoevents.ca/updates/index.html)

---

## Executive Summary

**0/6 asset classes are money-ready.** Policy-clean cohort (2026-05-26 `money_ready_verdict.json`) shows severe degradation vs May-15 plans:

| Class | Verdict (2026-05-26) | n | WR | PF | vs May-15 Plan |
|---|---|---|---|---|---|
| CRYPTO | NOT_READY | 210 | 31.0% | 0.96 | PF 1.30→0.96, WR −15pp |
| FOREX | INSUFFICIENT_DATA | 11 | 9.1% | 0.21 | Collapsed (was n=305) |
| EQUITY | *(not in current verdict JSON — use dashboard)* | ~33 policy-clean | ~33% | ~0.90 | T2 candidate lost |
| COMMODITY | *(dashboard)* | ~28 | ~11% | ~0.31 | COT over-emission exposed |
| ETF | *(dashboard)* | 2 | 50% | 11.99 | INSUFF-N, not actionable |
| BOND | INSUFFICIENT / thin | 8–11 | ~0% | ~0 | De-prioritize |
| FUTURES | INSUFFICIENT_DATA | 11 | 9.1% | 0.48 | n=0 tile was misleading |
| PENNY/MEME | Quarantine | 1–148 | 0–7% | 0–0.19 | Full block required |

**Root causes (ranked):**
1. **Data integrity** — 39% PnL mismatch, 2,531 WON-with-negative-PnL rows, forward_validator frozen 11+ days
2. **Confidence inversion** — conf≥0.9 → ~14% WR; ranker still weights confidence at 10–35%
3. **Direction bias** — FOREX LONG 29% WR vs SHORT 61% PF 2.2+; gates partially fixed but emissions still polluted
4. **Universe pollution** — 179 crypto symbols, 8/18 equity tickers penny/meme, CT=F 57%+ commodity concentration
5. **Proven strategies unwired** — pead_equity (62% OOS WR) in shadow; ETF sector rotation emitter regime-empty

---

## Pipeline End-to-End (Symbol → Gate → Surface)

```
Symbol Universe (config.py / scanner.py)
    ↓
Strategy Emitters (production_scanner, baby_strats, copy_trader, COT, ETF emitters)
    ↓
Elite Scorer + ML Composite (elite_scorer.py, smart_picks_engine._compute_ml_composite)
    ↓
passes_active_gate() — BLOCKED_SOURCE_SYSTEMS, direction triples, ADV, VIX, RR, concentration
    ↓
passes_smart_gate() — trust, forward WR, Bonferroni (partial), HF strict (opt-in)
    ↓
Smart Picks Engine — rank, dedupe, tier (smart_picks_engine.py → smart_picks.json)
    ↓
Dashboard / MySQL sync / money_ready_verdict.py
```

**Critical observation**: Gates are **asymmetric** — they block some bad picks but also block good SHORT FOREX and low-VIX EQUITY momentum while letting high-VIX momentum and LONG FOREX through historically.

---

## Safety Gate Forensics — Big Winners We Filtered Out?

### Yes — documented cases where gates destroyed edge

| Case | Asset | Evidence | Gate that blocked | Exemption? |
|---|---|---|---|---|
| **FOREX SHORT bias** | FOREX | LONG 80% vol @ 29% WR; SHORT PF 8.11 n=29 | LONG direction allowed for years; partial blocks added 2026-05 | **No exemption** — hard block LONG until LONG PF>1.0 rolling 30d |
| **ig_contrarian SHORT** | FOREX | SHORT WR 61.4% PF 2.24 n=57 | Global block removed 2026-05-25; LONG still blocked | SHORT already unblocked — no streak exemption needed |
| **PEAD equity** | EQUITY | 62.2% OOS WR WF-verified | Shadow-only (`PEAD_EQUITY_ENABLED=0`) | **Promote to probation** — not gate exemption, promotion |
| **VIX-filtered momentum** | EQUITY | VIX<20: PF 5.37 WR 75% backtest | VIX gate branch exists but unmerged (`feat/equity-vix-regime-gate-sidecar`) | Wire gate — blocks bad picks, doesn't exempt |
| **Low-conf CRYPTO** | CRYPTO | conf 0.5–0.6 → ~60% WR vs conf≥0.9 → ~14% | Ranker promotes high conf (incident #17) | **Invert conf for ranking** (QW executed, env-gated) |
| **ETF sector rotation** | ETF | Backtest PF 2.05–3.22 | Emitter enabled but **0 picks** — no sector above SMA200+3m momo (regime, not gate) | No exemption — wait for regime or lower threshold in shadow |

### No — do NOT exempt (false “hot streaks”)

- PENNY/MEME small-n 100% WR (PNUT 7/7) — selection bias
- COMMODITY cotton 7d PF 44 — COT over-emission artifact
- SUPREME EDGE 82% WR cells — post-hoc segment search (incident #16)

### Hot-streak exemption — recommended design (not built)

Use **probation promotion**, not gate bypass:

```sql
-- Proposed: strategy_hot_streak (see DB schema section)
-- IF rolling_14d WR >= 60% AND n >= 20 AND PF >= 1.5 AND DSR >= 0.85
-- THEN trust_tier = 'PROBATION_PLUS' → relax ONLY min_confidence by 0.05, never RR or concentration
```

Never exempt: concentration caps, RR floor, BLOCKED_SOURCE_SYSTEMS, Bonferroni on promotion.

---

## Oscillating / Range-Bound “Sure Things”

These pairs show repeated two-level oscillation — edge is **regime-conditional**, not automatic:

| Symbol | Range / Mechanism | Strategy | Gate requirement |
|---|---|---|---|
| **USDJPY=X** | 147–155, BoJ intervention ~152+ | SHORT at 151+ tight SL | DXY confluence + session filter |
| **GC=F** | $2,000–$2,500 + COT commercial extremes | Fade at commercial net SHORT extreme | COT MATCH + 3d lag + 1 pick/week |
| **BTCUSDT** | ±15% around 200d EMA | Funding rate extreme reversal 48–72h | ADV>$10M, conf inverted |
| **NG=F** | Seasonal storage cycle | LONG when EIA storage < 5yr avg (Oct–Nov) | Carry_momo sidecar, not raw COT |
| **EURUSD=X** | Mean-revert to 200d MA after 3%+ dev | MeanReversionBB SHORT (PF 2.09 n=44) | Block DXY-unaware trend LONG |

**New module proposal**: `alpha_engine/range_oscillator_gate.py` (opt-in) — detects price within 2% of historical intervention/support level; distinct from generic mean-reversion.

---

## Top-Notch Strategy Per Asset Class

### CRYPTO — Liquid-25 + On-Chain + Funding
- **Universe**: BTC, ETH, SOL + top 22 by ADV>$10M; remove 9 meme + illiquid alts
- **Strategy**: MVRV-Z on-chain (`CRYPTO_ONCHAIN_MOMENTUM_ENABLED=1`) + funding carry + M-001 BTC UTC hour filter (reject 08–09Z)
- **Sources whitelist**: `dna_winner_picks`, `mega_mutation`, `kimi_riseoftheclaw`, `baby_strats_forward` only
- **Gates**: ADV>$10M, conf inverted for rank, trust≥0.6, slippage 15bps
- **Target**: PF>1.5, WR>50%, n≥100 clean

### EQUITY — VIX-Regime Large-Cap Momentum + PEAD
- **Universe**: 30 LC (AAPL, MSFT, NVDA, …); quarantine GME/AMC/NIO/LCID/RIVN/SNDL
- **Strategy**: 12-1 momentum top-5 + PEAD (`pead_equity` probation) + ConnorsRSI2 on SPY/QQQ
- **Gates**: VIX<22 hard block, SPY>200SMA, factor score
- **Target**: PF>2.5, WR>60% (backtest-supported with VIX gate)

### ETF — SPDR Sector Rotation + VIX Skip
- **Universe**: 11 SPDR sectors + IWM
- **Strategy**: Faber TAA 10mo SMA + Antonacci 12-1 top-3 long-only; skip month when VIX>25
- **Enable**: `ETF_SECTOR_EMITTER_ENABLED=1` (already in `alpha-engine-etf.yml`)
- **Target**: PF 2.05–3.22 backtest; paper until 30d live PF>1.6

### COMMODITY — Deduped Multi-Symbol COT
- **Universe**: CT=F, GC=F, KC=F, SB=F, ZC=F, ZS=F, HG=F, NG=F, SI=F, CC=F; cap 25% PnL/symbol
- **Strategy**: CFTC COT commercial extreme, **1 signal per weekly release**, 3d lag
- **P0**: Re-derive all historical PF post-PR-#994 dedup before any Tier claim
- **Target**: PF>1.5, n≥20 clean cycles

### FOREX — SHORT-Only 4 Majors (Paper)
- **Universe**: EURUSD, GBPUSD, AUDUSD, USDJPY only
- **Strategy**: SHORT via `ig_contrarian`, MeanReversionBB, `cta_fx`; live FRED carry
- **Gates**: FOREX LONG blocked (already in `passes_smart_gate`); M-007 HARD_DISABLE until paper PF>1.3
- **Target**: 30d paper SHORT-only → promote or kill class

### BOND — Research Only
- **Universe**: TLT, IEF, LQD, HYG, TIP
- **Strategy**: TIPS MR + HYG-LQD credit spread MR; MOVE>130 skip
- **Gates**: sizing=False until n≥50; `BOND_ELITE_FLOOR=32`
- **Target**: Track only — no sizing until n≥100

### FUTURES — Merge Tile / Micro Pilots
- **Action**: Deprecate empty FUTURES tile; reclassify ES/NQ→EQUITY, ZN/ZB→BOND, GC/SI/HG→COMMODITY
- **Pilots**: `mes_overnight_drift`, `mgc_asia_mean_reversion` on micros
- **Target**: n≥30 per pilot before UI tile

### PENNY / MEME / IPO — Quarantine or Build
- **PENNY/MEME**: Full `RESEARCH_ONLY` — zero production emissions
- **IPO**: Honest UI caveat now; MVP scanner (EDGAR S-1 + lockup + PEAD) in 3h build

---

## Incidents / Enhancements Dashboard Items (Itemized)

Map new work to [incidents.html](https://findtorontoevents.ca/audit/incidents.html) categories:

### P0 Incidents (fix before sizing)
| ID | Title | Component | Fix PR |
|---|---|---|---|
| INC-10 | PnL integrity 39% mismatch | `trading_picks.pnl_pct` | Re-resolve via `re_resolve_historical_v2.py` |
| INC-11 | WON rows avg −41% PnL | outcome_resolver | SQL relabel + resolver fix |
| INC-15 | sync_active_mysql_picks_to_json missing | forward_validator chain | `alpha_engine/active_picks_sync.py` |
| INC-16 | SUPREME EDGE post-hoc caveat missing | template.html | Add Bonferroni caveat |
| INC-17 | Confidence inverts ranker | smart_picks_engine.py | **QW-01** `CONFIDENCE_INVERT_CRYPTO=1` |
| NEW | forward_validator frozen 270h+ | forward_validator.py | Restart + EXPIRED backlog |
| NEW | CRYPTO 48h zero closes | resolver | Same as validator |

### P1 Enhancements (edge recovery)
| ID | Title | Asset | Fix |
|---|---|---|---|
| ENH-PEAD | Promote pead_equity shadow→probation | EQUITY | PR-QW-02 after 2026-06-14 gate OR early probation |
| ENH-VIX | Merge equity VIX regime sidecar | EQUITY | PR-QW-06 |
| ENH-ETF | ETF sector rotation live picks | ETF | Emitter enabled; monitor regime |
| ENH-FOREX | SHORT-only enforcement | FOREX | Already in smart_gate; verify active_gate |
| ENH-COT | COMMODITY post-dedup re-derive | COMMODITY | SQL + dashboard regen |
| ENH-PENNY | Quarantine penny/meme from prod | EQUITY/CRYPTO | PR-QW-08 |
| ENH-RANGE | Range oscillator gate module | FOREX/COMMODITY | New opt-in sidecar |

---

## Proposed Database Schema — Roadmap Registry

Replace scattered JSON (`incidents_enhancements_feed.json`, hypothesis registry, M-### backlog) with queryable MySQL in `ejaguiar1_stocks`:

```sql
CREATE TABLE audit_roadmap_items (
  id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  item_type           ENUM('INCIDENT','ENHANCEMENT','STRATEGY','MILESTONE') NOT NULL,
  asset_class         ENUM('OVERALL','CRYPTO','EQUITY','ETF','FOREX','COMMODITY','BOND','FUTURES','PENNY_MEME','IPO') NOT NULL DEFAULT 'OVERALL',
  priority            ENUM('P0','P1','P2','P3') NOT NULL DEFAULT 'P2',
  status              ENUM('OPEN','IN_PROGRESS','BLOCKED','DONE','WONT_FIX') NOT NULL DEFAULT 'OPEN',
  m_number            VARCHAR(16) NULL COMMENT 'e.g. M-001, M-107',
  title               VARCHAR(255) NOT NULL,
  description         TEXT,
  affected_component  VARCHAR(255),
  recommended_fix     TEXT,
  success_metric      VARCHAR(512),
  evidence_path       VARCHAR(512) COMMENT 'reports/ or updates/ relative path',
  github_pr_url       VARCHAR(512),
  source_report       VARCHAR(255) COMMENT 'e.g. asset_class_90day_plan_CRYPTO_2026-05-15.md',
  depends_on_id       INT UNSIGNED NULL,
  assigned_to         VARCHAR(64),
  reported_by         VARCHAR(64),
  created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  resolved_at         DATETIME NULL,
  INDEX idx_class_status (asset_class, status),
  INDEX idx_priority (priority, status),
  INDEX idx_m_number (m_number),
  FOREIGN KEY (depends_on_id) REFERENCES audit_roadmap_items(id) ON DELETE SET NULL
);

CREATE TABLE audit_roadmap_item_links (
  roadmap_id    INT UNSIGNED NOT NULL,
  link_type     ENUM('MD','URL','GITHUB','INCIDENT_DUP') NOT NULL,
  link_value    VARCHAR(1024) NOT NULL,
  PRIMARY KEY (roadmap_id, link_type, link_value(255)),
  FOREIGN KEY (roadmap_id) REFERENCES audit_roadmap_items(id) ON DELETE CASCADE
);
```

**Seed command**: `python3 tools/audit_pick_funnel/seed_incidents_enhancements.py --migrate-to-db` (to be built) reads `incidents_enhancements_feed.json` + this EAGLE audit → upserts rows.

**Dashboard wiring**: `incidents.html` fetches from `/audit/data/incidents_enhancements_feed.json` today — add optional MySQL refresh step in `audit-dashboard.yml` to merge DB + JSON until cutover.

---

## PR Stack (see companion quick-wins MD)

Execute order: P0 data fixes → ranker invert → direction blocks → strategy promotions → universe trims.

**Executed this session:**
- QW-01: `CONFIDENCE_INVERT_CRYPTO` env flag in `smart_picks_engine.py` (default OFF)
- Skill: `/dedup-md-review` updated with `dedup_md_files.py --from-file` workflow

**Already done in repo:**
- QW-03: `ETF_SECTOR_EMITTER_ENABLED=1` in `alpha-engine-etf.yml`
- FOREX LONG block in `passes_smart_gate` (lines ~7249+)
- ig_contrarian SHORT unblocked (2026-05-25)

---

## DAILY_IDEAS.MD Cross-Reference

| Idea | Priority | Status | Tie to audit |
|---|---|---|---|
| IDEA-A (20-round criteria per class) | High | Partial (90-day plans done) | Execute M-001, VIX gate, COT dedup |
| IDEA-H (Polymarket→macro) | Medium | Wired in prod | Extend to equity overlay |
| IDEA-E (8-K partnerships) | Low (4.5/10) | DEFER | After P0 fixes |
| IDEA-B (Penny revisit) | Block | QUARANTINE | PR-QW-08 |
| Hot streak / copy-trader EXEMPT | Research | Dual-mode in extracted_strategies.json | Use probation tier, not full exempt |

---

## Canonical Files Read (deduped)

```
reports/90day_gap_analysis_2026-05-15.md
reports/asset_class_90day_plan_{BOND,COMMODITY,CRYPTO,EQUITY,ETF,FOREX,FUTURES,PENNY_MEME}_2026-05-15.md
```

81 worktree duplicate paths suppressed (when present on Windows host).

---

*Generated by Cursor Composer — EAGLE audit 2026-05-27 EST*
