# EAGLE Remaining Items — Kimi K2.6 Cloud Backlog
**Date:** 2026-05-27 02:31 EDT | **Model:** Kimi K2.6 (via Cloud)  
**Branch:** `eagle-quickwins-2026-05-27`  
**Depends on:** `reports/EAGLE_quick_wins_2026-05-27_0231_EDT_Kimi_K2.6_Cloud.md`

---

## Direct Answers to User Questions

### Q1: Do we have picks that would have won big, but safety gates filtered them out?

**Answer: YES — but we cannot prove it without the audit lane.**

Evidence:
- **FOREX 48h contradiction:** `pick_summary_stats_48h` shows 86.2% WR / PF 6.35 on recent USDCAD=X LONG picks, while `money_ready_verdict` shows 9.1% WR. If the 48h data is correct, the FOREX directional gate (blocking LONGs with elite<75) may have filtered winners in the past that are now resolving positively. However, the 48h data could also be a classification bug — hence PR-2 in the quick-wins doc.
- **FUTURES ConnorsRSI2:** Blocked historically under BLOCKED_STRATEGIES or misrouted to COMMODITY. The 13/13 YM=F winners in 48h suggest prior rejections may have been false negatives.
- **Confidence 0.85-0.90 band:** Already corrected in `quality_gates.py` (M-034 threshold raised from 0.85 → 0.90 after Kimi live-site analysis showed 82% WR in 0.85-0.90 band). This WAS a confirmed case of gate-filtered winners.

Without a `rejected_picks_audit` table (PR-8), these are hypotheses. The honest answer: **we don't know for sure, and that ignorance is itself a P0 risk.**

### Q2: Do some picks deserve exemption to safety gates?

**Answer: No blanket exemptions. Bounded, auditable, time-boxed exemptions are defensible.**

Rules for any exemption:
1. **Evidence over rolling window:** n≥30 clean trades, PF>1.5, WR>50%, DSR>0.85
2. **Per-sleeve, not per-class:** Exempt "ConnorsRSI2 on YM=F" not "all FUTURES"
3. **Time-boxed:** Max 30-day exemption, auto-revoke if rolling 10-trade WR drops below 45%
4. **Audit trail:** Every exemption decision logged to `exemption_log.json` with timestamp, rationale, evidence hash
5. **Human review:** 7-day peer-review window before any exemption affects sizing

The `_STREAK_CACHE` in `quality_gates.py` (line 258) computes per-strategy streaks but is **never used for admission decisions**. It should be wired to a bounded exemption engine.

### Q3: Do certain trades fluctuate between 2 prices and are basically a sure thing?

**Answer: No "sure thing" exists. The closest evidence is bounded mean-reversion on broad-index futures.**

| Candidate | Evidence | Confidence |
|---|---|---|
| **ConnorsRSI2 on YM=F** | 13/13 wins in 48h, +1.95% per trade, ~20K min holds | Medium — needs n>30 paper |
| **ETF SPY-QQQ pair reversion** | Theoretical; no live track record in system | Low |
| **Bond credit-spread MR** | Academic (HYG-LQD) but unwired; n=0 in prod | Low |
| **Major FX rangebound** (USDCAD in low-vol regimes) | 48h data supportive but regime-dependent | Low-Medium |

**Critical caveat:** "Fluctuates between 2 prices" implies a stationary, bounded process. Real markets are non-stationary. A strategy that looks like a "sure thing" for 13 trades can blow up on trade 14 when regime shifts. The correct posture is: **treat oscillation strategies as high-frequency, low-duration pilots with hard regime-change stops.**

---

## Batch A — Observability & Governance (next 7 days)

### PR-009: Rejected Picks Audit Lane (completes PR-8)
- Schema + cron + dashboard panel
- Files: `audit_trail/rejected_picks_logger.py`, `audit_dashboard/template.html` (new panel)

### PR-010: Hot-Streak Exemption Engine
- Wire `_STREAK_CACHE` to admission logic with bounded rules (see Q2 above)
- Files: `audit_trail/streak_exemption_engine.py`, `audit_trail/quality_gates.py` (import + call)

### PR-011: Oscillation-Detection Scanner
- Auto-flag symbols with 14d RSI(2) mean-reversion behavior (RSI(2)<10 → bounce within 3 days >50% of time)
- Files: `tools/oscillation_scanner.py`
- Output: `oscillation_candidates.json` consumed by `futures_strategies.py` + `etf_strategies.py`

### PR-012: Unified `findings` Database Table
- Replace split INCIDENT_/ENHANCEMENT_ families with one lifecycle model
- See schema proposal below

---

## Batch B — Asset-Class Corrective PRs (next 14 days)

### EQUITY
1. **Merge VIX regime sidecar branch** (`feat/equity-vix-regime-gate-sidecar-2026-05-13`) — backtest PF 5.37
2. **PEAD strategy on top-100 LC** (M-009) — earnings post-announcement drift
3. **Overnight intraday reversal** (M-025) — module not created
4. **DOW tilt** (M-026) — Tue/Wed long bias hook in score_booster

