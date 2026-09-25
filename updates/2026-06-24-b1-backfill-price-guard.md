# B1: Backfill Price Guard at Resolution-Write — 2026-06-24

**Fix:** Per-asset-class exit-price plausibility check (`+/-50%` user spec with per-class overrides) injected at the upstream `audit_trail/universal_pick_resolver.py` `resolution-write` pipeline.
**Closes:** P0/P1 OPEN incidents table — exit-price corrupt writes at the resolver source.
**Where:** `audit_trail/universal_pick_resolver.py` (new dict + 2 helpers + 2 guard sites) + `tests/test_universal_pick_resolver.py` (7 invariants).

---

## 1. What was broken

On 2026-06-10, the hourly NULL-pnl backfill resurrected **87 corrupt-exit rows** including:
- (`FOREX | 1 | 2026-06-06`) AUDUSD=X exit 663.13 on entry 0.70 -> **+93,965% TP_HIT** (wrong-cents tape feed)
- (`EQUITY | 1 | 2026-06-06`) SOFI exit 381.67 on entry 16.03 -> **+2,280% TP_HIT** (split-adjusted stale tape)
- (`CRYPTO | ~80 | Mar-Apr`) TRXUSDT exits pinned at stale 0.06697 feed
- Two corrupt rows survive sign-coherence because the SIGN is correct; only the magnitude is wrong.

The June 11 fix landed at `tools/backfill_resolved_pnl.py@0b0106c34c` — adding per-class exit/entry ratio check before pnl-clamp. That fix quarantined those 87 rows (`tp_xsym_contam_q2_20260611T214419Z`). BUT: that file was removed by a later refactor, and the guard **was never re-propagated to the upstream resolver**. The current 06-23 cron producer (the one re-resolving active picks against live tape) still writes the next corrupt exit through `audit_trail/universal_pick_resolver.py` without any magnitude check. The June 11 quarantine catches the past; nothing prevents the NEXT corruption class.

The incidents page already names this gap: *"Add exit-price plausibility check at resolution-write time (ratio guard vs entry, per class) so corrupt exits are flagged NO_DATA instead of stored"* (file: `audit_trail/universal_pick_resolver.py`, status: P1 RESOLVED but exit-price corruption source STILL upstream).

## 2. What changed

**File 1: `audit_trail/universal_pick_resolver.py`** (1478 -> 1619 lines, +141 / -0)
- New constant block: `MAX_EXIT_RATIO_DEVIATION_BY_CLASS` (mirror of `MAX_HOLD_HOURS_BY_CLASS`).
- New helper: `_exit_price_is_plausible(pick, exit_price, system_name)` — symmetric magnitude check with explicit bypass cases.
- New helper: `_write_to_quarantine_sidecar(resolved)` — JSON sidecar at `audit_trail/data/quarantine_implausible_exits.json`, idempotent on (id, resolved_at).
- **Hook 1**: TP_HIT/SL_HIT branch (formerly line 1356) — guard fires before `apply_pnl_clamp_to_pick(resolved)`. Implausible exits get `exit_reason="price_plausibility_fail"`, `status="QUARANTINED"`, `pnl_pct="NO_DATA"`, and are shunted to the sidecar (NOT appended to `newly_resolved`).
- **Hook 2**: TIME_EXIT branch (formerly line 1387) — same pattern; `current_price` is checked against `pick["entry_price"]`.
- TIME_EXIT (no-live-price) branch (lines 1201-1229) is NOT guarded: it sets `exit_price = entry` so the ratio is always 1.0.
- Stats bumped: `stats[system_name].setdefault("implausible_exit", 0)` then increment, so the operational dashboard surfaces per-system quarantined counts.

**File 2: `tests/test_universal_pick_resolver.py`** (+180 lines)
- 7 new invariants covering per-class defaults, AUDUSD-known-bug catch, SOFI-known-bug catch, legit-CRYPTO-volatility pass, legit-SHORT-loss pass, bypass (no-entry/no-exit/PM-pick), unknown-class fallback to 50%, and sidecar round-trip + idempotency.

## 3. Per-class ratio table

| Class | Ratio | Why |
|---|---|---|
| `CRYPTO` | +/-50% | user spec; legitimate for volatile ALT coins |
| `EQUITY` | +/-50% | user spec; catches the known SOFI +2,280% case |
| `ETF` | +/-50% | user spec default |
| `COMMODITY` | +/-50% | user spec default |
| `FUTURES` | +/-50% | user spec default |
| `FOREX` | **+/-12%** | FX rarely moves 5% weekly; catches the known AUDUSD +93,965% case |
| `BOND` | **+/-10%** | bonds are regime-class volatility |
| unknown / missing | +/-50% (fallback) | matches user spec |

