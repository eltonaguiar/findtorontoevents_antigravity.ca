# COMS Status Report

## History Preservation
- Messages are stored in the local cache of the agents and are typically retained until the agent is restarted.
- In the event that an agent goes offline, the messages sent during the downtime will not be lost if they are stored in the COMS system. However, the details can depend on the configuration and setup of the system.

## Offline Agent Behavior
- If one agent's computer was offline, it may lose real-time communication but not the stored messages.
- Once the agent reconnects, it should sync the messages from the COMS system, allowing it to catch up on missed interactions.

## Local File Storage
- Messages may be stored locally, but this is often not a default behavior and varies by agent configuration.
- Clarification on local storage specifics can be provided based on the implementation.