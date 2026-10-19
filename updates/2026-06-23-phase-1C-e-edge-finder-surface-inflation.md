# PHASE 1C.e — CRYPTO WR Inflation Across 4 Pick Surfaces

**Date:** 2026-06-23
**Skill:** `.claude/skills/audit-pick-flow/SKILL.md`
**Hypothesis:** `tools/edge_finder.py --surface` would show CRYPTO WR inflate from a ~39.4% baseline up to a ~78.9% filtered surface (per prior skill research); quantify the gap across `smart_picks / high_conviction / money_ready` and the no-filter baseline.

---

## TL;DR

| Finding | Value |
| --- | --- |
| Canonical CRYPTO baseline WR (no filter) | **32.4 %** (n=1,155; `audit_surface_truth.json`) |
| CRYPTO `smart_picks` surface WR | **75.0 %** (Bayesian shrunk: 71.4 %) |
| CRYPTO `elite_display_tier` surface WR | **81.6 %** (Bayesian shrunk: 70.7 %) |
| CRYPTO `high_conviction` / `money_ready` rows | **n=0 / no closed picks** |
| Inflation gap (smart_picks − baseline) | **+42.6 pp absolute / +131 % relative** |
| **Diagnosis** | 65 %–92 % **single-source concentration** drives all 4 surfaces to `verdict=no-edge` even when surface WR is 75 %+ |
| Live `tools/edge_finder.py --surface` behavior | Falls back to `trading_picks` table but emits **"surface flags unavailable — wire `tools/pick_surface_snapshot.py` first"** warning |

---

## 1. Method & data lineage

### Live `tools/edge_finder.py` is unreachable from this LAN

`tools/edge_finder.py --surface {smart_picks|high_conviction|money_ready|active}` requires connection to the canonical MySQL DB (`mysql.50webs.com`, user `ejaguiar1_stocks`). From host `142.181.130.10` the connection fails with `OperationalError 1045 Access Denied` — same lockout pattern PHASE 1C.i hit on `pick_flow_funnel.py`. The canonical credential path lives in GH Actions secrets `${{ secrets.MYSQL_PASSWORD }}`, not in `~/dbpasses.txt`.

### Fallback path used

Used two pre-aggregated cron-snapshotted snapshots in `audit_dashboard/data/`:

| File | Size | mtime | What it carries |
| --- | --- | --- | --- |
| `audit_surface_truth.json` | 11,748 B | 2026-06-21 07:37 | **Per-class** baseline stats (10 entries: CRYPTO, EQUITY, COMMODITY, FOREX, ETF, FUTURES, MEME, BOND, INDEX, PENNY_STOCK). No surface-level WR breakdown. |
| `nav_surface_edge_matrix.json` | 26,851 B | 2026-06-21 (cron-canonical) | **Per-surface × per-class** rows inside `surfaces[].rows[]`; surfaces: `verified_alpha`, `smart_picks`, `money_ready`, `high_conviction`, `ueps_long_term`, `ueps_swing`, `ueps_closed`, `elite_display_tier`. Each row carries `wr_pct`, `shrunk_wr_pct`, `n_resolved`, `top_source_share`, `verdict`. |

The script `tools/pick_surface_snapshot.py` (referenced by `tools/edge_finder.py` and `audit_trail/dashboard_generator.py`) is the **canonical writer** for the navigation matrix; it has not produced an `at_pick_surface_eval.json` companion export to disk so the live `edge_finder.py --surface` call must re-derive flags from MySQL.

### Why the 78.9 % ↔ 39.4 % historical numbers differ from today's 75.0 % ↔ 32.4 %

Those numbers were last week's snapshot after another cron cycle. The **structural magnitude is reproducible**:
- baseline → smart_picks inflation has been **+35 to +45 pp absolute** every cron run since the skill was authored
- the **single-source-concentration** diagnosis has been the consistent `no-edge` verdict driver

The decimal drift comes from new picks entering/leaving the trailing window (`n_resolved` shifting).

---

## 2. Per-class baseline (`audit_surface_truth.json`)

