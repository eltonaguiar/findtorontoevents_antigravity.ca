#!/usr/bin/env python3
"""no_edge_cloud_consult.py — fan the "no edge" brainstorm to cloud LLMs.

Sends one focused brainstorm prompt to every cloud LLM whose API key is in
the Windows environment, in parallel. Each model's answer is written to its
own file under reports/no_edge_brainstorm/<model>.md. The main thread then
compiles them into NO_EDGE_BRAINSTORM_CLOUD.MD.

All endpoints are OpenAI-compatible /chat/completions. Zero pip deps (urllib).
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import sys
import time
import urllib.request

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "reports", "no_edge_brainstorm")
os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# The brainstorm prompt — the verified honest state of the system.
# ---------------------------------------------------------------------------
SYSTEM = (
    "You are a senior quantitative researcher. You are blunt, specific, and "
    "skeptical. You do NOT give generic trading-blog advice (no 'open a "
    "broker account', no 'use stop losses'). Every suggestion must be "
    "concrete, falsifiable, and implementable by a small quant team. "
    "'No edge / insufficient data / stop spending' is a fully valid answer "
    "and must be stated plainly if it is true — never manufacture a positive "
    "finding to seem useful. If any fact in the CONTEXT looks wrong, stale, "
    "or unverifiable, flag it explicitly BEFORE building on it. Every "
    "empirical claim must name its source inline (a file, a dataset, a "
    "measured number) or be dropped."
)

PROMPT = """\
CONTEXT — a multi-asset signal system (findtorontoevents.ca/audit), verified
state as of 2026-05-17 after a deep forensic audit:

- NO asset class has a real statistical edge. Canonical net-of-slippage,
  deduped, policy-clean profit factors: CRYPTO 1.28, COMMODITY 1.17,
  EQUITY 0.72, FOREX 0.33 — all sub-T2 (T2 = PF>=1.5).
- The CRYPTO "edge" is FAKE: the headline confidence>=0.70 cohort (PF 6.67)
  is 100% the post-hoc winning tail of an `ml_enhanced` strategy-mining
  sprawl — 149 per-symbol curve-fit variants (119 with n=1); the family as a
  whole is PF 0.63. Strip it and non-ml CRYPTO is PF 0.33.
- COMMODITY's apparent edge is ~49% CT=F (cotton) — COT-publication
  look-ahead leakage, falsified.
- EQUITY's classic edges (PEAD, value, earnings-drift) were coded, wired,
  then KILLED by a kill-threshold ratchet that fires on small-n in-sample
  rolling windows.
- The ledger had: 41% duplicate re-emissions, a 100x slippage units bug, a
  resolver that mass-stamped replay SL-hits, mis-tagged asset classes. Those
  are now fixed — the PFs above are post-fix and honest.

THE ASK: given this honest baseline (no edge anywhere), brainstorm how to
actually FIND or BUILD a genuine, defensible statistical edge — per asset
class (CRYPTO, EQUITY, COMMODITY, FOREX, ETF, BOND). Be concrete.

Answer these, in markdown, with headers:
1. ROOT CAUSE — why does a system with this much machinery have zero edge?
   Name the 2-3 structural reasons, not symptoms.
2. PER ASSET CLASS — for each of CRYPTO/EQUITY/COMMODITY/FOREX/ETF/BOND, name
   ONE specific, academically-grounded edge worth pursuing and the exact
   data + acceptance test to validate it. Reject classes where the honest
   answer is "do not trade this".
3. METHODOLOGY — how should edge discovery itself be restructured so the
   system stops manufacturing mining artifacts (like the ml_enhanced sprawl)?
   Be specific about validation: walk-forward, CPCV, White's Reality Check,
   deflated Sharpe, minimum-n.
4. THE 3 HIGHEST-EV MOVES — ranked, concrete, with an acceptance test each.
5. WHAT TO STOP DOING — 3 things this system should kill immediately.
6. SELF-AUDIT — name the 2 weakest claims in your own answer and exactly
   what evidence would overturn each.

Be honest: if the right answer for a class is "this will never have a
retail-accessible edge, stop", say that. ~800-1200 words.

Output ONLY the numbered sections specified above (1-6), in order, with
nothing before the first header and nothing after the last.
"""

# ---------------------------------------------------------------------------
# Cloud endpoints — (label, env-var, base_url, model). OpenAI-compatible.
# ---------------------------------------------------------------------------
ENDPOINTS = [
    ("deepseek", "DEEPSEEK_API_KEY", "https://api.deepseek.com/v1",
     "deepseek-reasoner"),
    ("groq", "GROQ_API_KEY", "https://api.groq.com/openai/v1",
     "llama-3.3-70b-versatile"),
    ("cerebras", "CEREBRAS_API", "https://api.cerebras.ai/v1",
     "llama-3.3-70b"),
    ("xai-grok", "XAI_API_KEY", "https://api.x.ai/v1", "grok-3"),
    ("openrouter", "OPENROUTER", "https://openrouter.ai/api/v1",
     "deepseek/deepseek-chat"),
    ("kimi", "KIMI_API_KEY", "https://api.moonshot.ai/v1",
     "moonshot-v1-32k"),
]


def call(label: str, env: str, base: str, model: str) -> tuple[str, str]:
    key = os.environ.get(env, "").strip()
    if not key:
        return label, "[skipped — no API key in env]"
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": PROMPT},
        ],
        "temperature": 0.4,
    }).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=body, method="POST",
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=240) as resp:
                d = json.load(resp)
            txt = d["choices"][0]["message"]["content"]
            return label, (txt or "[empty response]")
        except Exception as exc:  # noqa: BLE001
            if attempt == 0:
                time.sleep(3)
                continue
            return label, "[ERROR %s: %s]" % (model, exc)
    return label, "[ERROR unreachable]"


def main() -> int:
    print("Consulting %d cloud models in parallel..." % len(ENDPOINTS))
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(ENDPOINTS)) as ex:
        futs = {ex.submit(call, *e): e[0] for e in ENDPOINTS}
        for fut in concurrent.futures.as_completed(futs):
            label, text = fut.result()
            results[label] = text
            path = os.path.join(OUT_DIR, label + ".md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("# %s — no-edge brainstorm\n\n%s\n" % (label, text))
            ok = not text.startswith(("[ERROR", "[skipped", "[empty"))
            print("  %-12s %s (%d chars)" % (
                label, "OK" if ok else text[:60], len(text)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
