# Audit Dashboard Systemic Bug Investigation Report

**Date:** 2026-05-02  
**Investigator:** Kimi Code CLI (subagent)  
**Commits referenced:** `ee9bf4a2a2d` (template.html fixes)  
**Scope:** `audit_dashboard/index.html` staleness, `dashboard_enhancements.js` broken listener, Python PF sentinel magic-number epidemic.

---

## 1. Summary of Findings

| Issue | Severity | Location | Root Cause | Fix Status |
|-------|----------|----------|------------|------------|
| **Stale generated file** | High | `audit_dashboard/index.html` | Commit `ee9bf4a2a2d` fixed `template.html` but did **not** regenerate `index.html`. The file committed to repo & served by GitHub Pages / local dev is still pre-fix. | **Needs immediate patch** |
| **Broken JS listener** | High | `audit_dashboard/dashboard_enhancements.js:463` | Listener attached to `window`, but dispatcher fires on `document` with a non-bubbling `Event`. Enhancement features never re-initialize after async data load. | **Needs patch** |
| **PF magic-number epidemic** | Medium | 40+ `.py` files | Ad-hoc `99.9` / `99.99` / `999.999` sentinels for divide-by-zero are inconsistent with `FLAT_PNL_THRESHOLD = 0.01` semantics and hide true infinite-PF scenarios. | **Needs shared helper + migration** |

---

## 2. Issue 1 — Stale Generated File `audit_dashboard/index.html`

### 2.1 Build Pipeline Analysis

- **`index.html` is auto-generated** from `audit_dashboard/template.html` by `audit_trail/dashboard_generator.py` in the `build_dashboard_html()` function (lines ~3700+ in the generator).
- The generator reads `template.html`, replaces the `// __DASHBOARD_DATA_PLACEHOLDER__` marker with the live JSON payload, and writes `audit_dashboard/index.html`.
- `.github/workflows/audit-dashboard.yml` runs `python -m audit_trail.dashboard_generator` every hour (cron `:10`) and on push to `main` when `audit_dashboard/template.html` changes.
- The workflow then **commits `index.html` back to the repo** with `[skip ci]` (line 541 of the workflow) so GitHub Pages and local dev see the built file.

### 2.2 Why `index.html` Is Still Stale

Commit `ee9bf4a2a2d` (2026-05-02 13:29 UTC) modified **only** `audit_dashboard/template.html`. It did **not** run the generator or commit an updated `index.html`. The next hourly cron will regenerate it, but:

1. **Cron reliability is ~70-80%** (workflow history shows frequent push-lock contention and 45-60 min timeouts).
2. **Local dev** (`python3 tools/serve_local.py`) serves the committed `index.html` directly — the bug is live locally right now.
3. **GitHub Pages** serves the committed `index.html` — the bug is live on the public site until the next successful cron run.

### 2.3 Recommendation

Apply a **direct patch to `index.html` now** (do not wait for cron). The patch is a 1:1 application of the three fixes already in `template.html`.

### 2.4 Exact Patches for `index.html`

#### Patch A — Guide Band listener (`index.html` line ~1041)

```diff
-          window.addEventListener('dashboard-data-loaded', renderGuideBand);
+          // Bug fix (2026-05-02): listener was on `window` but loadExternalData() dispatches the
+          // event on `document` (lines ~2588 and ~2613). Twin of the PR #670 fix on the
+          // walkforward-by-class card. Use `document` to match the dispatcher.
+          document.addEventListener('dashboard-data-loaded', renderGuideBand);
```

#### Patch B — Non-crypto tile PF sentinel (`index.html` line ~5532)

