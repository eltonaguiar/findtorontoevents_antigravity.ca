import json, urllib.request, time, sys

PROXY = "http://localhost:4000/v1/chat/completions"
MODELS = ["nvidia-deepseek-v4-pro", "deepseek-chat-direct", "paid-mode-large",
          "hybrid-model-large", "cloudflare-llama", "ollama-cloud-local"]
ROUNDS = 15

SEED = """# Quick-Pick & Long-Term Methodology (DRAFT v0 — to be refined)

Covers QUICK-PICK (fast, consensus-only, no backtest) and LONG-TERM (hold for years)
selection for FIVE asset groups: STOCKS, ETFs, BONDS, FUTURES, COMMODITIES.

## Quick-Pick rules (per group)
- STOCKS: analyst consensus + 13F ownership + moat; tilt mega-cap quality.
- ETFs: broad/low-cost core; rank by AUM + expense + breadth.
- BONDS: T-bill/short-duration ballast first; rate-risk aware.
- FUTURES: avoid unless clear trend; managed-futures TSMOM only.
- COMMODITIES: gold/broad-basket as hedge; momentum filter.

## Long-Term rules (per group)
- STOCKS: durable compounders, ROIC, balance sheet, reinvestment runway.
- ETFs: dual-momentum / factor tilt; rebalance discipline.
- BONDS: ladder + duration vs rate cycle.
- FUTURES: diversifying TSMOM sleeve, low correlation.
- COMMODITIES: strategic 5-10% inflation hedge.
"""

def call(model, prompt, max_tokens=1400, timeout=200):
    body = json.dumps({"model": model,
                       "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": max_tokens, "temperature": 0.4}).encode()
    req = urllib.request.Request(PROXY, body, {"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=timeout))
    return (d["choices"][0]["message"]["content"] or "").strip()

draft = SEED
changelog = []
for r in range(1, ROUNDS + 1):
    model = MODELS[(r - 1) % len(MODELS)]
    prompt = f"""You are reviewer in round {r}/{ROUNDS} of a 15-round swarm refining a stock/ETF/bond/futures/commodity selection METHODOLOGY. Two modes: QUICK-PICK (fast, pure-consensus, NO backtest) and LONG-TERM (multi-year hold).

CURRENT DRAFT:
---
{draft}
---

Improve it. Keep what works; fix gaps; add CONCRETE signal sources + numeric thresholds (e.g. analyst count, expense-ratio caps, duration bands, momentum lookbacks, position sizing, rebalance cadence, when-to-avoid rules). Cover ALL FIVE groups in BOTH modes. Be specific and usable.

OUTPUT EXACTLY:
CHANGELOG: <=2 lines on what you changed this round.
---
<the FULL improved methodology in markdown, <=750 words>
"""
    try:
        out = call(model, prompt)
        if "---" in out:
            head, _, body = out.partition("---")
            cl = head.replace("CHANGELOG:", "").strip()
            body = body.strip()
        else:
            cl, body = "(no changelog parsed)", out
        if len(body) > 200:           # only accept substantive drafts
            draft = body
        changelog.append(f"R{r} [{model}]: {cl[:200]}")
        print(f"round {r} OK [{model}] draft={len(draft)}c")
    except Exception as e:
        changelog.append(f"R{r} [{model}]: FAIL {e}")
        print(f"round {r} FAIL [{model}]: {e}")
    time.sleep(0.5)

with open("reports/QUICK_PICK_METHODOLOGY_SWARM_2026-06-02.md", "w", encoding="utf-8") as f:
    f.write("# Quick-Pick & Long-Term Methodology — 15-Round AI Swarm Refinement\n\n")
    f.write("**Date:** 2026-06-02 · **Orchestrator:** Claude Opus 4.8 · **Panel (rotating):** "
            + ", ".join(MODELS) + f" · **Rounds:** {ROUNDS}\n\n")
    f.write("> Methodology design via iterative multi-model refinement. Opinion/process design, "
            "not backtested edge. Per-round changelog at the end.\n\n")
    f.write("## FINAL METHODOLOGY (round-15 draft)\n\n")
    f.write(draft + "\n\n---\n\n## Round-by-round changelog\n\n")
    f.write("\n".join(f"- {c}" for c in changelog) + "\n")
print("WROTE reports/QUICK_PICK_METHODOLOGY_SWARM_2026-06-02.md")
