import { expect, test, type Page } from "@playwright/test";

/**
 * Сквозной сценарий US-01…US-05: заявка из текста → подтверждение → конструкция →
 * спецификация → смета с ожидаемым итогом → статус «смета готова».
 * Ожидаемый итог 12 331,96 ₽ — тот же, что в unit-тесте сметы (EXPECTED_TOTAL_KOP).
 */
const REQUEST_TEXT =
  "Здравствуйте! Нужен шкаф в прихожую 1200х2100х600 мм, 4 полки, две двери. " +
  "Меня зовут Анна Смирнова, телефон +7 (900) 123-45-67, почта anna@example.com";

const FIELDS = [
  "product_type",
  "width_mm",
  "height_mm",
  "depth_mm",
  "shelves",
  "doors",
  "client_name",
  "phone",
  "email",
];

async function pasteAndParse(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "+ Новая заявка" }).click();
  await page.getByLabel("Текст заявки").fill(REQUEST_TEXT);
  await page.getByRole("button", { name: "Разобрать текст" }).click();
  await expect(
    page.getByRole("heading", { name: /1\. Заявка №\d+/ }),
  ).toBeVisible();
}

test("менеджер вставляет текст, поля подсвечены как найденные в тексте", async ({
  page,
}) => {
  await pasteAndParse(page);
  for (const key of FIELDS) {
    const row = page.getByTestId(`field-${key}`);
    await expect(row).toHaveAttribute("data-state", "guess");
    await expect(page.getByTestId(`field-${key}-source`)).toHaveText(
      "найдено в тексте",
    );
  }
  await expect(page.getByLabel(/Ширина, мм/)).toHaveValue("1200");
  await expect(page.getByLabel(/Телефон/)).toHaveValue("+79001234567");
  await expect(
    page.getByRole("button", { name: "Заявка разобрана" }),
  ).toBeDisabled();
  await expect(page.getByTestId("missing")).toContainText("не подтверждено");
});

test("полный путь: заявка → конструкция → смета готова", async ({ page }) => {
  await pasteAndParse(page);

  // Менеджер правит глубину и подтверждает остальное.
  const depth = page.getByLabel(/Глубина, мм/);
  await depth.fill("600");
  for (const key of FIELDS) {
    const row = page.getByTestId(`field-${key}`);
    await row.getByRole("button").click();
    await expect(row).toHaveAttribute("data-state", "confirmed");
  }
  await expect(page.getByTestId("field-width_mm-source")).toHaveText(
    "найдено в тексте",
  );
  await page.getByLabel(/Клиент/).fill("Анна Смирнова-Кедрова");
  await page
    .getByTestId("field-client_name")
    .getByRole("button", { name: "Сохранить" })
    .click();
  await expect(page.getByTestId("field-client_name-source")).toHaveText(
    "ввёл человек",
  );

  await page.getByRole("button", { name: "Заявка разобрана" }).click();
  await expect(page.getByTestId("status")).toHaveAttribute(
    "data-status",
    "parsed",
  );

  // Конструктор: параметры подставлены из заявки, ошибка валидации видна сразу.
  const form = page.locator("form.design-form");
  await expect(form.getByLabel("Ширина, мм")).toHaveValue("1200");
  await form.getByLabel("Дверей").fill("1");
  await page.getByRole("button", { name: "Построить спецификацию" }).click();
  await expect(page.getByTestId("design-problems")).toContainText(
    "ширина двери 1196 мм",
  );
  await form.getByLabel("Дверей").fill("2");
  await page.getByRole("button", { name: "Построить спецификацию" }).click();

  const spec = page.getByTestId("spec");
  await expect(spec.locator('tr[data-part="shelf"]')).toContainText(
    "1166 × 580",
  );
  await expect(spec.locator('tr[data-part="door"]')).toContainText(
    "2096 × 596",
  );
  await expect(page.getByTestId("status")).toHaveAttribute(
    "data-status",
    "designed",
  );

  await page.getByRole("button", { name: "Посчитать смету" }).click();
  await expect(page.getByTestId("estimate-total")).toHaveText("12 331,96 ₽");
  // Нетто и запас в едином формате: 2 знака для м² и м, ×1,10 вместо ×1,1 (BUG-11).
  const estimate = page.getByTestId("estimate");
  await expect(estimate).toContainText("9,13");
  await expect(estimate).toContainText("21,97");
  await expect(estimate).toContainText("×1,10");
  await expect(estimate).not.toContainText("9,125152");
  await expect(page.getByTestId("status")).toHaveAttribute(
    "data-status",
    "estimated",
  );
  await expect(page.getByTestId("estimate-warnings")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Отправить клиенту" }),
  ).toBeEnabled();
});

test("смета без цены помечена неполной, отправка закрыта", async ({ page }) => {
  await pasteAndParse(page);
  for (const key of FIELDS) {
    await page.getByTestId(`field-${key}`).getByRole("button").click();
  }
  await page.getByRole("button", { name: "Заявка разобрана" }).click();
  await page
    .locator("form.design-form")
    .getByLabel("Ручки")
    .selectOption("HW-HANDLE-BLACK");
  await page.getByRole("button", { name: "Построить спецификацию" }).click();
  await page.getByRole("button", { name: "Посчитать смету" }).click();
  await expect(page.getByTestId("estimate-warnings")).toContainText(
    "итог неполный",
  );
  await expect(page.getByText("Итого (неполный)")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Отправить клиенту" }),
  ).toBeDisabled();
});
