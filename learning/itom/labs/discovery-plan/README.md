# Lab: Create Your First Discovery Plan

**Time:** 30-40 minutes

## Goal

Create a Discovery plan that automatically discovers CIs and populates the CMDB.

## Step 1: Navigate to Discovery Plans

**Breadcrumb:** All > IT Operations Management > Discovery > Plans > New

## Step 2: Create the Plan

| Field | Value | Notes |
|-------|-------|-------|
| Name | `My First Discovery Plan` | Descriptive name |
| Description | `Runs custom discovery every day at 2AM` | Optional but helpful |
| Schedule | `0 2 * * *` | Runs daily at 2 AM |
| Active | Checked | Enable the plan |
| Error Handling | `stop_on_error` | Stop on first error |
| Max Runtime | `3600` | 1 hour maximum |

## Step 3: Add a Discovery Source

| Field | Value | Notes |
|-------|-------|-------|
| Name | `My Discovery Source` | Source identifier |
| Type | `SNMP` or `SSH` | Depends on device type |
| Host | `hostname-or-ip` | Target device |
| Credentials | Select existing or create new | SSH key or username/password |

## Step 4: Run the Plan

1. Click **Run** on the plan record
2. Observe the **Discovery Results** related list
3. Check for any **errors** in the log

## Step 5: Verify CI Population

1. Navigate to All > CMDB > CI List
2. Verify new CIs appeared from the discovery run
3. Check related lists for discovered relationships

---

**Time:** 30-40 minutes