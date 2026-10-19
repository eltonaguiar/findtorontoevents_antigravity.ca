# Asset-class pick-performance verdict — 2026-10-06

- Payload generated: `2026-10-06T02:24:29.552307+00:00` (repo_sha `9c6aee746e0a`)
- Book: `recent_closed`=3500 realised + `active_raw[OPEN]`=804 unrealised
- Closed-at span: 2026-02-21 → 2026-10-06

**Basis.** Equal-weight sum of per-pick `pnl_pct` (percentage points), realised for closed picks. `WR%` = wins ÷ decided; `WRlb95` = Wilson 95% lower bound; `PF` = gross win ÷ gross loss; `t` = mean/SE (|t| ≥ 2 ≈ 95% confidence the mean ≠ 0); `Σ` = net pp. Windows bucket closed rows by `closed_at`.

**Verdict rule.** TOO EARLY if decided < 30. Else STRONG if PF ≥ 1.20 and WRlb95 ≥ 45 and t ≥ 2; MODEST if mean > 0 and PF ≥ 1.05 and t > 0; WEAK if mean < 0 or PF < 1.0; else INCONCLUSIVE.

## Headline

- **STRONG**: CRYPTO
- **TOO EARLY (incl. no closed history)**: BOND, COMMODITY, FUTURES, MEME, PENNY_STOCK, SPORTS

## Per-class detail (window | N | W/L/F | decided | WR% | WRlb95 | PF | mean% | t | Σ% | verdict)

### CRYPTO

| Window | N | W/L/F | decided | WR% | WRlb95 | PF | mean% | t | Σ% | verdict |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 7d | 473 | 286/187/0 | 473 | 60.5 | 56.0 | 2.30 | +1.447 | +4.49 | +684.4 | STRONG |
| 14d | 723 | 396/327/0 | 723 | 54.8 | 51.1 | 2.01 | +1.408 | +4.46 | +1017.8 | STRONG |
| 30d | 1308 | 648/660/0 | 1308 | 49.5 | 46.8 | 1.60 | +0.963 | +4.87 | +1259.8 | STRONG |
| 90d | 2020 | 971/1049/0 | 2020 | 48.1 | 45.9 | 1.47 | +0.769 | +5.42 | +1552.4 | STRONG |
| ALL | 2154 | 1041/1113/0 | 2154 | 48.3 | 46.2 | 1.44 | +0.703 | +5.25 | +1515.0 | STRONG |

### EQUITY

| Window | N | W/L/F | decided | WR% | WRlb95 | PF | mean% | t | Σ% | verdict |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 7d | 25 | 9/7/9 | 16 | 56.2 | 33.2 | 2.05 | +0.676 | +0.98 | +16.9 | TOO EARLY |
| 14d | 49 | 13/27/9 | 40 | 32.5 | 20.1 | 0.50 | -0.945 | -1.80 | -46.3 | WEAK |
| 30d | 115 | 45/61/9 | 106 | 42.5 | 33.5 | 0.96 | -0.073 | -0.17 | -8.4 | WEAK |
| 90d | 289 | 123/157/9 | 280 | 43.9 | 38.2 | 1.08 | +0.152 | +0.50 | +44.0 | MODEST |
| ALL | 637 | 303/324/10 | 627 | 48.3 | 44.4 | 1.26 | +0.524 | +2.26 | +333.8 | MODEST |

### FOREX

| Window | N | W/L/F | decided | WR% | WRlb95 | PF | mean% | t | Σ% | verdict |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 7d | 81 | 15/37/29 | 52 | 28.8 | 18.3 | 0.59 | -0.098 | -1.79 | -7.9 | WEAK |
| 14d | 81 | 15/37/29 | 52 | 28.8 | 18.3 | 0.59 | -0.098 | -1.79 | -7.9 | WEAK |
| 30d | 81 | 15/37/29 | 52 | 28.8 | 18.3 | 0.59 | -0.098 | -1.79 | -7.9 | WEAK |
| 90d | 118 | 34/55/29 | 89 | 38.2 | 28.8 | 0.79 | -0.049 | -1.06 | -5.8 | WEAK |
| ALL | 206 | 65/102/39 | 167 | 38.9 | 31.9 | 0.87 | -0.032 | -0.76 | -6.6 | WEAK |

### COMMODITY

