# Card Registry v2

- Primary key: `workflow_run_id + object_id + audience_key`.
- One projection card per primary key.
- `event_id` and callback `event_id` are dedupe keys.
- Registry stores message ID, chat ID, sender profile, view, version, latest lifecycle event and a bounded timeline.
- Only lifecycle events from n8n/Work Commander change workflow status.
- Card callbacks may change presentation immediately; control actions become lifecycle truth only after Commander writes back.
