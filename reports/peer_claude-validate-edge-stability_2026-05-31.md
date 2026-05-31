# peer_claude-validate-edge-stability — 2026-05-31

(EST 2026-05-31 17:06) Validator: Claude Opus 4.7
Scope: VALIDATE edge_stability.html cells vs live MySQL `ejaguiar1_stocks.trading_picks`.

---

## 1. Source / methodology

- Page: `audit_dashboard/edge_stability.html` reads per-class JSON at
  `audit_dashboard/data/edge_stability/edge_stability_<CLASS>.json`.
- Builder: `tools/edge/edge_stability.py` (SCHEMA_VERSION=v1).
- Methodology (verbatim, `tools/edge/edge_stability.py:50-58, 90-99, 146-158`):
  - Loads from `audit_trail/data/dashboard_payload.json` keys
    `picks.recent_closed` + `universal_resolved_picks`.
  - WIN = `status in (WON, WIN, CLOSED_TP, TP_HIT)` OR `pnl_pct > 0`.
  - Windows = 7d / 30d / 90d / all by `exit_dt` (closed_at/exit_time/timestamp).
  - PF, WR%, Sharpe via `alpha_engine.walk_forward_validator.compute_window_metrics`.

**Source-file gap (HIGH)**: `audit_trail/data/dashboard_payload.json` no longer
exists in the repo (verified with `ls audit_trail/data/`). The page renders from
stale per-class JSON files with `as_of = 2026-05-12T21:53:04Z` — **19 days old at
audit time**. Live re-run uses the same WIN convention applied directly to
`trading_picks`.

---

## 2. Page numbers (verbatim, from disk JSON `as_of 2026-05-12T21:53Z`)

| Class | n | PF | WR% | Sharpe | 7d_WR | 30d_WR | 90d_WR | Verdict |
|-------|----:|-----:|-----:|------:|------:|-------:|-------:|---------|
| BOND      |   12 | 0.66 | 50.0 | -0.171 |  0.0 |  0.0 | 50.0 | INSUFFICIENT_DATA |
| COMMODITY |  178 | 4.31 | 58.4 |  0.352 | 94.3 | 62.3 | 58.4 | STABLE_EDGE |
| CRYPTO    | 1873 | 1.27 | 45.7 |  0.093 | 41.9 | 45.8 | 45.7 | DECAYING_EDGE |
| EQUITY    |  286 | 1.92 | 54.5 |  0.237 | 37.1 | 55.1 | 54.5 | STABLE_EDGE |
| ETF       |  106 | 1.35 | 55.7 |  0.124 | 65.0 | 72.2 | 55.7 | MIXED |
| FOREX     | 1033 | 1.17 | 43.9 |  0.027 | 28.9 | 42.3 | 43.9 | DECAYING_EDGE |

Verified via `python3 -c "import json;d=json.load(open(...))"` against each
`edge_stability_<CLASS>.json`.

---

## 3. Live DB re-run (verbatim SQL)

PRE-EXPECTATION: live numbers should match if the JSON was rebuilt recently.
Because the JSON is 19 days stale AND the upstream payload file is gone,
significant drift is expected, particularly on N (more closed picks since 2026-05-12).

```sql
SELECT LOWER(TRIM(category)) AS cat, UPPER(status), pnl_pct, closed_at
FROM trading_picks
WHERE closed_at IS NOT NULL
  AND pnl_pct  IS NOT NULL
  AND status IN ('TP_HIT','SL_HIT','LOST','TIME_EXIT','EXPIRED');
```

Returned: **6,622 closed rows** (live as of EST 2026-05-31 17:06).

Class map (per page legend; matches resolver convention — `category` column,
case-insensitive; EQUITY absorbs `equity / stock / stocks / penny / pennystock`
per memory note `feedback:confidence-trust-edges-2026-05-31`):
- BOND = `bond`
- COMMODITY = `commodity`
- CRYPTO = `crypto`
- EQUITY = `equity, stock, stocks, penny, pennystock`
- ETF = `etf`
- FOREX = `forex`

WIN convention identical to `_is_won` (`edge_stability.py:90`).

### RAW RESULT (live)

| Class | n | PF | WR% | Sharpe | 7d_WR | 30d_WR | 90d_WR |
|-------|----:|------:|-----:|------:|------:|-------:|-------:|
| BOND      |    5 | 362.63 | 60.0 |  0.512 |  0.0 |  0.0 | 60.0 |
| COMMODITY |  706 |   0.69 | 41.4 | -0.035 |  0.0 |  2.6 | 41.4 |
| CRYPTO    | 4082 |   0.96 | 48.8 | -0.007 | 54.5 | 47.2 | 49.1 |
| EQUITY    |   92 |   0.61 | 46.7 | -0.114 | 33.3 | 31.0 | 46.7 |
| ETF       |   16 |   0.38 | 37.5 | -0.357 | 66.7 | 66.7 | 37.5 |
| FOREX     | 1653 |   2.45 | 45.7 |  0.028 | 21.4 | 17.0 | 45.7 |

---

## 4. Drift table (page → live)

