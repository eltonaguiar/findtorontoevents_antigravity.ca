# Firing 16 Sub-Report: H-017 Third Real Collection + Funding Family A_passed Marker QC Review

**Date:** 2026-05-21 (Firing 16 of autonomous 30m 6/8-gate continual research loop, job 019e4ad4-d78d-7423-98a5-1ae6d58289fd)  
**Subagent:** Grok Build (delegated per CYCLE_2026-05-21_FIRING16_SUMMARY.md kickoff — H-017 / Funding subagent: third `--collect` + quality/completeness/consistency review of the F15-created A_passed marker for crypto funding family)  
**Primary Focus:** Execute third real `tools/h017_liquidation_cascade.py --collect --json`; QC the newly promoted `A_passed/crypto_funding_confluence_kimi_arb_family_2026-05-21.md` against the underlying 21 CLOSED real evidence from universal_resolved_picks.json (F14 extraction); produce this short sub-report + ensure proper CYCLE_16 references. Builds on F14 (first collection + 21-pick evidence + promotion rec) and F15 (second collection + marker creation + F15 sub-report).  
**Research-only. M-107 / registry compliant. No live sizing or prod changes.**

---

## 1. Executed Scope (Exact per CYCLE16 Directive)

1. **Third real H-017 collection run**:
   - Command: `cd /home/eaguiar2015/findtorontoevents_antigravity.ca && python3 tools/h017_liquidation_cascade.py --collect --json`
   - Executed 2026-05-21 ~13:59 UTC (immediately following F15 second run; third consecutive real daily accrual).
   - **Results**: 0 new cascade events across all 5 symbols (BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT).
     - raw_records=0 for every symbol (free Binance 1m klines ~1500 bars / ~1-3.5d recent window; no qualifying settlement-window proxy cascade in the interval: displacement >1.5×1h-ATR **AND** volume >2× median **AND** |funding| in top 30%).
   - Stderr (exact):
     ```
     # H-017 shadow collector (daily accrual)
     # BTCUSDT (collect)... raw_records=0
     # ETHUSDT (collect)... raw_records=0
     # SOLUSDT (collect)... raw_records=0
     # BNBUSDT (collect)... raw_records=0
     # XRPUSDT (collect)... raw_records=0
     # new_unique_resolved=0 (total_existing_before=0)
     # no new unique cascade events today; log unchanged
     # daily snapshot → /home/eaguiar2015/findtorontoevents_antigravity.ca/reports/h017_shadow_collect_20260521.json
     ```
   - JSON stdout: `{"new": 0, "total": 0, "records": []}`
   - Daily snapshot **updated** (idempotent overwrite with fresh run_ts): `reports/h017_shadow_collect_20260521.json` (new_resolved=0, total_in_shadow=0, run_ts="2026-05-21T13:59:25+00:00").
   - Shadow JSONL `alpha_engine/data/h017_liquidation_cascade_shadow.jsonl`: **still not created** (correct per `collect_shadow` logic in tools/h017_liquidation_cascade.py:310 — only written on new_unique > 0; dedup on (symbol, id)). First qualifying events will initialize it with `_to_resolved_pick` schema records (h017_* meta fields).
   - n tracking (H-017 shadow): remains 0 after three consecutive real daily runs. Accrual mechanism fully operational and stable (collector live since F14 ~12:59; F15 ~13:29; F16 ~13:59). Per F13 design + docstring: target n≥50 for validate + edge_stability_harness + 6/8 (eff_floor=0.30 x3 windows, cost_survival≥0.60, WR≥0.50). Rare triggers expected (only extreme settlement dislocations); free API proxy limitation explicit (no direct /fapi/v1/liquidationOrders history).

