#!/usr/bin/env python3
"""
Opt-in sidecar: run TauricResearch/TradingAgents multi-agent signal analysis.

Install: pip install tradingagents-framework
API keys required: OPENAI_API_KEY or ANTHROPIC_API_KEY in environment

## Wiring Plan
Target caller: alpha_engine/smart_picks_engine.py (score_pick, conviction override)
Wire-up: read tools/data/trading_agents_signals.json; if symbol has ta_signal=bullish + confidence>=0.7,
         add +10 to smart_score and tag pick with "ta_signal_confirmed"
Expected PR/date: after >=2-week shadow validation (target 2026-06-01)
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "data", "trading_agents_signals.json")

DEFAULT_SYMBOLS_RAW = "AAPL,MSFT,NVDA,BTCUSDT,SOLUSDT"
DEFAULT_SYMBOL_CLASS: dict[str, str] = {
    "AAPL": "EQUITY",
    "MSFT": "EQUITY",
    "NVDA": "EQUITY",
    "BTCUSDT": "CRYPTO",
    "SOLUSDT": "CRYPTO",
}

LIVE_MODE = os.environ.get("TA_LIVE_MODE", "0").strip() == "1"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [trading_agents_sidecar] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _resolve_symbols() -> list[str]:
    raw = os.environ.get("TA_SYMBOLS", DEFAULT_SYMBOLS_RAW)
    return [s.strip().upper() for s in raw.split(",") if s.strip()]


def _asset_class_for(symbol: str) -> str:
    return DEFAULT_SYMBOL_CLASS.get(symbol, "EQUITY")


def _write_json(payload: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    log.info("Wrote %s", OUTPUT_PATH)


def _unavailable_stub(error: str | None = None) -> dict[str, Any]:
    stub: dict[str, Any] = {
        "generated_at": _now_iso(),
        "model_used": "unavailable",
        "install_cmd": "pip install tradingagents-framework",
        "signals": [],
    }
    if error:
        stub["error"] = error
    return stub


# ---------------------------------------------------------------------------
# LLM / model resolution (safe — no money spent unless TA_LIVE_MODE=1)
# ---------------------------------------------------------------------------

def _resolve_llm_config() -> tuple[str | None, str | None, str]:
    """
    Returns (provider, api_key, model_label).
    Priority: ANTHROPIC_API_KEY -> OPENAI_API_KEY -> None
    """
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if anthropic_key:
        return ("anthropic", anthropic_key, "claude-haiku-4-5-20251001")

    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if openai_key:
        return ("openai", openai_key, "gpt-4o-mini")

    return (None, None, "unavailable")


# ---------------------------------------------------------------------------
# Stub signal builder (dry-run / no-live-mode)
# ---------------------------------------------------------------------------

def _build_dry_run_signal(symbol: str) -> dict[str, Any]:
    """
    Returns a clearly-labelled dry-run placeholder — no LLM calls, no cost.
    All votes are 'hold' / neutral so the stub cannot accidentally influence scores.
    """
    return {
        "symbol": symbol,
        "asset_class": _asset_class_for(symbol),
        "ta_signal": "neutral",
        "confidence": 0.0,
        "fundamentals_vote": "hold",
        "technicals_vote": "hold",
        "sentiment_vote": "hold",
        "risk_assessment": "medium",
        "generated_at": _now_iso(),
        "_dry_run": True,
        "_note": "Set TA_LIVE_MODE=1 to enable real TradingAgents analysis",
    }


# ---------------------------------------------------------------------------
# Live signal builder (only executed when TA_LIVE_MODE=1)
# ---------------------------------------------------------------------------

def _build_live_signal(
    symbol: str,
    agent_graph: Any,
    provider: str,
    model_label: str,
) -> dict[str, Any]:
    """
    Runs a TradingAgents analysis for one symbol and maps the result to our schema.
    This function is only called when TA_LIVE_MODE=1 AND tradingagents is installed.
    """
    ts = _now_iso()
    log.info("Running TradingAgents analysis for %s (%s)...", symbol, provider)

    try:
        # TradingAgents framework entry point — adapt to actual API as needed.
        # The public TauricResearch/TradingAgents repo exposes:
        #   result = agent_graph.propagate(company_name, analysis_date)
        # result contains keys: final_trade_decision, reasoning, risk_assessment, ...
        result = agent_graph.propagate(symbol, ts[:10])  # date portion only

        decision_raw: str = str(result.get("final_trade_decision", "hold")).lower()
        reasoning: dict[str, Any] = result.get("reasoning", {})

        def _map_vote(text: str) -> str:
            text = text.lower()
            if "buy" in text or "bull" in text or "long" in text:
                return "buy"
            if "sell" in text or "bear" in text or "short" in text:
                return "sell"
            return "hold"

        def _map_signal(vote: str) -> str:
            if vote == "buy":
                return "bullish"
            if vote == "sell":
                return "bearish"
            return "neutral"

        fundamentals_text = reasoning.get("fundamentals_analyst", "hold")
        technicals_text = reasoning.get("technical_analyst", "hold")
        sentiment_text = reasoning.get("sentiment_analyst", "hold")
        risk_text = str(result.get("risk_assessment", "medium")).lower()

        fundamentals_vote = _map_vote(fundamentals_text)
        technicals_vote = _map_vote(technicals_text)
        sentiment_vote = _map_vote(sentiment_text)
        overall_signal = _map_signal(_map_vote(decision_raw))

        # Simple confidence: fraction of analysts aligned with final decision
        votes = [fundamentals_vote, technicals_vote, sentiment_vote]
        target = _map_vote(decision_raw)
        aligned = sum(1 for v in votes if v == target)
        confidence = round(aligned / len(votes), 4)

        risk_level = "medium"
        if "low" in risk_text:
            risk_level = "low"
        elif "high" in risk_text:
            risk_level = "high"

        return {
            "symbol": symbol,
            "asset_class": _asset_class_for(symbol),
            "ta_signal": overall_signal,
            "confidence": confidence,
            "fundamentals_vote": fundamentals_vote,
            "technicals_vote": technicals_vote,
            "sentiment_vote": sentiment_vote,
            "risk_assessment": risk_level,
            "generated_at": ts,
        }

    except Exception as exc:  # noqa: BLE001
        log.warning("TradingAgents analysis failed for %s: %s", symbol, exc)
        fallback = _build_dry_run_signal(symbol)
        fallback["_error"] = str(exc)
        return fallback


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    log.info("trading_agents_signal_sidecar starting (LIVE_MODE=%s)", LIVE_MODE)

    # ------------------------------------------------------------------
    # 1. Check if tradingagents is installed
    # ------------------------------------------------------------------
    try:
        import tradingagents  # noqa: F401  # type: ignore[import]
    except ImportError:
        log.info(
            "tradingagents package not installed. "
            "Install with: pip install tradingagents-framework"
        )
        _write_json(_unavailable_stub())
        return 0

    # ------------------------------------------------------------------
    # 2. Resolve LLM config
    # ------------------------------------------------------------------
    provider, api_key, model_label = _resolve_llm_config()

    if provider is None:
        log.warning("No LLM API key found (OPENAI_API_KEY or ANTHROPIC_API_KEY).")
        _write_json(
            _unavailable_stub(
                error="No LLM API key found (OPENAI_API_KEY or ANTHROPIC_API_KEY)"
            )
        )
        return 0

    log.info("Using provider=%s model=%s", provider, model_label)

    # ------------------------------------------------------------------
    # 3. Dry-run guard — don't spend money unless TA_LIVE_MODE=1
    # ------------------------------------------------------------------
    symbols = _resolve_symbols()
    log.info("Symbols: %s", symbols)

    if not LIVE_MODE:
        log.info(
            "TA_LIVE_MODE is not set — writing dry-run stubs. "
            "Set TA_LIVE_MODE=1 to enable real analysis."
        )
        signals = [_build_dry_run_signal(s) for s in symbols]
        payload = {
            "generated_at": _now_iso(),
            "model_used": model_label,
            "signals": signals,
        }
        _write_json(payload)
        return 0

    # ------------------------------------------------------------------
    # 4. Live mode — build agent graph and run analysis
    # ------------------------------------------------------------------
    try:
        from tradingagents.graph.trading_graph import TradingAgentsGraph  # type: ignore[import]
        from tradingagents.default_config import DEFAULT_CONFIG  # type: ignore[import]

        config = dict(DEFAULT_CONFIG)
        config["llm_provider"] = provider
        config["backend_url"] = ""  # local, no remote backend

        if provider == "anthropic":
            config["deep_think_llm"] = model_label
            config["quick_think_llm"] = model_label
            os.environ.setdefault("ANTHROPIC_API_KEY", api_key)
        else:
            config["deep_think_llm"] = model_label
            config["quick_think_llm"] = model_label
            os.environ.setdefault("OPENAI_API_KEY", api_key)

        agent_graph = TradingAgentsGraph(
            selected_analysts=["fundamentals", "technical", "sentiment"],
            debug=False,
            config=config,
        )

    except Exception as exc:  # noqa: BLE001
        log.error("Failed to initialise TradingAgentsGraph: %s", exc)
        _write_json(_unavailable_stub(error=f"Graph init failed: {exc}"))
        return 0

    signals: list[dict[str, Any]] = []
    for symbol in symbols:
        sig = _build_live_signal(symbol, agent_graph, provider, model_label)
        signals.append(sig)

    payload = {
        "generated_at": _now_iso(),
        "model_used": model_label,
        "signals": signals,
    }
    _write_json(payload)
    log.info("Done. %d signal(s) written.", len(signals))
    return 0


if __name__ == "__main__":
    sys.exit(main())
