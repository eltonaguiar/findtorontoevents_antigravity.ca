# FreshPicks Fund-Grade Overhaul — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a centralized quality gate inside `send_fresh_pick()` so ALL 5 Discord senders get dedup, confidence filtering, dynamic TP/SL, Kelly sizing, expiry fields, and rate limiting — without changing any workflow YAML logic.

**Architecture:** New `cross_aggregation/freshpicks_gate.py` module with `FreshPicksGate` class containing 7 gates. `freshpicks_notify.py` imports and calls the gate at the top of `send_fresh_pick()`. State persisted to `data/freshpicks_gate_state.json` via existing git-commit steps in workflows.

**Tech Stack:** Python 3.11, `requests` (already installed), Binance public klines API (free, no key), existing `cross_aggregation/aggregator.py` for BANNED_STRATEGIES list.

---

### Task 1: Create `cross_aggregation/freshpicks_gate.py` — Core Gate Module

**Files:**
- Create: `cross_aggregation/freshpicks_gate.py`

**Context for implementer:**
- This is the single enforcement point for ALL freshpicks sends
- It must work in GitHub Actions (ubuntu-latest, Python 3.11, only `requests` pip-installed)
- State file `data/freshpicks_gate_state.json` is committed by workflows so state persists across runs
- Symbol normalization: reuse pattern from `cross_aggregation/aggregator.py:242-249` (BTC-USD → BTCUSDT)
- Banned strategies list: import from `cross_aggregation.aggregator` or duplicate the set (safer for CI)
- ATR: use Binance public API `https://api.binance.com/api/v3/klines?symbol={sym}&interval=1h&limit=15` — no API key needed

**Step 1: Write the full module**

