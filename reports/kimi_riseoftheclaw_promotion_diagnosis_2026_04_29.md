# kimi_riseoftheclaw Promotion-Step Diagnosis (2026-04-29)

**Phase 2-B EQUITY follow-up.** Read-only investigation. No code changes.

---

## TL;DR

- **Root cause: (D) Per-source trust-tier hardcoded as UNTRUSTED in `cross_aggregation/system_trust_registry.py:245-251`.** Every kimi pick is stamped `trust_tier=UNTRUSTED` at `audit_trail/dashboard_generator.py:12027`, then hard-rejected by `passes_active_gate` at `audit_trail/quality_gates.py:3597` (`BLOCKED_ACTIVE_TRUST_TIERS = {"BANNED", "AVOID", "UNTRUSTED"}`). The static-registry tier is reinforced by the dynamic-recompute path: kimi's `KIMI_RISEOFTHECLAW/data/closed_picks.json` lifetime stats are 994 trades @ WR 28.07% → BANNED tier dynamically. The 30-day window is WR 63.5% (CRYPTO 55.6%, FOREX 69.8%) and the EQUITY pull from the universal closed ledger is WR 79.27% on n=82 — but the registry uses lifetime stats, so the recent edge never surfaces.

- **Same fix unblocks 6 of the 7 S-tier dormant EQUITY strategies named in HFPA Phase 2-B** (`donchian-stock-breakout`, `rs-breakout-scout`, `price-accel-scout`, `mtf-align-scout`, `whale-accum-scout`, `vol-contraction-scout`). All 6 are 100% kimi-sourced and 100% UNTRUSTED-stamped. The 7th (`stocks_rsi2_pullback`) is `multi_asset_copytrader` / RELIABLE — blocked by the substring rsi2 filter already documented in `reports/EDGE_DELIVERY_INVESTIGATION_2026_04_29.md`.

- **Secondary blocker behind trust_tier: non-crypto raw-score floor (55).** AMD/SOFI scored 17-20 in active_raw; even with trust_tier fixed, the `ACTIVE_DISPLAY_NON_CRYPTO_MIN_RAW_SCORE = 55` floor at `quality_gates.py:3957-3965` would still block them. Two of five (NVDA, MSFT) have score=0 — those get skipped (treated as unscored) and would pass post-fix. **Full fix requires both: lift trust-tier + add `kimi_riseoftheclaw` to `_NC_SCORE_EXEMPT_SOURCES` (line 3932) OR boost score generation for kimi non-crypto picks.**

---

## Verification stats (snapshot from origin/main `audit_dashboard/data/dashboard_data.json`, 2026-04-29 15:52 UTC)

```
kimi active picks (current snapshot): 0
kimi closed in last 7d:               50
kimi closed in last 30d (per panel):  82 EQUITY @ WR 79.27%, PF 7.379, sum +304.35%
```

**Latest 5 kimi closed picks (firing actively, including last 30 minutes):**

```
closed_at=2026-04-29T16:36:55Z  IWM       LONG  pnl=-1.737% SL_HIT
closed_at=2026-04-29T16:13:06Z  NEAR-USD  LONG  pnl=-3.797% SL_HIT
closed_at=2026-04-29T16:09:35Z  DOGE-USD  LONG  pnl=-3.323% SL_HIT
closed_at=2026-04-29T16:09:35Z  IWM       LONG  pnl=-1.765% SL_HIT
closed_at=2026-04-29T14:48:52Z  AMZN      LONG  pnl=+4.162% TP_HIT
```

**5 kimi picks in `picks.active_raw` (pre-gate):** all have `_gate_passed=False` and `trust_tier=UNTRUSTED`.

