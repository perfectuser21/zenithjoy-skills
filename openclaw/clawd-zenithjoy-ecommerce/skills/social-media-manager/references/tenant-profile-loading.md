# Tenant Profile Loading Contract

The manager loads the tenant-specific profile from the approved social-media tenant registry. In the current blueprint the registry is:

`media/config/social-media-tenants.json`

The registry key must be the canonical `tenant_id`. The current entries are `zenithjoy` and `jinnuoshengyuan`. Each entry contains the company label, manager role, workflow, platform adapter, device binding, account roles, destination resources, run policy, readiness, and approval boundary.

Compatibility IDs are input aliases only:

```json
{
  "yueshengyun": "zenithjoy",
  "jinoshengyuan": "jinnuoshengyuan"
}
```

Normalize the ID first, then load exactly one entry. Pass the normalized `tenant_id`, the selected profile reference, and any `legacy_tenant_id` to the Commander and every Worker. A missing profile, mismatched Agent, device, account, or destination is a blocked run; do not fall back to another tenant.

The registry is an operational binding source, not a place to store secrets. Credentials and raw tokens remain in the configured secret/auth stores.
