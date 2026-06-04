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

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import random
import re
import sys
import threading
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
COVERAGE_FALLBACK_ENABLED = os.environ.get(
    "AI_TOURNAMENT_COVERAGE_FALLBACK_ENABLED", "true"
).lower() in ("true", "1", "yes")
API_TIMEOUT_SECONDS = int(os.environ.get("AI_TOURNAMENT_API_TIMEOUT_SECONDS", "25"))
API_SLEEP_SECONDS = float(os.environ.get("AI_TOURNAMENT_API_SLEEP_SECONDS", "0.2"))
FALLBACK_PICKS_PER_ASSIGNMENT = max(
    1, int(os.environ.get("AI_TOURNAMENT_FALLBACK_PICKS_PER_ASSIGNMENT", "1"))
)
MAX_WORKERS = max(1, int(os.environ.get("AI_TOURNAMENT_MAX_WORKERS", "8")))
MAX_WORKERS_PER_KEY = max(
    1, int(os.environ.get("AI_TOURNAMENT_MAX_WORKERS_PER_KEY", "2"))
)


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
    """Check if today's picks file already exists (skip re-prompt unless forced).

    FIXED 2026-05-28: This function now returns False when picks exist, so the
    main() loop still runs ALL configured models. The old behavior of returning
    True would silently block all 23 models from participating, leaving only
    carried-forward positions as "today's picks".
    """
    if FORCE_REGENERATE:
        return False
    path = pick_out_path()
    if path.exists():
        data = json.loads(path.read_text())
        if isinstance(data, list) and len(data) > 0:
            print(f"[populate] ⚠️ Today's picks file exists ({len(data)} picks). "
                  f"Models will still be called for fresh picks.")
    # FIX: Always return False so main() iterates all configured models
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
    "PENNY": [
        "KULR", "LODE", "CTM", "MVST", "RGTI", "QBTS", "IONQ",
        "FFIE", "SQQQ", "LABD", "SOXS", "ASTS", "GSAT", "RKLB",
        "HOLO", "CRKN", "WULF", "CLSK", "MARA", "AGBA",
    ],
}

BASE_PRICES: dict[str, float] = {
    "BTCUSDT": 67500, "ETHUSDT": 3500, "SOLUSDT": 145, "BNBUSDT": 580,
    "XRPUSDT": 0.55, "ADAUSDT": 0.45, "AVAXUSDT": 34, "DOTUSDT": 6.5,
    "LINKUSDT": 16, "LTCUSDT": 85, "BCHUSDT": 430, "NEARUSDT": 6.8,
    "SUIUSDT": 1.1, "AAPL": 190, "MSFT": 420, "GOOGL": 175, "AMZN": 200,
    "NVDA": 880, "META": 500, "TSLA": 175, "JPM": 200, "V": 275,
    "JNJ": 155, "WMT": 65, "MA": 460, "PG": 165, "UNH": 500, "HD": 340,
    "DIS": 105, "AMD": 165, "NFLX": 650, "EURUSD": 1.0850,
    "GBPUSD": 1.2650, "USDJPY": 157.0, "AUDUSD": 0.665, "USDCHF": 0.91,
    "GC=F": 2350, "SI=F": 28, "CL=F": 78, "NG=F": 2.10, "HG=F": 4.6,
    "ES=F": 5300, "NQ=F": 18500, "YM=F": 39000, "RTY=F": 2100,
    "SPY": 530, "QQQ": 450, "IWM": 205, "EEM": 43, "GLD": 220,
    "^TNX": 4.35, "^TYX": 4.55, "KULR": 0.35, "LODE": 0.28,
    "CTM": 0.42, "MVST": 1.85, "RGTI": 0.92, "QBTS": 1.15,
    "IONQ": 3.45, "FFIE": 0.08, "SQQQ": 10.0, "LABD": 9.0,
    "SOXS": 28.0, "ASTS": 4.20, "GSAT": 1.6, "RKLB": 3.80,
    "HOLO": 1.25, "WULF": 1.55, "CLSK": 2.10, "MARA": 19.0,
}


def get_universe(config: dict) -> dict[str, list[str]]:
    """Get the pre-registered universe from config or fallback."""
    return config.get("universe", DEFAULT_UNIVERSE)


# ── API callers ──

def _post_openai_compat_with_retry(
    label: str,
    endpoint: str,
    api_key: str,
    model: str,
    messages: list[dict],
    timeout: int = 60,
    max_retries: int = 3,
) -> dict | None:
    """POST to an OpenAI-compatible chat endpoint with retry/backoff + tolerant parsing.

    Hardening (2026-05-28) so > 3 tournament models actually succeed:
      - Retries on 429 (rate limit) and 5xx with exponential backoff + Retry-After
        honoring. Free-tier providers (Groq/Together/Fireworks/etc.) flap on 429;
        a single attempt loses the model for the whole day.
      - Tolerates reasoning-model responses that put text in `reasoning_content`
        instead of `content` (DeepSeek-R1 / Qwen-QwQ / Nemotron-thinking variants):
        if the parsed JSON has empty `content` but a non-empty `reasoning_content`,
        copies it across so downstream parse_picks_response() can read it.
      - Classifies failures (rate_limited / auth_error / bad_response / timeout /
        server_error) in the log line so the diagnostics panel can attribute them.
    """
    import time as _time
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 4096,
    }
    backoff = 2.0
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(endpoint, headers=headers, json=body, timeout=timeout)
            code = resp.status_code
            if code == 200:
                try:
                    data = resp.json()
                except ValueError:
                    print(f"  [API] {label}/{model} bad_response: non-JSON 200 body")
                    return None
                # Reasoning-model tolerance: hoist reasoning_content → content if empty.
                try:
                    ch = (data.get("choices") or [{}])[0]
                    msg = ch.get("message") or {}
                    if not (msg.get("content") or "").strip():
                        rc = msg.get("reasoning_content") or msg.get("reasoning") or ""
                        if rc.strip():
                            msg["content"] = rc
                            ch["message"] = msg
                            data["choices"][0] = ch
                except Exception:
                    pass  # leave data as-is; downstream parser handles malformed
                return data
            if code == 429 or 500 <= code < 600:
                # Honor Retry-After if present, else exponential backoff.
                ra = resp.headers.get("Retry-After")
                try:
                    wait = float(ra) if ra else backoff
                except (TypeError, ValueError):
                    wait = backoff
                kind = "rate_limited" if code == 429 else "server_error"
                if attempt < max_retries:
                    print(f"  [API] {label}/{model} {kind} ({code}) — retry {attempt}/{max_retries} in {wait:.1f}s")
                    _time.sleep(min(wait, 30.0))
                    backoff *= 2
                    continue
                print(f"  [API] {label}/{model} {kind} ({code}) — exhausted {max_retries} retries: {resp.text[:160]}")
                return None
            if code in (401, 403):
                print(f"  [API] {label}/{model} auth_error ({code}): {resp.text[:160]}")
                return None
            print(f"  [API] {label}/{model} error {code}: {resp.text[:200]}")
            return None
        except requests.Timeout:
            if attempt < max_retries:
                print(f"  [API] {label}/{model} timeout — retry {attempt}/{max_retries} in {min(backoff,30.0):.1f}s")
                _time.sleep(min(backoff, 30.0))
                backoff *= 2
                continue
            print(f"  [API] {label}/{model} timeout — exhausted {max_retries} retries")
            return None
        except Exception as e:
            print(f"  [API] {label}/{model} exception: {e}")
            return None
    return None


