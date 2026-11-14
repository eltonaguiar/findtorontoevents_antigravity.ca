# EQUITY / ETF / BOND — One Deeper Proposed Fix + Mutual-Funds Honest-Options Spec
Base: `.inspect-wt` at f54efb3b4a (HEAD 464035ff56), all anchors grep-verified. Companion: `quick_wins.md`. Date: 2026-11-14.

---

# §A. PROPOSED FIX (deeper): Entry-time-anchored intrabar replay — repairs the poisoned ETF/EQUITY "honest truth" that gates money_ready

## A.1 Problem (verified)

money_ready gates EQUITY/ETF on an "intrabar truth" cohort that collapses ETF to **WR 2.2% / PF 0.0216 (n=45)** while every other ETF surface says 39.5-73.3% WR (`live_money_ready.json` `.classes.ETF.intrabar_truth` + `.intrabar_daily_divergence.pf_inflation_x=84.99`, `flag:true`; `live_pf_registry.json` ETF PF 1.84055 n=15; `closed_stats.json` ETF 14d WR 39.5% n=43). EQUITY shows the same divergence at smaller magnitude (daily PF 1.2983 vs honest 0.9392, `pf_inflation_x` 1.38).

Root cause chain, all verified at f54efb3b4a in `audit_trail/universal_pick_resolver.py`:

1. **No entry-time anchor.** `_check_tp_sl_intrabar()` (:558-596) iterates `ohlcv_bars` from oldest to newest and returns the first bar whose low/high crosses SL/TP. The bar dicts have **no timestamps**: yfinance path (:502-510) keeps only `{open,high,low,close,volume}`; the Binance path (:537-548) receives `k[0] = open_time` and throws it away.
2. **Window includes pre-entry bars.** The OHLC cache is `period="5d", interval="1h"` for non-crypto (:485, called at :1043) and `limit=48` 1h bars for crypto (:519). A pick entered intraday today replays ~4 days of pre-entry ETF bars first.
3. **TP/SL clamp tightens SL to 1-2.5%.** Before replay, every pick is clamped to TP 2-4% / SL 1-2.5% (:1231-1252). For a LONG at today's price, `low <= entry×0.975..0.99` inside the pre-entry 5-day window is near-certain for sector/leveraged ETFs (TQQQ/ARKK/SOXX daily ranges 2-5%). Result: pick resolves `SL_HIT` on a **wick that predates entry**. 2 of 45 ETF intrabar rows survived → 2.2% WR.
4. **Universe narrowing amplifies it.** The intrabar cache prefetches only symbols appearing in current active feeds (:1025-1047), so older-but-unresolved picks resolve via close-price/TIME_EXIT and never enter the intrabar cohort — and the money_ready cohort is further narrowed to one source (`live_money_ready.json` `.classes.ETF.top_source = "etf_scanner", share 1.0`).

`UNVERIFIED at f54efb3b4a`: the production writer of the `at_signal_outcomes.intrabar_*` columns that money_ready reads (string `intrabar_truth`/`sizing_source` has no match anywhere in this tree; resolver at this base writes `at_pick_outcomes`, :849-876). The mechanism above is in the resolver this base ships; whichever newer writer inherited `_check_tp_sl_intrabar` inherits the same defect. Verify on origin/main before merge (grep `at_signal_outcomes` + `intrabar`).

## A.2 Fix (patch: `proposed_fix_intrabar_anchor.patch`)

1. **Carry timestamps in bars.**
   - `_fetch_yfinance_ohlcv` (:485-517): add `"t"` (ISO string from `hist.index`).
   - `_fetch_binance_klines_ohlcv` (:519-556): add `"t_ms": int(k[0])`.
