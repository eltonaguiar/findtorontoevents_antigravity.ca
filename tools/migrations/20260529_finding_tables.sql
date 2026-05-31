-- Migration: create FINDING_<CLASS> tables for the FINDINGS subsystem.
--
-- One table per asset class (mirrors the existing INCIDENT_<CLASS> /
-- ENHANCEMENT_<CLASS> pattern). IDE agents (Claude, Grok, Cursor, etc.) log
-- dated findings here via tools/audit_pick_funnel/cli_track.py finding ...,
-- and they render on audit_dashboard/incidents.html (the public surface at
-- findtorontoevents.ca/audit/incidents.html). Times stored UTC, rendered EST.
--
-- Idempotent: CREATE TABLE IF NOT EXISTS. Safe to re-run.
-- Target DB: ejaguiar1_stocks on mysql.50webs.com.

CREATE TABLE IF NOT EXISTS FINDING_OVERALL (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    severity ENUM('P0','P1','P2','P3','INFO','NOTEWORTHY') NOT NULL DEFAULT 'INFO',
    status ENUM('OPEN','INVESTIGATING','CONFIRMED','RESOLVED','WONTFIX') NOT NULL DEFAULT 'OPEN',
    agent VARCHAR(80) NULL,
    evidence TEXT NULL,
    linked_incident_id INT NULL,
    linked_enhancement_id INT NULL,
    created_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_title (title),
    INDEX ix_status (status),
    INDEX ix_severity (severity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS FINDING_STOCKS (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    severity ENUM('P0','P1','P2','P3','INFO','NOTEWORTHY') NOT NULL DEFAULT 'INFO',
    status ENUM('OPEN','INVESTIGATING','CONFIRMED','RESOLVED','WONTFIX') NOT NULL DEFAULT 'OPEN',
    agent VARCHAR(80) NULL,
    evidence TEXT NULL,
    linked_incident_id INT NULL,
    linked_enhancement_id INT NULL,
    created_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_title (title),
    INDEX ix_status (status),
    INDEX ix_severity (severity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS FINDING_ETFS (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    severity ENUM('P0','P1','P2','P3','INFO','NOTEWORTHY') NOT NULL DEFAULT 'INFO',
    status ENUM('OPEN','INVESTIGATING','CONFIRMED','RESOLVED','WONTFIX') NOT NULL DEFAULT 'OPEN',
    agent VARCHAR(80) NULL,
    evidence TEXT NULL,
    linked_incident_id INT NULL,
    linked_enhancement_id INT NULL,
    created_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_title (title),
    INDEX ix_status (status),
    INDEX ix_severity (severity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS FINDING_CRYPTO (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    severity ENUM('P0','P1','P2','P3','INFO','NOTEWORTHY') NOT NULL DEFAULT 'INFO',
    status ENUM('OPEN','INVESTIGATING','CONFIRMED','RESOLVED','WONTFIX') NOT NULL DEFAULT 'OPEN',
    agent VARCHAR(80) NULL,
    evidence TEXT NULL,
    linked_incident_id INT NULL,
    linked_enhancement_id INT NULL,
    created_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_title (title),
    INDEX ix_status (status),
    INDEX ix_severity (severity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS FINDING_FOREX (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    severity ENUM('P0','P1','P2','P3','INFO','NOTEWORTHY') NOT NULL DEFAULT 'INFO',
    status ENUM('OPEN','INVESTIGATING','CONFIRMED','RESOLVED','WONTFIX') NOT NULL DEFAULT 'OPEN',
    agent VARCHAR(80) NULL,
    evidence TEXT NULL,
    linked_incident_id INT NULL,
    linked_enhancement_id INT NULL,
    created_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_title (title),
    INDEX ix_status (status),
    INDEX ix_severity (severity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS FINDING_COMMODITIES (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    severity ENUM('P0','P1','P2','P3','INFO','NOTEWORTHY') NOT NULL DEFAULT 'INFO',
    status ENUM('OPEN','INVESTIGATING','CONFIRMED','RESOLVED','WONTFIX') NOT NULL DEFAULT 'OPEN',
    agent VARCHAR(80) NULL,
    evidence TEXT NULL,
    linked_incident_id INT NULL,
    linked_enhancement_id INT NULL,
    created_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_title (title),
    INDEX ix_status (status),
    INDEX ix_severity (severity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS FINDING_BONDS (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    severity ENUM('P0','P1','P2','P3','INFO','NOTEWORTHY') NOT NULL DEFAULT 'INFO',
    status ENUM('OPEN','INVESTIGATING','CONFIRMED','RESOLVED','WONTFIX') NOT NULL DEFAULT 'OPEN',
    agent VARCHAR(80) NULL,
    evidence TEXT NULL,
    linked_incident_id INT NULL,
    linked_enhancement_id INT NULL,
    created_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_title (title),
    INDEX ix_status (status),
    INDEX ix_severity (severity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS FINDING_FUTURES (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    severity ENUM('P0','P1','P2','P3','INFO','NOTEWORTHY') NOT NULL DEFAULT 'INFO',
    status ENUM('OPEN','INVESTIGATING','CONFIRMED','RESOLVED','WONTFIX') NOT NULL DEFAULT 'OPEN',
    agent VARCHAR(80) NULL,
    evidence TEXT NULL,
    linked_incident_id INT NULL,
    linked_enhancement_id INT NULL,
    created_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_title (title),
    INDEX ix_status (status),
    INDEX ix_severity (severity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS FINDING_PENNY (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    severity ENUM('P0','P1','P2','P3','INFO','NOTEWORTHY') NOT NULL DEFAULT 'INFO',
    status ENUM('OPEN','INVESTIGATING','CONFIRMED','RESOLVED','WONTFIX') NOT NULL DEFAULT 'OPEN',
    agent VARCHAR(80) NULL,
    evidence TEXT NULL,
    linked_incident_id INT NULL,
    linked_enhancement_id INT NULL,
    created_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_title (title),
    INDEX ix_status (status),
    INDEX ix_severity (severity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
