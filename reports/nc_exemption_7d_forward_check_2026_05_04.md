# NC Gate Exemption — 7-Day Forward WR Check
**Generated:** 2026-05-04  
**Payload `generated_at`:** 2026-05-04T22:55:48.677059+00:00 (0.9h old — PROCEED)  
**Window:** 2026-04-28 to 2026-05-04 (7 days post-exemption)

---

## Context

PR #446 (`fix/nc-active-gate-exemptions-2026-04-27`) was **closed without merging** (`merged=false`).  
Despite this, `kimi_riseoftheclaw` was subsequently added to `_NC_SCORE_EXEMPT_SOURCES` via a separate commit on 2026-04-29 (see `quality_gates.py:4647` comment).  
`non_crypto_consensus` was NOT added to the exemption set (PR #446 did not land).

**Sources verified in this check:**
- `non_crypto_consensus` — WR floor 50% (task spec)
- `kimi_riseoftheclaw` — WR floor 55% (task spec)

---

## Aggregation Script

Script: `/tmp/nc_exemption_7d_check.py`

```python
#!/usr/bin/env python3
"""
NC Exemption 7-day Forward WR Check — 2026-05-04
Sources: non_crypto_consensus, kimi_riseoftheclaw
Window: entry_day or close_day >= 2026-04-28 (7 days back from 2026-05-04)
"""
import json, datetime, sys

CUTOFF = "2026-04-28"
SOURCES = ["non_crypto_consensus", "kimi_riseoftheclaw"]
FLOORS = {
    "non_crypto_consensus": 0.50,
    "kimi_riseoftheclaw":   0.55,
}
NOISE_THRESHOLD_PCT = 0.05   # |pnl_pct| < 0.05% = resolver noise
NOISE_SHARE_CAP = 0.30       # if noise_share > 30% -> HUMAN_REVIEW

with open("audit_trail/data/dashboard_payload.json") as f:
    d = json.load(f)

# ... (full script at /tmp/nc_exemption_7d_check.py)
```

### Script stdout

```
Payload generated_at: 2026-05-04T22:55:48.677059+00:00
7-day window: 2026-04-28 to 2026-05-04 (inclusive)
Total recent_closed picks: 3500

=== non_crypto_consensus ===
  Total in recent_closed (all dates): 118
  Picks in 7-day window (>= 2026-04-28): 19
  Status values present: {'EXPIRED', 'LOST', 'WON'}
  wins (status-based): 15 | wins (pnl>0): 15
  n_7d=19, n_with_pnl=19, wins=15, losses=4
  WR=78.9% | PF=2.273 | avg_pnl=0.0010%
  Resolver noise wins: 15/15 = 100.0%
  Floor: 50% | STATUS: INSUFFICIENT_DATA

=== kimi_riseoftheclaw ===
  Total in recent_closed (all dates): 329
  Picks in 7-day window (>= 2026-04-28): 45
  Status values present: {'LOST', 'WON'}
  wins (status-based): 19 | wins (pnl>0): 19
  n_7d=45, n_with_pnl=45, wins=19, losses=26
  WR=42.2% | PF=0.980 | avg_pnl=-0.0380%
  Resolver noise wins: 0/19 = 0.0%
  Floor: 55% | STATUS: PRUNE

======================================================================
DECISION TABLE
Source                           n      WR     PF  noise%  avg_pnl  floor STATUS
----------------------------------------------------------------------
non_crypto_consensus            19   78.9%  2.273  100.0%  0.0010%    50% INSUFFICIENT_DATA
kimi_riseoftheclaw              45   42.2%  0.980    0.0% -0.0380%    55% PRUNE
```

---

## Per-Source Forward Stats Table

| Source | n | WR | PF | noise_share | avg_pnl | floor | Status |
|---|---|---|---|---|---|---|---|
| `non_crypto_consensus` | 19 | 78.9%* | 2.273* | **100.0%** | 0.0010% | 50% | **INSUFFICIENT_DATA** |
| `kimi_riseoftheclaw` | 45 | 42.2% | 0.980 | 0.0% | −0.0380% | 55% | **PRUNE** |

\* WR/PF are resolver-noise artifacts — all 15 wins have `|pnl_pct| < 0.05%` (max 0.0065%).

### Resolver Noise Deep-Dive: `non_crypto_consensus`

Every "win" in the 7-day window is a FOREX pair resolved against the yfinance live close at entry price ≈ exit price. The largest win PnL is 0.0065% (USDCAD); losses are uniformly −0.0050% (SL-distance floor). The 78.9% WR is **entirely resolver artifact** — not real edge. This source is **not in `_NC_SCORE_EXEMPT_SOURCES`** (PR #446 was not merged), so no prune action is taken; the noise issue is flagged for the next human reviewer.

Win pnl breakdown (all 15 wins):
```
EURGBP=X   0.003600%  USDCAD=X   0.006500%  EURJPY=X   0.004700%
GBPJPY=X   0.005100%  USDJPY=X   0.006300%  EURJPY=X   0.002700%
AUDJPY=X   0.001100%  AUDUSD=X   0.001400%  CADJPY=X   0.000300%
EURGBP=X   0.000100%  EURJPY=X   0.000400%  GBPJPY=X   0.000100%
GBPUSD=X   0.000400%  USDCAD=X   0.000300%  USDCHF=X   0.001100%
```
All < 0.05% threshold. Losses: 3 × LOST (−0.005000% each) + 1 EXPIRED (0.000000%).

---

## Decision Per Source

| Source | Decision | Reason |
|---|---|---|
| `non_crypto_consensus` | **INSUFFICIENT_DATA** | n=19 < 20 (trigger 1); also 100% resolver noise — if n were ≥20 would be HUMAN_REVIEW |
| `kimi_riseoftheclaw` | **PRUNE** | n=45 ≥ 20; noise_share=0%; WR 42.2% < 55% floor; PF 0.980 < 1.0 |

---

## Actions Taken

### PRUNE: `kimi_riseoftheclaw`

**File edited:** `audit_trail/quality_gates.py`  
**Location:** `_NC_SCORE_EXEMPT_SOURCES` set, formerly lines 4647–4658

Removed entry `"kimi_riseoftheclaw"` and replaced with tombstone comment explaining the prune decision. The `ai_challenge` category in `audit_dashboard/hc_filter.js:90` and `tools/hc_gates_python.py:100` were inspected — those are UI category memberships, not gate exemptions; they were left untouched.

**Parity check:** `python tools/hc_parity_test.py` → `divergent=0` ✓

### KEEP (deferred): `non_crypto_consensus`

Not in `_NC_SCORE_EXEMPT_SOURCES` (PR #446 was not merged). No edit required. Flagged: if this source is later added to the exemption set, the resolver noise issue must be resolved first — the FOREX picks are being closed at entry price and generating phantom micro-wins. Recommend: add this source to the resolver's non-crypto 5bp threshold only after verifying yfinance FOREX close data is live (not stale).

---

## Files Edited

| File | Lines | Change |
|---|---|---|
| `audit_trail/quality_gates.py` | 4647–4658 (pre-edit) → 4647–4652 (post-edit) | Removed `"kimi_riseoftheclaw"` from `_NC_SCORE_EXEMPT_SOURCES`; added tombstone comment |

---

## PR

PR #802 opened for the PRUNE: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/802

---

## Exemption Location Map (for future reference)

| File | Line(s) | What it controls |
|---|---|---|
| `audit_trail/quality_gates.py:4634` | `_NC_SCORE_EXEMPT_SOURCES` | Active non-crypto score gate exemption (this is the kill switch) |
| `audit_trail/quality_gates.py:4820` | `_SCORE_FLOOR_EXEMPT_SOURCES` | Universal 40-floor exemption (synthetic strategy names) |
| `audit_dashboard/hc_filter.js:90` | `ai_challenge` array | UI category membership only — not a gate |
| `tools/hc_gates_python.py:100` | `ai_challenge` array | Python mirror of UI category — not a gate |
| `audit_trail/feed_membership.py` | N/A | No `kimi_riseoftheclaw` or `non_crypto_consensus` references found |

---

## Next Check

- **`non_crypto_consensus`:** Recheck 2026-05-11 (7 more days). Resolve noise issue before adding to exemption. Minimum n=20 clean (post-noise-filter) trades required.
- **`kimi_riseoftheclaw`:** PRUNED. Restore requires: 7d forward WR ≥ 55% + n ≥ 20 in a fresh window. See `reports/kimi_riseoftheclaw_promotion_diagnosis_2026_04_29.md` for original justification.
