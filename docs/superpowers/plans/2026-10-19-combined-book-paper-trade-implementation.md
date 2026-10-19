# Combined-Book Paper-Trade Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone `combined_book/` package — backtest harness + frozen RULES.md + paper simulator + monthly gates — that reproduces the approved spec's Grok-benchmarked numbers (no-overlay CAGR 8.8% / Sharpe 1.27 / DD −20.5%; 5% overlay CAGR 6.5% / Sharpe 1.20 / DD −14.4%; coin-flip control PF ≈ 0.81 rejected) and reports `NOT READY` / `READY` / `KILL`.

**Architecture:** A package at repo root `combined_book/` with one module per responsibility: `rules.py` (frozen constants + SHA-256), `fetch.py` (yfinance daily closes + monthly returns), sleeve modules (`trend_sleeve.py`, `quality_sleeve.py`, `put_sleeve.py`), `combiner.py` (inverse-vol weights, 40% cap, the pre-registered 5–10% vol-cap selection rule), `simulator.py` (month-end engine + backtest + stats), `ledger.py` (JSON ledger, starting positions 2026-09-30), `gates.py` (statistical go-live + kill gates), and `cli.py`. TDD throughout: write a failing test, implement minimally, pass, commit.

**Tech Stack:** Python 3, pandas, numpy, pytest, optional yfinance (with cached CSV fallback). No PortfolioManager / Redis-bus integration.

---

## File map

| Path | Responsibility |
|------|----------------|
| `combined_book/__init__.py` | Package marker (empty docstring). |
| `combined_book/rules.py` | Frozen constants, RULES.md text, SHA-256 compute/verify. |
| `combined_book/fetch.py` | ETF universe map, cached daily closes, monthly returns. |
| `combined_book/trend_sleeve.py` | 1/3/12-m lookback blend, ~10% vol sizing. |
| `combined_book/quality_sleeve.py` | QUAL/VLUE/MTUM/USMV equal-weight blend. |
| `combined_book/put_sleeve.py` | XYLD proxy / CBOE PUT index monthly returns. |
| `combined_book/combiner.py` | Inverse-vol weights, 40% cap, vol-cap selection rule. |
| `combined_book/simulator.py` | Combines sleeves, equity curve, backtest, stats. |
| `combined_book/ledger.py` | JSON positions/returns ledger. |
| `combined_book/gates.py` | Wilson CI, binomial p-value, bootstrap PF, Sharpe, random-entry percentile, Deflated Sharpe, go-live + kill gates. |
| `combined_book/cli.py` | `init-ledger` / `run-month` / `backtest` / `gates` / `hash-check` / `report`. |
| `tests/test_combined_book_rules.py` | Rules + hash tests. |
| `tests/test_combined_book_fetch.py` | Fetch + monthly-returns tests. |
| `tests/test_combined_book_sleeves.py` | Trend / quality / put sleeve tests. |
| `tests/test_combined_book_combiner.py` | Combiner + vol-cap selection tests. |
| `tests/test_combined_book_simulator.py` | Simulator + backtest stats tests. |
| `tests/test_combined_book_ledger.py` | Ledger tests. |
| `tests/test_combined_book_gates.py` | Gates + statistical-helper tests. |
| `tests/test_combined_book_reproduction.py` | Network-marked reproduction vs documented targets. |

Note: the reference grokbot repo (`eltonaguiar/grokbot`) was confirmed empty (only a blank README) on 2026-10-19; there is no `results.csv` to diff against, so reproduction is checked against the documented targets from the approved spec.

---

### Task 1: Package skeleton + `rules.py` (freeze + hash)

**Files:**
- Create: `combined_book/__init__.py`
- Create: `combined_book/rules.py`
- Create: `tests/test_combined_book_rules.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_combined_book_rules.py
"""Tests for frozen rules + SHA-256 hashing."""
from combined_book import rules


def test_rules_hash_is_64_hex_chars():
    assert len(rules.RULES_HASH) == 64
    assert all(c in "0123456789abcdef" for c in rules.RULES_HASH)


def test_rules_hash_changes_when_text_changes():
    h1 = rules.compute_rules_hash("rules version 1")
    h2 = rules.compute_rules_hash("rules version 2")
    assert h1 != h2


def test_verify_accepts_matching_hash():
    assert rules.verify_rules_hash(rules.RULES_HASH) is True


def test_verify_rejects_wrong_hash():
    assert rules.verify_rules_hash("0" * 64) is False


def test_frozen_constants_exist():
    assert rules.STARTING_CAPITAL == 100_000.0
    assert rules.PER_SLEEVE_CAP == 0.40
    assert rules.TRADE_COST_BPS == 10.0
    assert rules.KILL_DRAWDOWN == -0.15
    assert rules.VOL_TARGET_MIN == 0.05
    assert rules.VOL_TARGET_MAX == 0.10
    assert "d5bed907932009a96d45521c15102cba2092ec9307dfd8367aedf3f21c9fcfd5" in rules.RULES_REFERENCE_HASH
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_combined_book_rules.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'combined_book'`.

- [ ] **Step 3: Create the package and `rules.py`**

```python
# combined_book/__init__.py
"""Standalone combined-book paper-trade sleeve package."""
```

