# GHA Strategy Kill Tribunal Findings — 2026-11-16

Repo: eltonaguiar/findtorontoevents_antigravity.ca
Worktree: .kilo/worktrees/ghactions-v4

## 1. Kill Tribunal / Kill Switch Infrastructure

### Workflows

| Workflow | Path | Schedule | Entry Point |
|----------|------|----------|-------------|
| Strategy Kill Tribunal | `.github/workflows/strategy-tribunal.yml` | Fri 14:00 UTC (cron `53 14 * * 5`) + `workflow_dispatch` | `tools/strategy_kill_tribunal.py` |
| Honest Kill Switch | `.github/workflows/honest-kill-switch.yml` | Every 12h (cron `49 */12 * * *`) + `workflow_dispatch` | `alpha_engine/honest_kill_switch.py --apply` |

### Tribunal (weekly, P1-B)

`tools/strategy_kill_tribunal.py` queries `at_signal_outcomes` (MySQL, intrabar-resolved TP_HIT/SL_HIT only, 90d window) and classifies each `strategy x asset_class`:

- **KILL**: n>=30 AND WR<35% AND PF<0.8
- **PROBATION**: n>=15 AND (WR<40% OR PF<1.0)
- **KEEP**: else

`DO_NOT_AUTO_KILL = {"luxalgo_confluence"}` — exempt unless n>=100 AND WR<40% (auto-override).

Apply mode (`--apply`) requires `TRIBUNAL_APPLY=1` secret; appends KILL verdicts to `audit_trail/data/emitter_audit.json` -> `recommended_actions.force_kill`.

Outputs:
- `reports/strategy_tribunal_<date>.json`
- `audit_dashboard/data/strategy_tribunal_latest.json` (dashboard sidecar — currently 404s on live site per peer review RR3)
- `audit_trail/data/emitter_audit.json`

### Honest Kill Switch (every 12h)

`alpha_engine/honest_kill_switch.py` queries `trading_picks` (primary) + `at_pick_outcomes` (supplement). Criteria: min_trades=30, min_wr=0.45, min_pf=1.0 (per asset class). Latest run (2026-11-16T00:26): 181 total, 56 evaluated, 14 survivors, 42 killed, 115 insufficient data, 10 protected.

Outputs:
- `alpha_engine/data/honest_kill_switch.json`
- `alpha_engine/strategy_kill_list.json`
- `reports/blacklist_impact_simulation.json`

### Blocklist / Kill List / Core Whitelist

| File | Path | Purpose |
|------|------|---------|
| Core whitelist | `alpha_engine/data/core_whitelist.json` | `protected_strategies` (21), `core_strategies` (20), `incubator_strategies` (9), `kill_list` (~520 system-strategy pairs), `kill_patterns` (2), metadata incl. `last_kill_run` |
| Blocklist | `alpha_engine/strategy_blocklist.py` | `_RETIRED_STRATEGIES` (hard-block, ~47 names), `_PAPER_ONLY_STRATEGIES` (~40 names), FX kill switch, commodity inverse kill switch, composite system-strategy pairs with per-pair rollback env flags |
| Kill list (auto) | `alpha_engine/data/strategy_kill_list.json` | `auto_kill_strategies`: currently **empty** |
| Kill switch status | `alpha_engine/data/kill_switch_status.json` | Per-strategy status (latest: critical, rolling 20-trade WR 15%) |

### Dashboard Generator Rendering

`audit_trail/dashboard_generator.py`:
- Lines 18135–18178: injects `payload["kill_switch"]` metrics from `honest_kill_switch.json` + `blacklist_impact_simulation.json`
- Lines 1045–1175: `_apply_external_source_gate()` blocks external-source picks whose strategy is in `core_whitelist.json` kill_list
- Lines 14613–14634: auto-tuner kill list filter on dashboard output
- `JSON_PICK_SOURCES` (line 3685): registry of all JSON pick sources used by `pipeline_health_monitor.py` for staleness checks

## 2. Flagged Strategy Analysis

### CRITICAL — signal_validation (KILL)

| Metric | Value |
|--------|-------|
| WR | 5.9% |
| PF | 0.12 |
| MDD | 121.8% |
| n | 102 |
| 90d cum | -116.8% |
| Tier | Below Tier 3 |

