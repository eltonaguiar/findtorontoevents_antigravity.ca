# Validation: "+313.43% rolling 100" claim

(EST 2026-05-31 17:30) Investigator: claude-validate-plus-313-rolling-100
Repo: eltonaguiar/findtorontoevents_antigravity.ca

## TL;DR

**Verdict: FABRICATED / SOURCE_NOT_FOUND.**

- The literal string "+313.43%" or "313.43% rolling 100" does **NOT EXIST** anywhere in
  `audit_dashboard/`, `reports/`, `updates/`, `alpha_engine/`, `tools/`, or any audit JSON
  surface that feeds the live `/audit` dashboard.
- The only occurrence of `313.43` in the entire (non-worktree) tree is a stale **trade
  PRICE field** (per-share USD) inside `STOCKS/competition/competition-stocks.json` at
  `.asset_classes.stocks.results[6].trades_sample[12].price = 313.43` — i.e. a dollar price,
  not a percent return, not a rolling window.
- Independently reproducing "rolling 100" against live `ejaguiar1_stocks.trading_picks` yields
  SUM=+132.93% / COMPOUND=+257.12% / WR 48.0% / PF 3.34 — neither sum nor compound
  equals 313.43. A sweep across 7 window sizes × 4 orderings produced **no match** within
  ±5 percentage points of 313.43.
