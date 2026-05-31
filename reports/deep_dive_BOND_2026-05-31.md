# Deep Dive — BOND (2026-05-31)

Status: **FAIL / INSUFFICIENT_DATA** (per CLAUDE.md Goal #1: 0/6 classes pass T2; BOND is among the worst — zero wins on every closed pick to date).

Canonical sources for this report:
- `audit_dashboard/data/pf_registry.json` (`by_asset_class`, `by_asset_class_strategy_symbol`, `by_asset_class_strategy_date`, generated 2026-05-30/31)
- `audit_dashboard/data/money_ready_verdict.json` (generated 2026-05-30T23:05Z)
- `audit_dashboard/data/pick_summary_stats_{2w,48h}.json` (BOND bucket null in both windows)
- `audit_dashboard/data/dashboard_data.json` (empty `{}` in this worktree snapshot; not authoritative — pf_registry + money_ready_verdict are.)
- CLAUDE.md banner snapshot (2026-05-30): "BOND INSUFF-N (PF 0 / WR 0% / n=8)"

A worktree-local snapshot of `dashboard_data.json` shows `{}` — the live `/audit` page reads the generated file from the deploy pipeline. Numbers below come straight from `pf_registry` and `money_ready_verdict`, which are the verdict-grade feeds.

## Current State (n, WR, PF, MDD, expectancy, recency)

From `pf_registry.json` (raw + policy-clean-net both empty/zero for BOND):

| Metric | Value | Source |
|---|---|---|
| n (raw closed) | **2** | `by_asset_class[BOND]` |
| wins / losses | 0 / 2 | `by_asset_class[BOND]` |
| WR | **0.0%** | `by_asset_class[BOND].win_rate_pct` |
| PF | **0.0** | `gross_profit=0 / gross_loss=0.013955` |
| Gross loss | 0.013955 (1.40 pp cumulative on 2 trades) | `by_asset_class[BOND]` |
| Total PnL pct | **−1.40 pp cumulative (−0.013955)** | `by_asset_class[BOND]` |
| Avg loss per losing trade | ~0.70 pp | computed |
| Expectancy | **null** (n too small for money-ready harness) | `money_ready_verdict.classes.BOND.expectancy` |
| MDD | null (no return series ≥ floor) | `money_ready_verdict.classes.BOND.mdd` |
| CVaR-95 | null | `money_ready_verdict.classes.BOND.cvar_95` |
| DSR | null ("n=0 too small for DSR") | `money_ready_verdict.classes.BOND.details.dsr` |
| PBO / SPA | null (need ≥2 strategies with n≥20; we have 1 with n=2) | `money_ready_verdict.classes.BOND.details.pbo/spa` |
| `_mdd_gate_enforce` | true (gate is on; we just have no data) | `money_ready_verdict.classes.BOND` |
| Verdict | **INSUFFICIENT_DATA** | `money_ready_verdict.classes.BOND.verdict` |
| data_source | `backfill_no_data` | money_ready_verdict |
| Recency (2w window) | **`by_class.BOND = null`** — no closed BOND picks in last 14 days | `pick_summary_stats_2w.json` |
| Recency (48h window) | **`by_class.BOND = null`** — no closed BOND picks in last 48h | `pick_summary_stats_48h.json` |

CLAUDE.md banner cited n=8; pf_registry as-of 2026-05-30/31 shows n=2 raw / 0 policy-clean. The most likely reconciliation: 6 of the 8 picks have been excluded by the policy-clean filter (gate flips, stale-data, or pre-M-067 cohort), leaving 2 raw + 0 in the audit-grade view. Either way, **n is sub-statistical and every closed BOND pick has lost money.**

Reconciliation issue is flagged in the Risk Register.

## Per-Source Autopsy (top 5 sources by volume; WR/PF each)

`pf_registry` does not surface a per-source breakdown for BOND because `by_asset_class_policy_clean_net[BOND]` is empty (no rows survive the policy-clean filter). The only data we have is at the strategy×symbol level:

| Source / Strategy | Symbol | n | W | L | WR | PF | PnL pp |
|---|---|---|---|---|---|---|---|
| `bond_scanner` | TLT | 1 | 0 | 1 | 0% | 0.0 | −0.84 |
| `bond_scanner` | IEF | 1 | 0 | 1 | 0% | 0.0 | −0.56 |
| (no other BOND strategies present) | — | — | — | — | — | — | — |

Per-date (last closed date for BOND was 2026-05-25):

| Trade date | n | W | L | WR | PF | PnL pp |
|---|---|---|---|---|---|---|
| 2026-05-25 | 2 | 0 | 2 | 0% | 0.0 | −1.40 |

Effectively: **`bond_scanner` is the only BOND source, and it is 0-for-2 on TLT + IEF.** There is no top-5 to autopsy — there is one strategy, one closed batch, and zero wins.

## Strategy Breakdown (per-strategy WR/PF/single_source_pct; flag concentration)

| Strategy | n | WR | PF | single_source_pct | Concentration flag |
|---|---|---|---|---|---|
| `bond_scanner` | 2 | 0% | 0.0 | **100%** (all BOND closed-picks come from one scanner) | **CONCENTRATION = 100% — HHI = 1.0** |

CLAUDE.md feedback (`feedback-concentration-strategy-not-engine.md`): concentration is measured at the strategy level. BOND has **HHI = 1.0** (single-strategy monopoly). The threshold cited in the project banner (HHI > 0.30) is exceeded by a factor of 3.3×.

By symbol within `bond_scanner`: TLT 50%, IEF 50% — internally split, but the universe is exclusively long-duration Treasury ETFs. No corp / muni / TIPS / floater / short-duration / international diversification. This is **single-axis-rate-bet concentration** in addition to single-strategy concentration.

## What Is Failing (root causes — name strategies, sources, patterns)

1. **`bond_scanner` is single-strategy, single-factor (duration), and 0% WR on its only closed batch.** No alternative source has ever produced a closed BOND pick — no AI tournament BOND models, no Hyrotrader BOND component, no curated `regime_terminal` BOND output. The class is structurally orphaned.
2. **Universe collapse to TLT + IEF.** Both are USD long-duration UST proxies. They are 0.95+ correlated to each other. Picking both = one bet expressed twice → 100% concentration on the rate-duration factor with no factor diversification (credit, term, currency, real-vs-nominal).
3. **No regime gate.** A bond long-duration thesis only works in disinflation / Fed-cut-pricing regimes. There is no evidence in the `bond_scanner` signal that it conditions on 2y/10y curve, real-yield trend, CPI surprises, or the DXY. The 2026-05-25 batch lost on both legs → consistent with the macro regime that week (re-flation/curve steepening), which a regime-aware scanner would have flagged as a "don't fire" condition.
4. **No exit discipline visible in PnL distribution.** Both losses are −0.56 pp and −0.84 pp — small in absolute terms because the holding window was short, but the win column is hard-zero. A 0/2 with both losses suggests either: (a) the scanner is firing into a trend-following stop-out, or (b) the resolver is closing too quickly to give a trade time to work. With n=2 we cannot distinguish; we need n≥30 to autopsy exit discipline.
5. **Policy-clean filter wipes the entire class.** `by_asset_class_policy_clean_net[BOND]` is **empty** — meaning *zero* BOND picks survive the M-067 policy-clean cohort. So the audit-grade view of BOND is "we don't ship BOND picks at all in the clean view." This is a much larger problem than 0% WR: **we have no policy-clean BOND data to evaluate.**
6. **No closed picks in the last 14 days; none in the last 48h.** BOND is effectively dormant. We are not gathering new data to fix the n=2 problem.

Root-cause summary: **one undifferentiated scanner, single-factor universe, no regime gate, no exit instrumentation, no policy-clean data, no recent activity.** Every dial is at the worst setting.

## External Replication Options

For BOND we want a benchmark with a real, public, multi-year track record we can replicate or piggy-back on. Candidates ranked by feasibility for this stack:

1. **PIMCO BOND ETF (BOND, ticker PIMCO Active Bond)** — actively managed, monthly holdings disclosure (PIMCO 13F + N-PORT). Replicate by mirroring top-10 weights into `bond_scanner_v2_pimco`. Pros: hedge-fund-grade manager, free data. Cons: monthly lag; license-of-strategy concerns are minimal because holdings are public.
2. **DBMF (iMGP DBi Managed Futures Strategy ETF)** — replicates the average CTA managed-futures fund's exposures, of which a significant sleeve is bond-futures (US10Y, Bund, JGB). Pros: published factor regression weekly. Cons: BOND is a sleeve, not the whole product.
3. **KMLM (KFA Mount Lucas Managed Futures Index)** — similar story, bond futures inside a broader trend product.
4. **MTUM / QMOM (MSCI USA Momentum / Alpha Architect)** — equity momentum, not bond. **Not applicable** — drop from BOND short-list.
5. **MyFXBook** — FX only; not applicable for BOND.
6. **Hyperliquid HLP** — crypto-perp LP; not applicable.
7. **AGG / BND** — passive aggregate-bond benchmarks. Use as a **null-hypothesis benchmark**: we should not be running a BOND strategy that under-performs AGG buy-and-hold net of costs. Set AGG TR as the hurdle.
8. **VanEck CLOI / Janus Henderson AAA-CLO (JAAA)** — credit-spread sleeve. Pair with a duration sleeve to break TLT/IEF concentration.
9. **TIP / VTIP (TIPS)** — real-yield exposure, different factor than nominal duration.
10. **HYG / LQD** — credit-spread bond ETFs. Useful for factor expansion if we want a long-credit sleeve.
11. **Academic: Asness/AQR "Value & Momentum Everywhere" (2013)** for the bond cross-section. Apply trend + carry + value to a basket of {UST, Bund, JGB, Gilt, OAT, AGB}. The "carry" leg (long highest-yielding sovereign vs short lowest) has 30+ years of out-of-sample data.

**Recommended primary replication target: PIMCO BOND top-10 + AGG hurdle**, with DBMF rate-sleeve regression as a sanity check and TIP/HYG/LQD added later for factor expansion.

## 30/60/90 Day Rescue Plan

### 30 days (2026-05-31 → 2026-06-30) — collect data + de-orphan
- **D+0..7**: Add a regime gate to `bond_scanner`: do not fire long-duration unless (2y10y steepening < 5bp/week) AND (5y5y breakeven within 1σ of trailing 60d mean). Codify in `alpha_engine/bond_scanner_regime_gate.py`. Wire into the production scanner per the Wire-Up Rule in CLAUDE.md.
- **D+0..14**: Expand universe from {TLT, IEF} to {TLT, IEF, SHY, AGG, LQD, HYG, TIP, MBB}. This breaks the single-factor (duration) concentration immediately, and grows the closed-pick pool faster.
- **D+7..30**: Bootstrap `bond_scanner_v2_pimco` — pull PIMCO BOND monthly N-PORT, mirror top-10 long-only positions, score as a sidecar strategy. Mark opt-in per CLAUDE.md Wire-Up Rule; ship a `## Wiring Plan` block.
- **D+0..30**: Reconcile the n=8 (CLAUDE.md banner) vs n=2 (current pf_registry) gap. File a P1 ticket; trace the 6 missing picks through the policy-clean filter. Output: `reports/bond_n_reconciliation_2026-06.md`.
- **Acceptance for 30d**: n_closed ≥ 30, ≥3 distinct symbols, ≥2 distinct strategies (`bond_scanner` + `bond_scanner_v2_pimco`), HHI ≤ 0.60.

### 60 days (2026-07-01 → 2026-07-31) — find any edge
- Add credit-spread sleeve (LQD/HYG long when OAS narrows, neutral otherwise).
- Add real-yield sleeve (TIP when 10y real-yield rolling-12m z-score < −0.5).
- Add bond-carry cross-section (long highest-yield sovereign futures proxy ETF (BWX/IGOV slices) vs short lowest).
- Run the money-ready harness weekly. Target: by 2026-07-31, `money_ready_verdict.classes.BOND.verdict ∈ {INSUFFICIENT_DATA, SUB_T2}` with n ≥ 60, PF > 1.0, WR > 45%.
- **Acceptance for 60d**: n ≥ 60, PF ≥ 1.0, WR ≥ 45%, HHI ≤ 0.40, AGG-hurdle (cumulative-return − AGG TR over the window) ≥ 0.

### 90 days (2026-08-01 → 2026-08-30) — reach Tier 2 floor
- Run weekly DSR/SPA gates on the four sleeves (duration / credit / real-yield / carry).
- Concentration cap enforced at HHI ≤ 0.30 (project banner threshold) by sizing the largest strategy down before any new pick is published.
- **Acceptance for 90d (Tier-2 floor per CLAUDE.md)**: PF > 1.5, WR > 50%, MDD < 20%, n ≥ 100 policy-clean trades, DSR passes, SPA p < 0.05 on at least one sleeve, AGG-hurdle ≥ +200 bps net.

If we cannot pass 60-day acceptance by 2026-07-31, **demote BOND to "blocked from sizing" per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`** and add `bond_scanner` to `BLOCKED_SOURCE_SYSTEMS` for the closed-pick stream.

## Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Banner cites n=8 but pf_registry shows n=2 raw / 0 policy-clean. Could be reporting drift, policy filter eating data, or stale banner. | High | Med | Reconcile in 30d window; produce `reports/bond_n_reconciliation_2026-06.md`. |
| R2 | 100% strategy concentration (HHI=1.0). Any `bond_scanner` failure mode wipes the entire class. | High | High | 30d plan adds `bond_scanner_v2_pimco`; 60d plan adds credit + real-yield. |
| R3 | TLT/IEF correlation ~0.95 → "two picks, one bet". | Certain | High | Expand universe in 30d (LQD/HYG/TIP/MBB/SHY/AGG). |
| R4 | No regime gate → BOND fires into adverse macro and loses 100% of the time, as observed 2026-05-25. | High | High | 30d: ship 2y10y + 5y5y breakeven gate. |
| R5 | Sub-statistical n (n=2 raw, 0 policy-clean). Any conclusion drawn is noise. | Certain | Med | Plan demands n≥30 by 30d, n≥60 by 60d, n≥100 policy-clean by 90d. |
| R6 | Policy-clean filter excludes 100% of BOND picks → audit-grade BOND view is empty. | Certain | High | Investigate filter rules during reconciliation (R1). May indicate a labeling bug rather than a strategy bug. |
| R7 | No closed picks in 14d / 48h windows → strategy is dormant; cannot rescue with no flow. | Certain | High | 30d plan widens universe + regime gate may also un-block firing. |
| R8 | New `bond_scanner_v2_pimco` could ship as orphan integration (Wire-Up Rule violation). | Med | Med | PR template must answer Wire-Up Rule yes/no before merge. |
| R9 | PIMCO N-PORT data has up to 30-day lag → replication is stale. | Med | Low | Treat as benchmark, not pure replication; pair with live signals. |
| R10 | Demotion to BLOCKED if 60d gate fails — could remove BOND from `/audit` entirely. | Med | Med | Documented exit per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`. |

## Acceptance Criteria

**30 days (2026-06-30):**
- [ ] n_closed (policy-clean) ≥ 30
- [ ] ≥ 3 distinct symbols traded
- [ ] ≥ 2 distinct strategies wired into production scanner
- [ ] HHI ≤ 0.60
- [ ] Regime gate live in `bond_scanner` (PR merged, caller in production scoring path)
- [ ] `reports/bond_n_reconciliation_2026-06.md` published

**60 days (2026-07-31):**
- [ ] n_closed (policy-clean) ≥ 60
- [ ] PF ≥ 1.0
- [ ] WR ≥ 45%
- [ ] HHI ≤ 0.40
- [ ] AGG-hurdle (cumulative net return − AGG TR) ≥ 0 bps
- [ ] Credit + real-yield sleeves shipped
- [ ] DSR computable (n ≥ 60 → harness no longer returns null)

**90 days (2026-08-30) — Tier 2 floor:**
- [ ] PF > 1.5
- [ ] WR > 50%
- [ ] MDD < 20%
- [ ] n ≥ 100 policy-clean trades
- [ ] DSR passes
- [ ] SPA p < 0.05 on ≥ 1 sleeve
- [ ] AGG-hurdle ≥ +200 bps net
- [ ] HHI ≤ 0.30 (project banner threshold)

## Hard Rule (Until Met)

**Until BOND clears the 60-day acceptance gate (n ≥ 60 policy-clean, PF ≥ 1.0, WR ≥ 45%, HHI ≤ 0.40, AGG-hurdle ≥ 0):**

1. **No real-money sizing of BOND picks.** Paper-only.
2. **No promotion of any BOND signal to High Conviction / Smart Picks / Money Ready buckets on `/audit`.** BOND must remain in INSUFFICIENT_DATA / SUB_T2 verdict labels until the gate is cleared.
3. **No new BOND strategy may ship as a production caller without a `## Wiring Plan` block in the PR** (CLAUDE.md Wire-Up Rule) and an explicit n ≥ 20 paper-track plan before it is allowed to influence the closed-pick stream.
4. **Any session that touches BOND must read this report first** and not cite the deprecated n=8 banner without reconciliation.
5. **If 60-day gate fails on 2026-07-31, `bond_scanner` is added to `BLOCKED_SOURCE_SYSTEMS` per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` and BOND is removed from the active asset-class roster on `/audit` until the 90-day rescue plan is rebuilt from scratch.**

— end —
