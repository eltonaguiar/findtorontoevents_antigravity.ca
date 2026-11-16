# `/audit` live truth check — 2026-11-16 (picks, WIRED, prediction markets, JS errors, stale boxes, DB health)

**Audited:** `https://findtorontoevents.ca/audit/` (v99.0), its live payload `data/dashboard_data.json`
(24,880,077 B, `generated_at 2026-11-16T03:03:33Z`), the deployed HTML/JS bundles, and
`data/db_health.json` (02:47:34Z).

**Method:** live HTTP fetches; a headless Chromium run (3 passes) capturing console errors, failed
requests, and post-render DOM state; Python parsing of the payload; in-page `fetch`/`JSON.parse`
probes to separate "endpoint broken" from "JS broken".

**Caveat:** this worktree (`deliver-docs`) is ~115 commits behind `origin/main`; the local
`dashboard_data.json` is from 2026-10-23. All findings below come from the **live deployed**
artifacts, not the local copies. No repo code was changed by this audit.

---

## TL;DR

1. Two dashboard panels are down for **one shared reason**: `strategy_ic_analysis.json` contains
   `"pf": Infinity` and `money_ready_verdict.json` contains `"r_score": NaN`. Python's `json` accepts
   those literals; browsers' `JSON.parse` rejects the whole file. That is the entire IC "endpoint may
   be unreachable" error and the Money-Ready "No data available / unknown" tile.
2. **Smart Picks are structurally zero**, not merely unlucky: of 4,211 raw active picks, `smart_score`
   is present on **0**, `forward_validated` on 27, `at_issue_trust_tier` on 0. 4,211 → 20 is the gate
   working as written, on inputs almost nothing supplies.
3. **Prediction markets are emitting but never surface**: 43 Kalshi/Polymarket-derived rows exist in
   `active_raw` (35 OPEN) across 8 sources — **0 reach the 20 active picks**.
4. **The hypothesis tracker is not wired at all**: 0 mentions in the payload, live
   `hypothesis_registry.json` is a 404, the local file is 44 bytes, and `dashboard_generator.py`
   never loads it.
5. **The DB-health box contradicts the page's own remediation box**: `db_health.json` reports
   **22,947 ghost rows** in 10 cohorts with `ok: true / green`, while `template.html:857` states
   "Ghost rows: 0 (was 22,947)" and line 911 asserts "DB health GREEN: ghost rows 0".
6. **The freshness banner cannot go red on a broken source**: with Money-Ready unparseable it printed
   "✅ ALL SOURCES CURRENT" directly above "No data available / unknown".
7. Two page scripts are **404 on live** (`forward_clock.js`, `excess_column.js`) even though `main`
   already restores them (commit `71342d43`) — a deploy gap, not a code gap.

---

## 1. Picks reality: active, closed, per class

### Active (the 20 shown)

| Class | n | Sources |
|---|---|---|
| ETF | 10 | `etf_all_strategies` ×10 |
| CRYPTO | 3 | `inverse_mutations`, `tsom_strategy` ×2 |
| EQUITY | 2 | `regime_terminal` ×2 |
| FOREX | 2 | `copy_trader` ×2 (both `forward_validated=True`) |
| COMMODITY | 2 | `commodity_carry_momo` ×2 |
| FUTURES | 1 | `ml_gatekeeper` |
| BOND | 0 | — |

All 20 are <4h old. **ETF is 50% of the visible book from a single generator** — worth a
concentration note on the page; the dashboard shows 10 "active" ETF rows but ETF closed history is
2W/5L, PF 0.40.

### Raw vs gated

- `picks.active_raw` = **4,211**; `picks.active` = **20**; `picks.smart_picks` = **0**.
- Raw by class: CRYPTO 3,589 · FOREX 291 · EQUITY 193 · COMMODITY 65 · ETF 49 · BOND 11 ·
  FUTURES 11 · SPORTS 2.
- Top raw source: `inverse_mutations` at 2,322 rows (55% of all raw picks) — one emitter dominates
  the input universe.
- Gate-field coverage across 4,211 raw rows: `forward_validated` **27**, `smart_score` **0**,
  `elite_score` 230, `trust_tier` 306, `at_issue_trust_tier` **0**.

**Reading:** the 4,211→20 drop is not a bug in the gate; it is the gate being fed fields nobody
stamps. "0 smart picks" will persist until emitters write `smart_score`/`at_issue_trust_tier` at
issue time. Fixing supply matters more than loosening the gate.

### Closed

- `summary`: total 14,579 · valid 7,791 · WR 41.2% · `total_pnl_pct` −85.95 · compounded −99.0 ·
  PF 0.92 · zero-pnl 133 · auto-expired 8,978 · integrity-excluded 5,983.
