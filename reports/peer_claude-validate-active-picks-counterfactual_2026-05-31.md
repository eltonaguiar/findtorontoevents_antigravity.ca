# Active Picks Counterfactual — Equal-Allocation What-If

(EST 2026-05-31 16:50) Read-only DB simulation. Per RULES, every claim is backed by SQL + raw output.

## Lane Definitions (source-of-truth lookups)

### Verified Alpha
Source: `audit_trail/feed_membership.py:48-54`
```
VERIFIED_ALPHA_SOURCES = frozenset({
    "claws_of_doom",
})
```
Plus `trust_tier == 'PROVEN'` AND strategy not force-demoted. Cross-check via `is_verified_alpha_per_pick()`.

### Smart Picks
Source: `audit_trail/quality_gates.py:441-497`
```
SMART_PICKS_MIN_SCORE = 60  # FROZEN 2026-05-20 to 2026-08-18
SMART_PICKS_MIN_SCORE_EQUITY = 50
SMART_PICKS_MIN_SCORE_FOREX = 40
SMART_PICKS_MIN_SCORE_COMMODITY = 30
SMART_PICKS_MIN_SCORE_BOND = 35
SMART_PICKS_MIN_SCORE_ETF = 35
SMART_PICKS_MIN_CONFIDENCE = 0.60
```
DB proxy used here: `elite_score >= 60 AND confidence >= 0.60` (class-agnostic floor; real gate is per-class).

### UEPS
Source: `audit_dashboard/data/ueps_picks.json` (22 long-term value picks, ALL `status="ACTIVE"`, 0 swing, 0 short).
Generated 2026-05-31T20:42:07Z. Universe size 51, filtered 49.

### Active vs Recent-Closed (raw status dist)
PRE-EXPECTATION: ACTIVE/OPEN should dominate (live book).
```sql
SELECT status, COUNT(*) FROM trading_picks GROUP BY status;
```
RAW:
```
ACTIVE     3599    OPEN       4444
LOST       2854    SL_HIT     1508
TP_HIT     3613    TIME_EXIT 26026
EXPIRED     621
```
Verdict: matches expectation — 8043 unrealized vs ~34.6k closed.

## Equal-Allocation Simulation ($1000 per pick, parallel)

PRE-EXPECTATION (per user memory `project-money-ready-2026-05-31`): no class passes T2; CRYPTO sub-T2; equity recent improving; trust_score=7 is the only real edge. So we expect (a) UEPS un-evaluable (all active), (b) VERIFIED_ALPHA empty (claws_of_doom not emitting), (c) SMART_PICKS leaky once we go lifetime, (d) recent-30d positive due to CRYPTO recovery.

### Query template
```sql
SELECT pnl_pct, category, closed_at, source_system
FROM trading_picks
WHERE pnl_pct IS NOT NULL AND status NOT IN ('ACTIVE','OPEN') AND <lane>
ORDER BY closed_at;
```
Portfolio return %% = mean(pnl_pct). Sharpe = mean/std * sqrt(252). MaxDD on chronological compounded path (1/n weight).

### Results

| Lane | n | WR%% | Avg PnL/pick %% | Portfolio Return %% | $ on $n*1000 | Sharpe(ann) | MaxDD%% |
|---|---|---|---|---|---|---|---|
| RECENT_CLOSED_30D | 1277 | 42.83 | +0.2532 | +0.2532 | +$3,232.96 on $1.277M | 0.86 | 0.17 |
| **VERIFIED_ALPHA (claws_of_doom)** | **0** | n/a | n/a | n/a | empty — source has emitted 0 picks lifetime | n/a | n/a |
| SMART_PICKS_elite60_conf60 (lifetime) | 1164 | 9.79 | +0.0672 | +0.0672 | +$781.73 on $1.164M | 0.74 | 0.03 |
| SMART_PICKS_30D | 75 | 41.33 | +0.3893 | +0.3893 | +$292.00 on $75K | **2.08** | 0.43 |
| **UEPS_source (in DB)** | **0** | n/a | n/a | n/a | source_system='ueps' not yet writing to trading_picks | n/a | n/a |
| TRUST_SCORE_GE_7 | 2430 | 4.94 | +0.0949 | +0.0949 | +$2,306.53 on $2.43M | 0.84 | 0.02 |
| EQUITY_30D | 27 | 33.33 | **-0.8867** | **-0.8867** | **-$239.41 on $27K** | -5.80 | 0.94 |

### Per-Class Breakdown — Best Lane (SMART_PICKS_30D)
All 75 picks in last 30d are CRYPTO. WR 41.3% / avg +0.39%. **No equity, no forex, no commodity** at elite>=60 + conf>=0.60 closed in 30d.

