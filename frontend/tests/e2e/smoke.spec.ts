import { expect, test } from "@playwright/test";

test("loads the unauthenticated login screen", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Workspace Login" })).toBeVisible();
});