| Window | N | W/L/F | decided | WR% | WRlb95 | PF | mean% | t | Σ% | verdict |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 7d | 3 | 0/2/1 | 2 | 0.0 | 0.0 | 0.00 | -3.341 | -1.45 | -10.0 | TOO EARLY |
| 14d | 3 | 0/2/1 | 2 | 0.0 | 0.0 | 0.00 | -3.341 | -1.45 | -10.0 | TOO EARLY |
| 30d | 3 | 0/2/1 | 2 | 0.0 | 0.0 | 0.00 | -3.341 | -1.45 | -10.0 | TOO EARLY |
| 90d | 3 | 0/2/1 | 2 | 0.0 | 0.0 | 0.00 | -3.341 | -1.45 | -10.0 | TOO EARLY |
| ALL | 3 | 0/2/1 | 2 | 0.0 | 0.0 | 0.00 | -3.341 | -1.45 | -10.0 | TOO EARLY |

### ETF

| Window | N | W/L/F | decided | WR% | WRlb95 | PF | mean% | t | Σ% | verdict |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 7d | 17 | 10/7/0 | 17 | 58.8 | 36.0 | 3.53 | +0.895 | +2.11 | +15.2 | TOO EARLY |
| 14d | 34 | 16/18/0 | 34 | 47.1 | 31.5 | 1.27 | +0.189 | +0.57 | +6.4 | MODEST |
| 30d | 68 | 29/39/0 | 68 | 42.6 | 31.6 | 0.86 | -0.124 | -0.54 | -8.4 | WEAK |
| 90d | 217 | 96/121/0 | 217 | 44.2 | 37.8 | 1.07 | +0.064 | +0.40 | +13.9 | MODEST |
| ALL | 471 | 218/253/0 | 471 | 46.3 | 41.8 | 1.14 | +0.153 | +1.18 | +71.9 | MODEST |

### FUTURES

| Window | N | W/L/F | decided | WR% | WRlb95 | PF | mean% | t | Σ% | verdict |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 7d | 0 | — | — | — | — | — | — | — | — | TOO EARLY |
| 14d | 0 | — | — | — | — | — | — | — | — | TOO EARLY |
| 30d | 0 | — | — | — | — | — | — | — | — | TOO EARLY |
| 90d | 0 | — | — | — | — | — | — | — | — | TOO EARLY |
| ALL | 0 | — | — | — | — | — | — | — | — | TOO EARLY |

### BOND

| Window | N | W/L/F | decided | WR% | WRlb95 | PF | mean% | t | Σ% | verdict |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 7d | 3 | 0/3/0 | 3 | 0.0 | 0.0 | 0.00 | -0.927 | -4.15 | -2.8 | TOO EARLY |
| 14d | 3 | 0/3/0 | 3 | 0.0 | 0.0 | 0.00 | -0.927 | -4.15 | -2.8 | TOO EARLY |
| 30d | 3 | 0/3/0 | 3 | 0.0 | 0.0 | 0.00 | -0.927 | -4.15 | -2.8 | TOO EARLY |
| 90d | 10 | 2/8/0 | 10 | 20.0 | 5.7 | 0.31 | -0.486 | -1.88 | -4.9 | TOO EARLY |
| ALL | 29 | 10/18/1 | 28 | 35.7 | 20.7 | 0.52 | -0.265 | -1.66 | -7.7 | TOO EARLY |

### MEME

| Window | N | W/L/F | decided | WR% | WRlb95 | PF | mean% | t | Σ% | verdict |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 7d | 0 | — | — | — | — | — | — | — | — | TOO EARLY |
| 14d | 0 | — | — | — | — | — | — | — | — | TOO EARLY |
| 30d | 0 | — | — | — | — | — | — | — | — | TOO EARLY |
| 90d | 0 | — | — | — | — | — | — | — | — | TOO EARLY |
| ALL | 0 | — | — | — | — | — | — | — | — | TOO EARLY |

### PENNY_STOCK

| Window | N | W/L/F | decided | WR% | WRlb95 | PF | mean% | t | Σ% | verdict |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 7d | 0 | — | — | — | — | — | — | — | — | TOO EARLY |
| 14d | 0 | — | — | — | — | — | — | — | — | TOO EARLY |
| 30d | 0 | — | — | — | — | — | — | — | — | TOO EARLY |
| 90d | 0 | — | — | — | — | — | — | — | — | TOO EARLY |
| ALL | 0 | — | — | — | — | — | — | — | — | TOO EARLY |

### SPORTS

| Window | N | W/L/F | decided | WR% | WRlb95 | PF | mean% | t | Σ% | verdict |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 7d | 0 | — | — | — | — | — | — | — | — | TOO EARLY |
| 14d | 0 | — | — | — | — | — | — | — | — | TOO EARLY |
| 30d | 0 | — | — | — | — | — | — | — | — | TOO EARLY |
| 90d | 0 | — | — | — | — | — | — | — | — | TOO EARLY |
| ALL | 0 | — | — | — | — | — | — | — | — | TOO EARLY |

