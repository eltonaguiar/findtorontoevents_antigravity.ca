# ai4trade Promotion Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the validation layer that decides which ai4trade.ai originator agents earn a real `.py` file in `baby_strategies/`, based on forward-tracked picks produced by a separate ingestor.

**Architecture:** Two source files (`ai4trade_promotion_gate.py` orchestrator + `ai4trade_gate_criteria.py` pure-function criteria) plus a fixture factory. Seven gate criteria are independent pure functions over a list of closed picks. Orchestrator loads picks tagged `source_system="ai4trade"`, groups by `agent_id`, runs each criterion, writes `audit_dashboard/data/ai4trade_gate_report.json`. Promoted agents get an auto-generated wrapper file in `baby_strategies/pending/`, NOT `baby_strategies/` — human move activates.

**Tech Stack:** Python 3.13+, pytest, numpy (already a dep), no new packages. Reuses `alpha_engine.darwin_score_v2_calculator`, `alpha_engine.momentum_catcher.fetch_btc_4h_regime`, `alpha_engine.forward_validator`.

**Spec reference:** [docs/superpowers/specs/2026-04-14-ai4trade-promotion-gate-design.md](../specs/2026-04-14-ai4trade-promotion-gate-design.md)

**Peer coordination:** The ingestor (Cursor's `alpha_engine/ai_trader_crowd_intel.py`) is out of scope. This plan assumes that, by the time the gate runs, picks with `source_system == "ai4trade"` and a top-level `agent_id` field exist in the normal pick pipeline. If the ingestor is not yet wired, the gate runs clean and reports zero tracked agents.

---

## File Structure

| File | Role | Max size (guideline) |
|------|------|----------------------|
| `alpha_engine/ai4trade_gate_criteria.py` | Pure functions, one per gate criterion. No I/O. | ~300 lines |
| `alpha_engine/ai4trade_promotion_gate.py` | Orchestrator: load picks, group by agent, run criteria, write report, render wrappers, CLI. | ~350 lines |
| `tests/fixtures/ai4trade_picks.py` | Synthetic pick factory for unit + integration tests. | ~120 lines |
| `tests/test_ai4trade_gate_criteria.py` | One test per criterion, isolated. | ~400 lines |
| `tests/test_ai4trade_promotion_gate.py` | End-to-end integration test. | ~200 lines |
| `audit_dashboard/data/ai4trade_gate_report.json` | Output artifact. Written at runtime. | N/A |
| `baby_strategies/pending/ai4trade_agent_<id>.py` | Auto-generated wrapper. Written at runtime. | ~60 lines each |

**Do NOT edit:**
- `alpha_engine/scanner.py` (no new imports)
- `alpha_engine/config.py` (no new `STRATEGY_FAMILIES` entries — those land only when a human moves a wrapper out of `pending/`)
- `baby_strategies/pending/AUDIT_FINDINGS.md` (Cursor's audit, preserve as-is)

---

## Data Contract

Every function in this plan operates on a **Pick** dict with this schema (a subset of the existing closed-pick schema in the forward-validator pipeline):

```python
# A closed ai4trade pick, as produced by the ingestor and annotated by forward validator
Pick = {
    "source_system": "ai4trade",                    # REQUIRED, filter key
    "agent_id": 784,                                # REQUIRED, int, originator agent id
    "agent_display_name": "ClaudeTrader",           # optional, str
    "is_copy_trade": False,                         # REQUIRED, bool, True if copy of upstream agent
    "symbol": "BTCUSDT",                            # REQUIRED, str
    "direction": "LONG",                            # REQUIRED, "LONG" or "SHORT"
    "first_tracked_at": "2026-04-14T00:00:00Z",    # REQUIRED, ISO str, when WE first saw it
    "closed_at": "2026-04-16T04:00:00Z",           # REQUIRED if closed, ISO str
    "status": "closed",                             # REQUIRED, "open" or "closed"
    "pnl_pct": 2.34,                                # REQUIRED if closed, float, -100..inf
    "pnl_usd": 234.12,                              # optional, float
    "entry_price": 72000.0,                         # optional, float
    "exit_price": 73685.0,                          # optional, float
}
```

**Agent** is a derived type used inside this module only:

```python
Agent = {
    "agent_id": 784,
    "display_name": "ClaudeTrader",
    "picks": [Pick, ...],               # all picks we've seen from this agent
    "closed_picks": [Pick, ...],        # filtered subset where status == "closed"
    "first_tracked_at": datetime,       # min(pick["first_tracked_at"] for pick in picks)
}
```

---

## Task 1: Test fixture factory

**Files:**
- Create: `tests/fixtures/__init__.py` (empty, if missing)
- Create: `tests/fixtures/ai4trade_picks.py`
- Test: N/A — this is fixture-only

- [ ] **Step 1: Create empty `__init__.py` if missing**

Run: `test -f tests/fixtures/__init__.py || touch tests/fixtures/__init__.py`

- [ ] **Step 2: Write the fixture factory**

Create `tests/fixtures/ai4trade_picks.py`:

```python
"""Synthetic ai4trade pick factory for unit + integration tests.

Every factory helper returns dicts that match the Pick schema used by
alpha_engine.ai4trade_promotion_gate and alpha_engine.ai4trade_gate_criteria.
"""
from datetime import datetime, timedelta, timezone
from typing import Iterable

UTC = timezone.utc


def make_pick(
    agent_id: int,
    symbol: str = "BTCUSDT",
    direction: str = "LONG",
    pnl_pct: float = 1.0,
    days_ago_closed: int = 1,
    days_ago_first_tracked: int = 2,
    is_copy_trade: bool = False,
    status: str = "closed",
    display_name: str = "test_agent",
) -> dict:
    now = datetime.now(UTC)
    first_tracked = now - timedelta(days=days_ago_first_tracked)
    closed = now - timedelta(days=days_ago_closed) if status == "closed" else None
    return {
        "source_system": "ai4trade",
        "agent_id": agent_id,
        "agent_display_name": display_name,
        "is_copy_trade": is_copy_trade,
        "symbol": symbol,
        "direction": direction,
        "first_tracked_at": first_tracked.isoformat().replace("+00:00", "Z"),
        "closed_at": closed.isoformat().replace("+00:00", "Z") if closed else None,
        "status": status,
        "pnl_pct": pnl_pct,
        "pnl_usd": pnl_pct * 100,
        "entry_price": 72000.0,
        "exit_price": 72000.0 * (1 + pnl_pct / 100),
    }


def make_agent_picks(
    agent_id: int,
    n: int = 30,
    wr_pct: float = 60.0,
    avg_win: float = 2.0,
    avg_loss: float = -1.5,
    direction_mix: str = "mixed",  # "mixed", "long_only", "short_only"
    weeks_ago_first_tracked: float = 8.5,
    is_copy_trade: bool = False,
    display_name: str = "test_agent",
) -> list[dict]:
    """Build n closed picks for one agent with the target WR."""
    n_wins = round(n * wr_pct / 100)
    n_losses = n - n_wins
    picks: list[dict] = []
    first_tracked_days = int(weeks_ago_first_tracked * 7)
    for i in range(n):
        is_win = i < n_wins
        pnl = avg_win if is_win else avg_loss
        if direction_mix == "long_only":
            direction = "LONG"
        elif direction_mix == "short_only":
            direction = "SHORT"
        else:
            direction = "LONG" if i % 2 == 0 else "SHORT"
        picks.append(make_pick(
            agent_id=agent_id,
            direction=direction,
            pnl_pct=pnl,
            days_ago_closed=max(1, first_tracked_days - i),
            days_ago_first_tracked=first_tracked_days,
            is_copy_trade=is_copy_trade,
            display_name=display_name,
        ))
    return picks


def flatten(*groups: Iterable[dict]) -> list[dict]:
    out: list[dict] = []
    for g in groups:
        out.extend(g)
    return out
```

- [ ] **Step 3: Commit**

```bash
git add tests/fixtures/__init__.py tests/fixtures/ai4trade_picks.py
git commit -m "test(ai4trade): add synthetic pick fixture factory"
```

---

## Task 2: Criterion 1 — originator-only filter

**Files:**
- Create: `alpha_engine/ai4trade_gate_criteria.py`
- Test: `tests/test_ai4trade_gate_criteria.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_ai4trade_gate_criteria.py`:

```python
"""Unit tests for alpha_engine.ai4trade_gate_criteria (one test per criterion)."""
from tests.fixtures.ai4trade_picks import make_agent_picks, flatten
from alpha_engine import ai4trade_gate_criteria as C


def test_originator_only_rejects_pure_copy_agent():
    picks = make_agent_picks(agent_id=1, n=30, is_copy_trade=True)
    result = C.originator_only(picks)
    assert result.passed is False
    assert "copy" in result.reason.lower()


def test_originator_only_passes_mixed_agent():
    originals = make_agent_picks(agent_id=1, n=20, is_copy_trade=False)
    copies = make_agent_picks(agent_id=1, n=10, is_copy_trade=True)
    result = C.originator_only(flatten(originals, copies))
    assert result.passed is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ai4trade_gate_criteria.py::test_originator_only_rejects_pure_copy_agent -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'alpha_engine.ai4trade_gate_criteria'`.

- [ ] **Step 3: Write minimal implementation**

Create `alpha_engine/ai4trade_gate_criteria.py`:

```python
"""Pure-function gate criteria for the ai4trade promotion gate.

Each function takes a list of closed Pick dicts for ONE agent and returns
a CriterionResult. No I/O. No globals (except imported constants). Deterministic.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class CriterionResult:
    passed: bool
    reason: str
    detail: dict | None = None


def originator_only(picks: list[dict]) -> CriterionResult:
    """Pass if the agent has at least one non-copy signal."""
    originals = [p for p in picks if not p.get("is_copy_trade", False)]
    if not originals:
        return CriterionResult(
            passed=False,
            reason="agent has no originator signals — all picks are copy-trades",
            detail={"n_total": len(picks), "n_originals": 0},
        )
    return CriterionResult(
        passed=True,
        reason="has originator signals",
        detail={"n_total": len(picks), "n_originals": len(originals)},
    )
```

- [ ] **Step 4: Run both tests to verify they pass**

Run: `python -m pytest tests/test_ai4trade_gate_criteria.py -v`

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add alpha_engine/ai4trade_gate_criteria.py tests/test_ai4trade_gate_criteria.py
git commit -m "feat(ai4trade): criterion 1 — originator-only filter"
```

---

## Task 3: Criterion 2 — forward sample size (n ≥ 30 closed)

**Files:**
- Modify: `alpha_engine/ai4trade_gate_criteria.py`
- Modify: `tests/test_ai4trade_gate_criteria.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ai4trade_gate_criteria.py`:

```python
def test_forward_sample_rejects_n_below_30():
    picks = make_agent_picks(agent_id=1, n=29)
    result = C.forward_sample(picks, min_n=30)
    assert result.passed is False
    assert "29" in result.reason

def test_forward_sample_passes_n_30():
    picks = make_agent_picks(agent_id=1, n=30)
    result = C.forward_sample(picks, min_n=30)
    assert result.passed is True

def test_forward_sample_excludes_open_picks():
    closed = make_agent_picks(agent_id=1, n=25)
    opens = [{**p, "status": "open", "closed_at": None} for p in
             make_agent_picks(agent_id=1, n=10)]
    result = C.forward_sample(closed + opens, min_n=30)
    assert result.passed is False
    assert result.detail["n_closed"] == 25
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ai4trade_gate_criteria.py -v -k forward_sample`

Expected: 3 errors/failures with `AttributeError: module '...' has no attribute 'forward_sample'`.

- [ ] **Step 3: Add the implementation**

Append to `alpha_engine/ai4trade_gate_criteria.py`:

```python
def forward_sample(picks: list[dict], min_n: int = 30) -> CriterionResult:
    """Pass if the agent has at least min_n CLOSED picks. Open picks don't count."""
    closed = [p for p in picks if p.get("status") == "closed"]
    n_closed = len(closed)
    if n_closed < min_n:
        return CriterionResult(
            passed=False,
            reason=f"only {n_closed} closed picks — need {min_n}",
            detail={"n_closed": n_closed, "min_n": min_n},
        )
    return CriterionResult(
        passed=True,
        reason=f"{n_closed} closed picks",
        detail={"n_closed": n_closed, "min_n": min_n},
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ai4trade_gate_criteria.py -v`

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add alpha_engine/ai4trade_gate_criteria.py tests/test_ai4trade_gate_criteria.py
git commit -m "feat(ai4trade): criterion 2 — forward sample n≥30 closed"
```

---

## Task 4: Criterion 3 — time under test (≥ 8 weeks)

**Files:**
- Modify: `alpha_engine/ai4trade_gate_criteria.py`
- Modify: `tests/test_ai4trade_gate_criteria.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ai4trade_gate_criteria.py`:

```python
def test_time_under_test_rejects_too_recent():
    picks = make_agent_picks(agent_id=1, n=30, weeks_ago_first_tracked=4.0)
    result = C.time_under_test(picks, min_weeks=8)
    assert result.passed is False

def test_time_under_test_passes_8_weeks():
    picks = make_agent_picks(agent_id=1, n=30, weeks_ago_first_tracked=8.1)
    result = C.time_under_test(picks, min_weeks=8)
    assert result.passed is True
    assert result.detail["weeks_under_test"] >= 8.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ai4trade_gate_criteria.py -v -k time_under_test`

Expected: 2 errors.

- [ ] **Step 3: Add the implementation**

Append to `alpha_engine/ai4trade_gate_criteria.py`:

```python
from datetime import datetime, timezone


def _parse_iso(s: str) -> datetime:
    """Parse an ISO-8601 string with trailing Z. Always returns tz-aware UTC."""
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def time_under_test(picks: list[dict], min_weeks: float = 8.0) -> CriterionResult:
    """Pass if max(now - first_tracked_at) for the agent is ≥ min_weeks.

    First-tracked means WE first saw the signal. Historical performance on
    ai4trade.ai before we started tracking does not count.
    """
    if not picks:
        return CriterionResult(passed=False, reason="no picks", detail={"weeks_under_test": 0.0})
    firsts = [_parse_iso(p["first_tracked_at"]) for p in picks if p.get("first_tracked_at")]
    if not firsts:
        return CriterionResult(passed=False, reason="no first_tracked_at timestamps",
                               detail={"weeks_under_test": 0.0})
    earliest = min(firsts)
    now = datetime.now(timezone.utc)
    weeks = (now - earliest).total_seconds() / (7 * 86400)
    if weeks < min_weeks:
        return CriterionResult(
            passed=False,
            reason=f"only {weeks:.1f} weeks under test — need {min_weeks}",
            detail={"weeks_under_test": round(weeks, 2), "min_weeks": min_weeks},
        )
    return CriterionResult(
        passed=True,
        reason=f"{weeks:.1f} weeks under test",
        detail={"weeks_under_test": round(weeks, 2), "min_weeks": min_weeks},
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ai4trade_gate_criteria.py -v`

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add alpha_engine/ai4trade_gate_criteria.py tests/test_ai4trade_gate_criteria.py
git commit -m "feat(ai4trade): criterion 3 — ≥8 weeks under test"
```

---

## Task 5: Criterion 4 — regime coverage (≥ 48h red BTC 4h)

**Files:**
- Modify: `alpha_engine/ai4trade_gate_criteria.py`
- Modify: `tests/test_ai4trade_gate_criteria.py`

**Rationale:** Prevents rally-only survivors. Needs a callable injected by the orchestrator so tests don't hit the network.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ai4trade_gate_criteria.py`:

```python
def test_regime_coverage_passes_with_48h_red_period():
    picks = make_agent_picks(agent_id=1, n=30, weeks_ago_first_tracked=10)
    # Fake regime series: 60h of "red" sandwiched inside the tracking window.
    def fake_regime_hours(_from, _to):
        return {"red_hours_total": 60.0, "longest_red_run_hours": 60.0}
    result = C.regime_coverage(picks, min_red_hours=48, regime_fn=fake_regime_hours)
    assert result.passed is True

def test_regime_coverage_rejects_rally_only():
    picks = make_agent_picks(agent_id=1, n=30, weeks_ago_first_tracked=10)
    def fake_regime_hours(_from, _to):
        return {"red_hours_total": 12.0, "longest_red_run_hours": 12.0}
    result = C.regime_coverage(picks, min_red_hours=48, regime_fn=fake_regime_hours)
    assert result.passed is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ai4trade_gate_criteria.py -v -k regime_coverage`

Expected: 2 errors.

- [ ] **Step 3: Add the implementation**

Append to `alpha_engine/ai4trade_gate_criteria.py`:

```python
from typing import Callable


def regime_coverage(
    picks: list[dict],
    min_red_hours: float = 48.0,
    regime_fn: Callable[[datetime, datetime], dict] | None = None,
) -> CriterionResult:
    """Pass if tracking window spans ≥min_red_hours of red BTC 4h regime,
    with longest_red_run_hours also ≥min_red_hours (one contiguous stretch)."""
    if regime_fn is None:
        raise ValueError("regime_fn is required — inject from orchestrator")
    if not picks:
        return CriterionResult(passed=False, reason="no picks", detail={})
    firsts = [_parse_iso(p["first_tracked_at"]) for p in picks if p.get("first_tracked_at")]
    earliest = min(firsts)
    latest = datetime.now(timezone.utc)
    stats = regime_fn(earliest, latest)
    longest_run = float(stats.get("longest_red_run_hours", 0.0))
    if longest_run < min_red_hours:
        return CriterionResult(
            passed=False,
            reason=(f"longest red BTC 4h run = {longest_run:.1f}h "
                    f"— need {min_red_hours}h contiguous"),
            detail={**stats, "min_red_hours": min_red_hours},
        )
    return CriterionResult(
        passed=True,
        reason=f"longest red run {longest_run:.1f}h covers bar",
        detail={**stats, "min_red_hours": min_red_hours},
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ai4trade_gate_criteria.py -v`

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add alpha_engine/ai4trade_gate_criteria.py tests/test_ai4trade_gate_criteria.py
git commit -m "feat(ai4trade): criterion 4 — ≥48h red BTC 4h regime coverage"
```

---

## Task 6: Criterion 5 — tier-1 stats (WR/PF/DD/Darwin)

**Files:**
- Modify: `alpha_engine/ai4trade_gate_criteria.py`
- Modify: `tests/test_ai4trade_gate_criteria.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_ai4trade_gate_criteria.py`:

```python
def test_tier1_stats_passes_strong_agent():
    picks = make_agent_picks(agent_id=1, n=50, wr_pct=58, avg_win=2.0, avg_loss=-1.2)
    result = C.tier1_stats(picks, min_wr=55, min_pf=1.5, max_dd=20, min_darwin_v2=0.3)
    assert result.passed is True

def test_tier1_stats_fails_low_wr():
    picks = make_agent_picks(agent_id=1, n=50, wr_pct=48, avg_win=2.0, avg_loss=-1.2)
    result = C.tier1_stats(picks, min_wr=55, min_pf=1.5, max_dd=20, min_darwin_v2=0.3)
    assert result.passed is False
    assert "wr" in result.reason.lower()

def test_tier1_stats_fails_low_pf():
    picks = make_agent_picks(agent_id=1, n=50, wr_pct=55, avg_win=1.0, avg_loss=-1.2)
    result = C.tier1_stats(picks, min_wr=55, min_pf=1.5, max_dd=20, min_darwin_v2=0.3)
    assert result.passed is False
    assert "pf" in result.reason.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ai4trade_gate_criteria.py -v -k tier1_stats`

Expected: 3 errors.

- [ ] **Step 3: Add the implementation**

Append to `alpha_engine/ai4trade_gate_criteria.py`:

```python
import math


def _compute_stats(closed_picks: list[dict]) -> dict:
    """Return WR%, PF, max_dd%, expectancy from closed picks."""
    if not closed_picks:
        return {"n": 0, "wr_pct": 0.0, "pf": 0.0, "max_dd_pct": 0.0, "expectancy": 0.0}
    pnls = [float(p.get("pnl_pct", 0.0)) for p in closed_picks]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x <= 0]
    wr_pct = len(wins) / len(pnls) * 100.0
    loss_sum = abs(sum(losses))
    win_sum = sum(wins)
    pf = (win_sum / loss_sum) if loss_sum > 0 else (float("inf") if win_sum > 0 else 0.0)
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for x in pnls:
        cum += x
        peak = max(peak, cum)
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd
    expectancy = sum(pnls) / len(pnls)
    return {
        "n": len(pnls),
        "wr_pct": round(wr_pct, 2),
        "pf": round(pf, 3) if math.isfinite(pf) else 999.0,
        "max_dd_pct": round(max_dd, 2),
        "expectancy": round(expectancy, 4),
    }


def _darwin_v2(stats: dict) -> float:
    """Local Darwin v2: WR*0.35 + log(PF)*0.30 + Sharpe*0.20 + ConsecWins*0.15.

    Sharpe and ConsecWins approximated as 0 for the minimal impl; refine when
    integrating with alpha_engine.darwin_score_v2_calculator.
    """
    wr = stats.get("wr_pct", 0.0) / 100.0
    pf = stats.get("pf", 0.0)
    log_pf = math.log(pf) if pf > 0 else 0.0
    return round(wr * 0.35 + log_pf * 0.30, 4)


def tier1_stats(
    picks: list[dict],
    min_wr: float = 55.0,
    min_pf: float = 1.5,
    max_dd: float = 20.0,
    min_darwin_v2: float = 0.3,
) -> CriterionResult:
    closed = [p for p in picks if p.get("status") == "closed"]
    stats = _compute_stats(closed)
    darwin = _darwin_v2(stats)
    stats["darwin_v2"] = darwin
    fails = []
    if stats["wr_pct"] < min_wr:
        fails.append(f"WR {stats['wr_pct']:.1f}% < {min_wr}")
    if stats["pf"] < min_pf:
        fails.append(f"PF {stats['pf']:.2f} < {min_pf}")
    if stats["max_dd_pct"] > max_dd:
        fails.append(f"DD {stats['max_dd_pct']:.1f}% > {max_dd}")
    if darwin < min_darwin_v2:
        fails.append(f"Darwin v2 {darwin:.3f} < {min_darwin_v2}")
    if fails:
        return CriterionResult(passed=False, reason="; ".join(fails), detail=stats)
    return CriterionResult(passed=True, reason="all tier-1 stats pass", detail=stats)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ai4trade_gate_criteria.py -v`

Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add alpha_engine/ai4trade_gate_criteria.py tests/test_ai4trade_gate_criteria.py
git commit -m "feat(ai4trade): criterion 5 — tier-1 stats gate"
```

---

## Task 7: Criterion 6 — correlation floor (r < 0.7 vs top-5)

**Files:**
- Modify: `alpha_engine/ai4trade_gate_criteria.py`
- Modify: `tests/test_ai4trade_gate_criteria.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_ai4trade_gate_criteria.py`:

```python
def test_correlation_floor_passes_uncorrelated():
    picks = make_agent_picks(agent_id=1, n=30, wr_pct=60, avg_win=1.5, avg_loss=-1.0)
    top5_daily_returns = {
        "strat_a": [0.1, -0.2, 0.3, -0.1, 0.2] * 6,
        "strat_b": [-0.1, 0.2, -0.3, 0.1, -0.2] * 6,
    }
    result = C.correlation_floor(picks, top5_daily_returns, max_r=0.7)
    assert result.passed is True

def test_correlation_floor_rejects_duplicate():
    picks = make_agent_picks(agent_id=1, n=30, wr_pct=60, avg_win=1.5, avg_loss=-1.0)
    # Craft returns identical to the agent's closed-pick daily aggregate so r≈1.0
    agent_daily = C._daily_returns(picks)
    top5 = {"clone": list(agent_daily.values())}
    result = C.correlation_floor(picks, top5, max_r=0.7)
    assert result.passed is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ai4trade_gate_criteria.py -v -k correlation_floor`

Expected: 2 errors.

- [ ] **Step 3: Add the implementation**

Append to `alpha_engine/ai4trade_gate_criteria.py`:

```python
from collections import defaultdict


def _daily_returns(picks: list[dict]) -> dict:
    """Aggregate closed-pick pnl_pct to a {date_iso: sum_pnl} dict."""
    daily: dict = defaultdict(float)
    for p in picks:
        if p.get("status") != "closed" or not p.get("closed_at"):
            continue
        day = _parse_iso(p["closed_at"]).date().isoformat()
        daily[day] += float(p.get("pnl_pct", 0.0))
    return dict(daily)


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2 or n != len(ys):
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def correlation_floor(
    picks: list[dict],
    top5_daily_returns: dict[str, list[float]],
    max_r: float = 0.7,
) -> CriterionResult:
    """Pass if |Pearson r| of agent daily returns vs every top-5 strategy < max_r.

    top5_daily_returns: mapping strategy_name -> list of daily PnL floats,
    assumed pre-aligned to the agent's date range by the caller.
    """
    agent_daily = _daily_returns(picks)
    if len(agent_daily) < 5:
        return CriterionResult(
            passed=False,
            reason=f"only {len(agent_daily)} unique trading days — need ≥5 for correlation",
            detail={"n_days": len(agent_daily)},
        )
    agent_values = list(agent_daily.values())
    worst_r = 0.0
    worst_name = None
    for name, returns in top5_daily_returns.items():
        k = min(len(agent_values), len(returns))
        if k < 5:
            continue
        r = _pearson(agent_values[-k:], returns[-k:])
        if abs(r) > abs(worst_r):
            worst_r = r
            worst_name = name
    if abs(worst_r) >= max_r:
        return CriterionResult(
            passed=False,
            reason=f"|r|={abs(worst_r):.2f} with {worst_name} ≥ {max_r}",
            detail={"worst_r": round(worst_r, 3), "worst_strategy": worst_name},
        )
    return CriterionResult(
        passed=True,
        reason=f"max |r|={abs(worst_r):.2f}",
        detail={"worst_r": round(worst_r, 3), "worst_strategy": worst_name},
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ai4trade_gate_criteria.py -v`

Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add alpha_engine/ai4trade_gate_criteria.py tests/test_ai4trade_gate_criteria.py
git commit -m "feat(ai4trade): criterion 6 — correlation floor vs top-5"
```

---

## Task 8: Criterion 7 — LONG-bias check

**Files:**
- Modify: `alpha_engine/ai4trade_gate_criteria.py`
- Modify: `tests/test_ai4trade_gate_criteria.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_ai4trade_gate_criteria.py`:

```python
def test_long_bias_flags_pure_long_agent():
    picks = make_agent_picks(agent_id=1, n=30, direction_mix="long_only")
    result = C.long_bias(picks, threshold_pct=95)
    assert result.passed is False
    assert result.detail["long_biased"] is True

def test_long_bias_passes_mixed_agent():
    picks = make_agent_picks(agent_id=1, n=30, direction_mix="mixed")
    result = C.long_bias(picks, threshold_pct=95)
    assert result.passed is True
    assert result.detail["long_biased"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ai4trade_gate_criteria.py -v -k long_bias`

Expected: 2 errors.

- [ ] **Step 3: Add the implementation**

Append to `alpha_engine/ai4trade_gate_criteria.py`:

```python
def long_bias(picks: list[dict], threshold_pct: float = 95.0) -> CriterionResult:
    """Flag if ≥threshold_pct of closed picks are LONG.

    A flagged agent is NOT auto-failed; it's marked long_biased and the
    orchestrator blocks promotion unless a paired SHORT-source agent exists.
    This criterion returns passed=False when flagged so the orchestrator
    stalls promotion until the pair condition is satisfied.
    """
    closed = [p for p in picks if p.get("status") == "closed"]
    if not closed:
        return CriterionResult(passed=False, reason="no closed picks",
                               detail={"long_biased": False, "long_pct": 0.0})
    long_count = sum(1 for p in closed if p.get("direction", "").upper() == "LONG")
    long_pct = long_count / len(closed) * 100
    long_biased = long_pct >= threshold_pct
    if long_biased:
        return CriterionResult(
            passed=False,
            reason=f"{long_pct:.1f}% LONG — flagged long_biased, needs SHORT pair",
            detail={"long_biased": True, "long_pct": round(long_pct, 2)},
        )
    return CriterionResult(
        passed=True,
        reason=f"{long_pct:.1f}% LONG",
        detail={"long_biased": False, "long_pct": round(long_pct, 2)},
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ai4trade_gate_criteria.py -v`

Expected: 16 passed.

- [ ] **Step 5: Commit**

```bash
git add alpha_engine/ai4trade_gate_criteria.py tests/test_ai4trade_gate_criteria.py
git commit -m "feat(ai4trade): criterion 7 — LONG-bias check"
```

---

## Task 9: Report builder (per-agent record + JSON aggregate)

**Files:**
- Create: `alpha_engine/ai4trade_promotion_gate.py`
- Create: `tests/test_ai4trade_promotion_gate.py`

- [ ] **Step 1: Write the failing integration test**

Create `tests/test_ai4trade_promotion_gate.py`:

```python
"""Integration tests for alpha_engine.ai4trade_promotion_gate."""
from tests.fixtures.ai4trade_picks import make_agent_picks
from alpha_engine import ai4trade_promotion_gate as G


def fake_regime_fn(_from, _to):
    return {"red_hours_total": 96.0, "longest_red_run_hours": 72.0}


def test_group_by_agent_builds_agent_records():
    picks = (
        make_agent_picks(agent_id=1, n=30, display_name="alpha")
        + make_agent_picks(agent_id=2, n=15, display_name="beta")
    )
    agents = G._group_by_agent(picks)
    assert len(agents) == 2
    assert agents[1]["display_name"] == "alpha"
    assert len(agents[1]["closed_picks"]) == 30
    assert len(agents[2]["closed_picks"]) == 15


def test_build_report_record_contains_all_gates():
    picks = make_agent_picks(agent_id=1, n=50, wr_pct=58, avg_win=2.0, avg_loss=-1.2,
                             weeks_ago_first_tracked=9, direction_mix="mixed")
    agent = G._group_by_agent(picks)[1]
    record = G._build_agent_record(
        agent,
        regime_fn=fake_regime_fn,
        top5_daily_returns={},
    )
    assert set(record["gates"].keys()) == {
        "originator_only", "forward_sample", "time_under_test",
        "regime_coverage", "tier1_stats", "correlation_floor", "long_bias_check",
    }
    assert record["agent_id"] == 1
    assert "promotion_status" in record
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ai4trade_promotion_gate.py -v`

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Create the orchestrator module**

Create `alpha_engine/ai4trade_promotion_gate.py`:

```python
"""ai4trade promotion gate — decides which ai4trade.ai originator agents
earn a real .py file in baby_strategies/.

Reads picks tagged source_system="ai4trade" from the normal pick pipeline.
Writes audit_dashboard/data/ai4trade_gate_report.json every run.
Writes baby_strategies/pending/ai4trade_agent_<id>.py on promotion.

Never writes directly to baby_strategies/ — human move activates.

See docs/superpowers/specs/2026-04-14-ai4trade-promotion-gate-design.md.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from alpha_engine import ai4trade_gate_criteria as C

# Default thresholds — mirror the design doc.
MIN_N_CLOSED = 30
MIN_WEEKS_UNDER_TEST = 8.0
MIN_RED_REGIME_HOURS = 48.0
MIN_WR_PCT = 55.0
MIN_PF = 1.5
MAX_DD_PCT = 20.0
MIN_DARWIN_V2 = 0.3
MAX_CORRELATION = 0.7
LONG_BIAS_THRESHOLD_PCT = 95.0


def _group_by_agent(picks: list[dict]) -> dict[int, dict]:
    """Group ai4trade picks by agent_id into Agent records."""
    agents: dict[int, dict] = {}
    for p in picks:
        if p.get("source_system") != "ai4trade":
            continue
        aid = p.get("agent_id")
        if aid is None:
            continue
        a = agents.setdefault(aid, {
            "agent_id": aid,
            "display_name": p.get("agent_display_name", f"agent_{aid}"),
            "picks": [],
            "closed_picks": [],
        })
        a["picks"].append(p)
        if p.get("status") == "closed":
            a["closed_picks"].append(p)
    return agents


def _build_agent_record(
    agent: dict,
    regime_fn: Callable,
    top5_daily_returns: dict[str, list[float]],
) -> dict:
    picks = agent["picks"]
    gates = {
        "originator_only": C.originator_only(picks),
        "forward_sample": C.forward_sample(picks, min_n=MIN_N_CLOSED),
        "time_under_test": C.time_under_test(picks, min_weeks=MIN_WEEKS_UNDER_TEST),
        "regime_coverage": C.regime_coverage(
            picks, min_red_hours=MIN_RED_REGIME_HOURS, regime_fn=regime_fn),
        "tier1_stats": C.tier1_stats(
            picks, min_wr=MIN_WR_PCT, min_pf=MIN_PF,
            max_dd=MAX_DD_PCT, min_darwin_v2=MIN_DARWIN_V2),
        "correlation_floor": C.correlation_floor(
            picks, top5_daily_returns, max_r=MAX_CORRELATION),
        "long_bias_check": C.long_bias(picks, threshold_pct=LONG_BIAS_THRESHOLD_PCT),
    }
    all_pass = all(r.passed for r in gates.values())
    promotion_status = "promote" if all_pass else "blocked"
    return {
        "agent_id": agent["agent_id"],
        "display_name": agent["display_name"],
        "n_picks_total": len(picks),
        "n_closed": len(agent["closed_picks"]),
        "gates": {k: asdict(v) for k, v in gates.items()},
        "promotion_status": promotion_status,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ai4trade_promotion_gate.py -v`

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add alpha_engine/ai4trade_promotion_gate.py tests/test_ai4trade_promotion_gate.py
git commit -m "feat(ai4trade): orchestrator group-by-agent + report record"
```

---

## Task 10: Wrapper template renderer

**Files:**
- Modify: `alpha_engine/ai4trade_promotion_gate.py`
- Modify: `tests/test_ai4trade_promotion_gate.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ai4trade_promotion_gate.py`:

```python
def test_render_wrapper_contains_agent_id_and_scan():
    record = {
        "agent_id": 784,
        "display_name": "ClaudeTrader",
        "n_closed": 47,
        "promotion_status": "promote",
    }
    src = G._render_wrapper_source(record)
    assert "ai4trade_agent_784" in src
    assert "ClaudeTrader" in src
    assert "def scan" in src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ai4trade_promotion_gate.py::test_render_wrapper_contains_agent_id_and_scan -v`

Expected: `AttributeError: module 'alpha_engine.ai4trade_promotion_gate' has no attribute '_render_wrapper_source'`.

- [ ] **Step 3: Add the implementation**

Append to `alpha_engine/ai4trade_promotion_gate.py`:

```python
_WRAPPER_TEMPLATE = '''"""Auto-generated ai4trade wrapper — agent {agent_id} ({display_name}).

Promoted {promotion_date} after passing the ai4trade_promotion_gate.
Gate report snapshot at commit time stored in the matching .meta.json.

DO NOT EDIT. To deactivate, move this file back to baby_strategies/pending/
or add the agent to BLOCKED_SOURCE_SYSTEMS. See
docs/superpowers/specs/2026-04-14-ai4trade-promotion-gate-design.md.
"""
from alpha_engine import ai_trader_crowd_intel as _ingest

AGENT_ID = {agent_id}
DISPLAY_NAME = "{display_name}"


def scan(data: dict, context: dict | None = None) -> list[dict]:
    """Return this agent's live signals from the ai4trade ingestor."""
    try:
        raw = _ingest._fetch_signal_feed()
    except Exception:
        return []
    return [
        s for s in raw
        if s.get("agent_id") == AGENT_ID and not s.get("is_copy_trade", False)
    ]


ai4trade_agent_{agent_id}_scan = scan
'''


def _render_wrapper_source(record: dict) -> str:
    return _WRAPPER_TEMPLATE.format(
        agent_id=record["agent_id"],
        display_name=record["display_name"].replace('"', '\\"'),
        promotion_date=datetime.now(timezone.utc).date().isoformat(),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ai4trade_promotion_gate.py -v`

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add alpha_engine/ai4trade_promotion_gate.py tests/test_ai4trade_promotion_gate.py
git commit -m "feat(ai4trade): wrapper source renderer"
```

---

## Task 11: Main orchestrator `run_gate()` + filesystem side effects

**Files:**
- Modify: `alpha_engine/ai4trade_promotion_gate.py`
- Modify: `tests/test_ai4trade_promotion_gate.py`

- [ ] **Step 1: Write the failing integration test**

Append to `tests/test_ai4trade_promotion_gate.py`:

```python
import json
from pathlib import Path


def test_run_gate_writes_report_and_pending_wrapper(tmp_path):
    strong = make_agent_picks(agent_id=784, n=50, wr_pct=58, avg_win=2.0, avg_loss=-1.2,
                              weeks_ago_first_tracked=9, direction_mix="mixed",
                              display_name="ClaudeTrader")
    weak = make_agent_picks(agent_id=99, n=10, wr_pct=45, avg_win=1.0, avg_loss=-1.5,
                            weeks_ago_first_tracked=2, direction_mix="mixed",
                            display_name="noob")
    report_path = tmp_path / "report.json"
    pending_dir = tmp_path / "pending"
    pending_dir.mkdir()

    result = G.run_gate(
        picks=strong + weak,
        report_path=report_path,
        pending_dir=pending_dir,
        regime_fn=fake_regime_fn,
        top5_daily_returns={},
    )

    assert report_path.exists()
    data = json.loads(report_path.read_text())
    assert len(data["agents"]) == 2
    promoted = [a for a in data["agents"] if a["promotion_status"] == "promote"]
    assert len(promoted) == 1
    assert promoted[0]["agent_id"] == 784
    assert (pending_dir / "ai4trade_agent_784.py").exists()
    assert (pending_dir / "ai4trade_agent_784.meta.json").exists()
    assert not (pending_dir / "ai4trade_agent_99.py").exists()
    assert result["promoted"] == [784]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ai4trade_promotion_gate.py::test_run_gate_writes_report_and_pending_wrapper -v`

Expected: `AttributeError: module '...' has no attribute 'run_gate'`.

- [ ] **Step 3: Add the implementation**

Append to `alpha_engine/ai4trade_promotion_gate.py`:

```python
def run_gate(
    picks: list[dict],
    report_path: Path,
    pending_dir: Path,
    regime_fn: Callable,
    top5_daily_returns: dict[str, list[float]],
    dry_run: bool = False,
) -> dict:
    """Run the promotion gate end-to-end.

    Side effects (skipped when dry_run=True):
      - Writes report_path (the JSON artifact).
      - For each promoted agent, writes pending_dir/ai4trade_agent_<id>.py
        and pending_dir/ai4trade_agent_<id>.meta.json.

    Returns a summary dict: {"n_tracked": int, "promoted": [agent_id, ...]}.
    """
    agents = _group_by_agent(picks)
    records = [
        _build_agent_record(agent, regime_fn=regime_fn, top5_daily_returns=top5_daily_returns)
        for agent in agents.values()
    ]
    promoted_ids: list[int] = []
    for rec in records:
        if rec["promotion_status"] != "promote":
            continue
        promoted_ids.append(rec["agent_id"])
        if dry_run:
            continue
        source = _render_wrapper_source(rec)
        py_path = pending_dir / f"ai4trade_agent_{rec['agent_id']}.py"
        meta_path = pending_dir / f"ai4trade_agent_{rec['agent_id']}.meta.json"
        py_path.write_text(source, encoding="utf-8")
        meta_path.write_text(
            json.dumps({
                "agent_id": rec["agent_id"],
                "display_name": rec["display_name"],
                "promoted_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "gate_snapshot": rec,
            }, indent=2),
            encoding="utf-8",
        )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "n_tracked": len(records),
        "agents": records,
    }
    if not dry_run:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {"n_tracked": len(records), "promoted": promoted_ids}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ai4trade_promotion_gate.py -v`

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add alpha_engine/ai4trade_promotion_gate.py tests/test_ai4trade_promotion_gate.py
git commit -m "feat(ai4trade): run_gate orchestration + pending wrapper writes"
```

---

## Task 12: Dry-run CLI entry

**Files:**
- Modify: `alpha_engine/ai4trade_promotion_gate.py`
- Modify: `tests/test_ai4trade_promotion_gate.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ai4trade_promotion_gate.py`:

```python
def test_run_gate_dry_run_skips_file_writes(tmp_path):
    strong = make_agent_picks(agent_id=784, n=50, wr_pct=58, avg_win=2.0, avg_loss=-1.2,
                              weeks_ago_first_tracked=9, direction_mix="mixed",
                              display_name="ClaudeTrader")
    report_path = tmp_path / "report.json"
    pending_dir = tmp_path / "pending"
    pending_dir.mkdir()

    result = G.run_gate(
        picks=strong,
        report_path=report_path,
        pending_dir=pending_dir,
        regime_fn=fake_regime_fn,
        top5_daily_returns={},
        dry_run=True,
    )

    assert result["promoted"] == [784]
    assert not report_path.exists()
    assert not (pending_dir / "ai4trade_agent_784.py").exists()
```

- [ ] **Step 2: Run test to verify it passes**

Run: `python -m pytest tests/test_ai4trade_promotion_gate.py -v`

Expected: 5 passed (the `dry_run` branch was already implemented in Task 11).

- [ ] **Step 3: Add `__main__` CLI**

Append to `alpha_engine/ai4trade_promotion_gate.py`:

```python
def _default_regime_fn(start: datetime, end: datetime) -> dict:
    """Wrap alpha_engine.momentum_catcher.fetch_btc_4h_regime into a
    (longest_red_run_hours, red_hours_total) stats dict.

    The wrapped fetcher returns a single regime snapshot; this default
    conservatively returns longest_red_run_hours based on whether BTC is
    currently in a red regime. Real implementation should read a bar history.
    """
    try:
        from alpha_engine.momentum_catcher import fetch_btc_4h_regime
    except Exception:
        return {"red_hours_total": 0.0, "longest_red_run_hours": 0.0}
    try:
        regime, _change = fetch_btc_4h_regime()
    except Exception:
        return {"red_hours_total": 0.0, "longest_red_run_hours": 0.0}
    hours = (end - start).total_seconds() / 3600
    red = hours if str(regime).lower() in {"bear", "red", "down"} else 0.0
    return {"red_hours_total": red, "longest_red_run_hours": red}


def _load_picks_from_dashboard_data() -> list[dict]:
    """Load closed picks tagged source_system='ai4trade' from the dashboard export."""
    path = Path("audit_dashboard/data/dashboard_data.json")
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    picks = raw.get("active_picks", []) + raw.get("closed_picks", [])
    return [p for p in picks if p.get("source_system") == "ai4trade"]


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="ai4trade promotion gate runner")
    ap.add_argument("--dry-run", action="store_true",
                    help="Skip filesystem writes; only print the summary.")
    ap.add_argument("--report-path", default="audit_dashboard/data/ai4trade_gate_report.json")
    ap.add_argument("--pending-dir", default="baby_strategies/pending")
    args = ap.parse_args()

    picks = _load_picks_from_dashboard_data()
    result = run_gate(
        picks=picks,
        report_path=Path(args.report_path),
        pending_dir=Path(args.pending_dir),
        regime_fn=_default_regime_fn,
        top5_daily_returns={},
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run compile check**

Run: `python -m py_compile alpha_engine/ai4trade_promotion_gate.py && python -m alpha_engine.ai4trade_promotion_gate --dry-run`

Expected: valid JSON summary, `"n_tracked": 0` if no ai4trade picks exist yet.

- [ ] **Step 5: Commit**

```bash
git add alpha_engine/ai4trade_promotion_gate.py tests/test_ai4trade_promotion_gate.py
git commit -m "feat(ai4trade): dry-run CLI entry + default regime fn + dashboard loader"
```

---

## Task 13: Demotion pass (weekly sweep for previously-promoted wrappers)

**Files:**
- Modify: `alpha_engine/ai4trade_promotion_gate.py`
- Modify: `tests/test_ai4trade_promotion_gate.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ai4trade_promotion_gate.py`:

```python
def test_demotion_pass_marks_two_consecutive_failures(tmp_path):
    agent_id = 555
    wrapper = tmp_path / f"ai4trade_agent_{agent_id}.py"
    meta = tmp_path / f"ai4trade_agent_{agent_id}.meta.json"
    wrapper.write_text("# stub")
    meta.write_text(json.dumps({
        "agent_id": agent_id,
        "display_name": "fading",
        "promoted_at": "2026-02-01T00:00:00Z",
        "consecutive_failures": 1,
    }))

    weak = make_agent_picks(agent_id=agent_id, n=50, wr_pct=40, avg_win=1.0, avg_loss=-2.0,
                            weeks_ago_first_tracked=10, direction_mix="mixed",
                            display_name="fading")
    record = G._build_agent_record(
        G._group_by_agent(weak)[agent_id],
        regime_fn=fake_regime_fn,
        top5_daily_returns={},
    )
    result = G._apply_demotion(record, meta_path=meta)
    assert result["blocked"] is True
    assert json.loads(meta.read_text())["consecutive_failures"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ai4trade_promotion_gate.py::test_demotion_pass_marks_two_consecutive_failures -v`

Expected: `AttributeError: module '...' has no attribute '_apply_demotion'`.

- [ ] **Step 3: Add the implementation**

Append to `alpha_engine/ai4trade_promotion_gate.py`:

```python
def _apply_demotion(record: dict, meta_path: Path) -> dict:
    """Mutation-before-kill demotion: increment consecutive_failures in the
    wrapper meta file. On the 2nd consecutive fail, mark blocked=True.

    Never deletes files (per feedback_no_abort_ideas.md). Caller decides
    what to do with blocked=True; this function only updates the meta.
    """
    if record["promotion_status"] == "promote":
        meta = json.loads(meta_path.read_text())
        meta["consecutive_failures"] = 0
        meta_path.write_text(json.dumps(meta, indent=2))
        return {"blocked": False, "consecutive_failures": 0}
    meta = json.loads(meta_path.read_text())
    meta["consecutive_failures"] = int(meta.get("consecutive_failures", 0)) + 1
    meta["last_failure_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    meta["last_failure_record"] = record
    blocked = meta["consecutive_failures"] >= 2
    meta["blocked"] = blocked
    meta_path.write_text(json.dumps(meta, indent=2))
    return {"blocked": blocked, "consecutive_failures": meta["consecutive_failures"]}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ai4trade_promotion_gate.py -v`

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add alpha_engine/ai4trade_promotion_gate.py tests/test_ai4trade_promotion_gate.py
git commit -m "feat(ai4trade): demotion pass — 2-consecutive-fail block"
```

---

## Task 14: Full test suite green + final compile check

**Files:**
- No source changes expected.

- [ ] **Step 1: Run the full gate test suite**

Run: `python -m pytest tests/test_ai4trade_gate_criteria.py tests/test_ai4trade_promotion_gate.py -v`

Expected: all 22 tests pass (16 criterion + 6 orchestrator).

- [ ] **Step 2: py_compile scanner-path files to confirm no collateral damage**

Run: `python -m py_compile alpha_engine/scanner.py alpha_engine/config.py alpha_engine/antigravity_strategies.py alpha_engine/ai4trade_promotion_gate.py alpha_engine/ai4trade_gate_criteria.py`

Expected: exit code 0, no output.

- [ ] **Step 3: Dry-run the CLI against the live dashboard export**

Run: `python -m alpha_engine.ai4trade_promotion_gate --dry-run`

Expected: valid JSON `{"n_tracked": N, "promoted": [...]}`. If no ai4trade picks exist in `audit_dashboard/data/dashboard_data.json` yet, `n_tracked` will be 0 — that is correct behavior.

- [ ] **Step 4: Confirm no uncommitted diffs against scanner.py / config.py / antigravity_strategies.py**

Run: `git diff --stat alpha_engine/scanner.py alpha_engine/config.py alpha_engine/antigravity_strategies.py`

Expected: empty output.

- [ ] **Step 5: Commit any loose artifacts (should be nothing new)**

```bash
git status
```

If clean: done. If there are stray changes, review and commit separately.

---

## Post-implementation checklist

Before declaring this feature shipped, the engineer should:

1. Verify `audit_dashboard/data/ai4trade_gate_report.json` is written on the next scheduled run.
2. Confirm no file has been written to `baby_strategies/` itself — only `baby_strategies/pending/`.
3. Post a Redis bus broadcast on `bus:broadcast:log` summarizing the first gate run.
4. After the first real gate run, skim the report for any agent with `promotion_status == "promote"` and verify by hand before the 8-week clock even allows promotion. (There should be zero promotions until at least 8 weeks after the ingestor started tagging picks.)