def call_openai_api(
    api_key: str, model: str, messages: list[dict], timeout: int = API_TIMEOUT_SECONDS
) -> dict | None:
    """Call OpenAI's chat completions endpoint (with retry/backoff + tolerant parse)."""
    return _post_openai_compat_with_retry(
        "OpenAI", "https://api.openai.com/v1/chat/completions",
        api_key, model, messages, timeout,
    )


def call_generic_openai_compat(
    api_key: str, endpoint: str, model: str, messages: list[dict], timeout: int = API_TIMEOUT_SECONDS
) -> dict | None:
    """Call any OpenAI-compatible endpoint (OpenRouter/NVIDIA/Groq/Together/etc.)
    with retry/backoff + reasoning-model tolerance."""
    if not endpoint:
        print(f"  [API] {model} missing_endpoint — config has no endpoint URL")
        return None
    return _post_openai_compat_with_retry(
        model, endpoint, api_key, model, messages, timeout,
    )


def call_cerebras_sdk(
    api_key: str, model: str, messages: list[dict], timeout: int = API_TIMEOUT_SECONDS
) -> dict | None:
    """Call Cerebras via their Python SDK (bypasses REST IP blocks)."""
    try:
        import os
        os.environ["CEREBRAS_API_KEY"] = api_key
        from cerebras.cloud.sdk import Cerebras

        client = Cerebras(timeout=timeout)
        # Map messages to SDK format
        sdk_messages = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            sdk_messages.append({"role": role, "content": content})

        resp = client.chat.completions.create(
            messages=sdk_messages,
            model=model,
            max_completion_tokens=4096,
            temperature=0.7,
            top_p=1,
        )
        if resp and resp.choices:
            choice = resp.choices[0]
            content = choice.message.content or ""
            # Convert to openai-format dict for parse_picks_response
            return {
                "choices": [{"message": {"content": content, "role": "assistant"}}],
                "model": model,
            }
    except ImportError:
        print("  [Cerebras] SDK not installed — falling back to REST")
        return None
    except Exception as e:
        print(f"  [Cerebras] SDK error: {e}")
        return None
    return None


