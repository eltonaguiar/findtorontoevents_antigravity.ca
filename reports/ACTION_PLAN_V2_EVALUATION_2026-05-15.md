# Action Plan v2 — 14-Day Acceptance Evaluation
**Evaluation date:** 2026-05-15  
**Plan shipped:** 2026-05-01  
**Elapsed:** 14 days  
**Dashboard snapshot:** 2026-05-15T21:00:17Z  
**Evaluator:** Claude Code (automated, no PRs opened)

---

## Executive summary

**Verdict: PARTIALLY-DELIVERED**

- 5 of 10 "within-7-day" items shipped cleanly; 5 slipped.
- The 14-day gate (Items 11 + 12 live) is half-met: Item 12 (B9 shadow) shipped on day 3; Item 11 (B25-Diag data accumulation) was never production-enabled.
- Overall PF improved 0.98 → 1.15 (+0.17), beating the 21-day target of ≥1.05 — but six of ten V-gates failed, and the PF number is dominated by CRYPTO volume (n=8123) which masks a worsening BOND class and a still-loss-making FOREX class.
- Three new regressions introduced since 2026-05-01: BOND PF collapsed (1.72 → 0.66), B16 daily artifact stopped emitting after day 2 (13-day gap), and all active EQUITY picks have `timeframe=None` (V2 gate failure).

---

## 1. Per-item status table (Items 1-17)

| Order | Item | Status | Evidence / Blocker |
|------:|------|--------|-------------------|
| 1 | Verify V1-V10 | **PARTIAL** | V3/V4/V6 pass; V1/V2/V5/V7/V8/V10 fail; V9 partial — see §3 |
| 2 | B23 resolver wireup | **SHIPPED** | `audit_trail/universal_pick_resolver.py:223` — `tradingagents` in SYSTEM_SOURCES ✅ |
| 3 | B2-redux timeframe grid | **SHIPPED** | `dashboard_data.json::performance.asset_class_timeframe_grid` populated; `template.html:10772` renders it ✅ |
| 4 | EQUITY-REGRESS diagnostic | **NOT COMPLETED** | "report only" task; no `reports/equity_regress_*.md` found. Grid shipped (Item 3) but diagnostic report was never written. |
| 5 | B6 concept UI chips | **SHIPPED** | `updates/2026-05-01-b6-concept-ui-filters.md` + `template.html:7047` concept filter guard ✅ |
| 6 | B19 pair carve-out | **SHIPPED** | `updates/2026-05-02-b19-pair-exception-carve-out.md`; `pair_exceptions.py` with `PAIR_EXCEPTION_CARVE_OUT_ENABLED` gate. Default-OFF requirement met. ✅ |
| 7 | HYRO-FRESHNESS audit | **NOT STARTED** | No May 2026 update referencing HYRO audit. `audit_dashboard/hyrotrader/hyro_live_signals.js` has zero date stamps — content is static JS signal calculator, not telemetry. Last hyro update was 2026-04-28. |
| 8 | B14-redux slippage stress | **SHIPPED** | `tools/slippage_stress_test.py` new; `reports/slippage_stress_2026-05-02.md` + JSON artifact exist ✅ |
| 9 | FOREX-RESOLVER-2 shadow | **NOT SHIPPED** | `outcome_resolver.py` still has FOREX at 5bp (0.0005); no `FOREX_RESOLVER_2_ENABLED` flag or non-JPY pip threshold shadow logic found. A separate FOREX P0/P1 fix (TP/SL hardcap raise) landed 2026-05-08 — related but not the specified item. |
| 10 | B7 COT scaffold | **PARTIAL** | `updates/2026-05-02-b7-cot-schema-audit.md` — schema fix and `JSON_PICK_SOURCES` registration shipped. Full opt-in scaffold (Wire-Up Rule compliance + production caller named) is incomplete. |
| 11 | B25-Diag (7-day raw log) | **NOT STARTED AS DESIGNED** | `tradingagents_emitter.py:55` has `TRADINGAGENTS_DEBUG_RAW` flag; but no GHA workflow enables it in production. No 7-day accumulation, no diagnostic report. The B25 identical-metrics *fix* (prompt hardening, 2026-05-01) shipped separately — that is distinct from the diagnostic. |
| 12 | B9 TradingAgents shadow | **SHIPPED** | `updates/2026-05-04-b9-adversarial-shadow.md`; `tools/run_ueps_pickers.py` calls `adversarial_debate.apply_to_picks()` behind `UEPS_ADVERSARIAL_ENABLED` flag. Shadow is informational-only (no filtering). ✅ |
| 13 | B5 Cursor Phase 3 scoring | **NOT STARTED** | Gated on V9 (B4 48h soak) — V9 is partial pending pipeline_health.json. |
| 14 | B13 Per-class HMM | **NOT STARTED** | Gated on V10 (B12 7d soak) — V10 failed. |
| 15 | B17 HC after-cost gate | **SHIPPED (shadow only)** | `updates/2026-05-02-b17-hc-after-cost-gate.md` — stamp logic in dashboard_generator, default-OFF. Counted as started; shadow not yet 14 days. |
| 16 | B18 Shadow auto-promotion | **NOT STARTED** | Gated on B16 artifact — B16 stopped emitting after day 2. |
| 17 | B25-Fix TradingAgents | **NOT STARTED** | Gated on Item 11 (B25-Diag report) — which never started. |

