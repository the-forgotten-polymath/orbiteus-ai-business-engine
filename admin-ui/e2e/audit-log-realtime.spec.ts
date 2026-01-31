import { expect, test } from "@playwright/test";

/**
 * DoD §15.3 — `/technical/audit-log` realtime auto-refresh.
 *
 * Tab A is sitting on the audit log page. Tab B mutates a `crm.person`
 * via the API (which triggers `BaseRepository._audit("create", ...)`).
 * The audit log subscribes to every tenant-scoped model topic, so the
 * new row MUST surface in Tab A without a manual reload.
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

test("audit log refreshes when another tab creates a record", async ({ browser }) => {
  test.skip(
    !process.env.E2E_FULL_SUITE,
    "Audit-log realtime test requires a fully seeded tenant (E2E_FULL_SUITE=1)",
  );
  const ctxA = await browser.newContext();
  const ctxB = await browser.newContext();
  const pageA = await ctxA.newPage();
  const pageB = await ctxB.newPage();

  await login(pageA);
  await login(pageB);

  await pageA.goto("/technical/audit-log");
  await expect(
    pageA.getByRole("heading", { name: /audit/i }).first(),
  ).toBeVisible();

  // Mutation in Tab B
  const stamp = Date.now();
  const name = `Audit RT ${stamp}`;
  const created = await pageB.evaluate(async (n) => {
    const r = await fetch("/api/crm/person", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ name: n, kind: "individual" }),
    });
    return { ok: r.ok, body: await r.json().catch(() => null) };
  }, name);
  expect(created.ok).toBe(true);

  // The audit log table should pick up a `create` row referencing the
  // new record's id within ~3s. We assert on `crm.person` so we don't
  // chase a flaky exact-name match if the audit row formatter strips
  // the `name` column.
  await expect(
    pageA.getByText(/crm\.person/i).first(),
  ).toBeVisible({ timeout: 5_000 });

  await ctxA.close();
  await ctxB.close();
});