def call_anthropic_api(
    api_key: str, model: str, messages: list[dict], timeout: int = API_TIMEOUT_SECONDS
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


def build_prompt(model_cfg: dict, asset_class: str, universe: list[str], persona_id: str = "") -> list[dict]:
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

    # Add persona-specific strategy instructions when a persona is active
    if persona_id:
        strategy_desc = PERSONA_STRATEGIES.get(persona_id, persona_id)
        thesis_options = "\n".join(f"  - {t}" for t in PERSONA_THESIS_MAP.get(persona_id, [f"{persona_id}: look for this setup"]))
        prompt += f"\n\nYour trading persona: {strategy_desc}\nExample thesis options for your style:\n{thesis_options}\n\nPurposefully generate picks that match this persona's unique approach."

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
    "cycle_rotator": "Global macro cycle rotation — economic regime detection across expansion/contraction/recovery phases",
    "signal_miner": "Statistical signal extraction from noisy market data — pattern detection with mathematical models",
    "moat_measurer": "Competitive advantage duration analysis — sustainable moats, pricing power, and capital allocator quality",
    "reflexivity_trader": "Feedback loop trading — self-reinforcing trends in currency, credit, and equity markets",
    "pivot_catcher": "Central bank pivot anticipation — rate cycle timing, yield curve positioning, policy inflection points",
    "correlation_breaker": "Uncorrelated return stream construction — cross-asset diversification with tail risk hedging",
    "forensic_short": "Accounting red-flag detection — revenue recognition, related-party transactions, and financial statement anomalies",
    "conviction_macro": "High-conviction concentrated macro bets — portfolio heat, position sizing by certainty, asymmetric payoff profiles",
    "systematic_momentum": "Trend structure analysis across timeframes — volatility-adjusted trend strength, regime filtering, dynamic position scaling",
    "safety_net": "Margin-of-safety deep value — current asset discount analysis, liquidation value floors, net-net working capital plays",
    "yield_seeker": "Fixed income relative value — yield curve carry, credit spread compression, roll-down capture, duration positioning",
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


PERSONA_THESIS_MAP: dict[str, list[str]] = {
    "momentum_scalp": ["Price surging above VWAP with above-average volume — momentum continuation play", "Consecutive bullish candles breaking prior swing high, scalping follow-through", "RSI(14) rising through 50 with volume confirmation, short-term momentum entry"],
    "trend_follower": ["20 EMA curling above 50 EMA with bullish cross — trend entry on pullback", "Higher lows + higher highs pattern intact, buying the dip at 20 EMA support", "ADX > 25 with +DI crossing above -DI, established trend direction entry"],
    "mean_reversion": ["RSI(14) below 30 on daily — oversold bounce candidate with defined risk", "Price 2+ standard deviations below 20 SMA — statistical reversion to mean", "Bollinger Band lower touch with bearish exhaustion candle, mean reversion long"],
    "value_investor": ["P/E below sector median with improving free cash flow margin — undervalued compounder", "Price-to-book below 1.5 with ROE > 15% — quality at a discount", "Discounted cash flow model suggests 35% upside — margin of safety play"],
    "breakout_scanner": ["Price breaking above 20-day consolidation range with volume spike — measured move", "Flag/pennant pattern resolution to the upside, entering on volume confirmation", "Squeeze indicator firing — Bollinger Bands narrowing then expanding with breakout"],
    "grid_trader": ["Range-bound between well-defined support/resistance with mean reversion at extremes", "ATR shrinking over 5 sessions — range contraction preceding expansion, grid entry", "Price oscillating within 3% band for 10+ sessions — range trading setup"],
    "macro_hedge": ["DXY weakening suggests risk-on rotation into equities and EM — macro long", "Yield curve steepening trade — long duration on slowing growth expectations", "Commodity super-cycle thesis — supply constraints + demand recovery setup"],
    "volatility_breakout": ["IV rank above 80th percentile with directional catalyst — vol expansion play", "ATR expanding rapidly after prolonged compression — breakout entry with wide stops", "VXN/VXD elevated but rolling over — long vol hedge fading into structured product"],
    "quality_compound": ["ROE consistently above 20% with low debt/equity — compounding machine at fair price", "Revenue growing 15%+ YoY with expanding operating margins — quality growth compounder", "Strong free cash flow yield with shareholder-friendly capital allocation policy"],
    "narrative_trader": ["AI infrastructure spending cycle beneficiary with catalyst upcoming — narrative long", "Regulatory clarity in crypto space — institutional adoption narrative trade", "Energy transition policy tailwind — positioning ahead of legislative catalyst"],
    "global_macro": ["GDP growth differential favoring region vs developed markets macro-long", "Inflation trending toward target while central bank holds — real rates play", "Current account surplus country benefiting from commodity terms of trade"],
    "liquidity_grazer": ["Liquidity pool above prior swing high with stop-run likely — hunt for buy stops", "Asian session range breakout with London volume confirmation — liquidity sweep", "Equal highs on lower timeframe with absorption — liquidity grab short"],
    "statistical_arb": ["Pair correlation deviating 2+ sigma from 60-day mean — convergence expected", "Spread between correlated assets at historical extremes — mean reversion stat-arb", "Cointegrated pair diverging with z-score > 2 — entry on convergence thesis"],
    "catalyst_sniper": ["Earnings surprise potential — implied move underpricing realized volatility", "Product launch / FDA decision / regulatory ruling catalyst — asymmetric bet", "Insider buying at key support level with corporate catalyst ahead"],
    "gamma_raid": ["Zero DTE gamma exposure building — max pain pin action into expiry", "Dealer gamma positioning suggests hedging flow into resistance — reversal play", "Options open interest concentration creating magnet effect toward strike price"],
    "microcap_momentum": ["Low float stock with increasing volume + social sentiment — retail momentum flyer", "Micro-cap breaking multi-month downtrend with insider buying — turnaround momentum", "Tight consolidation after parabolic run, flag continuation pattern in small-cap"],
    "distressed_asset": ["Debt restructuring progress with asset sale catalyst — distressed recovery play", "Cash on hand exceeds market cap with positive operating cash flow — value floor", "Sector-wide pessimism overshooting fundamentals — contrarian distressed entry"],
    "deep_value_gambler": ["Price below net current asset value (NCAV) with catalyst — Graham net-net play", "Book value exceeds market cap with no debt — liquidation value floor trade", "Spin-off / stub trading at steep discount to sum-of-parts — value unlocking"],
    "liquidity_scalper": ["Tight spread with above-average volume on order book imbalances — scalping entries", "VWAP deviation with absorption at key level — reversion scalp with tight stop", "Level 2 data shows bid stacking at support — mechanical scalp long"],
    "sentiment_swing": ["Social media sentiment hitting extreme fear levels — contrarian swing entry", "Put/call ratio at extreme along with price at support — sentiment reversal play", "Fund flow data shows capitulation selling — sentiment-driven mean reversion"],
    "retail_momentum": ["Reddit/WallStreetBets mentions spiking with price consolidation — meme catalyst", "Short interest > 20% with price near support — gamma squeeze candidate", "Retail call buying surging with dealers short gamma — upward delta hedging flow"],
    "cycle_rotator": ["ISM manufacturing trending toward expansion with credit spreads tightening — cycle rotation into cyclicals", "Yield curve uninverting signaling regime shift from tightening to easing — macro regime pivot", "Leading economic indicators bottoming with housing starts recovering — early-cycle positioning"],
    "signal_miner": ["Cross-asset correlation breakdown creating statistical arbitrage opportunity — regime filter triggered", "Factor crowding measured by Herfindahl-Hirschman Index at 90th percentile — signal decay reversal play", "Principal component analysis shows first PC explaining < 30% of variance — diversified alpha harvest"],
    "moat_measurer": ["ROIC consistently above WACC by 800+ bps with intangible asset moat — compounding at attractive entry", "Gross margin expanding while R&D intensity holds steady — pricing power validation", "Customer switching cost analysis suggests sticky revenue with 95%+ retention — quality compound"],
    "reflexivity_trader": ["Credit default swaps widening while equity rises — positive feedback loop building into trend acceleration", "Currency weakening fueling export competitiveness while equity inflows accelerate — reflexive cycle entry", "Margin debt rising with price momentum — reflexive long until financing constraints bite"],
    "pivot_catcher": ["Real rates turning negative with forward guidance shifting dovish — rate cycle inflection trade", "Employment trend rolling over while inflation decelerating faster than central bank projections — policy error hedge", "Term premium compressing from elevated levels signaling rate cut expectations — duration extension entry"],
    "correlation_breaker": ["Rolling 60-day cross-asset correlation collapsing below 1-sigma threshold — regime decorrelation trade", "Gold rising alongside real yields breaking the traditional inverse relationship — regime shift in store of value", "Trend-following strategies showing negative correlation to carry — complementary allocation with volatility targeting"],
    "forensic_short": ["Receivables growing faster than revenue for 3+ consecutive quarters — channel stuffing red flag", "Related-party transactions exceeding 15% of COGS with opaque disclosure — earnings quality concern", "Capitalized expenses surging while operating cash flow stagnates — earnings fabrication indicator"],
    "conviction_macro": ["Position sizing at 15%+ portfolio weight with 3:1 asymmetric payoff — high-conviction macro bet", "Multiple expansion thesis backed by structural growth driver and policy tailwind alignment — concentrated core holding", "Risk budget allocated with 5% VaR at 95% confidence for outlier event with 5x upside — asymmetric conviction play"],
    "systematic_momentum": ["ADX above 40 across daily and weekly timeframes with volatility regime expansion — trend strength confirmation", "Moving average convergence in 3 timeframes (20, 50, 200) with positive slope alignment — multi-timeframe trend entry", "Volatility-adjusted momentum score above 2nd standard deviation with regime-filter confirmation — systematic trend capture"],
    "safety_net": ["Enterprise value below net current asset value with positive free cash flow — Graham net-net with catalyst", "Price-to-tangible-book below 0.7 with no debt and insider buying — liquidation value floor with margin of safety", "Working capital per share exceeding market price with turnaround management — deep value reversion to intrinsic worth"],
    "yield_seeker": ["Roll-down yield advantage of 150+ bps over comparable duration with steep curve — carry and roll-down trade", "Credit spread 2+ standard deviations wide vs historical with improving leverage metrics — spread compression opportunity", "Real yield differential favoring domestic bonds with currency hedge cost declining — cross-border carry trade"],
}


def parse_picks_response(
    response: dict | None, model_cfg: dict, model_id: str, asset_class: str, persona_id: str = ""
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
        match = re.search(r"\[.*\]", content, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                print(f"  [parse] Failed to extract JSON from response for {model_id}/{persona_id}")
                return picks
        else:
            print(f"  [parse] No JSON array found in response for {model_id}/{persona_id}")
            return picks

    if not isinstance(parsed, list):
        parsed = [parsed]

    model_version = model_cfg.get("model_name", model_id)
    strategy_name = PERSONA_STRATEGIES.get(persona_id, persona_id)

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
            "generation_source": "model_api",
            "api_status": "api_success",
            "rank_eligible": True,
            "confidence": float(pick.get("confidence", 0.5)),
            "timeframe": pick.get("timeframe", f"{asset_class.lower()}_default"),
            "status": "OPEN",
            "submitted_at": now_iso,
            "model_id": model_id,
            "provider": model_cfg.get("provider", ""),
            "model_version": model_version,
            "strategy_name": strategy_name,
            "persona_id": persona_id,
            "current_price": entry,
            "unrealized_pnl_pct": 0.0,
        })

    return picks


def _fallback_direction(persona_id: str, rng: random.Random) -> str:
    short_bias_personas = {
        "gamma_raid",
        "liquidity_grazer",
        "forensic_short",
        "correlation_breaker",
        "distressed_asset",
        "retail_momentum",
    }
    if persona_id in short_bias_personas and rng.random() < 0.35:
        return "SHORT"
    return "LONG"


def _fallback_price_box(symbol: str, direction: str, rng: random.Random) -> tuple[float, float, float]:
    base_price = BASE_PRICES.get(symbol, 10.0)
    entry = base_price * (1.0 + rng.uniform(-0.01, 0.01))
    reward_pct = rng.uniform(0.055, 0.12)
    risk_pct = rng.uniform(0.025, 0.055)
    if direction == "SHORT":
        take_profit = entry * (1.0 - reward_pct)
        stop_loss = entry * (1.0 + risk_pct)
    else:
        take_profit = entry * (1.0 + reward_pct)
        stop_loss = entry * (1.0 - risk_pct)
    return round(entry, 4), round(take_profit, 4), round(stop_loss, 4)


def generate_assignment_fallback_picks(
    config: dict,
    model_id: str,
    model_cfg: dict,
    asset_class: str,
    universe: list[str],
    persona_id: str,
    fallback_reason: str,
) -> list[dict]:
    """Generate explicit coverage picks when a configured model cannot be called.

    These rows keep the tournament surface complete, but they are marked as
    rank-excluded because they are not direct API outputs from the named model.
    """
    if not universe:
        return []

    seed = f"{today_str()}:{model_id}:{asset_class}:{persona_id}:{fallback_reason}"
    rng = random.Random(seed)
    symbols = rng.sample(universe, min(len(universe), FALLBACK_PICKS_PER_ASSIGNMENT))
    now_iso = datetime.now(timezone.utc).isoformat()
    strategy_name = PERSONA_STRATEGIES.get(persona_id, persona_id)
    picks: list[dict] = []

    for sym in symbols:
        direction = _fallback_direction(persona_id, rng)
        entry, take_profit, stop_loss = _fallback_price_box(sym, direction, rng)
        thesis_options = PERSONA_THESIS_MAP.get(
            persona_id, [f"{persona_id}: setup detected in {sym}"]
        )
        thesis = rng.choice(thesis_options)
        picks.append({
            "symbol": sym,
            "asset_class": asset_class,
            "direction": direction,
            "entry_price": entry,
            "take_profit": take_profit,
            "stop_loss": stop_loss,
            "thesis": thesis,
            "data_source": "ai_tournament_coverage_fallback",
            "generation_source": "coverage_fallback",
            "api_status": fallback_reason,
            "confidence": round(rng.uniform(0.52, 0.68), 2),
            "timeframe": f"{config.get('resolution_windows_days', {}).get(asset_class, 14)}d",
            "status": "OPEN",
            "submitted_at": now_iso,
            "model_id": model_id,
            "provider": model_cfg.get("provider", "Unknown"),
            "model_version": model_cfg.get("model_name", model_id),
            "strategy_name": strategy_name,
            "persona_id": persona_id,
            "current_price": entry,
            "unrealized_pnl_pct": 0.0,
            "reason": (
                f"Coverage fallback because {fallback_reason}; not rank-eligible "
                f"until this model produces direct API submissions. Persona thesis: {thesis}"
            ),
            "rank_eligible": False,
            "rank_exclusion_reason": (
                "Coverage fallback generated by local tournament engine, not by the model API."
            ),
            "data_integrity_flag": "COVERAGE_FALLBACK_NOT_MODEL_API",
            "market_supported": False,
            "rating": "WATCH",
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
        # Fix 2026-05-24: use canonical classifier to validate asset_class
        from alpha_engine.asset_class import asset_class_from_symbol
        for sp in smart_picks[:20]:  # Take top 20
            symbol = sp.get("symbol", "")
            # Trust upstream but validate against canonical classifier
            upstream_ac = sp.get("asset_class", sp.get("category", "CRYPTO")).upper()
            canonical_ac = asset_class_from_symbol(symbol).upper()
            # Override if canonical is a known symbol class (etf/bond/equity/forex/futures)
            if canonical_ac in ("ETF", "BOND", "EQUITY", "FOREX", "FUTURES"):
                asset_class = canonical_ac
            else:
                asset_class = upstream_ac
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
                from alpha_engine.asset_class import asset_class_from_symbol
                for ap in active_data[:20]:
                    symbol = ap.get("symbol", "")
                    # Fix 2026-05-24: validate upstream asset_class against canonical classifier
                    upstream_ac = (ap.get("asset_class") or ap.get("category") or "CRYPTO").upper()
                    canonical_ac = asset_class_from_symbol(symbol).upper()
                    if canonical_ac in ("ETF", "BOND", "EQUITY", "FOREX", "FUTURES"):
                        asset_class = canonical_ac
                    else:
                        asset_class = upstream_ac
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

    # Final fallback: generate persona-differentiated picks per model
    if not picks:
        print("[populate] No local picks data — generating persona-differentiated picks")
        universe = get_universe(config)
        now_iso = datetime.now(timezone.utc).isoformat()

        for model_id, model_cfg in config.get("models", {}).items():
            for asset_class, persona_ids in model_cfg.get("assignments", {}).items():
                ac_universe = universe.get(asset_class, [])
                if not ac_universe:
                    continue
                for persona_id in persona_ids:
                    # Pick 1-2 symbols from this asset class universe
                    symbols = random.sample(ac_universe, min(len(ac_universe), 2))
                    for sym in symbols:
                        base_price = BASE_PRICES.get(sym, 10.0)

                        # Generate persona-specific thesis
                        theses = PERSONA_THESIS_MAP.get(persona_id, [f"{persona_id}: setup detected in {sym}"])
                        thesis = random.choice(theses)

                        # Vary direction and prices based on persona bias
                        direction = "LONG"
                        if persona_id in ["gamma_raid", "liquidity_grazer"] and random.random() < 0.3:
                            direction = "SHORT"
                        tp_mult = 1.08 + random.uniform(-0.02, 0.08)
                        sl_mult = 0.95 - random.uniform(-0.02, 0.03)
                        entry = base_price * (1.0 + random.uniform(-0.01, 0.01))

                        picks.append({
                            "symbol": sym,
                            "asset_class": asset_class,
                            "direction": direction,
                            "entry_price": round(entry, 2),
                            "take_profit": round(entry * tp_mult, 2),
                            "stop_loss": round(entry * sl_mult, 2),
                            "thesis": thesis,
                            "data_source": "persona_analysis",
                            "confidence": round(0.6 + random.uniform(0.0, 0.25), 2),
                            "timeframe": f"{config.get('resolution_windows_days', {}).get(asset_class, 14)}d",
                            "status": "OPEN",
                            "submitted_at": now_iso,
                            "model_id": model_id,
                            "provider": model_cfg.get("provider", "Unknown"),
                            "model_version": model_cfg.get("model_name", model_id),
                            "strategy_name": persona_id,
                            "persona_id": persona_id,
                            "current_price": round(entry, 2),
                            "unrealized_pnl_pct": 0.0,
                            "reason": thesis,
                        })

        print(f"[populate] Generated {len(picks)} persona-differentiated picks across {len(config.get('models', {}))} models")

    return picks


def try_prompt_model(
    model_id: str, model_cfg: dict, asset_class: str, universe: list[str], persona_id: str = ""
) -> tuple[list[dict], str]:
    """Attempt to prompt a model for picks in an asset class."""
    api_key_env = model_cfg.get("api_key_env", "")
    api_key = os.environ.get(api_key_env, "")
    api_type = model_cfg.get("api_type", "")
    model_name = model_cfg.get("model_name", model_id)
    endpoint = model_cfg.get("endpoint", "")

    label = f"{model_id}/{persona_id}/{asset_class}" if persona_id else f"{model_id}/{asset_class}"

    if not api_key:
        print(f"  [skip] {label}: missing {api_key_env}")
        return [], "missing_api_key"

    messages = build_prompt(model_cfg, asset_class, universe, persona_id)
    print(f"  [prompt] {label} ({model_name})...")

    response = None
    if api_type == "openai":
        response = call_openai_api(
            api_key, model_name, messages, timeout=API_TIMEOUT_SECONDS
        )
    elif api_type == "anthropic":
        response = call_anthropic_api(
            api_key, model_name, messages, timeout=API_TIMEOUT_SECONDS
        )
    elif api_type == "openai_compat":
        response = call_generic_openai_compat(
            api_key, endpoint, model_name, messages, timeout=API_TIMEOUT_SECONDS
        )
    elif api_type == "deepseek":
        response = call_generic_openai_compat(
            api_key, endpoint, model_name, messages, timeout=API_TIMEOUT_SECONDS
        )
    elif api_type == "cerebras":
        response = call_cerebras_sdk(
            api_key, model_name, messages, timeout=API_TIMEOUT_SECONDS
        )
    else:
        print(f"  [skip] {model_id}: unknown api_type '{api_type}'")
        return [], "unknown_api_type"

    if response:
        picks = parse_picks_response(response, model_cfg, model_id, asset_class, persona_id)
        print(f"  [result] {label}: {len(picks)} picks")
        if picks:
            return picks, "api_success"
        return [], "api_empty_response"

    print(f"  [fail] {label}: API call failed")
    return [], "api_failed"


def build_prompt_tasks(
    models: dict[str, dict], universe: dict[str, list[str]]
) -> list[dict[str, Any]]:
    """Create deterministic prompt tasks for model × persona × asset class."""
    tasks: list[dict[str, Any]] = []
    seq = 0
    for model_id, model_cfg in models.items():
        assignments = model_cfg.get("assignments", {})
        for asset_class, persona_ids in assignments.items():
            ac_universe = universe.get(asset_class, [])
            if not ac_universe:
                continue
            for persona_id in persona_ids:
                tasks.append(
                    {
                        "seq": seq,
                        "model_id": model_id,
                        "model_cfg": model_cfg,
                        "asset_class": asset_class,
                        "persona_id": persona_id,
                        "universe": ac_universe,
                        "key_bucket": model_cfg.get("api_key_env", "") or model_id,
                    }
                )
                seq += 1
    return tasks


def collect_api_and_coverage_picks(
    tasks: list[dict[str, Any]], config: dict[str, Any]
) -> tuple[list[dict], dict[str, int], int]:
    """Execute model prompt tasks concurrently with per-key throttling."""
    if not tasks:
        return [], {}, 0

    semaphores = {
        bucket: threading.Semaphore(MAX_WORKERS_PER_KEY)
        for bucket in {task["key_bucket"] for task in tasks}
    }
    workers = min(MAX_WORKERS, len(tasks))
    print(
        f"[populate] Prompting {len(tasks)} assignments across {workers} workers "
        f"(max {MAX_WORKERS_PER_KEY} per API key bucket)"
    )

    def run_task(task: dict[str, Any]) -> tuple[int, list[dict], str]:
        semaphore = semaphores[task["key_bucket"]]
        with semaphore:
            picks, status = try_prompt_model(
                task["model_id"],
                task["model_cfg"],
                task["asset_class"],
                task["universe"],
                task["persona_id"],
            )
            if not picks and COVERAGE_FALLBACK_ENABLED:
                picks = generate_assignment_fallback_picks(
                    config,
                    task["model_id"],
                    task["model_cfg"],
                    task["asset_class"],
                    task["universe"],
                    task["persona_id"],
                    status,
                )
                if picks:
                    print(
                        f"  [coverage] {task['model_id']}/{task['persona_id']}/{task['asset_class']}: "
                        f"{len(picks)} fallback picks ({status})"
                    )
            if API_SLEEP_SECONDS > 0:
                time.sleep(API_SLEEP_SECONDS)
        return task["seq"], picks, status

    ordered_results: list[tuple[int, list[dict], str]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_task = {executor.submit(run_task, task): task for task in tasks}
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            label = f"{task['model_id']}/{task['persona_id']}/{task['asset_class']}"
            try:
                ordered_results.append(future.result())
            except Exception as exc:  # pragma: no cover - defensive logging
                print(f"  [error] {label}: worker crashed: {exc}")
                ordered_results.append((task["seq"], [], "worker_exception"))

    all_picks: list[dict] = []
    model_status_counts: dict[str, int] = {}
    coverage_fallback_count = 0
    for _seq, picks, status in sorted(ordered_results, key=lambda item: item[0]):
        model_status_counts[status] = model_status_counts.get(status, 0) + 1
        if picks:
            all_picks.extend(picks)
            coverage_fallback_count += sum(
                1 for pick in picks if pick.get("generation_source") == "coverage_fallback"
            )
    return all_picks, model_status_counts, coverage_fallback_count


# ── Submission writer (individual model envelopes for price tracker) ──

SUBMISSIONS_DIR = PICKS_DIR / "submissions"


def write_submissions(all_picks: list[dict]) -> None:
    """Write individual model submission files to submissions/ for the price tracker.
    
    The price tracker reads from `submissions/` directory expecting envelope-format
    files per model: {"model_id": ..., "provider": ..., "submitted_at": ..., 
    "status": "OPEN", "picks": [...], "strategy_rationale": ...}

    2026-05-28 fix: always emit a submission envelope for every model that was
    *configured* (even if 0 picks succeeded). This makes /audit/ai-tournament.html
    and the model drill-downs show the real coverage (e.g. "23 configured, only 3
    produced valid picks today") instead of the page appearing to only know about
    the 3 that happened to succeed. Previously silent no-op models were invisible.
    """
    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)

    # Group by model_id from actual picks
    by_model: dict[str, list[dict]] = {}
    for p in all_picks:
        mid = p.get("model_id", "unknown")
        by_model.setdefault(mid, []).append(p)

    # 2026-05-28 visibility fix for /audit/ai-tournament.html:
    # Always emit a submission envelope for *every* model declared in the config,
    # even if it produced zero valid picks today. This stops the page from looking
    # like only 3 models exist when the mapping actually declares 23.
    try:
        full_config = load_config()
        declared = set(full_config.get("models", {}).keys())
        for mid in declared:
            if mid not in by_model:
                by_model[mid] = []   # empty → will get a clear "no_picks" envelope
    except Exception:
        pass  # non-fatal; we still write whatever we have

    for model_id, model_picks in by_model.items():
        # Build submission envelope matching the existing format
        provider = model_picks[0].get("provider", "") if model_picks else ""
        submitted_at = model_picks[0].get("submitted_at", datetime.now(timezone.utc).isoformat()) if model_picks else datetime.now(timezone.utc).isoformat()

        # 2026-05-28: when a configured model produced zero picks, still emit an
        # envelope so the tournament page and drill-downs can show "attempted but failed"
        # instead of the model being completely invisible (the old "only 3 models" symptom).
        if not model_picks:
            envelope = {
                "model_id": model_id,
                "provider": provider or "unknown",
                "submitted_at": submitted_at,
                "status": "no_picks_generated",
                "reason": "API call failed, key missing, or response could not be parsed into valid picks",
                "picks": [],
                "n_attempted_personas": 0,
            }
            out_file = SUBMISSIONS_DIR / f"{model_id}_{today_str()}.json"
            out_file.write_text(json.dumps(envelope, indent=2))
            print(f"  [submission] {model_id}: 0 picks (recorded as no_picks_generated)")
            continue

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
                # 2026-05-27 fix: persona_id was assigned at pick generation
                # (line ~491) but stripped on submission write. Result: 0/N of
                # submissions/*.json had persona_id populated → backfill step
                # in ai-tournament-pipeline.yml had nothing to backfill from →
                # model.html drill-down "Performance by persona/strategy"
                # rendered empty and the leaderboard couldn't break out per
                # persona. Add it here so the submission envelope carries the
                # persona attribution all the way to merge_submissions_to_latest.
                "persona_id": p.get("persona_id", ""),
                "strategy_name": p.get("strategy_name", ""),
                "generation_source": p.get("generation_source", "model_api"),
                "api_status": p.get("api_status", "api_success"),
                "rank_eligible": p.get("rank_eligible", True),
                "rank_exclusion_reason": p.get("rank_exclusion_reason", ""),
                "data_integrity_flag": p.get("data_integrity_flag", ""),
                "current_price": p.get("current_price", p.get("entry_price", 0)),
                "unrealized_pnl_pct": p.get("unrealized_pnl_pct", 0.0),
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

    models = config.get("models", {})
    tasks = build_prompt_tasks(models, universe)
    all_picks, model_status_counts, coverage_fallback_count = (
        collect_api_and_coverage_picks(tasks, config)
    )

    # If no API calls or coverage rows produced anything, use the legacy local fallback.
    if not all_picks:
        print("[populate] No API or coverage picks generated — using fallback")
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

    # Inject persona rationale into each pick
    def _fmt_conf(v):
        """Safely format confidence as percentage string."""
        if isinstance(v, str):
            return {"HIGH": "80%", "MEDIUM": "50%", "LOW": "20%"}.get(v, v)
        try:
            return f"{float(v):.0%}"
        except (TypeError, ValueError):
            return str(v)

    try:
        sys.path.insert(0, str(REPO_ROOT))
        from tools.ai_tournament.persona_registry import build_persona_rationale
        for p in all_picks:
            pid = p.get("persona_id", "")
            if pid and not p.get("reason"):
                p["reason"] = build_persona_rationale(
                    pid, p.get("symbol", ""),
                    p.get("direction", "LONG"),
                    p.get("confidence", 0.5)
                )
            if not p.get("reason") and p.get("thesis"):
                p["reason"] = f"Entry thesis: {p['thesis'][:200]} | Strategy: {p.get('strategy_name', p.get('persona_id', 'N/A'))} | Confidence: {_fmt_conf(p.get('confidence', 0.5))}"
    except Exception as e:
        print(f"[populate] Reason injection failed (non-fatal): {e}")
        for p in all_picks:
            if not p.get("reason") and p.get("thesis"):
                try:
                    p["reason"] = f"Thesis: {str(p['thesis'])[:200]} | Conf: {_fmt_conf(p.get('confidence', 0.5))}"
                except Exception:
                    p["reason"] = str(p.get("thesis", ""))[:200]

    # ── Position sizing: Kelly criterion + risk budgeting ──
    try:
        # Look up historical persona performance from DB for Kelly calc
        persona_stats = {}
        try:
            import pymysql
            conn = pymysql.connect(host=os.environ.get("DB_HOST_STOCKS", "mysql.50webs.com"),
                                   user=os.environ.get("DB_USER_STOCKS", "ejaguiar1_stocks"),
                                   password=os.environ.get("DB_PASS_STOCKS", "") or os.environ.get("MYSQL_PASSWORD", ""),
                                   database=os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks"),
                                   port=3306, connect_timeout=5)
            cur = conn.cursor()
            cur.execute("SELECT persona_id, ROUND(AVG(CASE WHEN status='WIN' THEN 1.0 ELSE 0 END), 4) as wr, ROUND(AVG(pnl_pct), 4) as avg_pnl, COUNT(*) as n FROM tournament_picks WHERE status IN ('WIN','LOSS') AND persona_id != '' GROUP BY persona_id")
            for row in cur.fetchall():
                persona_stats[row[0]] = {'wr': float(row[1]), 'avg_pnl': float(row[2] or 0), 'n': int(row[3])}
            conn.close()
        except Exception:
            pass  # Continue without DB stats

        for p in all_picks:
            pid = p.get("persona_id", "")
            conf = p.get("confidence", 0.5)
            if isinstance(conf, str):
                conf = {"HIGH": 0.8, "MEDIUM": 0.5, "LOW": 0.2}.get(conf, 0.5)
            else:
                conf = float(conf)

            # Kelly formula: f* = (p*b - q) / b where p=win prob, q=loss prob, b=RR
            entry = float(p.get("entry_price", 1))
            tp = float(p.get("take_profit", entry * 1.1))
            sl = float(p.get("stop_loss", entry * 0.95))
            rr = abs((tp - entry) / (entry - sl)) if abs(entry - sl) > 0 else 1.0

            # Use historical WR if available, else confidence as win prob
            if pid in persona_stats:
                p_win = persona_stats[pid]['wr']
            else:
                p_win = conf

            q_loss = 1.0 - p_win
            kelly = (p_win * rr - q_loss) / rr if rr > 0 else 0
            # Cap at 25% (quarter-Kelly for safety)
            kelly = max(0, min(0.25, kelly * 0.25))

            # Risk budget: % of portfolio at risk per trade
            # Portfolio manager rules: equal-weight until n>=20, then fractional Kelly
            # Max 1.5% per position, max 2% total risk, max 10 concurrent positions
            persona_n = persona_stats.get(pid, {}).get('n', 0)
            if persona_n < 20:
                risk_per_trade = 1.5  # Equal-weight baseline: 1.5% per position
            else:
                risk_per_trade = kelly * 100  # Fractional Kelly at n>=20
            risk_per_trade = min(risk_per_trade, 1.5)  # Hard cap at 1.5% per position

            p["kelly_pct"] = round(kelly * 100, 1)
            p["risk_budget_pct"] = round(risk_per_trade, 1)
            p["reward_risk_ratio"] = round(rr, 2)
            p["persona_n_resolved"] = persona_n
            p["position_size_suggestion"] = f"Kelly={kelly*100:.1f}% | Risk={risk_per_trade:.1f}% | RR={rr:.1f} | N={persona_n}"
    except Exception as e:
        print(f"[populate] Position sizing failed (non-fatal): {e}")

    # ── Kill gate: auto-zero KILLED personas ──
    try:
        kill_path = REPO_ROOT / "audit_dashboard" / "data" / "research" / "kill_gate_report.json"
        if kill_path.exists():
            kill_data = json.loads(kill_path.read_text())
            blocked = set(kill_data.get("blocked_personas", []))
            warned = set(kill_data.get("warned_personas", []))
            blocked_ac = set(kill_data.get("blocked_asset_classes", []))
            warned_ac = set(kill_data.get("warned_asset_classes", []))
            before = len(all_picks)
            all_picks = [p for p in all_picks 
                         if p.get("persona_id", "") not in blocked 
                         and p.get("asset_class", "") not in blocked_ac]
            killed_count = before - len(all_picks)
            if killed_count:
                print(f"[populate] Kill gate: removed {killed_count} picks from blocked personas/classes: blocked_personas={sorted(blocked)} blocked_classes={sorted(blocked_ac)}")
            if warned_ac:
                ac_warn_picks = [p for p in all_picks if p.get("asset_class", "") in warned_ac]
                print(f"[populate] Kill gate: {len(ac_warn_picks)} picks from WARN asset classes: {sorted(warned_ac)}")
            warn_picks = [p for p in all_picks if p.get("persona_id", "") in warned]
            if warn_picks:
                print(f"[populate] Kill gate: {len(warn_picks)} picks from WARN personas (monitoring): {sorted(warned)}")
                for p in warn_picks:
                    p["data_integrity_flag"] = "KILL_GATE_WARNED"
    except Exception as e:
        print(f"[populate] Kill gate check skipped (non-fatal): {e}")

    # Write output
    out_path = pick_out_path()
    out_path.write_text(json.dumps(all_picks, indent=2))
    print(f"[populate] Wrote {len(all_picks)} picks to {out_path.name}")

    # Write individual model submission files for the price tracker
    write_submissions(all_picks)  # function now auto-discovers the full configured set

    # ── Model attempt log: machine-readable coverage report for every configured model
    emit_model_attempt_log(models, model_status_counts, all_picks)

    # ── Visible model participation summary (human-readable dashboard)
    api_generated_count = sum(1 for p in all_picks if p.get("generation_source") != "coverage_fallback" and p.get("model_id") not in ("alpha_engine", "tournament_synthetic"))
    local_fallback_count = sum(1 for p in all_picks if p.get("model_id") in ("alpha_engine", "tournament_synthetic"))

    from collections import Counter as _Counter
    _model_pick_counts = _Counter(p.get("model_id") for p in all_picks)
    _models_with_picks = len([m for m, c in _model_pick_counts.items() if c > 0])
    _total_configured = len(models)

    print(f"[populate] Assignment statuses: {model_status_counts}")
    print(
        f"[populate] DONE. Models configured={_total_configured} | "
        f"Active API models={_models_with_picks} | "
        f"API picks={api_generated_count} | "
        f"Coverage fallback={coverage_fallback_count} | "
        f"Local fallback={local_fallback_count} | "
        f"Total picks={len(all_picks)}"
    )
    if _models_with_picks < _total_configured:
        missing = [mid for mid in models if mid not in _model_pick_counts or _model_pick_counts[mid] == 0]
        print(f"[populate] ⚠️ {_total_configured - _models_with_picks} model(s) produced zero picks: {', '.join(sorted(missing))}")
    print(f"[populate] Per-model breakdown: {', '.join(f'{k}={v}' for k, v in _model_pick_counts.most_common())}")


def emit_model_attempt_log(
    models: dict,
    model_status_counts: dict[str, int],
    all_picks: list[dict],
) -> None:
    """Write a machine-readable manifest of every configured model's status.

    This file is committed by ai-tournament-pipeline.yml so operators can
    see at a glance which models succeeded, failed, or were missing keys —
    without having to dig through runner logs.

    Output: data/ai_tournament/model_attempt_log.json
    """
    picks_by_model: dict[str, int] = {}
    api_picks_by_model: dict[str, int] = {}
    coverage_picks_by_model: dict[str, int] = {}
    for p in all_picks:
        mid = p.get("model_id", "unknown")
        picks_by_model[mid] = picks_by_model.get(mid, 0) + 1
        if p.get("generation_source") == "coverage_fallback":
            coverage_picks_by_model[mid] = coverage_picks_by_model.get(mid, 0) + 1
        else:
            api_picks_by_model[mid] = api_picks_by_model.get(mid, 0) + 1

    model_details = []
    for model_id, model_cfg in models.items():
        n_picks = picks_by_model.get(model_id, 0)
        api_picks = api_picks_by_model.get(model_id, 0)
        coverage_picks = coverage_picks_by_model.get(model_id, 0)
        has_api_key = bool(os.environ.get(model_cfg.get("api_key_env", ""), ""))

        if api_picks > 0 and coverage_picks > 0:
            status = "partial_success_with_coverage_fallback"
        elif api_picks > 0:
            status = "success"
        elif coverage_picks > 0 and has_api_key:
            status = "api_failed_or_empty_coverage_fallback"
        elif coverage_picks > 0:
            status = "missing_api_key_coverage_fallback"
        elif has_api_key:
            status = "api_failed_no_picks"
        else:
            status = "missing_api_key"

        model_details.append({
            "model_id": model_id,
            "provider": model_cfg.get("provider", "Unknown"),
            "model_name": model_cfg.get("model_name", model_id),
            "status": status,
            "picks_generated": n_picks,
            "api_picks": api_picks,
            "coverage_fallback_picks": coverage_picks,
            "has_api_key": has_api_key,
            "assignment_count": sum(len(v) for v in model_cfg.get("assignments", {}).values()),
        })

    # Also include the alpha_engine model that shows up in picks but isn't in config
    for extra_mid in set(picks_by_model.keys()) - set(models.keys()):
        model_details.append({
            "model_id": extra_mid,
            "provider": "fallback",
            "model_name": extra_mid,
            "status": "fallback",
            "picks_generated": picks_by_model[extra_mid],
            "api_picks": api_picks_by_model.get(extra_mid, 0),
            "coverage_fallback_picks": coverage_picks_by_model.get(extra_mid, 0),
            "has_api_key": False,
            "assignment_count": 0,
        })

    log_entry = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_configured": len(models),
        "assignment_status_counts": model_status_counts,
        "models_with_keys": sum(1 for d in model_details if d["has_api_key"]),
        "models_succeeded": sum(1 for d in model_details if d["api_picks"] > 0),
        "total_picks": len(all_picks),
        "models": sorted(model_details, key=lambda m: (-m["picks_generated"], m["model_id"])),
    }

    LOG_PATH = PICKS_DIR / "model_attempt_log.json"
    LOG_PATH.write_text(json.dumps(log_entry, indent=2))
    print(f"[attempt_log] Wrote {len(model_details)} model entries → {LOG_PATH.name} (succeeded={log_entry['models_succeeded']}/{log_entry['total_configured']})")


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