---

## 2. 14-day acceptance criterion evaluation

**Criterion:** "Within 14 days: items 11 (B25-Diag) + 12 (B9 shadow start) live; B25-Diag accruing log data toward its 7-day window."

| Sub-criterion | Result | Notes |
|---|---|---|
| Item 12 (B9) live | **MET** | Shipped 2026-05-04 (day 3) |
| Item 11 (B25-Diag) live | **NOT MET** | `TRADINGAGENTS_DEBUG_RAW` flag exists in code but never enabled in production workflows |
| B25-Diag accruing 7d of log data | **NOT MET** | Zero log data accumulated; no workflow triggers debug mode |

**7-day criterion (reference):** "Items 1-10 complete; queue down to 6 gated items."
- Items completing within 7 days: **5** (Items 2, 3, 5, 6, 8)
- Items that slipped: **5** (Items 1-partial, 4, 7, 9, 10-partial)
- This criterion was NOT met.

---

## 3. V1-V10 verification gates

| Gate | Description | Status | Command output / Evidence |
|------|-------------|--------|--------------------------|
| V1 | UEPS picks in `picks.active` with `pick_type=long_term_value` | **FAIL** | `len([p for p in active if p.get('pick_type')=='long_term_value']) == 0`. 50 active picks, zero are UEPS. B9 update (2026-05-04) claims 17/77 active picks had `source_system=ueps` on that date — not reproduced today. |
| V2 | EQUITY × POSITION lane non-empty | **FAIL** | All 26 EQUITY active picks have `timeframe=None`. V2 requires ≥2 POSITION-timeframe picks (PEP, LLY confirmed at v1 time). Timeframe stamping appears broken for EQUITY. |
| V3 | TradingAgents emitter dormant when flag off | **PASS** | `tradingagents_emitter.py:321-324` — hard no-op: `return {"emitted": 0, "skipped": 0, "errors": 0, "reason": "TRADINGAGENTS_EMITTER_ENABLED not set"}`. Flag check at line 313. ✅ |
| V4 | Penny skyrocket cron wired | **PASS** | `.github/workflows/penny-skyrocket-runner.yml` exists with `cron: '48 14 * * 1-5'`; commit `2ce39e0b 2026-05-15 Skyrocket Detector scan` confirms it ran today. ✅ |
| V5 | PEAD cache persists across runs | **FAIL** | `data/earnings/` contains only `.gitkeep` (empty). Zero earnings cache files. The `updates/2026-04-29-pead-earnings-bootstrap.md` describes the plan but no data materialized. |
| V6 | `concept_family` on 100% of `picks.active` | **PASS** | `len([p for p in active if p.get('concept_family')]) == 50` (50/50). ✅ |
| V7 | BOND credit-spread emitting or gap logged | **FAIL** | 0 active BOND picks. `dashboard_data.json::performance.asset_class_health.BOND.status = 'thin_sample'` (n=11). No bond-agent signal-availability gap log found. |
| V8 | B16 daily artifact emits | **FAIL** | Last file: `reports/forward_edge_audit_2026-05-02.md`. No reports for 2026-05-03 through 2026-05-15 (13-day gap). `tools/forward_edge_audit.py` exists but no GHA workflow found that schedules it daily. |
| V9 | B4 48h soak — concept registry stable | **PARTIAL** | (a) `concept_family` at 100% coverage ✅; (b) cannot verify — `pipeline_health.json` does not exist; (c) cannot verify — no multi-build log accessible. V9 is gating B5 (Item 13). |
| V10 | B12 7d soak — source-liveness watchdog stable | **FAIL** | `dashboard_data.json::source_liveness_watchdog == {}` (empty dict). No false-positive or true-positive alerts logged. Watchdog is not running. |

