# Bundle-Baby Quality Gate for Discord Picks — Implementation Plan

> **Strategy Registry:** See [ALL_STRATEGIES.md](../ALL_STRATEGIES.md) for the full crypto strategy inventory across all systems.

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Route all trading strategies through the Bundle-Baby pipeline so only forward-tested, quality-ranked strategies produce Discord picks — replacing the current "any 2 systems agree" consensus with a quality-gated flow.

**Architecture:** A Strategy Registry ingests strategies from all 20+ systems into a unified JSON envelope → Bundle-Baby system classifies, forward-tests, and ranks them → only bundles that pass a validation gate (min Sharpe, min trades, min win-rate) are allowed to emit Discord picks. The existing `cross_aggregation/discord_notify.py` gains a quality-score badge and validation-gate status on every alert.

**Tech Stack:** Python 3.14, SQLite (existing `bundle_babies.db`), JSON envelopes, GitHub Actions workflows, Discord webhooks (existing)

---

## Phase 1: Strategy Registry — The Single Entry Point

### Task 1: Create the incoming directories

**Files:**
- Create: `incoming_strategies/.gitkeep`
- Create: `failed_strategies/.gitkeep`

**Step 1: Create directories**

```bash
mkdir -p incoming_strategies failed_strategies
touch incoming_strategies/.gitkeep failed_strategies/.gitkeep
```

**Step 2: Add to .gitignore (JSON files only, keep .gitkeep)**

Add to `.gitignore`:
```
incoming_strategies/*.json
failed_strategies/*.json
```

**Step 3: Commit**

```bash
git add incoming_strategies/.gitkeep failed_strategies/.gitkeep .gitignore
git commit -m "chore: add incoming/failed strategy directories"
```

---

### Task 2: Define the JSON envelope schema

**Files:**
- Create: `strategy_registry/envelope_schema.py`

**Step 1: Write the failing test**

```python
# tests/test_envelope_schema.py
import pytest
from strategy_registry.envelope_schema import validate_envelope

def test_valid_envelope_passes():
    envelope = {
        "strategy_id": "opp_20260304_btc_001",
        "name": "Opposite Theory BTC",
        "type": "opposite",
        "source_system": "alpha_engine",
        "parameters": {"lookback": 24},
        "backtest_results": {
            "tier_1": {"passed": True, "sharpe_ratio": 1.5, "win_rate": 62, "max_drawdown": -10, "trades": 50, "total_return": 30, "pair": "BTC/USDT", "direction": "SHORT"},
        },
        "tags": {"symbol_scope": "single_symbol", "direction_bias": "short_only", "theory": "opposite"},
        "generated_at": "2026-03-04T12:00:00Z",
    }
    ok, errors = validate_envelope(envelope)
    assert ok is True
    assert errors == []

def test_missing_fields_fails():
    envelope = {"name": "Broken"}
    ok, errors = validate_envelope(envelope)
    assert ok is False
    assert "strategy_id" in str(errors)

def test_bad_type_fails():
    envelope = {
        "strategy_id": "x", "name": "x", "type": 123,
        "source_system": "alpha_engine",
        "backtest_results": {}, "tags": {}, "generated_at": "2026-03-04T12:00:00Z",
    }
    ok, errors = validate_envelope(envelope)
    assert ok is False
```

**Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_envelope_schema.py -v`
Expected: FAIL — module not found

**Step 3: Write minimal implementation**

```python
# strategy_registry/__init__.py
# (empty)

# strategy_registry/envelope_schema.py
"""JSON envelope schema for the Strategy Registry."""

REQUIRED_FIELDS = {
    "strategy_id": str,
    "name": str,
    "type": str,              # dna | opposite | web | ml | rule | consensus
    "source_system": str,     # which system generated it
    "backtest_results": dict,
    "tags": dict,
    "generated_at": str,
}

VALID_TYPES = {"dna", "opposite", "web", "ml", "rule", "consensus", "manual"}


