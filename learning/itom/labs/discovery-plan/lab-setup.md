# Lab Setup: Create Your First Discovery Plan

## Pre-conditions

- `com.snc.itom` plugin must be activated (System Definition → Plugins)
- User must have `sn_itom.admin` or `sn_itom.user` role
- A discovery source target must be reachable from the instance

## Required Roles

- `sn_itom.admin` – Full access to create and run discovery plans
- `sn_itom.user` – Can create plans and run them
- `itil` – Can view CIs and discovery results

## Required Plugins

- `com.snc.itom` – ITOM scoped application (required)
- `com.snm.discovery` – Discovery engine (automatically installed with ITOM)

## Environment Setup

- Ensure the target device (host) is reachable from the ServiceNow instance
- For SNMP discovery: Verify the SNMP community string is correct and the device responds
- For SSH discovery: Verify SSH is enabled on the target and the username/password works
- Have a test CI ready in the CMDB to verify discovery results

## Clean-up

- Delete the discovery plan and source after the lab if not needed for permanent use
- Remove any test CIs that were created during the lab