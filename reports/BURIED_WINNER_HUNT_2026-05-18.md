# Buried-Winner Hunt — 2026-05-18

Crawled the findtorontoevents.ca dashboard/tool links + Investment Hub to test
whether a genuinely strong system was orphaned and never fed into `/audit`.
3 parallel subagents (liveness, claimed-winner fact-check, orphan hunt).

## Verdict: NO buried winner. The user's suspicion is refuted.

Every "winner" claim is one of: cumulative-PnL inflation, fabricated/zeroed
PnL, placeholder-stat artifact (near-zero avg-loss → gaudy PF), un-deduped
OOS-export selection bias, or a stale backtest deck never run live.

## Link liveness (30 dashboards)

26 alive · **4 dead (404)**: `audit_dashboard/`, `breakout-arena/`,
`cross_aggregation/forward_test.html`, `audit/hyrotrader/` · **1 stale**:
`riseoftheclaw/` (frozen 2026-02-17). Production `/audit` + `findcryptopairs/now`
fresh (2026-05-18).

## "Before You Trade" checklist (2026-04-03) — all 5 systems FALSE

| system | checklist claim | reality |
|--------|-----------------|---------|
| Battleground DNA | 62% WR, +161% PnL, "best system" | cumulative-PnL inflation; raw 56.9% WR / +32.8% cum; canonical CRYPTO PF 1.25. No "DNA" entry in canonical registry. |
| System F ClawsOfDoom | 52% WR, +41% PnL | actual 49.4% WR (coin flip, below break-even); **all `pnl` fields = 0** — "+41%" fabricated. |
| Triple_EMA | PF 1.50, 6/6 symbols | canonical `proven_triple_ema_pullback` = n=1, WR 0%, PF 0. |
| Volume_Spike | PF 3.84–6.93 | no `volume_spike` strategy exists in canonical; PF range = ml_enhanced placeholder-stat fingerprint. |
| Cross-Aggregation Consensus | "trade when 3+ agree" | non-functional template; nearest real strategy `ensemble` PF 1.47 (sub-floor). |

**The Apr-3 checklist is stale + inflated — do not size any position on it.**

## Orphaned-winner candidates — none credible

- `aggregated_picks` 77.9% WR / PF 6.94, `kimi_signal_tracking` 76.6% / 7.70 —
  un-deduped `universal_resolved_picks.json` OOS-export numbers; the
  `hc_filter_backtest` report itself admits "the source-system gate does all
  the work" = selection bias, not edge. Already in-pipeline, not orphaned.
- `NEW_STRATEGIES_FINAL_REPORT.md` 8 strategies (KC_SCALP_v1 etc.) "PF 1.68–2.40,
  +195% PnL, ready for deployment" — closest to orphaned, BUT a 2026-03-08
  backtest-only deck, round-number WRs (73.0/71.0/69.0%), forward test never
  run, zero live picks. Orphaned because never executed, not a hidden winner.

## One actionable bug found

`audit_trail/quality_gates.py:4862-4869` — `_100WR_COMBOS` score boosts
(`auditensemble_long` PF 38, `vwap deviation scalp` PF 119) are the **same
near-zero-avg-loss placeholder pattern M-105 just removed for `ml_enhanced`
four lines above** (`:4857-4861`). Still live in the score path, absent from
the canonical registry. Self-contradicting — flagged for verify-or-strip
(quality_gates.py is peer-hot; not blind-edited here).

## Bottom line

Consistent with `EDGE_VERDICT_2026-05-18`, `COHORT_HARNESS_VERDICT_2026-05-18`,
M-105: no class above PF 1.5 in the canonical deduped ledger; 9+ harness kills;
0 admissible. A real buried winner would have to survive dedup + the
walk-forward harness — **none does.** No orphaned edge exists. The dashboards
display brand pages and cumulative-PnL tiles, not harness-grade verdicts.
