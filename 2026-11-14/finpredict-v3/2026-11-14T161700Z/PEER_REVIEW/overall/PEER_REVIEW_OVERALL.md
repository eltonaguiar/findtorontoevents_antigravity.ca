# PEER REVIEW — Overall / Systemic (2026-11-14)

Reviewing the 2026-11-14 prediction-system audit archives produced by the peer agents. This is a REVIEW of their work (not a new audit); every figure is attributed to its source peer.

## 1. Peer inventory reviewed

| Peer | Archive | Reviewed |
|---|---|---|
| finpredict (v1) | `.kilo/worktrees/finpredict/2026-11-14/finpredict/2026-11-14T160004Z/` | `2026-11-14-prediction-system-audit.md` (most complete merged doc) |
| finpredict-v2 | `.kilo/worktrees/finpredict-v2/2026-11-14/finpredict-v2_20261114-1602/` | `sub/E_statistical.md`, `sub/G_peer_reconciliation.md`, `sub/C_crypto.md` + raw evidence |
| finpredict-v4 | `audits/2026-11-14/finpredict-v4_2026-11-14-1555/` | `INDEX.md`, `actions_health_report.md`, `dashboard_metrics_sources.md`, `evidence_*.json` |
| ML-audit (childlike-airport) | `updates/2026-11-14-ML-AUDIT-childlike-airport/` | `proposed_fixes/` per class |
| hilarious-seer | `.kilo/worktrees/hilarious-seer/audit_quickwins/2026-11-14-hilarious-seer/` | quick-win proposals |
| spice-hyena | `.kilo/worktrees/spice-hyena/forreviews_final/2026-11-14T03-25-00Z_spice-hyena/` | review material |
| finpredict-v3 (mine) | `.kilo/worktrees/finpredict-v3/2026-11-14/finpredict-v3/2026-11-14T155500Z/` | audit + hygiene tool + quick-wins (reference) |

## 2. Verdict consensus — ALL peers agree: not money-ready, negative aggregate, multiple-testing/survivorship artifact

| Metric | v1 | v2 | v4 | mine |
|---|---|---|---|---|
| Overall WR | 41.8% | 41.8% | 41.8% | 41.8% |
| Profit factor | 0.94 | 0.94 | 0.94 | 0.94 |
| Compounded EW PnL | −99% | −99% | −99% | −99% |
| Sharpe (annual) | −1.31 | −1.31 | −1.31 | −1.31 |
| money_ready passes | 0/9 | 0/9 | 0/9 | 0/9 |
| Verdict | FAIL | FAIL | FAIL | FAIL |

Multiple-testing math: 361 strategy families + 285 baby strategies + mutation lab ⇒ ~260 lucky PF>1.5 survivors expected at p=5% (v1). Anti-overfit: 31/38 (82%) OVERFIT_LIKELY (v1). z-scores: CRYPTO z=−7.1, EQUITY z=1.39 (<1.96) (v1).

## 3. Systemic agreements (2+ peers independently confirmed)

- Crypto `current_price` pinned to entry (XRP/BTC at 0% while market moved) — v1, v2, v4, mine.
- Zombie raw feed: `inverse_mutations`/`inverse_luxalgo_confluence` ~2,267 rows; CRYPTO raw median ~89d — v2, mine (+v1).
- Survivorship: only 7,914/16,126 closed (49%) pass integrity; 8,888 auto-expired — all peers.
- `hyro_pick_performance.json` stale ~157h (6.6d) — v1, v2, mine.
- Actions failures cluster in trading/price/DB pipelines; 20+ workflows never run — v1, v4, mine.
- "1.9h ago" = signal age, not price freshness — v1, v2, v4, mine.

## 4. Disagreements / contradictions (call out)

- **Futures date-only seed:** v1 says it renders "no date" in the UI; v2 says NOT REPRODUCED (page shows a date). Flag for the master reviewer to settle against the live page.
- **Active-count surfaces differ:** 20 (curated `.picks.active`), 4,148 (`active_raw`), 263 (`concentration_summary.total_active`), 4,310 (`picks_now_live_pnl`), and v4 reported "0" on one surface. Name the surface before quoting a count.
- **v4 noncrypto is June-snapshot based:** v4 says COMMODITY "dead since June" / FUTURES "0 live"; the live 14:30Z payload has COMMODITY signals today (14:22Z). Treat v4 noncrypto as June baseline, not today.
- **EQUITY:** headline 75%/PF 8.86 on n=8 vs full n=461 (~43%/PF 0.70) — peers agree the headline is misleading, but cite different counter-samples.
- **Stale figures to drop/re-label:** "37 active in June" (actually May 2), "61% spot-flicker" (registry-wide is 7.7%), June "−1.4% 14d" (live 14d sum is −333%).

## 5. Gaps across all peers

- Workflow failure root causes (per-step logs) — UNVERIFIED everywhere (admin-only).
- Kalshi / prediction-market snapshot staleness — unresolved (code real, feeds dead).
- The peer transcript file (`chat_transcript_2026-11-14.md`) — NOT on disk.
- External equity quotes only confirm Friday close (no paid/real-time feed).

## 6. Best-of recommendation for the master plan

- **Backbone:** adopt v1 `2026-11-14-prediction-system-audit.md` (it already cross-references all peers and separates verified vs attributed).
- **Actions health:** v4 `actions_health_report.md` (GitHub-API counts) as primary; keep v1's named-step list as commentary.
- **Statistics/multiple-testing:** v2 `E_statistical.md` + v1 z-scores/expected-survivor math.
- **Runnable deliverable:** v3 `tools/pi_data_hygiene.py` + tests (only CI-gateable artifact; exit 1 on findings).
- **Per-class fixes:** ML-childlike-airport FIX_PROPOSED (DB-level PnL recompute/feed sync) for BOND/CRYPTO; v2 zombie quarantine; v4 retire-vs-re-emission gate for FUTURES.
- **Numbers to drop/relabel:** 37 active, 61% flicker, −1.4% 14d, v4 noncrypto-as-June.