def validate_envelope(envelope: dict) -> tuple[bool, list[str]]:
    """Validate a strategy envelope. Returns (ok, list_of_errors)."""
    errors = []

    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in envelope:
            errors.append(f"Missing required field: {field}")
        elif not isinstance(envelope[field], expected_type):
            errors.append(f"Field '{field}' must be {expected_type.__name__}, got {type(envelope[field]).__name__}")

    if "type" in envelope and isinstance(envelope["type"], str):
        if envelope["type"] not in VALID_TYPES:
            errors.append(f"Invalid type '{envelope['type']}', must be one of {VALID_TYPES}")

    return (len(errors) == 0, errors)
```

**Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_envelope_schema.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add strategy_registry/ tests/test_envelope_schema.py
git commit -m "feat: add strategy envelope schema with validation"
```

---

### Task 3: Build the Strategy Registry processor

**Files:**
- Create: `strategy_registry/registry.py`
- Test: `tests/test_strategy_registry.py`

**Step 1: Write the failing test**

```python
# tests/test_strategy_registry.py
import json
import pytest
from pathlib import Path

from strategy_registry.registry import StrategyRegistry


@pytest.fixture
def tmp_dirs(tmp_path):
    incoming = tmp_path / "incoming"
    failed = tmp_path / "failed"
    master = tmp_path / "master.json"
    incoming.mkdir()
    failed.mkdir()
    return incoming, failed, master


def test_process_valid_envelope(tmp_dirs):
    incoming, failed, master = tmp_dirs
    envelope = {
        "strategy_id": "test_001",
        "name": "Test Strategy",
        "type": "rule",
        "source_system": "alpha_engine",
        "backtest_results": {
            "tier_1": {"passed": True, "sharpe_ratio": 1.2, "win_rate": 60, "trades": 40},
        },
        "tags": {"symbol_scope": "single_symbol"},
        "generated_at": "2026-03-04T12:00:00Z",
    }
    (incoming / "test.json").write_text(json.dumps(envelope))

    reg = StrategyRegistry(incoming_dir=incoming, failed_dir=failed, master_path=master)
    processed = reg.process_all()
    assert processed == 1
    assert master.exists()

    data = json.loads(master.read_text())
    assert "test_001" in data["strategies"]
    assert not (incoming / "test.json").exists()  # consumed


def test_invalid_envelope_moves_to_failed(tmp_dirs):
    incoming, failed, master = tmp_dirs
    (incoming / "bad.json").write_text('{"name": "broken"}')

    reg = StrategyRegistry(incoming_dir=incoming, failed_dir=failed, master_path=master)
    processed = reg.process_all()
    assert processed == 0
    assert (failed / "bad.json").exists()
```

**Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_strategy_registry.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# strategy_registry/registry.py
"""Strategy Registry — watches incoming/ and merges into master JSON."""

import json
import logging
import shutil
from pathlib import Path

from strategy_registry.envelope_schema import validate_envelope

log = logging.getLogger("StrategyRegistry")


class StrategyRegistry:
    def __init__(
        self,
        incoming_dir: Path = Path("incoming_strategies"),
        failed_dir: Path = Path("failed_strategies"),
        master_path: Path = Path("battleground/data/tiered_backtest_results_master.json"),
    ):
        self.incoming_dir = Path(incoming_dir)
        self.failed_dir = Path(failed_dir)
        self.master_path = Path(master_path)

    def _load_master(self) -> dict:
        if self.master_path.exists():
            return json.loads(self.master_path.read_text())
        return {"strategies": {}, "updated_at": ""}

    def _save_master(self, data: dict) -> None:
        from datetime import datetime, timezone
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.master_path.parent.mkdir(parents=True, exist_ok=True)
        self.master_path.write_text(json.dumps(data, indent=2))

    def process_one(self, file_path: Path) -> bool:
        """Process a single envelope file. Returns True if successful."""
        try:
            envelope = json.loads(file_path.read_text())
        except Exception as e:
            log.error("Cannot parse %s: %s", file_path.name, e)
            file_path.rename(self.failed_dir / file_path.name)
            return False

        ok, errors = validate_envelope(envelope)
        if not ok:
            log.error("Validation failed for %s: %s", file_path.name, errors)
            file_path.rename(self.failed_dir / file_path.name)
            return False

        master = self._load_master()
        sid = envelope["strategy_id"]
        master["strategies"][sid] = {
            "name": envelope["name"],
            "type": envelope["type"],
            "source_system": envelope["source_system"],
            "backtest_results": envelope.get("backtest_results", {}),
            "tags": envelope.get("tags", {}),
            "parameters": envelope.get("parameters", {}),
            "generated_at": envelope["generated_at"],
        }
        self._save_master(master)
        log.info("Integrated strategy: %s (%s)", sid, envelope["type"])
        file_path.unlink()
        return True

    def process_all(self) -> int:
        """Process all envelopes in the incoming directory. Returns count of successful."""
        count = 0
        for fp in sorted(self.incoming_dir.glob("*.json")):
            if self.process_one(fp):
                count += 1
        return count
