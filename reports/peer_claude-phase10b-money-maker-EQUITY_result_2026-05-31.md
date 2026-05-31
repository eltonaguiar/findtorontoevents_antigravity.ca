# /money-maker-readyv2 — EQUITY

**Snapshot:** 2026-05-31 06:30Z · live `ejaguiar1_stocks.trading_picks` · categories `equity | stock | stocks`

## Class verdict at 06:30Z 2026-05-31

| View | n | WR | PF | avg pnl_pct | Sharpe-proxy | T2 (PF>1.5 / WR>50 / MDD<20 / n≥100) |
|---|---|---|---|---|---|---|
| Naive (status IN WON/LOST only) | 121 | 13.22% | **0.090** | −3.049 | −6.10 | **FAIL** (every axis) |
| Unified, all closed | 1,764 | 4.42% | 0.595 | −0.093 | — | **FAIL** (resolver-zero contamination) |
| Unified, excl pnl=0 (signal only) | **187** | **41.71%** | **0.595** | −0.877 | — | **FAIL** on PF/WR/avg |
| 14d window (closed, all statuses) | 66 | 24.2% | 0.225 | — | — | FAIL — getting worse, not better |

**T2-status:** FAIL on (PF, WR, MDD, edge direction). Class is bleeding under all three measurement frames.

Note: CLAUDE.md baseline (`pf_registry.by_asset_class_policy_clean_net` 2026-05-25) reports EQUITY PF 0.90 / WR 33% / n=33. That is the **policy-clean cohort** (after BLOCKED_SOURCE_SYSTEMS + dedup + concentration trim). The live raw DB above shows the un-filtered emission is materially worse — meaning the block-list is doing real work, but what remains in production is still sub-T2.

## Best candidate

`stocks_rsi2_pullback` (the `strategy` field — `source_system` for these rows is mixed `alpha_engine` / `multi_asset_copytrader` etc.):

- **n=78  WR=44.9%  PF=1.11  avg=+0.0 (slight positive expectancy)** (unified, excl pnl=0)
- Matches Phase 3 MC watchlist: **P(T2 at n=100) = 52%, P(T1) = 14%**.
- **CRITICAL CONTRADICTION:** This strategy was added to `BLOCKED_SOURCE_SYSTEMS` in `alpha_engine/config.py:270` on 2026-05-28 citing *"10 EQUITY trades, WR 30%, PF 0.032 — catastrophically bad"*. The data has since grown 7.8× and the picture inverted (44.9% WR, PF 1.11, MC-positive). The kill was based on a tiny pre-protected-cadence sample and should be reversed — see Action #1.

Other notable per-`strategy` cuts (unified, excl pnl=0):

| strategy | n | WR | PF | verdict |
|---|---|---|---|---|
| stocks_rsi2_pullback | 78 | 44.9% | **1.11** | UNBLOCK + watchlist |
| regime_mild_bull | 6 | 66.7% | 1.39 | tiny-n watchlist |
| regime_accumulation | 14 | 57.1% | 0.70 | tiny-n, edge in WR not PF |
| regime_mild_bear | 25 | 24.0% | 0.09 | KILL — broken regime gate |
| regime_strong_bear | 11 | 0.0% | 0.00 | KILL — no shorts working |
| smart_money_accumulation | 9 | 33.3% | 0.07 | KILL — failing badly |

By `source_system` (the production routing field):

| source_system | n | WR | PF | verdict |
|---|---|---|---|---|
| multi_asset_copytrader | 76 | 43.4% | 0.91 | borderline — copy-trader basket has signal but doesn't clear T2 |
| alpha_engine | 35 | 45.7% | 0.76 | borderline |
| regime_terminal | 44 | 31.8% | 0.49 | drag — regime gate not adding value |
| alpha_engine_fast | 16 | 56.2% | 0.24 | high WR / low PF → SL too tight, asymmetric R:R bad |
| ml_strategy_reviver | 1 | 0% | 0 (−72%) | KILL — single-trade catastrophe, do not size |

## T2 gap

