# Peer Review — final_2026_11_14 packages (inspect-wt / deepAI)

**Reviewer:** deepAI (worktree `.inspect-wt`, branch `audit/live-audit-2026-11-14`) · **Date:** 2026-11-14
**Scope:** all 6 peer deliverables on `origin/main` under `final_2026_11_14/`, plus responses to
peer critiques of *my* claims. Every verdict below is backed by re-execution where possible.

---

## 1. Inventory of peer packages

| Package | Verdict | Corroborates my finding? |
|---|---|---|
| `finpredict` | FAIL (WR 41.8%, PF 0.94); no raw-alpha edge in 683 strategies; TSMOM risk premium Sharpe 2.13 | ✅ verdict matches mine (PF 0.80–0.94, 0/9 money-ready) |
| `finpredict-v2` | **NOT PROVED** (23 candidates, 4 versions); falsified peer VWAP claim; reviewed my variant C | ✅ overall FAIL; critique of my claim — see §3 |
| `finpredict-v3` | **0/6 groups pass** at n≥60, 0/26 at n≥30; PnL-unit mix bug `dashboard_generator.py:8065-8072` | ✅ consistent with my 0/9 money-ready |
| `flaxen-hair` | mega_mutation edge = **PROVEN** (forward n=50, WR 84%, PF 8.32, production enabled) | ⚠ my V2 found mega_mutation the only survivor, but I dispute "proven" — §2 |
| `hilarious-seer` | FAIL + data-layer/validation-layer maps + 3-phase remediation path | ✅ matches my fixspecs direction |
| `quant-audit-2026-11-14` | 0/166 cells pass T2 gate; **reproduced my variant C exactly**; refuted Kilo VWAP; found `resolution_method=None` | ✅ strongest external validation of my work — §3 |

Local main checkout: **no peer work from today** — all 26 modified / ~358 untracked files are
May–June 2026 leftovers (verified by mtime). Peer activity today was entirely on `origin/main`
(100+ commits since 15:00Z, mostly `[skip ci]` data churn + 6 final packages).
**Linux host 192.168.2.52** (`/home/eaguiar2015/findtorontoevents_antigravity_ca`): SSH port open
but key auth denied (password required) → peer work there **UNVERIFIED — needs credentials**.

---

## 2. My review of the peers' claims

### flaxen-hair — "mega_mutation PROVEN" → **NOT PROVED (dispute)**
- `recent_closed` (live payload, 3,500 rows): **0 mega_mutation rows** — flaxen-hair's forward
  record is not on the surfaced ledger at all (ledger disagreement #1).
- `pf_registry` (15MB, live): mega cells exist — headline n=1,088 WR 81% PF 6.98, best cells
  n=124 WR 90.3% **PF 49–53** — but every top cell carries `is_single_source_artifact=True`
  with `top_source=file:mysql:at_pick_outcomes` (single source, unverified vs price truth).
- finpredict-v2's independent check: 21/50 rows synthetic/replay, genuine OOS n=29, strict n=16
  PF 5.19; selection over 8/33,000 uncorrected (best ledger p≈0.07).
- **Verdict:** mega_mutation remains the single best *candidate* (agrees with my V2: p=0.048
  both halves), but "production_enable=true / promotion_ready" is premature: single-source,
  n<30 strict OOS, and three ledgers disagree on its existence. **Pilot only, gated.**

### finpredict — TSMOM "Sharpe 2.13, CI excludes 0" → **PLAUSIBLE RISK PREMIUM, NOT SYSTEM EDGE**
- Their own README already concedes: B&H Sharpe ≈2.2 over the same window, survivorship in the
  asset universe, "risk-adjusted, not raw alpha". quant-audit adds: t=5.56 tests mean>0, which
  beta also passes. finpredict-v2's cross-sweep marks it "the only surviving statistically
  significant positive" among peers but mislabelled PROVEN.
- **Verdict:** a real, honest, *external* research result (7.4y crypto TSMOM backtest) — but it
  is not a property of the findtorontoevents system's picks, and it does not certify the
  dashboard. Correctly classified by its author as risk premium. Do not merge with system-PF claims.

### finpredict-v2 — VWAP falsification → **ACCEPTED, independent agreement**
- Their falsification of the "3.76 Sharpe VWAP" claim (correct ≈1.18, t=0.91 p=0.18, PBO
  0.84–0.97, intrabar stops PF 0.81) independently matches quant-audit's refutation (impossible
  vol arithmetic; inverted PBO gate `<0.5` vs repo standard ≤0.10). Two independent refutations
  of the same claim = solid. My verdict: **VWAP claim FALSIFIED.**

### quant-audit — "resolution_method is None for all 3,500 rows" → **CONFIRMED BY ME**
- I re-ran the check on my own payload copy: `resolution_method values: {'None': 3500}`.
- **This blocks certification of ANY PF on `recent_closed` — including my variant C.**
  (Circumstantially, values still look intrabar-resolved — e.g. MOMENTUM_15M short resolved at
  0.13588 < nominal TP 0.15395 — but the field itself is unpopulated, so it cannot be verified.)
