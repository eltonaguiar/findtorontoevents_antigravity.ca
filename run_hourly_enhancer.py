import json, urllib.request, time, os, re, collections, sys

PROXY = "http://localhost:4000/v1/chat/completions"
DEVIL = "nvidia-deepseek-v4-pro"
REFINERS = ["deepseek-chat-direct", "paid-mode-large", "hybrid-model-large",
            "cloudflare-llama", "ollama-cloud-local"]
CYCLES = 5
SLEEP_S = 3600
REPORT = "reports/HOURLY_PICKS_ENHANCEMENT_2026-06-02.md"
STATE = "reports/FINAL_AGREED_PICKS_2026-06-02.json"
METH = "reports/QUICK_PICK_METHODOLOGY_SWARM_2026-06-02.md"

# seed picks from CQP consensus
state = {
    "picks": {"MSFT": 90, "BRKB": 89, "SGOV": 95, "VOO": 94, "VTI": 92, "COST": 89, "AGG": 92},
    "avoid": ["INTC", "NVDA", "TSLA"],
    "methodology_notes": ["Stability-tilt: bonds/T-bills + broad ETF + quality mega-cap.",
                          "Exclude divisive/AVOID-flagged names. Verify live before sizing."],
    "cycles_done": 0,
}

def call(model, prompt, mx=1100, to=200):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": mx, "temperature": 0.4}).encode()
    req = urllib.request.Request(PROXY, body, {"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=to))
    return (d["choices"][0]["message"]["content"] or "").strip()

def log(msg):
    print(msg, flush=True)

def picks_str(s):
    return ", ".join(f"{k}:{v}" for k, v in sorted(s["picks"].items(), key=lambda x: -x[1]))

# init report
if not os.path.exists(REPORT):
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("# Hourly Picks Enhancement — Debate + Devil's-Advocate Swarm (5 cycles)\n\n")
        f.write("**Date:** 2026-06-02 · **Orchestrator:** Claude Opus 4.8 · "
                f"**Devil's advocate:** {DEVIL} · **Refiners:** {', '.join(REFINERS)}\n\n")
        f.write("> Each hourly cycle: devil's-advocate attacks the basket, refiners respond + adjust "
                "confidence, consensus carried forward. Opinion/process, not backtested edge.\n\n")

for c in range(1, CYCLES + 1):
    log(f"=== CYCLE {c}/{CYCLES} start ===")
    meth_ctx = ""
    if os.path.exists(METH):
        meth_ctx = open(METH, encoding="utf-8").read()[:3000]

    cur = picks_str(state)
    avoid = ", ".join(state["avoid"])
    notes = "; ".join(state["methodology_notes"][-6:])

    # 1) DEVIL'S ADVOCATE
    dev_prompt = f"""You are the DEVIL'S ADVOCATE in cycle {c} of a stability-tilted consensus stock/ETF/bond basket review.
CURRENT BASKET (ticker:confidence): {cur}
AVOID: {avoid}
NOTES: {notes}

Attack this basket HARD in <=200 words: concentration risk, rate-cycle/duration risk, valuation, regime fragility, single points of failure, anything overrated. Name the WEAKEST pick and the strongest MISSING candidate. Be specific."""
    try:
        devil = call(DEVIL, dev_prompt)
    except Exception as e:
        devil = f"(devil's advocate failed: {e})"
    log(f"  devil {len(devil)}c")

    # 2) REFINERS respond
    refiner_picks = []
    use = [REFINERS[(c - 1 + i) % len(REFINERS)] for i in range(3)]
    for rm in use:
        ref_prompt = f"""Cycle {c} refiner. Stability-tilted consensus basket. Use analyst consensus, 13F ownership, moat/quality, rate-cycle awareness. NO backtest.
CURRENT BASKET: {cur}
AVOID: {avoid}
DEVIL'S ADVOCATE CRITIQUE:
{devil}

Respond to the critique and output your improved basket. OUTPUT EXACTLY:
PICKS: TICKER:CONF, TICKER:CONF, ... (7-9 names, CONF 0-100, react to the critique — drop/swap weak names, keep strong)
DELTA: <=2 bullets on what you changed and why."""
        try:
            out = call(rm, ref_prompt)
            pm = re.search(r"PICKS:\s*(.+)", out)
            if pm:
                d = {}
                for tok in pm.group(1).split(","):
                    mm = re.match(r"\s*([A-Za-z\.]+)\s*:\s*(\d+)", tok)
                    if mm:
                        d[mm.group(1).upper().replace(".", "")] = int(mm.group(2))
                if d:
                    refiner_picks.append((rm, d, out))
            log(f"  refiner {rm}: {len(refiner_picks and refiner_picks[-1][1] or {})} picks")
        except Exception as e:
            log(f"  refiner {rm} FAIL: {e}")

    # 3) aggregate refiners -> new consensus (majority appearance, avg conf)
    if refiner_picks:
        conf = collections.defaultdict(list)
        for _, d, _ in refiner_picks:
            for tk, v in d.items():
                conf[tk].append(v)
        nref = len(refiner_picks)
        newpicks = {tk: round(sum(v) / len(v)) for tk, v in conf.items() if len(v) >= max(2, (nref + 1) // 2)}
        if len(newpicks) >= 5:
            state["picks"] = dict(sorted(newpicks.items(), key=lambda x: -x[1])[:9])

    state["cycles_done"] = c
    state["methodology_notes"].append(f"C{c}: devil flagged weakest; refiners reconciled -> {picks_str(state)}")

    # append cycle to report + save state every cycle
    with open(REPORT, "a", encoding="utf-8") as f:
        f.write(f"## Cycle {c} ({time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())})\n\n")
        f.write(f"**Devil's advocate ({DEVIL}):**\n\n> " + devil.replace("\n", "\n> ") + "\n\n")
        f.write(f"**Refiner panel:** {', '.join(use)}\n\n")
        for rm, d, out in refiner_picks:
            f.write(f"- *{rm}*: {', '.join(f'{k}:{v}' for k,v in sorted(d.items(),key=lambda x:-x[1]))}\n")
        f.write(f"\n**Consensus after cycle {c}:** {picks_str(state)}\n\n---\n\n")
    json.dump(state, open(STATE, "w", encoding="utf-8"), indent=2)
    log(f"=== CYCLE {c} done -> {picks_str(state)} ===")

    if c < CYCLES:
        time.sleep(SLEEP_S)

# FINAL agreed block
with open(REPORT, "a", encoding="utf-8") as f:
    f.write("## FINAL AGREED CONSENSUS (after 5 hourly debate cycles)\n\n")
    f.write(f"**Picks (ticker:confidence):** {picks_str(state)}\n\n")
    f.write(f"**Avoid:** {', '.join(state['avoid'])}\n\n")
    f.write("**Methodology trail:**\n" + "\n".join(f"- {n}" for n in state["methodology_notes"]) + "\n")
log("ALL CYCLES COMPLETE")
print("HOURLY_ENHANCER_DONE", flush=True)