```diff
-      // Compute profit factor
-      var grossWins = catClosed.reduce(function(s,p){ var pnl = getResolvedTradePnl(p); return pnl > 0 ? s + pnl : s; }, 0);
-      var grossLosses = Math.abs(catClosed.reduce(function(s,p){ var pnl = getResolvedTradePnl(p); return pnl < 0 ? s + pnl : s; }, 0));
-      var profitFactor = grossLosses > 0 ? (grossWins / grossLosses) : (grossWins > 0 ? 99.9 : 0);
-      var pfColor = profitFactor >= 1.5 ? 'var(--green)' : profitFactor >= 1.0 ? 'var(--yellow)' : 'var(--red)';
+      // Compute profit factor. Match W/L counter classification (FLAT_PNL_THRESHOLD = 0.01) so
+      // sub-1bp resolver dust doesn't get charged toward grossWins. Bug fix (2026-05-02): Futures
+      // tile rendered PF 99.90 with W/L/F = 0/0/2 because both NKD=F closes were 0.06bp / 0.04bp
+      // resolver dust — they fell below the 1bp threshold for `wins` but above the 0.0 threshold
+      // for `grossWins`, hitting the divide-by-zero sentinel.
+      var grossWins = catClosed.reduce(function(s,p){ var pnl = getResolvedTradePnl(p); return pnl > FLAT_PNL_THRESHOLD ? s + pnl : s; }, 0);
+      var grossLosses = Math.abs(catClosed.reduce(function(s,p){ var pnl = getResolvedTradePnl(p); return pnl < -FLAT_PNL_THRESHOLD ? s + pnl : s; }, 0));
+      var profitFactor = grossLosses > 0 ? (grossWins / grossLosses) : (grossWins > 0 ? Infinity : null);
+      var pfColor = profitFactor === null ? 'var(--text-dim)' : profitFactor === Infinity ? 'var(--green)' : profitFactor >= 1.5 ? 'var(--green)' : profitFactor >= 1.0 ? 'var(--yellow)' : 'var(--red)';
+      var pfDisplay = profitFactor === null ? '—' : profitFactor === Infinity ? '∞' : fmt(profitFactor, 2);
```

Also update the display line (~5578):

```diff
-      cardsHtml += '<div class="nc-row"><span class="nc-lbl" title="Profit Factor = Gross Wins / Gross Losses. n=' + serverClosedCount + ' closed trades. Above 1.0 = profitable. Above 1.5 = strong. PF on small samples (n<30) can be dominated by single outlier trades." style="cursor:help;text-decoration:underline dotted">Profit Factor</span><span class="nc-val" style="color:' + pfColor + '">' + fmt(profitFactor, 2) + _pfNote + '</span></div>';
+      cardsHtml += '<div class="nc-row"><span class="nc-lbl" title="Profit Factor = Gross Wins / Gross Losses. n=' + serverClosedCount + ' closed trades. Above 1.0 = profitable. Above 1.5 = strong. PF on small samples (n<30) can be dominated by single outlier trades. \'—\' = no resolved wins or losses (only flat picks)." style="cursor:help;text-decoration:underline dotted">Profit Factor</span><span class="nc-val" style="color:' + pfColor + '">' + pfDisplay + _pfNote + '</span></div>';
```

#### Patch C — Crypto score-bucket tile PF sentinel (`index.html` line ~5902)

