ServiceNow ACL Evaluation Flow

When a user attempts to read, write, create, or delete a record, ServiceNow evaluates Access Control Lists (ACLs) in the following order:

1. Table-level ACL (record ACL) for the requested operation.
   - If no table ACL grants access, evaluation stops and access is denied.
   - If table ACL grants access, proceed to step 2.

2. Field-level ACL (if applicable) for each field being accessed.
   - Field ACLs only run when the parent table ACL permits the operation.
   - If any field ACL denies access, that field is not accessible (read/write) or the operation may be blocked depending on the operation type.

ACL Components:
- Condition builder (preferred) or Script.
- Scripts must set answer = true to grant access.
- Field-level scripts have access to current and previous (on update) but not gs; use current instead.
- ACLs can be role-specific or global (blank role).

Debugging:
- Enable glide.sys.log_security or use Session Debug → Security to see evaluated ACLs with pass/fail.

Best Practices:
- Prefer Condition builder over scripts for performance.
- Separate create and write ACLs when needed.
- Layer ACLs with Data Policies (mandatory/read-only) and Business Rules for server‑side logic that must always run.
