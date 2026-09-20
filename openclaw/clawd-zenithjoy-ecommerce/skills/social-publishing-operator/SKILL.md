---
name: social-publishing-operator
description: Publish or upload an approved ZenithJoy content object to Facebook, Instagram, or TikTok through the existing authenticated publishing bridge. Use for previewing, executing, checking, or reconciling a social publication; do not use for content strategy, paid ads, account setup, or Shopify catalog sync.
---

# Social Publishing Operator

Use this Skill from the existing `social-media-manager` Agent, or from the approved
department Agent while it is explicitly acting with
`manager_role=social-media-manager`. The current single-Agent bootstrap for
cross-border commerce uses `zenithjoy-ecommerce` in that manager role until a
separate Social Media Manager runtime can be introduced without restarting an
active Gateway. Do not create one Agent per platform and do not route publication
through the lead-generation phone Worker.

## Ownership

- `social-media-manager`: selects the approved content object, platform variants, schedule, and acceptance criteria.
- `zenithjoy-ecommerce`: may temporarily perform the same manager role for
  `tenant_id=zenithjoy` in the approved single-Agent department bootstrap; it
  must load the canonical ZenithJoy tenant profile and preserve the same approval,
  idempotency, and readback requirements.
- This Skill: validates one frozen publication contract, calls the deterministic bridge, preserves idempotency, and returns evidence.
- `zenithjoy-shared-social-media`: remains the bounded lead-generation Worker; it does not publish.
- `infra` / `dev`: own bridge deployment, secret injection, API scopes, and production gates.

## Required contract

Every run must include:

- `tenant_id=zenithjoy`;
- `content_object_id` from the canonical content pipeline;
- `platform`: `facebook`, `instagram`, or `tiktok`;
- `delivery_mode`: `public`, `draft`, or `private` as allowed by the platform matrix;
- `action`: `validate`, `preview`, `execute`, or `status`;
- a stable `idempotency_key` for `execute`;
- an `approval_id` for every external write, unless the frozen task carries a verified standing preauthorization that resolves to an approval record;
- the platform-specific text/media fields.

The frozen content object and its approval record take precedence over chat wording. A missing or stale approval blocks execution but not validation or preview.

Read [the publication contract and capability matrix](references/publishing-contract.md) when selecting a platform or delivery mode.

## Execute

Use the deterministic helper:

```text
node scripts/social-publish.mjs --input /path/to/publication.json
```

The runtime must inject `SOCIAL_PUBLISH_BRIDGE_KEY`; the default bridge base is `https://www.zenithjoyai.com` and may be overridden with `SOCIAL_PUBLISH_BRIDGE_URL`. Never print either value or copy them into a task, content record, log, or Skill.

1. Load exactly the `zenithjoy` tenant profile and confirm the account/platform binding.
2. Read the canonical content object. Reject a mutable chat-only draft.
3. Run `action=validate`, then `action=preview`.
4. For `action=execute`, require approval evidence, a stable idempotency key, a verified HTTPS media URL, and the production gate already enabled by an authorized infrastructure workflow. This Skill never changes a gate, OAuth scope, account setting, or secret.
5. Preserve the same idempotency key and identical payload for retries. A conflict, ambiguous outcome, timeout, or pending state goes to review; never invent a new key and retry blindly.
6. Read back the platform result. TikTok uses `action=status` with `publish_id`. Meta must have a returned content ID plus platform permalink/readback before the business object becomes `Published`; otherwise record `Publish submitted / verification pending`.
7. Write the result to the content object and run/event ledger: platform, content ID, permalink/evidence URL, actor, approval ID, idempotency key, timestamp, and next check.

## Boundaries

- Facebook and Instagram publication is an L3 external action. The server gate is fail-closed and remains off outside an approved publication window.
- TikTok draft upload is supported separately from direct posting. Direct public TikTok posting is unavailable until the app review and creator capability readback allow it.
- This Skill does not create ads, change budget, manage comments/messages, alter account privacy, install sales channels, or sync Shopify products.
- CAPTCHA, login challenge, account warning, missing platform asset, `401/403`, permission error, or identity mismatch is a blocking result. Do not use browser automation as a silent fallback.

## Completion

Return one structured result with `content_object_id`, platform, delivery mode, action, approval ID, idempotency key, remote ID/status, evidence URL when available, and `next_check_at`. Completion requires target-system evidence; a successful HTTP request alone is not enough.
