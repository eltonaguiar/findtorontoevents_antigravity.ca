# Supreme Edge Enhancement — Master Plan Review (2026-05-13)

**Reviewing:** [updates/2026-05-11-money-maker-master-plan.html](updates/2026-05-11-money-maker-master-plan.html) (synthesis of 5 agent plans + peer chatlog, generated 2026-05-11)
**Reviewer:** Opus 4.7 (1M ctx), this session
**Goal:** track delta between the plan and current state; flag what's done, what's invalidated by recent findings, what's still binding.

## Status of each plan item — per asset class

### COMMODITY (plan said STABLE_EDGE)
| Plan item | Status today | Notes |
|---|---|---|
| P0 Verify `multi_asset_cot` PF=19.19 via DB query | **SHIPPED** in PR #913 (multi_asset_cot forensic verifier) — verdict pending DB run | The plan's PF=19.19 was correctly flagged "implausible"; verifier added but no run output cited yet |
| P0 Disclose CT=F / KC=F symbol concentration | **PARTIALLY SHIPPED** | PR #940 adds `symbols_allowed` + `symbols_filtered_out` provenance fields to walkforward.by_class.COMMODITY |
| P1 Add COMMODITY to `walkforward_validator.py` output path | **SHIPPED today (PR #940)** | The plan's exact request. Now populated at `min_trades=20`, post-filter universe HG=F + PL=F. Live entry expected on next dashboard refresh. |
| P1 Wire real CFTC COT data to validate cot_positioning_CT_locked 89.8% WR | **REOPENED — TIMING LEAKAGE FOUND** (PR #941) | The 89.8% WR figure is **likely overstated** per [reports/cot_timing_leakage_audit_2026-05-13.md](reports/cot_timing_leakage_audit_2026-05-13.md). DeepSeek estimates corrected WR ~45-55%. The plan's validation request must now include the 3-day publication-lag patch BEFORE re-running |
| P2 Add term-structure / inventory / seasonality | unchanged P2 | Not touched this session |

**Plan invalidation:** the COMMODITY "STABLE_EDGE" verdict at PF 3.92 may not survive the COT lag patch. The plan's promotion gate ("PF≥1.5 / WR≥50 / MDD≤20 for 2 consecutive weekly snapshots") needs a re-run on lag-corrected data. **The MERGED PR #940 walk-forward gives the platform the right surface to do this re-run; PR #941 supplies the correct data.**

### EQUITY (plan said STABLE_EDGE, the broadest candidate)
| Plan item | Status |
|---|---|
| P0 Reconcile `claude_gainer_st` winner-vs-blacklist contradiction | **SHIPPED PR #910** |
| P0 Verify capped-vs-raw PnL gap | **SHIPPED PR #914** (docs) |
| P1 Bottom-symbol pruning + HC parity | not touched this session |
| P1 Add earnings-drift + sector-RS + breadth features | not touched |

**Status:** EQUITY confirmed Tier 2 — PF 1.55 / WR 53.2% / n=447 (live `asset_class_health`). The plan's "strongest broad candidate" framing holds.

### CRYPTO (plan said DECAYING_EDGE)
| Plan item | Status |
|---|---|
| P0 Blacklist `kimi_signal_tracking` | **SHIPPED PR #907** |
| P0 `crypto_soc_*` quarantine | **SHIPPED PR #908** |
| P0 Cap `quan_engine` to 12% CRYPTO volume | **SHIPPED PR #906** |
| P1 Promote `st_fear_greed_contrarian` to HC gating | not touched |
| P1 Wire decay-replacement pipeline | not touched |
| Cloud-agent: confidence-inversion gate (+56 lines uncommitted) | **PENDING — flagged for independent reproduction** before any merge per [reports/cloud_agent_claims_validation_2026-05-12.md](reports/cloud_agent_claims_validation_2026-05-12.md). Same audit produced the falsified "41 dormant strategies" claim. |

**Net:** the plan's P0 cluster is shipped. The decay-replacement pipeline + the confidence-inversion gate are the two open bets.

### FOREX (plan said DECAYING_EDGE, mutate-before-kill)
| Plan item | Status |
|---|---|
| P0 Hard-cap FOREX sizing at 0 until PF≥0.8 | **SHIPPED PR #909** — verified `sizing_allowed=false` in current payload |
| P0 PR #876 pnl_pct anomaly clamp | **MERGED** 2026-05-11 |
| P1 Spawn FOREX deep-dive subagent | **SHIPPED today** (commit `5e37cd3999`, [reports/deep_dive_forex_2026-05-12.md](reports/deep_dive_forex_2026-05-12.md)) — covers per-source autopsy, three-axis mutation decisions, external replication options, 30/60/90-day rescue plan |
| P1 Wire COT / DXY-beta / carry-rate features | not yet started |
| P2 Rebuild FOREX from scratch | not started (Month-2 work per plan) |

### ETF (plan said INSUFFICIENT_DATA, at n floor)
| Plan item | Status |
|---|---|
| P1 Expand ETF universe (XLF, XLE, XLK) to reach n=120-180 | partial — ETF is **now n=107**, just past the charter floor; needs continued growth |
| P1 Block leveraged ETFs | not touched |
| P2 Sector-theme + AUM + expense-ratio filters | not touched |

**Status:** ETF crossed the n≥100 charter floor. Plan's promotion gate (n≥100 AND PF≥1.5 AND consistency≥80%) is now data-feasible. PF is at 1.34 — short of T2 by 0.16.

### BOND (plan said INSUFFICIENT_DATA, n=11-18)
| Plan item | Status |
|---|---|
| P1 Add BOND to walkforward_validator output path | **NOT YET** — same single-file pattern as PR #940 but for BOND |
| P2 Expand BOND universe + add duration / risk filters | not touched |
| Plus this session: BOND_ELITE_FLOOR 40→32 set as GitHub variable | live |

**Status:** the plan's BOND framing assumed legacy `futures_momentum` on ZN=F WAS bond_*. My session's forensic ([reports/commodity_bond_forensic_2026-05-13.md](reports/commodity_bond_forensic_2026-05-13.md)) confirmed those 21 BOND rows are mis-classified legacy futures, not real bond_* picks. Zero genuine `bond_*` closed picks yet. `BOND_ELITE_FLOOR=32` unblocks Layer 1 of the curation gate; Layer 2 (forward-gate override) and Layer 3 (active_picks merge) still open as P0 follow-ups.

### FUTURES (plan said INSUFFICIENT_DATA)
No movement this session.

## Plan items NOT in the plan that the multi-model review surfaced

The supreme plan covered per-class edges but didn't flag the binding infrastructure constraints. External-model consensus this session (DeepSeek + Loker + GPT-OSS) added five P0.5 items:

1. **Explicit `alpha_engine/position_sizer.py`** with vol-targeting + max-allocation-per-name — currently `sizing_allowed=true` flags are meaningless without this
2. **Slippage + execution cost model** wired into PF/Sharpe — without it backtest numbers are fantasy
3. **Live-vs-backtest drift circuit-breaker** auto-flipping `sizing_allowed=false` on rolling-WR breach (CRYPTO −31.12pp gap is currently visible but not acted on)
4. **Concentration controls** — COMMODITY = 100% HG=F today
5. **Portfolio-level MDD limit** per Charter §7

These were not in any of the 5 plans that fed the supreme plan synthesis. **They are now the binding constraints for any "money-ready" claim**, ahead of further strategy edge work.

## Plan items now invalidated or in question

| Plan claim | Status |
|---|---|
| `cot_positioning_CT_locked` 89.8% WR | **LIKELY OVERSTATED** — COT timing-leakage confirmed at 98% (PR #941). DeepSeek estimates corrected WR ~45-55% |
| COMMODITY "STABLE_EDGE" PF 3.61-3.92 | **PROVISIONAL** until lag-corrected re-run on full 100-pick history |
| BOND legacy 21 rows = bond signal data | **REJECTED** — these are mis-classified `futures_momentum` on ZN=F |
| `multi_asset_cot` PF=19.19 | **STILL UNVERIFIED** — PR #913 forensic verifier shipped but DB run output not surfaced |

## Net-new action items the supreme plan should incorporate

1. **COT timing-leakage acceptance gate** — paper-pilot graduation 2026-05-23 now requires lag-corrected WR ≥ 75% on full 100-pick history (PR #941 prerequisite)
2. **BOND Layer 2/3 fix cluster** — `FORWARD_GATE_OVERRIDES[bond]=10` + merge `bond_picks.json` → `active_picks.json` for live sizing
3. **Five P0.5 infrastructure items** above — these gate every other class's promotion to live capital, not just CRYPTO/FOREX
4. **External-model second-opinion as standard procedure** — when internal swarms converge, query 2-3 external models in parallel; catches consensus risk; cost trivial (~$0.02/round for DeepSeek)

## Recommendation for the next supreme plan refresh

Generate a **v2 plan dated 2026-05-13** that:
1. Promotes the 5 P0.5 infra items above to TOP priority
2. Adds the lag-corrected COT acceptance gate as the CT=F graduation prerequisite
3. Marks the original P0 cluster (PRs #905-914 + #940 + #941 + BOND var) as SHIPPED
4. Re-runs the edge-stability sidecar AFTER the COT lag patch lands to get post-correction COMMODITY numbers
5. Sets the explicit go-live order: infra (P0.5) → COT-corrected COMMODITY paper-pilot → EQUITY second-class to T2 lineup → ETF as third slot if PF clears 1.5

The 5-plan synthesis methodology is sound but missed infrastructure gating. Next refresh should consult external models in the same way this session did.
