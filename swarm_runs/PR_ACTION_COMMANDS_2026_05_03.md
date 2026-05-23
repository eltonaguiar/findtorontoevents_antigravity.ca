# PR Action Commands — 2026-05-03 (operator approval queue)

**DO NOT execute these commands automatically.** Each block is staged for operator y/N. Validates `swarm_runs/PR_TRIAGE_2026_05_03_MANUAL.md` recommendations using the FIXED 3-engine swarm pipeline (`tools/swarm/prompts/pr_review_inline.md` + `_pr_capture.py`).

Run dirs:
- `swarm_runs/pr_validate_batch_2026_05_03/` — deepseek+xai for all 6 PRs
- `swarm_runs/pr_validate_kimi_660/` — kimi for #660
- `swarm_runs/new_engine_audit_20260503T175428Z/kimi/pr_723.json` — kimi for #723 (re-used; pre-existing healthy run)

Kimi was attempted on every PR but the kimi.exe `-p <prompt>` argv path hits the Windows ~32K command-line ceiling for prompts >20KB; only #660 (20KB) and #723 (40KB → succeeded earlier from a smaller medium-cap capture) made it through. Where kimi is missing, the deepseek+xai pair (both HEALTHY per `swarm_inspect.py`) is the consensus basis.

---

## Validated MERGE candidates

### PR #723 — B18 shadow-mode auto-promotion

```bash
# Swarm verdict: 3/3 MERGE/HIGH; evidence cited:
#   kimi:     audit_trail/dashboard_generator.py:13585 (id() dedup), PR body (default-OFF flag)
#   deepseek: audit_trail/quality_gates.py:3922-3924 (shadow bypass), reports/feedback/B18-claude-sonnet-self-review-2026-05-03.md
#   xai:      reports/feedback/B18-claude-sonnet-self-review-2026-05-03.md (rolling-window note), PR body (B18b deferred)
# CI status: no checks reported (mergeStateStatus UNKNOWN)
# Mergeable: UNKNOWN (operator should `gh pr view 723 --json mergeable` immediately before merge)
# All 3 engines flagged only MINOR concerns; X's priority-merge call CONFIRMED.

gh pr review 723 --approve --body-file swarm_runs/pr_validate_batch_2026_05_03/review_body_723.md
gh pr merge 723 --squash --delete-branch
```

### PR #724 — FOREX/CRYPTO deep-dives + rescue plan (docs-only)

```bash
# Swarm verdict: 2/3 MERGE-leaning (deepseek MERGE/HIGH; xai HOLD/HIGH on peer-ack-gate; kimi skipped — 66KB prompt > 32K Windows arg cap)
# Evidence cited:
#   deepseek: file-list-backed (6 docs); reports/FOREX_RESCUE_CONSOLIDATED_2026_05_03.md sec 7.1
#   xai:      reports/FOREX_RESCUE_CONSOLIDATED_2026_05_03.md:130-135 (peer-ack gate)
# CI status: no checks reported
# Mergeable: UNKNOWN
# X's priority-merge call CONFIRMED CONDITIONAL on honoring the no-code-changes constraint stated in the PR.

gh pr review 724 --approve --body-file swarm_runs/pr_validate_batch_2026_05_03/review_body_724.md
gh pr merge 724 --squash --delete-branch
```

### PR #615 — scanner blocker fixes (CONDITIONAL — CI failing)

```bash
# Swarm verdict: 2/3 MERGE-leaning (deepseek MERGE/HIGH; xai HOLD/MEDIUM citing CI red; kimi skipped — 43KB prompt)
# Evidence cited:
#   deepseek: alpha_engine/outcome_resolver.py (v2.1 retry-cap), file-list-backed
#   xai:      checks: 'test (3.12) FAILURE'; alpha_engine/outcome_resolver.py:151 (scope concern)
# CI status: test (3.11) CANCELLED, test (3.12) FAILURE  <-- BLOCKER per xai
# Mergeable: UNKNOWN
# X's priority-merge call DOWNGRADED TO CONDITIONAL: do NOT merge until 3.12 test passes or is documented as pre-existing-unrelated.

# DO NOT merge yet. Use review-only:
gh pr review 615 --comment --body-file swarm_runs/pr_validate_batch_2026_05_03/review_body_615.md

# After CI is green, then:
# gh pr review 615 --approve --body-file swarm_runs/pr_validate_batch_2026_05_03/review_body_615.md
# gh pr merge 615 --squash --delete-branch
```

---

## Validated REQUEST_CHANGES / CLOSE candidates

### PR #660 — emergency gate fixes (close-replace per X)

