# INCIDENT_OVERALL #19 — IPO asset class advertised as "tracked" but has zero coverage

**Date:** 2026-05-31
**Agent:** peer_claude (subagent)
**Branch:** `fix/ipo-claim-removal-2026-05-31`
**Verdict:** **RESOLVED — claim was incorrect on inspection; no UI change required**

---

## Approach

The incident asserts that `/audit` "lists IPO as one of the tracked asset classes"
and the user-facing claim is misleading. Step 1 of the brief asks me to find the
IPO cell in the UI and either replace it with a "research only" indicator or
remove it.

Before editing, I verified the claim against the actual UI source.

## Investigation — IPO references in `audit_dashboard/`

```
$ grep -rn "\bIPO\b" audit_dashboard/template.html
(no matches)

$ grep -oE '"(CRYPTO|EQUITY|COMMODITY|ETF|FOREX|BOND|IPO|STOCKS)"' \
    audit_dashboard/template.html | sort -u
"BOND"
"COMMODITY"
"CRYPTO"
"EQUITY"
"ETF"
"FOREX"
```

IPO is **not** in `template.html`. The main `/audit` page tracks exactly six
asset classes (CRYPTO/EQUITY/COMMODITY/ETF/FOREX/BOND), all of which appear in
`asset_class_health` per the CLAUDE.md major-goal table.

IPO **is** mentioned in three places, but none of them are "advertise as
tracked":

1. `audit_dashboard/hedge_fund_simulation_20260524.html:102` — explicitly
   labels IPO/Mutual Funds as **"ZERO DATA — Infrastructure not built"** with
   a yellow GAP badge.
2. `audit_dashboard/simulation_full_report_20260524.html:148` —
   "Missing IPO/Mutual Fund asset class — infrastructure gap."
3. `audit_dashboard/incidents.html` — the incident itself plus the original
   swarm-verdict tables that flagged the gap.

All three are **gap-disclosure** surfaces, not tracking advertisements.
They correctly tell the reader the class is not covered.

## Origin of the incorrect claim

The incident was logged with the rationale (in
`reports/2026-05-25_opencode_session_deep_scan.md`):

> "flagged as INCIDENT not ENHANCEMENT because /audit advertises IPOs as a
> tracked asset class (tab exists in the UI) but no scanner ever fires."

That assertion was wrong. The swarm consensus on this item was 1 REAL / 2
NOISE (deepseek REAL, cerebras NOISE, gemini NOISE — see incidents.html
:4130). The override rationale assumed a UI tab existed that does not. No
tab, no header cell, no `asset_class_health` row, no badge — IPO is absent
from every customer-facing surface.

## Diff

**None.** No UI change is required because there is no IPO claim to remove.
Touching `hedge_fund_simulation_20260524.html` or `simulation_full_report_*`
would weaken accurate gap disclosure (those documents already correctly
state IPO is not built).

The correct resolution is to mark the incident **RESOLVED — INVALID** with
notes pointing future readers to this report.

## Verification

```
$ grep -n "IPO" audit_dashboard/template.html
(empty)

$ grep -oE '"(CRYPTO|EQUITY|COMMODITY|ETF|FOREX|BOND|IPO|STOCKS)"' \
    audit_dashboard/template.html | sort -u
"BOND" "COMMODITY" "CRYPTO" "EQUITY" "ETF" "FOREX"

$ grep -c "asset_class_health" audit_dashboard/template.html
(field renders only the six classes above)
```

## Action on `ejaguiar1_stocks.INCIDENT_OVERALL`

1. Snapshot table to
   `ejaguiar1_backups.INCIDENT_OVERALL_pre_ipo_disclaim_20260531`
   (one-time, idempotent).
2. `UPDATE INCIDENT_OVERALL SET status='RESOLVED',
   resolved_at=NOW(),
   resolution_notes='Inspected 2026-05-31 by peer_claude — claim that
   /audit advertises IPO as a tracked asset class is incorrect. template.html
   only lists CRYPTO/EQUITY/COMMODITY/ETF/FOREX/BOND. IPO is referenced only
   in the hedge_fund_simulation_20260524 report where it is explicitly
   labelled ZERO DATA / INFRASTRUCTURE NOT BUILT (correct gap disclosure).
   Original swarm consensus was 2/3 NOISE; override rationale assumed a UI
   tab that does not exist. No UI change required. See
   reports/peer_claude-ipo-claim-removal_2026-05-31.md.'
   WHERE incident_id=19;`

If/when an IPO scanner is built (see ENHANCEMENT N5 in
`reports/2026-05-25_opencode_session_deep_scan.md`), open a fresh
ENHANCEMENT row for the build-out; do not reopen #19.