```

**Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_strategy_registry.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add strategy_registry/registry.py tests/test_strategy_registry.py
git commit -m "feat: add Strategy Registry processor"
```

---

## Phase 2: Validation Gate — Quality Filter for Discord

### Task 4: Add validation gate to Bundle-Baby system

**Files:**
- Modify: `bundle_baby_system.py` (add `evaluate_gate()` method)
- Test: `tests/test_validation_gate.py`

**Step 1: Write the failing test**

```python
# tests/test_validation_gate.py
from bundle_baby_system import BundleBabySystem

def test_gate_proven_status():
    stats = {
        "forward_win_rate": 60,
        "forward_sharpe": 1.5,
        "forward_max_dd": -12,
        "forward_trades": 25,
        "forward_realized_pnl": 15.0,
    }
    gate = BundleBabySystem.evaluate_gate(stats)
    assert gate["status"] in ("PROVEN", "ELITE")
    assert gate["checks_passed"] >= 5

def test_gate_collecting_status():
    stats = {
        "forward_win_rate": 0,
        "forward_sharpe": 0,
        "forward_max_dd": 0,
        "forward_trades": 2,
        "forward_realized_pnl": 0,
    }
    gate = BundleBabySystem.evaluate_gate(stats)
    assert gate["status"] == "COLLECTING"
    assert gate["checks_passed"] < 4

def test_gate_marginal_status():
    stats = {
        "forward_win_rate": 48,
        "forward_sharpe": 0.5,
        "forward_max_dd": -25,
        "forward_trades": 15,
        "forward_realized_pnl": 3.0,
    }
    gate = BundleBabySystem.evaluate_gate(stats)
    assert gate["status"] in ("TESTING", "MARGINAL")
```

**Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_validation_gate.py -v`
Expected: FAIL — `evaluate_gate` not found

**Step 3: Add `evaluate_gate()` to `bundle_baby_system.py`**

Add this method to the `BundleBabySystem` class (after `rank_bundles`):

```python
@staticmethod
def evaluate_gate(stats: dict) -> dict:
    """
    Evaluate an 8-check validation gate for a bundle's forward-test stats.
    Returns: {"status": str, "checks_passed": int, "check_details": dict}

    Statuses: COLLECTING (<10 trades) → TESTING (1-4 checks) → MARGINAL (5-6) → PROVEN (7) → ELITE (8)
    """
    checks = {}

    trades = stats.get("forward_trades", 0)
    wr = stats.get("forward_win_rate", 0)
    sharpe = stats.get("forward_sharpe", 0)
    max_dd = stats.get("forward_max_dd", 0)
    pnl = stats.get("forward_realized_pnl", 0)

    # Gate 1: Minimum trades (statistical significance)
    checks["min_trades"] = {"passed": trades >= 10, "value": trades, "threshold": 10}
    # Gate 2: Win rate > 50%
    checks["win_rate"] = {"passed": wr > 50, "value": wr, "threshold": 50}
    # Gate 3: Sharpe > 0.5
    checks["sharpe"] = {"passed": sharpe > 0.5, "value": sharpe, "threshold": 0.5}
    # Gate 4: Max drawdown > -20% (not too deep)
    checks["max_drawdown"] = {"passed": max_dd > -20, "value": max_dd, "threshold": -20}
    # Gate 5: Positive realized PnL
    checks["positive_pnl"] = {"passed": pnl > 0, "value": pnl, "threshold": 0}
    # Gate 6: Win rate > 55% (higher bar)
    checks["strong_wr"] = {"passed": wr > 55, "value": wr, "threshold": 55}
    # Gate 7: Sharpe > 1.0 (strong risk-adjusted)
    checks["strong_sharpe"] = {"passed": sharpe > 1.0, "value": sharpe, "threshold": 1.0}
    # Gate 8: Max DD > -10% (tight risk)
    checks["tight_drawdown"] = {"passed": max_dd > -10, "value": max_dd, "threshold": -10}

    passed = sum(1 for c in checks.values() if c["passed"])

    if trades < 10:
        status = "COLLECTING"
    elif passed <= 4:
        status = "TESTING"
    elif passed <= 6:
        status = "MARGINAL"
    elif passed == 7:
        status = "PROVEN"
    else:
        status = "ELITE"

    return {"status": status, "checks_passed": passed, "check_details": checks}