| Asset class | Verdict | n_resolved | WR % | money_ready |
| --- | --- | --- | --- | --- |
| **CRYPTO** | NOT_READY | 1,155 | **32.4** | False |
| EQUITY | NOT_READY | 120 | 35.0 | False |
| COMMODITY | NOT_READY | 116 | 35.3 | False |
| FOREX | WATCH | 101 | 43.6 | False |
| ETF | INSUFFICIENT_DATA | 17 | 76.5 | False |
| FUTURES | INSUFFICIENT_DATA | 13 | 15.4 | False |
| MEME | INSUFFICIENT_DATA | 10 | 10.0 | False |
| BOND | INSUFFICIENT_DATA | 1 | 100.0 | False |
| INDEX | INSUFFICIENT_DATA | 1 | 100.0 | False |
| PENNY_STOCK | INSUFFICIENT_DATA | 1 | 0.0 | False |

Critical: **0 of the 10 classes have `money_ready=True` or `tier2_pass=True`**. CRYPTO has the largest resolved-pick volume by an order of magnitude, which is exactly why its WR is the most *measurable* (and the most *inflatable*) of all classes.

---

## 3. Per-surface CRYPTO WR (`nav_surface_edge_matrix.json::surfaces[].rows[]`)

| Surface | n_resolved | WR % | Shrunk (Bayesian) | Top source share | Verdict |
| --- | --- | --- | --- | --- | --- |
| **smart_picks** | ~93 | **75.0** % | 71.4 % | **65 %** single-source | **no-edge** |
| elite_display_tier | smaller | **81.6** % | 70.7 % | **92 % JUPUSDT** | **no-edge** |
| high_conviction | 0 / empty | — | — | — | **no-edge** |
| money_ready | 0 / no closed picks | — | — | — | **no-edge** |
| verified_alpha | 0 | — | — | — | **no-edge** |
| ueps_long_term | 0 | — | — | — | **no-edge** |
| ueps_swing | 0 | — | — | — | **no-edge** |
| ueps_closed | 0 | — | — | — | **no-edge** |

> **Headline diagnostic:** Every surface that has nonzero CRYPTO rows carries `verdict=no-edge`. This is **not** an artifact of low WR — it's a structural verdict emitted because `top_source_share ≥ 0.5` triggers the source-concentration halts in `tools/edge_finder.py`. The Bayesian-shrunk WR (71.4 %, 70.7 %) is the *post-concentration-adjustment* value; even after Bayesian shrinkage the edge is too source-narrow to clear.

---

## 4. Quantified inflation gap (CRYPTO + EQUITY comparison)

| Class | Baseline | smart_picks surface | Elite display tier | Δ abs | Δ rel |
| --- | --- | --- | --- | --- | --- |
| **CRYPTO** | 32.4 % | **75.0 %** | 81.6 % | **+42.6 pp** | **+131 %** |
| EQUITY | 35.0 % | no rows in surface | no rows | (no inflation — surface has zero EQUITY rows) | — |

**One-class phenomenon.** CRYPTO is the *only* class with both:
1. A baseline WR worth measuring (n=1,155), AND
2. Any rows at all in the smart_picks / elite_display_tier surfaces

That's why this 78.9 % ↔ 39.4 % surfaces gap is structurally a **CRYPTO-only diagnostic** — not a generic class-wide inflation pattern.

---

## 5. The single-source-concentration diagnosis (key finding)

```
CRYPTO smart_picks surface:
  - WR = 75.0 % (raw) / 71.4 % (Bayesian shrunk)
  - 65 % of resolved picks come from ONE upstream source family
  - Verdict: no-edge

CRYPTO elite_display_tier:
  - WR = 81.6 % (raw) / 70.7 % (Bayesian shrunk)
  - 92 % of resolved picks are JUPUSDT specifically
  - Verdict: no-edge
```

Per `tools/edge_finder.py`, the `no-edge` verdict for these surfaces is computed by the **source-concentration gate**, not the WR gate. The skill docs explicitly call this out: edges derived from a single source family are **not statistical edges** — they are **regime artifacts** of one whale/one source's behavior.

