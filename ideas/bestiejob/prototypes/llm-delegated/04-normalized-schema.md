# Delegated task output

- model: `ULTRA_FREE_CLOUD_LARGE`
- generated_utc: 2026-11-18T03:56:27Z
- status: ok

## Response

```markdown
# BESTIEJOB Normalized Job Schema v1.0

## 1. JSON Schema-like Object

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["job_id", "dedupe_key", "source", "title", "company", "posted_at", "liveness"],
  "properties": {
    "job_id": { "type": "string", "format": "uuid" },
    "dedupe_key": { "type": "string", "description": "SHA-256 of canonical fields" },
    "source": {
      "type": "object",
      "properties": {
        "adapter": { "type": "string" },
        "board": { "type": "string" },
        "scan_id": { "type": "string" },
        "provenance": { "type": "string" }
      }
    },
    "urls": {
      "type": "object",
      "properties": {
        "posting": { "type": "string", "format": "uri" },
        "apply": { "type": "string", "format": "uri" },
        "corroborating": { "type": "array", "items": { "type": "string", "format": "uri" } }
      }
    },
    "employer": {
      "type": "object",
      "properties": {
        "name": { "type": "string" },
        "client": { "type": "string" },
        "hiring_channel": { "type": "string", "enum": ["direct", "agency", "rpo", "vendor"] }
      }
    },
    "title": { "type": "string" },
    "location": {
      "type": "object",
      "properties": {
        "raw": { "type": "string" },
        "city": { "type": "string" },
        "region": { "type": "string" },
        "country": { "type": "string" },
        "lat": { "type": "number" },
        "lon": { "type": "number" },
        "remote": { "type": "boolean" },
        "eligibility": { "type": "string", "enum": ["local", "canada", "global"] }
      }
    },
    "posted_at": {
      "type": "object",
      "properties": {
        "absolute": { "type": "string", "format": "date-time" },
        "time_field": { "type": "string" },
        "source": { "type": "string" }
      }
    },
    "valid_through": { "type": "string", "format": "date-time" },
    "req_id": { "type": "string" },
    "description": {
      "type": "object",
      "properties": {
        "full": { "type": "string" },
        "snippet": { "type": "string" }
      }
    },
    "tracks": {
      "type": "object",
      "properties": {
        "platform": { "type": "string", "enum": ["ServiceNow", "Salesforce", "Other"] },
        "domain": { "type": "string", "enum": ["ITSM", "CMDB", "ITAM", "Other"] },
        "certs": { "type": "array", "items": { "type": "string" } },
        "match_evidence": { "type": "array", "items": { "type": "string" } }
      }
    },
    "liveness": {
      "type": "object",
      "properties": {
        "state": { "type": "string", "enum": ["live", "dead", "unknown"] },
        "last_checked": { "type": "string", "format": "date-time" },
        "access": { "type": "string", "enum": ["public", "login", "paywall", "removed"] }
      }
    },
    "rights": {
      "type": "object",
      "properties": {
        "reuse": { "type": "boolean" },
        "license": { "type": "string" }
      }
    }
  }
}
```

## 2. Example Normalized Record

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "dedupe_key": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
  "source": {
    "adapter": "linkedin_api",
    "board": "linkedin",
    "scan_id": "scan_20241201_143022",
    "provenance": "https://linkedin.com/jobs/123456789"
  },
  "urls": {
    "posting": "https://linkedin.com/jobs/123456789",
    "apply": "https://company.com/careers/apply/98765",
    "corroborating": ["https://indeed.com
