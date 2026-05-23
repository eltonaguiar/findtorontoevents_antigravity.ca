#!/usr/bin/env python3
"""consult_ling_crypto.py — consult inclusionai/ling-2.6-1t (free, via OpenRouter)
for insights on the crypto prediction system.

Loads live active crypto picks, builds a smart-picks vs high-conviction example
block, and sends one honest-context prompt to Ling. Writes the answer to
reports/ling_crypto_consult_2026-05-18.md.

OpenAI-compatible /chat/completions. Zero pip deps (urllib).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACTIVE = os.path.join(REPO, "alpha_engine", "data", "active_picks.json")
OUT = os.path.join(REPO, "reports", "ling_crypto_consult_2026-05-18.md")

MODEL = "inclusionai/ling-2.6-1t"
BASE = "https://openrouter.ai/api/v1"

SYSTEM = (
    "You are a senior quantitative crypto researcher. Blunt, specific, "
    "skeptical. No generic trading-blog advice. If a fact in the context "
    "looks wrong or unverifiable, flag it before building on it. Every "
    "claim names the field/number it rests on."
)


def _f(p: dict, k: str) -> float:
    try:
        return float(p.get(k) or 0)
    except (TypeError, ValueError):
        return 0.0


def _examples() -> str:
    try:
        d = json.load(open(ACTIVE, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "[active_picks.json unavailable]"
    picks = [p for p in (d if isinstance(d, list) else d.values())
             if isinstance(p, dict)]
    crypto = [p for p in picks
              if str(p.get("asset_class", "")).upper() == "CRYPTO"]
    crypto.sort(key=lambda p: -_f(p, "confidence"))
    rows = []
    for p in crypto[:10]:
        rows.append(
            "  %-10s %-5s entry=%s tp=%s sl=%s | conf=%.2f "
            "method_a=%.1f ml_composite=%.1f rr=%.2f | %s / %s" % (
                p.get("symbol", "?"), p.get("direction", "?"),
                p.get("entry_price"), p.get("take_profit"),
                p.get("stop_loss"), _f(p, "confidence"),
                _f(p, "method_a_score"), _f(p, "ml_composite_score"),
                _f(p, "risk_reward"),
                str(p.get("strategy", "?"))[:34],
                p.get("source_system", "?")))
    return "\n".join(rows) if rows else "[no active crypto picks]"


PROMPT = """\
CONTEXT — the findtorontoevents.ca crypto prediction system, verified state
2026-05-18 after an exhaustive leakage-controlled edge hunt:

- CRYPTO asset class: profit factor ~1.25-1.28 net-of-slippage, win rate
  ~44.6%, n~8000 closed trades. Sub-institutional (Tier-2 floor is PF>=1.5).
- 10 straight candidates have been REJECTED by a strict walk-forward
  admissibility gate (eff>=0.30, same sign, >=3/5 windows): every one showed
  in-sample separation that did NOT hold a stable sign out-of-sample.
- The headline CRYPTO "edge" was an artifact: the `ml_enhanced` family is
  ~149 per-symbol curve-fit variants (many with n=1), family PF ~0.63.
- Two ways the system surfaces crypto picks:
  * SMART PICKS  — score-ranked by a composite (method_a_score,
    ml_composite_score, ml_probability) from `smart_picks_engine`.
  * HIGH-CONVICTION — ranked by an HF conviction tier / elite_score /
    self-reported model `confidence`.
- Honest finding so far: `confidence` is NOT a reliable edge proxy on
  CRYPTO (it inverts above ~0.85), and the score fields are frequently 0 or
  unpopulated on live picks.

CURRENT LIVE CRYPTO PICKS (top 10 by confidence — note how sparse the
score fields actually are):
{EXAMPLES}

THE ASK — insights on this crypto prediction system. Answer in markdown:
1. READING THE PICKS — what do these 10 live picks tell you? Anything
   structurally wrong (sources, sparse scores, direction mix, TP/SL geometry)?
2. SMART vs HIGH-CONVICTION — is splitting picks into a score-ranked lane
   and a confidence-ranked lane sound, given confidence is unreliable on
   CRYPTO? How would you rank picks instead?
3. WHY NO EDGE — given 10 harness kills and a curve-fit ml_enhanced sprawl,
   name the 2-3 STRUCTURAL reasons a crypto prediction system like this
   ends up with PF ~1.25 and no admissible edge.
4. CONCRETE FIXES — 3 specific, free-data, implementable changes to the
   crypto pick pipeline. For each: the change, the data, and a falsifiable
   acceptance test (must be walk-forward, same-sign-stability, not just WR).
5. HONEST CALL — is retail crypto directional prediction worth continuing,
   or should this stay a paper research sandbox? Say plainly.

## SELF-AUDIT — name the 2 weakest claims in your own answer and what
evidence would overturn each.

~700-1000 words. Output ONLY the 5 numbered sections + the self-audit.
"""


def main() -> int:
    key = os.environ.get("OPENROUTER", "").strip()
    if not key:
        print("ERROR: OPENROUTER env var not set")
        return 1
    prompt = PROMPT.replace("{EXAMPLES}", _examples())
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
    }).encode()
    req = urllib.request.Request(
        BASE + "/chat/completions", data=body, method="POST",
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            d = json.load(resp)
        txt = d["choices"][0]["message"]["content"] or "[empty response]"
    except Exception as exc:  # noqa: BLE001
        print("ERROR calling %s: %s" % (MODEL, exc))
        return 1
    report = "# Ling 2.6 (1T) — crypto prediction system consult\n\n" \
             "Model: `%s` via OpenRouter. 2026-05-18.\n\n%s\n" % (MODEL, txt)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(report)
    print(report)
    print("\nwritten -> reports/ling_crypto_consult_2026-05-18.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
