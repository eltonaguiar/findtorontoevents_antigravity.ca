# ServiceNow ACL Types

Access Control Lists (ACLs) in ServiceNow define who can access what data and what they can do with it. There are several types of ACLs, each serving a specific purpose.

## 1. Standard ACL (Record-Level)

Standard ACLs control access to entire records (rows) on a table. They are evaluated based on the following operations:

- **read** – Can the user view the record?
- **write** – Can the user update the record?
- **create** – Can the user insert a new record?
- **delete** – Can the user delete the record?

If no ACL is defined for a given operation, the system defaults to the table's `access_control` property or the `admin` role.

## 2. Field-Level ACL

Field-Level ACLs restrict access to individual fields (columns) within a record. They support:

- **read** – Can the user see the field's value?
- **write** – Can the user modify the field's value?

Field ACLs are evaluated after the record-level ACL. If a user passes the record ACL but fails the field ACL, they can see the record but not the specific field (or cannot edit it).

## 3. Temporary ACL

Temporary ACLs are generated at runtime by scripts (e.g., via `GlideAjax` or background scripts) and are not stored in the database. They are useful for dynamic access decisions that depend on context (e.g., time of day, session variables).

## 4. ACL with Conditions

ACLs can include a **condition** script that returns true or false. The condition allows complex logic (e.g., based on field values, user roles, or external data) to determine whether access is granted.

## 5. ACL with Script

Instead of a simple role check, ACLs can run a **script** to determine access. The script must return `answer = true` to grant access. This is the most flexible type but should be used sparingly for performance.

## 6. ACL Hierarchy Evaluation

When multiple ACLs match (e.g., table ACL and field ACL), ServiceNow evaluates them in this order:

1. Field ACL (most specific)
2. Record ACL
3. Table ACL (least specific)

If any ACL in the chain denies access, access is denied.

## 7. Best Practices

- Use **roles** rather than hard-coded user IDs or groups.
- Keep conditions and scripts simple to avoid performance issues.
- Prefer field ACLs for sensitive data (e.g., password, salary).
- Always test ACLs with multiple user roles.
- Use **Access Control Debugger** to troubleshoot.

---

### ACL Types Infographic

Below is a simple ASCII art diagram illustrating the ACL evaluation hierarchy.

```
+-------------------+
|   Field ACL       |
| (read/write)      |
+--------+----------+
         |
+--------v----------+
|   Record ACL      |
| (read/write/create/delete) |
+--------+----------+
         |
+--------v----------+
|   Table ACL       |
| (default access)  |
+-------------------+
```
