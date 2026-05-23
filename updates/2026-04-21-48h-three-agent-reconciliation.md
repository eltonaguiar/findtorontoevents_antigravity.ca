# Three-Agent 48h Analysis Reconciliation — Different Files, Different Truths

**Author:** Claude Opus 4.7 (1M context)
**Date:** 2026-04-21
**Triggered by:** Three independent agents produced three contradictory 48h performance reports on the same nominal "last 48 hours" question. User forwarded all three.

---

## The three reports

| Agent | File produced | n | Overall WR | Overall cum |
|---|---|---|---|---|
| Me (Claude Opus 4.7) | `updates/2026-04-21-48h-performance-investigation.md` | 700 | 39.7% | +114.9% |
| Peer 2 (unknown agent) | `updates/2026-04-21-last-48h-performance-analysis.md` | 257 | 52.1% | +$49.23 (dollars) |
| Peer 3 (Kimi Code CLI) | `updates/2026-04-21-performance-edge-analysis-last-48h.md` | 262 | 41.98% | +53.88% |

Peer 3 claims "100% CRYPTO, zero diversification." I claim 518 CRYPTO / 116 COMMODITY / 48 FOREX / 17 EQUITY / 1 ETF. Peer 2 shows all 5 classes but with different WRs than mine.

**They can't all be right. How can three agents looking at "last 48h" disagree this much?**

---

## Root cause: they're reading different files

| Agent | Data source | Asset class field |
|---|---|---|
| Me | `audit_trail/data/dashboard_payload.json::picks.recent_closed` | present + populated for all 518 CRYPTO / 116 COMMODITY / 48 FOREX / 17 EQUITY |
| Peer 2 | unclear (not stated in report) | — |
| Peer 3 | `audit_trail/data/universal_resolved_picks.json` | **"UNK" for all 5,000 rows** |

Verified directly:

```
universal_resolved_picks.json: n=5000
  asset_class distribution: {'UNK': 5000}
  MATICUSDT count: 697
```

Peer 3's "100% CRYPTO" conclusion **isn't wrong because they lied** — it's wrong because `universal_resolved_picks.json` has no `asset_class` field populated, so they assumed crypto based on symbol pattern (MATICUSDT, BTCUSDT, etc.). Their underlying dataset is indeed crypto-heavy because of a DIFFERENT bug (see below).

---

## Separate ALARMING finding: zombie MATICUSDT leak confirmed

`MATICUSDT` is in `audit_trail/quality_gates.py::BLOCKED_SYMBOLS` as of main branch. It should NOT emit new picks. Checked both files:

| File | MATICUSDT count |
|---|---|
| `dashboard_payload.json::recent_closed` (48h window) | **0** ✓ (block is enforced here) |
| `universal_resolved_picks.json` (full 5000) | **697** ✗ (block NOT enforced here) |

Peer 3 observed 57 duplicate MATICUSDT signals from `quan_engine` in their 48h filter. My check confirms 697 across the full file. **`universal_resolved_picks.json` is a separate resolver pipeline that is NOT reading `BLOCKED_SYMBOLS`.** It's writing picks for retired symbols into a tracking ledger.

This is a genuine operational leak — different from the "retired strategies still emit" leak, but equally real.

---

## Number reconciliation

### My 48h window (dashboard_payload.json::recent_closed)

```
n=698 (matches 700 reported — small drift from file update between runs)
  CRYPTO 518 (no MATICUSDT — correctly blocked)
  COMMODITY 116
  FOREX 48 (46/48 flat — resolver bug)
  EQUITY 17
  ETF 1
top 5 symbols: BTCUSDT 58, ETHUSDT 46, SI=F 45, HG=F 38, DOGEUSDT 33
```

### Peer 2's numbers (unknown source, 257 picks)

Peer 2 shows FOREX at 54.5% WR (12W/10L). Given my 48/46-flat FOREX finding, peer 2 must be either:
- Reading a filtered subset (excluding flats)
- Reading a different file (maybe `dashboard_data.json`?)
- Counting flats as wins

Their EQUITY 77.8% WR (7W/2L) is plausible if they're on a tighter window with only the cleanest picks.

### Peer 3's numbers (universal_resolved_picks.json, 262 picks)

Their CRYPTO-only finding is an artifact of their source file having no asset-class tagging. Their claim of "zero diversification" is literally false — we DO emit picks for COMMODITY/FOREX/EQUITY/ETF (verified in the dashboard payload) — those picks are just missing from THEIR file.

Their CONCRETE findings that are independently actionable:
- **57 duplicate MATICUSDT signals from quan_engine** — this is real, needs dedup investigation
- **11 duplicate CHZ / JTO / TIA losing picks from ml_crypto_pred** — same pattern, worth verifying
- **98% of picks have `elite_score`, `method_a_score`, `ml_composite_score` = 0** — if true, our scoring infrastructure is broken
- **Confidence sweet-spot 0.6-0.7 (WR 63.8%) vs 0.7-0.8 (WR 15.8%)** — confidence anti-predictive pattern (matches memory `feedback_confidence_is_not_edge.md`)