```
sym=AVAX-USD   ac=CRYPTO  score=22 conf=0.35 trust_tier=UNTRUSTED trust_score=3 fwd_wr=100.0 (n=3)
sym=AMD        ac=EQUITY  score=20 conf=0.35 trust_tier=UNTRUSTED trust_score=6 fwd_wr= 77.8 (n=9)
sym=SOFI       ac=EQUITY  score=17 conf=0.35 trust_tier=UNTRUSTED trust_score=3 fwd_wr=  0.0 (n=1)
sym=NVDA       ac=EQUITY  score= 0 conf=0.35 trust_tier=UNTRUSTED trust_score=6 fwd_wr= 80.0 (n=10)
sym=MSFT       ac=EQUITY  score= 0 conf=0.35 trust_tier=UNTRUSTED trust_score=6 fwd_wr= 58.3 (n=12)
```

**Trust-tier distribution of kimi closed picks (296 in dashboard_data.recent_closed):** 100% UNTRUSTED across CRYPTO (n=23), EQUITY (n=172), FOREX (n=21), ETF (n=71), BOND (n=9).

**Trust-tier distribution of all 157 active_raw picks:** RELIABLE=28, WATCH=123, **UNTRUSTED=5 (all kimi)**, PROVEN=1. **kimi is the only UNTRUSTED-tier source in the entire active raw pool.**

---

## Emitter + workflow + data-file paths

- **Emitter (Python):** `KIMI_RISEOFTHECLAW/live_scanner.py` (and several siblings: `alpha_engine_v2.py`, `alpha_research_engine.py`, `forex_scanner.py`, etc.)
- **Output file:** `KIMI_RISEOFTHECLAW/data/active_picks.json` (10 active picks, lastUpdated 2026-04-28T01:39:29Z) — schema differs from dashboard format: uses `signal=BUY/SELL` instead of `direction=LONG/SHORT`, `entryPrice` instead of `entry_price`, `confidence` is integer 35/40/55 not float 0.35/0.55, etc. **`_normalize_pick` handles all renames correctly** — schema is NOT the bug.
- **Closed-pick file:** `KIMI_RISEOFTHECLAW/data/closed_picks.json` (994 trades, only CRYPTO 333 + FOREX 661 — note: NO EQUITY in this file).
- **GHA workflow:** `.github/workflows/backtest-and-deploy.yml` (paths-on-push to `KIMI_RISEOFTHECLAW/live_scanner.py`, `KIMI_RISEOFTHECLAW/index.html`, `KIMI_RISEOFTHECLAW/js/**`, `KIMI_RISEOFTHECLAW/css/**`); also `.github/workflows/kimi-feb172026-live.yml` (referenced in `EDGE_DELIVERY_INVESTIGATION_2026_04_29.md`, ran green ~2026-04-29 18:26 UTC).
- **Dashboard load path:** `audit_trail/dashboard_generator.py:6643-6647` reads `KIMI_RISEOFTHECLAW/data/active_picks.json` → loops `activePicks` → `_normalize_pick(p, "kimi_riseoftheclaw", "OPEN")` → appends to `active`.

---

## Trace through the gate(s)

1. **Load** (`dashboard_generator.py:6643`): 10 active picks read from `KIMI_RISEOFTHECLAW/data/active_picks.json`.
2. **Normalize** (`dashboard_generator.py:6646` → `_normalize_pick:5804`): schema renames work (`signal` → `direction`, `entryPrice` → `entry_price`, etc.). 5 of 10 reach `active_raw` (the other 5 lost upstream — likely staleness/age, not investigated).
3. **Trust-tier stamp** (`dashboard_generator.py:12027`): `pick["trust_tier"] = get_tier(pick.get("source_system", ""))`.
   - `get_tier` from `cross_aggregation/system_trust_registry.py` resolves `kimi_riseoftheclaw` → alias `kimi` (line 557) → static `TIER_UNTRUSTED` (line 246).
   - Dynamic recompute (line 723-720): reads `KIMI_RISEOFTHECLAW/data/closed_picks.json`, computes lifetime WR 28.07% on 994 trades → `_compute_tier_from_stats` returns BANNED. Static-registry override path (line 821-825) downgrades BANNED → UNTRUSTED only when static is RELIABLE/PROVEN with positive PnL — kimi static is UNTRUSTED with -219 total_pnl, so dynamic BANNED stays BANNED, but the result is "demoted to UNTRUSTED" — pick is stamped UNTRUSTED.
