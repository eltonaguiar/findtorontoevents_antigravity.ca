# Testing plan — audit page truth-layer PR

Date: 2026-11-16
Branch: `fix/audit-truth-layer-2026-11-16`
Author: kilo / auditpage
Base: `origin/main`

This plan separates **implemented in this PR** from **still open**. A green check on section A does not mean section B is fixed.

Peer plans reviewed before this PR:

| Plan | Kept | Rejected |
|---|---|---|
| `ACTIONPLAN_AUDITPAGE/2026-11-16T0625Z_kilo_auditpage/` | spine: 0 money-ready, ghosts real, WIRED_IN static, PM path split | June PF 2.6 / 2.4 sleeves (stale) |
| `ACTIONPLAN_AUDITPAGE/2026-11-16T0626Z_auditpage-v4/` | sign vs magnitude, ghost check must fail, 150m stale banner, PF `n/a`, GHA table is stale | — |
| `ACTIONPLAN_AUDITPAGE_2026-11-16T06-23-31Z/` | evidence index, owner split | "6 broken workflows"; "positive-expectancy stream" wording |

`auditpage-v2` and `auditpage-v3` landed no plan.

---

## A. Implemented here — must pass before merge

### A1. Ghost-row verdict (unit)

```bash
python3 -m unittest tests.test_ghost_row_verdict -v
```

Pass: 4 tests OK.

| Input | Expected tier | Expected threshold_pass |
|---|---|---|
| 0 | green | true |
| 500 | yellow | false |
| 22947 | red | false |

Fail if `threshold_pass` is true for any `total_ghosts > 0`.

### A2. Source no longer claims ghosts are gone

```bash
rg -n -F "Ghost rows: 0" audit_dashboard/template.html audit_dashboard/index.html
```

Pass: no matches.

```bash
rg -n "ghost_row_verdict" tools/db_health_check.py
rg -n "Sign consistency" audit_dashboard/dashboard_enhancements.js
rg -n "mins > 150" audit_dashboard/template.html audit_dashboard/index.html
rg -n "PF2.6" audit_dashboard/template.html
```

Pass: verdict helper present; tile renamed; stale threshold is 150; PF2.6 string gone from the template banner.

### A3. Infinity PF / W/L no longer rendered as edge

```bash
rg -n "Infinity \? '∞'|\\\\u221e" audit_dashboard/template.html audit_dashboard/index.html
```

Pass: no matches in the profit-factor or open-forward W/L lines. Zero-loss PF and zero-loser open rows must render `n/a`.

### A4. JS syntax of the edited HTML

```bash
node -e "
const fs=require('fs');
for (const f of ['audit_dashboard/template.html','audit_dashboard/index.html']) {
  const html=fs.readFileSync(f,'utf8');
  if (html.includes('<<<<<<<')) throw new Error(f+' conflict marker');
  const re=/<script[^>]*>([\\s\\S]*?)<\\/script>/g; let m,i=0;
  while ((m=re.exec(html))) {
    if (m[1].length>50000) { i++; continue; }
    try { new Function(m[1]); } catch(e) { throw new Error(f+' script '+i+': '+e.message); }
    i++;
  }
  console.log(f,'ok',i,'small scripts');
}
"
```

Pass: both files print `ok`. Large inline blocks are skipped (same rule as `audit-dashboard.yml`).

---

## B. Still open — do not mark fixed from this PR

These were validated as real and deliberately not executed here.

### B1. Ghost rows still in the database

`audit_dashboard/data/db_health.json` `checks.ghost_rows.data.total_ghost_rows` was **22947** at `generated_at` 2026-11-16T01:29:16Z. This PR only changes the scorer. The next `tools/db_health_check.py` run should write `threshold_pass: false` and `tier: red` while that count remains.

Do **not** run `tools/cleanup_ghost_rows.py --execute` without a dry-run diff and an explicit go-ahead. Quarantine-not-delete is the standing policy.

Verify after the next health run:

```bash
python3 -c "
import json
d=json.load(open('audit_dashboard/data/db_health.json'))
g=d['checks']['ghost_rows']['data']
assert g['total_ghost_rows']==0 or g['threshold_pass'] is False
assert g['total_ghost_rows']<1000 or g['tier']=='red'
print('ghost', g['total_ghost_rows'], g['tier'], g['threshold_pass'])
"
```