### ETF
5. **Antonacci sector dual momentum 12-1** (M-023) — module not created
6. **Black-Litterman with Ledoit-Wolf fix** — prior LinAlgError on rolling cov
7. **FRED economic momentum** — blocked on no FRED_API_KEY

### COMMODITY
8. **COT MATCH gate + DSR≥0.85** (M-008) — verify_system_pf.py shipped but not called
9. **Carry-momo double-sort sidecar** (M-022) — Miffre 2010 replication
10. **Re-derive PF/WR post-PR-#994** — P0 data integrity

### FOREX
11. **Live carry_yield_diff from FRED** — replace static snapshot
12. **4-major universe limit** — EURUSD, GBPUSD, AUDUSD, USDJPY only
13. **Real CFTC COT data for 6E/6B/6J** — proxy z-score is noise

### CRYPTO
14. **BTC UTC-hour death-zone filter** (M-001) — 08-09Z reject, 22Z boost
15. **ADV minimum gate (>$1M)** in production path
16. **On-chain momentum enable** (Glassnode MVRV-Z)

### BOND
17. **FRED_API_KEY in GitHub secrets** (M-032)
18. **TIPS-Treasury breakeven MR** — Fleckenstein-Longstaff-Lustig 2014 pilot
19. **Cochrane-Piazzesi curve-carry** — TLT/IEF/SHY momentum
20. **HYG-LQD credit-spread MR** — 2σ bounce pilot

### FUTURES
21. **Unify futures taxonomy** — merge empty FUTURES tile into COMMODITY or standalone
22. **Micro contract support** — MES, MNQ, MGC
23. **Asia overnight MR pilot** — MGC/JPY futures

### PENNY / MEME / IPO
24. **Permanent quarantine enforcement** — 0% risk, block all emitters
25. **IPO post-listing momentum** — replacement for failed lockup-short (PR-6)
26. **Cheap-stock (<$5) ADV gate** — no emission if float < $10M ADV

---

## Database Schema Proposal: Unified `findings` Table

### Problem
Today, incidents and enhancements live in:
- `audit_dashboard/incidents.html` (static HTML)
- `reports/incidents_*.md` (scattered markdown)
- `updates/index.html` (update cards)
- No SQL table links findings to PRs, reports, or asset classes

### Proposed Schema

```sql
CREATE TABLE findings (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    finding_type    ENUM('incident','enhancement','roadmap','investigation') NOT NULL,
    asset_class     VARCHAR(32),
    severity        ENUM('P0','P1','P2','P3'),
    impact          ENUM('critical','high','medium','low'),
    status          ENUM('open','investigating','resolved','deferred','wontfix') DEFAULT 'open',
    title           VARCHAR(255) NOT NULL,
    summary         TEXT,
    component       VARCHAR(128),  -- e.g. 'quality_gates.py:1690'
    recommended_fix TEXT,
    owner           VARCHAR(64),
    reporter        VARCHAR(64),
    source_doc_path VARCHAR(512),
    parent_id       INT NULL,
    canonical_hash  VARCHAR(64),   -- SHA-256 of evidence blob
    evidence_json   JSON,
    created_at      DATETIME DEFAULT NOW(),
    updated_at      DATETIME DEFAULT NOW() ON UPDATE NOW(),
    closed_at       DATETIME NULL,
    INDEX idx_type_class (finding_type, asset_class),
    INDEX idx_status_severity (status, severity),
    INDEX idx_component (component),
    INDEX idx_reporter (reporter),
    FOREIGN KEY (parent_id) REFERENCES findings(id)
);

CREATE TABLE finding_events (
    id          INT PRIMARY KEY AUTO_INCREMENT,
    finding_id  INT NOT NULL,
    event_type  ENUM('status_change','severity_change','assignment','comment','evidence_add','pr_link'),
    old_value   VARCHAR(255),
    new_value   VARCHAR(255),
    actor       VARCHAR(64),
    event_at    DATETIME DEFAULT NOW(),
    payload_json JSON,
    FOREIGN KEY (finding_id) REFERENCES findings(id)
);

CREATE TABLE finding_links (
    id          INT PRIMARY KEY AUTO_INCREMENT,
    finding_id  INT NOT NULL,
    link_type   ENUM('pr','report','commit','dashboard_url','external'),
    link_url    VARCHAR(1024),
    link_title  VARCHAR(255),
    FOREIGN KEY (finding_id) REFERENCES findings(id)
);
```

### Migration Path
1. Backfill from existing `reports/incidents_*.md` via parser
2. Wire `audit_trail/dashboard_generator.py` to read `findings` table for `/audit/incidents.html`
3. Replace static HTML with server-rendered or JSON-hydrated page
4. Add `finding_id` to every PR template so PRs auto-link

---

## Top-Notch Strategy Per Asset Class (Kimi Recommendation)

