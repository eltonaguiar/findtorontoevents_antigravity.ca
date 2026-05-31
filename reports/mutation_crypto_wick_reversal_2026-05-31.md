# Mutation autopsy — crypto_liquidity_wick_reversal_v1

**Date:** 2026-05-31
**Protocol:** `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate-before-kill)
**Trigger:** strategy is 100% BTCUSDT concentrated. CLAUDE.md concentration rule
(HHI > 0.30 at strategy level) is violated at HHI = 1.00. Before sizing up or
killing, run the three-axis autopsy.

## Sources of truth

| Source | Path | Note |
|---|---|---|
| Closed picks (raw) | `battleground/data/closed_picks.json` | 43 closed rows for this strategy |
| Per-symbol registry | `audit_dashboard/data/pf_registry.json` → `by_asset_class_strategy_symbol` | post-policy-clean cohort, n=30 (13 rows filtered by policy gates) |
| Banned strategies | `strategy_health/data/banned_strategies.json` | not banned as of this report |

Raw-cohort numbers (n=43) and policy-clean cohort (n=30) diverge slightly on WR
(58.1% raw vs 60.0% policy-clean) and PF (1.50 raw vs 1.56 policy-clean). The
policy-clean numbers are verdict-grade per M-067; raw numbers are informational.

## Step 1 — Three-axis slice

### Axis 1: SYMBOL (the requested mutation axis)

| Symbol   | N (raw) | Wins | WR%   | PF    | Source |
|----------|--------:|-----:|------:|------:|--------|
| BTCUSDT  | 43      | 25   | 58.1  | 1.50  | closed_picks.json |
| BTCUSDT  | 30      | 18   | 60.0  | 1.56  | pf_registry (policy-clean) |
| ETHUSDT  | 0       | —    | —     | —     | NO DATA |
| SOLUSDT  | 0       | —    | —     | —     | NO DATA |
| BNBUSDT  | 0       | —    | —     | —     | NO DATA |
| AVAXUSDT | 0       | —    | —     | —     | NO DATA |

**Finding:** the strategy has produced **zero closed picks** on ETH, SOL, BNB,
AVAX (or any non-BTC symbol). This is not a "BTC outperforms alts" finding —
the strategy as currently wired only **emits** on BTCUSDT. We cannot answer
"does the edge generalize?" from observational closed-picks data because there
is no emission on alts to observe.

### Axis 2: DIRECTION

All 43 closes split:
- BUY (long-only emissions in the sample): all 43. There are no SHORT closes
  for this strategy in `closed_picks.json`. Direction-axis is non-informative.

### Axis 3: TIMEFRAME

Closes show a tight cluster on 3h holding window (e.g. 2026-02-24 13:00 →
16:00). Single-bucket — TF-axis non-informative.

### Axis 4: vol-normalization (research only)

Not applicable here: the strategy already operates on a wick / liquidity
trigger which is, by construction, a price-action shape. The Step 1b
ATR-normalization mutation is a tool for momentum/RSI threshold strategies and
does not apply.

## Step 2 — Symbol × system compatibility

Following Step 2 of the protocol (`ALLOW` if WR ≥ 55% and trades ≥ 10):

- **BTCUSDT: ALLOW.** WR 58.1% (raw) / 60.0% (policy-clean), n=30, PF 1.56.
  Exceeds the 55% / 10-trade allow threshold.
- All other symbols: no data — neither ALLOW nor BLOCK can be issued from
  observational data.

## Step 5 — Mutation-quality score (curve-fit guard)

MutationQuality ≈ (WR_subset × N_subset) / N_total
= (0.60 × 30) / 30 = **0.60**

The "winning subset" is 100% of total closed trades, which is the trivial
upper bound — there is no smaller subset to curve-fit to. This is the inverse
of the usual curve-fit failure mode (a tiny lucky subset). Here, the strategy
is genuinely uniform within its (single) symbol universe.

## Verdict — BTC-only filter (keep) + emission-coverage probe

**Decision matrix:**

| Option | Verdict | Rationale |
|---|---|---|
| `size_up` (production sizing increase) | **NO** | n=30 is below the n≥100 "proven" bar in CLAUDE.md goal #1. WR 60% / PF 1.56 is Tier-2-ish but on a single-symbol cohort that violates HHI<0.30. Cannot defend a real-money allocation increase. |
| `BTC-only filter (keep as-is)` | **YES** | Current behaviour (emits BTCUSDT only, WR 60%, PF 1.56) is the de-facto BTC allowlist. Keep it — do **not** force-expand to alts without a proper emission-coverage probe first. |
| `reject / BLOCKED_SOURCE_SYSTEMS` | **NO** | Performance does not justify kill — the strategy is a Tier-2 candidate on its native symbol. Killing it would violate the mutate-before-kill rule (no rehab has been attempted yet). |

**Headline:** This is **not** a "BTC wins, alts lose" finding. It is a "strategy
emits BTC-only by construction" finding. The mutation question is mis-posed —
the right next step is a coverage probe (SANDBOX) on alts, not a kill or a
size-up.

## Next step (single, concrete)

1. **Emission-coverage probe (SANDBOX, research-only):** review
   `incubator/agents/cursor_ai/crypto_liquidity_wick_reversal_v1.py.meta.json`
   and `incubator/agents/codex_gpt5/crypto_liquidity_wick_reversal_v1.py.meta.json`
   to find the symbol universe the scanner walks. If it iterates only BTCUSDT,
   the BTC concentration is a wiring choice, not an edge claim. Lift the
   universe to {ETHUSDT, SOLUSDT, BNBUSDT, AVAXUSDT} in **SANDBOX tier only**
   (no production emission) and accumulate ≥20 closes per symbol before
   re-running this autopsy.
2. **Do NOT** add a `BLOCKED_SOURCE_SYSTEMS` entry. Concentration is at the
   strategy level (per `feedback-concentration-strategy-not-engine.md`) and the
   correct fix is universe expansion, not engine kill.
3. **Hold off on sizing-up** real-money exposure on BTCUSDT until n ≥ 100 on
   the policy-clean cohort, per CLAUDE.md goal #1 "proven" bar.

## Reproducer

```bash
python3 - << 'PY'
import json
from collections import defaultdict
with open('battleground/data/closed_picks.json') as f:
    picks = json.load(f)
by_sym = defaultdict(lambda: {'n':0,'wins':0,'gw':0.0,'gl':0.0})
for p in picks:
    if (p.get('strategy') or '').lower() != 'crypto_liquidity_wick_reversal_v1':
        continue
    sym = p['symbol']; pnl = p.get('pnl_pct') or 0.0
    by_sym[sym]['n'] += 1
    if p.get('status') == 'WIN': by_sym[sym]['wins'] += 1
    (by_sym[sym]['gw'] if pnl > 0 else by_sym[sym]['gl']).__iadd__  # see direct math below
    if pnl > 0: by_sym[sym]['gw'] += pnl
    else:       by_sym[sym]['gl'] += abs(pnl)
for sym, s in by_sym.items():
    wr = s['wins']/s['n']*100
    pf = s['gw']/s['gl'] if s['gl']>0 else float('inf')
    print(f"{sym:10} n={s['n']:>3}  wr={wr:5.1f}%  pf={pf:5.2f}")
PY
```

Plus the policy-clean view:

```bash
python3 -c "
import json
d = json.load(open('audit_dashboard/data/pf_registry.json'))
for row in d['by_asset_class_strategy_symbol']:
    if row.get('strategy') == 'crypto_liquidity_wick_reversal_v1':
        print(row)
"
```
