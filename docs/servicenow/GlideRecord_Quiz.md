# GlideRecord Quiz

Test your knowledge of ServiceNow GlideRecord syntax. For each scenario, write the GlideRecord code snippet that fulfills the requirement. After you've written your answer, you can check the solution by expanding the details section.

---

## Question 1: Active Incidents from Last 7 Days

**Scenario:**  
You need to retrieve all **active** incident records (state = 1 or 2, assuming 1 = New, 2 = In Progress) that were created in the last 7 days.

**Requirement:**  
Write the GlideRecord code that adds the necessary conditions for:
- Active state
- Created on or after 7 days ago (relative to now)

**Hint:**  
You can use `addQuery` for state and a date condition for `sys_created_on`.

<details>
<summary>Check Solution</summary>

```javascript
var gr = new GlideRecord('incident');
gr.addQuery('active', true); // or state IN (1,2) depending on your table
gr.addQuery('sys_created_on', '>=', gs.daysAgoStart(7));
gr.query();
```
</details>
---

## Question 2: Sort Descending by sys_created_on

**Scenario:**
You have a GlideRecord query that retrieves some records. You need to sort the results so the newest records appear first.

**Requirement:**
Add the appropriate line to sort the GlideRecord in descending order based on the `sys_created_on` field.

<details>
<summary>Check Solution</summary>

```javascript
gr.orderByDesc("sys_created_on");
```

</details>