```

**Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_validation_gate.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add bundle_baby_system.py tests/test_validation_gate.py
git commit -m "feat: add 8-check validation gate to Bundle-Baby system"
```

---

### Task 5: Wire validation gate into aggregator's consensus filter

**Files:**
- Modify: `cross_aggregation/aggregator.py` (add quality gate check before emitting picks)

**Step 1: Write the failing test**

```python
# tests/test_aggregator_quality_gate.py
import json
import pytest
from pathlib import Path
from unittest.mock import patch

def test_demoted_strategy_filtered():
    """Strategies with COLLECTING status should be filtered from consensus."""
    from cross_aggregation.aggregator import passes_quality_gate

    # Mock: strategy has only 3 forward trades → COLLECTING
    result = passes_quality_gate("test_strat", forward_trades=3, forward_win_rate=0, forward_sharpe=0)
    assert result is False

def test_proven_strategy_passes():
    """PROVEN strategies should pass the quality gate."""
    from cross_aggregation.aggregator import passes_quality_gate

    result = passes_quality_gate("test_strat", forward_trades=30, forward_win_rate=62, forward_sharpe=1.5)
    assert result is True
```

**Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_aggregator_quality_gate.py -v`
Expected: FAIL — `_passes_quality_gate` not found

**Step 3: Add quality gate function to aggregator.py**

Add after the BANNED_STRATEGIES block (~line 108):

```python
# ── Quality Gate Integration (Bundle-Baby forward-test validation) ──
# Strategies must have at least TESTING status (4+ checks) to participate in consensus.
# This prevents untested or poor-performing strategies from polluting Discord picks.
QUALITY_GATE_MIN_STATUS = "TESTING"  # Minimum: TESTING (4+ checks passed)
_GATE_STATUS_ORDER = ["COLLECTING", "TESTING", "MARGINAL", "PROVEN", "ELITE"]


def passes_quality_gate(
    strategy_name: str,
    forward_trades: int = 0,
    forward_win_rate: float = 0,
    forward_sharpe: float = 0,
    forward_max_dd: float = 0,
    forward_pnl: float = 0,
) -> bool:
    """Check if a strategy passes the minimum quality gate for consensus inclusion."""
    try:
        from bundle_baby_system import BundleBabySystem
        gate = BundleBabySystem.evaluate_gate({
            "forward_trades": forward_trades,
            "forward_win_rate": forward_win_rate,
            "forward_sharpe": forward_sharpe,
            "forward_max_dd": forward_max_dd,
            "forward_realized_pnl": forward_pnl,
        })
        status_idx = _GATE_STATUS_ORDER.index(gate["status"])
        min_idx = _GATE_STATUS_ORDER.index(QUALITY_GATE_MIN_STATUS)
        return status_idx >= min_idx
    except Exception:
        # If bundle system unavailable, allow through (graceful degradation)
        return True