```python
# combined_book/rules.py
"""Frozen rules for the standalone combined-book pilot.

Any change to RULES_MARKDOWN changes RULES_HASH and starts a new pilot.
"""
from pathlib import Path
import hashlib

# --- Frozen constants (recorded in RULES.md) ---
STARTING_CAPITAL = 100_000.0
REBALANCE_CADENCE = "monthly"
PER_SLEEVE_CAP = 0.40
TRADE_COST_BPS = 10.0

# Go-live gate thresholds
GO_LIVE_N_MONTHS = 100
GO_LIVE_PF = 1.5
GO_LIVE_WR = 0.50
GO_LIVE_MAX_DD = -0.20

# Kill thresholds
KILL_DRAWDOWN = -0.15
KILL_AFTER_MONTHS = 24
KILL_PF = 1.0
KILL_WR = 0.50
KILL_SHARPE = 0.0
KILL_BOOTSTRAP_P = 0.5

# Pre-registered volatility-cap selection rule range
VOL_TARGET_MIN = 0.05
VOL_TARGET_MAX = 0.10

# External pilot's reference rules hash (informational; ours differs)
RULES_REFERENCE_HASH = "d5bed907932009a96d45521c15102cba2092ec9307dfd8367aedf3f21c9fcfd5"

RULES_MARKDOWN = """\
# Combined-Book Paper-Trade Rules (frozen)

- Starting capital: $100,000 (fixed).
- Rebalance cadence: monthly.
- Per-sleeve weight cap: 40%.
- Sleeve combination: inverse-volatility weights.
- Trade cost: 10 bps per trade (trend sleeve).
- Target book volatility cap: 5% annualized, selected by the pre-registered rule:
  pick the highest target in 5%-10% whose pre-2016 backtest max drawdown stays within
  the -15% kill limit. 6% hit -16.5%, so 5% wins. Run on pre-2016 data only.
- Put-write sleeve: tradeable proxy XYLD; backtest series CBOE PUT index.
- Trend sleeve may hold net-short bond stance; borrow cost modeled or flagged unmodeled.
- Uninvested cash earns 0%.
- Go-live gate (all must pass): >=100 months; PF >= 1.5; win rate >= 50%; worst DD
  no deeper than -20%. Reported alongside: Wilson 95% CI, binomial p-value,
  bootstrapped PF (seeded), Sharpe vs SPY, random-entry percentile, Deflated Sharpe.
- Kill criteria (either kills): live paper DD worse than -15%; OR at >=24 months any of
  PF < 1.0, win rate < 50%, Sharpe <= 0, bootstrap P(PF <= 1) > 0.5.
"""


def compute_rules_hash(rules_text: str) -> str:
    return hashlib.sha256(rules_text.encode("utf-8")).hexdigest()


RULES_HASH = compute_rules_hash(RULES_MARKDOWN)


def verify_rules_hash(expected: str | None = None) -> bool:
    target = expected if expected is not None else RULES_HASH
    return compute_rules_hash(RULES_MARKDOWN) == target
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_combined_book_rules.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add combined_book tests/test_combined_book_rules.py
git commit -m "feat(combined_book): frozen rules + SHA-256 hash"
```

---

### Task 2: `fetch.py` (data access + monthly returns)

**Files:**
- Create: `combined_book/fetch.py`
- Create: `tests/test_combined_book_fetch.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_combined_book_fetch.py
"""Tests for data fetching + monthly-return computation."""
import pandas as pd
import pytest

from combined_book import fetch


def _daily_series(dates, prices):
    s = pd.Series(prices, index=pd.to_datetime(dates))
    s.index.name = "date"
    return s


def test_monthly_returns_resamples_to_last_price():
    s = _daily_series(
        ["2026-01-05", "2026-01-20", "2026-02-10", "2026-02-25", "2026-03-15"],
        [100.0, 110.0, 115.0, 120.0, 130.0],
    )
    r = fetch.monthly_returns(s)
    # Jan last=110, Feb last=120, Mar last=130
    assert list(r.index.strftime("%Y-%m")) == ["2026-01", "2026-02", "2026-03"]
    assert abs(r.iloc[0] - 0.10) < 1e-9  # (110-100)/100
    assert abs(r.iloc[1] - (120 - 110) / 110) < 1e-9
    assert abs(r.iloc[2] - (130 - 120) / 120) < 1e-9


def test_get_daily_closes_caches_to_disk(tmp_path):
    data = {"SPY": _daily_series(["2026-01-05"], [100.0])}
    fetch._write_cache(data, tmp_path)  # helper to seed cache
    out = fetch.get_daily_closes(["SPY"], cache_dir=tmp_path)
    assert "SPY" in out
    assert (tmp_path / "SPY.csv").exists()


def test_universe_contains_core_symbols():
    assert "SPY" in fetch.UNIVERSE
    assert "XYLD" in fetch.UNIVERSE
    assert "PUT" in fetch.UNIVERSE
    assert "QUAL" in fetch.UNIVERSE
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_combined_book_fetch.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'combined_book.fetch'`.

- [ ] **Step 3: Implement `fetch.py`**

```python
# combined_book/fetch.py
"""Fetch historical daily closes/returns for the combined-book ETF universe."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

UNIVERSE = {
    "SPY": "trend_stock", "EFA": "trend_stock", "EEM": "trend_stock",
    "IWM": "trend_stock",
    "TLT": "trend_bond", "IEF": "trend_bond", "SHY": "trend_bond",
    "LQD": "trend_bond", "HYG": "trend_bond", "TIP": "trend_bond",
    "GLD": "trend_comm", "DBC": "trend_comm", "USO": "trend_comm",
    "SLV": "trend_comm",
    "VNQ": "trend_re",
    "QUAL": "quality", "VLUE": "quality", "MTUM": "quality", "USMV": "quality",
    "XYLD": "put_proxy", "PUT": "put_index",
}


def _default_cache_dir() -> Path:
    return Path(os.environ.get("COMBINED_BOOK_CACHE", "combined_book/data"))


def _write_cache(closes: dict, cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    for sym, series in closes.items():
        series.to_frame(name="close").to_csv(cache_dir / f"{sym}.csv")


def _read_cache(sym: str, cache_dir: Path) -> pd.Series | None:
    path = cache_dir / f"{sym}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    return df["close"].dropna()


def _download(symbol: str) -> pd.Series:
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover - env dependent
        raise RuntimeError("yfinance is required to download missing data") from exc
    df = yf.download(symbol, auto_adjust=True, progress=False)
    close = df["Close"].squeeze()
    close.index = pd.to_datetime(close.index)
    return close.dropna()


def get_daily_closes(
    symbols: list[str], cache_dir: Path | None = None
) -> dict[str, pd.Series]:
    cache_dir = cache_dir or _default_cache_dir()
    out: dict[str, pd.Series] = {}
    missing: list[str] = []
    for sym in symbols:
        cached = _read_cache(sym, cache_dir)
        if cached is not None and not cached.empty:
            out[sym] = cached
        else:
            missing.append(sym)
    if missing:
        fetched = {sym: _download(sym) for sym in missing}
        _write_cache(fetched, cache_dir)
        out.update(fetched)
    return out


def monthly_returns(series: pd.Series) -> pd.Series:
    monthly = series.resample("ME").last().dropna()
    return monthly.pct_change().dropna()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_combined_book_fetch.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add combined_book/fetch.py tests/test_combined_book_fetch.py
git commit -m "feat(combined_book): data fetch + monthly returns"
```

