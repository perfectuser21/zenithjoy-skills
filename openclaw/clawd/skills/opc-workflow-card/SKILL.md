---
name: opc-workflow-card
description: "Deterministically project OPC Workflow/Task lifecycle events into one continuously updated Feishu card, maintain the Card Registry, and handle card actions without creating duplicate cards. Use for OPC_WORKFLOW_EVENT and OPC_CALLBACK messages."
---

# OPC Workflow Card Bridge

Cards are projections of Work Commander facts. Never invent or independently advance workflow state.

## Lifecycle event

For an `OPC_WORKFLOW_EVENT` request, pass the exact JSON payload to:

```text
node skills/opc-workflow-card/scripts/card-registry.mjs upsert --payload-base64 <base64-json>
```

The script deduplicates by `event_id`, creates or patches the registered card, and returns the message ID and card version. Do not send a second card manually.

For a recovery attempt, keep the same Workflow Run card and `message_id`. A new `execution_id` is accepted only when `resumes_execution_id` exactly matches the Registry's current execution and the current terminal status is `blocked` or `failed`; then the Registry advances to the new attempt and continues patching the original card. Never resume a card from `completed` or `stopped`, and never create a replacement card merely because the attempt changed.

When invoked through n8n, finish with exactly one line `CARD_PROJECTION_RESULT <script-json>`. If the script reports `ok=false`, do not emit a success marker.

## Card callback

For `OPC_CALLBACK <json>`:

1. Preserve the exact action JSON plus inbound `event_id`, `message_id`, `chat_id` and sender ID when available.
2. Run:

```text
node skills/opc-workflow-card/scripts/card-registry.mjs action --payload-base64 <base64-json>
```

3. `open_task_detail`, `open_workflow_summary` and `open_evidence` patch the registered card in place.
4. `mark_blocked` sends a scoped control event to n8n; only Work Commander may change workflow truth. The card displays the request until Commander writes back.
5. Duplicate callbacks are idempotent. Unknown run/card/action returns a factual error and creates nothing.

Do not interpret a button click as a new Task. Do not send links to nonexistent applications. Do not use card buttons as URLs unless a verified destination URL exists.
