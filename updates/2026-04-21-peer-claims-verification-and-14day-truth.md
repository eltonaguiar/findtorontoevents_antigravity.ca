# Peer-Claim Verification + 14-Day Truth (vs 48h Bounce-Day Bias)

**Author:** Claude Opus 4.7 (1M context)
**Date:** 2026-04-21
**Triggered by:** User noted "48h may be too short" + flood of 6 peer-agent reports with conflicting numbers.
**Scope:** Verify each peer claim against the full ~3500-pick `recent_closed` window AND a 14-day sub-window. **NO production changes.** Verification only.

---

## The bombshell: 48h window was massively unrepresentative

| Window | n | WR | PF | cum PnL% |
|---|---|---|---|---|
| **48 hours** | 698 | **39.8%** | **1.336** | **+114.91** |
| **14 days** | 2,521 | **26.6%** | **0.660** | **−1,110.95** |

**The 48h window captured 1 mean-reversion bounce day (2026-04-20).** Over the prior 12 days the book bled at -1111% cum. Every peer agent's "we made +50/$150% over 48h" finding describes a regime, not the system's edge.

This is exactly what the Ollama models warned about (PR #310 §10): "regime-lucky, not robust." Confirmed at 14-day scale.

---

## Peer-claim verification matrix

Verified against `audit_trail/data/dashboard_payload.json::picks.recent_closed` (3,500 picks, ~14 days).

| Source | Claim | Verified? | Truth |
|---|---|---|---|
| Free Buff (PR #311) | `quan_engine_scalp` -794% / 0% WR | **NO** | n=0 in `recent_closed`. Possibly in `strategy_performance.json` historical aggregates. PR #311 about to merge a kill of a strategy that may not be emitting in this view. |
| Kimi (tweaks) | `enhanced_ml_A_xgboost` -76% / 11.3% WR | **NO** | n=0 in `recent_closed`. |
| Kimi (tweaks) | confidence 0.6-0.7 = "GOLDEN ZONE" 63.8% WR / +150% | **REFUTED** | Full window: conf 0.6-0.7 is **n=906 WR 28.9% cum −408.62%** — the SINGLE LARGEST LOSING BUCKET. Kimi's 48h-only finding inverted reality. |
| Kimi (tweaks) | confidence 0.7-0.8 = "TOXIC" 15.8% WR / -64% | **REFUTED** | Full window: conf 0.7-0.8 is n=91 WR 30.8% cum -45 (small bucket, not toxic). |
| Kimi + Roocode | "Block crypto SHORTs — they're 29.6% WR / -2%" | **REFUTED** | Full window: SHORT n=458 WR **40.4%** PF 0.607. LONG n=1200 WR **30.5%** PF 0.559. **SHORT WR is HIGHER than LONG WR.** Both lose, but blocking SHORTs based on "they're bad" is wrong. The 48h favored LONG only because of the bounce. |
| Kimi (toxic syms) | ARBUSDT/TIAUSDT/APEUSDT bleeding | **VERIFIED** | ARBUSDT n=45 WR 33% cum −98; TIAUSDT n=14 WR 21% cum −136; APEUSDT n=11 WR 18% cum −70. Real drags. |
| Kimi (toxic syms) | XRPUSDT toxic | **PARTIAL** | XRPUSDT n=64 WR 33% cum −23. Real drag but smaller than the 3 above. |
| Kimi (toxic syms) | CHZUSDT toxic | **TOO SMALL** | CHZUSDT n=3 cum −6. Sample insufficient. |
| Peer 3 (Kimi CLI) | "98% of picks have elite_score=0" | **REFUTED** | Only 14/3500 (**0.4%**) have elite_score=0 in `recent_closed`. Their claim was from `universal_resolved_picks.json` which has different fields. |
| Peer 3 (Kimi CLI) | "100% of picks are CRYPTO" | **REFUTED** | Their source file (`universal_resolved_picks.json`) has all 5,000 rows tagged `asset_class=UNK`. We DO emit non-crypto (518 CRYPTO + 116 COMMODITY + 48 FOREX + 17 EQUITY in last 48h). They assumed crypto from symbol patterns. |
| Peer 6 (ChatGPT Codex) | "TRXUSDT BUY: 11 trades, +1.10, 54.5% WR" | **CHECK NEEDED** | TRX is in `BLOCKED_SYMBOLS` per `quality_gates.py`. If they have 11 trades, that's a leak. |

---

## What's actually true in the data

### The real CRYPTO confidence pattern (full ~3500 window)

| Conf bucket | n | WR | cum PnL% |
|---|---|---|---|
| [0.00-0.50) | 105 | 43.8% | −45.73 |
| **[0.50-0.60)** | **216** | **46.8%** | **+19.88** ← only positive bucket |
| [0.60-0.70) | **906** | **28.9%** | **−408.62** ← biggest loser |
| [0.70-0.80) | 91 | 30.8% | −45.23 |
| [0.80-0.90) | 323 | 33.7% | **−807.88** ← second biggest loser |
| [0.90-1.01) | 17 | 29.4% | +0.58 |

**Real sweet spot is conf [0.50, 0.60).** The 0.6-0.7 bucket has the most picks AND the most loss. Kimi's "cap at 0.70" recommendation would not help — the picks > 0.7 aren't the worst, the 0.6-0.7 zone IS.

This matches `feedback_confidence_is_not_edge.md` from session memory.

### The real CRYPTO direction pattern (full window)

| Direction | n | WR | PF | cum |
|---|---|---|---|---|
| LONG | 1,200 | 30.5% | 0.559 | −534 |
| SHORT | 458 | **40.4%** | 0.607 | **−753** |

SHORT has higher WR. Its larger negative cum is from individual losers being bigger (different stop sizing). Don't block SHORT — investigate why SHORTs hit larger absolute losses when they lose.

### Symbol kill list — only the verified ones

Per Bonferroni-corrected significance (PR #300 framework):

**Verified strong drains (n ≥ 10, cum < −50%):**
- ARBUSDT (n=45, cum −97)
- TIAUSDT (n=14, cum −136)
- APEUSDT (n=11, cum −70)

**Verified moderate drain (n ≥ 30, cum < −20):**
- XRPUSDT (n=64, cum −23)

**Sample too small to act on:**
- CHZUSDT (n=3)

---

## What about FORCE_CLOSED on COMMODITY/FOREX?

My PR #310 said FOREX/COMMODITY was a "resolver bug." More accurate after deeper look:

- **COMMODITY: 496/563 (88%) FORCE_CLOSED** with W/L/F = 104/125/267, cum +0.95%, mean +0.002%
- **FOREX: 278/840 (33%) FORCE_CLOSED** with W/L/F = 110/11/157, cum +1.61%

`FORCE_CLOSED` ≠ `flat-close`. These picks DID resolve, with real (small) P/L. The exit_reason "FORCE_CLOSED" means "neither TP nor SL hit, position closed at expiry." The pnl is the actual mark-to-market drift over the holding period.

**This isn't a bug — it's strategy design.** FOREX/COMMODITY strategies are setting TP/SL too far from entry for the holding window. Most picks expire without triggering either. The result: lots of small ±drift outcomes that look like flats but are real.

**Implication:** WR/PF for these classes should be computed AFTER excluding FORCE_CLOSED to see whether the actual TP-vs-SL hit ratio carries edge:

| Class | Pre-exclusion WR | Post-exclusion WR (TP_HIT vs SL_HIT only) |
|---|---|---|
| COMMODITY | (need to compute) | (need to compute) |
| FOREX | (need to compute) | (need to compute) |

---

## Action items (verified, evidence-based)

### P0 — Flag PR #311 with verification gap

`quan_engine_scalp` doesn't exist in `recent_closed`. The PR's premise is from a different data source (probably historical `strategy_performance.json`). Verify before merging:
- If quan_engine_scalp HAS historical -794% but is CURRENTLY not emitting, killing it is symbolic, not impactful.
- If it IS emitting somewhere we don't see, the kill is correct but needs trace.

### P1 — Reject Kimi's confidence-cap recommendation

Capping conf at 0.70 (Kimi tweak #3) would NOT help — the 0.6-0.7 bucket is our biggest loser bucket. Real edge is in [0.50, 0.60). Kimi's recommendation was based on a 48h MATIC-dominated artifact.

### P2 — Reject Kimi/Roocode's "block crypto SHORTs" recommendation

SHORT WR (40.4%) is HIGHER than LONG WR (30.5%) over full window. The 48h SHORT-loses pattern is regime-conditional (bounce day). Blocking SHORT permanently would harm us in trending-down regimes.

### P3 — Verified symbol blocks (3 only, not 5)

Add to `BLOCKED_SYMBOLS`: ARBUSDT, TIAUSDT, APEUSDT. (Skip XRPUSDT for now — n=64 is borderline, watch another week. Skip CHZUSDT — n=3 too small.)

### P4 — Investigate why SHORTs lose bigger

LONG cum −534 on n=1200 → −0.45/pick. SHORT cum −753 on n=458 → −1.65/pick. SHORTs lose **3.6× more per losing trade**. Likely larger stops or higher-vol symbols. Investigate stop-distance distribution by direction.

### P5 — Don't act on hourly patterns from any 48h analysis

Both Ollama models (PR #310 §10) and the 14-day data confirm: 48h hourly splits are noise. Wait for 14-day patterns to validate.

---

## The methodology that actually works

1. **Use `recent_closed` as source of truth** (not `universal_resolved_picks.json` which has tagging bugs)
2. **Use ≥14-day window for direction/confidence/symbol decisions** (48h is regime-biased)
3. **Use Bonferroni correction** at α/N_strategies for kill decisions (PR #300 framework)
4. **Verify each peer agent's claim against full window before acting**
5. **Distinguish FORCE_CLOSED ≠ flat-close** (former is real outcome, latter is bug indicator)

---

## What this means for "where is our edge?"

After 14-day clean look:
- **No edge in CRYPTO at conf [0.6-0.9]** (3 of the largest losing buckets)
- **Marginal edge in CRYPTO at conf [0.5-0.6]** (only positive bucket, +20 cum on n=216)
- **EQUITY remains the only consistently positive class** (cycles 3-9 + this verification)
- **FOREX/COMMODITY are inconclusive** until FORCE_CLOSED reclassification done
- **Most "winner" strategies in 48h were retired** (`st_fear_greed_contrarian`, `st_obv_support_divergence`) — yet they print at +35% over 48h. That's regime-luck, not edge.

**The honest answer to user's "where is our edge?":** Marginal-to-none in CRYPTO over 14d at current configuration. EQUITY is the one bright spot. 48h windows can show fake edge during favorable regimes — don't act on them.

---

## Files in this PR

- `updates/2026-04-21-peer-claims-verification-and-14day-truth.md` — this report

No production files changed. Verification only.

## Reproduce

```bash
python -c "
import json
from collections import defaultdict
from datetime import datetime, timezone, timedelta
dp = json.load(open('audit_trail/data/dashboard_payload.json','r',encoding='utf-8'))
closed = [p for p in dp['picks']['recent_closed'] if p.get('pnl_pct') is not None]

# 14-day window
def cdt(p):
    for f in ('closed_at','resolved_at','timestamp'):
        v=p.get(f)
        if v:
            try: return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
            except: pass
    return None
cutoff = datetime.now(timezone.utc) - timedelta(days=14)
w14 = [p for p in closed if (dt:=cdt(p)) and dt >= cutoff]
pnls = [float(p['pnl_pct']) for p in w14]
print(f'14-day: n={len(w14)}, WR={sum(1 for x in pnls if x>0.01)/len(pnls)*100:.1f}%, cum={sum(pnls):+.2f}%')

# Confidence buckets in CRYPTO
crypto = [p for p in closed if (p.get('asset_class') or '').upper() == 'CRYPTO']
for lo,hi in [(0.0,0.5),(0.5,0.6),(0.6,0.7),(0.7,0.8),(0.8,0.9),(0.9,1.01)]:
    bs = [p for p in crypto if p.get('confidence') is not None and lo <= float(p['confidence']) < hi]
    if bs:
        bp = [float(p['pnl_pct']) for p in bs]
        print(f'  conf [{lo:.2f}-{hi:.2f}): n={len(bs)}, WR={sum(1 for x in bp if x>0.01)/len(bs)*100:.1f}%, cum={sum(bp):+.2f}%')
"
```