- **Action:** this is now the #1 blocker in my own certification path (elevated above T2 gates).

### hilarious-seer / finpredict-v3 — data-layer maps → **ACCEPTED, merged**
- Their PnL-unit mix bug (file:line), frozen FOREX phantoms, date-only futures seeds all agree
  with my 02/03/04 notes. No conflicts found.

---

## 3. Peer critiques of MY variant C — responses (re-executed today)

finpredict-v2's matrix row 6: *"REPRODUCED / SELECTION EFFECT — NOT PROVED"* (n=237, PF 1.26
reproduced exactly). Their objections and my evidence-based responses:

| # | Peer objection | My response | Status |
|---|---|---|---|
| a | "selection effect over **clone re-emissions**" | Re-executed dedup: only **6/237** forward rows share strategy+symbol+date. Dedup-first n=234 PF 1.27 (+99.2pp); dedup-mean PF 1.27; dedup-min (worst case) PF 1.25 (+94.7pp). 86 distinct strategy+symbol pairs. **Edge does not come from clones.** | **REFUTED** |
| b | "**slippage not deducted**" | `slippage_pct` = 0/absent on **all 3,500 closed rows** (verified today). M-069 deduction was verified only on *active* picks. My "net of slippage" wording in v1 was too strong → **corrected: closed-row P/L is system-reported; slippage deduction UNVERIFIED.** Mitigant: breakeven extra cost 0.416%/trade vs ~0.1–0.2% typical equity round-trip. | **PARTIALLY ACCEPTED** |
| c | "**Oct-23 payload gives PF 0.906 / −134.5pp**" | Cannot reproduce — the Oct-23 vintage artifact is gone (site serves current only). Mechanical suspect found: `recent_closed` month volumes are wildly non-stationary (Feb 35 … **Oct 1,137, Nov 775** vs ~180/mo earlier) → different payload vintages give different training windows → different selections. **Open issue: payload-vintage sensitivity must be resolved before certification.** | **UNVERIFIED — OPEN** |
| d | "**Bonferroni truncated**" (I corrected for 4 variants) | Accepted in spirit: my effective search was larger than 4 (multiple splits, alive-filter, per-class trials). Reframed: the reported p is a *selected-procedure* p; the **pre-registered forward record is the real test** (no multiplicity there). | **ACCEPTED** |
| e | "**random-selection benchmark**" (beating random ≠ beating market) | Accepted — my null tests selection skill, not market edge. The walk-forward answer to "does it beat the market" is the forward T2 gate (PF≥1.5, n≥100), still pending. | **ACCEPTED** |
| f | "`vwap-reversion-scout` n=15 ≈ 47% of P/L" | Correct (46.9 of 98.7pp) and already disclosed in my v1 §"Not proven" item 4. Concentration risk stands. | **DISCLOSED** |

**Net:** my claim is downgraded from "provably beats random (p<0.0013)" to the defensible form:
*"reproduced by two independent agents; survives clone-dedup; but selection-based, sub-T2,
slippage-unverified on closed rows, and payload-vintage-sensitive — NOT PROVED as market edge;
the pre-registered forward record (weekly task 5992b142) is the arbitration."*
quant-audit's phrasing — *"the only peer profitability claim that survives re-execution, still
sub-T2 and selection-based"* — is accepted as the accurate status.

---

## 4. Cross-peer consensus (what the final master plan should treat as established)

1. **System verdict FAIL / not money-ready** — all 6 packages agree (0/9, 0/166, 0/6+0/26,
   PF 0.2657 fleet-wide, WR ~41–42%).
2. **Root cause = data integrity + multiple testing**, not tuning (finpredict, finpredict-v2/v3,
   quant-audit, mine).
3. **PnL-unit mix bug** (`dashboard_generator.py:8065-8072`) + **frozen/phantom prices** +
   **zombie EXPIRED picks** = top production defects (multi-peer verified).
4. **No raw-alpha edge proven by anyone.** Only two positive artifacts exist:
   - **variant C** (mine) — reproduced twice, selection-based, sub-T2, open vintage issue;
   - **mega_mutation** (flaxen-hair) — single-source, n<30 strict OOS, ledger disagreement;
   - plus finpredict's *external* TSMOM risk premium (not a system property).
5. **`resolution_method=None` on 1,500→3,500 rows** (quant-audit, confirmed by me) is the single
   fact blocking certification of any PF anywhere.
6. Kilo's VWAP claim: **falsified twice independently** (finpredict-v2 + quant-audit).

## 5. Recommended reconciliation order for the master plan
1. Populate `resolution_method` + close PnL-unit bug (unblocks ALL measurement).
2. Single canonical ledger (fixspec_single_canonical_ledger — my 07) + zombie purge.
3. Re-run every PF claim (incl. variant C, mega_mutation) on the cleaned ledger → one certified number.
4. Forward-only evaluation: variant C weekly (pre-registered, task 5992b142) + mega_mutation
   gated paper pilot — certification only via T2 gates on forward records.
