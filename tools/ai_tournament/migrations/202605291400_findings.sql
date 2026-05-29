-- FINDINGS table — dated, agent-logged observations surfaced on /audit/incidents.html.
-- Single table (NOT per-class like INCIDENT_*/ENHANCEMENT_*): findings are
-- cross-cutting, date/time-ordered "noteworthy" notes, optionally linked to an
-- incident or enhancement. asset_class is nullable (NULL = OVERALL/cross-cutting).
--
-- created_at stores UTC-naive (server is UTC); EST is derived at render time by
-- render_incidents_page.py::created_est(). DO NOT store EST in the DB.
--
-- Apply manually (NOT auto-applied by any generator):
--   DB_PASS_STOCKS=*** mysql -h mysql.50webs.com -u ejaguiar1_stocks ejaguiar1_stocks \
--     < tools/ai_tournament/migrations/202605291400_findings.sql
-- Idempotent (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS FINDINGS (
  finding_id            INT NOT NULL AUTO_INCREMENT,
  asset_class           VARCHAR(20)  DEFAULT NULL,                 -- NULL = OVERALL/cross-cutting
  source_agent          VARCHAR(100) DEFAULT NULL,                 -- which AI/IDE agent logged it
  finding_type          ENUM('OBSERVATION','METRIC','LEAKAGE','CORRELATION','RISK','DATA_QUALITY','OTHER') NOT NULL DEFAULT 'OBSERVATION',
  severity              ENUM('P0','P1','P2','P3','INFO') NOT NULL DEFAULT 'INFO',
  title                 VARCHAR(500) NOT NULL,
  detail                TEXT DEFAULT NULL,
  evidence              JSON DEFAULT NULL,                         -- {file:line, query, numbers} — claimed, not verified
  status                ENUM('OPEN','TRIAGED','ACK','ARCHIVED','SUPERSEDED') NOT NULL DEFAULT 'OPEN',
  noteworthy            TINYINT(1) NOT NULL DEFAULT 0,             -- pin to top of the findings feed
  linked_incident_id    INT DEFAULT NULL,                         -- optional FK-by-convention to INCIDENT_*.incident_id
  linked_enhancement_id INT DEFAULT NULL,                         -- optional FK-by-convention to ENHANCEMENT_*.enhancement_id
  link_md_path          VARCHAR(500)  DEFAULT NULL,
  link_url              VARCHAR(1000) DEFAULT NULL,
  link_github_ref       VARCHAR(255)  DEFAULT NULL,
  created_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,   -- UTC-naive; render layer converts to EST
  updated_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (finding_id),
  KEY idx_fi_status_sev  (status, severity),
  KEY idx_fi_noteworthy  (noteworthy, created_at),
  KEY idx_fi_class       (asset_class),
  KEY idx_fi_created     (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
