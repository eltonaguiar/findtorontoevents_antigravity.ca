# SUPREME EDGE — Next Steps Plan + Current State Evaluation

**Generated:** 2026-05-12 02:10Z
**Session HEAD:** `613c65cb5ef` (main)
**Branch:** main

## Current state snapshot

### Real-money state machine per Codex governance (current)

| Class | State | DSR-verified edges | Master plan gate to advance |
|---|---|---|---|
| **COMMODITY** | REHAB | `cot_positioning` n=104, WR 86.5%, DSR=1.0000 | Walk-forward.by_class fold count >0 + concentration disclosure (CT=F/KC=F) |
| **EQUITY** | REHAB | `stocks_rsi2_pullback` n=70, WR 62.9% (P0 #10) | n→100 + capped-MDD verified + `claude_gainer_st` enforcement test |
| **CRYPTO** | BLOCKED | 4 ml_enhanced sleeves (INJUSDT/FETUSDT/DYDXUSDT/RENDERUSDT) DSR≥0.9995 | All 3 P0 quarantines shipped ✓; post-quarantine forward window PF≥1.5 (need 7d data) |
| **FOREX** | BLOCKED | ZERO (anti-overfit ZERO EDGE_LIKELY_REAL) | Resolver bug fix + COT/DXY/carry/news features + ≥1 quarter clean data |
| **ETF** | REHAB | None yet (n at floor) | n≥100 sample; THIN_REHAB verdict shipped to HC panel |
| **BOND** | BLOCKED | None (n=18) | n≥100 multi-month accumulation |
| **FUTURES** | BLOCKED | None | re-emission plan OR formal retire from /audit |
| **INDEX_STOCK** | REHAB-scaffold | None (n=0) | Investigate writer; remove if zero generator path |

**Current LIVE_ELIGIBLE: 0 / 6.** Earliest target: week 8 of remediation.

### Production code shipped this session (20+ commits)

| Layer | Commits |
|---|---|
| Truth layer | `81bd0b86388` Wave 1 unfreeze (40d HALT removed); `4a2d337a5dc` blacklist + crypto_soc quarantine + elite-score floors raised; `1c535a19105` capped-MDD; `a64e80e70d1` CI fix (3 FOREX toxic re-blocked); `956a30b801c` HC verdicts refresh + decay-block (futures_momentum, MeanReversionBB) |
| Anti-overfit | `3e388035b8c` sidecar + JSON; `0f3ac2fa8be` hourly cron; `47d396c31f7` `/audit/anti_overfit.html` viewer + nav pill `2896aa19228` |
| Calibration | `06cf04b8eb2` audit tool; `e1981c571d7` `_normalize_confidence` helper; `613c65cb5ef` migrated all 9 callsites |
| Day-of-week gate | `bde7dde2fe0` opt-in env-flag for CRYPTO {Mon, Wed} + MEMECOIN {Sat} |
| Documentation | `2aa813998a0` ?Guide SUPREME EDGE refresh + Decay Alerts + HC audit + DB Health remediation tables in master plan |
| PR merges | #876 FOREX clamp + #884 mysql_sync category + #878 short BULL gate + #891 closed_at fallback |

### Statistically validated edges (Lopez de Prado AFML DSR ≥ 0.95)

8 of 42 strategies survive DSR test:

| Strategy | Class | n | WR | Sharpe | DSR |
|---|---|---|---|---|---|
| `cot_positioning` | COMMODITY | 104 | 86.5% | +1.377 | **1.0000** |
| `ml_enhanced_INJUSDT_1d_B_lightgbm` | CRYPTO | 27 | 100% | +2.490 | 1.0000 |
| `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` | CRYPTO | 31 | 96.8% | +1.828 | 1.0000 |
| `ml_enhanced_FETUSDT_1d_B_lightgbm` | CRYPTO | 25 | 100% | +1.371 | 1.0000 |
| `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` | CRYPTO | 34 | 85.3% | +0.514 | 0.9995 |

Plus 3 more EDGE_LIKELY_REAL. **33 of 42 audited strategies REJECTED as OVERFIT_LIKELY** — mostly `ml_enhanced_*_15m_*` family.

## "Easiest path to real money" — analysis per asset class

### Tier 1 candidates (lowest friction to LIVE_ELIGIBLE)

**COMMODITY via `cot_positioning` carve-out**
- Already DSR-verified. Single-strategy real edge.
- Friction: 96.7% OPEN-bloat in `trading_picks` (resolver lag). Wave 1.5 needed.
- Path to live: (a) Wave 1.5 ships resolver fix → (b) 7d clean OPEN-bloat → (c) `cot_positioning` ships ~30 closed picks/wk → (d) accumulate n≥150 (5 weeks) → (e) shadow 14d → LIVE.
- **Estimated time to real money: 7-9 weeks at 1% per trade.**
- Expected lift: WR 86.5% × avg trade (need full PnL/trade reconcile).

**EQUITY via `stocks_rsi2_pullback`**
- n=70 / WR 62.9% / +0.78% avg already in DB.
- Path to live: (a) verify ML calibration fix doesn't perturb scoring → (b) ship n→100 → (c) shadow 14d → LIVE.
- **Estimated time: 5-7 weeks at 0.5% per trade.**
- Expected lift: +0.78% avg × n=30-40 picks/month = +20-30% monthly base before sizing.

**ETF — wait for sample**
- PF 1.20 / n=88-100. Below master plan n≥100 charter.
- Path to live: emit 3-week universe expansion (XLF/XLE/XLK) → n→150 → shadow.
- **Estimated time: 8-10 weeks.**

### Tier 2 — needs more work

**CRYPTO sleeves** — 4 DSR-real strategies named, but class drag still real (kimi_signal_tracking blacklisted but baby_strats partial quarantine). Sleeve-level promotion is possible if class-aggregate is decoupled from sleeve-level decisions.

**BOND** — n=18; multi-month accumulation needed.

### Tier 3 — defer / retire

**FOREX** — zero DSR-survivors; resolver bug fix + ≥1 quarter clean data required.
**FUTURES** — silent-dead; re-emission plan needed.
**INDEX_STOCK** — n=0; investigate or remove.

## Action items grouped (4 buckets)

### Bucket A — Truth layer cleanup (P0 blocking for any real-money promotion)
1. Wave 1.5a `lm_signals` expire-cron exit_price=0 fix (F10, ~30 min, PHP side)
2. Wave 1.5b `at_discord_notifications.signal_tier` writer fix (F8, ~30 min)
3. Wave 1.5c `at_consensus_picks` time-travel guard (F4, ~20 min)
4. Ghost Rows 655k investigation — identify writer + bulk DELETE or read-time filter (~2h)
5. `hf_stats` refresh trigger workflow_dispatch (~1 min)
6. Confidence schema writer fix — locate the source of 0-10 scale leakage (~1h)

### Bucket B — DSR / overfit / validation framework (P1)
1. `anti_overfit_audit.json` consume in dashboard_generator → surface DSR per strategy card on /audit
2. CPCV upgrade in `p3_backtest_runner.py` (peer high-priority)
3. v3b LLM-driven signal translator (peer high-priority — flips NO_EDGE → MIXED/GO)
4. Re-fire P5 swarms with v3a numbers (~$0.35)
5. Wire DSR threshold (≥0.95) into HC filter gate
6. WFE validator + auto-retirement framework

### Bucket C — Decay & risk (P1)
1. `DECAY_ALERT_REDUCE` soft-demote framework (9 P1 decay alerts not yet hard-blocked)
2. Investigate `hs_lb_None` (0% WR — parsing bug suspected)
3. PR #885 ConcentrationChecker production wire-up (currently orphan)
4. FRED macro filter wire-up (`FRED_API_KEY` to secrets)
5. Drift-pause auto-flip dry-run (peer Phase 4.1)
6. Per-class regime filter (PR #902 fix CI failures first)

### Bucket D — Dashboard / UX / governance (P2)
1. Wire `readiness.by_class` payload (Codex state-machine fields)
2. PR #846 conflict resolve (Shadow Probation panel)
3. PR #904 conflict resolve (peer's research orchestrator + edge stability sidecar)
4. `last_signal_date` field in `systems` payload
5. Reconcile `/audit` threshold text with `docs/PERFORMANCE_CHARTER.md` v1.0
6. Top-N portfolio Monte Carlo simulator (Phase 5 Wave 3 — settles concentration debate)

## Key insights from session work

1. **Data trust > alpha hunt.** 5/6 DB Health red-tier metrics are forward-fixable; ghost rows (655k) is the remaining hard one. Until truth layer green, no class verdict is verdict-grade.

2. **DSR is the most discriminating gate.** 33 of 42 audited strategies fail DSR ≥ 0.95. The 9 that pass are mostly 1d/1h timeframe (NOT 15m).

3. **15-minute timeframe is overfit-bait.** Multiple `ml_enhanced_*_15m_*` variants pass raw WR/PF gates but fail multiple-testing correction. Adopt as system-wide anti-pattern.

4. **Confidence is anti-signal system-wide.** Verified P0 #9: conf≥0.9 bucket WR 14.4% vs <0.5 bucket 60.3%. ML calibration broken across all classes, not just ETF/CRYPTO. Confidence schema mixed-scale (0-1 + 0-10) adds noise.

5. **FOREX class is genuinely sub-floor.** PF 0.27-0.57 across multiple reads. Zero DSR-survivors. The /audit `EDGE 65.8% N=73` claim was a small-sample artifact.

6. **COT is the strongest single edge.** `cot_positioning` n=104, WR 86.5%, DSR=1.0. Antigravity confirmed via independent path (`cot_positioning_CT_locked` 89.8% WR). **First real-money candidate.**

7. **Kimi hallucinated 7 EQUITY strategy names** (Cursor Genius, Blue Chip Growth, Alpha Factor Composite, etc.). Zero exist in DB. Always cross-check named recommendations against DB.

8. **OPEN-bloat masks edge.** cot_positioning shows 3886 rows in trading_picks; only 104 closed (96.7% OPEN). The 86.5% WR is on a small subset. Wave 1.5 fixes will surface real closed-cohort over next 4 weeks.

## Recommended next 5 commits (sequential or parallel-safe)

1. **Bucket A #5** — trigger `gh workflow run audit-dashboard.yml --ref main` to refresh `hf_stats` (19d stale)
2. **Bucket B #1** — `dashboard_generator` consumes `anti_overfit_audit.json`, adds `dsr_verdict` field per strategy card
3. **Bucket A #4** — Ghost Rows investigation (smaller-scoped probe)
4. **Bucket C #1** — `DECAY_ALERT_REDUCE` framework (soft-demote 9 unblocked alerts)
5. **Bucket D #4** — `last_signal_date` in `systems` payload (closes earlier P1)
