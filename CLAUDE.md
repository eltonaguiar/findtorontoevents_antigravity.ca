# FindTorontoEvents Antigravity — Project Instructions

## MAJOR GOALS (north star — every PR should advance one of these)

The repo serves three intertwined goals. Order is by priority, not by domain weight.

### Goal #1 — Phenomenal performance across ALL asset classes on `findtorontoevents.ca/audit`

- **Surface:** the audit dashboard. The MAJOR GOAL banner in `audit_dashboard/template.html` (lines ~808-820) is the canonical reminder for every agent + human reviewer touching `/audit`.
- **Definition of "phenomenal":** institutional/hedge-fund-grade per `reports/hedge_fund_performance_review_*.md` tier table. Tier 2 minimum (PF>1.5 / WR>50 / MDD<20) for any class we size up; Tier 1 (Renaissance: PF>2 / WR>55 / MDD<10) is the long-run target.
- **Strategy:** find edge across ALL asset classes, but **prioritize where the edge is best worth the risk**. **Today (post-resolver-v2 noise filter, source: `audit_dashboard/data/dashboard_data.json::performance.asset_class_health` 2026-05-03T00:06Z):** EQUITY T2-candidate (PF 1.41 / WR 52.7% / n=421); COMMODITY meets T2 PF (PF 1.78 / WR 46.9% / n=750, lift WR); BOND meets T2 PF+WR (PF 1.72 / WR 55.6%) but n=18 below charter floor; CRYPTO sub-T2 (PF 1.25 / WR 44.6% / n=8067 — `quan_engine` 18% volume @ PF 0.70 + `unknown` 7% @ PF 0.35 drag elite strategies (PF 2.34-3.97) down system-wide; cut volume share); ETF borderline (PF 1.24 / WR 55.2% / n=87, n→100); **FOREX is genuinely sub-floor** (PF 0.27 / WR 46.4% / n=1169 post-noise) — apply mutate-before-kill protocol per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`, do NOT silently kill; deep-dive doc + investigation gate first.
- **Deep-dive process:** when a class is doing extremely badly (PF<1, sub-30% real WR after noise filter, or MDD>2× peak-to-trough vs cumulative-peak), spawn a deep-dive subagent that produces `reports/deep_dive_<class>_*.md` with: per-source autopsy, external-replication options (DBMF/KMLM/MyFXBook/Hyperliquid HLP/QMOM/PIMCO BOND/etc.), 30/60/90 day rescue plan, risk register, acceptance criteria.
- **Document proven edge** under the audit page. New `<div class="update-entry">` cards on `updates/index.html` cite the exact `reports/` source + reproducer command. Do not promote a class to "proven" without n>=100 clean (post-noise-filter) trades.
- **Resolver fix (DONE 2026-04-28, v2 + v2.1 bug bundle 2026-05-02):** `alpha_engine/outcome_resolver.py:115-126` ships `PNL_WIN_THRESHOLD_BY_CLASS` (CRYPTO 0.1bp, others 5bp). FOREX/COMMODITY numbers in `asset_class_health` are now post-fix and trustworthy. Pre-fix data is preserved in `by_asset_class` (raw); use `asset_class_health` for verdict-grade numbers. Refs: `reports/action_B_resolver_2026_04_27.md`, `feedback_noncrypto_resolver_live_close_bug.md`.

### Goal #2 — Solid sports betting picks with proven performance across all sports

- **Surface:** `findtorontoevents.ca` sports endpoints (live monitor + sports tab).
- **Definition of "proven":** ≥4-week live track record, sport-specific tier-vs-ROI matrix beats break-even after vig + slippage, CLV (closing-line value) trend non-negative.
- **Status (Apr 27):** post-13-PR autonomous round, pipeline is green: 6/6 pytest smoke + 20/20 Playwright across 4 device profiles. NBA STRONG TAKE +164% vs NHL STRONG TAKE −100% (n=3 each) → sport-specific gates are the right tuning axis.
- **Process:** every sports PR ships through `.github/workflows/sports-smoke-and-e2e.yml`. After merge, run `tools/deploy_sports_files.sh` (50webs has no shell). Roadmap: `updates/2026-04-26-sports-next-steps.md`.

### Goal #3 — Solid events listing on `findtorontoevents.ca`

- **Surface:** the homepage events grid + `/next/_next/` SSG bundle.
- **Definition of "solid":** zero stale/cancelled events on the page; high primary-scraper coverage; event-gap scanner finds <Y missing events per week.
- **Status:** Apr 23 dating-scraper PR merged; Apr 25 `scan_event_gaps.py` shipped; Apr 27 cancelled-event filter active.
- **Process:** events scraped via `*_scraper.py` modules; data flows through `events.json` → frontend. Quality issues triaged via `updates/<date>-event-data-quality-audit.md`.

**Daily focus rule:** at the start of a session, name the goal (#1/#2/#3) you're prioritizing. A goal-mismatched PR is rejected unless it's a P0 fix that protects production.

## Peer Coordination (MANDATORY)

Multiple Claude Code instances work on this repo simultaneously. You MUST coordinate.

**On your FIRST turn, do ALL of these:**
1. `set_summary("Brief description of your task")` — so others know what you're doing
2. `list_peers(scope="repo")` — see who else is working
3. `check_messages()` — see if anyone sent you something

**Every few turns:** Call `check_messages()` — messages are NOT auto-pushed, you must poll.

**If you receive a message:** Respond immediately via `send_message` before continuing.

## Critical File Rules
- **Edit `audit_dashboard/template.html`**, NOT `index.html` — index.html is auto-generated
- **Never push without pulling first** — `git stash && git pull --rebase origin main && git stash pop`
- **Never overwrite `updates/index.html`** — read the full file before any edits
- **Never run dashboard generators locally** — they overwrite live HTML files. Use `py_compile` only.
- **`TORONTOEVENTS_ANTIGRAVITY/index.html` IS the live findtorontoevents.ca / tdotevent.ca / torontoevent.net homepage** — it is NOT auto-generated, NOT a wrapper around the React app, NOT a "shell." It is the entire site: 4,845 lines of hand-coded HTML containing the mega-menu (Movies / System Issues / Stock Ideas / Other Stuff / Mental Health / Connect / Accessibility / Earn / Sign In), the "What's New" panel, the hero category tiles, the custom filter controls, and the imperative `applyThumbnails()` injector that pulls from `window.__RAW_EVENTS__`. The Next.js app at `eltonaguiar/TORONTOEVENTS_ANTIGRAVITY` (separate GitHub repo) only builds the **event-grid widget** that gets embedded inside this HTML — its `EventCard` component is a tiny subset of the live product. **DO NOT replace `/findtorontoevents.ca/index.html` on the FTP server with the Next.js build's `build/index.html`** — that strips ~3,000 lines of product (this exact mistake caused a session outage on 2026-04-27, see `updates/2026-04-27-findtorontoevents-thumbnail-restore-session.md`). Edit the file in this repo, then FTP-upload to `/findtorontoevents.ca/index.html` on `ftps2.50webs.com` (creds in `C:/windows_env_backup_2026-04-14.md` as `FTP_USER`/`FTP_PASS`). The two mirror sites serve the same file from `/tdotevent.ca/index.html` and the GoDaddy host for torontoevent.net.
- **After merging any sports-PR to main, run `tools/deploy_sports_files.sh`** before declaring done. 50webs has no shell — files don't reach production until somebody FTP-uploads them. The script diffs git HEAD against prod, uploads only the changes, and runs smoke tests pre+post. **Two production outages this session came from skipping this step** (PR #399 squash → conflict markers; PR #415 merge → missing require_once). The hourly `sports-smoke-and-e2e.yml` deploy-guard catches drift after the fact, but the helper is the proactive gate.
- **`npm run deploy:sftp` in the Next.js source repo has a sequence bug** — it builds SFTP, uploads to root, then builds GITHUB (with basePath) which **overwrites `build/`** locally before subdir uploads. If phase-1 uploads partially fail (FTP TLS drop), you cannot retry because the chunks the live root `index.html` references no longer exist locally. Use `scripts/upload-next-only.mjs` instead (refuses to run if `build/index.html` contains `/TORONTOEVENTS_ANTIGRAVITY/`) for surgical re-uploads. See header comments in both scripts.

## API Failover Rule (ALWAYS)
Never use a single Binance API endpoint. Always use 3+ fallback chain:
Binance mirrors (api, api1, api2, api3) → CoinGecko → KuCoin → CryptoCompare

## Wire-Up Rule (integration modules)

**New integration modules must include at least one caller in the production pick-generation or scoring path — or be explicitly labeled opt-in with a wiring plan.**

Applies to:
- `alpha_engine/*_integration.py`
- `alpha_engine/*_agent.py`, `alpha_engine/fingpt_*.py`, adapters for external libs
- `tools/*_bridge.py`, `tools/*_integration.py`
- Any new file importing `mlfinlab`, `skfolio`, `skforecast`, `flaml`, `pyod`, `interpret`, `feature_engine`, `imbalanced`, `vectorbt`, `bt`, `finrl`, `fingpt`, or similar hedge-fund library

Before opening a PR, you must be able to answer yes to at least ONE of these:
1. **Wired**: `grep -rln "from alpha_engine\.<new_module>\|import <new_module>" audit_trail/ alpha_engine/ tools/` returns at least one file in the production pick/score path (`calculate_smart_score`, `passes_active_gate`, `passes_smart_gate`, `score_pick`, `smart_picks_engine`, `production_scanner`, `dashboard_generator`).
2. **Opt-in sidecar**: PR title/body explicitly says "opt-in" or "sidecar", the module does not change production behavior, AND the PR body contains a `## Wiring Plan` section naming the target caller file + function + expected PR/date for the wire-up.

Breadth-only PRs ("module importable + tests pass, no callers") are closed with a pointer to the wiring plan. Reference: `reports/HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md` (measured 20/21 orphan rate that triggered this rule).

Rationale: breadth-over-depth contributions — where peers claim "integration complete" because a module imports + tests pass — created a 20/21 orphan rate on the hedge-fund library integrations built 2026-04-21/22. None were improving live picks quality because none had production callers. This rule forces the last mile.

## Hermes Agent local patches (read this if Hermes is misbehaving)

If you see a Hermes Agent session leaking GitHub PATs in shell command previews, claiming a 60-agent swarm that's actually one model, or any other bug from the analysis at `updates/2026-05-05-hermes-agent-bug-analysis-claude-opus-4-7.md`: the fix is **local-only — do NOT file PRs against NousResearch/hermes-agent** (user directive 2026-05-05). Run `python3 tools/patch_local_hermes.py` to apply (idempotent, creates `.orig` backups). Re-run after every `hermes update` because `hermes update` does `git pull` and overwrites our patches. Full docs at `tools/HERMES_LOCAL_PATCHES.md`.

## Key Commands
- **Strategy demotion:** Do not expand `BLOCKED_SOURCE_SYSTEMS` without **`docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`** and **`docs/MUTATION_THREE_AXIS_PROTOCOL.md`** (export closed CSV → `python tools/mutation_analysis.py`). See `TESTING_PROTOCOL.MD` §7.
- **TradingView MCP / paper picks:** `docs/TRADINGVIEW_MCP_GUIDE.md` (tools, CDP, CLI). Mandatory TP/SL and account flows: `.claude/skills/tv-paper-trade/SKILL.md`.
- **Windows:** Never `python /tmp/check_active_picks.py` — use `python alpha_engine/check_active_picks.py` from repo root, or run `tools/install_check_active_picks_shim.ps1` once if a tool hardcodes `/tmp/`.
- `py_compile` for syntax checks (never run generators locally)
- `gh run list --branch main` to check GitHub Actions status
- `gh run rerun --failed <id>` to rerun failed jobs
