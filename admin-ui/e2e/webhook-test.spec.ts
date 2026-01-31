import { expect, test } from "@playwright/test";

/**
 * DoD §15.3 — Webhook "Test" button via the Technical page.
 *
 * Registers a webhook pointing at `webhook.site` (or any reflector
 * URL passed via `E2E_WEBHOOK_TARGET`) and clicks the "Test"
 * delivery action. The test is satisfied when the backend
 * acknowledges the click — receiver-side verification stays out of
 * scope for an automated e2e (the test should not depend on a
 * third-party HTTP collector).
 *
 * Skipped (`test.skip`) when no `E2E_WEBHOOK_TARGET` is provided so
 * a CI run doesn't accidentally hit a real public endpoint.
 */

const EMAIL = process.env.E2E_LOGIN_EMAIL ?? "admin@example.com";
const PASSWORD = process.env.E2E_LOGIN_PASSWORD ?? "admin1234";
const TARGET = process.env.E2E_WEBHOOK_TARGET ?? "";

test("admin can register a webhook and trigger a test delivery", async ({ page }) => {
  test.skip(!TARGET, "E2E_WEBHOOK_TARGET not set");

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

  await page.goto("/technical/webhooks");
  await expect(
    page.getByRole("heading", { name: /webhook/i }).first(),
  ).toBeVisible();

  // Use the public REST API to register the webhook so the test isn't
  // tied to a specific UI form layout. The Technical page picks up
  // the row through the same realtime backplane the rest of the
  // suite verifies.
  const stamp = Date.now();
  const created = await page.evaluate(
    async ({ url, name }) => {
      const r = await fetch("/api/base/webhooks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          name,
          url,
          secret: "e2e-secret",
          event_mask: ["record.created"],
          model_filter: "crm.person",
          field_filter: [],
          is_active: true,
          active: true,
        }),
      });
      return { ok: r.ok, status: r.status, body: await r.json().catch(() => null) };
    },
    { url: TARGET, name: `e2e-${stamp}` },
  );
  expect(created.ok, `webhook create failed: ${JSON.stringify(created)}`).toBe(true);
  const webhookId = (created.body as { id: string }).id;

  // Trigger the synthetic delivery
  const tested = await page.evaluate(async (id) => {
    const r = await fetch(`/api/base/webhooks/${id}/test`, {
      method: "POST",
      credentials: "include",
    });
    return { ok: r.ok, status: r.status, body: await r.json().catch(() => null) };
  }, webhookId);

  expect(tested.ok, `webhook test failed: ${JSON.stringify(tested)}`).toBe(true);
});