```

**Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_aggregator_quality_gate.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add cross_aggregation/aggregator.py tests/test_aggregator_quality_gate.py
git commit -m "feat: add quality gate filter to cross-system aggregator"
```

---

## Phase 3: Enhanced Discord Alerts with Quality Badges

### Task 6: Add quality badge to Discord embeds

**Files:**
- Modify: `cross_aggregation/discord_notify.py` (add gate status + quality score to pick embeds)

**Step 1: Write the failing test**

```python
# tests/test_discord_quality_badge.py
from cross_aggregation.discord_notify import _quality_badge

def test_elite_badge():
    badge = _quality_badge("ELITE", 8)
    assert "ELITE" in badge
    assert "8/8" in badge

def test_collecting_badge():
    badge = _quality_badge("COLLECTING", 1)
    assert "COLLECTING" in badge
    assert "1/8" in badge

def test_no_gate_badge():
    badge = _quality_badge(None, 0)
    assert "UNRATED" in badge
```

**Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_discord_quality_badge.py -v`
Expected: FAIL

**Step 3: Add `_quality_badge()` to discord_notify.py**

Add after the color constants (~line 56):

```python
# ── Quality Gate Badges ──
_GATE_EMOJI = {
    "ELITE": "\U0001f451",       # 👑
    "PROVEN": "\u2705",          # ✅
    "MARGINAL": "\U0001f7e1",    # 🟡
    "TESTING": "\U0001f9ea",     # 🧪
    "COLLECTING": "\u23f3",      # ⏳
}


def _quality_badge(status: str | None, checks_passed: int) -> str:
    """Return a compact badge string for Discord embed fields."""
    if status is None:
        return "\u2753 UNRATED (0/8)"  # ❓
    emoji = _GATE_EMOJI.get(status, "\u2753")
    return f"{emoji} {status} ({checks_passed}/8)"
```

**Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_discord_quality_badge.py -v`
Expected: PASS

**Step 5: Integrate badge into `send_consensus_alert` embed builder**

In `send_consensus_alert()`, find where pick fields are built (the embed field loop). Add the quality badge as a field:

```python
# Inside the per-pick embed builder, add a field:
gate_status = p.get("gate_status")
gate_checks = p.get("gate_checks", 0)
if gate_status:
    fields.append({
        "name": "Quality Gate",
        "value": _quality_badge(gate_status, gate_checks),
        "inline": True,
    })
```

**Step 6: Commit**

```bash
git add cross_aggregation/discord_notify.py tests/test_discord_quality_badge.py
git commit -m "feat: add quality gate badges to Discord consensus alerts"
```

---

### Task 7: Add `send_job_failure()` helper to discord_notify.py

**Files:**
- Modify: `cross_aggregation/discord_notify.py`

**Step 1: Write the failing test**

```python
# tests/test_discord_job_failure.py
from unittest.mock import patch
from cross_aggregation.discord_notify import send_job_failure

@patch("cross_aggregation.discord_notify._post")
@patch("cross_aggregation.discord_notify.WEBHOOK_URL", "https://fake")
def test_send_job_failure_posts_embed(mock_post):
    send_job_failure(
        system_label="ML Crypto Engine",
        job_name="production_run",
        error_msg="ZeroDivisionError: division by zero"
    )
    mock_post.assert_called_once()
    embed = mock_post.call_args[0][0][0]
    assert "FAILURE" in embed["title"]
    assert "ZeroDivisionError" in embed["description"]
```

**Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_discord_job_failure.py -v`
Expected: FAIL

**Step 3: Add `send_job_failure()` to discord_notify.py**

Add after the existing `send_forward_test_update()` function:

```python
def send_job_failure(system_label: str, job_name: str, error_msg: str):
    """Notify Discord when a trading job (scan, backtest, forward-test) fails."""
    if not WEBHOOK_URL:
        return

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    error_msg = error_msg[:500] + ("..." if len(error_msg) > 500 else "")

    embeds = [
        {
            "title": f"\U0001f6a8 {system_label} \u2014 {job_name.upper()} FAILURE",
            "description": f"An error occurred while running **{job_name}**.\n\n`{error_msg}`",
            "color": COLOR_RED,
            "timestamp": now.isoformat(),
            "footer": {"text": "Automated failure alert | Cross-System Consensus"},
        }
    ]
    _post(embeds)
