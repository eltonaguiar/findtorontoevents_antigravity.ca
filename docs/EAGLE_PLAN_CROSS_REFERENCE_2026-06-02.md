# EAGLE Plan Cross-Reference — 2026-06-02

**Date:** 2026-06-02 (updated 18:46Z with EAGLE-6 + ADR-2026-06-02-01)
**Author:** claude-opus-4-7-c9b9
**Source:** 8 EAGLE MDs + EAGLE-6 implementation in the 24h window + 1 EAGLE_JUNE2 root-cause

## Purpose

Multiple agents shipped overlapping EAGLE plans on 2026-06-02. Future readers will hit a "which one is canonical?" trap. This doc establishes the cross-reference and the single canonical-source rule.

## Changelog

- **2026-06-02 18:46Z (v2)**: Added EAGLE-6 (minimax-m3-free, PR #456, commit `5b8704cef`/`b194de6d6`) entry. EAGLE-6 is the final gate at production_scanner 6f2.7 — supersedes parts of my SOURCE_SYSTEM_CONCENTRATION_CAP spec (EAGLE-6 HHI<=0.20 is tighter than my HHI<=0.30 soft gate). ADR-2026-06-02-01 records the relationship and the "complementary, not duplicative" decision.
- **2026-06-02 18:16Z (v1)**: Initial cross-reference for 8 EAGLE plans + 3 spec docs.

## The 8 EAGLE plans (all 2026-06-02)

| Plan file | Author | Length | Status | Canonical ref to EAGLE_JUNE2? |
|---|---|---:|---|---|
| `EAGLE_JUNE2_claude-opus-4-7.md` | Claude Opus 4.7 (mine) | 462 | **CANONICAL** | (self) |
| `EAGLE2_2026-06-02_CLAUDE_OPUS_4_7.MD` | Claude Opus 4.7 | 175 | EAGLE-2 enhancement | yes (Predecessor line 5) |
| `EAGLE3_2026-06-02_CLAUDE_OPUS_4_7.MD` | Claude Opus 4.7 | 162 | EAGLE-3 synthesis+exec of 8 peers | yes (line 5) |
| `EAGLE2_2026-06-02_minimax-m3-free.MD` | minimax-m3-free | 213 | EAGLE-2 enhancement | yes (line 5) |
| `EAGLE3_2026-06-02_minimax-m3-free.MD` | minimax-m3-free | 620 | EAGLE-3 quant review+enhance | (untested) |
| `EAGLE2_2026-06-02_MIMO_FINAL.MD` | Mimo v2.5 Pro | 138 | EAGLE-2 final impl | not cross-ref'd |
| `EAGLE2_JUNE2_MIMO_V2_5_PRO.MD` | Mimo v2.5 Pro | 314 | EAGLE-2 enhancement | not cross-ref'd |
| `reports/EAGLE2_2026-06-02_CLAUDE_CODE.MD` | Claude Code (gx10) | 590 | EAGLE-2 enhancement | (DRAFT) |
| `reports/EAGLE2_2026-06-02_COMPOSER.md` | Composer (Cursor) | 501 | EAGLE-2 quant | (DRAFT) |
| `reports/EAGLE2_2026-06-02_GROK.md` | Grok | 309 | EAGLE-2 enhancement | (DRAFT) |
| `reports/EAGLE2_2026-06-02_deepseek_v4.MD` | DeepSeek v4 (Mercury 2) | 154 | EAGLE-2 quant | (DRAFT) |
| `PR #456` (EAGLE-6 plan in PR body) | minimax-m3-free | (PR doc) | **EAGLE-6 statistical admissibility gate** | (gate sits ON TOP of EAGLE-4/5) |

**EAGLE3_2026-06-02_CLAUDE_OPUS_4_7.MD is the synthesis-of-8 file** — it cites all 8 peer EAGLE MDs in its section 1 table and reaches a uniform consensus on 5 points.

**EAGLE-6 (minimax-m3-free, PR #456)** is the first plan that was both documented AND implemented in the same window. The implementation lives at `alpha_engine/eagle_gates.py` and is wired into `alpha_engine/production_scanner.py:5608` (the `apply_eagle6_admissibility` call at the 6f2.7 step). EAGLE-6 fails-open on missing data (`UNSCORED` verdict) and emits per-pick `_eagle6_verdict` + `_eagle6_gates` tags for observability.

**EAGLE3_2026-06-02_CLAUDE_OPUS_4_7.MD is the synthesis-of-8 file** — it cites all 8 peer EAGLE MDs in its section 1 table and reaches a uniform consensus on 5 points.

## Canonical-source rule (operator directive)

Per `project-eagle-june2-2026-06-02.md` memory and the CLAUDE.md "Do NOT trust unsourced model claims about /audit numbers" rule:

1. **`EAGLE_JUNE2_claude-opus-4-7.md` is the root-cause canonical doc.** When a future agent asks "why are our strategies bad?", cite this file.
2. **Per-class action items live in section 7 of EAGLE_JUNE2** — 7 next actions including the concentration cap spec (`docs/SOURCE_SYSTEM_CONCENTRATION_CAP_2026-06-02.md`), score booster spec (`docs/SCORE_BOOSTER_CALIBRATION_VERIFICATION_2026-06-02.md`), and DB creds migration spec (`docs/DB_CREDENTIALS_MIGRATION_2026-06-02.md`).
3. **EAGLE-2 plans (8 of them) are enhancement layers** — they accept the EAGLE_JUNE2 root cause and propose specific actions. The EAGLE-3 synthesis collapsed them.
4. **Future EAGLE-4/5/6/... plans must reference EAGLE_JUNE2 in the first 10 lines** (per the EAGLE-2 Claude Opus 4.7 "Predecessor" convention).

## Cross-reference map (action → owner file)

| Action | Canonical source | Cross-referenced in |
|---|---|---|
| Root cause = research-to-production translation gap + concentration + SL/TP mis-tune + data feed | `EAGLE_JUNE2_claude-opus-4-7.md` section 0 + 5 | EAGLE-2 Opus 4.7, EAGLE-2 minimax, EAGLE-3 Opus 4.7 (synthesis) |
| Source-system concentration cap (n<50 hard gate, HHI<=0.30 soft) | `docs/SOURCE_SYSTEM_CONCENTRATION_CAP_2026-06-02.md` | EAGLE_JUNE2 section 7.1. **SUPERSEDED for HHI by EAGLE-6** (HHI<=0.20 per-strategy is tighter; see ADR-2026-06-02-01 below) |
| Score booster calibration (smoothing + recalibration + drift) | `docs/SCORE_BOOSTER_CALIBRATION_VERIFICATION_2026-06-02.md` | EAGLE_JUNE2 section 6.2 |
| DB creds to GitHub Secrets (P1 security) | `docs/DB_CREDENTIALS_MIGRATION_2026-06-02.md` | EAGLE_JUNE2 section 7 (linked from Qwen ownership memory) |
| Promotion gate (lab to production) | `EAGLE2_2026-06-02_CLAUDE_OPUS_4_7.MD` Pillar 3 #12-14, also `EAGLE2_2026-06-02_minimax-m3-free.MD` "What I add #2" | EAGLE-3 Opus 4.7 "Per-peer contributions" |
| ETF Dual Momentum Day-30 checkpoint | `EAGLE_JUNE2_claude-opus-4-7.md` section 7.4 + `project-etf-pilot-day1-2026-06-02.md` | EAGLE-2 Opus 4.7 Pillar 4 ETF row, EAGLE-2 minimax ETF row |
| ML conf cap 0.95 to 0.85 (anti-predictive) | `EAGLE3_2026-06-02_CLAUDE_OPUS_4_7.MD` "Claude Code - ML confidence is anti-predictive" | PR #440 (shipped 2026-06-02) |
| Sign-flip purge 367 rows | `EAGLE2_2026-06-02_CLAUDE_OPUS_4_7.MD` Pillar 1 #4 | PR #432 + #433 (shipped) |
| Resolver intrabar OHLC replay on 9,657 ghost OPEN picks | `EAGLE_JUNE2_claude-opus-4-7.md` section 7.7 | Not yet EAGLE-2 referenced |
| Per-class mutation framework | `EAGLE_JUNE2_claude-opus-4-7.md` section 6.3 | EAGLE-2 Opus 4.7 Pillar 2 #7-11 |

## ADR-2026-06-02-01: SOURCE_SYSTEM_CONCENTRATION_CAP spec vs EAGLE-6 HHI gate

**Context:** On 2026-06-02 06:55Z, I shipped `docs/SOURCE_SYSTEM_CONCENTRATION_CAP_2026-06-02.md` proposing a per-source-system concentration cap (n<50 hard gate + HHI<=0.30 soft gate) at `alpha_engine/concentration_cap.py`. The doc explicitly stated the cap is **not yet merged** and needs 2nd-agent review per CLAUDE.md 2026-05-31. At 18:00Z, minimax-m3-free shipped EAGLE-6 (PR #456) which implements an HHI<=0.20 per-strategy cap at the production pipeline step 6f2.7 via `alpha_engine/eagle_gates.py::apply_eagle6_admissibility`.

**Decision:** Treat EAGLE-6's HHI gate as **superseding** my spec doc for the HHI threshold (0.20 vs 0.30). My spec's n<50 cold-start escape + per-class scope remain valid proposals that the EAGLE-6 PR did NOT cover. The two are **complementary, not duplicative**:

| Concern | SOURCE_SYSTEM_CONCENTRATION_CAP spec | EAGLE-6 |
|---|---|---|
| HHI threshold | 0.30 (soft, post-add) | 0.20 (hard, per-strategy) |
| Scope | per asset_class x source_system | per strategy pick share |
| Cold-start | n<10 skip, n<50 hard block | n<30 = INSUFFICIENT-N verdict |
| Implementation | spec only (NOT merged) | merged at 6f2.7 |
| Status | DRAFT (superseded for HHI) | SHIPPED |

**Action:** My spec doc should be **kept** (for the per-asset-class scope and the cold-start logic) but annotated with "HHI=0.30 SUPERSEDED by EAGLE-6's HHI=0.20" in its next revision. This ADR records the relationship so a future reader does not wonder why we have two concentration-cap proposals.

**Why not just delete my spec?** Because (a) EAGLE-6 does not cover the per-asset-class dimension (only per-strategy), (b) my spec's cold-start escape is more granular, (c) the spec was committed to origin/main and is cited in `EAGLE_JUNE2 §7.1` — deleting it would create a dangling reference.

**Refs:** PR #456 (EAGLE-6), commit `b194de6d6` (P0 PF math fix), `docs/SOURCE_SYSTEM_CONCENTRATION_CAP_2026-06-02.md` (this spec), `EAGLE_JUNE2_claude-opus-4-7.md §7.1` (original ask).

## Outstanding cross-references to add (not blocking)

These EAGLE-2 plans don't yet link back to EAGLE_JUNE2 explicitly. Low-priority cleanup, not blocking:

- `EAGLE2_2026-06-02_MIMO_FINAL.MD` — needs "Predecessor: EAGLE_JUNE2_claude-opus-4-7.md" in first 10 lines
- `EAGLE2_JUNE2_MIMO_V2_5_PRO.MD` — same
- `reports/EAGLE2_2026-06-02_CLAUDE_CODE.MD` — has EAGLE_JUNE2 references in body but no "Predecessor:" frontmatter line
- `reports/EAGLE2_2026-06-02_COMPOSER.md` — same
- `reports/EAGLE2_2026-06-02_GROK.md` — same
- `reports/EAGLE2_2026-06-02_deepseek_v4.MD` — same

If you are the future reader/agent, do NOT auto-PR these frontmatter lines — per CLAUDE.md "Do NOT autonomously produce code-diff PRs from a single agent's imagined function names + line numbers." Wait for an operator-authorized sweep.

## Memory pointers (already saved)

- `project-eagle-june2-2026-06-02.md` — 462-line review, root-cause canonical
- `project-etf-pilot-day1-2026-06-02.md` — Tier-2 lab pass wired for forward n
- `project-qwen-ownership-2026-05-31.md` — DB creds to Secrets is P1 from qwen's queue
- `feedback-silent-file-revert-pattern_2026-06-01.md` — shared working tree gotcha, multiple FTP-redeploys this session

## Status

**DONE.** Cross-reference map in place. The 8 EAGLE plans are now linked to EAGLE_JUNE2 and to the 3 spec docs (`SOURCE_SYSTEM_CONCENTRATION_CAP_2026-06-02.md`, `SCORE_BOOSTER_CALIBRATION_VERIFICATION_2026-06-02.md`, `DB_CREDENTIALS_MIGRATION_2026-06-02.md`).
