#!/usr/bin/env python3
"""pick_improvement_harvest.py — harvest per-asset-class pick-improvement ideas
from cloud LLMs (incl. Ollama Cloud) via Windows-env API keys.

Companion to tools/no_edge_cloud_consult.py. Different prompt: not "is there an
edge" but "given the verified no-edge baseline, harvest concrete ways to
improve picks per asset class". Each model writes its own file under
reports/pick_improvement_harvest/<model>.md. Zero pip deps (urllib).
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import sys
import time
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "reports", "pick_improvement_harvest")
os.makedirs(OUT, exist_ok=True)

SYSTEM = ("You are a senior quantitative researcher. Blunt, specific, no "
          "generic trading-blog advice. Every idea must be concrete, "
          "falsifiable, and implementable by a small quant team. "
          "'No edge / insufficient data / stop spending' is a fully valid "
          "answer and must be stated plainly if it is true — never "
          "manufacture a positive finding to seem useful. If any fact in the "
          "CONTEXT looks wrong, stale, or unverifiable, flag it explicitly "
          "BEFORE building on it. Every empirical claim must name its source "
          "inline (a file, a dataset, a measured number) or be dropped.")

PROMPT = """\
A multi-asset signal system (findtorontoevents.ca/audit). VERIFIED state
2026-05-18 — canonical net-of-slippage, deduped, policy-clean profit factors:
CRYPTO 1.28, COMMODITY 1.17, EQUITY 0.72, FOREX 0.33 — ALL sub-Tier-2 (1.5).
NO asset class has a real edge. The one apparent edge (cotton/CT=F COT, 77% WR)
was a single-symbol concentration + COT-publication look-ahead leakage artifact
— now blocked. The CRYPTO number is the winning tail of a 149-variant
ml_enhanced per-symbol mining sprawl (family PF 0.63).

TASK: harvest concrete ways to IMPROVE picks PER ASSET CLASS. For each of
CRYPTO, EQUITY, COMMODITY, FOREX, ETF, BOND give, in markdown:
- ONE specific, academically-grounded signal/feature worth adding, the exact
  data source, and a falsifiable acceptance test (n, WR, PF, OOS method).
- ONE thing to CUT or fix that is currently degrading that class's picks.
- If the honest answer for a class is "no retail edge — stop", say so.
Then: 3 cross-class improvements to the PICK PROCESS itself (feature
engineering, validation, ensembling, sizing) that would raise pick quality
regardless of class. ~600-900 words. Be concrete; cite real techniques.

Finally, a section headed "## SELF-AUDIT" — name the 2 weakest claims in
your own answer and exactly what evidence would overturn each.

Output ONLY the headed sections specified above (the six asset-class blocks,
the cross-class improvements, then SELF-AUDIT), in that order, with nothing
before the first header and nothing after the last.
"""

# (label, env-var, base-url, model). OpenAI-compatible /chat/completions.
ENDPOINTS = [
    ("ollama-cloud", "OLLAMA_CLOUD_KEY", "https://ollama.com/v1",
     "gpt-oss:120b"),
    ("deepseek", "DEEPSEEK_API_KEY", "https://api.deepseek.com/v1",
     "deepseek-reasoner"),
    ("xai-grok", "XAI_API_KEY", "https://api.x.ai/v1", "grok-3"),
    ("kimi", "KIMI_API_KEY", "https://api.moonshot.ai/v1", "moonshot-v1-32k"),
    ("openrouter", "OPENROUTER", "https://openrouter.ai/api/v1",
     "deepseek/deepseek-chat"),
]


def call(label, env, base, model):
    key = os.environ.get(env, "").strip()
    if not key:
        return label, "[skipped — no key]"
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": PROMPT}],
        "temperature": 0.4,
    }).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=body, method="POST",
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.load(r)
            return label, (d["choices"][0]["message"]["content"] or "[empty]")
        except Exception as exc:  # noqa: BLE001
            if attempt == 0:
                time.sleep(3)
                continue
            return label, "[ERROR %s: %s]" % (model, exc)
    return label, "[ERROR]"


def main():
    print("harvesting from %d cloud models..." % len(ENDPOINTS))
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(ENDPOINTS)) as ex:
        for fut in concurrent.futures.as_completed(
                {ex.submit(call, *e) for e in ENDPOINTS}):
            label, text = fut.result()
            with open(os.path.join(OUT, label + ".md"), "w",
                      encoding="utf-8") as fh:
                fh.write("# %s — pick-improvement harvest\n\n%s\n" % (label, text))
            ok = not text.startswith(("[ERROR", "[skipped", "[empty"))
            print("  %-14s %s (%d chars)" % (
                label, "OK" if ok else text[:50], len(text)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
