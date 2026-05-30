# Execution Plan — Sprint: Brain /ping endpoint

## Contract Summary

Two artifacts required:
- `packages/brain/src/routes/ping.js` — route handler
- `tests/ping.test.js` — test file

Two behaviors verified:
- `GET /api/brain/ping` → HTTP 200 with `{ pong: true, ts: <unix_timestamp> }`

---

## Commit Order (TDD discipline: test first)

### Commit 1 — Failing E2E/unit test (defines "done")

Create `tests/ping.test.js` with a test that will fail until the route is implemented.

**File: `tests/ping.test.js`**

```js
// tests/ping.test.js
import { describe, test, expect, beforeAll, afterAll } from 'vitest';
import express from 'express';
import request from 'supertest';

// We import the route before it exists — this will fail until commit 2
import pingRouter from '../packages/brain/src/routes/ping.js';

describe('GET /api/brain/ping', () => {
  let app;

  beforeAll(() => {
    app = express();
    app.use('/api/brain', pingRouter);
  });

  test('returns HTTP 200', async () => {
    const res = await request(app).get('/api/brain/ping');
    expect(res.status).toBe(200);
  });

  test('response contains pong: true', async () => {
    const res = await request(app).get('/api/brain/ping');
    expect(res.body.pong).toBe(true);
  });

  test('response contains ts as positive unix timestamp', async () => {
    const before = Math.floor(Date.now() / 1000);
    const res = await request(app).get('/api/brain/ping');
    const after = Math.floor(Date.now() / 1000);
    expect(typeof res.body.ts).toBe('number');
    expect(res.body.ts).toBeGreaterThan(0);
    expect(res.body.ts).toBeGreaterThanOrEqual(before);
    expect(res.body.ts).toBeLessThanOrEqual(after);
  });
});
```

At this point, `vitest` will fail with a module-not-found error on the import — confirming the test is genuinely failing before the implementation exists.

---

### Commit 2 — Implementation (makes the test pass)

Create `packages/brain/src/routes/ping.js` following the established ESM Router pattern used by every other route in this package (e.g. `status.js`, `actions.js`).

**File: `packages/brain/src/routes/ping.js`**

```js
// packages/brain/src/routes/ping.js
import { Router } from 'express';

const router = Router();

/**
 * GET /api/brain/ping
 * Lightweight liveness check.
 * Returns { pong: true, ts: <unix_seconds> }
 */
router.get('/ping', (req, res) => {
  res.status(200).json({
    pong: true,
    ts: Math.floor(Date.now() / 1000),
  });
});

export default router;
```

Then wire the router into `packages/brain/src/routes.js`:

```js
// Add import near the top of routes.js, alongside other route imports:
import pingRouter from './routes/ping.js';

// Add to the router registration block (after existing routes):
router.use('/', pingRouter);
```

After this commit, `vitest` passes all three tests and the live curl commands in the contract verify correctly:

```bash
curl -sf localhost:5221/api/brain/ping | jq -e '.pong == true'   # → true
curl -sf localhost:5221/api/brain/ping | jq -e '.ts > 0'         # → true
```

---

## File Creation Order

| Step | File | Action |
|------|------|--------|
| 1 | `tests/ping.test.js` | Create (failing test — commit 1) |
| 2 | `packages/brain/src/routes/ping.js` | Create (route implementation — commit 2) |
| 3 | `packages/brain/src/routes.js` | Edit (wire in pingRouter — commit 2) |

---

## Design Decisions

- **ESM syntax** (`import`/`export default`): matches the existing codebase; `packages/brain` uses `"type": "module"`.
- **`Math.floor(Date.now() / 1000)`**: produces a standard Unix epoch integer (seconds), satisfying `.ts > 0` trivially and making the value predictable in tests.
- **`router.get('/ping', ...)` mounted via `router.use('/', pingRouter)`**: consistent with how `dispatchRouter` and others attach directly at the root of `/api/brain/`.
- **No database dependency**: ping is a pure liveness check — no pool import, no async DB call. This keeps it fast and available even during DB degradation.
- **Test uses `supertest`**: avoids spinning up a real HTTP server; tests the Express router directly and in-process, making them fast and hermetic.

---

## What Would Make This Sprint FAIL

- `packages/brain/src/routes/ping.js` missing or not exporting a default Router.
- `routes.js` not mounting the pingRouter (route would 404 in production even if unit test passes).
- `ts` field returning milliseconds instead of seconds (`.ts > 0` would still pass, but the field would be inconsistent with Unix convention and mislead callers).
- Test file importing from a path that doesn't match the artifact path in the contract.
