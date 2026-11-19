# Lab Validation: Create Your First Discovery Plan

## Pass Criteria

- [ ] Discovery plan created successfully with no script errors
- [ ] Discovery source added to the plan without validation errors
- [ ] Plan run completed status is `Success` or `Completed`
- [ ] New CIs appear in All > CMDB > CI List after the run
- [ ] At least one discovered CI has required fields populated (asset_tag, model, location)
- [ ] No critical errors in the Discovery run log

## Fail Actions

- If the plan fails to run: Check the **System Log** (`System Logs → All`) for errors related to the discovery source credentials or network connectivity
- If no CIs appear: Verify the discovery source is Active and the Host field is correct; ping/connect to the target device manually
- If CIs appear but fields are empty: Check the discovery mapper configuration; ensure the mapper is mapping the expected attributes

## Screenshots to Capture

1. Discovery plan form with all fields filled
2. Discovery plan Run button clicked
3. Discovery Results related list showing success
4. CMDB CI List showing new CIs
5. New CI record with populated fields