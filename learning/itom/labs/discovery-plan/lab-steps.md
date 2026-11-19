# Lab Steps: Create Your First Discovery Plan

## Step 1: Navigate to Discovery Plans

**Breadcrumb:** All > IT Operations Management > Discovery > Plans > New

1. Go to the Application Navigator (left sidebar)
2. Search for "Discovery Plans"
3. Click **Discovery Plans** under IT Operations Management

## Step 2: Create a New Plan

1. Click **New** on the Discovery Plans list header
2. Fill in the form:

| Field | Value | Required |
|-------|-------|----------|
| Name | `My First Discovery Plan` | Yes |
| Description | `Runs custom discovery daily at 2AM` | Optional |
| Schedule | `0 2 * * *` (cron: daily at 2 AM) | Yes |
| Active | Checked | Yes |
| Error Handling | `stop_on_error` | Recommended |
| Max Runtime | `3600` (seconds) | Recommended |

3. Click **Submit**

## Step 3: Add a Discovery Source

1. In the plan record, find the **Discovery Sources** related list
2. Click **New** on that related list
3. Fill in the source fields:

| Field | Value | Notes |
|-------|-------|-------|
| Name | `My Discovery Source` | Source identifier |
| Type | `SNMP` (or `SSH`, `WMI`) | Depends on device type |
| Host | `snomophone.example.com` | Target device hostname or IP |
| Port | `161` (for SNMP) or `22` (for SSH) | Default ports |
| Version | `v2c` or `v3` | SNMP version |
| Community | `public` (for v2c) | SNMP community string |
| Username | `admin` (for SSH/v3) | SSH username or SNMP v3 user |
| Authentication Password | `your-auth-password` | For SNMP v3 or SSH |
| Privacy Password | `your-privacy-password` | For SNMP v3 or SSH |

4. Click **Submit**

## Step 4: Run the Discovery Plan

1. Back on the plan record, click **Run** in the header menu
2. The plan status will change to `Running`
3. Wait for the run to complete (may take a few minutes)
4. Check the **Discovery Results** related list for outcomes

## Step 5: Verify CI Population

1. Navigate to All > CMDB > CI List
2. Look for new CIs that appeared from the discovery run
3. Click on a newly discovered CI to view its details
4. Check the **Discovery Results** related list on the CI record
5. Verify the CI has appropriate fields populated (asset_tag, model, location, etc.)

---