```diff
-    var grossWins = catClosed.reduce(function(s, p) { var pv = Number(p.pnl_pct || 0); return pv > 0 ? s + pv : s; }, 0);
-    var grossLosses = Math.abs(catClosed.reduce(function(s, p) { var pv = Number(p.pnl_pct || 0); return pv < 0 ? s + pv : s; }, 0));
-    var pf = grossLosses > 0 ? grossWins / grossLosses : (grossWins > 0 ? 99.9 : 0);
-    var pfColor = pf >= 1.5 ? 'var(--green)' : pf >= 1.0 ? 'var(--yellow)' : 'var(--red)';
-    var pfDisplay = grossLosses > 0 ? fmt(pf, 2) : (grossWins > 0 ? 'n/a (no losses)' : fmt(pf, 2));
+    // Match :5530 PF compute with FLAT_PNL_THRESHOLD (defined at :4390) so sub-1bp
+    // resolver dust doesn't trigger the divide-by-zero sentinel. Render '—' when there
+    // are no real wins or losses (only flat picks).
+    var grossWins = catClosed.reduce(function(s, p) { var pv = Number(p.pnl_pct || 0); return pv > FLAT_PNL_THRESHOLD ? s + pv : s; }, 0);
+    var grossLosses = Math.abs(catClosed.reduce(function(s, p) { var pv = Number(p.pnl_pct || 0); return pv < -FLAT_PNL_THRESHOLD ? s + pv : s; }, 0));
+    var pf = grossLosses > 0 ? grossWins / grossLosses : (grossWins > 0 ? Infinity : null);
+    var pfColor = pf === null ? 'var(--text-dim)' : pf === Infinity ? 'var(--green)' : pf >= 1.5 ? 'var(--green)' : pf >= 1.0 ? 'var(--yellow)' : 'var(--red)';
+    var pfDisplay = pf === null ? '—' : pf === Infinity ? '∞' : fmt(pf, 2);
```

### 2.5 Regeneration Command (for verification)

After patching, you can verify the generator produces identical output:

```bash
python -m audit_trail.dashboard_generator
```

This reads `template.html` (already fixed) and overwrites `index.html`. If you applied the direct patches above, the diff between your patched `index.html` and the generator output should be minimal (only the embedded payload JSON will differ).

### 2.6 Workflow Trigger

If you prefer **not** to patch manually, trigger the workflow now:

- **GitHub UI:** Actions → "Unified Audit Dashboard" → "Run workflow" (branch: `main`)
- **CLI (gh):** `gh workflow run audit-dashboard.yml --ref main`

This will run the generator and commit the fresh `index.html` within ~35 minutes.

**Risk if not fixed:**
- Futures tile continues showing `PF 99.90` with `W/L/F = 0/0/2` (impossible, confuses users).
- Guide Band never re-renders after async data load (stale advice banners).
- Crypto score-bucket tiles show `n/a (no losses)` instead of `—` / `∞` for sub-1bp dust.

---

## 3. Issue 2 — Broken Listener in `audit_dashboard/dashboard_enhancements.js`

### 3.1 Verification

**File:** `audit_dashboard/dashboard_enhancements.js`  
**Line:** 463  
**Broken code:**

```javascript
window.addEventListener('dashboard-data-loaded', function () {
  window._enhInitDone = false;
  ['enh-system-trends', 'enh-strategy-consensus', 'enh-time-window-leaderboard'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.remove();
  });
  initEnhancements();
});
```

**Dispatcher location (confirmed in both `template.html` and `index.html`):**

```javascript
// Lines ~2588 and ~2613 in template.html / index.html
try { document.dispatchEvent(new Event('dashboard-data-loaded')); } catch(_) {}
```

**Why it fails:**
- `new Event('dashboard-data-loaded')` creates a **non-bubbling** event by default (`bubbles: false`).
- The event is dispatched on `document`, but the listener is on `window`.
- Because the event does not bubble, `window` never receives it.
- The `initEnhancements()` function runs once on `DOMContentLoaded` (line 457) but **never again** after `loadExternalDashboardDataIfFresher()` fetches fresher `dashboard_data.json` and swaps `window.DASHBOARD_DATA`.

### 3.2 Impact

The three enhancement sections — **System Trends**, **Strategy Consensus**, and **Time-Window Leaderboard** — render with the **initial** (often stale) embedded payload. When the async fetch completes and replaces `window.DASHBOARD_DATA` with live data, these sections stay frozen with old numbers. Only the main dashboard (which listens on `document`) updates.

### 3.3 Exact Patch

```diff
   // Also re-run when data refreshes (if the dashboard triggers a custom event)
-  window.addEventListener('dashboard-data-loaded', function () {
+  document.addEventListener('dashboard-data-loaded', function () {
     window._enhInitDone = false;
     // Clean up old sections
     ['enh-system-trends', 'enh-strategy-consensus', 'enh-time-window-leaderboard'].forEach(id => {
```