- `recent_closed`: 3,500 rows, 3,371 unique on `(symbol, source, closed_at)`; statuses LOST 2,006 /
  WON 1,454 / CLOSED 40; 40 rows (1.1%) carry null/zero pnl.
- Page tile says **Closed Picks 1,661**; payload has 3,500 recent / 7,791 valid / 14,579 total.
  1,661 matches none of them — the tile's cohort is undocumented (see §7).

---

## 2. WIRED IN (childlike) on main vs live

- `data/wired_in_childlike_active_picks.json`: `generated_at 2026-11-15T01:50Z`, **3 picks**
  (XLV LONG ETF, LLY LONG EQUITY, SHY LONG BOND), `trust_tier: UNPROVEN`, `paper_only: true`.
- In the payload those three appear only in the raw/shadow surface; **none is in the active 20**.
- The page renders "0 proven - 20 sandbox (4189 gated out)" and "Verified Alpha 0 · 0 smart".
- Local closed companion file is 106 B (empty) → "0 proven" is correct, not a rendering failure.

**Verdict:** WIRED shadow monitoring is behaving exactly as designed (paper-only, unproven, never
sized). It is not feeding active picks and should not be reported as if it were.

---

## 3. Prediction markets (Kalshi / Polymarket)

- `active_raw` contains **43** PM-derived rows: `forward_signals` 7, `kalshi_signal_agent` 4,
  `genetic_programmer` 4, `prediction_market_agents` 3, `mape_evolver` 3,
  `copy_trader_polymarket` 2, `prediction_market` 2, `prediction_market_consensus` 2.
  Statuses: OPEN 35, SL_HIT 5, TP_HIT 2, EXPIRED 1.
- **Active 20: 0 PM rows.** They are emitted, then gated out like everything else.
- Payload-wide mentions: `kalshi` 125, `polymarket` 47, `prediction_market` 88 — concentrated in
  `picks`, `consensus`, `conflicts`, `pcg5_shadow_summary`, not in the active book.
- `predictions_leaderboard` has exactly **1** `polymarket` row: 45 predictions, **95.6% WR**, but
  **avg_pnl −47.57%**. A 95.6% win rate paired with a large negative mean is internally
  inconsistent and should not be displayed as a performance claim.
- Missing artifacts: `alpha_engine/data/kalshi_signals.json`, `prediction_market_agents/data/*.json`
  (kalshi/whale/momentum/consensus) are absent locally; `copy_trader_intel/data/polymarket_picks.json`
  exists (2 picks, 02:34Z).

**Verdict:** PM is producing signal and reaching the shadow/consensus layers, but contributes
nothing to the active surface. Two sub-issues: missing `kalshi_signals.json`, and the
leaderboard row whose WR and PnL disagree.

---

## 4. Hypothesis tracker

- Live `data/hypothesis_registry.json` → **404**. Payload: **0** occurrences of "hypoth".
- `audit_trail/data/hypothesis_registry.json` is 44 B; `dashboard_generator.py` never loads it.
- Only trace on the page is a static H-119 mention in the template.

**Verdict:** not feeding the dashboard in any form. Either wire it (JSON_PICK_SOURCES / a research
panel) or delete the stale mention so the page stops implying coverage it doesn't have.

---

## 5. Render bugs — one root cause, two symptoms

### 5a. Strategy IC panel

Page shows: "Failed to load IC analysis data. The strategy_ic_analysis.json endpoint may be
unreachable or the file may be missing."

Reality: HTTP **200**, `application/json`, 42,632 B, correct shape (`by_class` for 7 classes,
`n_strategies 112`, `bonferroni_corrected_alpha 0.000316`). In-page probe:

```
JSON.parse -> SyntaxError: Unexpected token 'I', ..."pf": Infinity
```

`Infinity` is not a JSON token. Python's `json.load` accepts it (so every Python-side check says
"valid JSON"); the browser rejects the entire document, so the panel's `.catch()` fires. The element
ids it needs (`ic-analysis-summary`, `ic-analysis-body`) are present — it is not a DOM bug.

### 5b. Money-Ready freshness tile

Same failure: `money_ready_verdict.json` is 200 / 46,251 B / fresh (`generated_at 03:02Z`) and
contains `"r_score": NaN`. `JSON.parse` fails, `dashboard_freshness.js`'s `extract()` never runs, the
row renders "No data available / unknown". The JSON is fine for Python consumers, dead for the page.

### Fix sites (verified recipe)

`audit_trail/dashboard_generator.py` already contains `_sanitize_for_json()` (≈line 378) with a
docstring describing this exact 2026-04-27 outage — these two artifacts simply bypass it.

- `alpha_engine/money_ready_verdict.py:1783` — `print(json.dumps(out, indent=2))` uses Python's
  `allow_nan=True` default. Change to sanitize + `allow_nan=False`:
  ```python
  from audit_trail.dashboard_generator import _sanitize_for_json
  print(json.dumps(_sanitize_for_json(out), indent=2, allow_nan=False))
  ```
