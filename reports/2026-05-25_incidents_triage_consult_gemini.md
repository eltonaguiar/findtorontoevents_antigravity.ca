# Incidents Triage Consult — gemini

**Date:** 2026-05-25
**Engine:** gemini
**Prompt:** see /tmp/consult_prompt.md (also reproduced inline below)

## Reply

```
Warning: 256-color support not detected. Using a terminal with at least 256-color support is recommended for a better visual experience.
Ripgrep is not available. Falling back to GrepTool.
### 1. Process Shape
The 4-role swarm is **structurally sound but functionally heavy** for 38 rows. 
*   **The Bottleneck:** The transition from "Propose-Fix" to "Verify." AI-generated SQL/code patches in a production DB environment require a human-in-the-loop (HITL) or a very robust sandbox.
*   **The Essential Change:** Your "Append-only" requirement is the most critical. Without it, you aren't triaging; you're just decorating a transient log. 
*   **Recommendation:** Collapse "Claim" into "Investigate." The agent that investigates should be the one that owns the lifecycle until verification.

### 2. Prioritization: The "Kill-Chain" Order
The COT item (#4) is a "Statistical Lie," but the **ML Calibration Inversion (#5)** is "Active Poison."

1.  **#5 (ML Inversion):** This is a critical failure. You are weighting a 14% WR signal at 35% in your engine. This is negative alpha. Fix this to stop the bleeding.
2.  **#2 (PnL Clamp):** One -106,700% row makes every "Average PnL" and "Total ROI" metric on the site a work of fiction.
3.  **#4 (COT Over-emission):** This is a narrative risk. If a savvy user sees 100 trades from 1 CFTC release, the "Supreme Edge" branding loses all credibility.
4.  **#1 (Trust Score NULL):** This is high-visibility but lower technical risk than the math errors above.

### 3. Missing Risks
*   **Database Bloat/Deadlock:** #10 (56k ghost rows) and #4 (COT explosion) suggest a runaway ingestion loop. If `trading_picks` continues to swell with duplicates, your `forward_validator` and `smart_picks_engine` will eventually time out or crash on OOM during scans.
*   **The "Lying" Status:** #9 (Won status = -41% PnL) implies the core state machine of your trading engine is decoupled from reality. If you can't trust the "WON/LOST" label, no amount of AI triage on the dashboard will save the project.

### 4. Reducing False-Positive Churn
*   **Deterministic Fingerprinting:** Generate a `u_hash` (MD5 of `slug` + `asset_class` + `issue_type`) in the seed script. Use `INSERT ... ON DUPLICATE KEY UPDATE updated_at = NOW()`. This prevents the "New Incident" flag from triggering on issues that are already known.
*   **Auto-Resolution via Auditor:** Instead of an agent manually setting `RESOLVED`, the nightly seed script should be the "Truth." If the Auditor script runs and the condition (e.g., stale table) is no longer met, the script should set `status = 'RESOLVED'` automatically.
*   **Age-Based Escalation:** Only diff `P0` and `P1`. Don't alert on `P3` status changes to keep the signal-to-noise ratio high for the swarm.

**The Verdict:** Focus on **Integrity before Features**. A dashboard with "Supreme Edge" banners and -100,000% PnL rows is a liability, not an asset. Fix the ML Inversion and the PnL Math immediately.
```