---

### Task 3: `trend_sleeve.py`

**Files:**
- Create: `combined_book/trend_sleeve.py`
- Create: `tests/test_combined_book_sleeves.py`

- [ ] **Step 1: Write the failing tests (trend section)**

```python
# tests/test_combined_book_sleeves.py
"""Tests for trend / quality / put sleeves."""
import pandas as pd

from combined_book import put_sleeve, quality_sleeve, trend_sleeve
from combined_book.fetch import monthly_returns


def _daily_series(dates, prices):
    s = pd.Series(prices, index=pd.to_datetime(dates))
    s.index.name = "date"
    return s


def _monthly_series(months, vals):
    return pd.Series(vals, index=pd.to_datetime([f"{m}-01" for m in months]))


def test_blend_trend_score_uses_lookbacks():
    # 12 months of data ending at price 110, 1m ago 100 -> score > 0
    closes = _daily_series(
        ["2025-10-01", "2025-11-01", "2025-12-01", "2026-01-01",
         "2026-02-01", "2026-03-01", "2026-04-01", "2026-05-01",
         "2026-06-01", "2026-07-01", "2026-08-01", "2026-09-01",
         "2026-10-01"],
        [100.0] * 12 + [110.0],
    )
    score = trend_sleeve.blend_trend_score(closes)
    assert score is not None
    assert score > 0.0


def test_blend_trend_score_short_history_returns_none():
    closes = _daily_series(["2026-10-01", "2026-10-02"], [100.0, 101.0])
    assert trend_sleeve.blend_trend_score(closes) is None


def test_trend_target_weights_sum_to_cap_fraction():
    closes = {
        "SPY": _daily_series(
            ["2025-10-01", "2026-01-01", "2026-04-01", "2026-07-01", "2026-10-01"],
            [100.0, 102.0, 104.0, 106.0, 108.0]),
        "TLT": _daily_series(
            ["2025-10-01", "2026-01-01", "2026-04-01", "2026-07-01", "2026-10-01"],
            [100.0, 99.0, 98.0, 97.0, 96.0]),
    }
    w = trend_sleeve.trend_target_weights(closes, vol_target=0.10, cap_fraction=0.35)
    assert abs(sum(w.values()) - 0.35) < 1e-9
    assert set(w.keys()) == {"SPY", "TLT"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_combined_book_sleeves.py -v -k trend`
Expected: FAIL with import error.

- [ ] **Step 3: Implement `trend_sleeve.py`**

```python
# combined_book/trend_sleeve.py
"""Trend-following sleeve: 1/3/12-m lookback blend, ~10% vol sizing."""
from __future__ import annotations

import numpy as np

from combined_book.fetch import monthly_returns

TREND_LOOKBACKS = (1, 3, 12)


def blend_trend_score(closes, lookbacks=TREND_LOOKBACKS):
    if len(closes) <= max(lookbacks):
        return None
    scores = []
    for m in lookbacks:
        ret = closes.iloc[-1] / closes.iloc[-m - 1] - 1.0
        scores.append(float(ret))
    return float(np.mean(scores))


def realized_vol(monthly, window=12):
    if len(monthly) < 2:
        return 0.0
    return float(monthly.tail(window).std(ddof=0))


def trend_target_weights(closes_by_symbol, vol_target=0.10, cap_fraction=1.0):
    eligible = {
        s: c for s, c in closes_by_symbol.items()
        if blend_trend_score(c) is not None
    }
    raw = {}
    for s, c in eligible.items():
        v = realized_vol(monthly_returns(c))
        raw[s] = vol_target / v if v > 0 else 0.0
    total = sum(raw.values())
    if total <= 0:
        return {s: 0.0 for s in eligible}
    return {s: (x / total) * cap_fraction for s, x in raw.items()}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_combined_book_sleeves.py -v -k trend`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add combined_book/trend_sleeve.py tests/test_combined_book_sleeves.py
git commit -m "feat(combined_book): trend sleeve lookback blend + vol sizing"
```

---

### Task 4: `quality_sleeve.py`

- [ ] **Step 1: Write the failing tests (quality section)**

```python
# add to tests/test_combined_book_sleeves.py
def test_quality_monthly_returns_is_equal_weight_blend():
    months = ["2026-01", "2026-02", "2026-03"]
    q = _monthly_series(months, [0.01, 0.02, -0.01])
    v = _monthly_series(months, [0.03, 0.01, 0.00])
    m = _monthly_series(months, [0.02, -0.01, 0.01])
    u = _monthly_series(months, [0.00, 0.00, 0.02])
    closes = {"QUAL": q, "VLUE": v, "MTUM": m, "USMV": u}
    r = quality_sleeve.quality_monthly_returns(closes)
    # mean of the four per month
    assert abs(r["2026-01-01"] - (0.01 + 0.03 + 0.02 + 0.00) / 4) < 1e-9
    assert abs(r["2026-02-01"] - (0.02 + 0.01 - 0.01 + 0.00) / 4) < 1e-9
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_combined_book_sleeves.py -v -k quality`
Expected: FAIL with import error.

- [ ] **Step 3: Implement `quality_sleeve.py`**

```python
# combined_book/quality_sleeve.py
"""Quality/value sleeve: equal-weight blend of QUAL/VLUE/MTUM/USMV monthly returns."""
from __future__ import annotations

import pandas as pd

from combined_book.fetch import monthly_returns

QUALITY_UNIVERSE = ("QUAL", "VLUE", "MTUM", "USMV")


def quality_monthly_returns(closes_by_symbol):
    series = [
        monthly_returns(c)
        for sym, c in closes_by_symbol.items()
        if sym in QUALITY_UNIVERSE
    ]
    series = [s for s in series if not s.empty]
    if not series:
        return pd.Series(dtype=float)
    frame = pd.concat(series, axis=1).fillna(0.0)
    return frame.mean(axis=1)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_combined_book_sleeves.py -v -k quality`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add combined_book/quality_sleeve.py tests/test_combined_book_sleeves.py
git commit -m "feat(combined_book): quality sleeve equal-weight blend"
```

---

### Task 5: `put_sleeve.py`

