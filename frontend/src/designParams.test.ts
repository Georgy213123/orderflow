import { describe, expect, it } from "vitest";
import type { RequestDetail } from "./api";
import { initialParams } from "./designParams";

const request: RequestDetail = {
  id: 1,
  raw_text: "",
  status: "parsed",
  status_label: "разобрана",
  parser: "rules",
  created_at: "2026-11-01T10:00:00Z",
  missing: [],
  fields: [
    { key: "width_mm", value: "1200" },
    { key: "height_mm", value: "2100" },
    { key: "shelves", value: "4" },
  ].map((f) => ({
    ...f,
    key: f.key as RequestDetail["fields"][number]["key"],
    label: "",
    source: "text" as const,
    confirmed: true,
    fragment: null,
    required: false,
  })),
};

describe("initialParams (US-03)", () => {
  it("параметры шкафа берутся из подтверждённых полей заявки", () => {
    const p = initialParams(request, null);
    expect(p.width_mm).toBe(1200);
    expect(p.height_mm).toBe(2100);
    expect(p.shelves).toBe(4);
    expect(p.depth_mm).toBe(500); // не указано в заявке — значение по умолчанию
    expect(p.doors).toBe(0);
  });
});