2. **Anchor the replay.** `_check_tp_sl_intrabar` (:558-596) gains an optional `entry_ts: float` (epoch seconds). Before evaluating each bar, skip bars whose `t` resolves earlier than `entry_ts` (fallback: `pick["timestamp"]` parsed by the existing `_parse_timestamp`, :616). Bars without a `t` key keep legacy behavior (fail-open, no regression for exotic feeds).
3. **Flag clamped picks in the outcome.** In the resolution result (:1263-1292), if the clamp at :1231-1252 actually rewrote TP/SL, set `resolved["_tp_sl_clamped"] = True` — lets the intrabar cohort be audited clamped-vs-native later without another schema change.
4. **Backfill + regenerate (ops, one-time).** Re-run the resolver over the active feeds for the last ~14d (crypto `limit` can be raised 48→336 in the same run to widen the crypto window symmetrically — optional flag). Regenerate `money_ready_verdict.json`. Expected: ETF `intrabar_truth.n` stays ~45 but `wr`/`pf` move from (0.0222 / 0.0216) toward the daily band (39.5-73.3% / 0.72-1.84); `intrabar_daily_divergence.flag` flips to false for ETF if the divergence was pure pre-entry SL; EQUITY honest PF should drift up from 0.9392.

## A.3 Rollout gates & acceptance criteria

- G1 Ship behind `RESOLVER_INTRABAR_ANCHOR=1` (default ON; `=0` restores legacy replay verbatim).
- G2 Before flip: dry-run 30d replay on a sample of 50 ETF + 50 EQUITY picks; assert (a) no pick resolves before its own `entry_ts`, (b) SL-first intra-bar ordering unchanged, (c) delta report: old vs new WR/PF per class attached to the PR.
- G3 Acceptance: ETF `intrabar_daily_divergence.pf_inflation_x` drops from 84.99× into < 2× or the divergence flag flips false; money_ready ETF verdict changes only via the recomputed JSON (no hand-edited numbers).
- G4 Watch item: `at_signal_outcomes` writer version bump so downstream consumers can distinguish anchored rows (`_resolver_version`/`RESOLVER_VERSION` constant, cite line in patch context).
- Rollback: flip env var off; no schema migration involved (bars are in-memory; outcomes keep the same columns).

## A.4 Expected live effect

- money_ready ETF stops reporting a fabricated 2.2% WR as "honest truth"; the 85× PF inflation flag retires.
- EQUITY honest PF moves 0.9392 → (daily 1.2983 − realistic intrabar cost); the 1.38× divergence resolves.
- BOND `insufficient_intrabar` sizing (n=26, WR 7.69%) gets a truthful recompute; combined with §B gates this decides restart vs retire with real numbers instead of poisoned ones.

---

# §B. BOND restart-or-retire decision framework (concrete gates)

State (verified): operator-frozen since 2026-06-03 (`audit_trail/quality_gates.py:1726-1732`, BOND in `BLOCKED_ASSET_CLASSES`, −60 score at :4107); pipeline still emits daily (`.github/workflows/bond-agent.yml:11` cron 14:32 Mon-Fri; scanner registry entry `audit_trail/dashboard_generator.py:4012-4015` over 14 symbols; scanner `alpha_engine/bond_scanner.py` with run_bond_scanner()); the daily *scanner* workflow is already disabled (`.github/workflows/alpha-engine-bond.yml.disabled:17`); live book: active_raw n=15 all ~25h, closed n=35 newest 98.1h, money_ready n_resolved=1, registry n=2, PF 0.0 (`live_pf_registry.json` BOND). Decision framework — run each gate in order; all data already collectable from existing JSONs:

- **Gate B1 (retire default):** if after §A.4's anchored recompute BOND `intrabar_truth.n` stays < 30 AND registry policy-clean n stays < 30 for another 30 consecutive days → **retire**: remove BOND from `template.html:6232-6237` categories + `_PER_ASSET_CLASSES`/`_NC_ASSET_CLASSES`, delete `bond-agent.yml`, keep the 35 closed rows as history. Rationale: money cannot be validated on n=1 resolved rows; a class with 1 closed row per ~100 emitted is not a pipeline, it's noise.
- **Gate B2 (restart):** only if the paper-only bypass defined in the freeze comment (`quality_gates.py:1732`: "paper-only 60d on HYG/LQD credit-spread strategies") completes 60d with ≥ 30 resolved paper trades AND net-of-cost PF ≥ 1.0 at ≥ 45% WR → lift BOND from `BLOCKED_ASSET_CLASSES` **for those two symbols only**, re-enable `bond-agent.yml` cron, and set `policy_frozen=false` via the operator step.
- **Gate B3 (falsifier):** if during the paper window the 14 symbols' bond backtests (PF 1.29-1.62 cited at `template.html:908`) fail walk-forward OOS PF ≥ 0.85× in-sample (`alpha_engine/walkforward_validator.py` outputs already flow to `live_dashboard_data.json .walkforward`) → retire without paper phase.
- **Gate B4 (hygiene, do regardless):** QW5 (pause cron while frozen) ships immediately; BOND stays visible in closed-history surfaces only.

