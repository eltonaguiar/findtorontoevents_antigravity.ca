# Delegated task output

- endpoint: `http://192.168.2.32:1234/v1/chat/completions`
- model: `mistralai/ministral-3-3b`
- generated_utc: 2026-11-18T03:54:22Z
- status: ok

## Response

Here’s a **minimal normalized schema** for `BESTIEJOB` ingestion, designed to streamline scan → verify → deduplicate → inbox merge workflows while preserving provenance.

---

### **Core Schema (JSON)**
```json
{
  "job": {
    "id": "string",                     # Unique identifier (e.g., UUID or hash)
    "url": ["string"],                  # Primary URL (can be multiple if scraped from redirects)
    "source_url": "string",             # Original source URL (if different from `url`)
    "req_id": "string",                 # Reference ID (e.g., LinkedIn job ID, SF/ITSM ticket ref)

    "company": {
      "name": "string",
      "sector": ["string"],              # Optional: e.g., ["Tech", "Finance"]
      "geo": {                           # Geo metadata
        "country": "string",
        "region": "string",
        "city": "string",
        "latitude": number,             # Lat/Long for proximity checks
        "longitude": number
      }
    },

    "position": {
      "title": "string",                # Job title
      "remote_eligibility": ["boolean"],# [True, False, Unknown] (e.g., "Hybrid" → `Unknown`)
      "is_remote": boolean              # Boolean flag (not eligibility)
    },

    "posting": {
      "posted_at": "timestamp",         # ISO 8601 or Unix epoch
      "source": {                       # Source metadata
        "name": "string",                # e.g., "LinkedIn", "Indeed"
        "platform": "string",            # e.g., "SF", "ITSM", "SN"
        "adapter": "string"             # e.g., "scraper", "API", "webhook"
      },
      "certs": ["string"]               # Certifications (e.g., ["ISO 27001", "HIPAA"])
    },

    "content": {
      "description": "string",          # Full job description
      "snippet": "string"                # Shortened/key phrase (for deduplication)
    },

    "tracks": ["string"],               # Categorization (e.g., ["SN/SF", "ITAM"])
    "liveness": boolean,                 # Is the link active? (True/False/Unknown)

    "evidence": {                        # Provenance
      "scrape": {
        "timestamp": "timestamp",
        "status": "string"              # e.g., "success", "failed"
      },
      "dedupe_keys": ["string"]         # Hashes for deduplication (e.g., `snippet + url`)
    }
  },

  "metadata": {                         # Optional: Board-specific metadata
    "board_id": "string",
    "lead_snapshot": boolean,           # Was this a lead snapshot?
    "inbox_merge": boolean               # Flag for merge operations
  }
}
```

---

### **Key Fields Explained**
| Field Group          | Purpose                                                                 |
|----------------------|-------------------------------------------------------------------------|
| **Identity/URLs**    | Track job via URL (handles redirects).                                   |
| **Company**          | Normalize company data for deduplication and sector analysis.            |
| **Title/Location**   | Standardize title + geo for filtering.                                  |
| **Remote Eligibility** | Boolean flag for remote work eligibility (not just "remote").           |
| **Posting Metadata** | Track source, certs, and posting time for provenance.                   |
| **Content**          | Full description + snippet for deduplication.                           |
| **Tracks**           | Categorize jobs (e.g., ITAM/SN/SF) for downstream analytics.             |
| **Liveness/Dead-Link**| Validate link health post-scraping.                                      |
| **Evidence**         | Log provenance (scrape timestamp, deduplication hashes).                |

---

### **Mapping from `scan_boards.py`/`render_board.py` Shapes**
#### **1. Lead Snapshot Shape → Job Schema**
```python
# Example output from scan_boards.py
{
  "job