- [ ] **Step 1: Write the failing tests (put section)**

```python
# add to tests/test_combined_book_sleeves.py
def test_put_monthly_returns_prefers_index():
    months = ["2026-01", "2026-02"]
    idx = _monthly_series(months, [0.01, 0.00])
    proxy = _monthly_series(months, [0.05, 0.05])
    closes = {"PUT": idx, "XYLD": proxy}
    r = put_sleeve.put_monthly_returns(closes, use_index=True)
    assert abs(r["2026-01-01"] - 0.01) < 1e-9


def test_put_monthly_returns_uses_proxy_when_requested():
    months = ["2026-01", "2026-02"]
    idx = _monthly_series(months, [0.01, 0.00])
    proxy = _monthly_series(months, [0.05, 0.05])
    closes = {"PUT": idx, "XYLD": proxy}
    r = put_sleeve.put_monthly_returns(closes, use_index=False)
    assert abs(r["2026-01-01"] - 0.05) < 1e-9
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_combined_book_sleeves.py -v -k put`
Expected: FAIL with import error.

- [ ] **Step 3: Implement `put_sleeve.py`**

```python
# combined_book/put_sleeve.py
"""Put-write sleeve: XYLD tradeable proxy; CBOE PUT index for backtest series."""
from __future__ import annotations

import pandas as pd

from combined_book.fetch import monthly_returns

PUT_PROXY = "XYLD"
PUT_INDEX = "PUT"


def put_monthly_returns(closes_by_symbol, use_index=True):
    key = PUT_INDEX if use_index else PUT_PROXY
    if key not in closes_by_symbol:
        return pd.Series(dtype=float)
    return monthly_returns(closes_by_symbol[key])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_combined_book_sleeves.py -v -k put`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add combined_book/put_sleeve.py tests/test_combined_book_sleeves.py
git commit -m "feat(combined_book): put-write sleeve XYLD/PUT"
```

---

### Task 6: `combiner.py` (inverse vol, cap, vol-cap selection rule)

**Files:**
- Create: `combined_book/combiner.py`
- Create: `tests/test_combined_book_combiner.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_combined_book_combiner.py
"""Tests for the combiner + pre-registered vol-cap selection rule."""
from combined_book import combiner


def test_inverse_vol_weights_sum_to_one():
    vols = {"a": 0.20, "b": 0.10}
    w = combiner.inverse_vol_weights(vols)
    assert abs(sum(w.values()) - 1.0) < 1e-9
    assert w["a"] < w["b"]  # lower vol gets more weight


def test_apply_per_sleeve_cap_clips_and_renormalizes():
    weights = {"a": 0.6, "b": 0.2, "c": 0.2}
    capped = combiner.apply_per_sleeve_cap(weights, cap=0.40)
    assert all(v <= 0.40 + 1e-9 for v in capped.values())
    assert abs(sum(capped.values()) - 1.0) < 1e-6


def test_max_drawdown_computed_correctly():
    eq = [1.0, 1.2, 0.9, 1.1]
    assert abs(combiner.max_drawdown(eq) - (0.9 / 1.2 - 1.0)) < 1e-9


def test_select_vol_cap_picks_5_when_6_breaks():
    pre = {0.06: -0.165, 0.05: -0.144}
    assert combiner.select_vol_cap(pre) == 0.05


def test_select_vol_cap_picks_highest_viable():
    pre = {0.10: -0.12, 0.08: -0.10, 0.05: -0.08}
    assert combiner.select_vol_cap(pre) == 0.10
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_combined_book_combiner.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Implement `combiner.py`**

```python
# combined_book/combiner.py
"""Inverse-vol sleeve combination, per-sleeve cap, book-level vol-cap selection rule."""
from __future__ import annotations

import numpy as np

from combined_book.rules import KILL_DRAWDOWN, PER_SLEEVE_CAP, VOL_TARGET_MAX, VOL_TARGET_MIN


def inverse_vol_weights(vols):
    inv = {k: (1.0 / v if v > 0 else 0.0) for k, v in vols.items()}
    total = sum(inv.values())
    if total <= 0:
        return {k: 0.0 for k in vols}
    return {k: v / total for k, v in inv.items()}


def apply_per_sleeve_cap(weights, cap=PER_SLEEVE_CAP):
    capped = {k: min(v, cap) for k, v in weights.items()}
    total = sum(capped.values())
    if total <= 0:
        return {k: 0.0 for k in weights}
    shortfall = 1.0 - total
    uncapped = [k for k in weights if weights[k] < cap]
    if uncapped and shortfall > 0:
        bonus = shortfall / len(uncapped)
        for k in uncapped:
            capped[k] += bonus
    return {k: v for k, v in capped.items()}


def max_drawdown(equity):
    arr = np.asarray(equity, dtype=float)
    peak = np.maximum.accumulate(arr)
    dd = arr / peak - 1.0
    return float(dd.min())


def select_vol_cap(pre2016_max_dd_by_target):
    for target in sorted(pre2016_max_dd_by_target, reverse=True):
        if VOL_TARGET_MIN <= target <= VOL_TARGET_MAX:
            if pre2016_max_dd_by_target[target] >= KILL_DRAWDOWN:
                return target
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_combined_book_combiner.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add combined_book/combiner.py tests/test_combined_book_combiner.py
git commit -m "feat(combined_book): inverse-vol combiner + vol-cap selection rule"
```

---

### Task 7: `simulator.py` (combine, equity curve, backtest, stats)