| Class | Δn | ΔPF | ΔWR(pp) | ΔSharpe | 7d_WR shift | Verdict |
|-------|------:|------:|--------:|--------:|-------------|---------|
| BOND      | 12 → 5 (-58%)            | 0.66 → **362.63** | +10.0 | +0.68 |   0 →  0 | **RADICALLY-DIFFERENT** (huge PF; n shrank — winnable rows replaced) |
| COMMODITY | 178 → 706 (+296%)        | 4.31 → **0.69**   | -17.0 | -0.39 |  94.3 → 0.0 | **RADICALLY-DIFFERENT** (was STABLE_EDGE → NO_EDGE; lost flagship status) |
| CRYPTO    | 1873 → 4082 (+118%)      | 1.27 → 0.96       |  +3.1 | -0.10 |  41.9 → 54.5 | **DRIFT** (PF lost edge floor 1.0; 7d_WR lifted +12.6pp) |
| EQUITY    | 286 → 92 (-68%)          | 1.92 → 0.61       |  -7.8 | -0.35 |  37.1 → 33.3 | **RADICALLY-DIFFERENT** (was STABLE_EDGE → NO_EDGE; n collapsed) |
| ETF       | 106 → 16 (-85%)          | 1.35 → 0.38       | -18.2 | -0.48 |  65.0 → 66.7 | **RADICALLY-DIFFERENT** + INSUFFICIENT_DATA now |
| FOREX     | 1033 → 1653 (+60%)       | 1.17 → **2.45**   |  +1.8 | +0.00 |  28.9 → 21.4 | **RADICALLY-DIFFERENT** (was DECAYING_EDGE; PF now 2.45 — possible new edge) |

All 6 cells drift > 5% on at least one column → **STALE flag = TRUE** for entire page.

---

## 5. Verdict per class

| Class | Verdict | Note |
|-------|---------|------|
| BOND      | **radically-different** | PF jumped from 0.66 → 362.63 — almost certainly tiny-loss-divisor artifact (n=5; gp/gl ratio explodes when gl≈0). Treat with care; flag for investigation. |
| COMMODITY | **radically-different** | Flagship "STABLE_EDGE PF 4.31" on the page is **false** today. Live PF 0.69 means CT=F-class commodity has lost its edge; matches CLAUDE.md note "COMMODITY FAIL+INSUFF-N (PF 0.31 / WR 11% / n=28, CT=F 57% concentration)" — the n=706 here includes broader commodity (commodity_screener etc.) but PF<1 confirms current sub-T2 status. |
| CRYPTO    | **drift** | n more than doubled; PF slipped under break-even (0.96); but 7d_WR LIFTED +12.6pp to 54.5%. Page's DECAYING_EDGE label outdated; live looks more like MIXED w/ recent-lift signal. |
| EQUITY    | **radically-different** | n collapse 286 → 92 likely reflects the case-mess `stocks` vs `equity` discussed in memory `feedback:confidence-trust-edges-2026-05-31`. PF 0.61 contradicts page's "STABLE_EDGE PF 1.92". |
| ETF       | **radically-different** | Now below n=30 INSUFFICIENT_DATA floor (n=16). Page's MIXED-PF-1.35 entirely stale. |
| FOREX     | **radically-different** | Page says DECAYING_EDGE PF 1.17; live PF **2.45** flips the narrative. Worth a deep-dive — but 7d_WR 21.4% / 30d_WR 17.0% says edge is **time-localized** (older wins). |

---

## 6. Recommended updated cells (replace on next page rebuild)

```
BOND:      n=5     PF=362.63  WR=60.0%  Sharpe= 0.512  7d=0.0   30d=0.0   90d=60.0   (PF likely artifact)
COMMODITY: n=706   PF=0.69    WR=41.4%  Sharpe=-0.035  7d=0.0   30d=2.6   90d=41.4   (NO_EDGE; was flagship STABLE_EDGE)
CRYPTO:    n=4082  PF=0.96    WR=48.8%  Sharpe=-0.007  7d=54.5  30d=47.2  90d=49.1   (MIXED w/ 7d lift)
EQUITY:    n=92    PF=0.61    WR=46.7%  Sharpe=-0.114  7d=33.3  30d=31.0  90d=46.7   (INSUFFICIENT_DATA-adjacent, NO_EDGE)
ETF:       n=16    PF=0.38    WR=37.5%  Sharpe=-0.357  7d=66.7  30d=66.7  90d=37.5   (INSUFFICIENT_DATA)
FOREX:     n=1653  PF=2.45    WR=45.7%  Sharpe= 0.028  7d=21.4  30d=17.0  90d=45.7   (PF-rich, recency-decaying)
```

---

## 7. Stale-flag escalations

1. **STALE: edge_stability.html (entire page)** — last rebuild 2026-05-12T21:53Z; all
   6 classes drift >5%; flagship COMMODITY narrative is **false** today.
2. **HIGH: pipeline broken** — `audit_trail/data/dashboard_payload.json` is
   missing, so `python -m tools.edge.edge_stability --all` will print
   `::error::missing payload` and exit with empty data. Until the upstream payload
   builder is restored, the page cannot self-refresh.
3. **WATCH: BOND PF=362.63** — small-n / tiny-loss-divisor artifact; do not
   promote to /audit without n>=30 + path-replay confirmation.
4. **NEW SIGNAL: FOREX PF 2.45 over 1653 trades** — worth a money-maker-readyv2
   pass to see if this is a stable shift or a few outlier wins; 7d/30d WR
   collapse (21%/17%) suggests recency decay regardless.

---

## 8. Files
- Live numbers JSON: `/tmp/live_edge_metrics.json`
- Source methodology: `tools/edge/edge_stability.py`
- Stale snapshots: `audit_dashboard/data/edge_stability/edge_stability_<CLASS>.json` (as_of 2026-05-12)

(EST 2026-05-31 17:06) End of validation.
