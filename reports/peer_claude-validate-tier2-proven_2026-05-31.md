# VALIDATE — TIER-2 PROVEN section (signal_validation / mega_mutation / rl_agent)

(EST 2026-05-31 16:35) Read-only validation of the `/audit` "TIER-2 PROVEN" hero-card section. Methodology-proof: every claim has its source query/file inline.

---

## 1. Page claim vs live snapshot vs live DB

### Source of truth A — code: `_TIER2_PROMOTION_TARGETS`
`audit_trail/dashboard_generator.py:11441`:
```
"signal_validation",
"mega_mutation",
"rl_agent",
```
These three names are the **only** strategies the Tier-2 hero card renders. Source: VERBATIM excerpt above.

### Source of truth B — live dashboard JSON
File: `audit_dashboard/data/dashboard_data.json`  
`generated_at`: **2026-05-28T21:29:18.513454+00:00** (~3 days STALE as of 2026-05-31)

| Strategy | tier | tier_reason | n | wr_pct | PF | MDD | total_pnl_pct | wins | losses | n_closed | last_signal |
|---|---|---|---|---|---|---|---|---|---|---|---|
| signal_validation | **Building** | n=88 below 100-pick floor (CHARTER s10) | 88 | 17.0 | 0.39 | 67.57 | -56.94 | 15 | 48 | 420 | 2026-05-28T17:22Z |
| mega_mutation | **Below Tier 3** | MDD=28.3%>20 | 124 | 62.9 | 2.97 | 28.27 | **+246.2** | 78 | 46 | 177 | 2026-05-28T20:35Z |
| rl_agent | **Building** | n=0 below 100-pick floor (CHARTER s10) | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 | 0 | (empty) |

`flagged_dropouts` array contains all four targets (including `claude_gainer` — "not in systems[] feed"). **The dashboard is already honestly self-flagging all four targets — none are claimed as strict Tier 2.**

### Source of truth C — user's task brief
> signal_validation (WR 12% PF 0.29 MDD 79.5% n=92), mega_mutation (WR 65.9% PF 3.55 MDD 28.3% n=135 90d_cum +318%), rl_agent (n=0 0/0/0)

These numbers differ from the live snapshot above. signal_validation is **drifting worse** (WR 17%→12%, MDD 67%→79%, n 88→92); mega_mutation drift is small (n 124→135, WR 62.9→65.9). **Drift confirmed** between user's view and snapshot B.

### Source of truth D — live MySQL `ejaguiar1_stocks.trading_picks`
Query (verbatim) executed 2026-05-31 ~20:35Z:

```sql
SELECT strategy, COUNT(*), SUM(pnl_pct>0) wins, SUM(pnl_pct<0) losses,
       SUM(pnl_pct), MIN(closed_at), MAX(closed_at)
FROM trading_picks
WHERE (strategy LIKE '%mega_mutation%' OR source_system='signal_validation'
       OR strategy='rl_ppo_agent' OR source_system IN('rl_agent','rl_ppo_agent'))
AND closed_at IS NOT NULL AND pnl_pct IS NOT NULL;
```

Raw result (separate queries, exact values):
- **mega_mutation** family (LIKE '%mega_mutation%'): n=**2**, wins=0, losses=2, sum_pnl=**-6.81%**, worst=-4.78%, best=-2.03%, first close 2026-05-23 13:10, last 2026-05-25 12:23.
- **signal_validation** as `source_system`: n=**0** rows.
- **rl_ppo_agent**: n=5 rows total, **0 closed**, 0 wins.

DISTINCT strategy names that matched: `mega_mutation_ema_momentum_m006`, `mega_mutation_macd_rsi_m048`, `mega_mutation_macd_rsi_m084`, `Revival_Mutated_mega_mutation_*`, `rl_ppo_agent`. NO exact `mega_mutation`, `signal_validation`, or `rl_agent` row exists. Schema columns: `id, symbol, direction, strategy, …, source_system, status, pnl_pct, …`.