- The claim cannot be reconciled with the agreed headline ("RAW at_raw_picks 11.13% WR /
  PF 0.46" or "WR 25.28% / PF 0.61 outlier-capped"). +313% compound over 100 trades on a
  PF<1 dataset is mathematically near-impossible.

**Answer to the operator's questions:**
- *"Is it a compounded win-rate?"* No. "Win-rate" is a count ratio (0–100%); it cannot be
  +313%. If someone called it a "compounded WR" they were misnaming something.
- *"Is it real?"* No source found. Not present in any /audit JSON or report.
- *"What is it based on?"* Unknown — likely either an LLM fabrication (see CLAUDE.md
  warning "DO NOT trust unsourced model claims about /audit numbers"), or a cherry-picked
  arithmetic SUM of `pnl_pct` over a hand-picked window (note: SUM of TOP 100 winners
  on raw `trading_picks` is +5283% — easy to land near 313 with any "top winners" filter).
- *"Does this mean we have profitable strategies?"* The CURRENT live "last 100 closed"
  cohort (all closed statuses, ordered by closed_at DESC, 48h window) is genuinely
  profitable: SUM=+132.93%, COMPOUND=+257.12%, WR=48%, PF=3.34. That is REAL and worth
  investigating — but it is NOT 313.43 and it is NOT a "rolling 100" KPI documented anywhere
  on /audit. The 48-hour window is also too small (only ~48h elapsed) to claim "edge."

## Step 1 — Source search

PRE-EXPECTATION: if "+313.43% rolling 100" is on /audit, it should appear in
`audit_dashboard/data/*.json` or `audit_dashboard/template.html`.

Query (verbatim):

```
grep -rln "313\.43" --include="*.html" --include="*.json" --include="*.py" --include="*.js" \
  /home/eaguiar2015/findtorontoevents_antigravity.ca/ 2>/dev/null \
  | grep -v worktrees | grep -v node_modules
```

RAW RESULT:

```
/home/eaguiar2015/findtorontoevents_antigravity.ca/STOCKS/competition/competition-slim.json
/home/eaguiar2015/findtorontoevents_antigravity.ca/STOCKS/competition/competition-stocks.json
```

Path of the `313.43` value (via Python JSON walker):

```
.asset_classes.stocks.results[6].trades_sample[12].price = 313.43
```

VERDICT: REFUTES the claim that "+313.43% rolling 100" is a published audit KPI. The
only hit is a per-share price, not a percent return.

Additional negative searches (also no hits):

```
grep -rn "\+313\|313%\|313\.43%\|rolling 100\|rolling_100" \
  /home/eaguiar2015/findtorontoevents_antigravity.ca/audit_dashboard/ \
  /home/eaguiar2015/findtorontoevents_antigravity.ca/reports/ \
  /home/eaguiar2015/findtorontoevents_antigravity.ca/updates/
# -> 0 hits
```

```
grep -rn "313" audit_dashboard/data/pf_registry.json \
  audit_dashboard/data/money_ready_verdict.json \
  audit_dashboard/data/asset_class_health.json
# -> only 3 hits, all are sub-1.0 PF gross-loss / total-pnl values
#   (gross_loss=0.313061, gross_loss=0.0313, total_pnl_pct=-0.0313)
```

## Step 2 — Independent reproduction against live DB

DB: `ejaguiar1_stocks.trading_picks` (host mysql.50webs.com, user
ejaguiar1_stocks).

Schema verified — relevant columns: `pnl_pct decimal(10,4)`, `status varchar(20)`,
`closed_at datetime`, `source_system varchar(50)`. There is no `outcome` column; closed
states are `WON, LOST, SL_HIT, TP_HIT, TIME_EXIT, EXPIRED`.

PRE-EXPECTATION: "rolling 100" usually means the most-recent 100 closed picks.

### 2a — Last 100 by `closed_at DESC` (status='WON' or 'LOST' only)

Query (verbatim):

```sql
SELECT pnl_pct FROM trading_picks
WHERE status IN ('WON','LOST') AND pnl_pct IS NOT NULL
ORDER BY closed_at DESC LIMIT 100;
```

RAW RESULT (computed in Python from cursor):

```
n=100
SUM_arithmetic_pct=-362.99%
AVG_pct=-3.6299%
WR=0.00%
PF=0.0000
COMPOUND_pct=-99.91%
MIN=-98.40% MAX=-0.07%
```

Note: those 100 are ALL labeled LOST (WR=0) — these are catastrophic-loss labels likely
from the EXPIRED→LOST mislabeling discussed in CLAUDE.md. NOT a +313% scenario.

### 2b — Last 100 by `closed_at DESC` across ALL closed statuses

Query:

```sql
SELECT pnl_pct, status, source_system, closed_at FROM trading_picks
WHERE status IN ('WON','LOST','SL_HIT','TP_HIT','TIME_EXIT','EXPIRED')
  AND pnl_pct IS NOT NULL
ORDER BY closed_at DESC LIMIT 100;
```

RAW RESULT:

```
n=100
SUM_arithmetic_pct=132.93%
AVG_pct=1.3293%
WR=48.00%
PF=3.3426
COMPOUND_pct=257.12%
MIN=-4.83% MAX=9.01%
date range: 2026-05-29 13:33:17  ->  2026-05-31 20:14:17  (~48h)
```

VERDICT: PARTIAL — these numbers look healthy (PF 3.34, COMPOUND +257%) but
they are NOT 313.43. They also span only ~48h, so they are not a stable
"rolling 100" KPI — they are a 48h spot reading.

### 2c — Window sweep hunting for 313.43

Tried `closed_at DESC`, `closed_at ASC`, `created_at DESC`, `updated_at DESC`
× LIMIT in {50,100,150,200,250,300,500}. For each, computed arithmetic SUM and
COMPOUND return. **No combination produced SUM or COMPOUND within ±5pp of
313.43.**

### 2d — Cherry-pick test (top 100 winners)

```sql
SELECT pnl_pct FROM trading_picks
WHERE status IN ('WON','LOST','SL_HIT','TP_HIT','TIME_EXIT','EXPIRED')
  AND pnl_pct IS NOT NULL
ORDER BY pnl_pct DESC LIMIT 100;
```

RAW RESULT: `SUM=5283.38%  AVG=52.83%`

So an arbitrary "top winners" cherry-pick easily exceeds 313%. A more
restrictive cherry-pick (e.g. top 100 in a single source-system, capped
at some max) could plausibly land near 313%. There is no way to falsify
this without the original query.

## Step 3 — Sanity check vs the headline

Headline claims (operator-supplied):

- RAW `at_raw_picks`: WR 11.13% / PF 0.46
- Outlier-capped: WR 25.28% / PF 0.61

For a 100-trade cohort with WR=25%, PF=0.61, the arithmetic SUM of pnl_pct is
**negative by construction** (PF<1 ↔ gross_win < gross_loss ↔ sum<0). A
COMPOUND return of +313% over 100 trades requires average per-trade gross
multiplier of ~1.014 (i.e. ~1.4% per trade compounded, with no large
drawdowns). That is incompatible with WR 25% / PF 0.61.

VERDICT: REFUTES — +313.43% on the WR-25%/PF-0.61 dataset is mathematically
implausible.

## Step 4 — Verdict + return code

- Source query found in repo: **NO**
- Number reproducible from `trading_picks`: **NO** (closest natural reading
  = COMPOUND 257.12% on 48h window)
- Consistent with headline raw stats: **NO**
- Most likely origin: LLM fabrication (CLAUDE.md explicitly warns about
  Cloudflare-hosted models inventing /audit numbers) OR a hand-cherry-picked
  arithmetic SUM over an undeclared filter.

`PLUS_313:verdict=FABRICATED:definition=other:source_query_found=false`

## Step 5 — What is real, then?

Worth pulling forward (not as "+313.43" but as a genuinely interesting signal):

- The live last-100 closed cohort across all closed statuses on `trading_picks`
  is currently +132.93% arithmetic / +257.12% compound, WR 48%, PF 3.34,
  but spans only the last ~48h.
- This is **inconsistent** with the headline WR 25% / PF 0.61, suggesting
  either (a) the headline is computed on a much longer / pre-resolver-fix
  window, or (b) the 48h cohort is dominated by a single newly-mutated
  source/strategy. Worth a deep-dive — but do not advertise it on /audit
  until it is reproduced over n>=200 and a stable >=14d window.