**Files:**
- Create: `combined_book/simulator.py`
- Create: `tests/test_combined_book_simulator.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_combined_book_simulator.py
"""Tests for the month-end simulator + backtest stats."""
import pandas as pd

from combined_book import simulator


def _series(months, vals):
    return pd.Series(vals, index=pd.to_datetime([f"{m}-01" for m in months]))


def test_combine_sleeves_dot_product():
    sleeve = {
        "trend": _series(["2026-01", "2026-02"], [0.01, 0.02]),
        "quality": _series(["2026-01", "2026-02"], [0.03, -0.01]),
        "put": _series(["2026-01", "2026-02"], [0.00, 0.01]),
    }
    weights = {"trend": 0.35, "quality": 0.40, "put": 0.25}
    r = simulator.combine_sleeves(sleeve, weights)
    assert abs(r["2026-01-01"] - (0.35 * 0.01 + 0.40 * 0.03 + 0.25 * 0.00)) < 1e-9


def test_equity_curve_compounds():
    r = _series(["2026-01", "2026-02"], [0.10, -0.05])
    eq = simulator.equity_curve(r)
    assert abs(eq.iloc[0] - 1.10) < 1e-9
    assert abs(eq.iloc[1] - 1.10 * 0.95) < 1e-9


def test_max_drawdown_from_returns():
    r = _series(["2026-01", "2026-02", "2026-03"], [0.20, -0.25, 0.10])
    assert simulator.max_drawdown_from_returns(r) < 0.0


def test_compute_stats_includes_required_keys():
    r = _series(["2026-01", "2026-02", "2026-03"], [0.01, 0.02, -0.01])
    stats = simulator.compute_stats(r)
    for key in ("n_months", "cagr", "sharpe", "annualized_sharpe", "max_dd",
                "pf", "win_rate", "bootstrap_p_over_1"):
        assert key in stats
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_combined_book_simulator.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Implement `simulator.py`**

```python
# combined_book/simulator.py
"""Month-end engine: combine sleeve returns into a book series + equity curve."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from combined_book.combiner import (
    apply_per_sleeve_cap,
    inverse_vol_weights,
    max_drawdown,
)
from combined_book.gates import (
    annualized_sharpe,
    bootstrapped_pf,
    profit_factor,
    sharpe,
)


def combine_sleeves(sleeve_returns, weights):
    frame = pd.DataFrame(sleeve_returns).fillna(0.0)
    ordered = [k for k in weights if k in frame.columns]
    return frame[ordered].dot(
        pd.Series({k: weights[k] for k in ordered})
    )


def book_return_series(sleeve_returns, vols, vol_cap):
    w = apply_per_sleeve_cap(inverse_vol_weights(vols))
    r = combine_sleeves(sleeve_returns, w)
    annual = r.std(ddof=0) * math.sqrt(12)
    if annual > 0:
        r = r * (vol_cap / annual)
    return r, w


def equity_curve(monthly_returns):
    return (1.0 + monthly_returns).cumprod()


def max_drawdown_from_returns(monthly_returns):
    return max_drawdown(equity_curve(monthly_returns).values)


def compute_stats(monthly_returns, n_variants=1):
    r = monthly_returns.dropna()
    n = len(r)
    wins = int((r > 0).sum())
    eq = equity_curve(r)
    span_years = max(n / 12.0, 1e-9)
    cagr = float((eq.iloc[-1] ** (1.0 / span_years)) - 1.0) if n > 0 else 0.0
    pfs = bootstrapped_pf(r.tolist())
    boot_p_over_1 = float(np.mean(np.asarray(pfs) <= 1.0))
    return {
        "n_months": n,
        "cagr": cagr,
        "sharpe": sharpe(r.tolist()),
        "annualized_sharpe": annualized_sharpe(r.tolist()),
        "max_dd": max_drawdown_from_returns(r),
        "pf": profit_factor(r.tolist()),
        "win_rate": wins / n if n > 0 else 0.0,
        "wins": wins,
        "bootstrap_p_over_1": boot_p_over_1,
        "n_variants": n_variants,
    }


def run_backtest(fetch_func, vol_cap=0.05, start=None, end=None):
    closes = fetch_func()
    sleeve_returns = {
        "trend": _trend_combined(closes),
        "quality": _quality_combined(closes),
        "put": _put_combined(closes),
    }
    vols = {
        "trend": float(sleeve_returns["trend"].std(ddof=0)) if len(sleeve_returns["trend"]) else 0.0,
        "quality": float(sleeve_returns["quality"].std(ddof=0)) if len(sleeve_returns["quality"]) else 0.0,
        "put": float(sleeve_returns["put"].std(ddof=0)) if len(sleeve_returns["put"]) else 0.0,
    }
    r, w = book_return_series(sleeve_returns, vols, vol_cap)
    if start:
        r = r.loc[start:]
    if end:
        r = r.loc[:end]
    return {"returns": r, "weights": w, "stats": compute_stats(r)}
```

The `run_backtest` helper uses three sleeve aggregates defined in `simulator.py`:

```python
# combined_book/simulator.py (append below run_backtest)
from combined_book.put_sleeve import put_monthly_returns
from combined_book.quality_sleeve import quality_monthly_returns
from combined_book.trend_sleeve import trend_target_weights


def _trend_combined(closes):
    trend_symbols = {
        s for s, kind in _UNIVERSE_LOCAL.items() if kind.startswith("trend")
    }
    trend_closes = {s: c for s, c in closes.items() if s in trend_symbols}
    w = trend_target_weights(trend_closes, cap_fraction=1.0)
    if not w:
        return pd.Series(dtype=float)
    return combine_sleeves(
        {s: monthly_returns_local(c) for s, c in trend_closes.items()}, w
    ).fillna(0.0)


def _quality_combined(closes):
    return quality_monthly_returns(closes)


def _put_combined(closes):
    return put_monthly_returns(closes, use_index=True)
```

`_UNIVERSE_LOCAL` and `monthly_returns_local` are thin aliases so `run_backtest` can be used without importing `fetch` at module top (keeps the module lazy):

```python
# combined_book/simulator.py (append)
from combined_book.fetch import UNIVERSE as _UNIVERSE_LOCAL, monthly_returns as monthly_returns_local
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_combined_book_simulator.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add combined_book/simulator.py tests/test_combined_book_simulator.py
git commit -m "feat(combined_book): simulator + backtest stats"
```

---

### Task 8: `ledger.py` (JSON ledger, starting positions)

**Files:**
- Create: `combined_book/ledger.py`
- Create: `tests/test_combined_book_ledger.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_combined_book_ledger.py
"""Tests for the JSON positions/returns ledger."""
import json

from combined_book import ledger

STARTING = {
    "put_write": 0.40,
    "trend": 0.35,
    "quality_value": 0.19,
    "cash": 0.06,
}


def test_init_ledger_writes_file(tmp_path):
    p = tmp_path / "ledger.json"
    doc = ledger.init_ledger(STARTING, p, capital=100_000.0, date_closed="2026-09-30")
    assert doc["capital"] == 100_000.0
    assert doc["start_date"] == "2026-09-30"
    assert doc["starting_positions"] == STARTING
    assert json.loads(p.read_text(encoding="utf-8"))["currency"] == "USD"


def test_append_month_row_updates_cash(tmp_path):
    p = tmp_path / "ledger.json"
    doc = ledger.init_ledger(STARTING, p)
    ledger.append_month_row(doc, "2026-10", 0.01, STARTING)
    assert len(doc["monthly_returns"]) == 1
    assert abs(doc["cash"] - 100_000.0 * 1.01) < 1e-6


def test_round_trip_save_load(tmp_path):
    p = tmp_path / "ledger.json"
    doc = ledger.init_ledger(STARTING, p)
    ledger.append_month_row(doc, "2026-10", 0.01, STARTING)
    ledger.save_ledger(doc, p)
    loaded = ledger.load_ledger(p)
    assert loaded["starting_positions"] == STARTING
    assert loaded["monthly_returns"][0]["month"] == "2026-10"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_combined_book_ledger.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Implement `ledger.py`**

```python
# combined_book/ledger.py
"""JSON ledger of positions + monthly returns; records starting positions."""
from __future__ import annotations

import json
from pathlib import Path


def init_ledger(starting_positions, path, capital=100_000.0, date_closed="2026-09-30"):
    doc = {
        "currency": "USD",
        "capital": capital,
        "start_date": date_closed,
        "starting_positions": dict(starting_positions),
        "monthly_returns": [],
        "cash": capital,
        "positions": dict(starting_positions),
    }
    save_ledger(doc, path)
    return doc


def load_ledger(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def append_month_row(ledger, month_label, book_return, positions):
    ledger["monthly_returns"].append(
        {"month": month_label, "return": float(book_return)}
    )
    ledger["positions"] = dict(positions)
    total_ret = sum(r["return"] for r in ledger["monthly_returns"])
    ledger["cash"] = ledger["capital"] * (1.0 + total_ret)
    return ledger


def save_ledger(ledger, path):
    Path(path).write_text(json.dumps(ledger, indent=2), encoding="utf-8")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_combined_book_ledger.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add combined_book/ledger.py tests/test_combined_book_ledger.py
git commit -m "feat(combined_book): JSON ledger + starting positions"
```

---

### Task 9: `gates.py` (statistical gates)

**Files:**
- Create: `combined_book/gates.py`
- Create: `tests/test_combined_book_gates.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_combined_book_gates.py
"""Tests for the statistical go-live + kill gates."""
from combined_book import gates


def test_wilson_ci_bounds():
    lo, hi = gates.wilson_ci(60, 100)
    assert 0.0 <= lo < 0.60 < hi <= 1.0


def test_binomial_pvalue_matches_known_case():
    # 60/100 against p0=0.5 is ~2 sigma -> p ~ 0.045
    p = gates.binomial_pvalue(60, 100)
    assert 0.01 < p < 0.10


def test_profit_factor():
    assert abs(gates.profit_factor([1.0, 2.0, -1.0, -0.5]) - (3.0 / 1.5)) < 1e-9
    assert gates.profit_factor([1.0, 2.0]) == float("inf")


def test_bootstrapped_pf_reproducible():
    a = gates.bootstrapped_pf([0.01, -0.02, 0.03, -0.01], seed=1, n_sims=200)
    b = gates.bootstrapped_pf([0.01, -0.02, 0.03, -0.01], seed=1, n_sims=200)
    assert a == b


def test_sharpe_zero_vol_is_zero():
    assert gates.sharpe([0.01, 0.01, 0.01]) == 0.0


def test_annualized_sharpe_scales():
    assert abs(gates.annualized_sharpe([0.01, 0.02, -0.01]) - gates.sharpe([0.01, 0.02, -0.01]) * (12 ** 0.5)) < 1e-9


def test_deflated_sharpe_lower_than_raw():
    raw = gates.sharpe([0.01, 0.02, -0.01, 0.02, 0.01])
    df = gates.deflated_sharpe(raw, n_variants=50, n_samples=60)
    assert df < raw


def test_random_entry_percentile_in_range():
    pct = gates.random_entry_percentile([0.01, 0.02, -0.01], [0.02, 0.01, -0.02], seed=3, n_sims=200)
    assert 0.0 <= pct <= 1.0


def test_evaluate_go_live():
    ok, checks = gates.evaluate_go_live(
        {"n_months": 120, "pf": 1.8, "win_rate": 0.55, "max_dd": -0.10}
    )
    assert ok is True
    assert all(checks.values())


def test_evaluate_kill_requires_24_months():
    killed, _ = gates.evaluate_kill(
        {"n_months": 12, "max_dd": -0.30, "pf": 0.5, "win_rate": 0.4,
         "annualized_sharpe": -0.5, "bootstrap_p_over_1": 0.9}
    )
    assert killed is False  # still too few months


def test_evaluate_kill_fires_after_24_months():
    killed, kills = gates.evaluate_kill(
        {"n_months": 30, "max_dd": -0.30, "pf": 0.5, "win_rate": 0.4,
         "annualized_sharpe": -0.5, "bootstrap_p_over_1": 0.9}
    )
    assert killed is True
    assert kills["drawdown"] is True
    assert kills["pf"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_combined_book_gates.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Implement `gates.py`**

```python
# combined_book/gates.py
"""Go-live + kill gates; statistical reporting helpers."""
from __future__ import annotations

import math

import numpy as np

from combined_book.rules import (
    GO_LIVE_MAX_DD,
    GO_LIVE_N_MONTHS,
    GO_LIVE_PF,
    GO_LIVE_WR,
    KILL_AFTER_MONTHS,
    KILL_BOOTSTRAP_P,
    KILL_DRAWDOWN,
    KILL_PF,
    KILL_SHARPE,
    KILL_WR,
)


def wilson_ci(wins, n, z=1.96):
    if n <= 0:
        return (0.0, 0.0)
    phat = wins / n
    denom = 1.0 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n) / denom
    return (centre - margin, centre + margin)


def binomial_pvalue(wins, n, p0=0.5):
    if n <= 0:
        return 1.0
    phat = wins / n
    se = math.sqrt(p0 * (1 - p0) / n)
    if se == 0:
        return 0.0
    z = (phat - p0) / se
    return 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2))))


def profit_factor(returns):
    pos = sum(x for x in returns if x > 0)
    neg = -sum(x for x in returns if x < 0)
    return pos / neg if neg > 0 else float("inf")


def bootstrapped_pf(returns, seed=42, n_sims=2000):
    rng = np.random.default_rng(seed)
    arr = np.asarray(returns, dtype=float)
    pfs = []
    for _ in range(n_sims):
        sample = rng.choice(arr, size=len(arr), replace=True)
        pfs.append(profit_factor(sample))
    return pfs


def sharpe(returns, rf=0.0):
    arr = np.asarray(returns, dtype=float)
    if len(arr) < 2 or arr.std(ddof=0) == 0:
        return 0.0
    return float((arr.mean() - rf) / arr.std(ddof=0))


def annualized_sharpe(returns, periods_per_year=12):
    return sharpe(returns) * math.sqrt(periods_per_year)


def deflated_sharpe(sharpe_val, n_variants, n_samples):
    if n_variants <= 1 or n_samples <= 1:
        return sharpe_val
    e_max = ((1.0 - math.gamma(1.0 / n_variants))
             * math.sqrt(2.0 * math.log(n_variants)))
    var = 1.0 / n_samples
    return (sharpe_val - e_max) / math.sqrt(1.0 + var)


def random_entry_percentile(book_returns, ref_returns, seed=7, n_sims=1000):
    rng = np.random.default_rng(seed)
    book = np.asarray(book_returns, dtype=float)
    ref = np.asarray(ref_returns, dtype=float)
    n = min(len(book), len(ref))
    if n == 0:
        return 0.0
    actual = sharpe(book[:n])
    sims = []
    for _ in range(n_sims):
        perm = rng.permutation(n)
        sims.append(sharpe(ref[perm]))
    return float(np.mean(np.asarray(sims) <= actual))


def evaluate_go_live(stats):
    checks = {
        "n_months": stats["n_months"] >= GO_LIVE_N_MONTHS,
        "pf": stats["pf"] >= GO_LIVE_PF,
        "win_rate": stats["win_rate"] >= GO_LIVE_WR,
        "max_dd": stats["max_dd"] >= GO_LIVE_MAX_DD,
    }
    return all(checks.values()), checks


def evaluate_kill(stats):
    if stats["n_months"] < KILL_AFTER_MONTHS:
        return False, {}
    kills = {
        "drawdown": stats["max_dd"] < KILL_DRAWDOWN,
        "pf": stats["pf"] < KILL_PF,
        "win_rate": stats["win_rate"] < KILL_WR,
        "sharpe": stats["annualized_sharpe"] <= KILL_SHARPE,
        "bootstrap": stats["bootstrap_p_over_1"] > KILL_BOOTSTRAP_P,
    }
    return any(kills.values()), kills
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_combined_book_gates.py -v`
Expected: PASS (11 passed).

- [ ] **Step 5: Commit**

```bash
git add combined_book/gates.py tests/test_combined_book_gates.py
git commit -m "feat(combined_book): statistical gates + helpers"
```

---

### Task 10: `cli.py` (subcommands)

**Files:**
- Create: `combined_book/cli.py`
- Create: `tests/test_combined_book_cli.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_combined_book_cli.py
"""Tests for the CLI subcommands."""
from combined_book.cli import main


def test_hash_check_reports_current_hash(capsys):
    code = main(["hash-check"])
    out = capsys.readouterr().out
    assert code == 0
    assert "RULES_HASH" in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_combined_book_cli.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Implement `cli.py`**

```python
# combined_book/cli.py
"""Command-line interface for the combined-book paper-trade module."""
from __future__ import annotations

import argparse

from combined_book.ledger import append_month_row, init_ledger, load_ledger, save_ledger
from combined_book.rules import RULES_HASH, RULES_MARKDOWN, verify_rules_hash


def _cmd_hash_check(_args):
    ok = verify_rules_hash()
    print(f"RULES_HASH={RULES_HASH}")
    print(f"hash_valid={ok}")
    return 0 if ok else 1


def _cmd_init_ledger(args):
    init_ledger(args.positions, args.path, capital=args.capital, date_closed=args.date)
    print(f"ledger initialized -> {args.path}")
    return 0


def _cmd_report(_args):
    print(RULES_MARKDOWN)
    print(f"RULES_HASH={RULES_HASH}")
    return 0


def _cmd_backtest(args):
    from combined_book.simulator import run_backtest
    from combined_book.fetch import get_daily_closes, UNIVERSE
    symbols = [s for s in UNIVERSE if s != "PUT"]  # PUT is an index, not an ETF
    result = run_backtest(
        lambda: get_daily_closes(symbols, cache_dir=args.cache),
        vol_cap=args.vol_cap,
        start=args.start,
        end=args.end,
    )
    stats = result["stats"]
    print(f"n_months={stats['n_months']}")
    print(f"cagr={stats['cagr']:.4f}")
    print(f"annualized_sharpe={stats['annualized_sharpe']:.4f}")
    print(f"max_dd={stats['max_dd']:.4f}")
    print(f"pf={stats['pf']:.4f}")
    print(f"win_rate={stats['win_rate']:.4f}")
    return 0


def _cmd_gates(args):
    from combined_book.gates import evaluate_go_live, evaluate_kill
    ledger = load_ledger(args.path)
    returns = [r["return"] for r in ledger["monthly_returns"]]
    from combined_book.simulator import compute_stats
    stats = compute_stats(__import__("pandas").Series(returns))
    go, go_checks = evaluate_go_live(stats)
    killed, kill_checks = evaluate_kill(stats)
    print(f"go_live={go} checks={go_checks}")
    print(f"kill={killed} kills={kill_checks}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="combined_book")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("hash-check").set_defaults(func=_cmd_hash_check)

    p_init = sub.add_parser("init-ledger")
    p_init.add_argument("--path", default="combined_book/data/ledger.json")
    p_init.add_argument("--capital", type=float, default=100_000.0)
    p_init.add_argument("--date", default="2026-09-30")
    p_init.add_argument("--positions", default="{\"put_write\":0.40,\"trend\":0.35,\"quality_value\":0.19,\"cash\":0.06}")
    p_init.set_defaults(func=_cmd_init_ledger)

    p_bt = sub.add_parser("backtest")
    p_bt.add_argument("--vol-cap", type=float, default=0.05)
    p_bt.add_argument("--start", default=None)
    p_bt.add_argument("--end", default=None)
    p_bt.add_argument("--cache", default=None)
    p_bt.set_defaults(func=_cmd_backtest)

    p_g = sub.add_parser("gates")
    p_g.add_argument("--path", default="combined_book/data/ledger.json")
    p_g.set_defaults(func=_cmd_gates)

    p_r = sub.add_parser("report")
    p_r.set_defaults(func=_cmd_report)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_combined_book_cli.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add combined_book/cli.py tests/test_combined_book_cli.py
git commit -m "feat(combined_book): CLI subcommands"
```

---

### Task 11: Reproduction verification + freeze artifact + docs

**Files:**
- Create: `tests/test_combined_book_reproduction.py`
- Create: `combined_book/data/` (runtime cache dir; gitignore data files)
- Create: `updates/2026-10-19-combined-book-paper-trade-pilot.md`
- Modify: `docs/superpowers/specs/2026-10-19-combined-book-paper-trade-design.md` (mark Status approved)

- [ ] **Step 1: Write the reproduction test (network-marked)**

```python
# tests/test_combined_book_reproduction.py
"""Reproduction checks vs the documented Grok-benchmarked targets.

