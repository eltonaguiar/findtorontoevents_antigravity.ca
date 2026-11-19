# Lab Validation: Create Your First Correlation Rule

## Pass Criteria

- [ ] Correlation rule created successfully with no validation errors
- [ ] Rule is Active and Order is set
- [ ] Test event sent with source matching rule filter
- [ ] Test event has severity matching rule severity
- [ ] Incident auto-created from the correlation rule
- [ ] Incident linked to the correct CI in Affected CIs related list
- [ ] Event record shows it was consumed by the rule

## Fail Actions

- If no incident is created: Verify the rule is Active; check the **System Log** (`System Logs → All`) for correlation rule evaluation errors
- If incident is created but CI is wrong: Verify the `{{ci}}` substitution variable; ensure the event has a CI selected
- If incident is not linked to CI: Check the action's CI field configuration; ensure the rule passes the CI value

## Screenshots to Capture

1. Correlation rule form with all fields filled
2. Event form being submitted with test data
3. New incident appearing in the incident list
4. Incident detail page showing CI linked in Affected CIs