Fixed only when `total_ghost_rows==0` **and** a fresh `generated_at` is newer than 2026-11-16T01:29Z.

### B2. Sign vs magnitude

Same file: `pnl_integrity.data.gt1pct_mismatch` 130 / 24158 (0.54%) is sign consistency. `naive_magnitude_mismatch` 6535 (27.05%) is not fixed. The tile must show both after deploy. A page that still says only "99.5%" is not this PR.

### B3. Money-ready

`audit_surface_truth.json` `money_ready_count` must stay 0. No class may be sized. Do not restore `futures_momentum` n57 PF 2.6 or `forex_rsi2` n19 PF 2.4 as forward-track leads.

Current ledger (do not mix sources in one cell):

- Intrabar: CRYPTO n=3716 WR 35.8% PF 0.916; FOREX n=612 WR 32.2% PF 0.66; EQUITY n=250 WR 59.2% PF 0.939; COMMODITY n=229 WR 40.2% PF 1.026.
- `strategy_perf_by_class.json`: COMMODITY `futures_momentum` n=681 WR 37.3% PF 0.2488; FOREX `forex_rsi2_mean_reversion` n=1091 WR 39.78% PF 0.3754.

### B4. Prediction markets stay shadow

Not changed. Still true:

- `alpha_engine/data/prediction_market_picks.json` exists (2 picks).
- `audit_dashboard/data/prediction_market_picks.json` does not.
- `kalshi_signals.json` missing at both `alpha_engine/data/` and `prediction_market_agents/data/`.
- `alpha_engine/config.py` still blacklists `prediction_market_consensus`.
- Do not add a sizing path. A later PR may add `PREDICTION_MARKETS_SHADOW_ONLY` and one write path. Do not delete `audit-dashboard.yml` while consolidating the other PM workflows (eight files mention them).

### B5. WIRED_IN

`wired_in_childlike_active_picks.json` remains a static paper snapshot (XLV/LLY/SHY, sizing 0). Not regenerated by this PR. `scratch-hippodraco` 85–100% WR must not be promoted (PBO 0.603, copy-trading rejected).

### B6. GitHub Actions

Do not open fix PRs from the 06:23 "6 failing runs" table. Rechecked 2026-11-16T06:32Z: those resolvable run ids succeeded. `forward-validator.yml` does not exist. Canonical queue work stays in `GHACTIONS_2026-11-16/`.

Publish freshness: last scheduled Unified Audit Dashboard success at audit time was 2026-11-16T03:21:42Z (`43797722088`). Dispatches queued on `dashboard-publish` (`cancel-in-progress: false`). Do not re-add the `push:` trigger.

```bash
gh run list -w "Unified Audit Dashboard" -b main -L 15
```

Healthy: a `schedule` success newer than the previous one, and no pile of cancelled `workflow_dispatch` runs ahead of it.

### B7. Walk-forward Sharpe -65.632

Real value is `alpha_engine/data/walkforward_results.json` `by_class.BOND.oos_sharpe`, not a file under `audit_dashboard/data/`. Not clamped in this PR. A fix must skip or show `n/a` when n<30 or std≈0, in that file's producer.

### B8. PF 999 sentinels

`strategy_perf_by_class.json` still has PF 999 zero-loss sentinels (HoffmanStripTrendStrategy and others). Display blanking in this PR covers the HTML cards that rendered `∞`. The JSON sentinel is not rewritten here. Do not quote 999 as edge.

---

## C. After merge / after the next dashboard deploy

The live page is `audit_dashboard/index.html` uploaded by `audit-dashboard.yml`. `dashboard_enhancements.js` is a separate script tag.

1. Open https://findtorontoevents.ca/audit/ after a **scheduled** (not piled-up dispatch) success.
2. Truth layer must not say "Ghost rows: 0".
3. DB Health tile title must be "Sign consistency (sampled)" and the subtitle must include a magnitude count.
4. Ghost tile must still show the live count. If the next health JSON was produced by this scorer, tier color is red while count ≥ 1000, and `overall.banner_should_show` is true.
5. A page younger than 150 minutes must not say "DATA STALE".
6. Open Forward-Trades W/L column must show `n/a`, not `∞`, when a system has winners and zero losers.
7. Major-goal banner must not cite PF 2.6 or PF 2.4.

If the scheduled run regenerates `index.html` from an older template, re-check that the generator input includes this PR's `template.html`. Both files were patched so a deploy of either copy keeps the same four display fixes.
