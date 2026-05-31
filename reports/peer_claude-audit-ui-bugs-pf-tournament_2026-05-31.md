# Audit UI Bug Investigation — pf.html (cursor_agent__aggressive) + ai-tournament.html

**Date:** 2026-05-31
**Author:** Claude Opus 4.7 (peer subagent)
**Scope:** Two bounded UI bugs reported on findtorontoevents.ca/audit.

---

## BUG 1 — `pf.html?key=cursor_agent__aggressive`: TP/SL fields appear missing

### Symptom
The model portfolio detail page renders "—" in the TP column for every open position. SL renders numerically.

### Investigation

- Renderer: `audit_dashboard/pf.html`
  - Line 363: fetches `./data/pf_portfolio_<safe>.json`.
  - Line 250–251: renders `fmtNum(p.tp_price, 4)` / `fmtNum(p.sl_price, 4)`.
  - Line 120 (`fmtNum`): null/NaN returns `'—'`.
- Live JSON probe — `https://findtorontoevents.ca/audit/data/pf_portfolio_cursor_agent__aggressive.json`:
  - All 14 open positions: `"tp_price": null`, `"sl_price": <number>`.
  - `portfolio.config_snapshot` = `{appetite: "aggressive", pf_ci_lo: 1.129, edge_signal: 0.1143, seeded_from: "ai_tournament_leaderboard.json"}` — does NOT embed the resolved TP/SL config.

### Root cause (upstream, by design — NOT a renderer bug)

`config/portfolio_risk_profiles.json` — `aggressive` block:
```json
"take_profit": {"pct": null, "r_multiple": "trail"},
"stop_loss":   {"atr_mult": 2.5, "pct_floor": -15.0}
```

`tools/portfolios/risk.py:108-120`:
- TP path: when `tp_cfg.pct` is null AND `r_multiple` is the string `"trail"` (not a number), the function falls through with `tp_price = None`.
- This is intentional: aggressive sleeve uses a trailing TP (managed by the live monitor), not a fixed level at entry.

So:
- **Bug class:** UX/labeling, not a missing field.
- **`tp_price = null` is correct semantically** ("trail-managed, no fixed TP").
- The pf.html renderer displays this as `—`, which the user reads as "missing TP".
- SL is *not* missing — `sl_price` is populated from ATR×2.5 floored at −15%.

### Recommended fix (NOT shipped — needs operator review)

Two viable approaches:

**A. Embed config flavor in JSON (preferred, semantically correct).**
- File: `tools/portfolios/engine.py:127-149`
- Change: when assembling the position record, include `tp_mode` (`"fixed_pct"` | `"r_multiple_n"` | `"trail"` | `"none"`) derived from the appetite config used at entry.
- Then `pf.html:250` becomes: `(p.tp_price != null ? fmtNum(p.tp_price,4) : (p.tp_mode === 'trail' ? '<span title="trailing TP — no fixed level at entry">trail</span>' : '—'))`.

**B. Renderer-only fallback (lower confidence — assumes appetite==aggressive ⇒ trail).**
- File: `audit_dashboard/pf.html:250`
- Read `portfolio.risk_appetite` and label `tp_price=null` as "trail" when appetite == "aggressive".
- Brittle if conservative/balanced profiles later add their own trail variants.

**Recommendation:** ship A as a small generator PR after operator review (touches the daily pf_portfolio writer and the schema). I did **not** ship this in this session because it changes data-pipeline output (per the operator's rule "don't ship generator fixes without operator review").

### Action taken
- **Docs only** — this report.
- No PR opened against `tools/portfolios/`.

---

## BUG 2 — `ai-tournament.html`: leaderboard performance data missing

### Symptom
The all-time leaderboard table on `/audit/ai-tournament.html` does not render rows even though pick volume is healthy.

### Investigation

Data probes (live):
| Source | Status | Result |
|--------|--------|--------|
| `data/ai_tournament_leaderboard.json` | OK | `generated_at=2026-05-31T05:00:12Z`, 46 models (36 rank-eligible), all have `rank`, `wr`, `pf`, `n_resolved`, `score`, `tier`, `rank_eligible`. Top of list: `deepseek_v4` rank=1, wr=0.5769, pf=3.457, n=208. |
| `data/ai_tournament_model_summary.json` | OK | `generated_at=2026-05-31T05:00:12Z`, 46 models, populated. |
| `data/ai_tournament_picks_latest.json` | OK | array len=4419, schema includes `model_id, take_profit, stop_loss, status, exit_price, pnl_pct, ...` |

→ **Data is fresh and complete. Bug is in the renderer.**

### Root cause (renderer, JS ReferenceError)

File: `audit_dashboard/ai-tournament.html` line **685** (pre-fix).

```js
ranked.forEach((m, i) => {
  // ... declares: tier, hasWr, wrDisplay, wrClass, hasPf, pfDisplay, pfClass
  tbody.innerHTML += `<tr>
    <td class="rank">#${rankNum}</td>   //  <-- rankNum is NOT declared
    ...
```

`rankNum` is referenced inside the template literal but never declared in scope. This throws `ReferenceError: rankNum is not defined` on the *first* eligible model, aborts the `forEach`, and leaves `tbody` with only the optional banner row (or empty). The model-summary table further down the page still renders (different function), which matches the user's "performance data missing" wording: the *leaderboard* is empty while the rest of the page partially renders.

`grep -n "rankNum"` returns exactly one hit — the broken usage at line 685. There is no shadowing closure variable.

The leaderboard JSON's model records include a `rank` field (1..36), so the obvious fix is `m.rank` with a positional fallback.

### Fix shipped

`audit_dashboard/ai-tournament.html` — added one line before the template literal:

```js
const rankNum = (m.rank != null) ? m.rank : (i + 1);
```

This is the minimal correct fix:
- Uses the authoritative pipeline-assigned `rank` from `ai_tournament_leaderboard.json`.
- Falls back to the loop index (`i+1`) for the approximate / fallback render paths that pass `calcModelStats(...)` output, which may not carry `rank`.
- Does not change any other branch, data shape, or CSS.

### Action taken

- **PR opened** on branch `fix/ai-tournament-rankNum-undefined-2026-05-31` against `main`.
- Single-line JS fix, no schema/data changes.
- Verified all 3 inline `<script>` blocks still parse with `new Function(...)`.

### Verification plan after merge + FTP

- Open https://findtorontoevents.ca/audit/ai-tournament.html
- Confirm: 36 ranked models render in `#lb-body` with `#1 deepseek_v4`, `#2 ...`, etc.
- Confirm: no `ReferenceError: rankNum is not defined` in browser console.
- Confirm: tab counts (`5d`, `3d`, `today`) populate from `allPicks`.

---

## Summary

| Bug | Type | Status | Where |
|-----|------|--------|-------|
| pf.html cursor_agent__aggressive TP missing | Upstream/by-design label gap | Docs only — escalated to operator | `tools/portfolios/engine.py:127`, `config/portfolio_risk_profiles.json` aggressive.take_profit |
| ai-tournament.html performance data missing | JS ReferenceError in renderer | **PR shipped** | `audit_dashboard/ai-tournament.html:685` |