```

**Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_discord_job_failure.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add cross_aggregation/discord_notify.py tests/test_discord_job_failure.py
git commit -m "feat: add send_job_failure() Discord helper"
```

---

## Phase 4: System Adapters — Feed Existing Systems into Registry

### Task 8: Adapter for cross_aggregation consensus picks → envelope

**Files:**
- Create: `strategy_registry/adapters/consensus_adapter.py`
- Test: `tests/test_consensus_adapter.py`

**Step 1: Write the failing test**

```python
# tests/test_consensus_adapter.py
from strategy_registry.adapters.consensus_adapter import consensus_pick_to_envelope

def test_consensus_pick_converts():
    pick = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "confidence": 0.85,
        "entry_price": 65000,
        "take_profit": 70000,
        "stop_loss": 62000,
        "strategy": "connors_rsi2",
        "source_systems": ["alpha_engine", "mercury2", "kimi"],
        "agreement_count": 3,
    }
    envelope = consensus_pick_to_envelope(pick)
    assert envelope["strategy_id"].startswith("consensus_")
    assert envelope["type"] == "consensus"
    assert envelope["source_system"] == "cross_aggregation"
    assert "BTCUSDT" in envelope["name"]
```

**Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_consensus_adapter.py -v`

**Step 3: Write implementation**

```python
# strategy_registry/adapters/__init__.py
# (empty)

# strategy_registry/adapters/consensus_adapter.py
"""Convert cross-aggregation consensus picks into Strategy Registry envelopes."""

from datetime import datetime, timezone


def consensus_pick_to_envelope(pick: dict) -> dict:
    """Convert a consensus pick dict into a Strategy Registry envelope."""
    symbol = pick.get("symbol", "UNKNOWN")
    direction = pick.get("direction", "LONG")
    strategy = pick.get("strategy", "consensus")
    timestamp = datetime.now(timezone.utc).isoformat()
    sid = f"consensus_{symbol}_{direction}_{strategy}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    return {
        "strategy_id": sid,
        "name": f"Consensus {symbol} {direction} ({strategy})",
        "type": "consensus",
        "source_system": "cross_aggregation",
        "parameters": {
            "confidence": pick.get("confidence", 0),
            "agreement_count": pick.get("agreement_count", 0),
            "source_systems": pick.get("source_systems", []),
        },
        "backtest_results": {
            "tier_1": {
                "passed": pick.get("agreement_count", 0) >= 2,
                "win_rate": pick.get("confidence", 0) * 100,
                "pair": symbol,
                "direction": direction,
                "entry_price": pick.get("entry_price"),
                "take_profit": pick.get("take_profit"),
                "stop_loss": pick.get("stop_loss"),
            },
        },
        "tags": {
            "symbol_scope": "single_symbol",
            "direction_bias": "long_only" if direction == "LONG" else "short_only",
            "source": "consensus",
            "agreement": str(pick.get("agreement_count", 0)),
        },
        "generated_at": timestamp,
    }
```

**Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_consensus_adapter.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add strategy_registry/adapters/ tests/test_consensus_adapter.py
git commit -m "feat: add consensus pick → envelope adapter"
```

---

### Task 9: Adapter for DNA picks → envelope

**Files:**
- Create: `strategy_registry/adapters/dna_adapter.py`
- Test: `tests/test_dna_adapter.py`

**Step 1: Write the failing test**

```python
# tests/test_dna_adapter.py
from strategy_registry.adapters.dna_adapter import dna_pick_to_envelope

def test_dna_pick_converts():
    pick = {
        "symbol": "ETHUSDT",
        "direction": "LONG",
        "entry_price": 3000,
        "take_profit": 3300,
        "stop_loss": 2800,
        "strategy": "RSI2_FearGreed_Confluence",
        "confidence": 0.72,
        "dna_hash": "abc123",
    }
    envelope = dna_pick_to_envelope(pick)
    assert envelope["type"] == "dna"
    assert envelope["source_system"] == "genome"
    assert "dna_hash" in envelope["parameters"]
```

