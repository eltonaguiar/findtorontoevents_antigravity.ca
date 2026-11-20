# Session log — audit surface consolidation (2026-11-20)

**Agent:** Zoo (subq-savant-1.4) · **Mode:** architect → code
**Worktree:** `/home/eaguiar2015/findtorontoevents_antigravity.ca`
**Plan:** [`plans/2026-11-20-audit-surface-consolidation-plan.md`](../../plans/2026-11-20-audit-surface-consolidation-plan.md)

## What was asked

1. Review all recent COMS messages and get caught up.
2. Register for COMS (`COMS register --agent <provider>-<model>`), subscribe only to my inbox.
3. Look into the repo and the three live surfaces — findtorontoevents.ca/audit, /audit2, /audit3.
4. Create a plan of suggested fixes, including a test plan, with the goal of consolidating
   what is useful from the three audit surfaces into one source, given the MySQL databases
   and GitHub Actions jobs behind them.
5. Context from the user: we have tried to predict stocks, crypto, forex, bonds, ETFs,
   commodities, futures and mutual funds, and have not found anything strong yet.

## What I did

- Loaded the `coms-messaging` skill for the bus protocol (`inbox/<host>/<worktree>/<agent>`,
  QoS 1 vs retained, register writes a retained `registry/...` topic).
- Searched the repo for `audit2`/`audit3` references and read the landed reviews instead of
  re-deriving them: `docs/AUDIT_SURFACES_FULL_REVIEW_2026-11-19.md`,
  `docs/NEXT_PHASE_PLAN_2026-11-19.md`, `docs/plans/2026-11-19-audit3-v2-evidence-and-success-metric-plan.md`,
  plus the COMS handoffs (`COMS_AUDIT2_3_HANDOFF_2026-11-19.md`, `COMS_STATUS_2026-11-19.md`).
- Inspected the deploy registry in [`tools/deploy_audit_files.py`](../../tools/deploy_audit_files.py)
  and the audit2 merge guard [`tests/test_audit2_page_deploy.py`](../../tests/test_audit2_page_deploy.py).
- Wrote the consolidation plan with a P0/P1/P2 fix backlog, a test plan (unit, e2e, live smoke,
  fail-injection) and an explicit non-goals section.

## Findings that drive the plan

| Finding | Evidence |
|---|---|
| Two workflows publish `audit3_ledger.json` | `audit3-ledger.yml` (6-hourly → `/audit3`) and `audit-dashboard.yml` (hourly → `/audit/data`); measured lag 223 min |
| Three money-ready denominators | `/audit` 0/10, `/audit3` 0/9, audit2 echoes the ledger |
| Contradictory class numbers | COMMODITY `WATCH` vs `KILL`; ETF WR 1.9% vs 43.2% |
| Two kill lists, one shared name | 42/56 legacy vs 8–11 audit3 cells; only `futures_momentum` in common |
| Selection alpha negative | −0.2763%/trade, CI [−0.506, −0.043], n=3,192 |
| Coverage over 100% | `scored_rows` 8,605 vs `valid_closed_picks` 8,175 → 105.26% |
| Class labels contaminated | all 285 `bt_backtest_runs` tagged CRYPTO, incl. `NZDUSD=X`, `AUDJPY=X` |
| Sleeves not evidence | 0/10 verified against audit3 cells; CRYPTO sleeve PF 155.85 inside class PF 0.8383 |

## Suggestions

1. One artifact, one writer — and make parity a hard gate, not a warning.
2. One population and one provenance triple on every tile; a page may show a slice but must
   label it and print the denominator.
3. Lead with selection alpha, not win rate or raw PF.
4. Keep the two kill vocabularies separate but publish their union with provenance.
5. Do not hunt new strategies until the measurement layer is auditable.

## Next

Implement P0-1 (single writer), then P0-2 (parity gate) with fail-injection tests, polling
COMS between steps.
