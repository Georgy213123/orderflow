import type { Design, DesignParams, RequestDetail } from "./api";

function num(request: RequestDetail, key: string, fallback: number): number {
  const v = request.fields.find((f) => f.key === key)?.value;
  const n = v ? Number.parseInt(v, 10) : Number.NaN;
  return Number.isFinite(n) ? n : fallback;
}

/** Параметры шкафа по умолчанию: из подтверждённых полей заявки или из сохранённой конструкции. */
export function initialParams(request: RequestDetail, design: Design | null): DesignParams {
  if (design) return design.params;
  return {
    width_mm: num(request, "width_mm", 800),
    height_mm: num(request, "height_mm", 2000),
    depth_mm: num(request, "depth_mm", 500),
    thickness_mm: 16,
    shelves: num(request, "shelves", 0),
    doors: num(request, "doors", 0),
    back_panel: true,
    board_code: "LDSP16-WHITE",
    edge_code: "EDGE04-WHITE",
    back_code: "HDF3-WHITE",
    handle_code: "HW-HANDLE",
  };
}