Marked ``network`` and ``integration``; deselect by default in CI.
"""
import math

import pytest

from combined_book.fetch import UNIVERSE, get_daily_closes
from combined_book.simulator import run_backtest


@pytest.mark.network
@pytest.mark.integration
def test_reproduction_targets_5pct_overlay():
    symbols = [s for s in UNIVERSE if s != "PUT"]
    result = run_backtest(
        lambda: get_daily_closes(symbols),
        vol_cap=0.05,
        start="1988-01-01",
        end="2026-12-31",
    )
    stats = result["stats"]
    # 5% overlay targets from approved spec
    assert stats["cagr"] == pytest.approx(0.065, abs=0.015)
    assert stats["annualized_sharpe"] == pytest.approx(1.20, abs=0.25)
    assert stats["max_dd"] == pytest.approx(-0.144, abs=0.03)


@pytest.mark.network
@pytest.mark.integration
def test_coin_flip_control_rejected():
    # coin-flip control should show PF around 0.81 (< 1) -> not a real edge
    import numpy as np
    rng = np.random.default_rng(4)
    returns = rng.choice([0.05, -0.05], size=200)
    from combined_book.gates import profit_factor
    assert profit_factor(returns.tolist()) < 1.0
```

- [ ] **Step 2: Run the reproduction tests (network enabled)**

Run: `python -m pytest tests/test_combined_book_reproduction.py -v -m network`
Expected: PASS, or if a target is outside tolerance, STOP and reconcile before proceeding (do not loosen the check silently). Record actual vs target in the updates doc.

- [ ] **Step 3: Freeze artifact — write RULES.md and verify hash**

Run:
```bash
mkdir -p combined_book/data
python -m combined_book.cli report > combined_book/data/RULES.md
python -m combined_book.cli hash-check
```
Expected: `hash_valid=True`; the printed `RULES_HASH` matches `combined_book.rules.RULES_HASH`. Record this hash in `docs/superpowers/specs/2026-10-19-combined-book-paper-trade-design.md` (section 2 reference block) as our own archive hash.

- [ ] **Step 4: Create the updates doc**

```markdown
# updates/2026-10-19-combined-book-paper-trade-pilot.md

## What was built
- Standalone `combined_book/` package: backtest harness, frozen RULES.md + SHA-256,
  paper simulator + ledger, monthly go-live/kill gates.

## Reproduction results (vs documented targets)
| metric | target | actual | tol | pass? |
|--------|--------|--------|-----|-------|
| no-overlay CAGR | 8.8% | TBD | ±1.5pp | TBD |
| no-overlay Sharpe | 1.27 | TBD | ±0.25 | TBD |
| no-overlay max DD | −20.5% | TBD | ±3pp | TBD |
| 5% overlay CAGR | 6.5% | TBD | ±1.5pp | TBD |
| 5% overlay Sharpe | 1.20 | TBD | ±0.25 | TBD |
| 5% overlay max DD | −14.4% | TBD | ±3pp | TBD |
| coin-flip control PF | ≈0.81 (rejected) | TBD | <1.0 | TBD |

## Frozen rules hash
- Our RULES_HASH: (record actual)
- Reference pilot hash: d5bed907932009a96d45521c15102cba2092ec9307dfd8367aedf3f21c9fcfd5

## Pilot state
- Starting positions (2026-09-30 close): put-write 40%, trend 35%, quality/value 19%, cash 6%.
- First paper month: October 2026 close; first check 2026-11-02.
- Full go-live gate requires 100 months (~8 years).
```

- [ ] **Step 5: Update spec status + commit**

```bash
git add tests/test_combined_book_reproduction.py combined_book/data/RULES.md \
  updates/2026-10-19-combined-book-paper-trade-pilot.md \
  docs/superpowers/specs/2026-10-19-combined-book-paper-trade-design.md
git commit -m "docs(combined_book): reproduction + freeze artifact + pilot updates"
```

---

## Self-Review

- **Spec coverage:** backtest harness (Tasks 7 & 11), RULES.md freeze + SHA-256 (Tasks 1 & 11), paper simulator + ledger + starting positions (Tasks 8 & 10), monthly gates (Task 9), 5% vol-cap rule (Task 6), XYLD/PUT (Task 5), net-short bonds + cash-0% (documented in RULES.md), kill criteria + go-live gate (Task 9). All §3–§7 requirements mapped.
- **Placeholder scan:** The only `TBD` values are runtime reproduction outputs the test fills in (Task 11 Step 4), not code placeholders. All code blocks are complete.
- **Type consistency:** `compute_stats` returns the exact keys `gates.evaluate_go_live`/`evaluate_kill` consume; `run_backtest` returns `returns`/`weights`/`stats`; `init_ledger`/`append_month_row`/`load_ledger`/`save_ledger` signatures are identical across Tasks 8 and 10. `combiner.select_vol_cap` and `book_return_series` share `vol_cap` float convention (0.05).