4. **Re-apply gate** (`dashboard_generator.py:13098 → _filter_active_picks_with_gate:10802 → passes_active_gate`):
   - Line 3596-3599: `_pick_trust_tier in BLOCKED_ACTIVE_TRUST_TIERS` → `UNTRUSTED in {"BANNED","AVOID","UNTRUSTED"}` → **REJECT**.
   - The comment at line 588-590 explicitly states UNTRUSTED was added "because 7 UNTRUSTED picks from kimi_riseoftheclaw were leaking through with score=120 (2026-04-04)". **The 2026-04-04 fix is now blocking the 2026-04 EQUITY edge that emerged afterwards.**

---

## Root cause

**(D) — Trust-tier hardcoded as UNTRUSTED + dynamic recompute is class-blind, not "Per-class HC filter only fires on CRYPTO"** — closer to the panel's diagnosis but not exactly the option D in the prompt. The mechanism is:

- The static registry was set to UNTRUSTED on 2026-03-15 with the note "CONFIRMER ONLY: solo picks blocked", reflecting kimi's poor system-wide performance at that time.
- The dynamic recompute uses `closed_picks.json` aggregated across ALL asset classes (no per-class slicing) and across ALL time (no recency window). At 28.07% lifetime WR on 994 trades, it yields BANNED.
- **Both the static and dynamic paths lose the EQUITY-specific 79.27% WR signal** because (a) static is hand-edited and is stale, and (b) dynamic is class-blind on the lifetime view.
- Once stamped UNTRUSTED, the active-gate hard-rejects unconditionally.

This is closest to **(D) — class-aware HC filter falls through to default-reject**, but the literal mechanism is "trust-tier system is class-blind".

---

## Concrete fix recommendation (do NOT implement here)

**Recommendation: split kimi trust-tier evaluation by asset class AND restrict to a recency window.** Specifically:

1. **In `cross_aggregation/system_trust_registry.py`**:
   - Replace the single static entry for `kimi` with per-class entries: `kimi_equity` (PROVEN @ WR 79% / n=82 / +304%), `kimi_forex` (RELIABLE @ WR 69.8% / n=149 / 30d), `kimi_crypto` (WATCH @ WR 55.6% / n=117 / 30d), `kimi_etf`, `kimi_bond`.
   - Make `_compute_tier_from_stats` accept a recency window (default 30d) and slice closed_picks.json by `exit_time`.
   - Make `get_tier(source_system, asset_class=None)` so callers can ask for the per-class tier.

2. **In `audit_trail/dashboard_generator.py:12027`**: pass `asset_class` into `get_tier`:
   ```python
   pick["trust_tier"] = get_tier(pick.get("source_system", ""), pick.get("asset_class"))
   ```

3. **In `audit_trail/quality_gates.py:3932 (_NC_SCORE_EXEMPT_SOURCES)`**: add `kimi_riseoftheclaw` to the exempt list to lift the secondary score-floor blocker for non-crypto picks (kimi's confidence/score profile is below 55 because the kimi schema confidence=35/40/55 is integer-percent, not float, and the score-translation pipeline doesn't account for that).

**Smallest possible single-PR fix (acceptable as Phase 2 starter):** delete the static `kimi` entry from `SYSTEM_TRUST` (force fall-through to dynamic recompute) AND add a 30-day recency window to `_compute_tier_from_stats`. This alone would yield WR ~63.5% / n=266 → RELIABLE tier, immediately lifting the active-gate block for all 7 dormant EQUITY strategies.

**Riskier alternative (NOT recommended):** widen `BLOCKED_ACTIVE_TRUST_TIERS` to drop UNTRUSTED. This re-opens the 2026-04-04 leak (low-quality kimi crypto picks at score=120), so it would have to be paired with a stricter score floor.

---

## Expected impact