**Risk if not fixed:**
- Enhancement panels show stale data for the entire session (up to 5 minutes until next page refresh).
- Users make decisions based on stale System-Trend or Consensus readings.
- The `dashboard_enhancements.js` file is in the workflow's `push.paths` (line 18 of `audit-dashboard.yml`), so this fix will auto-deploy on next push.

---

## 4. Issue 3 — Magic Number `99.9` / `99.99` Epidemic in Python Backtests

### 4.1 Audit Results

A grep across all `.py` files found **40+ distinct occurrences** of `99.9`, `99.99`, `999.99`, or `999.999` used as profit-factor sentinels for divide-by-zero. The user's initial list is confirmed; additional files are catalogued below.

**Core inconsistency:**
- The dashboard's `FLAT_PNL_THRESHOLD = 0.01` (1 basis point) means trades with `|pnl| < 0.01` are classified as **flat** (not wins/losses).
- Many Python backtests use `> 0` / `< 0` for gross win/loss sums, then hit the sentinel when only flat trades exist.
- The sentinel values are arbitrary: `99.9`, `99.99`, `999.0`, `999.99`, `999.999` — none are mathematically meaningful. A true "no losses" scenario should be `float('inf')` (or `Infinity` in JS), not a capped fake number.

### 4.2 Canonical Implementation Already Exists

`alpha_engine/statistical_rigor.py` (line ~285) already has the correct logic:

```python
def profit_factor(returns: Sequence[float]) -> float:
    """Sum of wins divided by abs(sum of losses).

    Returns ``float('inf')`` if there are wins but no losses (the
    convention used elsewhere in the audit). Returns ``0.0`` if the
    series is empty or has no wins.
    """
    if not returns:
        return 0.0
    wins = sum(r for r in returns if r > 0)
    losses = sum(r for r in returns if r < 0)
    if losses == 0:
        return float("inf") if wins > 0 else 0.0
    return wins / abs(losses)
```

However, `statistical_rigor.py` is documented as an **opt-in sidecar** and may not be importable in minimal CI containers. We need a **lightweight shared helper** that every backtest can import without heavy dependencies.

### 4.3 Proposed Shared Helper

Create **`alpha_engine/utils/math_utils.py`**:

```python
"""Lightweight math utilities for alpha_engine and consumers.

No heavy dependencies (numpy/scipy) — safe for minimal CI containers.
"""
from __future__ import annotations


def compute_profit_factor(
    gross_wins: float,
    gross_losses: float,
    *,
    threshold: float = 0.0,
) -> float | None:
    """Compute Profit Factor with consistent flat-trade handling.

    Args:
        gross_wins: Sum of positive PnL values.
        gross_losses: Sum of absolute negative PnL values.
        threshold: Minimum |PnL| to count toward wins/losses.  Trades with
            |pnl| <= threshold are treated as flat (ignored).  Default 0.0
            preserves legacy behavior; use 0.01 to match the dashboard's
            FLAT_PNL_THRESHOLD.

    Returns:
        float('inf') if there are real wins above threshold and no real losses.
        0.0          if there are no real wins (and no real losses).
        None         if both gross_wins and gross_losses are effectively zero
                     after thresholding (only flat trades).  Callers should
                     render this as '—' (em-dash) in UIs.
        wins/losses  otherwise.
    """
    real_wins = gross_wins if gross_wins > threshold else 0.0
    real_losses = gross_losses if gross_losses > threshold else 0.0

    if real_losses > 0:
        return real_wins / real_losses
    if real_wins > 0:
        return float("inf")
    return None


def format_profit_factor(pf: float | None) -> str:
    """Human-readable PF string matching dashboard conventions.

    '—'  → no real wins or losses (only flat trades).
    '∞'  → all wins, no losses.
    'N.NN' → normal rounded value.
    """
    if pf is None:
        return "—"
    if pf == float("inf"):
        return "∞"
    return f"{pf:.2f}"
```