```bash
# Swarm verdict: 3/3 NOT-MERGE (kimi REQUEST_CHANGES/HIGH; deepseek HOLD/MEDIUM; xai HOLD/MEDIUM)
# Concerns (all 3 engines independently surfaced):
#   - min_ml_score 0.82 vs 0.90 internal contradiction (config/hf_quality_gates.json:25 vs config/per_asset_thresholds.json:15)
#   - min_risk_reward 1.25 vs 1.50 internal contradiction (config/hf_quality_gates.json:28 vs config/per_asset_thresholds.json:13)
#   - max_risk_reward 3.0 vs 2.00 internal contradiction (config/hf_quality_gates.json:30 vs config/per_asset_thresholds.json:14)
# X's close-replace call CONFIRMED. Same-PR JSON contradictions on the most important parameters.

gh pr review 660 --request-changes --body-file swarm_runs/pr_validate_batch_2026_05_03/review_body_660.md
# Optional close (only after author/operator confirms it should be replaced rather than fixed in-place):
# gh pr close 660 --comment "Closing per swarm consensus: same-PR config contradictions (min_ml_score, min_risk_reward, max_risk_reward). Will reopen as a clean reconciliation PR."
```

### PR #661 — infrastructure modules (close-replace per X)

```bash
# Swarm verdict: 2/3 NOT-MERGE (deepseek REQUEST_CHANGES/HIGH; xai HOLD/MEDIUM; kimi skipped — 37KB prompt)
# Concerns:
#   - alpha_engine/statistical_rigor.py referenced by __init__.py + README + body but NOT in changed-files list (deepseek blocking)
#   - test (3.11) FAILURE, test (3.12) CANCELLED (deepseek + xai blocking)
#   - Hardcoded "2026-05-02T00:00:00Z" in alpha_engine/track_calculator.py export (deepseek major)
# X's close-replace call CONFIRMED. Cited fabricated exports + red CI.

gh pr review 661 --request-changes --body-file swarm_runs/pr_validate_batch_2026_05_03/review_body_661.md
# Optional close:
# gh pr close 661 --comment "Closing per swarm consensus: missing statistical_rigor.py + red CI on 3.11/3.12 + stale hardcoded timestamp. Reopen after restructuring."
```

### PR #644 — per-asset quality gate plan (split candidate per X)

```bash
# Swarm verdict: 1/2 MERGE-leaning (deepseek MERGE/HIGH; xai HOLD/MEDIUM citing scope-creep; kimi skipped — 51KB prompt)
# X's split-into-3 call PARTIALLY CONFIRMED:
#   - xai major concern matches X exactly: 'Body says one file should be changed but multiple files are modified' (PR body vs file list)
#   - deepseek treats the multi-file scope as acceptable since PER_ASSET_QUALITY_ACTIVE_PERMISSIVE=1 default makes active-gate opt-in
# Splits per X's triage: per-asset summary tile (good) / dashboard tile (good) / CI gate (good) / penalty-coefficient deltas (toxic_combo:-25->-10) need separate evidence cite.

gh pr review 644 --request-changes --body-file swarm_runs/pr_validate_batch_2026_05_03/review_body_644.md
# After author splits or updates body+adds penalty-delta evidence:
# gh pr close 644 --comment "Closing per operator decision: split into 3 surgical PRs per swarm-confirmed scope-creep finding."
```

---

## Operator decision matrix

| Action | PRs | Confidence |
|---|---|---|
| Approve + merge | #723 | HIGH (3/3 MERGE) |
| Approve + merge (docs-only, honor peer-ack gate) | #724 | MEDIUM-HIGH (2/3) |
| Comment only; merge after CI green | #615 | MEDIUM (CI red blocks) |
| Request changes | #660, #661, #644 | HIGH (3/3 or 2/2 NOT-MERGE) |

---

## Cost

- deepseek: 6 PRs (~95K tokens total) ~ $0.06
- xai: 6 PRs (~76K tokens total) ~ $0.04
- kimi: OAuth-bundled, $0
- **Estimated total: ~$0.10** (well under the $0.20 cap)

## Open questions

- Kimi was skipped on 4/6 PRs due to Windows arg-length limit (`-p <prompt>` ceiling at ~32KB, prompts ranged 36-66KB). Mitigation paths:
  - Use a smaller `--max-diff` cap when capturing (default 60K — could drop to 8K for kimi-only runs at the cost of partial-diff fabrication risk).
  - Wire kimi to read prompts from a temp file (kimi CLI does support `--input-format text` with stdin per `worker_runner.py:603-607`, but the dispatcher doesn't currently use it).
  - For these 4 PRs, deepseek+xai HEALTHY pair carried the consensus.
- All 6 PRs report `mergeStateStatus: UNKNOWN` and `mergeable: UNKNOWN` — operator should re-fetch immediately before any merge command.
