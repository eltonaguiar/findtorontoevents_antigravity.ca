# First-stop repository map

This is a navigation aid, **not an exhaustive inventory or a profitability
audit**. Paths were checked in the local working tree on 2026-11-15. Historical
reports and current-looking snapshots are claims to independently recheck.
The working tree can differ from GitHub `main`; record the actual commit,
uncommitted inputs and snapshot timestamps when doing the audit.

## 1. Orientation and previous investigations

1. `AGENTS.md` and `docs/AGENT_QUICKSTART_AUDIT_AND_STRATEGIES.md` — workspace
   constraints, dashboard flow, strategy registries and data-source overview.
2. `.claude/skills/money-maker-ready/SKILL.md`,
   `.claude/skills/money-maker-readyv2/SKILL.md`,
   `.claude/skills/money-maker-ready-June112026edition/SKILL.md` and
   `.claude/skills/money-maker-ready-July112026edition/SKILL.md` — previous
   audit programs and the July pivot. The July document's ETF allocation and
   crypto measurement conclusions are historical claims, not current proof.
3. `docs/MONEY_READY_MASTER_LOOP_2026-06.md`, `TESTING_PROTOCOL.MD` and
   `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — previous validation and
   mutate-before-kill rules. Treat retrospective symbol/timeframe slicing as
   additional trials, requiring independent evaluation.
4. `reports/KIMI_HF_STRATEGY_REVIEW_2026_05_02.md`,
   `docs/kimi_audit/kimi_quant_audit.md` and
   `updates/2026-05-14-audit-dashboard-kimi-protocol-operationalization.md` —
   starting points for Kimi's prior reviews and operationalization. Many more
   Kimi-related items exist; search rather than assuming these are complete.
5. `WIRED_IN/README.md` and prior dated folders, especially
   `WIRED_IN/2026-11-15_012638_UTC_copilot-financial-review-20261115/` and
   `WIRED_IN/2026-11-15_0128_buffy/` — earlier specifications and elimination
   evidence. Review independently and preserve other contributors' work.
6. `updates/index.html` — public-facing strategy history. Compare it with
   dated evidence and code; an update entry is not itself proof.

An independent local search did not find an exact `RECOVERY_PROTOCOL` filename
or matching phrase. This is a **search result, not proof of absence**: check
other names, cases, untracked material, branches and inaccessible files as
authorized. Record gaps.

## 2. Live picks and data integrity

- `audit_dashboard/template.html` — dashboard source; do not edit the
  generated dashboard HTML.
- `audit_trail/dashboard_generator.py`,
  `audit_trail/universal_pick_resolver.py`, `audit_trail/quality_gates.py`
  and `alpha_engine/outcome_resolver.py` — investigate generation, filters
  and outcome handling. Trace actual callers and current runtime configuration;
  do not infer live behavior from filenames alone.
- `audit_dashboard/data/dashboard_data.json`,
  `audit_dashboard/data/money_ready_verdict.json` and
  `audit_dashboard/data/pf_registry.json` — local snapshots if present; check
  timestamps, lineage, cohorts and whether tracked before using numbers.
  Some files are large; inspect keys and bounded slices rather than dumping
  them. Reconcile with the live surface and source ledger when authorized.
- `reports/hypothesis_registry.json` — existing hypothesis registration
  record; consult the applicable repository protocol before new tests.

## 3. Strategy, validation and risk code

- `alpha_engine/scanner.py`, `alpha_engine/crypto_edge_strategies.py`,
  `alpha_engine/cointegration_pairs.py`, `alpha_engine/equity_strategies.py`,
  `alpha_engine/forex_strategies.py`, `alpha_engine/etf_strategies.py`,
  `alpha_engine/etf_scanner.py`, `alpha_engine/bond_scanner.py` — starting
  points across asset classes; discover other registries and verify wiring.
- `alpha_engine/backtest/` — backtest engine, costs, portfolio and sizing;
  `alpha_engine/walkforward_validator.py` — walk-forward implementation.
  Establish actual assumptions before reusing them.
- `alpha_engine/benchmark_closed_ledger.py` and
  `tests/test_benchmark_closed_ledger.py` — existing paired benchmark and
  random-entry tools/tests. Examine assumptions and benchmark suitability;
  their presence does not establish a complete proof standard.
- `tools/mutation_analysis.py`, `tools/tactical_rotation_tracker.py` and
  `tools/tactical_blend_tracker.py` — prior slice and allocation research.
  Check their side effects and data requirements before running anything.
- `reports/`, `alpha_engine/data/`, `tests/` and `.github/workflows/` —
  reports, saved experiment outputs, tests and actual scheduled runners.
  Source data and archived results can be incomplete or stale.

## 4. Discovery recipe

From the repository root, an initial **filename** search is:

```bash
find . \( -name .git -o -name node_modules -o -name .venv \) -prune -o \
  \( -iname '*money-maker*' -o -iname '*money_maker*' -o -iname '*money_ready*' \
     -o -iname '*recovery*protocol*' -o -iname '*kimi*' \) -print
```

This intentionally excludes `.git`, `node_modules` and `.venv`; it does not
search other branches or prove the content was reviewed. Use bounded
content searches for naming variations and relevant concepts, deduplicate
copies, then log counts, actual reviews, exclusions and access failures.
Never print secrets or send repository/private data to outside providers.

## Files in this kit

- `SINGLE_AGENT_PROMPT.md` — copy-paste instructions for the investigation.
- `AUDIT_REPORT_TEMPLATE.md` — source coverage, inventory and failure report.
- `STRATEGY_SHORTLIST_TEMPLATE.md` — candidate specifications and evidence.

These are instructions and blank templates; **no backtest, live-data
reconciliation or profitability determination was performed for this kit**.
