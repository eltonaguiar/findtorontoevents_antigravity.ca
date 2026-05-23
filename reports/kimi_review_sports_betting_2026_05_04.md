# Kimi Sports-Betting Report Review — Cross-check vs Live State

**Source report:** `reports/kimi_swarm_archive_2026_05_04/findtorontoevents_swarm/sports_betting_analysis.md` (dated 2026-04-25)
**Reviewer date:** 2026-05-04
**Branch under review:** `fix/sports-stale-data-hardening-2026-05-04` (commit `40f98fe0331`)

---

## 1. Per-finding verdict

| # | Kimi Finding | Verdict | Evidence |
|---|---|---|---|
| 1 | TheOddsAPI key unauthorized → 0/500 credits, picks >48h stale | **AGREE (root cause real, fix is operational not code)** | `live-monitor/api/db_config.php:74` reads `$THE_ODDS_API_KEY = getenv('THE_ODDS_API_KEY')`; injected by `.github/workflows/torontoevent-deploy-live-monitor.yml:31,126` from GitHub secret `THE_ODDS_API_KEY`. `sports-betting-refresh.yml:656` already emits an `::error::` line with explicit rotation instructions when the upstream returns 401. PR #759 (per `NOTES_FOR_OTHER_CLAUDE.MD:38`) already FTP-patched the live key. The "code" is wired correctly — staleness is a **secret-rotation operational issue**, not a code defect. No PR will fix it; only owner action at the-odds-api.com + updating the GitHub secret. |
| 2 | "Last refresh" shows date-only, no HH:MM | **DISAGREE (already fixed)** | `live-monitor/sports-betting.html:2104-2105` calls `fmtTime(d.last_updated)` when the timestamp is >10 chars. `fmtTime` at line 1494 emits `Apr 25 14:32 ET` (month/day + hour:min + tz). Falls back to date-only only when the API returns a date-only string — which is itself the real bug (upstream payload), not a frontend formatting bug. |
| 3 | Win-rate warning persists at 37.5% n=24 (warning fatigue) | **AGREE (still unconditional)** | `live-monitor/sports-betting.html:457` renders `&#9888; Win Rate Currently Low or Unknown` as static markup; no JS gate on `directional_n` or cohort. Should be conditional (`n<15` OR Wilson CI upper < 0.5 OR cohort=all+policy-cleaner). Not addressed by the in-flight branch. |
| 4 | Two-ledger discrepancy (Pick History 126 / Bankroll 41) — no in-app reconciliation | **ALREADY-IN-FLIGHT (partial)** | Reconciliation **banner** exists at `sports-betting.html:480-481` with `reconciliation_ok===false` toggle (line 1634-1635), but it's a flag, not a side-by-side reconciliation tab. Kimi's full recommendation (unified view) is not built. |
| 5 | Arbitrage / Steam Moves show 0 with no fallback | **AGREE** | No "Last arbitrage found: Xh ago" affordance found in `sports-betting.html`. `sports_arb_scanner.php` and `sports_steam_detector.php` exist but UI shows blank zeros. |

---

## 2. TheOddsAPI claim verification (grep evidence)

- **Key wiring exists & is correct:**
  - `live-monitor/api/db_config.php:74` — `$THE_ODDS_API_KEY = getenv('THE_ODDS_API_KEY')`
  - `live-monitor/api/sports_picks.php:1384`, `sports_odds.php:254`, `sports_bets.php:908` — all consume `$THE_ODDS_API_KEY` and short-circuit with `missing THE_ODDS_API_KEY` if empty.
  - `.github/workflows/torontoevent-deploy-live-monitor.yml:31,39,67,126,136,152` — secret injected into both 50webs + GoDaddy `db_config.php` on deploy.
  - `.github/workflows/sports-betting-refresh.yml:656` — explicit owner-facing 401 rotation message.
- **Kimi's claimed secret name is wrong:** Kimi says `ODDS_API_KEY`; actual env var is `THE_ODDS_API_KEY` (with `THE_` prefix). Minor but matters for any rotation runbook.
- **Conclusion:** root cause is genuine (expired/unauthorized key). The fix is **non-code**: rotate at the-odds-api.com → update GitHub secret `THE_ODDS_API_KEY` → re-run `torontoevent-deploy-live-monitor.yml`.