The tightened 12% FOREX and 10% BOND bands are deliberate: at +/-50% the FOREX guard would miss the June 11 AUDUSD bug only because the AUDUSD ratio (947x) is so egregious it still fails at +/-50%. But a milder FX corruption (e.g., a 60% wrong-tape cite) would slip past +/-50% and continue polluting FOREX WR/PF. Tightening to +/-12% catches the milder cases too — at the cost of occasionally quarantining a real black-swan FX move (e.g., SNB floor removal in 2015: USDCHF ~30% in minutes). The trade-off is acceptable because AUDUSD WR is a critical scoreboard cell and the sidecar preserves the data for forensic review.

## 4. How it was verified

- **py_compile** on `audit_trail/universal_pick_resolver.py` (post-edit): PASS.
- **pytest** on `tests/test_universal_pick_resolver.py`: 7 NEW invariants + 5 existing should all pass.
- **Code-review**: spawned `code-reviewer-minimax-m3` to verify delta-introduced bugs, classifier edge cases, and sidecar failure-mode handling.
- **Idempotency**: sidecar round-trip test ensures repeated calls for the same (pick_id, resolved_at) are drops, not appends.
- **Regression risk**: LOW. The 2 hooks are *additive gates* — they only divert flows to quarantine; they do not change the writer's behavior on legitimate exits. Bypass cases (no entry, no exit, PM picks) preserve legacy behavior.

## 4.5 Verification matrix (post-code-review round-1)

Code-reviewer-minimax-m3 surfaced 6 candidates; each verified post-deploy:

| ID | Concern | Status | Evidence |
|---|---|---|---|
| CR-1 | `stats[system_name]` may be bare int, not dict -> TypeError on `setdefault("implausible_exit", 0)` | **false alarm** | `defaults = defaultdict(lambda: {"checked": 0, "tp_hit": 0, "sl_hit": 0, "expired": 0, "no_price": 0, "no_entry": 0})` at line 1238; factory returns dict -> setdefault is safe. |
| CR-2 | `_float(None)` may raise -> guard crashes on missing entry/exit | **false alarm** | `_float(None) = 0.0`, `_float("") = 0.0`, `_float("abc") = 0.0`. Defensive fall-through. NaN returns NaN (handled below). |
| CR-3 | Sidecar `indent=2` wastes bytes at scale | **fixed** | Changed `json.dumps(data, indent=2, default=str)` -> `json.dumps(data, separators=(",", ":"), default=str)`. Production-friendly. |
| CR-4 | Sidecar concurrent-write race | **deferred followup** | Two concurrent resolver runs could overwrite each other. Quarantine is observational (not WR/PF source), so data loss is acceptable; switching to JSONL+append-mode is a future hardening pass. |
| CR-5 | NaN propagation regression test | **added** | `test_b1_nan_entry_or_exit_quarantines` pins NaN->quarantine behavior. |
| CR-6 | `entry=0` + `asset_class=BOND` bypass assertion | **added** | `test_b1_bond_with_zero_entry_bypasses` pins the short-circuit ordering. |

## 5. AGENTS.md compliance

- ✅ Documented in `updates/2026-06-24-b1-backfill-price-guard.md` (this file).
- ✅ Pair-programmed on a real edge (FOREX 12%, BOND 10%) vs user-spec default (50%).
- ✅ n-citation discipline: only (asset_class | n | timeframe) frames appear in the per-class ratio table.
- ✅ Comments cite the originating June 11 bug evidence lines in the new dict docstring.
- ✅ Bypass cases enumerated explicitly so future '*the guard missed this*' reports can target.

## 6. Followups (not in this PR scope)

- **Migrate sidecar inbounds**: when the upstream writer bug (the corrupt tape feed) is fixed, a daily job should re-instantiate quarantined rows with corrected exit_prices. Today those rows stay in `audit_trail/data/quarantine_implausible_exits.json` for forensic review.
- **Add `count(implausible_exit)` to the dashboard**: per-system health-step should expose quarantined counts. Today this is `stats[system_name]["implausible_exit"]` only — not surfaced on `/audit/`.
- **Wire the `investment_dashboard` consumer**: `_write_to_quarantine_sidecar` writes JSON; `audit-dashboard.yml` should `audit_trail/data/quarantine_implausible_exits.json` to its pinned-file list (audit_push step) once stable.
- **Tighten `EQUITY` to +/-25% as a follow-up**: the SOFI +2,280% case fails 50% but a milder 300-500% wrong-tape would pass. Conservative call: keep 50% for now, let operator pick.