```python
"""
FreshPicks Quality Gate — Centralized enforcement for all Discord senders.

Every call to send_fresh_pick() passes through this gate. If rejected,
the pick is silently dropped with a log line. No workflow YAML changes needed.

Gates:
  G1: Dedup/throttle (30-min cooldown per symbol+direction, bypass if price changed)
  G2: Confidence floor (>= 0.65)
  G3: Losing strategy filter (rolling WR >= 48%, banned strategies blocked)
  G4: R:R sanity (>= 1.0) — checked after G5
  G5: Dynamic TP/SL (ATR-based replacement when static ladder detected)
  G6: Enrich: Kelly sizing + expiry timestamp
  G7: Rate cap (max 8 picks per 60-min rolling window)

State: data/freshpicks_gate_state.json (persisted via git commit in workflows)
"""

import json
import hashlib
import pathlib
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple

# Repo root (works both locally and in GitHub Actions)
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Gate state file
STATE_PATH = REPO_ROOT / "data" / "freshpicks_gate_state.json"

# --- Configuration ---
DEDUP_COOLDOWN_MIN = 30        # G1: minutes before same symbol+direction can re-send
CONFIDENCE_FLOOR = 0.65        # G2: minimum confidence (0-1 scale)
STRATEGY_WR_FLOOR = 0.48       # G3: minimum rolling win rate
STRATEGY_MIN_TRADES = 5        # G3: minimum trades before WR filter applies
RR_FLOOR = 1.0                 # G4: minimum risk:reward ratio
ATR_DEFAULT_PCT = 0.02         # G5: fallback ATR as fraction of price (2%)
ATR_SL_MULT = 1.5              # G5: SL = entry ± ATR * this
ATR_TP_MULT = 2.5              # G5: TP = entry ± ATR * this
KELLY_CAP = 0.02               # G6: max Kelly fraction (2% of portfolio)
EXPIRY_MINUTES = 15            # G6: signal expiry
RATE_CAP = 8                   # G7: max picks per rolling window
RATE_WINDOW_MIN = 60           # G7: rolling window in minutes

# Strategies with 0% win rate (from cross_aggregation/aggregator.py audit 2026-03-02)
BANNED_STRATEGIES = {
    "smart_money_fvg",
    "fourier_cycle_detector",
    "exchange_netflow_reversal",
    "price_touch_recurrence",
    "halloween_effect",
    "altcoin_season_rotation",
    "momentum_mean_rev_blend",
    "cross_sectional_momentum",
}

# System closed_picks paths for rolling WR
SYSTEM_CLOSED_PATHS = {
    "mercury2":       "mercury2/data/closed_picks.json",
    "mercury_2":      "mercury2/data/closed_picks.json",
    "alpha_engine":   "alpha_engine/data/closed_picks.json",
    "claws_of_doom":  "ml_battleground/system_f_clawsofdoom/data/closed_picks.json",
    "kimi":           "KIMI_RISEOFTHECLAW/data/closed_picks.json",
    "kimi_rise_of_the_claw": "KIMI_RISEOFTHECLAW/data/closed_picks.json",
    "cross_system_consensus": "data/cross_system_closed.json",
    "claude_gainer_ml": "crypto_gainer_ml/tracker/closed_picks.json",
}


def _normalize_symbol(raw: str) -> str:
    """Normalize symbol names: BTC-USD, BTCUSD, BTCUSDT -> BTCUSDT."""
    s = raw.strip().upper().replace("-", "")
    if s.endswith("USD") and not s.endswith("USDT"):
        s += "T"
    return s


def _load_state() -> dict:
    """Load gate state from disk."""
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:
            pass
    return {"dedup": {}, "rate_window": []}


def _save_state(state: dict):
    """Persist gate state to disk."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def _fetch_atr(symbol: str, period: int = 14) -> float:
    """Fetch ATR as fraction of price from Binance hourly klines. Returns fallback on error."""
    binance_sym = _normalize_symbol(symbol)
    url = f"https://api.binance.com/api/v3/klines?symbol={binance_sym}&interval=1h&limit={period + 1}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        if len(data) < period + 1:
            return ATR_DEFAULT_PCT
        # Klines: [open_time, open, high, low, close, ...]
        trs = []
        for i in range(1, len(data)):
            high = float(data[i][2])
            low = float(data[i][3])
            prev_close = float(data[i - 1][4])
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        atr = sum(trs[-period:]) / period
        close = float(data[-1][4])
        return atr / close if close > 0 else ATR_DEFAULT_PCT
    except Exception:
        return ATR_DEFAULT_PCT


def _is_static_ladder(entry: float, tp: float, sl: float) -> bool:
    """Detect static TP/SL (round percentages like 5%, 10%, 15%)."""
    if not entry or entry <= 0:
        return False
    tp_pct = abs(tp - entry) / entry if tp else 0
    sl_pct = abs(sl - entry) / entry if sl else 0
    round_pcts = [0.05, 0.10, 0.15, 0.20]
    for rp in round_pcts:
        if abs(tp_pct - rp) < 0.001 or abs(sl_pct - rp) < 0.001:
            return True
    return False


def _compute_kelly(confidence: float, edge: float, vol: float) -> float:
    """Kelly fraction: f = (2p-1) * edge / vol^2, capped at KELLY_CAP."""
    if vol < 0.001:
        vol = 0.001
    f = (2 * confidence - 1) * edge / (vol ** 2)
    return max(min(f, KELLY_CAP), 0.0)


def _compute_rolling_wr(system_key: str, n: int = 20) -> Optional[float]:
    """Compute rolling win rate over last N closed picks. Returns 0-1 or None."""
    rel_path = SYSTEM_CLOSED_PATHS.get(system_key)
    if not rel_path:
        return None
    try:
        with open(REPO_ROOT / rel_path) as f:
            closed = json.load(f)
        if not isinstance(closed, list) or len(closed) < STRATEGY_MIN_TRADES:
            return None
        recent = closed[-n:]
        wins = sum(
            1 for c in recent
            if c.get("status", "").upper() in ("WON", "WIN", "CLOSED_TP")
            or c.get("exit_reason", "").lower() in ("take_profit", "tp_hit")
            or (isinstance(c.get("pnl_pct", c.get("net_pnl_pct")), (int, float))
                and c.get("pnl_pct", c.get("net_pnl_pct", 0)) > 0)
        )
        return wins / len(recent)
    except Exception:
        return None


class GateResult:
    """Result of running the gate on a pick."""
    __slots__ = ("allowed", "reason", "pick")

    def __init__(self, allowed: bool, reason: str, pick: Optional[Dict] = None):
        self.allowed = allowed
        self.reason = reason
        self.pick = pick  # Enriched pick (with dynamic TP/SL, sizing, expiry)


class FreshPicksGate:
    """
    Centralized quality gate for all FreshPicks Discord sends.

    Usage:
        gate = FreshPicksGate()
        result = gate.check(system="Alpha Engine", pick={...})
        if result.allowed:
            # send result.pick to Discord (enriched with sizing/expiry)
        else:
            print(f"Blocked: {result.reason}")
        gate.mark_sent(pick)  # call AFTER successful Discord send
    """

    def __init__(self):
        self._state = _load_state()

    def check(self, system: str, pick: Dict) -> GateResult:
        """Run all 7 gates. Returns GateResult with allowed/reason/enriched pick."""
        symbol = pick.get("symbol", "???")
        direction = pick.get("direction", pick.get("signal", "LONG")).upper()
        entry = float(pick.get("entry_price", pick.get("price", 0)) or 0)
        tp = float(pick.get("tp_price", pick.get("take_profit", pick.get("target_price", 0))) or 0)
        sl = float(pick.get("sl_price", pick.get("stop_loss", pick.get("stop_price", 0))) or 0)
        confidence = float(pick.get("confidence", 0) or 0)
        strategy = pick.get("strategy_name", pick.get("strategy", pick.get("algorithm", "")))

        # Normalize confidence: handle 0-100 scale
        if confidence > 1:
            confidence = confidence / 100.0

        norm_sym = _normalize_symbol(symbol)
        dedup_key = f"{norm_sym}__{direction}"
        sys_key = system.lower().replace(" ", "_").replace("-", "_")

        # --- G2: Confidence floor ---
        if confidence < CONFIDENCE_FLOOR:
            return GateResult(False, f"G2: confidence {confidence:.2f} < {CONFIDENCE_FLOOR}")

        # --- G3: Losing strategy filter ---
        if strategy and strategy.lower() in BANNED_STRATEGIES:
            return GateResult(False, f"G3: banned strategy '{strategy}'")
        wr = _compute_rolling_wr(sys_key)
        if wr is not None and wr < STRATEGY_WR_FLOOR:
            return GateResult(False, f"G3: system '{sys_key}' rolling WR {wr:.0%} < {STRATEGY_WR_FLOOR:.0%}")

        # --- G5: Dynamic TP/SL (before G1 dedup so fingerprint uses new levels) ---
        if entry > 0:
            needs_dynamic = (tp <= 0 or sl <= 0 or _is_static_ladder(entry, tp, sl))
            # Also check if levels are identical to last send (stale)
            prev = self._state.get("dedup", {}).get(dedup_key, {})
            if not needs_dynamic and prev:
                if prev.get("entry") == entry and prev.get("tp") == tp and prev.get("sl") == sl:
                    needs_dynamic = True  # Same levels as last time — recompute

            if needs_dynamic:
                atr_pct = _fetch_atr(symbol)
                sl_dist = entry * atr_pct * ATR_SL_MULT
                tp_dist = entry * atr_pct * ATR_TP_MULT
                if direction in ("LONG", "BUY"):
                    sl = entry - sl_dist
                    tp = entry + tp_dist
                else:
                    sl = entry + sl_dist
                    tp = entry - tp_dist

        # --- G4: R:R sanity (after dynamic TP/SL) ---
        if entry > 0 and tp > 0 and sl > 0:
            risk = abs(entry - sl)
            reward = abs(tp - entry)
            rr = reward / risk if risk > 0 else 0
            if rr < RR_FLOOR:
                return GateResult(False, f"G4: R:R {rr:.2f} < {RR_FLOOR}")
        else:
            rr = 0

        # --- G1: Dedup / throttle ---
        now = datetime.now(tz=timezone.utc)
        prev = self._state.get("dedup", {}).get(dedup_key, {})
        if prev:
            try:
                last_sent = datetime.fromisoformat(prev["sent_at"])
                age_min = (now - last_sent).total_seconds() / 60
                if age_min < DEDUP_COOLDOWN_MIN:
                    # Allow if price levels actually changed
                    price_changed = (
                        prev.get("entry") != entry
                        or prev.get("tp") != round(tp, 4)
                        or prev.get("sl") != round(sl, 4)
                    )
                    if not price_changed:
                        return GateResult(
                            False,
                            f"G1: dedup — {dedup_key} sent {age_min:.0f}min ago, cooldown={DEDUP_COOLDOWN_MIN}min"
                        )
            except Exception:
                pass

        # --- G7: Rate cap ---
        rate_window = self._state.get("rate_window", [])
        cutoff = (now - timedelta(minutes=RATE_WINDOW_MIN)).isoformat()
        rate_window = [ts for ts in rate_window if ts > cutoff]
        if len(rate_window) >= RATE_CAP:
            return GateResult(False, f"G7: rate cap — {len(rate_window)} picks in last {RATE_WINDOW_MIN}min (max={RATE_CAP})")

        # --- G6: Enrich — Kelly sizing + expiry ---
        size_frac = 0.0
        if entry > 0 and tp > 0 and sl > 0:
            edge = abs(tp - entry) / entry
            vol = 0.50  # Default 50% annualized crypto vol
            size_frac = _compute_kelly(confidence, edge, vol)

        expires_at = now + timedelta(minutes=EXPIRY_MINUTES)

        # Build enriched pick (copy to avoid mutating caller's dict)
        enriched = dict(pick)
        enriched["entry_price"] = entry
        enriched["tp_price"] = round(tp, 4) if tp else 0
        enriched["sl_price"] = round(sl, 4) if sl else 0
        enriched["confidence"] = confidence
        enriched["direction"] = direction
        enriched["size_frac"] = round(size_frac, 4)
        enriched["expires_at"] = expires_at.isoformat()
        enriched["rr"] = round(rr, 2)

        return GateResult(True, "all gates passed", enriched)

    def mark_sent(self, pick: Dict):
        """Call after successful Discord send to update dedup state."""
        symbol = pick.get("symbol", "???")
        direction = pick.get("direction", "LONG").upper()
        norm_sym = _normalize_symbol(symbol)
        dedup_key = f"{norm_sym}__{direction}"
        now = datetime.now(tz=timezone.utc)

        # Update dedup
        dedup = self._state.setdefault("dedup", {})
        dedup[dedup_key] = {
            "sent_at": now.isoformat(),
            "entry": pick.get("entry_price", 0),
            "tp": pick.get("tp_price", 0),
            "sl": pick.get("sl_price", 0),
            "confidence": pick.get("confidence", 0),
            "system": pick.get("_system", "unknown"),
        }

        # Update rate window
        rate_window = self._state.setdefault("rate_window", [])
        rate_window.append(now.isoformat())
        # Prune old entries
        cutoff_rate = (now - timedelta(minutes=RATE_WINDOW_MIN)).isoformat()
        self._state["rate_window"] = [ts for ts in rate_window if ts > cutoff_rate]
        cutoff_dedup = (now - timedelta(hours=24)).isoformat()
        self._state["dedup"] = {
            k: v for k, v in dedup.items()
            if v.get("sent_at", "") > cutoff_dedup
        }

        _save_state(self._state)
```

