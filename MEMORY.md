# MEMORY

- **Response looping rule added to AGENTS.md, SOUL.md**: Scan responses for repetitive phrasing, circular reasoning, and over-explaining. Lead with answer, provide only necessary context, then stop. Quality > quantity.

- Added caching of OHLCV data to local CSV files to reduce API calls.
- Implemented concurrent processing of multiple crypto pairs using ThreadPoolExecutor for predictions and backtests.
- Integrated Python logging for better traceability and error handling.
- Updated imports to include concurrent.futures and logging.
- Refactored run_predictions and run_backtests to use parallel execution and logging.
- Added cache directory creation and ensured data persistence.
- Long-term crypto mission: judge pick quality against the true hourly crypto winners, with a wider liquid universe and hindsight reverse-engineering of better entries and TP/SL templates.
- Copy-trading research note: BingX and MQL5 are the strongest public source families for large-scale verified trader pools. BingX exposes crypto leaderboard cards with public performance stats; MQL5 exposes forex signal cards with growth, reliability, copy price, and category listings.

- Heartbeat 2026-03-26: Detected negative average PnL across active portfolios. Triggered mutate_top_performers.py subagent to evolve new strategies based on best-performing DNA from MySQL. 64 new mutations registered into the registry.

- **Institutional Strategy Policy (Rehabilitation-First):** Never "kill" a strategy outright. Every underperformer must cycle through the 6-stage Rehabilitation Pipeline defined in `TESTING_PROTOCOL.MD` (Cross-symbol → Cross-asset → Inverse → Mutation → Regime → Crossover) before reaching the Graveyard. Evidence: `winner_pattern_precursor_inverse` = 81.2% WR, `claude_gainer_ml_inverse` = 80.0% WR.

- **2026-04-12 PR Integration Session:** Created 4 new PRs for branches with integrated code lacking formal submissions: PR #127 (10 enhanced multi-asset strategies + MC validator), PR #128 (drift telemetry), PR #129 (FOREX/PAXG baby strategies), PR #130 (MIMO strategies + edge analysis). All 4 successfully merged to main (commit de81786b). 6 remaining PRs open (#76, #77, #79, #118, #119, #121) for continued strategy work.

- **2026-05-05 Swarm Cleanup Session:** Fixed 4 critical bugs in swarm tooling (cost overrun in openrouter estimate, thread safety in orchestrator, empty-envelope retry, API key pre-flight skip). Fixed YAML agent silent-drop bug causing 71% hallucination rate in bug_hunter. Fixed Hermes --model flag not reaching CLI causing 404 errors. Both swarms (.ruflo/ + tools/swarm/) verified ready on main. Confluence tests: 13/13 passed. Pruned dead files (_config_shared.py, bridge.ts, quant-*.md). Committed session docs + 3 ruflo agent YAMLs. Created HERMES_SWARM_NOTES.MD (comprehensive reference for Hermes Agent). Key files: HERMES_SWARM_NOTES.MD, CHATLOG_2026-05-05.md (in updates/), RUFLO_SWARM_GUIDE.MD.

- **Hermes Agent note:** Runs via WSL (`hermes chat -q`). 36 commits behind upstream — user should run `hermes update`. grok-3-fast not found — use grok-3 or grok-3-mini. Default orchestrator tier is `hybrid` (paid first, free fallback). OpenRouter :free models broken (404/429) — use pollinations or set OPENROUTER_API_KEY.

- **Cross-PC Protocol (cross-pc/v1) key learnings, 2026-05-07):**
  - **Peer identity matters:** `from=` field in envelope should match the actual runtime, not an arbitrary `--peer-id`. Cursor traffic showing `from=claude-main` was mislabeled — fixed by runtime-based identity in `cursor_claude_adapter.py`.
  - **Identity resolution order:** 1) explicit `--peer-id`, 2) `CROSS_PC_PEER_ID` env var, 3) inferred `<runtime>-<hostname>` from `--runtime` / `CROSS_PC_RUNTIME`.
  - **Broadcast routing:** Messages with `to=all` are stored under peer `"all"` in the offline queue (not empty-string broadcast). The gateway routes them to the `all` peer inbox, NOT via live WS broadcast to all sessions. WS broadcast is live-only (no persistence).
  - **`--poll-peer` flag:** The freebuff adapter now supports `--poll-peer all` to fetch the `all` inbox in addition to own inbox. Broadcasts only appear in the `all` inbox, not in individual peer inboxes.
  - **`to=` empty vs `to=all`:** Empty `to` = live-only broadcast (no persistence). `to=all` = stored in `all` peer's offline queue (durable, pollable).
  - **OfflineQueue deduplication:** Fixed bug where `OfflineQueue.push()` was not deduplicating by `message_id`, causing duplicates. Commit `ed87cf5346c`.
  - **Auto-ACK on poll:** Gateway now auto-ACKs messages when polled. Commit `07a59e079ed`.

- **swarm-sync-v2.yml bug (2026-05-07):** `CHANGED_FILES="$CHANGED_FILES $file"` accumulated a leading space, causing `git add " agent_shared_memory.json"` → exit code 127 (bare quote as command). Fixed with bash array: `CHANGED_FILES=()` / `CHANGED_FILES+=("$file")` / `git add "${CHANGED_FILES[@]}"`. Pushed to main as `458677309d1`.

- **GH_PAT_AGENTS secret:** Set in repo settings as `gho_...` token with `repo` scope. Enables workflow to push changes via `safe_push.sh`. Verified working on `swarm-sync-v2.yml` and `swarm-janitor.yml`.

- **Git workflow for this repo:** Remote `main` is protected — force-push blocked. Non-fast-forward pushes require pull-first. Always `git pull origin main --rebase` before pushing if remote has new commits. Use `safe_push.sh` or `git push --force-with-lease` (respects protection rules).