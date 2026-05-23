# CLAUDE1.MD — Live work log (Claude Opus 4.7, 1M)

**Branch:** `feat/audit-dashboard-enhancements-hermes-2026-05-09`
**Session start:** 2026-05-10 (post-compact)
**Domain:** JS-error audit verification → ops + verification suite
**Peer split (assumed; confirm via CLAUDE2/3/4.MD when they exist):**
- **CLAUDE1 (me)** — ops + verification (drift-pause activation, post-quarantine verification suite, post-PR-#13 verify ladder)
- **CLAUDE2** — UI hydration (SettingsContext fix) + drift orphan ingest (workflow commit-back + dashboard_generator + template) — design files at `tasks/aea2026065e54c48d.output` + `tasks/a036630034048986a.output` handed over
- **CLAUDE3** — was working on something earlier; need handoff context (please drop CLAUDE3.MD if active)
- **CLAUDE4** (artiku348/loker.v2.1-cld-cdr-480b) — TradingView integration + PR #879 monitoring + already shipped manual quarantines: `kimi_signal_tracking` (PF 0.26, n=657), 12 `baby_strats crypto_soc_*` overfitting signs, `ml_crypto_pred_v12` (dead since 2026-02-22). Tier defs in `template.html` aligned to `docs/PERFORMANCE_CHARTER.md` v1.0. Output formatting fix in `run_audit.py`.

**Last update:** 2026-05-10T05:34Z

---

## SHIPPED THIS SESSION

| # | Where | Commit / PR | What |
|---|-------|------------|------|
| 1 | this repo | `07067ce1c60` | JS-error audit spec + isolated config + Hermes original audit + verdict report |
| 2 | this repo | `e6d2266051b` | Strip 5 dev `127.0.0.1:7838/ingest/` blocks from `TORONTOEVENTS_ANTIGRAVITY/index.html` (15 lines) |
| 3 | this repo | `d1cc90c9752` | CI guard wired into `sports-smoke-and-e2e.yml` step 9 + tightened third-party regex + 5-phase action plan |
| 4 | this repo | `0562bb9a306` | Fix `quant-auditor-deep-nightly.yml` OUT_FILE/DATE_ONLY mismatch (4 nightly crashes since 2026-05-06 → green) |
| 5 | this repo | `ebe9d09fadd` | Append /audit + /audit/hyrotrader workflow review (Appendix D) to action plan |
| 6 | source repo (TORONTOEVENTS_ANTIGRAVITY) | PR #13, commits `4e1555b` + `cf3d974` | EventFeed mount-gate fix + defensive setMounted in fallback effect |
| 7 | live FTP | n/a | Cleaned `index.html` uploaded to `ftps2.50webs.com:/findtorontoevents.ca/` + `/tdotevent.ca/` (226 OK ×2, 355,567 bytes); `curl` confirms 0 hits for `7838|agent log` (was 10) |
| 8 | CI verifications | runs `25620525777` + `25620650990` | sports-smoke green w/ Hermes-jserr step (continue-on-error); quant-auditor-deep green post-fix |

**Key docs:**
- `updates/2026-05-10-js-error-audit.md` — Hermes' original audit (preserved)
- `updates/2026-05-10-js-error-audit-claude-verification.md` — verdict (refutes Hermes' homepage PASS)
- `updates/2026-05-10-js-error-audit-action-plan.md` — 5-phase plan + Appendix A-E (reproducer, sub-agents, files changed, /audit GHA review, peer notes)

---

## DESIGN AGENTS — STATUS

| Agent | Focus | Status | Output file |
|-------|-------|--------|-------------|
| A | SettingsContext fix design | DONE — winner Option B (consumer-level gate ~30 LoC). FOUC not React #418. | `tasks/aea2026065e54c48d.output` |
| B | drift orphan ingest design | DONE — full diff for workflow + dashboard_generator + template + size cap + path-filter tighten | `tasks/a036630034048986a.output` |
| C | post-PR-#13 verify ladder | DONE — 5 rungs (V1-V5) + Outcome A/B branches + 7-day monitoring + rollback plan | `tasks/abe36225f24e32227.output` |
| D | drift-pause activation flow | DONE — winner Approach C (hybrid: JSON probation tier auto-managed; permanent BAN in Python human-only). 6-phase roadmap, 26h dev + 7d soak. Key gap: drift is per-asset-class but blocklist is per-source-system → recommend extending compute_dynamic_drift_score.js to per-source. | `tasks/a53c89219838c17e1.output` |
| E | post-quarantine verification suite (5 layers) | DONE — 5 layers (UNIT/GENERATION/STORAGE/EXECUTION/DASHBOARD) + orchestrator `tools/verify_quarantine.py` + 8 instrumentation gaps + 7-day rollout | `tasks/a40184ecb43a6dd80.output` |

**Handoff:** A + B handed to CLAUDE2 (covering UI hydration + drift ingest). I keep C/D/E.

---

## ACTIVE TODOs (mine)

### Immediate (this session, before peer handoff)
- [x] Wire CI guard into sports-smoke-and-e2e.yml — DONE
- [x] Verify CI green via workflow_dispatch — DONE (25620525777)
- [x] Fix quant-auditor-deep-nightly bug — DONE (0562bb9a306)
- [x] Update action plan with Appendix D — DONE
- [x] Notify all 4 peers of work split — DONE
- [x] Agent D (drift-pause activation) DONE
- [x] Agent E (post-quarantine verification) DONE
- [x] Ship E-Day-1: Layer 1 unit test + GAP #1 (`blocklist_history.jsonl`) — DONE commit `7333b41e278`. 92/92 tests pass in 0.43s. Schema doc defines event enum + Wire-Up Rule callers.
- [ ] Take over CLAUDE4's residual: TV chart-widget access bug, PR #879 monitoring, audit functionality expansion.
- [x] **CLAUDE3 takeover DONE** commit `cc478c5f140`: 9 Riskfolio files KILLED (dep no-install Py 3.14 + misdiagnoses FOREX edge decay + duplicates pypfopt fallback already in scripts/portfolio_optimizer.py); 5 vectorbt + 4 pandas-ta files quarantined in `experiments/hedgelib_2026_05_10/` with Wiring Plans; 4 chat artifacts deleted; disposition doc + lib survey kept. Agent F (ship-order) + Agent G (4-tier test plan) both DONE; will gate any future wire-in.
- [x] **graphify code-map + skill:** installed `graphifyy 0.x` via `uv tool`; ran `graphify extract audit_trail --backend ollama --model qwen3-coder:480b-cloud --no-cluster` → 1420 nodes, 2654 edges, 35k-line `graph.json`. AST-only (semantic LLM phase needs `pip install openai` for ollama-compat backend — note in skill, future enhancement). `query/path/explain` commands verified working — returns file:line refs + edge types (calls, contains, rationale_for). Skill at `.claude/skills/graphify-intel/SKILL.md` documents commands + when-to-use + refresh policy + Wire-Up Rule note. `.gitignore` excludes `graphify-out/`.

### Pending external (gated on humans / other systems)
- [ ] Human merge PR #13 → Next.js rebuild → SFTP `_next/static/chunks/` redeploy
- [ ] After redeploy: re-run Playwright spec → confirm React #418 cleared OR fall through to Outcome B (formatLastUpdated / SettingsContext flicker investigation)
- [ ] Flip CI step `continue-on-error: true` → blocking once 24h soak green
- [ ] FTP mirror to GoDaddy host (`torontoevent.net`) — separate `FTPGODADDY*` creds
- [ ] CLAUDE2 ships SettingsContext consumer-gate (Option B from Agent A)
- [ ] CLAUDE2 ships drift orphan ingest (Agent B diff)

### E-7-day rollout (Agent E)
- [x] **E-D1:** Layer 1 unit test + `blocklist_history.jsonl` schema — DONE `7333b41e278` (92/92 pass, 0.43s)
- [x] **E-D2:** structured `blocklist_skip` logging + dry_run gap doc — DONE `26a34ef2f88`. quality_gates.py + strategy_blocklist.py both emit 7-key schema record on block. 2 tests added pinning the contract (94/94 pass). `audit_trail/GENERATOR_DRY_RUN_GAP.md` documents the E-D3 prereq (generators need `dry_run` kwarg before Layer 2 generation tests can run).
- [x] **Research orchestrator FULL PIPELINE SHIPPED** — 5-pass × 7 classes + weekly cron:
  - PR 1 (`8d1b3344e12`): skeleton + BOND pilot with textbook seeds + STUB backtest
  - PR 2a (`7241f1135bd`): live P1 swarm + verify_citations (hallucination guard)
  - PR 2b (`e6c148a181b`): live P2 swarm + p2_loader
  - PR 2c (`e23824a53e0`): REAL backtest math (yfinance + SMA proxy)
  - PR 3 (`3b04fdd4eb2`): mass-fire 5 remaining classes + FOREX
  - PR 4 (`a5ac7e16eed`): P5 SYNTHESIS swarm wired (6 of 7 NO_EDGE, 1 MIXED — honest)
  - PR 5 (`a060a87b3c8`): v3a keyword-routed signal dispatch (6 handlers: sma_cross/rsi_mr/momentum/mean_reversion_zscore/breakout/buy_and_hold)
  - PR 6 (`39971015b63`): weekly cron `.github/workflows/research-orchestrator.yml` Saturday 06:00 UTC, manual workflow_dispatch for per-class refresh
  - Total session cost: ~$1 across 21 swarm passes (7×P1 + 7×P2 + 7×P5).
  - Live: 26 runs across 7 classes at `/audit/research_index.html`.
  - Pending (v3b): LLM-driven spec-faithful signal translator. Current v3a keyword routing covers ~15% of specs; rest default to SMA. v3b unlocks per-spec signal accuracy → likely flips several NO_EDGE → MIXED/GO once n grows past 30.
  - Pending (CPCV): close `project_cpcv_gap_2026_04_28.md` by swapping walk-forward for CPCV in `p3_backtest_runner`.
- [ ] **E-D2:** generator skip-logging + dry_run entries — unblocks L2
- [ ] **E-D3:** Layer 2 generation test + `quarantine-verify.yml` workflow (hourly)
- [ ] **E-D4:** MySQL env stub + Layer 3 storage script
- [ ] **E-D5:** check_active_picks --json + tv_place_pick comment tag
- [ ] **E-D6:** Layer 4 execution + orchestrator `tools/verify_quarantine.py`
- [ ] **E-D7:** dashboard data-testid + Layer 5 Playwright + exec-time gate enforcement (highest-leverage gap)

### D-roadmap (Agent D, runs parallel to E)
- [ ] **D-Phase-1 (8h):** ship `config/strategy_probation.json` + `quality_gates.py::_load_probation()` + `is_on_probation()` (mtime-cached) + wire into `is_blocked_pick()` returning sizer multiplier. Hot-reload + sizer math unit tests. Behind `feature_flags.json::auto_probation_enabled=false` initially.
- [ ] **D-Phase-2 (6h):** ship `tools/drift/reconcile_probation.py` (single writer): tier ladder + 8h hysteresis + 25% blast-circuit-breaker + data-freshness pre-check.
- [ ] **D-Phase-3 (5h):** `tools/drift/generate_kill_investigation.ps1` + `tools/drift/run_mutation_for_probation.py` — auto-investigation docs per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + mutation analysis per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`. CLAUDE4-style manual quarantines (`kimi_signal_tracking`, baby_strats, ml_crypto_pred_v12) become test fixtures for the auto path.
- [ ] **D-Phase-4 (3h):** wire into `audit-drift-telemetry.yml` between `Trigger probation actions` step and artifact upload + commit-back gated on `[skip ci]` + `git pull --rebase` retry loop.
- [ ] **D-Phase-5 (4h):** probation history tile on /audit (coordinate with CLAUDE2 — they own the React side, I ship the JSON contract).
- [ ] **D-Phase-6 (rolling 7d):** soak monitoring + tune blast threshold + freshness window.
- [ ] **D KEY GAP:** extend `tools/drift/compute_dynamic_drift_score.js` to compute per-source rows (currently per-asset-class; blocklist enforces per-source). Without this, auto-pause is blunt (all-CRYPTO blast) instead of surgical.
- [ ] **E (Post-quarantine verification):** design completing — likely 5 layers (unit / generation / storage / execution / dashboard) + orchestrator `tools/verify_quarantine.py --strategy <name> --since <ts>`.
- [ ] **CLAUDE4 takeover:** TV chart-widget access bug (re-establish CDP), PR #879 monitor (5-phase Hermes work), audit functionality expansion candidates.

---

## CRITICAL FINDINGS (read before duplicating work)

1. **EventFeed is already `dynamic({ssr:false})`** at `src/app/page.tsx:15-22` of source repo. PR #13 mount-gate fix is defense-in-depth. Real React #418 source is elsewhere — likely `formatLastUpdated` (uses `suppressHydrationWarning` to paper over `Intl.DateTimeFormat` Node-vs-browser drift) OR `SettingsContext` post-hydration class flicker (technically FOUC, not #418, but worth verifying).

2. **SettingsContext is FOUC, not React #418** per strict React 18 hydration timing. Server + first CSR render both use `defaultSettings`; mismatch only appears AFTER hydration commits via the localStorage `useEffect` → re-render. Visual flicker, not thrown error. Agent A recommends consumer-level gate (Option B) over Provider mount-gate (Option A — kills SSR for SEO) over cookie+middleware (Option C — too much complexity for the gain).

3. **127.0.0.1:7838/ingest/ dev script** is now stripped from prod live homepage (P2 done). 5 `// #region agent log` blocks removed. `curl` confirms 0 hits.

4. **Hermes' "no real errors" verdict** was wrong on `/index.html` (missed React #418 + dev-script) but right on `/audit/` + `/audit/hyrotrader/`. Puppeteer-CDP "console only" check doesn't catch React-rethrown `pageerror` events. Add to feedback memory: don't trust Hermes browser-tool verdicts on SSR React pages without independent Playwright capture.

5. **`/audit` + `/audit/hyrotrader/` GHA pipeline state:** mostly healthy. 5 hourly/daily workflows 5/5 green. `hyro-bridge-regen.yml` recovered manually 2026-05-09T22:34. `quant-auditor-deep-nightly.yml` was broken 4 nights — fixed by my `0562bb9a306`. `drift_scores_latest.json` is orphan (Agent B / CLAUDE2 fixing).

6. **Ghost-path warning** (memory `feedback_use_claude_peers_not_redis_bus.md` + Hermes session pattern): `/mnt/c/...` writes from WSL get lost. Canonical path is `/mnt/e/findtorontoevents_antigravity.ca/` (this dir).

---

## PEER COORDINATION

| Peer | Domain | Last contact |
|------|--------|--------------|
| `dmqq9su6` | (no summary set) — assumed CLAUDE2, covering UI hydration + drift ingest | 2026-05-10T05:32Z (sent agent A+B handoff) |
| `u3zbeuav` | Hermes handoff cycle, PR #879, monitor running | 2026-05-10T05:32Z (status update sent) |
| `7f3eotwj` | DAILY_IDEAS.MD analysis + VectorBT POC | 2026-05-10T05:32Z (Wire-Up Rule reminder + offered to fold VectorBT into Agent D design) |
| `b4oubwxd` | (no summary set) | 2026-05-10T05:32Z (dedupe ping sent) |

---

## REFERENCES

- Spec: `tests/playwright/test_hermes_jserror_audit_2026-05-10.spec.ts`
- Config: `playwright.hermes_jserr.config.ts`
- Workflow gate: `.github/workflows/sports-smoke-and-e2e.yml` line 114 (flip continue-on-error after 24h green)
- FTP backup pre-strip: `/tmp/ftp_backup_2026-05-10/index.html.50webs.bak` (6165 lines, 10 7838-hits — for rollback)
- FTP env vars: `$FTP_USER`, `$FTP_PASS`, `$FTP_SERVER` (already loaded; GoDaddy mirror uses `$FTPGODADDY*`)
- Source repo clone: `e:\TORONTOEVENTS_ANTIGRAVITY_src` (branch `fix/eventfeed-hydration-now-2026-05-10`, PR #13)

---

## NEXT UPDATE TRIGGER

This file gets refreshed when:
- Agent E completes (D done)
- Peer message arrives that changes work split
- New commit/PR ships
- A SHIPPED item moves to verified-live
- I take over a CLAUDE4 task

## CLAUDE4 RESIDUAL — TAKEOVER QUEUE

Per user 2026-05-10T05:34Z: claude #4 ended, take on or supplement their work. Their session shipped:
- Tier defs in `audit_dashboard/template.html` aligned to `docs/PERFORMANCE_CHARTER.md` v1.0
- Manual P0 quarantines in `quality_gates.py`: `kimi_signal_tracking` (PF 0.26, n=657, -955 PnL%), 12 `baby_strats crypto_soc_*`, `ml_crypto_pred_v12` (dead since 2026-02-22)
- Output formatting in `tools/run_audit.py`
- Comment on PR #879
- Edge by asset class report update

Open from CLAUDE4 (I will pick up):
1. **TV chart-widget CDP access bug** — they got connection but couldn't read charts. Re-investigate after current ops/verify ladder lands.
2. **PR #879 monitor** — 5-phase Hermes work; track merge-readiness; flag if rotting.
3. **Audit functionality expansion** — vague "expand audit to cover more aspects" — defer unless concrete asks surface.

Their manual quarantines BECOME test fixtures for my D-Phase-3 auto-investigation flow — those 14 strategies are the ground truth that `reconcile_probation.py` should reach autonomously when Agent D ships.
