"""
AI Tournament — Pick Population Engine.

Loads model × persona mapping from config/model_persona_mapping.json,
attempts to call each model's API to generate forward-test picks, and
writes the aggregated results to data/ai_tournament/picks_YYYYMMDD.json.

API fallback chain per model:
  1. Direct API call (if API key available)
  2. Skip (log warning) if no key
If ALL models fail, falls back to generating picks from local alpha engine data.

Usage:
    python tools/populate_picks.py
    FORCE_REGENERATE=true python tools/populate_picks.py  # re-prompt even if picks exist for today
"""

from __future__ import annotations

import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "model_persona_mapping.json"
PICKS_DIR = REPO_ROOT / "data" / "ai_tournament"
LATEST_PICKS = REPO_ROOT / "audit_dashboard" / "data" / "ai_tournament_picks_latest.json"
ACTIVE_PICKS = REPO_ROOT / "alpha_engine" / "data" / "active_picks.json"
SMART_PICKS = REPO_ROOT / "alpha_engine" / "data" / "smart_picks.json"

FORCE_REGENERATE = os.environ.get("FORCE_REGENERATE", "false").lower() in ("true", "1", "yes")


def load_config() -> dict[str, Any]:
    """Load the model-persona mapping configuration."""
    if not CONFIG_PATH.exists():
        print(f"[populate] ERROR: config not found at {CONFIG_PATH}")
        sys.exit(1)
    return json.loads(CONFIG_PATH.read_text())


def today_str() -> str:
    """YYYYMMDD string for today's date."""
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def pick_out_path() -> Path:
    """Path for today's picks file."""
    PICKS_DIR.mkdir(parents=True, exist_ok=True)
    return PICKS_DIR / f"picks_{today_str()}.json"


def already_generated() -> bool:
    """Check if today's picks file already exists (skip re-prompt unless forced)."""
    if FORCE_REGENERATE:
        return False
    path = pick_out_path()
    if path.exists():
        data = json.loads(path.read_text())
        if isinstance(data, list) and len(data) > 0:
            print(f"[populate] Today's picks already exist at {path.name} ({len(data)} picks)")
            return True
    return False


# ── Universe definitions ──

DEFAULT_UNIVERSE: dict[str, list[str]] = {
    "CRYPTO": [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT",
    ],
    "EQUITY": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
        "JPM", "V", "JNJ", "WMT", "MA", "PG", "DIS", "NFLX",
    ],
    "FOREX": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF"],
    "COMMODITY": ["GC=F", "SI=F", "CL=F", "NG=F", "HG=F"],
    "ETF": ["SPY", "QQQ", "IWM", "EEM", "GLD"],
    "BOND": ["^TNX", "^TYX"],
}


def get_universe(config: dict) -> dict[str, list[str]]:
    """Get the pre-registered universe from config or fallback."""
    return config.get("universe", DEFAULT_UNIVERSE)


# ── API callers ──

