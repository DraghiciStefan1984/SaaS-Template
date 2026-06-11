import { expect, test } from "@playwright/test";

test("loads the public landing page", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "Launch clear SaaS products from one stable core" }),
  ).toBeVisible();
});

test("public pages do not create horizontal page overflow on a 320px viewport", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 568 });

  for (const path of ["/", "/login", "/register", "/terms"]) {
    await page.goto(path);
    const dimensions = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));

    expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth);
  }
});
