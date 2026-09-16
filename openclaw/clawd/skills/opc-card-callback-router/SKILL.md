---
name: opc-card-callback-router
description: "Handle OPC Workflow/Task Feishu card button callbacks through the deterministic Card Registry bridge and route control actions to n8n/Work Commander."
---

# OPC Card Callback Router v2

## Trigger

An inbound card action arrives as:

`OPC_CALLBACK {"action":"open_task_detail","workflow_run_id":"...","attempt_id":"...","execution_id":"...","object_id":"...","audience_key":"..."}`

Only accept a JSON object with `action` and `workflow_run_id`, plus inbound message context. Preserve inbound card action event ID, message ID, chat ID and sender ID when available.

## Execute

1. Merge the callback JSON with context fields: `event_id`, `message_id`, `chat_id`, `sender_id`.
2. Base64-encode the compact JSON without changing values.
3. Run exactly once:

```text
node /root/clawd/skills/opc-workflow-card/scripts/card-registry.mjs action --payload-base64 <base64-json>
```

4. Trust the script's registry lookup and dedupe result. Do not send or patch another card manually.
5. If successful, reply with a short acknowledgement only when Feishu requires one; the card itself is the result.

## Actions

- `open_task_detail`: patch the registered card to its current Task view.
- `open_workflow_summary`: patch the same card back to Workflow view.
- `open_evidence`: show only evidence from the latest registered lifecycle event.
- `mark_blocked`: send a scoped control request to n8n; Work Commander decides and writes back workflow truth.

Never create a new Task from a click. Never infer missing registry data. Never mutate workflow status directly. Duplicate callbacks are idempotent.
