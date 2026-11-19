```markdown
# Dedupe Analysis and Synthesis for Batch-A

## Dedupe Rules

### Auto-Merge
- **Same ATS, Same Tenant, Same Posting ID**: Auto-merge if all three criteria match.

### Review
- **Same ATS, Same Tenant, Different Posting ID**: Review if the normalized canonical URL matches.
- **Same Title, Same Company, Same Area**: Review if the city is different.

### Keep Separate
- **Different ATS or Tenant**: Keep separate.
- **Same Title, Same City**: Keep separate if the company or area is different.
- **US Twin Separate**: Keep separate if the location is remote-CA and there is a US twin.

### Anti-Merge Cases
- **Rejected Candidates**: Keep separate if the candidate status is rejected.
- **Zero Roles**: Keep separate if there are zero roles.

## Synthesis

### Executive Summary of Batch-A

Batch-A consists of 9 leads with varying criteria for deduplication. The leads include:

- **eqbank (lever, GTA, candidate-dev)**
- **versapay (lever, remote-CA, candidate-dev; US twin separate)**
- **levio (greenhouse, Quebec, 6 needs-ontario-check)**
- **servicenow (smartrecruiters, sales, rejected)**
- **solink (ashby, 0 roles)**

Key points for deduplication:
- Auto-merge leads with the same ATS, tenant, and posting ID.
- Review leads with the same ATS and tenant but different posting IDs if the normalized canonical URL matches.
- Review leads with the same title, company, and area if the city is different.
- Keep leads separate if the ATS or tenant is different.
- Keep leads separate if the title and city are the same but the company or area is different.
- Keep leads separate if there is a US twin for remote-CA leads.
- Keep rejected candidates and leads with zero roles separate.

This analysis ensures that leads are appropriately merged, reviewed, or kept separate based on the given criteria.
```