Decision owner: operator (freeze lift is explicitly operator-owned per `template.html:997` tooltip text).

---

# §C. Mutual funds — honest options (vaporware today)

Verified state: zero MUTUAL rows in `live_dashboard_data.json` (regex count 0); `alpha_engine/mutual_fund_ranker.py` does not exist; the only mutual-fund code paths are a classifier arm (`audit_dashboard/database_consolidation.py:81` `if cat in ("mutual_fund",): return "MUTUAL_FUND"`) and a spec'd-but-unbuilt universe (`multi_asset/portfolio_defs.py:674-699` — 14 funds: VFINX, VTSAX, VBTLX, VTIAX, VGSLX, VPMAX, VWELX, VGHCX, VITAX, FXAIX, FBALX, FSMEX, FSPTX, FBIOX, with sector groupings and risk_params including "Mutual funds settle T+1 ... No intraday execution"; strategy entry/exit rules at :380-395 `tactical_fund_rotation`). Prior art: `audit_dashboard/incidents.html:5193-5198` (IDEA-C: yfinance `quoteType=MUTUALFUND` + expense-ratio < 0.5% + no-load filter) and `hedge_fund_simulation_20260524.html:120` (Fidelity Zero / Schwab candidates).

**Option 1 — Remove from UI (recommended now, ~0.5 day).** Mutual funds currently appear nowhere on /audit, so the honest action is a *non*-action plus documentation: add a one-line note in the per-asset summary that MUTUAL_FUND is classified-but-unimplemented (`database_consolidation.py:81` classifier can never match a live row because no emitter sets `category=mutual_fund`), preventing a future audit from re-deriving the "vaporware" finding. Cost: one doc line. Risk: none.

**Option 2 — Implement the ranker (2-3 days + workflow).** Only worthwhile if the user actually trades mutual funds:
- `alpha_engine/mutual_fund_ranker.py` — ranks `multi_asset/portfolio_defs.py:676-696` universe by 3M momentum + 1M reversal (rules already spec'd at :384-387), NAV-only execution at 16:00 ET (risk_params `rebalance_frequency_days: 21`, `min_holding_period_days: 30`, `default_stop_dd_pct: -8`).
- Data: yfinance daily NAV is sufficient (same `data_source: yfinance` declared at :721); no intraday claims anywhere in the surface.
- Output: `alpha_engine/data/active_picks_mutual_fund.json` + registry entry in `audit_trail/dashboard_generator.py:4012`-style tuple with asset_class `MUTUAL_FUND` + a new daily cron cloned from `bond-agent.yml` shape.
- Honest constraint to surface: T+1 settlement and NAV-only pricing mean pick cards must show "NAV close execution" and forward stats will lag 1 day — put this in the tooltip, not hidden.
- Gate to ship: same money_ready n≥30 policy as §B; start as `MUTUAL_FUND` class in shadow mode (emit to closed-shadow, no `picks.active`).

Recommendation: **Option 1 now; Option 2 only on explicit user demand.** The class has no live evidence trail, no demand signal in the audit surfaces, and the equity/ETF books already under-serve their own sample-size gates (ETF policy-clean n=15).

---

# Outputs in this folder
- `quick_wins.md` — 6 actionable quick wins + 2 verification results, all anchored.
- `quick_wins.patch` — hunks for QW1-QW6 (dashboard_generator.py, template.html, test fixture, bond-agent.yml, funds.html).
- `proposed_fix.md` — this file (§A deeper fix spec, §B bond gates, §C mutual-funds options).
- `proposed_fix_intrabar_anchor.patch` — resolver entry-anchor implementation.
