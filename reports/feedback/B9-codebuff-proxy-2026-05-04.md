# B9 Multi-AI Feedback — Codebuff (Proxy) — 2026-05-04

## Item reviewed
B9 — TradingAgents wire-in (shadow): connect adversarial_debate.apply_to_picks
to the UEPS emitter as a 14-day shadow run (logs only, no filtering).

## A. Confirmed assumptions

1. **apply_to_picks signature confirmed.** `apply_to_picks(picks, *, http_post=None)`
   accepts a list or iterable of pick dicts, returns the same list with adversarial
   fields stamped. The `http_post` param is for injecting test stubs — no change
   needed for production use. The function handles all exceptions internally
   (`except Exception: logger.exception(...)`) so it can never break the host path.

2. **run_screeners return schema is compatible.** `run_screeners` returns a dict with
   key `"long_picks": [list of pick dicts]`. Each pick dict has a `"symbol"` key
   which `score_pick` uses for logging. The schema is compatible with
   `adversarial_debate.score_pick`'s expected keys (`"symbol"`, `"thesis"`,
   `"summary"`, `"asset_class"` — all optional or handled via `.get()`).

3. **14-day shadow interpretation correct.** The module is default-OFF
   (`UEPS_ADVERSARIAL_ENABLED` not set = no-op). Shadow = operator sets the flag to
   observe results for 14 days before deciding to act on `adversarial_keep`. No code
   needed to enforce the shadow window beyond keeping `adversarial_keep` as a
   read-only field that callers don't act on yet.

4. **Correct place to add the call.** Inside `run_screeners()` after line 113
   (`long_picks = long_screener.screen_universe(inputs, top_n=top_n_long)`) and
   before the payload dict is assembled (line 125). This ensures adversarial fields
   flow through to both `ueps_picks.json` (written by `write_payload`) and
   `active_picks.json` (synced by `sync_to_active_picks`).

## B. Surfaced contradictions / blockers

1. **Type annotation risk:** `long_picks` from `ValueScreener.screen_universe` is
   `list[dict]` per the screener module. `apply_to_picks` accepts `list | Iterable`
   and always returns a list. No type issue — caller can just use the returned list
   without re-assigning since the mutation is in-place.

2. **Import cycle risk:** `tools/run_ueps_pickers.py` already imports from
   `alpha_engine.*`. Adding `from alpha_engine import adversarial_debate` follows
   the same pattern — no cycle risk confirmed (adversarial_debate doesn't import
   from tools/).

3. **Provider API key availability in CI:** `apply_to_picks` makes LLM API calls
   only when `UEPS_ADVERSARIAL_ENABLED=1`. In CI this flag is absent, so the call
   is a no-op. No CI secret needed for the integration tests.

## C. Recommended deltas

- Wrap the import in a `try/except ImportError` guard in case adversarial_debate
  has a missing dep in some deployment environments. Alternatively, just import
  at the top of the file as it's already in the same package with no extra deps
  beyond stdlib.
- Add a brief `logger.info("[adversarial] shadow run: %d picks scored, keep=%d/%d", ...)` 
  after the `apply_to_picks` call so the shadow results are visible in the workflow log.

## D. Net verdict: ready-to-ship

Clean ~10-line change. All guardrails already in place. No new infra needed.
