# Implementation Plan — Post-Opus Handoff 2026-05-13

## Scope (from session_handoff_2026-05-12_opus.md)
**P0 (highest leverage)**
1. COMMODITY walk-forward backtest (4 sleeves: metals/energy/ag/softs; 36mo train/12mo test rolling 2012-2025 OOS-only per Charter §8-9; no in-sample). Refs: walkforward_validator.py:185, universal_pick_resolver.py, alpha_engine/*commodity*.py.
2. BOND regression forensic (PF 1.72→0.66, n=18→11) + COMMODITY n-drop (816→425) via SQL diff on closed_picks snapshots + regime_filter timestamps. Use audit_trail/mysql_client.py + dashboard_data.json queries.
3. Resolve cloud-agent quality_gates.py (uncommitted +56-line confidence-inversion) + set BOND_ELITE_FLOOR=32 (blocked on PAT scope).

**P1 (after quality_gates clean)**
- A: FOREX composite ranking (0.4*WR+0.3*Trust+0.2*Score+0.1*Liquidity + 4-tier WR bands, feature flag, A/B in quality_gates.py:2600+).
- B/C: EQUITY sample expansion (gate 85→78, dynamic Trust) + ETF to T2 (Trust/Score cuts, min-hold 4h, PF+0.16).
- D: COMMODITY WR lift (thin-coverage + CTA 3-win; resolve multi_asset_cot contradiction).
- E: COT z-score bootstrap (stratified by commercial_net_z quintile, p<0.01 lift ≥1.5pp).
- F: dormant-strategies-audit-v2 (reproducible dashboard_data.json query for WR≥0.55 + stale last_emit).
- G: New alpha_engine/macro_regime.py (wire FRED/COT/VIX to quality_gates:753 + scanner:1203 + dashboard_generator:12567).
- H: Asymmetric risk (COMMODITY 3-4x ETF baseline in position_sizer + regime_modifier).

**P2 (structural)**
- performance_alerts auto-shadow, BOND WF, 248-strat factor panel, MAJOR GOAL banner update (template.html:808).

**Future points from §7**: Add re-resolution logging, PAT hygiene, multi-agent .work-in-progress claims, invoke money-maker-ready skill.

## Per-Item Plan + Testing
**All changes**:
- Read neighboring files first (conventions: no comments, mimic style, use existing validators like test_quality_gates.py, walkforward_validator.py:500).
- Document fix in updates/2026-05-13-*.md (what broken, change, verification command).
- Only my edits on clean branch (e.g. feature/commodity-wf-20260513).
- Run: `python -m pytest tests/test_quality_gates.py -q --tb=no`, `python -m audit_trail.walkforward_validator --class COMMODITY`, ruff lint if present, dashboard_generator dry-run. Verify with money-maker-ready skill.
- PR via gh (title/body with refs to handoff lines + swarm ideas). No force-push.

**P0-1 COMMODITY WF (first)**: Extend walkforward_validator.py with sleeve tagging in commodity files + 4-sleeve rolling fn. Test: mock folds, assert OOS decay<5%, no train leakage (test_walkforward_commodity_4sleeve). Emit walkforward.commodity_sleeves.json to dashboard. (Swarm idea refs: walkforward_validator.py:162, audit_trail/verify.py).

**Forensics (P0-2/3)**: SQL query in new audit_trail/closed_picks_forensic.py or quality_gates extension; pandas diff on two JSON snapshots. Repro: `grep -A20 "asset_class" audit_trail/universal_pick_resolver.py`. Update reports/bond_root_cause_*.md.

**P1 sequence (post cloud-agent commit)**: Start with P1-A (FOREX in quality_gates.py:291-300 + tests), then G (new macro_regime.py), then B/C/E/F/H. Use swarm ideas for exact line placements + reproducible greps.

**Coordination**: Create .work-in-progress/claim files before editing shared (quality_gates.py). After each PR, update MEMORY.md + invoke money-maker-ready skill for re-audit.

**Verification milestones**:
- After P0: COMMODITY in walkforward.by_class with PF/WR stable OOS → update headline in dashboard_generator + handoff doc.
- Full queue: Run full money-maker-ready audit; confirm 3+ classes T2+ with WF coverage.
- Swarm review after plan (next step).

This plan merges swarm output (general/explore agents), prioritizes P0 per reviewer Q1, ensures reproducible queries + existing test coverage. Ready for swarm review.

**Next**: Swarm review of this plan → implement P0 on clean branch → PR.
