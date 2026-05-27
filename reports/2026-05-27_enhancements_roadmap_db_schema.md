---
title: "DB schema proposal: incidents + enhancements → roadmap"
date: 2026-05-27
context: "User asked for a database table to organize incidents/enhancements into an overall roadmap"
---

# Why a DB table (vs the current JSON sidecar)

Today's state:
- **Incidents** live in `audit_dashboard/data/incidents.json` + `incidents_enhancements_feed.json` (JSON, hand-curated, 38 entries)
- **Enhancements** scattered across `reports/MASTER_ACTION_PLAN_2026-05-15.md` (M-001..M-039), `reports/asset_class_90day_plan_*.md` (per-class), `DAILY_IDEAS.MD`, `updates/index.html` cards
- **Roadmap rollup:** nowhere. The same item lives in 3-4 docs; status drift is constant.

A real table gives us:
- One canonical row per item (no more "fixed in PR #X but plan still says PENDING")
- Joinable to PRs (link to gh PR number, merge SHA)
- Joinable to picks (which item closed a regression on which symbol/strategy)
- Time-series view: "show all P0 items opened in May, closed in June" → real velocity tracking
- Auto-populate the `/audit/incidents.html` page instead of hand-curating

# Schema

```sql
CREATE TABLE ejaguiar1_stocks.roadmap_items (
  -- Identity
  item_id            VARCHAR(32)  NOT NULL,   -- e.g. 'M-001', 'INC-P0-007', 'QW-1', 'A1'
  item_kind          ENUM('master_plan','incident','quick_win','workstream','asset_plan','hypothesis') NOT NULL,
  PRIMARY KEY (item_id),

  -- Classification
  severity           ENUM('P0','P1','P2','P3') NOT NULL,
  asset_class        ENUM('CRYPTO','EQUITY','COMMODITY','ETF','FOREX','BOND','FUTURES','PENNY_MEME','UNIVERSAL') NOT NULL,
  workstream         VARCHAR(8) NULL,         -- A1, A2, B1, C1, G1, ... (institutional readiness)

  -- Title + body
  title              VARCHAR(255) NOT NULL,
  body_md            TEXT NULL,               -- full description (markdown)
  rationale_md       TEXT NULL,               -- why it matters / evidence
  source_doc         VARCHAR(255) NULL,       -- 'reports/asset_class_90day_plan_EQUITY_2026-05-15.md' etc.

  -- Lifecycle
  status             ENUM('proposed','approved','in_progress','blocked','done','rejected','superseded') NOT NULL DEFAULT 'proposed',
  blocked_reason     VARCHAR(255) NULL,
  superseded_by      VARCHAR(32) NULL,        -- another item_id

  -- Effort + impact
  effort             ENUM('S','M','L','XL') NULL,
  expected_pf_lift   DECIMAL(6,3) NULL,       -- e.g. +0.57 for 1.0 → 1.57 PF
  measured_pf_lift   DECIMAL(6,3) NULL,       -- post-merge actual
  expected_wr_lift   DECIMAL(5,3) NULL,
  measured_wr_lift   DECIMAL(5,3) NULL,

  -- Files & PRs
  files_touched      JSON NULL,               -- ['alpha_engine/etf_sector_emitter.py', ...]
  related_pr_numbers JSON NULL,               -- [9, 10, 14]
  merge_sha          VARCHAR(40) NULL,
  closed_by_pr       INT NULL,                -- canonical PR that closed it

  -- Gates & approvals
  needs_user_approval BOOLEAN DEFAULT FALSE,
  approval_grantor    VARCHAR(64) NULL,       -- 'eltonaguiar', 'kilo-code-auto', ...
  approval_ts         DATETIME NULL,

  -- Provenance
  proposed_by        VARCHAR(64) NULL,        -- 'kilo-code', 'mimo-v2.5-pro', 'mercury2', 'subagent-D', ...
  proposed_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  done_at            DATETIME NULL,

  -- Cross-references
  parent_item_id     VARCHAR(32) NULL,        -- a quick-win is child of a master-plan item
  related_items      JSON NULL,               -- ['M-008', 'M-021']

  INDEX idx_status_severity (status, severity),
  INDEX idx_asset_class (asset_class),
  INDEX idx_workstream (workstream),
  INDEX idx_proposed_at (proposed_at),
  INDEX idx_done_at (done_at),
  FOREIGN KEY (superseded_by) REFERENCES roadmap_items(item_id),
  FOREIGN KEY (parent_item_id) REFERENCES roadmap_items(item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- Sidecar: per-item history (one row per status change)
CREATE TABLE ejaguiar1_stocks.roadmap_item_history (
  history_id     BIGINT AUTO_INCREMENT PRIMARY KEY,
  item_id        VARCHAR(32) NOT NULL,
  ts             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actor          VARCHAR(64) NOT NULL,      -- agent or username
  field_changed  VARCHAR(64) NOT NULL,
  old_value      VARCHAR(255) NULL,
  new_value      VARCHAR(255) NULL,
  note_md        TEXT NULL,
  FOREIGN KEY (item_id) REFERENCES roadmap_items(item_id),
  INDEX idx_item_ts (item_id, ts)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- Sidecar: per-item review (multiple AI/human reviewers can comment)
CREATE TABLE ejaguiar1_stocks.roadmap_item_reviews (
  review_id      BIGINT AUTO_INCREMENT PRIMARY KEY,
  item_id        VARCHAR(32) NOT NULL,
  reviewer       VARCHAR(64) NOT NULL,     -- e.g. 'subagent-A', 'deepseek-v4', 'eltonaguiar'
  verdict        ENUM('approve','approve_with_notes','needs_changes','reject','defer') NOT NULL,
  body_md        TEXT NULL,
  ts             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (item_id) REFERENCES roadmap_items(item_id),
  INDEX idx_item_reviewer (item_id, reviewer)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

# Seed data — 38 open incidents + 39 master-plan items + 11 quick-wins

Single insert script populates from the existing JSON. Skeleton:

```python
# tools/seed_roadmap_items.py (sketch)
import json, mysql.connector
from pathlib import Path