**V-gate summary:** 2 PASS, 6 FAIL, 1 PARTIAL, 1 cannot verify (V9-b/c)

---

## 4. PF analysis — baseline → current

**Dashboard generated at:** 2026-05-15T21:00:17Z  
**Methodology note:** After-cost PF uses a round-trip cost deducted from gross PnL, assuming a representative 2% avg trade (from dashboard: avg_win=2.95%, avg_loss=2.13%). This is a rough estimate. The §6.8 methodology from `REMAINING_ACTION_ITEMS_2026_04_30.md` was not re-run directly.

### Overall PF

| Metric | Baseline (2026-05-01) | Current (2026-05-15) | Delta |
|--------|----------------------|----------------------|-------|
| Overall PF (clean_metrics) | 0.98 | **1.15** | **+0.17** |
| Overall WR | ~44% (est.) | 44.5% | ≈flat |
| Total resolved picks | ~8000 (est.) | 8,270 | +270 |

The 21-day PF target of ≥1.05 is **met** at current 1.15 — with 7 days to spare. However, the gain is heavily weighted toward COMMODITY and CRYPTO whose n dominates. The improvement is real but fragile.

### Per-class PF table

| Class | Baseline PF | Baseline WR | Baseline n | Current PF | Current WR | Current n | Delta PF | After-Cost PF* | 21-day target |
|-------|------------|------------|-----------|-----------|-----------|----------|----------|---------------|--------------|
| CRYPTO | 1.25 | 44.6% | 8,067 | 1.30 | 46.1% | 8,123 | +0.05 | ~0.91 | Not gated |
| EQUITY | 1.41 | 52.7% | 421 | 1.55 | 51.5% | 425 | +0.14 | ~1.40 | ≥1.05 |
| FOREX | 0.27 | 46.4% | 1,169 | 0.87 | 55.4% | 305 | +0.60 | ~0.80 | ≥1.05 |
| COMMODITY | 1.78 | 46.9% | 750 | 2.36 | 60.5% | 339 | +0.58 | ~2.01 | ≥1.05 |
| ETF | 1.24 | 55.2% | 87 | 1.33 | 57.4% | 108 | +0.09 | ~1.20 | ≥1.05 |
| BOND | 1.72 | 55.6% | 18 | **0.66** | 54.5% | 11 | **−1.06** | ~0.61 | ≥1.05 |
| FUTURES | N/A | N/A | 0 | None | 0.0% | 0 | N/A | N/A | Not tracked |

\* After-cost PF uses cost schedule: CRYPTO 30bp, EQUITY 10bp, FOREX 8bp, COMMODITY 15bp, ETF 10bp, BOND 8bp applied as round-trip cost / 2% avg trade proxy. Treat these as directional, not exact.

### Critical data-quality warnings

1. **FOREX n-count anomaly:** n dropped from 1,169 → 305 (−74%). The FOREX P0/P1 fix (2026-05-08) reclassified `phantom_expired` picks, which likely explains the drop. Gross PF improved 0.27 → 0.87, but FOREX is still loss-making after costs (~0.80 after-cost PF). The improvement is partly real progress and partly better phantom-expired filtering — the two effects cannot be separated without a resolver replay.

2. **BOND regression:** PF 1.72 → 0.66 on n=11 (below 30-pick charter floor). This may be pure statistical noise at thin sample — but it is a signal that bond-agent picks have not closed cleanly in 14 days. Requires investigation before any B13/B17 sizing increase.

3. **COMMODITY n drop:** n 750 → 339. Paired with PF improving 1.78 → 2.36. Likely the same phantom-expired filter is removing noise trades. The PF improvement appears genuine but n-halving means the per-source breakdown cannot be validated.

4. **EQUITY timeframe=None:** All 26 active EQUITY picks lack a timeframe tag. This breaks V2 and means the B2-redux grid EQUITY×POSITION cell is always 0, making the "EQUITY regression diagnostic" impossible without fixing timeframe stamping first.

---

## 5. Honest verdict by acceptance criterion

| Criterion | Target | Result | Verdict |
|---|---|---|---|
| Items 1-10 complete (7-day) | 10/10 | 5/10 shipped cleanly | **FAILED** |
| Item 11 live (14-day) | B25-Diag running | Not enabled in production | **FAILED** |
| Item 12 live (14-day) | B9 shadow running | Shipped 2026-05-04 | **MET** |
| B25-Diag accruing 7d data (14-day) | Logs accumulating | Zero logs | **FAILED** |
| Overall PF ≥ 1.05 within 21 days | 0.98 → ≥1.05 | 1.15 (day 14) | **MET** ✅ |
| V-gates V1-V10 pass | 10/10 | 2/10 pass, 6 fail, 1 partial, 1 uncheckable | **FAILED** |