**Step 2: Verify file runs without import errors**

Run: `cd e:/findtorontoevents_antigravity.ca && py -c "from cross_aggregation.freshpicks_gate import FreshPicksGate; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add cross_aggregation/freshpicks_gate.py
git commit -m "feat: add centralized FreshPicks quality gate (7-gate pipeline)"
```

---

### Task 2: Integrate Gate into `freshpicks_notify.py`

**Files:**
- Modify: `cross_aggregation/freshpicks_notify.py`

**Context for implementer:**
- `send_fresh_pick()` is called by 5 different workflows
- The gate check goes at the TOP of the function, before embed building
- If gate rejects, return `False` (same as a failed send — callers already handle this)
- The gate returns an enriched pick with dynamic TP/SL, sizing, expiry — use those values
- Add `size_frac` and `expires_at` as new embed fields
- Keep ALL existing functionality intact (stats, trust badges, sandbox routing)

**Step 1: Add gate import and singleton at module level (after existing imports, around line 40)**

After line `_HAS_CLASSIFIER = False` (line 40), add:

```python
# Centralized quality gate — dedup, confidence, R:R, dynamic TP/SL, sizing, expiry
try:
    from cross_aggregation.freshpicks_gate import FreshPicksGate
    _gate = FreshPicksGate()
    _HAS_GATE = True
except ImportError:
    _gate = None
    _HAS_GATE = False
```