- `strategy_ic_analysis.json` — **no committed builder exists in this tree** (grep finds only
  `tools/deploy_audit_files.py:38` and the nightly's guarded `git add`; the builder was removed
  2026-06-12 because `build_ic_analysis.py` never existed). The live file is nonetheless regenerated
  and still emits `inf`. Add a strict-JSON guard at the writing boundary, or stop shipping the
  artifact until a builder exists.

Recipe validated on the live files`"` — `json.loads(..., parse_constant=lambda c: None)` then
`json.dumps(..., allow_nan=False)` yields 42,628 B / 46,252 B (essentially unchanged) and both now
pass Node's `JSON.parse`.

### 5c. JavaScript errors on the live page

Headless run: **8 console errors, 0 page errors**.

| Error | Source | Impact |
|---|---|---|
| 404 `forward_clock.js`, 404 `excess_column.js` | deploy gap (main fixed in `71342d43`) | forward clock + excess column dead |
| `TypeError: Cannot read properties of null (reading 'name')` at `dashboard_enhancements.js:156` | `(p.source_strategies \|\| []).map(s => s.name ...)` when the array contains `null` | Operator Review Today section fails to render |
| 2× CORS block on cryptocompare for HYPE | live-price enrichment | HYPE shows no live price |
| 1 network abort + assorted 404s | asset fetches | cosmetic |

Fix for 5c-TypeError is one line: `.filter(Boolean)` before `.map(...)` in
`dashboard_enhancements.js` (and the same guard anywhere else `source_strategies` is mapped).

---

## 6. Freshness panel / stale boxes

Observed at 02:47Z (user snapshot): "⚠ STALE SOURCES DETECTED" — Edge Stability 3h10m,
AI Leaderboard 18h45m, Dashboard Data 1h, Money Ready "No data available", Swarm 162d.
Observed at 05:1xZ: "✅ ALL SOURCES CURRENT" — Edge Stability 3h23m, AI Leaderboard 26m,
Dashboard Data 8m, **Money Ready still "No data available / unknown"**.

Two defects:

1. **Unknown ≠ stale.** The banner is computed only from sources whose timestamp parsed, so an
   unparseable source (Money Ready) is invisible to the verdict and the header can claim
   "ALL CURRENT" while a row says "No data available". Unknown must be treated as failing.
2. **Swarm really is dead.** `swarm_picks.json` newest row is **2026-06-06** (340 rows,
   2026-05-11 → 2026-06-06). 162 days is accurate; the generator has stopped.

Genuinely fresh: `dashboard_data.json` (8m), `edge_stability/edge_stability_index.json`
(as_of 00:54Z), `ai_leaderboard/ai_leaderboard_index.json` (as_of 09:18Z then regenerated),
`db_health.json` (02:47Z).

---

## 7. Numbers that disagree on the same page

| Metric | Page tile | Payload summary |
|---|---|---|
| Win rate | 44.1% | 41.2% |
| Profit factor | 1.16 | 0.92 |
| Closed picks | 1,661 | 7,791 valid / 14,579 total |
| Σ trade % | +337.88% | — |
| Compound return | −92.44% | −99.0% |

The page recomputes client-side over a filtered cohort; the summary aggregates a different one.
Both can be "right" and still mislead, because neither tile names its cohort or n. Same pattern in
"Smart Snapshot 75.4%" / "Swing 75% (65)" next to an aggregate 44.3%. Recommendation: put cohort +
n in every KPI label (e.g. "WR 44.1% · n=1,661 · deduped, pnl-valid").

---

## 8. DB Health box (source: `data/db_health.json`, 02:47:34Z)

Overall: `checks_run 5, passed 5, any_red false, harness_healthy true`, elapsed **538 s**.

| Check | Result | Note |
|---|---|---|
| `won_pnl_contradiction` | green | TP_HIT n=7,001 avg +3.41; SL_HIT n=3,866 avg −3.20; LOST n=5,556 avg −1.76 |
| `pnl_integrity` | green | 24,158 sampled, 130 sign mismatches (0.54%) — but **naive magnitude mismatch 6,535 (27.05%)** |
| `status_standardization` | green | 0 non-canonical |
| `ghost_rows` | **green despite 22,947 ghosts** | 10 cohorts, e.g. MEMECOIN `meta_strategy` DOGEUSDT LONG 3,569 rows / 1 distinct entry; same symbol 3,160 rows / 4 entries |
| `open_bloat` | green | **open_count 91,776 vs active_count 21**, total 144,483; last terminal write 02:26Z; not frozen |

Two contradictions fall out:

