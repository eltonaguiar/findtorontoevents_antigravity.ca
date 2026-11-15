# Phase 1 head start — where the history actually lives

Verified against the tree on 2026-11-15. Quote paths exactly; several contain spaces.

## One correction before you start

**No file is literally named `RECOVERY_PROTOCOL*.MD`.** `find . -iname "*recovery*protocol*"`
returns nothing at any depth. The protocol documents that do exist are named `PROTOCOL*.md`,
and they live outside `reports/`:

| Path | Note |
|---|---|
| `research/profitability/PROTOCOL.md` | the base protocol |
| `research/profitability/PROTOCOL_v3.md`, `PROTOCOL_v4.md` | later revisions |
| `research/profitability/PROTOCOL_ADDENDUM_1.md` | addendum |
| `2026-11-15_AM_profitability-plan/copilot-financial-review/10_FORWARD_TRACKING_PROTOCOL.md` | current forward-tracking protocol |
| `rigorous_validation_protocol.py` (root) | the executable version of the validation protocol |

Point agents at those instead of hunting a filename that does not exist.

## 1. The audit protocol (read first, it defines the vocabulary)

| Path | What it is |
|---|---|
| `.claude/skills/money-maker-ready/SKILL.md` | the v1 per-asset-class edge audit; defines PROVEN/PROMISING/REJECT |
| `.claude/skills/money-maker-readyv2/SKILL.md` | v2: stronger success criteria, nav-surface edge matrix, weekly filter |
| `.claude/skills/money-maker-ready-June112026edition/SKILL.md` | June 2026 edition |
| `.claude/skills/money-maker-ready-July112026edition/SKILL.md` | July 2026 edition, latest |
| `docs/BACKTEST_ADMISSIBILITY_STANDARD.md` | the repo's own admissibility bar (block bootstrap, Tier-1 conditions) |
| `.claude/skills/hypothesis-registry/SKILL.md` | how a hypothesis is pre-registered before any backtest (rule M-107) |
| `.claude/skills/hypothesis-registry-explained/SKILL.md` | the conceptual version |

## 2. Money-maker outputs (the audits themselves)

Per-class plan/result pairs — 16 files, the most directly comparable set:

```
reports/peer_claude-phase10b-money-maker-{EQUITY,CRYPTO,FOREX,ETF,bond,commodity,futures,penny}_{plan,result}_2026-05-31.md
```

| Path | What it is |
|---|---|
| `reports/MONEY_MAKER_READY_JUNE_2026_EDITION.md` | consolidated June edition |
| `reports/money_maker_ready_20260611.md` | latest single-file readiness report |
| `reports/2026-05-26_money_maker_v2_unblock_plan.md` | what blocked v2 and why |
| `reports/grok_money_maker_audit_transcript_2026-05-15.md` | outside-model audit transcript |
| `reports/ollama_consult_money_maker_synthesis_2026-05-12.md` | local-model synthesis |
| `reports/ollama_consult_money_maker_qwen25coder14b.md`, `..._qwen3-claude-opus-distill.md`, `..._qwen35cloud.md` | raw local-model consults |
| `updates/2026-05-13-money-maker-action-plan.md` | the action plan derived from all of the above |
| `updates/2026-05-11-money-maker-{master-plan,multi-agent-comparison,kimi,codex,cursor,claude-code,copilot}.html` | the five-agent bake-off (published) |
| `final_v4/flaxen-hair_2026-11-14T2200/05_money_maker_readyv2/` | most recent run of the v2 skill |
| `backups/money-maker-readyv2.md.bak` | prior skill text (diff it to see what the criteria were then) |

Do **not** read `archive/2026-05-31_testing_protocol_dedupe/reports_money_maker_*` — duplicate
snapshots of the files above. Same content, older names.

## 3. Edge conclusions already reached (so nobody re-litigates them)

| Path | Conclusion on file |
|---|---|
| `reports/EDGE_HUNT_DEFINITIVE_CONCLUSION_2026-06-22.md` | the "we have looked everywhere" capstone |
| `reports/EDGE_HUNT_EXHAUSTED_2026-05-18.md` | exhausted-avenues inventory |
| `reports/NET_EDGE_HUNT_2026-06-13.md` | net-of-cost hunt |
| `reports/DEFINITIVE_NETCOST_MONEYREADY_SCAN_2026-06-13.md` | net-cost money-ready scan |
| `reports/REAL_MONEY_NO_SURVIVORS_2026-06-05.md` | zero survivors under the real-money bar |
| `reports/BOTH_GOALS_EXHAUSTED_CAPSTONE_2026-06-22.md` | both objectives closed |
| `reports/PATH_TO_PROVEN_EDGE_2026-05-17.md` | the roadmap version |
| `reports/EDGE_BY_ASSET_CLASS_2026_04_22.md` | first per-class verdict set |
| `docs/STRATEGY_AUDIT.md` | ~450 strategies catalogued, by system |
| `docs/PROVEN_LIVE_STRATEGIES.md` | what the repo *claims* is proven (treat as a claim, not evidence) |
| `reports/2026-10-22-proven-winners-per-asset-class.md` | most recent winner list |
| `reports/2026-10-22-winner-hunt-aggregated-findings.md` | aggregate of that hunt |

## 4. Kimi swarm — 14 top-level folders

