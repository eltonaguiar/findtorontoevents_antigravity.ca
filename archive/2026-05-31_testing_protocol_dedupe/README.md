# Archive: 2026-05-31 testing-protocol dedupe

This directory contains 33 files that were superseded by the canonical
synthesis in `TESTING_PROTOCOL.MD` Section 0 (PR #404).

**Files are NOT deleted** — they are preserved here for forensic review.
Operator can verify the consolidation by spot-checking any archived file
against the canonical synthesis.

Filenames are flattened with `__` substituted for `/` so the original
path can be reconstructed (e.g. `reports__money_maker_ready_20260512T194402Z.md`
came from `reports/money_maker_ready_20260512T194402Z.md`).

## Reason for archival (per batch reviews)

| File | Reason |
|------|--------|
| `reports__money_maker_ready_2026051*Z*.md` | Dated snapshots, superseded by `reports/money_ready_per_class_synthesis_2026-05-31.md` |
| `reports__money_ready_state_2026-05-12T23Z.md` | Introduced orphan "Tier 3" band (PF>=1.2/WR>=45%) used nowhere else |
| `reports__money_ready_verdict_2026-05-17.{md,json}` | Used SPA family-wise alpha=0.1 (14x looser than canonical Bonferroni 0.007) |
| `reports__money_ready_validation_plan_2026-05-11.md` | Cited poisoned `multi_asset_cot PF=12.16 n=91` as actionable Tier-1 |
| `reports__MONEY_MAKER_READYV2_*.md` (ADDENDUM/FREEBUFF/NORTH_STAR) | Superseded methodology spine |
| `reports__roadmap_no_edge_to_money_ready_2026_05_18.md` | PBO<=0.55 (11x looser than canonical PBO<=0.05) |
| `reports__equity_money_ready_path_20260517.md` | n>=50 / n>=20 floors (well below canonical n>=500 graduation) |
| `reports__2026-05-25_money_maker_readyv2_vs_actual.md` | Screening-only floors not flagged as such |
| `reports__PHENOMENAL_PERFORMANCE_METHODOLOGY.md` | Tier card duplicates `docs/PERFORMANCE_CHARTER.md` |
| `reports__CONFIDENCE_METHODOLOGY_2026-05-24.md` | Persona n>=20 floor self-acknowledged as "mathematically unsupportable" |
| `reports__ai_tournament_methodology_swarm_review_20260519.md` | n=30 ranking-only floor; tournament T3 PF drift (1.3 vs charter 1.2) |
| `reports__CLAUDE_METHODOLOGY_PROOF_2026_05_02.md` | FLAT_PNL_THRESHOLD pre-fix snapshot |
| `docs__SWARM_REVISED_METHODOLOGY_2026-05-13.md` | Pre-cursor-framework methodology revision |
| `docs__METHODOLOGY_FOR_EXPERTS.md` | Stale 2026-03-24 snapshot, predates resolver v2 + cursor framework |
| `reports__kimi_uplift_2026_05_02__METHODOLOGY.md` | Tier table uses point estimates at n=20 (canonical requires CI lower bound + n>=500) |
| `reports__hyrotrader_methodology_enhancements_2026-05-15.{md,html}` | 90-day P0/P1/P2 roadmap (HTML twin of MD), complementary, dated |
| `reports__DEEP_DIVE_MONEYREADY_2026-05-18.md` | Per-class admissibility deep-dive, superseded by `reports/money_ready_per_class_synthesis_2026-05-31.md` |
| `reports__HARVEST_CONSTRUCTIVE_MONEY_READY_2026-05-19.md` | Multi-AI harvest, ideas absorbed into canonical synthesis |
| `reports__MONEY_READY_METHODOLOGY.md` | Historical bridge doc; self-corrected to n>=250 (CRYPTO 500). Preserved here intact. |
| `reports__money_maker_readyv2_2026-05-17.md` | Historical — established concentration-first rule (preserved) |
| `reports__money_maker_ready_v2_deep_dive_2026-05-31.md` | **Tier labels INVALID** — used capped-MC bootstrap (banned per `reports/peer_claude-URGENT_METHODOLOGY_FLAG_MC_AUDIT_TOOL_2026-05-31.md`) |
| `updates__2026-04-23-audit-whatif-hc-scoping-methodology.md` | Historical scoping doc; active spec lives in `audit_dashboard/hc_filter.js` |

## Restoration

If a file is needed back, `git mv` it from the archive path back to its
original path (replace `__` with `/`).
