"""TradingAgents-style stock-pick emitter (opt-in producer).

Inspired by tauricresearch/tradingagents (Apache-2.0). Rather than importing
their LangGraph framework wholesale (which would add a heavy dependency and
duplicate modules already in alpha_engine/), this emitter captures the core
multi-role-analyst → bull/bear → trader → risk-manager → portfolio-manager
synthesis in a single consolidated prompt and emits picks in the format the
audit dashboard already consumes.

Output: ``alpha_engine/data/tradingagents_picks.json`` — registered as the
``tradingagents`` source in ``audit_trail.dashboard_generator.JSON_PICK_SOURCES``.
When the env flag is OFF (default), the file is never written and the source
appears with 0 picks — graceful no-op.

Activation:
    TRADINGAGENTS_EMITTER_ENABLED=1
    DEEPSEEK_API_KEY=<key>            # default model (or any provider name+key)
    python -m alpha_engine.tradingagents_emitter

Provider selection follows the registry in ``alpha_engine.adversarial_debate``
(stdlib-only HTTP, OpenAI-compatible chat completions). Pick a provider via
``TRADINGAGENTS_PROVIDER=<name>`` (default ``deepseek``).

Strategy attribution: ``source_system='tradingagents'``,
``strategy='tradingagents_consensus'``. Picks surface under active_picks on
``/audit`` once the dashboard generator runs after this emitter writes.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from alpha_engine.adversarial_debate import (
    DebateError,
    _extract_content,
    _parse_thesis_json,
    _post_chat,
)

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WATCHLIST = ROOT / "alpha_engine" / "data" / "tradingagents_watchlist.json"
DEFAULT_OUTPUT = ROOT / "alpha_engine" / "data" / "tradingagents_picks.json"

ENV_FLAG = "TRADINGAGENTS_EMITTER_ENABLED"
ENV_PROVIDER = "TRADINGAGENTS_PROVIDER"
ENV_MODEL = "TRADINGAGENTS_MODEL"
ENV_DEBUG_RAW = "TRADINGAGENTS_DEBUG_RAW"

# Output-hygiene shadow flag (default OFF). When ON, the per-ticker LLM call
# uses the layered multi-asset prompt from alpha_engine.prompts instead of the
# hardcoded equity SYSTEM_PROMPT below. This only changes the *framing* of the
# pick prose (a CRYPTO/FOREX pick stops getting equity-desk wording) — it does
# NOT change the JSON schema, the parser, gate logic, or predictive power.
# Not an edge claim. Default OFF so production behavior is unchanged until the
# operator explicitly flips it.
ENV_MULTIASSET_PROMPT = "TRADINGAGENTS_MULTIASSET_PROMPT"

DEFAULT_PROVIDER = os.environ.get(ENV_PROVIDER, "deepseek").lower()
DEFAULT_MODEL = os.environ.get(ENV_MODEL) or None  # None = provider's default


# ────────────────────────────────────────────────────────────────────────
# Prompt
# ────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a multi-agent equity research desk that mirrors a real-world hedge-fund decision committee. For the single ticker the user submits, internally play every role below in order, then output ONE consensus decision.

Roles to consider (each contributes a perspective; you do NOT print intermediate reasoning):
  1. Fundamentals analyst — earnings trend, valuation, balance-sheet quality.
  2. Technical analyst — trend, RSI/MACD, support/resistance, volume profile.
  3. News analyst — recent material catalysts, guidance changes, regulatory.
  4. Sentiment analyst — institutional flow, social/options sentiment, short interest.
  5. Bull researcher — strongest case for going long.
  6. Bear researcher — strongest case for staying flat or shorting.
  7. Trader — sizes the trade given conflict between bull/bear.
  8. Risk manager — reviews position sizing, stop placement, single-name concentration.
  9. Portfolio manager — final BUY / HOLD / SELL decision with confidence.

Produce ONLY a JSON object with these exact keys (no markdown fences, no prose):
{
  "action": "BUY" | "HOLD" | "SELL",
  "confidence": <float in [0,1]>,
  "thesis": "<WRITE 2 real sentences specific to THIS ticker's fundamentals/technicals — DO NOT copy example text>",
  "rationale": "<WRITE 4 real sentences synthesizing bull vs bear case for THIS ticker — DO NOT copy example text>",
  "time_horizon_days": <int between 5 and 90>,
  "target_pct": <float, expected upside in % from current price; positive for BUY, negative for SELL>,
  "stop_pct": <float, max acceptable loss in %, always positive>,
  "key_risks": ["<short>", "..."]
}

Rules:
- BUY only if multi-role agreement is strong; default to HOLD on conflict.
- target_pct must be ≥ stop_pct × 1.5 (positive risk-reward).
- For HOLD or SELL, set target_pct sign to match action (HOLD: 0).
- confidence ≥ 0.65 indicates trade-worthy conviction; below that, prefer HOLD.
- thesis and rationale MUST be ticker-specific real analysis, never template text.
- confidence, target_pct, and stop_pct MUST reflect THIS ticker's specific risk profile. Do NOT use round defaults (e.g. 0.80, 10.0, 5.0). If your analysis produces the same numbers as a prior ticker, reconsider — identical metrics across different tickers indicate insufficient per-ticker analysis."""


