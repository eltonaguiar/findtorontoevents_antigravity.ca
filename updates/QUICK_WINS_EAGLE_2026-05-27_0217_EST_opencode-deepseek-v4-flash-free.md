# Quick Wins — EAGLE Session 2026-05-27
**Model:** opencode / deepseek-v4-flash-free  
**Timestamp:** 2026-05-27 02:17 EST  
**Source:** End-to-end pipeline audit (symbol universe → strategies → safety gates → dashboard)

---

## P0 — Fix Confidence-Inversion in smart_picks_engine.py

**Problem:** `_compute_ml_composite()` at `alpha_engine/smart_picks_engine.py:65` weights confidence at 10% (already dropped from 30% on 2026-05-25 after Spearman IC measured at 0.07). But the fallback path (`ml_score` is None) uses `conf * 0.8 * ml_null_penalty(0.5)` — producing scores of ~0.34 from a 0.85-confidence pick with no ML score. This structurally passes picks with high confidence but zero ML evidence.

**Evidence:** Pool-wide Spearman(confidence, pnl) = 0.07 (n=3500). CRYPTO confidence band 0.85-0.95 has WR ~20% (anti-predictive). The 0.10 weight still lets inverted confidence leak through for picks with ml_score > 0 because `ml_val * 0.75 + conf * 0.10 + fwd_wr * 0.15` — a high confidence pick with mediocre ml_score still scores well.

**Fix:** `alpha_engine/smart_picks_engine.py` line 105 — change `_w_ml, _w_conf, _w_fwd = 0.75, 0.10, 0.15` to `0.82, 0.03, 0.15`. This slams confidence to near-zero (matching its measured IC), shifts freed weight to ml_score (the only positive-signal dimension at IC=0.33).

**Risk:** Low. Confidence was already proven anti-predictive. If ml_score is sparse for non-CRYPTO classes, the fallback path (conf * 0.8 * 0.5) still applies but at least the primary path stops amplifying noise.

---

## P0 — Rehabilitate CT=F (Cotton) from HOLD_KILLED_PENDING_DATA

**Problem:** `alpha_engine/data/active_picks.json` has CT=F on HOLD_KILLED_PENDING_DATA citing "8.3% WR / n=12". The actual resolver-v2 ledger shows CT=F at **66.7% WR / PF 3.50 / +32.30% PnL**. The kill panel used wrong sample sizes (same "n=12 WR 8.3%" string appears for GC=F and KC=F — copy-paste error).

**Fix:** 
1. Remove CT=F from `HOLD_KILLED_PENDING_DATA` in production_scanner.py
2. Add CT=F back to COMMODITY symbol universe in `alpha_engine/config.py`
3. Document the kill-panel copy-paste error in the incident log

**Risk:** Low-Medium. CT=F is a single symbol with n=15 closed. The 66.7% WR is on a small sample but the ledger is unambiguous. Monitor next 20 CT=F picks.

---

## P1 — COMMODITY Filter-Survival Gap Patch

**Problem:** Dashboard WR=85.5% (n=228) vs raw WR=60.2% (n=354) — the 126 excluded picks are concentrated in losing strategies (cta_replicator, combined_confidence). The gap hides that 35% of emitted picks are filtered out, and those filtered picks cluster in losing cohorts.

**Fix:** Add a `filter_survival_gap` metric to the dashboard JSON that reports `(n_before_gates - n_after_gates) / n_before_gates` per strategy per asset class. When >30%, flag the strategy for review. File: `audit_trail/dashboard_generator.py`.

**Risk:** Low. Pure observability — doesn't change gate behavior, just makes the filter burden visible.

---

## P1 — ADX Range-Gated Mean Reversion Wrapper

**Problem:** Crypto spends 60-70% of time range-bound (ADX < 20). Current MR strategies fire during ALL market conditions, including trends where they get destroyed. The `adx_range_mean_reversion.py` strategy (`baby_strategies/adx_range_mean_reversion.py`) already implements this gate but is not wired to production.

**Winners (existing survivors that would benefit):**
- Connors R3 (71.9% WR, Sharpe 1.54, n=750) — Best overall survivor
- Keltner Mean Reversion (68.3% WR, Sharpe 2.02, PF 2.77) — Highest Sharpe in survivor pool
- Connors RSI-2 (68.6% WR, n=849) — Most tested
- VWAP Mean Reversion (64.5% WR, n=722)

**Fix:** Create `alpha_engine/adx_regime_gate.py` — a lightweight wrapper that checks ADX(14) < 25 before allowing mean-reversion entries. Wire it as an opt-in gate in `quality_gates.py:passes_active_gate` around line 7150 (alongside the existing regime filter sidecar). Default OFF, enable for CRYPTO mean-reversion strategies first.