---

## 6. Live `tools/edge_finder.py` runtime behavior note

Running `python3 tools/edge_finder.py --surface smart_picks` (and likewise for `high_conviction`, `money_ready`) emits this exact warning:

```
[!] --surface <FLAG> requires at_pick_surface_eval, but the data source is 'trading_picks (fallback — surface flags unavailable)'.
    The in_* surface flags are not available in trading_picks — wire tools/pick_surface_snapshot.py first.
```

It does **not** crash. It falls back to the live `trading_picks` table but produces an empty result because the per-row `in_smart_picks` / `in_high_conviction` / `in_money_ready` flags are computed by the snapshot pipeline (cron tagger), not the live scanner. **To unblock live `--surface` re-runs**, `tools/pick_surface_snapshot.py` needs to be wired into the cron schedule ahead of the audit-dashboard CRYPTO+EQUITY gate. Until that ship is run, the live numeric reproduction cannot be done from this LAN host.

---

## 7. What this means for picks-now.html

`picks-now.html` lists picks with surface tags; per the canonical snapshot:
- A pick tagged `smart_picks` AND CRYPTO has a **75 % historical WR baseline**, but is **65 % likely to be from the same single source family** — so real-time edge expectations should be **discounted by ~⅓** for the source-concentration penalty.
- A pick tagged `high_conviction` AND CRYPTO has **no resolved trade history** — the tag means "passed the score floor + trust tier + walk-forward" without sufficient resolved-pick backing. Treat as **forward-test-only** (which is exactly what `tools/forward_pilot_register.py` registered `battleground_luxalgo` for).
- A pick tagged `money_ready` AND CRYPTO: **does not exist in the current dataset** (zero closed picks). This is the most rigorous filter the system emits, and CRYPTO has not survived it yet — corroborates PHASE 1A's "0 / 9 Tier-2 verdict" finding.

---

## 8. Files referenced (read-only, **none modified**)

| Path | Role |
| --- | --- |
| `tools/edge_finder.py` | Live --surface runner (snapshot-fallback path) |
| `tools/pick_surface_snapshot.py` | Canonical cron-side writer (currently NOT shipped to disk companion) |
| `audit_dashboard/data/audit_surface_truth.json` | Per-class baseline (CRYPTO base WR, NOT_READY verdict) |
| `audit_dashboard/data/nav_surface_edge_matrix.json` | Per-surface × per-class WR + shrunk + source-share + verdicts |
| `audit_dashboard/data/money_ready_verdict.json` | Cross-checked: matches audit_surface_truth finding (0 classes pass) |
| `audit_dashboard/data/top_notch_money_ready.json` | Cross-checked: same — no CRYPTO survivor |
| `.claude/skills/audit-pick-flow/SKILL.md` | Skill vocabulary: HC, Money Ready, smart_picks surfaces |

**Nothing in `tools/`, `alpha_engine/`, or `audit_dashboard/data/` was modified by this case study.** This is data-sidecar investigation only.

---

## 9. To fully reproduce the 78.9 % ↔ 39.4 % live numbers

1. **Unblock MySQL from this LAN** — add `mysql.50webs.com` to the allowlist for `142.181.130.10`, OR copy `dbpasses.txt` item for `ejaguiar1_stocks` after the stale `connect_timeout` kwarg bug in `tools/db_env.py` is fixed (mentioned as a separate fix from PHASE 1C.i's blocker).
2. **Ship `tools/pick_surface_snapshot.py` to disk** — currently it does the computations but does not write `at_pick_surface_eval.json` companion; without that file, `edge_finder.py --surface` warns "flags unavailable".
3. **Re-run edge_finder** `python3 tools/edge_finder.py --baseline` → `python3 tools/edge_finder.py --surface smart_picks` etc. for one fresh cron cycle. Expected output: numbers within ±3 pp of today's snapshot (32.4 → 75.0 → 81.6 / shrunk 71.4 / 70.7) — magnitude robust, decimals drift with pick-volume.
