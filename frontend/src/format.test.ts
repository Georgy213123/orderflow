import { describe, expect, it } from "vitest";
import { edgeLabel, formatDate, formatKop, formatQty, sourceLabel, statusIndex } from "./format";

describe("format", () => {
  it("деньги из копеек без float-арифметики", () => {
    expect(formatKop(1233196)).toBe("12 331,96 ₽");
    expect(formatKop(5)).toBe("0,05 ₽");
    expect(formatKop(-150)).toBe("-1,50 ₽");
  });

  it("количество из строки Decimal", () => {
    expect(formatQty("10.49")).toBe("10,49");
    expect(formatQty("8.000000")).toBe("8");
    expect(formatQty("9.125152")).toBe("9,125152");
    expect(formatQty("1.150")).toBe("1,15");
  });

  it("источник поля", () => {
    expect(sourceLabel("text")).toBe("найдено в тексте");
    expect(sourceLabel("human")).toBe("ввёл человек");
  });

  it("порядок статусов", () => {
    expect(statusIndex("new")).toBe(0);
    expect(statusIndex("sent")).toBe(4);
  });

  it("дата и кромка", () => {
    expect(formatDate("2026-10-01")).toBe("01.10.2026");
    expect(formatDate(null)).toBe("—");
    expect(edgeLabel(2, 2)).toBe("2 дл. + 2 кор.");
    expect(edgeLabel(0, 0)).toBe("—");
  });
});
