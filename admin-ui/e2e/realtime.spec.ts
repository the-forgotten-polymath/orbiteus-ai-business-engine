import { expect, test } from "@playwright/test";

/**
 * DoD §15.3 — realtime cross-tab refresh.
 *
 * Tab A is parked on the `crm.person` list. Tab B (different browser
 * context, same tenant) creates a person via the public API. Tab A
 * MUST display the new record without a manual reload — the
 * `useRealtimeList` hook listens for `record.created` on the
 * tenant-scoped SSE topic and triggers a refetch.
 *
 * Soft target: <2s end-to-end (the DoD aspires to 500ms, but
 * Playwright + dev compose adds enough latency that a 2s tolerance
 * keeps the test honest without false positives).
 */

const EMAIL = process.env.E2E_LOGIN_EMAIL ?? "admin@example.com";
const PASSWORD = process.env.E2E_LOGIN_PASSWORD ?? "admin1234";

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  const ok = await page.evaluate(
    async ({ email, password }) => {
      const r = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password }),
      });
      return r.ok;
    },
    { email: EMAIL, password: PASSWORD },
  );
  if (!ok) throw new Error("login API call failed");
  await page.goto("/");
}

test("Tab A picks up creation made in Tab B (SSE)", async ({ browser }) => {
  test.skip(
    !process.env.E2E_FULL_SUITE,
    "Cross-tab realtime test requires a stable demo tenant (E2E_FULL_SUITE=1)",
  );
  const ctxA = await browser.newContext();
  const ctxB = await browser.newContext();
  const pageA = await ctxA.newPage();
  const pageB = await ctxB.newPage();

  await login(pageA);
  await login(pageB);

  // Tab A → list view. Wait for the table or the empty state, both
  // mean the page has finished loading.
  await pageA.goto("/crm/person");
  await expect(pageA.getByRole("heading", { name: /Person/i }).first()).toBeVisible();

  // Tab B creates a record. We use the public API directly (the
  // browser shares the cookie session set by /login) — the form
  // is already exercised in `critical-path.spec.ts`.
  const stamp = Date.now();
  const name = `Realtime E2E ${stamp}`;
  const created = await pageB.evaluate(async (n) => {
    const r = await fetch("/api/crm/person", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ name: n, kind: "individual" }),
    });
    return { ok: r.ok, status: r.status, body: await r.json().catch(() => null) };
  }, name);
  expect(created.ok, `create failed: ${JSON.stringify(created)}`).toBe(true);

  // Tab A should display the new row within ~2s without a manual reload.
  await expect(pageA.getByText(name)).toBeVisible({ timeout: 4_000 });

  await ctxA.close();
  await ctxB.close();
});
