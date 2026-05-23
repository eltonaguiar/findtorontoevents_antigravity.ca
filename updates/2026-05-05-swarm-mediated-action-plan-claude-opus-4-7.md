# Swarm-Mediated Action Plan — Multi-Agent MD Consolidation

**Agent:** claude-opus-4-7 (Claude Code, 1M context)
**Timestamp:** 2026-05-05T01:18Z
**Method:** my analysis → swarm review (3 engines) → consensus action with QA gates

## Inputs reviewed (multi-agent harvest)

| Source | Agent | Format |
|---|---|---|
| `updates/2026-05-05-audit-perasset-deepdive-claude-opus-4-7.md` | claude-opus-4-7 (PR #805) | per-class deep-dive + refuted claims |
| `updates/2026-05-05-swarm-audit-strategy-health-report.md` | freebuff (3-engine swarm) | KILL/INVERSE consensus |
| `reports/audit_swarm_analysis_20260505T005402Z.md` | opencode + 4 engines | quan_engine P0 + per-class fix MDs |
| `reports/copilot_audit_analysis_2026-05-05T01-00.md` | GitHub Copilot Sonnet 4.6 (PR #806) | first-party data + reproducible scripts |
| `reports/fix_<CLASS>_20260505T005402Z.md` × 7 | opencode | per-class action plans |
| `updates/2026-05-05-round-2-execution.md` | unknown | data integrity findings |

## My consensus shortlist (P0 candidates, cross-agent convergent)

| ID | Item | Risk | Convergence |
|---|---|---|---|
| **A** | `closed_picks.json` missing `score/trust_score/smart_score/grade/strat_fwd_wr/trust_tier` (0/7645 populated) | Low (data fix) | opencode round-2 + multiple ✓ |
| **B** | quan_engine volume cap or confidence-band recalibration (CRYPTO PF 1.25→~1.55) | Med (strategy) | opencode + freebuff + my MD ✓ |
| **C** | R:R "INVERTED" code comment (`quality_gates.py:2492-2511`) vs live page (R:R≥2.0 = 58% WR PF 3.06) | Low (verify-then-fix) | OpenCode webfetch ✓ |
| **D** | `alpha_engine_fast` n=358 PF 0.62 -127% PnL — kill or mutate | Med | Cursor + freebuff ✓ |
| E | `futures_momentum` 2% rolling WR alert active | Low (already-flagged) | Copilot ✓ |
| F | `goldmine_stocks` PF 0.14 on n=453 | Low | Copilot ✓ |
| G | regime detection offline (0 trades labeled) | Med (system bug) | Copilot ✓ |

## Swarm review of action plan — 3-engine verdict

**Run:** `swarm_runs/run_20260505T011655Z` — deepseek + cerebras + xai, 3/3 OK, $0.067, 7.5s.

**Unanimous verdict: SHIP-A** — closed_picks.json field backfill.

Reasoning (cerebras + deepseek + xai converge):
- **Lowest risk** — pure data-integrity, no strategy change, no runtime side-effects
- **Highest impact** — unblocks every "Score >= X = Y% WR" tooltip claim, enables real backtest cohort analysis
- **Foundation** — without accurate closed-pick data, can't properly evaluate B/C/D
- **Implementation simplicity** — one-line copy in close-handler

Items B and D require CLAUDE.md `MUTATION_THREE_AXIS_PROTOCOL.md` deep-dive docs first. Item C is analysis-only (re-run `tools/mutation_analysis.py`).

## Item A — full implementation plan with QA gates

### Architecture finding

The active→closed migration happens in `alpha_engine/outcome_resolver.py::resolve_outcomes()`. Active records in `active_picks.json` carry the full field set; closed records currently only retain `exit_price/exit_date/status/pnl`. The fields `score/trust_score/smart_score/grade/strat_fwd_wr/trust_tier` are computed at active-pick-emit time and dropped on close.

### Implementation plan

1. **Locate close-handler** in `alpha_engine/outcome_resolver.py` (around line 891 `resolve_outcomes`). Verify it reads from `active_picks.json` and writes to `closed_picks.json`.
2. **Add field-preservation step** before final closed-pick write:
   ```python
   PRESERVE_FIELDS = ("score", "trust_score", "smart_score", "grade",
                       "strat_fwd_wr", "trust_tier", "ml_score", "confidence",
                       "rr", "rr_ratio")
   for field in PRESERVE_FIELDS:
       if field in active_pick and field not in closed_pick:
           closed_pick[field] = active_pick[field]
   ```
3. **One-time historic backfill** via separate `tools/backfill_closed_pick_fields.py` — reads `closed_picks.json`, joins to `audit_dashboard/data/dashboard_data.json::picks.recent_closed` (which retains the fields), writes back. Idempotent.

### QA gates (per swarm consensus)

| Phase | Gate | Tool | Pass criteria |
|---|---|---|---|
| Pre-merge | Unit test `test_close_path_preserves_score_fields` | pytest | New test green; existing tests unaffected |
| Pre-merge | Static analysis | ruff + mypy | No new warnings on touched files |
| Pre-merge | Code review: transactional ordering (cerebras flag) | reviewer | Confirms copy happens before active-pick deletion in same transaction |
| Post-merge | `audit-dashboard.yml` workflow runs green | gh run watch | conclusion=success |
| Post-merge | `outcome_resolver` next scheduled run produces non-zero score field | python check on `closed_picks.json` | grep shows >0 records with `score` populated |
| Post-merge | Playwright spot-check: open `/audit` → click closed pick → verify tooltip shows non-zero score | `tests/e2e/audit_tooltip.spec.js` (new) | Tooltip displays value, not "n/a" |
| Post-merge | JS console clean on `/audit` page load | Playwright | Zero JS errors related to score fields |
| 24h post-merge | Backfill script run on historic closed_picks | manual | Non-empty count of records updated |

### Risk mitigations

- **Active-pick deletion race**: cerebras flagged that active records may be deleted before close-write. Verify by reading `outcome_resolver.py:resolve_outcomes` before implementing. If race exists, add fields BEFORE the deletion step.
- **Field-name drift**: some agents reference `forward_wr` vs `strat_fwd_wr` — preserve a superset, document the canonical names.
- **Rollback**: backfill script is idempotent; close-handler change is additive (only adds fields, doesn't modify existing). Easy revert via single commit.

## Items B/C/D — deferred with required-precondition checklist

**Each requires before implementation:**
- B (quan_engine cap): `reports/deep_dive_CRYPTO_2026-05-XX.md` per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
- C (R:R reconciliation): re-run `tools/mutation_analysis.py` on current `closed_picks.json`, diff against `quality_gates.py:2492-2511`
- D (alpha_engine_fast): `reports/deep_dive_alpha_engine_fast_2026-05-XX.md` with kill/mutate decision

## Cross-asset findings worth tracking (not in P0 batch)

- E: `futures_momentum` 2% rolling WR — HIGH alert active, mechanical kill-list addition
- F: `goldmine_stocks` PF 0.14 on n=453 — kill candidate (Copilot)
- G: regime detection offline (0 trades labeled) — system bug, separate investigation
- Inverse mutation precedent: `inverse_quan_engine_scalp` at 70% WR / PF 2.0 / n=1643 (freebuff verified) — strong evidence for INVERSE-mutation pattern, not just speculative

## Process notes

- This MD is **planning/analysis only**. No code changes accompany this commit.
- The actual close-handler diff (Item A implementation) ships as a separate PR after pre-merge gates listed above are demonstrated.
- Multi-agent harvest pattern this session: claude-opus-4-7 + claude-sonnet-4-6 (Copilot) + opencode + freebuff + cursor each produced complementary analyses; convergence on quan_engine + closed_picks integrity gives high signal-to-noise.

## Related session work

- PR #800 (revert USDJPY=X kill) — MERGED
- PR #801 (Cursor GHA + lazy DecayTracker) — MERGED
- PR #803 (pandas+pyarrow+numpy) — MERGED + runtime-validated
- PR #804 (CI Tests regressions on main) — MERGED
- PR #805 (claude-opus-4-7 audit per-asset deep-dive) — OPEN
- PR #806 (Copilot Sonnet 4.6 audit + reproducible scripts) — OPEN
- Branch `feat/swarm-audit-strategy-health-2026-05-05` (freebuff) — 3-engine swarm consensus; commits not yet PR'd

## Deferred (user-side actions)

- Update repo secret `GH_PAT` to new `GH_AMPERE` token value (CIM workflow validation showed PR #803 fix works; only the auth-on-push step fails).
- Rotate `THE_ODDS_API_KEY` to unblock sports endpoint smoke.
- Provision `MEMECOIN_DB_PASS` in 50webs cPanel for PR #798 merge.
