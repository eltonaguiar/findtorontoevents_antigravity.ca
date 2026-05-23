# Copilot Non-Crypto Remediation Validation — 2026-05-03

Generated 2026-05-03 ~19:00Z. Read-only post-merge audit (PRs #727 + #731 already merged ~14 h prior to this validation request).

## TL;DR

- **2 of 3 wire-ups are live on `main`.** Wire-up #3 (`MAX_HOLD_HOURS_BY_CLASS` in `audit_trail/universal_pick_resolver.py`) is **MISSING from main**. The change exists only on the unmerged copilot branch.
- The "84/84 tests pass" claim is documented but the test file `tests/test_universal_pick_resolver.py` was **never merged** to main (PR #731 only cherry-picked the elite_scorer + quality_gates test files), so the resolver test is not actually running in CI on `main`.
- Recommendation: open a follow-up PR to land the missing resolver hunk + its test. No fabrication malicious; the PR-split simply dropped the third file.

## PR identification

| Field | Value |
|-------|-------|
| Original copilot branch | `copilot/debug-asset-class-performance` |
| Original copilot commit | `4cda0da92db` (7 files, +308 / -18) |
| PR #727 (merged) | `feat(phase3-wireup): wire non_crypto_boosters + get_effective_min_score into live pipeline` — merged 2026-05-03T04:49:08Z by eltonaguiar — merge commit `f1516173f10` — **2 files** (`alpha_engine/elite_scorer.py`, `audit_trail/quality_gates.py`) |
| PR #731 (merged) | `test+docs(phase3-wireup): cherry-pick copilot tests + doc for PR #727` — merged 2026-05-03T05:09:00Z — merge commit `d398dce90bb` — **3 files** (`tests/test_elite_scorer.py`, `tests/test_quality_gates.py`, `updates/2026-05-03-non-crypto-remediation-wiring.md`) |
| Files originally on the copilot branch but NOT merged | `audit_trail/universal_pick_resolver.py`, `tests/test_universal_pick_resolver.py` |
| `git log main --oneline ... universal_pick_resolver.py` | last touched `9ee4470e02d` (Item 2) — *not* `4cda0da92db` |
| `git branch -r --contains 4cda0da92db` | `origin/copilot/debug-asset-class-performance` only — confirms commit is **not** on main |

There is no open PR carrying the resolver change. Operator action required to land it.

## Wire-up verification

### Wire-up #1 — `passes_smart_gate` -> `get_effective_min_score` — **VERIFIED**

- File: `audit_trail/quality_gates.py` (live on main).
- `STRATEGY_SCORE_OVERRIDES` dict at line 267 contains the cited entries: `forex_rsi2_mean_reversion: 30` (line 269), `bond_yield_momentum: 28` (line 279), plus 17 other non-crypto strategies.
- `get_effective_min_score(strategy_name, asset_class)` defined at line 292; consults overrides first, falls back to `_class_floors`. Crypto strategies are NOT in the override dict, so crypto picks fall through to `SMART_PICKS_MIN_SCORE = 60` (unchanged).
- `passes_smart_gate` at line 4814 calls `get_effective_min_score(...)` at line 4945, gated by env-var rollback `STRATEGY_SCORE_OVERRIDES_DISABLED`.
- Crypto path verified UNAFFECTED.

### Wire-up #2 — `compute_elite_score` -> `compute_non_crypto_boost` — **VERIFIED**

- File: `alpha_engine/elite_scorer.py` (live on main).
- `compute_elite_score` defined at line 1700; calls `compute_non_crypto_boost(pick)` at line 2982-2983 inside a `try/except` block that records `_non_crypto_boost_error` on failure (verified per the doc `updates/2026-05-03-non-crypto-remediation-wiring.md`).
- Module `alpha_engine/non_crypto_boosters.py` exists and exports `compute_non_crypto_boost`.
- The doc cites caps: FOREX +15, COMMODITY/FUTURES +15, ETF +10, BOND +10, EQUITY +8 (all bounded; no unbounded multiplier). Crypto path returns `(0, {"_non_crypto_boost": "skipped_crypto"})`, so crypto scoring is unchanged.

### Wire-up #3 — `universal_pick_resolver` per-class `MAX_HOLD_HOURS_BY_CLASS` — **MISSING ON MAIN**

- File on main: `audit_trail/universal_pick_resolver.py` line 29 still reads `MAX_HOLD_HOURS = 48  # Auto-expire picks older than 48h` with no `MAX_HOLD_HOURS_BY_CLASS` dict, no `_max_hold_hours_for(...)` helper, and the time-expiry branch at line 818 still uses the single `MAX_HOLD_HOURS * 3600` constant.
- The cited diff (`MAX_HOLD_HOURS_BY_CLASS` dict + `_max_hold_hours_for` helper + per-pick lookup) IS present in copilot commit `4cda0da92db` but that commit is only on `origin/copilot/debug-asset-class-performance`.
- PR #727's merged file list (`gh pr view 727 --json files`) confirms only 2 files were merged — the resolver was dropped during the PR split.
- A stray reference to `MAX_HOLD_HOURS_BY_CLASS` exists in `alpha_engine/per_class_position_caps.py:80` as a comment claiming "Calibrated to per-asset-class hold window (PR #730 MAX_HOLD_HOURS_BY_CLASS)" — this is a phantom reference; PR #730 doesn't carry the constant either.
- **Net effect on production**: FOREX/BOND/COMMODITY/ETF picks still get TIME_EXIT-closed at 48 h. The score-floor relaxation (#1) and non-crypto boost (#2) help these classes pass the gate, but slow markets will still be auto-closed before TP/SL resolves — the very gap CLAUDE_DEBUGGING_GUIDE.MD Step 7 was meant to fix.

This is **not malicious fabrication**. The doc and the original copilot commit are consistent; the merge step dropped the file. Likely a manual cherry-pick or rebase decision on the operator side.

## Test / CI verification

- `tests/test_elite_scorer.py`: merged via PR #731. Doc claims 6/6 pass.
- `tests/test_quality_gates.py`: merged via PR #731. Doc claims 56/56 pass.
- `tests/test_universal_pick_resolver.py`: **NOT merged** — only on copilot branch. The "5/5 pass (was 4; +1 new test for per-class hold)" claim cannot be verified on main and that new test is not running in CI.
- Recent CI on main (audit-dashboard.yml): last 3 completed runs all `success` (`7f1946f54aa`, `af94b7da58c`, `6622e507156`); 2 newer runs in_progress as of this report.

Step-9-style spot checks (per the doc):
- `get_effective_min_score("fear_greed_contrarian", "CRYPTO") == 60` -> claimed pass; consistent with code-read.
- `get_effective_min_score("forex_rsi2_mean_reversion", "FOREX") == 30` -> consistent with `STRATEGY_SCORE_OVERRIDES` line 269.
- `get_effective_min_score("bond_yield_momentum", "BOND") == 28` -> consistent with line 279.

## Swarm validation

**SKIPPED** to stay within the $0.10 token budget. The swarm dispatch step would have re-litigated these grep findings; the file-state truth is unambiguous.

## Goal-1 alignment (per CLAUDE.md asset-class-health baseline)

Pulled from `audit_dashboard/data/dashboard_data.json::performance.asset_class_health`:

| Class | PF | WR | n | Verdict |
|-------|------|------|------|---------|
| EQUITY | 1.41 | 52.9% | 420 | T2-candidate |
| CRYPTO | 1.24 | 44.6% | 8218 | watch |
| FOREX | **0.27** | 46.4% | 1169 | stressed (sub-floor) |
| COMMODITY | 1.78 | 46.9% | 750 | T2 PF, low WR |
| ETF | 1.24 | 55.2% | 87 | borderline |
| BOND | 1.72 | 55.6% | 18 | T2 PF + WR (n thin) |

Expected post-merge effect of what *did* land (#1 + #2):
- FOREX: score-floor relaxation (rsi2_mean_reversion 40 -> 30 etc.) lets more proven-strategy picks through. Non-crypto boost adds session-overlap + carry-differential signal. Net: more candidates surface, but with FOREX's structural 0.27 PF, expect modest lift, not Tier-2.
- BOND/COMMODITY/ETF: low-n classes; #2 boost helps ranking. ETF n=87 (need n>=100 per charter) — score-floor relaxation may help cross n=100 threshold.

Expected post-merge effect of #3 (when it lands):
- FOREX/BOND time-exit window 48h -> 120h. Many forex/bond picks resolve over 5-14 days; lifting the hold window stops premature TIME_EXIT closes from masking true WR. This is the single largest expected WR lift for these slow markets.

**Conclusion**: the *most impactful* wire-up for FOREX/BOND (the worst-performing classes) is the one missing. PRs #727+#731 alone will not move FOREX off the stressed verdict.

## Recommended action

| Step | Status |
|------|--------|
| Merge PR #727 / #731 | DONE 2026-05-03T05:09:00Z |
| Open follow-up PR with resolver hunk + test | **REQUIRED — operator action** |
| Update `alpha_engine/per_class_position_caps.py:80` comment that references PR #730 (currently a phantom) | nice-to-have, do in same follow-up |
| Decide whether to roll-forward (cherry-pick `4cda0da92db -- audit_trail/universal_pick_resolver.py tests/test_universal_pick_resolver.py`) or roll a fresh PR with same diff | operator choice |

Suggested cherry-pick command (do not execute without operator approval):

```
git fetch origin copilot/debug-asset-class-performance
git checkout -b feat/wire-resolver-time-exit-2026-05-03 origin/main
git checkout 4cda0da92db -- audit_trail/universal_pick_resolver.py tests/test_universal_pick_resolver.py
git commit -m "feat(resolver): wire MAX_HOLD_HOURS_BY_CLASS into universal_pick_resolver TIME_EXIT (split from PR #727)"
gh pr create --title "feat(resolver): per-class TIME_EXIT window" --body "Splits the missing third file from copilot wire-up commit 4cda0da92db. PRs #727 + #731 carried the score override + boost wires; this lands the per-class 48 h / 96 h / 120 h TIME_EXIT helper."
```

No `gh pr review --comment` posted on PR #727 because (a) author is `eltonaguiar` (operator), and (b) the PRs are already merged — review feedback would be unactionable on the merged PR.

## Open questions (BLOCKED-ON-OPERATOR)

1. Was the resolver hunk intentionally dropped (e.g. operator wanted to test #1+#2 isolated first), or was it an accidental cherry-pick miss?
2. The phantom "PR #730 MAX_HOLD_HOURS_BY_CLASS" comment in `alpha_engine/per_class_position_caps.py:80` — is PR #730 a typo for #727, or an unrelated PR?
3. Should the follow-up PR include the cap recalibration that the per-class-caps comment expected (i.e. were the position caps tuned for the longer hold windows that aren't actually applied yet)?