**Step 2: Add gate check at start of `send_fresh_pick()` (insert right after line 200, before `symbol = pick.get(...)`)**

Insert at line 201 (before existing `symbol = pick.get("symbol", "???")` line):

```python
    # --- Centralized quality gate (dedup, confidence, R:R, sizing, expiry) ---
    if _HAS_GATE and _gate is not None:
        gate_result = _gate.check(system, pick)
        if not gate_result.allowed:
            print(f"  [FreshPicks GATE] Blocked {pick.get('symbol', '?')} from {system}: {gate_result.reason}")
            return False
        # Use enriched pick (dynamic TP/SL, normalized confidence, etc.)
        pick = gate_result.pick
```

**Step 3: Add sizing + expiry fields to embed (insert after the "System" field, around line 238)**

After the existing `fields` list (after the `{"name": "System", ...}` entry), add these fields before the stats block:

```python
    # Add sizing field (from gate enrichment)
    size_frac = pick.get("size_frac", 0)
    if size_frac > 0:
        fields.append({"name": "Size", "value": f"{size_frac:.1%} of portfolio", "inline": True})

    # Add expiry field
    expires_at_str = pick.get("expires_at", "")
    if expires_at_str:
        try:
            exp_dt = datetime.fromisoformat(expires_at_str)
            fields.append({"name": "Expires", "value": f"<t:{int(exp_dt.timestamp())}:R>", "inline": True})
        except Exception:
            pass

    # Add R:R field
    rr = pick.get("rr", 0)
    if rr > 0:
        fields.append({"name": "R:R", "value": f"1:{rr:.2f}", "inline": True})
```