def _user_prompt(ticker: str, asset_class: str, today: str) -> str:
    return (
        f"Ticker: {ticker}\n"
        f"Asset class: {asset_class}\n"
        f"As-of date: {today}\n"
        "Apply your decision committee and respond with the consensus JSON only."
    )


def _multiasset_enabled() -> bool:
    """True when the multi-asset-prompt shadow flag is ON. Default OFF."""
    return os.environ.get(ENV_MULTIASSET_PROMPT, "0").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _resolve_system_prompt(asset_class: str) -> str:
    """Return the system prompt for this ticker's asset class.

    With the shadow flag OFF (default), returns the unchanged hardcoded
    equity SYSTEM_PROMPT — production behavior is identical to before this
    module existed.

    With the flag ON, composes a per-asset-class prompt via
    ``alpha_engine.prompts.build_system_prompt``. FAIL-SAFE: any error while
    building the multi-asset prompt (missing prompt asset, import failure)
    falls back to the hardcoded SYSTEM_PROMPT so the emitter never crashes
    and never silently produces an empty prompt.
    """
    if not _multiasset_enabled():
        return SYSTEM_PROMPT
    try:
        from alpha_engine.prompts import build_system_prompt
        prompt = build_system_prompt(asset_class)
        if not prompt or not prompt.strip():
            raise ValueError("build_system_prompt returned empty prompt")
        return prompt
    except Exception as e:  # noqa: BLE001 — fail-safe to the known-good prompt
        logger.warning(
            "[tradingagents] multi-asset prompt build failed for asset_class=%r "
            "(%s: %s); falling back to hardcoded equity SYSTEM_PROMPT.",
            asset_class, type(e).__name__, e,
        )
        return SYSTEM_PROMPT


# ────────────────────────────────────────────────────────────────────────
# Watchlist
# ────────────────────────────────────────────────────────────────────────

