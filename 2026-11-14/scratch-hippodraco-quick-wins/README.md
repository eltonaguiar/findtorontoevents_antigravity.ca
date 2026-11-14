# Quick Wins — Proposed Fixes per Asset Class + Overall
**Date:** 2026-11-14 · **Worktree:** scratch-hippodraco · **Source audit:** `../../scratch-hippodraco.MD` (this worktree root)
**Status:** PROPOSALS ONLY — no code changed, nothing run against production DBs except read-only checks already in the audit. Subagent drafts for overall/crypto/forex/equity/ETF were returned and folded in with verified file:line (see "Subagent-refined" sections); bond/futures/commodity/mutual-funds files are from the audit + flaxen-hair's peer set read directly. `scratch-hippodraco.MD` and this folder are untracked in this worktree — not committed/pushed.
**Scope asked:** stocks, bonds, ETFs, mutual funds, forex, crypto (+ commodity/futures, which the system actually trades).

## Verdict recap (why these quick wins)
Headline PnL is not trustworthy: mixed `pnl_pct` units (percent vs 0.01× fraction, 6,306 rows), resolver stalled ~7.5h while dashboard said fresh, 90,588 zombie OPEN picks, walkforward frozen 2026-04-15, no class money-ready on intrabar truth (CRYPTO PF 0.92, EQUITY 0.94, FOREX 0.66, ETF 0.02, BOND 0.39), mutual funds phantom. Full evidence: `../../scratch-hippodraco.MD`.

## Folder structure
```
scratch-hippodraco-quick-wins/
├── README.md                  ← this index + top-10 + rollout
├── overall/OVERALL.md         ← platform quick wins QW-ALL-1..9 (freshness badge, PnL contract, zombie drain, CI contracts…)
├── crypto/CRYPTO.md           ← QW-CRYPTO-* (incl. coinglass addendum from peer review)
├── forex/FOREX.md             ← QW-FOREX-*
├── equity-stocks/EQUITY.md    ← QW-EQUITY-*
├── etf/ETF.md                 ← QW-ETF-*
├── bond/BOND.md               ← QW-BOND-* (bond-ETF proxies, vacuous gate, ZN=F contradiction)
├── futures/FUTURES.md         ← QW-FUTURES-*
├── commodity/COMMODITY.md     ← QW-COMMODITY-* (only intrabar PF>1 — protect it, kill 999,999% rows)
├── mutual-funds/MUTUAL_FUNDS.md ← retire-vs-build decision (recommend retire surface, keep tables quarantined)
└── peer-review/PEER_REVIEW.md ← review of childlike-airport / flaxen-hair / hilarious-seer work + main-repo recent files
```

## Top 10 quick wins (impact ÷ effort)
| # | Win | Where | Effort |
|---|---|---|---|
| 1 | Surface freshness YELLOW/RED in dashboard payload + badge (kill stale-green) | overall QW-ALL-1 | S (3h) |
| 2 | PnL unit contract: percent-only + `pnl_source`, delete generator ×100 guess | overall QW-ALL-2 | M (12h incl. guarded backfill) |
| 3 | One clamp at write; reject 999,999% rows; flag hardcoded XAU/XAG prices | overall QW-ALL-3 | M (8h) |
| 4 | Zombie OPEN drain: tombstone-expire (pnl NULL, never 0) + accrual>resolution alert | overall QW-ALL-4 / crypto | M (10h) |
| 5 | Reconcile active counts 20/158/4,148; quarantine `active_raw` | overall QW-ALL-5 | M (8h) |
| 6 | Artifact max-age stamps (walkforward 212d, ML 173d) + suppress regime WR at 0.1% coverage | overall QW-ALL-6 | S–M (6h) |
| 7 | Intrabar-primary PF on class cards; ETF daily PF 1.84 vs 0.02 labelled "upper bound" | etf / overall | S |
| 8 | Fix EQUITY/BOND published stats (PF 8.86 on n=8; BOND 0.06 vs 0.59) — one stats module | equity / bond | M |
| 9 | BOND gate honesty: `minTrades=0` → thresholdPass must be false/insufficient-data | bond | S (<1h) |
| 10 | CI contract tests (recomputed-vs-stored PnL, count reconciliation, artifact age) | overall QW-ALL-8 | M (10h) |

## Rollout
**First weekend (display/honesty, low risk):** QW-ALL-1, QW-ALL-6, QW-ALL-3 display half, guardian MAX-by-id.
**Following week (ledger):** QW-ALL-2 contract → dry-run → guarded per-class backfill (snapshot first); QW-ALL-4 drain; QW-ALL-5; QW-ALL-7 (frontend stops recomputing PnL); QW-ALL-9 (status vocab + `total_pnl_pct` rename with alias). Contract tests go from warn → fail as each fix lands.
Per AGENTS.md: each implemented fix ships with `updates/<date>-<desc>.md` on a clean branch with only your files; no force-push; never run `check_active_picks.py` / `smart_picks_engine.py` unasked.

## Dependency note (from peer R2 review, accepted)
Several per-class files repeat the same root-cause fixes (same-bar TP/SL, freshness guardian, classifier unification). Implement them **once** via the OVERALL items and treat per-class files as scopes/verifications, not separate implementations: same-bar → `forward_validator` (ETF/CRYPTO/FOREX), freshness-by-class → `db_freshness_check.py` (FUTURES/COMMODITY/ETF), classifier → `alpha_engine/asset_class.py` (FOREX/BOND/ETF/FUTURES/COMMODITY). Ordering dependency: display floors (min-n, intrabar-primary) are only trustworthy **after** QW-ALL-2 (unit contract) — republished numbers will move again until then.

## Status delta (~18:00Z)
Peers have begun implementing: gatekeeper leakage flip shipped by finpredict-v3 (verify before duplicating QW-CRYPTO-3b), 3 P0 truth fixes by finpredict incl. a NEW adopted item QW-ALL-10 (`summary_picks` WR>100%) and QW-ALL-11 (dead-JS deploy guard). Full merged delta: `../../scratch-hippodraco.MD` Appendix A.

## Peer corroboration (see peer-review/)
Independent audits in `childlike-airport`, `flaxen-hair`, `hilarious-seer` worktrees found the **same** unit bug (flaxen recomputed it in JSON files: `vix_reversal::SI=F` rows 100× apart), the same stale/zombie pattern, and the same mutual-fund gap — three-way corroboration. Where peers proposed unsafe variants (writing `pnl_pct=0` on expiry, `|v|≤1` auto-normalisation), this folder adopts the safe version (NULL tombstone, recompute-from-prices guard) and flags the difference in `peer-review/PEER_REVIEW.md`.
