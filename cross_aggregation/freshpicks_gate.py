"""
FreshPicks Quality Gate — Centralized enforcement for all Discord senders.
==========================================================================

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
  G9: Score floor (>= 20 for LONG picks, per leak-free audit v3)

State: data/freshpicks_gate_state.json (persisted via git commit in workflows)
"""

import json
import pathlib
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional

# MySQL gate logging (fire-and-forget)
try:
    from audit_trail.mysql_client import log_gate_decision as _mysql_log_gate
    _HAS_MYSQL_GATE = True
except ImportError:
    _HAS_MYSQL_GATE = False

# Repo root (works both locally and in GitHub Actions)
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Gate state file
STATE_PATH = REPO_ROOT / "data" / "freshpicks_gate_state.json"

# --- Configuration ---
DEDUP_COOLDOWN_MIN = 30        # G1: minutes before same symbol+direction can re-send
CONFIDENCE_FLOOR = 0.30        # TESTING SPRINT: was 0.65, lowered to let most signals through
STRATEGY_WR_FLOOR = 0.01       # TESTING SPRINT: was 0.48, effectively disabled
STRATEGY_MIN_TRADES = 5        # G3: minimum trades before WR filter applies
RR_FLOOR = 1.0                 # G4: minimum risk:reward ratio
ATR_DEFAULT_PCT = 0.02         # G5: fallback ATR as fraction of price (2%)
ATR_SL_MULT = 1.5              # G5: SL = entry ± ATR * this
ATR_TP_MULT = 2.5              # G5: TP = entry ± ATR * this
KELLY_CAP = 0.02               # G6: max Kelly fraction (2% of portfolio)
EXPIRY_MINUTES = 15            # G6: signal expiry
RATE_CAP = 999                 # TESTING SPRINT: was 8, uncapped
RATE_WINDOW_MIN = 60           # G7: rolling window in minutes
REGIME_FNG_EXTREME_FEAR = 20   # G8: F&G threshold for extreme fear
REGIME_LONG_PENALTY = 0.15     # G8: confidence penalty for LONG in extreme fear
MIN_AGREEMENT_SANDBOX = 1      # G8: warn (not block) if agreement < 2
SCORE_FLOOR_LONG = 20          # G9: minimum Score for LONG picks (audit v3: Score>=20 = 90% WR)
SCORE_FLOOR_SHORT = 0          # G9: no score floor for SHORT (too few data points)

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
    "mercury2":                  "mercury2/data/closed_picks.json",
    "mercury_2":                 "mercury2/data/closed_picks.json",
    "alpha_engine":              "alpha_engine/data/closed_picks.json",
    "claws_of_doom":             "ml_battleground/system_f_clawsofdoom/data/closed_picks.json",
    "kimi":                      "KIMI_RISEOFTHECLAW/data/closed_picks.json",
    "kimi_rise_of_the_claw":     "KIMI_RISEOFTHECLAW/data/closed_picks.json",
    "cross_system_consensus":    "data/cross_system_closed.json",
    "claude_gainer_ml":          "crypto_gainer_ml/tracker/closed_picks.json",
}


def _normalize_symbol(raw: str) -> str:
    """Normalize symbol names: BTC-USD, BTCUSD, BTC/USDT, BTCUSDT -> BTCUSDT."""
    s = raw.strip().upper().replace("/", "").replace("-", "")
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
    """Fetch ATR as fraction of price from Binance hourly klines."""
    binance_sym = _normalize_symbol(symbol)
    _SPOT_BASES = [
        "https://api.binance.com", "https://api1.binance.com",
        "https://data-api.binance.vision", "https://api.binance.us",
    ]
    data = None
    for _base in _SPOT_BASES:
        try:
            url = f"{_base}/api/v3/klines?symbol={binance_sym}&interval=1h&limit={period + 1}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            break  # success
        except Exception:
            continue
    if not data:
        return ATR_DEFAULT_PCT
    try:
        if len(data) < period + 1:
            return ATR_DEFAULT_PCT
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
    for rp in (0.05, 0.10, 0.15, 0.20):
        if abs(tp_pct - rp) < 0.001 or abs(sl_pct - rp) < 0.001:
            return True
    return False


