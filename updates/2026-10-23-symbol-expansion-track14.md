# Parallel Track 14 — Symbol Universe Expansion (Zero-Survivor Check)

**Status:** Complete
**Date:** 2026-10-23
**Scope:** `multi_asset/portfolio_defs.py` — `ASSET_CLASS_CONFIGS` universe expansion + symbol normalization maps
**Backtest:** `tools/winner_hunt_backtest.py` (re-run) → `reports/winner_hunt_results.json`

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*

---

## 1. Background

Parallel Track 13 (winner hunt backtest) found **zero** true winners (0 ELITE / 0
SURVIVOR) across the 599-strategy FDR family. Following the user's instruction
*"if needed expand our symbol list and check further"*, Track 14 expands the symbol
universe so the portfolio/strategy engine can generate picks across a broader set of
high-quality, liquid instruments.

## 2. What Changed

Expanded the per-asset-class `universe` lists in `ASSET_CLASS_CONFIGS`
([`multi_asset/portfolio_defs.py`](../multi_asset/portfolio_defs.py:414)), and the
corresponding symbol-normalization maps so new symbols resolve to canonical form
(`crypto.symbol_normalization` and `QA_CHECKS.symbol_mismatch.normalization_map`).

| Asset class | Before | After | Added (liquidity profile) |
|-------------|-------:|------:|------|
| stock       | 23 | 58 | AVGO, NFLX, ADBE, INTC, QCOM, CSCO, IBM, PYPL, NOW, CRWD, WFC, C, MS, SCHW, AXP, MRK, ABBV, AMGN, GILD, CVS, TMO, MCD, SBUX, NKE, DIS, PEP, KO, DE, BA, GE, HON, LIN, ORLY, TJX, LOW |
| penny       | 16 | 16 | (unchanged — already high-vol micro-cap set) |
| etf        | 30 | 61 | VTI, VOO, VT, GDX, XME, COPX, REMX, VCIT, VCSH, MCHI, EWZ, EWG, EWJ, INDA, KWEB, ARKK, IGV, SMH, SOXX, XBI, IBB, TAN, ICLN, SCHD, DVY, VYM, MTUM, USMV, UDN, FXE, FXY |
| futures     | 14 | 14 | (unchanged — majors already covered) |
| forex       | 11 | 19 | EURCHF=X, CADJPY=X, CHFJPY=X, EURAUD=X, EURCAD=X, GBPAUD=X, AUDCAD=X, NZDJPY=X |
| crypto      | 6 | 32 | AVAXUSDT, DOTUSDT, LTCUSDT, TRXUSDT, ETCUSDT, ATOMUSDT, DOGEUSDT, LINKUSDT, MATICUSDT, UNIUSDT, XLMUSDT, FILUSDT, HBARUSDT, ALGOUSDT, APTUSDT, NEARUSDT, ARBUSDT, OPUSDT, SUIUSDT, SEIUSDT, TIAUSDT, INJUSDT, PEPEUSDT, SHIBUSDT, BONKUSDT, WIFUSDT |
| mutual_fund | 14 | 14 | (unchanged — core Vanguard/Fidelity set) |

Crypto `sector_groupings` were expanded from 3 groups (layer1/defi/meme) to 5
(layer1, payment_transfer, defi, layer2, meme) so the new names are grouped correctly.

## 3. Verification

- `python3 -c "import py_compile; py_compile.compile('multi_asset/portfolio_defs.py', doraise=True)"` → OK.
- Module import + `get_universe()` returns the expanded sizes above (e.g. crypto 6→32, etf 30→61, stock 23→58, forex 11→19).
- No duplicate symbols within the crypto universe (32 loaded / 32 unique).
- Normalization round-trips resolve new variants — e.g. `DOGE-USD → DOGEUSDT`, `EUR/CHF → EURCHF=X`, `WIF-USD → WIFUSDT`.

## 4. Backtest Re-Run

Re-ran `python3 tools/winner_hunt_backtest.py`. Updated result: `reports/winner_hunt_results.json`
(generated `2026-10-23T02:13:21Z`).

```
total_strategies   599
fdr_family_size    599
passed_all_gates   8
passed_fdr         24
ELITE              0
SURVIVOR           0
FAILED             599
```

**Result: still 0 ELITE / 0 SURVIVOR.** No new survivors emerged from the expansion
at this point.

### Important data-path note

The winner-hunt backtest does **not** read `portfolio_defs.py` directly. It consumes
`audit_dashboard/data/pf_registry.json`, which is aggregated by
[`tools/build_pf_registry.py`](../tools/build_pf_registry.py) from **closed-pick
ledgers** (`JSON_PICK_SOURCES` + optional MySQL `trading_picks`/`tournament_picks`/
`at_pick_outcomes`). Expanding the universe in `portfolio_defs.py` makes the new
symbols *available* to the portfolio/strategy engine, but those symbols only enter the
backtest after picks are generated and flow into the closed-pick ledgers → `pf_registry.json`.

Notably, several expanded names already have closed-pick history in the current registry
(e.g. `ml_enhanced_LTCUSDT_4h_A_xgboost`, `ml_enhanced_LINKUSDT_4h_A_xgboost`,
`ml_enhanced_ATOMUSDT`), confirming the broader universe aligns with instruments already
trading — but none pass the winner gates.

## 5. FDR Bar Impact of a Larger Family

The Benjamini–Hochberg FDR correction scales each q-value with the family size **m**:

```
q_i = p_i * m / rank_i
```

Adding strategies to the family (larger m) raises the q-values of *every* tested
strategy, **tightening** the statistical bar for ELITE classification. In other words,
expanding the universe makes it *harder*, not easier, for any single strategy to be
declared a winner — the trade-off being a stronger protection against false discoveries
across the enlarged search space.

If/once the expanded universe generates picks that flow into the ledgers, the family
size (currently 599) may grow further, and the FDR threshold will tighten accordingly.
No winner is expected to be declared from a larger family unless its edge survives a
stricter q threshold.

## 6. Deliverables

- Modified [`multi_asset/portfolio_defs.py`](../multi_asset/portfolio_defs.py) — expanded universe + normalization maps.
- Updated [`reports/winner_hunt_results.json`](../reports/winner_hunt_results.json) — re-run 2026-10-23T02:13:21Z.
- This documentation file.
- Commit SHA: see git log.