- `template.html:857` — "Ghost rows: 0 (was 22,947)" and line 911 — "DB health GREEN: ghost rows 0"
  **versus** the live check reporting 22,947 with `ok: true`. Either the check's threshold treats
  "no *new* ghosts" as pass, or the static copy is wrong. Both cannot stand.
- **91,776 OPEN rows against 21 live active picks** is a 4,370× ratio; the dashboard's "active 20"
  is consistent with `active_count 21`, so the resolver is fine and the backlog is the issue.
- `ghost_rows` alone took **503.9 s** of the 538 s harness — a single hourly check consuming ~9
  minutes for a query whose result is then ignored by the verdict.

---

## 9. What is healthy (don't "fix" these)

- `money_ready_verdict.json` content itself is fresh (03:02Z) and sane: 10 classes, all
  `NOT_READY`, `watch: [COMMODITY]`; FOREX wr .3219 / pf .6596 / n 612; CRYPTO .3576 / .9163 / n 3716;
  EQUITY .592 / .9392 / n 250.
- `audit_surface_truth.json` fresh; `strategy_ic_analysis` content is statistically coherent
  (34 positive / 37 negative strategies, Bonferroni alpha 0.000316) — only its encoding is broken.
- Forward validator freshness 0h; `won_pnl_contradiction` clean; statuses standardized.
- WIRED shadow pipeline, paper-only and unproven — correct by design.
- All 20 active picks are <4h old; no stale active rows.

---

## 10. Prioritized actions

**P0 — one-line correctness, unblocks two panels**

1. `alpha_engine/money_ready_verdict.py:1783` → sanitize + `allow_nan=False` (snippet in §5).
2. Strict-JSON gate for `strategy_ic_analysis.json` at its write/deploy boundary
   (`tools/deploy_audit_files.py:38`), or add the missing builder.
3. `dashboard_enhancements.js` — `.filter(Boolean)` on `source_strategies` (§5c TypeError).
4. Deploy the two restored script tags from `71342d43` (`forward_clock.js`, `excess_column.js`).

**P1 — stop the page lying**

5. Freshness banner: treat unparseable sources as failing (never "ALL CURRENT" with a "No data" row).
6. Reconcile the ghost-row claim: make `ghost_rows` fail above a threshold, and correct
   `template.html:857/911` to match `db_health.json` (or remove the static assertion).
7. Label every KPI tile with cohort + n (§7); decide one canonical closed-picks count.
8. Flag the `polymarket:consensus` leaderboard row (95.6% WR, −47.57% avg PnL) as inconsistent
   instead of ranking it.

**P2 — supply, not gates**

9. Emit `smart_score` / `at_issue_trust_tier` at issue time, or Smart Picks stays at 0 by construction.
10. PM path: restore `kalshi_signals.json`; document why all 43 PM raw rows are gated out.
11. Hypothesis registry: wire or delete the stale H-119 reference.
12. Retire or restart `swarm_picks` (162d dead) and `BOND` emitters; the 60–87h silent-emitter
    warnings (`forward_signals`, `orphan_emitter_bond/etf`, `bond_scanner`,
    `growth_stock_screener`) are accurate.
13. Investigate the 91,776 OPEN rows vs 21 active — resolver throughput/backlog, not a display bug.

---

## Evidence appendix (reproducible)

```bash
# 1. payload truth
curl -s https://findtorontoevents.ca/audit/data/dashboard_data.json -o /tmp/dd.json
python3 -c "import json;d=json.load(open('/tmp/dd.json'));p=d['picks'];print(len(p['active']),len(p['active_raw']),len(p['smart_picks']))"

# 2. the actual browser failure (Python accepts these files; Node does not)
curl -s https://findtorontoevents.ca/audit/data/strategy_ic_analysis.json -o /tmp/ic.json
node -e "JSON.parse(require('fs').readFileSync('/tmp/ic.json','utf8'))"   # Unexpected token 'I'
curl -s https://findtorontoevents.ca/audit/data/money_ready_verdict.json -o /tmp/mr.json
node -e "JSON.parse(require('fs').readFileSync('/tmp/mr.json','utf8'))"   # Unexpected token 'N'

# 3. health box source
curl -s https://findtorontoevents.ca/audit/data/db_health.json | python3 -m json.tool | head -40
```

Headless probe: Chromium via Playwright, 15–22 s settle, capturing `console`, `pageerror`,
`response.status>=400`, then in-page `fetch` of each `data/*.json` and a `JSON.parse` of the body.
Confirmed 8 console errors, 0 page errors, and the two `SyntaxError`s above.

**Not verified / limitations:** no logged-in or DB-side checks were run; MySQL was not queried
directly (all DB health figures come from `db_health.json`); the local worktree is 115 commits
behind `main`, so no local unit tests were run against these artifacts; the IC artifact's producer
could not be identified in this tree.