**Step 4: Add `mark_sent()` call after successful Discord send**

In the `send_fresh_pick()` function, right before the final `return _post(...)` line (around line 279), wrap it:

```python
    success = _post({"embeds": [embed]})
    if success and _HAS_GATE and _gate is not None:
        pick["_system"] = system
        _gate.mark_sent(pick)
    return success
```

Also update the sandbox send path (around line 274) similarly:

```python
            ok = r.status_code in (200, 204)
            if ok and _HAS_GATE and _gate is not None:
                pick["_system"] = system
                _gate.mark_sent(pick)
            return ok
```

**Step 5: Verify import works**

Run: `cd e:/findtorontoevents_antigravity.ca && py -c "from cross_aggregation.freshpicks_notify import send_fresh_pick; print('OK')"`

Expected: `OK`

**Step 6: Commit**

```bash
git add cross_aggregation/freshpicks_notify.py
git commit -m "feat: integrate centralized gate into send_fresh_pick() — all 5 senders now gated"
```

---

### Task 3: Add State File to Workflow Git Commits

**Files:**
- Modify: `.github/workflows/cross-aggregator.yml` (line 174)
- Modify: `.github/workflows/alpha-engine-live.yml` (around `git add` step)
- Modify: `.github/workflows/deploy-riseoftheclaw.yml` (around `git add` step)
- Modify: `.github/workflows/kimi-feb172026-live.yml` (around `git add` step)
- Modify: `.github/workflows/claude-gainer-tracker.yml` (around `git add` step)

**Context for implementer:**
- Each workflow has a "Commit and push if changed" step with `git add` commands
- We need to add `data/freshpicks_gate_state.json` so the dedup state persists across runs
- Use `2>/dev/null || true` suffix since the file won't exist on first run

**Step 1: Update cross-aggregator.yml**

Find line 174:
```yaml
          git add data/aggregated_picks.json data/freshpicks_consensus_sent.json
```
Add after it:
```yaml
          git add data/freshpicks_gate_state.json 2>/dev/null || true
```

**Step 2: Update the other 4 workflows**

For each workflow, find the `git add` step in the "Commit and push" section and add:
```yaml
          git add data/freshpicks_gate_state.json 2>/dev/null || true
```

**Step 3: Commit**