**Overall verdict: PARTIALLY-DELIVERED**

The headline PF number looks good (1.15 vs 0.98 baseline), but the verification gate failures (6/10) indicate the infrastructure validating that improvement is not working. PF improvement via COMMODITY + FOREX noise-filter removal is real but cannot be fully attributed to the v2 action items.

---

## 6. New bugs and regressions introduced since 2026-05-01

| Bug | Severity | Evidence |
|-----|----------|---------|
| B16 forward_edge_audit cron stopped | HIGH | Last file: 2026-05-02; 13-day gap; V8 FAIL; blocks B18 |
| EQUITY timeframe=None on all active picks | HIGH | V2 FAIL; breaks EQUITY×POSITION diagnostic; EQUITY WR dropped 52.7%→51.5% while n grew |
| BOND PF 1.72→0.66 regression | MEDIUM | n=11 thin sample but trend is negative; bond-agent not closing picks |
| Source-liveness watchdog not running | MEDIUM | V10 FAIL; `source_liveness_watchdog={}` in dashboard |
| pipeline_health.json absent | MEDIUM | V9-b/c uncheckable; concept-registry error monitoring blind |
| PEAD earnings cache empty | LOW | V5 FAIL; `data/earnings/` = `.gitkeep` only; PEAD strategy cannot operate |
| UEPS picks absent from active | LOW | V1 FAIL; B9 shadow (Item 12) accruing zero adversarial-debate data |
| sidecar_promotion_status shows n=0 for all | LOW | Promotes with zero trades — data integrity issue in promotion-status builder |

Note: B25 identical-metrics prompt-hardening fix (2026-05-01) was shipped and is a genuine improvement, but it was sequenced *before* the diagnostic — the v2 plan explicitly required diagnostic-before-fix. The fix may have addressed symptoms without confirming root cause.

---

## 7. Top 3 follow-up actions for the next 7 days (2026-05-16 to 2026-05-22)

### Priority 1 — Fix B16 cron (unblocks B18 and V8)

**Why:** The `forward_edge_audit.py` tool exists but has no GHA schedule. Without daily `reports/forward_edge_audit_<date>.md` artifacts, V8 fails, B16 cannot feed B17's after-cost stamping accurately, and B18 auto-promotion has no artifact to read. This is a one-file workflow addition (30-min fix).

**Action:** Add `.github/workflows/forward-edge-audit-daily.yml` with a `cron: '30 6 * * *'` schedule that runs `python tools/forward_edge_audit.py` and commits the output. Verify V8 passes within 24h.

### Priority 2 — Enable B25-Diag in the TradingAgents workflow (unblocks Item 11 and B25-Fix)

**Why:** `TRADINGAGENTS_DEBUG_RAW=1` already exists in the emitter code but is never set in the workflow that runs the emitter. Until this flag is production-enabled and 7 days of raw LLM responses accumulate, Item 11 cannot complete and Item 17 (B25-Fix) cannot be properly sequenced. Every day without logs is a day wasted against the 7-day accumulation window.

**Action:** Add `TRADINGAGENTS_DEBUG_RAW: "1"` to the `env:` block of the TradingAgents emitter workflow. Log files should be written to `alpha_engine/data/tradingagents_raw_logs/` (excluded from dashboard payload, included in git). Produce the diagnostic report after 7 days.

### Priority 3 — Fix EQUITY timeframe=None stamping and write EQUITY-REGRESS diagnostic

**Why:** V2 fails, the B2-redux grid shows EQUITY×POSITION = 0 (defeating its purpose as a diagnostic tool), and EQUITY WR has drifted slightly downward (52.7%→51.5%) without explanation. Until timeframe is stamped correctly on EQUITY picks, no grid-based regression analysis is possible. This was supposed to be a "report only" Item 4 but the prerequisite infrastructure is broken.

**Action:** Identify which emitter or normalizer strips `timeframe` from EQUITY picks (grep `dashboard_generator.py` for `_normalize_pick()` and the EQUITY asset-class branch). Fix the stamp. Then run the EQUITY-REGRESS analysis: pull the EQUITY×POSITION vs EQUITY×SWING cells, identify which strategies lost WR since 2026-04-01, and write `reports/equity_regress_diagnostic_2026-05-22.md`.

---

*This report was produced by automated evaluation on 2026-05-15. No PRs were opened. All findings are based on the current state of the main branch and `audit_dashboard/data/dashboard_data.json` as of 2026-05-15T21:00:17Z.*
