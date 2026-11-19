# Lab Setup: Create Your First Correlation Rule

## Pre-conditions

- `com.snc.itom` plugin must be activated (System Definition → Plugins)
- `com.snc.event_management` plugin must be activated (if separate from ITOM)
- User must have `sn_itom.admin` or `sn_itom.user` role
- At least one CI must exist in the CMDB to link the event to

## Required Roles

- `sn_itom.admin` – Full access to create correlation rules and send events
- `sn_itom.user` – Can create rules and send events
- `itil` – Can view incidents and events

## Required Plugins

- `com.snc.itom` – ITOM scoped application (required)
- `com.snc.event_management` – Event Management (often installed with ITOM)

## Environment Setup

- Have at least one CI in the CMDB with `asset_tag` and `serial_number` populated
- Prepare a test event source name (e.g., `Test Integration`) that will match the rule's source filter
- Ensure the test CI has a valid `sys_id` to use in the test event

## Clean-up

- Delete the correlation rule after the lab if not needed for permanent use
- Remove the test event if it remains in the system
- Keep the incident as a reference or delete it if it's a test record