```bash
git add .github/workflows/cross-aggregator.yml .github/workflows/alpha-engine-live.yml .github/workflows/deploy-riseoftheclaw.yml .github/workflows/kimi-feb172026-live.yml .github/workflows/claude-gainer-tracker.yml
git commit -m "ci: persist freshpicks gate state across workflow runs"
```

---

### Task 4: Refactor `send_top_picks_now.py` to Use Shared Gate

**Files:**
- Modify: `scripts/send_top_picks_now.py`

**Context for implementer:**
- This file already has inline dedup, dynamic TP/SL, Kelly sizing, expiry — all duplicated from what's now in `freshpicks_gate.py`
- Replace the inline implementations with imports from the shared module
- Keep the consensus-specific loading logic (`load_consensus_signals()`) and circuit breaker
- The safety filters (`_apply_safety_filters`, `_filter_duplicates`, etc.) can be simplified since the gate handles most of it
- However, `send_top_picks_now.py` uses `PicksRouter` to route signals to different channels (master_picks, freshpicks, sandbox) — the gate only applies to freshpicks sends
- So we keep the router logic but can remove the duplicate dedup/quality code since the router's `send_signal()` path already goes through PicksRouter which has its own quality checks

**Step 1: Remove duplicate functions**

Remove these functions (they're now in `freshpicks_gate.py` or `PicksRouter`):
- `_compute_atr()` (lines 161-180)
- `_compute_dynamic_tp_sl()` (lines 183-207)
- `_compute_kelly_size()` (lines 210-228)
- `_signal_fingerprint()` (lines 337-340)
- `_load_dedup_cache()` (lines 343-350)
- `_save_dedup_cache()` (lines 353-356)
- `_filter_duplicates()` (lines 359-394)
- `_update_dedup_cache()` (lines 397-417)
- `DEDUP_CACHE_PATH` constant (line 333)
- `DEDUP_COOLDOWN_MINUTES` constant (line 334)

Keep:
- `_check_circuit_breaker_pre_send()`
- `load_consensus_signals()`
- `_compute_rr()`
- `_is_fresh()`
- `_apply_safety_filters()` — simplify to only freshness + confidence + R:R (remove dynamic TP/SL and Kelly inline code)
- `send_top_picks()` — remove dedup filter call since PicksRouter handles its own gates

**Step 2: Simplify `_apply_safety_filters`**

Replace the function body to only do freshness + confidence + R:R:

```python
def _apply_safety_filters(signals: list[dict]) -> list[dict]:
    """Apply safety filters: freshness, confidence floor, R:R sanity."""
    filtered = []
    skipped = {"stale": 0, "confidence": 0, "rr": 0}

    for sig in signals:
        if not _is_fresh(sig):
            skipped["stale"] += 1
            continue
        conf = sig.get('confidence', 0)
        if conf < 0.60:
            skipped["confidence"] += 1
            continue
        rr = _compute_rr(sig)
        if rr is not None and rr < 1.0:
            skipped["rr"] += 1
            continue
        filtered.append(sig)

    total = sum(skipped.values())
    if total:
        print(f"Safety filters: {total} removed (stale={skipped['stale']}, "
              f"low_conf={skipped['confidence']}, bad_rr={skipped['rr']}), "
              f"{len(filtered)} remaining")
    return filtered
```

**Step 3: Remove dedup filter call from `send_top_picks()`**

In `send_top_picks()`, remove these lines (around line 448-452):
```python
    # Cross-run dedup: suppress unchanged signals
    signals = _filter_duplicates(signals)
    if not signals:
        print("All signals suppressed by dedup filter (no new/changed signals)")
        return
```

Also remove the `actually_sent` tracking and `_update_dedup_cache(actually_sent)` call since dedup now happens in the gate inside `send_fresh_pick()`.

Remove the `import hashlib` since it's no longer used.

**Step 4: Verify**

Run: `cd e:/findtorontoevents_antigravity.ca && py -c "from scripts.send_top_picks_now import send_top_picks; print('OK')"`

Expected: `OK` (or import error if `risk_management` isn't available locally — that's fine, it works in CI)

**Step 5: Commit**

```bash
git add scripts/send_top_picks_now.py
git commit -m "refactor: remove duplicate dedup/sizing from send_top_picks — now handled by shared gate"
```

---

### Task 5: Smoke Test End-to-End

**Files:**
- None (read-only verification)

**Step 1: Test gate rejects low confidence**

```bash
cd e:/findtorontoevents_antigravity.ca && py -c "
from cross_aggregation.freshpicks_gate import FreshPicksGate
gate = FreshPicksGate()
result = gate.check('Test', {'symbol': 'BTCUSDT', 'direction': 'LONG', 'entry_price': 67000, 'confidence': 0.40})
print(f'Allowed: {result.allowed}, Reason: {result.reason}')
assert not result.allowed
assert 'G2' in result.reason
print('PASS: low confidence blocked')
"
```

Expected: `PASS: low confidence blocked`

**Step 2: Test gate allows good pick and enriches it**

```bash
cd e:/findtorontoevents_antigravity.ca && py -c "
from cross_aggregation.freshpicks_gate import FreshPicksGate
gate = FreshPicksGate()
result = gate.check('Test', {'symbol': 'BTCUSDT', 'direction': 'LONG', 'entry_price': 67000, 'tp_price': 72000, 'sl_price': 64000, 'confidence': 0.80})
print(f'Allowed: {result.allowed}')
assert result.allowed
assert result.pick['size_frac'] > 0, 'Kelly sizing missing'
assert result.pick['expires_at'], 'Expiry missing'
assert result.pick['rr'] > 0, 'R:R missing'
print(f'Size: {result.pick[\"size_frac\"]:.2%}, RR: {result.pick[\"rr\"]}, Expires: {result.pick[\"expires_at\"]}')
print('PASS: good pick enriched')
"
```

Expected: `PASS: good pick enriched`

**Step 3: Test dedup blocks repeat**

```bash
cd e:/findtorontoevents_antigravity.ca && py -c "
from cross_aggregation.freshpicks_gate import FreshPicksGate
gate = FreshPicksGate()
pick = {'symbol': 'ETHUSDT', 'direction': 'LONG', 'entry_price': 2000, 'tp_price': 2300, 'sl_price': 1850, 'confidence': 0.75}
r1 = gate.check('Test', pick)
assert r1.allowed, f'First should pass: {r1.reason}'
gate.mark_sent(r1.pick)
r2 = gate.check('Test', pick)
print(f'Second check: Allowed={r2.allowed}, Reason={r2.reason}')
assert not r2.allowed
assert 'G1' in r2.reason
print('PASS: dedup blocks identical repeat')
"
```

Expected: `PASS: dedup blocks identical repeat`

**Step 4: Test banned strategy rejected**

```bash
cd e:/findtorontoevents_antigravity.ca && py -c "
from cross_aggregation.freshpicks_gate import FreshPicksGate
gate = FreshPicksGate()
pick = {'symbol': 'BTCUSDT', 'direction': 'LONG', 'entry_price': 67000, 'tp_price': 72000, 'sl_price': 64000, 'confidence': 0.80, 'strategy': 'smart_money_fvg'}
result = gate.check('Test', pick)
assert not result.allowed
assert 'G3' in result.reason
print('PASS: banned strategy blocked')
"
```

Expected: `PASS: banned strategy blocked`

**Step 5: Clean up test state file**

```bash
rm -f data/freshpicks_gate_state.json
```

**Step 6: Final commit — all tasks done**

```bash
git add -A
git commit -m "feat: FreshPicks fund-grade overhaul — centralized 7-gate pipeline for all Discord senders

Addresses Discord feedback: massive duplication, static price ladders,
confidence drift, low-quality scout picks, missing sizing/expiry.

New: cross_aggregation/freshpicks_gate.py (7 gates)
- G1: 30-min dedup per symbol+direction (bypass if price changed)
- G2: Confidence floor >= 0.65
- G3: Banned strategy + rolling WR filter
- G4: R:R >= 1.0
- G5: ATR-based dynamic TP/SL (replaces static ladders)
- G6: Kelly sizing + 15-min expiry in Discord embed
- G7: Rate cap 8 picks per 60-min window

Modified: freshpicks_notify.py, send_top_picks_now.py, 5 workflow YAMLs"
```