**Risk:** Low-Medium. ADX is a 3-line calculation. The gate defaults OFF. Enabling it for CRYPTO MR strategies prevents trend-period losses (estimated +5-8% WR improvement on MR cohort based on ADX-regime backtest in survivor pool).

---

## P1 — Wire Connors R3 Survivor to EQUITY and FOREX Production

**Problem:** Connors R3 is a SURVIVOR (71.9% WR, Sharpe 1.54, n=750 across 24 symbols, 3 asset classes) but only exists in `baby_strategies/` — not wired to production.

**Fix:** Add `connors_r3_survivor` to `STRATEGY_FAMILIES` in `alpha_engine/config.py` with family=momentum. Wire it to `proven_research_strategies.py` for EQUITY and FOREX. Allowlist it in `emitter_whitelist.py`. Set initial allocation to 0.5x (EXPERIMENTAL tier) with confidence floor 0.60.

**Risk:** Low — survivor has 750 trades across 3 asset classes. Start at 0.5x, monitor 30 days.

---

## P1 — FOREX TP/SL Rebalance (Hot Streak Carve-Out)

**Problem:** FOREX net-negative despite ~52% WR because wins avg 0.62%, losses avg 1.00%. The TP/SL asymmetry is structural: tight TP / wide SL. The 2026-05-15 gap analysis reports sizing_allowed bug fixed in aebc51bb16 but the TP/SL geometry is still broken.

**Fix:** For FOREX picks with R:R < 1.5 (wider SL than TP): apply a default TP boost of 1.5x if confidence >= 0.65, OR reject. Implement in `audit_trail/trade_geometry.py` as a FOREX-specific override.

**Risk:** Medium. Changing TP geometry affects resolved outcomes. Paper-only for 30 days before enforce.

---

## P2 — Deploy Dedup .MD Review Skill

**Problem:** 210 duplicate .MD files across 10+ `.claude/worktrees/agent-*/reports/` — every review session wastes time on identical copies.

**Fix:** Already built at `tools/dedup_md_review.py` + `.claude/skills/dedup-md-review/SKILL.md`. Add to `AGENTS.md` as a pre-read step. Run `python3 tools/dedup_md_review.py --list` to generate a clean file list for any future review session.

---

## P2 — Create `roadmap_items` DB Table

**Problem:** Incidents/enhancements currently live in 18 MySQL tables (INCIDENT_<CLASS> + ENHANCEMENT_<CLASS>) plus a JSON export layer. There is no unified roadmap view that maps incidents→priority→sprint→status.

**Proposed schema:**

```sql
CREATE TABLE roadmap_items (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    item_type       ENUM('incident','enhancement','hypothesis','task') NOT NULL,
    severity        ENUM('P0','P1','P2','P3','HIGH','MEDIUM','LOW') NOT NULL,
    asset_class     VARCHAR(32) DEFAULT 'OVERALL',
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    component       VARCHAR(128),           -- file path or module name
    reporter        VARCHAR(64),            -- model or human who identified
    sprint          VARCHAR(32),            -- e.g. 'Sprint 1', '2026-06'
    status          ENUM('backlog','triaged','in_progress','done','wontfix','duplicate') DEFAULT 'backlog',
    fix_file        VARCHAR(255),            -- primary file changed
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    resolved_at     TIMESTAMP NULL,
    UNIQUE KEY uq_title_class (title(100), asset_class)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

This replaces the 18-table sprawl with a single unified table. The JSON export for the dashboard reads from this table. Migration: INSERT ... SELECT from each INCIDENT_<CLASS> and ENHANCEMENT_<CLASS> table.

---

## Summary

| Priority | Item | Effort | Impact | File(s) |
|----------|------|--------|--------|---------|
| P0 | Fix confidence-inversion weight | 1 line | High | `alpha_engine/smart_picks_engine.py:105` |
| P0 | Rehabilitate CT=F | 2 lines | Medium | `production_scanner.py`, `config.py` |
| P1 | COMMODITY filter-survival gap | 20 lines | Medium | `audit_trail/dashboard_generator.py` |
| P1 | ADX regime-gated MR wrapper | 80 lines | High | `alpha_engine/adx_regime_gate.py` (new) |
| P1 | Wire Connors R3 to prod | 30 lines | Medium | `config.py`, `emitter_whitelist.py` |
| P1 | FOREX TP/SL rebalance | 25 lines | Medium | `audit_trail/trade_geometry.py` |
| P2 | Deploy dedup skill | 0 lines (done) | Low | `tools/dedup_md_review.py` |
| P2 | Create roadmap_items DB table | 1 migration | Medium | MySQL schema |
