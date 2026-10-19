# ServiceNow ACL Evaluation Flow

## Learning Objectives
- Understand the order of ACL evaluation in ServiceNow.
- Distinguish between table-level and field-level ACLs.
- Recognize the role of conditions and scripts in ACLs.
- Know how to debug ACL effectiveness.

## Section 1: ACL Evaluation Order
**Key Concept:** ServiceNow evaluates ACLs in a specific sequence.
**Content Verbatim:** When a user attempts to read, write, create, or delete a record, ServiceNow evaluates Access Control Lists (ACLs) in the following order:
1. Table-level ACL (record ACL) for the requested operation.
   - If no table ACL grants access, evaluation stops and access is denied.
   - If table ACL grants access, proceed to step 2.
2. Field-level ACL (if applicable) for each field being accessed.
   - Field ACLs only run when the parent table ACL permits the operation.
   - If any field ACL denies access, that field is not accessible (read/write) or the operation may be blocked depending on the operation type.
**Visual Element:** Flowchart with two steps: Table ACL → Field ACL, each with decision diamonds (Grant/Deny).
**Text Labels:** Step 1: Table-level ACL, Step 2: Field-level ACL
**Data Points:** None

## Section 2: ACL Components
**Key Concept:** ACLs consist of conditions or scripts.
**Content Verbatim:** ACL Components:
- Condition builder (preferred) or Script.
- Scripts must set answer = true to grant access.
- Field-level scripts have access to current and previous (on update) but not gs; use current instead.
- ACLs can be role-specific or global (blank role).
**Visual Element:** Icons representing Condition builder (gear) and Script (</>).
**Text Labels:** Condition Builder, Script
**Data Points:** None

## Section 3: Debugging ACLs
**Key Concept:** Use built‑in debugging to see ACL evaluation results.
**Content Verbatim:** Debugging:
- Enable glide.sys.log_security or use Session Debug → Security to see evaluated ACLs with pass/fail.
**Visual Element:** Bug/magnifying glass icon.
**Text Labels:** Debug ACLs
**Data Points:** None

## Section 4: Best Practices
**Key Concept:** Follow recommended practices for effective ACL design.
**Content Verbatim:** Best Practices:
- Prefer Condition builder over scripts for performance.
- Separate create and write ACLs when needed.
- Layer ACLs with Data Policies (mandatory/read-only) and Business Rules for server‑side logic that must always run.
**Visual Element:** Checklist icon.
**Text Labels:** Best Practices
**Data Points:** None