2. **QC review of A_passed marker** (F15 artifact: `reports/continual_research/6gate_validation/A_passed/crypto_funding_confluence_kimi_arb_family_2026-05-21.md`):
   - Performed line-by-line against source evidence (F14_H017 sub-report:24-37 stats + 164-177 rec; F15 sub-report:68-82 explicit 21-pick list; universal_resolved_picks.json slice via F14 targeted extraction; emitters; prior CYCLE/F13 reports).
   - **Quality**: High. Concise (42 lines), production-grade tone, exhaustive citations (exact file:line for F14 report, slice JSON, coinglass_strategies/strategies/funding_confirmation.py:6-31 and :28, alpha_engine/funding_rate_arb.py, hypothesis_registry, updates/, 6GATES). Clear structure (stats, impl, rec, citations, dual-track note). Matches style of sibling A_passed markers (e.g. multi_timeframe..._crypto_2026-05-21.md) while appropriately noting "Real Evidence" vs full 6/8 (justified by low per-variant n).
   - **Completeness**: Strong for a marker artifact. Covers: family variants (coinglass_funding_confluence / "Crypto Funding Confluence (RSI+BB)", kimi_funding_arb_relaxed_mut, Revival_Mutated_funding_rate_carry_*, FUNDING_PRO_v1); aggregate + per-slice stats; live emitter wiring; distinction from killed H-035/H-003 (relaxed + confluence/carry vs periodic sign-flip); explicit dual-track with H-017 shadow (n=0); actionable next (daily-PnL G1, 14-30d reval, CRYPTO 90-day + A/B). References F14/F15 sub-reports and the 21 CLOSED evidence.
   - **Consistency with 21 CLOSED real evidence**: **Perfect match, no discrepancies**.
     - Stats verbatim from F14 extraction (confirmed F15): n=21 CLOSED (all resolved), WR=81.0% (17/21), mean_pnl_pct=+2.22%, median=+2.50%, total_pnl_pct=+46.67%.
     - Highest-conviction: `Crypto Funding Confluence (RSI+BB)` (coinglass emitter): n=8, WR=100%, mean=+3.50%, sum=+28.00% (all BTCUSDT, all TP_HIT, recent May 18-21).
     - kimi_funding_arb_relaxed_mut: n=6, WR=33%, net sum +0.26% (examples at universal:10715+ with explicit +2.5% TP_HIT on ATOM/TRX).
     - Revival_Mutated_funding_rate_carry_* (BTC/ETH/SOL): n=6, WR=100%, positive per-trade PnL.
     - FUNDING_PRO_v1: n=1, +3.5%.
     - F15 sub-report:68-82 provides the explicit per-pick list matching the aggregate (e.g., 8x +3.5 coinglass BTC; kimi mixed but net +; carry perfect small samples). Marker cites F14 report + slice JSON + F15 execution correctly.
     - No invented numbers, no drift from F14 cross-analysis of universal_resolved_picks.json, no pollution claims. Real family remains distinct/complementary to H-017 mechanical proxy (settlement-timed cascade fade).
   - **Minor observations (QC notes, no blocking issues)**: Per-variant n low (limits formal per-strat 6/8 power today — correctly flagged in marker); full per-pick table lives in F15 sub-report (appropriate, marker is summary). Could optionally append the 11-line F15 list in future refresh if n grows, but current form is tight and usable for A/B/registry/90-day. Title "Real Evidence (CRYPTO Funding/Liquidation Family)" accurately signals the evidence basis vs pure gate-pass markers.
   - **Verdict**: Marker passes QC. Production-ready, fully cited, consistent with the 21 CLOSED real evidence. No edits required at this time. Ready for audit integration, CRYPTO T1 wave, and living log appends.

3. **Produced this sub-report** (this file) + CYCLE_16 integration (detailed completion section appended below).

All actions research-grade, cited, no prod changes.

---

## 2. Updated n Tracking (Post Third Collection)

- **H-017 (mechanical proxy, this collector, M-107 pre-reg)**: shadow_total=0 after 3 real daily runs (F14 first, F15 second, F16 third; all 0 new_unique due to free API window + quiet settlements). Accrual clock live and stable. JSONL absent (correct). Snapshot artifacts: reports/h017_shadow_collect_20260521.json (latest run_ts 2026-05-21T13:59:25+00:00), reports/h017_liquidation_cascade_20260521.json (INSUFFICIENT_DATA n=0). Next event expected on high-vol 8h UTC settlement (news/FOMC/etc.). Per collector (tools/h017_liquidation_cascade.py:273-338 collect_shadow, 208-245 _to_resolved_pick, 341-476 proxy logic): schema-compatible with validate_resolved_picks + harness once n grows.
- **Real funding/liquidation family (now A_passed per F15 marker)**: Stable at 21 CLOSED (no new in short windows). Aggregate 81% WR / +46.67% total PnL unchanged. Coinglass perfect n=8 slice stable. Live emitters confirmed operational.
- **Dual-track status**: Real family promoted on aggregate real CLOSED + live prod + F9-F14 consensus (F14 rec at :164-177). H-017 shadow continues separately for the distinct Ring-approved "different alpha" (cascade convexity at settlement vs broader confluence/carry). No overlap/pollution.

---

## 3. 7-Day Accrual + Validation Plan (F16 Forward, unchanged from F15)

**Immediate / Daily (accrual live)**:
- Continue cadence: `python3 tools/h017_liquidation_cascade.py --collect --json` (or via scheduler/30m loop; --dry-run for previews). Append to logs if desired.
- Monitor: `ls -l reports/h017_shadow_collect_*.json alpha_engine/data/h017_liquidation_cascade_shadow.jsonl` (or cat latest snapshot).
- On first events (volatile settlements): inspect new_records + h017_displacement_atr / volume_ratio / funding_rate / net_ret_bps in snapshot; append observations to this sub-report + living logs.

**7 days**:
- Target: 3-10+ events if vol (baseline 0-3). If n_shadow≥5-10: preliminary validate (manual JSONL filter or temp patch validate_resolved_picks.py for --strategy-filter "funding_settlement_liquidation_cascade" + --by-asset-class CRYPTO --min-trades 1).
- Re-extract real family from universal_resolved_picks.json (expect + few more CLOSED from ongoing emission); compare WR/PF vs any new H-017 proxy events.
- Update: This sub-report + CYCLE_FIRING16 + A_passed marker (if new real family stats) + updates/2026-05-21-continual-6gate-asset-class-research/index.html + CONTINUAL_STRATEGY_RESEARCH_BASELINE.md.
- Command ref: python one-liners used in F14/F15 for targeted slice (or full validate post-filter).

