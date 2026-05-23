# Task: Dashboard Template Fixes (P0/P1)

## Repo
`C:\findtorontoevents_antigravity.ca`

## Constraints
- NEVER edit `audit_dashboard/index.html` (auto-generated)
- NEVER run `audit_trail/dashboard_generator.py` locally
- Edit `audit_dashboard/template.html` only
- Run `py_compile audit_trail/quality_gates.py` after any gate edits
- Do NOT push — let operator review first

---

## FIX 1 — CRITICAL: Static MAJOR GOAL banner (template.html lines 887-892)

Replace the 6 stale asset-class spans with live data from 2026-05-15T23:35Z.

**Current spans** contain wrong numbers like PF 1.42 for EQUITY, PF 1.72 for BOND, PF 2.08 for COMMODITY, PF 0.28 for FOREX, etc.

**Replace with:**
```html
<span data-mg-class="EQUITY"><strong style="color:#22c55e">EQUITY</strong> &mdash; T2 candidate (PF 1.55, WR 51.4%, n=426). Scale.<span class="metric-tip" tabindex="0" role="img" aria-label="EQUITY capped vs raw PnL caveat" data-metric-tooltip="EQUITY system_clean_metrics shows raw PnL 363.32 vs capped (10% per-pick) PnL 35.71 — a 10x gap that means 1-2 outlier wins drive most of the headline edge. The numbers above use the capped basis. For sizing decisions, weigh the capped figure; do not assume raw PnL persists out-of-sample. Source: dashboard_data.json::system_clean_metrics.alpha_engine.">&#9432;</span></span>
<span data-mg-class="CRYPTO"><strong style="color:#f59e0b">CRYPTO</strong> &mdash; PF 1.30, WR 46.3%, n=8115. Sub-T2; <code>quan_engine</code> / <code>luxalgo_filters</code> drag; 12 crypto_soc baby_strats quarantined (4-6&sigma; WR decay).</span>
<span data-mg-class="ETF"><strong style="color:#06b6d4">ETF</strong> &mdash; PF 1.33, WR 57.4%, n=108. Charter floor met; lift PF to 1.5 for T2.</span>
<span data-mg-class="COMMODITY"><strong style="color:#22c55e">COMMODITY</strong> &mdash; <strong style="color:#22c55e">PF 2.48</strong>, WR 61.2%, n=345 (post-resolver-v2). T2 PF confirmed ✓; WR exceeds 50% ✓; verify MDD for full T2.</span>
<span data-mg-class="FOREX"><strong style="color:#ef4444">FOREX</strong> &mdash; PF 0.86, WR 55.0%, n=309 (post-resolver-v2). Sub-floor (PF&lt;1.0). Mutation protocol active; LONG-direction blocks pending 2026-05-22 re-eval.</span>
<span data-mg-class="BOND"><strong style="color:#ef4444">BOND</strong> &mdash; PF 0.66, WR 54.5%, n=11. Sub-floor (PF&lt;1.0); n&lt;100 charter floor. Scanner active; accumulating picks.</span>
```

Also update the `<span id="major-goal-asof">` timestamp line (line 893):
```html
<span id="major-goal-asof" style="color:#a5b4fc">Data updated 2026-05-16 &mdash; source: asset_class_health (resolved_n, post-resolver-v2).</span>
```

---

## FIX 2 — HIGH: N_INSUFFICIENT warning on BOND walk-forward Sharpe

Find the JS that renders the OOS Sharpe cell in the walk-forward table. Add a conditional: if the class is BOND (or if `worst_fold_wr == 0` and `folds <= 10`), append a ⚠ badge styled in amber:

```
⚠ N_INSUF
```

with tooltip: `"Sharpe artifact: n=11 total picks; 2-pick test folds produce std≈0 → Sharpe→∞. Not indicative of real OOS edge."`

Color: amber (#f59e0b). Do NOT hide or zero out the number — just flag it.

---

## FIX 3 — ALSO in template.html line ~12817: update stale BOND status note

Update the BOND stat note from the old n=18/PF 1.72 values to:
```
stat: 'n=11 (resolved_n, 2026-05-16)',  note: 'PF 0.66, WR 54.5% (resolved_n=11, post-resolver-v2, 2026-05-15T23:35Z). Sub-floor; scanner active accumulating picks. Walk-forward Sharpe 16.224 is N_INSUFFICIENT artifact (2-pick test folds at n=11).'
```

---

## Test plan
1. `grep -c "PF 1.42\|PF 1.72\|n=88\|PF 2.08\|n=816\|n=1249\|PF 0.28\|n=18\|52\.8\%\|44\.8\%\|53\.4\%\|48\.7\%\|45\.6\%\|55\.6\%" audit_dashboard/template.html` → must return 0
2. `grep -c "PF 1.55\|PF 1.30\|PF 1.33\|PF 2.48\|PF 0.86\|PF 0.66" audit_dashboard/template.html` → must return ≥ 6
3. `grep -c "N_INSUF\|N_INSUFFICIENT" audit_dashboard/template.html` → must return ≥ 1
4. `grep "BOND.*PF" audit_dashboard/template.html` → must NOT show "1.72"
