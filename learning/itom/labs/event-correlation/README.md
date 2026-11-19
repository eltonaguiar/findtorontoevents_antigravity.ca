# Lab: Create Your First Correlation Rule

**Time:** 30-40 minutes

## Goal

Create a correlation rule that automatically creates an incident from repeated high-severity events.

## Step 1: Navigate to Correlation Rules

**Breadcrumb:** All > IT Operations Management > Event Management > Correlation Rules > New

## Step 2: Create the Rule

| Field | Value | Notes |
|-------|-------|-------|
| Name | `Multiple High Severity Events` | Descriptive name |
| Active | Checked | Enable the rule |
| Order | `10` | Lower numbers run first |
| Source Filter | `Test Integration` | Filter by source |
| Severity | `2` (Major) | Only Major+ severity |
| Condition | `source` contains `Test` AND `severity` = `2` | Advanced condition |

## Step 3: Define the Action

| Field | Value | Notes |
|-------|-------|-------|
| Action | Create Incident | Auto-create an incident |
| Incident Short Description | `Multiple high-severity events from {{ci}}` | Use substitution variables |
| Incident Category | `incident` | Default category |
| Assign to Group | `IT Operations` | Assignment group |
| CI | `{{ci}}` | Link to affected CI |

## Step 4: Test the Rule

1. Send a test event with source `Test Integration` and severity `2`
2. Verify an incident was auto-created
3. Check the incident is linked to the correct CI

## Step 5: Verify

1. Navigate to All > Incidents > All
2. Confirm the new incident appears
3. Verify the incident is linked to the correct CI in the Affected CIs related list

---

**Time:** 30-40 minutes