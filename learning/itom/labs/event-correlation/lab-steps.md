# Lab Steps: Create Your First Correlation Rule

## Step 1: Navigate to Correlation Rules

**Breadcrumb:** All > IT Operations Management > Event Management > Correlation Rules > New

1. Go to the Application Navigator (left sidebar)
2. Search for "Event Management"
3. Navigate to **Correlation Rules** under IT Operations Management > Event Management
4. Click **New** on the Correlation Rules list header

## Step 2: Configure the Rule Form

Fill in the correlation rule form:

| Field | Value | Required |
|-------|-------|----------|
| Name | `Multiple High Severity Events` | Yes |
| Active | Checked | Yes |
| Order | `10` | Yes (lower runs first) |
| Source | `Test Integration` | Recommended |
| Severity | `2` (Major) | Yes |
| Advanced Condition | `source` contains `Test` AND `severity` = `2` | Yes |

1. Click **Submit** to save the rule

## Step 3: Define the Action

1. After saving the rule, scroll to the **Actions** related list
2. Click **New** on the Actions related list
3. Configure the action:

| Field | Value | Notes |
|-------|-------|-------|
| Action | `Create Incident` | Auto-create an incident |
| Short Description | `Multiple high-severity events from {{ci}}` | Use `{{ci}}` substitution |
| Category | `incident` | Default incident category |
| Assignment Group | `IT Operations` | Select appropriate group |
| CI | `{{ci}}` | Link alert to CI |
| Description | `Auto-created from correlation rule: Multiple High Severity Events` | Optional |

4. Click **Submit**

## Step 4: Send a Test Event

1. Navigate to All > IT Operations Management > Event Management > Events > New
2. Fill in the event form:

| Field | Value | Notes |
|-------|-------|-------|
| Source | `Test Integration` | Must match rule source filter |
| Severity | `2` (Major) | Must match rule severity |
| CI | Select a CI from the CMDB | Must exist in CMDB |
| Description | `Test event for correlation rule` | Optional |
| State | `New` | Default state |

3. Click **Submit**

## Step 5: Verify the Result

1. Wait a few seconds for the correlation rule to evaluate
2. Navigate to All > Incidents > All
3. Confirm the new incident appears with:
   - Short Description: `Multiple high-severity events from <CI name>`
   - Correct CI linked in the Affected CIs related list
4. Check the Event record to see if it was consumed by the rule

---