**Controls:**
- `signal_validation::MomentumEMA` is in `core_whitelist.json` kill_list
- NOT in `strategy_blocklist.py` `_RETIRED_STRATEGIES`
- NOT in `honest_kill_switch.json` killed list

**Recommendation:** KILL immediately. PF=0.12 is catastrophic. Add `signal_validation` to `_RETIRED_STRATEGIES` in `strategy_blocklist.py`, apply tribunal kill, and verify no active picks remain on the dashboard.

### mega_mutation (KEEP — proven winner)

| Metric | Value |
|--------|-------|
| WR | 58.3% |
| PF | 1.96 |
| MDD | 24.3% |
| n | 103 |
| 90d cum | +150.3% |
| Tier | Tier 3 |
| Status | Paper-trading floor |

**Controls:**
- `mega_mutation::unknown` is in `core_whitelist.json` kill_list
- **UNBLOCKED 2026-06-05** per `strategy_blocklist.py` comments (lines 198–213): sign-coherence check retraction, direction-aware query shows sign_flips=0, post-INCIDENT#91 stats n=109 WR=61.5% PF=2.79
- NOT in `strategy_blocklist.py` `_RETIRED_STRATEGIES`
- NOT in `honest_kill_switch.json` killed list

**Recommendation:** KEEP. It is the only verified CRYPTO edge. Remove `mega_mutation::unknown` from `core_whitelist.json` kill_list (stale entry contradicts unblock). Production enable follows paper pilot promotion gate: rolling_30d_n_closed>=30, WR>=55%, PF within 30% of 2.79. `production_enable=false` in `mega_mutation_state.json` until pilot passes.

### rl_agent (Building — needs 100+ picks)

| Metric | Value |
|--------|-------|
| WR | 0.0% |
| PF | 0.00 |
| MDD | 0.0% |
| n | 0 |
| Status | Building |

**Controls:**
- `rl_agent::rl_ppo_agent` is in `core_whitelist.json` kill_list
- NOT in `strategy_blocklist.py` retired set

**Recommendation:** Keep in Building / paper-only. Do not kill yet — zero picks means insufficient data, not proven toxicity. Needs 100+ resolved picks to graduate. Remove `rl_agent::rl_ppo_agent` from core_whitelist kill_list (premature kill on zero-data strategy) or move to `incubator_strategies`/paper-only.

### claude_gainer (not in systems[] feed)

**Controls:**
- `claude_gainer` is in `core_whitelist.json` kill_list
- `claude_gainer_st` is in `WEAK_SYSTEMS_SET` in `score_booster.py` (gets -10 score penalty)
- Multiple `claude_gainer*` variants in kill_list

**Recommendation:** Already blocked. Verify no picks leaking through `systems[]` feed. Investigate why absent entirely — possibly fully killed already.

---

### HIGH severity — REDUCE (>20% WR drop from baseline)

| Strategy | Rolling 7d WR | Baseline | Drop | Kill List Status |
|----------|--------------|----------|------|-----------------|
| forex_rsi2_mean_reversion | 5% | 20% | -75% | **CONTRADICTION**: blocklist retired (line 237) BUT honest_kill_switch SURVIVOR (n=893, WR=46.9%, PF=1.71) |
| kimi_signal_tracking | 2% | 43% | -95% | Blocked: kill_list (3 entries), blocklist retired (line 226), composite pair ("kimi_signal_tracking","default") |
| volume_spike_breakout | 31% | 47% | -34% | Blocked: kill_list, composite pair ("rapid_fire","volume_spike_breakout"), honest_kill_switch KILLED (n=856, WR=14.5%, PF=0.26) |
| ema_momentum_m006 | 36% | 48% | -25% | NOT in any kill list or blocklist |
| crypto-momentum-scout | 0% | 41% | -100% | Blocked: kill_list ("kimi_riseoftheclaw::crypto-momentum-scout") |
| unknown | 14% | 44% | -68% | Blocked: kill_list ("unknown"); honest_kill_switch insufficient data (n=29, WR=44.8%) |

