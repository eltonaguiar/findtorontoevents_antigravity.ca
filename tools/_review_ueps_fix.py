"""Cross-check UEPS active-gate fix with 3 AIs (DeepSeek + Cerebras Qwen + xAI Grok)."""
from __future__ import annotations

import concurrent.futures as _fut
import json
import os
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "reports" / "feedback"
OUT.mkdir(parents=True, exist_ok=True)


PROVIDERS = [
    {
        "name": "deepseek-ueps",
        "url": "https://api.deepseek.com/v1/chat/completions",
        "model": "deepseek-chat",
        "key_env": ["DEEPSEEK_API_KEY", "DEEPSEEK_API"],
    },
    {
        "name": "cerebras-qwen-ueps",
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "model": "qwen-3-235b-a22b-instruct-2507",
        "key_env": ["CEREBRAS_API_KEY", "CEREBRAS_API"],
    },
    {
        "name": "xai-grok-ueps",
        "url": "https://api.x.ai/v1/chat/completions",
        "model": "grok-3",
        "key_env": ["XAI_API_KEY", "X_AI_KEY", "GROK_SUPER"],
    },
]

PROMPT = """You are reviewing a hedge-fund alpha pipeline's active-picks gate. Empirical state:

REPO: findtorontoevents_antigravity.ca
GATE: audit_trail/quality_gates.py:passes_active_gate

CONTEXT:
- 30 UEPS (Universal Equity Pick Signal) picks in picks.active_raw with TF=POSITION (3y+ value horizon, magic_formula x piotroski x acquirers)
- 0 of 30 reach picks.active (post-gate)
- UEPS strategy: long-term value, fundamental ranking, NO closed history yet (chicken-and-egg: no closed -> no fwd_wr -> blocked from going live)

EMPIRICAL REJECTION BREAKDOWN (instrumented passes_active_gate against each):
- 19/30 (63%): "non-crypto raw score below active-display floor" (score < 55 floor; UEPS scoring naturally low: META=19, QCOM=52, V=45, MA=50, PYPL=51 ... only ADBE=56 passes)
- 6/30  (20%): BLOCKED_SYMBOLS data-quality blacklist: ADBE, HD, CRM, MSFT, TSLA, NVDA. These were blocked for short-term feed/redenomination/short-term-strategy issues; UEPS is 3y+ horizon.
- 4/30  (13%): elite_grade=D hard-block (IBM, AVGO, BMY, BA). elite_grade is calibrated for short-term momentum quality.
- 1/30  (3%):  status=SL_HIT (GOOGL — already closed, leaked into active_raw — likely separate resolver freshness bug)
- 0/30  (0%):  trust_score < 3 (UEPS picks have trust=3 which passes; ACTIVE_NON_CRYPTO_MIN_TRUST_SCORE=3 strict-less-than)
- 0/30  (0%):  forward_wr floor (only triggers when edge_trades >= 20; UEPS has 0)

CRITICAL CONSTRAINTS:
- CLAUDE.md Wire-Up Rule: every gate-change must be opt-in OR have explicit production caller
- 14-day shadow rule: any gate/scoring change ships default-OFF behind env flag for >=14 days
- Each PR ships small (1-3 files) with tests + per-PR doc
- Score floor 55, BLOCKED_SYMBOLS, and elite_grade D filters all serve real purposes for short-term strategies — must NOT degrade them

PROPOSED FIX OPTIONS (rate viability + risk):
A. Add "ueps" to _NC_SCORE_EXEMPT_SOURCES (existing pattern from kimi_riseoftheclaw, multi_asset_copytrader). Bypasses the 55 floor for UEPS only.
B. Long-horizon source bypass: if pick.trade_timeframe == "POSITION" AND source_system == "ueps", skip BLOCKED_SYMBOLS + elite_grade D + score floor. Behind env flag UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED (default-OFF, 14d shadow).
C. Lower the score floor to 40 globally for trade_timeframe=POSITION (broadest impact, riskier).
D. Carve out a separate "long_term_picks" panel on /audit that does not pass through passes_active_gate at all (UI-level fix, no gate change).
E. Defer entirely until UEPS has 20+ closed picks; meanwhile show count badge on /audit.

QUESTION: Reply <300 words covering:
1. RECOMMENDED OPTION (single letter + 1-sentence justification)
2. WHAT TO DROP (any of A-E that you'd reject as wrong-shape)
3. SAFETY: what's the worst-case if your pick goes wrong, and what canary metric tells us within 14d?
4. UNIT TESTS to write (1-3 tests max)
5. ROLLBACK: 1-line env-flag flip OR PR revert?

Be brutally honest. Cite option letters. No padding."""


def _resolve_key(env_list):
    for env in env_list:
        v = os.environ.get(env)
        if v and v.strip():
            return v.strip()
    return None


def call_provider(p):
    key = _resolve_key(p["key_env"])
    if not key:
        return p["name"], "ERROR: no key"
    body = {
        "model": p["model"],
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": 700,
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        p["url"],
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (ueps-fix-reviewer/1.0)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            d = json.loads(resp.read().decode("utf-8", errors="replace"))
        msg = d["choices"][0]["message"]
        return p["name"], (msg.get("content") or msg.get("reasoning_content") or "")
    except Exception as e:
        return p["name"], f"ERROR: {e!r}"


def main():
    with _fut.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(call_provider, p) for p in PROVIDERS]
        results = [f.result(timeout=180) for f in futures]
    for name, content in results:
        out = OUT / f"{name}.md"
        out.write_text(content, encoding="utf-8")
        is_err = content.startswith("ERROR")
        try:
            print(f"{name}: {'ERROR' if is_err else f'OK ({len(content)} chars)'}")
        except Exception:
            pass


if __name__ == "__main__":
    main()
