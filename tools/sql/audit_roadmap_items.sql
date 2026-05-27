-- audit_roadmap_items — unified incidents/enhancements/roadmap registry (EAGLE 2026-05-27)
-- Database: ejaguiar1_stocks
-- Apply: mysql ejaguiar1_stocks < tools/sql/audit_roadmap_items.sql

CREATE TABLE IF NOT EXISTS audit_roadmap_items (
  id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  item_type           ENUM('INCIDENT','ENHANCEMENT','STRATEGY','MILESTONE') NOT NULL,
  asset_class         VARCHAR(32) NOT NULL DEFAULT 'OVERALL',
  priority            ENUM('P0','P1','P2','P3') NOT NULL DEFAULT 'P2',
  status              ENUM('OPEN','IN_PROGRESS','BLOCKED','DONE','WONT_FIX') NOT NULL DEFAULT 'OPEN',
  m_number            VARCHAR(16) NULL,
  title               VARCHAR(255) NOT NULL,
  description         TEXT,
  affected_component  VARCHAR(255),
  recommended_fix     TEXT,
  success_metric      VARCHAR(512),
  evidence_path       VARCHAR(512),
  github_pr_url       VARCHAR(512),
  source_report       VARCHAR(255),
  depends_on_id       INT UNSIGNED NULL,
  assigned_to         VARCHAR(64),
  reported_by         VARCHAR(64),
  created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  resolved_at         DATETIME NULL,
  UNIQUE KEY uq_roadmap_title_class (title(191), asset_class),
  INDEX idx_class_status (asset_class, status),
  INDEX idx_priority (priority, status),
  INDEX idx_m_number (m_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS audit_roadmap_item_links (
  roadmap_id    INT UNSIGNED NOT NULL,
  link_type     ENUM('MD','URL','GITHUB','INCIDENT_DUP') NOT NULL,
  link_value    VARCHAR(1024) NOT NULL,
  PRIMARY KEY (roadmap_id, link_type, link_value(191)),
  CONSTRAINT fk_roadmap_links FOREIGN KEY (roadmap_id) REFERENCES audit_roadmap_items(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
