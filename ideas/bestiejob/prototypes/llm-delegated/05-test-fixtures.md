# Delegated task output

- model: `ULTRA_FREE_CLOUD_FAST`
- generated_utc: 2026-11-18T03:57:54Z
- status: ok

## Response

# Test Fixture Job Objects for BESTIEJOB Matcher
## Fixture 1: ServiceNow Body-Only Cert CSA/CAD Match
```json
[
  {
    "title": "ServiceNow Certifications",
    "company": "ServiceNow",
    "location": "Canada",
    "description": "Certified ServiceNow CSA/CAD",
    "url": "https://example.com/servicenow-cert",
    "posted_at": "2023-02-20T14:30:00Z",
    "req_id": "SN-001",
    "hiring_channel": "ServiceNow",
    "active_state": "active"
  }
]
```

## Fixture 2: Salesforce LWC/Apex French Posting Canada-Remote
```json
[
  {
    "title": "Développeur LWC/Apex",
    "company": "Salesforce",
    "location": "Canada-Remote",
    "description": "Développeur LWC/Apex",
    "url": "https://example.com/salesforce-lwc-apex",
    "posted_at": "2023-02-20T14:30:00Z",
    "req_id": "SF-002",
    "hiring_channel": "Salesforce",
    "active_state": "active"
  }
]
```

## Fixture 3: ITSM/CMDB/ITAM-Only Other Role in GTA
```json
[
  {
    "title": "ITSM/CMDB/ITAM Specialist",
    "company": "ITSM/CMDB/ITAM",
    "location": "GTA",
    "description": "ITSM/CMDB/ITAM Specialist",
    "url": "https://example.com/itsm-cmdb-itam",
    "posted_at": "2023-02-20T14:30:00Z",
    "req_id": "IT-003",
    "hiring_channel": "ITSM/CMDB/ITAM",
    "active_state": "active"
  }
]
```

## Fixture 4: Global-Remote Confirm
```json
[
  {
    "title": "Global-Remote Specialist",
    "company": "Global-Remote",
    "location": "Global-Remote",
    "description": "Global-Remote Specialist",
    "url": "https://example.com/global-remote",
    "posted_at": "2023-02-20T14:30:00Z",
    "req_id": "GR-004",
    "hiring_channel": "Global-Remote",
    "active_state": "active"
  }
]
```

## Fixture 5: US-Only Exclusion
```json
[
  {
    "title": "US-Only Exclusion",
    "company": "US-Only",
    "location": "US-Only",
    "description": "US-Only Exclusion",
    "url": "https://example.com/us-only",
    "posted_at": "2023-02-20T14:30:00Z",
    "req_id": "US-005",
    "hiring_channel": "US-Only",
    "active_state": "inactive"
  }
]
```

## Fixture 6: Hybrid Toronto
```json
[
  {
    "title": "Hybrid Specialist",
    "company": "Hybrid",
    "location": "Toronto",
    "description": "Hybrid Specialist",
    "url": "https://example.com/hybrid",
    "posted_at": "2023-02-20T14:30:00Z",
    "req_id": "HY-006",
    "hiring_channel": "Hybrid",
    "active_state": "active"
  }
]
```

## Fixture 7: Stale/Undated Posting
```json
[
  {
    "title": "Stale Posting",
    "company": "Stale",
    "location": "Stale",
    "description": "Stale Posting",
    "url": "https://example.com/stale",
    "posted_at": "1900-01-01T00:00:00Z",
    "req_id": "ST-007",
    "hiring_channel": "Stale",
    "active_state": "inactive"
  }
]
```

## Fixture 8: Duplicate URL/Req_id Case (Provide Two Records)
```json
[
  {
    "title": "Duplicate URL/Req_id",
    "company": "Duplicate",
    "location": "Duplicate",
    "description": "Duplicate URL/Req_id",
    "url": "https://example.com/duplicate",
    "posted_at": "2023-02-20T14:30:00Z",
    "req_id": "DU-008",
    "hiring_channel": "Duplicate",
    "active_state": "active"
  },
  {
    "title": "Duplicate URL/Req_id",
    "company": "Duplicate",
    "location": "Duplicate",
    "description": "Duplicate URL/Req_id",
    "url": "https://example.com/duplicate",
    "posted_at": "2023-02-20T14:30:00Z",
    "req_id": "DU-008",
    "hiring_channel": "Duplicate",
    "active_state": "active"
  }
]
```

## Fixture 9: Agency Undisclosed Client
```json
[
  {
    "title": "Agency Undisclosed Client",
    "company": "Agency Undisclosed",
    "location": "Agency Undisclosed",
    "description": "Agency Undisclosed Client",
    "url": "https://example.com/agency-undisclosed",
    "posted
