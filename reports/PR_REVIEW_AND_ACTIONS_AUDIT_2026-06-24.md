# Open-PR Review + GitHub Actions Audit — 2026-06-24

**Author:** claude-opus · invoked via /money-maker-ready-June112026edition (args: "review all open PRs + actions audit"). Read-only review — no merges/closes executed (those are outward/irreversible operator decisions).

## 1. GitHub Actions health — ✅ GREEN

- **0 failures in the last 80 completed `main` runs.** The scheduled fleet (scanners, resolvers, deploys, picks-now, signal recorder, etc.) is healthy as of 2026-06-24T15:45Z.
- No systemic workflow breakage. No action required.

## 2. Root-cause of "every PR shows failing checks"

The failing PR checks are the `test (3.11)` / `test (3.12)` matrix job. Pulled the logs: the suite runs 6,354 tests; only **3 fail**, and they are **stale-drift, not current bugs**:

| failing test | cause | status on current main |
|---|---|---|
| `test_tpsl_policy::...defaults_for_commodity` (assert 100.5==106.25) | old branch returned the 0.5% MIN_TP_PCT floor for a no-history commodity | **PASSES on main** — verified locally: `get_optimal_tp_sl(category="commodity", symbol="GC=F", entry=100, LONG)` → (106.25, 96.25); commodity policy = 2.5×2.5/100 = 0.0625 TP / 0.0375 SL |
| `test_select_forward_track_candidates::test_g_load_pick_funnel_real` | `FileNotFoundError: pick_funnel_90d.json` (gitignored / hourly-regenerated; absent in CI) | test-design defect introduced by **#667** — needs skip-when-absent or a fixture |
| `test_select_forward_track_candidates::test_h_live_data_smoke_run_only_no_write` | same FileNotFoundError | same (#667) |

`tpsl_policy.py`, `adaptive_tp_sl.py`, `test_tpsl_policy.py` are **identical to origin/main** and pass — confirming the commodity failure is purely branch staleness.

## 3. Per-PR triage — ALL 10 are severely stale

`gh api compare/main...<head>` — ahead/behind main:

| PR | head | ahead | **behind** | recommendation |
|---|---|---:|---:|---|
| #667 | feat/b5-forward-track-tool (06-24) | 1 | 879 | **REBASE** + fix the 2 new file-dependent tests (skip-when-absent); content (cell selector) may be genuinely new |
| #666 | feat/b1-backfill-price-guard (06-24) | 1 | 879 | **REBASE**; verify the resolver guard isn't already on main |
| #665 | fix/ci-tests-drift-reconciliation | 3 | 4,815 | the active CI-drift fix — **REBASE + finish**; most aligned with this audit |
| #657 | feat/contract-test-cold-merge (06-22) | 1 | 3,429 | **REBASE**; re-evaluate vs current CI |
| #622 | feat/honest-kill-switch-per-class-thresholds | 1 | (compare 404 — ref moved) | re-open compare after rebase; kill-switch work largely on main already |
| #600 | worktree-equity-reachability (06-13) | 3 | 15,166 | **CLOSE as superseded** (11 days, 15k commits; edge-hunt already concluded) |
| #595 | feat/intrabar-replay-noncrypto (06-13) | 1 | 15,794 | **CLOSE as superseded** (intrabar replay now default-on on main) |
| #581 | feat/minimax-next-steps-batch | 14 | 15,904 | **CLOSE / cherry-pick** any unmerged file |
| #564 | audit-dig-deeper (06-12) | 163 | 14,337 | **CLOSE as superseded** (163 ahead but 14k behind = unmergeable divergence) |
| #562 | feat/audit-edge-hunt-session-docs (06-12) | 2 | 16,608 | **CLOSE as superseded** (session docs, long obsolete) |

(The huge "behind" counts are inflated by main's hundreds of daily `[skip ci]` scanner commits, but every branch genuinely predates large swaths of merged work.)

## 4. Verdict + recommended operator actions

- **CI is not actually broken** — main is green; the PR red is stale-branch drift. No code fix needed on main for the tpsl test.
- **5 stale doc/session PRs (06-12/13: #562, #564, #581, #595, #600)** → recommend **close as superseded** (content months old; edge-hunt concluded + documented in later reports).
- **4 recent PRs (#657, #665, #666, #667)** → **rebase onto main + re-run CI**; for #667 also fix the 2 new tests that depend on `pick_funnel_90d.json` (make them skip when the gitignored file is absent — the same pattern other data-dependent tests already use).
- Merges/closes are outward-facing + irreversible → left for operator decision, not auto-executed.
