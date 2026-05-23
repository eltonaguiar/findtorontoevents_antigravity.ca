# 2026-04-28/29 — CI cleanup session summary

Compact summary of one Claude Opus 4.7 session that started as "review Cursor's GH actions work" and turned into 5 merged PRs + a sports FTP deploy + a scheduled verifier agent.

## Outcome

| # | What | Conclusion |
|---|---|---|
| #482 | HF wire-up test fixture rework + sports playwright favicon/stock-nav routes | merged 20:23Z |
| #485 | Quick Guess ML timeout 22→30 min (chronic timeout, not concurrency) | merged 20:55Z |
| #488 | Removed dead `/findstocks/portfolio2/stock-nav.js` script tags from 3 HTML pages | merged 21:03Z |
| #490 | Drop redundant `page.route` after #488 deploy | merged 21:21Z |
| #493 | Remove fatal `git fetch --unshallow` from 5 hourly workflows (`.git` is 37 GB, OOMs ubuntu-latest) | merged 01:24Z |
| FTP | `tools/deploy_sports_files.sh` — 3 files shipped, smoke green pre+post | done 21:03Z |
| trig_01XfQyPWhnHTCFChYiMtLDTQ | One-shot remote agent at 06:30 UTC to verify the disk-space fix held across ≥4 hourly runs | scheduled |

End state of the three originally-failing workflows Cursor flagged:
- **CI Tests** — green (PR #482)
- **Sports endpoint smoke + Playwright** — green, source-of-truth fixed (PR #482 + PR #488 + FTP deploy)
- **Quick Guess ML Agent** — green pending verification (PR #485 timeout + PR #493 disk fix)

## What mattered

### 1. Refusing the wrong fix

Cursor's local-workspace patch rewrote `tests/test_hf_quality_gate_wire.py` with **weaker assertions** (inverted booleans, dropped `_hf_quality_gate_pass` checks, soft-fail escape hatches). That would have shipped green CI by lowering the bar. The on-main test was failing for a real reason — and fixing it correctly meant tracing the actual rejection path, not flipping the assertion.

Trace: `passes_active_gate` mutates `pick["score"]` via `_apply_score_penalties`. With `confidence=0.65`, `score=70`, no `ml_score`, and `datetime.now()` timestamp, the score was penalized to 59, failed the 60 floor at line 4218, and `return False` happened **before** the HF wire-up at line 4349 ever ran. The HF wire-up itself is correct (verified by calling `passes_hedge_fund_gate` directly: returns `(False, "HF_GATE: CRYPTO confidence 0.650 in dead band [0.60,0.70)...")` for the dead-band pick and `(False, "HF_GATE: CRYPTO banned symbol DOGEUSDT...")` for DOGE).

The **fix** was to make `_pick()` realistic: add `ml_score: 0.72` (avoids -20 `null_ml_solo_source` penalty), use `_safe_timestamp()` anchored to the most-recent 22:00 UTC (avoids time-of-day penalty flakiness), add `forward_trades: 30, forward_wr: 0.55` so `_forward_bypass` clears the score floor regardless of penalty stacking. All 6 tests now pass against unchanged on-main `audit_trail/quality_gates.py`.

### 2. Finding the deeper bug under the symptom

PR #482 included a `page.route('**/favicon.ico')` to suppress noise. After it merged, the smoke test still failed — there was a **second** 404 the first fix didn't address: `/findstocks/portfolio2/stock-nav.js`, missing on prod for >10 CI runs. Adding a second narrow `page.route` (PR #482 hotfix) got smoke green, but the underlying bug — three HTML pages referencing a file that doesn't exist anywhere — was still there. PR #488 removed the dead `<script>` tags from `live-monitor/sports-betting.html`, `live-monitor/goldmine-alerts.html`, and `findforex2/portfolio/index.html`. After FTP deploy, PR #490 dropped the now-redundant `page.route`.

### 3. Following the failure stack to a runner-disk OOM

Quick Guess ML had been getting cancelled hourly. Surface symptom: 22-minute timeout. PR #485 bumped to 30 min, fixing the timeout-cancelled cluster. But two new failures came in 8-9 minutes later with `System.IO.IOException: No space left on device`. Investigation: `du -sh .git` → **37 GB**. The workflow's pre-`safe_push.sh` block did `git fetch --unshallow`, which on a ubuntu-latest runner with ~14 GB free disk is fatal. `safe_push.sh` already does `--deepen=150` internally for shallow repos, so the workflow-level unshallow was both redundant AND a disk killer. PR #493 removed it from the 5 affected workflows; the same `--unshallow` in two more files was already inert (those use `fetch-depth: 0`).

## Process notes

- **Worktree-per-task isolation.** All 5 PRs cut from `origin/main` into `.worktrees/`, never touching the local `audit-improvements-2026-04-28` branch (which is 951 commits behind main and holds peer w03yqel9's UEPS work).
- **Subagent dispatch for mechanical multi-file work.** PR #485 (timeout bump, single YAML edit) and PR #493 (unshallow removal across 5 YAMLs) both via `general-purpose` subagents — saved primary context and produced clean PRs.
- **Peer coordination via `claude-peers` MCP** before/after every PR. Three peers active throughout: `w03yqel9` (UEPS execution), `fd0uag0p` (Goal #1 orchestrator, PR queue), `ee95rosa` (Goal #1 Wave 2 strict-gate). Confirmed PR #482 was non-conflicting with peer-owned PR #478 (HF strict smart gate) by reading the latter's diff before pushing.
- **Live-prod verification** via headless chromium against `findtorontoevents.ca/live-monitor/sports-betting.html` after the FTP deploy: 0 console errors, 0 stock-nav refs.

## Loose threads explicitly NOT addressed

- `live-monitor/goldmine-alerts.html` cleanup is in main (PR #488) but not deployed. `tools/deploy_sports_files.sh` only covers `sports-betting.html`; goldmine has no automated deploy. Source is fixed; prod still serves the old file with the dead reference. Low-impact since users see the same noise they always did. Two options for future: (a) add `goldmine-alerts.html` to `SPORTS_FILES` array in the deploy script, or (b) one-off FTP upload.
- `findforex2/portfolio/index.html` similarly fixed in main but not deployed (separate FTP path entirely).
- The 951-commit gap on `audit-improvements-2026-04-28` is peer w03yqel9's UEPS branch. That branch deleted the HF wire-up at `quality_gates.py:4349`. Restoring it is a precondition for HF strict mode to fire on UEPS picks; flagged to that peer via `send_message` but the action belongs to them.

## Verifier agent

`trig_01XfQyPWhnHTCFChYiMtLDTQ` fires once at **2026-04-29T06:30:00Z**. It will:
- Pull `gh run list` for Quick Guess ML and the 4 other affected workflows
- Confirm runs since `01:25Z` (post-merge of PR #493)
- Write `updates/2026-04-29-disk-fix-verification.md`
- If clean: commit + push the verification doc directly to main (docs-only)
- If failures recurred: write the doc but escalate via final report instead of committing

Routine: https://claude.ai/code/routines/trig_01XfQyPWhnHTCFChYiMtLDTQ