def _load_watchlist(path: Path) -> tuple[list[dict], dict]:
    """Returns (tickers_list, meta_dict)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"watchlist not found: {path}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"watchlist is not valid JSON: {e}")
    tickers = data.get("tickers") or []
    meta = {k: v for k, v in data.items() if k != "tickers"}
    if not isinstance(tickers, list):
        raise SystemExit("watchlist 'tickers' must be a list")
    return tickers, meta


# ────────────────────────────────────────────────────────────────────────
# Placeholder detection
# ────────────────────────────────────────────────────────────────────────

# LLMs occasionally echo the example/template values from the prompt verbatim.
# Any thesis or rationale that matches one of these strings (case-insensitive,
# after stripping) is treated as a parsing failure and the pick is dropped.
# Add new patterns here when new placeholder variants are observed in prod.
_PLACEHOLDER_PATTERNS: frozenset[str] = frozenset({
    "thesis text",
    "rationale text",
    "thesis here",
    "rationale here",
    "your thesis here",
    "your rationale here",
    "insert thesis",
    "insert rationale",
    "consensus view",
    "<thesis>",
    "<rationale>",
    "n/a",
    "",
})


def _is_placeholder(text: str) -> bool:
    """Return True if `text` looks like a copied template placeholder."""
    return text.strip().lower() in _PLACEHOLDER_PATTERNS


# ────────────────────────────────────────────────────────────────────────
# Pick assembly
# ────────────────────────────────────────────────────────────────────────

def _assemble_pick(decision: dict, ticker: str, asset_class: str, *, ts_iso: str) -> dict | None:
    """Convert an LLM JSON decision into a dashboard-ready pick dict.

    Returns None if the decision is malformed or below confidence floor.
    Confidence floor is taken from env or default 0.65.
    """
    if not isinstance(decision, dict):
        return None
    action = str(decision.get("action") or "").upper().strip()
    if action not in ("BUY", "SELL"):
        # HOLD/UNKNOWN do not become picks.
        return None

    try:
        conf = float(decision.get("confidence") or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    floor = float(os.environ.get("TRADINGAGENTS_CONFIDENCE_FLOOR", "0.65"))
    if conf < floor:
        return None

    try:
        target_pct = float(decision.get("target_pct") or 0.0)
        stop_pct = float(decision.get("stop_pct") or 0.0)
    except (TypeError, ValueError):
        return None
    # Risk-reward sanity. For SELL, target_pct is negative.
    if stop_pct <= 0:
        return None
    if action == "BUY" and target_pct < stop_pct * 1.0:
        return None
    if action == "SELL" and abs(target_pct) < stop_pct * 1.0:
        return None

    # Reject picks where thesis or rationale is a copied template placeholder.
    thesis_raw = str(decision.get("thesis") or "")
    rationale_raw = str(decision.get("rationale") or "")
    if _is_placeholder(thesis_raw) or _is_placeholder(rationale_raw):
        logger.warning(
            "[tradingagents] %s rejected — placeholder thesis/rationale detected "
            "(thesis=%r rationale=%r). Prompt may not be activating per-ticker analysis.",
            ticker, thesis_raw[:60], rationale_raw[:60],
        )
        return None

    direction = "LONG" if action == "BUY" else "SHORT"
    horizon = decision.get("time_horizon_days") or 21
    try:
        horizon_int = max(1, min(365, int(horizon)))
    except (TypeError, ValueError):
        horizon_int = 21

    # Entry price comes from the live picker downstream; we leave a sentinel
    # the resolver fills (production_scanner/yfinance lookup). Setting
    # entry_price=None forces the gate's `_is_valid_pick` filter to drop the
    # pick if no live price is available — the right behavior, not a guess.
    pick = {
        "id": f"tradingagents::{ticker}::{ts_iso[:16].replace('-', '').replace(':', '')}",
        "strategy": "tradingagents_consensus",
        "source_system": "tradingagents",
        "symbol": ticker,
        "category": asset_class.lower() if asset_class else "stock",
        "asset_class": asset_class or "EQUITY",
        "signal_type": action,
        "direction": direction,
        "entry_price": None,
        "take_profit_pct": round(target_pct, 4),
        "stop_loss_pct": round(stop_pct, 4),
        "score": int(round(min(100, max(0, conf * 100)))),
        "confidence": round(conf, 4),
        "thesis": str(decision.get("thesis") or "")[:400],
        "rationale": str(decision.get("rationale") or "")[:800],
        "time_horizon_days": horizon_int,
        "key_risks": [str(r)[:120] for r in (decision.get("key_risks") or [])][:5],
        "timestamp": ts_iso,
        "status": "OPEN",
        "source_tier": "EXPERIMENTAL",
        "tradingagents_version": "v1-consolidated-prompt",
    }
    return pick


# ────────────────────────────────────────────────────────────────────────
# Per-ticker call
# ────────────────────────────────────────────────────────────────────────

def call_tradingagents(ticker: str, asset_class: str, *, today: str | None = None,
                       provider: str | None = None, model: str | None = None,
                       http_post=None) -> dict:
    """Call the configured LLM with the consolidated TradingAgents prompt.

    Returns the parsed decision dict (with at minimum `action` and
    `confidence`). Raises DebateError on transport / parsing failure so the
    caller can decide whether to skip the ticker or abort.
    """
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    raw = _post_chat(
        provider or DEFAULT_PROVIDER,
        _resolve_system_prompt(asset_class),
        _user_prompt(ticker, asset_class, today),
        model=model or DEFAULT_MODEL,
        max_tokens=600,
        http_post=http_post,
    )
    text = _extract_content(raw)
    if os.environ.get(ENV_DEBUG_RAW, "0").strip().lower() in ("1", "true"):
        logger.debug("[tradingagents] raw LLM response for %s: %r", ticker, text[:600])
    decision = _parse_decision_json(text)
    if decision is None:
        raise DebateError(f"could not parse decision JSON for {ticker}: {text[:200]!r}")
    return decision


def _parse_decision_json(text: str) -> dict | None:
    """Parse the model's JSON decision, tolerating markdown fences and prose."""
    # Reuse the tolerant parser's brace-scan, but keep the full object (not
    # just thesis/confidence).
    cand = text.strip().strip("`")
    # Try direct parse first.
    try:
        obj = json.loads(cand)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    # Find the outermost {...} blob.
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                blob = text[start:i + 1]
                try:
                    obj = json.loads(blob)
                    if isinstance(obj, dict):
                        return obj
                except json.JSONDecodeError:
                    start = -1
                    continue
    return None


# ────────────────────────────────────────────────────────────────────────
# Top-level emit
# ────────────────────────────────────────────────────────────────────────

