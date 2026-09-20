# ZenithJoy Social Publication Contract

Verified local bridge baseline: 2026-09-19. Re-read the live bridge status before every production run; this file is a routing contract, not live account state.

## Capability matrix

| Platform | Delivery mode | Current adapter | Current boundary |
| --- | --- | --- | --- |
| Facebook Page | `public` | `POST /api/meta/publish` | Text and public photo posts are live-tested. Production gate defaults off. |
| Instagram Business | `public` | `POST /api/meta/publish` | Public image posts are live-tested. Reels/video/carousels are not implemented. Production gate defaults off. |
| TikTok | `draft` | `POST /api/tiktok/draft` | Uploads to the TikTok inbox/draft flow when the live creator/token check passes. |
| TikTok | `private` | `POST /api/tiktok/publish` | Direct Post adapter is restricted to `SELF_ONLY`; production gate defaults off. |
| TikTok | `public` | none | Blocked until TikTok app review and creator capability return a public privacy option. |

Shopify product/catalog sync, Meta Commerce, TikTok Shop, paid ads, and account administration are separate capabilities.

## Input

```json
{
  "tenant_id": "zenithjoy",
  "content_object_id": "content-20260919-001",
  "platform": "instagram",
  "delivery_mode": "public",
  "action": "preview",
  "approval_id": "approval-record-id",
  "idempotency_key": "content-20260919-001-instagram-v1",
  "caption": "Approved caption",
  "media_url": "https://www.zenithjoyai.com/media/content-20260919-001.jpg"
}
```

Platform fields:

- Facebook: `message` and optional `media_url`.
- Instagram: `caption` and required `media_url`.
- TikTok draft: required `video_url`.
- TikTok private: `video_url`, `duration_seconds`, optional `title`, plus explicit booleans `is_aigc`, `promotes_own_brand`, and `paid_partnership`.
- TikTok status: `publish_id`.

## Runtime secrets

- `SOCIAL_PUBLISH_BRIDGE_KEY`: internal Bearer credential, injected from the runtime secret store.
- `SOCIAL_PUBLISH_BRIDGE_URL`: optional base URL; defaults to `https://www.zenithjoyai.com`.

Platform access tokens stay in the publishing bridge/Cloudflare secret store. OpenClaw must not receive Meta or TikTok platform tokens directly.

## State handling

- `validate` and `preview` create no platform publication.
- `execute` is an external write and needs an approval record or verified preauthorization.
- Reuse the identical `idempotency_key` and payload for a retry.
- `idempotency_key_conflict`, ambiguous outcomes, or `publish_outcome_requires_review` are review states, not retry prompts.
- Store `Submitted` until a platform content ID and platform readback/permalink exist.
- Store `Published` only after the platform result is independently readable.
