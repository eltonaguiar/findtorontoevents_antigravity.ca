# Remaining Action Items Evaluation — 2026-05-19

## Context

We run a multi-asset algorithmic trading system with CI-gated quality controls.
Session CX is complete (goal state = ACHIEVED). Three genuine action items remain
open. Evaluate each independently and give a concrete recommendation.

---

## Item 1: EIA_API_KEY → GitHub Actions Secrets

**Situation:**
- `tools/co1_commodity_inventory_surprise_research.py` (CO-1 / H-027) uses the
  U.S. Energy Information Administration (EIA) free API v2 for inventory surprise
  signals on energy ETFs (USO, UNG, UGA, UHN).
- The key currently lives in the Windows registry (`HKCU\Environment\EIA_API_KEY`).
- CI workflows (`pead-shadow-collector.yml`, future CO-1 harness job) cannot access
  Windows registry env vars — they run in GitHub-hosted Linux runners.
- H-027 energy-only backtest verdict: HARNESS REJECTED (WR=49.4%, gross_edge=-0.40 bps).
  The edge doesn't pass the walk-forward harness even with real EIA data.

**Question:** Should we bother wiring EIA_API_KEY into GitHub Actions secrets now,
given H-027 is HARNESS REJECTED? Or defer until DBA/DBB parsers are wired and
we have a genuine 6-proxy CO-1 test to run?

**Options:**
- A: Wire it now (trivial, `gh secret set EIA_API_KEY`, 60 seconds) — future-proofs CI regardless of H-027 status
- B: Defer until DBA/DBB parsers are done and CO-1 has a real CI workflow to trigger
- C: Abandon CO-1 entirely — H-027 is HARNESS REJECTED, EIA data doesn't help COMMODITY edge

---

## Item 2: D-001 $25K CT=F Shadow Tracker Implementation

**Situation:**
- Swarm (deepseek/xai/kilo) unanimously chose Option C: $25K partial shadow,
  restricted to CT=F (Cotton #2 Futures) picks that pass COT_STALE_GATE.
- CT=F COT-filtered subset: WR=77.5%, PF=4.69, n=40 — elite tier.
- Overall COMMODITY class: WR=46.9%, PF=1.78, n=750 — below T2 WR floor.
- COT_STALE_GATE is now enforce-by-default (M-001, 2026-05-19).
- COMMODITY_CTF_WEEKLY_CAP=1 is already in place (max 1 CT=F pick/week).

**What needs to be built:**
A shadow PnL tracker that:
1. Reads picks from `alpha_engine/data/active_picks.json` (filter: asset_class=COMMODITY, symbol=CT=F, cot_stale_gate_pass=True)
2. Logs them to a JSONL file (`alpha_engine/data/ctf_shadow_log.jsonl`) with entry_price, entry_ts, tp, sl
3. On each run, checks for exits (tp/sl hit or time-based) against a price feed
4. Computes running forward PnL over a 60-day window
5. Outputs a summary to `reports/ctf_shadow_summary_<date>.md`

**Question:** Is this the right implementation plan? What's the minimum viable version?
What risks exist in the design? How similar is this to the PEAD shadow runner
(`tools/pead_shadow_runner.py`) — can we reuse patterns?

**Constraints:**
- Cannot run CT=F price feed locally (no futures data subscription)
- Must be fail-open (0 picks is not an error)
- Shadow only — no real capital, no writes to active_picks.json

---

## Item 3: DBA/DBB Parser Investigation — USDA FAS PSD API

**Situation:**
- CO-1 uses 6 ETF proxies: USO, UNG, UGA, UHN (EIA → real data), DBA, DBB (USDA/LME → offline=True)
- DBA = PowerShares DB Agriculture Fund — tracks corn, wheat, soybeans, sugar
- DBB = PowerShares DB Base Metals — tracks copper, aluminum, zinc
- Current USDA FAS PSD API call: `https://apps.fas.usda.gov/psdonline/api/psd/keyData/` → 404
- Without DBA/DBB, CO-1 gives `offline_synthetic: true` and the energy-only verdict
  (WR=49.4%) is the only real evidence.

**Question:**
1. What is the correct USDA FAS PSD API endpoint for crop ending-stocks data
   (corn/wheat/soybeans/sugar)? The API docs are at `https://apps.fas.usda.gov/psdonline/`
2. Is USDA NASS Quickstats API (`https://quickstats.nass.usda.gov/api`) a better
   alternative for supply/demand data?
3. For LME base metals inventory (DBB proxy), what free API gives weekly warehouse
   stock levels? Candidates: LME Open Data, Quandl CHRIS/LME series, FRED metals data.
4. Given H-027 is already HARNESS REJECTED for energy, is there any reason to expect
   DBA/DBB to produce a PASS? Or is the hypothesis fundamentally flawed (seasonal
   inventory surprise ≠ tradeable ETF edge)?

---

## Instructions

For each item above:
- Give a concrete recommendation (A/B/C for Item 1; implementation verdict for Item 2;
  API guidance for Item 3)
- State your confidence level (high/medium/low)
- Name the single biggest risk in your recommendation
- What would change your answer?

Keep responses focused: 2-3 paragraphs per item maximum.
