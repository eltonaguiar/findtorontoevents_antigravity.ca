# PEER REVIEW — MUTUAL_FUNDS

**Reviewer:** finpredict-v3 peer-review subagent, 2026-11-14T16:17Z

## 1. Peer docs read
- ML-audit `proposed_fixes/mutual_funds/FIX_PROPOSED.md` (ZERO coverage; propose build).
- ML-audit `proposed_fixes/overall/FIX_PROPOSED.md` §3.3 (add MUTUAL_FUND class; absent everywhere).
- v1 `2026-11-14-prediction-system-audit.md` §10 (inspect-wt: effectively UNBUILT).
- Mine `2026-11-14-prediction-data-hygiene.md` (mutual funds unbuilt: ranker/html absent).
- v4: MUTUAL_FUNDS absent from all v4 per-class reports & dashboard (not covered).
- v2: MUTUAL_FUNDS not among the 9 audited classes (BOND/PENNY_STOCK smallest).

## 2. Peer verdict per class
- ML (mutual_funds): "Status: **ZERO coverage — complete absence**" — no `MUTUAL_FUND_SYMBOLS`, no gatekeeper map entry (class id -1), no scanner/strategy, no dashboard tile; fund tickers (VFIAX/VTSAX/FXAIX) fall back to "equity"/"unknown". Impact: fund picks would be misclassified, dropped by ML gate, invisible.
- v1 / inspect-wt: "Mutual funds are effectively **UNBUILT** … `alpha_engine/mutual_fund_ranker.py` and `/audit/mutual-funds.html` do **not** exist. Mutual-fund predictions are planned, not delivered."
- Mine: "Mutual funds unbuilt (`mutual_fund_ranker.py` / `mutual-funds.html` absent)."

## 3. Peer-proposed quick wins (with source)
Build-side (ML):
1. Add `MUTUAL_FUND_SYMBOLS` frozenset + `_CAT_MAP`/`_LOWER_TO_UPPER` + `asset_class_from_symbol`/`normalize_asset_class` branches + `is_mutual_fund()` (`alpha_engine/asset_class.py`).
2. Add `"MUTUAL_FUND": 7` to `ASSET_CLASS_MAP` (ml_gatekeeper/gatekeeper.py:73) so funds encode to 7, not -1.
3. Add `"MUTUAL_FUND"` to `_PER_ASSET_CLASSES`/`_CANONICAL`/`_AC_TF_GRID_ASSET_CLASSES` (dashboard_generator.py) for a dashboard tile.
4. Create stub `mutual_fund_scanner.py` + `mutual_fund_strategies.py` (mirror bond_scanner) emitting placeholder signals (ML §3.3).
5. Verify DB accepts `"MUTUAL_FUND"` as an asset_class value; no whitelist blocks inserts.

## 4. Disagreements / contradictions
- **Build vs suppress**: ML proposes building a ranker/scanner (even as a stub). v1/inspect-wt + mine treat it as a planned-not-delivered class with **no real data source** (no NAV/OHLCV feed) — emitting a stub that returns placeholder/empty signals risks adding *more fabricated/empty output* of exactly the kind the whole audit already condemns. No peer verified any real fund data path.
- ML itself flags the internal inconsistency: the planned `mutual_fund_ranker.py` does not exist; only DB families `mutual_fund_v1/v2` + tactical rotation in `portfolio_defs.py` exist.
- Scope conflict: ML overall defers "mutual fund strategy implementation" to a per-asset-class doc while the mutual_funds fix proposes stubs — the two ML docs disagree on how far to build now.

## 5. Gaps
- No peer provides a real fund data source (NAV/expense-ratio/OHLCV); all proposed strategies are stubs.
- No peer has a forward/closed ledger for mutual funds (zero rows exist).
- No consensus on whether to add the class or hold until a real feed exists.

## 6. Recommended best-of (master plan)
Stage it: declare **MUTUAL_FUNDS planned/not-built** (not a live class) in the master plan. Do the low-cost classification work now — `asset_class` set + gatekeeper mapping + dashboard tile (ML items 1–3) so any existing fund tickers stop being miscounted as EQUITY/UNKNOWN. **Do NOT emit placeholder signals** (defer ML item 4 stub emission) until a real NAV/OHLCV source and a forward ledger n>=100 exist. This reconciles build-vs-suppress: classify now, emit later.