def is_enabled() -> bool:
    return os.environ.get(ENV_FLAG, "0").strip().lower() in ("1", "true", "yes", "on")


def emit_picks(*, watchlist_path: Path | None = None, output_path: Path | None = None,
               provider: str | None = None, model: str | None = None,
               http_post=None) -> dict[str, Any]:
    """Read watchlist, call LLM per ticker, write picks JSON, return summary.

    Hard no-op when the env flag is OFF — returns a summary with reason.
    """
    if not is_enabled():
        return {"emitted": 0, "skipped": 0, "errors": 0, "reason": f"{ENV_FLAG} not set"}

    watchlist_path = watchlist_path or DEFAULT_WATCHLIST
    output_path = output_path or DEFAULT_OUTPUT
    tickers, meta = _load_watchlist(watchlist_path)

    picks: list[dict] = []
    skipped: list[str] = []
    errors: list[dict] = []

    ts_iso = datetime.now(timezone.utc).isoformat()
    today = ts_iso[:10]

    for entry in tickers:
        if not isinstance(entry, dict):
            continue
        ticker = str(entry.get("symbol") or "").strip().upper()
        if not ticker:
            continue
        asset_class = str(entry.get("asset_class") or "EQUITY").upper()
        try:
            decision = call_tradingagents(
                ticker, asset_class, today=today,
                provider=provider, model=model, http_post=http_post,
            )
        except DebateError as e:
            errors.append({"ticker": ticker, "error": str(e)})
            logger.warning("[tradingagents] %s failed: %s", ticker, e)
            continue
        except Exception as e:  # noqa: BLE001 — emitter must never crash
            errors.append({"ticker": ticker, "error": f"unexpected: {e!r}"})
            logger.exception("[tradingagents] %s unexpected failure", ticker)
            continue

        pick = _assemble_pick(decision, ticker, asset_class, ts_iso=ts_iso)
        if pick is None:
            skipped.append(ticker)
            continue
        picks.append(pick)

    # Batch-level identical-metrics detection. If 2+ picks share the same
    # (confidence, take_profit_pct, stop_loss_pct) tuple, the LLM likely echoed
    # a default rather than analyzing each ticker independently.
    if len(picks) >= 2:
        from collections import Counter
        metric_tuples = [
            (round(p["confidence"], 2), round(p["take_profit_pct"], 1), round(p["stop_loss_pct"], 1))
            for p in picks
        ]
        dupe_tuples = {t: n for t, n in Counter(metric_tuples).items() if n > 1}
        if dupe_tuples:
            logger.warning(
                "[tradingagents] identical (conf, tp, sl) metrics across %d picks: %s — "
                "LLM may not be differentiating tickers. Set %s=1 to log raw responses.",
                sum(dupe_tuples.values()), dupe_tuples, ENV_DEBUG_RAW,
            )

    payload = {
        "generated_at": ts_iso,
        "source_system": "tradingagents",
        "version": "v1-consolidated-prompt",
        "watchlist_size": len(tickers),
        "emitted": len(picks),
        "skipped": skipped,
        "errors": errors,
        "active_picks": picks,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="alpha_engine.tradingagents_emitter")
    parser.add_argument("--watchlist", type=Path, default=DEFAULT_WATCHLIST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--provider", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--dry-run", action="store_true",
                        help="parse watchlist + check env, do not call LLM")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.dry_run:
        tickers, _ = _load_watchlist(args.watchlist)
        print(f"watchlist: {len(tickers)} tickers from {args.watchlist}")
        print(f"flag {ENV_FLAG}: {'ON' if is_enabled() else 'OFF'}")
        print(f"provider: {args.provider or DEFAULT_PROVIDER}")
        print(f"model: {args.model or DEFAULT_MODEL or '(provider default)'}")
        return 0

    if not is_enabled():
        print(f"{ENV_FLAG} is not set; nothing to do (set =1 to enable).", file=sys.stderr)
        return 1

    summary = emit_picks(
        watchlist_path=args.watchlist,
        output_path=args.output,
        provider=args.provider,
        model=args.model,
    )
    print(json.dumps(
        {k: v for k, v in summary.items() if k != "active_picks"},
        indent=2,
    ))
    print(f"wrote {summary['emitted']} picks to {args.output}")
    return 0


__all__ = [
    "ENV_FLAG",
    "ENV_MULTIASSET_PROMPT",
    "DEFAULT_WATCHLIST",
    "DEFAULT_OUTPUT",
    "is_enabled",
    "call_tradingagents",
    "emit_picks",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