## Classes with NO recent picks — investigation

| Class | recent closed | recent open | status |
|---|---:|---:|---|
| CRYPTO | 2154 | 460 | resolvable |
| EQUITY | 637 | 92 | resolvable |
| FOREX | 206 | 134 | resolvable |
| COMMODITY | 3 | 63 | resolvable |
| ETF | 471 | 17 | resolvable |
| FUTURES | 0 | 10 | no closed history |
| BOND | 29 | 26 | resolvable |
| MEME | 0 | 0 | zero rows in BOTH books (0 closed, 0 open). |
| PENNY_STOCK | 0 | 0 | zero rows in BOTH books (0 closed, 0 open). |
| SPORTS | 0 | 2 | no closed history |


**Why MEME and PENNY_STOCK emit nothing.** The MEME/PENNY enhanced-v2 strategies
*are* declared (`alpha_engine/june2026_research_candidates.py`:
`ENHANCED_V2_BY_CLASS["MEME"]`, `["PENNY_STOCK"]`), but `_build_generators()`
gates each one on its flagship generator:

```python
entry = FLAGSHIP_BY_CLASS.get(ac)
if not entry:
    continue          # <-- skipped entirely, no generator registered
```

`FLAGSHIP_BY_CLASS` (`alpha_engine/eight_class_flagship_strategies.py`) has keys
`CRYPTO, EQUITY, ETF, FOREX, COMMODITY, FUTURES, BOND, PREDICTION_MARKETS,
CHEAP_STOCKS, IPO` — **there is no `MEME` key and no `PENNY_STOCK` key**, so both
classes fall through the `continue` and never produce a forward-observation pick.
Compounding causes: the academic emitter wires only 1 of 3 MEME strategies
(`academic_strategies_emitter.py`: "MEME 1/3 wired (prototype)"), and MEME's
position cap was halved (`per_class_position_caps.py`: `"MEME": 0.01  # CUT 50%
2026-06-12`). Even the broad all-time ledger is tiny for these: MEME n=10
(PF 0.02), PENNY_STOCK n=1 — so there is no "earlier picks" evidence to fall back
on either.


**Classes that are genuinely too early (no meaningful closed history).**

- **FUTURES** — 0 closed rows; `performance.resolution_coverage.FUTURES` shows
  `resolved: 0, meets_gate: false`. Nothing to grade yet.
- **SPORTS** — 0 closed rows; `resolution_coverage.SPORTS` `resolved: 0,
  meets_gate: false`. 2 open picks only.
- **COMMODITY** — only 3 closed rows ever; `resolution_coverage.COMMODITY`
  `resolved: 3 / 13 = 23%`, `meets_gate: false`, despite 63 picks still open.
  The resolver is not clearing this class, so "performance" is unknowable today.
- **BOND** — 29 closed rows in the pick book, but `asset_class_health.BOND` is
  `insufficient_data` with `n: 0`: the broader registry/ledger view has no BOND
  entry at all (the local `pf_registry.json` is stale 2026-06-23 and
  `source_files_canonical: false`). A source-coverage gap, not just a small sample.

## Cross-check: pick book (recent) vs asset_class_health (broader all-time)

`performance.asset_class_health` is a *different, broader* basis (all-time ledger; n up to ~8× the recent book). Where the two disagree, treat the recent book as the apples-to-apples read and the health view as a flag.

| Class | recent ALL: N | recent PF | recent Σ% | health N | health PF | health Σ% | status |
|---|---:|---:|---:|---:|---:|---:|---|
| CRYPTO | 2154 | 1.44 | +1515.0 | 17147 | 0.279 | -814.9 | stressed |
| EQUITY | 637 | 1.26 | +333.8 | 451 | 0.974 | -0.27 | watch |
| FOREX | 206 | 0.87 | -6.6 | 397 | 0.987 | -0.05 | stressed |
| COMMODITY | 3 | 0.00 | -10.0 | 11 | 0.067 | -0.26 | thin_sample |
| ETF | 471 | 1.14 | +71.9 | 15 | 1.835 | 1.3 | thin_sample |
| FUTURES | 0 | — | — | 11 | 0.475 | -0.09 | thin_sample |
| BOND | 29 | 0.52 | -7.7 | 0 | — | 0.0 | insufficient_data |
| MEME | 0 | — | — | 10 | 0.023 | -0.65 | thin_sample |
| PENNY_STOCK | 0 | — | — | 1 | 0.000 | -0.01 | insufficient_data |
| SPORTS | 0 | — | — | — | — | — | — |
