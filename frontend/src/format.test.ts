import { describe, expect, it } from "vitest";
import {
  edgeLabel,
  formatDate,
  formatFactor,
  formatKop,
  formatQuantity,
  sourceLabel,
  statusIndex,
} from "./format";

describe("format", () => {
  it("деньги из копеек без float-арифметики", () => {
    expect(formatKop(1233196)).toBe("12 331,96 ₽");
    expect(formatKop(5)).toBe("0,05 ₽");
    expect(formatKop(-150)).toBe("-1,50 ₽");
  });

  it("количество по единице: м² и м — 2 знака, штуки — целые (BUG-11)", () => {
    expect(formatQuantity("9.125152", "m2")).toBe("9,13");
    expect(formatQuantity("2.506816", "m2")).toBe("2,51");
    expect(formatQuantity("21.968", "m")).toBe("21,97");
    expect(formatQuantity("10.49", "m2")).toBe("10,49");
    expect(formatQuantity("10.5", "m2")).toBe("10,50");
    expect(formatQuantity("8.000000", "pcs")).toBe("8");
    expect(formatQuantity("16", "pcs")).toBe("16");
  });

  it("округление половины вверх по строке, без float", () => {
    expect(formatQuantity("0.125", "m")).toBe("0,13");
    expect(formatQuantity("0.124999", "m")).toBe("0,12");
    expect(formatQuantity("9.995", "m2")).toBe("10,00");
    expect(formatQuantity("1234.5", "m2")).toBe("1 234,50");
    expect(formatQuantity("2.5", "pcs")).toBe("3");
  });

  it("коэффициент запаса всегда с двумя знаками (BUG-11)", () => {
    expect(formatFactor("1.15")).toBe("1,15");
    expect(formatFactor("1.1")).toBe("1,10");
    expect(formatFactor("1.100")).toBe("1,10");
    expect(formatFactor("1.000")).toBe("1,00");
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
