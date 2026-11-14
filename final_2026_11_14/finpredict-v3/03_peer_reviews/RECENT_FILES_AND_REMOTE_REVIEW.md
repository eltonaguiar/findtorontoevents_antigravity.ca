# Recent Files & Remote Review — finpredict-v3 (2026-11-14)

A review of the recently modified files on disk and the remote GitHub
(`https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/`), attributing
each finding to its source. Focus is the prediction/trading system, not BESTIEJOB.

## Remote state
- `origin/main` advances on the automated hourly cycle (Data/coinglass/gainer/scan
  `[skip ci]` commits); the meaningful work lands via the peer branches listed below.
- Key remote branches to merge/review: `fix/audit-js-syntax-and-deploy-guard`
  (JS parse-dead fix), `finpredict-v2`, `fix/p0-safe-fixes-2026-11-14` (v4),
  `audit/live-audit-2026-11-14`, `audit-stale-data-and-accuracy-across-asset-classes`,
  `docs/scratch-hippodraco-audit-2026-11-14`, `kilo/audit-findings-2026-11-14`.

## Meaningful recent local changes (last ~8h)

| Area | Files | Who | Verdict |
|---|---|---|---|
| Master plan | `2026-11-14/finpredict/…T160004Z/master-plan/` | v1 | Strong planning foundation; needs fix of registry-ID duplication + close 4 decision conflicts |
| Actions deep dive | `2026-11-14/finpredict-v2_…/actions_deepdive/` (GA1–GA4 + raw) | v2 | Root causes: audit-dashboard runtime p50 97min vs 60min cron → 0-job cancels; 56/365 stale workflows; `summary_picks` WR>100% |
| Profitability research | `research/profitability/` (run_v1–v4, PROTOCOL_v1–v4, SCORECARD, validation/) | v2 | Pre-registered 12-candidate study; **NOT PROVED**; independent VWAP falsification; ITERATION-005 claimed edge (diversified vol-targeted trend) under validation |
| ML validation | `2026-11-14/finpredict-v3/…T174500Z/ML_VALIDATION/` | v3 (me) | leakage/look-ahead/stale models; horizon harness 0/6, 0/26 |
| Live browser validation | `.kilo/worktrees/finpredict-v3/…T175500Z/LIVE_BROWSER_VALIDATION.md` | v3 (me) | frontend React #418, audit CORS feed blocks |
| Scoring framework | `alpha_engine/statistical_scoring_framework.py`, `research/PROFITABLE_SCORING_FRAMEWORK.md` | v4 | untracked; proposed |
| Quick wins | `.kilo/worktrees/flaxen-hair/quick_wins/` (01–08 + shared normalize_pnl_units.py) | flaxen-hair | PnL-unit mix bug corroboration; 93 rows: 47 ratio/32 percent/14 off |
| Quick wins | `.kilo/worktrees/scratch-hippodraco/` | scratch | QW-ALL-1..9 implementation-ready checklist |

## Cross-peer consensus on defects (verified independently)
1. **PnL-unit mix bug** — `audit_trail/dashboard_generator.py:8065-8072` (heuristic
   `if abs(pnl_val)<0.10: pnl_val*=100`). Corroborated by flaxen-hair, scratch, ML, seer.
2. **Stale/frozen prices** — crypto `current_price==entry_price`; 11 frozen FOREX phantoms.
3. **Zombie/garbage rows** — expiry/survivorship; crypto 86.7% EXPIRED zombies.
4. **Multiple-testing inflation** — N≈658 ⇒ ~32.9 false positives at p=5%.
5. **Backtest↔forward disconnect** — 0 rows have both bt_trades>0 and fwd_trades>0.
6. **0/9 money-ready** — no class/ML model proven.

## Veto list (agreed)
- v4 & ML-audit destructive SQL (DELETE/UPDATE/INSERT OR REPLACE) — hold behind dry-run/archive.
- Mutual-fund stub scanner (ML) — adopt classification-only.
- hilarious-seer "purge old picks >30d" — quarantine-in-view instead.

## For the coordinator (carry-forward)
1. Sign off `d8c8dd25581` (gatekeeper leakage-masking default ON, already on origin/main).
2. Confirm `fix/audit-js-syntax-and-deploy-guard` merges (JS parse-dead since 2026-10-04).
3. Hold v4/ML destructive SQL.
4. Fix audit-dashboard cron + FTP step (v2 GA4).
5. Close the 4 master-plan decision conflicts before P1.
