import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Field } from "../api";
import { FieldRow } from "./FieldRow";

const def = { key: "width_mm" as const, label: "Ширина, мм" };
const guess: Field = {
  key: "width_mm",
  label: "Ширина, мм",
  value: "1200",
  source: "text",
  confirmed: false,
  fragment: "1200х2100х600 мм",
  required: true,
};

describe("FieldRow (US-02)", () => {
  it("предположение разбора подсвечено и ждёт подтверждения", () => {
    render(<FieldRow def={def} field={guess} required editable onSave={vi.fn()} />);
    expect(screen.getByTestId("field-width_mm")).toHaveAttribute("data-state", "guess");
    expect(screen.getByTestId("field-width_mm-source")).toHaveTextContent("найдено в тексте");
    expect(screen.getByText("не подтверждено")).toBeInTheDocument();
    expect(screen.getByText("«1200х2100х600 мм»")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Подтвердить" })).toBeEnabled();
  });

  it("подтверждение отправляет то же значение", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<FieldRow def={def} field={guess} required editable onSave={onSave} />);
    await userEvent.click(screen.getByRole("button", { name: "Подтвердить" }));
    expect(onSave).toHaveBeenCalledWith("width_mm", "1200");
  });

  it("правка меняет кнопку на «Сохранить»", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<FieldRow def={def} field={guess} required editable onSave={onSave} />);
    const input = screen.getByLabelText(/Ширина/);
    await userEvent.clear(input);
    await userEvent.type(input, "1250");
    await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));
    expect(onSave).toHaveBeenCalledWith("width_mm", "1250");
  });

  it("подтверждённое поле не подтверждают повторно", () => {
    render(
      <FieldRow
        def={def}
        field={{ ...guess, confirmed: true }}
        required
        editable
        onSave={vi.fn()}
      />,
    );
    expect(screen.getByText("подтверждено")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Подтвердить" })).toBeDisabled();
  });

  it("пустое поле без источника", () => {
    render(<FieldRow def={def} required editable onSave={vi.fn()} />);
    expect(screen.getByTestId("field-width_mm")).toHaveAttribute("data-state", "empty");
    expect(screen.queryByTestId("field-width_mm-source")).toBeNull();
  });
});

describe("FieldRow: очистка необязательного поля (R-08)", () => {
  it("ошибочно найденную почту можно убрать", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const email: Field = {
      ...guess,
      key: "email",
      label: "Почта",
      value: "x@y.z",
      required: false,
    };
    render(
      <FieldRow
        def={{ key: "email", label: "Почта" }}
        field={email}
        required={false}
        editable
        onSave={onSave}
      />,
    );
    await userEvent.clear(screen.getByLabelText("Почта"));
    await userEvent.click(screen.getByRole("button", { name: "Убрать" }));
    expect(onSave).toHaveBeenCalledWith("email", "");
  });

  it("обязательное поле пустым не сохраняется", async () => {
    render(<FieldRow def={def} field={guess} required editable onSave={vi.fn()} />);
    await userEvent.clear(screen.getByLabelText(/Ширина/));
    expect(screen.getByRole("button", { name: "Сохранить" })).toBeDisabled();
  });
});
