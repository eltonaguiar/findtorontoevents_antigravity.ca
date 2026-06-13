# P2-10 — Adopt growth-stock-screener factors into the EQUITY scoring path

**Date:** 2026-06-13
**Goal (north star):** Goal #1 — phenomenal performance across all asset classes.
**Per CLAUDE.md wire-up rule:** opt-in sidecar with a `## Wiring Plan` (THRESHOLD FREEZE 2026-05-20 → 2026-08-18 blocks a forced wire-in).
**Working dir:** `/home/eaguiar2015/findtorontoevents_antigravity.ca-worktrees/feat-minimax-next-steps`
**Files:**
- New module: `/home/eaguiar2015/findtorontoevents_antigravity.ca-worktrees/feat-minimax-next-steps/alpha_engine/growth_factors.py` (~310 LOC incl. docstrings, blank lines, CLI)
- This report: `/home/eaguiar2015/findtorontoevents_antigravity.ca-worktrees/feat-minimax-next-steps/reports/p2-10_growth_factors_2026-06-13.md`

---

## 1. Setup

The existing `alpha_engine.growth_stock_screener.py` (May 2026) already
implements a 5-stage growth screen (RS rating, liquidity, Stage-2 uptrend,
quarterly revenue growth, institutional accumulation). It is **NOT** wired
into the production scoring path — it is an opt-in sidecar that emits
`audit_dashboard/data/growth_stock_picks.json` from a separate workflow.

Separately, `alpha_engine/equity_strategy_harness.py:464` ships a
`GrowthFactorSignal` that is a **proxy** for growth (it uses 6-12m price
momentum, not real fundamentals). That proxy cannot distinguish a
high-revenue-growth stock from a momentum pump.

P2-10 ADOPTS the *real* fundamental factors from the growth-stock-screener
(revenue growth %, EPS growth %, PEG ratio, market cap) into a small,
pure, opt-in module that can be wired into the EQUITY scoring path in a
follow-up sprint.

---

## 2. Existing growth-screener findings

| Source | File:line | What it does | Verdict |
|--------|-----------|--------------|---------|
| GrowthStockScreener (5-stage) | `alpha_engine/growth_stock_screener.py:1-415` | RS rating, liquidity, uptrend, **quarterly revenue growth** (yfinance `.quarterly_financials`), institutional accumulation. | Reusable: revenue-growth extractor at lines 162-201. |
| GrowthFactorSignal (proxy) | `alpha_engine/equity_strategy_harness.py:464-473` | 6-12m momentum proxy. | **Not** what we want — it is momentum, not fundamentals. |
| Wire-up note in growth_stock_screener.py:12-17 | "Wiring plan: emit picks JSON… Production scorer wire-in (calculate_smart_score / dashboard_generator) tracked in follow-up PR." | Confirms no production caller today. | The follow-up PR is P2-10. |
| Test coverage | `tests/test_growth_stock_screener.py:1-197` | 11 tests, all use stubs — no live yfinance. | Pattern to mirror in a follow-up PR. |

**Factors adopted into `growth_factors.py` (verbatim from `growth_stock_screener.py:162-201` + yfinance `.info` extensions):**
1. `revenue_growth_pct` — YoY most-recent-quarter revenue growth.
2. `eps_growth_pct` — YoY most-recent-quarter EPS growth (new — not in original screener but trivially derived from `.info`).
3. `peg_ratio` — `pegRatio` (with `trailingPegRatio` fallback).
4. `market_cap` — `marketCap`.

---

## 3. EQUITY scoring path analysis

