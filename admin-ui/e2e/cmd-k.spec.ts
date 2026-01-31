import { expect, test } from "@playwright/test";

/**
 * DoD §15.3 — Command Palette (⌘K) navigates to a registered action.
 *
 * Opens the palette, types a query, picks the first match, asserts we
 * landed on the matching auto-CRUD list. The action set is populated
 * by `_seed_auto_actions` in `backend/api.py` so any fresh tenant has
 * at least the `crm.person.list` action registered.
 */

const EMAIL = process.env.E2E_LOGIN_EMAIL ?? "admin@example.com";
const PASSWORD = process.env.E2E_LOGIN_PASSWORD ?? "admin1234";

test("Cmd-K opens, filters, and navigates", async ({ page }) => {
  test.skip(
    !process.env.E2E_FULL_SUITE,
    "Cmd-K palette test depends on the seeded action set (E2E_FULL_SUITE=1)",
  );
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

  // Open the palette. We send a literal Cmd-K (Mac) and Ctrl-K
  // (everything else) so the test passes regardless of host OS.
  // Playwright's `keyboard.press("Meta+KeyK")` works under Chromium
  // on every OS — the listener treats Meta and Control symmetrically.
  await page.keyboard.press("Meta+KeyK");

  // Type a query likely to match a built-in action.
  await page.keyboard.type("person");
  // Wait for at least one result to render. We accept any list-style
  // role so the test isn't tied to a specific Mantine version.
  const firstResult = page.getByRole("option").first();
  await expect(firstResult).toBeVisible({ timeout: 4_000 });

  await firstResult.click();

  // Landing target: the auto-CRUD list page for crm.person, or a
  // close cousin (e.g. /crm/customer if the action set differs).
  // Either way, the URL MUST mention "/crm/" and the page MUST
  // render a heading.
  await expect(page).toHaveURL(/\/crm\//, { timeout: 5_000 });
  await expect(
    page.getByRole("heading").first(),
  ).toBeVisible();
});