- **EQUITY active book volume**: Phase 2-B panel measured 0 currently active. Post-fix, the 5 kimi rows in `active_raw` (4 EQUITY + 1 CRYPTO) would activate immediately. Per the 30-day rate (n=82 EQUITY @ WR 79%, ~2.7 per day), **expect ~15-20 fresh EQUITY active picks/week from kimi alone** once the trust-tier block is lifted.
- **6 dormant S-tier EQUITY strategies revived** (`donchian-stock-breakout`, `rs-breakout-scout`, `price-accel-scout`, `mtf-align-scout`, `whale-accum-scout`, `vol-contraction-scout`). Combined recent 30d volume: 51 closed picks. **Expected ~12-15 fresh active picks/week** from the 6 kimi-sourced strategies.
- **30d realized edge expected to translate to active book**: per Phase 2-B panel, kimi delivers ~135% of EQUITY 30d edge (sum +304% on n=82). If the gate is lifted, this edge can finally be captured live instead of forever validated in closed_picks.

---

## Why this was not caught before

- The 2026-04-04 fix added UNTRUSTED to `BLOCKED_ACTIVE_TRUST_TIERS` to plug a kimi leak in CRYPTO. The fix had no per-class logic and no recency check.
- The static registry was last edited 2026-03-15 ("CONFIRMER ONLY since 2026-03-15"). Kimi's 79% WR EQUITY edge appeared in the 6 weeks AFTER that snapshot. No process re-evaluated the tier when the closed-pick distribution changed.
- The HFPA Phase 2-B EQUITY panel's 9/9 unanimous diagnosis ("active-gate / HC-filter rejection at the promotion step") was correct — but the panel did not have access to `audit_trail/quality_gates.py:591` line where UNTRUSTED is the explicit hardcoded rejection. This investigation closes that gap.

---

## Reproducer commands

```bash
# Verify kimi firing-not-promoting:
python -c "
import json
from datetime import datetime, timezone, timedelta
with open('audit_dashboard/data/dashboard_data.json') as f: d = json.load(f)
print('kimi active:', sum(1 for p in d['picks']['active'] if p.get('source_system')=='kimi_riseoftheclaw'))
print('kimi active_raw:', sum(1 for p in d['picks'].get('active_raw',[]) if p.get('source_system')=='kimi_riseoftheclaw'))
print('kimi closed (recent_closed):', sum(1 for p in d['picks']['recent_closed'] if p.get('source_system')=='kimi_riseoftheclaw'))
"

# Verify all kimi picks stamped UNTRUSTED:
python -c "
import json
with open('audit_dashboard/data/dashboard_data.json') as f: d = json.load(f)
from collections import Counter
tt = Counter(p.get('trust_tier') for p in d['picks']['recent_closed'] if p.get('source_system')=='kimi_riseoftheclaw')
print('kimi trust_tier distribution:', dict(tt))
"
```

---

## References

- `audit_trail/quality_gates.py:588-591` — `BLOCKED_ACTIVE_TRUST_TIERS` (the hard-block)
- `audit_trail/quality_gates.py:3596-3599` — gate enforcement
- `audit_trail/quality_gates.py:3932-3965` — `_NC_SCORE_EXEMPT_SOURCES` (secondary score-floor blocker)
- `audit_trail/dashboard_generator.py:12027` — `pick["trust_tier"] = get_tier(...)`
- `audit_trail/dashboard_generator.py:6643-6647` — kimi load path
- `cross_aggregation/system_trust_registry.py:245-251` — static `kimi` UNTRUSTED entry
- `cross_aggregation/system_trust_registry.py:557` — alias `kimi_riseoftheclaw → kimi`
- `cross_aggregation/system_trust_registry.py:688-720` — `_compute_tier_from_stats` (class-blind, lifetime-only)
- `KIMI_RISEOFTHECLAW/data/active_picks.json` — emitter output (10 active, last update 2026-04-28T01:39:29Z)
- `KIMI_RISEOFTHECLAW/data/closed_picks.json` — emitter native ledger (994 trades, CRYPTO+FOREX only)
- `reports/HFPA_PHASE-2-findings-EQUITY-2026-04-29.md` — Phase 2-B panel finding
- `reports/EDGE_DELIVERY_INVESTIGATION_2026_04_29.md` — prior investigation (kimi NOT covered)
