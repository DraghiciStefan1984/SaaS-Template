import { expect, test } from "@playwright/test";

test("loads the public landing page", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "Launch clear SaaS products from one stable core" }),
  ).toBeVisible();
});