---

## 3. Does `fix/sports-stale-data-hardening-2026-05-04` address root cause or symptoms?

**Symptoms only.** Diff (`git diff main...fix/sports-stale-data-hardening-2026-05-04`, 3 files / +20/-2):

- `live-monitor/api/db_connect.php:+http_response_code(503)` on DB connect failure
- `live-monitor/api/sports_db.php:+http_response_code(503)` in `sports_db_json_error`
- `live-monitor/sports-betting.html:2110` — banner threshold tightened **48h → 24h**
- `live-monitor/sports-betting.html:2152-2167` — per-card age chip (green <6h / amber 6-24h / red >24h)

This makes staleness **visible faster and per-card** but does not refresh data. Until the operator rotates the key, every pick card will simply render the red "X days old" chip. That is the correct UX trade-off (truthful degradation), but Kimi's #1 (key rotation) is fundamentally an ops/runbook task, not in-scope for this PR.

---

## 4. Top 3 follow-up PRs after stale-hardening lands

1. **Conditional win-rate warning** — gate `&#9888; Win Rate Currently Low or Unknown` (line 457) on `directional_n < 15 || wilson_upper < 0.5 || (cohort==='all' && policy_fix_cohort_cleaner)`. Add Wilson CI subtitle next to `.metric-win-rate`. Est: 1-2h. Addresses Kimi #3.
2. **Cached-odds graceful degradation** — when `sports_odds.php` / `sports_picks.php` returns `missing THE_ODDS_API_KEY` or upstream 401, fall back to last-known rows from `lm_sports_odds_history` and tag each with the per-card age chip already added in this branch. Currently the line-shopping/arb tabs collapse to empty. Est: 3-4h. Addresses Kimi #5 + #6.
3. **Reconciliation sub-tab under My Bets** — extend the existing `reconciliation-banner` flag (line 480) into a real side-by-side `lm_sports_bets` vs `lm_sports_daily_picks` view with row-level diff highlighting. Est: 4h. Addresses Kimi #4.

(Honourable mention: extend `sports-betting-refresh.yml:656` to open a GitHub issue automatically on 401 instead of only emitting `::error::` — closes the ops loop on the #1 root cause.)

---

## 5. Responsible-gambling / AGCO compliance

**MISSING — flag for separate PR.** Grep (`responsible|gambl|AGCO|19\+|connex.ontario`, case-insensitive) on `live-monitor/sports-betting.html` returns only:

- Line 428: *"Paper betting simulation only. Not gambling advice. Past performance does not predict future results."*
- Line 1002: A glossary mention of "Why Are Gambling Markets Organised So Differently".

There is **no AGCO-mandated 19+ age gate, no ConnexOntario 1-866-531-2600 helpline reference, no responsible-gambling disclosure block, no self-exclusion / time-out / deposit-limit messaging.** AGCO's "Standards for Internet Gaming" (Standards 2.05, 4.05, 4.07) require operator-facing sites that present odds/picks to display problem-gambling resources and 19+ messaging prominently — even on a paper-betting simulation, the optics for an Ontario-domiciled product are poor without this. **Recommended P1 follow-up:** add a footer compliance block: 19+ badge, ConnexOntario number/link (`https://www.connexontario.ca/`), "Play responsibly" with self-assessment link, and a short disclaimer that this is a simulation and not an AGCO-licensed operator. Est: 1h.

---

## 6. Items needing more info

- Kimi cites `Pick History 126 picks @ 29.8% WR` vs `Bankroll 41 tickets @ 37.5% WR` — could not verify counts without live DB access. Reconciliation logic in PHP layer (`sports_metrics_lib.php`) was not deep-read; a short audit there would confirm whether the gap is a definitional cohort split (graded picks vs paper-bet tickets) or a true sync bug.
- Kimi's `DQ-001..DQ-010` proposal is sound but should be folded into existing `sports-forensics-weekly.yml` rather than a new endpoint — out of scope for the immediate PR queue.
