# Peer Review — FUTURES

**Reviewer:** finpredict-v3 (2026-11-14T16:17Z)

---

## 1. Peer docs read (inventory)

| Peer | File | Verdict |
|---|---|---|
| v4 | `audits/2026-11-14/finpredict-v4_2026-11-14-1555/noncrypto_deep_dive.md` | FUTURES DEAD / BLOCKED |
| v2 | `.kilo/worktrees/finpredict-v2/2026-11-14/finpredict-v2_20261114-1602/sub/D_non_crypto.md` | **FAIL** — 100% zero PnL, frozen prices |
| v1 | `.kilo/worktrees/finpredict/2026-11-14/finpredict/2026-11-14T160004Z/updates/2026-11-14-prediction-system-audit.md` | FUTURES dead (3 OPEN, 0 closed ever) |
| ML | `updates/2026-11-14-ML-AUDIT-childlike-airport/proposed_fixes/` | **no futures folder** (only crypto/ + bonds/) — NOT FOUND |
| self(v3) | `2026-11-14T155500Z/updates/2026-11-14-prediction-data-hygiene.md` | futures `no date` seed; gated placeholder row |

**v4 `proposed_fixes/futures/` = EMPTY** (0 files).

---

## 2. Peer verdicts (quoted + key numbers)

- **v4 noncrypto:** "FUTURES … DEAD / BLOCKED. Zero live emission. The sole 'active' pick is a stale artifact." `picks_now_live_pnl.json` = **0** live picks; intrabar n=52 WR 42% PF 1.09 → INSUFFICIENT_N; HTML banner: "Futures remain BLOCKED… 6.3% WR on n=17 with 76% LOST-exit rate." The "1 future" = YM=F ghost in 26-day-stale `dashboard_data.json`.
- **v2 D_non_crypto:** **FAIL** — 1 curated ES=F active (LONG 7583.0); 13 `active_raw` rows **100% `pnl=0`**, 77% >30d stale; **frozen April prices** prove no mark-to-market (ZN=F `111.015625` = Yahoo 2026-04-02 close exactly; CL=F 112.06 vs 88.56 now = **−21.0%**; GC=F −17.3%); duplicate emission (ES=F×3, YM=F×6); **0 rows in `recent_closed`**; `forwardWR=0.059` contradicts MRV WR 42.3%.
- **v1 audit:** FUTURES **3 OPEN** in `active_raw`, **0 closed ever**; `ES=F` seed `signal_time` = bare `"2026-11-14"` date-only → UI renders "no date"; raw median 2,344h. "Dead."
- **self(v3):** `ES=F` active pick has date-only `signal_time`/`entry_time`; is gated (`_gate_passed=false`), trust LOW, 0 closed history → flag `DATE_ONLY_SEED`; recommend not listing gated/placeholder rows as active.

---

## 3. Quick-win fixes proposed by peers

| Fix | Source(s) | Multi-peer? |
|---|---|---|
| Formally retire FUTURES OR build a re-emission plan (current state BLOCKED) | v4 (rec 4); v1 (dead) | **YES** |
| Resolve/close stale ghost picks (YM=F artifact; 3 OPEN never resolved) | v4; v2 (0 closed, no resolution) | **YES** |
| Emit full ISO timestamps — never date-only `signal_time`; filter gated/placeholder rows from active panel | v1; self (`DATE_ONLY_SEED`) | **YES** |
| Fix frozen/unpriced prices (never mark-to-market): ZN=F/CL=F/GC=F April zombies | v2 (§6); v4 (stale artifact) | **YES** |
| Deduplicate emissions (ES=F×3, YM=F×6) | v2 (§6) | single |
| Reconcile contradicting WR surfaces (forwardWR 0.059 vs MRV 42.3%) | v2 (§6) | single |

---

## 4. Disagreements / contradictions

- **Active pick count:** v4 = 0 (live pricing tracker); v2 = 1 (curated panel, ES=F); v1 = 3 (active_raw). Different layers; all agree "essentially no live futures."
- **"1 active pick with no date":** v1 confirms the date-only string renders "no date"; **v2 says NOT REPRODUCED** (Playwright shows "Nov 14, 8:06 AM"). Contradiction between peers on the UI rendering — likely a version/render-path difference, should be re-verified.
- **WR surfaces:** v2 reports `forwardWR=0.059` (5.9%) vs MRV 42.3% for the same class — noted as a cohort conflict, not resolved.

---

## 5. Gaps (not fixed/verified by any peer)

- No ML-audit futures fix exists (`proposed_fixes/futures` NOT FOUND) — the class is the least-owned.
- No peer implemented any re-emission or retirement decision; all recommendations are advisory.
- Intraday fill granularity for futures exits UNVERIFIED (daily-close reconstruction only).
- No peer verified a long viable live futures sample (0 closed ever in primary feed).

---

## 6. Recommended best-of for the master plan (FUTURES)

1. **Adopt v4's decision gate:** either formally retire the module or approve a re-emission plan — nothing else should proceed until this choice is made.
2. **Adopt v2's evidence as the diagnostic baseline:** the frozen April prices and 0 closed rows prove no mark-to-market and no resolution; use `recent_closed=0` as the hard kill trigger.
3. **Adopt v1 + self's seed fix:** emit full ISO timestamps and filter gated/placeholder (`_gate_passed=false`) rows out of the active panel — this is the only cheap, code-level fix with clear owner.
4. **Do not size** any futures pick until a validated closed sample exists (v4 intrabar n=52 INSUFFICIENT_N).