**14 days**:
- Target: n_shadow ≥10-25.
- Full: `python3 tools/validate_resolved_picks.py --by-asset-class CRYPTO --min-trades 5 --output reports/validation_h017_funding_f16_14d.json` (post-process for H-017 + real family slices).
- Gates: edge_stability_harness + statistical_validation_framework (bootstrap p, WF consistency, MC stress, MTC FDR, DSR) on family + any H-017 slice.
- Per-gate tables for coinglass/kimi vs H-017 proxy; decision on sidecar emitter or further promotion.
- Hygiene: Re-run post F10 tagging patch for clean CRYPTO attribution (already dominant).

**30-60d (n≥50 target for H-017)**:
- H-017: n≥50 + 3+ admissible eff windows (eff≥0.30) + cost_survival≥0.60 + WR≥0.50 → registry update (UNTESTED→TESTED_PASS) + A/B marker + optional emitter prototype (alpha_engine/h017_liquidation_emitter.py pattern from H-037).
- Family: Expand variants (basis_carry etc.); full daily-PnL G1 + 30bps rigor + institutional filters; volume scaling if emission high.
- Living: Append to CRYPTO 90-day plan, master baseline, public log, hypothesis_registry.

**Scheduler / Ops**:
- Add to autonomous loop (see swarm / .github/workflows or tools/); existing F13/F14/F15 playbooks apply.
- Artifacts: collector `tools/h017_liquidation_cascade.py:273 (collect_shadow), 479 (main), 208 (_to_resolved_pick), 341-476 (backtest_symbol proxy + cascade detection)`; validate `tools/validate_resolved_picks.py`; harness `alpha_engine/edge_stability_harness.py`; registry `reports/hypothesis_registry.json:369-392 (H-017)`; F14 slice `pending_fresh_backtest/FIRING14_CRYPTO_FUNDING_FAMILY_SLICE_2026-05-21.json`.

---

## 4. CYCLE_16 Integration + Next

- **This subagent completes Firing 16 H-017/Funding scope** (per kickoff): third real collection executed (0 new, total=0, snapshot refreshed 13:59:25); A_passed marker `A_passed/crypto_funding_confluence_kimi_arb_family_2026-05-21.md` QC'd and **passed** (high quality, complete, fully consistent with 21 CLOSED 81% WR / +46.67% evidence from F14 extraction + F15 list; no changes needed); this sub-report + CYCLE16 completion section delivered.
- **A/B Impact**: Real funding family remains A_passed (F15 marker stable post-QC). H-017 shadow n=0 after 3 runs (accrual live, distinct mechanical track). Complements the other two CRYPTO A_passed (MTF n=68 8/8, EMA Ribbon n=20 7/8) under parallel maturation.
- **Citations in this report**: `tools/h017_liquidation_cascade.py` (third run + full logic), `reports/h017_shadow_collect_20260521.json` (refreshed), `A_passed/crypto_funding_confluence_kimi_arb_family_2026-05-21.md`, F14_H017_FIRST..._2026-05-21.md:24-177 (primary 21-pick evidence + promotion rec), F15_H017_SECOND..._2026-05-21.md:12-82 (second run + explicit pick list + marker creation), `universal_resolved_picks.json` (21 CLOSED), `coinglass_strategies/strategies/funding_confirmation.py:6-31`, `alpha_engine/funding_rate_arb.py`, CYCLE_2026-05-21_FIRING16_SUMMARY.md (kickoff), hypothesis_registry.json, prior F13/F14/F15 CYCLEs + living updates/.
- **Open in F16 (H-017 track)**: First shadow events; n growth to power G4+; parallel CRYPTO/EQUITY subagent maturation.

**Firing 16 H-017 / Funding subagent complete. Third collection executed (n=0 after 3 runs, live). A_passed marker QC passed with full consistency to 21 real CLOSED evidence. Dual-track + 7-day plan documented. CYCLE_16 updated. Loop continues.**

*End of sub-report. All research-only, fully cited, production-grade. Next: Incorporate into CYCLE close + public updates + CRYPTO 90-day + registry A/B (no changes).*

---

**Appendix: Exact Third Run Artifacts**
- Snapshot (post-F16): `/home/eaguiar2015/findtorontoevents_antigravity.ca/reports/h017_shadow_collect_20260521.json` (run_ts 2026-05-21T13:59:25+00:00, 0/0).
- Collector source (key paths): `tools/h017_liquidation_cascade.py:69 (REPORT_PATH), 73 (SHADOW_LOG), 273-338 (collect_shadow), 320-332 (daily snapshot write), 208-245 (_to_resolved_pick schema).`
- Marker under review: `reports/continual_research/6gate_validation/A_passed/crypto_funding_confluence_kimi_arb_family_2026-05-21.md` (42 lines, QC passed).