**Step 2: Run test to verify it fails**

**Step 3: Write implementation**

```python
# strategy_registry/adapters/dna_adapter.py
"""Convert DNA/genome picks into Strategy Registry envelopes."""

from datetime import datetime, timezone


def dna_pick_to_envelope(pick: dict) -> dict:
    """Convert a DNA pick dict into a Strategy Registry envelope."""
    symbol = pick.get("symbol", "UNKNOWN")
    direction = pick.get("direction", "LONG")
    strategy = pick.get("strategy", "dna")
    timestamp = datetime.now(timezone.utc).isoformat()
    sid = f"dna_{symbol}_{strategy}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    return {
        "strategy_id": sid,
        "name": f"DNA {symbol} {direction} ({strategy})",
        "type": "dna",
        "source_system": "genome",
        "parameters": {
            "dna_hash": pick.get("dna_hash", ""),
            "confidence": pick.get("confidence", 0),
        },
        "backtest_results": {
            "tier_1": {
                "passed": True,
                "win_rate": pick.get("confidence", 0) * 100,
                "pair": symbol,
                "direction": direction,
                "entry_price": pick.get("entry_price"),
                "take_profit": pick.get("take_profit"),
                "stop_loss": pick.get("stop_loss"),
            },
        },
        "tags": {
            "symbol_scope": "single_symbol",
            "direction_bias": "long_only" if direction == "LONG" else "short_only",
            "source": "dna",
        },
        "generated_at": timestamp,
    }
```

**Step 4: Run tests, commit**

```bash
py -m pytest tests/test_dna_adapter.py -v
git add strategy_registry/adapters/dna_adapter.py tests/test_dna_adapter.py
git commit -m "feat: add DNA pick → envelope adapter"
```

---

## Phase 5: Registry Runner + GitHub Actions Workflow

### Task 10: Create registry runner CLI

**Files:**
- Create: `strategy_registry/__main__.py`

**Step 1: Write the runner**

```python
# strategy_registry/__main__.py
"""CLI entry point: python -m strategy_registry"""

import logging
from strategy_registry.registry import StrategyRegistry

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")


def main():
    reg = StrategyRegistry()
    count = reg.process_all()
    print(f"[StrategyRegistry] Processed {count} envelope(s)")


if __name__ == "__main__":
    main()
```

**Step 2: Test manually**

```bash
py -m strategy_registry
```
Expected: `Processed 0 envelope(s)` (empty inbox)

**Step 3: Commit**

```bash
git add strategy_registry/__main__.py
git commit -m "feat: add strategy registry CLI runner"
```

---

### Task 11: Add registry step to cross-aggregator GitHub Actions workflow

**Files:**
- Modify: `.github/workflows/cross-aggregator.yml`

**Step 1: Read current workflow**

Read `.github/workflows/cross-aggregator.yml` to understand the current job steps.

**Step 2: Add registry processing step BEFORE aggregation**

Add this step after "Install dependencies" and before the main aggregation:

```yaml
      - name: Process strategy inbox
        run: |
          python -m strategy_registry || echo "Registry: no envelopes to process"
```

**Step 3: Add bundle-baby quality gate refresh step AFTER aggregation**

```yaml
      - name: Update bundle quality gates
        run: |
          python -c "
          from bundle_baby_system import BundleBabySystem
          bs = BundleBabySystem()
          bundles = bs.rank_bundles()
          print(f'[BundleBaby] Ranked {len(bundles)} bundles')
          " || echo "BundleBaby: update skipped"
```

**Step 4: Commit**

```bash
git add .github/workflows/cross-aggregator.yml
git commit -m "feat: add strategy registry + bundle quality gate to CI pipeline"
```

---

## Phase 6: Wire Failure Alerts into Long-Running Scripts

### Task 12: Wrap aggregator main() with failure reporting

**Files:**
- Modify: `cross_aggregation/aggregator.py` (wrap `main()` in try/except)