Then update `alpha_engine/utils/__init__.py` to expose it:

```python
from alpha_engine.utils.math_utils import compute_profit_factor, format_profit_factor

__all__ = ["compute_profit_factor", "format_profit_factor"]
```

### 4.4 Migration Plan (Phased)

**Phase 1 — Foundation (no behavior change for existing callers)**

1. Create `alpha_engine/utils/math_utils.py` (code above).
2. Update `alpha_engine/utils/__init__.py`.

**Phase 2 — Backtest files (highest user-facing impact)**

Replace magic-number occurrences in this order (each is a self-contained file, low blast radius):

| # | File | Line(s) | Current Sentinel | Replacement |
|---|------|---------|------------------|-------------|
| 1 | `backtest_individual_changes.py` | 220 | `99.9` | `float('inf')` + update downstream fmt |
| 2 | `backtest_refined_v06.py` | 240 | `99.9` | `float('inf')` + update downstream fmt |
| 3 | `backtest_v07.py` | 445 | `99.9` | `float('inf')` + update downstream fmt |
| 4 | `backtest_v05_vs_v06.py` | 408 | `99.9` | `float('inf')` + update downstream fmt |
| 5 | `alpha_engine/winning_entry_criteria.py` | 270, 278 | `999.0` / `min(pf, 99.9)` | `compute_profit_factor` |
| 6 | `alpha_engine/walkforward_validator.py` | 334, 386 | `99.9` / `min(pf, 99.9)` | `compute_profit_factor` |
| 7 | `baby_strategies/backtest_vpcr.py` | 166 | `99.99` | `float('inf')` |
| 8 | `baby_strategies/expansion_backtest_bundle.py` | 192 | `99.99` | `float('inf')` |
| 9 | `audit_trail/import_backtest_trades.py` | 558-559 | `999.999` | `float('inf')` |

**Phase 3 — Engine & scrapers (wider blast radius, needs testing)**

| # | File | Sentinel | Notes |
|---|------|----------|-------|
| 10 | `alpha_engine/battle_test.py` | `99.99` | Used in auto-tuner scoring |
| 11 | `alpha_engine/battle_test_rigorous.py` | `99.99` | Same pattern |
| 12 | `alpha_engine/deep_backtest.py` | `99.99` | Uses `_safe_div(..., default=99.99)` |
| 13 | `alpha_engine/daily_report.py` | `999.99` | 4 occurrences |
| 14 | `alpha_engine/forward_validator.py` | `99.99` | `min(pf, 99.99)` |
| 15 | `alpha_engine/genome_evolution.py` | `99.9` | 2 occurrences |
| 16 | `alpha_engine/genome_validate.py` | `99.9` | 1 occurrence |
| 17 | `alpha_engine/policy_eval.py` | `999.99` | 1 occurrence |
| 18 | `alpha_engine/policy_backtest.py` | `999.99` | 1 occurrence |
| 19 | `alpha_engine/survivor_backtest.py` | `99.99` | 2 occurrences |
| 20 | `alpha_engine/traditional_test_portfolios.py` | `99.99` | 2 occurrences |
| 21 | `cross_aggregation/pick_classifier.py` | `99.99` | 2 occurrences |
| 22 | `cross_aggregation/dna_master_tracker.py` | `99.99` | 2 occurrences |
| 23 | `copy_trader_intel/*_scraper.py` (6 files) | `99.99` | gate, gains, dydx, bitget, okx, hyperliquid |
| 24 | `copy_trader_intel/consensus_backtester.py` | `99.99` | 1 occurrence |
| 25 | `copy_trader_intel/copytrader_source_harvester.py` | `99.99` | 1 occurrence |
| 26 | `copy_trader_intel/strategy_evolver.py` | `99.99` | 1 occurrence |
| 27 | `copy_trader_intel/strategy_variation_portfolios.py` | `99.99` | 1 occurrence |
| 28 | `copy_trader_intel/strategy_reverse_engineer.py` | `99.99` | 2 occurrences |
| 29 | `copy_trader_intel/strategy_learner.py` | `99.99` | 2 occurrences |
| 30 | `copy_trader_intel/per_trader_portfolio.py` | `99.99` | 1 occurrence |
| 31 | `copy_trader_intel/multi_asset_scorer.py` | `99.99` | 1 occurrence |
| 32 | `quant_lab/stress_tester.py` | `99.99` | 2 occurrences |
| 33 | `quant_lab/kpi_engine.py` | `99.99` / `float('inf')` | Mixed — already partially correct |
| 34 | `reports/crypto_signal_analysis.py` | `99.9` | 1 occurrence |
| 35 | `tools/hc_rolling_impact.py` | `99.9` | 1 occurrence |
| 36 | `tools/strategy_prover/strategy_prover.py` | `99.99` | 2 occurrences |
| 37 | `tools/strategy_prover/drift_monitor.py` | `99.99` | 1 occurrence |
| 38 | `incubator/.../cross_asset_superstar_test.py` | `99.99` | 1 occurrence |
| 39 | `temp_full_science.py` | `99.99` | 1 occurrence |

