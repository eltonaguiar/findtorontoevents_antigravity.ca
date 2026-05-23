#!/usr/bin/env python3
"""test_swarm_models.py — live-test every endpoint in swarm_models.py and
classify each as a SMART (reasoning-grade) or FAST (cheap/quick) model.

For each callable endpoint it sends:
  1. a connectivity probe (must answer at all),
  2. a numeracy probe with a definitive answer — separates reasoning-grade
     models from weak ones.

Records latency, OK/FAIL, numeracy-correct. Writes
reports/swarm_model_test_<UTC>.md with a SMART/FAST classification and a
consult-script fit recommendation.

Zero pip deps (urllib). Run: python tools/test_swarm_models.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
from swarm_models import available_endpoints, resolve_key, build_headers  # noqa: E402

# Numeracy probe — definitive answer. PF = (WR*avg_win)/((1-WR)*avg_loss).
# PF 1.40, WR 45% -> avg_win/avg_loss = 1.40 * 0.55 / 0.45 = 1.711...
# A reasoning-grade model returns ~1.71 and "above". A weak model fumbles it.
NUMERACY_Q = (
    "A trading strategy has profit factor 1.40 and win rate 45%. "
    "Profit factor = (WR*avg_win)/((1-WR)*avg_loss). Compute avg_win/avg_loss "
    "to 2 decimals. Reply with ONLY the number, nothing else."
)
NUMERACY_ANSWER = 1.71  # accept 1.69-1.73


def _call(ep, prompt: str, max_tokens: int = 60) -> tuple[bool, float, str]:
    key = resolve_key(ep.env_vars)
    body = json.dumps({
        "model": ep.model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens, "temperature": 0.0,
    }).encode()
    req = urllib.request.Request(
        ep.base_url.rstrip("/") + "/chat/completions", data=body,
        method="POST", headers=build_headers(ep, key))
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            d = json.load(resp)
        txt = d["choices"][0]["message"]["content"] or ""
        return True, time.time() - t0, txt.strip()
    except Exception as exc:  # noqa: BLE001
        return False, time.time() - t0, "ERR: %s" % exc


def _numerate(txt: str) -> bool:
    import re
    for m in re.findall(r"-?\d+\.?\d*", txt):
        try:
            if abs(float(m) - NUMERACY_ANSWER) <= 0.03:
                return True
        except ValueError:
            pass
    return False


def main() -> int:
    eps = available_endpoints()
    print("Testing %d callable endpoints..." % len(eps))
    rows = []
    for ep in eps:
        ok1, lat1, _ = _call(ep, "Reply with exactly: OK", 20)
        # 1200 tokens so reasoner models (deepseek-reasoner etc.) have room
        # to emit their chain-of-thought AND still reach the final number.
        ok2, lat2, ans = _call(ep, NUMERACY_Q, 1200)
        numerate = ok2 and _numerate(ans)
        rows.append({
            "label": ep.label, "model": ep.model, "tier": ep.tier,
            "reachable": ok1, "latency_s": round((lat1 + lat2) / 2, 2),
            "numerate": numerate, "answer": ans[:50],
        })
        print("  %-18s %s tier=%-5s lat=%.1fs numerate=%s" % (
            ep.label, "OK " if ok1 else "DEAD", ep.tier,
            (lat1 + lat2) / 2, numerate))

    # Declared tier is the reliable classifier (one-shot numeracy probe is
    # noisy); the probe is a liveness + sanity cross-check.
    smart = [r for r in rows if r["reachable"] and r["tier"] == "smart"]
    fast = [r for r in rows if r["reachable"] and r["tier"] == "fast"]
    dead = [r for r in rows if not r["reachable"]]
    flagged = [r for r in smart if not r["numerate"]]

    lines = [
        "# Swarm Model Test — %s" % time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                  time.gmtime()),
        "",
        "Live connectivity + numeracy probe of every callable endpoint in "
        "`tools/swarm_models.py`. Class = the endpoint's DECLARED tier "
        "(reliable); `numerate` = did it pass a one-shot profit-factor probe "
        "(noisy sanity check — a declared-smart model failing it is flagged).",
        "",
        "| endpoint | model | reachable | latency | numerate | class |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        cls = (r["tier"].upper() if r["reachable"] else "DEAD")
        lines.append("| %s | %s | %s | %.1fs | %s | %s |" % (
            r["label"], r["model"], "yes" if r["reachable"] else "NO",
            r["latency_s"], "yes" if r["numerate"] else "no", cls))
    lines += [
        "",
        "## Classification",
        "",
        "**SMART (%d)** — quant reasoning, second-opinion consults: %s" % (
            len(smart), ", ".join(r["label"] for r in smart) or "none"),
        "",
        "**FAST (%d)** — breadth / quick checks, not quant verdicts: %s" % (
            len(fast), ", ".join(r["label"] for r in fast) or "none"),
        "",
        "**DEAD (%d)**: %s" % (
            len(dead), ", ".join(r["label"] for r in dead) or "none"),
        "",
        "**Sanity flag** — declared-smart endpoints that failed the one-shot "
        "numeracy probe (probe noise, not necessarily a real problem; re-run "
        "to confirm): %s" % (
            ", ".join(r["label"] for r in flagged) or "none"),
        "",
        "## Consult-script fit",
        "",
        "- `no_edge_cloud_consult.py` / `strategic_fork_consult.py` / "
        "`consult_ling_crypto.py` — verdict-grade reasoning -> use the SMART "
        "set only. A FAST model in a no-edge brainstorm produces confident "
        "noise.",
        "- `pick_improvement_harvest.py` — idea breadth -> SMART + FAST both "
        "fine (more diverse inputs help; harness gates the result anyway).",
        "- The asset-class diagnostic prompt "
        "(`reports/ASSET_CLASS_DIAGNOSTIC_PROMPT.md`) -> SMART set only; it "
        "demands numeric reasoning about PF/WR/walk-forward stability.",
    ]
    report = "\n".join(lines) + "\n"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = os.path.join(REPO, "reports", "swarm_model_test_%s.md" % stamp)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(report)
    print("\nSMART:", [r["label"] for r in smart])
    print("FAST: ", [r["label"] for r in fast])
    print("written -> reports/swarm_model_test_%s.md" % stamp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