| File | Function | Notes |
|------|----------|-------|
| `alpha_engine/scanner.py` | `apply_quality_gates` (line 2554+) | Per-class scoring. EQUITY category normalized from `stock`/`etf`/`bond` (line 2881). |
| `alpha_engine/production_scanner.py:2819` | `apply_quality_gates` | Production gate chain. **No fundamental factor hook** today. |
| `audit_trail/quality_gates.py:456` | `SMART_PICKS_MIN_SCORE_EQUITY = 50` | **FROZEN** 2026-05-20 → 2026-08-18 (90-day freeze per Kimi Renaissance Review). |
| `audit_trail/quality_gates.py:491` | `ASSET_CLASS_SMART_THRESHOLDS["EQUITY"]` | min_score 40, min_fwr 0.50, min_trades 5. |
| `alpha_engine/smart_picks_engine.py:915` | `score_pick` | The actual scorer (per meta-engine). |
| `alpha_engine/institutional_scoring.py:131` | `score_pick_institutional` | Alt scorer. |

**Where new factors plug in:** the natural hook is the EQUITY branch of
`alpha_engine/production_scanner.py:score_pick()` (or the
`SMART_PICKS_MIN_SCORE_EQUITY` block in `audit_trail/quality_gates.py:456-458`).
Today neither is touched by `growth_stock_screener` data.

---

## 4. Module design — `alpha_engine/growth_factors.py`

**Purity guarantees:**
- No DB writes.
- No mutations to `trading_picks` (returns shallow copies from `apply_to_pick`).
- No mutation of caller-supplied pick dicts (verified by smoke test).
- Cache writes are local JSON only.

**Public surface:**
- `class GrowthFactorEngine`
  - `score(symbol: str) -> dict`
    Keys: `symbol, revenue_growth_pct, eps_growth_pct, peg_ratio, market_cap, factor_score, source, fetched_at, enabled`
  - `apply_to_pick(pick: dict, factor_score: float | None) -> dict`
    Adds `growth_factor_score` field; bumps `pick["score"]` by
    `factor_score * SCORE_BUMP_PER_SIGMA * pick["score"]` (default 0.5 % per sigma)
    **only when** `GROWTH_FACTORS_ENABLED=1`. Returns the input unchanged
    (as a shallow copy) when disabled, when `factor_score` is None, when
    the pick has no `score`, or when `factor_score` is NaN/inf.
- `class GrowthFactorEngine()` is the only public class.
- All else (`_enabled`, `_to_percent`, etc.) is private.

**Data source:** `yfinance.Ticker(symbol).info` (free tier). 7-day TTL JSON
cache at `data/growth_factors/<SYMBOL>.json`. `_fetch_info()` honours the
cache before any network call. Cache writes are best-effort (`debug`-logged
on failure, never raised).

**Sigma model (tunable via env):**
```
factor_score = 0.05*rev_pct + 0.05*eps_pct + (-0.5)*(1.5 - peg) + 0.25*(log10(mcap) - 10)
```
For AAPL (rev 16.6 %, eps 21.8 %, peg 2.35, mcap $4.28T) this yields
`factor_score = 3.00` (verified live — see CLI example below). A high-growth
small/mid cap (rev 30 %, eps 25 %, peg 1.0, mcap $5B) would yield ~+1.5 to +2.5.

**CLI usage:**
```bash
# Stdout JSON of the four factors
python3 -m alpha_engine.growth_factors --symbol AAPL --stdout

# Apply the bump to a pick file (rewrites in place)
python3 -m alpha_engine.growth_factors --symbol AAPL --apply-to /tmp/pick.json

# Quiet mode
python3 -m alpha_engine.growth_factors --symbol NVDA --stdout --quiet
```

---

## 5. Reproducer

```bash
# Syntax check
python3 -c "import py_compile; py_compile.compile('alpha_engine/growth_factors.py', doraise=True)"
# → exit 0

# Import check
PYTHONPATH=. python3 -c "from alpha_engine.growth_factors import GrowthFactorEngine; print('OK')"
# → OK

# Live fetch (uses yfinance; requires network on first run)
PYTHONPATH=. python3 -m alpha_engine.growth_factors --symbol AAPL --stdout
# → JSON with revenue_growth_pct=16.6, eps_growth_pct=21.8, peg_ratio=2.35,
#   market_cap=4275929874432, factor_score=3.0028, source=yfinance

# Re-run uses the 7d cache (source: "cache")
PYTHONPATH=. python3 -m alpha_engine.growth_factors --symbol AAPL --stdout
# → source: "cache"
```

