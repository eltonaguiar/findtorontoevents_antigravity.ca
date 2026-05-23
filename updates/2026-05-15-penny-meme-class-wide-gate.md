# PENNY/MEME Class-Wide Gate Enhancement (2026-05-15)

**PR Scope:** Upgrade the existing leaky MEMECOIN strategy-pair quarantine (quality_gates.py ~1933-1974) to a true class-wide gate for both MEMECOIN and PENNY_STOCK. Add `is_low_quality_or_meme()` helper + CATEGORY_RISK BLOCK mapping in config.py. Deprecate or neuter the penny_volume_* strategies in community_strategies.py. Wire early in scanner/production_scanner before emit.

**Why (converged sources):**
- `reports/asset_class_action_items_2026-05-15.md`: "PENNY/MEME — folded into EQUITY/CRYPTO (leaky quarantine). ... the string `PENNY_STOCK` does not appear in `quality_gates.py` at all — penny stocks have zero gating, not even leaky pair-blocks." Top action #6 in priority stack.
- `reports/asset_class_verification_2026-05-15.md` and `asset_class_90day_plan_PENNY_MEME_2026-05-15.md`: class-wide block described in plans but not implemented; only exact `(MEMECOIN, strategy)` tuples.
- `DAILY_IDEAS.MD` (2026-05-13 IDEA-B): "Penny stocks revisit ... Microcap WR + PF historical by float-size bin. Pump-and-dump red flags... Catalyst-driven moves." + Kimi hallucinations of penny-EQUITY names flagged for drop.
- `reports/daily_ideas_synthesis_2026-05-15.md` and MASTER_ACTION_PLAN_2026-05-15.md: MEMECOIN quarantine (M-038) listed as pending.
- Live: MEMECOIN class PF ~0.50-0.58, WR 15-31%, massive negative edge; penny names (NIO, LCID, RIVN, GME, AMC, SNDL) drag EQUITY WR via gap risk (no liquidity/ADV filter like crypto has).

**Files changed (my changes only):**
- `audit_trail/quality_gates.py`: Add early class-wide check `if (asset_class or pick.get('asset_class')) in ("MEMECOIN", "PENNY_STOCK"): return False` (after existing pair list for backward compat; update comment to "class-wide + legacy pairs").
- `alpha_engine/config.py`: Add `def is_low_quality_or_meme(symbol: str) -> bool` (mktcap proxy or static list + ADV check if available) and update `CATEGORY_RISK` for "penny"/"meme" to BLOCK (instead of loose -15%SL/+35%TP).
- `alpha_engine/scanner.py` and/or `alpha_engine/production_scanner.py`: Call the new helper pre-emit for EQUITY/CRYPTO paths.
- `community_strategies.py`: Deprecate `penny_volume_breakout` + `community_penny_volume_surge` (return [] or log warning).
- `updates/2026-05-15-penny-meme-class-wide-gate.md`: This doc (mandatory per AGENTS.md).

**Production caller (Wire-Up Rule):** `passes_active_gate` (quality_gates) + pre-emit in scanner/production_scanner. No new modules.

**Acceptance criteria:**
- py_compile clean on all 4 files.
- Existing MEMECOIN pair blocks still work (backward).
- New PENNY_STOCK or low-quality names (e.g. SNDL, GME) blocked even without exact strategy match.
- CATEGORY_RISK "meme" now hard BLOCK (no more amplified losses).
- penny_volume strategies emit 0 (deprecation).
- No regression on high-float legitimate names (if any remain in EQUITY LC list).
- 1 swarmv2-pr-review or manual review on the diff passes with no critical risk.
- Dashboard /audit EQUITY and CRYPTO tiles show reduced volume from meme/penny (n stable or cleaner).

**Risks & rollback:**
- Risk: over-block (some "penny" may be legitimate mid-cap in future); mitigated by helper using mktcap<$2B / ADV<$5M (configurable) + allowlist in config.
- Rollback: set `PENNY_MEME_CLASS_GATE=0` env (or comment the if), or revert the CATEGORY_RISK map.
- No impact on resolver, paper (unless tv-paper-trade hooks scanner), DB, or GHA paths (no new pipeline script; quality_gates and config already in audit-dashboard.yml paths).

**Missed impacts addressed (from post-swarm review in reports/asset_class_enhancements_pr_scopes_2026-05-15.md):**
- Coordinated with open PR #1083 (which touches VIX/FOREX/ML/baby but not PENNY class gate — complementary).
- Re-uses existing kill_gate min-n logic for thin classes.
- No new data fetch or deps (pure symbol/class gate).
- LONG bias note: penny/meme are often pump (LONG) — the class gate helps regardless of direction.

**Refs:** asset_class_action_items_2026-05-15 (priority #6), verification_2026-05-15, daily_ideas_synthesis #8 (drop list), Kimi edge audit 2026-05-11, MASTER M-038.

**Implementation order in bundle:** This is a standalone small PR (low risk, high leak-closure impact). Can be done before or after #1083 merge. After this, EQUITY universe split (PR-2) becomes cleaner (fewer pennies to split).

---
Created 2026-05-15 as part of asset-class enhancements PR set (review of daily_ideas.MD + MASTER + recent .MDs + swarm). Swarm review of this change to follow before push.