| Class | Strategy | Rationale | Expected PF | Evidence Quality |
|---|---|---|---|---|
| **CRYPTO** | Liquid Core 25 + source whitelist + on-chain MVRV-Z | Shrink to BTC/ETH/SOL + top 7 L1s; block diluters | 1.45-1.60 | Medium — needs 30d paper |
| **EQUITY** | VIX<22 + 12-1 momentum on 30 LC + PEAD overlay | Backtest PF 5.37; merge existing branch | 2.50-3.50 | High — backtest proven |
| **ETF** | 11-Sector Rotation + VIX<25 + dual momentum | Faber/Antonacci academic; backtest PF 3.22 | 2.00-3.00 | High — backtest proven |
| **COMMODITY** | Miffre carry-momo double-sort + COT dedup | Real edge; COT headline is artifact | 1.50-2.00 | Medium — unwired |
| **FOREX** | 4-major SHORT-only + DXY confluence + session gate | SHORT PF 8.11 vs LONG PF 0.80; isolate winners | 1.30-1.50 | Low-Medium — small n |
| **BOND** | TIPS-Treasury breakeven MR + curve carry + credit MR | 3 academic pilots; research-only | Unknown | Low — no live data |
| **FUTURES** | ConnorsRSI2 on YM=F + micro Dow pilot | 13/13 in 48h; oscillation capture | 1.50-2.50 | Medium — needs n>30 |
| **PENNY** | **NO PRODUCTION STRATEGY** | Quarantine permanently | N/A | N/A |
| **MEME** | **NO PRODUCTION STRATEGY** | Quarantine permanently | N/A | N/A |
| **IPO** | Post-listing momentum avoidance (90d long, SPY>200SMA) | Lockup short failed; pivot to momentum | Unknown | Low — needs backtest |
| **Cheap Stocks (<$5)** | **NO PRODUCTION STRATEGY** | Same as PENNY; ADV <$10M = block | N/A | N/A |

---

## Incidents / Enhancements Dashboard Items

### New INCIDENT Rows (suggested)

| # | Type | Class | Priority | Title | Evidence |
|---|---|---|---|---|---|
| INC-029 | INCIDENT | FOREX | **P0** | 48h stats contradict money_ready verdict by 77pp WR | `pick_summary_stats_48h` vs `money_ready_verdict.json` |
| INC-030 | INCIDENT | ETF | P1 | WIN_RATE_TRAP_BLACKLIST orphaned — IWM/GLD still emitting | `quality_gates.py:1690` |
| INC-031 | INCIDENT | CRYPTO | **P0** | 0 closed in 48h (322 active) — class stalled | `pick_summary_stats_48h.json` |
| INC-032 | INCIDENT | OVERALL | P1 | No rejected-picks audit lane — cannot answer "what did we miss?" | Missing table |
| INC-033 | INCIDENT | FUTURES | P2 | 70% of =F activity misrouted to COMMODITY | Known from prior audits |
| INC-034 | INCIDENT | IPO | P2 | Lockup short strategy backtest FAILED all gates | `ipo_lockup_backtest_2026-05-17.md` |

### New ENHANCEMENT Rows (suggested)

| # | Type | Class | Impact | Title |
|---|---|---|---|---|
| ENH-025 | ENHANCEMENT | OVERALL | HIGH | Unified `findings` SQL table + dashboard renderer |
| ENH-026 | ENHANCEMENT | OVERALL | HIGH | Bounded hot-streak exemption engine with audit trail |
| ENH-027 | ENHANCEMENT | OVERALL | MEDIUM | Oscillation-detection scanner (RSI(2) mean-reversion flag) |
| ENH-028 | ENHANCEMENT | FUTURES | HIGH | ConnorsRSI2 YM=F → micro Dow paper pilot |
| ENH-029 | ENHANCEMENT | EQUITY | HIGH | PEAD earnings-drift sleeve on clean LC universe |
| ENH-030 | ENHANCEMENT | CRYPTO | HIGH | Source whitelist + noisy-source quarantine |
| ENH-031 | ENHANCEMENT | IPO | MEDIUM | Post-listing momentum strategy (replacement for lockup short) |
| ENH-032 | ENHANCEMENT | COMMODITY | HIGH | Carry-momo double-sort wiring (Miffre 2010) |
| ENH-033 | ENHANCEMENT | FOREX | MEDIUM | Live carry_yield_diff from FRED (not static snapshot) |
| ENH-034 | ENHANCEMENT | BOND | MEDIUM | TIPS/curve/credit MR pilot trio |

---

## Verification Plan
- `py_compile` on all touched `.py` files
- `python3 tools/dedup_md_files.py --paths-only` on any batch review
- No local dashboard generation (per CLAUDE.md)
- Git push to origin/main after pull --rebase

---

## References
- `reports/EAGLE_quick_wins_2026-05-27_0231_EDT_Kimi_K2.6_Cloud.md`
- `reports/EAGLE_end_to_end_review_2026-05-27_claude_opus_4_7.md`
- `updates/REMAINING_ITEMS_EAGLE_2026-05-27_0217_EST_GPT-5.4_OpenAI.md`
- `audit_dashboard/data/pick_summary_stats_48h.json`
- `audit_dashboard/data/money_ready_verdict.json`
- `audit_trail/quality_gates.py:1690`
- `reports/ipo_lockup_backtest_2026-05-17.md`