- **n needed:** 100 − 78 = **22 more clean closures of `stocks_rsi2_pullback`**.
- **Current cadence:** EQUITY closes ≈ 4.7/day over 14d, of which the rsi2 share ≈ 1.5/day (rough estimate from 78 closures over ~52 days post-revival). At 1.5/day, **time-to-n=100 ≈ 15 days**.
- **Bottleneck:** the strategy is on `BLOCKED_SOURCE_SYSTEMS` (config.py:270) and in the smart-picks blocklist (`smart_picks_engine.py:492, 536`). It is currently **emitting only via legacy copy-trader / alpha_engine paths that haven't picked up the block** — once those callers sync the block-list, emission collapses to zero.
- **At current PF/WR trajectory** (44.9% WR / PF 1.11 / avg expectancy ≈ 0): if cadence is protected, the MC P(T2 at n=100) = 52% is achievable. If we let the block stay, the strategy is killed pre-T2.

## Actions ranked by impact

### 1. UNBLOCK `stocks_rsi2_pullback` (single highest-impact change for EQUITY) — **HIGH IMPACT, LOW RISK**
- Remove the entry at `alpha_engine/config.py:270` (`'stocks_rsi2_pullback',  # 10 EQUITY trades, WR 30%, PF 0.032`).
- Remove from `smart_picks_engine.py:492` blocklist and re-allow the source pattern at `:536`.
- Justification: the original kill was based on n=10 (pre-cadence-protection). Live n=78 shows WR=44.9% / PF=1.11 — matches MC P(T2)=52% candidate from Phase 3 (PR #179). This is the *only* EQUITY strategy with both edge AND data depth approaching T2.
- **Add to a new `PROBATION_WATCHLIST` config block** (does not exist yet — propose adding to `alpha_engine/config.py` near line 280) with a `min_protected_n = 120` floor so future block proposals require ≥120 closures before re-considering kill.

### 2. KILL the broken regime-shorts: `regime_strong_bear`, `regime_mild_bear`, `smart_money_accumulation` — **MEDIUM IMPACT**
- Add to `BLOCKED_SOURCE_SYSTEMS` at config.py:262-280 with kill rationale: regime_strong_bear n=11 WR 0% PF 0; regime_mild_bear n=25 WR 24% PF 0.09; smart_money_accumulation n=9 WR 33% PF 0.07.
- These are dragging the class-level PF from a possible ~0.95 down to 0.60.
- Mutation-three-axis (`docs/MUTATION_THREE_AXIS_PROTOCOL.md`) decision: **vol-floor mutation fails** (already at tight vol); **regime-gate mutation fails** (these *are* regime gates and they're wrong); **source-confluence mutation N/A** (single-source). → KILL is the correct axis.

### 3. MUTATE `alpha_engine_fast` SL — **MEDIUM IMPACT**
- WR=56.2% but PF=0.24 means SL is way too tight relative to TP. R:R asymmetry is killing a strategy with positive base-rate.
- Three-axis decision: **SL-axis mutation** (loosen by 1.5× ATR-equivalent). File: `alpha_engine/non_crypto_boosters.py` — search for `alpha_engine_fast` SL config. Stage as A/B on next 30 closures before full rollout.

### 4. FIX the `TIME_EXIT` resolver writing pnl_pct=0 — **HIGH SYSTEMIC IMPACT (Phase 4 finding)**
- EQUITY has **1,576 rows with status=TIME_EXIT and pnl_pct=0**. Phase 4 (PR #180-181) flagged the resolver for writing past-TP without intrabar verification; the EQUITY-side symptom is `TIME_EXIT` defaulting to 0 instead of mark-to-market close.
- Impact: with these rows treated as 0-pnl wins+losses, naïve dashboards see WR=4.4% — *catastrophically misleading*. The unified-excl-zero view (the truth) shows WR=41.7%.
- Action: open follow-up issue to the Phase 4 PR — extend the intrabar verifier to write the mark-to-market exit price (or `EXPIRED` if data unavailable) for TIME_EXIT EQUITY rows. Targets: `alpha_engine/outcome_resolver.py` (the file referenced in CLAUDE.md as the resolver-fix landing zone).

### 5. ADD `regime_accumulation` to WATCHLIST — **LOW IMPACT, OPTION VALUE**
- n=14 WR=57.1% PF=0.70 — too small to graduate, but the WR signal is strong enough to protect emission and re-check at n=50.

### 6. ADD Phase 9 candidate #6: 200-day MA trend strategy — **MEDIUM IMPACT, NEW EDGE**
- PR #190 ranked this as next-session candidate. EQUITY is the natural home (vs CRYPTO/FOREX which already have CTA momentum coverage).
- Concrete file to create: `alpha_engine/new_strategies/equity_sma200_trend.py`. Wire into `production_scanner.py` per CLAUDE.md Wire-Up Rule. Allowlist `equity_sma200_trend` in `smart_picks_engine.py` allowlist (line ~492).

## Watchlist (protected emission cadence to n=100)

| strategy | n | needed to n=100 | protect for | reason |
|---|---|---|---|---|
| stocks_rsi2_pullback | 78 | 22 | ≥15 days post-unblock | MC P(T2)=52% confirmed live |
| regime_accumulation | 14 | 86 | ≥60 days | WR=57% signal, needs depth |
| multi_asset_copytrader (EQUITY slice) | 76 | 24 | ≥30 days | PF 0.91 borderline |

## Risk factors / blockers

1. **Resolver bug (Phase 4)** — TIME_EXIT zero-pnl contamination on **1,576 of 1,764** EQUITY closed rows (89% of dataset). The naïve verdict (PF 0.09 / WR 13%) is what gets published to dashboards if filters are off; the truthful verdict (PF 0.60 / WR 42%) requires `pnl_pct != 0`. Until Action #4 lands, **every EQUITY dashboard reading is suspect**.
2. **Block-list stale-sample risk** — `stocks_rsi2_pullback` was killed at n=10. Adding the proposed `PROBATION_WATCHLIST` n≥120 floor (Action #1) is the structural fix to prevent the same pattern on EQUITY's future candidates.
3. **Category mis-tagging** — Did not find systematic mistag in EQUITY (the union `equity | stock | stocks` covered the dataset; no `etf` rows leaked in based on source_system distribution).
4. **NULL pnl_pct in closed rows** — only 9 EQUITY rows (Phase 6+8 backfill cleaned most). Low risk.
5. **Stale pf_registry vs live** — registry (2026-05-25) shows n=33 for EQUITY policy-clean; live shows n=187 signal-bearing closures. Registry is 6 days stale and missing the rsi2_pullback re-emergence. Action: re-run `tools/backfill_trust_score.py` (already modified per git status) and rebuild pf_registry policy-clean cohort.

## What I would ship next (concrete PRs)

### PR A — `fix(equity): unblock stocks_rsi2_pullback + add PROBATION_WATCHLIST floor`
- Files: `alpha_engine/config.py`, `alpha_engine/smart_picks_engine.py`, `reports/peer_claude-phase10b-money-maker-EQUITY_result_2026-05-31.md` (cite this report).
- Diff:
  - `config.py:270` — delete `'stocks_rsi2_pullback'` entry; add a `PROBATION_WATCHLIST = {'stocks_rsi2_pullback': {'n_protect': 100, 'rationale': 'MC P(T2)=52%, peer_claude-phase10b 2026-05-31'}}` block.
  - `smart_picks_engine.py:492` — re-allowlist; `:536` — remove from blocklist set.
- Expected impact: EQUITY class PF moves from 0.60 → ~0.80 within 15 days as rsi2_pullback emissions resume; n=100 hit ≈ 2026-06-15; if MC holds, EQUITY becomes first T2-pass class.

### PR B — `fix(resolver): EQUITY TIME_EXIT mark-to-market instead of zero pnl`
- Files: `alpha_engine/outcome_resolver.py`.
- Diff: when `status='TIME_EXIT'` for EQUITY, fetch close price at `exit_time` from `tools/db_env.py` price source; compute `pnl_pct` from entry; mark `tp_fill_method='time_exit_mtm'`. If price source unavailable, downgrade to `status='EXPIRED'` rather than write 0.
- Expected impact: removes 1,576-row zero-pnl contamination; class dashboards stop reporting misleading PF=0.09.

### PR C (optional) — `feat(equity): add equity_sma200_trend strategy (Phase 9 #6)`
- New file `alpha_engine/new_strategies/equity_sma200_trend.py`; wire into `production_scanner.py`; allowlist; ship with explicit Wire-Up section per CLAUDE.md.

---

**One-line class verdict:** EQUITY is FAIL on T2 across every axis (PF 0.60 / WR 42% / negative expectancy after resolver-zero filter), but has one MC-positive candidate (`stocks_rsi2_pullback` n=78 PF 1.11) being suppressed by a stale n=10 kill — unblocking it is the single highest-impact PR for this class.
