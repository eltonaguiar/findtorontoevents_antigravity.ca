# SmartRecruiters Detail Pass and Workday Routing Plan for BestieJob Job-Hunt Swarm

## SmartRecruiters Detail Pass

### Step 1: Identify Target Postings
- **eqbank/versapay**: 2 candidates
- **ServiceNow board**: 100 postings for build roles

### Step 2: Execute Detail Pass
- **Endpoint**: POST /postings/{id}/details
- **Parameters**:
  - `--max-details 100`
  - Honor `retry-After` header
  - Stop on status codes: 401, 403, 429

### Step 3: Classification
- **Read Duties**: Focus on platform+build actions
- **Exclude**: Sales roles (CPQ role rejected)

## Workday Routing

### Step 1: Identify Target Tenants
- Use `scripts/gap_channels_scan.py` for big-5/consulting tenants
- **BatchA Execution Plan**: List of tenants

### Step 2: Apply Gates
- Apply same gates as identified in the SmartRecruiters detail pass