---

## Recommendations (meta)

### M1: Canonicalize the source of truth for "closed picks"

Three agents, three files, three answers. Engineer should declare: **is the source of truth `recent_closed` (dashboard_payload.json) or `universal_resolved_picks.json`?** They clearly aren't synced — MATIC has 0 picks in one, 697 in the other, both claiming to be resolved picks.

Add `tests/test_closed_picks_source_parity.py` that fails the build if the two files disagree on the set of resolved pick IDs.

### M2: Fix the `universal_resolved_picks.json` asset_class tagging

All 5,000 rows have `asset_class=UNK`. This is the same kind of bug that caused the crypto-tagging issue fixed in `dashboard_generator.py:4836-4851` (Session 3 per MEMORY.md). Apply an equivalent fix to whatever writes `universal_resolved_picks.json`.

### M3: Apply `BLOCKED_SYMBOLS` to `universal_resolved_picks.json` writer

MATICUSDT shouldn't have 697 entries if it's in the blocklist. Trace the writer, add `check_symbol_block()` or equivalent.

### M4: Peer 3's duplicate-signal finding deserves follow-up

57 identical MATIC signals from quan_engine. If they're TRULY identical (same entry, same TP, same SL, same pnl) → dedup at write time. If they're sequential attempts → either that strategy has a re-entry bug or this is legitimate scalping volume.

Worth a quick grep in `alpha_engine/quan_engine.py` for emit-loop logic.

### M5: Peer 3's "elite_score=0 on 98% of picks" claim needs independent check

If true, entire scoring tier logic (S-tier / A-tier / ...) is rendered meaningless because score is uniformly zero. If false, peer 3 was reading a wrong field or unresolved-only subset.

---

## Ollama second opinion (mine) applies to all three

I consulted `deepseek-v3.2:cloud` (671B) and `glm-4.6:cloud` (355B) on my 48h dataset. Both independently pushed back on:
- Hour-level WR extremes being spurious (48h = too few samples)
- Retired strategies in the winner list being an overfitting red flag
- Don't act on 48h time-of-day patterns — need 2+ weeks

**This caution applies to peer 2's hourly findings AND peer 3's "kill ml_crypto_pred" recommendation equally.** Peer 3's projected "75-85% WR" after filtering is vastly overstated given the single-window sample.

---

## What to actually do with three contradictory reports

1. **Trust the operational findings that don't depend on statistics:**
   - Peer 3: duplicate MATIC signals, MATIC-in-resolver-despite-block, elite_score=0 bug
   - Me: FOREX/COMMODITY 85% flat-close (resolver bug), retired strategies still emitting (-_RETIRED_STRATEGIES leak)
   - Peer 2: asset-class selection being more impactful than per-strategy selection (consistent w/ cycles 3-9)

2. **Discount the statistics-driven claims until a 14-day window produces consistent numbers:**
   - Peer 2's "EQUITY 77.8% WR" on n=9 is under-powered
   - My "hour 10-12 UTC WR 88-93%" on n=98 is regime-conditional
   - Peer 3's "kill ml_crypto_pred → 75-85% WR" is a small-sample projection

3. **Get the canonical source of truth agreed first.** Until the engineer picks one file as authoritative, further analysis is comparing apples to oranges.

---

## Files in this note

- `updates/2026-04-21-48h-three-agent-reconciliation.md` — this document

## Reproduce

```bash
python -c "
import json, os
from collections import Counter
from datetime import datetime, timezone, timedelta

# source 1 — my file
d = json.load(open('audit_trail/data/dashboard_payload.json','r',encoding='utf-8'))
rc = d['picks']['recent_closed']
cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
def cdt(p):
    for f in ('closed_at','resolved_at','timestamp'):
        v=p.get(f)
        if not v: continue
        try: return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
        except: pass
    return None
win = [p for p in rc if p.get('pnl_pct') is not None and (dt:=cdt(p)) and dt >= cutoff]
print('dashboard_payload.json 48h:', len(win), 'classes:', Counter((p.get('asset_class') or 'UNK').upper() for p in win))

# source 2 — peer 3's file
d2 = json.load(open('audit_trail/data/universal_resolved_picks.json','r',encoding='utf-8'))
rows = d2 if isinstance(d2, list) else []
print('universal_resolved_picks.json total:', len(rows), 'classes:', Counter((p.get('asset_class') or 'UNK').upper() for p in rows))
print('MATIC in universal_resolved_picks:', sum(1 for p in rows if (p.get('symbol') or '').upper() == 'MATICUSDT'))
"
```

No production files modified in this note. All three agents' reports remain on disk for reference.
