# Delegated task output

- endpoint: `http://127.0.0.1:4000/v1/chat/completions`
- model: `ULTRA_FREE_CLOUD_FAST`
- generated_utc: 2026-11-18T03:54:16Z
- status: ok

## Response

**Geo/Eligibility Heuristics for Toronto/GTA and Canada-Remote Job Matching**
===========================================================

### Toronto Core and GTA Cities

*   **Toronto Core**: If the job is located in Toronto's core area (e.g., downtown Toronto), consider it a high-priority match for Toronto-based candidates.
*   **GTA Cities**: For GTA cities like Mississauga, Markham, Brampton, Vaughan, Etobicoke, Scarborough, North York, Richmond Hill, Oakville, and Burlington, consider them as secondary priority matches for Toronto-based candidates.

### Ontario/Canada-Remote Signals

*   **Ontario-Remote**: If the job is listed as "Ontario-remote" or has a similar signal, consider it a match for Ontario-based candidates.
*   **Canada-Remote**: For jobs listed as "Canada-remote" or have a similar signal, consider them as matches for Canadian candidates, regardless of province or territory.

### French Terms (Télétravail, à distance, Canada à distance)

*   **Télétravail**: If the job is listed with the French term "Télétravail" (telecommuting), consider it a match for French-speaking candidates in Canada.
*   **à distance**: For jobs listed with the French term "à distance" (remote), consider them as matches for French-speaking candidates in Canada.
*   **Canada à distance**: If the job is listed with the French term "Canada à distance" (Canada remote), consider it a match for French-speaking candidates across Canada.

### Hybrid/Onsite Ambiguity

*   **Hybrid**: If the job is listed as "hybrid" or has a similar signal, consider it a match for candidates who can work remotely part-time and onsite part-time.
*   **Onsite**: For jobs listed as "onsite" or have a similar signal, consider them as matches for candidates who can work exclusively from the office.

### Global-Remote-Confirm Cases

*   **Global Remote**: If the job is listed as "global remote" or has a similar signal, consider it a match for candidates worldwide, regardless of location.
*   **Confirm Remote**: For jobs listed with a "confirm remote" signal, consider them as matches for candidates who can work remotely and have a flexible schedule.

### Decision Rules and Examples

*   **Rule 1**: If the job is located in Toronto's core area, consider it a high-priority match for Toronto-based candidates.
    *   Example: Job listing for a software developer in downtown Toronto.
*   **Rule 2**: If the job is listed as "Ontario-remote" or has a similar signal, consider it a match for Ontario-based candidates.
    *   Example: Job listing for a customer service representative in Ontario with a remote work option.
*   **Rule 3**: If the job is listed as "Canada-remote" or has a similar signal, consider it a match for Canadian candidates, regardless of province or territory.
    *   Example: Job listing for a data analyst in Canada with a remote work option.
*   **Rule 4**: If the job is listed with the French term "Télétravail" or has a similar signal, consider it a match for French-speaking candidates in Canada.
    *   Example: Job listing for a marketing specialist in Quebec with a télétravail option.
*   **Rule 5**: If the job is listed as "hybrid" or has a similar signal, consider it a match for candidates who can work remotely part-time and onsite part-time.
    *   Example: Job listing for a sales representative in Toronto with a hybrid work arrangement.
*   **Rule 6**: If the job is listed as "global remote" or has a similar signal, consider it a match for candidates worldwide, regardless of location.
    *   Example: Job listing for a software engineer with a global remote work option.

By applying these geo/eligibility heuristics, you can effectively match job listings with candidates based on their location and work preferences.