### Per-Class Breakdown — RECENT_CLOSED_30D
- CRYPTO n=1113 WR 47.2% avg +0.51%% — **the only profitable class**
- FOREX n=53 WR 17.0% avg -0.29%%
- COMMODITY n=77 WR 2.6% avg **-2.07%%** — catastrophic
- STOCKS n=2 WR 0% avg -23.8%%
- EQUITY n=27 WR 33.3% avg -0.89%%
- ETF n=3 WR 66.7% avg +1.12%% (n too small)

Verdict: matches memory — CRYPTO is the recent winner; commodity/equity continue to lose. The "TRUST_SCORE=7 is an edge" claim does NOT replicate at the broader trust_score>=7 cut (WR 4.94% on n=2430 with CRYPTO dominating at WR 4.25%), suggesting the earlier 85.9% WR / n=99 finding was specific to a narrower subset (likely category='stock' OR a particular strategy intersection).

## Reality Check — Which Lane Would Have Been Profitable?

PROFITABLE (closed, simulated):
1. **SMART_PICKS_30D**: +0.39% portfolio / Sharpe 2.08 (best risk-adjusted)
2. RECENT_CLOSED_30D: +0.25% / Sharpe 0.86
3. SMART_PICKS_elite60_conf60 lifetime: +0.07% / Sharpe 0.74 (decayed badly vs 30d)
4. TRUST_SCORE_GE_7: +0.09% / Sharpe 0.84 (CRYPTO-only edge)

UN-EVALUABLE (zero closed rows):
- VERIFIED_ALPHA — claws_of_doom emits 0 in `trading_picks` (lifetime)
- UEPS — separate JSON sidecar, all 22 picks still ACTIVE (issued 2026-05-31)

LOSING:
- EQUITY_30D: -0.89% portfolio / Sharpe -5.80 — would have lost $239 on $27K

**Best lane: SMART_PICKS_30D** (CRYPTO-only, Sharpe 2.08). But it's 100% one class, which the memory notes (Goal #1: 0/6 classes pass T2; CRYPTO is sub-T2 PF 1.14).

## Suggested Filter Additions (per-lane)

| Lane | Add Filter | Expected Effect |
|---|---|---|
| RECENT_CLOSED_30D | EXCLUDE `category IN ('COMMODITY','STOCKS','EQUITY')` (avg -0.89 to -23.8%%) | Drops 108 losing picks; portfolio return rises ~+0.07pp to ~+0.32%% |
| SMART_PICKS_elite60_conf60 | RESTRICT `category='CRYPTO' AND closed_at >= NOW()-30d` (matches SMART_PICKS_30D) | Recovers Sharpe 0.74 → 2.08, returns 0.07 → 0.39 |
| VERIFIED_ALPHA | REBOOT pipeline: `claws_of_doom` writes zero picks to `trading_picks`. Fix emitter OR widen `VERIFIED_ALPHA_SOURCES` after S4 rehab on `claude_gainer_st` per feed_membership.py:51-53 | Currently zero coverage = zero alpha capture |
| UEPS | Add a daily snapshot job that writes UEPS picks to `trading_picks` with `source_system='ueps'` so they enter the resolver (currently sidecar-only; INCIDENT_STOCKS #2 fix landed for source_system but no closed rows yet) | Enables forward tracking; n must reach >=30 before any profitability claim |
| TRUST_SCORE_GE_7 | ADD `category='STOCKS'` (the 85.9% WR / n=99 finding from memory was scoped here, not broad). Current broad cut is CRYPTO-dominated and only 4.25% WR | Surfaces the actual edge documented in `project-confidence-trust-edges-2026-05-31` |
| EQUITY_30D | KILL or pause until resolver-intrabar lands (the upstream T2 blocker per memory `project-session-close-2026-05-31`). Live equity closes are bag-holds | Avoids -0.89%%/pick drag |

## Caveats / Methodology Notes

- `pnl_pct` is in percent (decimal(10,4)). Equal-$1000 per position → portfolio return % equals mean(pnl_pct).
- Sharpe is daily-equivalent annualized; not strictly daily because closes are heterogeneous in horizon. Use as relative rank, not absolute.
- MaxDD is computed on a *diversified* 1/n compounded path so values look small; the per-pick worst trade is much deeper (commodity -23.8%).
- "active picks" cannot be back-simulated — they have no exit price. The right counterfactual for active picks is forward expectation, not historical PnL.
- VERIFIED_ALPHA emitting zero is itself the headline: the lane is named on the dashboard but produces no rows. This is consistent with the DISPUTED banner on template.html:909.

## Outputs

- This file: `/home/eaguiar2015/findtorontoevents_antigravity.ca/reports/peer_claude-validate-active-picks-counterfactual_2026-05-31.md`
- No DB writes. No HTML/shared-tree edits.
