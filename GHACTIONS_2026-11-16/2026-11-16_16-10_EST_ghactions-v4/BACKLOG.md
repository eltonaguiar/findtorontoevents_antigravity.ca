# PRIORITIZED BACKLOG — ghactions-v4 handoff

**Date:** 2026-11-16_16-10_EST (20:10 UTC)
**Author:** ghactions-v4 / `meituan-longcat-2-5`
**Detail write-up:** `GHACTIONS_2026-11-16/2026-11-16_15-54_EST_ghactions-v4/FINAL_SUMMARY.md`
**Deployed:** `github.com/eltonaguiar/findtorontoevents_antigravity.ca` → `origin/main`

Priority key: **P0** = blocks correctness/money or needs the human · **P1** = CI reliability · **P2** = data integrity/dashboard · **P3** = hygiene.

---

## P0 — Owner-gated / external (agents cannot finish these)

### 1. QA Market Validation — 5 missing API secrets
- **What:** `qa-market-validation.yml` fails hourly because adapters 2–6 have no keys; only Stooq (blocked from runner IPs) + yfinance (flaky) remain → "ALL 7 sources failed" for equities.
- **Do this:** GitHub → Settings → Secrets and variables → Actions → New repository secret:
  `FINNHUB_API_KEY`, `TIINGO_API_KEY`, `TWELVE_DATA_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `FMP_API_KEY`.
- **Why agents can't:** values live in `~/dbpasses.txt`, which agents must never read or expose. Either the owner sets them, or an operator runs `gh secret set <NAME> --body "$(grep ... ~/dbpasses.txt)"` themselves.
- **Bundled in:** PR #786. **Verify:** `gh workflow run qa-market-validation.yml` then confirm adapters 2–6 return data.
- **Detail:** `updates/2026-11-16-gha-qa-market-validation-secrets.md`

### 2. 51 phantom queued runs
- **What:** 51 runs stuck `queued` forever with 0 jobs (batches 2026-08-07 → 2026-11-11). They pollute the queue view and concurrency accounting.
- **Why agents can't:** all four removal paths fail — REST cancel `409 Cannot cancel a workflow run that has not been queued yet`; REST delete `403`; UI "Cancel workflow" → "Failed to cancel workflow."; UI delete not offered for queued runs.
- **Do this:** open a GitHub Support ticket, or supply a **classic PAT** with Actions administration/delete scope and run the removal loop.
- **Detail:** `updates/2026-11-16-gha-phantom-queued-runs.md`

### 3. Decide on peer commit `d5259137541` (ghactions)
- **What:** "fix(forex): read `FOREX_HARD_DISABLE` live; add VIX rule combos; un-lie the freshness tiles".
- **State:** CONFLICTS with current main on `audit_dashboard/dashboard_freshness.js:111` and `audit_dashboard/template.html:908` (both advanced by PR #843 and others).
- **Do this:** rebase onto `origin/main` and re-verify; the sibling commits `99a44602602` + `c8a5792f5a6` from the same worktree are **already landed** (see `9d1f147d31a`, `ed10e4c5e61`).

---

## P1 — CI reliability

### 4. Reusable-workflow mass conversion — GATED
- **Done:** `.github/workflows/gha-scan-job.yml` + canary conversions of `consensus-outcome-tracker.yml` and `adaptive-trust-tuner.yml` (`7a14df40eccf`).
- **Gate:** need **3–5 clean runs of BOTH canaries**. So far `consensus-outcome-tracker` #6413 @ 20:12:54Z = SUCCESS; `adaptive-trust-tuner` next fires 00:16Z.
- **Then:** convert the 39 simple candidates, then the full 181, in cadence order (hourly → `*/2h` → `*/4h` → daily → weekly), one branch per cadence.
- **Rollback:** `git revert 7a14df40eccf`.
- **Detail:** `reports/gha_rollout_approach.md` §2, `reports/gha_rollout_progress_2026-11-16.md`

### 5. Post-rollout regression watch
- The ~173-workflow concurrency/timeout rollout is live. Watch `reports/actions_failure_guardian.json` and `reports/gha_queue_audit.json` for new failure/queue patterns over the next 24–48h.
- **Done so far:** 0 failures in the latest 25 runs at every checkpoint.

---

## P2 — Data integrity / dashboard

### 6. BOND asset class (n=1) after the `SKIP_FRED` fix
- `etf-bond-scanner.yml` now defaults `SKIP_FRED` to `0` (`793b0fd5d81d`), so FRED yield-curve data is fetched again. Confirm BOND pick emission resumes and the class accumulates forward picks.
- **Detail:** `updates/2026-11-16-gha-stale-data-sources.md`

### 7. Money Ready 0/9 — emitter supply, not CI
- No asset class passes Tier-2 (n≥100, WR≥50%, PF≥1.5, DSR>0.95, PBO<0.05). CRYPTO 35.9%/PF0.92, FOREX 32.2%/PF0.66, EQUITY 59.2%/PF0.94 (PF<1), COMMODITY 40.2%/PF1.03, others INSUFF-N.
- **Do this:** per-class emitter mutate/kill decisions; the dashboard already flags 6 strategies with >20% WR drop → REDUCE.
- **Detail:** `updates/2026-11-16-gha-money-ready-zero.md`, `updates/2026-11-16-gha-strategy-kill-tribunal.md`

### 8. `hypothesis_registry.json` is not wired into the dashboard
- 23 entries exist in `reports/hypothesis_registry.json` (+2 in `audit_trail/data/`) but nothing in `audit_trail/dashboard_generator.py` or the dashboard JS consumes it. This is the "theory/hypothesis tracker" gap.
- **Do this:** design the wire-in (a tile or a data source) — offered to the swarm.

### 9. Confirm `strategy_ic_analysis.json` regenerates nightly
- Restored builder + workflow step (`7fc03f130810`). Confirm `pick-funnel-nightly.yml` produces a fresh file and the `/audit` IC card renders.

---

## P3 — Hygiene

### 10. Land the remaining peer wrap-up docs (both apply clean)
- `ghactions-v2` `e8c2db6c971` — "remaining-work prioritized list post-wrap".
- `ghactions-v3` `9fa7f9f0dc6` — "prioritized backlog post-v3 wrapup".
- **Note:** peers have already landed their substantive work — ghactions-v3 hardening (`b46ad800f64`, `45cddbf105e`) and ghactions-v2 feed-health (`a5ed3f57562`, PR #850) are on main.

### 11. `_dynamic-runner-template.yml`
- The only workflow still missing a concurrency group — it has **no triggers** (documentation stub). Decide: keep as documentation, or delete. Do not "fix" it by adding a group.

---

## Quick prompts for the next agent

1. `git fetch origin && git log --oneline -20 origin/main` — check before any edit.
2. Workflow hygiene is **done** — verify with `python3 tools/gha_phase1_inventory.py` rather than re-adding.
3. Never read or expose `~/dbpasses.txt`.
4. Do **not** auto-run `check_active_picks.py` or `alpha_engine/smart_picks_engine.py`.
5. COMS has no read/check verb — `COMS listen --agent <seat>` is the only subscriber; consider adding `COMS check --inbox` to `AGENT_REGISTER_PROMPT.md`.
