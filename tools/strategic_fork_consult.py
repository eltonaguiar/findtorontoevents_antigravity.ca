#!/usr/bin/env python3
"""strategic_fork_consult.py — fan the post-edge-hunt strategic fork to cloud LLMs.

After 7 straight edge_stability_harness kills (EDGE_HUNT_CONCLUSION_2026-05-18),
the question is no longer "find edge in the ledger" — it is "given no edge,
how should the program proceed structurally". This is a NEW question, not the
convergence trap. Sends one prompt to every cloud LLM with an API key in env,
in parallel; writes each answer to reports/strategic_fork/<model>.md.

OpenAI-compatible /chat/completions. Zero pip deps (urllib).
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import sys
import time
import urllib.request

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "reports", "strategic_fork")
os.makedirs(OUT_DIR, exist_ok=True)

SYSTEM = (
    "You are a senior quant fund strategist advising a small team. You are "
    "blunt, specific, skeptical. No generic advice. Every recommendation must "
    "be concrete, sequenced, and resource-aware (small team, modest budget). "
    "You have seen many retail/small quant efforts fail — be realistic about "
    "base rates. 'No edge / insufficient data / stop spending' is a fully "
    "valid answer and must be stated plainly if it is true — never "
    "manufacture a positive finding to seem useful. If any fact in the "
    "CONTEXT looks wrong, stale, or unverifiable, flag it explicitly BEFORE "
    "building on it. Every empirical claim must name its source inline (a "
    "file, a dataset, a measured number) or be dropped."
)

PROMPT = """\
CONTEXT — a multi-asset signal system, verified state 2026-05-18 after an
exhaustive, leakage-controlled edge hunt:

- 7 straight kills by a strict walk-forward admissibility gate
  (edge_stability_harness: eff>=0.30, SAME SIGN, >=3 of 5 windows).
- Killed: method_a_score, risk_reward/R:R, COT positioning (CT=F leakage),
  the ml_enhanced 149-variant mining sprawl, qlib factors + regime score,
  COMMODITY roll-yield, BOND 2s10s slope-momentum, CRYPTO funding-rate
  (tested on 6yr/4838 events), EQUITY PEAD (242 names, 6988 picks).
- Every candidate failed the SAME way: strong in-sample separation that does
  not hold a stable SIGN out-of-sample. PEAD — the most OOS-robust anomaly in
  the academic literature — failed identically here.
- Data excuses were eliminated, not worked around (deep archives pulled).
- Honest conclusion: the system's input space (price/volume technicals, COT,
  funding rate, futures term structure, earnings surprise) does NOT contain
  admissible edge at retail latency/cost.
- The team is small. Budget is modest. Money posture is currently paper-only.

THE THREE OPTIONS ON THE TABLE (the operator sees value in all three):
1. NEW INPUT CLASS — acquire data the system has never seen: order-flow
   microstructure (L2 book imbalance, trade tape), options-implied signals
   (skew, dealer gamma, flow), genuine alt-data. A program; likely paid data.
2. RESEARCH-SANDBOX — freeze the edge hunt; paper-only; the harness stays as
   the admission gate for any future candidate. Zero capital at risk.
3. STRUCTURE ALPHA — stop hunting directional/predictive signals; pursue
   structural edge: market-making, funding-rate arb, basis/carry capture —
   where you are PAID to provide liquidity or carry, not to predict direction.

THE ASK — answer in markdown with headers:
1. ARE THESE MUTUALLY EXCLUSIVE? Can/should 2 or 3 run concurrently for a
   small team, or does focus demand picking one? Be specific.
2. SEQUENCING — give a concrete 90-day plan. What runs first, what gates the
   next step, what is the kill-criterion for each strand.
3. BASE RATES — honestly, what is the probability each option produces a
   real, harness-passing edge within 6-12 months? Rank them.
4. STRUCTURE ALPHA — is this genuinely different from directional signal
   hunting, or just a harder version of the same trap? If real, name ONE
   concrete structural strategy and its data + capital + risk requirements.
5. THE SINGLE HIGHEST-EV MOVE — if the team can only commit to ONE thing
   this quarter, what is it and why. One concrete acceptance test.
6. SELF-AUDIT — name the 2 weakest claims in your own answer and exactly
   what evidence would overturn each.

Be honest: if the right answer is "this is unlikely to ever beat costs, keep
it a research sandbox and stop spending", say that plainly. ~700-1100 words.

Output ONLY the numbered sections specified above (1-6), in order, with
nothing before the first header and nothing after the last.
"""

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
        return label, "[skipped - no API key in env]"
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
                fh.write("# %s - strategic fork\n\n%s\n" % (label, text))
            ok = not text.startswith(("[ERROR", "[skipped", "[empty"))
            print("  %-12s %s (%d chars)" % (
                label, "OK" if ok else text[:60], len(text)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