```
KIMI/                                  KIMI_RISEOFTHECLAW/
KIMI_FEB172026/                        KIMI_CLAW_RESEARCH_FEB162026/
KIMI_NEW STUFF ALERTS ETC/             Kimi_Agent_Improving Crypto_Forex Picks/
Kimi_Agent_Investigating Crypto_Forex Win-Rate/
Kimi_Agent_From Coin Flip to Hedge Fund Picks/
Kimi_Agent_Winning Algo_ Signals & Communities_Feb 14 2026/
Kimi_Agent_High-Score Asset Picks/     Kimi_Agent_Crypto Pick Strategy Challenge Winners/
Kimi_Agent_BTC Scalping Strategy Replication/
Kimi_Agent_AI Algorithm Prompting Guide/
Kimi_Agent_ML Enhancement Integration Plan/
```

Highest-value files inside them:

- `KIMI/KIMI_AGENTSWARM_MOTHERLOAD.md` — the swarm's own master prompt/plan
- `KIMI_RISEOFTHECLAW/STRATEGY_RESEARCH_FRAMEWORK.md`, `STRATEGY_RESEARCH_NOTES.md`, `STRATEGY_STATUS_REPORT.md`, `HIGH_SHARPE_STRATEGIES.md`, `SKYROCKET_STRATEGIES.md`, `EXECUTIVE_DASHBOARD.md`, `MULTI_AGENT_PIPELINE.md` — the research record
- `KIMI_RISEOFTHECLAW/elimination_engine.py`, `backtest_v2.py`, `battle_test_rigorous.py`, `ml_signal_ranker.py`, `live_challenge.py` — the actual machinery
- `Kimi_Agent_From Coin Flip to Hedge Fund Picks/hedge_fund_quality_framework.md` + `comprehensive_audit_report.txt` + the per-class `*_audit_report.txt` files
- `Kimi_Agent_Investigating Crypto_Forex Win-Rate/WIN_RATE_INVESTIGATION_REPORT.md` + `mysql_database_forensics_report.md`

Reports about the swarm (60+): `reports/KIMI_*`, `reports/kimi_*`, `reports/peer_claude-deep_critique_kimi_2026-05-31.md`,
`reports/KIMI_SWARM_VERIFICATION_2026-05-20T0200Z.md`, `reports/kimi_ultimate_proven_edge_2026-05-16.md`,
`reports/KIMI_VS_MAIN_COMPARISON_2026_05_02.md`, `swarm_runs/KIMI_{AUDIT,PREDICTION_EDGE}AUDIT_RESPONSE.md`.

## 5. The measurement instruments (use these; don't reimplement)

| Path | Measures |
|---|---|
| `reports/hypothesis_registry.json` | every pre-registered hypothesis, its rule, its verdict |
| `reports/hypothesis_test_results.json`, `reports/HYPOTHESIS_TEST_RESULTS.md` | harness outputs |
| `tools/hypothesis_test_harness.py` | runs a registered hypothesis |
| `tools/forward_tracker.py` | pre-registered forward ledger + O'Brien-Fleming interim looks + kill rules |
| `state/forward_test/plan.json` | the live pre-registration (start dates, fixed sample, kill rules) |
| `tools/pick_excess.py` | excess-vs-benchmark definition, clustered t, collapsed windows |
| `tools/build_benchmark_prices.py` | daily SPY / BTC-USD closes used as the benchmark leg |
| `alpha_engine/deflated_sharpe.py` | Bailey–López de Prado DSR |
| `alpha_engine/rigorous_backtest_harness.py` | purged k-fold walk-forward + DSR + PBO wiring |
| `alpha_engine/walkforward_validator.py` | walk-forward efficiency |
| `alpha_engine/statistical_validation_framework.py` | the shared stats layer |
| `audit_trail/quality_gates.py` | the gates a pick must pass in production (threshold freeze!) |
| `ml_gatekeeper/gatekeeper.py`, `ml_consensus/consensus.py` | ML quality gate + consensus |
| `probabilistic_sharpe_engine.py` (root) | PSR/DSR + Monte Carlo engine |
| `tools/deflated_sharpe_results.json` | per-strategy DSR results used by the live EAGLE gate |
| `reports/pbo_cpcv_dsr_wiring_audit_2026-06-05.md` | what was wired vs merely written |
| `reports/whites_reality_check_m105.md`, `reports/whites_reality_check_2026-05-17.md` | White's Reality Check runs |
| `reports/AUDIT_STAT_VALIDATION_2026-05-22.md` | do the dashboard's own stats hold up |

**PBO and White's Reality Check are not in the main tree.** `tools/pbo.py`,
`tools/whites_reality_check.py` and `tools/pbo_cscv.py` exist only under
`.claude/worktrees/cluster-a-fix-2026-06-21/tools/`. Main keeps the *reports* of those runs but
not the code, which is the repo's signature failure mode (a method run once by an agent, then
left behind). Re-establish the implementation next to its report before citing its numbers.

Provenance of the numbers on the live page: `audit_dashboard/data/dashboard_data.json`
(generated) from `audit_trail/dashboard_generator.py`. Any per-class WR/PF must be traced to
that JSON, not to a report that summarised it.

## 6. Known landmines (save the agent a day)

1. **`n < 30` rows are unproven, not failed.** Most of the repo's "kill" history is kills of
   strategies that never had enough trades to be judged.
2. **Correlated rows.** Many picks share one `closed_at` (one market episode). Clustered t,
   not trade-level t.
3. **Threshold freezes.** `audit_trail/quality_gates.py` prints `THRESHOLD FREEZE ACTIVE`; a
   gate change may be inert by design.
4. **Silent file reverts.** Concurrent agents/processes rewrite files on disk. Verify against
   `git show <commit>:<path>`, not against what `cat` shows.
5. **Generated files are committed.** `audit_dashboard/index.html` is generated from
   `audit_dashboard/template.html` — edit the template, never the output.
6. **Dedupe before reviewing.** `archive/2026-05-31_testing_protocol_dedupe/` is a copy of
   reports you will also find live.
