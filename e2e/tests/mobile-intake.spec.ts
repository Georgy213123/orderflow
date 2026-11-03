import { expect, test } from "@playwright/test";

test.describe("мобильная форма заявки", () => {
  test.skip(({ isMobile }) => !isMobile, "только мобильный вьюпорт");

  test("ввод вручную на 390 px: без горизонтальной прокрутки, поля сохраняются", async ({
    page,
  }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Заполнить вручную" }).click();
    await expect(page.getByRole("heading", { name: /Заявка №/ })).toBeVisible();

    const width = page.getByLabel(/Ширина, мм/);
    await width.fill("900");
    await page
      .getByTestId("field-width_mm")
      .getByRole("button", { name: "Сохранить" })
      .click();
    await expect(page.getByTestId("field-width_mm-source")).toHaveText(
      "ввёл человек",
    );
    await expect(page.getByTestId("field-width_mm")).toHaveAttribute(
      "data-state",
      "confirmed",
    );

    const overflow = await page.evaluate(
      () =>
        document.documentElement.scrollWidth -
        document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
    await expect(page.getByTestId("missing")).toContainText(
      "Телефон: не заполнено",
    );
  });
});