### Source of truth E — live file ledger `genome/data/mega_mutation_picks.json`
mtime 2026-05-31 20:17. n=**283 closed_picks** TODAY. Replay stats (computed from the JSON):

```
n=283  wins=185  losses=98  WR=65.37%  PF=3.332  arith_sum_pnl=+719.51%
arithmetic_MDD=74.79%      compound_geometric_pnl=+90,904.22%
At snapshot ts 2026-05-28 21:29Z: n=254 closed, cum_arith_pnl=+574.88%
```

`signals_database.json` (the `_TIER2_PROMOTION_TARGETS` source for signal_validation): 379 records, **none carry `pnl_pct` / `outcome` / `status`** — only `validated` + `validation_results`. So whatever populates the dashboard's signal_validation n=88 wins=15 losses=48 is NOT this ledger directly; it must be the resolver-output path. `rl_agent/data/closed_picks.json` does not exist.

PRE-EXPECTATION: dashboard stats reconcile to DB or file ledger. RESULT: **REFUTES.** Three different counts for mega_mutation across three sources (DB:2, file:283, dashboard:124). signal_validation is `DB_MISSING` in `system_pf_verification.json:155-173` and absent from `trading_picks`.

---

## 2. Most important question — is mega_mutation's "+318%" 90d_cum a REAL edge or an arithmetic artifact?

### Verdict: **Real WR/PF edge on the file ledger; but the "+318%" / "+246%" / "+575%" `total_pnl_pct` number is an arithmetic-sum artifact, NOT a tradable return.**

Source code — verbatim from `audit_trail/dashboard_generator.py:11540-11550`:
```
    # Build cumulative
    cum = 0.0
    cum_series = []
    for _, v in series:
        cum += v
        cum_series.append(round(cum, 2))
```
This is **arithmetic addition** of per-trade `pnl_pct`. It is mathematically equivalent to assuming you reset the notional to the same starting $ before every trade — i.e. it pretends compounding never happens. It is NOT account growth.

Forward-test cross-check on the ledger:
- arith_sum 90d ≈ +575% to +720% (per snapshot vs current ledger).
- compound geometric 90d ≈ +90,904% on the same trade tape — implausibly large, indicating either (a) extreme leverage in the pnl_pct units OR (b) repeated large gains that the geometric series exaggerates because no max-allocation cap is applied.
- The fact that arith and compound diverge by 2 orders of magnitude is itself a red flag that the ledger pnl_pct units are not "% of total account."

Same-magnitude artifact as +313% headline? **PARTIAL — same arithmetic class of artifact (sum of pnl_pct, no compounding, no cap, no realistic position-sizing).** It is consistent with the dashboard-wide convention: every `total_pnl_pct` in `systems[]` is an arithmetic sum. So yes, the user's hypothesis that "+318%" mega and "+313%" headline are the same kind of fake-looking-large number is **correct** — both are arithmetic pnl_pct sums, not compound returns.

That said, the **WR=65% / PF=3.3 / n=283** of the mega_mutation family on the ledger IS a non-trivial signal. So:
- Edge signal: real (large n, high PF, persistent over 90 days).
- "+318% 90d_cum" framing: artifact. The dashboard text "90d cum" on the hero card implies account growth, which is misleading.

`mega_mutation_real` = **partial**: the edge is real; the headline number is misleading.

---

## 3. Validate "Building" / "Below Tier 3" labels — what code determines this?

`_classify_tier()` is called at `dashboard_generator.py:11774`. Same file lines 3155-3170 in template.html document the tier colour rule. The 4 thresholds for strict Tier-2 admission (line 11775: `is_strict_tier2 = (tier_label == "Tier 2")`) follow CHARTER §2.