**Recommendations:**
- **forex_rsi2_mean_reversion**: Investigate the blocklist vs honest_kill_switch contradiction. Rolling 7d WR=5% vs baseline 20% is a 75% collapse. Reduce position sizing or disable pending reconciliation. If blocklist retirement is authoritative, enforcement is already active; if honest kill switch survivor status is authoritative, re-evaluate.
- **kimi_signal_tracking**: Already hard-blocked across all three mechanisms. Verify enforcement — no new emissions since 2026-03-29 per blocklist comments.
- **volume_spike_breakout**: Already killed by honest kill switch and composite pair block. Verify no emissions.
- **ema_momentum_m006**: NOT blocked anywhere. Add to tribunal watchlist, reduce position sizing, monitor for n>=30 kill eligibility.
- **crypto-momentum-scout**: Already blocked as composite pair. Verify enforcement.
- **unknown**: Already in kill_list. Verify enforcement.

---

### MEDIUM severity — MONITOR (silent emitters)

| Emitter | Silent Duration |
|---------|----------------|
| forward_signals | 87h |
| orphan_emitter_bond | 61h |
| bond_scanner | 61h |
| orphan_emitter_etf | 60h |
| growth_stock_screener | 61h |

**Controls:** `pipeline_health_monitor.py` `check_staleness()` iterates `JSON_PICK_SOURCES` from `audit_trail/dashboard_generator.py:3685`, flags CRITICAL (>24h for crypto systems, >72h for non-crypto) and writes to `chatwithit.MD` via `--write-flags`.

**Recommendation:** Investigate why each emitter has not produced a pick. Check emitter process health, file mtime, and DB connectivity. Restart stalled emitters. `pipeline_health_monitor.py --fail-on-critical` can gate CI on stale critical systems.

---

## 3. Actionable Fixes Summary

| # | Strategy | Action | Mechanism | File |
|---|----------|--------|-----------|------|
| 1 | signal_validation | KILL | Add to `_RETIRED_STRATEGIES` + tribunal apply | `alpha_engine/strategy_blocklist.py` |
| 2 | mega_mutation | KEEP + remove stale kill_list entry | Remove from core_whitelist kill_list | `alpha_engine/data/core_whitelist.json` |
| 3 | rl_agent | Keep building, remove premature kill | Remove from core_whitelist kill_list or move to incubator | `alpha_engine/data/core_whitelist.json` |
| 4 | claude_gainer | Verify no leakage | Audit `systems[]` feed | `audit_trail/dashboard_generator.py` |
| 5 | forex_rsi2_mean_reversion | Investigate contradiction, reduce sizing | Reconcile blocklist vs honest_kill_switch | `alpha_engine/strategy_blocklist.py` / `alpha_engine/data/honest_kill_switch.json` |
| 6 | kimi_signal_tracking | Verify enforcement | Composite pair block already active | `alpha_engine/strategy_blocklist.py` |
| 7 | volume_spike_breakout | Verify enforcement | Honest kill switch KILLED + composite pair | `alpha_engine/data/honest_kill_switch.json` |
| 8 | ema_momentum_m006 | Add to watchlist, reduce sizing | Tribunal monitor | `tools/strategy_kill_tribunal.py` |
| 9 | crypto-momentum-scout | Verify enforcement | Kill_list composite pair | `alpha_engine/data/core_whitelist.json` |
| 10 | unknown | Verify enforcement | Kill_list entry | `alpha_engine/data/core_whitelist.json` |
| 11 | forward_signals | Investigate silence, restart | pipeline_health_monitor staleness | `alpha_engine/pipeline_health_monitor.py` |
| 12 | orphan_emitter_bond | Investigate silence, restart | pipeline_health_monitor staleness | `alpha_engine/pipeline_health_monitor.py` |
| 13 | bond_scanner | Investigate silence, restart | pipeline_health_monitor staleness | `alpha_engine/pipeline_health_monitor.py` |
| 14 | orphan_emitter_etf | Investigate silence, restart | pipeline_health_monitor staleness | `alpha_engine/pipeline_health_monitor.py` |
| 15 | growth_stock_screener | Investigate silence, restart | pipeline_health_monitor staleness | `alpha_engine/pipeline_health_monitor.py` |

---

## 4. Documentation Path

Findings documented at:
`updates/2026-11-16-gha-strategy-kill-tribunal.md`