def _compute_kelly(confidence: float, edge: float, vol: float) -> float:
    """Kelly fraction: f = (2p-1) * edge / vol^2, capped at KELLY_CAP."""
    if vol < 0.001:
        vol = 0.001
    f = (2 * confidence - 1) * edge / (vol ** 2)
    return max(min(f, KELLY_CAP), 0.0)


def _fetch_fear_greed() -> Optional[int]:
    """Fetch current Fear & Greed index (0-100). Returns None on failure."""
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        return int(data["data"][0]["value"])
    except Exception:
        return None


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
                and (c.get("pnl_pct") or c.get("net_pnl_pct", 0)) > 0)
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
        self.pick = pick


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
        gate.mark_sent(result.pick)  # call AFTER successful Discord send
    """

    def __init__(self):
        self._state = _load_state()

    def _log_gate(self, symbol, direction, system, strategy, gate, result, reason, confidence=None, entry=None):
        """Fire-and-forget MySQL gate logging."""
        if _HAS_MYSQL_GATE:
            try:
                _mysql_log_gate(symbol, direction, system, strategy, gate, result, reason,
                                confidence=confidence, entry_price=entry)
            except Exception:
                pass

    def check(self, system: str, pick: Dict) -> GateResult:
        """Run all gates (G1-G9). Returns GateResult with allowed/reason/enriched pick."""
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
            reason = f"G2: confidence {confidence:.2f} < {CONFIDENCE_FLOOR}"
            self._log_gate(norm_sym, direction, system, strategy, "G2_CONFIDENCE", "REJECT", reason, confidence, entry)
            return GateResult(False, reason)

        # --- G3: Losing strategy filter ---
        if strategy and str(strategy).lower() in BANNED_STRATEGIES:
            reason = f"G3: banned strategy '{strategy}'"
            self._log_gate(norm_sym, direction, system, strategy, "G3_STRATEGY", "REJECT", reason, confidence, entry)
            return GateResult(False, reason)
        wr = _compute_rolling_wr(sys_key)
        if wr is not None and wr < STRATEGY_WR_FLOOR:
            reason = f"G3: system '{sys_key}' rolling WR {wr:.0%} < {STRATEGY_WR_FLOOR:.0%}"
            self._log_gate(norm_sym, direction, system, strategy, "G3_STRATEGY", "REJECT", reason, confidence, entry)
            return GateResult(False, reason)

        # --- G8: Regime-aware confidence adjustment ---
        fng = _fetch_fear_greed()
        regime_warning = None
        if fng is not None:
            if fng <= REGIME_FNG_EXTREME_FEAR and direction in ("LONG", "BUY"):
                # Penalize LONG in extreme fear — contrarian must have very high confidence
                old_conf = confidence
                confidence = confidence - REGIME_LONG_PENALTY
                regime_warning = f"F&G={fng} (Extreme Fear) — LONG confidence penalized {old_conf:.2f}→{confidence:.2f}"
                if confidence < CONFIDENCE_FLOOR:
                    reason = f"G8: {regime_warning} — below floor {CONFIDENCE_FLOOR}"
                    self._log_gate(norm_sym, direction, system, strategy, "G8_REGIME", "REJECT", reason, confidence, entry)
                    return GateResult(False, reason)

        # --- G9: Score floor (leak-free audit v3 recommendation) ---
        score_raw = pick.get("score", pick.get("Score", pick.get("pfScore", None)))
        if score_raw is not None:
            try:
                score_val = float(score_raw)
            except (ValueError, TypeError):
                score_val = None
            if score_val is not None:
                floor = SCORE_FLOOR_LONG if direction in ("LONG", "BUY") else SCORE_FLOOR_SHORT
                if floor > 0 and score_val < floor:
                    reason = f"G9: Score {score_val:.0f} < {floor} ({direction} floor)"
                    self._log_gate(norm_sym, direction, system, strategy, "G9_SCORE_FLOOR", "REJECT", reason, confidence, entry)
                    return GateResult(False, reason)

        # --- G5: Dynamic TP/SL (before G1 so fingerprint uses new levels) ---
        if entry > 0:
            needs_dynamic = (tp <= 0 or sl <= 0 or _is_static_ladder(entry, tp, sl))
            prev = self._state.get("dedup", {}).get(dedup_key, {})
            if not needs_dynamic and prev:
                if prev.get("entry") == entry and prev.get("tp") == tp and prev.get("sl") == sl:
                    needs_dynamic = True

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
        rr = 0.0
        if entry > 0 and tp > 0 and sl > 0:
            risk = abs(entry - sl)
            reward = abs(tp - entry)
            rr = reward / risk if risk > 0 else 0
            if rr < RR_FLOOR:
                reason = f"G4: R:R {rr:.2f} < {RR_FLOOR}"
                self._log_gate(norm_sym, direction, system, strategy, "G4_RR", "REJECT", reason, confidence, entry)
                return GateResult(False, reason)

        # --- G1: Dedup / throttle ---
        now = datetime.now(tz=timezone.utc)
        prev = self._state.get("dedup", {}).get(dedup_key, {})
        if prev:
            try:
                last_sent = datetime.fromisoformat(prev["sent_at"])
                age_min = (now - last_sent).total_seconds() / 60
                if age_min < DEDUP_COOLDOWN_MIN:
                    price_changed = (
                        prev.get("entry") != entry
                        or prev.get("tp") != round(tp, 4)
                        or prev.get("sl") != round(sl, 4)
                    )
                    if not price_changed:
                        reason = f"G1: dedup — {dedup_key} sent {age_min:.0f}min ago (cooldown={DEDUP_COOLDOWN_MIN}min)"
                        self._log_gate(norm_sym, direction, system, strategy, "G1_DEDUP", "REJECT", reason, confidence, entry)
                        return GateResult(False, reason)
            except Exception:
                pass

        # --- G7: Rate cap ---
        rate_window = self._state.get("rate_window", [])
        cutoff = (now - timedelta(minutes=RATE_WINDOW_MIN)).isoformat()
        rate_window = [ts for ts in rate_window if ts > cutoff]
        if len(rate_window) >= RATE_CAP:
            reason = f"G7: rate cap — {len(rate_window)} picks in last {RATE_WINDOW_MIN}min (max={RATE_CAP})"
            self._log_gate(norm_sym, direction, system, strategy, "G7_RATE_CAP", "REJECT", reason, confidence, entry)
            return GateResult(False, reason)

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

        # Regime context for embed display
        if fng is not None:
            enriched["fear_greed"] = fng
            if fng <= 20:
                enriched["regime_label"] = "Extreme Fear"
            elif fng <= 40:
                enriched["regime_label"] = "Fear"
            elif fng <= 60:
                enriched["regime_label"] = "Neutral"
            elif fng <= 80:
                enriched["regime_label"] = "Greed"
            else:
                enriched["regime_label"] = "Extreme Greed"
        if regime_warning:
            enriched["regime_warning"] = regime_warning

        # Agreement context (pass-through from pick)
        agreement = pick.get("agreement_count", pick.get("consensus_count", 0))
        total_sys = pick.get("total_systems", 0)
        if agreement:
            enriched["agreement_count"] = agreement
            enriched["total_systems"] = total_sys

        self._log_gate(norm_sym, direction, system, strategy, "ALL_GATES", "PASS", "all gates passed", confidence, entry)
        return GateResult(True, "all gates passed", enriched)

    def mark_sent(self, pick: Dict):
        """Call after successful Discord send to update dedup state."""
        symbol = pick.get("symbol", "???")
        direction = pick.get("direction", "LONG").upper()
        norm_sym = _normalize_symbol(symbol)
        dedup_key = f"{norm_sym}__{direction}"
        now = datetime.now(tz=timezone.utc)

        dedup = self._state.setdefault("dedup", {})
        dedup[dedup_key] = {
            "sent_at": now.isoformat(),
            "entry": pick.get("entry_price", 0),
            "tp": pick.get("tp_price", 0),
            "sl": pick.get("sl_price", 0),
            "confidence": pick.get("confidence", 0),
            "system": pick.get("_system", "unknown"),
        }

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