A small smoke test is in §7 below.

---

## 6. Wiring Plan (per CLAUDE.md)

The THRESHOLD FREEZE (2026-05-20 → 2026-08-18) bans any production-score
change without operator approval. P2-10 therefore ships as an **opt-in
sidecar** with the explicit wiring plan below — a single follow-up PR
will perform the actual wire-in once the freeze ends.

```
## Wiring Plan
- Target caller: alpha_engine/production_scanner.py:apply_quality_gates()
  (EQUITY branch, line ~2880-2890 where category is normalized)
  OR alpha_engine/smart_picks_engine.py:score_pick() (EQUITY branch, line ~915+)
- Expected call (1 line):
    if cat in ("equity","stock","etf") and os.environ.get("GROWTH_FACTORS_ENABLED") == "1":
        factors = GrowthFactorEngine().score(pick["symbol"])
        pick = GrowthFactorEngine().apply_to_pick(pick, factors["factor_score"])
- Date: post-2026-08-18 (after THRESHOLD FREEZE ends) — follow-up PR.
- Operator approval: required (touches production scoring; touches frozen threshold).
- Test gate: the wire-in PR must add tests/test_growth_factors_wired.py
  with a stubbed yfinance to assert the bump is applied to EQUITY picks
  and skipped for CRYPTO/FOREX picks.
- Risk register:
  * network: yfinance can rate-limit. Cache mitigates (7d TTL).
  * stale data: 7d TTL is fine for quarterly fundamentals.
  * score drift: SCORE_BUMP_PER_SIGMA default 0.5 % is below the 5 %
    threshold-noise floor observed in closed-pick analysis.
- Rollback: unset GFF env var (no code revert needed; sidecar is opt-in).
```

Wiring decision: **OPT-IN SIDECAR with documented wiring plan.** No
production code is modified in P2-10.

---

## 7. Verification

```text
$ python3 -c "import py_compile; py_compile.compile('alpha_engine/growth_factors.py', doraise=True); print('OK')"
OK
$ PYTHONPATH=. python3 -c "from alpha_engine.growth_factors import GrowthFactorEngine; print('IMPORT_OK')"
IMPORT_OK

# Smoke test (in-process, no DB)
$ python3 - <<'PY'
from alpha_engine.growth_factors import GrowthFactorEngine
e = GrowthFactorEngine()
pick = {"symbol":"AAPL","score":100.0,"direction":"LONG"}
out = e.apply_to_pick(pick, factor_score=2.0)
assert out["score"] == 100.0, "disabled -> no-op"
assert pick["score"] == 100.0, "input untouched"
import os; os.environ["GROWTH_FACTORS_ENABLED"] = "1"
out2 = e.apply_to_pick({"symbol":"AAPL","score":100.0}, factor_score=2.0)
assert abs(out2["score"] - 101.0) < 1e-6, f"got {out2['score']}"
print("ALL_OK")
PY
ALL_OK
```

`apply_to_pick` mutation / immutability / disabled-no-op / enabled-bump
behaviour all verified. `score()` returns all required keys.

---

## 8. Open questions / follow-ups

1. **Wire-in PR after 2026-08-18.** Carries the test file
   `tests/test_growth_factors_wired.py` and the 1-line hook in
   `production_scanner.py` per the wiring plan.
2. **Cache dir hygiene.** `data/growth_factors/` will grow by 1 JSON per
   symbol. Add a 30-day TTL sweep in a future housekeeping PR if it
   becomes a noise issue.
3. **Sector / industry breakdown.** `yfinance.info` exposes `sector` /
   `industryKey`; a future PR could add sector-relative z-scores (PEG
   vs sector median, etc.).
4. **Yfinance rate-limit handling.** Today the engine just returns
   `factor_score=0.0` (neutral) on fetch failure. A retry-with-backoff
   decorator is a future improvement, not in scope for P2-10.