incidents = json.loads(Path('audit_dashboard/data/incidents.json').read_text())
master = parse_master_action_plan('reports/MASTER_ACTION_PLAN_2026-05-15.md')  # extract M-001..M-039
qw = parse_quick_wins('reports/2026-05-27_quick_wins_from_90day_plans.md')

with conn.cursor() as cur:
    for row in incidents + master + qw:
        cur.execute("""
            INSERT INTO roadmap_items
              (item_id, item_kind, severity, asset_class, title, body_md, source_doc,
               status, effort, related_pr_numbers, proposed_by, needs_user_approval)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              status=VALUES(status), body_md=VALUES(body_md), last_updated_at=NOW()
        """, row.as_tuple())
```

# Views for the dashboard

```sql
-- Active roadmap (open P0/P1, sorted by severity + class)
CREATE OR REPLACE VIEW v_roadmap_active AS
SELECT item_id, severity, asset_class, title, status, effort,
       expected_pf_lift, files_touched, related_pr_numbers,
       last_updated_at
FROM roadmap_items
WHERE status IN ('proposed','approved','in_progress','blocked')
  AND severity IN ('P0','P1')
ORDER BY FIELD(severity,'P0','P1'), FIELD(asset_class,'CRYPTO','EQUITY','COMMODITY','ETF','FOREX','BOND','FUTURES','PENNY_MEME','UNIVERSAL');

-- Velocity (items closed by month)
CREATE OR REPLACE VIEW v_roadmap_velocity AS
SELECT DATE_FORMAT(done_at, '%Y-%m') AS month,
       severity,
       asset_class,
       COUNT(*) AS closed_count,
       AVG(measured_pf_lift) AS avg_measured_lift
FROM roadmap_items
WHERE status = 'done'
GROUP BY DATE_FORMAT(done_at, '%Y-%m'), severity, asset_class;

-- Blocked items (need attention)
CREATE OR REPLACE VIEW v_roadmap_blocked AS
SELECT item_id, severity, asset_class, title, blocked_reason, last_updated_at
FROM roadmap_items
WHERE status = 'blocked'
ORDER BY FIELD(severity,'P0','P1','P2','P3'), last_updated_at;
```

# Dashboard wiring

- `audit_dashboard/template.html` adds a `<section id="roadmap">` that fetches `/audit/data/roadmap_active.json` (generated nightly from `v_roadmap_active`).
- Existing `incidents.html` page becomes a filtered view: `WHERE item_kind = 'incident'`.
- New `enhancements.html`: `WHERE item_kind IN ('master_plan','quick_win','workstream','asset_plan')`.
- Roadmap page renders the same data grouped by `workstream`, with merge-tracker links to GitHub PRs.

# Approval gates this enables (machine-readable)

Today CLAUDE.md says "explicit user approval required" for BLOCKED_* edits. A DB row makes that auditable:

```sql
-- Was the PENNY_STOCK gate approved before the gate landed?
SELECT item_id, status, approval_grantor, approval_ts, closed_by_pr
FROM roadmap_items
WHERE item_id = 'QA-1';
-- If status='done' but approval_ts IS NULL → audit failure, raise alarm
```

CI hook: any PR touching `quality_gates.BLOCKED_*` rejects unless its body cites a `roadmap_items.item_id` with `approval_ts IS NOT NULL`.

# What this does NOT do

- Doesn't replace `reports/MASTER_ACTION_PLAN_2026-05-15.md` — that doc stays as the human-readable rationale source. The DB table is the operational state.
- Doesn't replace `hypothesis_registry.json` — hypotheses have their own pre-registration discipline. A `roadmap_items.item_kind='hypothesis'` row would link via `item_id = hypothesis_id`.
- Doesn't auto-close items — closure remains explicit (a PR or operator action sets `status='done'`).

# Implementation cost

- Schema: 3 tables + 3 views = ~120 lines of SQL
- Seed script: ~150 lines of Python (parses 4 file formats, writes ~88 rows)
- Dashboard JSON sidecar generator: ~80 lines added to `audit_trail/dashboard_generator.py`
- CI approval-gate hook: ~30 lines bash

**Total ~2-3 hours of focused work.** Recommend doing it AFTER the foundation-fix PRs land — so the seed data isn't already wrong by the time it's written.

# Recommended item_id scheme

| Prefix | Source | Example |
|---|---|---|
| `M-NNN` | Master action plan | `M-001` (BTC hour filter) |
| `INC-P0-NNN` | Incidents page | `INC-P0-007` (forward validator frozen) |
| `QW-N` | Quick wins doc | `QW-1` (EQUITY VIX gate) |
| `QA-N` | Quick wins pending approval | `QA-1` (PENNY_STOCK gate) |
| `WS-X` | Workstream (institutional) | `WS-A1` (freshness SLA) |
| `H-NNN` | Hypothesis registry | `H-010` (EQUITY PEAD — REJECTED) |

This makes the cross-references already used in the 90-day plans actually link-traversable in the table.