def call_openai_api(
    api_key: str, model: str, messages: list[dict], timeout: int = 60
) -> dict | None:
    """Call an OpenAI-compatible chat completions endpoint."""
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 4096,
            },
            timeout=timeout,
        )
        if resp.status_code == 200:
            return resp.json()
        print(f"  [API] OpenAI error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"  [API] OpenAI exception: {e}")
    return None


def call_generic_openai_compat(
    api_key: str, endpoint: str, model: str, messages: list[dict], timeout: int = 60
) -> dict | None:
    """Call any OpenAI-compatible endpoint (OpenRouter, etc.)."""
    try:
        resp = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 4096,
            },
            timeout=timeout,
        )
        if resp.status_code == 200:
            return resp.json()
        print(f"  [API] {model} error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"  [API] {model} exception: {e}")
    return None


def call_anthropic_api(
    api_key: str, model: str, messages: list[dict], timeout: int = 60
) -> dict | None:
    """Call Anthropic's messages API."""
    try:
        system_msg = ""
        filtered_messages = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                filtered_messages.append(m)

        payload: dict[str, Any] = {
            "model": model,
            "messages": filtered_messages,
            "max_tokens": 4096,
            "temperature": 0.7,
        }
        if system_msg:
            payload["system"] = system_msg

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout,
        )
        if resp.status_code == 200:
            return resp.json()
        print(f"  [API] Anthropic error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"  [API] Anthropic exception: {e}")
    return None


# ── Prompt builder ──

BUILD_PROMPT = """You are a quantitative trading analyst participating in a prediction tournament.
Your task: generate {n} specific, actionable forward-test picks for {asset_class}.

Rules:
1. Pick ONLY from the approved universe: {universe}
2. Each pick must have: symbol, direction (LONG/SHORT), entry_price, take_profit, stop_loss, thesis
3. Max SL/TP ratio: 2.0 (SL cannot exceed 2× TP distance)
4. Min RR ≥ 1.5 (reward-to-risk ratio)
5. Be specific — use current approximate prices. Entry must be within 2% of current price.
6. Timeframe: {timeframe}
7. Asset class: {asset_class}
8. Provide a brief thesis explaining the edge
9. Confidence score 0.0-1.0

Output ONLY a valid JSON array. No markdown, no explanation, no code fences. Example:
[
  {{
    "symbol": "BTCUSDT",
    "asset_class": "CRYPTO",
    "direction": "LONG",
    "entry_price": 67500.0,
    "take_profit": 72500.0,
    "stop_loss": 64800.0,
    "thesis": "BTC consolidating above support with declining volume, upside breakout likely",
    "data_source": "technical_analysis",
    "confidence": 0.72,
    "timeframe": "14d"
  }}
]"""


def build_prompt(model_cfg: dict, asset_class: str, universe: list[str]) -> list[dict]:
    """Build the messages array for prompting a model."""
    config = load_config()
    windows = config.get("resolution_windows_days", {})
    timeframe_days = windows.get(asset_class, 14)

    # Number of picks: 2-4 per asset class
    n_picks = random.randint(2, 4)

    # Pick a subset of the universe (5-8 symbols)
    universe_sample = random.sample(universe, min(len(universe), 8))

    prompt = BUILD_PROMPT.format(
        n=n_picks,
        asset_class=asset_class,
        universe=json.dumps(universe_sample),
        timeframe=f"{timeframe_days}d",
    )

    return [
        {"role": "system", "content": "You are a quantitative trading analyst. Output raw JSON only."},
        {"role": "user", "content": prompt},
    ]


# ── Response parsers ──

PERSONA_STRATEGIES: dict[str, str] = {
    "momentum_scalp": "Momentum scalping on 15min-1h timeframe",
    "trend_follower": "Trend following with 20/50 EMA cross",
    "mean_reversion": "Mean reversion with RSI < 30 / > 70",
    "value_investor": "Value with P/E < sector avg + healthy balance sheet",
    "sector_rotation": "Sector rotation based on relative strength",
    "carry_trade": "Carry trade focusing on interest rate differentials",
    "grid_trader": "Grid trading in range-bound markets",
    "growth_at_reasonable_price": "GARP — PEG < 1.5, revenue growth > 15%",
    "seasonal_pattern": "Seasonal commodity patterns (planting/harvest/storage)",
    "breakout_scanner": "Breakout from 20-day consolidation with volume",
    "momentum_momentum": "3-6 month price momentum with volume confirmation",
    "macro_hedge": "Macro-driven hedges against inflation/growth",
    "volatility_breakout": "Volatility breakout with ATR-based stops",
    "quality_compound": "Quality compounding: ROE > 15%, debt/equity < 0.5",
    "supply_demand": "Supply/demand imbalance at key price levels",
    "central_bank_policy": "Central bank policy divergence trades",
    "narrative_trader": "Narrative-driven plays (AI, energy transition, etc.)",
    "moat_investor": "Wide moat companies with pricing power",
    "global_macro": "Global macro based on GDP/inflation differentials",
    "factor_rotation": "Factor rotation (value, momentum, quality, low vol)",
    "purchasing_power_parity": "PPP-based mean reversion for currency pairs",
    "duration_call": "Duration call based on yield curve expectations",
    "liquidity_grazer": "Liquidity grab on high-timeframe levels",
    "statistical_arb": "Statistical arbitrage on correlated pairs",
    "weather_hedge": "Weather-driven commodity hedges",
    "order_flow": "Order flow imbalance at support/resistance",
    "volatility_tilt": "Volatility risk premium harvesting",
    "flight_to_safety": "Safe haven flows during risk-off events",
    "bayesian_breakout": "Bayesian probability of breakout continuation",
    "cross_sectional_momentum": "Cross-sectional momentum across sectors",
    "inventory_cycle": "Inventory cycle positioning (EIA reports)",
    "onchain_analytics": "On-chain metrics (exchange flows, whale activity)",
    "earnings_momentum": "Earnings surprise + guidance revision momentum",
    "geopolitical_risk": "Geopolitical risk premium trades",
    "quality_growth": "Quality growth at reasonable valuation",
    "technical_swing": "Technical swing on 4h-1d timeframe",
}


def parse_picks_response(
    response: dict | None, model_cfg: dict, model_id: str, asset_class: str
) -> list[dict]:
    """Parse picks from an API response."""
    picks: list[dict] = []

    if not response:
        return picks

    # Extract text content from different API response formats
    content = ""

    # OpenAI format
    if "choices" in response:
        choice = response["choices"][0]
        if "message" in choice:
            content = choice["message"].get("content", "")
        elif "text" in choice:
            content = choice["text"]

    # Anthropic format
    elif "content" in response:
        for block in response["content"]:
            if block.get("type") == "text":
                content += block.get("text", "")

    if not content:
        return picks

    # Try to extract JSON from the response
    content = content.strip()
    
    # Remove markdown code fences if present
    if content.startswith("```"):
        lines = content.split("\n")
        # Find the first and last ``` markers
        start = 0
        end = len(lines)
        for i, line in enumerate(lines):
            if line.strip().startswith("```"):
                if start == 0:
                    start = i + 1
                else:
                    end = i
                    break
        content = "\n".join(lines[start:end])

    # Try to parse as JSON
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        # Try to find JSON array in the text
        match = re.search(r"\[.*\]", content, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                print(f"  [parse] Failed to extract JSON from response for {model_id}")
                return picks
        else:
            print(f"  [parse] No JSON array found in response for {model_id}")
            return picks

    if not isinstance(parsed, list):
        parsed = [parsed]

    strategy_name = ""
    persona_ids = model_cfg.get("assignments", {}).get(asset_class, [])
    if persona_ids:
        persona_id = persona_ids[0]
        strategy_name = PERSONA_STRATEGIES.get(persona_id, persona_id)

    model_version = model_cfg.get("model_name", model_id)

    now_iso = datetime.now(timezone.utc).isoformat()
    for pick in parsed:
        if not isinstance(pick, dict):
            continue
        symbol = pick.get("symbol", "")
        if not symbol:
            continue

        entry = float(pick.get("entry_price", 0))
        tp = float(pick.get("take_profit", 0))
        sl = float(pick.get("stop_loss", 0))

        # Validate basic structure
        if entry <= 0 or tp <= 0 or sl <= 0:
            continue

        picks.append({
            "symbol": symbol,
            "asset_class": asset_class,
            "direction": pick.get("direction", "LONG"),
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "thesis": pick.get("thesis", strategy_name),
            "data_source": pick.get("data_source", "ai_prediction"),
            "confidence": float(pick.get("confidence", 0.5)),
            "timeframe": pick.get("timeframe", f"{asset_class.lower()}_default"),
            "status": "OPEN",
            "submitted_at": now_iso,
            "model_id": model_id,
            "provider": model_cfg.get("provider", ""),
            "model_version": model_version,
            "strategy_name": strategy_name,
            "persona_id": persona_ids[0] if persona_ids else "",
            "current_price": entry,
            "unrealized_pnl_pct": 0.0,
        })

    return picks


# ── Local fallback generator ──

def generate_fallback_picks(config: dict) -> list[dict]:
    """Generate picks from local alpha engine data when API calls fail."""
    print("[populate] All API calls failed — generating fallback picks from local data")
    picks: list[dict] = []
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # Try to load smart picks first
    smart_data = None
    if SMART_PICKS.exists():
        try:
            smart_data = json.loads(SMART_PICKS.read_text())
        except Exception:
            pass

    if smart_data and isinstance(smart_data, dict):
        smart_picks = smart_data.get("picks", [])
        excluded = smart_data.get("excluded_reasons", {})
        print(f"[populate] Found {len(smart_picks)} smart picks, {len(excluded)} excluded groups")
        for sp in smart_picks[:20]:  # Take top 20
            symbol = sp.get("symbol", "")
            asset_class = sp.get("asset_class", "CRYPTO")
            direction = sp.get("direction", "LONG")
            entry = float(sp.get("entry_price", sp.get("current_price", 0)))
            if entry <= 0:
                continue
            tp_dist = float(sp.get("take_profit", entry * 1.15))
            sl_dist = float(sp.get("stop_loss", entry * 0.95))

            picks.append({
                "symbol": symbol,
                "asset_class": asset_class,
                "direction": direction,
                "entry_price": entry,
                "take_profit": tp_dist if direction == "LONG" else entry * 0.85,
                "stop_loss": sl_dist if direction == "LONG" else entry * 1.05,
                "thesis": sp.get("thesis", sp.get("strategy", "Alpha engine pick")),
                "data_source": "alpha_engine",
                "confidence": float(sp.get("smart_score", sp.get("score", 0.5))),
                "timeframe": "14d" if asset_class == "CRYPTO" else "30d",
                "status": "OPEN",
                "submitted_at": now_iso,
                "model_id": "alpha_engine",
                "provider": "Alpha Engine",
                "model_version": "smart_picks_v1",
                "strategy_name": sp.get("strategy", "Smart pick"),
                "persona_id": "alpha_consensus",
                "current_price": entry,
                "unrealized_pnl_pct": 0.0,
            })

    # If still no picks, try active_picks.json
    if not picks and ACTIVE_PICKS.exists():
        try:
            active_data = json.loads(ACTIVE_PICKS.read_text())
            if isinstance(active_data, list):
                for ap in active_data[:20]:
                    symbol = ap.get("symbol", "")
                    asset_class = ap.get("asset_class", ap.get("category", "CRYPTO"))
                    direction = ap.get("direction", "LONG")
                    entry = float(ap.get("entry_price", ap.get("price", 0)))
                    if entry <= 0:
                        continue
                    picks.append({
                        "symbol": symbol,
                        "asset_class": asset_class,
                        "direction": direction,
                        "entry_price": entry,
                        "take_profit": entry * 1.15,
                        "stop_loss": entry * 0.92,
                        "thesis": ap.get("thesis", ap.get("strategy", "Active pick")),
                        "data_source": "alpha_engine",
                        "confidence": float(ap.get("score", ap.get("elite_score", 0.5))),
                        "timeframe": "14d",
                        "status": "OPEN",
                        "submitted_at": now_iso,
                        "model_id": "alpha_engine",
                        "provider": "Alpha Engine",
                        "model_version": "active_picks_v1",
                        "strategy_name": ap.get("strategy", "Active pick"),
                        "persona_id": "alpha_consensus",
                        "current_price": entry,
                        "unrealized_pnl_pct": 0.0,
                    })
        except Exception:
            pass

    # Final fallback: generate synthetic but realistic picks
    if not picks:
        print("[populate] No local picks data — generating synthetic picks per asset class")
        universe = get_universe(config)
        now_iso = datetime.now(timezone.utc).isoformat()
        
        # Generate one pick per major asset class
        synthetic_entries = {
            "CRYPTO": ("BTCUSDT", 67500.0, 72500.0, 64000.0, "LONG"),
            "EQUITY": ("NVDA", 880.0, 960.0, 820.0, "LONG"),
            "FOREX": ("EURUSD", 1.0850, 1.1000, 1.0750, "LONG"),
            "COMMODITY": ("GC=F", 2350.0, 2450.0, 2280.0, "LONG"),
            "ETF": ("SPY", 530.0, 550.0, 515.0, "LONG"),
        }
        for ac, (sym, entry, tp, sl, direction) in synthetic_entries.items():
            picks.append({
                "symbol": sym,
                "asset_class": ac,
                "direction": direction,
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "thesis": f"Technical setup in {ac} — trend continuation expected",
                "data_source": "market_analysis",
                "confidence": 0.65,
                "timeframe": f"{14 if ac == 'CRYPTO' else 30}d",
                "status": "OPEN",
                "submitted_at": now_iso,
                "model_id": "tournament_synthetic",
                "provider": "Fallback Generator",
                "model_version": "v1",
                "strategy_name": f"{ac}_synthetic_fallback",
                "persona_id": "fallback",
                "current_price": entry,
                "unrealized_pnl_pct": 0.0,
            })

    return picks


def try_prompt_model(
    model_id: str, model_cfg: dict, asset_class: str, universe: list[str]
) -> list[dict]:
    """Attempt to prompt a model for picks in an asset class."""
    api_key_env = model_cfg.get("api_key_env", "")
    api_key = os.environ.get(api_key_env, "")
    api_type = model_cfg.get("api_type", "")
    model_name = model_cfg.get("model_name", model_id)
    endpoint = model_cfg.get("endpoint", "")

    if not api_key:
        print(f"  [skip] {model_id}/{asset_class}: no {api_key_env}")
        return []

    messages = build_prompt(model_cfg, asset_class, universe)
    print(f"  [prompt] {model_id}/{asset_class} ({model_name})...")

    response = None
    if api_type == "openai":
        response = call_openai_api(api_key, model_name, messages)
    elif api_type == "anthropic":
        response = call_anthropic_api(api_key, model_name, messages)
    elif api_type == "openai_compat":
        response = call_generic_openai_compat(api_key, endpoint, model_name, messages)
    elif api_type == "deepseek":
        response = call_generic_openai_compat(api_key, endpoint, model_name, messages)
    elif api_type == "cerebras":
        response = call_generic_openai_compat(api_key, endpoint, model_name, messages)
    else:
        print(f"  [skip] {model_id}: unknown api_type '{api_type}'")

    if response:
        picks = parse_picks_response(response, model_cfg, model_id, asset_class)
        print(f"  [result] {model_id}/{asset_class}: {len(picks)} picks")
        return picks

    print(f"  [fail] {model_id}/{asset_class}: API call failed")
    return []


# ── Submission writer (individual model envelopes for price tracker) ──

SUBMISSIONS_DIR = PICKS_DIR / "submissions"


def write_submissions(all_picks: list[dict]) -> None:
    """Write individual model submission files to submissions/ for the price tracker.
    
    The price tracker reads from `submissions/` directory expecting envelope-format
    files per model: {"model_id": ..., "provider": ..., "submitted_at": ..., 
    "status": "OPEN", "picks": [...], "strategy_rationale": ...}
    """
    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)

    # Group by model_id
    by_model: dict[str, list[dict]] = {}
    for p in all_picks:
        mid = p.get("model_id", "unknown")
        by_model.setdefault(mid, []).append(p)

    for model_id, model_picks in by_model.items():
        # Build submission envelope matching the existing format
        provider = model_picks[0].get("provider", "") if model_picks else ""
        submitted_at = model_picks[0].get("submitted_at", datetime.now(timezone.utc).isoformat())

        # Extract pick bodies (strip envelope-only fields, keep per-pick fields)
        pick_bodies = []
        for p in model_picks:
            # Map float confidence (0.0-1.0) to string (HIGH/MEDIUM/LOW)
            # to match existing submission format convention
            conf = p.get("confidence") or 0.5
            if isinstance(conf, (int, float)):
                if conf >= 0.7:
                    conf_str = "HIGH"
                elif conf >= 0.4:
                    conf_str = "MEDIUM"
                else:
                    conf_str = "LOW"
            else:
                conf_str = str(conf)

            body = {
                "symbol": p.get("symbol", ""),
                "asset_class": p.get("asset_class", ""),
                "direction": p.get("direction", "LONG"),
                "entry_price": p.get("entry_price", 0),
                "take_profit": p.get("take_profit", 0),
                "stop_loss": p.get("stop_loss", 0),
                "thesis": p.get("thesis", ""),
                "data_source": p.get("data_source", "ai_prediction"),
                "confidence": conf_str,
                "rating": p.get("rating", "STRONG"),
                "market_supported": p.get("market_supported", True),
                "timeframe": p.get("timeframe", "1D"),
                "status": p.get("status", "OPEN"),
                "submitted_at": p.get("submitted_at", submitted_at),
                "model_id": model_id,
            }
            pick_bodies.append(body)

        envelope = {
            "model_id": model_id,
            "provider": provider,
            "submitted_at": submitted_at,
            "status": "OPEN",
            "picks": pick_bodies,
            "strategy_rationale": model_picks[0].get("strategy_name", f"Tournament pick from {model_id}"),
        }

        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        out_file = SUBMISSIONS_DIR / f"{model_id}_{date_str}.json"
        out_file.write_text(json.dumps(envelope, indent=2))
        print(f"  [submission] Wrote {len(pick_bodies)} picks → {out_file.name}")


# ── Main ──

def main() -> None:
    print(f"[populate] AI Tournament Pick Generator — {datetime.now(timezone.utc).isoformat()}")
    print(f"[populate] Force regenerate: {FORCE_REGENERATE}")

    config = load_config()
    universe = get_universe(config)

    # Skip if already generated for today
    if already_generated():
        return

    all_picks: list[dict] = []
    api_success = False

    models = config.get("models", {})

    # Try each model for each assigned asset class
    for model_id, model_cfg in models.items():
        assignments = model_cfg.get("assignments", {})
        for asset_class in assignments:
            ac_universe = universe.get(asset_class, [])
            if not ac_universe:
                continue
            picks = try_prompt_model(model_id, model_cfg, asset_class, ac_universe)
            if picks:
                api_success = True
                all_picks.extend(picks)
            time.sleep(0.5)  # Rate limit between models

    # If no API calls succeeded, use fallback
    if not api_success or not all_picks:
        print("[populate] No API picks generated — using fallback")
        fallback = generate_fallback_picks(config)
        all_picks.extend(fallback)

    # Add existing picks from previous days (carry forward still-open ones)
    existing_picks = load_existing_picks()
    if existing_picks:
        existing_open = [p for p in existing_picks if p.get("status") == "OPEN"]
        existing_ids = {(p["model_id"], p["symbol"]) for p in all_picks}
        for ep in existing_open:
            key = (ep.get("model_id", ""), ep.get("symbol", ""))
            if key not in existing_ids:
                all_picks.append(ep)
        print(f"[populate] Carried forward {len(existing_open)} open picks from previous days")

    # Write output
    out_path = pick_out_path()
    out_path.write_text(json.dumps(all_picks, indent=2))
    print(f"[populate] Wrote {len(all_picks)} picks to {out_path.name}")

    # Also write latest
    LATEST_PICKS.parent.mkdir(parents=True, exist_ok=True)
    LATEST_PICKS.write_text(json.dumps(all_picks, indent=2))
    print(f"[populate] Wrote {len(all_picks)} picks to {LATEST_PICKS.name}")

    # Write individual model submission files for the price tracker
    write_submissions(all_picks)

    success_count = sum(1 for p in all_picks if p.get("model_id") != "alpha_engine" and p.get("model_id") != "tournament_synthetic")
    fallback_count = len(all_picks) - success_count
    print(f"[populate] Done. API-generated: {success_count}, Fallback: {fallback_count}, Total: {len(all_picks)}")


def load_existing_picks() -> list[dict]:
    """Load picks from previous day's file to carry forward open positions."""
    picks = []
    if PICKS_DIR.exists():
        files = sorted(PICKS_DIR.glob("picks_*.json"), reverse=True)
        for f in files[:3]:  # Check last 3 days
            try:
                data = json.loads(f.read_text())
                if isinstance(data, list):
                    picks.extend(data)
            except Exception:
                pass
    return picks


if __name__ == "__main__":
    main()