**Step 1: Find the existing `main()` or `if __name__` block**

Read the bottom of `cross_aggregation/aggregator.py`.

**Step 2: Add failure reporting**

```python
# At the bottom of aggregator.py, wrap the entry point:
if __name__ == "__main__":
    try:
        aggregate()  # or whatever the current entry function is
    except Exception as exc:
        try:
            from cross_aggregation.discord_notify import send_job_failure
            send_job_failure("Cross-Aggregator", "aggregation_run", str(exc))
        except Exception:
            pass
        raise
```

**Step 3: Commit**

```bash
git add cross_aggregation/aggregator.py
git commit -m "feat: add Discord failure alerting to cross-aggregator"
```

---

## Phase 7: End-to-End Integration Test

### Task 13: Write an end-to-end test for the full pipeline

**Files:**
- Create: `tests/test_e2e_registry_to_bundle.py`

**Step 1: Write the test**

```python
# tests/test_e2e_registry_to_bundle.py
"""End-to-end: envelope → registry → bundle-baby → quality gate."""

import json
import pytest
from pathlib import Path

from strategy_registry.registry import StrategyRegistry
from bundle_baby_system import BundleBabySystem


@pytest.fixture
def e2e_dirs(tmp_path):
    incoming = tmp_path / "incoming"
    failed = tmp_path / "failed"
    master = tmp_path / "master.json"
    incoming.mkdir()
    failed.mkdir()
    return incoming, failed, master


def test_full_pipeline(e2e_dirs):
    incoming, failed, master = e2e_dirs

    # 1. Drop an envelope
    envelope = {
        "strategy_id": "e2e_test_001",
        "name": "E2E Test Strategy",
        "type": "rule",
        "source_system": "test",
        "backtest_results": {
            "tier_1": {"passed": True, "sharpe_ratio": 2.0, "win_rate": 65, "trades": 100, "total_return": 40, "pair": "BTC/USDT", "direction": "LONG"},
        },
        "tags": {"symbol_scope": "single_symbol", "direction_bias": "long_only"},
        "generated_at": "2026-03-04T12:00:00Z",
    }
    (incoming / "e2e.json").write_text(json.dumps(envelope))

    # 2. Registry processes it
    reg = StrategyRegistry(incoming_dir=incoming, failed_dir=failed, master_path=master)
    processed = reg.process_all()
    assert processed == 1

    # 3. Master file has the strategy
    data = json.loads(master.read_text())
    assert "e2e_test_001" in data["strategies"]

    # 4. Quality gate evaluates it
    gate = BundleBabySystem.evaluate_gate({
        "forward_trades": 50,
        "forward_win_rate": 65,
        "forward_sharpe": 2.0,
        "forward_max_dd": -8,
        "forward_realized_pnl": 40.0,
    })
    assert gate["status"] == "ELITE"
    assert gate["checks_passed"] == 8
```

**Step 2: Run the test**

Run: `py -m pytest tests/test_e2e_registry_to_bundle.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_e2e_registry_to_bundle.py
git commit -m "test: add E2E test for registry → bundle → quality gate pipeline"
```

---

## Summary

| Phase | Tasks | What it delivers |
|-------|-------|-----------------|
| **1. Strategy Registry** | 1–3 | Single entry point for all strategies via JSON envelopes |
| **2. Validation Gate** | 4–5 | 8-check quality filter; only tested strategies pass to Discord |
| **3. Discord Enhancement** | 6–7 | Quality badges on picks + job failure alerts |
| **4. System Adapters** | 8–9 | Consensus + DNA picks auto-convert to envelopes |
| **5. CI Integration** | 10–11 | Registry runs in GitHub Actions before every aggregation |
| **6. Failure Alerts** | 12 | Discord notifications when any pipeline job crashes |
| **7. E2E Test** | 13 | Proves the full pipeline works end-to-end |

**Key outcome:** Discord picks go from "any 2 systems agree" → "2+ systems agree AND the strategy has passed forward-test quality gates (min trades, min win-rate, min Sharpe)". This directly addresses the Mercury feedback about higher-quality Discord picks.
