# PEER REVIEW — ETF

**Reviewer:** finpredict-v3 peer-review subagent, 2026-11-14T16:17Z

## 1. Peer docs read
- v4 `noncrypto_deep_dive.md` §3 ETF (1,722 open; n=44 intrabar; BITO/IBIT).
- v4 `dashboard_data_report.md` §2.2/2.3/2.4 §5 (ETF INSUFFICIENT_DATA; policy-clean n=15).
- v4 `market_crossref_report.md` ETFs (IWM/GLD OPEN ~5mo; HDV/SCHD current).
- v1 `2026-11-14-prediction-system-audit.md` §2 ETF row (30 OPEN, 15 frozen); §7 ETF PF 0.76.
- v2 `E_statistical.md` §5 (ETF n=15, PF 1.8358, z=+1.81) + §7.1 (summary WR 232.9% bug).
- ML-audit `proposed_fixes/overall/FIX_PROPOSED.md` (ETF feed fresh 2d; class backfill).
- Mine `2026-11-14-prediction-data-hygiene.md` (ETF no price bug; last_quote).

## 2. Peer verdict per class
- v4 (noncrypto): "ETF Verdict: STALE / REHAB" — intrabar **n=44, WR 2.3%, PF 0.022** = "worst intrabar-verified class"; top picks BITO/IBIT are **Bitcoin ETFs (crypto proxies)**; strategy `etf_rsi2_pullback` n=3 (WR 66.7%, PF 24.51) — sample laughably small.
- v4 (dashboard): **INSUFFICIENT_DATA** (intrabar n=45, WR 2.2%, PF 0.022; recent closed DB raw 14d n=47, WR 25.5%, PF 0.621; policy-clean net **n=15, PF 1.836**).
- v1: headline ETF PF 0.76; 30 OPEN, 15 (50%) frozen at 0%.
- v2: **n=15, WR 73.33%, PF 1.8358, z=+1.81, p=0.071** — the only class with PF>1 but does **not** survive 9-class Bonferroni (α=0.0056).
- v4 crossref: IWM/GLD OPEN ~5mo, far past TP (IWM +34.6% vs TP +7%, GLD +42.2% vs TP +6%), still OPEN.

## 3. Peer-proposed quick wins (with source + dedup)
1. **Split/count crypto-ETFs separately** — BITO/IBIT are BTC proxies and pollute equity-ETF stats (v4 noncrypto; crossref) — UNIQUE.
2. Purge the 1,722 stale/unmanaged backlog (v4 noncrypto; v1) — DUPLICATE with all-class purge.
3. Add `last_quote` timestamp; show "last close Fri 11/13" so 0% PnL reads as parked, not live (mine §per-class).
4. Re-quote at next session open; refresh GLD/IWM/HDV/SCHD prices (mine; v4 crossref).
5. Keep class INSUFFICIENT_DATA; do not size on n=15 (v4 dashboard; v2).
6. Fix `summary_picks` WR-as-232.9% denominator bug (v2 §7.1) — cross-class but visible on ETF surface.

## 4. Disagreements / contradictions
- **n=44 intrabar (WR 2.3%) vs n=15 policy-clean (PF 1.84)**: same class, opposite directions; both tiny, neither statistically meaningful. v2 explicitly: ETF is the only class with PF>1 but fails Bonferroni.
- **Headline PF 0.76 (v1) vs policy-clean PF 1.836 (v2)** — surface disagreement.
- Freshness: v1/v4 flags ETF price-frozen; mine+ML report ETF feed is fresh (2d) with no price bug — the *emission* feed is fresh, the *old OPEN inventory* is frozen.

## 5. Gaps
- ML-audit `proposed_fixes/etfs/` is EMPTY (no ETF-specific fix) — NOT FOUND.
- No peer proposes a real ETF strategy/edge plan; all fixes are hygiene.
- Crypto-ETF contamination (BITO/IBIT) untracked in any dataset.

## 6. Recommended best-of (master plan)
Treat as **INSUFFICIENT_DATA / rehab**: no sizing (v4/v2 agree). P0 = hygiene (purge 1,722, refresh prices, last_quote) + segregate crypto-ETFs so the n=15 PF>1 sign isn't driven by BTC proxies. Require a forward ledger n>=100 before any promotion.
