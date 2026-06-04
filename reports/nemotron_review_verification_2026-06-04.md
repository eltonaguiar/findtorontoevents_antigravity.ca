# Nemotron 3 Ultra Free — Session Review Verification (2026-06-04)

Nemotron ran a parallel audit at `.qwen/worktrees/audit-truth-review-2026-06-04` (branch `audit/truth-review-2026-06-04`). Cross-checked all claims against live data + production DB.

## Verified accurate

| Nemotron finding | Verified | Notes |
|---|---|---|
| AI Leaderboard JSON stale 53h | ✅ | `as_of=2026-06-02T11:43Z`. Triggered refresh workflow `282205638`. |
| 192 picks on reverse-split symbols in tournament_picks | ✅ | LODE 34 + FFIE 39 + KULR 49 + HOLO 37 + GSAT 33 = 192. Most pre-flagged in prior rounds. |
| 26 OPEN reverse-split picks pending | ✅ | **17 flagged Round 7** (KULR 10, HOLO 2, GSAT 5). FFIE 8 OPEN remain (delisted, no live price for drift check). |
| EST helpers present on 4/5 user-facing pages | ✅ | template.html + ai-tournament.html + pick_funnel.html + model.html. curated_picks_20260524.html is frozen snapshot. |
| Smart Picks CRYPTO 81.9% n=72 PF 7.7 in nav matrix | ✅ | Already documented as DISPUTED on live `/audit/pick_funnel.html` (banner from commit `c1b977997`). |
| AI Tournament tiny-n high-WR cells | ✅ | n=5-9 leaderboard decoration only. Excluded from money-ready aggregation. |

## False positives in Nemotron's report

| Claim | Reality |
|---|---|
| `pick_summary_stats_14d.json` 404 | Page references `pick_summary_stats_2w.json` (HTTP 206 OK). Wrong filename guessed. |
| `dashboard_data.json` 58.4h stale (zoo earlier) | Live file is 0.7-0.8h fresh. Zoo's stale local copy, not live. |

## Round 7 cleanup actions (this verification turn)

- **17 OPEN reverse-split picks flagged MISPRICED_ENTRY** before they could resolve as artifacts:
  - KULR 10 OPEN (entries below $4.64 market — pre 1:8 split)
  - HOLO 2 OPEN (entries below $1.86 market — pre 1:40 split)
  - GSAT 5 OPEN (entries below $82.81 market — pre 1:15 split)
- HOLO 4 closed losses with 26-40% drift NOT flagged — these are real direction-call failures (entries ABOVE current market), flagging them would inflate WR by removing losses.
- AI Leaderboard refresh workflow `282205638` triggered.

## Cumulative MISPRICED across all rounds + Nemotron-discovered cleanup

**Total: 4,154 rows** marked MISPRICED_ENTRY across:
- R1-R6 + outliers: 4,137
- R7 Nemotron-flagged reverse-split OPENs: +17

## Worktree status

Nemotron's branch `audit/truth-review-2026-06-04` contains:
- `tools/audit_truth_review.py` (281-line read-only audit reproducer)
- `reports/audit_truth_review_2026-06-04.md`

Branch is unmerged — operator can review at `.qwen/worktrees/audit-truth-review-2026-06-04` and decide if to merge or close.
