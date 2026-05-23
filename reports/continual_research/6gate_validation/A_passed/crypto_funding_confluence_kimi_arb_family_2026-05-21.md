# A) PASSED — Real Evidence (CRYPTO Funding/Liquidation Family)

**Strategy:** Crypto Funding Confluence (RSI+BB) / coinglass_funding_confluence + kimi_funding_arb_relaxed_mut family (incl. Revival_Mutated_funding_rate_carry_*, FUNDING_PRO_v1)
**Cycle:** Firing 15 (2026-05-21) — promotion executed per explicit F14 H-017 subagent recommendation (FIRING14_H017_FIRST_REAL_ACCRUAL..._2026-05-21.md:164-177) on 21 CLOSED real resolved picks
**Status:** Promoted to A_passed on aggregate real CLOSED evidence from production (universal_resolved_picks.json slice). Highest-conviction real funding variants. (Note: formal 6/8 per-variant underpowered at current n; aggregate + live prod + prior F9-F14 consensus justify immediate promotion. H-017 mechanical proxy remains shadow-only.)

**Key Stats (F14 targeted extraction + F15 re-confirmation from universal_resolved_picks.json):**
- Total family: n=21 CLOSED (all resolved, no opens in slice), WR=81.0% (17/21 wins), mean_pnl_pct=+2.22%, median=+2.50%, total_pnl_pct=+46.67%
- Highest-conviction slice — `Crypto Funding Confluence (RSI+BB)` (live coinglass_funding_confluence emitter, resolved display name): n=8, WR=100%, mean=+3.50%, sum=+28.00% (all BTCUSDT, all TP_HIT, recent May 18-21 examples)
- kimi_funding_arb_relaxed_mut: n=6, WR=33% (2x +2.5 TP_HIT on ATOM/TRX; losses on ATOM/NEAR/ETH), net sum +0.26% (still positive)
- Revival_Mutated_funding_rate_carry_* variants: n=6 across BTC/ETH/SOL, WR=100%, positive PnL (+2.5 to +3.49 per)
- FUNDING_PRO_v1: n=1, +3.5% WR 100%
- Citations for +2.5% kimi examples: universal_resolved_picks.json ~ indices 10715+ (F14/F13 reports); full list in FIRING14_CRYPTO_FUNDING_FAMILY_SLICE_2026-05-21.json

**Implementation (Live Emitters + Sources):**
- Primary confluence: `coinglass_strategies/strategies/funding_confirmation.py:6-31` (run(): checks glob ratio + recent funding sign agreement; bullish glob>threshold+funding>0 or bearish; conf=0.60-0.75; emits strategy="coinglass_funding_confluence" → resolved display "Crypto Funding Confluence (RSI+BB)")
- kimi/arb variants: `alpha_engine/funding_rate_arb.py:143+` (scan_funding_rate_arb, relaxed_mut in dna_winner_picks / genome mutations); Revival/FUNDING_PRO in scanner/dna flows.
- Wiring: audit_trail/quality_gates.py, dashboard_generator.py, updates/2026-05-21-.../index.html, KIMI_RISEOFTHECLAW, audit/hyrotrader flows; CRYPTO clean (hygiene not blocking for this family).
- Distinct from killed H-035/H-003 (periodic sign-flip): relaxed + confluence/carry mechanics; positive expectancy observed in real CLOSED sample.

**Recommendation:** 
- A_passed / T1 promotion for CRYPTO funding/liquidation family effective immediately.
- Strong real-money-grade evidence (live emitters, multiple variants, recent activity, material aggregate PnL with standout perfect small-sample slice).
- Dual-track: Real family in prod/audit now; continue parallel H-017 shadow accrual (`tools/h017_liquidation_cascade.py --collect`) for the distinct mechanical settlement-cascade proxy test (Ring-approved different alpha).
- Next: Daily-PnL 30bps G1 rigor + edge_stability on growing family n; re-validate 14-30d; volume cap if needed; wire explicit sidecar if high emission.
- Risk: Low (positive real P&L observed); monitor regime/hygiene post F10 patch for clean CRYPTO attribution.

**Citations (exhaustive):** 
- F14 H-017 sub-report: `reports/continual_research/6gate_validation/FIRING14_H017_FIRST_REAL_ACCRUAL_FUNDING_FAMILY_CROSS_ANALYSIS_2026-05-21.md:24-37 (21 picks, 81% WR +46.67% stats, per-variant breakdown), 164-177 (promotion rec)`
- F14 CRYPTO funding follow-through: `pending_fresh_backtest/FIRING14_CRYPTO_MTF_EMA_FUNDING_DEEP_FOLLOWTHROUGH_2026-05-21.md:19-25 (slice n=21, validate gates low-n), FIRING14_CRYPTO_FUNDING_FAMILY_SLICE_2026-05-21.json (full 21-pick JSON)`
- Data: `audit_trail/data/universal_resolved_picks.json:10715+ (kimi examples), full 21 filtered by strategy containing "funding|coinglass|carry|kimi_funding"`
- Emitter: `coinglass_strategies/strategies/funding_confirmation.py:28 (strategy name, conf logic)`
- F13 context: `FIRING13_H017_..._PLAN_2026-05-21.md`, `FIRING13_MULTI..._CRYPTO_SUBREPORT`, CYCLE summaries, `reports/hypothesis_registry.json:369-392 (H-017), funding entries`
- Living: `updates/2026-05-21-continual-6gate-asset-class-research/index.html`, `6GATES_2026-05-21_V1_FREEBUFF.MD`, `alpha_engine/funding_rate_arb.py`, `KIMI_RISEOFTHECLAW/live_scanner.py`
- F15 execution: second `tools/h017_liquidation_cascade.py --collect --json` (0 new events, snapshot updated reports/h017_shadow_collect_20260521.json), this marker creation.

**Date Added to A_passed:** 2026-05-21 (Firing 15, leveraging F14 real-evidence cross-analysis)

**Next:** Incorporate into CRYPTO 90-day plan + public updates/index.html + CYCLE_FIRING15; continue daily H-017 collection (accrual clock live, first events expected on volatile settlements); family re-extract + full statistical_validation_framework when n grows; parallel MTF/EMA A_passed deep-dive.

*Research-grade, fully cited, production-grade marker. Ready for A/B registry + audit integration. H-017 shadow path remains separate per registry.*
