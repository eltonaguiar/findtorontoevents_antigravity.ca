"""Multi-asset prompt builder for LLM pick emitters.

Composes a layered "Antigravity desk" system prompt from:
  1. ``base_desk.txt``   — generalized multi-asset committee rules + JSON schema.
  2. ``annex_<class>.txt`` — per-asset-class special instructions.
  3. A strict-JSON framing prefix (mirrors ``worker_runner._GEMINI_JSON_PREFIX``).

Scope note: this is an OUTPUT-HYGIENE module. It only changes the *framing*
of LLM pick prose so a CRYPTO/FOREX/COMMODITY pick stops receiving
equity-research-desk wording. It does NOT change the JSON schema, the
parsing path, gate logic, or predictive power. It is not an edge claim.

Reference spec: ``reports/PROMPT_STYLE_SYNTHESIS_AI_TOOLS_2026-05-17.md`` §5, §6, §10.

The consuming emitter (``alpha_engine.tradingagents_emitter``) only uses this
builder when the env flag ``TRADINGAGENTS_MULTIASSET_PROMPT`` is ON; with the
flag OFF (default) the existing hardcoded equity prompt is unchanged.
"""
from __future__ import annotations

from pathlib import Path

_PROMPT_DIR = Path(__file__).resolve().parent

# Strict-JSON framing — same intent as tools/swarm/worker_runner._GEMINI_JSON_PREFIX.
STRICT_JSON_PREFIX = (
    "STRICT MODE: respond with VALID JSON ONLY. "
    "No prose, no markdown, no code fences, no explanation before or after. "
    "First character of your response MUST be '{'. "
    "Last character MUST be '}'.\n\n"
)

# Asset-class -> annex filename. Unknown classes fall back to equity (the
# historical default in tradingagents_emitter) so behavior is never worse
# than today's single-prompt baseline.
_ANNEX_BY_CLASS: dict[str, str] = {
    "CRYPTO": "annex_crypto.txt",
    "EQUITY": "annex_equity.txt",
    "STOCK": "annex_equity.txt",
    "FOREX": "annex_forex.txt",
    "FX": "annex_forex.txt",
    "COMMODITY": "annex_commodity.txt",
    "FUTURES": "annex_futures.txt",
    "ETF": "annex_etf.txt",
    "BOND": "annex_bond.txt",
}

_DEFAULT_CLASS = "EQUITY"


def _read(name: str) -> str:
    return (_PROMPT_DIR / name).read_text(encoding="utf-8").strip()


def supported_asset_classes() -> tuple[str, ...]:
    """Asset-class keys with a dedicated annex (canonical names only)."""
    return ("CRYPTO", "EQUITY", "FOREX", "COMMODITY", "FUTURES", "ETF", "BOND")


def build_system_prompt(asset_class: str | None) -> str:
    """Compose the strict-JSON multi-asset system prompt for ``asset_class``.

    Layers: STRICT_JSON_PREFIX + base desk rules + the matching per-class
    annex. Unknown / empty asset classes fall back to the EQUITY annex.

    Raises FileNotFoundError / OSError if the prompt assets are missing — the
    caller (tradingagents_emitter) catches this and falls back to its existing
    hardcoded SYSTEM_PROMPT, so a packaging error never breaks the emitter.
    """
    key = (asset_class or "").strip().upper()
    annex_file = _ANNEX_BY_CLASS.get(key, _ANNEX_BY_CLASS[_DEFAULT_CLASS])
    base = _read("base_desk.txt")
    annex = _read(annex_file)
    return f"{STRICT_JSON_PREFIX}{base}\n\n{annex}"


__all__ = [
    "STRICT_JSON_PREFIX",
    "build_system_prompt",
    "supported_asset_classes",
]