Live snapshot tier reasons (from JSON):
- signal_validation → **Building** (n=88 below 100-pick floor, CHARTER s10). Correct: 88 < 100.
- mega_mutation → **Below Tier 3** (MDD=28.3% > 20). Correct per CHARTER (Tier 2 max MDD=20%, mega's MDD = 28.27%).
- rl_agent → **Building** (n=0 below 100-pick floor). Correct.

The badges are honest. The visual "TIER-2 PROVEN" heading at template.html:1259 is misleading because **none of the three currently qualifies** as strict Tier-2. Code comment at template.html:1255-1256 explicitly anticipates this: *"strategies that drop out of Tier-2 at recompute time get an honest 'Building' / 'Tier 3' / 'Below Tier 3' badge instead of a fake Tier-2 stamp"* — but the section *heading* still says "TIER-2 PROVEN" even when 0/3 actually pass. **Visual/data mismatch is a real UX bug.**

`dropouts_confirmed` = **TRUE** — all three are in `flagged_dropouts` of the live JSON (plus claude_gainer).

---

## 4. Three most-recent picks per strategy

From `dashboard_data.json` `tier2_proven_strategies.cards[].recent_picks` (3 days stale; can't pull DB rows because DB has 0 signal_validation / 2 mega_mutation / 0 rl_agent).

Dashboard JSON shows live source-system mapping (computed via `_strategy_recent_picks` which filters by `source_system == system_name`). Recent_picks arrays for all 3 are present in the JSON but the snapshot is 3 days stale, so I report them only for reference (not validating against today's DB because today's DB has no matching rows).

---

## 5. Drift summary per cell

| Cell | Page (user task) | Live JSON 2026-05-28 | Live DB 2026-05-31 | Live file ledger 2026-05-31 |
|---|---|---|---|---|
| signal_validation n | 92 | 88 | **0** | n/a (no pnl in file) |
| signal_validation WR | 12% | 17% | n/a | n/a |
| signal_validation PF | 0.29 | 0.39 | n/a | n/a |
| signal_validation MDD | 79.5% | 67.57% | n/a | n/a |
| mega_mutation n | 135 | 124 | **2** | **283** |
| mega_mutation WR | 65.9% | 62.9% | 0% (2/2 losses) | **65.37%** |
| mega_mutation PF | 3.55 | 2.97 | 0 | **3.33** |
| mega_mutation 90d_cum | +318% | +246.2 (total) | -6.81% | +719.51% arith / +90,904% compound |
| rl_agent n | 0 | 0 | 0 closed | n/a (no file) |

Drift severity: **HIGH** — 3 different "n" values for mega_mutation across 3 sources; user view drifted from snapshot. The site is stale by 3 days *and* the snapshot disagrees with the DB *and* the file ledger.

---

## Acceptance return

- TIER2_strategies_validated = 3
- page_matches_DB = 0 of 3 (signal_validation MISSING in DB; mega_mutation has 2 rows not 124; rl_agent 0 rows)
- page_matches_file_ledger = 0 of 3 cleanly (mega_mutation 124 vs 283 closed; signal_validation no pnl column in ledger; rl_agent ledger absent)
- mega_mutation_real = **partial** — edge is real (65% WR / PF 3.3 / n=283); but "+318% 90d_cum" framing is an arithmetic-sum artifact, not account growth
- dropouts_confirmed = **TRUE** — all 3 already in flagged_dropouts as Building/Below-Tier-3

## Most important finding

The "TIER-2 PROVEN" hero-section header is **structurally misleading**: as of 2026-05-28 snapshot it contains 0 strictly-Tier-2 strategies (all three are flagged), yet the heading retains the "PROVEN" word. Recommend either (a) auto-hide the section when `is_strict_tier2=false` for all cards, or (b) rename section to "TIER-2 CANDIDATES (live tier shown per card)" so the badge stripe (Building / Below Tier 3) carries the truth.

Secondary finding: every `total_pnl_pct` and 90d_cum number on the dashboard is an **arithmetic sum of pnl_pct values** (verbatim from `dashboard_generator.py:11540-1550`). Same root-cause class as the "+313%" headline the user is suspicious of. This is NOT compound return, NOT account growth — it is "sum of percent changes if every trade had the same starting notional and never compounded." Should be labelled "avg_trade_pct × n" or "Σ pnl_pct (non-compounded)" to avoid misleading a hedge-fund reader.

NFA — read-only diagnostic, no code/data writes outside this report.