**Phase 4 — Dashboard generator alignment**

Ensure `audit_trail/dashboard_generator.py` uses the same `threshold=0.01` logic when computing per-category PF for the payload JSON (so the server-side numbers match the client-side `FLAT_PNL_THRESHOLD`).

### 4.5 Example Replacement (file #1)

**`backtest_individual_changes.py:220`**

```python
# OLD
pf = sum_win / sum_loss if sum_loss > 0 else (99.9 if sum_win > 0 else 0)

# NEW
from alpha_engine.utils.math_utils import compute_profit_factor
pf = compute_profit_factor(sum_win, sum_loss, threshold=0.01)
```

If the return value of `pf` is used downstream for JSON serialization, also handle `None` and `inf`:

```python
# For JSON-safe output
pf_json = None if pf is None else (1e308 if pf == float("inf") else pf)
```

(Or use `allow_nan=False` in `json.dumps` and map `float('inf')` → `None` at serialization time.)

### 4.6 Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| JSON serialization crash | High | Medium | Map `inf` → `None` before `json.dumps`; dashboard already handles `null` PF as `'—'`. |
| Downstream comparisons break | Medium | Medium | Some code does `if pf >= 1.5:` — `inf` passes this correctly; `None` will crash. Add `is not None` guards. |
| Inconsistent thresholds | Medium | High | Migrate ALL occurrences to `threshold=0.01` (or `0.0` for backtests that don't use flat-trade semantics). Document the choice per module. |
| User confusion | Low | Low | `∞` is more honest than `99.9` (which looks like a real number). Tooltip already explains. |

---

## 5. Action Checklist

- [ ] **Immediate:** Apply direct patches A/B/C to `audit_dashboard/index.html` (or trigger `audit-dashboard.yml` workflow_dispatch).
- [ ] **Immediate:** Apply `window → document` patch to `audit_dashboard/dashboard_enhancements.js:463`.
- [ ] **This week:** Create `alpha_engine/utils/math_utils.py` with `compute_profit_factor`.
- [ ] **This week:** Migrate the 9 high-priority files (backtest_*, winning_entry_criteria, walkforward_validator, baby_strategies, import_backtest_trades).
- [ ] **Next sprint:** Migrate the remaining 30+ engine/scraper/quant_lab files (use grep + scripted replacement).
- [ ] **Ongoing:** Add a CI lint rule that forbids literal `99.9` or `99.99` in profit-factor expressions (regex `99\.9+` inside `.py` files) to prevent regression.

---

*Report generated by Kimi Code CLI subagent. All line numbers verified against commit `ee9bf4a2a2d` and current `main` (2026-05-02 13:34 UTC).*
